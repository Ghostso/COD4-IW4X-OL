"""Final inner-layer check with the now-closed key provenance.

From 0xBA1F60..0xBA206D and 0xBA38F8:
    p608.key = codec_02A0(obj+0x620)[0:16]     (receive direction)
    provider covers frame[26:382]              (352 bytes)
    skip = 22 from base frame+4

Try that exact key against the 352-byte body with every standard mode and
report whether an inner opcode appears.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from Crypto.Cipher import AES

TABLE_02A0 = bytes([
    0x80, 0x22, 0xDE, 0xAA, 0x0B, 0x1C, 0x21, 0xF4, 0x00, 0xFF,
    0xEE, 0x37, 0x27, 0x92, 0x10, 0xCE, 0xAA, 0xF4, 0x3C, 0x21])
INDEX_02A0 = bytes([
    0x13, 0x12, 0x09, 0x04, 0x11, 0x01, 0x0A, 0x08, 0x0D, 0x02,
    0x0F, 0x03, 0x0C, 0x10, 0x05, 0x07, 0x00, 0x0E, 0x06, 0x0B])


def codec_02a0(src: bytes) -> bytes:
    return bytes(TABLE_02A0[INDEX_02A0[i]] ^ src[i] for i in range(20))


def load_frame(path: Path):
    for line in path.read_text(encoding="utf-8",
                               errors="replace").splitlines():
        try:
            ev = json.loads(line)
        except Exception:
            continue
        if ev.get("event") == "hold_recv" and ev.get("len", 0) > 300:
            return bytes.fromhex(ev["hex"])
    return None


def show(label: str, data: bytes):
    text = ''.join(chr(b) if 32 <= b < 127 else '.' for b in data[:64])
    print(f"{label}\n  {data[:64].hex()}\n  {text}")


def main() -> int:
    frame = load_frame(Path(sys.argv[1]))
    rx_raw = bytes.fromhex(Path(sys.argv[2]).read_text().strip())
    if not frame:
        print("no frame")
        return 1
    key = codec_02a0(rx_raw)[:16]
    print("frame", len(frame))
    print("rx_raw", rx_raw.hex())
    print("key   ", key.hex())

    body = frame[26:378]
    print("body", len(body), "mod16", len(body) % 16)
    n = len(body) // 16 * 16
    for mode_name, mode in (("ECB", AES.MODE_ECB),
                            ("CBC", AES.MODE_CBC),
                            ("OFB", AES.MODE_OFB),
                            ("CFB", AES.MODE_CFB)):
        for iv_name, iv in (("iv=0", b"\x00" * 16),
                            ("iv=frame16", frame[10:26]),
                            ("iv=body0", body[:16]),
                            ("iv=key", key)):
            try:
                if mode == AES.MODE_ECB:
                    pt = AES.new(key, mode).decrypt(body[:n])
                else:
                    pt = AES.new(key, mode, iv).decrypt(body[:n])
            except Exception as exc:
                print(f"{mode_name} {iv_name}: ERR {exc}")
                continue
            show(f"{mode_name} {iv_name}", pt)
            claimed = int.from_bytes(pt[:4], "little")
            print(f"  u32@0={claimed} op@4=0x{pt[4]:02x}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
