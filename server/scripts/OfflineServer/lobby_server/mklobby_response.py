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
  0xB9A470   response parser. Requires, in order:
                 HTTP status 200
                 the request URL still parses
                 "auth_task" == expected
                 "code" == 700
                 "iv_seed" present
                 "client_ticket" base64 -> exactly 0x80 bytes
                 "server_ticket" base64 -> exactly 0x80 bytes
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
    # Stage 32 must be answered with 0x39 (57), NOT 0x21 (33).
    # 0xB9A470 stores the parsed auth_task into [objA+0x18], and the gate
    # that decides whether objC (the ticket object) gets created is
    # 0xB889D0:  cmp dword ptr [ecx+0x18], 0x39 / sete al
    # Answering 33 passes the validator (it accepts 0x21 or 0x39) but fails
    # that later gate, so 0x801A00 is never called and the lobby stage dies.
    32: 57,    # 0x20     -> 0x39
}

# engine "null reference" tag; [obj+0xD8] must equal this for success
NULL_REF = 0xEFBDADDE
NULL_REF_BYTES = NULL_REF.to_bytes(4, "little")   # DE AD BD EF

TICKET_LEN = 0x80   # both tickets must base64-decode to exactly 128 bytes



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
        '"lsg_server_ticket_size":%d,"lsg_server_ticket":"%s"}'
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

    probe = payload.replace("$AUTH_TASK", "11").replace("$IV_SEED", "0")
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
    print(payload.replace("$AUTH_TASK", "11").replace("$IV_SEED", "0"))
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
