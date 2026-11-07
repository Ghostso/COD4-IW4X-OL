"""AFD ETW 采集器 —— 第一~五、七阶段的**零注入 / 免管理员**实现。

为什么不是 Frida
----------------
本机装有 360 安全卫士并开着 HIPS 注入防护，`frida.attach()` 到**任何**
其他进程都会 `TransportError: timeout was reached`（自附加正常，说明是
跨进程注入被拦，不是脚本缺陷）。`rt_hook.js` 本身没写错，只是在这台机器上
跑不起来。pktmon 也不行——本 shell 非管理员，PktMon 驱动未加载。

可用的替代是 **`Microsoft-Windows-Winsock-AFD` 内核 ETW**：不需要管理员
（`logman start ... -ets` 免提权即可），不需要注入目标进程，因此既不碰 360
的注入防护，也不碰游戏自带的 ACE/TP3/TGuard。拿到的地址是内核渲染的
运行时对端，例如 `127.0.0.1:34567`——正是「必须从实际运行时参数确认」要的东西。

能力与缺口（诚实记录）
----------------------
能拿到：
  * socket 创建（地址族 / 类型 / 协议）
  * bind / connect / listen / accept，**含真实 ip:port**
  * TCP send / recv 与 UDP sendto / recvfrom 的**字节数**、以及套接字生命周期
拿不到：
  * **调用栈**（第六阶段）——AFD manifest 不产生栈事件；本脚本补不了这个洞
  * **线程 ID**、**用户态 SOCKET 句柄值**、**载荷内容**
  本脚本用内核 `Endpoint` 指针代替句柄做归组，字段名仍叫 `handle`，
  下游按 handle 分组即可，但要知道它不是 `socket()` 的返回值。

进程归因
--------
AFD 事件里**只有 EventID 1000 带 ProcessId**，其余事件只带内核 `Process`
指针。所以先扫一遍建立 `Process 指针 -> PID`，再据此归因全部事件。

两个由此产生的固有盲区（必须知道，不要当成数据缺失来排查）：
  * **采集开始前就已打开的套接字无法归因** —— 它的创建事件在会话之外，
    于是 Process 指针进不了映射表，这些事件的 `pid` 会是 null。
    对策：**先起采集，再启动目标程序**。
  * **内核 Endpoint 指针会被复用** —— 套接字销毁后同一地址可能分配给新
    套接字。所以 `handle` 记作 `<Endpoint>#<第几次创建>`，而不是裸指针。

用法：
    # 采集 60 秒整个系统，落盘 JSONL
    python scripts/rt_etw.py --seconds 60 --out logs/rt_etw.jsonl

    # 只关心游戏进程（进程名模糊匹配，采集开始前解析）
    python scripts/rt_etw.py --name codoMP --seconds 120

    # 换个会话名/中间产物路径（用来并行跑多次）
    python scripts/rt_etw.py --session rt2 --etl logs/afd2.etl --xml logs/afd2.xml

    # 带上域名解析提供程序（第二阶段后半：IP 不是写死的才需要）
    python scripts/rt_etw.py --dns --seconds 60

    # 打印已知的 Location 码 -> 操作 对照表（由受控靶子实测得到）
    python scripts/rt_etw.py --list-locations

    # 原样转储全部事件（排查映射缺口时用）
    python scripts/rt_etw.py --raw --seconds 30

记录落盘后：
    python scripts/rt_summary.py logs/rt_etw.jsonl
"""
import argparse
import collections
import ctypes
import ctypes.wintypes as w
import datetime
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from rt_sockets import proc_names  # noqa: E402  复用 Toolhelp 枚举

AFD_GUID = '{E53C6823-7BB8-44BB-90DC-3F86090D48A6}'
NS_GUID = '{55404E71-4DB9-4DEB-A5F5-8F86E46DDE56}'

# 由 scripts/_selftest_target.py 在受控条件下实测得到（见文档头）。
# Location 是 AFD 内部的操作点编号；同一个操作在 enter/exit 上位置码不同。
LOCATIONS = {
    1006: 'socket() 进入',
    1013: 'socket() 返回',
    2000: '关闭/拆除 进入',
    2001: '关闭/拆除 返回',
    2002: '关闭/拆除 进入(2)',
    2003: '关闭/拆除 返回(2)',
    3047: 'TCP send 进入',
    3051: 'TCP send 返回',
    3056: 'TCP send 进入(2)',
    3024: 'TCP send 返回(2)',
    3100: 'UDP sendto 进入',
    3202: 'UDP sendto 返回',
    4107: 'TCP recv 进入',
    4115: 'TCP recv 进入(2)',
    4116: 'TCP recv 返回(2)',
    4123: 'TCP recv 返回',
    4200: 'UDP recv 进入',
    4201: 'UDP recvfrom 返回（含对端）',
    5023: 'connect 进入（含对端）',
    5024: 'connect 返回（Status 在此）',
    6010: 'accept 进入',
    6011: 'accept 返回',
    6216: '套接字信息查询 进入',
    6220: '套接字信息查询 返回',
    6501: 'accept 通知（聚合）',
    7010: 'bind 进入',
    7022: 'bind 返回（临时端口在此确定）',
    8004: 'UDP 数据通知（聚合）',
    9000: '数据通知（聚合）',
    11002: 'setsockopt（Option/Value）',
    12001: '断开通知（聚合）',
    13006: 'listen 进入（Backlog）',
    13012: 'listen 返回',
}

# NTSTATUS -> 常见 Winsock 错误
NTSTATUS = {
    0: None,
    0xC0000236: ('WSAECONNREFUSED', 10061),
    0xC0000234: ('WSAEINTR', 10004),
    0xC00000B5: ('WSAECONNABORTED', 10053),
    0xC0000120: ('WSAECONNRESET', 10054),
    0xC000013A: ('WSAEINTR/CTRL-C', 10004),
    0xC0000128: ('WSAENOTSOCK', 10038),
    0xC0000054: ('WSAEWOULDBLOCK', 10035),
    0xC00000B0: ('WSAETIMEDOUT', 10060),
    0x8000001D: ('WSAHOST_NOT_FOUND', 11001),
}


def win(path):
    return os.path.abspath(path).replace('/', '\\')


def run(cmd, **kw):
    """跑外部命令；输出统一按 latin1 解码以免中文控制台编码报错。"""
    p = subprocess.run(cmd, capture_output=True, **kw)
    out = (p.stdout or b'').decode('latin1', 'ignore')
    err = (p.stderr or b'').decode('latin1', 'ignore')
    return p.returncode, (out + err).strip()


def hexaddr(a):
    """AFD 地址串 -> (family, ip, port)；解析不了返回 (None, raw, None)。

    形态：`127.0.0.1:9`、`0.0.0.0`、`[fe80::54ba:60e8:5930:d84c%21]:57521`。
    IPv6 带 scope id（`%21`）要保留，否则 ip 会被截断。
    """
    if not a:
        return None, None, None
    a = a.strip()
    if not a:
        return None, None, None
    m = re.match(r'^\[(.*?)\](?::(\d+))?$', a)      # 带方括号的 v6
    if m:
        return 'AF_INET6', m.group(1), (int(m.group(2)) if m.group(2) else None)
    if ':' in a:
        head, _, tail = a.rpartition(':')
        if tail.isdigit():
            return ('AF_INET6' if ':' in head else 'AF_INET'), head, int(tail)
        if re.fullmatch(r'[0-9a-fA-F:.%]+', a):     # 无端口的 v6
            return 'AF_INET6', a, None
        return None, a, None
    if re.fullmatch(r'[0-9a-fA-F.]+', a):
        return 'AF_INET', a, None
    return None, a, None


AF = {0: 'AF_UNSPEC', 2: 'AF_INET', 23: 'AF_INET6'}
TYPE = {1: 'SOCK_STREAM', 2: 'SOCK_DGRAM', 3: 'SOCK_RAW'}
PROTO = {0: 'IPPROTO_IP', 1: 'IPPROTO_ICMP', 6: 'IPPROTO_TCP', 17: 'IPPROTO_UDP'}


_ISO = re.compile(r'(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.(\d+))?'
                  r'(Z|[+-]\d{2}:\d{2}(?::\d{2})?)?')


def _off_of(s):
    """取出 ISO 串尾部写的偏移量（`Z` / `+HH:MM` / `+HH:MM:SS`），没有则 None。"""
    m = _ISO.match(s or '')
    return m.group(8) if m else None


def _off_seconds(off):
    if not off or off == 'Z':
        return 0
    sign = 1 if off[0] == '+' else -1
    p = off[1:].split(':')
    secs = int(p[0]) * 3600 + int(p[1]) * 60
    if len(p) > 2:
        secs += int(p[2])
    return sign * secs


def dom_offset(evs):
    """本次会话**占多数**的偏移量字符串（没有则 None）。

    tracerpt 在这台机器上把几乎全部事件渲染成 `+07:59`，却对其中**一条**写了
    `+08:00`。两个都不能逐条无条件相信：

    * 若按它自己写的偏移逐条换算，那条 `+08:00` 会落到采集开始**之前** 57 秒
      （不可能），并把 t 的零点整体带偏，使别的记录出现负 t。
    * 若一律当 UTC，整条时间线会偏 8 小时。

    而 `+07:59` 这一族是**自洽**的：按它换算，首条事件落在采集头 `at`
    （Python 的 time.time()）之后 +1.2s、末条落在 +58.3s（采集正是 58 秒）
    —— 两个独立时钟互证。所以取众数，用它统一解释全部事件；那一条离群的
    offset 标签按 tracerpt 的渲染抖动处理。
    """
    c = collections.Counter(x for x in (_off_of(e['t']) for e in evs) if x)
    return c.most_common(1)[0][0] if c else None


def iso_epoch(s, force_off=None):
    """tracerpt 的 SystemTime（ISO8601）-> Unix 秒。

    两个坑：

    1. 它出现在 <TimeCreated SystemTime="..."/> 的**属性**里，不是元素文本，
       所以不能用 tag() 取——早先版本就是这么把时间全丢成 0 的。
    2. 偏移量标签**不可逐条信任**（见 dom_offset 的说明），所以默认调用方
       应传入会话众数 `force_off`，把整条时间线统一到同一个偏移下。
    """
    m = _ISO.match(s or '')
    if not m:
        return None
    y, mo, d, h, mi, se = (int(x) for x in m.groups()[:6])
    us = int((m.group(7) or '0')[:6].ljust(6, '0'))
    off = force_off if force_off is not None else m.group(8)
    tz = datetime.timezone(datetime.timedelta(seconds=_off_seconds(off)))
    try:
        return datetime.datetime(y, mo, d, h, mi, se, us, tzinfo=tz).timestamp()
    except ValueError:
        return None


def parse_etl(etl, xml, keep_xml):
    """ETL -> XML -> 事件字典列表（按时间排序）。"""
    rc, out = run(['tracerpt', win(etl), '-o', win(xml), '-of', 'XML', '-y'])
    if not os.path.exists(xml):
        print('[!] tracerpt 未产出 XML。rc=%s 输出：%s' % (rc, out[:400]))
        return []
    d = open(xml, encoding='utf-8', errors='ignore').read()
    blocks = re.findall(r'<Event .*?</Event>', d, re.S)

    def field(b, n):
        m = re.search(r'<Data Name="%s">(.*?)</Data>' % n, b, re.S)
        return m.group(1).strip() if m else None

    def tag(b, n):
        m = re.search(r'<%s[^>]*>(.*?)</%s>' % (n, n), b, re.S)
        return m.group(1).strip() if m else None

    def tstamp(b):
        m = re.search(r'<TimeCreated\s+SystemTime="([^"]+)"', b)
        return m.group(1).strip() if m else None

    evs = []
    for b in blocks:
        eid = tag(b, 'EventID')
        if not eid or eid == '0':
            continue
        names = re.findall(r'<Data Name="(.*?)">', b)
        vals = {n: field(b, n) for n in names}
        evs.append({
            'id': int(eid),
            't': tstamp(b),
            'proc': vals.pop('Process', None),
            'ep': vals.pop('Endpoint', None),
            'vals': vals,
        })
    # 时间序：按**统一偏移后**的 epoch 排。不能按 ISO 字典序排——那样一条
    # 离群的 offset 标签（如 +08:00 vs +07:59）会把顺序排错，零点也就跟着错。
    dom = dom_offset(evs)
    evs.sort(key=lambda e: (iso_epoch(e['t'], dom) or 0))
    if not keep_xml:
        try:
            os.remove(xml)
        except OSError:
            pass
    return evs


def build_ptr2pid(evs):
    m = {}
    for e in evs:
        pid = e['vals'].get('ProcessId')
        if e['proc'] and pid:
            m[e['proc']] = int(pid, 16)
    return m


def to_int(s):
    try:
        return int(s, 0)
    except (TypeError, ValueError):
        return None


def emit(evs, ptr2pid, want_pids, fh, raw, do_print):
    """有状态地把事件流翻译成 rt_hook.js 兼容的 JSONL。"""
    T0 = time.time()
    # t 的零点 = 会话中第一条带时间戳的事件（evs 已按统一偏移后的 epoch 排序）
    dom = dom_offset(evs)
    T0E = next((x for x in (iso_epoch(e['t'], dom) for e in evs) if x is not None), None)
    out = []
    # 每个 endpoint 的挂起状态：connect 的对端、send/recv 的长度
    pend = {}
    # 内核 Endpoint 指针在套接字销毁后会被复用，所以指针本身不是唯一句柄。
    # 给每个「创建」分配一个世代号，handle 变成 `<ep>#<n>`，生命周期才可区分。
    life = {}

    def P(ep):
        return pend.setdefault(ep or '?', {})

    def hnew(ep):
        life[ep] = life.get(ep, 0) + 1
        return '%s#%d' % (ep, life[ep])

    def hold(ep):
        return '%s#%d' % (ep, life.get(ep, 1))

    def rec(o, tid_pid=None):
        # t 是相对会话首事件的秒数（与 rt_hook.js 的 t 同义）；
        # 绝对时间保留在 wall 里。两者都来自 ETL 的真实时间戳。
        if o.get('t') is None:
            ep = iso_epoch(o.get('wall'), dom)
            o['t'] = round(ep - T0E, 6) if (ep is not None and T0E is not None) else None
        if o.get('pid') is None and tid_pid:
            o['pid'] = tid_pid
        out.append(o)
        if fh:
            fh.write(json.dumps(o, ensure_ascii=False) + '\n')

    for e in evs:
        pid = ptr2pid.get(e['proc'])
        if want_pids and pid not in want_pids:
            continue
        ep = e['ep']
        v = e['vals']
        st = to_int(v.get('Status'))
        ee = to_int(v.get('EnterExit'))
        # 创建事件开新世代；其余事件沿用当前世代。
        h = hnew(ep) if (e['id'] == 1000 and ee == 0) else hold(ep)
        base = {'pid': pid, 'handle': h, 'ep': ep, 'src': 'etw',
                'id': e['id'], 'loc': to_int(v.get('Location')), 'ee': ee,
                'wall': e['t']}
        if raw:
            o = dict(base)
            o.update({k: x for k, x in v.items() if x is not None})
            rec(o)
            continue

        i = e['id']

        if i == 1000:
            if ee == 0:
                P(ep).update(fam=to_int(v.get('AddressFamily')),
                             typ=to_int(v.get('SocketType')),
                             prot=to_int(v.get('Protocol')))
            else:
                s = P(ep)
                o = dict(base, api='socket',
                         family=AF.get(s.get('fam'), s.get('fam')),
                         type=TYPE.get(s.get('typ'), s.get('typ')),
                         proto=PROTO.get(s.get('prot'), s.get('prot')),
                         ret=0)
                rec(o)

        elif i == 1030:
            fam, ip, port = hexaddr(v.get('Address'))
            if ee == 0:
                P(ep)['bind'] = {'family': fam, 'ip': ip, 'port': port}
            else:
                a = hexaddr(v.get('Address'))
                rec(dict(base, api='bind',
                         addr={'family': a[0], 'ip': a[1], 'port': a[2]},
                         ret=0 if not st else -1, err=st))

        elif i == 1018:
            if ee == 0:
                fam, ip, port = hexaddr(v.get('Address'))
                P(ep)['conn'] = {'family': fam, 'ip': ip, 'port': port}

        elif i == 1017:
            a = P(ep).get('conn') or {'family': None, 'ip': None, 'port': None}
            nt = NTSTATUS.get(st)
            rec(dict(base, api='connect', addr=a,
                     ret=0 if st == 0 else -1,
                     err=(nt[1] if nt else st), ntstatus=(hex(st) if st else None)))

        elif i == 1037:
            if ee == 0:
                P(ep)['backlog'] = to_int(v.get('Backlog'))
            else:
                rec(dict(base, api='listen', backlog=P(ep).get('backlog'),
                         ret=0 if not st else -1, err=st))

        elif i == 1024:
            a = hexaddr(v.get('Address'))
            rec(dict(base, api='accept',
                     addr={'family': a[0], 'ip': a[1], 'port': a[2]},
                     accept_handle=v.get('AcceptEndpoint'),
                     backlog=to_int(v.get('CurrentBacklog')),
                     ret=0 if not st else -1, err=st))

        elif i == 1035:
            rec(dict(base, api='setsockopt', option=to_int(v.get('Option')),
                     value=to_int(v.get('Value')), ret=0 if not st else -1, err=st))

        elif i == 1003:          # TCP send
            if ee == 0:
                P(ep)['send'] = to_int(v.get('BufferLength'))
            else:
                rec(dict(base, api='send', len=P(ep).get('send'),
                         ret=P(ep).get('send') if st == 0 else -1, err=st,
                         payload=None))

        elif i == 1004:          # TCP recv
            if ee == 0:
                P(ep)['recvwant'] = to_int(v.get('BufferLength'))
            else:
                n = to_int(v.get('BufferLength'))
                rec(dict(base, api='recv', want=P(ep).get('recvwant'),
                         ret=n if not st else -1, err=st, payload=None))

        elif i == 1007:          # UDP sendto
            if ee == 0:
                fam, ip, port = hexaddr(v.get('Address'))
                P(ep)['to'] = {'family': fam, 'ip': ip, 'port': port}
                P(ep)['ulen'] = to_int(v.get('BufferLength'))
            else:
                n = to_int(v.get('BufferLength')) or P(ep).get('ulen')
                rec(dict(base, api='sendto', addr=P(ep).get('to'), len=n,
                         ret=n if not st else -1, err=st, payload=None))

        elif i == 1009:          # UDP recvfrom
            fam, ip, port = hexaddr(v.get('Address'))
            n = to_int(v.get('BufferLength'))
            rec(dict(base, api='recvfrom',
                     addr={'family': fam, 'ip': ip, 'port': port}, ret=n,
                     err=st, payload=None))

        elif i in (1001, 1002):
            if ee == 0:
                rec(dict(base, api='closesocket', ret=0, err=st))

        elif i == 1032:
            rec(dict(base, api='disconnect', reason=to_int(v.get('Reason')),
                     ret=0, err=st))

    if do_print:
        for o in out:
            api = o.get('api', 'id=%s' % o.get('id'))
            a = o.get('addr') or {}
            extra = ''
            if a:
                extra = ' %s:%s' % (a.get('ip'), a.get('port'))
            if o.get('len') is not None:
                extra += ' len=%s' % o.get('len')
            if o.get('err'):
                extra += ' err=%s%s' % (o.get('err'),
                                        ('(%s)' % o['ntstatus']) if o.get('ntstatus') else '')
            hh = o.get('handle') or ''
            hh = (hh.split('#')[0][-4:] + '#' + hh.split('#')[1]) if '#' in hh else hh[-6:]
            print('  pid=%-6s %-11s h=%-9s%s' % (o.get('pid'), api, hh, extra))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pid', type=int, action='append', default=[])
    ap.add_argument('--name', action='append', default=[])
    ap.add_argument('--seconds', type=int, default=60)
    ap.add_argument('--out', default='logs/rt_etw.jsonl')
    ap.add_argument('--etl', default='logs/rt_afd.etl')
    ap.add_argument('--xml', default='logs/rt_afd.xml')
    ap.add_argument('--session', default='codolrt')
    ap.add_argument('--dns', action='store_true', help='同时开启 NameResolution 提供程序')
    ap.add_argument('--keep-xml', action='store_true', help='保留中间 XML')
    ap.add_argument('--raw', action='store_true', help='原样转储全部事件')
    ap.add_argument('--list-locations', action='store_true')
    ap.add_argument('--reparse', action='store_true',
                    help='不采集，直接用已有的 --etl 重新解码落盘（改解析器后回归用）')
    a = ap.parse_args()

    if a.list_locations:
        print('EventID / Location -> 操作（由 scripts/_selftest_target.py 实测）')
        print('  EnterExit: 0=进入 1=返回 3=聚合通知 4=选项类')
        for loc in sorted(LOCATIONS):
            print('    loc=%-6d %s' % (loc, LOCATIONS[loc]))
        return 0

    # ---- 目标进程（采集前解析；采集期间新建的进程不在其中） --------------------
    want = set(a.pid)
    if a.name and not want:
        nm = proc_names()
        hits = [p for p, n in nm.items()
                if all(x.lower() in n.lower() for x in a.name)]
        if not hits:
            print('[!] 没有进程名匹配 %r。当前样本：%s'
                  % (a.name, ', '.join(sorted(set(nm.values()))[:25])))
            print('[i] 仍然继续采集全系统事件，落盘后可按 --pid 复查。')
        else:
            want.update(hits)
            print('[i] 匹配到目标 pid: %s'
                  % ', '.join('%d(%s)' % (p, nm[p]) for p in hits))

    for d in ('logs',):
        os.makedirs(d, exist_ok=True)
    os.makedirs(os.path.dirname(os.path.abspath(a.etl)) or '.', exist_ok=True)

    if a.reparse:
        # 直接拿已有 ETL 重新解码。注意采集头里记的 seconds/at 是**上次**的，
        # 这里沿用旧头的 at 让 t 的零点与原采集一致，便于和新旧文件对照。
        if not os.path.exists(a.etl):
            print('[!] --reparse 指定的 ETL 不存在：%s' % a.etl)
            return 2
        print('[i] --reparse：直接解码 %s（%d 字节）' % (a.etl, os.path.getsize(a.etl)))
        hdr = None
        if os.path.exists(a.out):
            try:
                with open(a.out, encoding='utf-8') as fh:
                    hdr = json.loads(fh.readline())
            except Exception:
                hdr = None
        a.seconds = (hdr or {}).get('seconds', a.seconds)
    else:
        # ---- 起 ETW 会话 -----------------------------------------------------
        run(['logman', 'stop', a.session, '-ets'])      # 清掉上次残留
        for p in (a.etl, a.xml):
            try:
                os.remove(p)
            except OSError:
                pass

        cmd = ['logman', 'start', a.session, '-p', AFD_GUID,
               '-o', win(a.etl), '-ets']
        rc, out = run(cmd)
        if not os.path.exists(a.etl):
            print('[!] 会话启动失败（未生成 ETL）。rc=%s\n%s' % (rc, out))
            return 2
        print('[i] AFD 会话已启动 -> %s' % a.etl)

        if a.dns:
            rc2, out2 = run(['logman', 'update', a.session, '-p', NS_GUID,
                             '-o', win(a.xml + '.dns.etl'), '-ets'])
            print('[i] NameResolution：%s' % ('已加入' if rc2 == 0 else out2[:200]))

        print('[*] 采集 %d 秒……（现在去操作目标程序）' % a.seconds)
        try:
            for i in range(a.seconds):
                time.sleep(1)
                if sys.stdout.isatty() and (i + 1) % 10 == 0:
                    print('    ... %d/%d' % (i + 1, a.seconds))
        except KeyboardInterrupt:
            print('\n[i] 提前停止（已采集 %ds）' % (i + 1))

        rc, out = run(['logman', 'stop', a.session, '-ets'])
        print('[i] 会话已停止（rc=%s）' % rc)
        if not os.path.exists(a.etl):
            print('[!] 没有 ETL 产出')
            return 2
        print('[i] ETL %d 字节' % os.path.getsize(a.etl))

    # ---- 解码 -----------------------------------------------------------------
    evs = parse_etl(a.etl, a.xml, a.keep_xml)
    if not evs:
        print('[!] 没有解析到事件。会话可能在起之前就被停了，或提供程序未产生数据。')
        return 2
    ptr2pid = build_ptr2pid(evs)
    print('[i] 共 %d 条事件；Process 指针 -> PID：%s'
          % (len(evs), ', '.join('%s=%d' % (k[-6:], v) for k, v in ptr2pid.items())))

    if want:
        n = sum(1 for e in evs if ptr2pid.get(e['proc']) in want)
        print('[i] 其中属于目标 pid 的 %d 条' % n)

    os.makedirs(os.path.dirname(os.path.abspath(a.out)) or '.', exist_ok=True)
    with open(a.out, 'w', encoding='utf-8') as fh:
        head = {
            'note': 'session start', 'src': 'etw', 'at': time.time(),
            'schema': 'compatible with rt_hook.js; handle = kernel AFD Endpoint '
                      'pointer (NOT the user-mode SOCKET value); no tids, no payloads',
            'etl': a.etl, 'providers': ['AFD'] + (['NameResolution'] if a.dns else []),
            'want_pids': sorted(want) or 'all', 'seconds': a.seconds,
        }
        if a.reparse:
            # 保留原采集的 at（T0 参照点），否则新旧文件无法对齐
            head['at'] = (hdr or {}).get('at', head['at'])
            head['note'] = 'reparse of %s' % a.etl
            head['reparsed_at'] = time.time()
            head['want_pids'] = sorted(want) or (hdr or {}).get('want_pids', 'all')
        fh.write(json.dumps(head, ensure_ascii=False) + '\n')
        print('\n[i] 事件时间线（目标进程）：' if want else '\n[i] 事件时间线：')
        out = emit(evs, ptr2pid, want, None, a.raw, True)

        print('\n[*] 落盘 %d 条 -> %s' % (len(out), a.out))
        for o in out:
            fh.write(json.dumps(o, ensure_ascii=False) + '\n')

    print('\n[*] 用 python scripts/rt_summary.py %s 生成 16 节报告' % a.out)
    return 0


if __name__ == '__main__':
    ctypes.windll.kernel32.SetConsoleOutputCP(65001)
    sys.exit(main())
