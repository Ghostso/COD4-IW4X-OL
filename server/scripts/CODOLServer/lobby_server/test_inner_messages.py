import importlib.util
import struct
import sys
import unittest
from pathlib import Path

from Crypto.Cipher import AES


PROBE_PATH = Path(__file__).with_name("lobby_plain_probe.py")
SPEC = importlib.util.spec_from_file_location("lobby_plain_probe", PROBE_PATH)
probe = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = probe
SPEC.loader.exec_module(probe)


class InnerMessageTests(unittest.TestCase):
    def test_arm_fragment_points_to_opcode_and_arm_byte(self):
        message = probe.build_inner_87()

        cursor = struct.unpack_from("<I", message)[0]
        self.assertEqual(cursor, 4)
        self.assertEqual(message[cursor], 0x87)
        self.assertEqual(message[cursor + 1], 1)

    def test_business_fragment_points_to_opcode_and_has_short_body(self):
        message = probe.build_inner_89(payload=b"\xAA\xBB", value=7)

        cursor = struct.unpack_from("<I", message)[0]
        self.assertEqual(cursor, 4)
        self.assertEqual(message[cursor], 0x89)
        body = memoryview(message)[cursor + 1:]
        self.assertEqual(bytes(body[:3]), b"\x01\x01\x00")
        self.assertEqual(struct.unpack_from("<H", body, 3)[0], 2)
        self.assertEqual(bytes(body[5:7]), b"\xAA\xBB")
        self.assertEqual(struct.unpack_from("<I", body, 7)[0], 7)

    def test_business_fragment_survives_server_cbc_builder(self):
        src20 = bytes(range(20))
        message = probe.build_inner_89()
        frame = probe.build_0x85_server_cbc(
            2, src20, frame_len=382, inner=message)
        plaintext = AES.new(
            probe.codec_02a0(src20)[4:20], AES.MODE_CBC, frame[10:26]
        ).decrypt(frame[26:-8])

        self.assertEqual(plaintext[:len(message)], message)
        self.assertEqual(struct.unpack_from("<I", plaintext)[0], 4)
        self.assertEqual(plaintext[4], 0x89)
        self.assertEqual(plaintext[5:14], b"\x01\x01\x00\x00\x00\x00\x00\x00\x00")


if __name__ == "__main__":
    unittest.main()
