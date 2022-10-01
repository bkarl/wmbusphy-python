import struct
import unittest

import numpy as np

from telegram_type_a import TelegramTypeA


class TestTelegramTypeA(unittest.TestCase):
    format_first_block = '<BBH6sH'
    first_block_size = 9 # crc and length field

    def gen_first_block(self, L):
        return struct.pack(self.format_first_block, L, 0, 0, b'000000', 0)

    def gen_second_block(self, CI, num_bytes):
        payload = np.arange(num_bytes, dtype=np.uint8)
        payload[0] = CI
        payload = payload.tobytes()
        payload += b'CC' # fake CRC
        return payload, payload[1:num_bytes]

    def gen_nth_block(self, num_bytes):
        payload = np.arange(num_bytes, dtype=np.uint8)
        payload = payload.tobytes()
        payload += b'CC' # fake CRC
        return payload, payload[:num_bytes]

    def test_n_blocks(self):
        total_payload_sizes = [10, 20, 32]
        for total_payload_size in total_payload_sizes:
            with self.subTest(total_payload_size=total_payload_size):
                CI = 0xA7
                L = self.first_block_size + total_payload_size
                raw_packet = self.gen_first_block(L)
                num_blocks = total_payload_size // 16 + 1
                total_expected_payload = b''
                for i in range(num_blocks):
                    block_size = 16
                    if i == num_blocks - 1 and (L - 9) % 16 != 0:
                        block_size = (L - 9) % 16
                    if i == 0:
                        packed_payload, expected_payload = self.gen_second_block(CI, block_size)
                    else:
                        packed_payload, expected_payload = self.gen_nth_block(block_size)
                    raw_packet += packed_payload
                    total_expected_payload += expected_payload
                telegramA = TelegramTypeA.create_from_bytes(raw_packet)
                assert telegramA.L == L
                assert telegramA.CI == CI
                assert telegramA.payload == total_expected_payload

    def test_calc_real_frame_size(self):
        length_field = [(11, 11+2+2), (9+16, 9+16+2+2), (9+48, 9+48+2+2+2+2)]
        for length in length_field:
            with self.subTest(length=length):
                L, expected = length
                total_len = TelegramTypeA.calc_real_frame_size(L)
                assert total_len == expected
