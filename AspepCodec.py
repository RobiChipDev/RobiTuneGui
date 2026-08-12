from enum import Enum
import bitstruct
from AspepCrc import AspepCrc4, AspepCrc16

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
	def __init__( self ):
		# create an empty packet
		self.empty()
		pass

	def __init__( self, type, *args ):
		# create a packet based on assigned type
		self.__init__()
		self.set( type, args )		
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
				self.ver = args[ 0 ]
				self.enCrc = args[ 1 ]
				self.rxsMax = args[ 2 ]
				self.txsMax = args[ 3 ]
				self.txaMax = args[ 4 ]
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

	def encode( self ) -> tuple[ bytes, bytes ]:
		match self.type:
			case EAspepPktType.Beacon:
				packedByte = self.__encodeBeacon()
				return packedByte

			case EAspepPktType.Ping:
				packedByte = self.__encodePing()
				return packedByte

			case EAspepPktType.Request:
				fPacket, sPacket = self.__encodeRequest()
				return fPacket, sPacket

		return bytes(), bytes()

	def decode( self, bufLen, buf ) -> None:
		# create a packet based on input buffer
		self.__init__()
		type = bitstruct.unpack( 'u4', buf, allow_truncated = True )
			
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
	
	def __encodeBeacon( self ) -> bytes:
		# |-4 bits-|-3 bits--|-1 bits-|-6 bits--|-7 bits--|-7 bits--|-4 bits-|
		# |-Type---|-version-|-CRC_EN-|-RXS Max-|-TXS Max-|-TXA Max-|-CRCH---|
		# No payload
		packedByte = bitstruct.pack( 'u4u3u1u6u7u7', self.type, self.ver, self.enCrc, self.rxsMax, self.txsMax, self.txaMax )
		self.crcH = AspepCrc4().computeCrc( int.from_bytes( packedByte ) )

		packedByte = bitstruct.pack( 'u4u3u1u6u7u7u4', self.type, self.ver, self.enCrc, self.rxsMax, self.txsMax, self.txaMax, self.crcH )
		return packedByte

	def __encodePing( self ) -> bytes:
		# |-4 bits-|-2 bits-|-2 bits-|-4 bits-|-16 bits------|-4 bits-|
		# |-Type---|-C------|-N------|-LLID---|-Packet Numer-|-CRCH---|
		# No payload
		packedByte = bitstruct.pack( 'u4u2u2u4u16', self.type, self.c, self.n, self.LLID, self.pktNum )
		self.crcH = AspepCrc4().computeCrc( int.from_bytes( packedByte ) )

		packedByte = bitstruct.pack( 'u4u2u2u4u16u4', self.type, self.c, self.n, self.LLID, self.pktNum, self.crcH )
		return packedByte

	def __encodeError( self ) -> bytes:
		# |-4 bits-|-4 bits-|-8 bits--|-8 bits--|-4 bits-|-4 bits-|
		# |-Type---|-Resrv--|-ErrCode-|-ErrCode-|-Resrv--|-CRCH---|
		# No payload
		packedByte = bitstruct.pack( 'u4u4u8u8u4', self.type, 0, self.err, self.err2, 0 )
		self.crcH = AspepCrc4().computeCrc( int.from_bytes( packedByte ) )

		packedByte = bitstruct.pack( 'u4u4u8u8u4u4', self.type, 0, self.err, self.err2, 0, self.crcH )
		return packedByte

	def __encodeRequest( self ) -> tuple[ bytes, bytes ]:
		# |-4 bits-|-13 bits-|-11 bits-|-4 bits-| Intra Pkt Pause |-N bytes-|-2 bytes-|
		# |-Type---|-PL Len--|-Resrv---|-CRCH---|                 |-Payload-|-CRC-----|
		
		# prepare header
		# payloadLen: is set to the number of bytes of the Payload part of the packet
		packedByte = bitstruct.pack( 'u4u13u11', self.type, self.payloadLen, 0 )
		self.crcH = AspepCrc4().computeCrc( int.from_bytes( packedByte ) )
		fPacket = bitstruct.pack( 'u4u13u11u4', self.type, self.payloadLen, 0, self.crcH )

		self.crc = AspepCrc16().computeCrc( int.from_bytes( self.payload ) )
		sPacket = self.payload + self.crc
		return fPacket, sPacket

	def __encodeAsync( self ) -> tuple[ bytes, bytes ]:
		# |-4 bits-|-13 bits-|-11 bits-|-4 bits-| Intra Pkt Pause |-N bytes-|-2 bytes-|
		# |-Type---|-PL Len--|-Resrv---|-CRCH---|                 |-Payload-|-CRC-----|

		# the ASYNC packet is totally identical to REQUEST packet
		return self.__encodeAsync()

	def __encodeResponse( self ) -> tuple[ bytes, bytes ]:
		# |-4 bits-|-13 bits-|-11 bits-|-4 bits-| Intra Pkt Pause |-N bytes-|-2 bytes-|
		# |-Type---|-PL Len--|-Resrv---|-CRCH---|                 |-Payload-|-CRC-----|
				
		# prepare header
		# payloadLen: is set to the number of bytes of the Payload part of the packet
		packedByte = bitstruct.pack( 'u4u13u11', self.type, self.payloadLen, 0 )
		self.crcH = AspepCrc4().computeCrc( int.from_bytes( packedByte ) )
		fPacket = bitstruct.pack( 'u4u13u11u4', self.type, self.payloadLen, 0, self.crcH )
		
		self.crc = AspepCrc16().computeCrc( int.from_bytes( self.payload ) )
		sPacket = self.payload + self.crc
		return fPacket, sPacket

	def __decodeBeacon( self, packedByte ) -> None:
		# |-4 bits-|-3 bits--|-1 bits-|-6 bits--|-7 bits--|-7 bits--|-4 bits-|
		# |-Type---|-version-|-CRC_EN-|-RXS Max-|-TXS Max-|-TXA Max-|-CRCH---|
		# No payload
		self.type, self.ver, self.enCrc, self.rxsMax, self.txsMax, self.txaMax,	self.crcH = bitstruct.unpack( 'u4u3u1u6u7u7u4', packedByte )
		pass 

	def __decodePing( self, packedByte ) -> None:
		# |-4 bits-|-2 bits-|-2 bits-|-4 bits-|-16 bits------|-4 bits-|
		# |-Type---|-C------|-N------|-LLID---|-Packet Numer-|-CRCH---|
		# No payload
		self.type, self.c, self.n, self.LLID, self.pktNum, self.crcH = bitstruct.unpack( 'u4u2u2u4u16u4', packedByte )
		pass

	def __decodeError( self, packedByte ) -> None:
		# |-4 bits-|-4 bits-|-8 bits--|-8 bits--|-4 bits-|-4 bits-|
		# |-Type---|-Resrv--|-ErrCode-|-ErrCode-|-Resrv--|-CRCH---|
		# No payload
		self.type, _, self.err, self.err2, _, self.crcH = bitstruct.unpack( 'u4u4u8u8u4u4', packedByte )
		pass

	def __decodeResponse( self, packedByte ) -> None:
		# |-4 bits-|-13 bits-|-11 bits-|-4 bits-| Intra Pkt Pause |-N bytes-|-2 bytes-|
		# |-Type---|-PL Len--|-Resrv---|-CRCH---|                 |-Payload-|-CRC-----|

		# separated into two immutable bytes
		headerPt = packedByte[ :4 ]
		payloadPt = packedByte[ 4: ]

		self.type, self.payloadLen, _, self.crcH, _, self.crcH = bitstruct.unpack( 'u4u4u8u8u4u4', headerPt )
		self.payload = payloadPt[ :-2 ]
		self.crc = payloadPt[ -2: ]
		pass
