from pathlib import Path
p=Path(r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_SERVER_319_20261021\include\codol_weaponattach.h')
s=p.read_text(encoding='utf-8').replace('bool codol_weaponattach_apply(codol_weapondef_t *def, const codol_weaponattach_t *attach);','''typedef struct { int applied; int skipped; } codol_weaponattach_result_t;
bool codol_weaponattach_apply_ex(codol_weapondef_t *def, const codol_weaponattach_t *attach,
                                codol_weaponattach_result_t *result);
bool codol_weaponattach_apply(codol_weapondef_t *def, const codol_weaponattach_t *attach);''')
p.write_text(s,encoding='utf-8')
p=Path(r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_SERVER_319_20261021\src\battle\weaponattach.c')
s=p.read_text(encoding='utf-8')
s=s.replace('bool codol_weaponattach_apply(codol_weapondef_t *def, const codol_weaponattach_t *a)\n{\n    int i;\n    if (!def || !a) return false;','bool codol_weaponattach_apply_ex(codol_weapondef_t *def, const codol_weaponattach_t *a,\n                                codol_weaponattach_result_t *result)\n{\n    int i;\n    if (!def || !a) return false;\n    if (result) { result->applied=0; result->skipped=0; }')
s=s.replace('        switch (e->field_offset) {','        { int known=1; switch (e->field_offset) {')
s=s.replace('        default: return false;\n        }\n    }\n    return true;\n}','        default: known=0; break;\n        }\n        if (known) { if (result) result->applied++; }\n        else if (result) result->skipped++; }\n    }\n    return true;\n}\nbool codol_weaponattach_apply(codol_weapondef_t *def, const codol_weaponattach_t *a)\n{\n    codol_weaponattach_result_t r;\n    return codol_weaponattach_apply_ex(def,a,&r);\n}')
p.write_text(s,encoding='utf-8')
print('patched skip-known')
