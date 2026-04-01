"""
CAN Interface Layer — UDP Socket Backend
Works across two separate processes on Windows, Mac, and Linux.
No extra software required.

Both ECU and Diagnostic Tool connect to localhost UDP.
ECU  listens on port 5000 (RX), sends to port 5001 (TX).
Tool listens on port 5001 (RX), sends to port 5000 (TX).

Each UDP datagram = one CAN frame:
  Bytes 0-3  : arbitration ID (big-endian uint32)
  Bytes 4-11 : CAN data (8 bytes, zero-padded)
"""

import socket
import struct
import logging

logger = logging.getLogger(__name__)

HOST        = "127.0.0.1"
ECU_PORT    = 5000   # ECU receives here
TESTER_PORT = 5001   # Tester receives here

ECU_RX_ID = 0x7E0
ECU_TX_ID = 0x7E8

SF = 0x00
FF = 0x10
CF = 0x20
FC = 0x30

FRAME_SIZE = 12   # 4 bytes ID + 8 bytes data


def _pack_frame(arb_id: int, data: bytes) -> bytes:
    data = data.ljust(8, b'\x00')[:8]
    return struct.pack(">I", arb_id) + data


def _unpack_frame(raw: bytes):
    arb_id = struct.unpack(">I", raw[:4])[0]
    data   = raw[4:12]
    return arb_id, data


class CANInterface:
    """ECU-side CAN interface. Receives on ECU_PORT, sends to TESTER_PORT."""

    def __init__(self, channel="vcan0", bustype="virtual"):
        self._rx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._rx.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._rx.bind((HOST, ECU_PORT))
        self._rx.settimeout(None)

        self._tx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        logger.info(f"ECU CAN socket: RX=:{ECU_PORT}  TX->:{TESTER_PORT}")
        print(f"  [CAN] UDP socket  RX port:{ECU_PORT}  TX port:{TESTER_PORT}")

    def send_single_frame(self, data: bytes):
        frame_data = bytes([len(data)]) + data
        frame_data = frame_data.ljust(8, b'\x00')
        self._tx.sendto(_pack_frame(ECU_TX_ID, frame_data), (HOST, TESTER_PORT))
        logger.debug(f"TX SF {frame_data.hex(' ').upper()}")

    def send_multi_frame(self, data: bytes):
        total_len = len(data)
        ff_data = bytes([(FF | (total_len >> 8)), total_len & 0xFF]) + data[:6]
        self._tx.sendto(_pack_frame(ECU_TX_ID, ff_data), (HOST, TESTER_PORT))

        raw = self._rx.recv(FRAME_SIZE)
        _, fc_data = _unpack_frame(raw)
        if (fc_data[0] & 0xF0) != FC:
            logger.warning("Expected FC, got something else")
            return

        sn, offset = 1, 6
        while offset < total_len:
            chunk = data[offset:offset + 7]
            cf_data = bytes([CF | (sn & 0x0F)]) + chunk
            self._tx.sendto(_pack_frame(ECU_TX_ID, cf_data), (HOST, TESTER_PORT))
            sn += 1
            offset += 7

    def send(self, data: bytes):
        if len(data) <= 7:
            self.send_single_frame(data)
        else:
            self.send_multi_frame(data)

    def receive_request(self, timeout=None):
        self._rx.settimeout(timeout)
        try:
            while True:
                raw = self._rx.recv(FRAME_SIZE)
                arb_id, data = _unpack_frame(raw)
                if arb_id != ECU_RX_ID:
                    continue
                pci        = data[0]
                frame_type = pci & 0xF0
                if frame_type == SF:
                    length  = pci & 0x0F
                    payload = bytes(data[1:1 + length])
                    logger.debug(f"RX SF {payload.hex(' ').upper()}")
                    return payload
                logger.warning(f"Unsupported frame type {frame_type:#04x}")
        except socket.timeout:
            return None

    def send_flow_control(self, block_size=0, st_min=0):
        fc = bytes([FC, block_size, st_min, 0, 0, 0, 0, 0])
        self._tx.sendto(_pack_frame(ECU_TX_ID, fc), (HOST, TESTER_PORT))

    def close(self):
        self._rx.close()
        self._tx.close()
        logger.info("ECU CAN socket closed")
