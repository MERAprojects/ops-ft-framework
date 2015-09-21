# (C) Copyright 2015 Hewlett Packard Enterprise Development LP
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#
import pexpect
from opstestfw import gbldata
from opstestfw import *
import opstestfw.switch
import time
import xml.etree.ElementTree
import os
import re
from Topology import Topology

"""
This is the base class for any device - This gives the test case developer the
ability to connect to the device along with interacting with the device
"""


class Device ():

    def __init__(self, **kwargs):
        self.topology = kwargs.get('topology', None)
        self.device = kwargs.get('device', None)
        self.expectHndl = None
        self.expectList = ['login:\s*$',
                           'root@\S+:.*#\s*$',
                           'bash-\d+.\d+#',
                           pexpect.EOF,
                           pexpect.TIMEOUT]
        self.Connect()

    def cmd(self, cmd):
        retStruct = self.DeviceInteract(command=cmd)
        returnCode = retStruct.get('returnCode')
        if returnCode != 0:
            LogOutput('error',
                      "Failed to send command " + cmd + " to device"
                      + self.device)
            return None
        returnBuffer = retStruct.get('buffer')
        return returnBuffer

    # Device Connect Method
    def Connect(self):
        # Look up and see if we are physical or virtual
        xpathString = ".//reservation/id"
        rsvnEtreeElement = XmlGetElementsByTag(self.topology.TOPOLOGY,
                                               xpathString)
        if rsvnEtreeElement is None:
            # We are not in a good situation, we need to bail
            LogOutput('error',
                      "Could not find reservation id tag in topology")
            return None

        rsvnType = rsvnEtreeElement.text

        # Look up the device name in the topology - grab connectivity
        # information
        xpathString = ".//device[name='" + self.device + "']"
        etreeElement = XmlGetElementsByTag(self.topology.TOPOLOGY,
                                           xpathString)
        if etreeElement is None:
            # We are not in a good situation, we need to bail
            LogOutput('error', "Could not find device " + self.device + " in \
                      topology")
            return None
        if rsvnType == 'virtual':
            # Code for virtual
            # Go and grab the connection name
            xpathString = ".//device[name='\
                          " + self.device + "']/connection/name"
            virtualConn = XmlGetElementsByTag(self.topology.TOPOLOGY,
                                              xpathString)
            if virtualConn is None:
                LogOutput('error', "Failed to virtual connection for \
                          " + self.device)
                return None
            telnetString = "docker exec -ti " + self.device + " /bin/bash"
        else:
            # Code for physical
            # Grab IP from etree
            xpathString = ".//device[name='" + self.device + "']/connection/ipAddr"
            ipNode = XmlGetElementsByTag(self.topology.TOPOLOGY, xpathString)
            if ipNode is None:
                LogOutput('error',
                          "Failed to obtain IP address for \
                          device " + self.device)
                return None

            self.ipAddress = ipNode.text
            LogOutput('debug',
                      self.device + " connection \
                      IP address:  " + self.ipAddress)

            # Grab Port from etree
            xpathString = ".//device[name='" + self.device + "']/connection/port"
            portNode = XmlGetElementsByTag(self.topology.TOPOLOGY, xpathString)
            if portNode is None:
                LogOutput('error',
                          "Failed to obtain Port for \
                          device " + self.device)
                return None

            self.port = portNode.text
            LogOutput('debug',
                      self.device + " connection port:  " + self.port)

            # Grab a connetion element - not testing this since this should
            # exist since we obtained things before us
            xpathString = ".//device[name='" + self.device + "']/connection"
            connectionElement = XmlGetElementsByTag(self.topology.TOPOLOGY,
                                                    xpathString)

            # Grab a connetion element - not testing this since this should
            # exist since we obtainedthings before us
            xpathString = ".//device[name='" + self.device + "']/connection"
            connectionElement = XmlGetElementsByTag(self.topology.TOPOLOGY,
                                                    xpathString)
            # Create Telnet handle
            # Enable expect device Logging for every connection
            # Single Log file exists for logging device exchange using pexpect
            # logger.  Device logger  name format :: devicename_IP-Port

            telnetString = "telnet " + self.ipAddress + " " + self.port
            expectFileString = self.device + "_" + self.ipAddress + "--" + self.port + ".log"

            ExpectInstance = opstestfw.ExpectLog.DeviceLogger(expectFileString)
            expectLogFile = ExpectInstance.OpenExpectLog(expectFileString)
            if expectLogFile == 1:
                LogOutput('error', "Unable to create expect log file")
                exit(1)
            # Opening an expect connection to the device with the specified
            # log file
            LogOutput('debug',
                      "Opening an expect connection to the device with the \
                      specified log file" + expectFileString)
            if rsvnType == 'virtual':
                logFile = opstestfw.ExpectLog.DeviceLogger(expectLogFile)
                self.expectHndl = pexpect.spawn(telnetString,
                                                echo=False,
                                                logfile=logFile)
                self.expectHndl.delaybeforesend = 1
            else:
                logFile = opstestfw.ExpectLog.DeviceLogger(expectLogFile)
                self.expectHndl = pexpect.spawn(telnetString,
                                                echo=False,
                                                logfile=logFile)

            # Lets go and detect our connection - this will get us to a context
            # we know about
            retVal = self.DetectConnection()
            if retVal is None:
                LogOutput('error',
                          "Failed to detect connection for device - looking \
                          to reset console")
                # Connect to the console
                conDevConn = console.Connect(self.ipAddress)
                # now lets logout the port we are trying to connect to
                # print("send logout seq")
                retCode = console.ConsolePortLogout(connection=conDevConn,
                                                    port=self.port)
                if retCode != 0:
                    return None
                console.ConnectionClose(connection=conDevConn)
                # Now retry the connect & detect connection
                logFile = opstestfw.ExpectLog.DeviceLogger(expectLogFile)
                self.expectHndl = pexpect.spawn(telnetString,
                                                echo=False,
                                                logfile=logFile)
                retVal = self.DetectConnection()
            if retVal is None:
                return None

    # DetectConnection - This will get the device in the proper context state
    def DetectConnection(self):
        bailflag = 0

        self.expectHndl.send('\r')
        time.sleep(2)
        connectionBuffer = []
        sanitizedBuffer = ""
        while bailflag == 0:
            index = self.expectHndl.expect(self.expectList,
                                           timeout=200)
            if index == 0:
                # Need to send login string
                LogOutput("debug", "Login required::")
                self.expectHndl.sendline("root")
                connectionBuffer.append(self.expectHndl.before)
            elif index == 1:
                bailflag = 1
                LogOutput("debug", "Root prompt detected:")
                connectionBuffer.append(self.expectHndl.before)
            elif index == 2:
                # Got prompt.  We should be good
                bailflag = 1
                LogOutput("debug", "Root prompt detected: Virtual")
                connectionBuffer.append(self.expectHndl.before)
            elif index == 3:
                # Got EOF
                LogOutput('error', "Telnet to switch failed")
                return None
            elif index == 4:
                # Got a Timeout
                LogOutput('error', "Connection timed out")
                return None
            else:
                connectionBuffer.append(self.expectHndl.before)
        # Append on buffer after
        connectionBuffer.append(self.expectHndl.after)
        self.expectHndl.expect(['$'], timeout=2)
        # Now lets put in the topology the expect handle
        for curLine in connectionBuffer:
            sanitizedBuffer += curLine
        LogOutput('debug', sanitizedBuffer)
        return self.expectHndl

    # Routine allows the user to interact with a device and get appropriate
    # output
    def DeviceInteract(self, **kwargs):
        command = kwargs.get('command')
        errorCheck = kwargs.get('errorCheck', True)
        ErrorFlag = kwargs.get('CheckError')

        # Local variables
        bailflag = 0
        returnCode = 0
        retStruct = dict()
        retStruct['returnCode'] = 1
        retStruct['buffer'] = []

        # Send the command
        self.expectHndl.send(command)
        self.expectHndl.send('\r')
        time.sleep(1)
        connectionBuffer = []

        while bailflag == 0:
            index = self.expectHndl.expect(self.expectList,
                                           timeout=120)
            if index == 0:
                # Need to send login string
                self.expectHndl.send("root \r")
                connectionBuffer.append(self.expectHndl.before)
            elif index == 1:
                # Got prompt.  We should be good
                bailflag = 1
                connectionBuffer.append(self.expectHndl.before)
            elif index == 2:
                # Got bash prompt - virtual
                bailflag = 1
                connectionBuffer.append(self.expectHndl.before)
            elif index == 3:
                # got EOF
                bailflag = 1
                connectionBuffer.append(self.expectHndl.before)
                LogOutput('error', "connection closed to console")
                returnCode = 1
            elif index == 4:
                # got Timeout
                bailflag = 1
                connectionBuffer.append(self.expectHndl.before)
                LogOutput('error', "command timeout")
                returnCode = 1
            else:
                connectionBuffer.append(self.expectHndl.before)
                connectionBuffer.append(self.expectHndl.after)
                self.expectHndl.expect(['$'], timeout=1)

        santString = ""
        for curLine in connectionBuffer:
            santString += str(curLine)

        # Error Check routine identification
        # There are seperate Error check libraries for CLI,OVS and REST
        # commands.  The following portion checks for Errors for OVS commands
        if errorCheck is True and returnCode == 0 and ErrorFlag is None:
            # Dump the buffer the the debug log
            LogOutput('debug',
                      "Sent and received from device: \n" + santString + "\n")

        # The following portion checks for Errors in CLI commands
        if ErrorFlag == 'CLI':
            LogOutput('debug', "CLI ErrorCode")
        if ErrorFlag == 'Onie':
            LogOutput('debug', "NEED TO FIX")

        # Return dictionary
        LogOutput('debug',
                  "Sent and received from device: \n" + santString + "\n")
        retStruct['returnCode'] = returnCode
        retStruct['buffer'] = santString
        return retStruct

    def ErrorCheck(self, **kwargs):
        buffer = kwargs.get('buffer')
        # Local variables
        returnCode = 0

        retStruct = dict()
        retStruct['returnCode'] = returnCode

        # Set up the command for error check
        command = "echo $?"
        buffer = ""
        self.expectHndl.send(command)
        self.expectHndl.send('\r\n')

        index = self.expectHndl.expect(['root@\S+:.*#\s*$',
                                        'bash-\d+.\d+#\s*$'], timeout=200)
        if index == 0 or index == 1:
            buffer += self.expectHndl.before
            buffer += self.expectHndl.after
        else:
            LogOutput('error',
                      "Received timeout in opstestfw.switch.ErrorCheck")
            retStruct['returnCode'] = 1
            return retStruct

        bufferSplit = buffer.split("\n")
        for curLine in bufferSplit:
            testforValue = re.match("(^[0-9]+)\s*$", curLine)
            if testforValue:
                # Means we got a match
                exitValue = int(testforValue.group(1))
            if exitValue != 0:
                returnCode = exitValue
            else:
                returnCode = 0

        retStruct['returnCode'] = returnCode
        return retStruct
