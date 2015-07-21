###PROC+#####################################################################
# Name:        switch.OVS.OvsBridgeConfig
#
# Namespace:   switch.OVS
#
# Author:      Vince Mendoza
#
# Purpose:     Logic to create a simple bridge
#
# Params:      connection - device connection
#              action     - config or unconfig
#              bridge     - logical bridge device name to configure
#              ports      - a list of ports to add to the bridge
#              vlanMode   - choices are access, trunk, native-tagged, native-untagged
#              nativeVlan - for access & native-tagged,  native-untagged, this is the vlan
#                           to set the tag
#              trunkVlans - list of vlans for trunked mode
#
# Returns:     JSON structure
#              returnCode - status of command
#              data: Temp_Sensors: 
#                     "name": {"max"."temperature". "min"} 
#                    Bridge
#                     "name": {Vlans, Ports}
#                        Vlans
#                          "name": {admin, id}
#                        Ports
#                           "name": {Interface, trunk, tag}
#                    Open_vSwitch_UUID
#                    other_config: {diag_version, number_of_macs, vendor, base_mac_address, interface_count, 
#                                   onie_version, part_number, max_bond_member_count,"Product Name", 
#                                   platform_name, max_bond_count, max_interface_speed, device_version, 
#                                   country_code, label_revision, serial_number, manufacture_date, 
#                                   manufacturer}
#                    Fans
#                      "name": {status, rpm, speed}
#
##PROC-#####################################################################
import common
import switch
import re

def OvsBridgeConfig(**kwargs):
    connection = kwargs.get('connection')
    action = kwargs.get('action', 'config')
    bridge = kwargs.get('bridge', 'br0')
    ports = kwargs.get('ports', None)
    vlanMode = kwargs.get('vlanMode', 'access')
    nativeVlan = kwargs.get('nativeVlan', '1')
    trunkVlans = kwargs.get('trunkVlans', None)
    
    if connection is None:
       return False
    
    retStruct = dict()
    
    if action == 'config':
       # Commands to configure bridge
       
       # check to see if the bridge device is defined...
        command = "ovs-vsctl br-exists " + bridge
        devIntRetStruct = switch.DeviceInteract(connection=connection, command=command)
        retCode = devIntRetStruct['returnCode']
        if retCode != 0:
           # This means we need to add the bridge
           command = "ovs-vsctl add-br " + bridge
           devIntRetStruct = switch.DeviceInteract(connection=connection, command=command)
           retCode1 = devIntRetStruct.get('returnCode')
           if retCode1 != 0:
              common.LogOutput('error', "Failed to create bridge " + bridge)
              retString = common.ReturnJSONCreate(returnCode=1, data="")
              return retString
        else:
           common.LogOutput('debug', "Bridge " + bridge + " exists")
        
        # Now add ports to the  bridge
        if ports != None:
           for curPort in ports:
              command = "ovs-vsctl add-port " + bridge + " " + str(curPort) + " -- set Interface " + str(curPort) + " user_config:admin=up"
              devIntRetStruct = switch.DeviceInteract(connection=connection, command=command)
              retCode = devIntRetStruct['returnCode']
              if retCode != 0:
                 # Failed to add the port to the bridge
                 common.LogOutput('error', "Failed to add port " + str(curPort) + " to bridge " + bridge)
                 retString = common.ReturnJSONCreate(returnCode=1, data="")
                 return retString
              else:
                 common.LogOutput('debug', "Added port " + str(curPort) + " to bridge " + bridge)
              # Add vlan to port
              if vlanMode == 'access':
                 # configure access mode
                 command = "ovs-vsctl set port " + str(curPort) + " tag=" + str(nativeVlan)
                 devIntRetStruct = switch.DeviceInteract(connection=connection, command=command)
                 retCode = devIntRetStruct['returnCode']
                 if retCode != 0:
                    common.LogOutput('error', "Failed to set vlan tag " + str(nativeVlan) + " on port " + str(curPort))
                    retString = common.ReturnJSONCreate(returnCode=1, data="")
                    return retString
                 else:
                    common.LogOutput('debug', "Set port " + str(curPort) + " tag attribute to " + str(nativeVlan))
                 
                 command = "ovs-vsctl set port " + str(curPort) + " vlan_mode=access"
                 devIntRetStruct = switch.DeviceInteract(connection=connection, command=command)
                 retCode = devIntRetStruct['returnCode']
                 if retCode != 0:
                    common.LogOutput('error', "Failed to set port " + str(curPort) + " vlan_mode to access")
                    retString = common.ReturnJSONCreate(returnCode=1, data="")
                    return retString
                 else:
                    common.LogOutput('debug', "Set port " + str(curPort) + " vlan_mode to access")
              elif vlanMode == 'trunk':
                 if trunkVlans != None:
                    command = "ovs-vsctl set port " + str(curPort) + " trunks=" + str(trunkVlans)
                    devIntRetStruct = switch.DeviceInteract(connection=connection, command=command)
                    retCode = devIntRetStruct['returnCode']
                    if retCode != 0:
                       common.LogOutput('error', "Failed to set port "+ str(curPort) + " trunks to " + str(trunkVlans))
                       retString = common.ReturnJSONCreate(returnCode=1, data="")
                       return retString
                    else:
                       common.LogOutput('debug', "Set port " + str(curPort) + " trunks=" + str(trunkVlans))
                    
                    
                 # For each port
    #else:
       # Commands to unconfigure the bridge
    
    
    retString = common.ReturnJSONCreate(returnCode=0, data=retStruct)
    return retString