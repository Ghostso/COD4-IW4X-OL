#!/usr/bin/env python3
"""file 0x9C6xxx-0x9C8xxx 遥测事件模板表全提取:
   每个模板 = 事件名 + printf 风格字段 (%u/%llu/%s/%d/...).
   目标: 一张完整"事件名→字段类型序列"表, 覆盖 71/* 所有事件.
"""
E=r"E:\codol_re\client_image_20261027.bin"
d=open(E,"rb").read()
def strs(lo,hi):
    out=[];i=lo
    while i<hi:
        e=d.find(b"\x00",i)
        if e<0 or e>hi: break
        s=d[i:e]
        out.append((i,s));i=e+1
    return out
# 扫一片. 先定范围: 0x9C6000-0x9C9000
print("=== file 0x9C6000-0x9C9000 内所有 >=6 串 ===")
count=0
templates=[]
for off,s in strs(0x9C6000,0x9C9000):
    if len(s)<6: continue
    try: t=s.decode("ascii")
    except:
        t=s.decode("latin1")
    if not all(32<=b<127 or b<32 for b in s): continue
    # 只保留看起来像"事件名|格式"或者纯字母名的
    import re
    if re.match(r"^[A-Za-z_][A-Za-z0-9_]*\|\S", t) or re.match(r"^[A-Z][A-Za-z0-9_]{4,}$", t):
        templates.append((off,t));count+=1
        print("  0x%X  %r"%(off,t))
print("\n共 %d 条"%count)
