import os
b=open(r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\ENGINE_DUMP_20260925_111537\engine\engine_best.bin','rb').read()
base=0x00994000
for va in [0x00CD2550,0x00CD3468,0x00CD34B0,0x00CD34F8,0x00CD3538,0x00CD35F4,0x00CD3618,0x00CD3950,0x00CD8340,0x00CD8388,0x00CD9490]:
    off=va-base
    chunk=b[off:off+160]
    asc=''.join(chr(c) if 32<=c<127 else '.' for c in chunk)
    print('\n%08x off=%x' % (va,off))
    print(asc)
    print(chunk[:96].hex(' '))
