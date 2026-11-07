#!/usr/bin/env python3
"""s138_b_namepool: 多编码复核 ReadQueuedMessages / queued 等名字池."""
import re, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
E = r"E:\codol_re\client_image_20261027.bin"
d = open(E, "rb").read(); N = len(d); VA = 0x400000

def hits(pat, enc):
    p = pat.encode(enc)
    out = []
    i = 0
    while True:
        j = d.find(p, i)
        if j < 0: break
        out.append(j); i = j + 1
        if len(out) >= 12: break
    return out

print("=== ASCII (case-sensitive) ===")
for w in ["ReadQueuedMessages","QueuedMessage","QueuedMessages","queued","Queued",
          "PushMessage","eventPush","channelData","ChannelData","MaxResults",
          "maxResults","consume","Consume","populateQueue","messageQueue",
          "subscribe","Subscribe","Messages","MessagesGet","MessagesRead",
          "QueuedMessageType","queuedMessage","QueuedEvent","pendingMessage"]:
    h = hits(w, "ascii")
    print("  %-20s %d  %s" % (w, len(h), ["0x%X" % x for x in h[:6]]))

print("\n=== UTF-16LE ===")
for w in ["ReadQueuedMessages","QueuedMessages","QueuedMessage","queued","Queued",
          "PushMessage","eventPush","channelData","Messages","subscribe","consume"]:
    h = hits(w, "utf-16-le")
    print("  %-20s %d  %s" % (w, len(h), ["0x%X" % x for x in h[:6]]))

print("\n=== 部分词: 'Messages' 前后各 40 字节的串上下文 ===")
p = b"Messages"
i = 0; cnt = 0
while cnt < 40:
    j = d.find(p, i)
    if j < 0: break
    i = j + 1
    # 提取周边串
    lo = max(0, j - 60); hi = min(N, j + 60)
    seg = d[lo:hi]
    toks = re.findall(rb"[\x20-\x7e]{2,}", seg)
    print("  @0x%X  %r" % (j, [t.decode() for t in toks]))
    cnt += 1
