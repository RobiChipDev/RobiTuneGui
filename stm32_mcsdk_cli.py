#!/usr/bin/env python3
"""
stm32_mcsdk_cli.py
Command-line Controller for STM32 MCSDK 6.x Motor Control Protocol (MCP)
over ASPEP/UART.

Dependencies:
    pip install pyserial

Examples:
    python stm32_mcsdk_cli.py ports
    python stm32_mcsdk_cli.py -p COM7 connect
    python stm32_mcsdk_cli.py -p COM7 version
    python stm32_mcsdk_cli.py -p COM7 raw-mcp --hex "00 00"
    python stm32_mcsdk_cli.py -p COM7 command --id 0x0006 --motor 1
    python stm32_mcsdk_cli.py -p COM7 get --data-id 0x1234
    python stm32_mcsdk_cli.py -p COM7 set --data-id 0x1234 --value-hex "78 56 34 12"

Notes:
- MCSDK 6.x uses MCP over ASPEP.
- MCP command header is a 16-bit little-endian word:
      bits 15..3 : Command ID
      bits  2..0 : Motor selector (0=global/non-motor, 1=Motor 1, 2=Motor 2...)
- GET_MCP_VERSION command ID is 0.
- SET_DATA_ELEMENT command ID is 1.
- GET_DATA_ELEMENT command ID is 2.
- Register/Data Element IDs are project/MCSDK generated. Supply the exact 16-bit
  Data Element ID from your generated register interface / protocol documentation.
"""

from __future__ import annotations

import argparse
import struct
import sys
import time
from dataclasses import dataclass
from typing import Optional

try:
    import serial
    from serial.tools import list_ports
except ImportError:
    serial = None
    list_ports = None


# --------------------------
# ASPEP constants / CRC4
# --------------------------

ASPEP_BEACON = 0x5
ASPEP_PING = 0x6
ASPEP_DATA = 0x9
ASPEP_ASYNC = 0xA

CRC4_LUT = (
    0x0, 0x7, 0xE, 0x9,
    0xB, 0xC, 0x5, 0x2,
    0x1, 0x6, 0xF, 0x8,
    0xA, 0xD, 0x4, 0x3,
)

# Capability-probe beacon used by the Controller to request the performer's
# maximum supported capabilities. Header CRC is 0xA -> F5 FF FF AF.
ASPEP_CAPABILITY_PROBE = bytes.fromhex("F5 FF FF AF")

MCP_GET_VERSION_ID = 0x0000
MCP_SET_DATA_ELEMENT_ID = 0x0001
MCP_GET_DATA_ELEMENT_ID = 0x0002

# Common response value in MCSDK. We deliberately do not make success depend
# on this constant; raw status is always displayed.
MCP_CMD_OK = 0x00


class ProtocolError(RuntimeError):
    pass


def crc4_28bits(header_28: int) -> int:
    """ST ASPEP CRC4 over the lower 28 header bits, nibble by nibble."""
    crc = 0
    h = header_28 & 0x0FFFFFFF
    for shift in range(0, 28, 4):
        crc = CRC4_LUT[crc ^ ((h >> shift) & 0xF)]
    return crc


def with_header_crc(header_28: int) -> int:
    h = header_28 & 0x0FFFFFFF
    return h | (crc4_28bits(h) << 28)


def make_data_header(payload_len: int, packet_type: int = ASPEP_DATA) -> bytes:
    if not 0 <= payload_len <= 0x1FFF:
        raise ValueError("ASPEP payload length must fit in 13 bits (0..8191).")
    header = packet_type | (payload_len << 4)
    return struct.pack("<I", with_header_crc(header))


def make_ping_header() -> bytes:
    # Basic ping: type=6, all option fields zero.
    return struct.pack("<I", with_header_crc(ASPEP_PING))


def parse_aspep_header(raw: bytes) -> dict:
    if len(raw) != 4:
        raise ProtocolError(f"ASPEP header must be 4 bytes, got {len(raw)}.")
    h = struct.unpack("<I", raw)[0]
    received_crc = (h >> 28) & 0xF
    expected_crc = crc4_28bits(h)
    ptype = h & 0xF
    return {
        "raw": h,
        "type": ptype,
        "payload_len": (h >> 4) & 0x1FFF if ptype in (ASPEP_DATA, ASPEP_ASYNC) else 0,
        "crc_received": received_crc,
        "crc_expected": expected_crc,
        "crc_ok": received_crc == expected_crc,
    }


@dataclass
class AspepPacket:
    header: bytes
    packet_type: int
    payload: bytes

    def hex(self) -> str:
        return (self.header + self.payload).hex(" ")


class McsdkSerialController:
    def __init__(
        self,
        port: str,
        baudrate: int = 115200,
        timeout: float = 1.0,
        intra_packet_pause_ms: float = 1.0,
        verbose: bool = False,
    ):
        if serial is None:
            raise RuntimeError("pyserial is not installed. Run: pip install pyserial")
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.intra_packet_pause = intra_packet_pause_ms / 1000.0
        self.verbose = verbose
        self.ser: Optional[serial.Serial] = None

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()

    def log(self, msg: str) -> None:
        if self.verbose:
            print(msg, file=sys.stderr)

    def open(self) -> None:
        if self.ser and self.ser.is_open:
            return
        self.ser = serial.Serial(
            port=self.port,
            baudrate=self.baudrate,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=0.05,
            write_timeout=self.timeout,
        )
        # Give USB-UART bridges a short settling interval.
        time.sleep(0.05)
        self.ser.reset_input_buffer()
        self.ser.reset_output_buffer()

    def close(self) -> None:
        if self.ser:
            self.ser.close()
            self.ser = None

    def _read_exact(self, n: int, timeout: Optional[float] = None) -> bytes:
        if not self.ser:
            raise RuntimeError("Serial port is not open.")
        deadline = time.monotonic() + (self.timeout if timeout is None else timeout)
        out = bytearray()
        while len(out) < n:
            chunk = self.ser.read(n - len(out))
            if chunk:
                out.extend(chunk)
                continue
            if time.monotonic() >= deadline:
                raise TimeoutError(f"Timeout reading {n} bytes; received {len(out)}: {out.hex(' ')}")
        return bytes(out)

    def _write(self, data: bytes) -> None:
        if not self.ser:
            raise RuntimeError("Serial port is not open.")
        self.log(f"TX: {data.hex(' ')}")
        self.ser.write(data)
        self.ser.flush()

    def read_packet(self, timeout: Optional[float] = None) -> AspepPacket:
        header = self._read_exact(4, timeout)
        info = parse_aspep_header(header)
        if not info["crc_ok"]:
            raise ProtocolError(
                f"Bad ASPEP header CRC: {header.hex(' ')} "
                f"(rx={info['crc_received']:X}, calc={info['crc_expected']:X})"
            )
        payload_len = info["payload_len"]
        payload = self._read_exact(payload_len, timeout) if payload_len else b""
        self.log(f"RX: {(header + payload).hex(' ')}")
        return AspepPacket(header, info["type"], payload)

    def connect_aspep(self, do_ping: bool = True) -> dict:
        """
        Controller connection sequence:
        1. Send capability-probe BEACON.
        2. Receive performer's BEACON.
        3. Echo performer's BEACON to accept negotiated capabilities.
        4. Receive final BEACON when supplied by firmware.
        5. Optional PING.
        """
        if not self.ser:
            self.open()
        self.ser.reset_input_buffer()

        self._write(ASPEP_CAPABILITY_PROBE)
        performer = self.read_packet()

        if performer.packet_type != ASPEP_BEACON:
            raise ProtocolError(
                f"Expected ASPEP BEACON (type 0x5), got type 0x{performer.packet_type:X}: "
                f"{performer.hex()}"
            )

        # Echo the negotiated performer beacon.
        self._write(performer.header)

        # Some MCSDK versions/ports return a final beacon; some are immediately
        # ready for data. Read it opportunistically with a short timeout.
        final_beacon = None
        try:
            candidate = self.read_packet(timeout=min(0.15, self.timeout))
            if candidate.packet_type == ASPEP_BEACON:
                final_beacon = candidate
            else:
                # Unexpected early packet: retain only in diagnostic output.
                self.log(f"ASPEP post-beacon packet: {candidate.hex()}")
        except TimeoutError:
            pass

        ping_reply = None
        if do_ping:
            self._write(make_ping_header())
            try:
                ping_reply = self.read_packet(timeout=min(0.30, self.timeout))
                if ping_reply.packet_type != ASPEP_PING:
                    self.log(f"Expected PING reply; received type 0x{ping_reply.packet_type:X}")
            except TimeoutError:
                # Ping is a diagnostic; a successful beacon negotiation is enough
                # to continue on firmware variants that do not answer this probe.
                self.log("No PING response; continuing after successful BEACON negotiation.")

        return {
            "performer_beacon": performer.header,
            "final_beacon": final_beacon.header if final_beacon else None,
            "ping_reply": ping_reply.header if ping_reply else None,
        }

    def send_aspep_data(self, payload: bytes) -> AspepPacket:
        header = make_data_header(len(payload), ASPEP_DATA)
        # ASPEP controller sends header first, then payload after a short
        # intra-packet pause. 1 ms is conservative for common UART setups.
        self._write(header)
        if payload:
            if self.intra_packet_pause > 0:
                time.sleep(self.intra_packet_pause)
            self._write(payload)

        response = self.read_packet()
        if response.packet_type not in (ASPEP_DATA, ASPEP_ASYNC):
            raise ProtocolError(
                f"Expected ASPEP data response, got type 0x{response.packet_type:X}: "
                f"{response.hex()}"
            )
        return response

    @staticmethod
    def make_mcp_command(command_id: int, motor: int = 0, payload: bytes = b"") -> bytes:
        if not 0 <= command_id <= 0x1FFF:
            raise ValueError("MCP command ID must fit in 13 bits (0..0x1FFF).")
        if not 0 <= motor <= 7:
            raise ValueError("Motor selector must be 0..7.")
        command_word = ((command_id & 0x1FFF) << 3) | (motor & 0x7)
        return struct.pack("<H", command_word) + payload

    def transact_mcp(self, command_id: int, motor: int = 0, payload: bytes = b"") -> bytes:
        req = self.make_mcp_command(command_id, motor, payload)
        response = self.send_aspep_data(req)
        return response.payload

    def transact_raw_mcp(self, payload: bytes) -> bytes:
        return self.send_aspep_data(payload).payload

    def get_mcp_version(self) -> tuple[int, int, bytes]:
        rsp = self.transact_mcp(MCP_GET_VERSION_ID, motor=0)
        if len(rsp) < 5:
            raise ProtocolError(
                f"GET_MCP_VERSION expected >=5 response bytes (4 data + status), got "
                f"{len(rsp)}: {rsp.hex(' ')}"
            )
        version = struct.unpack_from("<I", rsp, 0)[0]
        status = rsp[-1]
        return version, status, rsp

    def get_data_element(self, data_id: int, motor: int = 0) -> tuple[bytes, int]:
        # Data Element ID itself includes its target/type/register encoding in MCSDK.
        payload = struct.pack("<H", data_id & 0xFFFF)
        rsp = self.transact_mcp(MCP_GET_DATA_ELEMENT_ID, motor=motor, payload=payload)
        if not rsp:
            raise ProtocolError("Empty MCP response.")
        return rsp[:-1], rsp[-1]

    def set_data_element(self, data_id: int, value: bytes, motor: int = 0) -> tuple[bytes, int]:
        payload = struct.pack("<H", data_id & 0xFFFF) + value
        rsp = self.transact_mcp(MCP_SET_DATA_ELEMENT_ID, motor=motor, payload=payload)
        if not rsp:
            raise ProtocolError("Empty MCP response.")
        return rsp[:-1], rsp[-1]


def parse_int(text: str) -> int:
    return int(text, 0)


def parse_hex_bytes(text: str) -> bytes:
    cleaned = (
        text.replace("0x", "")
        .replace("0X", "")
        .replace(",", " ")
        .replace(":", " ")
        .replace("-", " ")
    )
    tokens = cleaned.split()
    if len(tokens) == 1 and len(tokens[0]) > 2:
        s = tokens[0]
        if len(s) % 2:
            raise argparse.ArgumentTypeError("Continuous hex string must contain an even number of digits.")
        try:
            return bytes.fromhex(s)
        except ValueError as e:
            raise argparse.ArgumentTypeError(str(e)) from e
    try:
        return bytes(int(tok, 16) for tok in tokens)
    except ValueError as e:
        raise argparse.ArgumentTypeError(f"Invalid hex byte string: {text}") from e


def status_text(status: int) -> str:
    return f"0x{status:02X}" + (" (CMD_OK)" if status == MCP_CMD_OK else "")


def self_test() -> None:
    vectors = {
        "capability beacon": (struct.pack("<I", with_header_crc(0x0FFFFFF5)), "f5 ff ff af"),
        "ping": (make_ping_header(), "06 00 00 60"),
        "data len=4": (make_data_header(4), "49 00 00 70"),
        "data len=15": (make_data_header(15), "f9 00 00 30"),
    }
    failed = False
    for name, (got, expected) in vectors.items():
        ok = got.hex(" ") == expected
        print(f"{name:18s}: {got.hex(' ')}  {'OK' if ok else 'FAIL expected ' + expected}")
        failed |= not ok
    if failed:
        raise SystemExit(2)


def add_serial_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("-p", "--port", help="Serial port, e.g. COM7 or /dev/ttyACM0")
    p.add_argument("-b", "--baudrate", type=int, default=115200, help="UART baud rate (default: 115200)")
    p.add_argument("--timeout", type=float, default=1.0, help="I/O timeout in seconds (default: 1.0)")
    p.add_argument(
        "--pause-ms",
        type=float,
        default=1.0,
        help="ASPEP header-to-payload pause in ms (default: 1.0)",
    )
    p.add_argument("-v", "--verbose", action="store_true", help="Print raw TX/RX frames to stderr")


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="STM32 MCSDK 6.x MCP/ASPEP command-line controller"
    )
    add_serial_args(parser)
    sub = parser.add_subparsers(dest="action", required=True)

    sub.add_parser("ports", help="List serial ports")
    sub.add_parser("selftest", help="Run offline ASPEP CRC/header test vectors")
    sub.add_parser("connect", help="Perform ASPEP beacon negotiation and ping")
    sub.add_parser("version", help="Read MCP protocol version")

    p = sub.add_parser("raw-mcp", help="Send an exact MCP payload inside ASPEP")
    p.add_argument("--hex", required=True, type=parse_hex_bytes, help='MCP bytes, e.g. "00 00"')

    p = sub.add_parser("command", help="Send an MCP command ID with optional payload")
    p.add_argument("--id", required=True, type=parse_int, help="MCP Command ID, e.g. 0x0006")
    p.add_argument("--motor", type=int, default=1, help="Motor selector 0..7 (default: 1)")
    p.add_argument("--payload-hex", type=parse_hex_bytes, default=b"", help="Optional command payload")

    p = sub.add_parser("get", help="GET_DATA_ELEMENT (command ID 2)")
    p.add_argument("--data-id", required=True, type=parse_int, help="16-bit MCSDK Data Element ID")
    p.add_argument("--motor", type=int, default=0, help="MCP header motor selector (normally 0)")

    p = sub.add_parser("set", help="SET_DATA_ELEMENT (command ID 1)")
    p.add_argument("--data-id", required=True, type=parse_int, help="16-bit MCSDK Data Element ID")
    p.add_argument("--value-hex", required=True, type=parse_hex_bytes, help="Raw register value bytes")
    p.add_argument("--motor", type=int, default=0, help="MCP header motor selector (normally 0)")

    return parser


def require_port(args) -> None:
    if not args.port:
        raise SystemExit("error: --port/-p is required for this command")


def main() -> None:
    args = make_parser().parse_args()

    if args.action == "ports":
        if list_ports is None:
            raise SystemExit("pyserial is not installed. Run: pip install pyserial")
        ports = list(list_ports.comports())
        if not ports:
            print("No serial ports found.")
        for p in ports:
            print(f"{p.device:20s} {p.description}")
        return

    if args.action == "selftest":
        self_test()
        return

    require_port(args)
    with McsdkSerialController(
        port=args.port,
        baudrate=args.baudrate,
        timeout=args.timeout,
        intra_packet_pause_ms=args.pause_ms,
        verbose=args.verbose,
    ) as ctl:
        hs = ctl.connect_aspep(do_ping=True)
        if args.verbose:
            print(
                "ASPEP connected:"
                f" performer={hs['performer_beacon'].hex(' ')}"
                f" final={hs['final_beacon'].hex(' ') if hs['final_beacon'] else '-'}"
                f" ping={hs['ping_reply'].hex(' ') if hs['ping_reply'] else '-'}",
                file=sys.stderr,
            )

        if args.action == "connect":
            print("ASPEP connection established.")
            print(f"Performer beacon : {hs['performer_beacon'].hex(' ')}")
            print(f"Final beacon     : {hs['final_beacon'].hex(' ') if hs['final_beacon'] else '(none)'}")
            print(f"Ping reply       : {hs['ping_reply'].hex(' ') if hs['ping_reply'] else '(none)'}")

        elif args.action == "version":
            version, status, raw = ctl.get_mcp_version()
            print(f"MCP version : 0x{version:08X} ({version})")
            print(f"Status      : {status_text(status)}")
            print(f"Raw payload : {raw.hex(' ')}")

        elif args.action == "raw-mcp":
            rsp = ctl.transact_raw_mcp(args.hex)
            print(f"RX MCP payload: {rsp.hex(' ')}")
            if rsp:
                print(f"Status        : {status_text(rsp[-1])}")

        elif args.action == "command":
            rsp = ctl.transact_mcp(args.id, args.motor, args.payload_hex)
            print(f"RX MCP payload: {rsp.hex(' ')}")
            if rsp:
                print(f"Data          : {rsp[:-1].hex(' ')}")
                print(f"Status        : {status_text(rsp[-1])}")

        elif args.action == "get":
            data, status = ctl.get_data_element(args.data_id, args.motor)
            print(f"Data   : {data.hex(' ')}")
            print(f"Status : {status_text(status)}")

        elif args.action == "set":
            data, status = ctl.set_data_element(args.data_id, args.value_hex, args.motor)
            print(f"Data   : {data.hex(' ') if data else '(none)'}")
            print(f"Status : {status_text(status)}")


if __name__ == "__main__":
    main()
