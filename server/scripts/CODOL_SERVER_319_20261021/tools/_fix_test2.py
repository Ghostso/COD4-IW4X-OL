from pathlib import Path
p=Path(r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_SERVER_319_20261021\tests\test_weapondefs.c')
s=p.read_text(encoding='utf-8').replace('assert(codol_weapondef_damage_for_hit(ak,100,true,CODOL_HITLOC_HEAD)==54);','assert(codol_weapondef_damage_for_hit(ak,100,true,CODOL_HITLOC_HEAD)==49);')
p.write_text(s,encoding='utf-8')
print('patched')
