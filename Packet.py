from enum import Enum
import serial
import os.path
import codecs
from threading import Thread, Lock, RLock
import binascii
from DeciboxApi import DeciboxAPI

######################################################
##
##             Vauban's Opcodes Enum
##
######################################################

class VaubanOpcodes(Enum):

     
    MSG_SEND_BIP                    = 0x42
    MSG_SEND_LED                    = 0x44
    MSG_SEND_ENROLLMENT             = 0x45
    MSG_SEND_FINGERPRINT_DEFINE     = 0x4D
    MSG_SEND_POLLING                = 0x50



######################################################
##
##           Vauban's Enrollement data
##                  Fingers Enum
##
######################################################

class VaubanEnrollementData(Enum):

    ENROLLEMENT_ONE_FINGER          = 0x1
    ENROLLEMENT_TWO_FINGER          = 0x2
    ENROLLEMENT_THREE_FINGER        = 0x3
    

######################################################
##
##              Vauban Opcode Handler
##
######################################################

class VaubanOpcodeHandler(object):

    def __init__(self):
        return

    ######################################################
    ##
    ##                 Sending handler
    ##  
    ######################################################

    def sendLedPacket(self, pRedValue, pGreenValue, pBlueValue, pTime, pRepeat, pDevicePtr):
        
        lPacket = VaubanPacket(device=pDevicePtr, opcode=VaubanOpcodes.MSG_SEND_LED)

        # Red Led
        lPacket.pushData(pRedValue, 2)

        # Green Led
        lPacket.pushData(pGreenValue, 2)

        # Blue Led
        lPacket.pushData(pBlueValue, 2)

        # Time
        lPacket.pushData(pTime, 2)

        # Repeat
        lPacket.pushData(pRepeat, 1)

        pDevicePtr.device.write(lPacket.finalizePacket())

    def sendBuzzerPacket(self, pState, pTime, pRepeat, pDevicePtr):

        lPacket = VaubanPacket(device=pDevicePtr, opcode=VaubanOpcodes.MSG_SEND_BIP)

        # buzzer state
        lPacket.pushData(pState, 1)

        # buzzer time
        lPacket.pushData(pTime, 2)

        # buzzer repeat
        lPacket.pushData(pRepeat, 1)

        pDevicePtr.device.write(lPacket.finalizePacket())

        return

    def sendEnrollementPacket(self, pFingerCount, pDevicePtr):
        
        lPacket = VaubanPacket(device=pDevicePtr, opcode=VaubanOpcodes.MSG_SEND_ENROLLMENT)

        # finger count
        lPacket.pushData(pFingerCount)

        pDevicePtr.device.write(lPacket.finalizePacket())

    def sendPollingPacket(sekf, pDevicePtr):

        lPacket = VaubanPacket(device=pDevicePtr, opcode=VaubanOpcodes.MSG_SEND_POLLING)
        pDevicePtr.device.write(lPacket.finalizePacket())

        return

    def sendVerificationPacket(self, pMode, pDevicePtr):

        lPacket = VaubanPacket(device=pDevicePtr, opcode=VaubanOpcodes.MSG_SEND_FINGERPRINT_DEFINE)
        
        # 1 = Enable fingerprint check
        # 0 = Disable fingerprint check
        lPacket.pushData(pMode, 1)

        pDevicePtr.device.write(lPacket.finalizePacket())




    def processPacket(self, pPacket):

        if pPacket.opcode == 'E':

            lResult = self.handlingEnrollementPacket(pPacket)

            # Enrollement failed
            if type(lResult) is bool:
                return

            # Enrollement succeed
            else:
                
                DeciboxAPI().checkAccess(lResult, "/dev/ttyUSB0")
                return

        elif pPacket.opcode == 'P':
            return

        else :
            
            return
        
        return

    ######################################################
    ##
    ##              Handling enrollement
    ##  
    ######################################################

    def handlingEnrollementPacket(self, pPacket):

        lStr = ""

        lState = binascii.unhexlify(str(pPacket.raw[0])).decode()

        print( "receive enrollement state : " + lState )

        # Enrollement succeed
        if lState == 'S':

            for lInt in pPacket.raw[1:9]:
                lStr += binascii.unhexlify(str(lInt)).decode()

            
            lJ = 0
            lBuffer = ""
            lCardId = ""

            for lI in range(len(lStr) -1, -1, -1) :

                lBuffer += lStr[ lI ]

                if lJ == 1:

                    lCardId += lBuffer[::-1]
                    lBuffer = ''
                    lJ = 0

                else:
                    lJ += 1

            return lCardId.lower()

        # Enrollement failed
        else :
            return False


        return


######################################################
##
##              Vauban device manager
##
######################################################

class VaubanDevice(object):

    mDevicePtr = None
    mDeviceID = 0
    mRunThread = None
    mCallback = None

    def __init__(self, pInterface, pDeviceID):

        if pDeviceID is None or pDeviceID <= 0:
            raise NameError("Invalid deviceID : " + str(pDeviceID))

        if os.path.exists(pInterface) == False : 
            raise NameError("Invalid interface " + pInterface)


        self.mDevicePtr = serial.Serial(
            port=pInterface,
            baudrate=19200,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            bytesize=serial.EIGHTBITS)

        if self.mDevicePtr.is_open == False:
            raise NameError("Could not open interface " + pInterface + " maybe busy ? ")

        self.mDeviceID = pDeviceID

        return

    ######################################################
	##
	##        Start read service async thread
	##
	######################################################

    def startReadService(self, pReadCallback):
       
        self.mRunThread = Thread(target=self._readService)
        self.mRunThread.daemon = False
        self.mRunThread.start()
        self.mCallback = pReadCallback

        return


    def _readService(self):

        lPacket = bytearray()
        lOnRead = False

        while(True):

            # read one byte from device
            lByte = int(hex(int.from_bytes(self.mDevicePtr.read(),  byteorder='big')).replace('0x', '').upper())
            
            # if we receive new packet, or we are on reading
            if lByte == 0x2 or lOnRead == True:
                
                lOnRead = True
                lPacket.append(lByte)

            # if we are at end of our packet
            if lByte == 0x3:
                
                lOnRead = False

                if callable(self.mCallback) :
                    
                    # Lock callback while we use it
                    Lock()

                    self.mCallback(lPacket)
                    lPacket.clear()
            
                    # Release callback locking
                    RLock()

        return

    ######################################################
	##
	##                 Class properties
	##
	######################################################

    @property
    def deviceId(self):
        return int(self.mDeviceID)

    @property
    def device(self):
        return self.mDevicePtr


class VaubanPacket(object):

    mOpcode = 0x0
    mBytes = bytearray()
    mControlFrame = bytearray()
    mDevicePtr = None
    mRawPacket = None
    
    ######################################################
	##
	##            Constants do not change
	##
	######################################################
    
    mStartFrame = 0x2
    mEndFrame = 0x3


    ######################################################
	##
	##                  Constructor
	##
	######################################################

    def __init__(self, *args, **kwargs):

        lDevicePtr = kwargs.get('device', None)
        lOpcode = kwargs.get('opcode', 0x0)
        lPacket = None

        if 'packet' in kwargs:
            lPacket = kwargs.get('packet', None)

            if lPacket is not None and len(lPacket) >= 5:
                self.decodePacket(lPacket)

        if lDevicePtr is None and lPacket is None:
            raise NameError("Invalid device ptr")

        self.mDevicePtr = lDevicePtr

        if lOpcode is not 0x0:
            self.mOpcode = lOpcode.value

    
    def decodePacket(self, pPacket):

        lDeviceId = pPacket[1:5]
        lOpcode = pPacket[5]

        print(lOpcode)

        lString = ""

        for lInt in lDeviceId:
            lString += binascii.unhexlify(str(lInt)).decode()
    
        lDeviceId = int(lString, 16)

        self.mOpcode = binascii.unhexlify(str(lOpcode)).decode()
        self.mRawPacket = pPacket[6:]

        return

    def readPacket(self, pSize):
        return

    ######################################################
	##
	##              Create control frame
	##
	######################################################

    def createControlFrame(self):
        
        lXorStr = ""

        for lByte in self.mBytes:
            lXorStr += hex(int(lByte)) + "^"

        lControlFrame = hex(eval(lXorStr[:-1])).replace('0x', '').upper().zfill(2)

        for lChar in lControlFrame:
            lByte = int(codecs.encode(bytes(lChar.encode('ascii')), 'hex'))

            self.mControlFrame.append(lByte)

    ######################################################
	##
	##             Push data in our packet
	##
	######################################################

    def pushData(self, pData, pByteSize = 1):  

        if(issubclass(type(pData), Enum) is True):
            pData = pData.value
        
        if type(pData) is bytearray or type(pData) is dict:
            
            for lByte in pData:
                self.mBytes.append(lByte)

        else:

            if len(str(pData)) < 2 and  pByteSize == 2 or len(hex(pData).replace('0x', '')) < 2 and  pByteSize == 2:
                pData = '0' + hex(pData).replace('0x', '').upper()
            else : 
                pData = hex(pData).replace('0x', '').upper()

            if len(str(pData)) >= 2:
               
                for lData in str(pData):
                    self.mBytes.append(int(hex(ord(str(lData).encode('ascii'))).replace('0x', '')))
                
            else:
                print(pData)
                self.mBytes.append(int(hex(ord(str(pData).encode('ascii'))).replace('0x', '').zfill(pByteSize)))
           

    ######################################################
    ##
    ##             Insert our device ID
    ##
    #####################################################

    def insertDeviceID(self):

        if self.mDevicePtr is None:
            raise NameError("Invalid device ptr, aborting deviceId building...")

        lDeviceId = hex(self.mDevicePtr.deviceId).replace("0x", "").upper().zfill(4)
           

        for lI in lDeviceId:
            lByte = int(codecs.encode(bytes(lI.encode('ascii')), 'hex'))
            
            self.mBytes.append(int('0x' + str(lByte), 16))

        return


    ######################################################
	##
	##   Finalize packet and push header data ect ...
	##
	######################################################

    def finalizePacket(self):
     
        lPacket = self.mBytes

        self.mBytes = bytearray()

        # Insert device Id first in our packet
        self.insertDeviceID()
       
        # Insert packet opcode 
        self.mBytes.append(int(hex(ord(chr(self.mOpcode))).replace('0x', ''), 16))


        # push our temp bytebuffer in our 
        for lByte in lPacket:
            self.mBytes.append(int('0x'+str(lByte), 16))

        # Create control frame
        # with xor()
        self.createControlFrame()


        for lByte in self.mControlFrame:
            self.mBytes.append(int('0x'+str(lByte), 16))

        lPacket = []

        self.mBytes.insert(0, self.mStartFrame)
        self.mBytes.append(self.mEndFrame)

        return self.mBytes


    ######################################################
	##
	##                 Class properties
	##
	######################################################

    @property
    def opcode(self):
        return self.mOpcode

    @property
    def raw(self):
        return self.mRawPacket


