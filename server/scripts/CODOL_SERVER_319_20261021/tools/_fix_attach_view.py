from pathlib import Path
p=Path(r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_SERVER_319_20261021\src\battle\weaponattach.c')
s=p.read_text(encoding='utf-8')
s=s.replace('''const codol_weaponattach_t *codol_weaponattach_find(const char *name)
{
    int i;
    if (!name) return NULL;
    for (i=0;i<codol_weaponattach_scalar_count;i++)
        if (!strcmp(table[i].name,name)) return (const codol_weaponattach_t *)&table[i];
    return NULL;
}
''','''const codol_weaponattach_t *codol_weaponattach_find(const char *name)
{
    static codol_weaponattach_t view;
    int i;
    if (!name) return NULL;
    for (i=0;i<codol_weaponattach_scalar_count;i++) {
        if (!strcmp(table[i].name,name)) {
            view.name=table[i].name;
            view.count=table[i].count;
            view.entries=table[i].entries;
            return &view;
        }
    }
    return NULL;
}
''')
p.write_text(s,encoding='utf-8')
print('patched view')
