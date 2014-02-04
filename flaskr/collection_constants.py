"""
Constants used both by collect_attributes and data_collector_windows.

These are defaults that are overriden by command line arguments to those two
scripts.

There's another constant called DEFAULT_SSH_PORT but in data_collector_windows
it's 12541 and in collect_attributes it's 22, so it's not being included in
here since they probably serve different purposes.
"""

DEFAULT_SAMBA_HOST  = 'smb.rivermeadow.com'
DEFAULT_SAMBA_SHARE = 'sambarepo'
DEFAULT_SAMBA_USER  = 'shaman01'
DEFAULT_SAMBA_PASS  = 'scloud2012'

#: The default WMI executable we invoke remotely
PYWMI_EXE = 'pywmi.exe'

# used in deploy_exe.py:start_sshd()
# These values randomly picked out of a hat
# Initial "backoff" value. Backoff is so that code doesn't retry something at
# fixed intervals but using some variable timeout, sleep, etc.
SSHD_BACKOFF_INIT_SECS = 2
# This is the factor with which we multiply backoff, which is currently:
# backoff = backoff * SSHD_BACKOFF_FACTOR
SSHD_BACKOFF_FACTOR = 2
# Initial timeout for running start_sshd.bat. The timeout value changes in each
# retry loop as timeout = START_SSHD_TIMEOUT * backoff
START_SSHD_TIMEOUT_INIT_SECS = 10

# http://www.hiteksoftware.com/knowledge/articles/049.htm
WIN_E_ACCESS_DENIED = 5
WIN_E_BAD_FORMAT = 11
WIN_E_DATA_INVALID = 13

# http://www.hiteksoftware.com/knowledge/articles/049.htm
ICACLS_OK_CODES = (WIN_E_ACCESS_DENIED, WIN_E_DATA_INVALID, WIN_E_BAD_FORMAT)
