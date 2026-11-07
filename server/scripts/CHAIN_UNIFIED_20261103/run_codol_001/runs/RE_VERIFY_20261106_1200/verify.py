# -*- coding: utf-8 -*-
"""
verify.py -- 以原版二进制为对照的自动化回归校验器
=============================================================================
用途：把"从 3.19 客户端逆向出来的每一条结论"变成**可机械复核的断言**，
      原版 `codoMP_unpacked_146.exe` 是唯一对照物（权威等级 1）。

  python -I verify.py baseline     # 首次：采集观测值 → _baseline.json
  python -I verify.py check        # 之后每次：重算并与 baseline + 绝对断言比对
  python -I verify.py graph        # 只打印依赖图与未闭项

退出码：0 = 全通过；1 = 有断言失败/变更；2 = 依赖图不合法。
设计要点：
  · 绝对断言（abs）—— 直接写死期望值，与 baseline 无关。
  · 观测断言（obs）—— 只与 _baseline.json 比，任何变化都算"回归"。
  · 依赖图 —— 已闭任务不得依赖未闭任务；不得成环。
"""
import sys, os, json, struct, hashlib, io
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

MD = Cs(CS_ARCH_X86, CS_MODE_32)

def norm_text(s):
    return ' '.join(s.lower().replace('\t', ' ').split())

def hexnorm(s):
    return (s or '').replace(' ', '').replace('\n', '').lower()

def insns(va, count):
    buf = P.rd(va, 16 * count)
    out = []
    for ins in MD.disasm(buf, va):
        out.append(norm_text(ins.mnemonic + ' ' + ins.op_str))
        if len(out) >= count:
            break
    return out

HERE = os.path.dirname(os.path.abspath(__file__))
BIN = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\UNPACKED_146\codoMP_unpacked_146.exe'
TASKS = os.path.join(HERE, 'tasks.json')
BASE = os.path.join(HERE, '_baseline.json')

# ----------------------------------------------------------------- PE
class PE(object):
    def __init__(self, path):
        with io.open(path, 'rb') as f:
            self.d = f.read()
        d = self.d
        e = struct.unpack_from('<I', d, 0x3C)[0]
        self.ib = struct.unpack_from('<I', d, e + 0x34)[0]
        nsec = struct.unpack_from('<H', d, e + 6)[0]
        opt = struct.unpack_from('<H', d, e + 20)[0]
        s0 = e + 24 + opt
        self.secs = []          # (va, vsz, raw, rsz, chars)
        for k in range(nsec):
            o = s0 + 40 * k
            vs, va, rs, ra = struct.unpack_from('<IIII', d, o + 8)
            ch = struct.unpack_from('<I', d, o + 36)[0]
            self.secs.append((self.ib + va, vs, ra, rs, ch))
        self.sha = hashlib.sha256(d).hexdigest()
    def rd(self, va, n):
        """va 为绝对 VA；self.secs 里存的是绝对 VA，故不再减 ib。"""
        for v, vs, ra, rs, ch in self.secs:
            if v <= va < v + max(vs, rs):
                off = ra + (va - v)
                return self.d[off: off + n]
        return None
    def u32(self, va):
        b = self.rd(va, 4)
        return None if b is None else struct.unpack('<I', b)[0]
    def cstr(self, va, maxn=96):
        b = self.rd(va, maxn)
        if b is None: return None
        z = b.find(b'\x00')
        return (b[:z] if z >= 0 else b).decode('latin1')
    def exec_sections(self):
        return [(s[0], s[0] + s[1], s[2], s[3]) for s in self.secs if s[4] & 0x20000000]
    def small_sections(self, lim=0x2000000):
        return [(s[0], s[0] + s[1], s[2], s[3]) for s in self.secs if s[1] <= lim]

P = PE(BIN)
_cache_calls = {}
_cache_xrefs = {}

def calls(target):
    """全部 E8 rel32 -> target 的调用点（升序）。"""
    if target in _cache_calls: return _cache_calls[target]
    out = []
    for va, ve, ra, rs in P.exec_sections():
        buf = P.d[ra:ra + min(ve - va, rs)]
        for i in range(len(buf) - 4):
            if buf[i] == 0xE8:
                rel = struct.unpack_from('<i', buf, i + 1)[0]
                if (va + i + 5 + rel) & 0xFFFFFFFF == target:
                    out.append(va + i)
    _cache_calls[target] = sorted(out)
    return _cache_calls[target]

def xrefs(addr, step=1):
    """可执行段内逐字节出现该 4 字节小端值的位置（升序）。"""
    key = (addr, step)
    if key in _cache_xrefs: return _cache_xrefs[key]
    need = struct.pack('<I', addr)
    out = []
    for va, ve, ra, rs in P.exec_sections():
        buf = P.d[ra:ra + min(ve - va, rs)]
        p = 0
        while True:
            i = buf.find(need, p)
            if i < 0: break
            if i % step == 0 or step == 1:
                out.append(va + i)
            p = i + 1
    _cache_xrefs[key] = sorted(out)
    return _cache_xrefs[key]

def vtslots(fn):
    """该函数指针在（小）数据段里出现的所有位置。"""
    need = struct.pack('<I', fn)
    out = []
    for va, ve, ra, rs in P.small_sections():
        buf = P.d[ra:ra + min(ve - va, rs)]
        p = 0
        while True:
            i = buf.find(need, p)
            if i < 0: break
            if i % 4 == 0:
                out.append(va + i)
            p = i + 1
    return sorted(out)

def hexval(s):
    return int(s, 16) if isinstance(s, str) else s

# ----------------------------------------------------------------- checks
def run_check(c):
    k = c['kind']
    if k == 'insn':                        # 语义：va 处单条指令 == 期望文本
        got = insns(hexval(c['va']), 1)
        return (got[0] if got else '<undecodable>'), norm_text(c['eq'])
    if k == 'seq':                         # 语义：va 起连续指令序列
        return insns(hexval(c['va']), len(c['eq'])), [norm_text(x) for x in c['eq']]
    if k == 'bytes':
        got = P.rd(hexval(c['va']), len(c['eq_hex'].replace(' ', '')) // 2)
        return hexnorm((got or b'').hex()), hexnorm(c['eq_hex'])
    if k == 'str':
        return P.cstr(hexval(c['va'])), c['eq']
    if k == 'u32':
        return P.u32(hexval(c['va'])), hexval(c['eq']) if 'eq' in c else None
    if k == 'ptru32':                      # [va] 是指针；取其指向处的 dword
        p = P.u32(hexval(c['va'])) or 0
        return P.u32(p), (hexval(c['eq']) if 'eq' in c else None)
    if k == 'code':                        # va 处的原始字节（空格不敏感）
        got = P.rd(hexval(c['va']), len(c['eq_hex'].replace(' ', '')) // 2)
        return hexnorm((got or b'').hex()), hexnorm(c['eq_hex'])
    if k == 'calls':
        return calls(hexval(c['target'])), ([hexval(x) for x in c['eq']] if 'eq' in c else None)
    if k == 'xrefs':
        st = c.get('step', 1)
        return xrefs(hexval(c['addr']), st), ([hexval(x) for x in c['eq']] if 'eq' in c else None)
    if k == 'noxref':
        return calls(hexval(c['addr'])), []      # 无 E8 调用点
    if k == 'vtslot':                            # 函数指针落在哪些（小）数据段
        return vtslots(hexval(c['fn'])), ([hexval(x) for x in c['eq']] if 'eq' in c else None)
    if k == 'callcount':                         # 只需数量（结构回归）
        return len(calls(hexval(c['target']))), (c['eq'] if 'eq' in c else None)
    raise ValueError('unknown kind ' + k)

def norm(v):
    if isinstance(v, list) and v and isinstance(v[0], int):
        return ['0x%08X' % x for x in v]
    if isinstance(v, int):
        return '0x%08X' % v
    return v

_LOG = []
def say(s=''):
    _LOG.append(s)
    sys.stdout.write(s.encode('ascii', 'backslashreplace').decode('ascii') + '\n')

def flush_log(name='report.txt'):
    with io.open(os.path.join(HERE, 'out', name), 'w', encoding='utf-8') as f:
        f.write('\n'.join(_LOG) + '\n')

def report_open(tasks, order):
    """每次运行都打印未闭清单——防止'做了一个忘了一个'。"""
    op = [t for t in order if tasks[t].get('status') == 'open']
    say('')
    say('==== 未闭清单 (%d 条) ====' % len(op))
    for t in op:
        say('  %-4s %s' % (t, tasks[t]['title']))
        if tasks[t].get('blocked_on'):
            say('       缺口: %s' % tasks[t]['blocked_on'])
    return [t for t in op]

# ----------------------------------------------------------------- main
def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else 'check'
    tj = json.load(io.open(TASKS, encoding='utf-8'))
    tasks = {t['id']: t for t in tj['tasks']}
    order = [t['id'] for t in tj['tasks']]

    # ---- 依赖图合法性
    bad = []
    # ★ 重复 id 检查：tasks 是 dict，重复 id 会静默覆盖，等于把旧项弄丢。
    _ids = [t['id'] for t in tj['tasks']]
    for _d in sorted(set(_ids)):
        if _ids.count(_d) > 1:
            bad.append('重复 id: %s 出现 %d 次（后者会静默覆盖前者 ⇒ 旧项被丢弃）'
                       % (_d, _ids.count(_d)))
    for tid, t in tasks.items():
        for dep in t.get('depends_on', []):
            if dep not in tasks:
                bad.append('%s depends on unknown %s' % (tid, dep))
            elif t.get('status') == 'closed' and tasks[dep].get('status') != 'closed':
                bad.append('%s 已闭却依赖未闭的 %s' % (tid, dep))
    # 环检测
    colour = {}
    def dfs(u, stack):
        colour[u] = 1
        for v in tasks[u].get('depends_on', []):
            if v not in tasks: continue
            if colour.get(v) == 1:
                bad.append('依赖环: %s -> %s' % (u, v)); return
            if colour.get(v) is None:
                dfs(v, stack + [v])
        colour[u] = 2
    for u in order:
        if colour.get(u) is None:
            dfs(u, [])

    if mode == 'graph':
        for u in order:
            t = tasks[u]
            say('[%s] %-4s %s' % (t.get('status', '?'), u, t['title']))
            if t.get('depends_on'):
                say('        dép: %s' % ', '.join(t['depends_on']))
            for a in t.get('assert', []):
                say('        · %s' % json.dumps(a, ensure_ascii=False))
        if bad:
            say('\n依赖图问题:')
            for b in bad: say('  ! ' + b)
            flush_log('graph.txt'); return 2
        flush_log('graph.txt'); return 0

    # ---- 采集
    obs = {}
    results = []
    for tid in order:
        t = tasks[tid]
        tpass = True
        details = []
        for i, a in enumerate(t.get('assert', [])):
            try:
                got, exp = run_check(a)
            except Exception as ex:
                tpass = False
                details.append('  ERR  %s: %s' % (a['kind'], ex))
                continue
            g = norm(got); e = None if exp is None else norm(exp)
            key = '%s#%d' % (tid, i)
            obs[key] = {'task': tid, 'kind': a['kind'], 'where': a.get('va') or a.get('target') or a.get('addr') or a.get('fn'), 'value': g}
            if e is not None:
                if a.get('subset'):
                    gset = g if isinstance(g, list) else [g]
                    miss = [x for x in e if x not in gset]
                    if miss:
                        tpass = False
                        details.append('  FAIL %s @%s  缺少 %s（实际 %d 项）'
                                       % (a['kind'], a.get('target') or a.get('addr') or a.get('va'),
                                          ' '.join(miss), len(gset)))
                elif g != e:
                    tpass = False
                    details.append('  FAIL %s @%s\n        got %s\n        exp %s' % (a['kind'], a.get('va') or a.get('target') or a.get('addr') or a.get('fn'), g, e))
            details.append('  ok   %s @%s = %s' % (a['kind'], a.get('va') or a.get('target') or a.get('addr') or a.get('fn'), g))
        results.append((tid, t.get('status'), tpass, details))

    if mode == 'baseline':
        op = report_open(tasks, order)
        json.dump({'bin_sha256': P.sha, 'obs': obs, 'open_ids': op},
                  io.open(BASE, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
        say('baseline 已写出: %s  (bin sha256=%s…)' % (BASE, P.sha[:16]))
        for tid, st, ok, det in results:
            say('[%s] %s %s' % ('ok' if ok else 'FAIL', tid, tasks[tid]['title']))
            for d in det: say(d)
        flush_log('baseline.txt')
        return 0 if all(r[2] for r in results if tasks[r[0]].get('status') != 'open') and not bad else 1

    # ---- check
    prev = None
    if os.path.exists(BASE):
        prev = json.load(io.open(BASE, encoding='utf-8'))
    changed = []
    if prev:
        if prev.get('bin_sha256') != P.sha:
            changed.append('!! 二进制已变: %s -> %s' % (prev.get('bin_sha256', '?')[:16], P.sha[:16]))
        for k, v in obs.items():
            pv = prev.get('obs', {}).get(k)
            if pv is None:
                changed.append('新增观测 %s' % k)
            elif pv['value'] != v['value']:
                changed.append('REGRESS %s (%s): %s -> %s' % (k, v['where'], pv['value'], v['value']))
    else:
        changed.append('（无 baseline，先跑 baseline）')

    nfail = 0
    for tid, st, ok, det in results:
        if not ok:
            if tasks[tid].get('status') == 'open':
                say('[open] %s  %s   （未闭，断言不计失败）' % (tid, tasks[tid]['title']))
            else:
                nfail += 1
                say('[FAIL] %s  %s' % (tid, tasks[tid]['title']))
                for d in det:
                    if 'FAIL' in d or 'ERR' in d: say(d)
    say('---- 汇总 ----')
    say('任务 %d 条：断言全过 %d，失败 %d' % (len(results), len(results) - nfail, nfail))
    if prev:
        say('baseline 比对：%d 处差异' % len(changed))
        if changed:
            for c in changed: say('  ' + c)
    if bad:
        say('依赖图问题：')
        for b in bad: say('  ! ' + b)
    ok = (nfail == 0) and (not bad) and (prev is not None) and (not changed)
    say('=> ' + ('全部通过' if ok else '未通过'))
    op = report_open(tasks, order)
    if prev is not None and 'open_ids' in prev:
        gained = [x for x in op if x not in prev['open_ids']]
        closed = [x for x in prev['open_ids'] if x not in op]
        if closed:
            say('  本次闭掉: %s' % ', '.join(closed))
        if gained:
            say('  ⚠ 本次新增未闭: %s  （必须确认不是把旧项丢了）' % ', '.join(gained))
    flush_log(mode + '.txt')
    return 0 if ok else (2 if bad else 1)

if __name__ == '__main__':
    sys.exit(main())
