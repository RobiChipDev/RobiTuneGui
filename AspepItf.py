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
# ASPEP: (A)synchronous (S)erial (P)acket (E)xchange (P)rotocol
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

# ============================================================
# Controller connection sequence: 
# (refer to runStateMachine & EAspepState)
# 1. Send capability-probe BEACON.
# 2. Receive performer's BEACON.
# 3. Echo performer's BEACON to accept negotiated capabilities.
# 4. Receive final BEACON when supplied by firmware.
# 5. Optional PING.
# ============================================================
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
	Connect = 1		# state transition: Idle -> Conf
	pass

# main interface
class CAspepItf():
# consts and definitions
	CONN_TIMEOUT = 10.0		# 10 seconds
	SYNC_WAIT_TIMEOUT = 1.0	# 1 second
	RECV_BUF_SIZE = 100		# 100 bytes

# public functions
	def __init__( self, portNum, baudrate ):
		# init serial interface
		self.comm = serial.Serial()
		self.comm.port = portNum
		self.comm.baudrate = baudrate
		self.comm.bytesize = serial.EIGHTBITS
		self.comm.parity = serial.PARITY_NONE
		self.comm.stopbits = serial.STOPBITS_ONE
		self.comm.timeout = 1
		try:
			self.comm.open()
			time.sleep( 0.5 )
			self.comm.reset_input_buffer()
			self.comm.reset_output_buffer()
			pass

		except serial.SerialException as e:
			print( f"Serial error occured: { e }" )
			pass

		# init state machine variables
		self.role = EAspepRole.Ctrl
		self.state = EAspepState.Idle
		self.syncState = EAspepSyncState.Idle
		self.req = EAspepReq.Non

		# init empty BEACON/PING/REQUEST packet
		self.beacon = CPktDscrpt( EAspepPktType.Beacon, 0, 0, 0, 0, 0 )
		self.ping = CPktDscrpt( EAspepPktType.Ping, 0, 0, 0, 0 )
		self.request = CPktDscrpt( EAspepPktType.Request )
		self.response = CPktDscrpt( EAspepPktType.Response )

		# init timing related variables
		self.currTick = time.perf_counter() # float in second
		self.lastTick = self.currTick		# float in second
		self.timer = 0						# float in second
		self.subTimer = 0					# float in second
		self.timBeacon = 0
		self.timPing = 0

		# init buffer for decoder
		self.decodeBuf = bytes()
		self.decodeBufLen = 0
		pass

	def connect( self, enableCrc: bool, rxsMax, txsMax, txaMax, timBeacon: float = 1.0, timPing: float = 1.0 ) -> bool:
		"""Establish connection
		Args:
			timBeacon: unit( second )
			timPing: unit( second )
		Returns:
			Is the connection process initiated successfully?
		"""
		if self.comm.is_open == False:
			return False
		
		self.beacon.set( EAspepPktType.Beacon, 0, enableCrc, rxsMax, txsMax, txaMax )
		self.timBeacon = timBeacon
		self.timPing = timPing
		self.req = EAspepReq.Connect
		return True

	def getState( self ) -> EAspepState:
		return self.state

	def sendRequest( self, payload: bytes ) -> bool:
		if self.state != EAspepState.Connected:
			return False

		# Force the sync status to revert to the “Request”, 
		# and discard response that have not yet been retrieved.
		self.request.set( EAspepPktType.Request, len( payload ), payload )
		self.syncState = EAspepSyncState.RequestInBuf
		return True

	def readResponse( self ) -> tuple[ bool, bytes ]:
		if self.isResponseReady() == False:
			return False, bytes()

		self.syncState = EAspepSyncState.Idle
		return True, self.response.payload

	def isResponseReady( self ) -> bool:
		if self.state != EAspepState.Connected:
			return False

		return self.syncState == EAspepSyncState.ResponseInBuf
		
	def runStateMachine( self ):
		# update the time tick
		self.lastTick = self.currTick
		self.currTick = time.perf_counter()
		self.timer += self.currTick - self.lastTick
		self.subTimer += self.currTick - self.lastTick
		
		# handle recv pkgs
		recvPkt = self.__runDecodeMchn()

		# The "Synchronous" channel has priority over the "Control" channel that has priority over the "Asynchronous" one. 
		# This means that if several packets are ready for transmission on either side of a connection, 
		# when the serial link is available (not busy), the packet belonging to the channel with the highest priority will be sent first.

		# run state machine after recv pkgs decoded
		match self.state:
			case EAspepState.Idle:
				if self.req == EAspepReq.Connect:
					# sending master's capabilities
					packedBytes = self.beacon.encode()
					self.comm.write( packedBytes )

					self.timer = 0
					self.subTimer = 0
					self.req = EAspepReq.Non
					self.state = EAspepState.Conf
					return
				pass

			case EAspepState.Conf:
				if self.timer > self.CONN_TIMEOUT:
					# timeout condition
					self.timer = 0
					self.subTimer = 0
					self.state = EAspepState.Idle
					return

				if ( recvPkt.type == EAspepPktType.Undefine ) and ( self.subTimer > self.timBeacon ):
					# no response from performer, send a repetion of beacon
					self.subTimer = 0
					packedBytes = self.beacon.encode()
					self.comm.write( packedBytes )
					return	

				if recvPkt.type == EAspepPktType.Beacon:
					if ( self.beacon == recvPkt ) == True:
						# both Controller and Performer acknowledge capability
						packedBytes = self.ping.encode()
						self.comm.write( packedBytes )
										
						self.timer = 0
						self.subTimer = 0
						self.state = EAspepState.Connecting
						return
					else:
						# the capability on both side is differ, merge the beacon
						self.beacon = copy.copy( recvPkt )
						packedBytes = self.beacon.encode()
						self.comm.write( packedBytes )

						self.subTimer = 0
						self.state = EAspepState.Conf
						return
				pass

			case EAspepState.Connecting:
				if self.timer > self.CONN_TIMEOUT:
					# timeout condition
					self.timer = 0
					self.subTimer = 0
					self.req = EAspepReq.Non
					self.state = EAspepState.Idle
					return

				if ( recvPkt.type == EAspepPktType.Undefine ) and ( self.subTimer > self.timPing ):
					# no response from performer, send a repetion of beacon
					self.subTimer = 0
					packedBytes = self.ping.encode()
					self.comm.write( packedBytes )
					return	

				if recvPkt.type == EAspepPktType.Ping:
					if ( recvPkt.c != 0 ) == True:
						self.timer = 0
						self.subTimer = 0
						self.req = EAspepReq.Non
						self.state = EAspepState.Connected
						return
					pass
				pass

			case EAspepState.Connected:
				if self.syncState == EAspepSyncState.RequestInBuf:
					fPacket, _ = self.request.encode( self.beacon.enCrc )
					self.comm.write( fPacket )
					self.syncState = EAspepSyncState.IntraPause
					return

				if self.syncState == EAspepSyncState.IntraPause:
					_, sPacket = self.request.encode( self.beacon.enCrc )
					self.comm.write( sPacket )
					self.syncState = EAspepSyncState.WaitResponse
					return

				if self.syncState == EAspepSyncState.WaitResponse:
					if ( recvPkt.type == EAspepPktType.Undefine ) and ( self.subTimer > self.SYNC_WAIT_TIMEOUT ):
						self.subTimer = 0
						self.syncState = EAspepSyncState.Idle
						return

					if recvPkt.type != EAspepPktType.Response:
						return

					self.response = copy.copy( recvPkt )
					self.syncState = EAspepSyncState.ResponseInBuf
					return
				pass

			case _:
				# state out of range handling
				self.timer = 0
				self.subTimer = 0
				self.req = EAspepReq.Non
				self.state = EAspepState.Idle
				pass
		pass

# private functions
	def __runDecodeMchn( self ) -> CPktDscrpt:
		dscrpt = CPktDscrpt( EAspepPktType.Undefine )

		if self.comm.is_open == False:
			return dscrpt
		
		self.decodeBuf = self.comm.read_all()
		self.decodeBufLen = len( self.decodeBuf )
		if self.decodeBufLen == 0:
			return dscrpt
		
		dscrpt.decode( self.decodeBufLen, self.decodeBuf )
		return dscrpt