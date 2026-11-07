"""Verify the recovered 0x85 HMAC formula with the known K material.

Formula (from 0xC78040 / 0xBA13D0):
    tag8 = HMAC-SHA1(K, message)[:8]

Try both derived directions (codec_02A0 / codec_0420 over the matching
20-byte source) and several 378-byte message slices.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import sys
from pathlib import Path

TABLE_02A0 = bytes([
    0x80, 0x22, 0xDE, 0xAA, 0x0B, 0x1C, 0x21, 0xF4, 0x00, 0xFF,
    0xEE, 0x37, 0x27, 0x92, 0x10, 0xCE, 0xAA, 0xF4, 0x3C, 0x21])
INDEX_02A0 = bytes([
    0x13, 0x12, 0x09, 0x04, 0x11, 0x01, 0x0A, 0x08, 0x0D, 0x02,
    0x0F, 0x03, 0x0C, 0x10, 0x05, 0x07, 0x00, 0x0E, 0x06, 0x0B])
TABLE_0420 = bytes([
    0x41, 0x13, 0x09, 0xAE, 0x3F, 0xA3, 0xBC, 0xF3, 0x18, 0x72,
    0xEA, 0xBC, 0x09, 0x32, 0x11, 0xCC, 0x12, 0x42, 0x54, 0xF4])
INDEX_0420 = bytes([
    0x07, 0x11, 0x0E, 0x10, 0x09, 0x13, 0x0D, 0x00, 0x02, 0x03,
    0x04, 0x08, 0x01, 0x0A, 0x0B, 0x05, 0x12, 0x06, 0x0C, 0x0F])


def codec(src, table, index):
    return bytes(table[index[i]] ^ src[i] for i in range(20))


def load_frame(path):
    for line in path.read_text(encoding="utf-8",
                               errors="replace").splitlines():
        try:
            ev = json.loads(line)
        except Exception:
            continue
        if ev.get("event") == "hold_recv" and ev.get("len", 0) > 300:
            return bytes.fromhex(ev["hex"])
    return None


def main():
    if len(sys.argv) < 4:
        print("usage: _hmac_known.py <plain.jsonl> <tx.txt> <rx.txt>")
        return 2
    frame = load_frame(Path(sys.argv[1]))
    tx_raw = bytes.fromhex(Path(sys.argv[2]).read_text().strip())
    rx_raw = bytes.fromhex(Path(sys.argv[3]).read_text().strip())
    if not frame:
        print("no frame")
        return 1
    tail = frame[-8:]
    print("frame", len(frame), "tail", tail.hex())

    keys = {
        "tx_raw": tx_raw,
        "rx_raw": rx_raw,
        "tx_0420": codec(tx_raw, TABLE_0420, INDEX_0420),
        "rx_02a0": codec(rx_raw, TABLE_02A0, INDEX_02A0),
    }
    msgs = [
        ("frame[:-8]", frame[:-8]),
        ("frame[4:-8]", frame[4:-8]),
        ("frame[4:382]", frame[4:382]),
        ("frame[10:-8]", frame[10:-8]),
        ("frame[26:-8]", frame[26:-8]),
        ("frame[4:4+378]", frame[4:4 + 378]),
    ]
    for kname, key in keys.items():
        for mname, msg in msgs:
            digest = hmac.new(key, msg, hashlib.sha1).digest()
            mark = " <== HIT" if digest[:8] == tail else ""
            print(f"{kname:8s} {mname:18s} {digest[:8].hex()}{mark}")
            if digest[:8] == tail:
                print("  key", key.hex())
                print("  msg_len", len(msg))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
