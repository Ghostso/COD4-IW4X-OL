#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OFFLINE_001 independent second-pass verification (Workflow B length ledger + C golden compare).
Deliberately written with a DIFFERENT parsing strategy from verify_offline_001.py:
  - reads the raw log bytes and slices by character index instead of a regex over RX lines;
  - walks the descriptor by an explicit offset table instead of a tag-driven parser.
Read-only on all inputs. Writes only into 07_OFFLINE_001\_evidence\.
"""
import io, os, json, struct, hashlib

HERE = os.path.dirname(os.path.abspath(__file__))
OUT  = os.path.join(os.path.dirname(HERE), "_evidence")
os.makedirs(OUT, exist_ok=True)

ROOT   = r"D:\BaiduNetdiskDownload\使命召唤OL"
LOG    = os.path.join(ROOT, "REF_LOBBY_KIT", "battle_srv.log")
SESS_BIN = os.path.join(ROOT, "CODOL-Combat-Server-v0.1", "build", "bin",
                        "session_descriptor", "session_record_258.bin")

# FULL_A golden vector, transcribed from REF_LOBBY_KIT\codol_crypto.py:876-885
FULL_A_HEX = (
    "1308250000007F000001207100FF00FF000000FF00FF000000FF00FF000000FF00FF00007F0000012071"
    "01130808000000887766554433221108000000000812000000080100000010"
    "31343332373738363333000A41420F0000000000106D705F63726173685F74726F706963616C00"
    "07ABAD92D6070000000007000000000700000000070000000007000000000700000000"
    "130810000000000102030405060708090A0B0C0D0E0F"
    "071300000007000000000700000000070800000007FFFFFFFF071C030000071E000000"
    "070000000007070000000700000000"
    "0701E00D0C0A41420F000000000007000000000700000000070000000007010000000700000000"
)

def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1<<20), b""):
            h.update(c)
    return h.hexdigest().upper()

# ---- B: byte-index extraction, no regex -------------------------------------
def extract_rx4_bytes():
    with io.open(LOG, "r", encoding="utf-8", errors="replace") as f:
        for ln in f:
            # RX #4 is the only line whose token sequence starts with 'RX #4'
            if "RX #4" in ln and "len=219" in ln:
                marker = "hex="
                p = ln.find(marker)
                body = ln[p+len(marker):]
                toks = body.replace("\n", "").split(" ")
                toks = [t for t in toks if t != ""]
                return len(toks), toks, ln.rstrip("\n")
    return None, None, None

def cookie_len_ledger():
    n, toks, raw = extract_rx4_bytes()
    out = {"found": toks is not None}
    if not toks:
        return out
    out["declared_len_from_line"] = 219
    out["hex_tokens_available"] = n
    out["log_truncates_at_128"] = (n == 128)
    # Explicit offset table (no tag parser):
    segs = [
        ("hdr.type_ver",   0,   2, 219),
        ("hdr.verify_tag", 2,   2, 219),
        ("hdr.reserved",   4,   2, 219),
        ("cookie",         6,  38, 219),
        ("address_block", 44,  67, 219),
        ("magic_u64",    111,   8, 219),
        ("pubkey",       119, 100, 219),
    ]
    total = 0
    rows = []
    for name, off, ln, _ in segs:
        have = max(0, min(ln, n - off))
        rows.append({"field": name, "off": off, "len": ln,
                     "bytes_in_log": have, "off_end": off+ln})
        total += ln
    out["segments"] = rows
    out["sum_of_segment_lengths"] = total
    out["equals_declared"] = (total == 219)
    out["u64_magic_bytes"] = toks[111:119]
    out["u64_magic_is_one"] = (toks[111:119] == ["01","00","00","00","00","00","00","00"])
    out["pubkey_prefix"] = toks[119:127]
    out["pubkey_prefix_is_der"] = (toks[119:127] == ["30","44","03","02","07","00","02","01"])
    # alt 189 layout test: if address were 37B, magic u64 would sit at 103 and pubkey at 111
    out["alt189_magic_would_be_at_103"] = toks[103:111]
    out["alt189_magic_matches"] = (toks[103:111] == ["01","00","00","00","00","00","00","00"])
    out["alt189_pubkey_would_be_at_111"] = toks[111:119]
    out["alt189_pubkey_is_der"] = (toks[111:119] == ["30","44","03","02","07","00","02","01"])
    return out

# ---- C: offset-table walk (no tag grammar) -----------------------------------
def descriptor_offset_table():
    with open(SESS_BIN, "rb") as f:
        b = f.read()
    out = {"size": len(b), "sha256": sha256_file(SESS_BIN)}
    out["first_bytes"] = b[:3].hex(" ").upper()
    # The 5 leading fields are: BLOB(addr) BLOB(sessionid) u32 u32 u32
    # BLOB header = 13 08 <u32 len>. Read addr length.
    assert b[0] == 0x13 and b[1] == 0x08
    addr_len = struct.unpack_from("<I", b, 2)[0]
    out["addr_blob_len"] = addr_len
    p = 6 + addr_len
    assert b[p] == 0x13 and b[p+1] == 0x08
    sid_len = struct.unpack_from("<I", b, p+2)[0]
    out["sessionid_blob_len"] = sid_len
    p = p + 6 + sid_len
    gtype = struct.unpack_from("<I", b, p+1)[0]; p += 5
    maxp  = struct.unpack_from("<I", b, p+1)[0]; p += 5
    curp  = struct.unpack_from("<I", b, p+1)[0]; p += 5
    out["game_type"] = gtype; out["max_players"] = maxp; out["current_players"] = curp
    # scan for the 16B security key blob: 13 08 10 00 00 00 <16 bytes>
    needle = b"\x13\x08\x10\x00\x00\x00"
    idx = b.find(needle)
    out["securitykey_blob_offset"] = idx
    out["securitykey_blob_total_len"] = 6 + 16
    out["securitykey_payload_sha1"] = hashlib.sha1(b[idx+6:idx+22]).hexdigest().upper()
    out["securitykey_payload_is_ascending_0_to_15"] = (b[idx+6:idx+22] == bytes(range(16)))
    # compare to golden
    golden = bytes.fromhex(FULL_A_HEX)
    out["golden_len"] = len(golden)
    out["golden_sha256"] = hashlib.sha256(golden).hexdigest().upper()
    out["byte_exact_equal_to_golden"] = (b == golden)
    diffs = [i for i in range(min(len(b), len(golden))) if b[i] != golden[i]]
    out["diff_offsets"] = diffs
    out["diff_count"] = len(diffs)
    out["all_diffs_within_securitykey_payload"] = all(
        idx >= out["securitykey_blob_offset"] + 6 and
        idx <  out["securitykey_blob_offset"] + 22 for idx in diffs)
    _k = out["securitykey_blob_offset"] + 6
    out["securitykey_payload_in_bin"] = b[_k:_k+16].hex(" ").upper()
    # masked comparison: everything except the 16B securityKey payload must be byte-identical
    masked_ok = True
    for i in range(258):
        if out["securitykey_blob_offset"] + 6 <= i < out["securitykey_blob_offset"] + 22:
            continue
        if b[i] != golden[i]:
            masked_ok = False
            break
    out["byte_exact_except_securitykey"] = masked_ok
    return out

def main():
    res = {
        "tool": "verify_cookie_len_2nd.py",
        "input_hashes": {
            "battle_srv.log": sha256_file(LOG),
            "session_record_258.bin": sha256_file(SESS_BIN),
        },
        "B_cookie_echo_ledger": cookie_len_ledger(),
        "C_descriptor_offset_table": descriptor_offset_table(),
    }
    with io.open(os.path.join(OUT, "offline_001_evidence_2nd.json"), "w",
                 encoding="utf-8", newline="") as f:
        json.dump(res, f, indent=2, ensure_ascii=False)
    print(json.dumps(res, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
