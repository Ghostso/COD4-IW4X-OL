"""Offline check: is the 0x85 body a stream ciphertext (OFB/CTR) with an
all-zero IV and an AES key derived exactly as 0xBA0420 says?

The provider bound at [obj+0x608]+0xC is the OpenSSL "aes.1.1.4" EVP cipher.
If the mode is OFB/CTR with a zero IV, keystream(i) = AES(key, i) for each
16-byte block counter i, and XOR-ing it back over the captured body must
restore the inner plaintext the validator looks for (4-byte length + opcode
0x89 or 0x87).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from Crypto.Cipher import AES


def load_first_85(log_path: Path):
    for line in log_path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            ev = json.loads(line)
        except Exception:
            continue
        if ev.get("event") == "hold_recv" and ev.get("len", 0) > 300:
            return bytes.fromhex(ev["hex"])
    return None


def show(label: str, data: bytes):
    text = "".join(chr(b) if 32 <= b < 127 else "." for b in data)
    print(f"{label}: {data[:64].hex()}")
    print(f"{'':<{len(label)}}  {text}")


def score(pt: bytes):
    if len(pt) < 5:
        return None
    claimed = int.from_bytes(pt[:4], "little")
    opcode = pt[4]
    if opcode in (0x87, 0x89) and 5 <= claimed <= len(pt) + 8:
        return (claimed, opcode)
    return None


def decrypt_candidates(ct: bytes, key: bytes, ivs):
    results = []
    mode_specs = [
        ("ECB", AES.MODE_ECB, None),
        ("CBC", AES.MODE_CBC, None),
        ("OFB", AES.MODE_OFB, None),
        ("CFB", AES.MODE_CFB, None),
        ("CTR", AES.MODE_CTR, None),
    ]
    for mode_name, mode, _ in mode_specs:
        for iv_name, iv in ivs:
            try:
                if mode == AES.MODE_ECB:
                    pt = AES.new(key, mode).decrypt(ct)
                elif mode == AES.MODE_CTR:
                    pt = AES.new(key, mode, nonce=b"",
                                 initial_value=0).decrypt(ct)
                else:
                    pt = AES.new(key, mode, iv).decrypt(ct)
            except Exception as exc:
                results.append((mode_name, iv_name, None, str(exc)))
                continue
            results.append((mode_name, iv_name, pt, ""))
    return results


def main() -> int:
    log = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
        r"CODOLServer\logs\E57A5C_20261001_105349_a1\plain.jsonl")
    raw_key = sys.argv[2] if len(sys.argv) > 2 else \
        "224d27870f5bc6c6aaa12561bf719f785c2c42d2"

    frame = load_first_85(log)
    if not frame:
        print("no 0x85 frame found in", log)
        return 1
    print("frame len", len(frame))
    show("head", frame[:26])

    table = bytes([0x41, 0x13, 0x09, 0xAE, 0x3F, 0xA3, 0xBC, 0xF3,
                   0x18, 0x72, 0xEA, 0xBC, 0x09, 0x32, 0x11, 0xCC,
                   0x12, 0x42, 0x54, 0xF4])
    index = bytes([0x07, 0x11, 0x0E, 0x10, 0x09, 0x13, 0x0D, 0x00,
                   0x02, 0x03, 0x04, 0x08, 0x01, 0x0A, 0x0B, 0x05,
                   0x12, 0x06, 0x0C, 0x0F])
    src = bytes.fromhex(raw_key)
    key20 = bytes(table[index[i]] ^ src[i] for i in range(20))
    print("derived20", key20.hex())

    block16 = frame[10:26]
    bodies = (
        ("frame[:-8]", frame[:-8]),
        ("frame[4:-8]", frame[4:-8]),
        ("frame[10:-8]", frame[10:-8]),
        ("frame[26:-8]", frame[26:-8]),
    )
    body = bodies[0][1]
    ivs = (("iv=0", b"\x00" * 16),
           ("iv=frame16", block16),
           ("iv=ct[0:16]", body[:16]))
    candidates = (
        ("key=key20[:16]", key20[:16]),
        ("key=key20[:24]", key20[:24]),
        ("key=key20", key20),
        ("key=frame16", block16),
    )
    any_hit = False
    for name, key in candidates:
        if len(key) not in (16, 24, 32):
            continue
        for body_name, body in bodies:
            for mode_name, iv_label, pt, err in decrypt_candidates(
                    body, key, ivs):
                label = f"{name} {mode_name} {iv_label} {body_name}"
                if err:
                    print(f"{label}: ERR {err}")
                    continue
                hit = score(pt)
                if hit:
                    any_hit = True
                    print(f"HIT {label} length={hit[0]} "
                          f"opcode=0x{hit[1]:02X}")
                    show(label, pt)
        print()
    if not any_hit:
        print("NO_HIT: no AES mode/IV/key combination produced "
              "u32 length + 0x87/0x89")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
