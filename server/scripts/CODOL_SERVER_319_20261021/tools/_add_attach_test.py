from pathlib import Path
p=Path(r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_SERVER_319_20261021\tests\test_weapondefs.c')
s=p.read_text(encoding='utf-8')
s=s.replace('#include "codol_weapondefs.h"\n', '#include "codol_weapondefs.h"\n#include "codol_weaponattach.h"\n')
s=s.replace('    puts("test_weapondefs: all checks passed");\n', '''    {
        codol_weapondef_t d=*m4;
        const codol_weaponattach_t *hc=codol_weaponattach_find("highcal_base");
        const codol_weaponattach_t *fmj=codol_weaponattach_find("fmj_base");
        assert(hc && fmj);
        assert(codol_weaponattach_apply(&d,hc));
        assert(d.location_damage_multipliers[CODOL_HITLOC_TORSO_UPPER]==1.5f);
        d=*m4;
        assert(codol_weaponattach_apply(&d,fmj));
        assert(d.location_damage_multipliers[CODOL_HITLOC_HEAD]==1.2f);
    }
    puts("test_weapondefs: all checks passed");
''')
p.write_text(s,encoding='utf-8')
print('patched test')
