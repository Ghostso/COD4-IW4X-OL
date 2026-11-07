# -*- coding: utf-8 -*-
"""Export the CODOL 3.19 weapon index table as one standalone .xlsx workbook."""
import csv
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

BASE = r'D:\BaiduNetdiskDownload\使命召唤OL\_weapon_table_20261025'
SRC = BASE + r'\codol_weapon_index_3_19.csv'
DST = BASE + r'\CODOL_3.19_武器索引表.xlsx'

FONT = 'Arial'
HDR_FILL = PatternFill('solid', fgColor='1F3864')
HDR_FONT = Font(name=FONT, bold=True, color='FFFFFF', size=10)
BODY_FONT = Font(name=FONT, size=10)
ANCHOR_FILL = PatternFill('solid', fgColor='FFF2CC')
IMPL_FONT = Font(name=FONT, size=10, italic=True, color='808080')
THIN = Side(style='thin', color='D9D9D9')
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)

COLS = [
    ('engine_index', '引擎索引', 10, '0'),
    ('name', '武器内部名', 30, None),
    ('base_name', '基型', 24, None),
    ('clip_size', '弹匣', 8, '0'),
    ('fire_time_ms', '射击间隔(ms)', 12, '0'),
    ('reload_ms', '换弹(ms)', 10, '0'),
    ('damage', '伤害', 8, '0'),
    ('player_damage', '玩家伤害', 10, '0'),
    ('min_damage', '最小伤害', 10, '0'),
    ('max_damage_range', '最大射程', 12, '#,##0.0'),
    ('min_damage_range', '最小射程', 12, '#,##0.0'),
    ('ui_slots', '配件槽', 8, '0'),
    ('verified', '校验', 14, None),
]

rows = list(csv.DictReader(open(SRC, encoding='utf-8-sig')))

wb = Workbook()
ws = wb.active
ws.title = '武器索引表'

# header
for c, (key, title, width, fmt) in enumerate(COLS, start=1):
    cell = ws.cell(row=1, column=c, value=title)
    cell.font = HDR_FONT
    cell.fill = HDR_FILL
    cell.alignment = Alignment(horizontal='center', vertical='center')
    cell.border = BORDER
    ws.column_dimensions[get_column_letter(c)].width = width
ws.row_dimensions[1].height = 22

# body
for r, rec in enumerate(rows, start=2):
    is_implicit = rec['verified'] == 'implicit'
    is_anchor = rec['verified'] == 'anchor-verified'
    for c, (key, title, width, fmt) in enumerate(COLS, start=1):
        raw = rec.get(key, '')
        val = raw
        if fmt and raw != '' and key != 'name':
            try:
                val = int(raw)
            except ValueError:
                try:
                    val = float(raw)
                except ValueError:
                    val = raw
        cell = ws.cell(row=r, column=c, value=val)
        cell.font = IMPL_FONT if is_implicit else BODY_FONT
        cell.border = BORDER
        if fmt:
            cell.number_format = fmt
        if key == 'name' or key == 'base_name':
            cell.alignment = Alignment(horizontal='left')
        else:
            cell.alignment = Alignment(horizontal='center')
        if is_anchor:
            cell.fill = ANCHOR_FILL

ws.freeze_panes = 'C2'
ws.auto_filter.ref = 'A1:%s%d' % (get_column_letter(len(COLS)), len(rows) + 1)

# ---- notes sheet ----
ns = wb.create_sheet('说明')
ns.column_dimensions['A'].width = 4
ns.column_dimensions['B'].width = 26
ns.column_dimensions['C'].width = 96

notes = [
    ('标题', 'CODOL 3.19 武器索引表'),
    ('公式', '引擎索引 = 武器名在 common_mp.zone 字母序名字池中的位置 + 2'),
    ('', ''),
    ('', '索引 0 = none，索引 1 = defaultweapon_mp（隐式定义，表中灰色斜体）'),
    ('', ''),
    ('锚点验证', 'm4a1tech_mp = 585、vector_mp = 1112、m9_mp = 646'),
    ('', '三者与实跑 gamestate 的 baseWeapon 字段逐一吻合，表中黄色底纹标注'),
    ('', ''),
    ('动态段', '动态武器索引 = configstring 索引 − 5960'),
    ('', '实测 7184 − 5960 = 1224，等于 firstDynamicWeapon'),
    ('', '模块化串格式：** <base> <value8> <value9> <附件...>'),
    ('', '其中 <base> 即本表的引擎索引（41 个 base 中 40 个可解析为真枪名）'),
    ('', ''),
    ('数据来源', r'COD OL\main\common_mp.ff（逐块 CTR + zlib 解包）'),
    ('弹匣/射速等', '来自同 zone 的 WeaponDef 资产实测值，非推算'),
    ('空白统计', '255 条无属性：下挂霰弹(_shotgun_attach)、投掷物、装备等'),
    ('', '这些武器在 zone 内没有 SF_WEAPON_*_MP_NAME 本地化键，故无对应 WeaponDef'),
    ('', ''),
    ('复算', r'python _weapon_table_20261025\build_final_index.py'),
    ('', '脚本内建三条锚点断言，公式不符会直接 assert 失败'),
]
ns['B1'] = 'CODOL 3.19 武器索引表 — 说明'
ns['B1'].font = Font(name=FONT, bold=True, size=14, color='1F3864')
ns.row_dimensions[1].height = 26

r = 3
for label, text in notes:
    if label == '标题':
        continue
    if label:
        c = ns.cell(row=r, column=2, value=label)
        c.font = Font(name=FONT, bold=True, size=10, color='1F3864')
        c.alignment = Alignment(vertical='top')
    c = ns.cell(row=r, column=3, value=text)
    c.font = Font(name=FONT, size=10)
    c.alignment = Alignment(vertical='top', wrap_text=True)
    r += 1

wb.save(DST)
print('wrote', DST)
print('data rows:', len(rows), 'cols:', len(COLS))
