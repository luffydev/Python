######################################################
##
##                  Channel Handler
##
######################################################

from common.utils import SharedVar
import pickle

class ChannelHandler(object):
    
    mClientStack = list()
    mCurrentChannel = ""
    mCallback = None
    mEventListener = None

    ######################################################
	##
	##                  Constructor
	##
	######################################################

    def __init__(self, pChannelName):

        from websocket.ChannelHandler.ChannelEventHandler import ChannelEventHandler

        self.mEventListener = ChannelEventHandler()

        self.mClientStack = SharedVar('Core').get("Channel", pChannelName)
        self.mCurrentChannel = pChannelName

        if self.mClientStack == None:
            self.mClientStack = list()
            SharedVar('Core').set('Channel', pChannelName, self.mClientStack)
            
        return

    ######################################################
	##
	##         Check if client can join channel
	##
	######################################################

    def canJoin(self, pSocket):
        return pSocket.socketId not in self.mClientStack

    ######################################################
	##
	##    Check if client is already in this channel
	##
	######################################################

    def isAlreadyMember(self, pSocket):
        return pSocket.socketId in self.mClientStack

    ######################################################
	##
	##           Try to join this channel
	##
	######################################################

    def tryJoin(self, pSocket):

        from common.constants.Network import NetworkFlags

        if self.canJoin(pSocket) == True : 
            
            self.mClientStack.append(pSocket.socketId)
            self.save()     

            self.mEventListener.sendEvent(ChannelResolver().getIdFromString(self.mCurrentChannel), 'onChannelUpdate', pSocket)
            self.notify(pSocket, NetworkFlags.FLAG_NEW_CLIENT_CONNECTED)

            return True

        return False

    ######################################################
	##
	##           Try to leave this channel
	##
	######################################################


    def tryLeave(self, pSocket):

        from common.constants.Network import NetworkFlags

        if self.isAlreadyMember(pSocket) == False:
            return False
        else:
            pSocket.removeChannel(self.mCurrentChannel)
        
        return True
            


    ######################################################
	##
	##           Return channel's member
	##
	######################################################

    def getMemberList(self):
        return self.mClientStack

    def save(self):
        SharedVar('Core').set('Channel', str(self.mCurrentChannel), self.mClientStack)
        return 
    
    def notify(self, pSocket, pEvent):

        from websocket.Packet import Packet
        from common.constants.Network import Opcodes, Channel, NetworkFlags

        lPacket = Packet(opcode=Opcodes.SMSG_CHANNEL_NOTIFICATION, channel=Channel.GLOBAL)
        
        lPacket.WriteByte(ChannelResolver().getIdFromString(self.mCurrentChannel))
        lPacket.WriteInt32(pEvent)

        pSocket.server.sendToChannel(lPacket.deflate, pSocket, self.mCurrentChannel)

        return

    def leaveChannel(self, pSocket):

        from common.constants.Network import NetworkFlags

        self.mEventListener.sendEvent(ChannelResolver().getIdFromString(self.mCurrentChannel), 'onChannelUpdate', pSocket)
        
        self.notify(pSocket, NetworkFlags.FLAG_CLIENT_DISCONNECTED)

        self.mClientStack.remove(pSocket.socketId)
        self.save()

        return

class ChannelResolver(object):

     def getIdFromString(self, pStr):
         from common.constants.Network import Opcodes, Channel, NetworkFlags
         
         for lKey, lChannel in Channel.__members__.items():  
            if lKey == pStr:
                return lChannel.value

         return 0

     def getNameFromId(self, pId):
         from common.constants.Network import Opcodes, Channel, NetworkFlags

         for lKey, lChannel in Channel.__members__.items():  
            if lChannel.value == pId:
                return lKey

         return ''
