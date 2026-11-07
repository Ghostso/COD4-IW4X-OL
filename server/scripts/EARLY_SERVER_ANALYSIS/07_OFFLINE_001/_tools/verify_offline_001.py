#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OFFLINE_001 independent verification (Workflow A + C).
Read-only on all inputs. Writes only into 07_OFFLINE_001\_evidence\.
Re-implements AES-128 from FIPS-197 and SHA1/HMAC from the stdlib so that the
result does NOT depend on the reference codol_crypto.py implementation.
"""
import io, os, sys, json, struct, hashlib, hmac, re

HERE = os.path.dirname(os.path.abspath(__file__))
OUT  = os.path.join(os.path.dirname(HERE), "_evidence")
os.makedirs(OUT, exist_ok=True)

# ------------------------------------------------------------------ AES-128 (FIPS-197)
def _build_sbox():
    p = q = 1
    sbox = [0]*256
    while True:
        p = p ^ ((p << 1) & 0xFF) ^ (0x1B if (p & 0x80) else 0)
        q ^= (q << 1) & 0xFF
        q ^= (q << 2) & 0xFF
        q ^= (q << 4) & 0xFF
        q &= 0xFF
        if q & 0x80:
            q ^= 0x09
        q &= 0xFF
        x = q ^ ((q << 1) | (q >> 7)) & 0xFF
        x ^= ((q << 2) | (q >> 6)) & 0xFF
        x ^= ((q << 3) | (q >> 5)) & 0xFF
        x ^= ((q << 4) | (q >> 4)) & 0xFF
        x &= 0xFF
        sbox[p] = x ^ 0x63
        if p == 1:
            break
    sbox[0] = 0x63
    return sbox

SBOX = _build_sbox()
RCON = [0x01,0x02,0x04,0x08,0x10,0x20,0x40,0x80,0x1B,0x36,0x6C,0xD8,0xAB,0x4D]

def _xtime(a):
    a <<= 1
    if a & 0x100:
        a ^= 0x11B
    return a & 0xFF

def _mul(a, b):
    r = 0
    for _ in range(8):
        if b & 1:
            r ^= a
        b >>= 1
        a = _xtime(a)
    return r

def _expand_key(key):
    assert len(key) == 16
    w = [list(key[i*4:i*4+4]) for i in range(4)]
    for i in range(4, 44):
        t = list(w[i-1])
        if i % 4 == 0:
            t = t[1:] + t[:1]
            t = [SBOX[b] for b in t]
            t[0] ^= RCON[i//4 - 1]
        w.append([w[i-4][j] ^ t[j] for j in range(4)])
    return [bytes(sum(w[4*r:4*r+4], [])) for r in range(11)]

def _encrypt_block(rk, block):
    s = list(block)
    def ark(rnd):
        k = rk[rnd]
        for i in range(16):
            s[i] ^= k[i]
    def sub():
        for i in range(16):
            s[i] = SBOX[s[i]]
    def shift():
        # state is column-major: s[c*4+r]
        for r in range(1, 4):
            row = [s[c*4+r] for c in range(4)]
            row = row[r:] + row[:r]
            for c in range(4):
                s[c*4+r] = row[c]
    def mix():
        for c in range(4):
            a = s[c*4:c*4+4]
            s[c*4+0] = _mul(a[0],2)^_mul(a[1],3)^a[2]^a[3]
            s[c*4+1] = a[0]^_mul(a[1],2)^_mul(a[2],3)^a[3]
            s[c*4+2] = a[0]^a[1]^_mul(a[2],2)^_mul(a[3],3)
            s[c*4+3] = _mul(a[0],3)^a[1]^a[2]^_mul(a[3],2)
    ark(0)
    for rnd in range(1, 10):
        sub(); shift(); mix(); ark(rnd)
    sub(); shift(); ark(10)
    return bytes(s)

def _self_test():
    rk = _expand_key(bytes(range(16)))
    ct = _encrypt_block(rk, bytes.fromhex("00112233445566778899aabbccddeeff"))
    want = bytes.fromhex("69c4e0d86a7b0430d8cdb78070b4c55a")
    return ct == want, ct.hex(), want.hex()

# ------------------------------------------------------------------ CODOL AES128/SHA1 keystream
def keystream_xor(key16, seed6, data):
    w = _expand_key(key16)
    counter = bytearray(hashlib.sha1(seed6).digest())
    out = bytearray(data)
    for off in range(0, len(out), 16):
        blk = _encrypt_block(w, bytes(counter))
        for j in range(min(16, len(out)-off)):
            out[off+j] ^= blk[j]
        for j in range(16):
            counter[j] = (counter[j]+1) & 0xFF
            if counter[j]:
                break
    return bytes(out)

def mac8(key24, header6, rest):
    return hmac.new(key24[:24], header6 + rest, hashlib.sha1).digest()[:8]

def roundtrip_test():
    key = bytes(range(24))
    seed = bytes([3,0,0,0,0xc3,0xf2])
    pt = bytes(range(40))
    ct = keystream_xor(key[:16], seed, pt)
    pt2 = keystream_xor(key[:16], seed, ct)
    return pt2 == pt

# ------------------------------------------------------------------ read-only inputs
ROOT   = r"D:\BaiduNetdiskDownload\使命召唤OL"
SERVER = r"D:\BaiduNetdiskDownload\CODOL-AlphaBuild_By_Antia(20261006)\CODOL-AlphaBuild By Antia\CODOL_Server"
LOG    = os.path.join(ROOT, "REF_LOBBY_KIT", "battle_srv.log")
SESS_BIN = os.path.join(ROOT, "CODOL-Combat-Server-v0.1", "build", "bin",
                        "session_descriptor", "session_record_258.bin")

def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1<<20), b""):
            h.update(chunk)
    return h.hexdigest().upper()

# ------------------------------------------------------------------ Workflow B: 219B ledger (independent re-parse)
RX_RE = re.compile(r"RX #(\d+) peer=(\S+) len=(\d+) hex=([0-9a-fA-F ]+)")

def parse_rx(logpath):
    rows = {}
    with io.open(logpath, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            m = RX_RE.search(line)
            if m:
                rows[int(m.group(1))] = {
                    "len_declared": int(m.group(3)),
                    "hex": m.group(4).split(),
                    "line": line.rstrip("\n"),
                    "peer": m.group(2),
                }
    return rows

def cookie_echo_ledger(rows):
    r = rows.get(4)
    if not r:
        return {"status": "NOT_FOUND"}
    b = r["hex"]
    out = {
        "declared_len": r["len_declared"],
        "hex_byte_count_in_log": len(b),
        "truncated_in_log": len(b) < r["len_declared"],
        "note": ("battle_srv.py logs pkt[:128].hex(' ') so only the first 128 bytes "
                 "of a 219B packet are in the log; the length field itself is a direct "
                 "len(pkt) from recvfrom and is authoritative."),
        "layout_219": {
            "type_ver": {"off": 0, "len": 2, "val": " ".join(b[0:2])},
            "verification_tag": {"off": 2, "len": 2, "val": " ".join(b[2:4])},
            "reserved_zero": {"off": 4, "len": 2, "val": " ".join(b[4:6])},
            "cookie": {"off": 6, "len": 38, "val": " ".join(b[6:44])},
            "address_block": {"off": 44, "len": 67, "val": " ".join(b[44:111])},
            "u64_magic": {"off": 111, "len": 8, "val": " ".join(b[111:119])},
            "pubkey": {"off": 119, "len": 100,
                       "val": " ".join(b[119:128]),
                       "val_note": "only first 9 bytes present in log; full 100B is truncated"},
        },
        "arithmetic": "6 + 38 + 67 + 8 + 100 = 219",
        "field_checks": {
            "u64_at_111_eq_1": b[111:119] == ["01","00","00","00","00","00","00","00"],
            "pubkey_starts_DER_SEQ": b[119:127] == ["30","44","03","02","07","00","02","01"],
        },
        "alt_layout_189": {
            "arith": "44 + 37 + 8 + 100 = 189",
            "matches_observed": False,
            "reason": ("observed packet is declared len=219; a 189 layout would require a "
                       "37B address block at off 44, but the observed bytes 44..110 are a "
                       "67B run ending in the 00FF00FF0000 sentinel pattern and the u64==1 "
                       "magic sits at 111, not 103."),
        },
    }
    return out

# ------------------------------------------------------------------ Workflow C: 258B descriptor tag walk
TAG_NAMES = {0x08:"U32", 0x07:"I32", 0x0A:"U64", 0x13:"BLOB", 0x10:"STRING"}

def parse_descriptor(buf):
    """Walk the bd serialized descriptor using the tag grammar:
       0x08 + u32 ; 0x07 + i32 ; 0x0A + u64 ; 0x13 0x08 <u32 len> <payload> ; 0x10 <ascii> 0x00
    Returns (fields, consumed, error)."""
    fields = []
    i = 0
    n = len(buf)
    while i < n:
        start = i
        tag = buf[i]; i += 1
        if tag == 0x08:
            if i+4 > n: return fields, i, "truncated u32"
            v = struct.unpack_from("<I", buf, i)[0]; i += 4
            fields.append({"off":start,"len":i-start,"tag":"U32","value":v})
        elif tag == 0x07:
            if i+4 > n: return fields, i, "truncated i32"
            v = struct.unpack_from("<i", buf, i)[0]; i += 4
            fields.append({"off":start,"len":i-start,"tag":"I32","value":v})
        elif tag == 0x0A:
            if i+8 > n: return fields, i, "truncated u64"
            v = struct.unpack_from("<Q", buf, i)[0]; i += 8
            fields.append({"off":start,"len":i-start,"tag":"U64","value":v})
        elif tag == 0x13:
            if i+5 > n: return fields, i, "truncated blob hdr"
            if buf[i] != 0x08: return fields, i, "blob missing 0x08 sub-tag @%d"%i
            ln = struct.unpack_from("<I", buf, i+1)[0]; i += 5
            if i+ln > n: return fields, i, "truncated blob payload"
            payload = buf[i:i+ln]; i += ln
            fields.append({"off":start,"len":i-start,"tag":"BLOB","blob_len":ln,
                           "payload_sha1": hashlib.sha1(payload).hexdigest().upper()})
        elif tag == 0x10:
            j = i
            while j < n and buf[j] != 0x00:
                j += 1
            if j >= n: return fields, i, "unterminated string"
            s = buf[i:j].decode("latin-1"); i = j+1
            fields.append({"off":start,"len":i-start,"tag":"STRING","value":s})
        else:
            return fields, start, "unknown tag 0x%02X @%d"%(tag,start)
    return fields, i, None

def descriptor_analysis(path):
    with open(path,"rb") as f:
        buf = f.read()
    fields, consumed, err = parse_descriptor(buf)
    # locate the 16B securityKey blob (blob_len==16) and the 37B address blob
    key_blob = next((f for f in fields if f["tag"]=="BLOB" and f.get("blob_len")==16), None)
    addr_blob = next((f for f in fields if f["tag"]=="BLOB" and f.get("blob_len")==37), None)
    return {
        "path": path,
        "size": len(buf),
        "sha256": sha256_file(path),
        "parse_consumed": consumed,
        "parse_error": err,
        "field_count": len(fields),
        "first_8_fields": fields[:8],
        "last_8_fields": fields[-8:],
        "addr_blob_37": addr_blob,
        "securitykey_blob_16": key_blob,
        "full_field_table": fields,
    }

# ------------------------------------------------------------------ main
def main():
    res = {"tool": "verify_offline_001.py", "workflows": {}}
    ok, got, want = _self_test()
    res["aes128_kat"] = {"ok": ok, "got": got, "want": want}
    res["keystream_roundtrip"] = roundtrip_test()

    # hashes of inputs actually used
    res["input_hashes"] = {
        "battle_srv.log": sha256_file(LOG),
        "session_record_258.bin": sha256_file(SESS_BIN),
    }

    # B
    rows = parse_rx(LOG)
    res["workflows"]["B_cookie_echo"] = {
        "rx_count_parsed": len(rows),
        "ledger": cookie_echo_ledger(rows),
    }

    # C
    res["workflows"]["C_session_descriptor"] = descriptor_analysis(SESS_BIN)

    # A (structural): parse RX #5 header and confirm MAC construction fields are present.
    r5 = rows.get(5)
    if r5:
        b = r5["hex"]
        res["workflows"]["A_data_mac"] = {
            "rx5_declared_len": r5["len_declared"],
            "rx5_hex_count_in_log": len(b),
            "header": {
                "type_ver": b[0:2],
                "tag_le": b[2:4],
                "seq_le": b[4:6],
                "mac8": b[6:14],
                "len_le": b[14:16],
            },
            "mac_input_rule": "HMAC-SHA1(key24, pkt[0:6] || pkt[14:])[:8]",
            "recompute_blocked": ("full 24B transport key not recoverable: log records only "
                                  "transport[:16]; ECDH private scalar is random per run and "
                                  "not logged."),
            "transport_key_logged_prefix": None,
            "transport_key_logged_prefix_line": None,
        }
        # Capture the 16B prefix that the log printed for THIS session only.
        # The log holds many startup/selftest sessions; associate the KEY_EXCHANGE_OK
        # line that follows RX #4 and carries the same peer.
        peer = r5.get("peer")
        log_lines = list(io.open(LOG, encoding="utf-8", errors="replace"))
        rx4_idx = None
        for idx, line in enumerate(log_lines):
            if ("RX #4 " in line) and ("len=219" in line) and (peer in line):
                rx4_idx = idx
                break
        if rx4_idx is not None:
            for jdx in range(rx4_idx + 1, len(log_lines)):
                line = log_lines[jdx]
                if "KEY_EXCHANGE_OK" in line and "transport=" in line and (peer in line):
                    res["workflows"]["A_data_mac"]["transport_key_logged_prefix"] = \
                        line.split("transport=")[1].strip()
                    res["workflows"]["A_data_mac"]["transport_key_logged_prefix_line"] = jdx + 1
                    break

    with io.open(os.path.join(OUT, "offline_001_evidence.json"), "w",
                 encoding="utf-8", newline="") as f:
        json.dump(res, f, indent=2, ensure_ascii=False)

    print("AES128 KAT:", "OK" if ok else "FAIL", got)
    print("keystream roundtrip:", res["keystream_roundtrip"])
    print("RX parsed:", len(rows))
    print("B:", json.dumps(res["workflows"]["B_cookie_echo"]["ledger"]["field_checks"],
                           ensure_ascii=False))
    print("C: size=%d fields=%d err=%s" % (
        res["workflows"]["C_session_descriptor"]["size"],
        res["workflows"]["C_session_descriptor"]["field_count"],
        res["workflows"]["C_session_descriptor"]["parse_error"]))
    print("wrote", os.path.join(OUT, "offline_001_evidence.json"))

if __name__ == "__main__":
    main()
