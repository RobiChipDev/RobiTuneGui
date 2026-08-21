import sys
import serial.tools.list_ports
from enum import Enum
from PyQt6 import QtCore
from PyQt6 import QtWidgets
from McpItf import CMcpItf, EMcpRespStatusCode, EMcpState
from McpRegInfo import *
from RobiPlanner import *

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

	def __init__( self, mcp: CMcpItf, planner: CRobiPlanner ):
		# associate operational objects
		self.mcp = mcp
		self.planner = planner
		self.state = EGuiState.Idle

		# init application
		self.app = QtWidgets.QApplication( sys.argv )
		self.window = QtWidgets.QMainWindow()
		self.window.setWindowTitle( 'RobiTune' )
		self.window.resize( 800, 600 )

		self.lowFreqTick = QtCore.QTimer( self.window )
		self.lowFreqTick.timeout.connect( self.__lowFreqTick )
		self.lowFreqTick.start( 1000 ) # unit [ sec ]

		# init widgets one by one based on functionality
		self.__initConnectPanel()
		self.__initRegCtrl()
		self.__initFileOp()

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
		pass

	def exec( self ) -> None:
		self.window.show()
		self.app.exec()
		pass

# widgets initialization
	def __initConnectPanel( self ) -> None:
		self.lblConnState = QtWidgets.QLabel( "State: Idle", self.window )
		self.lblConnState.move( 200, 200 )

		self.lblMcpVer = QtWidgets.QLabel( "", self.window )
		self.lblMcpVer.move( 200, 250 )

		self.btnRefresh = QtWidgets.QPushButton( self.window )
		self.btnRefresh.setText( "Refresh" )
		self.btnRefresh.setGeometry( 0, 0, 100, 30 )
		self.btnRefresh.clicked.connect( self.__btnRefreshClick )
		
		self.btnConnect = QtWidgets.QPushButton( self.window )
		self.btnConnect.setText( TEXT_CONNECT )
		self.btnConnect.setGeometry( 400, 0, 100, 30 )
		self.btnConnect.clicked.connect( self.__btnConnectClick )

		self.tBoxMotorNo = QtWidgets.QLineEdit( self.window )
		self.tBoxMotorNo.setText( "1" )
		self.tBoxMotorNo.setPlaceholderText( "MotorNo" )
		self.tBoxMotorNo.resize( 100, 30 )
		self.tBoxMotorNo.move( 300, 0 )
		
		self.tBoxBaud = QtWidgets.QLineEdit( self.window )
		self.tBoxBaud.setText( "1843200" )
		self.tBoxBaud.setPlaceholderText( "Baudrate" )
		self.tBoxBaud.resize( 100, 30 )
		self.tBoxBaud.move( 200, 0 )

		self.ComBoxPortName = QtWidgets.QComboBox( self.window )
		self.ComBoxPortName.move( 100, 0 )
		ports = serial.tools.list_ports.comports()
		for port in ports:
			self.ComBoxPortName.addItem( port.device )
		pass

	def __initRegCtrl( self ) -> None:
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

		# prepare register identifiers for update routine
		self.regUpdRoutine = ( \
			packRegId( 22,	EMcpRegType.Bit16, 1 ), # VBUS \
			packRegId( 23,	EMcpRegType.Bit16, 1 ), # TEMP \
			packRegId( 109,	EMcpRegType.Bit32, 1 ), # POWER \
			) 
		pass

	def __initFileOp( self ) -> None:
		self.btnFileSelect = QtWidgets.QPushButton( self.window )
		self.btnFileSelect.setText( "Selelct" )
		self.btnFileSelect.setGeometry( 0, 160, 100, 30 )
		self.btnFileSelect.clicked.connect( self.__btnFileSelectClick )

		self.btnCtrlPlay = QtWidgets.QPushButton( self.window )
		self.btnCtrlPlay.setText( "Play" )
		self.btnCtrlPlay.setGeometry( 0, 190, 100, 30 )
		self.btnCtrlPlay.clicked.connect( self.__btnCtrlPlayClick )

		self.btnCtrlStop = QtWidgets.QPushButton( self.window )
		self.btnCtrlStop.setText( "Stop" )
		self.btnCtrlStop.setGeometry( 100, 190, 100, 30 )
		self.btnCtrlStop.clicked.connect( self.__btnCtrlStopClick )

		self.tBoxFilePath = QtWidgets.QLineEdit( self.window )
		self.tBoxFilePath.setText( "" )
		self.tBoxFilePath.setPlaceholderText( "Path" )
		self.tBoxFilePath.resize( 500, 30 )
		self.tBoxFilePath.move( 100, 160 )
		pass

# interaction events
	def __btnRefreshClick( self ) -> None:
		ports = serial.tools.list_ports.comports()
		for port in ports:
			self.ComBoxPortName.addItem( port.device )
			pass
		pass
	
	def __btnConnectClick( self ) -> None:
		if self.btnConnect.text() == TEXT_CONNECT:
			self.btnConnect.setText( TEXT_DISCONNECT )
			port = self.ComBoxPortName.currentText()
			baud = int( self.tBoxBaud.text() )
			self.mcp.connect( 1, port, baud )
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

	def __btnFileSelectClick( self ) -> None:
		filePath, _ = QtWidgets.QFileDialog.getOpenFileName( \
			self.window, "選擇檔案", \
			"",  # 起始路徑 \
			"所有檔案 (*.*);;文字檔案 (*.txt)"  # 檔案篩選器
		)
		if filePath:
			self.tBoxFilePath.setText( filePath )
			self.planner.importScript( self.tBoxFilePath.text() )
			pass
		pass

	def __btnCtrlPlayClick( self ) -> None:
		self.planner.start()
		pass

	def __btnCtrlStopClick( self ) -> None:
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