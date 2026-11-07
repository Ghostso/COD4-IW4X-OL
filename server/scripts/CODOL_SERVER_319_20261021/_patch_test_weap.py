from pathlib import Path
p=Path(r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_SERVER_319_20261021\tests\test_weapondefs.c')
s=p.read_text(encoding='utf-8')
s=s.replace('    const codol_weapondef_t *r870 = codol_weapondef_find("r870_mp");\n', '    const codol_weapondef_t *mp5 = codol_weapondef_find("mp5k_mp");\n')
s=s.replace('    assert(m4 && ak && r870);\n', '    assert(m4 && ak && mp5);\n')
s=s.replace('    assert(r870->clip_size == 8 && r870->fire_time_ms == 192);\n', '    assert(mp5->clip_size == 30 && mp5->fire_time_ms == 74 && mp5->damage == 40);\n')
p.write_text(s,encoding='utf-8')
print('patched')
