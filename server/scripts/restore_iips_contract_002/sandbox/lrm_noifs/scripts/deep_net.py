"""深度网络分析（只读）。

1. 对候选函数做**全函数**反汇编（不是 16 条尾部窗口），用于人工回溯
   sockaddr 构造 / 主机名来源 / socket 句柄来源（第三、四、五任务）。
2. 在每个函数体内列出所有「往内存写立即数」的指令（含 word/byte），
   sockaddr 的 sin_family / sin_port / sin_addr 一定出现在其中。
3. 全文件字符串扫描：Rse* / codol / qq.com / 端口串 / 协议名，
   用于第七任务（524=RseAuthState, 615=RseCountryOpen）与端点。

用法: python scripts/deep_net.py
输出: scripts/_out/deep_net.txt
"""
import sys, os, re, bisect, collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pe import Image
import x86callers as X

IMAGE_BASE = 0x10000000

# ---- 待全量反汇编的函数（都是 netcallers 里确认含网络调用的） ----
FUNCS_A = [  # 家族 A (0x002d…/0x0041…-0x0044…)
    (0x002d9470, 'A socket (OpenSSL bio)'),
    (0x002d94d0, 'A connect (OpenSSL bio)'),
    (0x002d97a0, 'A recv'),
    (0x002d9840, 'A send'),
    (0x00420c80, 'A WSAStartup/WSACleanup'),
    (0x00424780, 'A WSAIoctl+setsockopt'),
    (0x00424960, 'A htons/ntohs/getsockname'),
    (0x00424d80, 'A getsockopt'),
    (0x00424e70, 'A ntohs'),
    (0x00424ed0, 'A getpeername/getsockname'),
    (0x004250b0, 'A setsockopt'),
    (0x00425150, 'A getsockopt+setsockopt'),
    (0x004252f0, 'A closesocket'),
    (0x00425370, 'A socket'),
    (0x00425530, 'A connect  <== 关键'),
    (0x0042c910, 'A sendto x4'),
    (0x0042cc70, 'A sendto x4'),
    (0x0042d170, 'A bind'),
    (0x0042d930, 'A recvfrom'),
    (0x0042f670, 'A send (3字节头)'),
    (0x0042feb0, 'A send (%%c%%c 文本协议)'),
    (0x00430640, 'A 进程/管道'),
    (0x004310e0, 'A accept'),
    (0x00431460, 'A bind+listen  <== 关键'),
    (0x00443610, 'A WSAIoctl+setsockopt'),
    (0x00444f50, 'A recv'),
    (0x0044b240, 'A getaddrinfo  <== 关键'),
    (0x0044b400, 'A htons'),
    (0x0044d090, 'A ioctlsocket'),
    (0x0051c670, 'A ????'),
    (0x0051caa0, 'A shutdown+recv'),
    (0x0051cbc0, 'A send'),
]
FUNCS_B = [  # 家族 B (0x0064…-0x0068…)
    (0x00641a30, 'B socket AF_INET6'),
    (0x00650900, 'B socket'),
    (0x00650cfe, 'B connect  <== 关键'),
    (0x0065fca0, 'B getaddrinfo'),
    (0x0066fea0, 'B sendto x4'),
    (0x006705b0, 'B bind'),
    (0x00670d50, 'B recvfrom'),
    (0x00674450, 'B accept'),
    (0x006747c0, 'B bind+listen'),
    (0x0064ff20, 'B bind x2 + htons x4'),
]

STR_PATS = [
    (re.compile(rb'[A-Za-z0-9_\.\-]{3,}\.qq\.com'), 'qq.com 域名'),
    (re.compile(rb'codol', re.I), 'codol'),
    (re.compile(rb'[Rr]se[A-Za-z]{3,}'), 'Rse* 标识符'),
    (re.compile(rb'[Aa]uth[Ss]tate|[Cc]ountry[Oo]pen'), 'AuthState/CountryOpen'),
    (re.compile(rb'\b(19[0-9]|2[0-9][0-9])\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\b'), 'IPv4 串'),
    (re.compile(rb'uworld|demonware|UUC|uuacc|libuucl|wetest', re.I), '中间件名'),
    (re.compile(rb'20[0-9]{3}\b'), '端口串(20xxx)?'),
]


def dump_func(img, out, rva, tag):
    out.append('')
    out.append('=' * 78)
    out.append('### func 0x%08x   %s' % (rva, tag))
    out.append('=' * 78)
    try:
        insns = list(X.dis(img, rva, 0x1200))
    except Exception as e:
        out.append('   [反汇编失败 %s]' % e)
        return
    if not insns:
        out.append('   [空]')
        return
    stores = []
    for ins in insns:
        s = '%08x  %-22s %s %s' % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str)
        out.append('   ' + s)
        op = ins.op_str
        # 收集内存写立即数
        m = re.match(r'^(byte|word|dword) ptr \[(.*?)\], (0x[0-9a-f]+|[0-9]+)$', op)
        if m:
            try:
                v = int(m.group(3), 0)
            except ValueError:
                v = None
            stores.append((ins.address, m.group(1), m.group(2), m.group(3),
                           v, ins.mnemonic))
    out.append('')
    out.append('   -- 内存写立即数汇总 (sockaddr 字段必在其中) --')
    for (a, sz, mem, txt, v, mn) in stores:
        extra = ''
        if v is not None:
            if sz == 'word' and v == 2:
                extra = '  <= sin_family=AF_INET(2)?'
            elif sz == 'word' and v == 23:
                extra = '  <= sin_family=AF_INET6(23)?'
            elif 1024 <= v <= 65535:
                extra = '  <= 可能是端口 %d / 0x%x' % (v, v)
        out.append('   %08x  %s ptr [%s] = %s%s' % (a, sz, mem, txt, extra))


def scan_strings(img, out):
    out.append('')
    out.append('=' * 78)
    out.append('### 全文件关键字符串扫描')
    out.append('=' * 78)
    data = img.data if hasattr(img, 'data') else open(img.path, 'rb').read()
    for rx, tag in STR_PATS:
        seen = set()
        hits = []
        for m in rx.finditer(data):
            s = m.group(0)[:80]
            if s in seen:
                continue
            seen.add(s)
            hits.append((m.start(), s))
            if len(hits) >= 60:
                break
        out.append('')
        out.append('-- %s : %d 个去重命中 --' % (tag, len(hits)))
        for (off, s) in hits[:60]:
            try:
                dec = s.decode('latin-1')
            except Exception:
                dec = repr(s)
            out.append('   0x%08x  %s' % (off, dec))


def main():
    img = Image()
    out = []
    out.append('.text 网络函数全量反汇编 + 字符串扫描')
    for (rva, tag) in FUNCS_A:
        dump_func(img, out, rva, tag)
    for (rva, tag) in FUNCS_B:
        dump_func(img, out, rva, tag)
    try:
        scan_strings(img, out)
    except Exception as e:
        out.append('[字符串扫描失败] %r' % (e,))

    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_out', 'deep_net.txt')
    with open(p, 'w', encoding='utf-8') as f:
        f.write('\n'.join(out))
    print('-> scripts/_out/deep_net.txt  (%d 行)' % len(out))


if __name__ == '__main__':
    main()
