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
		# init grid layout
		self.layout = QtWidgets.QGridLayout()
		self.__initConnectPanel()
		self.__initStatusPanel()
		self.__initRegCtrl()
		self.__initFileOp()

		# finalize the window setting
		self.central_widget = QtWidgets.QWidget()
		self.window.setCentralWidget( self.central_widget )
		self.layout.setSpacing( 10 )			# 設定網格上下左右的間距為 10 像素
		#self.layout.setColumnStretch( 1, 2 )	# 讓第 1 列的寬度伸縮比例為其他列的 2 倍
		#self.layout.setRowStretch( 1, 3 )		# 讓第 1 行（文字區）的高度伸縮比例為其他行的 
		self.central_widget.setLayout( self.layout )
		pass

	def exec( self ) -> None:
		self.window.show()
		self.app.exec()
		pass

# widgets initialization
	def __initConnectPanel( self ) -> None:
		self.btnRefresh = QtWidgets.QPushButton()
		self.btnRefresh.setText( "Refresh" )
		self.btnRefresh.clicked.connect( self.__btnRefreshClick )
		self.layout.addWidget( self.btnRefresh, 0, 0 )
		
		self.btnConnect = QtWidgets.QPushButton()
		self.btnConnect.setText( TEXT_CONNECT )
		self.btnConnect.clicked.connect( self.__btnConnectClick )
		self.layout.addWidget( self.btnConnect, 0, 4 )

		self.tBoxMotorNo = QtWidgets.QLineEdit()
		self.tBoxMotorNo.setText( "1" )
		self.tBoxMotorNo.setPlaceholderText( "MotorNo" )
		self.layout.addWidget( self.tBoxMotorNo, 0, 1 )
		
		self.tBoxBaud = QtWidgets.QLineEdit()
		self.tBoxBaud.setText( "1843200" )
		self.tBoxBaud.setPlaceholderText( "Baudrate" )
		self.layout.addWidget( self.tBoxBaud, 0, 2 )

		self.ComBoxPortName = QtWidgets.QComboBox()
		ports = serial.tools.list_ports.comports()
		for port in ports:
			self.ComBoxPortName.addItem( port.device )
		pass
		self.layout.addWidget( self.ComBoxPortName, 0, 3 )
		pass

	def __initStatusPanel( self ) -> None:
		self.lblConnState = QtWidgets.QLabel( "Conn. State:")
		self.layout.addWidget( self.lblConnState, 1, 0 )

		self.tBoxConnState = QtWidgets.QLineEdit( self.window )
		self.tBoxConnState.setText( "Idle" )
		self.tBoxConnState.setPlaceholderText( "Conn. State" )
		self.layout.addWidget( self.tBoxConnState, 1, 1 )

		self.lblMcpVer = QtWidgets.QLabel( "MCP Ver:")
		self.layout.addWidget( self.lblMcpVer, 1, 2 )

		self.tBoxMcpVer = QtWidgets.QLineEdit()
		self.tBoxMcpVer.setText( "0" )
		self.tBoxMcpVer.setPlaceholderText( "Ver." )
		self.layout.addWidget( self.tBoxMcpVer, 1, 3, 1, 2 )

		self.tBoxVBus = QtWidgets.QLineEdit()
		self.tBoxVBus.setText( "0" )
		self.tBoxVBus.setPlaceholderText( "VBus" )
		self.layout.addWidget( self.tBoxVBus, 2, 0 )

		self.tBoxTemp = QtWidgets.QLineEdit()
		self.tBoxTemp.setText( "0" )
		self.tBoxTemp.setPlaceholderText( "Temp" )
		self.layout.addWidget( self.tBoxTemp, 2, 1 )
		pass

	def __initRegCtrl( self ) -> None:
		self.ComBoxRegType = QtWidgets.QComboBox()
		self.ComBoxRegType.addItems( [ \
			EGuiRegTypeTxt.BIT8.value, EGuiRegTypeTxt.BIT16.value, EGuiRegTypeTxt.BIT32.value, \
			EGuiRegTypeTxt.STR.value, EGuiRegTypeTxt.RAW.value ] )
		self.layout.addWidget( self.ComBoxRegType, 3, 0 )

		self.tBoxRegNo = QtWidgets.QLineEdit( )
		self.tBoxRegNo.setText( "0x001" )
		self.tBoxRegNo.setPlaceholderText( "Addr." )
		self.layout.addWidget( self.tBoxRegNo, 3, 1 )

		self.tBoxRegVal = QtWidgets.QLineEdit()
		self.tBoxRegVal.setText( "0x000" )
		self.tBoxRegVal.setPlaceholderText( "Val." )
		self.layout.addWidget( self.tBoxRegVal, 4, 1, 1, 3 )

		self.btnGetReg = QtWidgets.QPushButton()
		self.btnGetReg.setText( "GetReg" )
		self.btnGetReg.clicked.connect( self.__btnGetRegClick )
		self.layout.addWidget( self.btnGetReg, 4, 0 )

		self.btnSetReg = QtWidgets.QPushButton()
		self.btnSetReg.setText( "SetReg" )
		self.btnSetReg.clicked.connect( self.__btnSetRegClick )
		self.layout.addWidget( self.btnSetReg, 5, 0 )
		pass

	def __initFileOp( self ) -> None:
		self.btnFileSelect = QtWidgets.QPushButton()
		self.btnFileSelect.setText( "Selelct" )
		self.btnFileSelect.clicked.connect( self.__btnFileSelectClick )
		self.layout.addWidget( self.btnFileSelect, 6, 0 )

		self.btnCtrlPlay = QtWidgets.QPushButton()
		self.btnCtrlPlay.setText( "Play" )
		self.btnCtrlPlay.clicked.connect( self.__btnCtrlPlayClick )
		self.layout.addWidget( self.btnCtrlPlay, 7, 0 )

		self.btnCtrlStop = QtWidgets.QPushButton()
		self.btnCtrlStop.setText( "Stop" )
		self.btnCtrlStop.clicked.connect( self.__btnCtrlStopClick )
		self.layout.addWidget( self.btnCtrlStop, 8, 0 )

		self.tBoxFilePath = QtWidgets.QLineEdit()
		self.tBoxFilePath.setText( "" )
		self.tBoxFilePath.setPlaceholderText( "Script Path" )
		self.layout.addWidget( self.tBoxFilePath, 6, 1, 1, 3 )

		self.tBoxPlanState = QtWidgets.QLineEdit()
		self.tBoxPlanState.setText( "Idle" )
		self.tBoxPlanState.setPlaceholderText( "Planner State" )
		self.layout.addWidget( self.tBoxPlanState, 7, 1 )

		self.tBoxLineNo = QtWidgets.QLineEdit()
		self.tBoxLineNo.setText( "0" )
		self.tBoxLineNo.setPlaceholderText( "LineNo" )
		self.layout.addWidget( self.tBoxLineNo, 8, 1 )
		pass

# interaction events
	def __btnRefreshClick( self ) -> None:
		ports = serial.tools.list_ports.comports()
		self.ComBoxPortName.clear()
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
		self.planner.stop()
		pass

# tick (timer) events
	def __lowFreqTick( self ) -> None:
		if self.state == EGuiState.Idle:
			return
		
		if self.state == EGuiState.Connecting:
			match self.mcp.getAspepState():
				case EMcpState.Idle:
					self.tBoxConnState.setText( f"Idle" )
					pass
				case EMcpState.Config:
					self.tBoxConnState.setText( f"Configuration" )
					pass
				case EMcpState.Connecting:
					self.tBoxConnState.setText( f"Connecting" )
					pass
				case EMcpState.Connected:
					self.tBoxConnState.setText( f"Connected" )
					self.state = EGuiState.Connected

					_, ver = self.mcp.Cmd_GetMcpVer()
					self.tBoxMcpVer.setText( f"{ ver }" )
					pass
			return

		if self.state == EGuiState.Connected:
			# perform fields update routine
			self.tBoxPlanState.setText( str( self.planner.getState() ) )
			self.tBoxLineNo.setText( str( self.planner.currLineNo ) )
			self.tBoxVBus.setText( str( self.mcp.regVBus ) )
			self.tBoxTemp.setText( str( self.mcp.regTemp ) )
			pass

		pass