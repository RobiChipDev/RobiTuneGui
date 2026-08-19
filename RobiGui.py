import sys
from enum import Enum
from PyQt6 import QtCore
from PyQt6 import QtWidgets
from McpItf import CMcpItf, EMcpRespStatusCode, EMcpState
from McpRegInfo import *

# constants and definitions
TEXT_CONNECT = "Connect"
TEXT_DISCONNECT = "Disconnect"

class EGuiState( Enum ):
	Idle = 0
	Connecting = 1
	Connected = 2
	pass

class EGuiRegTypeTxt( Enum ):
	BIT8 = 'Bit8'
	BIT16 = 'Bit16'
	BIT32 = 'Bit32'
	STR = 'Str'
	RAW = 'RawStruct'
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

		self.tBoxMotorNo = QtWidgets.QLineEdit( self.window )
		self.tBoxMotorNo.setText( "1" )
		self.tBoxMotorNo.setPlaceholderText( "MotorNo" )
		self.tBoxMotorNo.resize( 100, 30 )
		self.tBoxMotorNo.move( 300, 0 )
	
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

		self.tBoxVBus = QtWidgets.QLineEdit( self.window )
		self.tBoxVBus.setText( "0" )
		self.tBoxVBus.setPlaceholderText( "VBus" )
		self.tBoxVBus.resize( 100, 30 )
		self.tBoxVBus.move( 10, 120 )

		self.tBoxTemp = QtWidgets.QLineEdit( self.window )
		self.tBoxTemp.setText( "0" )
		self.tBoxTemp.setPlaceholderText( "VBus" )
		self.tBoxTemp.resize( 100, 30 )
		self.tBoxTemp.move( 110, 120 )

		# register set / get interface
		self.ComBoxRegType = QtWidgets.QComboBox( self.window )
		self.ComBoxRegType.addItems( [ \
			EGuiRegTypeTxt.BIT8.value, EGuiRegTypeTxt.BIT16.value, EGuiRegTypeTxt.BIT32.value, \
			EGuiRegTypeTxt.STR.value, EGuiRegTypeTxt.RAW.value ] )
		self.ComBoxRegType.move( 100, 50 )

		self.tBoxRegNo = QtWidgets.QLineEdit( self.window )
		self.tBoxRegNo.setText( "0x001" )
		self.tBoxRegNo.setPlaceholderText( "Addr." )
		self.tBoxRegNo.resize( 100, 30 )
		self.tBoxRegNo.move( 200, 50 )

		self.tBoxRegVal = QtWidgets.QLineEdit( self.window )
		self.tBoxRegVal.setText( "0x000" )
		self.tBoxRegVal.setPlaceholderText( "Val." )
		self.tBoxRegVal.resize( 200, 30 )
		self.tBoxRegVal.move( 100, 80 )

		self.btnGetReg = QtWidgets.QPushButton( self.window )
		self.btnGetReg.setText( "GetReg" )
		self.btnGetReg.setGeometry( 0, 50, 100, 30 )
		self.btnGetReg.clicked.connect( self.__btnGetRegClick )

		self.btnSetReg = QtWidgets.QPushButton( self.window )
		self.btnSetReg.setText( "SetReg" )
		self.btnSetReg.setGeometry( 0, 80, 100, 30 )
		self.btnSetReg.clicked.connect( self.__btnSetRegClick )

		# init Motor Control Protocal
		self.state = EGuiState.Idle
		self.mcp = CMcpItf()

		# prepare register identifiers for update routine
		self.regUpdRoutine = ( \
			packRegId( 22,	EMcpRegType.Bit16, 1 ), # VBUS \
			packRegId( 23,	EMcpRegType.Bit16, 1 ), # TEMP \
			packRegId( 109,	EMcpRegType.Bit32, 1 ), # POWER \
			) 
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

	def __btnGetRegClick( self ) -> None:
		if self.state == EGuiState.Idle:
			return

		match self.ComBoxRegType.currentText():
			case EGuiRegTypeTxt.BIT8.value:
				regType = EMcpRegType.Bit8
				pass
			case EGuiRegTypeTxt.BIT16.value:
				regType = EMcpRegType.Bit16
				pass
			case EGuiRegTypeTxt.BIT32.value:
				regType = EMcpRegType.Bit32
				pass
			case EGuiRegTypeTxt.STR.value:
				regType = EMcpRegType.Str
				pass
			case EGuiRegTypeTxt.RAW.value:
				regType = EMcpRegType.RawStruct
				pass

		regId = packRegId( int( self.tBoxRegNo.text(), 0 ), regType, 1 )
		rtnValList = self.mcp.Cmd_GetRegister( regId )
		if len( rtnValList ) == 0:
			return
		self.tBoxRegVal.setText( str( rtnValList[ 0 ] ) )
		pass

	def __btnSetRegClick( self ) -> None:
		if self.state == EGuiState.Idle:
			return

		match self.ComBoxRegType.currentText():
			case EGuiRegTypeTxt.BIT8.value:
				regType = EMcpRegType.Bit8
				pass
			case EGuiRegTypeTxt.BIT16.value:
				regType = EMcpRegType.Bit16
				pass
			case EGuiRegTypeTxt.BIT32.value:
				regType = EMcpRegType.Bit32
				pass
			case EGuiRegTypeTxt.STR.value:
				regType = EMcpRegType.Str
				pass
			case EGuiRegTypeTxt.RAW.value:
				regType = EMcpRegType.RawStruct
				pass

		regId = packRegId( int( self.tBoxRegNo.text(), 0 ), regType, 1 )
		regVal = int( self.tBoxRegVal.text(), 0 )
		rtnValList = self.mcp.Cmd_SetRegister( regId, regVal )
		pass

# tick (timer) events
	def __lowFreqTick( self ) -> None:
		if self.state == EGuiState.Idle:
			return
		
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
			return

		if self.state == EGuiState.Connected:
			# perform fields update routine
			rtnValList = self.mcp.Cmd_GetRegister( *self.regUpdRoutine )
			self.tBoxVBus.setText( str( rtnValList[ 0 ] ) )
			self.tBoxTemp.setText( str( rtnValList[ 1 ] ) )
			pass

		pass