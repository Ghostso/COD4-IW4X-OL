#!/usr/bin/env python3
"""客户端遥测事件模板表全提取.
   特征: 形如 'EventName|%s|%u|%llu|...' 或 'EventName|${CODOID(%s)}|...'.
   在 E 镜像全范围扫(排除明显非事件串).
"""
import re
E=r"E:\codol_re\client_image_20261027.bin"
d=open(E,"rb").read(); N=len(d)

# 全镜像扫串 + 找带 |% 的
hits=[]
i=0
# 以 事件名 开头 的串: 名字后紧跟 '|'
for m in re.finditer(rb"([A-Z][A-Za-z0-9_]{2,40})\|(?=[%$][^|\x00]{0,40}\|)",d):
    hits.append((m.start(),m.group(0).split(b"\x00")[0]))
print("候选 %d 处"%len(hits))
# 去重(名字)
seen={}
for off,s in hits:
    try: t=s.decode("latin1")
    except: continue
    name=t.split("|")[0]
    if name not in seen:
        seen[name]=(off,t)
print("\n=== 事件模板 (名字 -> 格式) %d 种 ==="%len(seen))
for name,(off,t) in sorted(seen.items(),key=lambda kv:kv[1][0]):
    print("  0x%X  %s"%(off,t[:200]))
