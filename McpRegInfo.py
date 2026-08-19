import struct
from enum import Enum

################################
# Author: Boyce, RobiChip
# Date: 2026/08/12
# Description:
# MCP register container
# Register Identifier (RegId) format:
# 	|-3 bits-|-3 bits----|-10 bits----|
# 	|-Motor#-|-Data Type-|-Identifier-|

# TYPE_DATA_8BIT registers definition
class EMcp8BitReg( Enum ):
	Status = 1					# MC_REG_STATUS
	ControlMode = 2				# MC_REG_CONTROL_MODE
	RucStageNbr = 3				# MC_REG_RUC_STAGE_NBR, Run-up Control stage number 
	PfcStatus = 13				# MC_REG_PFC_STATUS
	PfcEnabled = 14				# MC_REG_PFC_ENABLED
	ScCheck = 15				# MC_REG_SC_CHECK
	ScState = 16				# MC_REG_SC_STATE
	ScSteps = 17				# MC_REG_SC_STEPS
	ScPp = 18					# MC_REG_SC_PP
	ScFocRepRate = 19			# MC_REG_SC_FOC_REP_RATE
	ScCompleted = 20			# MC_REG_SC_COMPLETED
	PositionCtrlState = 21		# MC_REG_POSITION_CTRL_STATE
	PositionAlignState = 22		# MC_REG_POSITION_ALIGN_STATE
	HtState = 23				# MC_REG_HT_STATE
	HtProgress = 24				# MC_REG_HT_PROGRESS
	HtPlacement = 25			# MC_REG_HT_PLACEMENT
	HtMechWantedDirection = 26	# MC_REG_HT_MECH_WANTED_DIRECTION
	LowsideModulation = 27		# MC_REG_LOWSIDE_MODULATION
	QuasiSynch = 28				# MC_REG_QUASI_SYNCH
	PbCharacterization = 29		# MC_REG_PB_CHARACTERIZATION
	OpenloopDc = 30				# MC_REG_OPENLOOP_DC
	OpenloopDcFilter = 31		# MC_REG_OPENLOOP_DC_FILTER
	Openloop = 32				# MC_REG_OPENLOOP
	OpenloopRevup = 33			# MC_REG_OPENLOOP_REVUP
	OpenloopVoltfactor = 34		# MC_REG_OPENLOOP_VOLTFACTOR
	OpenloopSensing = 35		# MC_REG_OPENLOOP_SENSING
	IpdEnable = 36				# MC_REG_IPD_ENABLE
	IpdDebug = 37				# MC_REG_IPD_DEBUG
	pass

# TYPE_DATA_16BIT registers definition
class EMcp16BitReg( Enum ):
	SpdKp = 2				# MC_REG_SPEED_KP                 ((2U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
	SpdKi = 3				# MC_REG_SPEED_KI                 ((3U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
	SpdKd = 4				# MC_REG_SPEED_KD                 ((4U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
	IqKp = 6				# MC_REG_I_Q_KP                   ((6U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
	IqKi = 7				# MC_REG_I_Q_KI                   ((7U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
	IqKd = 8				# MC_REG_I_Q_KD                   ((8U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
	IdKp = 10				# MC_REG_I_D_KP                   ((10U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
	IdKi = 11				# MC_REG_I_D_KI                   ((11U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
	IdKd = 12				# MC_REG_I_D_KD                   ((12U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
	StoPllC1 = 13			# MC_REG_STOPLL_C1                ((13U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
	SroPllC2 = 14			# MC_REG_STOPLL_C2                ((14U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
	StoCordicC1 = 15		# MC_REG_STOCORDIC_C1             ((15U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
	StoCordicC2 = 16		# MC_REG_STOCORDIC_C2             ((16U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
	StoPllKi = 17			# MC_REG_STOPLL_KI                ((17U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
	StoPllKp = 18			# MC_REG_STOPLL_KP                ((18U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
	FluxWkKp = 19			# MC_REG_FLUXWK_KP                ((19U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
	FluxWkKi = 20			# MC_REG_FLUXWK_KI                ((20U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
	FluxWkBus = 21			# MC_REG_FLUXWK_BUS               ((21U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
	BusVoltage = 22			# MC_REG_BUS_VOLTAGE              ((22U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
	HeatsTemp = 23			# MC_REG_HEATS_TEMP               ((23U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
	DacOut1 = 25			# MC_REG_DAC_OUT1                 ((25U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
	DacOut2 = 26			# MC_REG_DAC_OUT2                 ((26U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
	DacOut3 = 27			# MC_REG_DAC_OUT3                 ((27U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
	FluxWkBusMeas = 30		# MC_REG_FLUXWK_BUS_MEAS          ((30U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
	Ia = 31					# MC_REG_I_A                      ((31U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
	Ib = 32					# MC_REG_I_B                      ((32U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
	IalphaMeas = 33			# MC_REG_I_ALPHA_MEAS             ((33U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
	IbetaMeas = 34			# MC_REG_I_BETA_MEAS              ((34U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
	IqMeas = 35				# MC_REG_I_Q_MEAS                 ((35U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
	IdMeas = 36				# MC_REG_I_D_MEAS                 ((36U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
	IqRef = 37				# MC_REG_I_Q_REF                  ((37U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
	IdRef = 38				# MC_REG_I_D_REF                  ((38U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
	Vq = 39					# MC_REG_V_Q                      ((39U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
	Vd = 40					# MC_REG_V_D                      ((40U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
	Valpha = 41				# MC_REG_V_ALPHA                  ((41U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
	Vbeta = 42				# MC_REG_V_BETA                   ((42U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
	EncElAngle = 43			# MC_REG_ENCODER_EL_ANGLE         ((43U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
	EncSpd = 44				# MC_REG_ENCODER_SPEED            ((44U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
	StoPllElAngle = 45		# MC_REG_STOPLL_EL_ANGLE          ((45U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
	StoPllRotSpd = 46		# MC_REG_STOPLL_ROT_SPEED         ((46U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
	StoPllIalpha = 47		# MC_REG_STOPLL_I_ALPHA           ((47U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
	StoPllIbeta = 48		# MC_REG_STOPLL_I_BETA            ((48U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
	StoPllBemfAlpha = 49	# MC_REG_STOPLL_BEMF_ALPHA        ((49U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
	StoPllBemfBeta = 50		# MC_REG_STOPLL_BEMF_BETA         ((50U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
	StoCordicElAngle = 51	# MC_REG_STOCORDIC_EL_ANGLE       ((51U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
	StoCordicRotSpd = 52	# MC_REG_STOCORDIC_ROT_SPEED      ((52U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
	StoCordicIalpha = 53	# MC_REG_STOCORDIC_I_ALPHA        ((53U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
	StoCordicIbeta = 54		# MC_REG_STOCORDIC_I_BETA         ((54U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
	StoCordicBemfAlpha = 55	# MC_REG_STOCORDIC_BEMF_ALPHA     ((55U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
	StoCordicBemfBeta = 56	# MC_REG_STOCORDIC_BEMF_BETA      ((56U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
	DacUser1 = 57			# MC_REG_DAC_USER1                ((57U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
	DacUser2 = 58			# MC_REG_DAC_USER2                ((58U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
	HallElAngle = 59		# MC_REG_HALL_EL_ANGLE            ((59U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
	HallSpd = 60			# MC_REG_HALL_SPEED               ((60U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
	FFVq = 62				# MC_REG_FF_VQ                    ((62U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
	FFVd = 63				# MC_REG_FF_VD                    ((63U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
	FFVqPiOut = 64			# MC_REG_FF_VQ_PIOUT              ((64U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
	FFVdPiOut = 65			# MC_REG_FF_VD_PIOUT              ((65U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
	PfcDcBusRef = 66		# MC_REG_PFC_DCBUS_REF            ((66U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
	PfcDcBusMeas = 67		# MC_REG_PFC_DCBUS_MEAS           ((67U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
	PfcAcBusFreq = 68		# MC_REG_PFC_ACBUS_FREQ           ((68U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
	PfcAcBusRms = 69		# MC_REG_PFC_ACBUS_RMS            ((69U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
	PfcIKp = 70				# MC_REG_PFC_I_KP                 ((70U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
	PfcIKi = 71				# MC_REG_PFC_I_KI                 ((71U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
	PfcIKd = 72				# MC_REG_PFC_I_KD                 ((72U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
	PfcVKp = 73				# MC_REG_PFC_V_KP                 ((73U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
	PfcVKi = 74				# MC_REG_PFC_V_KI                 ((74U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
	PfcVKd = 75				# MC_REG_PFC_V_KD                 ((75U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
	PfcStartupDuration = 76	# MC_REG_PFC_STARTUP_DURATION     ((76U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
	ScPwmFreq = 77			# MC_REG_SC_PWM_FREQUENCY         ((77U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
	PosKp = 78				# MC_REG_POSITION_KP              ((78U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
	PosKi = 79				# MC_REG_POSITION_KI              ((79U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
	PosKd = 80				# MC_REG_POSITION_KD              ((80U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
	SpdKpDiv = 81			# MC_REG_SPEED_KP_DIV             ((81U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
	SpdKiDiv = 82			# MC_REG_SPEED_KI_DIV             ((82U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
	SpdKdDiv = 83			# MC_REG_SPEED_KD_DIV             ((83U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
	IdKpDiv = 84			# MC_REG_I_D_KP_DIV               ((84U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
	IdKiDiv = 85			# MC_REG_I_D_KI_DIV               ((85U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
	IdKdDiv = 86			# MC_REG_I_D_KD_DIV               ((86U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
	IqKpDiv = 87			# MC_REG_I_Q_KP_DIV               ((87U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
	IqKiDiv = 88			# MC_REG_I_Q_KI_DIV               ((88U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
	IqKdDiv = 89			# MC_REG_I_Q_KD_DIV               ((89U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
	PosKpDiv = 90			# MC_REG_POSITION_KP_DIV          ((90U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
	PosKiDiv = 91			# MC_REG_POSITION_KI_DIV          ((91U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
	PosKdDiv = 92			# MC_REG_POSITION_KD_DIV          ((92U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
	PfcIKpDiv = 93			# MC_REG_PFC_I_KP_DIV             ((93U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
	PfcIKiDiv = 94			# MC_REG_PFC_I_KI_DIV             ((94U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
	PfcIKdDiv = 95			# MC_REG_PFC_I_KD_DIV             ((95U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
	PfcVKpDiv = 96			# MC_REG_PFC_V_KP_DIV             ((96U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
	PfcVKiDiv = 97			# MC_REG_PFC_V_KI_DIV             ((97U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
	PfcVKdDiv = 98			# MC_REG_PFC_V_KD_DIV             ((98U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
	StoPllKiDiv = 99		# MC_REG_STOPLL_KI_DIV            ((99U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
	StoPllKpDiv = 100		# MC_REG_STOPLL_KP_DIV            ((100U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
	FluxWkKpDiv = 101		# MC_REG_FLUXWK_KP_DIV            ((101U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
	FluxWkKiDiv = 102		# MC_REG_FLUXWK_KI_DIV            ((102U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
	StartCurrentRef = 105	# MC_REG_STARTUP_CURRENT_REF      ((105U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
	FocVqRef = 107			# MC_REG_FOC_VQREF                ((107U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
	OpenLopCurrFactor = 108	# MC_REG_OPENLOOP_CURRFACTOR      ((108U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
	CurrMntr = 109			# MC_REG_CURR_MONITOR             ((109U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
	CurrMntrSamplNs = 110	# MC_REG_CURR_MONITOR_SAMPL_NS    ((110U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
	CurrMntrAvg	= 111		# MC_REG_CURR_MONITOR_AVG         ((111U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
	OverVoltThres = 112		# MC_REG_OVERVOLTAGETHRESHOLD     ((112U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
	UnderVoltThres = 113	# MC_REG_UNDERVOLTAGETHRESHOLD    ((113U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
	IpdVstr = 114			# MC_REG_IPD_VSTR                 ((114U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
	OpenLopElAngle = 115	# MC_REG_OPENLOOP_EL_ANGLE        ((115U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
	IpdVstptr = 116			# MC_REG_IPD_VSTPTR               ((116U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
	pass

# TYPE_DATA_32BIT registers definition
class EMcp32BitReg( Enum ):
	FaultFlag = 0			# MC_REG_FAULTS_FLAGS             ((0 << ELT_IDENTIFIER_POS) | TYPE_DATA_32BIT)
	SpdMeas = 1				# MC_REG_SPEED_MEAS               ((1 << ELT_IDENTIFIER_POS) | TYPE_DATA_32BIT)
	SpdRef = 2				# MC_REG_SPEED_REF                ((2 << ELT_IDENTIFIER_POS) | TYPE_DATA_32BIT)
	StoPllEstBemf = 3		# MC_REG_STOPLL_EST_BEMF          ((3 << ELT_IDENTIFIER_POS) | TYPE_DATA_32BIT)
	StoPllObsBemf = 4		# MC_REG_STOPLL_OBS_BEMF          ((4 << ELT_IDENTIFIER_POS) | TYPE_DATA_32BIT)
	StoCordicEstBemf = 5	# MC_REG_STOCORDIC_EST_BEMF       ((5 << ELT_IDENTIFIER_POS) | TYPE_DATA_32BIT) 
	StoCordicObsBemf = 6	# MC_REG_STOCORDIC_OBS_BEMF       ((6 << ELT_IDENTIFIER_POS) | TYPE_DATA_32BIT)
	FF1Q = 7				# MC_REG_FF_1Q                    ((7 << ELT_IDENTIFIER_POS) | TYPE_DATA_32BIT)
	FF1d = 8				# MC_REG_FF_1D                    ((8 << ELT_IDENTIFIER_POS) | TYPE_DATA_32BIT)
	FF2 = 9					# MC_REG_FF_2                     ((9 << ELT_IDENTIFIER_POS) | TYPE_DATA_32BIT)
	PfcFault = 40			# MC_REG_PFC_FAULTS               ((40 << ELT_IDENTIFIER_POS) | TYPE_DATA_32BIT)
	CurrPos = 41			# MC_REG_CURRENT_POSITION         ((41 << ELT_IDENTIFIER_POS) | TYPE_DATA_32BIT)
	ScRs = 91				# MC_REG_SC_RS                    ((91 << ELT_IDENTIFIER_POS) | TYPE_DATA_32BIT)
	ScLs = 92				# MC_REG_SC_LS                    ((92 << ELT_IDENTIFIER_POS) | TYPE_DATA_32BIT)
	ScKe = 93				# MC_REG_SC_KE                    ((93 << ELT_IDENTIFIER_POS) | TYPE_DATA_32BIT)
	ScVbus = 94				# MC_REG_SC_VBUS                  ((94 << ELT_IDENTIFIER_POS) | TYPE_DATA_32BIT)
	ScMeasNomSpd = 95		# MC_REG_SC_MEAS_NOMINALSPEED     ((95 << ELT_IDENTIFIER_POS) | TYPE_DATA_32BIT)
	ScCurrent = 96			# MC_REG_SC_CURRENT               ((96 << ELT_IDENTIFIER_POS) | TYPE_DATA_32BIT)
	ScSpdBandwidth = 97		# MC_REG_SC_SPDBANDWIDTH          ((97 << ELT_IDENTIFIER_POS) | TYPE_DATA_32BIT)
	ScLdLqRatio = 98		# MC_REG_SC_LDLQRATIO             ((98 << ELT_IDENTIFIER_POS) | TYPE_DATA_32BIT)
	ScNomSpd = 99			# MC_REG_SC_NOMINAL_SPEED         ((99 << ELT_IDENTIFIER_POS) | TYPE_DATA_32BIT)
	ScCurrBandwidth = 100	# MC_REG_SC_CURRBANDWIDTH         ((100 << ELT_IDENTIFIER_POS) | TYPE_DATA_32BIT)
	ScJ = 101				# MC_REG_SC_J                     ((101 << ELT_IDENTIFIER_POS) | TYPE_DATA_32BIT)
	ScF = 102				# MC_REG_SC_F                     ((102 << ELT_IDENTIFIER_POS) | TYPE_DATA_32BIT)
	ScMaxCurrent = 103		# MC_REG_SC_MAX_CURRENT           ((103 << ELT_IDENTIFIER_POS) | TYPE_DATA_32BIT)
	ScStartSpd = 104		# MC_REG_SC_STARTUP_SPEED         ((104 << ELT_IDENTIFIER_POS) | TYPE_DATA_32BIT)
	ScStartAcc = 105		# MC_REG_SC_STARTUP_ACC           ((105 << ELT_IDENTIFIER_POS) | TYPE_DATA_32BIT)
	MotorPwr = 109			# MC_REG_MOTOR_POWER              ((109 << ELT_IDENTIFIER_POS) | TYPE_DATA_32BIT)
	ResistorOffset = 116	# MC_REG_RESISTOR_OFFSET          ((116 << ELT_IDENTIFIER_POS) | TYPE_DATA_32BIT)
	pass

# TYPE_DATA_STRING registers definition
class EMcpStringReg( Enum ):
	FwName = 0
	CtrlStageName = 1
	PwrStageName = 2
	MotorName = 3
	pass

# TYPE_DATA_RAWSTRUCT registers definition
class EMcpRawStructReg( Enum ):
	GlobalConfig = 0		# MC_REG_GLOBAL_CONFIG            ((0U << ELT_IDENTIFIER_POS) | TYPE_DATA_RAW)
	MotorConfig = 1			# MC_REG_MOTOR_CONFIG             ((1U << ELT_IDENTIFIER_POS) | TYPE_DATA_RAW)
	AppConfig = 2			# MC_REG_APPLICATION_CONFIG       ((2U << ELT_IDENTIFIER_POS) | TYPE_DATA_RAW)
	FocFwConfig = 3			# MC_REG_FOCFW_CONFIG             ((3U << ELT_IDENTIFIER_POS) | TYPE_DATA_RAW)
	ScaleConfig = 4			# MC_REG_SCALE_CONFIG             ((4U << ELT_IDENTIFIER_POS) | TYPE_DATA_RAW)
	SpdRamp = 5				# MC_REG_SPEED_RAMP               ((6U << ELT_IDENTIFIER_POS) | TYPE_DATA_RAW)
	TorqRamp = 7			# MC_REG_TORQUE_RAMP              ((7U << ELT_IDENTIFIER_POS) | TYPE_DATA_RAW)
	RevupData = 8			# MC_REG_REVUP_DATA               ((8U << ELT_IDENTIFIER_POS) | TYPE_DATA_RAW) 
	CurrentRef = 13			# MC_REG_CURRENT_REF              ((13U << ELT_IDENTIFIER_POS) | TYPE_DATA_RAW)
	PosRamp = 14			# MC_REG_POSITION_RAMP            ((14U << ELT_IDENTIFIER_POS) | TYPE_DATA_RAW)
	AsyncUartA = 20			# MC_REG_ASYNC_UARTA              ((20U << ELT_IDENTIFIER_POS) | TYPE_DATA_RAW)
	AsyncUartB = 21			# MC_REG_ASYNC_UARTB              ((21U << ELT_IDENTIFIER_POS) | TYPE_DATA_RAW)
	AsyncStlink = 22		# MC_REG_ASYNC_STLNK              ((22U << ELT_IDENTIFIER_POS) | TYPE_DATA_RAW)
	HtHewPins = 28			# MC_REG_HT_HEW_PINS              ((28U << ELT_IDENTIFIER_POS) | TYPE_DATA_RAW)
	HtConnectedPins = 29	# MC_REG_HT_CONNECTED_PINS        ((29U << ELT_IDENTIFIER_POS) | TYPE_DATA_RAW)
	HtPhaseShift = 30		# MC_REG_HT_PHASE_SHIFT           ((30U << ELT_IDENTIFIER_POS) | TYPE_DATA_RAW)
	BemfAdcConf = 31		# MC_REG_BEMF_ADC_CONF            ((31U << ELT_IDENTIFIER_POS) | TYPE_DATA_RAW)
	pass

# struct format: little endian
McpRawStructFmt = { \
	EMcpRawStructReg.GlobalConfig: "<", \
	
	# F polePairs, F ratedFlux, F rs, F rsSkinFactor, F ls, F ld, F maxCurrent, F mass_kg, F cooling_tau_s, C name[ 24 ]
	EMcpRawStructReg.MotorConfig: "<fffffffff24s", \
	
	# U32 maxMechSpd, F maxReadCurrent, F nominalCurrent, U16 nominalVolt, U8 driveType, U8 padding
	EMcpRawStructReg.AppConfig: "<IffHBB", \
	
	# U8 primeSnsr, U8 auxSnsr, U8 topology, U8 FOCRate, U32 PWMFreq, U16 MediumFreq, U16 ConfigFlag1, U16 ConfigFlag2
	EMcpRawStructReg.FocFwConfig: "<BBBBIHHH", \
	EMcpRawStructReg.ScaleConfig: "", \
	
	# I32 rpm, U16 duration
	EMcpRawStructReg.SpdRamp: "<iH", \
	
	# I16 torq, U16 duration
	EMcpRawStructReg.TorqRamp: "<hH", \
	
	# 
	EMcpRawStructReg.RevupData: "", \

	# U16 iqref, U16 idref
	EMcpRawStructReg.CurrentRef: "<HH", \

	# F position, F duration
	EMcpRawStructReg.PosRamp: "<ff", \
	EMcpRawStructReg.AsyncUartA: "", \
	EMcpRawStructReg.AsyncUartB: "", \
	EMcpRawStructReg.AsyncStlink: "", \
	EMcpRawStructReg.HtHewPins: "", \
	EMcpRawStructReg.HtConnectedPins: "", \
	EMcpRawStructReg.HtPhaseShift: "", \
	EMcpRawStructReg.BemfAdcConf: "", \
	}

# MCP register type
class EMcpRegType( Enum ):
	Reserved = 0
	Bit8 = 1
	Bit16 = 2
	Bit32 = 3
	Str = 4
	RawStruct = 5
	Reserved2 = 6
	Reserved3 = 7
	pass

def packRegId( regNo: int, regType: EMcpRegType, motorNo ) -> bytes:
	payload = motorNo | ( regType.value << 3 ) | ( regNo << 6 )
	byte0 = payload & 0xFF
	byte1 = ( payload >> 8 ) & 0xFF
	return bytes( [ byte0, byte1 ] )

def unpackRegId( regId: bytes ) -> tuple[ int, EMcpRegType, int ]:
	payload = int( regId[ 0 ] ) | ( int( regId[ 1 ] ) << 8 )
	motorNo = payload & 0x7
	regTypeRaw = ( payload >> 3 ) & 0x7
	regNo = ( payload >> 6 ) & 0x3FF

	regtype = EMcpRegType( regTypeRaw )
	return regNo, regtype, motorNo

def decodeRegVal( type: EMcpRegType, regNo: int, packedBytes: bytes, startPos: int = 0 ) \
	-> tuple[ bool, int, int ] | tuple[ bool, int, str ] | tuple[ bool, int, bytes ]:
	match type:
		case EMcpRegType.Bit8:
			byteShift = 1
			regVal = int( packedBytes[ startPos ] )
			pass
		case EMcpRegType.Bit16:
			byteShift = 2
			regVal = int( packedBytes[ startPos ] ) | ( int( packedBytes[ startPos + 1 ] ) << 8 )
			pass
		case EMcpRegType.Bit32:
			byteShift = 4
			regVal = \
				int( packedBytes[ startPos ] ) | \
				( int( packedBytes[ startPos + 1 ] ) << 8 ) | \
				( int( packedBytes[ startPos + 2 ] ) << 16 ) | \
				( int( packedBytes[ startPos + 3 ] ) << 24 ) 
			pass
		case EMcpRegType.RawStruct:
			regEnum = EMcpRawStructReg( regNo )
			byteshift = struct.calcsize( McpRawStructFmt.get( regEnum ) )
			regVal = packedBytes[ startPos: ( startPos + byteShift ) ]
			pass
		case _:
			byteShift = 0
			return False, startPos, 0

	return True, ( startPos + byteShift ), regVal