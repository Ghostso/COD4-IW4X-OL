# -*- coding: utf-8 -*-
"""Replay the probe's response pipeline: template -> substitutions -> parse."""
import json, os, sys
sys.path.insert(0, os.path.abspath(r"CODOLServer\lobby_server"))
from mklobby_response import extra_data_json
raw = open(r"CODOLServer\lobby_server\lobby_response.json","rb").read()
# replicate the probe: task 10 -> ans 11
p = raw.replace(b"$AUTH_TASK", b"11")
echo_iv = os.environ.get("CODO_L_ECHO_IV_SEED","0") == "1"
p = p if echo_iv else p.replace(b'"iv_seed":$IV_SEED', b'"iv_seed":0')
_iext, _xtok = extra_data_json()
p = p.replace(b"$EXTRA_DATA", _xtok.encode() if isinstance(_xtok,str) else _xtok)
print("--- final body ---")
print(p.decode("utf-8","replace"))
print()
try:
    d = json.loads(p)
    print("JSON OK")
    for k in ("auth_task","code","iv_seed","lsg_server_ticket_size"):
        print("  %-24s = %r" % (k, d.get(k)))
    for k in ("client_ticket","server_ticket","lsg_server_ticket"):
        v = d.get(k)
        if v:
            import base64
            dd = base64.b64decode(v)
            print("  %-24s = b64 len=%d dec=%d tag=%s" % (k, len(v), len(dd), dd[:4].hex()))
except Exception as e:
    print("JSON PARSE FAIL:", e)
