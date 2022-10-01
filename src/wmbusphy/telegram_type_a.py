import struct
import attrs

@attrs.define
class TelegramTypeA:
    L: int
    C: int
    M: int
    A: int
    header_crc: int
    CI: int
    payload: bytes

    @classmethod
    def create_from_bytes(cls, bytes):
        format = f"<BBH6sHB"
        header_fields = bytes[:13]
        L, C, M, A, CRC, CI = struct.unpack(format, header_fields)
        payload = TelegramTypeA._extract_payload(L, bytes[12:])
        return cls(L, C, M, A, CRC, CI, payload)

    @staticmethod
    def _extract_payload(L, payload):
        L -= 9 # the header fields that have already been parsed (CRC and L field excluded)
        num_blocks = L // 16 + 1
        ret = b''
        for i in range(num_blocks):
            if i == num_blocks - 1 and (L % 16) != 0:
                ret += payload[i * (16 + 2):i * (16 + 2) + (L % 16)]
            else:
                ret += payload[i * (16 + 2):i * (16 + 2) + 16]

            if i == 0:
                ret = ret[1:16]  # first byte is CI field that has already been parsed

        return ret

    @staticmethod
    def calc_real_frame_size(length_field):
        num_bytes = length_field + 2 #CRC bytes in the first block
        num_bytes += ((length_field - 9) // 16) * 2 # CRC bytes per data block
        if (length_field - 9) % 16 != 0:
            num_bytes += 2 # if last block is now full
        return num_bytes

    def to_file_no_crc(self, filename):
        format = f"<BBH6sH"

        with open(filename, 'wb') as f:
            f.write(struct.pack(format, self.L, self.C, self.M, self.A, self.CI))
            f.write(self.payload)
