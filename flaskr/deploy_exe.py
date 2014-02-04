"""
Windows attribute collection

Windows requires using winexe and starting a remote ssh server.
"""

import re
import subprocess
import sh
import shlex
import time


import collection_constants as constants

# TODO(marco): globals are evil: all the below should be moved to collection_constants.py

WINEXE_ERRORS = re.compile('NT_STATUS|Error:', re.I|re.M)
WINEXE_CHARSET_ERROR = re.compile('^dos charset .* unavailable - using ASCII$')
RE_DRIVE = re.compile(r'.*Drive ([A-Z]+): is now connected to .*', re.DOTALL)
DEFAULT_TEMP_DIR = 'C:\\WINDOWS\\TEMP'

#: the name of the directory to create under windows %TEMP% directory to hold temporary files
COLLECTION_DIR_NAME = 'collection'
START_SSH_SCRIPT = 'start_sshd.bat'

# the location within COLLECTION_DIR_NAME where cygwin is extracted to
CYGWIN_DIR_NAME = 'cygwin'

# the name of the self-extracting zip exe
CYGWIN_EXE_NAME = 'cygwin.exe'


#: maximum times to retry a winexe command
WINEXE_RETRIES = 5

#: sleep time between winexe retries
WINEXE_RETRY_WAIT_TIME = 5


class DeployToWindowsException(Exception):
    """
    A custom exception that can later be caught in phoenix.

    TODO: maybe call self.logger.debug with the exception message and stack trace?
    """
    pass


class WinexeException(Exception):
    '''
    Wraps sh.ErrorReturnCode in exception args or can be used as a custom (our)
    exception object when calling winexe
    '''
    def __init__(self, e):
        super(WinexeException, self).__init__(e)
        if isinstance(e, (Exception, BaseException)):
            self._args_is_exc = True
            # HACK to get "exit_code" from sh exception object. Unfortunately,
            # the author of sh seems to not want to stuff the exit_code as
            # part of the exception.
            if isinstance(e, (sh.ErrorReturnCode, sh.SignalException)):
                # the following split('_')[1] will never fail unless a future
                # version of sh abandons dynamic exit code-based exceptions.
                # e.__class__.__name__ is something like 'ErrorReturnCode_11'
                # and we want the "11" part.
                exit_code = e.__class__.__name__.split('_')[1]
                # may be not necessary but in case a process returns an error
                # like E10033, we just want to preserve that and not get an
                # exception from int()
                if exit_code.isdigit():
                    self.exit_code = int(exit_code)
                else:
                    self.exit_code = exit_code

            # suck in attributes from _other_ exception object into self
            # so that caller can directly access attributes. Eg. ErrorReturnCode
            # returns an instance that has e.full_cmd, e.stdout, e.stderr which
            # can be accessed in calling code. This exception exposes attributes
            # from the wrapped object.
            self.__dict__.update(e.__dict__.copy())
        else:
            self._args_is_exc = False

    def __str__(self):
        if self._args_is_exc:
            return self.args[0].message
        return self.message


class DeployToWindows(object):
    """
    Sets up the samba share and remote ssh server, also handles pre_collection
    and post_collection on the remote source machine.
    """

    DEFAULT_PROCESSES_TO_KILL = ['bash.exe', 'sshd.exe', 'sh.exe', 'cygpath.exe', 'mkpasswd.exe']

    def __init__(self, host, username, password,
                 samba_host, samba_share,
                 samba_user, samba_pass, logger, samba_collection_dir="collection"):
        """
        :param samba_collection_dir: Use this to refer to the folder name on
            the samba share that should be used on the source machine. This can
            be updated for different releases of the contents on the samba
            drive.
        """
        self.host = host
        self.username = username
        self.password = password
        self.logger = logger
        self.samba_host = samba_host
        self.samba_share = samba_share
        self.samba_user = samba_user
        self.samba_pass = samba_pass
        self.samba_drive = None
        self.samba_collection_dir = samba_collection_dir
        self.collection_dir = None
        #self.src_win_temp_dir = self.get_win_temp_dir()

    def get_win_temp_dir(self):
        """
        @return: the Windows source TEMP directory, as configured in the %TEMP% system property
        """
        cmd = 'cmd /C echo %TEMP%'
        s_out, s_err = self.sh_winexe_command(cmd)
        if s_err:
            self.logger.error('There was an error trying to retrieve Windows TEMP dir: {}'
                .format(s_err))
            # TODO(marco): not sure this is really desirable, but for now it's worth a try
            return DEFAULT_TEMP_DIR
        lines = s_out.splitlines()
        # the typical invocation of the command above will return something like:
        #    "dos charset 'CP850' unavailable - using ASCII\nC:\\WINDOWS\\TEMP\r\n"
        # note the inconsistent use of carriage returns (splitlines() takes care of that),
        # and the fact that the error message is
        # actually returned in stdout (NOT stderr) - but it may well not be there,
        # if the charset were to magically be there for some source machine.
        # Hence the use of 'defensive coding'
        if len(lines) > 1:
            if WINEXE_CHARSET_ERROR.match(lines[0]):
                return lines[1]
            elif len(lines) == 1:
                return lines[0]
            else:
                raise WinexeException('Could not reliably find Windows TEMP directory, '
                                      '`echo %TEMP%` returned: {}'.format(s_out))

    def setup(self, ssh_server_exe, ssh_port, skip_copy=False):
        """Prepares the source machine for collection

        Mounts the samba share that contains the .exe files and cygwin, then
        starts the SSH server
        """
        self.logger.info("Setting up Source machine for collection")
        self.cleanup_all()
        # get the samba_drive name from the remote output
        self.logger.debug('Mounting samba drive...')
        self.samba_drive = self.mount_samba()
        self.logger.debug('mounted on source machine: {0}'.format(self.samba_drive))
        samba_collection_path = '{0}\\\\{1}'.format(self.samba_drive, self.samba_collection_dir)

        # Copy Cygwin from Samba share to Source in the Windows\Temp collection directory
        if not skip_copy:
            self.copy_cygwin(samba_collection_path)
            self.copy_pywmi(samba_collection_path)

        # TODO: Check STDOUT and STDERR to make sure the command executed successfully
        # TODO: We shouldn't need to pass the collection_dir back to the parent.
        #   The directory we use should already be known and passed from the parent to this sub
        self.collection_dir = r'{param_win_temp_dir}\\\\{param_collection_dir}'.format(
            param_win_temp_dir=self.src_win_temp_dir,
            param_collection_dir=COLLECTION_DIR_NAME
        )

        # start the remote ssh server
        self.logger.info('Starting sshd on {0}'.format(ssh_port))
        self.start_sshd(ssh_server_exe, self.collection_dir, ssh_port)

        #add back the sleep if we need to
        #time.sleep(5)
        self.logger.info('sshd started.')
        self.unmount_samba(self.samba_drive)
        self.logger.info('pre_collection done.')
        return self.collection_dir

    def teardown(self):
        """ Kill the processes on source machine, delete the temp directory and unmount
            the samba share
        """
        self.logger.info('Teardown sequence started')
        self.cleanup_all()
        self.logger.info('Teardown sequence ends')

    def cleanup_all(self):
        """ Executes all clean up tasks

        It will run, in succession, the task kill job, stop the services and finally remove the
        directories that we created.
        """
        self.cleanup_taskkill()
        self.stop_services()
        self.cleanup_directories()

    def cleanup_taskkill(self, processes=None, is_pid=False):
        """ Kills all tasks in ```processes``` or a default list

        @param processes: should contain a list of the process names or process ids
        @type processes: list or None

        @param is_pid: whether the list contains PIDs
        @type is_pid: boolean

        @return: the standard output and error from killing processes
        @rtype: tuple
        """
        proclist = processes or DeployToWindows.DEFAULT_PROCESSES_TO_KILL
        taskkill_command = 'cmd /C'
        at_least_one = False
        pid_flag = '/PID' if is_pid else ''
        for proc in proclist:
            # we want to execute all the taskkill commands in one single invocation, so we use
            # the & to concatenate (note: this won't run them in background)
            # Windows supports also the && and || operators, but neither would actually work here.
            taskkill_command = ' '.join([taskkill_command, 'taskkill', '/F', '/T', '/IM',
                                         pid_flag, proc, '& '])
            at_least_one = True
        result = (None, None)
        # TODO(marco): we are currently wiping out ALL the processes named as the ones that we
        # want to 'cleanup': this may well trip some of our users' long-running processes,
        # we should guard against that and avoid messing it: use Tasklist to filter out processes
        # that were not remotely started
        if at_least_one:
            self.logger.info('Killing tasks: {}'.format(proclist))
            result = self.sh_winexe_command(taskkill_command)
        return result

    def cleanup_directories(self, directories=None):
        """ Removes all the directories that we created, or the list passed in

        @param directories: a list of directories to remove
        @return: list or None
        """
        if not directories:
            directories = [r'{param_win_temp_dir}\\\\{param_collection_dir}'.format(
                param_win_temp_dir=self.src_win_temp_dir,
                param_collection_dir=COLLECTION_DIR_NAME)
            ]
        command = 'cmd /C'
        for directory in directories:
            directory = ''.join(['"', directory, '"'])
            command = ' '.join([command, 'rmdir /S /Q', directory, '& '])
        self.sh_winexe_command(command)

    def stop_services(self, services_list=None):
        if not services_list:
            services_list = ['winexesvc']
        command = ''
        for service in services_list:
            # When SSHD works we should stop the winexesvc via SSH
            if "winexesvc" not in service:
                command = ' '.join([command, 'sc stop', service, '& '])
        if command:
            command = ' '.join(['cmd /C', command])
            self.sh_winexe_command(command)
        command = 'cmd /C'
        for service in services_list:
            command = ' '.join([command, 'sc delete', service, '& '])
        self.sh_winexe_command(command)

    def copy_cygwin(self, samba_collection_path):
        """ Creates a directory and copies the Cygwin binaries into it

        @param samba_collection_path: the Samba path to the Cygwin repository
        """
        command = r'cmd /C "IF NOT EXIST "{param_win_temp_dir}\\\\{param_collection_dir}\\\\" '\
                  r'mkdir "{param_win_temp_dir}\\\\{param_collection_dir}\\\\"'\
            .format(param_win_temp_dir=self.src_win_temp_dir,
                    param_collection_dir=COLLECTION_DIR_NAME)
        # TODO: Update sh_winexe_command with exit code return
        self.sh_winexe_command(command)

        # xcopy will prompt for "File or Directory?" so use echo F to bypass
        # /C is continue even if errors
        # /F is for verbose output
        # /Y is suppress file-already-exists prompting
        command = r'cmd /C "echo F | xcopy /C /Y /F ' \
                  r'"{param_samba_collection_path}\\\\{param_cygwin_exe_name}" '\
                  r'"{param_win_temp_dir}\\\\{param_collection_dir}\\\\{param_cygwin_exe_name}""'\
            .format(param_samba_collection_path=samba_collection_path,
                    param_win_temp_dir=self.src_win_temp_dir,
                    param_cygwin_exe_name=CYGWIN_EXE_NAME,
                    param_collection_dir=COLLECTION_DIR_NAME)
        # TODO: Update sh_winexe_command with exit code return
        self.sh_winexe_command(command)

        command = r'cmd /C "{param_win_temp_dir}\\\\{param_collection_dir}\\\\{param_cygwin_exe_name} -y -o {param_win_temp_dir}\\\\{param_collection_dir}\\\\{param_cygwin_dir_name}\\\\ "'
        command = command.format(
            param_win_temp_dir=self.src_win_temp_dir,
            param_cygwin_exe_name=CYGWIN_EXE_NAME,
            param_cygwin_dir_name=CYGWIN_DIR_NAME,
            param_collection_dir=COLLECTION_DIR_NAME,
        )
        # TODO: Update sh_winexe_command with exit code return
        self.sh_winexe_command(command)
        # TODO(marco): figure out a way to combine the above commands and minimize calls to winexe

    def copy_pywmi(self, orig):
        """ Copies pywmi.exe from the orig directory to the %TEMP%/COLLECTION_DIR_NAME directory

        @param orig: the Samba share (most likely) directory from where to copy WMI from
        @type orig: string
        """
        cmd = r'cmd /C copy "{orig}\\\\{pywmi_exe}" '\
              r'"{param_win_temp_dir}\\\\{param_collection_dir}\\\\{pywmi_exe}""'\
            .format(orig=orig,
                    pywmi_exe=constants.PYWMI_EXE,
                    param_win_temp_dir=self.src_win_temp_dir,
                    param_collection_dir=COLLECTION_DIR_NAME)
        self.sh_winexe_command(cmd)

    def sh_winexe_command(self, remote_command, system_user=True, ostype=2, **kwargs):
        """ The "sh" version of winexe. Looks a lot cleaner and the subprocess
        boiler plate is taken care of by the module. No more blocking on
        reading stdout/stderr
        @param remote_command: string, command to execute remote, properly escaped
        @param system_user: bool, run remote_command as Windows system user?
        @param ostype: integer, 1 or 2, (see winexe documentation)
        @param kwargs: dict, passed to sh module. Use carefully
        """
        winexe = sh.winexe.bake(system=system_user,
                                ostype=ostype,
                                user='{0}%{1}'.format(self.username, self.password))
        tries = WINEXE_RETRIES
        while tries:
            self.logger.debug("[WINEXE try {0}]".format(1 + WINEXE_RETRIES - tries))
            # Should probably use a callback or use _iter=True argument here

            try:
                self.logger.debug('Executing remotely: {}'.format(remote_command))
                output = winexe('//{0}'.format(self.host), remote_command, **kwargs)
                self.logger.debug('Remote execution of {} terminated normally'.format(
                    remote_command))
                # TODO(marco): IMO this is too verbose, but let's have it for a while and see
                self.logger.debug('[STDOUT] :: {}'.format(output.stdout))
                self.logger.debug('[STDERR] :: {}'.format(output.stderr))
                return output.stdout, output.stderr
            except sh.ErrorReturnCode, e:
                # TODO: Return process return code to caller - how does this deal with if we expect
                #   or want it to fail
                self.logger.error('Executing {0} caused {1}'.format(remote_command, e.message))
                self.logger.exception(e)
                self.logger.debug('[ErrorReturnCode]: {0}'.format(e.__name__))
                self.logger.debug('[e.stdout]: {0} \n --End of e.stdout --'.format(e.stdout))
                self.logger.debug('[e.stderr]: {0} \n --End of e.stderr --'.format(e.stderr))
                if WINEXE_ERRORS.findall(e.stdout):
                    self.logger.debug('Sleeeping for {1} seconds before retrying {0}'.format(
                        remote_command, WINEXE_RETRY_WAIT_TIME))
                    time.sleep(WINEXE_RETRY_WAIT_TIME)
                    tries -= 1
                    continue
                # As it took me a while to figure out the logic here, I'm adding this comment:
                # This exception will be raised if sh raises and ErrorReturnCode,
                # but this is not due to a failure in Winexe (because we don't find any
                # WINEXE_ERRORS in stdout) - so there's no point in retrying and just re-raise
                raise WinexeException(e)
        # This is raised if we exhaust all the retries and still there's a failure
        raise WinexeException('Permanent failure executing {0}'.format(remote_command))

    def exec_winexe_command(self, remote_command, detach=False, system_user=True, os_type=2):
        """ Mount the samba share on source

        @param remote_command: the remote command to execute
        @type remote_command: string
        @param detach: TODO(jnew): add explanation
        @type detach: bool
        @param os_type: 0 - 32bit, 1 - 64bit, 2 - winexe will decide (default)
        @type os_type: int
        @param system_user: whether this command should be executed with system user privileges
        @type system_user: bool

        @return: a t-uple containing stdout and stderr
        @rtype: tuple

        """
        system_str = '--system' if system_user else ''
        winexe_cmd = r'winexe {system_str} --ostype {ostype} '\
                     '-U {username}%{password} //{host} '.format(
                     ostype=os_type,
                     system_str=system_str,
                     username=self.username,
                     password=self.password,
                     host=self.host)
        cmd_args = shlex.split(winexe_cmd, posix=False)
        cmd_args += (remote_command, )
        self.logger.debug('[CMD_ARGS] {}'.format(cmd_args))
        self.logger.debug('[CMD] {}'.format(' '.join(cmd_args)))
        for i in range(1, WINEXE_RETRIES+1):
            (s_out, s_err) = ("", "")
            self.logger.debug('[WINEXE try {}]'.format(i))
            if detach:
                proc = subprocess.Popen(cmd_args, stdout=subprocess.PIPE)
            else:
                proc = subprocess.Popen(cmd_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                while True:
                    out_bytes = proc.stdout.read(2048)
                    err_bytes = proc.stderr.read(2048)
                    if not out_bytes and not err_bytes:
                        break
                    else:
                        s_out += out_bytes
                        s_err += err_bytes
                self.logger.debug('[STDOUT] {}'.format(s_out))
                self.logger.debug('[STDERR] {}'.format(s_err))
            #TODO(cindy): add checking for other NT_STATUS errors
            if 'NT_STATUS_' not in s_out and 'NT_STATUS_' not in s_err:
                self.logger.debug('Command succeeded in winexe try {}'.format(i))
                break
            time.sleep(WINEXE_RETRY_WAIT_TIME)
        return s_out, s_err

    def mount_samba(self, drive_letter=''):
        """
        Mount the samba share on the source machine and return the drive letter
        or samba host+share of the form \\smb_server\share.

        NOTE: support for drive_letter = '*' has been removed. Either provide a
        valid drive letter that you have divined to be free, or skip it to
        directly use \\smb_server\share

        The default usage is to mount the samba share without a drive and
        access \\smb_server\share directly in the code.
        """
        # DE424 to prevent:"Multiple connections to a server or shared resource
        # by the same user, using more than one user name, are not allowed.
        # Disconnect all previous connections to the server or shared resource
        # and try again." - we will unmount ALL mounts using \\host\path
        samba_host_share = r'\\{0}\{1}'.format(self.samba_host,
                                               self.samba_share)
        self.logger.debug('Unmounting ALL mounts from source {0} to {1}'.format(
            self.host, samba_host_share))
        self.unmount_samba(r'{0}'.format(samba_host_share))

        self.logger.debug('Mounting samba {0}'.format(samba_host_share))
        drive_letter = '{0}:'.format(drive_letter) if drive_letter else ''
        command = r'net use {drive_letter} {samba_host_share} '\
                  '/user:{samba_host}\\{samba_user} {samba_pass} '\
                  '/persistent:no'.format(
                        drive_letter=drive_letter,
                        samba_host=self.samba_host,
                        samba_host_share=samba_host_share,
                        samba_user=self.samba_user,
                        samba_pass=self.samba_pass
                  )
        (s_out, s_err) = self.exec_winexe_command(command)
        # TODO(kk): Check return code of execution, rather than text searches
        if 'The command completed successfully' in s_out:
            mount = drive_letter or samba_host_share
            self.logger.debug('Mounted samba share {0} as {1}'.format(samba_host_share, mount))
            return mount
        elif s_err:
            raise DeployToWindowsException(s_err)

    def unmount_samba(self, samba_drive=None):
        """Unmount a samba share
        """
        if not samba_drive:
            samba_drive = self.samba_drive
        self.logger.debug('Umounting samba drive {0}'.format(samba_drive))
        # net use can be used to unmount a specific drive or unmount by smb _share_
        # If samba_drive is a host (indicated by starting \\), then we don't use
        # the ':' drive indicator. If samba_drive is not a host, use ':'
        indicator, yes = (':', '/YES') if samba_drive and \
                not samba_drive.startswith(r'\\') else ('', '')
        command = 'net use {0}{1} /DELETE {2}'.format(samba_drive, indicator,
                                                      yes)
        (s_out, s_err) = self.exec_winexe_command(command)
        # TODO(kk), do something with s_out, s_err and check/handle return code
        if s_err:
            self.logger.error('Unmounting samba has errors: {0}'.format(s_err))
        self.logger.debug('Samba drive {0} umounted.'.format(samba_drive))

    def start_sshd(self, ssh_server_exe, collection_dir, ssh_port):
        """Start the SSHServer.exe on remote machine
        Run C:\\WINDOWS\\TEMP\\collection\\cygwin\\start_sshd.bat
        """
        self.logger.debug('Starting sshd.exe %s' % ssh_server_exe)

        # start_ssh.bat takes the cygwin dir as parameter
        cygwin_path = r'{0}\\{1}'.format(self.collection_dir, CYGWIN_DIR_NAME)
        command = r'cmd /c "{0}\\{1} {0} {2}"'.format(cygwin_path, START_SSH_SCRIPT,
                                               ssh_port)

        # Replace two backslashes with one, because running winexe using the sh
        # module with extra slashes seems to have strange outcomes.
        command = command.replace(r'\\', '\\')
        backoff = constants.SSHD_BACKOFF_INIT_SECS
        for retry in range(1, 4):
            try:
                backoff *= constants.SSHD_BACKOFF_FACTOR
                timeout = constants.START_SSHD_TIMEOUT_INIT_SECS * backoff
                (s_out, s_err) = self.sh_winexe_command(command, system_user=False,
                                                        _timeout=timeout)
                # wait for sometime for SSH server to start
                time.sleep(backoff)
                self.logger.debug('(start_sshd.bat) executed')
                break
            except WinexeException, e:
                self.logger.exception(e)
                self.logger.info('[STDOUT] {0}'.format(e.stdout))
                self.logger.error('[STDERR] {0}'.format(e.stderr))
                exc = e.args[0]
                # sh module raises SIGINT when running a process does not
                # terminate within 'timeout' seconds. By this, it means that
                # sh will raise a SignalException_9 (9 == SIGINT) which we can
                # catch and retry
                if isinstance(exc, sh.SignalException):
                    self.logger.warning('Timed out after {0} seconds'.format(timeout))
                    self.logger.warning('Retry #{0}:{1}'.format(retry, command))
                    continue
                raise DeployToWindowsException(exc)
        else:
            raise DeployToWindowsException('Unable to run {0} on {1}'.format(
                command, self.host))

        return None

