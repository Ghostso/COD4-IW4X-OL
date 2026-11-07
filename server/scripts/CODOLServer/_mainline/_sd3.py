p = r"CODOLServer\lobby_server\lobby_plain_probe.py"
s = open(p, encoding="utf-8").read()
anchor = '    conn.settimeout(20.0)\n    log(path, {"event": "accept", "peer": list(peer), "mode": "handshake"})'
assert anchor in s
new = (
'    if serve_delay > 0:\n'
'        # Delay the whole handshake so the client\'s per-frame processing\n'
'        # happens AFTER the observer\'s patches.  Measured: a patch written\n'
'        # before ~40 s makes the process exit at ~50 s, so the two events\n'
'        # must be ordered patch-first / frame-processing-second.\n'
'        log(path, {"event": "serve_delay_start", "peer": list(peer),\n'
'                   "seconds": serve_delay})\n'
'        time.sleep(serve_delay)\n'
'        log(path, {"event": "serve_delay_done", "peer": list(peer)})\n'
+ anchor)
s = s.replace(anchor, new, 1)
open(p, "w", encoding="utf-8").write(s)
print("inserted")
