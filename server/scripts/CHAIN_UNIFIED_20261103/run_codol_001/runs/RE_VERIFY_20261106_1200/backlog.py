# -*- coding: utf-8 -*-
"""backlog.py -- 把 memory 散的"未闭/缺口/待办/尚未/未定"变成可推进的账本。

  python -I backlog.py                 # 重扫 + 打印统计 + 本次新增/消失
  python -I backlog.py list [--open]   # 列出条目（带 key）
  python -I backlog.py close <key> [备注]  # 标记已处理（写入 backlog_status.json）
  python -I backlog.py reopen <key>

key = sha1(文件名|原文)[:12]，**与行号无关** ⇒ 文件里加几行不会让状态错位。
"""
import os, io, sys, json, hashlib

M = r'C:\Users\Z7-CT5N1\.claude\projects\D--BaiduNetdiskDownload-----OL\memory'
HERE = os.path.dirname(os.path.abspath(__file__))
BL = os.path.join(HERE, 'backlog.json')
ST = os.path.join(HERE, 'backlog_status.json')
KW = ['未闭合', '未闭', '缺口', '待办', '尚未', '未定', '仍需',
      # ★ 2026-11-06 补：表格里的状态标记不含上面的词，曾导致
      #   room-open-items-ledger-165 的 10 项老账只被扫到 1 项。
      '❌', '⚠️ 部分', '⚠ 部分']


def scan():
    out = []
    for fn in sorted(os.listdir(M)):
        if not fn.endswith('.md') or fn == 'MEMORY.md':
            continue
        p = os.path.join(M, fn)
        lines = io.open(p, encoding='utf-8').read().split('\n')
        for i, l in enumerate(lines):
            s = l.strip()
            if not s or not any(k in s for k in KW):
                continue
            key = hashlib.sha1((fn + '|' + s).encode('utf-8')).hexdigest()[:12]
            out.append({'key': key, 'file': fn, 'line': i + 1, 'text': s})
    # 同一段文字可能重复出现 ⇒ 按 key 去重，保留最小行号
    seen = {}
    for r in out:
        k = r['key']
        if k not in seen or r['line'] < seen[k]['line']:
            seen[k] = r
    return sorted(seen.values(), key=lambda r: (r['file'], r['line']))


def load(p, d):
    if os.path.exists(p):
        try:
            return json.load(io.open(p, encoding='utf-8'))
        except Exception:
            pass
    return d


def save(p, o):
    json.dump(o, io.open(p, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)


def say(s=''):
    sys.stdout.write(str(s).encode('ascii', 'backslashreplace').decode('ascii') + '\n')


def main():
    items = scan()
    status = load(ST, {})
    old = load(BL, {'items': []})
    oldkeys = set(i['key'] for i in old.get('items', []))
    newkeys = set(i['key'] for i in items)
    added = sorted(newkeys - oldkeys)
    gone = sorted(oldkeys - newkeys)

    save(BL, {'items': items})
    save(ST, status)

    op = [i for i in items if status.get(i['key'], {}).get('status', 'open') == 'open']
    cl = [i for i in items if status.get(i['key'], {}).get('status') == 'closed']

    cmd = sys.argv[1] if len(sys.argv) > 1 else 'stats'
    if cmd == 'list':
        onlyopen = '--open' in sys.argv
        for i in (op if onlyopen else items):
            st = status.get(i['key'], {}).get('status', 'open')
            note = status.get(i['key'], {}).get('note', '')
            say('%s [%s] %s:%d  %s%s' % (i['key'], st, i['file'], i['line'],
                                           i['text'][:110], ('  //' + note) if note else ''))
        return 0
    if cmd in ('close', 'reopen'):
        if len(sys.argv) < 3:
            say('usage: backlog.py close <key> [note]'); return 2
        k = sys.argv[2]
        note = ' '.join(sys.argv[3:])
        status[k] = {'status': 'closed' if cmd == 'close' else 'open', 'note': note}
        save(ST, status)
        say('%s -> %s %s' % (k, status[k]['status'], note))
        return 0

    say('memory 散文项合计 = %d （已处理 %d / 待处理 %d）' % (len(items), len(cl), len(op)))
    if added:
        say('本次新增 %d 条:' % len(added))
        byk = {i['key']: i for i in items}
        for k in added[:10]:
            say('  + %s %s:%d %s' % (k, byk[k]['file'], byk[k]['line'], byk[k]['text'][:90]))
    if gone:
        say('⚠ 本次消失 %d 条（原文被改写/删除 —— 确认不是把旧项丢了）:' % len(gone))
        for k in gone[:10]:
            say('  - %s' % k)
    return 0


if __name__ == '__main__':
    sys.exit(main())
