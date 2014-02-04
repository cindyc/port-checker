import json
import nmap
import argparse
import logging
import deploy_exe

encloud_servers = [
    '4.30.151.146',
    '4.30.151.152',
    '4.30.151.153',
    '4.30.151.154',
    '4.30.151.159',
    '4.30.151.160',
]
smb_rivermeadow = ['smb.rivermeadow.com']

DEFAULT_PORTS = (
            135,
            137,
            139,
            445,
            12541,
            )

DEFAULT_PORT_SCAN_PLAN = {
    135 : {
        'tcp' : {
            'inbound' : encloud_servers,
        },
        'udp' : {
            'inbound' : encloud_servers,
            }
    },
    137 : {
        'tcp' : {
            'inbound' : encloud_servers,
        },
        'udp' : {
            'inbound' : encloud_servers,
            }
    },
    138 : {
        'tcp' : {
            'inbound' : encloud_servers,
        },
        'udp' : {
            'inbound' : encloud_servers,
            }
    },
    139 : {
        'tcp' : {
            'inbound' : encloud_servers,
        },
        'udp' : {
            'inbound' : encloud_servers,
            }
    },
    445: {
        'tcp' : {
            'outbound' : smb_rivermeadow,
            },
        'udp' : {
            'outbound' : smb_rivermeadow,
            }
    },
    12541: {
        'tcp' : {
            'inbound' : encloud_servers,
            }
    },
}

class PortScanner(object):
    """A port scanner to check if a port or list of ports are open
    """

    def __init__(self, host, username, password):
        """
        """
        self.scanner = nmap.PortScanner()
        self.host = host
        self.username = username
        self.password = password
        self.logger = logging.getLogger("PortScanner")
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(logging.StreamHandler())
        self.deployer = deploy_exe.DeployToWindows(self.host,
                                              self.username,
                                              self.password,
                                              samba_host='23.21.216.166',
                                              samba_share='collection_1161',
                                              samba_user='shaman01',
                                              samba_pass='scloud2010',
                                              logger=self.logger,
                                              samba_collection_dir="collection")

    def scan(self, scan_plan=DEFAULT_PORT_SCAN_PLAN):
        """Scan a list of ports
        """
        ports_status = {}
        ports = scan_plan.keys()
        ports_str = ','.join(map(str, ports))
        self.log('Checking ports {}'.format(ports_str))

        result = self.scanner.scan(self.host,
                arguments='-v -sT -sU -Pn -r -p {0}'.format(ports_str))
        self.log('nmap command: {0}'.format(self.scanner.command_line()))

        host_scan_result = result['scan'][self.host]
        protocols = ('tcp', 'udp')
        for port in scan_plan.keys():
            port_scan_plan = scan_plan[port]
            self.log('Got port {0} scan_plan {1}'.format(port, scan_plan))
            port_result = self._do_port_check(port, port_scan_plan,
                                              host_scan_result)
            ports_status[port] = port_result
            self.log('port_result is {}'.format(port_result))

        system_info_keys = ['Host Name', 'OS Name', 'OS Version']
        if host_scan_result['tcp'][445]['state']== 'open' and \
                host_scan_result['tcp'][139]['state']:
            host_info = self._get_host_info_winexe(system_info_keys)
        else:
            host_info = {}
            for key in system_info_keys:
                host_info[key] = 'Unable to determine, please make sure '\
                                 'ports 139 and 445 are not blocked'
        all_result = {'host' : host_info,
                     'ports': ports_status,
                     }
        return json.dumps(all_result, indent=4)

    def _do_port_check(self, port, port_scan_plan, host_scan_result):
        """fill in the port scan result and return it
        """
        port_scan_result = {}
        protocols_to_check = port_scan_plan.keys()
        for protocol in protocols_to_check:
            print 'host_scan_result is {}'.format(host_scan_result)
            port_protocol_state = host_scan_result[protocol][port]['state']
            port_scan_result[protocol] = {'status' : port_protocol_state,
                                          #'inbound': {},
                                          #'outbound' : {}
                                         }
            hosts_to_check = []
            if 'inbound' in port_scan_plan[protocol]:
                hosts_to_check += port_scan_plan[protocol]['inbound']
            if 'outbound' in port_scan_plan[protocol]:
                hosts_to_check += port_scan_plan[protocol]['outbound']
            self.log('hosts_to_check are: {0}'.format(hosts_to_check))
            for host_to_check in hosts_to_check:
                host_permission_result = self._do_port_host_permission_check(
                                                        port, host_to_check,
                                                        port_protocol_state)
                self.log('\nhost_permission_result is {}'.format(host_permission_result))
                for direction in ('inbound', 'outbound'):
                    if direction in port_scan_plan[protocol].keys():
                        if direction not in port_scan_result[protocol].keys():
                            port_scan_result[protocol][direction] = {}
                        port_scan_result[protocol][direction][host_to_check] =\
                            host_permission_result[direction]
        return port_scan_result

    def _do_port_host_permission_check(self, port, host, port_protocol_status):
        # for UDP, we consider open|filtered as 'open'
        if 'closed|filtered' in port_protocol_status or \
                'open|filtered' in port_protocol_status:
            host_permission_result = {'inbound' : 'check firewall',
                                      'outbound' : 'check firewall'
                                      }
        # 'closed' means the probe packet passed through the firewall
        # so it's open in terms of the firewall setting
        elif port_protocol_status in ('open', 'closed'):
            host_permission_result = {'inbound': 'open',
                                      'outbound': 'open'}
        elif 'filtered' in port_protocol_status:
            host_permission_result = {'inbound' : 'blocked',
                                      'outbound' : 'blocked'}
        else:
            host_permission_result = {'inbound' : 'unknown',
                                      'outbound' : 'unknown'
                                      }
        return host_permission_result


    def _get_host_info_winexe(self, system_info_keys):
        host_info = {}
        s_out, s_err = self.deployer.sh_winexe_command('systeminfo')
        if s_out:
            lines = s_out.split('\n')
            for line in lines:
                specs = line.split(':')
                if specs[0] in system_info_keys:
                    host_info[specs[0]] = specs[1].strip()
        return host_info

    def log(self, msg):
        self.logger.debug(msg)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Ceck ports on source machine required by migration')
    parser.add_argument('-m', '--source-machine', required=True,
                            help='source machine hostname/ip')
    parser.add_argument('--ports', default=DEFAULT_PORTS,
                            help='list of ports to scan')
    parser.add_argument('-u', '--username', default='Administrator',
                            help='The username to the source machine')
    parser.add_argument('-p', '--password', default='scloud2010',
                            help='The password to the source machine')
    args = parser.parse_args()
    scanner = PortScanner(args.source_machine, args.username, args.password)
    scan_result_json = scanner.scan()
    print scan_result_json
    with open('port_scan.json', 'w') as json_file:
        json_file.write(scan_result_json)
