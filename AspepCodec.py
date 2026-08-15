from enum import Enum

################################
# Author: Boyce, RobiChip
# Date: 2026/08/12
# Description:
# Data are sent in little-endian order: least significant bits of bytes are transmitted first.
# 
# All ASPEP packets share the same structure, depicted in the following profile:
# |-4 bytes-|--------------------|-N bytes-|-2 bytes-|
# |-Header--| Intra Packet Pause |-Payload-|-CRC-----|
#
# Header:
# |-4 bits-----|-24 bits--------|-4 bits-|
# |-Pkt Type---|-Header Content-|-CRCH---|
# 
# Intra Packet Pause: 
# It would typically be 1 ms in the Controller to Performer direction and 0 ms in the Performer to Controller direction.
#

# constant and definition
CRC4_LUT = ( \
    0x0, 0x7, 0xE, 0x9, \
    0xB, 0xC, 0x5, 0x2, \
    0x1, 0x6, 0xF, 0x8, \
    0xA, 0xD, 0x4, 0x3, \
)

class EAspepPktType( Enum ):
	Undefine = 0
	Beacon = 5		# "Control" channel. Used by Connection procedure & Recovery procedure
	Ping = 6		# "Control" channel. Used by Connection procedure & Recovery procedure & Recovery procedure
	Error = 15		# "Control" channel. Only sent by Performer for error reporting
	Request = 9		# "Synchronous" channel. Only sent by Controller for synchronous transaction
	Response = 10	# "Synchronous" channel. Only sent Performer for synchronous transaction
	Async = 9		# "Asynchronous" channel. Only sent by Performer
	pass

class CPktDscrpt():
	def __init__( self, type: EAspepPktType, *args ):
		# create a packet based on assigned type
		self.empty()
		self.set( type, *args )		
		pass

	def __eq__( self, target ) -> bool:
		if self.type != target.type:
			return False

		# BEACON
		if self.ver == target.ver and self.enCrc == target.enCrc and \
			self.rxsMax == target.rxsMax and self.txsMax == target.txsMax and \
				self.txaMax == target.txaMax:
			return True

		# PING
		if self.c == target.c and self.n == target.n and \
			self.LLID == target.LLID and self.pktNum == target.pktNum and \
				self.crcH == target.crcH:
			return True

		# REQUEST / RESPONSE / ASYNC

		# ERROR
		
		return False
	
	def empty( self ) -> None:
		self.type = EAspepPktType.Undefine
		
		# fields used by BEACON
		self.ver = 0	# version number of the ASPEP protocol. should be "0"
		self.enCrc = 0	# supports for computing a CRC on the payload of ASPEP packets. Set to 0 otherwise.
		self.rxsMax = 0	# maximum payload size of a REQUEST packet allowed on the connection
		self.txsMax = 0	# maximum payload size of a REPONSE packet allowed in the connection
		self.txaMax = 0	# maximum payload size of an ASYN packet allowed in the connection

		# fields used by PING
		self.c = 0		# Controller does not use the C field. C field is set to 1 by the Performer to indicate that it is already configured
		self.n = 0		# Controller does not use the N field. N field is set, by the Performer to the last bit of the number of the next expected REQUEST packet from the Performer
		self.LLID = 0	# Controller does not use the LIID field. The LIID field identifies the ASPEP Layer instance (and the physical serial interface) on which the packet is sent
		self.pktNum = 0	# The Packet Number field is used in the Keep-Alive procedure. It is set by the Controller to to a value that is incremented on each PING packet it sends.

		# fields used by ERROR
		self.err = 0
		self.err2 = 0

		# fields used by REQUEST, RESPONSE, ASYNC
		self.payloadLen = 0
		self.payload = bytes()

		# fields for CRC
		self.crc = 0	# 16 bits crc for payload
		self.crcH = 0	# 4 bits crc for header
		pass

	def set( self, type, *args ) -> None:
		self.type = type
		if len( args ) == 0:
			return

		match type:
			case EAspepPktType.Beacon:
				self.ver = args[ 0 ] & 0x07
				self.enCrc = args[ 1 ]
				self.rxsMax = args[ 2 ] & 0x3F
				self.txsMax = args[ 3 ] & 0x7F
				self.txaMax = args[ 4 ] & 0x7F
				pass
			
			case EAspepPktType.Ping:
				self.c = args[ 0 ]
				self.n = args[ 1 ]
				self.LLID = args[ 2 ]
				self.pktNum = args[ 3 ]
				pass

			case EAspepPktType.Request:
				self.payloadLen = args[ 0 ]
				self.payload = args[ 1 ]
				pass
		pass

	def encode( self, *args ) -> tuple[ bytes, bytes ]:
		match self.type:
			case EAspepPktType.Beacon:
				packedBytes = self.__encodeBeacon()
				return packedBytes

			case EAspepPktType.Ping:
				packedBytes = self.__encodePing()
				return packedBytes

			case EAspepPktType.Request:
				fPacket, sPacket = self.__encodeRequest( args[ 0 ] )
				return fPacket, sPacket

		return bytes(), bytes()

	def decode( self, bufLen, buf: bytes ) -> None:
		# create a packet based on input buffer
		self.empty()
		type = EAspepPktType( buf[ 0 ] & 0x0F )
			
		if bufLen <= 0:
			raise ValueError( "the buffer length is <= 0" )
	
		match type:
			case EAspepPktType.Beacon:
				self.__decodeBeacon( buf )
				pass
	
			case EAspepPktType.Ping:
				self.__decodePing( buf )
				pass
	
			case EAspepPktType.Error:
				self.__decodeError( buf )
				pass
	
			case EAspepPktType.Response:
				self.__decodeResponse( buf )
				pass
	
			case _:
				pass
		pass

# private functions

# ============================================================
# CRC-4 engine for ASPEP header generated by ChatGPT
#   - CRC over lower 28 bits
#   - CRC inserted into upper 4 bits [31:28]
#   - CRC-4 from CCITT-G.704 (X^4 + X + 1)
# ============================================================
	def __calcCrcH( self, header_28: int ) -> int:
		crc = 0
		h = header_28 & 0x0FFFFFFF
		for shift in range( 0, 28, 4 ):
			crc = CRC4_LUT[ crc ^ ( ( h >> shift ) & 0xF ) ]
		return crc

# ============================================================
# CRC-16 engine for ASPEP header generated by ChatGPT
#   - CRC over payload bytes
#   - CRC-16 from CCITT-X.25 standard (x^16 + x^12 + x^5 + 1)
#	- x^16 + x^12 + x^5 + 1 -> poly = 0x8408
# ============================================================

	def __calcCrcP( self, payload: bytes ) -> int:
		crc = 0x0000
		for b in payload:
			crc ^= b
			for _ in range( 8 ):
				if crc & 0x0001:
					crc = ( crc >> 1 ) ^ 0x8408
				else:
					crc >>= 1
				crc &= 0xFFFF
		crc ^= 0xFFFF
		return crc

	def __encodeBeacon( self ) -> bytes:
		# |-4 bits-|-3 bits--|-1 bits-|-6 bits--|-7 bits--|-7 bits--|-4 bits-|
		# |-Type---|-version-|-CRC_EN-|-RXS Max-|-TXS Max-|-TXA Max-|-CRCH---|
		# No payload
		header = self.type.value | ( self.ver << 4 ) | ( int( self.enCrc ) << 7 )
		header |= ( self.rxsMax << 8 ) | ( self.txsMax << 14 ) | ( self.txaMax << 21 )
		self.crcH = self.__calcCrcH( header )

		header |= ( self.crcH << 28 )
		byte0 = header & 0xFF
		byte1 = ( header >> 8 ) & 0xFF
		byte2 = ( header >> 16 ) & 0xFF
		byte3 = ( header >> 24 ) & 0xFF
		packedBytes = bytes( [ byte0, byte1, byte2, byte3] )
		return packedBytes

	def __encodePing( self ) -> bytes:
		# |-4 bits-|-2 bits-|-2 bits-|-4 bits-|-16 bits------|-4 bits-|
		# |-Type---|-C------|-N------|-LLID---|-Packet Numer-|-CRCH---|
		# No payload
		header = self.type.value | ( self.c << 4 ) | ( self.n << 6 )
		header |= ( self.LLID << 8 ) | ( self.pktNum << 12 )
		self.crcH = self.__calcCrcH( header )

		header |= ( self.crcH << 28 )
		byte0 = header & 0xFF
		byte1 = ( header >> 8 ) & 0xFF
		byte2 = ( header >> 16 ) & 0xFF
		byte3 = ( header >> 24 ) & 0xFF
		packedBytes = bytes( [ byte0, byte1, byte2, byte3] )
		return packedBytes

	def __encodeError( self ) -> bytes:
		# |-4 bits-|-4 bits-|-8 bits--|-8 bits--|-4 bits-|-4 bits-|
		# |-Type---|-Resrv--|-ErrCode-|-ErrCode-|-Resrv--|-CRCH---|
		# No payload
		header = self.type.value | ( 0 << 4 ) | ( self.err << 8 ) | ( self.err2 << 16 )
		self.crcH = self.__calcCrcH( header )

		header |= ( self.crcH << 28 )
		byte0 = header & 0xFF
		byte1 = ( header >> 8 ) & 0xFF
		byte2 = ( header >> 16 ) & 0xFF
		byte3 = ( header >> 24 ) & 0xFF
		packedBytes = bytes( [ byte0, byte1, byte2, byte3] )
		return packedBytes

	def __encodeRequest( self, enCrc: bool = False ) -> tuple[ bytes, bytes ]:
		# |-4 bits-|-13 bits-|-11 bits-|-4 bits-| Intra Pkt Pause |-N bytes-|-2 bytes-|
		# |-Type---|-PL Len--|-Resrv---|-CRCH---|                 |-Payload-|-CRC-----|
		
		# prepare header
		# payloadLen: is set to the number of bytes of the Payload part of the packet
		header = self.type.value | ( self.payloadLen << 4 ) 
		self.crcH = self.__calcCrcH( header )
		self.crc = self.__calcCrcP( self.payload )

		header |= ( self.crcH << 28 )
		byte0 = header & 0xFF
		byte1 = ( header >> 8 ) & 0xFF
		byte2 = ( header >> 16 ) & 0xFF
		byte3 = ( header >> 24 ) & 0xFF
		fPacket = bytes( [ byte0, byte1, byte2, byte3 ] )
		sPacket = ( self.payload + self.crc ) if ( enCrc == True ) else self.payload
		return fPacket, sPacket

	def __encodeAsync( self, enCrc: bool = False ) -> tuple[ bytes, bytes ]:
		# |-4 bits-|-13 bits-|-11 bits-|-4 bits-| Intra Pkt Pause |-N bytes-|-2 bytes-|
		# |-Type---|-PL Len--|-Resrv---|-CRCH---|                 |-Payload-|-CRC-----|

		# the ASYNC packet is totally identical to REQUEST packet
		return self.__encodeAsync( enCrc )

	def __encodeResponse( self, enCrc: bool = False ) -> tuple[ bytes, bytes ]:
		# |-4 bits-|-13 bits-|-11 bits-|-4 bits-| Intra Pkt Pause |-N bytes-|-2 bytes-|
		# |-Type---|-PL Len--|-Resrv---|-CRCH---|                 |-Payload-|-CRC-----|
				
		# the RESPONSE packet is totally identical to REQUEST packet
		return self.__encodeAsync( enCrc )

	def __decodeBeacon( self, packedBytes: bytes ) -> None:
		# |-4 bits-|-3 bits--|-1 bits-|-6 bits--|-7 bits--|-7 bits--|-4 bits-|
		# |-Type---|-version-|-CRC_EN-|-RXS Max-|-TXS Max-|-TXA Max-|-CRCH---|
		# No payload
		byte0 = packedBytes[ 0 ]
		byte1 = packedBytes[ 1 ]
		byte2 = packedBytes[ 2 ]
		byte3 = packedBytes[ 3 ]

		self.type = EAspepPktType( byte0 & 0x0F )
		self.ver = ( byte0 >> 4 ) & 0x07
		self.enCrc = ( byte0 >> 7 ) & 0x01

		buf = int( byte1 ) | ( int( byte2 ) << 8 ) | ( int( byte3 ) << 16 )
		self.rxsMax = buf & 0x3F
		self.txsMax = ( buf >> 6 ) & 0x7F
		self.txaMax = ( buf >> 13 ) & 0x7F
		self.crcH = ( buf >> 20 ) & 0x0F
		pass 

	def __decodePing( self, packedBytes ) -> None:
		# |-4 bits-|-2 bits-|-2 bits-|-4 bits-|-16 bits------|-4 bits-|
		# |-Type---|-C------|-N------|-LLID---|-Packet Numer-|-CRCH---|
		# No payload
		byte0 = packedBytes[ 0 ]
		byte1 = packedBytes[ 1 ]
		byte2 = packedBytes[ 2 ]
		byte3 = packedBytes[ 3 ]
		
		self.type = EAspepPktType( byte0 & 0x0F )
		self.c = ( byte0 >> 4 ) & 0x03
		self.n = ( byte0 >> 6 ) & 0x03
		
		buf = int( byte1 ) | ( int( byte2 ) << 8 ) | ( int( byte3 ) << 16 )
		self.LLID = buf & 0x0F
		self.pktNum = ( buf >> 4 ) & 0xFFFF
		self.crcH = ( buf >> 20 ) & 0x0F
		pass

	def __decodeError( self, packedBytes ) -> None:
		# |-4 bits-|-4 bits-|-8 bits--|-8 bits--|-4 bits-|-4 bits-|
		# |-Type---|-Resrv--|-ErrCode-|-ErrCode-|-Resrv--|-CRCH---|
		# No payload
		byte0 = packedBytes[ 0 ]
		byte1 = packedBytes[ 1 ]
		byte2 = packedBytes[ 2 ]
		byte3 = packedBytes[ 3 ]
				
		self.type = EAspepPktType( byte0 & 0x0F )
		self.err = byte1
		self.err2 = byte2
		self.crcH = ( byte3 >> 4 ) & 0x0F
		pass

	def __decodeResponse( self, packedBytes ) -> None:
		# |-4 bits-|-13 bits-|-11 bits-|-4 bits-| Intra Pkt Pause |-N bytes-|-2 bytes-|
		# |-Type---|-PL Len--|-Resrv---|-CRCH---|                 |-Payload-|-CRC-----|

		# separated into two immutable bytes
		headerPt = packedBytes[ :4 ]
		payloadPt = packedBytes[ 4: ]

		# decode header part
		buf = int( headerPt[ 0 ] ) \
			| ( int( headerPt[ 1 ] ) << 8 ) \
			| ( int( headerPt[ 2 ] ) << 16 ) \
			| ( int( headerPt[ 3 ] ) << 24 )
		self.type = EAspepPktType( buf & 0x0F )
		self.payloadLen = ( buf >> 4 ) & 0x1FFF
		self.crcH = ( buf >> 28 ) & 0x0F

		if len( payloadPt ) > self.payloadLen:
			# there are 2 bytes crc appended to the end of payload
			self.payload = payloadPt[ :-2 ]
			self.crc = payloadPt[ -2: ]
			pass
		else:
			# no 2 bytes crc appended
			self.payload = payloadPt
			self.crc = 0
			pass
		pass
