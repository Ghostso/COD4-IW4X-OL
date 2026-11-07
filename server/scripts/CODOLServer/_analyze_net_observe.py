# -*- coding: utf-8 -*-
"""Turn a game_net_probe JSONL capture into a readable network report."""

import json
import os
import re
import struct

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'logs', 'net_observe.jsonl')
OUT = os.path.join(HERE, 'NETWORK_OBSERVE_REPORT.md')


def hex_to_bytes(h):
    try:
        return bytes.fromhex(h.replace(' ', ''))
    except Exception:
        return b''


def parse_tls_sni(data):
    try:
        if len(data) < 5 or data[0] != 0x16:
            return None
        # record header: type(1) ver(2) len(2)
        p = 5
        if data[p] != 0x01:      # ClientHello
            return None
        p += 4                    # handshake type + length(3)
        p += 2                    # client version
        p += 32                   # random
        sid_len = data[p]; p += 1 + sid_len
        cs_len = struct.unpack('>H', data[p:p + 2])[0]; p += 2 + cs_len
        comp_len = data[p]; p += 1 + comp_len
        ext_total = struct.unpack('>H', data[p:p + 2])[0]; p += 2
        end = p + ext_total
        while p + 4 <= end:
            etype, elen = struct.unpack('>HH', data[p:p + 4]); p += 4
            edata = data[p:p + elen]; p += elen
            if etype == 0:        # server_name
                # list len(2), name type(1), name len(2), name
                if len(edata) >= 5:
                    nlen = struct.unpack('>H', edata[3:5])[0]
                    return edata[5:5 + nlen].decode('ascii', 'replace')
    except Exception:
        return None
    return None


def parse_http(data):
    try:
        text = data.decode('latin1', 'replace')
        first = text.split('\r\n', 1)[0]
        m = re.match(r'^(GET|POST|HEAD|PUT|OPTIONS|CONNECT)\s+(\S+)\s+HTTP/1\.[01]$', first)
        if not m:
            return None
        host = None
        hm = re.search(r'(?im)^Host:\s*(.+)$', text)
        if hm:
            host = hm.group(1).strip()
        return {'method': m.group(1), 'path': m.group(2), 'host': host}
    except Exception:
        return None


def main():
    rows = []
    with open(SRC, 'r', encoding='utf-8') as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except ValueError:
                    pass

    connects = []
    sock_target = {}
    first_send = {}
    first_recv = {}
    tls_sni = {}
    http_reqs = []

    for r in rows:
        k = r.get('kind')
        if k == 'connect':
            t = r.get('target') or {}
            key = (t.get('ip'), t.get('port'))
            connects.append((r.get('ts'), key, r.get('caller'), r.get('sock')))
            if r.get('sock') is not None:
                sock_target[r['sock']] = key
        elif k == 'send':
            sock = r.get('sock')
            data = hex_to_bytes(r.get('hex') or '')
            if sock not in first_send and data:
                first_send[sock] = (r.get('ts'), r.get('len'), data)
            if data and sock not in tls_sni:
                sni = parse_tls_sni(data)
                if sni:
                    tls_sni[sock] = sni
            http = parse_http(data)
            if http:
                http_reqs.append((r.get('ts'), sock_target.get(sock), http))
        elif k == 'recv':
            sock = r.get('sock')
            data = hex_to_bytes(r.get('hex') or '')
            if sock not in first_recv and data:
                first_recv[sock] = (r.get('ts'), r.get('len'), data)

    lines = []
    lines.append('# CODOL 游戏本体网络观测报告')
    lines.append('')
    lines.append('数据源：`CODOLServer/logs/net_observe.jsonl`')
    lines.append('启动方式：`game_launch_probe.py --mode baseline --safe-shm --ready 1`')
    lines.append('交接块：仅 `TCLS_SHAREDMEMEMORY<pid>`，明文头，len1=len2=0')
    lines.append('')
    lines.append('## 生命周期')
    lines.append('')
    for r in rows:
        if r.get('kind') in ('created_suspended', 'mapping_created', 'resumed', 'finished'):
            lines.append('- `%s` %s' % (r.get('kind'), json.dumps(
                {x: y for x, y in r.items() if x not in ('kind', 'label')},
                ensure_ascii=False)))
    lines.append('')
    lines.append('## 连接目标（去重）')
    lines.append('')
    lines.append('| 时间 | 目标 | 调用方 | socket |')
    lines.append('|---|---|---|---|')
    seen = set()
    for ts, key, caller, sock in connects:
        if key in seen:
            continue
        seen.add(key)
        lines.append('| %s | `%s:%s` | `%s` | %s |' % (ts, key[0], key[1], caller, sock))
    lines.append('')
    lines.append('## TLS SNI')
    lines.append('')
    if tls_sni:
        for sock, sni in sorted(tls_sni.items()):
            lines.append('- socket %s → `%s`（目标 `%s:%s`）' % (
                sock, sni, *(sock_target.get(sock) or ('?', '?'))))
    else:
        lines.append('- 未解出 SNI')
    lines.append('')
    lines.append('## HTTP 请求')
    lines.append('')
    if http_reqs:
        for ts, tgt, q in http_reqs:
            lines.append('- %s  `%s %s`  Host=`%s`  目标=%s' % (
                ts, q['method'], q['path'], q['host'],
                '%s:%s' % tgt if tgt else '?'))
    else:
        lines.append('- 无')
    lines.append('')
    lines.append('## 每 socket 首个发送负载')
    lines.append('')
    for sock in sorted(first_send, key=lambda x: str(x)):
        ts, ln, data = first_send[sock]
        tgt = sock_target.get(sock) or ('?', '?')
        head = data[:64].hex(' ')
        lines.append('- socket %s → %s:%s  len=%s  `%s`' % (sock, tgt[0], tgt[1], ln, head))
    lines.append('')
    lines.append('## 每 socket 首个接收负载')
    lines.append('')
    for sock in sorted(first_recv, key=lambda x: str(x)):
        ts, ln, data = first_recv[sock]
        tgt = sock_target.get(sock) or ('?', '?')
        head = data[:64].hex(' ')
        lines.append('- socket %s → %s:%s  len=%s  `%s`' % (sock, tgt[0], tgt[1], ln, head))
    lines.append('')

    with open(OUT, 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(lines) + '\n')
    print(OUT)
    print('\n'.join(lines[:80]))


if __name__ == '__main__':
    main()
