from pathlib import Path
p=Path(r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_SERVER_319_20261021\include\codol_weaponattach_scalar_firingrange.inc')
s=p.read_text(encoding='utf-8')
extra='''  {"highcal_base", 2, {{20,6,29985,0x0e6c,0x00000004},{7,6,0,0x0d54,0x3fc00000}}},
  {"fmj_base", 2, {{7,8,29985,0x0e78,0x3f19999a},{20,6,0,0x0e6c,0x00000004}}},
'''
p.write_text(extra+s,encoding='utf-8')
print('added test attachments')
