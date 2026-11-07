import json, base64
raw = open(r"CODOLServer\lobby_server\lobby_response.json", encoding="utf-8").read()
test = (raw.replace('"auth_task":$AUTH_TASK', '"auth_task":2')
           .replace("$IV_SEED", "0")
           .replace('"extra_data":$EXTRA_DATA', '"extra_data":"{}"'))
d = json.loads(test)
for k in ("client_ticket", "server_ticket", "lsg_server_ticket"):
    v = d[k]; dec = base64.b64decode(v)
    print("  %-22s b64len=%d dec=%d tag=%s plus=%s slash=%s"
          % (k, len(v), len(dec), dec[:4].hex(), "+" in v, "/" in v))
