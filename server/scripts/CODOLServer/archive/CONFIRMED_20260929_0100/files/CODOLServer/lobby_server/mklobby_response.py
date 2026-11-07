"""Build lobby_response.json for the /auth/ probe server.

Contract decoded from the retail client codoMP_client_shipRetail.exe.
The single most important rule: **the response "auth_task" is the ANSWER to
the request "auth_task"**, and the allowed answers are table-driven.

  0x7F2B90   start of an /auth/ round trip; sets sub-state [0x84ABA60] = 6
  0xB992E0   sets [obj+0x14] (stage) = 10, then sends the request
  0xB99B8C   request "auth_task" = [obj+0x14]  (the stage is echoed as task)
  0xB9A370   per-frame update; when the HTTP object reports state 5 (answer
             received) it calls [obj vtable +0x18] and stores the result in
             [obj+0x156C]
  0xB999C0   objB response dispatcher, keyed on the stage byte table at
             0xB99A40 / jump table at 0xB99A28:
                 stage 0   -> 0xB991A0          expects auth_task == 1
                 stage 10  -> 0xB9A470(0x0B)    expects auth_task == 11
                 stage 12  -> 0xB9A470(0x0D)    expects auth_task == 13
                 stage 24  -> 0xB9A470(0x19)    expects auth_task == 25
                 stage 26  -> 0xB9A470(0x1B)    expects auth_task == 27
                 other     -> 0x2CB (715), hard fail
  0xB99940   validator enforcing that rule (expected == answer, high word 0)
  0xB9A470   response parser shared by BOTH client classes.  Requires, in order:
                 HTTP status 200
                 the request URL still parses
                 "auth_task" == expected (validator [vtable+0x1C])
                 "code" == 700 (high dword 0)
                 0xB9A190() (no-op, always true)
                 "iv_seed" present
                 "client_ticket" base64 -> exactly [ebp+0xC] bytes (0x80 here)
                 "server_ticket" base64 -> exactly 0x80 bytes
                 [vtable+0x24](&json) == true      <-- extra_data, see below
                 client_ticket[0..3] LE uint32 == 0xEFBDADDE
                 0xBA9980 copies that tag into [obj+0xD8]; compare again
                 0xBA97B0 decrypts 24 bytes -> [obj+0x28], iv_seed -> [obj+0x2C]
              735 (0x2DF) is written in exactly two places: 0xB9A59B
              (auth_task field/validator) and 0xB9A7C7 (code missing, ticket
              length mismatch, [vtable+0x24] false, or [vtable+0x20] false).

  Two client classes share 0xB9A470:
    objB  vtable 0xD5A1F8 (0x32D0 bytes, created at 0x7F2C1D)
          dispatcher 0xB999C0: stages 0/10/12/24/26 only (0x7F2C19: stage
          > 0x1A -> 715); validator 0xB99940 accepts 11, 69 or expected;
          [vtable+0x24] = 0xB99610 needs a nested "extra_data" string with
          extended_data / cd_key / time_to_live, but tolerates its absence.
    objA  vtable 0xD59A7C (0x3E60 bytes, created at 0x7F2BE5 ONLY when the
          TCLS switch [0x331C5C0] != 0)
          dispatcher 0xB88A30: ONLY stage 0x20 (32), else 715;
          validator 0xB889E0 accepts answer 33 (0x21) or 57 (0x39);
          0xB889D0 "is polling" == ([objA+0x18] == 0x39);
          [vtable+0x24] = 0xB88FC0 REQUIRES a nested "extra_data" string with
          username / encrypted_codoid (base64 -> exactly 16 bytes) /
          encrypted_register_codoid_data (base64 -> <= 1024 bytes).
          0xB88CC0 sets [objA+0x14] = 0x20 and sends the request.

  0x7F2DB0  (auth sub-state handler) advances ONLY on result 700, then sets
          sub_state = 9, and creates the lobby object objC via 0x801A00 when
          [0x331C5C0] != 0 AND 0xB889D0 is true -> the stage-32 answer MUST be
          57 (0x39); answering 33 leaves sub_state=9 with no lobby socket.
          0x7F2FF2 additionally needs [0x81A9EC4] == 0x1BB (443) for its retry
          path.  [0x81A9EB8]/[0x81A9EC4] and [0x81A76A8] are filled by
          TenProxy ApplySettings (0x641600) from the TCLS shared memory.
  0xB783C0   bounds-checked blob reader (src, srclen, off, *next, dst, n)
  0xBA9980   copies client_ticket[0..3] into [obj+0xD8]
  0xB9A809   success iff [obj+0xD8] == 0xEFBDADDE
             => client_ticket MUST start with the 4 bytes  DE AD BD EF
  0xB9A79C   that same 4-byte tag also short-circuits the iv_seed based
             crypto at [obj vtable +0x20] (0xB99350), so no real key
             material is needed for a private server.
  0x7F2DB0   auth sub-state 6 only advances to 9 on [obj+0x156C] == 0x2BC
             (700). Anything else falls through to 0x7F2FED, fails the
             443-port test, and clears sub-state to 0 -> 0x7F271B then sets
             [0x84ABA50] = 0 -> "SF_UI_DW_LIVE_CONNECTING_FAILED".

$AUTH_TASK / $IV_SEED placeholders are substituted per request by
lobby_probe_server.py. ASCII only.

Usage:
  python -X utf8 mklobby_response.py
"""
import base64
import json
import os
import sys

here = os.path.dirname(os.path.abspath(__file__))
out = os.path.join(here, "lobby_response.json")

# request auth_task (== client stage) -> response auth_task
TASK_ANSWER = {
    0: 1,      # stage 0  -> 0xB991A0
    10: 11,    # 0x0A     -> 0xB9A470(0x0B)
    12: 13,    # 0x0C     -> 0xB9A470(0x0D)
    24: 25,    # 0x18     -> 0xB9A470(0x19)
    26: 27,    # 0x1A     -> 0xB9A470(0x1B)
    # 33 (0x21) also passes 0xB889E0, but only 57 makes 0xB889D0 true, and
    # 0x7F2E8D only creates objC (the lobby object) when that answer is 57.
    # 0x801A00 gets (&objA[0x28], &objA[0xD8]) and owns the lobby socket.
    32: 57,    # 0x20     -> 0x39 (57) = polling answer, gates objC
}

# engine "null reference" tag; [obj+0xD8] must equal this for success
NULL_REF = 0xEFBDADDE
NULL_REF_BYTES = NULL_REF.to_bytes(4, "little")   # DE AD BD EF

TICKET_LEN = 0x80   # both tickets must base64-decode to exactly 128 bytes



# ---------------------------------------------------------------- extra_data
# 0xB9A470 calls [obj vtable+0x24] with the parsed reply and returns 735
# (0x2DF) when that call says "no".  Both client classes want a nested JSON
# *string* in "extra_data", with different inner keys:
#
#   objB  (vtable 0xD5A1F8, stages 10/12/24/26, fallback path) -> 0xB99610
#       "extended_data"  string  <= 4096 bytes   (0xBAA490 copies it)
#       "cd_key"         base64 string           (0xB997E4)
#       "time_to_live"   int                     (0xB9984B)
#     Note 0xB996AC: when "extra_data" is ABSENT objB returns TRUE, so for the
#     fallback stages it is optional - but a present-and-wrong one is fatal.
#
#   objA  (vtable 0xD59A7C, stage 32, real lobby path)          -> 0xB88FC0
#       "username"                        string (-> [objA+0x35B4], UI name)
#       "encrypted_codoid"                base64 -> EXACTLY 16 bytes
#                                         (0xB891CB cmp edi,0x10 -> else 735)
#       "encrypted_register_codoid_data"  base64 -> <= 1024 bytes
#     Here extra_data is MANDATORY: 0xB8902E je 0xB891F8 -> return FALSE -> 735.
#
# One merged payload therefore satisfies both parsers.
EXTRA_DATA = {
    "username": "CODOL_LOCAL",
    "encrypted_codoid": None,                 # filled by extra_data_json()
    "encrypted_register_codoid_data": None,   # filled by extra_data_json()
    "extended_data": '{"version":"0","extended_data":true}',
    "cd_key": None,                           # filled by extra_data_json()
    "time_to_live": 3600,
}

CODOID_BYTES = b"CODOL-LOCAL-0001"          # exactly 16 bytes
REGISTER_BYTES = bytes(range(0x20, 0x60)) * 2   # 128 readable bytes
CD_KEY_BYTES = bytes(range(0x00, 0x40))         # 64 bytes


def extra_data_json():
    """Return (inner JSON text, JSON-string-escaped token) for the body."""
    inner = dict(EXTRA_DATA)
    inner["encrypted_codoid"] = base64.b64encode(CODOID_BYTES).decode("ascii")
    inner["encrypted_register_codoid_data"] = base64.b64encode(
        REGISTER_BYTES).decode("ascii")
    inner["cd_key"] = base64.b64encode(CD_KEY_BYTES).decode("ascii")
    text = json.dumps(inner, separators=(",", ":"), sort_keys=True)
    return text, json.dumps(text)


def client_ticket():
    """128 bytes whose first 4 bytes are the NULL_REF tag."""
    body = bytes((i * 5 + 17) & 0xFF for i in range(TICKET_LEN - 4))
    return NULL_REF_BYTES + body


def server_ticket():
    """128 bytes; MUST also start with NULL_REF tag (0xEFBDADDE) because
    the same validator (0xC73230) is used for both tickets."""
    body = bytes((i * 11 + 29) & 0xFF for i in range(TICKET_LEN - 4))
    return NULL_REF_BYTES + body


def build():
    ct = client_ticket()
    st = server_ticket()
    ct_b64 = base64.b64encode(ct).decode("ascii")
    st_b64 = base64.b64encode(st).decode("ascii")
    payload = (
        '{"auth_task":$AUTH_TASK,"code":700,"iv_seed":$IV_SEED,'
        '"client_ticket":"%s","server_ticket":"%s",'
        # kept for the queue/other-stage schema (0xB983F0, 0xBA9BC0);
        # ignored by the auth_task parsers.
        '"next_poll_after":0,"estimated_wait_time":0,"member_position":0,'
        '"lsg_server_ticket_size":%d,"lsg_server_ticket":"%s",'
        '"extra_data":$EXTRA_DATA}'
        % (ct_b64, st_b64, TICKET_LEN, st_b64)
    )
    return payload, ct, st, ct_b64, st_b64


def selftest(payload, ct, st):
    """Validate every hard requirement the client enforces."""
    ok = True

    def chk(label, cond):
        nonlocal ok
        print("  [%s] %s" % ("PASS" if cond else "FAIL", label))
        if not cond:
            ok = False

    iext, xtok = extra_data_json()
    probe = (payload.replace("$AUTH_TASK", "11").replace("$IV_SEED", "0")
                    .replace("$EXTRA_DATA", xtok))
    try:
        doc = json.loads(probe)
    except ValueError as e:
        chk("template parses as JSON: %s" % e, False)
        return False
    chk("template parses as JSON", True)

    chk("auth_task is an int in TASK_ANSWER.values()",
        isinstance(doc.get("auth_task"), int)
        and doc["auth_task"] in TASK_ANSWER.values())
    chk("code == 700", doc.get("code") == 700)
    chk("iv_seed present and int", isinstance(doc.get("iv_seed"), int))

    for name, raw in (("client_ticket", ct), ("server_ticket", st)):
        got = base64.b64decode(doc[name])
        chk("%s decodes to exactly %d bytes (got %d)"
            % (name, TICKET_LEN, len(got)), len(got) == TICKET_LEN)

    ct_dec = base64.b64decode(doc["client_ticket"])
    chk("client_ticket[0..3] == %s"
        % " ".join("%02X" % b for b in NULL_REF_BYTES),
        ct_dec[:4] == NULL_REF_BYTES)
    chk("client_ticket[0..3] LE uint32 == 0x%08X" % NULL_REF,
        int.from_bytes(ct_dec[:4], "little") == NULL_REF)

    v = int.from_bytes(ct_dec[:4], "little")
    print("  note: [obj+0xD8] will be 0x%08X, success requires 0x%08X"
          % (v, NULL_REF))
    print("  note: iv_seed crypto at [vtable+0x20] is skipped because the")
    print("        tag matches 0xEFBDADDE (0xB9A79C / 0xB9A7A2)")

    # ---- extra_data: what [obj vtable+0x24] checks (735 otherwise) ----------
    chk("extra_data present and is a JSON string",
        isinstance(doc.get("extra_data"), str))
    inner = None
    try:
        inner = json.loads(doc["extra_data"])
    except (KeyError, ValueError):
        pass
    chk("extra_data parses as nested JSON", isinstance(inner, dict))
    if not isinstance(inner, dict):
        return False

    # objA (stage 32, 0xB88FC0)
    chk("objA: 'username' present and <= 63 chars",
        isinstance(inner.get("username"), str)
        and 0 < len(inner["username"]) <= 63)
    cod = inner.get("encrypted_codoid")
    try:
        cod_raw = base64.b64decode(cod)
    except Exception:
        cod_raw = b""
    chk("objA: 'encrypted_codoid' base64-decodes to exactly 16 bytes (got %d)"
        % len(cod_raw), len(cod_raw) == 16)
    reg = inner.get("encrypted_register_codoid_data")
    try:
        reg_raw = base64.b64decode(reg)
    except Exception:
        reg_raw = b""
    chk("objA: 'encrypted_register_codoid_data' decodes to <= 1024 bytes "
        "(got %d)" % len(reg_raw), 0 < len(reg_raw) <= 1024)

    # objB (stages 10/12/24/26, 0xB99610)
    chk("objB: 'extended_data' present and <= 4096 bytes",
        isinstance(inner.get("extended_data"), str)
        and 0 < len(inner["extended_data"]) <= 4096)
    chk("objB: 'cd_key' present and is a string",
        isinstance(inner.get("cd_key"), str) and inner["cd_key"] != "")
    chk("objB: 'time_to_live' present and int",
        isinstance(inner.get("time_to_live"), int))

    # ---- the stage-32 answer gate (an answer of 33 never opens the lobby) ---
    chk("TASK_ANSWER[32] == 57 (0x39) so 0xB889D0 (is-polling) is true",
        TASK_ANSWER.get(32) == 57)
    return ok


def main():
    payload, ct, st, ct_b64, st_b64 = build()
    with open(out, "w", encoding="ascii", newline="") as f:
        f.write(payload)
    print("wrote " + out)
    print("auth_task mapping (request -> response):")
    for k in sorted(TASK_ANSWER):
        print("  %2d -> %d   (0x%02X -> 0x%02X)" % (k, TASK_ANSWER[k],
                                                    k, TASK_ANSWER[k]))
    print()
    _iext, _xtok = extra_data_json()
    print(payload.replace("$AUTH_TASK", "11").replace("$IV_SEED", "0")
                .replace("$EXTRA_DATA", _xtok))
    print()
    print("extra_data inner JSON (substituted for $EXTRA_DATA):")
    print("  " + _iext)
    print()
    print("client_ticket raw  : %d bytes, head %s"
          % (len(ct), " ".join("%02X" % b for b in ct[:8])))
    print("server_ticket raw  : %d bytes, head %s"
          % (len(st), " ".join("%02X" % b for b in st[:8])))
    print("base64 lengths     : client=%d server=%d"
          % (len(ct_b64), len(st_b64)))
    print()
    print("self test:")
    ok = selftest(payload, ct, st)
    print()
    print("RESULT: " + ("ALL CHECKS PASSED" if ok else "SOME CHECKS FAILED"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
