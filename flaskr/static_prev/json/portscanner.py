import json
import nmap
import argparse

DEFAULT_PORTS = (
            135,
            137,
            139,
            445,
            12541,
            )

class PortScanner(object):
    """A port scanner to check if a port or list of ports are open
    """

    def __init__(self, host):
        """
        """
        self.scanner = nmap.PortScanner()
        self.host = host

    def scan(self, scan_plan):
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
        return json.dumps(ports_status, indent=4)

    def _do_port_check(self, port, port_scan_plan, host_scan_result):
        """fill in the port scan result and return it
        """
        port_scan_result = {}
        protocols_to_check = port_scan_plan.keys()
        for protocol in protocols_to_check:
            print 'host_scan_result is {}'.format(host_scan_result)
            port_protocol_state = host_scan_result[protocol][port]['state']
            port_scan_result[protocol] = {'status' : port_protocol_state,
                                          'inbound': {},
                                          'outbound' : {}
                                         }
            hosts_to_check = port_scan_plan[protocol]['inbound'] + \
                             port_scan_plan[protocol]['outbound']
            self.log('hosts_to_check are: {0}'.format(hosts_to_check))
            for host_to_check in hosts_to_check:
                host_permission_result = self._do_port_host_permission_check(
                                                        port, host_to_check,
                                                        port_protocol_state)
                self.log('\nhost_permission_result is {}'.format(host_permission_result))
                for direction in ('inbound', 'outbound'):
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
            host_permission_result = {'inbound' : 'firewalled',
                                      'outbound' : 'firewalled'}
        else:
            host_permission_result = {'inbound' : 'unknown',
                                      'outbound' : 'unknown'
                                      }
        return host_permission_result


    def log(self, msg):
        print msg

encloud_servers = [
    '4.30.151.146',
    '4.30.151.152',
    '4.30.151.153',
    '4.30.151.154',
    '4.30.151.159',
    '4.30.151.160',
]
smb_rivermeadow = ['23.21.216.166']

DEFAULT_PORT_SCAN_PLAN = {
    135 : {
        'tcp' : {
            'inbound' : encloud_servers,
            'outbound' : [],
        },
        'udp' : {
            'inbound' : encloud_servers,
            'outbound' : [],
            }
    },
    137 : {
        'tcp' : {
            'inbound' : encloud_servers,
            'outbound' : [],
        },
        'udp' : {
            'inbound' : encloud_servers,
            'outbound' : [],
            }
    },
    138 : {
        'tcp' : {
            'inbound' : encloud_servers,
            'outbound' : [],
        },
        'udp' : {
            'inbound' : encloud_servers,
            'outbound' : [],
            }
    },
    139 : {
        'tcp' : {
            'inbound' : encloud_servers,
            'outbound' : [],
        },
        'udp' : {
            'inbound' : encloud_servers,
            'outbound' : [],
            }
    },
    445: {
        'tcp' : {
            'inbound' : smb_rivermeadow,
            'outbound' : [],
            },
        'udp' : {
            'inbound' : smb_rivermeadow,
            'outbound' : [],
            }
    },
}

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Ceck ports on source machine required by migration')
    parser.add_argument('-m', '--source-machine', required=True,
                            help='source machine hostname/ip')
    parser.add_argument('-p', '--ports', default=DEFAULT_PORTS,
                            help='list of ports to scan')
    args = parser.parse_args()
    scanner = PortScanner(args.source_machine)
    scan_result_json = scanner.scan(DEFAULT_PORT_SCAN_PLAN)
    print scan_result_json
    with open('port_scan.json', 'w') as json_file:
        json_file.write(scan_result_json)
