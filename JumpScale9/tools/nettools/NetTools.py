# TODO: test *2

import time
import socket
import netaddr
import re

from js9 import j

IPBLOCKS = re.compile("(^|\n)(?P<block>\d+:.*?)(?=(\n\d+)|$)", re.S)
IPMAC = re.compile("^\s+link/\w+\s+(?P<mac>(\w+:){5}\w{2})", re.M)
IPIP = re.compile("^\s+inet\s(?P<ip>(\d+\.){3}\d+)/(?P<cidr>\d+)", re.M)
IPNAME = re.compile("^\d+: (?P<name>.*?)(?=:)", re.M)


def parseBlock(block):
    result = {'ip': [], 'cidr': [], 'mac': '', 'name': ''}
    for rec in (IPMAC, IPNAME):
        match = rec.search(block)
        if match:
            result.update(match.groupdict())
    for mrec in (IPIP, ):
        for m in mrec.finditer(block):
            for key, value in list(m.groupdict().items()):
                result[key].append(value)
    return result


def getNetworkInfo():
    exitcode, output, err = j.sal.process.execute("ip a", showout=False)
    for m in IPBLOCKS.finditer(output):
        block = m.group('block')
        yield parseBlock(block)


class NetTools:

    def __init__(self):
        self.__jslocation__ = "j.sal.nettools"
        self.__imports__ = "netaddr"
        self.logger = j.logger.get('j.sal.nettools')
        self._windowsNetworkInfo = None

    def tcpPortConnectionTest(self, ipaddr, port, timeout=None):
        conn = None
        try:
            conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            if timeout:
                conn.settimeout(timeout)
            try:
                conn.connect((ipaddr, port))
            except BaseException:
                return False
        finally:
            if conn:
                conn.close()
        return True

    def ip_to_num(self, ip="127.0.0.1"):
        """
        Convert an IP string to number
        """
        return int(netaddr.IPAddress(ip))

    def waitConnectionTest(self, ipaddr, port, timeout):
        """
        will return false if not successfull (timeout)
        """
        self.logger.debug("test tcp connection to '%s' on port %s" % (ipaddr, port))
        if ipaddr.strip() == "localhost":
            ipaddr = "127.0.0.1"
        port = int(port)
        start = j.data.time.getTimeEpoch()
        now = start
        remainingtime = (timeout - (now - start)) or 1
        while remainingtime > 0:
            if j.sal.nettools.tcpPortConnectionTest(ipaddr, port, remainingtime):
                return True
            time.sleep(0.1)
            now = j.data.time.getTimeEpoch()
            remainingtime = (timeout - (now - start)) or 1
        return False

    def waitConnectionTestStopped(self, ipaddr, port, timeout):
        """
        will test that port is not active
        will return false if not successfull (timeout)
        """
        self.logger.debug("test tcp connection to '%s' on port %s" % (ipaddr, port))
        if ipaddr.strip() == "localhost":
            ipaddr = "127.0.0.1"
        port = int(port)
        start = j.data.time.getTimeEpoch()
        now = start
        while now < start + timeout:
            if j.sal.nettools.tcpPortConnectionTest(ipaddr, port, 1) is False:
                return True
            now = j.data.time.getTimeEpoch()
        return False

    def checkUrlReachable(self, url, timeout=5):
        """
        raise operational critical if unreachable
        return True if reachable
        """
        # import urllib.request, urllib.parse, urllib.error
        try:
            import urllib.request
            import urllib.parse
            import urllib.error
        except BaseException:
            import urllib.parse as urllib

        try:
            code = urllib.request.urlopen(url, timeout=timeout).getcode()
        except Exception:
            j.errorhandler.raiseOperationalCritical("Url %s is unreachable" % url)

        if code != 200:
            j.errorhandler.raiseOperationalCritical("Url %s is unreachable" % url)
        return True

    def checkListenPort(self, port):
        """
        Check if a certain port is listening on the system.

        @param port: sets the port number to check
        @return status: 0 if running 1 if not running
        """
        if port > 65535 or port < 0:
            raise ValueError("Port cannot be bigger then 65535 or lower then 0")

        self.logger.debug('Checking whether a service is running on port %d' % port)

        if j.core.platformtype.myplatform.isLinux:
            # netstat: n == numeric, -t == tcp, -u = udp, l= only listening, p = program
            command = "netstat -ntulp | grep ':%s '" % port
            # raise j.exceptions.RuntimeError("stop")
            exitcode, output, err = j.sal.process.execute(command, die=False, showout=False)
            return exitcode == 0
        elif j.core.platformtype.myplatform.isOSX():
            command = "netstat -an -f inet"
            exitcode, output, err = j.sal.process.execute(command, die=False, showout=False)
            for line in output.splitlines():
                match = re.match(".*\.%s .*\..*LISTEN" % port, line)
                if match:
                    return True
            # No ipv4? Then check ipv6
            command = "netstat -an -f inet6"
            exitcode, output, err = j.sal.process.execute(command, die=False, showout=False)
            for line in output.splitlines():
                match = re.match(".*\.%s .*\..*LISTEN" % port, line)
                if match:
                    return True
            return False
        elif j.core.platformtype.myplatform.isWindows:
            # We use the GetTcpTable function of the Windows IP Helper API (iphlpapi.dll)
            #
            # Parameters of GetTcpTable:
            #    - A buffer receiving the table.
            #    - An integer indicating the length of the buffer. This value will be overwritten with the required buffer size, if the buffer isn't large enough.
            #    - A boolean indicating if the table should be sorted.
            #
            # Microsoft reference: http://msdn2.microsoft.com/en-us/library/aa366026(VS.85).aspx
            # Python example code: http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/392572

            import ctypes
            import socket
            DWORD = ctypes.c_ulong
            MIB_TCP_STATE_LISTEN = 2
            dwSize = DWORD(0)

            # Retrieve the size of the TCP table, to create a structure with the right size.
            # We do this by calling the GetTcpTable function and passing an empty buffer.
            # Because the buffer is too small, the dwSize variable will be overwritten with the required buffer size.
            ctypes.windll.iphlpapi.GetTcpTable("", ctypes.byref(dwSize), 0)

            # Define MIB (Management Information Base) classes
            class MIB_TCPROW(ctypes.Structure):
                _fields_ = [('dwState', DWORD),
                            ('dwLocalAddr', DWORD),
                            ('dwLocalPort', DWORD),
                            ('dwRemoteAddr', DWORD),
                            ('dwRemotePort', DWORD)]

            class MIB_TCPTABLE(ctypes.Structure):
                _fields_ = [('dwNumEntries', DWORD),
                            ('table', MIB_TCPROW * dwSize.value)]

            tcpTable = MIB_TCPTABLE()  # Initialize the buffer that will retrieve the TCP table
            tcpTable.dwNumEntries = 0

            # Call the GetTcpTable function again, but now with a buffer that's large
            # enough. The TCP table will be written in the buffer.
            retVal = ctypes.windll.iphlpapi.GetTcpTable(ctypes.byref(tcpTable), ctypes.byref(dwSize), 0)
            if not retVal == 0:
                raise j.exceptions.RuntimeError(
                    "j.sal.nettools.checkListenPort: The function iphlpapi.GetTcpTable returned error number %s" %
                    retVal)

            # We can't iterate over the table the usual way as tcpTable.table isn't a Python table structure.
            for i in range(tcpTable.dwNumEntries):
                tcpState = tcpTable.table[i].dwState
                # socket.ntohs() convert a 16-bit integer from network to host byte order.
                tcpLocalPort = socket.ntohs(tcpTable.table[i].dwLocalPort)
                if tcpState == MIB_TCP_STATE_LISTEN and tcpLocalPort == port:
                    return True
            return False  # The port is not in a listening state.

        else:
            raise j.exceptions.RuntimeError("This platform is not supported in j.sal.nettools.checkListenPort()")

    def getNameServer(self):
        """Returns the first nameserver IP found in /etc/resolv.conf

        Only implemented for Unix based hosts.

        @returns: Nameserver IP
        @rtype: string

        @raise NotImplementedError: Non-Unix systems
        @raise RuntimeError: No nameserver could be found in /etc/resolv.conf
        """
        if j.core.platformtype.myplatform.isUnix:
            nameserverlines = j.tools.code.regex.findAll(
                "^\s*nameserver\s+(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\s*$",
                j.do.fileGetContents('/etc/resolv.conf'))

            if not nameserverlines:
                raise j.exceptions.RuntimeError('No nameserver found in /etc/resolv.conf')

            nameserverline = nameserverlines[0]
            return nameserverline.strip().split(' ')[-1]
        elif j.core.platformtype.myplatform.isWindows:
            import wmi
            w = wmi.WMI()
            for nicCfg in w.Win32_NetworkAdapterConfiguration():
                if nicCfg.DNSServerSearchOrder:
                    return str(nicCfg.DNSServerSearchOrder[0])
        else:
            raise NotImplementedError('This function is only supported on Unix/Windows systems')

    def getIpAddresses(self, up=False):
        if j.core.platformtype.myplatform.isLinux:
            result = list()
            for ipinfo in getNetworkInfo():
                result.extend(ipinfo['ip'])
            return result
        else:
            nics = self.getNics(up)
            result = []
            for nic in nics:
                ipTuple = self.getIpAddress(nic)
                if ipTuple:  # if empty array skip
                    result.extend([ip[0] for ip in ipTuple])
            return result

    def checkIpAddressIsLocal(self, ipaddr):
        if ipaddr.strip() in self.getIpAddresses():
            return True
        else:
            return False

    def getNics(self, up=False):
        """ Get Nics on this machine
        Works only for Linux/Solaris systems
        @param up: only returning nics which or up
        """
        regex = ''
        output = ''
        if j.core.platformtype.myplatform.isLinux or j.core.platformtype.myplatform.isESX():
            return [nic['name'] for nic in getNetworkInfo()]
        elif j.core.platformtype.myplatform.isSolaris():
            exitcode, output, err = j.sal.process.execute("ifconfig -a", showout=False)
            if up:
                regex = "^([\w:]+):\sflag.*<.*UP.*>.*$"
            else:
                regex = "^([\w:]+):\sflag.*$"
            nics = set(re.findall(regex, output, re.MULTILINE))
            exitcode, output, err = j.sal.process.execute("dladm show-phys", showout=False)
            lines = output.splitlines()
            for line in lines[1:]:
                nic = line.split()
                if up:
                    if nic[2] == 'up':
                        nics.add(nic[0])
                else:
                    nics.add(nic[0])
            return list(nics)
        elif j.core.platformtype.myplatform.isWindows:
            import wmi
            w = wmi.WMI()
            return ["%s:%s" % (ad.index, str(ad.NetConnectionID))
                    for ad in w.Win32_NetworkAdapter() if ad.PhysicalAdapter and ad.NetEnabled]
        else:
            raise j.exceptions.RuntimeError("Not supported on this platform!")

    def getNicType(self, interface):
        """ Get Nic Type on a certain interface
        @param interface: Interface to determine Nic type on
        @raise RuntimeError: On linux if ethtool is not present on the system
        """
        if j.core.platformtype.myplatform.isLinux or j.core.platformtype.myplatform.isESX():
            output = ''
            if j.do.exists("/sys/class/net/%s" % interface):
                output = j.do.fileGetContents("/sys/class/net/%s/type" % interface)
            if output.strip() == "32":
                return "INFINIBAND"
            else:
                if j.do.exists('/proc/net/vlan/%s' % (interface)):
                    return 'VLAN'
                exitcode, output, err = j.sal.process.execute("which ethtool", False, showout=False)
                if exitcode != 0:
                    raise j.exceptions.RuntimeError("Ethtool is not installed on this system!")
                exitcode, output, err = j.sal.process.execute("ethtool -i %s" % (interface), False, showout=False)
                if exitcode != 0:
                    return 'VIRTUAL'
                match = re.search("^driver:\s+(?P<driver>\w+)\s*$", output, re.MULTILINE)
                if match and match.group("driver") == "tun":
                    return "VIRTUAL"
                if match and match.group("driver") == "bridge":
                    return "VLAN"
                return "ETHERNET_GB"
        elif j.core.platformtype.myplatform.isSolaris():
            command = "ifconfig %s" % interface
            exitcode, output, err = j.sal.process.execute(command, showout=False, die=False)
            if exitcode != 0:
                # temporary plumb the interface to lookup its mac
                self.logger.warning(
                    "Interface %s is down. Temporarily plumbing it to be able to lookup its nic type" % interface)
                j.sal.process.execute('%s plumb' % command, showout=False)
                exitcode, output, err = j.sal.process.execute(command, showout=False)
                j.sal.process.execute('%s unplumb' % command, showout=False)
            if output.find("ipib") >= 0:
                return "INFINIBAND"
            else:
                # work with interfaces which are subnetted on vlans eq e1000g5000:1
                interfacepieces = interface.split(':')
                interface = interfacepieces[0]
                match = re.search("^\w+?(?P<interfaceid>\d+)$", interface, re.MULTILINE)
                if not match:
                    raise ValueError("Invalid interface %s" % (interface))
                if len(match.group('interfaceid')) >= 4:
                    return "VLAN"
                else:
                    if len(interfacepieces) > 1:
                        return "VIRTUAL"
                    else:
                        return "ETHERNET_GB"
        elif j.core.platformtype.myplatform.isWindows:
            if j.sal.nettools.getVlanTagFromInterface(interface) > 0:
                return "VLAN"
            else:
                import wmi
                w = wmi.WMI()
                NICIndex = interface.split(":")[0]
                nic = w.Win32_NetworkAdapter(index=NICIndex)[0]
                if hasattr(nic, 'AdapterTypeId'):
                    if nic.AdapterTypeId == 0:
                        return "ETHERNET_GB"
                    elif nic.AdapterTypeId == 15:
                        return "VIRTUAL"
                    else:
                        return "UNKNOWN"
                else:
                    return "UNKNOWN"
        else:
            raise j.exceptions.RuntimeError("Not supported on this platform!")

    def getVlanTag(self, interface, nicType=None):
        """Get VLan tag on the specified interface and vlan type"""
        if nicType is None:
            nicType = j.sal.nettools.getNicType(interface)
        if nicType == "INFINIBAND" or nicType == "ETHERNET_GB" or nicType == "VIRTUAL":
            return "0"
        if j.core.platformtype.myplatform.isLinux:
            # check if its a vlan
            vlanfile = '/proc/net/vlan/%s' % (interface)
            if j.do.exists(vlanfile):
                return j.sal.nettools.getVlanTagFromInterface(interface)
            bridgefile = '/sys/class/net/%s/brif/' % (interface)
            for brif in j.do.listDirsInDir(bridgefile):
                brif = j.do.getBaseName(brif)
                vlanfile = '/proc/net/vlan/%s' % (brif)
                if j.do.exists(vlanfile):
                    return j.sal.nettools.getVlanTagFromInterface(brif)
            return "0"
        elif j.core.platformtype.myplatform.isSolaris() or j.core.platformtype.myplatform.isWindows:
            return j.sal.nettools.getVlanTagFromInterface(interface)
        else:
            raise j.exceptions.RuntimeError("Not supported on this platform!")

    def getVlanTagFromInterface(self, interface):
        """Get vlan tag from interface
        @param interface: string interface to get vlan tag on
        @rtype: integer representing the vlan tag
        """
        if j.core.platformtype.myplatform.isLinux:
            vlanfile = '/proc/net/vlan/%s' % (interface)
            if j.do.exists(vlanfile):
                content = j.do.fileGetContents(vlanfile)
                match = re.search("^%s\s+VID:\s+(?P<vlantag>\d+)\s+.*$" % (interface), content, re.MULTILINE)
                if match:
                    return match.group('vlantag')
                else:
                    raise ValueError("Could not find vlantag for interface %s" % (interface))
            else:
                raise ValueError("This is not a vlaninterface %s" % (interface))
        elif j.core.platformtype.myplatform.isSolaris():
            # work with interfaces which are subnetted on vlans eq e1000g5000:1
            interface = interface.split(':')[0]
            match = re.search("^\w+?(?P<interfaceid>\d+)$", interface, re.MULTILINE)
            if not match:
                raise ValueError("This is not a vlaninterface %s" % (interface))
            return int(match.group('interfaceid')) / 1000
        elif j.core.platformtype.myplatform.isWindows:
            import wmi
            vir = wmi.WMI(namespace='virtualization')
            mac = j.sal.nettools.getMacAddress(interface)
            mac = mac.replace(":", "")
            dynFor = vir.Msvm_DynamicForwardingEntry(elementname=mac)
            return dynFor[0].VlanId if dynFor else 0

    def getReachableIpAddress(self, ip, port):
        """Returns the first local ip address that can connect to the specified ip on the specified port"""
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect((ip, port))
        except BaseException:
            raise j.exceptions.RuntimeError("Cannot connect to %s:%s, check network configuration" % (ip, port))
        return s.getsockname()[0]

    def getDefaultIPConfig(self):
        ipaddr = self.getReachableIpAddress("8.8.8.8", 22)
        for item in j.sal.nettools.getNetworkInfo():
            for ipaddr2 in item["ip"]:
                # print "%s %s"%(ipaddr2,ipaddr)
                if str(ipaddr) == str(ipaddr2):
                    return item["name"], ipaddr

    def bridgeExists(self, bridgename):
        cmd = "brctl show"
        rc, out, err = j.sal.process.execute(cmd, showout=False)
        for line in out.split("\n"):
            if line.lower().startswith(bridgename):
                return True
        return False

    def resetDefaultGateway(self, gw):
        def gwexists():
            cmd = "ip r"
            rc, out, err = j.sal.process.execute(cmd, showout=False)
            for line in out.split("\n"):
                if line.lower().startswith("default"):
                    return True
            return False

        def removegw():
            cmd = "ip route del 0/0"
            rc, out, err = j.sal.process.execute(cmd, showout=False, ignoreErrorOutput=False, die=False)

        removegw()
        couter = 0
        while gwexists():
            removegw()
            time.sleep(1)
            print("try to delete def gw")
            counter += 1
            if counter > 10:
                raise j.exceptions.RuntimeError("cannot delete def gw")

        cmd = 'route add default gw %s' % gw
        j.sal.process.execute(cmd)

    def getNetworkInfo(self):
        """
        returns {macaddr_name:[ipaddr,ipaddr],...}

        REMARK: format changed because there was bug which could not work with bridges

        TODO: change for windows

        """
        netaddr = {}
        if j.core.platformtype.myplatform.isLinux:
            return [item for item in getNetworkInfo()]
            # ERROR: THIS DOES NOT WORK FOR BRIDGED INTERFACES !!! because macaddr is same as host interface
            # for ipinfo in getNetworkInfo():
            #     print ipinfo
            #     ip = ','.join(ipinfo['ip'])
            #     netaddr[ipinfo['mac']] = [ ipinfo['name'], ip ]
        else:
            nics = self.getNics()
            for nic in nics:
                mac = self.getMacAddress(nic)
                ips = [item[0] for item in self.getIpAddress(nic)]
                if nic.lower() != "lo":
                    netaddr[mac] = [nic.lower(), ",".join(ips)]
        return netaddr

    def getIpAddress(self, interface):
        """Return a list of ip addresses and netmasks assigned to this interface"""
        if j.core.platformtype.myplatform.isLinux or j.core.platformtype.myplatform.isESX():
            command = "ip a s %s" % interface
            exitcode, output, err = j.sal.process.execute(command, showout=False, die=False)
            if exitcode != 0:
                return []
            nicinfo = re.findall(
                "^\s+inet\s+(.*)\/(\d+)\s(?:brd\s)?(\d+\.\d+\.\d+\.\d+)?\s?scope.*$", output, re.MULTILINE)
            result = []
            for ipinfo in nicinfo:
                ip = ipinfo[0]
                masknumber = int(ipinfo[1])
                broadcast = ipinfo[2]
                mask = ""
                for i in range(4):
                    mask += str(int(hex(pow(2, 32) - pow(2, 32 - masknumber))[2:][i * 2:i * 2 + 2], 16)) + "."
                result.append([ip, mask[:-1], broadcast])
            return result
        elif j.core.platformtype.myplatform.isSolaris():
            command = "ifconfig %s" % (interface)
            exitcode, output, err = j.sal.process.execute(command, showout=False, die=False)
            if exitcode != 0:
                return []
            result = []
            match = re.search(
                "^\s+inet\s+(?P<ipaddress>[\d\.]+)\s+.*netmask\s+(?P<netmask>[a-f\d]{8})\s?(broadcast)?\s?(?P<broadcast>[\d\.]+)?$",
                output,
                re.MULTILINE)
            if not match:
                return []
            ip = match.group('ipaddress')
            netmaskhex = match.group('netmask')
            broadcast = match.group('broadcast')
            mask = ""
            for i in range(4):
                mask += str(int(netmaskhex[i * 2:i * 2 + 2], 16)) + "."
            return [[ip, mask[:-1], broadcast]]
        elif j.core.platformtype.myplatform.isWindows:
            import wmi
            ipv4Pattern = '^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$'

            w = wmi.WMI()
            NICIndex = interface.split(":")[0]
            nic = w.Win32_NetworkAdapterConfiguration(index=NICIndex)[0]
            result = []
            if nic.IPAddress:
                for x in range(0, len(nic.IPAddress)):
                    # skip IPv6 addresses for now
                    if re.match(ipv4Pattern, str(nic.IPAddress[x])) is not None:
                        result.append([str(nic.IPAddress[x]), str(nic.IPSubnet[x]), ''])
            return result
        else:
            raise j.exceptions.RuntimeError("j.sal.nettools.getIpAddress not supported on this platform")

    def getMacAddress(self, interface):
        """Return the MAC address of this interface"""
        if interface not in self.getNics():
            raise LookupError("Interface %s not found on the system" % interface)
        if j.core.platformtype.myplatform.isLinux or j.core.platformtype.myplatform.isESX():
            if j.do.exists("/sys/class/net"):
                return j.do.fileGetContents('/sys/class/net/%s/address' % interface.split('@')[0]).strip()
            else:
                command = "ifconfig %s | grep HWaddr| awk '{print $5}'" % interface
                exitcode, output, err = j.sal.process.execute(command, showout=False)
                return self.pm_formatMacAddress(output)
        elif j.core.platformtype.myplatform.isSolaris():
            # check if interface is a logical inteface ex: bge0:1
            tokens = interface.split(':')
            if len(tokens) > 1:
                interface = tokens[0]
            command = "ifconfig %s" % interface
            exitcode, output, err = j.sal.process.execute(command, showout=False, die=False)
            if exitcode != 0:
                # temporary plumb the interface to lookup its mac
                self.logger.warning(
                    "Interface %s is down. Temporarily plumbing it to be able to lookup its MAC address" % interface)
                j.sal.process.execute('%s plumb' % command, showout=False)
                exitcode, output, err = j.sal.process.execute(command, showout=False, die=False)
                j.sal.process.execute('%s unplumb' % command, showout=False)
            if exitcode == 0:
                match = re.search(r"^\s*(ipib|ether)\s*(?P<mac>\S*)", output, re.MULTILINE)
                if match:
                    return self.pm_formatMacAddress(match.group("mac"))
            return None
        elif j.core.platformtype.myplatform.isWindows:
            import wmi
            w = wmi.WMI()
            NICIndex = interface.split(":")[0]
            return str(w.Win32_NetworkAdapterConfiguration(index=NICIndex)[0].MACAddress)
        else:
            raise j.exceptions.RuntimeError("j.sal.nettools.getMacAddress not supported on this platform")

    def pm_formatMacAddress(self, macaddress):
        macpieces = macaddress.strip().split(':')
        mac = ""
        for piece in macpieces:
            if len(piece) == 1:
                mac += "0"
            mac += piece + ":"
        mac = mac[:-1]
        return mac

    def isIpLocal(self, ipaddress):
        if ipaddress == "127.0.0.1" or ipaddress == "localhost":
            return True
        return ipaddress in self.getIpAddresses()

    def isIpInDifferentNetwork(self, ipaddress):
        for netinfo in self.getNetworkInfo():
            for ip, cidr in zip(netinfo['ip'], netinfo['cidr']):
                if ipaddress in netaddr.IPNetwork('{}/{}'.format(ip, cidr)):
                    return True
        return False

    def getMacAddressForIp(self, ipaddress):
        """Search the MAC address of the given IP address in the ARP table

        @param ipaddress: IP address of the machine
        @rtype: string
        @return: The MAC address corresponding with the given IP
        @raise: RuntimeError if no MAC found for IP or if platform is not suppported
        """
        def doArp(ipaddress):
            args = list()
            if j.core.platformtype.myplatform.isLinux:
                # We do not want hostnames to show up in the ARP output
                args.append("-n")

            return j.sal.process.execute(
                'arp %s %s' % (" ".join(args), ipaddress),
                die=False,
                showout=False
            )

        def noEntry(output):
            return ("no entry" in output) or ("(incomplete)" in output)

        if j.core.platformtype.myplatform.isUnix:
            if self.isIpInDifferentNetwork(ipaddress):
                warning = 'The IP address %s is from a different subnet. This means that the macaddress will be the one of the gateway/router instead of the correct one.'
                j.errorhandler.raiseWarning(warning % ipaddress)

            exitcode, output, err = doArp(ipaddress)
            # Output of arp is 1 when no entry found is 1 on solaris but 0
            # on Linux, so we check the actual output
            if noEntry(output):
                # ping first and try again
                self.pingMachine(ipaddress, pingtimeout=1)
                exitcode, output, err = doArp(ipaddress)

            mo = re.search(
                "(?P<ip>[0-9]+(.[0-9]+){3})\s+(?P<type>[a-z]+)\s+(?P<mac>([a-fA-F0-9]{2}[:|\-]?){6})", output)
            if mo:
                return self.pm_formatMacAddress(mo.groupdict()['mac'])
            else:
                # On Linux the arp will not show local configured ip's in the table.
                # That's why we try to find the ip with "ip a" and match for the mac there.

                output, stdout, stderr = j.sal.process.run('ip a', stopOnError=False)
                if exitcode:
                    raise j.exceptions.RuntimeError(
                        'Could not get the MAC address for [%s] because "ip" is not found' % s)
                mo = re.search(
                    '\d:\s+\w+:\s+.*\n\s+.+\s+(?P<mac>([a-fA-F0-9]{2}[:|\-]?){6}).+\n\s+inet\s%s[^0-9]+' %
                    ipaddress, stdout, re.MULTILINE)
                if mo:
                    return self.pm_formatMacAddress(mo.groupdict()['mac'])
            raise j.exceptions.RuntimeError("MAC address for [%s] not found" % ipaddress)
        else:
            raise j.exceptions.RuntimeError("j.sal.nettools.getMacAddressForIp not supported on this platform")

    def getHostname(self):
        """Get hostname of the machine
        """
        return socket.gethostname()

    def isNicConnected(self, interface):
        if j.core.platformtype.myplatform.isLinux:
            carrierfile = '/sys/class/net/%s/carrier' % (interface)
            if not j.do.exists(carrierfile):
                return False
            try:
                return int(j.do.fileGetContents(carrierfile)) != 0
            except IOError:
                return False
        elif j.core.platformtype.myplatform.isESX():
            nl = j.sal.nettools.getNics(up=True)
            if interface not in nl:
                return False
            else:
                return True
        elif j.core.platformtype.myplatform.isSolaris():
            if j.core.platformtype.getVersion() < 100:
                command = "dladm show-dev -p -o STATE %s" % interface
                expectResults = ['STATE="up"', 'STATE="unknown"']
            else:
                command = "dladm show-phys -p -o STATE %s" % interface
                expectResults = ['up', 'unknown']

            exitcode, output, err = j.sal.process.execute(command, die=False, showout=False)
            if exitcode != 0:
                return False
            output = output.strip()
            if output in expectResults:
                return True
            else:
                return False

    def getHostByName(self, dnsHostname):
        import socket
        return socket.gethostbyname(dnsHostname)

    def getDefaultRouter(self):
        """Get default router
        @rtype: string representing the router interface
        """
        if j.core.platformtype.myplatform.isLinux or j.core.platformtype.myplatform.isESX():
            command = "ip r | grep 'default' | awk {'print $3'}"
            exitcode, output, err = j.sal.process.execute(command, showout=False)
            return output.strip()
        elif j.core.platformtype.myplatform.isSolaris():
            command = "netstat -rn | grep default | awk '{print $2}'"
            exitcode, output, err = j.sal.process.execute(command, showout=False)
            return output.strip()
        else:
            raise j.exceptions.RuntimeError("j.sal.nettools.getDefaultRouter not supported on this platform")

    def validateIpAddress(self, ipaddress):
        """Validate wether this ip address is a valid ip address of 4 octets ranging from 0 to 255 or not
        @param ipaddress: ip address to check on
        @rtype: boolean...True if this ip is valid, False if not
        """
        if len(ipaddress.split()) == 1:
            ipList = ipaddress.split('.')
            if len(ipList) == 4:
                for i, item in enumerate(ipList):
                    try:
                        ipList[i] = int(item)
                    except BaseException:
                        return False
                    if not isinstance(ipList[i], int):
                        self.logger.warning('[%s] is not a valid ip address, octects should be integers' % ipaddress)
                        return False
                if max(ipList) < 256:
                    self.logger.warning('[%s] is a valid ip address' % ipaddress)
                    return True
                else:
                    self.logger.warning('[%s] is not a valid ip address, octetcs should be less than 256' % ipaddress)
                    return False
            else:
                self.logger.warning('[%s] is not a valid ip address, ip should contain 4 octets' % ipaddress)
                return False
        else:
            self.logger.warning('[%s] is not a valid ip address' % ipaddress)
            return False

    def pingMachine(self, ip, pingtimeout=60, recheck=False, allowhostname=True):
        """Ping a machine to check if it's up/running and accessible
        @param ip: Machine Ip Address
        @param pingtimeout: time in sec after which ip will be declared as unreachable
        @param recheck: Unused, kept for backwards compatibility
        @param allowhostname: allow pinging on hostname (default is false)
        @rtype: True if machine is pingable, False otherwise
        """
        if not allowhostname:
            if not j.sal.nettools.validateIpAddress(ip):
                raise ValueError('ERROR: invalid ip address passed:[%s]' % ip)

        self.logger.debug('pingMachine %s, timeout=%d, recheck=%s' % (ip, pingtimeout, str(recheck)))

        start = time.time()
        pingsucceeded = False
        while time.time() - start < pingtimeout:
            # if j.core.platformtype.myplatform.isSolaris():
            #     #ping -c 1 IP 1
            #     #Last 1 is timeout in seconds
            #     exitcode, output, err = j.sal.process.execute(
            #                         'ping -c 1 %s 1' % ip, False, False)
            if j.core.platformtype.myplatform.isLinux:
                # ping -c 1 -W 1 IP
                exitcode, output, err = j.sal.process.execute(
                    'ping -c 1 -W 1 -w 1 %s' % ip, False, False)
            elif j.core.platformtype.myplatform.isUnix:
                exitcode, output, err = j.sal.process.execute('ping -c 1 %s' % ip, False, False)
            elif j.core.platformtype.myplatform.isWindows:
                exitcode, output, err = j.sal.process.execute('ping -w %d %s' % (pingtimeout, ip), False, False)
            else:
                raise j.exceptions.RuntimeError('Platform is not supported')
            if exitcode == 0:
                pingsucceeded = True
                self.logger.debug('Machine with ip:[%s] is pingable' % ip)
                return True
            time.sleep(1)
        if not pingsucceeded:
            self.logger.debug("Could not ping machine with ip:[%s]" % ip)
            return False

    def downloadIfNonExistent(self, url, destination_file_path, md5_checksum=None,
                              http_auth_username=None, http_auth_password=None):
        """
        Downloads the file from the specified url to the specified destination if it is not already there
        or if the target file checksum doesn't match the expected checksum.
        """

        if j.do.exists(destination_file_path):

            if md5_checksum:

                if j.data.hash.md5(destination_file_path) == md5_checksum:
                    # File exists locally and its checksum checks out!
                    return

                # On invalid checksum, delete the local file
                j.do.remove(destination_file_path)

            else:
                # It exists but no checksum is provided so any existence of the local file suffices.
                return

        # If reached here then downloading is inevitable
        self.download(url, localpath=destination_file_path, username=http_auth_username, passwd=http_auth_password)

        # Now check if the downloaded file matches the provided checksum
        if md5_checksum and not j.data.hash.md5(destination_file_path) == md5_checksum:
            raise j.exceptions.RuntimeError(
                'The provided MD5 checksum did not match that of a freshly-downloaded file!')

    def download(self, url, localpath, username=None, passwd=None, overwrite=True):
        '''Download a url to a file or a directory, supported protocols: http, https, ftp, file
        @param url: URL to download from
        @type url: string
        @param localpath: filename or directory to download the url to pass - to return data
        @type localpath: string
        @param username: username for the url if it requires authentication
        @type username: string
        @param passwd: password for the url if it requires authentication
        @type passwd: string
        '''
        if not url:
            raise ValueError('URL can not be None or empty string')
        if not localpath:
            raise ValueError('Local path to download the url to can not be None or empty string')
        filename = ''
        if localpath == '-':
            filename = '-'
        if j.do.isDir(localpath):
            filename = j.do.joinPaths(localpath, j.do.getBaseName(url))
        else:
            if j.do.isDir(j.do.getDirName(localpath)):
                filename = localpath
            else:
                raise ValueError('Local path is an invalid path')
        self.logger.debug('Downloading url %s to local path %s' % (url, filename))
        from urllib.request import FancyURLopener
        from urllib.parse import splittype

        class myURLOpener(FancyURLopener):
            # read a URL, with automatic HTTP authentication

            def __init__(self, user, passwd):
                self._user = user
                self._passwd = passwd
                self._promptcalled = False
                FancyURLopener.__init__(self)

            def prompt_user_passwd(self, host, realm):
                if not self._user or not self._passwd:
                    raise j.exceptions.RuntimeError('Server requested authentication but nothing was given')
                if not self._promptcalled:
                    self._promptcalled = True
                    return self._user, self._passwd
                raise j.exceptions.RuntimeError(
                    'Could not authenticate with the given authentication user:%s and password:%s' %
                    (self._user, self._passwd))

        urlopener = myURLOpener(username, passwd)

        if not j.do.exists(filename):
            overwrite = True

        if overwrite:
            if username and passwd and splittype(url)[0] == 'ftp':
                url = url.split('://')[0] + '://%s:%s@' % (username, passwd) + url.split('://')[1]
            if filename != '-':
                urlopener.retrieve(url, filename, None, None)
                self.logger.debug('URL %s is downloaded to local path %s' % (url, filename))
                return
            else:
                return urlopener.open(url).read()
        return print("!!! File already exists did not overwrite")

    def getDomainName(self):
        """
        Retrieve the dns domain name
        """
        cmd = "dnsdomainname" if j.core.platformtype.myplatform.isLinux(
        ) else "domainname" if j.core.platformtype.myplatform.isSolaris() else ""
        if not cmd:
            raise PlatformNotSupportedError(
                'Platform "%s" is not supported. Command is only supported on Linux and Solaris' %
                j.core.platformtype.name)

        exitCode, domainName, err = j.sal.process.execute(cmd, showout=False)

        if not domainName:
            raise ValueError('Failed to retrieve domain name')

        domainName = domainName.splitlines()[0]

        return domainName


class NetworkZone:
    ipRanges = None  # array(IPRange)
