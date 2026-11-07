# -*- coding: utf-8 -*-
"""sweep_backlog.py -- 把散文项里"已被 tasks.json 关闭的任务号"命中的，批量标为已处理。"""
import os, io, json, re

HERE = os.path.dirname(os.path.abspath(__file__))
tj = json.load(io.open(os.path.join(HERE, 'tasks.json'), encoding='utf-8'))
closed = {t['id'] for t in tj['tasks'] if t.get('status') == 'closed'}
opn = {t['id'] for t in tj['tasks'] if t.get('status') == 'open'}

bl = json.load(io.open(os.path.join(HERE, 'backlog.json'), encoding='utf-8'))
ST = os.path.join(HERE, 'backlog_status.json')
st = json.load(io.open(ST, encoding='utf-8')) if os.path.exists(ST) else {}

n = 0
for it in bl['items']:
    txt = it['text']
    ids = set(re.findall(r'\b([A-Z]\d{1,2})\b', txt))
    hit = ids & closed
    if hit and not (ids & opn):
        st[it['key']] = {'status': 'closed',
                         'note': '已被 %s 覆盖(tasks.json 已闭)' % ','.join(sorted(hit))}
        n += 1
json.dump(st, io.open(ST, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
print('批量标记 %d 条为已处理；剩余未处理 %d 条'
      % (n, len(bl['items']) - sum(1 for v in st.values() if v.get('status') == 'closed')))
