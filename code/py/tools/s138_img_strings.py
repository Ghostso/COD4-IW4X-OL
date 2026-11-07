#!/usr/bin/env python3
"""s138_img_strings: 在客户端镜像里按多种编码搜 Messaging/queue/read 等, 并给上下文串."""
import re, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
E = r"E:\codol_re\client_image_20261027.bin"
d = open(E, "rb").read(); N = len(d); VA = 0x400000

def find_all(pat, limit=20):
    out = []; i = 0
    while True:
        j = d.find(pat, i)
        if j < 0: break
        out.append(j); i = j + 1
        if len(out) >= limit: break
    return out

def ctx(off, back=48, fwd=64):
    lo = max(0, off - back); hi = min(N, off + fwd)
    toks = re.findall(rb"[\x20-\x7e]{3,}", d[lo:hi])
    return [t.decode() for t in toks]

print("=== 客户端镜像: 关键词命中 ===")
for w in ["Messaging", "messaging", "readQueuedMessages", "QueuedMessages",
          "sendInstantMessage", "InstantMessage", "Channelmessage",
          "Demonware::", "Messaging2", "AckOnly", "ServiceRegistry",
          "ServiceResponse", "ServiceRequest", "registerTasks",
          "channelmessage", "ChannelMessage", "dwMessage", "MessageQueue",
          "msgQueue", "PushMessages", "eventpush", "EventPush"]:
    hits = find_all(w.encode(), 12)
    if hits:
        print("  %-22s %d  首: %s" % (w, len(hits), ["0x%X" % h for h in hits[:6]]))
        for h in hits[:2]:
            print("        ctx %r" % ctx(h))
    else:
        print("  %-22s 0" % w)

print("\n=== UTF-16LE: Messaging / readQueuedMessages ===")
for w in ["Messaging", "readQueuedMessages", "InstantMessage", "Channelmessage"]:
    hits = find_all(w.encode("utf-16-le"), 8)
    print("  %-22s %d  %s" % (w, len(hits), ["0x%X" % h for h in hits[:6]]))
