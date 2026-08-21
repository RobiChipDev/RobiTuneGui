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
	def __init__( self, opCode: EParseCmd = EParseCmd.Undefined, *args ):
		self.codeNo = opCode
		self.args = list( args )
		self.state = ECodeExecState.WaitExec

		# auxiliary variables
		self.timer = 0
		pass
	pass

class CRobiPlanner():
	# consts and definitions
	MAX_PLAN_STEP = 10

	def __init__( self, mcp: CMcpItf, plannerItvl: int = 0.5 ):
		'''plannerItvl: unit[ msec ]'''
		self.parser = CRobiParser()
		self.script = None
		self.currLineNo = 0
		self.currOpCode = None
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

	def __pushCmd( self, rawOpCode: list ) -> None:
		if len( rawOpCode ) == 1:
			# w/o args
			opCode = COpCode( rawOpCode[ 0 ] )
			pass
		else:
			# w/ args
			opCode = COpCode( rawOpCode[ 0 ], rawOpCode[ 1: ] )
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

	def __runPlanSteps( self ):
		if ( self.cmdQueue.empty() == True ) and self.planState == EPlanState.Idle:
			return

		# get next operation code
		if( self.opCode == None ):
			self.opCode = self.cmdQueue.get()
			self.planState = EPlanState.ExecForward
			pass

		while self.planState != EPlanState.Idle:

			flowCtrl = self.__execOpCode( self.planState, self.opCode )
			match flowCtrl:
				case EPlanFlowCtrl.Wait:
					yield

				case EPlanFlowCtrl.Next:
					if self.cmdQueue.empty() == True:
						self.opCode = None
						self.planState = EPlanState.Idle
						return
					self.opCode = self.cmdQueue.get()
					pass

				case _:
					self.opCode = None
					self.planState = EPlanState.Idle
					pass

			if self.planStepCnt > self.MAX_PLAN_STEP:
				yield
			self.planStepCnt += 1
			pass	
		pass

	def __execOpCode( self, planState: EPlanState, opCode: COpCode ) -> EPlanFlowCtrl:
		if planState == EPlanState.Idle:
			# exception, the planner might be forcely paused
			return EPlanFlowCtrl.Wait
		
		match opCode.execState:
			case ECodeExecState.WaitExec:
				self.__handleEntry( planState, opCode )
				pass

			case ECodeExecState.InExec:
				self.__handleExec( planState, opCode )
				if opCode.state == ECodeExecState.Done:
					return EPlanFlowCtrl.Next
				pass

		# keep current operation code	
		return EPlanFlowCtrl.Idle

	def __handleEntry( self, planState: EPlanState, opCode: COpCode ):
		match opCode.codeNo:
			case EParseCmd.Lin:
				pass

			case EParseCmd.Wait:
				opCode.timer = 0
				opCode.State = ECodeExecState.InExec
				pass

			case EParseCmd.SetReg:
				# SET_REG( regNo, regType, regVal )
				regId = packRegId( opCode.args[ 0 ], EMcpRegType( opCode.args[ 1 ] ) )
				self.mcp.Cmd_SetRegister( regId, opCode.args[ 2 ] )
				opCode.State = ECodeExecState.Done
				pass

			case EParseCmd.Start:
				# START()
				self.mcp.Cmd_StartMotor()
				opCode.State = ECodeExecState.Done
				pass

			case EParseCmd.Stop:
				# STOP()
				self.mcp.Cmd_StopMotor()
				opCode.State = ECodeExecState.Done
				pass

			case EParseCmd.StopRamp:
				# STOP_RAMP()
				self.mcp.Cmd_StopRamp()
				opCode.State = ECodeExecState.Done
				pass

			case EParseCmd.StopStart:
				# STOP_START()
				self.mcp.Cmd_StartStop()
				opCode.State = ECodeExecState.Done
				pass

			case EParseCmd.SpdRamp:
				# SPD_RAMP( TARGET_SPD, DURATION )
				self.mcp.workTick
				pass

			case _:
				opCode.State = ECodeExecState.Done
				pass
		pass

	def __handleExec( self, planState: EPlanState, opCode: COpCode ):
		match opCode.codeNo:
			case EParseCmd.Lin:
				pass

			case EParseCmd.Wait:
				if	opCode.timer >= opCode.args[ 0 ]:
					opCode.execState = ECodeExecState.Done
					return
				opCode.timer += self.planItvl
				pass

			case _:
				opCode.execState = ECodeExecState.Done
				pass
		pass

	pass # end of CRobiPlanner