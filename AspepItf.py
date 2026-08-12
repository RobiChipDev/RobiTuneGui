import time
import copy
import serial
from AspepCodec import EAspepPktType, CPktDscrpt
from enum import Enum
import struct

################################
# Author: Boyce, RobiChip
# Date: 2026/08/12
# Description:
# The transport layers are protocols on which MCP relies to transport its messages between the Controller and the Performer. 
# Their task is to adapt MCP communication to the physical link being used to transport it.
#
# Communication with ASPEP involves two Hosts, a Controller and a Performer, that exchange Packets.
#
# The protocols of the Transport Layers provide at least two channels that are multiplexed over the physical link: 
# a Synchronous channel and an asynchronous channel. 
# The Synchronous channel is used by MCP to transport the messages of the command service. 
# The Asynchronous channel is used by MCP to transport the messages of the Datalog and Notification services.
#

################################
# enumeration

class EAspepRole( Enum ):
	Ctrl = 0	# controller
	Perf = 1	# performer
	pass

class EAspepChannel( Enum ):
	Sync = 0	# controller sends requests to which the performer responds
	Async = 1	# unidirectional. performer sends ASYNC packets from performer to controller
	Ctrl = 2	# is used to establish and manage the connection
	pass

class EAspepErrCode( Enum ):
	BadPktType = 1
	BadPktSize = 2
	BadHeader = 4
	BadPayloadCrc = 5
	pass

class EAspepState( Enum ):
	Idle = 0
	Conf = 1		# ASPEP Connection Procedure
	Connecting = 2	# ASPEP Connection Procedure
	Connected = 3	# ASPEP Synchronous Transaction
	Recovery = 4
	pass

class EAspepSyncState( Enum ):
	Idle = 0
	RequestInBuf = 1
	IntraPause = 2		# REQUEST header was sent, and an in-frame pause was inserted.
	WaitResponse = 3
	ResponseInBuf = 4
	pass

class EAspepReq( Enum ):
	Non = 0			# request is empty
	Conf = 1		# configuration
	Connecting = 2	# start connection
	Connected = 3	# firm connection is established
	Recovery = 4	#
	pass

# auxiliary object
class AspepReg():
	def __init__( self, Id, Type, Motor ):
		
		pass

# main interface
class CAspepItf():
# consts and definitions
	CONN_TIMEOUT = 10000
	RECV_BUF_SIZE = 100

# public functions
	def __init__( self, portNum ):
		# init serial interface
		self.comm = serial.Serial( \
			port = portNum, \
			baudrate = 9600, \
			bytesize = serial.EIGHTBITS, \
            parity = serial.PARITY_NONE, \
            stopbits = serial.STOPBITS_ONE, \
            timeout = 1 )
		time.sleep( 0.05 )
		self.comm.reset_input_buffer()
		self.comm.reset_output_buffer()

		# init state machine variables
		self.role = EAspepRole.Ctrl
		self.state = EAspepState.Idle
		self.syncState = EAspepSyncState.Idle
		self.timer = 0
		self.req = EAspepReq.Non

		# init empty BEACON/PING/REQUEST packet
		self.beacon = CPktDscrpt( EAspepPktType.Beacon, 0, 0, 0, 0, 0 )
		self.ping = CPktDscrpt( EAspepPktType.Ping, 0, 0, 0, 0 )
		self.request = CPktDscrpt( EAspepPktType.Request )
		self.response = CPktDscrpt( EAspepPktType.Response )

		# init timing related variables
		self.timBeacon = 0
		self.timPing = 0
		self.tSyncWaitAck = 0
		pass

	def connect( self, enableCrc, rxsMax, txsMax, txaMax, timBeacon = 1000, timPing = 1000 ):
		self.beacon.set( EAspepPktType.Beacon, 0, enableCrc, rxsMax, txsMax, txaMax )
		self.timBeacon = timBeacon
		self.timPing = timPing
		self.req = EAspepReq.Conf
		pass

	def sendRequest( self, payload: bytes ) -> bool:
		if self.state != EAspepState.Connected:
			return False

		self.request.set( EAspepPktType.Request, len( payload ), payload )
		self.syncState = EAspepSyncState.RequestInBuf
		return True

	def readResponse( self ) -> tuple[ bool, bytes ]:
		if self.isResponseReady() == False:
			return False

		self.syncState = EAspepSyncState.Idle
		return True, self.response.payload

	def isResponseReady( self ) -> bool:
		if self.state != EAspepState.Connected:
			return False

		return self.syncState == EAspepSyncState.ResponseInBuf
		
	def runStateMachine( self ):
		# handle recv pkgs
		recvPkt = self.__runDecodeMchn()

		# The "Synchronous" channel has priority over the "Control" channel that has priority over the "Asynchronous" one. 
		# This means that if several packets are ready for transmission on either side of a connection, 
		# when the serial link is available (not busy), the packet belonging to the channel with the highest priority will be sent first.

		# run state machine after recv pkgs decoded
		match self.state:
			case EAspepState.Idle:
				if self.req == EAspepReq.Conf:
					# sending master's capabilities
					packedByte = self.beacon.encode()
					self.comm.write( packedByte )

					self.timer = 0
					self.req = EAspepReq.Non
					self.state = EAspepState.Conf
					return

				pass

			case EAspepState.Conf:
				self.timer += 1000
				if self.timer > self.CONN_TIMEOUT:
					# timeout condition
					self.timer = 0
					self.req = EAspepReq.Non
					self.state = EAspepState.Idle
					return

				if ( recvPkt.type == EAspepPktType.Undefine ) and ( self.timer > self.timBeacon ):
					# no response from performer, send a repetion of beacon
					packedByte = self.beacon.encode()
					self.comm.write( packedByte )
					return	

				if recvPkt.type == EAspepPktType.Beacon:
					if ( self.beacon == recvPkt ) == True:
						# both Controller and Performer acknowledge capability
						packedByte = self.ping.encode()
						self.comm.write( packedByte )
										
						self.timer = 0
						self.req = EAspepReq.Non
						self.state = EAspepState.Connecting
						return
					else:
						# the capability on both side is differ, merge the beacon
						self.beacon = copy.copy( recvPkt )
						packedByte = self.beacon.encode()
						self.comm.write( packedByte )
										
						self.timer = 0
						self.req = EAspepReq.Non
						self.state = EAspepState.Conf
						return
				pass

			case EAspepState.Connecting:
				self.timer += 1000
				if self.timer > self.CONN_TIMEOUT:
					# timeout condition
					self.timer = 0
					self.req = EAspepReq.Non
					self.state = EAspepState.Idle
					return

				if ( recvPkt.type == EAspepPktType.Undefine ) and ( self.timer > self.timPing ):
					# no response from performer, send a repetion of beacon
					packedByte = self.ping.encode()
					self.comm.write( packedByte )
					return	

				if recvPkt.type == EAspepPktType.Ping:
					if ( recvPkt.c != 0 ) == True:
						self.timer = 0
						self.req = EAspepReq.Non
						self.state = EAspepState.Connected
						return
					pass
				pass

			case EAspepState.Connected:
				if self.syncState == EAspepSyncState.RequestInBuf:
					fPacket, _ = self.request.encode()
					self.comm.write( fPacket )
					self.syncState = EAspepSyncState.IntraPause
					return

				if self.syncState == EAspepSyncState.IntraPause:
					_, sPacket = self.request.encode()
					self.comm.write( sPacket )
					self.syncState = EAspepSyncState.WaitResponse
					return

				if self.syncState == EAspepSyncState.WaitResponse:
					if recvPkt.type != EAspepPktType.Response:
						return

					self.response = copy.copy( recvPkt )
					self.syncState = EAspepSyncState.ResponseInBuf
					return
				
				pass

			case _:
				# state out of range handling
				self.state = EAspepState.Idle
				pass
		pass

# private functions
	def __runDecodeMchn( self ) -> CPktDscrpt:
		dscrpt = CPktDscrpt()
		self.recvLen = self.comm.read()
		if self.recvLen == 0:
			return dscrpt
		
		dscrpt.decode( self.recvLen, self.recvBuf )
		return dscrpt