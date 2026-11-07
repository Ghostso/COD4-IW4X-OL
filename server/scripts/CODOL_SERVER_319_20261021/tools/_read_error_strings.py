p=r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin'
d=open(p,'rb').read()
for v in [0xd37a7c,0xd377ac,0xd37c5c,0xd377c0,0xdadec4]:
    o=v-0x400000
    e=d.find(b'\0',o)
    print(hex(v),d[o:e].decode('latin1','replace'))
