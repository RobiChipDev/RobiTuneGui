from SerialItf import SerialItf
from AspepAux import EAspepPktType, PktDscrpt
from enum import Enum
import struct

################################
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

# MCP response codes
# The first response code, CMD_OK indicates the successful execution of the preceding command. All other codes indicate an error.
class EAspepMcpResp( Enum ):
	Ok = 0x00					# CMD_OK execution of the command was successful
	Nok = 0x01					# CMD_NOK xecution of the command failed
	Unknown = 0x02				# CMD_UNKNOWN command is unknow
	Unused = 0x03				# reserved
	RoReg = 0x04				# RO_REG read-only register
	UnknownReg = 0x05			# UNKNOWN_REG target register is unknown
	StrFormat = 0x06			# STRING_FORMAT the format of a text string in the command payload is wrong
	BadDataType = 0x07			# BAD_DATA_TYPE the type of a register in the command payload is wrong
	NoTxSyncSpace = 0x08		# NO_TXSYNC_SPACE the size of the response to the command exceeds the maximum payload size
	NoTxAsyncSpace = 0x09		# NO_TXASYNC_SPACE the number of signals requested for the datalog exceeds the maximum supprted by the performer
	WrongStructFormat = 0x0A	# WRONG_STRUCT_FORMAT the reported size of a structure transmitted in the command does not match its actual size
	WoReg = 0x0B				# WO_REG target register is write only. Its value cannot be read
	Unused2 = 0x0C				# reserved
	UserCmdNotImpl = 0x0D		# USER_CMD_NOT_IMPL command is a non implemented user command
	pass

class EAspepRegType( Enum ):
	Reserved = 0
	Bit8 = 1
	Bit16 = 2
	Bit32 = 3
	Text = 4
	RawStruct = 5
	Reserved2 = 6
	Reserved3 = 7
	pass

class EAspepErrCode( Enum ):
	BadPktType = 1
	BadPktSize = 2
	BadHeader = 4
	BadPayloadCrc = 5
	pass

class EAspepState( Enum ):
	Idle = 0
	Conf = 1
	Connecting = 2
	Connected = 3
	Recovery = 4
	pass

class EAspepSubState( Enum ):
	Idle = 0
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
class AspepItf():
# consts and definitions
	RESP_TIMEOUT = 10000
	RECV_BUF_SIZE = 100

# public functions
	def __init__( self, port ):
		# init serial interface
		self.comm = SerialItf()

		# init state machine variables
		self.role = EAspepRole.Ctrl
		self.state = EAspepState.Idle
		self.timer = 0
		self.req = EAspepReq.Non

		# init beacon packet
		self.beacon = PktDscrpt().setBeacon( enCrc = True, rxsMax = 0, txsMax = 0, txaMax = 0 )

		# init ping packet
		self.ping = PktDscrpt().setPing( c = 0, n = 0, LLID = 0, pktNum = 0 )

		# init timing related variables
		self.tBeacon = 0
		self.tPing = 0
		self.tSyncWaitAck = 0

		# init receiver
		self.recvLen = 0
		self.recvBuf = bytearray( self.RECV_BUF_SIZE )
		pass

	def open( self, enableCrc, rxsMax, txsMax, txaMax, tBeacon = 1000, tPing = 1000 ):
		self.req = EAspepReq.Conf
		self.beacon.enCrc = enableCrc
		self.beacon.rxsMax = rxsMax
		self.beacon.txsMax = txsMax
		self.beacon.txaMax = txaMax
		self.tBeacon = tBeacon
		self.tPing = tPing
		pass

	def Cmd_GetMcpVer( self ):
		# GET_MCP_VERSION
		CmdId = 0x0000
		PayloadLen = 0
		pass

	def Cmd_SetRegister( self, RegNum ):
		# SET_REGISTER
		CmdId = 0x0001
		PayloadLen = 0
		pass

	def Cmd_StartMotor( self, Motor ):
		# START_MOTOR
		CmdId = 0x0003
		PayloadLen = 0
		pass

	def Cmd_StopMotor( self, Motor ):
		# STOP_MOTOR
		CmdId = 0x0004
		PayloadLen = 0
		pass

	def Cmd_StopRamp( self, Motor ):
		# STOP_RAMP
		CmdId = 0.0005
		PayloadLen = 0
		pass

	def Cmd_StartStop( self, Motor ):
		# START_STOP
		CmdId = 0x0006
		PayloadLen = 0
		pass

	def RunStateMachine( self ):
		# handle recv pkgs
		self.__runDecodeMchn()

		# The "Synchronous" channel has priority over the "Control" channel that has priority over the "Asynchronous" one. 
		# This means that if several packets are ready for transmission on either side of a connection, 
		# when the serial link is available (not busy), the packet belonging to the channel with the highest priority will be sent first.

		# run state machine after recv pkgs decoded
		match self.state:
			case EAspepState.Idle:
				if self.req == EAspepReq.Conf:
					# start handshake to establish connection
					self.__transit( EAspepState.Conf )
				pass

			case EAspepState.Conf:
				if self.req == EAspepReq.Connecting:
					# BEACON acknowledged by both controller and performer
					self.__transit( EAspepState.Connecting )
					pass

				elif self.req == EAspepReq.Conf:
					# merge BEACON info. from performer
					self.__transit( EAspepState.Conf )
					pass

				else:
					self.timer += 1000
					if self.timer > self.RESP_TIMEOUT:
						self.__transit( EAspepState.Idle )
						pass
				pass

			case EAspepState.Connecting:
				if self.req == EAspepReq.Connected:
					self.__transit( EAspepState.Connected )
					pass

				else:
					self.timer += 1000
					if self.timer > self.RESP_TIMEOUT:
						self.__transit( EAspepState.Idle )
						pass
				pass

			case EAspepState.Connected:
				self.__runSubRoutine()
				pass

			case _:
				self.state = EAspepState.Idle
				pass
		pass

# private functions
	def __runDecodeMchn( self ):
		self.recvLen = self.comm.read()
		if self.recvLen == 0:
			return
		
		dscrpt = PktDscrpt( self.recvLen, self.recvBuf )
		match dscrpt.type:
			case EAspepPktType.Beacon:
				if ( self.beacon == dscrpt ) == True:
					self.req = EAspepReq.Connecting
				else:
					self.beacon = dscrpt
					self.req = EAspepReq.Conf
				pass

			case EAspepPktType.Ping:
				if ( dscrpt.c != 0 ) == True:
					self.req = EAspepReq.Connected
				pass

			case EAspepPktType.Error:
				pass

			case EAspepPktType.Async:
				pass

			case EAspepPktType.Response:
				pass

			case _:
				pass
		pass

	def __runSubRoutine( self ):
		if self.recvLen == 0:
			
			return
		pass

	def __transit( self, targetState ):
		self.req = EAspepReq.Non
		self.timer = 0

		match targetState:
			case EAspepState.Idle:
				self.state = EAspepState.Idle

			case EAspepState.Conf:
				self.beacon.setBeacon( self.enCrc, self.rxsMax, self.txsMax, self.txaMax )
				buf = self.beacon.encode()
				self.state = EAspepState.Conf

			case EAspepState.Connecting:
				self.ping.setPing( 0, 0, 0, 0 )
				buf = self.ping.encode()
				self.state = EAspepState.Connecting

			case EAspepState.Connected:
				self.state = EAspepState.Connected

			case _:
				raise ValueError( "unexpected target state" )

		if len( buf ) > 0:	
			self.comm.write( buf )
		pass

	def __formatHeader():
		# total 4 bytes
		# |-4 bit--|-24 bit--|-4 bit-|
		# |--Type--|-content-|-CRCH--|
		# CRC: CCITT-G.704 X^4 + X + 1

		pass

	def __formatPayload():
		# |-Payload-|-16 bit-|
		# |-Payload-|-CRC----|
		# CRC: CCITT-X.25 X^6 + X^12 + X^5 + 1
		pass

	def __send( self, Motor, CmdId, Payload ):
		BinedId = ( Motor << 13 ) | CmdId
		PackedData = struct.pack( 'H', BinedId, Payload )
		pass

	def __read( self ):
		pass