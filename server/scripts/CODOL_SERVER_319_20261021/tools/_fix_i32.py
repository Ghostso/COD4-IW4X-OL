from pathlib import Path
p=Path(r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_SERVER_319_20261021\src\battle\weaponattach.c')
s=p.read_text(encoding='utf-8')
s=s.replace('static int i32v(uint32_t v) { return (int)v; }', 'static int i32v(uint32_t v) { int i; memcpy(&i,&v,4); return i; }')
p.write_text(s,encoding='utf-8')
print('patched i32v')
