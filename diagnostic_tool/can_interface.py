"""
Tester CAN Interface — UDP Socket Backend
Mirror of the ECU's can_interface but from the tester's perspective.

Tool listens on port 5001 (RX), sends to port 5000 (TX).
"""

import socket
import struct
import logging

logger = logging.getLogger(__name__)

HOST        = "127.0.0.1"
ECU_PORT    = 5000   # ECU receives here  (tester sends to this)
TESTER_PORT = 5001   # Tester receives here

TESTER_TX_ID = 0x7E0
TESTER_RX_ID = 0x7E8

SF = 0x00
FF = 0x10
CF = 0x20
FC = 0x30

FRAME_SIZE = 12


def _pack_frame(arb_id: int, data: bytes) -> bytes:
    data = data.ljust(8, b'\x00')[:8]
    return struct.pack(">I", arb_id) + data


def _unpack_frame(raw: bytes):
    arb_id = struct.unpack(">I", raw[:4])[0]
    data   = raw[4:12]
    return arb_id, data


class TesterCANInterface:

    def __init__(self, channel="vcan0", bustype="virtual"):
        self._rx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._rx.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._rx.bind((HOST, TESTER_PORT))

        self._tx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        logger.info(f"Tester CAN socket: RX=:{TESTER_PORT}  TX->:{ECU_PORT}")

    def send_request(self, data: bytes):
        if len(data) <= 7:
            self._send_single_frame(data)
        else:
            self._send_multi_frame(data)

    def _send_single_frame(self, data: bytes):
        frame_data = bytes([len(data)]) + data
        frame_data = frame_data.ljust(8, b'\x00')
        self._tx.sendto(_pack_frame(TESTER_TX_ID, frame_data), (HOST, ECU_PORT))
        logger.debug(f"TX SF {frame_data.hex(' ').upper()}")

    def _send_multi_frame(self, data: bytes):
        total_len = len(data)
        ff = bytes([(FF | (total_len >> 8)), total_len & 0xFF]) + data[:6]
        self._tx.sendto(_pack_frame(TESTER_TX_ID, ff), (HOST, ECU_PORT))

        self._rx.settimeout(1.0)
        try:
            raw = self._rx.recv(FRAME_SIZE)
            _, fc_data = _unpack_frame(raw)
            if (fc_data[0] & 0xF0) != FC:
                logger.warning("No valid FC received")
                return
        except socket.timeout:
            logger.warning("FC timeout")
            return

        sn, offset = 1, 6
        while offset < total_len:
            chunk = data[offset:offset + 7]
            cf = bytes([CF | (sn & 0x0F)]) + chunk
            self._tx.sendto(_pack_frame(TESTER_TX_ID, cf), (HOST, ECU_PORT))
            sn += 1
            offset += 7

    def receive_response(self, timeout=2.0):
        self._rx.settimeout(timeout)
        try:
            while True:
                raw = self._rx.recv(FRAME_SIZE)
                arb_id, data = _unpack_frame(raw)
                if arb_id != TESTER_RX_ID:
                    continue

                pci        = data[0]
                frame_type = pci & 0xF0

                if frame_type == SF:
                    length = pci & 0x0F
                    return bytes(data[1:1 + length])

                if frame_type == FF:
                    total_len = ((pci & 0x0F) << 8) | data[1]
                    payload   = bytearray(data[2:])

                    # Send Flow Control
                    fc = bytes([FC, 0, 0, 0, 0, 0, 0, 0])
                    self._tx.sendto(_pack_frame(TESTER_TX_ID, fc), (HOST, ECU_PORT))

                    while len(payload) < total_len:
                        raw2 = self._rx.recv(FRAME_SIZE)
                        _, cf_data = _unpack_frame(raw2)
                        if (cf_data[0] & 0xF0) == CF:
                            payload += cf_data[1:]

                    return bytes(payload[:total_len])

        except socket.timeout:
            return None

    def close(self):
        self._rx.close()
        self._tx.close()
        logger.info("Tester CAN socket closed")
