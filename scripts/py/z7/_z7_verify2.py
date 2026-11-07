import json, base64, sys, os
sys.path.insert(0, os.path.abspath(r"CODOLServer\lobby_server"))
from mklobby_response import extra_data_json
raw = open(r"CODOLServer\lobby_server\lobby_response.json","rb").read()
p = raw.replace(b"$AUTH_TASK", b"2").replace(b"$IV_SEED", b"0")
_iext, _xtok = extra_data_json()
p = p.replace(b"$EXTRA_DATA", _xtok.encode() if isinstance(_xtok,str) else _xtok)
d = json.loads(p)
for k in ("code","iv_seed","auth_task"):
    print("  %-10s = %r" % (k, d[k]))
for k in ("client_ticket","server_ticket","lsg_server_ticket"):
    v = d[k]; dec = base64.b64decode(v)
    print("  %-20s dec=%d first4=%s" % (k, len(dec), dec[:4].hex()))
print("  ALL LEN==128:", all(len(base64.b64decode(d[k]))==128 for k in ("client_ticket","server_ticket","lsg_server_ticket")))
