import sys
from enum import Enum
from PyQt6 import QtCore
from PyQt6 import QtWidgets
from McpItf import CMcpItf, EMcpRespStatusCode, EMcpState

# constants and definitions
TEXT_CONNECT = "Connect"
TEXT_DISCONNECT = "Disconnect"

class EGuiState( Enum ):
	Idle = 0
	Connecting = 1
	Connected = 2
	pass

class CRobiGui():

	def __init__( self ):
		# init widgets
		self.app = QtWidgets.QApplication( sys.argv )
		
		self.window = QtWidgets.QMainWindow()
		self.window.setWindowTitle( 'RobiTune' )
		self.window.resize( 400, 300 )

		self.lowFreqTick = QtCore.QTimer( self.window )
		self.lowFreqTick.timeout.connect( self.__lowFreqTick )
		self.lowFreqTick.start( 1000 )

		self.lblConnState = QtWidgets.QLabel( "State: Idle", self.window )
		self.lblConnState.move( 200, 200 )

		self.lblMcpVer = QtWidgets.QLabel( "", self.window )
		self.lblMcpVer.move( 200, 250 )
		
		self.btnConnect = QtWidgets.QPushButton( self.window )
		self.btnConnect.setText( TEXT_CONNECT )
		self.btnConnect.setGeometry( 0, 0, 100, 30 )
		self.btnConnect.clicked.connect( self.__btnConnectClick )
	
		self.tBoxPort = QtWidgets.QLineEdit( self.window )
		self.tBoxPort.setText( "COM4" )
		self.tBoxPort.setPlaceholderText( "COM" )
		self.tBoxPort.resize( 100, 30 )
		self.tBoxPort.move( 100, 0 )
		
		self.tBoxBaud = QtWidgets.QLineEdit( self.window )
		self.tBoxBaud.setText( "1843200" )
		self.tBoxBaud.setPlaceholderText( "Baudrate" )
		self.tBoxBaud.resize( 100, 30 )
		self.tBoxBaud.move( 200, 0 )

		# init Motor Control Protocal
		self.state = EGuiState.Idle
		self.mcp = CMcpItf()
		pass

	def exec( self ) -> None:
		self.window.show()
		self.app.exec()
		pass

# interaction events
	def __btnConnectClick( self ) -> None:
		if self.btnConnect.text() == TEXT_CONNECT:
			self.btnConnect.setText( TEXT_DISCONNECT )
			port = self.tBoxPort.text()
			baud = int( self.tBoxBaud.text() )
			self.mcp.connect( 1, self.tBoxPort.text(), self.tBoxBaud.text() )
			self.state = EGuiState.Connecting
			pass
		else:
			self.btnConnect.setText( TEXT_CONNECT )
			self.mcp.disconnect()
			pass
		pass

# tick (timer) events
	def __lowFreqTick( self ) -> None:
		if self.state == EGuiState.Connecting:
			match self.mcp.getAspepState():
				case EMcpState.Idle:
					self.lblConnState.setText( f"State: Idle" )
					pass
				case EMcpState.Config:
					self.lblConnState.setText( f"State: Configuration" )
					pass
				case EMcpState.Connecting:
					self.lblConnState.setText( f"State: Connecting" )
					pass
				case EMcpState.Connected:
					self.lblConnState.setText( f"State: Connected" )
					self.state = EGuiState.Connected

					_, ver = self.mcp.Cmd_GetMcpVer()
					self.lblMcpVer.setText( f"MCP ver.{ ver }" )
					pass

		pass