from websocket.Dependency.websocket_server  import SimpleWebSocketServer, SimpleSSLWebSocketServer

from logging import getLogger
from django.conf import settings
from django.core.wsgi import get_wsgi_application
from threading import Thread, Lock, RLock
from common.utils import SharedVar
from websocket.WebsocketClient import WebsocketClient
from common.ScheduledTask import ScheduledObject
from common.logger import Logger

import time
import sys

class WebsocketServer(SimpleWebSocketServer):

    mServiceAlias = "[Django-WebSocket]"
    mServerThread = None
    mClientStack = {}
    mIdIterator = 0
    mPort = 0

    ######################################################
	##
	##                  Constructor
	##
	######################################################

    def __init__(self, pPort = None, pBindedHost = '', pDisableInit = False):

        if pPort is None:
            pPort = int(settings.WEBSOCKET_DEFAULT_PORT)

        self.mPort = int(pPort)

        if pDisableInit != True:
            SimpleWebSocketServer.__init__(self, pBindedHost, pPort, WebsocketClient ) 

        Logger("websocket").Write( self.mServiceAlias + " -> Init server ")

        self.resetChannels()

    def resetChannels(self):
        Logger("websocket").Write( self.mServiceAlias + " -> Clearing channel data ")

        SharedVar('Core').removePattern('Channel', '*')
        return


    ######################################################
	##
	##            Start Websocket Server
	##
	######################################################

    def start(self):
       
        Logger("websocket").Write( self.mServiceAlias + " -> Start server on port :  " + str(self.mPort))

        # Exec MySQL ping every 30 minutes ( 1800 secs )
        lScheduler = SharedVar("Core").get("Singleton", "Scheduler")
        lScheduledObject = ScheduledObject(self.doPingMySQL, 600) 

        lScheduledObject.isRepeated = True

        lScheduler.PushScheduledFunction(lScheduledObject)
       
        self.mServerThread = Thread(target=self.startThread)
        self.mServerThread.daemon = False
        self.mServerThread.start()

    ######################################################
	##
	##       Private method, use start instead 
	##
	######################################################

    def startThread(self):
        self.serveforever()
        return
        

    ######################################################
	##
	##              Return True or False
	##
	######################################################
    def hasClients(self):
        return leng(self.mClientStack) > 0

    ######################################################
	##
	##       Broadcast message to all Clients
	##
	######################################################
         
    def sendToAll(self, pPacket, pSender):

        for lSocket in self.mClientStack:
            if lSocket.socketId != pSender.socketId:
                lSocket.sendMessage(pPacket)


        return

    ######################################################
	##
	##     Broadcast message to a specific channel
	##
	######################################################

    def sendToChannel(self, pPacket, pSender, pChannel):
        
        from websocket.ChannelHandler.Channel import ChannelHandler

        lChannelHandler = ChannelHandler(pChannel)

        if lChannelHandler.isAlreadyMember(pSender) == False:
            return
       
        for lSocketId in lChannelHandler.getMemberList():
            if lSocketId in self.mClientStack and lSocketId != pSender.socketId:
                self.mClientStack[ lSocketId ].sendMessage(pPacket)

        return

    ######################################################
	##
	##     Broadcast message to a specific inst_id
	##
	######################################################

    def sendToInstId(self, pPacket, pSender, pInstID):
        
        from websocket.ChannelHandler.Channel import ChannelHandler

        for lSocketId in self.mClientStack:
            if self.mClientStack[ lSocketId ].instId == pInstID and lSocketId != pSender.socketId:
                self.mClientStack[ lSocketId ].sendMessage(pPacket)

        return

    ######################################################
	##
	##              On Client Connect !
	##
	######################################################

    def onClientConnect(self, pSocket):
       
        Lock()

        # if server is full
        if len(self.mClientStack) >= settings.WEBSOCKET_SERVER_CAPACITY and settings.WEBSOCKET_SERVER_CAPACITY != 0:
            
            from websocket.Packet import Packet
            from common.constants.Network import Opcodes, Channel, NetworkFlags
            
            lPacket = Packet(opcode=Opcodes.SMSG_SERVER_NOTIFICATION, channel=Channel.GLOBAL)
            lPacket.WriteUint32(NetworkFlags.FLAG_SERVER_IS_FULL)

            pSocket.sendMessage(lPacket.deflate)
            pSocket.close()

            return


        self.mIdIterator += 1
        pSocket.setSocketId(self.mIdIterator)
        self.mClientStack[ pSocket.socketId ] = pSocket

        time.sleep(0.10)

        RLock()

        return

    ######################################################
	##
	##              On Client Disconnect !
	##
	######################################################

    def onClientDisconnect(self, pSocket):
        Logger("websocket").Write(self.mServiceAlias + " -> Client id : " + str(pSocket.socketId) + " disconnected ")
        self.mClientStack.pop(pSocket.socketId)
        return

    @property 
    def clientList(self):
        return self.mClientStack


    ######################################################
	##
	##                  Mysql Ping
	##
	######################################################
    
    def doPingMySQL(self): 

        Logger("websocket").Write(self.mServiceAlias + " -> Exec ping on MySQL ")

        from django import db

        db.close_old_connections()

        from django.db import connections, connection

        connection.close()

        with connection.cursor() as lDBPtr:
            lDBPtr.execute("SELECT 1")
            
        return

class SslWebsocketServer(WebsocketServer, SimpleSSLWebSocketServer):
    def __init__(self, pCertfile, pKeyfile, pPort = None, pBindedHost = ''):

        if pPort is None:
            pPort = int(settings.WEBSOCKET_DEFAULT_PORT)

        WebsocketServer.__init__(self, pPort, pBindedHost, True)
        SimpleSSLWebSocketServer.__init__(self, pBindedHost, pPort, WebsocketClient, pCertfile, pKeyfile)


