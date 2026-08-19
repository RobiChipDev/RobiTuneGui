import time
import threading
from AspepItf import *
from McpRegInfo import *
from enum import Enum

################################
# Author: Boyce, RobiChip
# Date: 2026/08/12
# Description:
# MCP protocal "Controller" interface.
# The "Performer" is the device that runs the Motor Control application. 
# The "Controller" is the one that controls and monitors the Performer.
# Data are sent in little-endian order: least significant bits of bytes are transmitted first.
#
# The "Command" service deals with the sending, by the Controller, of commands that are executed by the Performer. 
# After execution, the Performer returns a status possibly preceded by additional data. 
# An example of a command is the START_MOTOR command that instructs the Motor Control application on the Performer side to set a motor under control.
# 
# The "Registry" service formalizes the access, by the Controller, to internal variables and states of the embedded motor control application on the Performer. 
# Registers are used to let the Controller read measurements made by the embedded motor control application, 
# write run time application parameters, or even trigger actions. 
# Examples of registers include the I_A register that references the current measured on phase A, 
# the CONTROL_MODE register used to get and set the control mode of the application or the SPEED_RAMP register that allows the controller to program a speed ramp for a motor, 
# just to name a few.
# 
# The "Datalog" service lets the Controller monitor the changing values of registers in a controlled way. 
# The registers to monitor and the value sampling rate are configurable. 
# This service allows for plotting registers values like an oscilloscope would do with physical signals.
# 
# The "Notification" service provides the Controller with the possibility to be notified when the values of a set of registers change. 
# For instance, it can be used to be notified whenever the STATUS register, that represents the state of the motor control state machine, changes.
#

# MCP response status codes
# The first response code, CMD_OK indicates the successful execution of the preceding command. All other codes indicate an error.
class EMcpRespStatusCode( Enum ):
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

class EMcpState( Enum ):
	Idle = 0
	Config = 1
	Connecting = 2
	Connected = 3
	pass

class CMcpItf():
# constants and definitions
	TICK_INTERVAL = 0.1	# second
	MAX_RXS = 0x3F
	MAX_TXS = 0x7F
	MAX_TXA = 0x7F
	MAX_WAIT_RESP_RETRY = 10

	def __init__( self ):
		self.motorNo = 0
		self.aspepItf = None

		# initialize MCP information container
		self.mcpVer = bytes()

		# initialize a timer to run the ASPEP machine periodically
		self.workTick = None
		pass

	def __del__( self ):
		self.workTick.join()
		pass

# configuration and state query services
	def connect( self, motorNo: int, port: str, baud: int ) -> None:
		self.motorNo = motorNo
		self.aspepItf = CAspepItf( port, baud )
		self.aspepItf.connect( True, self.MAX_RXS, self.MAX_TXS, self.MAX_TXA )
		
		# initialize a timer to run the ASPEP machine periodically
		self.workTick = threading.Thread( target = self.__tick, daemon = True )
		self.workTick.start()
		pass

	def disconnect( self ) -> None:
		pass

	def getAspepState( self ) -> EMcpState:
		if self.aspepItf == None:
			return EMcpState.Idle

		match self.aspepItf.getState():
			case EAspepState.Idle:
				return EMcpState.Idle
			case EAspepState.Conf:
				return EMcpState.Config
			case EAspepState.Connecting:
				return EMcpState.Connecting
			case EAspepState.Connected:
				return EMcpState.Connected
		return EMcpState.Idle

# all the following Cmd functions are blocking
	def Cmd_GetMcpVer( self ) -> tuple[ EMcpRespStatusCode, bytes ]:
		# GET_MCP_VERSION
		# Command payload: 0
		# Response payload: 4 bytes
		# Status code: always CMD_OK
		sendBytes = self.__packCommand( motorNo = self.motorNo, cmdId = 0x0000, payload = b"" )
		statusCode, self.mcpVer = self.__sendRecv( sendBytes )
		return statusCode, self.mcpVer

	def Cmd_SetRegister( self, *args ):
		# Cmd_SetRegister( id1, val1, id2, val2, ..., idN, valN  )
		# SET_REGISTER
		# Command payload: 
		# 	|-2 bytes-|-? bytes--|-2 bytes-|-? bytes--|----|-2 bytes-|-? bytes--|
		# 	|-RegId 1-|-RegVal 1-|-RegId 2-|-RegVal 2-|----|-RegId N-|-RegVal N-|
		# Response payload: 0 (if status code == CMD_OK) / N bytes (if status code == CMD_NOK)
		# Status code: CMD_OK / CMD_NOK
		packedBytes = bytes()
		for i in range( 0, len( args ), 2 ):
			packedByte += args[ i ]
			packedByte += args[ i + 1 ]
			pass
		sendBytes = self.__packCommand( motorNo = self.motorNo, cmdId = 0x0001, payload = packedByte )
		statusCode, respPayload = self.__sendRecv( sendBytes )
		pass

	def Cmd_GetRegister( self, *args ) -> list:
		# Cmd_GetRegister( id1, id2, ..., idN )
		# GET_REGISTER
		# Command payload: 
		# 	|-2 bytes-|-2 bytes-|----|-Nx2 bytes-|
		# 	|-RegId 1-|-RegId 2-|----|-RegId N---|
		# Response payload: 
		# 	|-? bytes--|-? bytes--|----|-? bytes--|
		# 	|-RegVal 1-|-RegVal 2-|----|-RegVal N-|
		# Status code: CMD_OK / error code
		packedBytes = bytes()
		for item in args:
			packedBytes += item
			pass
		sendBytes = self.__packCommand( motorNo = self.motorNo, cmdId = 0x0002, payload = packedBytes )
		statusCode, respPayload = self.__sendRecv( sendBytes )
		if statusCode != EMcpRespStatusCode.Ok:
			return list()

		rtnValList = list()
		byteCount = 0
		isValid = False
		regVal = None
		for i in range( 0, len( args ), 1 ):
			regNo, regType, motorNo = unpackRegId( args[ i ] )
			isValid, byteCount, regVal = decodeRegVal( regType, regNo, respPayload, byteCount )
			if isValid == False:
				break
			rtnValList.append( regVal )
			pass

		return rtnValList

	def Cmd_StartMotor( self ):
		# START_MOTOR
		# Command payload: 0
		# Response payload: 0
		# Status code: CMD_OK / CMD_NOK
		packedBytes = self.__packCommand( motorNo = self.motorNo, cmdId = 0x0003, payload = b"" )
		statusCode, _ = self.__sendRecv( packedBytes )
		pass

	def Cmd_StopMotor( self ):
		# STOP_MOTOR
		# Command payload: 0
		# Response payload: 0
		# Status code: CMD_OK / CMD_NOK
		packedBytes = self.__packCommand( motorNo = self.motorNo, cmdId = 0x0004, payload = b"" )
		statusCode, _ = self.__sendRecv( packedBytes )
		pass

	def Cmd_StopRamp( self ):
		# STOP_RAMP
		# Command payload: 0
		# Response payload: 0
		# Status code: always CMD_OK
		packedBytes = self.__packCommand( motorNo = self.motorNo, cmdId = 0x0005, payload = b"" )
		statusCode, _ = self.__sendRecv( packedBytes )
		pass

	def Cmd_StartStop( self, Motor ):
		# START_STOP
		# Command payload: 0
		# Response payload: 0
		# Status code: CMD_OK / CMD_NOK
		packedBytes = self.__packCommand( motorNo = self.motorNo, cmdId = 0x0006, payload = b"" )
		statusCode, _ = self.__sendRecv( packedBytes )
		pass

	def Cmd_FaultAck( self ):
		# FAULT_ACK
		# Command payload: 0
		# Response payload: 0
		# Status code: always CMD_OK
		packedBytes = self.__packCommand( motorNo = self.motorNo, cmdId = 0x0007, payload = b"" )
		statusCode, _ = self.__sendRecv( packedBytes )
		pass

# private function
	def __tick( self ) -> None:
		nextRun = time.perf_counter()

		while True:
			nextRun += self.TICK_INTERVAL
			sleepTime = nextRun - time.perf_counter()

			self.aspepItf.runStateMachine()
			if sleepTime > 0:
				time.sleep( sleepTime )
			pass
		pass

	def __packCommand( self, motorNo: int, cmdId: int, payload: bytes ) -> bytes:
		""" Pack MCP command

		format:
			|-3 bits-|-13 bits----|-N bytes---------|
			|-Motor#-|-Command ID-|-Command Payload-|
		"""
		binedId = motorNo | ( cmdId << 3 )
		byte0 = binedId & 0xFF
		byte1 = ( binedId >> 8 ) & 0xFF
		packedBytes = bytes( [ byte0, byte1 ] ) + payload
		return packedBytes

	def __sendRecv( self, txPackedBytes: bytes ) -> tuple[ int, bytes ]:
		""" MCP response
					
			format:
				|-N bytes----------|-8 bits------|
				|-Response Payload-|-Status Code-|
		"""
		retryCount = 0
		self.aspepItf.sendRequest( txPackedBytes )
		while ( self.aspepItf.isResponseReady() == False ) and ( retryCount <= self.MAX_WAIT_RESP_RETRY ):
			retryCount += 1
			time.sleep( 0.1 )
			pass

		_, rxPackedBytes = self.aspepItf.readResponse()
		if len( rxPackedBytes ) == 1:
			# only contain 1 status code, no valid payload
			return EMcpRespStatusCode( int.from_bytes( rxPackedBytes ) ), bytes()

		# split status code from the packet
		statusCode = EMcpRespStatusCode( int.from_bytes( rxPackedBytes[ -1: ] ) )
		respPayload = rxPackedBytes[ :-1 ]
		return statusCode, respPayload