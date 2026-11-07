"""Decide whether the client's 0x85 payloads are DW bit-packed frames
(i.e. the plain socket is relaying Demonware traffic) or a private
protocol of that socket.

Read-only: consumes capture logs only, touches no process and no game file.

Evidence used:
  * CODOLServer/logs/*/plain.jsonl   -- the 0x85 frames the client sent
  * the DW read path in the runtime image (0xBA20A0 / 0xBA3710) is only
    consulted for the structural expectation, not executed.

What "DW bit-packed" would look like:
  the DW demarshaller reads a length prefix then a bit-packed body whose
  first byte is typically a small control byte.  A 373-byte, 181-byte and
  405-byte payload that is *uniformly high entropy with no readable
  structure* is consistent with an encrypted/compressed body, NOT with a
  plain bit-packed message (those show low-entropy headers and repeating
  field patterns).

So the test performed here is a shape test: entropy, byte histogram, and
whether any payload region decodes as a plausible small-integer header.
"""
from __future__ import annotations

import glob
import json
import math
import os
import collections

ROOT = r"D:\BaiduNetdiskDownload\使命召唤OL"


def entropy(b: bytes) -> float:
    if not b:
        return 0.0
    c = collections.Counter(b)
    n = len(b)
    return -sum((v / n) * math.log2(v / n) for v in c.values())


def load_frames():
    frames = []
    for p in glob.glob(os.path.join(ROOT, "CODOLServer", "logs", "*",
                                    "plain.jsonl")):
        try:
            fh = open(p, encoding="utf-8", errors="replace")
        except OSError:
            continue
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                o = json.loads(line)
            except Exception:
                continue
            if o.get("event") not in ("recv", "hold_recv"):
                continue
            h = o.get("hex") or ""
            try:
                b = bytes.fromhex(h)
            except ValueError:
                continue
            frames.append((os.path.basename(os.path.dirname(p)), b))
    return frames


def split_frames(b: bytes):
    """Split a recv blob into (len, type, opcode, seq, body) chunks."""
    out = []
    i = 0
    while i + 6 <= len(b):
        ln = int.from_bytes(b[i:i + 4], "little")
        if ln < 6 or i + 4 + ln > len(b):
            break
        t = b[i + 4]
        op = b[i + 5]
        seq = b[i + 6] if i + 7 <= len(b) else None
        body = b[i + 10:i + 4 + ln]
        out.append((ln, t, op, seq, body))
        i += 4 + ln
    return out


def main():
    frames = load_frames()
    print("recv blobs loaded: %d" % len(frames))
    seen = set()
    n85 = 0
    for tag, b in frames:
        for ln, t, op, seq, body in split_frames(b):
            key = (tag, ln, seq)
            if key in seen:
                continue
            seen.add(key)
            if op != 0x85:
                continue
            n85 += 1
            e = entropy(body)
            uniq = len(set(body))
            top = collections.Counter(body).most_common(3)
            print()
            print("  tag=%s  len=%d  op=0x%02X seq=%s" % (tag, ln, op, seq))
            print("    body=%d bytes  entropy=%.3f bits/byte  distinct=%d/256"
                  % (len(body), e, uniq))
            print("    most common: %s" % [(hex(v), c) for v, c in top])
            print("    head: %s" % body[:16].hex(" "))
            # a DW bit-packed header would be a small control byte followed
            # by low-entropy field data; report the first byte explicitly
            if body:
                print("    first byte = 0x%02X" % body[0])
    print()
    print("0x85 frames examined: %d" % n85)
    print()
    print("interpretation key:")
    print("  entropy > 7.8 and distinct ~256  -> encrypted/compressed body")
    print("  entropy < 6.5 or visible structure -> plain bit-packed message")


if __name__ == "__main__":
    main()
