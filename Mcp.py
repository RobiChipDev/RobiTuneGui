################################
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