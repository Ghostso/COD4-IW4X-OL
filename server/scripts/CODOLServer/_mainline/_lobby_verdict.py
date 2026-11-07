"""Decode a _lobby_watch.py watch.jsonl and report the exact branch that
produced the lobby failure dialog ("Cannot connect to lobby service").

READ-ONLY analysis of an existing log file. ASCII only.

Usage:
  python -X utf8 _lobby_verdict.py --log <watch.jsonl>

Background (from static RE of codoMP_client_shipRetail.exe):

  0x007F25B0  lobby status probe
      [0x849BA3D] != 0            -> return 4  (FAIL)
      [0x84ABA50] == 0            -> return 4  (FAIL)
      [0x84ABA50] in 1..4         -> return 1  (still connecting)
      [0x84ABA50] == 5            -> return 3  (CONNECTED)

  0x007EF1C8  DW state 1 handler: status 3 -> advance, status 4 -> dialog
  0x007F26C0  lobby state machine driven by [0x84ABA50]
      1 dwLogonStart               -> 0x7F26E0  DNS
      2 DW_DNS_COMPLETE            -> 0x7F271B  auth sub-machine
      3 DW_ACCOUNT_LOGIN_COMPLETE  -> 0x7F276A
      4 DW_LOBBY_CONNECTED         -> 0x7F27B0
      5 (ok, done)

  0x007F271B case 2:
      call 0x7F28F0 (auth sub-state dispatcher, returns [0x84ABA60])
      ret == 0 -> [0x84ABA50] = 0 with "DW_ACCOUNT_ERROR"  <-- the dialog
      ret == 9 -> [0x84ABA50] = 3 with "DW_ACCOUNT_LOGIN_COMPLETE"

  0x007F2DB0  auth sub-state 6 (the /auth/ round trip):
      [obj+0x156C] result code decides the branch:
        0x2BC (700) -> sub_state 9 (or 8)   SUCCESS
        0x2C0 (704) -> retry once, then last_err=0x2C0
        0x2D5 (725) -> sub_state 4
        0x2DC (732) -> sub_state 0           FAIL, last_err untouched
        0x6D  (109) -> sub_state 0           FAIL, last_err untouched
        port != 0x1BB -> sub_state 0          FAIL, last_err = code
"""
import argparse
import json
import sys

L_STATE = {
    0: "FAIL/RESET",
    1: "dwLogonStart",
    2: "DW_DNS_COMPLETE",
    3: "DW_ACCOUNT_LOGIN_COMPLETE",
    4: "DW_LOBBY_CONNECTED",
    5: "OK/CONNECTED",
}

SUB_STATE = {
    0: "FAIL-IDLE (0x7F28F0 returns 0)",
    1: "0x7F2913 / 0x7F29C0 start",
    2: "0x7F2AB0 waiting",
    3: "0x7F2973 stop",
    4: "0x7F298C idle",
    5: "0x7F2B90 begin auth",
    6: "0x7F2DB0 /auth/ round trip",
    7: "0x7F295B 0x7F3100 poll",
    8: "0x7F294F 0x7F3190 queue wait",
    9: "0x7F298C DONE (success)",
}

CODE_HINTS = {
    0x2BC: "700 OK -> sub_state 9",
    0x2C0: "704 retry-once",
    0x2D5: "725 -> sub_state 4",
    0x2DC: "732 -> sub_state 0 FAIL (last_err untouched)",
    0x6D: "109 -> sub_state 0 FAIL (last_err untouched)",
    0x2DF: "735 auth_task/key mismatch",
    0x2E1: "737",
    0x2E7: "743",
}

def load(path):
    out = []
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except ValueError:
                continue
    return out


def hx(v):
    return ("0x%X" % v) if isinstance(v, int) else v


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", required=True)
    a = ap.parse_args()

    rows = load(a.log)
    events = [r for r in rows if "ev" in r]
    hist = [r for r in rows if "t" in r]
    print("samples = %d  events = %d" % (len(hist), len(events)))
    for e in events:
        print("  event:", e)
    if not hist:
        print("no samples")
        return 1

    print("")
    print("--- distinct values ---")
    for k in ("uA50", "sub_state", "obj_code", "bA3D", "dw_state",
              "last_err", "uA64", "uA78", "port"):
        seen = {}
        for r in hist:
            v = hx(r.get(k)) if k in ("obj_code", "last_err") else r.get(k)
            seen[v] = seen.get(v, 0) + 1
        print("  %-10s -> %s" % (k, seen))

    print("")
    print("--- lobby state [0x84ABA50] transitions (with state name) ---")
    last = object()
    for r in hist:
        key = (r.get("uA50"), r.get("sub_state"))
        if key == last:
            continue
        last = key
        print("  t=%7.2f  uA50=%-3s %-24s sub=%-3s %-34s obj_code=%-8s bA3D=%s"
              % (r.get("t"), r.get("uA50"),
                 L_STATE.get(r.get("uA50"), "?"), r.get("sub_state"),
                 SUB_STATE.get(r.get("sub_state"), "?"),
                 hx(r.get("obj_code")), r.get("bA3D")))

    print("")
    print("--- state-name string transitions ([0xE4EA3C]) ---")
    lastnm = object()
    for r in hist:
        nm = r.get("nm")
        if nm == lastnm:
            continue
        lastnm = nm
        print("  t=%7.2f  nm=%s" % (r.get("t"), nm))

    print("")
    print("--- window around the failure ---")
    bad = [r for r in hist if r.get("uA50") == 0 and r.get("t", 0) > 10]
    if bad:
        t0 = bad[0]["t"]
        print("  first uA50==0 at t=%.2f" % t0)
        for r in hist:
            if t0 - 3.0 <= r.get("t", 0) <= t0 + 1.0:
                print("   t=%7.2f dw=%s uA50=%s sub=%-3s obj_code=%-8s "
                      "obj_busy=%-5s last_err=%-8s uA64=%s bA3D=%s nm=%s"
                      % (r.get("t"), r.get("dw_state"), r.get("uA50"),
                         r.get("sub_state"), hx(r.get("obj_code")),
                         r.get("obj_busy"), hx(r.get("last_err")),
                         r.get("uA64"), r.get("bA3D"), r.get("nm")))
    else:
        print("  no uA50==0 sample after t=10 (client may not have failed)")

    print("")
    print("--- verdict ---")
    final = hist[-1]
    u = final.get("uA50")
    if u == 5:
        print("  PASS: lobby state reached 5 (connected).")
    elif u == 0:
        print("  FAIL: lobby state is 0 -> 0x7F25B0 returns 4 -> dialog")
        print("        'SF_UI_DW_LIVE_CONNECTING_FAILED'.")
        subs = sorted(x for x in set(r.get("sub_state") for r in hist)
                      if x is not None)
        codes = sorted(c for c in set(r.get("obj_code") for r in hist)
                       if isinstance(c, int))
        print("        observed sub_states: %s" % subs)
        print("        observed obj_codes : %s" % [hx(c) for c in codes])
        for c in codes:
            if c in CODE_HINTS:
                print("          %s = %s" % (hx(c), CODE_HINTS[c]))
        if 6 in subs and 9 not in subs:
            print("        auth round trip ran (sub 6) but never reached 9.")
        if 9 not in subs:
            print("        => /auth/ response was NOT accepted as success.")
    else:
        print("  UNRESOLVED: lobby state = %s (still pending / truncated)"
              % u)
    print("  last sample keys: %s" % sorted(final.keys()))
    return 0


if __name__ == "__main__":
    sys.exit(main())

