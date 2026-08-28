import time
import threading
from enum import Enum
from queue import Queue
from RobiParser import *
from McpItf import CMcpItf
from McpRegInfo import *

class EPlanState( Enum ):
	Idle = 0
	ExecForward = 1
	ExecBackward = 2
	pass

class EPlanFlowCtrl( Enum ):
	Wait = 0
	Next = 1
	Prev = 2
	pass

class ECodeExecState( Enum ):
	WaitExec = 0
	InExec = 1
	Done  = 2
	pass

class COpCode():
	def __init__( self, opCode: EParseCmd = EParseCmd.Undefined, lineNo: int = -1, *args ):
		self.codeNo = opCode
		self.lineNo = lineNo
		self.args = list( args )
		self.state = ECodeExecState.WaitExec

		# auxiliary variables
		self.timer = 0
		pass
	pass

class CRobiPlanner():
	# consts and definitions
	MAX_PLAN_STEP = 10

	def __init__( self, mcp: CMcpItf, plannerItvl: int = 500 ):
		'''
		Args:
			plannerItvl: unit[ msec ]
		'''
		self.parser = CRobiParser()
		self.script = None
		self.currLineNo = 0
		self.opCode = None
		self.cmdQueue = Queue() # thread-safe opcode storage
		self.mcp = mcp # associate motor control interface

		# planner setting
		self.planState = EPlanState.Idle
		self.planStepCnt = 0
		self.planItvl = float( plannerItvl ) * 0.001 # convert to sec: float
		self.planTick = threading.Thread( target = self.__runPlanTick, daemon = True )
		self.planTick.start()
		pass

	def __del__( self ):
		self.planTick.join()
		pass

	def importScript( self, path: str ) -> None:
		with open( path, 'r', encoding = 'utf-8' ) as f:
			self.script = f.read()
			print( self.script )
		pass

	def start( self ) -> None:
		status = self.parser.parse_and_start( self.script )
		while status != EParseState.End:
			# TBD error or step limit handling
			status = self.parser.resume()
			pass

		for item in self.parser.queue:
			self.__pushCmd( item )
			pass
		pass

	def stop( self ) -> None:
		pass

	def getState( self ) -> EPlanState:
		return self.planState

# private functions
	def __pushCmd( self, rawOpCode: list ) -> None:
		'''
		Args:
			rawOpCode(list): |-EParseCmd-|-lineNo-|-(arg list)*-|
		'''
		if len( rawOpCode ) < 2:
			raise ValueError( "OpCode args 數量錯誤" )

		if len( rawOpCode ) == 2:
			# w/o args
			opCode = COpCode( rawOpCode[ 0 ], rawOpCode[ 1 ] )
			pass
		else:
			# w/ args
			opCode = COpCode( rawOpCode[ 0 ], rawOpCode[ 1 ], *rawOpCode[ 2: ] )
			pass
		
		self.cmdQueue.put( opCode )	
		pass

	def __runPlanTick( self ) -> None:
		nextRun = time.perf_counter()
		
		while True:
			nextRun += self.planItvl
			sleepTime = nextRun - time.perf_counter()

			self.planStepCnt = 0
			self.__runPlanSteps()
			if sleepTime > 0:
				time.sleep( sleepTime )
				pass
		pass		

	def __runPlanSteps( self ) -> None:
		if ( self.cmdQueue.empty() == True ) and ( self.planState == EPlanState.Idle ):
			return None

		# get next operation code
		if self.opCode == None:
			self.opCode = self.cmdQueue.get()
			self.planState = EPlanState.ExecForward
			pass

		while self.planState != EPlanState.Idle:

			flowCtrl = self.__execOpCode( self.planState, self.opCode )
			match flowCtrl:
				case EPlanFlowCtrl.Wait:
					return None

				case EPlanFlowCtrl.Next:
					if self.cmdQueue.empty() == True:
						self.opCode = None
						self.planState = EPlanState.Idle
						return None
					self.opCode = self.cmdQueue.get()
					pass

				case _:
					self.opCode = None
					self.planState = EPlanState.Idle
					pass

			if self.planStepCnt > self.MAX_PLAN_STEP:
				return None
			self.planStepCnt += 1
			pass	
		pass

	def __execOpCode( self, planState: EPlanState, opCode: COpCode ) -> EPlanFlowCtrl:
		if planState == EPlanState.Idle:
			# exception, the planner might be forcely paused
			return EPlanFlowCtrl.Wait
		
		match opCode.state:
			case ECodeExecState.WaitExec:
				self.__handleEntry( planState, opCode )
				pass

			case ECodeExecState.InExec:
				self.__handleExec( planState, opCode )
				pass

		# decide flow control based on execution status of the operation code
		return EPlanFlowCtrl.Next if ( opCode.state == ECodeExecState.Done ) else EPlanFlowCtrl.Wait

	def __handleEntry( self, planState: EPlanState, opCode: COpCode ):
		self.currLineNo = opCode.lineNo
		match opCode.codeNo:
			case EParseCmd.Wait:
				opCode.timer = 0
				opCode.state = ECodeExecState.InExec
				pass

			case EParseCmd.SetReg:
				regId = packRegId( opCode.args[ 0 ].regNo, opCode.args[ 0 ].regType, self.mcp.motorNo )
				regVal = encodeRegVal( \
					opCode.args[ 0 ].regNo, \
					opCode.args[ 0 ].regType, \
					opCode.args[ 0 ].regVal )
				self.mcp.Cmd_SetRegister( regId, regVal )
				opCode.state = ECodeExecState.Done
				pass

			case EParseCmd.Start:
				self.mcp.Cmd_StartMotor()
				opCode.state = ECodeExecState.Done
				pass

			case EParseCmd.Stop:
				self.mcp.Cmd_StopMotor()
				opCode.state = ECodeExecState.Done
				pass

			case EParseCmd.StopRamp:
				self.mcp.Cmd_StopRamp()
				opCode.state = ECodeExecState.Done
				pass

			case EParseCmd.StopStart:
				self.mcp.Cmd_StartStop()
				opCode.state = ECodeExecState.Done
				pass

			case EParseCmd.SpdRamp:
				self.mcp.Cmd_SetSpdRamp( opCode.args[ 0 ].spd, opCode.args[ 0 ].duration )
				opCode.state = ECodeExecState.InExec
				pass

			case _:
				opCode.state = ECodeExecState.Done
				pass
		pass

	def __handleExec( self, planState: EPlanState, opCode: COpCode ) -> None:
		match opCode.codeNo:
			case EParseCmd.Wait:
				if opCode.timer >= opCode.args[ 0 ].duration:
					opCode.state = ECodeExecState.Done
					return None
				opCode.timer += self.planItvl
				pass

			case EParseCmd.SpdRamp:
				if self.mcp.fbkSpd >= opCode.args[ 0 ].spd:
					opCode.state = ECodeExecState.Done
					return None

				if ( opCode.timer * 1000.0 ) >= opCode.args[ 0 ].duration:
					opCode.state = ECodeExecState.Done
					return None
				opCode.timer += self.planItvl
				pass

			case _:
				opCode.state = ECodeExecState.Done
				pass
		pass

	pass # end of CRobiPlanner