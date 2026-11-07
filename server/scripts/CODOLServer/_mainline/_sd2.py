p = r"CODOLServer\lobby_server\lobby_plain_probe.py"
s = open(p, encoding="utf-8").read()
anchor = '    conn.settimeout(20.0)\n    log(path, {"event": "accept", "peer": list(peer), "mode": "handshake"})'
print("found:", anchor in s)
if anchor not in s:
    # show what is actually there
    i = s.find("    conn.settimeout(20.0)")
    print(repr(s[i:i+140]))
