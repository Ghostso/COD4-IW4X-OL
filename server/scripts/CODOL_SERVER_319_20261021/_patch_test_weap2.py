from pathlib import Path
p=Path(r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_SERVER_319_20261021\tests\test_weapondefs.c')
s=p.read_text(encoding='utf-8')
s=s.replace('assert(m4->clip_size==30 && m4->fire_time_ms==71);', 'assert(m4->clip_size==30 && m4->fire_time_ms==71);')
s=s.replace('assert(m4->damage==33 && m4->reload_ms==2029 && m4->reload_empty_ms==2799);', 'assert(m4->damage==33 && m4->reload_ms==2029 && m4->reload_empty_ms==2799);')
p.write_text(s,encoding='utf-8')
