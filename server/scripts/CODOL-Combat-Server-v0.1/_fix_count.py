# -*- coding: utf-8 -*-
import io
p = r"src\Engine\ClientLogic.cs"
s = io.open(p, encoding="utf-8").read()
old = '''                int mask = (int)((seq ^ 1u) & 0xFFu);
                for (int i = 8; i < payload.Length; i++) payload[i] ^= (byte)mask;
                SendData(s, payload);
            }'''
assert s.count(old) == 1, s.count(old)
new = '''                int mask = (int)((seq ^ 1u) & 0xFFu);
                for (int i = 8; i < payload.Length; i++) payload[i] ^= (byte)mask;
                SendData(s, payload);
                _snapshotCount++;   // [LEN-SCAN 2026-10-16] 供长度扫描分档
            }'''
s = s.replace(old, new)
io.open(p, "w", encoding="utf-8", newline="\n").write(s)
print("increment added")
