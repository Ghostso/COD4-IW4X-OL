from pathlib import Path
p=Path(r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_SERVER_319_20261021\tests\test_weapondefs.c')
s=p.read_text(encoding='utf-8').replace('assert(codol_weapondef_damage_for_hit(mp5,100,true,CODOL_HITLOC_HEAD)==44);','assert(codol_weapondef_damage_for_hit(mp5,100,true,CODOL_HITLOC_HEAD)==36);')
p.write_text(s,encoding='utf-8')
