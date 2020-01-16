#
#       Samsung TV websocket control plugin
#
#       Author:     Pawcio 2018
#
#       WebSocket implementation based on the https://github.com/dhbaird/easywsclient 
#
"""
<plugin key="SamsungTV_WS" version="1.0.0" name="SamsungTV_WS with Kodi Remote" author="Pawcio" wikilink="" externallink="http://">
    <description>
SamsungTV websocket control Plugin.<br/><br/>
All samsungs' tv with websocket control <br/><br/>
    </description>
    <params>
        <param field="Address" label="IP Address" width="200px" default="192.168.1.38"/>
        <param field="Port" label="Port" width="40px" required="true" default="8001"/>
        <param field="Mode1" label="MAC address for the wol" width="400px" default="e4:7d:bd:52:05:a9"/>
        <param field="Mode6" label="Debug" width="75px">
            <options>
                <option label="True" value="Debug"/>
                <option label="False" value="Normal"  default="true" />
            </options>
        </param>
    </params>
</plugin>
"""
import Domoticz
import time
import json

"""                                                                         
"KEY_CONTENTS"                           
"KEY_GUIDE"                                                        
"KEY_PANNEL_CHDOWN"                                          
"KEY_DTV"          
"KEY_HDMI"         
"""

KEY = {
    'PowerOff' :    '"KEY_POWER"',    # Key "Power"
    'Tools' :       '"KEY_TOOLS"',    # Key "Tools"
    'Channel' :     '"KEY_CH_LIST"',    # Key "Channel list"
    'Key1' :        '"KEY_1"',      # Key "1"
    'Key2' :        '"KEY_2"',      # Key "2"   
    'Key3' :        '"KEY_3"',      # Key "3"
    'Key4' :        '"KEY_4"',      # Key "4"
    'Key5' :        '"KEY_5"',      # Key "5"
    'Key6' :        '"KEY_6"',      # Key "6"
    'Key7' :        '"KEY_7"',      # Key "7"
    'Key8' :        '"KEY_8"',      # Key "8"
    'Key9' :        '"KEY_9"',      # Key "9"
    'Key0' :        '"KEY_0"',     # Key "0"
    "VolumeUp":     '"KEY_VOLUP"',  # Key "volume up"
    "Mute":         '"KEY_MUTE"' ,  # Key "mute"
    "ChannelUp":    '"KEY_CHUP" ',  # Key "bouquet up"
    "VolumeDown":   '"KEY_VOLDOWN"',  # Key "volume down"
    "ChannelDown":  '"KEY_CHDOWN"',  # Key "bouquet down"
    "Details":      '"KEY_INFO"',  # Key "info"
    "Up":           '"KEY_UP"',  # Key "up"
    "Home":         '"KEY_HOME"',  # Key "home"
    "Menu":         '"KEY_MENU"',  # Key "menu"
    "Left":         '"KEY_LEFT"',  # Key "left"
    "Select":       '"KEY_ENTER"',  # Key "OK"
    "Right":        '"KEY_RIGHT"',  # Key "right"
    "Down":         '"KEY_DOWN" ',  # Key "down"
    "Red" :         '"KEY_RED"',   # Key "red"
    "Green" :       '"KEY_GREEN"',   # Key "green"
    'Yellow' :      '"KEY_YELLOW"',   # Key "yellow"
    'Blue' :        '"KEY_BLUE"  ',   # Key "blue"
    'Source' :      '"KEY_SOURCE"',   # Key "source"
    "Back" :        '"KEY_RETURN"', 
    "Exit" :        '"KEY_EXIT"', 
}

class MyWebSocket:

    lastPing = time.time()

    CONTINUATION = 0x0
    TEXT_FRAME = 0x1
    BINARY_FRAME = 0x2
    CLOSE = 8
    PING = 9
    PONG = 0xa
    
    state = 0; #0 - wait for the http upgrade response
    conn = None
    url = ""
    addr = ""
    port = ""
    
    rxbuf = bytearray()
    full_message = bytearray()
    
    def __init__(self, url):
        self.state = 0
        self.url = url
        
    def createConnection(self, addr, port):
        
        self.lastPing = time.time()
        
        self.state = 1 #connecting
        self.addr = addr
        self.port = port
        self.conn = Domoticz.Connection(Name="WS", Transport="TCP/IP", Protocol="NONE", Address=addr, Port=port)
        self.conn.Connect()
        
        return self.conn
     
    def onConnect(self, Status):
        if 0 == Status:
            sendData =  'GET ' + self.url + ' HTTP/1.1\r\n'
            sendData += 'Upgrade: websocket\r\n' 
            sendData += 'Connection: Upgrade\r\n' 
            sendData += 'Origin: Domoticz\r\n' 
            sendData += 'Sec-WebSocket-Key: x3JJHMbDL1EzLkh9GBhXDw==\r\n' 
            sendData += 'Sec-WebSocket-Version: 13\r\n' 
            sendData += 'Host: '+self.addr+":"+self.port
            sendData += '\r\n\r\n'
            
            #Domoticz.Log("sendData: " + str(sendData))
            self.conn.Send(sendData.encode())
        else:
            #Can't connect
            self.state = 0
    
    def initVars(self):
        self.state = 0
        self.rxbuff = bytearray()
        self.full_message = bytearray()        
    
    def onDisconnect(self):
        self.conn = None
        self.initVars()
        
    def onMessage(self, Connection, Data):
        
        ret = bytearray()
        
        #Domoticz.Log("Connection: " + str(Connection))
        strData = str(Data)
        #Domoticz.Log("Data: " + strData)
        
        if 1 == self.state: 
            if "Switching Protocols" in strData:
                self.state = 2
            else:
                Domoticz.Error("Wrong ws upgrade response")
        elif 2 >= self.state:
            self.rxbuf += Data
            if len(self.rxbuf) < 2: 
                return      # Need at least 2 
            fin = (self.rxbuf[0] & 0x80) == 0x80
            opcode = self.rxbuf[0] & 0x0f
            mask = (self.rxbuf[1] & 0x80) == 0x80
            N0 = self.rxbuf[1] & 0x7f
            header_size = 2 + (2 if N0 == 126 else 0) + (8 if N0 == 127 else 0) + (4 if True == mask else 0);
            
            #Domoticz.Log("fin: " + str(fin) + " , opcode " + str(opcode) + " , mask: " + str(mask) + " , N0:" + str(N0) + " , header_size: " + str(header_size))
            
            if len(self.rxbuf) < header_size:
                return      #Need: header_size - rxbuf.size()
               
            N = 0
            i = 0
            masking_key = ([0, 0, 0, 0])
            if N0 < 126:
                N = N0
                i = 2
            elif N0 == 126:
                N = 0;
                N |= self.rxbuf[2] << 8;
                N |= self.rxbuf[3] << 0;
                i = 4
            elif N0 == 127:
                N = 0;
                N |= (self.rxbuf[2]) << 56;
                N |= (self.rxbuf[3]) << 48;
                N |= (self.rxbuf[4]) << 40;
                N |= (self.rxbuf[5]) << 32;
                N |= (self.rxbuf[6]) << 24;
                N |= (self.rxbuf[7]) << 16;
                N |= (self.rxbuf[8]) << 8;
                N |= (self.rxbuf[9]) << 0;
                i = 10

            if True == mask:
                masking_key[0] = self.rxbuf[i+0]
                masking_key[1] = self.rxbuf[i+1]
                masking_key[2] = self.rxbuf[i+2]
                masking_key[3] = self.rxbuf[i+3]

            if len(self.rxbuf) < header_size+N:
                return          #Need: header_size+N - rxbuf.size()

            #We got a whole message, now do something with it:
            if opcode == self.TEXT_FRAME or opcode == self.BINARY_FRAME or opcode == self.CONTINUATION:

                if True == mask:
                    for i in range(N):
                        rxbuf[i+header_size] ^= masking_key[i&0x3]
                        
                #just feed
                self.full_message += self.rxbuf[header_size:header_size+N]
                if True == fin:
                    #Domoticz.Log("message: " + str(self.full_message))
                    #callable(self.full_message)
                    ret = self.full_message
                    self.full_message = bytearray()

            elif opcode == self.PING:
                if True == mask:
                    for i in range(N):
                        self.rxbuf[i+header_size] ^= masking_key[i&0x3]
                self.sendData(self.PONG, self.rxbuf[header_size:header_size+N])
                self.lastPing = time.time()
            elif opcode == self.PONG:
                pass
            elif opcode == self.CLOSE:
                self.close()
            else:
                Domoticz.Error("ERROR: Got unexpected WebSocket message")
                self.close()

            self.rxbuf = bytearray()          
            
        
        return ret
    
    def sendData(self, type, buf):
        #TODO:
        #Masking key should (must) be derived from a high quality random
        #number generator, to mitigate attacks on non-WebSocket friendly
        #middleware:
        masking_key = bytearray([ 0x12, 0x34, 0x56, 0x78 ])
        useMask = True
        message_size = len(buf)
        
        if self.state < 2:
            return
        header = bytearray(2 + (2 if message_size >= 126 else 0) + (6 if message_size >= 65536 else 0) + (4 if True == useMask else 0))

        header[0] = 0x80 | type;
        if message_size < 126:
            header[1] = (message_size & 0xff) | (0x80 if True == useMask else 0);
            if True == useMask:
                header[2] = masking_key[0]
                header[3] = masking_key[1]
                header[4] = masking_key[2]
                header[5] = masking_key[3]
        elif message_size < 65536:
            header[1] = 126 | (0x80 if True == useMask else 0)
            header[2] = (message_size >> 8) & 0xff;
            header[3] = (message_size >> 0) & 0xff;
            if True == useMask:
                header[4] = masking_key[0]
                header[5] = masking_key[1]
                header[6] = masking_key[2]
                header[7] = masking_key[3]
        else:
            header[1] = 127 | (0x80 if True == useMask else 0)
            header[2] = (message_size >> 56) & 0xff
            header[3] = (message_size >> 48) & 0xff
            header[4] = (message_size >> 40) & 0xff
            header[5] = (message_size >> 32) & 0xff
            header[6] = (message_size >> 24) & 0xff
            header[7] = (message_size >> 16) & 0xff
            header[8] = (message_size >>  8) & 0xff
            header[9] = (message_size >>  0) & 0xff
            if True == useMask:
                header[10] = masking_key[0]
                header[11] = masking_key[1]
                header[12] = masking_key[2]
                header[13] = masking_key[3]

        myBuf = bytearray(buf)
        if True == useMask:
            for i in range(message_size):
                myBuf[i] ^= masking_key[i&0x3]
      
        s = header + myBuf
        self.conn.Send(s)
        
        return
        
    def close(self):
        if self.state == 0:
            return
        
        self.state = 0
        buf = bytearray([0x88, 0x80, 0x00, 0x00, 0x00, 0x00])   #last 4 bytes are a masking key
        self.conn.Send(buf)
        self.conn.Disconnect()
        
        Domoticz.Error("close called!!")
        
        return
       
    def getLastPing(self):
        return self.lastPing

  
class SamsungWS(MyWebSocket):

    lastKey = time.time()
    keyHistory = []
    
    def __init__(self, url):
        MyWebSocket.__init__(self, url)
    
    def onConnect(self, Status):
        if 0 != Status:
            self.keyHistory.clear()
          
        MyWebSocket.onConnect(self, Status)
     
    def onMessage(self, Connection, Data):
        prevState = self.state
        msg = MyWebSocket.onMessage(self, Connection, Data)
        #Domoticz.Log("msg: " + str(msg.decode("utf-8", "ignore")))
        
        try:
            j = json.loads(msg)
            if j["event"] == "ms.channel.connect":
                self.state = 3
                #connection established -> send all cached keys
                for key in self.keyHistory:
                    self.onKey(key)
                self.keyHistory.clear()
        except:
            pass
        
           
        
    def createConnection(self, addr, port):
        self.lastKey = time.time()
        return MyWebSocket.createConnection(self, addr, port)
        
    def onKey(self, key):
        #Domoticz.Error("key: " + cmd)
    
        lastKey = time.time()
        if self.state == 3:
            cmd = '{"method":"ms.remote.control","params":{"Cmd":"Click","DataOfCmd":' + key + ',"Option":"false","TypeOfRemote":"SendRemoteKey"}}'
            self.sendData(self.TEXT_FRAME, cmd.encode())
        else:
            
            self.keyHistory.append(key)
            
            if self.state == 0:
                #reconnect
                self.createConnection(Parameters["Address"], Parameters["Port"])
                                  
        return

    def getLastKey(self):
        return self.lastKey

    def close(self):
        MyWebSocket.close(self)
        self.keyHistory.clear()
        
class BasePlugin:
    
    status = 1
    ws = SamsungWS('/api/v2/channels/samsung.remote.control?name=d3Nwcm94eQ==')
    
   
    def onStart(self):
        if Parameters["Mode6"] == "Debug":
            Domoticz.Debugging(1)
            
        if (len(Devices) == 0):

            Domoticz.Device(Name="Input", Unit=1, Type=17, Image=2, Switchtype=17).Create()
            Domoticz.Device(Name="PowerOn", Unit=2, TypeName="Switch", Switchtype=9).Create()
                
        DumpConfigToLog()
        self.handleConnect()
        return

    def onConnect(self, Connection, Status, Description):

        #Domoticz.Error("Connection: " + str(Connection) + " , Status: " + str(Status) + " , Desc: " + str(Description))
        
        if (Status == 0):
            Domoticz.Log("Connected successfully to: "+Connection.Address)

            self.ws.onConnect(Status)
            self.status = 1
            self.SyncDevices(0)

            return
            
        else:
            Domoticz.Log("Failed to connect ("+str(Status)+") to: "+Parameters["Address"]+" with error: "+Description)
            self.status = 0

            
        self.SyncDevices(1)

    def onMessage(self, Connection, Data):
     
        #Domoticz.Error("Connection: " + str(Connection))
     
        if Parameters["Mode6"] == "Debug":
            Domoticz.Debug("onMessage called with Data: '"+str(Data)+"'")
        
        self.ws.onMessage(Connection, Data)
        
        """
        #try:
            # self.SyncDevices(0)
            #self.conn.Disconnect()
            #self.conn = None
                
        # except Exception as inst:
            # Domoticz.Error("Exception in onMessage, called with Data: '"+str(strData)+"'")
            # Domoticz.Error("Exception detail: '"+str(inst)+"'")
            # self.SyncDevices(1)
            # raise
        """
        return

    def onDisconnect(self, Connection):
        Domoticz.Log("Disconnected from: "+Connection.Address+":"+Connection.Port)
        self.ws.onDisconnect()
        return

    def onHeartbeat(self):
        #Domoticz.Debug("onHeartbeat called, last response seen " + str(self.lastHeartbeat) + "  heartbeats ago.")

        if (time.time() - self.ws.getLastPing()) > 30:
            self.ws.close()
            
        if time.time() - self.ws.getLastKey() > 30:
            self.ws.close()
            
        return

    def handleConnect(self):
        self.ws.createConnection(Parameters["Address"], Parameters["Port"])
    
    def SyncDevices(self, TimedOut):

        #UpdateDevice(1, self.status, "Samsung TV", TimedOut)
        UpdateDevice(1, 1, "Samsung TV", 0) #always on...

        return
        
    def sentWOL(self):
        import struct, socket
        # Took from the examples/Kodi.py
        mac_address = Parameters["Mode1"].replace(':','')
        # Pad the synchronization stream.
        data = ''.join(['FFFFFFFFFFFF', mac_address * 16])
        
        #Domoticz.Log('data: ' + str(data) + " , len: " + str(len(data)))
        
        send_data = b''
        # Split up the hex values and pack.
        for i in range(0, len(data), 2):
            send_data = b''.join([send_data, struct.pack('B', int(data[i: i + 2], 16))])
           
        # Broadcast it to the LAN.
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.sendto(send_data, ('<broadcast>', 7))  
        #Domoticz.Log('send_data: ' + str(send_data))
    
    def onCommand(self, Unit, Command, Level, Hue):  
        Domoticz.Log("onCommand "+str(Command))  
        
        if 1 == Unit:
            if "Off" == Command:
                Command = "PowerOff"
                
            if "On" == Command or "PowerOn" == Command:
                self.sentWOL()
            else:
                global KEY
                if Command in KEY:
                    self.ws.onKey(KEY[Command])
        else:
            self.sentWOL()
            
        return
        
        
global _plugin
_plugin = BasePlugin()

def onStart():
    global _plugin
    _plugin.onStart()

def onConnect(Connection, Status, Description):
    global _plugin
    _plugin.onConnect(Connection, Status, Description)

def onMessage(Connection, Data):
    global _plugin
    _plugin.onMessage(Connection, Data)

def onCommand(Unit, Command, Level, Hue):
    global _plugin
    _plugin.onCommand(Unit, Command, Level, Hue)

def onDisconnect(Connection):
    global _plugin
    _plugin.onDisconnect(Connection)

def onHeartbeat():
    global _plugin
    _plugin.onHeartbeat()

def UpdateDevice(Unit, nValue, sValue, TimedOut):
    # Make sure that the Domoticz device still exists (they can be deleted) before updating it 
    if (Unit in Devices):
        if (Devices[Unit].nValue != nValue) or (Devices[Unit].sValue != sValue) or (Devices[Unit].TimedOut != TimedOut):
            Devices[Unit].Update(nValue=int(nValue), sValue=str(sValue), TimedOut=TimedOut)
            Domoticz.Log("Update "+str(nValue)+":'"+str(sValue)+"' ("+Devices[Unit].Name+")")
    return

def DumpConfigToLog():
    for x in Parameters:
        if Parameters[x] != "":
            Domoticz.Debug( "'" + x + "':'" + str(Parameters[x]) + "'")
    Domoticz.Debug("Device count: " + str(len(Devices)))
    for x in Devices:
        Domoticz.Debug("Device:           " + str(x) + " - " + str(Devices[x]))
        Domoticz.Debug("Internal ID:     '" + str(Devices[x].ID) + "'")
        Domoticz.Debug("External ID:     '" + str(Devices[x].DeviceID) + "'")
        Domoticz.Debug("Device Name:     '" + Devices[x].Name + "'")
        Domoticz.Debug("Device nValue:    " + str(Devices[x].nValue))
        Domoticz.Debug("Device sValue:   '" + Devices[x].sValue + "'")
        Domoticz.Debug("Device LastLevel: " + str(Devices[x].LastLevel))
    return



