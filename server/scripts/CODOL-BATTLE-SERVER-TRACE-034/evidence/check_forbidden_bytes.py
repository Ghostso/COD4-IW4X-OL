# -*- coding: utf-8 -*-
"""TASK-034: does the LOCAL target configstring region enforce forbidden bytes 0x25 / 0x92 ?"""
import capstone, re
IMG = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(IMG,'rb').read(); BASE=0x400000
# scan the whole .text1 for cmp r/m8, imm8 with imm==0x25 or 0x92 
print("== 'cmp .., 0x25' and 'cmp .., 0x92' occurrences in 0x1000..0x8A6000 ==")
for imm in (0x25,0x92):
    hits=[]
    # forms: 80 /7 ib ; 3C ib (cmp al,imm8) ; 81/83 /7 imm32 (less likely) ; F6/F7 test
    for i in range(0x1000, 0x8A6000-6):
        if d[i]==0x80 and (d[i+1]&0xF8)==0x38 and d[i+2]==imm: hits.append((i,"80/7"))
        if d[i]==0x3C and d[i+1]==imm: hits.append((i,"3C"))
    print("  imm 0x%02X : %d hits  %s" % (imm,len(hits), ["%X(%s)"%(h,f) for h,f in hits[:16]]))
print()
print("== narrow to the configstring family (RVA 0x6D870..0x6E100) ==")
for imm in (0x25,0x92):
    loc=[]
    for i in range(0x6D870,0x6E100-3):
        if d[i]==0x80 and (d[i+1]&0xF8)==0x38 and d[i+2]==imm: loc.append((i,"80/7"))
        if d[i]==0x3C and d[i+1]==imm: loc.append((i,"3C"))
    print("  imm 0x%02X : %s" % (imm, ["%X(%s)"%(h,f) for h,f in loc] or "NONE"))
