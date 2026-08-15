import struct
import bitstruct
from enum import Enum

################################
# Author: Boyce, RobiChip
# Date: 2026/08/12
# Description:
# MCP register container
# Register Identifier (RegId) format:
# 	|-10 bits----|-3 bits----|-3 bits-|
# 	|-Identifier-|-Data Type-|-Motor#-|

# TYPE_DATA_8BIT registers definition
class EMcp8BitReg( Enum ):
	Status = 1					# MC_REG_STATUS
	ControlMode = 2				# MC_REG_CONTROL_MODE
	RucStageNbr = 3				# MC_REG_RUC_STAGE_NBR
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
	SpeedKp = 2			# MC_REG_SPEED_KP
	SpeedKi = 3			# MC_REG_SPEED_KI
	SpeedKd = 4			# MC_REG_SPEED_KD
	IqKp = 6			# MC_REG_I_Q_KP
	IqKi = 7			# MC_REG_I_Q_KI
	IqKd = 8			# MC_REG_I_Q_KD
	IdKp = 10			# MC_REG_I_D_KP
	IdKi = 11			# MC_REG_I_D_KI
	IdKd = 12			# MC_REG_I_D_KD
	StoPllC1 = 13		# MC_REG_STOPLL_C1
	StoPllC2 = 14		# MC_REG_STOPLL_C2
	StoCordicC1 = 15	# MC_REG_STOCORDIC_C1
	StoCordicC2 = 16	# MC_REG_STOCORDIC_C2
	StoPllKi = 17		# MC_REG_STOPLL_KI
	StoPllKp = 18		# MC_REG_STOPLL_KP
	FluxWkKp = 19		# MC_REG_FLUXWK_KP
	FluxWkKi = 20		# MC_REG_FLUXWK_KI
	FluxWkBus = 21		# MC_REG_FLUXWK_BUS
	BusVoltage = 22		# MC_REG_BUS_VOLTAGE
	HeatsTemp = 23		# MC_REG_HEATS_TEMP
	DacOut1 = 24		# MC_REG_DAC_OUT1
	DacOut2 = 25		# MC_REG_DAC_OUT2
	DacOut3 = 26		# MC_REG_DAC_OUT3
	FluxWkBusMeas = 27	# MC_REG_FLUXWK_BUS_MEAS
	Ia = 30				# MC_REG_I_A
	Ib = 31				# MC_REG_I_B
	Ialpha = 32			# MC_REG_I_ALPHA_MEAS
	pass

#define  MC_REG_I_BETA_MEAS              ((34U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
#define  MC_REG_I_Q_MEAS                 ((35U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
#define  MC_REG_I_D_MEAS                 ((36U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
#define  MC_REG_I_Q_REF                  ((37U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
#define  MC_REG_I_D_REF                  ((38U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
#define  MC_REG_V_Q                      ((39U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
#define  MC_REG_V_D                      ((40U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
#define  MC_REG_V_ALPHA                  ((41U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
#define  MC_REG_V_BETA                   ((42U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
#define  MC_REG_ENCODER_EL_ANGLE         ((43 << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
#define  MC_REG_ENCODER_SPEED            ((44 << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
#define  MC_REG_STOPLL_EL_ANGLE          ((45U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
#define  MC_REG_STOPLL_ROT_SPEED         ((46U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
#define  MC_REG_STOPLL_I_ALPHA           ((47U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
#define  MC_REG_STOPLL_I_BETA            ((48U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
#define  MC_REG_STOPLL_BEMF_ALPHA        ((49U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
#define  MC_REG_STOPLL_BEMF_BETA         ((50U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
#define  MC_REG_STOCORDIC_EL_ANGLE       ((51 << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
#define  MC_REG_STOCORDIC_ROT_SPEED      ((52 << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
#define  MC_REG_STOCORDIC_I_ALPHA        ((53 << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
#define  MC_REG_STOCORDIC_I_BETA         ((54 << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
#define  MC_REG_STOCORDIC_BEMF_ALPHA     ((55 << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
#define  MC_REG_STOCORDIC_BEMF_BETA      ((56 << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
#define  MC_REG_DAC_USER1                ((57U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
#define  MC_REG_DAC_USER2                ((58U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
#define  MC_REG_HALL_EL_ANGLE            ((59 << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
#define  MC_REG_HALL_SPEED               ((60 << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
#define  MC_REG_FF_VQ                    ((62U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
#define  MC_REG_FF_VD                    ((63U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
#define  MC_REG_FF_VQ_PIOUT              ((64U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
#define  MC_REG_FF_VD_PIOUT              ((65U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
#define  MC_REG_PFC_DCBUS_REF            ((66U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
#define  MC_REG_PFC_DCBUS_MEAS           ((67U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
#define  MC_REG_PFC_ACBUS_FREQ           ((68U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
#define  MC_REG_PFC_ACBUS_RMS            ((69U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
#define  MC_REG_PFC_I_KP                 ((70U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
#define  MC_REG_PFC_I_KI                 ((71U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
#define  MC_REG_PFC_I_KD                 ((72U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
#define  MC_REG_PFC_V_KP                 ((73U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
#define  MC_REG_PFC_V_KI                 ((74U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
#define  MC_REG_PFC_V_KD                 ((75U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
#define  MC_REG_PFC_STARTUP_DURATION     ((76U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
#define  MC_REG_SC_PWM_FREQUENCY         ((77 << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
#define  MC_REG_POSITION_KP              ((78 << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
#define  MC_REG_POSITION_KI              ((79 << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
#define  MC_REG_POSITION_KD              ((80 << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
#define  MC_REG_SPEED_KP_DIV             ((81 << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
#define  MC_REG_SPEED_KI_DIV             ((82 << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
#define  MC_REG_SPEED_KD_DIV             ((83 << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
#define  MC_REG_I_D_KP_DIV               ((84 << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
#define  MC_REG_I_D_KI_DIV               ((85 << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
#define  MC_REG_I_D_KD_DIV               ((86 << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
#define  MC_REG_I_Q_KP_DIV               ((87 << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
#define  MC_REG_I_Q_KI_DIV               ((88 << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
#define  MC_REG_I_Q_KD_DIV               ((89 << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
#define  MC_REG_POSITION_KP_DIV          ((90 << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
#define  MC_REG_POSITION_KI_DIV          ((91 << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
#define  MC_REG_POSITION_KD_DIV          ((92 << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
#define  MC_REG_PFC_I_KP_DIV             ((93 << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
#define  MC_REG_PFC_I_KI_DIV             ((94 << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
#define  MC_REG_PFC_I_KD_DIV             ((95 << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
#define  MC_REG_PFC_V_KP_DIV             ((96 << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
#define  MC_REG_PFC_V_KI_DIV             ((97 << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
#define  MC_REG_PFC_V_KD_DIV             ((98 << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
#define  MC_REG_STOPLL_KI_DIV            ((99 << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
#define  MC_REG_STOPLL_KP_DIV            ((100 << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
#define  MC_REG_FLUXWK_KP_DIV            ((101 << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
#define  MC_REG_FLUXWK_KI_DIV            ((102 << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
#define  MC_REG_STARTUP_CURRENT_REF      ((105 << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
#define  MC_REG_PULSE_VALUE              ((106 << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
#define  MC_REG_FOC_VQREF                ((107 << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
#define  MC_REG_OPENLOOP_CURRFACTOR      ((108U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
#define  MC_REG_CURR_MONITOR             ((109U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
#define  MC_REG_CURR_MONITOR_SAMPL_NS    ((110U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
#define  MC_REG_CURR_MONITOR_AVG         ((111U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
#define  MC_REG_OVERVOLTAGETHRESHOLD     ((112U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
#define  MC_REG_UNDERVOLTAGETHRESHOLD    ((113U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
#define  MC_REG_IPD_VSTR                 ((114U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
#define  MC_REG_OPENLOOP_EL_ANGLE        ((115U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)
#define  MC_REG_IPD_VSTPTR               ((116U << ELT_IDENTIFIER_POS) | TYPE_DATA_16BIT)

# TYPE_DATA_32BIT registers definition
#define  MC_REG_FAULTS_FLAGS             ((0 << ELT_IDENTIFIER_POS) | TYPE_DATA_32BIT)
#define  MC_REG_SPEED_MEAS               ((1 << ELT_IDENTIFIER_POS) | TYPE_DATA_32BIT)
#define  MC_REG_SPEED_REF                ((2 << ELT_IDENTIFIER_POS) | TYPE_DATA_32BIT)
#define  MC_REG_STOPLL_EST_BEMF          ((3 << ELT_IDENTIFIER_POS) | TYPE_DATA_32BIT) /* To check shifted by >> 16*/
#define  MC_REG_STOPLL_OBS_BEMF          ((4 << ELT_IDENTIFIER_POS) | TYPE_DATA_32BIT) /* To check shifted by >> 16*/
#define  MC_REG_STOCORDIC_EST_BEMF       ((5 << ELT_IDENTIFIER_POS) | TYPE_DATA_32BIT) /* To check shifted by >> 16*/
#define  MC_REG_STOCORDIC_OBS_BEMF       ((6 << ELT_IDENTIFIER_POS) | TYPE_DATA_32BIT) /* To check shifted by >> 16*/
#define  MC_REG_FF_1Q                    ((7 << ELT_IDENTIFIER_POS) | TYPE_DATA_32BIT) /* To check shifted by >> 16*/
#define  MC_REG_FF_1D                    ((8 << ELT_IDENTIFIER_POS) | TYPE_DATA_32BIT) /* To check shifted by >> 16*/
#define  MC_REG_FF_2                     ((9 << ELT_IDENTIFIER_POS) | TYPE_DATA_32BIT) /* To check shifted by >> 16*/
#define  MC_REG_PFC_FAULTS               ((40 << ELT_IDENTIFIER_POS) | TYPE_DATA_32BIT)
#define  MC_REG_CURRENT_POSITION         ((41 << ELT_IDENTIFIER_POS) | TYPE_DATA_32BIT)
#define  MC_REG_SC_RS                    ((91 << ELT_IDENTIFIER_POS) | TYPE_DATA_32BIT)
#define  MC_REG_SC_LS                    ((92 << ELT_IDENTIFIER_POS) | TYPE_DATA_32BIT)
#define  MC_REG_SC_KE                    ((93 << ELT_IDENTIFIER_POS) | TYPE_DATA_32BIT)
#define  MC_REG_SC_VBUS                  ((94 << ELT_IDENTIFIER_POS) | TYPE_DATA_32BIT)
#define  MC_REG_SC_MEAS_NOMINALSPEED     ((95 << ELT_IDENTIFIER_POS) | TYPE_DATA_32BIT)
#define  MC_REG_SC_CURRENT               ((96 << ELT_IDENTIFIER_POS) | TYPE_DATA_32BIT)
#define  MC_REG_SC_SPDBANDWIDTH          ((97 << ELT_IDENTIFIER_POS) | TYPE_DATA_32BIT)
#define  MC_REG_SC_LDLQRATIO             ((98 << ELT_IDENTIFIER_POS) | TYPE_DATA_32BIT)
#define  MC_REG_SC_NOMINAL_SPEED         ((99 << ELT_IDENTIFIER_POS) | TYPE_DATA_32BIT)
#define  MC_REG_SC_CURRBANDWIDTH         ((100 << ELT_IDENTIFIER_POS) | TYPE_DATA_32BIT)
#define  MC_REG_SC_J                     ((101 << ELT_IDENTIFIER_POS) | TYPE_DATA_32BIT)
#define  MC_REG_SC_F                     ((102 << ELT_IDENTIFIER_POS) | TYPE_DATA_32BIT)
#define  MC_REG_SC_MAX_CURRENT           ((103 << ELT_IDENTIFIER_POS) | TYPE_DATA_32BIT)
#define  MC_REG_SC_STARTUP_SPEED         ((104 << ELT_IDENTIFIER_POS) | TYPE_DATA_32BIT)
#define  MC_REG_SC_STARTUP_ACC           ((105 << ELT_IDENTIFIER_POS) | TYPE_DATA_32BIT)
#define  MC_REG_RESISTOR_OFFSET          ((116 << ELT_IDENTIFIER_POS) | TYPE_DATA_32BIT)

#define  MC_REG_MOTOR_POWER              ((109 << ELT_IDENTIFIER_POS) | TYPE_DATA_32BIT)

#define  MC_REG_FW_NAME                  ((0U << ELT_IDENTIFIER_POS) | TYPE_DATA_STRING)
#define  MC_REG_CTRL_STAGE_NAME          ((1U << ELT_IDENTIFIER_POS) | TYPE_DATA_STRING)
#define  MC_REG_PWR_STAGE_NAME           ((2U << ELT_IDENTIFIER_POS) | TYPE_DATA_STRING)
#define  MC_REG_MOTOR_NAME               ((3U << ELT_IDENTIFIER_POS) | TYPE_DATA_STRING)

#define  MC_REG_GLOBAL_CONFIG            ((0U << ELT_IDENTIFIER_POS) | TYPE_DATA_RAW)
#define  MC_REG_MOTOR_CONFIG             ((1U << ELT_IDENTIFIER_POS) | TYPE_DATA_RAW)
#define  MC_REG_APPLICATION_CONFIG       ((2U << ELT_IDENTIFIER_POS) | TYPE_DATA_RAW)
#define  MC_REG_FOCFW_CONFIG             ((3U << ELT_IDENTIFIER_POS) | TYPE_DATA_RAW)
#define  MC_REG_SCALE_CONFIG             ((4U << ELT_IDENTIFIER_POS) | TYPE_DATA_RAW)
#define  MC_REG_SPEED_RAMP               ((6U << ELT_IDENTIFIER_POS) | TYPE_DATA_RAW)
#define  MC_REG_TORQUE_RAMP              ((7U << ELT_IDENTIFIER_POS) | TYPE_DATA_RAW)
#define  MC_REG_REVUP_DATA               ((8U << ELT_IDENTIFIER_POS) | TYPE_DATA_RAW) /* Configure all steps*/
#define  MC_REG_CURRENT_REF              ((13U << ELT_IDENTIFIER_POS) | TYPE_DATA_RAW)
#define  MC_REG_POSITION_RAMP            ((14U << ELT_IDENTIFIER_POS) | TYPE_DATA_RAW)
#define  MC_REG_ASYNC_UARTA              ((20U << ELT_IDENTIFIER_POS) | TYPE_DATA_RAW)
#define  MC_REG_ASYNC_UARTB              ((21U << ELT_IDENTIFIER_POS) | TYPE_DATA_RAW)
#define  MC_REG_ASYNC_STLNK              ((22U << ELT_IDENTIFIER_POS) | TYPE_DATA_RAW)
#define  MC_REG_HT_HEW_PINS              ((28U << ELT_IDENTIFIER_POS) | TYPE_DATA_RAW)
#define  MC_REG_HT_CONNECTED_PINS        ((29U << ELT_IDENTIFIER_POS) | TYPE_DATA_RAW)
#define  MC_REG_HT_PHASE_SHIFT           ((30U << ELT_IDENTIFIER_POS) | TYPE_DATA_RAW)
#define  MC_REG_BEMF_ADC_CONF            ((31U << ELT_IDENTIFIER_POS) | TYPE_DATA_RAW)

# MCP register type
class EMcpRegType( Enum ):
	Reserved = 0
	Bit8 = 1
	Bit16 = 2
	Bit32 = 3
	Text = 4
	RawStruct = 5
	Reserved2 = 6
	Reserved3 = 7
	pass

def packRegId8bit( id: EMcp8BitReg, motorNo ) -> bytes:
	packedBytes = bitstruct.pack( 'u10u3u3', id, EMcpRegType.Bit8, motorNo )
	return packedBytes

def packRegId16bit( id: EMcp16BitReg, motorNo ) -> bytes:
	packedBytes = bitstruct.pack( 'u10u3u3', id, EMcpRegType.Bit16, motorNo )
	return packedBytes

def unpackRegId( regId: bytes ) -> tuple[ int, EMcpRegType, int ]:
	id, regTypeRaw, motorNo = bitstruct.unpack( 'u10u3u3', regId )
	regtype = EMcpRegType( regTypeRaw )
	return id, regtype, motorNo