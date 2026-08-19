import copy
import time
import threading
from enum import Enum
from queue import Queue
from RobiParser import *
from McpItf import CMcpItf

class EPlanState( Enum ):
	Idle = 0
	Exec = 1
	pass

class CRobiPlanner():
	def __init__( self, mcp: CMcpItf, plannerItvl: int ):
		self.parser = CRobiParser()
		self.script = None
		self.currLineNo = 0
		self.cmdQueue = Queue() # thread-safe
		self.mcp = mcp # associate motor control interface

		# planner setting
		self.planState = EPlanState.Idle
		self.opCode = None
		self.planItvl = plannerItvl
		self.planTick = threading.Thread( target = self.__runPlanner, daemon = True )
		self.planTick.start()
		pass

	def __del__( self ):
		self.planTick.join()
		pass

	def importScript( self, path: str ):
		with open( path, 'r', encoding = 'utf-8' ) as f:
			self.script = f.read()
			print( self.script )
		pass

	def start( self ):
		status = self.parser.parse_and_start( self.script )
		while status != EParseState.End:
			for item in self.parser.queue:
				self.cmdQueue.put( item )	
				pass
			status = self.parser.resume()
			pass

		for item in self.parser.queue:
			self.cmdQueue.put( item )	
			pass
		pass

	def __runPlanner( self ) -> None:
		if ( self.cmdQueue.empty() == True ) and self.planState == EPlanState.Idle:
			return

		if( self.opCode == None ):
			self.opCode = self.cmdQueue.get()
			self.__execOpCode( self.opCode )
			pass
	pass

	def __execOpCode( self, opCode: tuple ) -> None:
		
		match opCode[ 0 ]:
			case EParseCmd.Lin:
				pass

			case EParseCmd.Wait:
				self.planTimer = 0
				pass

			case EParseCmd.SetReg:
				self.mcp.Cmd_SetRegister( opCode[ 1 ], opCode[ 2 ], opCode[ 3 ] )
				pass

			case _:
				pass