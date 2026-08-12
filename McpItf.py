import time
import threading
import struct
from AspepItf import CAspepItf
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

# MCP register type
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

class CMcpItf():
# constants and definitions
	TICK_INTERVAL = 0.1	# second

	def __init__( self, motorId ):
		self.motorId = motorId
		self.aspepItf = CAspepItf( "COM3" )
		self.aspepItf.connect()

		# initialize a timer to run the ASPEP machine periodically
		self.tickStopSignal = threading.Event()
		self.workTick = threading.Thread( target = self.__Tick, args = ( self.tickStopSignal ) )
		self.workTick.start()
		pass

	def __del__( self ):
		self.tickStopSignal.set()
		self.workTick.join()
		pass

################################
# MCP Command format
# |-3 bits-|-13 bits----|-N bytes---------|
# |-Motor#-|-Command ID-|-Command Payload-|
#
# MCP Response format
# |-N bytes----------|-8 bits------|
# |-Response Payload-|-Status Code-|
#
# all the following Cmd functions are blocking

	def Cmd_GetMcpVer( self ):
		# GET_MCP_VERSION
		# Command payload: 0
		# Response payload: 4 bytes
		# Status code: always CMD_OK
		packedBytes = self.__packCommand( motorId = self.motorId, cmdId = 0x0000, payload = b"" )
		self.aspepItf.sendRequest( packedBytes )
		while self.aspepItf.isResponseReady() == False:
			time.sleep( 0.1 )
			pass

		_, McpVer = self.aspepItf.readResponse()
		pass

	def Cmd_SetRegister( self, RegNum ):
		# SET_REGISTER
		# Command payload: 
		# 	|-2 bytes-|-2 bytes-|-Nx2 bytes-|
		# 	|-RegId 1-|-RegId 2-|-RegId 2+N-|
		# Response payload: 
		# 	|-10 bits----|-3 bits----|-3 bits-|-2 bytes--|-M bytes-|
		# 	|-Identifier-|-Data Type-|-Motor#-|-Buf Size-|-Buf-----|
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
	pass

# private function
	def __Tick( self, stopEvent ):
		nextRun = time.perf_counter()

		while not stopEvent.is_set():
			nextRun += self.TICK_INTERVAL
			sleepTime = nextRun - time.perf_counter()

			self.aspepItf.runStateMachine()
			if sleepTime > 0:
				time.sleep( sleepTime )

			pass

		pass

	def __packCommand( self, motorId, cmdId, payload ) -> bytes:
		binedId = ( motorId << 13 ) | cmdId
		packedData = struct.pack( 'H', binedId, payload )
		return packedData