from pathlib import Path
p=Path(r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_SERVER_319_20261021\tests\test_weapondefs.c')
s=p.read_text(encoding='utf-8')
s=s.replace('    assert(m4->ads_view_kick_pitch_min==2.0f);\n    assert(m4->ads_view_kick_pitch_max==15.0f);\n    assert(m4->ads_spread==8.0f);\n    assert(m4->hip_view_kick_pitch_min==25.0f);\n    assert(m4->hip_view_kick_pitch_max==1575.0f);\n', '''    assert(m4->hip_spread_stand_min==2.0f);
    assert(m4->hip_spread_stand_max==15.0f);
    assert(m4->hip_spread_ducked_min==1.0f);
    assert(m4->hip_spread_ducked_max==5.0f);
    assert(m4->ads_spread==8.0f);
''')
p.write_text(s,encoding='utf-8')
print('ok')
