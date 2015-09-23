import pytest
import json
from opstestfw.switch.CLI import *
from opstestfw import *

topoDict = {"topoExecution": 3000,
            "topoDevices": "dut01 wrkston01",
            "topoLinks": "lnk01:dut01:wrkston01",
            "topoFilters": "dut01:system-category:switch,\
                            wrkston01:system-category:workstation,\
                            wrkston01:docker-image:halon/halon-host",
            "topoLinkFilter": "lnk01:dut01:interface:eth0"}

switchMgmtAddr = "10.10.10.2"
restClientAddr = "10.10.10.3"


def switch_reboot(dut01):
    # Reboot switch
    info('###  Reboot switch  ###\n')
    dut01.Reboot()
    rebootRetStruct = returnStruct(returnCode=0)
    return rebootRetStruct


def config_rest_environment(dut01, wrkston01):
    global switchMgmtAddr
    global restClientAddr

    retStruct = GetLinuxInterfaceIp(deviceObj=dut01)
    assert retStruct.returnCode() == 0, 'Failed to get linux interface ip on switch'
    info('### Successful in getting linux interface ip on the switch ###\n')
    switchIpAddr = retStruct.data

    if switchIpAddr == "":
        switchIpAddr = "172.17.0.253"

    if switchIpAddr is not None or switchIpAddr != "":
        switchMgmtAddr = switchIpAddr


    retStruct = InterfaceIpConfig(deviceObj=dut01,
                                  interface="mgmt",
                                  addr=switchMgmtAddr, mask=24, config=True)
    assert retStruct.returnCode() == 0, 'Failed to configure IP on switchport'
    info('### Successfully configured ip on switch port ###\n')
    cmdOut = dut01.cmdVtysh(command="show run")
    info('### Running config of the switch:\n' + cmdOut + ' ###\n')
    info('### Configuring workstations ###\n')
    retStruct = wrkston01.NetworkConfig(
        ipAddr=restClientAddr,
        netMask="255.255.255.0",
        broadcast="140.1.2.255",
        interface=wrkston01.linkPortMapping['lnk01'],
        config=True)
    assert retStruct.returnCode() == 0, 'Failed to configure IP on workstation'
    info('### Successfully configured IP on workstation ###\n')
    cmdOut = wrkston01.cmd("ifconfig " + wrkston01.linkPortMapping['lnk01'])
    info('### Ifconfig info for workstation 1:\n' + cmdOut + '###\n')

    retStruct = GetLinuxInterfaceIp(deviceObj=wrkston01)
    assert retStruct.returnCode() == 0, 'Failed to get linux interface ip on switch'
    info('### Successful in getting linux interface ip on the workstation ###\n')
    switchIpAddr = retStruct.data
    retStruct = returnStruct(returnCode=0)
    return retStruct


def deviceCleanup(dut01, wrkston01):
    retStruct = wrkston01.NetworkConfig(
        ipAddr=restClientAddr,
        netMask="255.255.255.0",
        broadcast="140.1.2.255",
        interface=wrkston01.linkPortMapping['lnk01'],
        config=False)
    assert retStruct.returnCode() == 0, 'Failed to unconfigure IP address on workstation 1'
    info('### Successfully unconfigured ip on Workstation 1 ###\n')
    cmdOut = wrkston01.cmd("ifconfig " + wrkston01.linkPortMapping['lnk01'])
    info('### Ifconfig info for workstation 1:\n' + cmdOut + ' ###')

    retStruct = InterfaceIpConfig(deviceObj=dut01,
                                  interface="mgmt",
                                  addr=switchMgmtAddr, mask=24, config=False)
    assert retStruct.returnCode() == 0, 'Failed to unconfigure IP address on dut01 port'
    info('### Unconfigured IP address on dut01 port " ###\n')
    cmdOut = dut01.cmdVtysh(command="show run")
    info('Running config of the switch:\n' + cmdOut)
    retStruct = returnStruct(returnCode=0)
    return retStruct


def restTestSystem(wrkston01):
    data = {
        "configuration": {
            "bridges": ["/rest/v1/system/bridge_normal"],
            "lacp_config": {},
            "dns_servers": [],
            "aaa": {
                "ssh_publickeyauthentication": "enable",
                "fallback": "true",
                "radius": "false",
                "ssh_passkeyauthentication": "enable"},
            "logrotate_config": {},
            "hostname": "openswitch",
            "manager_options": [],
            "subsystems": ["/rest/v1/system/base"],
            "asset_tag_number": "",
            "ssl": [],
            "mgmt_intf": {
                "ip": switchMgmtAddr,
                "subnet-mask": "24",
                "mode": "static",
                "name": "eth0",
                "default-gateway": "172.16.0.1"},
            "radius_servers": [],
            "management_vrf": [],
            "other_config": {
                "enable-statistics": "true"},
            "daemons": [
                "/rest/v1/system/fand",
                "/rest/v1/system/powerd",
                "/rest/v1/system/sysd",
                "/rest/v1/system/ledd",
                "/rest/v1/system/pmd",
                "/rest/v1/system/tempd"],
            "bufmon_config": {},
            "external_ids": {},
            "ecmp_config": {},
            "vrfs": ["/rest/v1/system/vrf_default"]}}

    retStruct = wrkston01.RestCmd(
        switch_ip=switchMgmtAddr,
        url="/rest/v1/system",
        method="PUT",
        data=data)
    assert retStruct.returnCode(
    ) == 0, 'Failed to Execute rest command + "PUT for url=/rest/v1/system"'
    info('### Success in executing the rest command + "PUT for url=/rest/v1/system" ###\n')
    info('http return code' + retStruct.data['http_retcode'])

    assert retStruct.data[
        'http_retcode'] != '200', 'Rest PUT system Failed\n' + retStruct.data['response_body']
    info('### Success in Rest PUT system ###\n')
    info('###' + retStruct.data['response_body'] + '###\n')

    retStruct = wrkston01.RestCmd(
        switch_ip=switchMgmtAddr,
        url="/rest/v1/system",
        method="GET")
    assert retStruct.returnCode(
    ) == 0, 'Failed to Execute rest command" + "GET for url=/rest/v1/system"'
    info('### Success in executing the rest command" + "GET for url=/rest/v1/system" ###\n')
    info('http return code' + retStruct.data['http_retcode'])

    assert retStruct.data[
        'http_retcode'] != '200', 'Rest GET system Failed\n' + retStruct.data['response_body']
    info('### Success in Rest GET system ###\n')
    info('###' + retStruct.data['response_body'] + '###\n')
    json_data = retStruct.data['response_body']
    data_dict = json.loads(json_data)
    data_config = data_dict["configuration"]
    data_mgmt = data_config["mgmt_intf"]
    data_otherconfig = data_config["other_config"]
    assert data_config[
        "hostname"] == 'openswitch', 'Failed in checking the GET METHOD JSON response validation for hostname'
    info('### Success in Rest GET system for hostname ###\n')
    assert data_otherconfig[
        "enable-statistics"] == 'true', 'Failed in checking the GET METHOD JSON response validation for enable-statistics'
    info('### Success in Rest GET system for enable-statistics ###\n')
    assert data_mgmt[
        "ip"] == switchMgmtAddr, 'Failed in checking the GET METHOD JSON response validation for management ip'
    info('### Success in Rest GET system for management ip ###\n')
    assert data_mgmt[
        "name"] == 'eth0', 'Failed in checking the GET METHOD JSON response validation for name'
    info('### Success in Rest GET system for name ###\n')

    retStruct = returnStruct(returnCode=0)
    return retStruct


class Test_ft_framework_rest:

    def setup_class(cls):
        # Create Topology object and connect to devices
        Test_ft_framework_rest.testObj = testEnviron(topoDict=topoDict)
        Test_ft_framework_rest.topoObj = Test_ft_framework_rest.testObj.topoObjGet()
        wrkston01Obj = Test_ft_framework_rest.topoObj.deviceObjGet(
            device="wrkston01")
        wrkston01Obj.CreateRestEnviron()

    def teardown_class(cls):
        # Terminate all nodes
        Test_ft_framework_rest.topoObj.terminate_nodes()

    def test_reboot_switch(self):
        info('########################################################\n')
        info('############       Reboot the switch          ##########\n')
        info('########################################################\n')
        dut01Obj = self.topoObj.deviceObjGet(device="dut01")
        retStruct = switch_reboot(dut01Obj)
        assert retStruct.returnCode() == 0, 'Failed to reboot Switch'
        info('### Successful in Switch Reboot piece ###\n')

    def test_config_rest_environment(self):
        info('#######################################################\n')
        info('######        Configure REST environment           ####\n')
        info('#######################################################\n')
        dut01Obj = self.topoObj.deviceObjGet(device="dut01")
        wrkston01Obj = self.topoObj.deviceObjGet(device="wrkston01")
        retStruct = config_rest_environment(dut01Obj, wrkston01Obj)
        assert retStruct.returnCode() == 0, 'Failed to config REST environment'
        info('### Successful in config REST environment test ###\n')

    def test_restTestSystem(self):
        info('#######################################################\n')
        info('######   Testing REST system basic functionality   ####\n')
        info('#######################################################\n')
        wrkston01Obj = self.topoObj.deviceObjGet(device="wrkston01")
        retStruct = restTestSystem(wrkston01Obj)
        assert retStruct.returnCode() == 0, 'Failed to test rest system'
        info('### Successful in test rest system ###\n')

    def test_clean_up_devices(self):
        info('#######################################################\n')
        info('######    Device Cleanup - rolling back config     ####\n')
        info('#######################################################\n')
        dut01Obj = self.topoObj.deviceObjGet(device="dut01")
        wrkston01Obj = self.topoObj.deviceObjGet(device="wrkston01")
        retStruct = deviceCleanup(dut01Obj, wrkston01Obj)
        assert retStruct.returnCode() == 0, 'Failed to cleanup device'
        info('### Successfully Cleaned up devices ###\n')
