p = r"CODOLServer\lobby_server\lobby_plain_probe.py"
s = open(p, encoding="utf-8").read()

# 1) add the parameter to serve_handshake signature (after handshake_delay-like args)
anchor = "                    hold_after_83: float = 0.0,"
assert anchor in s
s = s.replace(anchor, anchor + "\n                    serve_delay: float = 0.0,", 1)

# 2) insert the delay at the very start of the connection body
old_body = '''    """Drive the 0x81 -> client 0x82 -> 0x83 handshake.'''
assert old_body in s
# find the first log/accept line inside serve_handshake after the docstring
import re
m = re.search(r'(def serve_handshake\([\s\S]*?\n    \)\s*->\s*None:\n(?:    """[\s\S]*?"""\n)?)(\s*)([^\n]*\n)', s)
print("anchor2 found:", bool(m))
if m:
    insert = m.group(1) + m.group(2) + (
        "if serve_delay > 0:\n"
        + m.group(2) + "    # Delay the whole handshake so that the client's\n"
        + m.group(2) + "    # per-frame processing happens LATER than the observer's\n"
        + m.group(2) + "    # patches (which cannot be written before ~40 s without\n"
        + m.group(2) + "    # killing the process at ~50 s).\n"
        + m.group(2) + "    log(path, {\"event\": \"serve_delay_start\",\n"
        + m.group(2) + "               \"peer\": list(peer), \"seconds\": serve_delay})\n"
        + m.group(2) + "    time.sleep(serve_delay)\n"
        + m.group(2) + "    log(path, {\"event\": \"serve_delay_done\", \"peer\": list(peer)})\n"
    ) + m.group(3)
    s = s[:m.start()] + insert + s[m.end():]

# 3) CLI arg
old_cli = '    ap.add_argument("--hold-after-83", type=float, default=0.0,'
assert old_cli in s
s = s.replace(old_cli,
    '    ap.add_argument("--serve-delay", type=float, default=0.0,\n'
    '                    help="wait this many seconds after accept before "\n'
    '                         "driving the handshake (moves the client\'s frame "\n'
    '                         "processing later in time)")\n'
    + old_cli, 1)

open(p,"w",encoding="utf-8").write(s)
print("probe patched")
