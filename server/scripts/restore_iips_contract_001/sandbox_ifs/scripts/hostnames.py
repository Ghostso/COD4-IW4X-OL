"""全目录 hostname / IP / URL 抽取 —— 为「所有目标地址」一节提供证据面。

只做抽取与归类，**不从端口反推用途**，也不把字符串当作运行时事实；
输出的是「哪里写了什么」，用途一栏靠 whois 域的归属 + 所在文件的性质判定。

用法：
    python scripts/hostnames.py [根目录]
"""
import collections
import os
import re
import sys

HOST = re.compile(
    rb'\b((?:[a-zA-Z0-9_](?:[a-zA-Z0-9_-]{0,61}[a-zA-Z0-9_])?\.)+'
    rb'(?:com|net|org|cn|qq\.com|tencent|io|tv)[a-zA-Z0-9.-]*)')
URL = re.compile(rb'[a-zA-Z]{3,6}://[^\s"\'<>\x00-\x1f]{4,120}')
IP = re.compile(rb'\b(?:\d{1,3}\.){3}\d{1,3}\b')
HOST_U = re.compile(
    r'\b((?:[a-zA-Z0-9_](?:[a-zA-Z0-9_-]{0,61}[a-zA-Z0-9_])?\.)+'
    r'(?:com|net|org|cn|io|tv)[a-zA-Z0-9.-]*)')

TEXT_EXT = ('.ini', '.cfg', '.xml', '.txt', '.dat', '.json', '.lua', '.tdr')
SKIP_DIRS = ('__pycache__', 'scripts', '.git')
# .ifs 载荷已确认是加密的，里面不可能有明文端点；大文件一律跳过，
# 否则会在这 23 GB 上白跑十几分钟且零产出。
SKIP_EXT = ('.ifs', '.tvm0', '.bk', '.png', '.jpg', '.dds', '.bik', '.ogg',
            '.wav', '.mp3', '.zip', '.7z', '.pdb', '.map')
MAX_BYTES = 32 * 1024 * 1024

# 归属判定：域名 → 用途（依据 Tencent 公开的产品域名划分）
OWNER = [
    ('xuanfeng', 'XF 旋风加速/P2P'),
    ('pdldir', 'XF 加速 P2P 目录'),
    ('fs_hello', 'XF 加速 在线/保活'),
    ('fs_conn', 'XF 加速 url→hash'),
    ('fs_h2u', 'XF 加速 hash→url'),
    ('fs_report', 'XF 加速 状态上报'),
    ('stun.qq.com', 'STUN（加速器 NAT 穿透）'),
    ('down.qq.com', '补丁 CDN'),
    ('update.cross.qq.com', '版本服务器'),
    ('codol.qq.com', 'CODOL 游戏域'),
    ('tub.codol', 'CODOL STUN'),
    ('iips.qq.com', 'IIPS 补丁通道'),
    ('gcloud', 'GCloud 语音'),
    ('qq.com', '(腾讯域，需逐条判定)'),
]


def owner(h):
    for k, v in OWNER:
        if k in h:
            return v
    return ''


def src_kind(path):
    e = os.path.splitext(path)[1].lower()
    return 'text' if e in TEXT_EXT else 'binary'


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else '.'
    hosts = collections.defaultdict(set)   # host -> {files}
    ips = collections.defaultdict(set)
    urls = collections.defaultdict(set)

    for dp, dn, fns in os.walk(root):
        dn[:] = [d for d in dn if d not in SKIP_DIRS]
        for fn in fns:
            p = os.path.join(dp, fn)
            rel = os.path.relpath(p, root)
            if os.path.splitext(fn)[1].lower() in SKIP_EXT:
                continue
            try:
                if os.path.getsize(p) > MAX_BYTES:
                    continue
                with open(p, 'rb') as f:
                    d = f.read()
            except Exception:
                continue
            for m in HOST.finditer(d):
                h = m.group(1).decode('latin1').lower().rstrip('.')
                if len(h) > 5 and not h.startswith(('0.', '1.', '2.', '3.')):
                    hosts[h].add(rel)
            for m in URL.finditer(d):
                urls[m.group().decode('latin1')].add(rel)
            if src_kind(p) == 'text':
                try:
                    t = d.decode('utf-16le') if d[:2] in (b'\xff\xfe',) else \
                        d.decode('gb18030', 'ignore')
                except Exception:
                    t = ''
                for m in HOST_U.finditer(t):
                    hosts[m.group(1).lower()].add(rel)
                for m in IP.finditer(d):
                    ips[m.group().decode()].add(rel)

    print('######## hostname（%d）' % len(hosts))
    for h in sorted(hosts, key=lambda x: (owner(x) == '', x)):
        o = owner(h)
        print('  %-32s %-24s %s' % (h, ('<%s>' % o) if o else '',
                                    ', '.join(sorted(hosts[h])[:4])))
    print()
    print('######## URL（%d）' % len(urls))
    for u in sorted(urls):
        print('  %s' % u[:140])
    print()
    print('######## IPv4 字面量（%d，仅文本配置）' % len(ips))
    for i in sorted(ips):
        print('  %-18s %s' % (i, ', '.join(sorted(ips[i])[:4])))


if __name__ == '__main__':
    main()
