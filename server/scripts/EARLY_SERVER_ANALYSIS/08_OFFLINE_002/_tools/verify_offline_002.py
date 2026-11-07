#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OFFLINE_002 independent re-implementation of the A/B/C checks.
Read-only on every input. Writes only into 08_OFFLINE_002\_evidence\.
Deliberately a THIRD, independent parser:
  - B ledger: byte-index slice over the RX #4 hex token list + needle search
    (no regex, no shared helper with the two 07_OFFLINE_001 scripts);
  - A header: byte-index slice of RX #5;
  - C descriptor: explicit tag-walk over the 258B record;
  - C pickle: index the 28-field lobby descriptor and compare field 19 to the
    key file by hash only (the key value is never printed).
"""
import io, os, json, struct, hashlib, pickle

HERE = os.path.dirname(os.path.abspath(__file__))
OUT  = os.path.join(os.path.dirname(HERE), "_evidence")
os.makedirs(OUT, exist_ok=True)

ROOT = r"D:\BaiduNetdiskDownload\使命召唤OL"
LOG  = os.path.join(ROOT, "REF_LOBBY_KIT", "battle_srv.log")
SESS_BIN = os.path.join(ROOT, "CODOL-Combat-Server-v0.1", "build", "bin",
                        "session_descriptor", "session_record_258.bin")
PICKLE = os.path.join(r"D:\BaiduNetdiskDownload\CODOL-AlphaBuild_By_Antia(20261006)",
                      "CODOL-AlphaBuild By Antia", "CODOL_Server", "lobby", "session_desc.pickle")
KEYBIN = os.path.join(r"D:\BaiduNetdiskDownload\CODOL-AlphaBuild_By_Antia(20261006)",
                      "CODOL-AlphaBuild By Antia", "CODOL_Server", "lobby", "securitykey.bin")

def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest().upper()

def read_rx(target):
    """Return the raw hex token list for RX #<target> (byte-index strategy)."""
    with io.open(LOG, "r", encoding="utf-8", errors="replace") as f:
        for ln in f:
            if ("RX #%d " % target) in ln and " hex=" in ln:
                body = ln.split("hex=", 1)[1]
                toks = [t for t in body.replace("\n", "").split(" ") if t]
                return toks
    return None

res = {"tool": "verify_offline_002.py", "input_hashes": {}}
res["input_hashes"]["battle_srv.log"] = sha256_file(LOG)
res["input_hashes"]["session_record_258.bin"] = sha256_file(SESS_BIN)
res["input_hashes"]["session_desc.pickle"] = sha256_file(PICKLE)
res["input_hashes"]["securitykey.bin"] = sha256_file(KEYBIN)

# --------------------------------------------------------------- B: 219 ledger
toks4 = read_rx(4)
assert toks4 is not None, "RX #4 not found"
b4 = bytes(int(t, 16) for t in toks4)
res["B_cookie_echo"] = {
    "declared_len": 219,
    "hex_tokens_in_log": len(toks4),
    "log_truncated_at_128": len(toks4) == 128,
    "type_ver": list(b4[0:2]),
    "verification_tag_le": list(b4[2:4]),
    "segments": {
        "header_type_ver_tag_reserved": [0, 6],
        "cookie": [6, 38],
        "address_long": [44, 67],
        "u64_magic": [111, 8],
        "pubkey": [119, 100],
    },
    "sum_of_segments": 6 + 38 + 67 + 8 + 100,
    "u64_magic_is_one": (b4[111:119] == bytes([1] + [0]*7)),
    "pubkey_prefix_is_der_seq": (b4[119] == 0x30),
}
res["B_cookie_echo"]["alt189_magic_at_103_is_one"] = (b4[103:111] == bytes([1] + [0]*7))
res["B_cookie_echo"]["alt189_pubkey_at_111_is_der"] = (b4[111] == 0x30)

# --------------------------------------------------------------- A: RX #5 hdr
toks5 = read_rx(5)
assert toks5 is not None, "RX #5 not found"
b5 = bytes(int(t, 16) for t in toks5)
res["A_data_mac"] = {
    "declared_len": 54,
    "hex_tokens_in_log": len(toks5),
    "not_truncated": len(toks5) == 54,
    "header": {
        "type_ver": list(b5[0:2]),
        "tag_le": list(b5[2:4]),
        "seq_le": list(b5[4:6]),
        "mac8": b5[6:14].hex(),
        "len_le": list(b5[14:16]),
    },
    "len_le_value": b5[14] | (b5[15] << 8),
    "frame_self_consistent": (16 + (b5[14] | (b5[15] << 8))) == 54,
    "mac_input_rule": "HMAC-SHA1(key24, pkt[0:6] || pkt[14:])[:8]",
    "recompute_blocked": "log records only transport[:16]; ECDH private scalar random per run",
}
res["A_data_mac"]["transport_prefix_len_chars"] = None
with io.open(LOG, "r", encoding="utf-8", errors="replace") as f:
    lines = f.readlines()
for i, ln in enumerate(lines):
    if "RX #4 " in ln and "len=219" in ln:
        for ln2 in lines[i+1:i+6]:
            if "KEY_EXCHANGE_OK" in ln2 and "transport=" in ln2:
                res["A_data_mac"]["transport_prefix_len_chars"] = len(ln2.split("transport=")[1].strip())
                break
        break

# --------------------------------------------------------------- C: descriptor
data = open(SESS_BIN, "rb").read()
i = 0; fields = []
err = None
while i < len(data):
    tag = data[i]
    if tag in (0x08, 0x07):
        fields.append((i, 5, hex(tag))); i += 5
    elif tag == 0x0A:
        fields.append((i, 9, hex(tag))); i += 9
    elif tag == 0x13:
        ln = struct.unpack_from("<I", data, i + 2)[0]
        fields.append((i, 6 + ln, hex(tag))); i += 6 + ln
    elif tag == 0x10:
        j = data.index(0, i + 1)
        fields.append((i, (j - i) + 1, hex(tag))); i = j + 1
    else:
        err = "unknown tag 0x%02x at %d" % (tag, i); break
if err is None:
    sk_idx = None; sk_off = None
    for n, (off, ln, tg) in enumerate(fields):
        if tg == "0x13" and ln == 22:
            sk_idx = n; sk_off = off; break
    res["C_descriptor"] = {
        "size": len(data),
        "field_count": len(fields),
        "parse_consumed": i,
        "securitykey_field_index": sk_idx,
        "securitykey_blob_offset": sk_off,
        "securitykey_payload_range": [sk_off + 6, sk_off + 22] if sk_idx is not None else None,
        "first_field_blob_len": struct.unpack_from("<I", data, 2)[0],
        "first_field_total_len": fields[0][1],
    }
else:
    res["C_descriptor"] = {"error": err}

# C: pickle field index 19 vs key file (hash only)
obj = pickle.load(open(PICKLE, "rb"))
f19 = bytes(obj[19][1])
sk = open(KEYBIN, "rb").read()
res["C_pickle"] = {
    "field_count": len(obj),
    "field19_len": len(f19),
    "field19_equals_keybin": f19 == sk,
    "field19_sha256": hashlib.sha256(f19).hexdigest().upper(),
    "field0_blob_len": len(obj[0][1]),
    "field21_blob_len": len(obj[21][1]),
}

with io.open(os.path.join(OUT, "offline_002_evidence.json"), "w",
             encoding="utf-8") as f:
    json.dump(res, f, indent=2, ensure_ascii=False)

print(json.dumps(res, indent=2, ensure_ascii=False))
print("wrote", os.path.join(OUT, "offline_002_evidence.json"))
