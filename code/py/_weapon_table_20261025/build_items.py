# -*- coding: utf-8 -*-
"""Build the unified CODOL 3.19 item table and export it as one .xlsx workbook."""
import csv, os, io, sys, collections
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

BASE = r'D:\BaiduNetdiskDownload\使命召唤OL\_weapon_table_20261025'
ST = os.path.join(BASE, 'st')
CSV_OUT = os.path.join(BASE, 'codol_items_3_19.csv')
XLSX_OUT = os.path.join(BASE, 'CODOL_3.19_道具表.xlsx')

zh = {r['key']: r['text_zh']
      for r in csv.DictReader(open(os.path.join(BASE, 'localize_zh.csv'), encoding='utf-8-sig'))}


def clean(s):
    """Strip control/illegal bytes and stray high-byte prefixes left by zone padding."""
    if s is None:
        return ''
    s = ''.join(ch for ch in s if ch == '\t' or 32 <= ord(ch) < 0x10000)
    return s.strip()


def read(name):
    p = os.path.join(ST, name)
    return list(csv.reader(open(p, encoding='utf-8'))) if os.path.exists(p) else []


def resolve(item_id, name_key):
    cands = []
    if name_key:
        cands += [name_key, name_key.upper()]
    up = item_id.upper()
    cands += ['MPUI_%s_NAME' % up, 'SF_UI_%s_NAME' % up, '%s_NAME' % up]
    for k in cands:
        v = zh.get(k)
        if v and v.strip():
            return v
    return ''


SPECS = [
    ('经验卡', 'mp_badgetable.csv', [('类型', 4), ('倍率', 5)]),
    ('名片背景', 'mp_callsignbackground.csv', [('图标路径', 4)]),
    ('徽章', 'mp_callsignicon.csv', [('图标路径', 4)]),
    ('称号', 'mp_callsigntitle.csv', [('图标路径', 4)]),
    ('边框', 'mp_callsignframe.csv', [('图标路径', 3)]),
    ('名牌', 'mp_callsignnameplate.csv', [('图标路径', 4), ('颜色', 5)]),
    ('表情', 'mp_item_emo.csv', [('图标路径', 3)]),
    ('代币', 'mp_item_tok.csv', [('参数', 1), ('参数', 2)]),
    ('补给', 'mp_item_sup.csv', [('参数', 1)]),
    ('装备', 'mp_item_etk.csv', [('参数', 1)]),
    ('战利品', 'mp_item_wld.csv', [('参数', 1)]),
    ('收藏品', 'mp_cocollectibles.csv', [('描述键', 1), ('图标', 2)]),
]

rows_out = []
for cat, fname, extras in SPECS:
    data = read(fname)
    if not data:
        print('MISSING', fname)
        continue
    for r in data:
        if not r or not r[0].strip():
            continue
        item_id = clean(r[0])
        name_key = clean(r[1]) if len(r) > 1 else ''
        zhname = clean(resolve(item_id, name_key))
        ex = [clean(r[idx]) if len(r) > idx else '' for _, idx in extras]
        rows_out.append([cat, item_id, zhname, name_key or item_id, fname]
                        + ex + [''] * (2 - len(ex)))

with open(CSV_OUT, 'w', encoding='utf-8-sig', newline='') as fh:
    w = csv.writer(fh)
    w.writerow(['类别', 'ID', '中文名', '名称键', '来源表', '属性1', '属性2'])
    w.writerows(rows_out)

total = len(rows_out)
named = sum(1 for r in rows_out if r[2])
print('rows %d, named %d (%.1f%%)' % (total, named, 100.0 * named / total))
for cat in dict.fromkeys(r[0] for r in rows_out):
    sub = [r for r in rows_out if r[0] == cat]
    print('  %-8s %4d rows, %4d named' % (cat, len(sub),
                                          sum(1 for r in sub if r[2])))

# ---------------- xlsx ----------------
FONT = 'Arial'
HDR_FILL = PatternFill('solid', fgColor='1F3864')
HDR_FONT = Font(name=FONT, bold=True, color='FFFFFF', size=10)
BODY = Font(name=FONT, size=10)
NONAME = Font(name=FONT, size=10, color='C00000')
THIN = Side(style='thin', color='D9D9D9')
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
CAT_FILL = PatternFill('solid', fgColor='DDEBF7')

wb = Workbook()
ws = wb.active
ws.title = '道具总表'

HEAD = [('类别', 10), ('ID', 34), ('中文名', 46), ('名称键', 40),
        ('来源表', 30), ('属性1', 30), ('属性2', 16)]
for c, (title, width) in enumerate(HEAD, start=1):
    cell = ws.cell(row=1, column=c, value=title)
    cell.font = HDR_FONT
    cell.fill = HDR_FILL
    cell.alignment = Alignment(horizontal='center', vertical='center')
    cell.border = BORDER
    ws.column_dimensions[get_column_letter(c)].width = width
ws.row_dimensions[1].height = 22

for r, rec in enumerate(rows_out, start=2):
    for c, v in enumerate(rec[:7], start=1):
        cell = ws.cell(row=r, column=c, value=v)
        cell.border = BORDER
        cell.font = NONAME if (c == 3 and not v) else BODY
        cell.alignment = Alignment(horizontal='left' if c in (2, 3, 4, 5, 6) else 'center',
                                   vertical='center')
    if r % 2 == 0:
        pass
ws.freeze_panes = 'C2'
ws.auto_filter.ref = 'A1:G%d' % (total + 1)

# 分类 sheet
ws2 = wb.create_sheet('分类统计')
ws2.column_dimensions['A'].width = 14
ws2.column_dimensions['B'].width = 10
ws2.column_dimensions['C'].width = 12
ws2.column_dimensions['D'].width = 12
for c, t in enumerate(['类别', '条目数', '有中文名', '覆盖率'], start=1):
    cell = ws2.cell(row=1, column=c, value=t)
    cell.font = HDR_FONT
    cell.fill = HDR_FILL
    cell.alignment = Alignment(horizontal='center')
    cell.border = BORDER
r = 2
for cat in dict.fromkeys(x[0] for x in rows_out):
    sub = [x for x in rows_out if x[0] == cat]
    n = len(sub)
    m = sum(1 for x in sub if x[2])
    for c, v in enumerate([cat, n, m, m / n if n else 0], start=1):
        cell = ws2.cell(row=r, column=c, value=v)
        cell.font = BODY
        cell.border = BORDER
        if c == 4:
            cell.number_format = '0.0%'
        if c > 1:
            cell.alignment = Alignment(horizontal='center')
    r += 1
for c, v in enumerate(['合计', total, named, named / total], start=1):
    cell = ws2.cell(row=r, column=c, value=v)
    cell.font = Font(name=FONT, size=10, bold=True)
    cell.fill = CAT_FILL
    cell.border = BORDER
    if c == 4:
        cell.number_format = '0.0%'
    if c > 1:
        cell.alignment = Alignment(horizontal='center')

# 说明 sheet
ws3 = wb.create_sheet('说明')
ws3.column_dimensions['A'].width = 4
ws3.column_dimensions['B'].width = 20
ws3.column_dimensions['C'].width = 92
ws3['B1'] = 'CODOL 3.19 道具表 — 说明'
ws3['B1'].font = Font(name=FONT, bold=True, size=14, color='1F3864')
notes = [
    ('数据来源', r'COD OL\main\*.ff 及各 ff_init_*.ifs 内的 zone，逐块 CTR + zlib 解包'),
    ('中文名', r'来自 localized_code_post_gfx_mp.ff 的 localize 资产（GBK 编码）'),
    ('', '共解出 11365 条 键→中文 对照，见 localize_zh.csv'),
    ('', ''),
    ('经验卡', 'mp_badgetable.csv，类型列为 xpboost 即经验加成卡'),
    ('', '倍率列为加成比例（0.05 = 5%，0.3 = 30%）'),
    ('', ''),
    ('名片背景', 'mp/callsignbackground.csv，ID 前缀 pcb_'),
    ('徽章', 'mp/callsignicon.csv，ID 前缀 pci_'),
    ('称号', 'mp/callsigntitle.csv，ID 前缀 pct_'),
    ('边框', 'mp/callsignframe.csv，ID 前缀 pcf_'),
    ('名牌', 'mp/callsignnameplate.csv，ID 前缀 pcn_，含文字颜色'),
    ('', ''),
    ('收藏品', 'mp_cocollectibles.csv，ID 本身即本地化键（ZOMBIE_STORY_*）'),
    ('', '其中文串不在已下载的 localized 包内，故中文名列为空'),
    ('', ''),
    ('红色中文名', '表示该条在本地化表里查不到对应键'),
]
r = 3
for label, text in notes:
    if label:
        c = ws3.cell(row=r, column=2, value=label)
        c.font = Font(name=FONT, bold=True, size=10, color='1F3864')
        c.alignment = Alignment(vertical='top')
    c = ws3.cell(row=r, column=3, value=text)
    c.font = Font(name=FONT, size=10)
    c.alignment = Alignment(vertical='top', wrap_text=True)
    r += 1

wb.save(XLSX_OUT)
print('\nwrote', CSV_OUT)
print('wrote', XLSX_OUT)
