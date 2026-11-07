"""把 rt_etw.py / rt_hook.py 的 JSONL 汇总成《运行时定位》要求的 16 节报告。

两份采集器写出的记录字段并不完全一致：

    rt_etw.py   无 tid、无载荷、无调用栈；handle 是内核 AFD Endpoint 指针
                （**不是**用户态 SOCKET 值），形如 `0xFFFF...D920#3`，
                `#n` 是"同一个 Endpoint 指针被复用"的代次号。
    rt_hook.py  有 tid、有载荷前 N 字节、有调用栈；handle 是真正的 SOCKET 值。

本脚本对两者都能读。缺什么就在对应小节标 UNKNOWN，**不猜**。

用法：
    python scripts/rt_summary.py logs/game3.jsonl
    python scripts/rt_summary.py logs/rt.jsonl --names 122.96.96.225=tqos.gamesafe.qq.com
    python scripts/rt_summary.py logs/rt.jsonl --out docs/rt-report.md

设计上的一条硬规矩（来自用户第九阶段的要求）：
    **本脚本永不自动输出 `GAME_CONFIRMED`。**
    ETW 没有调用栈，端口和地址本身不构成"足够证据"。要标 GAME_CONFIRMED
    必须由人看完调用栈后显式传 `--assert-game <handle>`。
"""
import argparse
import collections
import ctypes
import json
import os
import sys

# ---------------------------------------------------------------- 判定档位

HIGH, MEDIUM, LOW, UNKNOWN = 'HIGH', 'MEDIUM', 'LOW', 'UNKNOWN'

LOOPBACK = ('127.', '::1', '0.0.0.0', '::')


def is_loop(ip):
    return not ip or ip.startswith(LOOPBACK)


def proto_okind(v):
    """把 socket 类型/协议统一成 'TCP' / 'UDP' / None。

    两份采集器写法不同：rt_hook.js 给整数（1/2/6/17），
    rt_etw.py 给 IPPROTO_ 之类名字，还可能给 'SOCK_STREAM'。
    不统一的话统计会静默归零 —— 这正是第一次跑出来的 bug。
    """
    if v is None:
        return None
    if isinstance(v, int):
        return {1: 'TCP', 6: 'TCP', 2: 'UDP', 17: 'UDP'}.get(v)
    s = str(v).upper()
    if 'UDP' in s or 'DGRAM' in s:
        return 'UDP'
    if 'TCP' in s or 'STREAM' in s:
        return 'TCP'
    return None


# ---------------------------------------------------------------- 读记录

def load(path):
    recs = []
    with open(path, encoding='utf-8') as fh:
        for i, line in enumerate(fh):
            line = line.strip()
            if not line:
                continue
            try:
                recs.append(json.loads(line))
            except ValueError:
                # 采集被打断时最后一行可能是半条，跳过即可
                print('[!] 第 %d 行不是完整 JSON，已跳过' % (i + 1))
    head = recs[0] if recs and 'note' in recs[0] else {}
    evs = [r for r in recs if 'note' not in r]
    return head, evs


def api_of(r):
    return r.get('api') or ('id=%s' % r.get('id'))


def bare(h):
    """去掉代次号：`0xFFFF...D920#3` → `0xFFFF...D920`。

    `accept_handle` 记的是**裸指针**，而 socket 记录带代次号，两边对不上。
    """
    return h.split('#')[0] if isinstance(h, str) else h


def nbytes(r):
    """这条记录携带的字节数（发/收都适用）。"""
    for k in ('len', 'want', 'bytes'):
        if r.get(k) is not None:
            return r[k]
    return None


# ---------------------------------------------------------------- 每个 handle 的画像

class Sock(object):
    def __init__(self, h):
        self.h = h
        self.first = None
        self.last = None
        self.fam = self.typ = self.proto = None
        self.binds = []
        self.remote = None          # (ip, port) —— 来自 connect
        self.listens = 0
        self.accepts = 0
        self.accepted = False   # 本 handle 是某次 accept 的**结果**（不是主动连出去的）
        self.n_send = 0
        self.n_recv = 0
        self.b_send = 0
        self.b_recv = 0
        self.udp_far = collections.Counter()   # sendto 目标
        self.udp_back = 0                      # recvfrom 次数
        self.errcnt = 0
        self.closed = 0
        self.tids = set()

    def span(self):
        if self.first is None:
            return None
        return self.last - self.first


def profile(evs):
    socks = {}
    created = {}    # 裸 ep 指针 → [(创建时刻, 代次 handle)]
    pending = []    # [(accept 时刻, accept_handle)]

    def S(h):
        if h not in socks:
            socks[h] = Sock(h)
        return socks[h]

    for r in evs:
        h = r.get('handle')
        if h is None:
            continue
        s = S(h)
        t = r.get('t')
        if t is not None:
            if s.first is None:
                s.first = t
            s.last = t
        if r.get('tid') is not None:
            s.tids.add(r['tid'])
        if r.get('err'):
            s.errcnt += 1
        a = api_of(r)
        if a == 'socket':
            s.fam = r.get('family', s.fam)
            s.typ = r.get('type', s.typ)
            s.proto = r.get('proto', s.proto)
            if t is not None:
                created.setdefault(bare(h), []).append((t, h))
        elif a == 'bind':
            ad = r.get('addr') or {}
            s.binds.append((ad.get('ip'), ad.get('port')))
        elif a == 'connect':
            ad = r.get('addr') or {}
            if r.get('ret') == 0:
                s.remote = (ad.get('ip'), ad.get('port'))
            else:
                s.remote = None
        elif a == 'listen':
            s.listens += 1
        elif a == 'accept':
            s.accepts += 1
            ah = r.get('accept_handle')
            if ah and t is not None:
                pending.append((t, ah))
        elif a == 'send':
            s.n_send += 1
            s.b_send += nbytes(r) or 0
        elif a == 'recv':
            s.n_recv += 1
            s.b_recv += nbytes(r) or 0
        elif a == 'sendto':
            s.n_send += 1
            s.b_send += nbytes(r) or 0
            ad = r.get('addr') or {}
            s.udp_far[(ad.get('ip'), ad.get('port'))] += 1
        elif a == 'recvfrom':
            s.n_recv += 1
            s.b_recv += nbytes(r) or 0
            s.udp_back += 1
        elif a == 'closesocket':
            s.closed += 1

    # accept_handle 是裸指针，而 socket 记录带代次号 —— 靠**时间**把它们对上：
    # 被 accept 出来的 socket，其 1000 事件必然紧跟在 accept 之后。
    # 同一个 Endpoint 指针会被复用，所以不能只看指针相等，否则会把
    # 后来复用该指针的 TLS 连接也误判成 IPC。
    for at, ah in pending:
        gens = created.get(bare(ah), [])
        if not gens:
            continue
        # 取**时间上最近**的一次创建，不假设先后：AFD 先建 Endpoint、accept 记录
        # 才落地，所以创建时刻往往比 accept 早几微秒 —— 用"只挑之后"会把正确的
        # 那一代跳过去，误选到几百毫秒后复用同一指针的下一代。
        pick = min(gens, key=lambda g: abs(g[0] - at))
        if abs(pick[0] - at) <= 0.05 and pick[1] in socks:
            socks[pick[1]].accepted = True
    return socks


def classify(s, assert_game=()):
    """给出用途标签。**只按行为判，不按端口号猜。**

    端口 80/443 只是佐证，真正定性的依据写在 note 里。
    """
    if s.h in assert_game:
        return 'GAME_CONFIRMED', '调用者显式确认（--assert-game）'
    lo = s.remote and is_loop(s.remote[0])
    bind_lo = bool(s.binds) and all(is_loop(b[0]) for b in s.binds)
    if s.listens or s.accepts or s.accepted or (lo and s.remote) or bind_lo:
        return 'CEF', '回环 listen/accept 或回环 connect/bind；与本机 IPC 一致'
    if not s.remote:
        if s.n_recv == 0 and s.n_send > 0 and s.udp_far:
            return 'TELEMETRY', '单向 sendto，**全程零 recvfrom 回应**'
        return 'UNKNOWN', '没有 connect，也没有 sendto 目标'
    port = s.remote[1]
    if port == 80:
        return 'HTTP', '端口 80；明文请求-响应'
    if port == 443:
        return 'HTTPS', '端口 443；5 字节记录头 + 大记录（TLS 分帧）'
    if port in (8080, 8081, 8000):
        return 'UNKNOWN', '非标准高端口，需调用栈才能定性'
    return 'UNKNOWN', '非 80/443，缺调用栈证据'


# ---------------------------------------------------------------- 调用栈
# ETW 通道拿不到栈；只有 rt_hook.js 的 backtrace 字段里有。
# 这里统一成"有就展开、没有就 UNKNOWN"，不拿 module 名硬凑。

def stacks_of(evs, apis):
    out = []
    for r in evs:
        if api_of(r) not in apis:
            continue
        bt = r.get('backtrace') or r.get('stack')
        if not bt:
            continue
        out.append((r, bt))
    return out


def render_bt(bt):
    if isinstance(bt, str):
        return [x.strip() for x in bt.split('\n') if x.strip()]
    lines = []
    for f in bt:
        if isinstance(f, dict):
            lines.append('%s!%s +0x%x' % (f.get('module', '?'),
                                          f.get('symbol', '?'),
                                          f.get('offset', 0) or 0))
        else:
            lines.append(str(f))
    return lines


# ---------------------------------------------------------------- 524 / 615

MARKERS = (524, 615)


def marker_stream(evs):
    """找长度正好等于 524 / 615 的发包/收包，并给出它前后的同连接数据流。

    这是《运行时定位》第七节要的东西：`Socket → 第一组发送 → 524 → 615 → 后续`。
    长度只是**线索**，不足以定性；有载荷时（rt_hook）附带前 32 字节。
    """
    res = {}
    for m in MARKERS:
        hits = [r for r in evs
                if api_of(r) in ('send', 'recv', 'WSASend', 'WSARecv',
                                 'sendto', 'recvfrom')
                and nbytes(r) == m]
        res[m] = hits
    return res


def context(evs, handle, t, window=0.25):
    """取某 handle 上 t 前后 window 秒内的全部记录，按时间排。"""
    rows = [r for r in evs if r.get('handle') == handle
            and r.get('t') is not None and abs(r['t'] - t) <= window]
    rows.sort(key=lambda r: r['t'])
    return rows


# ---------------------------------------------------------------- 渲染

def fmt_addr(ip, port):
    if ip is None:
        return '?'
    if ':' in ip and not ip.startswith('::'):
        return '[%s]:%s' % (ip, port)
    return '%s:%s' % (ip, port)


def fmt_n(n):
    if n is None:
        return '?'
    if n >= 1024 * 1024:
        return '%.1fM' % (n / 1048576.0)
    if n >= 1024:
        return '%.1fK' % (n / 1024.0)
    return str(n)


class Rep(object):
    def __init__(self):
        self.buf = []

    def sec(self, n, title, conf):
        self.buf.append('')
        self.buf.append('## 【%d】%s   [%s]' % (n, title, conf))
        self.buf.append('')

    def line(self, s=''):
        self.buf.append(s)

    def table(self, header, rows):
        self.buf.append('| ' + ' | '.join(header) + ' |')
        self.buf.append('|' + '|'.join(['---'] * len(header)) + '|')
        for r in rows:
            self.buf.append('| ' + ' | '.join(str(x) for x in r) + ' |')

    def text(self):
        return '\n'.join(self.buf)


def main():
    try:
        ctypes.windll.kernel32.SetConsoleOutputCP(65001)
    except Exception:
        pass

    ap = argparse.ArgumentParser()
    ap.add_argument('jsonl', help='rt_etw.py 或 rt_hook.py 写出的记录')
    ap.add_argument('--names', action='append', default=[],
                    metavar='IP=HOST',
                    help='地址反查表，可重复。IP 从 ipconfig /displaydns 里读出来最准')
    ap.add_argument('--assert-game', action='append', default=[],
                    metavar='HANDLE',
                    help='人已看过调用栈、确认这是游戏 socket，才传这个')
    ap.add_argument('--out', help='同时把报告写成 markdown 文件')
    a = ap.parse_args()

    head, evs = load(a.jsonl)
    if not evs:
        print('[!] %s 里没有任何事件记录' % a.jsonl)
        return 2

    names = {}
    for kv in a.names:
        if '=' in kv:
            ip, _, hn = kv.partition('=')
            names[ip.strip()] = hn.strip()

    socks = profile(evs)
    r = Rep()

    # ---- 元信息
    r.line('# 运行时定位报告')
    r.line()
    r.line('- 记录文件：`%s`' % a.jsonl)
    r.line('- 采集头：`%s`' % json.dumps(head, ensure_ascii=False))
    ts = [x['t'] for x in evs if x.get('t') is not None]
    r.line('- 事件数：**%d**；时间窗：`t = %.3f .. %.3f`（%.1f 秒）'
           % (len(evs), min(ts), max(ts), max(ts) - min(ts)) if ts else
           '- 事件数：**%d**；**没有任何记录带时间戳**' % len(evs))
    r.line()
    r.line('> 档位含义：**HIGH** 多源互证 / **MEDIUM** 单源直接观测 / '
           '**LOW** 只有间接线索 / **UNKNOWN** 本采集手段看不到。')

    # ---- 1 所有 socket
    r.sec(1, '所有 socket', HIGH if any(api_of(x) == 'socket' for x in evs) else UNKNOWN)
    cy = collections.Counter()
    for s in socks.values():
        cy[(s.fam, s.typ, s.proto)] += 1
    r.line('共 **%d** 个 socket（按 handle 代次号计，即内核 Endpoint 指针复用已拆分）。' % len(socks))
    r.line()
    r.table(['AddressFamily', 'SocketType', 'Protocol', '个数'],
            [(k[0], k[1], k[2], v) for k, v in cy.most_common()])
    r.line()
    r.line('AF_INET=2 / AF_INET6=23；SOCK_STREAM=1 / SOCK_DGRAM=2；'
           'IPPROTO_TCP=6 / IPPROTO_UDP=17。')

    # ---- 2 所有 connect
    conns = [x for x in evs if api_of(x) == 'connect']
    r.sec(2, '所有 connect', HIGH if conns else UNKNOWN)
    if not conns:
        r.line('本记录里没有 connect。')
    else:
        ok = [c for c in conns if c.get('ret') == 0]
        r.line('共 **%d** 次；成功 %d，失败 %d。' % (len(conns), len(ok), len(conns) - len(ok)))
        r.line()
        rows = []
        for c in sorted(conns, key=lambda x: x.get('t') or 0):
            ad = c.get('addr') or {}
            rows.append(('%.3f' % (c.get('t') or 0), c.get('handle'),
                         fmt_addr(ad.get('ip'), ad.get('port')),
                         c.get('ret'), c.get('err') or ''))
        r.table(['t', 'handle', '目标', 'ret', 'err'], rows)

    # ---- 3 目标地址
    r.sec(3, '所有目标地址', HIGH)
    far = collections.Counter()
    for s in socks.values():
        for k, v in s.udp_far.items():
            far[k] += v
        if s.remote:
            far[s.remote] += s.n_send
    rows = []
    for (ip, port), n in sorted(far.items(), key=lambda x: -x[1]):
        rows.append((fmt_addr(ip, port), n, names.get(ip, '—'),
                     '回环' if is_loop(ip) else '外网'))
    if rows:
        r.table(['地址', '报文数', '反查名', '范围'], rows)
    else:
        r.line('没有观测到任何目标地址。')

    # ---- 4 目标端口
    r.sec(4, '所有目标端口', HIGH)
    ports = collections.Counter()
    for (ip, port), n in far.items():
        ports[port] += n
    r.line('运行时**实际观测到**的端口（与配置里写了什么无关）：')
    r.line()
    r.table(['端口', '报文数'], [(p, n) for p, n in ports.most_common()])

    # ---- 5 TCP/UDP
    r.sec(5, 'TCP/UDP', HIGH)
    kinds = collections.Counter(proto_okind(s.typ) for s in socks.values())
    tcp, udp, unk = kinds.get('TCP', 0), kinds.get('UDP', 0), kinds.get(None, 0)
    r.line('SOCK_STREAM(TCP) **%d** 个；SOCK_DGRAM(UDP) **%d** 个。' % (tcp, udp)
           + ('未识别 **%d** 个（记录里 family/type 为空）。' % unk if unk else ''))
    r.line()
    for kind in ('TCP', 'UDP'):
        owners = [s for s in socks.values() if proto_okind(s.typ) == kind]
        if not owners:
            continue
        seen = []
        for s in owners:
            tgt = fmt_addr(*s.remote) if s.remote else (
                fmt_addr(*next(iter(s.udp_far))) if s.udp_far else '未连接')
            if tgt not in seen:
                seen.append(tgt)
        r.line('- %s 的去向：%s' % (kind, '、'.join('`%s`' % x for x in seen[:12])
                                 + ('…' if len(seen) > 12 else '')))

    # ---- 6 socket 创建位置
    creates = [x for x in evs if api_of(x) == 'socket']
    has_stack = any((x.get('backtrace') or x.get('stack')) for x in creates)
    r.sec(6, 'socket 创建位置', HIGH if has_stack else UNKNOWN)
    if has_stack:
        for x, bt in stacks_of(evs, ('socket',)):
            r.line('- t=%.3f h=%s' % (x.get('t') or 0, x.get('handle')))
            for ln in render_bt(bt):
                r.line('    - `%s`' % ln)
    else:
        r.line('**本采集手段看不到。** AFD ETW 通道不带调用栈；'
               '调用栈只有 rt_hook.js（注入式）能取，而本机被安全软件挡住了注入。')
        r.line()
        r.line('换句话说：【socket 创建位置】目前是 UNKNOWN，'
               '这不是没做，而是现有工具链在**不改动机器安全设置**的前提下做不到。')

    # ---- 7 connect 调用栈
    hs = any((x.get('backtrace') or x.get('stack')) for x in conns)
    r.sec(7, 'connect 调用栈', HIGH if hs else UNKNOWN)
    if hs:
        for x, bt in stacks_of(evs, ('connect',)):
            r.line('- t=%.3f h=%s' % (x.get('t') or 0, x.get('handle')))
            for ln in render_bt(bt):
                r.line('    - `%s`' % ln)
    else:
        r.line('UNKNOWN —— 同上，ETW 无栈。')

    # ---- 8 send/recv 调用栈
    hs = any((x.get('backtrace') or x.get('stack'))
             for x in evs if api_of(x) in ('send', 'recv', 'sendto', 'recvfrom'))
    r.sec(8, 'send/recv 调用栈', HIGH if hs else UNKNOWN)
    if hs:
        for x, bt in stacks_of(evs, ('send', 'recv', 'sendto', 'recvfrom')):
            r.line('- t=%.3f h=%s %s' % (x.get('t') or 0, x.get('handle'), api_of(x)))
            for ln in render_bt(bt):
                r.line('    - `%s`' % ln)
    else:
        r.line('UNKNOWN —— 同上，ETW 无栈。')

    # ---- 9 游戏候选
    r.sec(9, '游戏候选 socket', MEDIUM)
    cands = []
    for s in socks.values():
        tag, why = classify(s, a.assert_game)
        # 已经定性掉的用途（HTTP/HTTPS/CEF/TELEMETRY）不是"候选"，
        # 候选要的是"还没被解释掉、又确实在双向说话"的 socket。
        if tag in ('HTTP', 'HTTPS', 'CEF', 'TELEMETRY'):
            continue
        if s.n_send and s.n_recv:
            cands.append((s, tag, why))
    if not cands:
        r.line('**没有。** 本记录里所有有流量的 socket 都被 80/443/CEF/'
               '单向心跳解释掉了，没有留下"说不清用途、又在双向说话"的连接。')
        r.line()
        r.line('这是一个**否定性结论**，但它是强的：它说明游戏自己的网络层'
               '在这段采集里没有建立任何连接。')
    else:
        r.line('以下 socket 有双向流量、但现有证据不足以定性（端口和地址本身不算证据）：')
        r.line()
        for s, tag, why in cands:
            r.line('- `%s` → %s，发 %d 包/%s 收 %d 包/%s —— %s'
                   % (s.h, fmt_addr(*(s.remote or ('-', '-'))),
                      s.n_send, fmt_n(s.b_send), s.n_recv, fmt_n(s.b_recv), why))

    # ---- 10 确认的游戏 socket
    r.sec(10, '确认的游戏 socket', MEDIUM if a.assert_game else UNKNOWN)
    if a.assert_game:
        for h in a.assert_game:
            s = socks.get(h)
            r.line('- `%s`%s' % (h, '（已由调用者确认）' if s else ' **不存在于本记录**'))
    else:
        r.line('**本脚本不自动下这个结论。** 按第九阶段的要求，'
               '端口和地址本身不构成"足够证据"；'
               '要标 GAME_CONFIRMED 必须先拿到调用栈。')
        r.line()
        r.line('拿到栈之后，用 `--assert-game <handle>` 显式标注。')

    # ---- 11/12 524 / 615 归属
    mk = marker_stream(evs)
    for num in MARKERS:
        hits = mk[num]
        secn = 11 if num == 524 else 12
        r.sec(secn, '%d 所属连接' % num, HIGH if hits else UNKNOWN)
        if not hits:
            r.line('记录里**没有任何**发/收报文的长度正好等于 %d。' % num)
            r.line()
            r.line('（注：ETW 通道不带载荷，只能按长度找。若 %d 是协议里的**消息 ID**'
                   '而非长度，则必须用带载荷的 rt_hook 才能看见。）' % num)
        else:
            for x in hits:
                s = socks.get(x.get('handle'))
                r.line('- t=%.3f h=`%s` %s len=%s%s'
                       % (x.get('t') or 0, x.get('handle'), api_of(x), nbytes(x),
                          ' → %s' % fmt_addr(*s.remote) if s and s.remote else ''))
                pl = x.get('payload') or x.get('data')
                if pl:
                    r.line('      - 载荷前 32B：`%s`' % str(pl)[:64])

    # ---- 13/14 前后数据流
    for num in MARKERS:
        hits = mk[num]
        secn = 13 if num == 524 else 14
        r.sec(secn, '%d 前后数据流' % num, HIGH if hits else UNKNOWN)
        if not hits:
            r.line('UNKNOWN —— 没有定位到 %d，无从谈前后。' % num)
            continue
        for x in hits[:3]:
            h = x.get('handle')
            t0 = x.get('t') or 0
            r.line('### handle `%s`，以 t=%.3f 为中心 ±0.25s' % (h, t0))
            r.line()
            rows = []
            for y in context(evs, h, t0):
                rows.append(('%.3f' % y['t'],
                             '**%s**' % api_of(y) if y is x else api_of(y),
                             nbytes(y) if nbytes(y) is not None else '',
                             y.get('ret') if y.get('ret') is not None else '',
                             y.get('err') or ''))
            r.table(['t', 'api', '字节', 'ret', 'err'], rows)
            r.line()

    # ---- 15 仍未知
    r.sec(15, '仍未知的问题', HIGH)
    unknown = []
    if not has_stack and not stacks_of(evs, ('socket',)):
        unknown.append('【socket 创建位置】—— 无调用栈通道')
    if not (any((x.get('backtrace') or x.get('stack')) for x in conns)):
        unknown.append('【connect 调用栈】—— 无调用栈通道')
    if not any(x.get('payload') or x.get('data') for x in evs):
        unknown.append('【报文载荷/协议格式】—— ETW 通道不携带载荷')
    if not mk[524]:
        unknown.append('【524 的语义】—— 既没找到等长报文，也没载荷可判消息 ID')
    if not mk[615]:
        unknown.append('【615 的语义】—— 同上')
    for u in unknown:
        r.line('- %s' % u)
    r.line()
    r.line('这些全部指向同一个缺口：**注入式采集（能取栈和载荷）在本机被安全软件阻断**。')

    # ---- 16 下一步
    r.sec(16, '下一步', HIGH)
    r.line('1. 让目标进程真正跑起游戏网络层之后再采一次 ——')
    r.line('   当前这份记录里游戏自己的网络模块根本没加载，采到的全是引导/更新/CEF 流量。')
    r.line('2. 要拿调用栈和载荷，必须解决注入通道；这是**机器安全设置层面的决定**，')
    r.line('   需要你本人拍板，脚本不会自作主张去绕过或关闭安全软件。')
    r.line('3. 524/615 只有在游戏网络层起来之后才会出现；在拿到之前，'
           '【524 所属连接】只能停在 UNKNOWN。')

    out = r.text()
    print(out)
    if a.out:
        os.makedirs(os.path.dirname(os.path.abspath(a.out)) or '.', exist_ok=True)
        with open(a.out, 'w', encoding='utf-8') as fh:
            fh.write(out + '\n')
        print('\n[*] 报告已写入 %s' % a.out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
