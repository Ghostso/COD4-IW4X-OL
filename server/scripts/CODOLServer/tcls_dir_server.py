#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CODOL TCLS 目录服务器（本地复刻）。

用途
----
复刻 tcls_core.exe <-> dirserver (tcls.qq.com:10009) 的 DIRTREERESP 交换，
使客户端在停服后仍能拿到一份「非空」目录树。可选地在目录树中插入一个
指向本机大厅的节点，用来观察客户端是否会据此发起大厅连接。

协议形态（来自真实抓包，见 CODOLServer/tcls_dirtree_response.bin）
---------------------------------------------------------------
请求 33 字节（客户端 -> 目录服务器）::

    0a 09 64 1a 00 00 00 07 2a 9e 54 26 00 00 17 71
    00 00 00 01 00 00 00 00 00 00 00 00 00 00 02 30 00 00

    偏移  0..1   : 0a 09         固定魔数
    偏移  2..3   : 64 1a         固定
    偏移  4..7   : 00 00 00 07   序号（大端 u32 = 7）。注意：请求这里不是长度。
    偏移  8..11  : 2a 9e 54 26   ServiceID = 0x2A9E5426 = 715019302（大端）
    偏移 12..15  : 00 00 17 71   事务号 txn（响应同字段 +1 -> 0x1772）
    偏移 16..19  : 00 00 00 01   固定
    偏移 20..29  : 全 0
    偏移 30..32  : 00 02 30      = 560（客户端类型/版本）

响应 774 字节（目录服务器 -> 客户端）::

    偏移  0..1   : 0a 09         固定魔数
    偏移  2..3   : 64 1a         固定
    偏移  4..7   : 00 00 02 ec   大端 u32 = 748 = 总长 774 - 固定头 26
    偏移  8..11  : 2a 9e 54 26   ServiceID（大端，回显）
    偏移 12..15  : 00 00 17 72   事务号 txn+1
    偏移 16..19  : 00 00 00 01   固定
    偏移 20..23  : 00 × 4        固定填充
    偏移 24..25  : 02 06
    偏移 26      : 载荷起点
    偏移 26..27  : 00 09
    偏移 28..29  : 00 00
    偏移 30..31  : 02 db         根节点 nodeid 低位
    偏移 54      : 09 "dir_root" 00   根节点名
    ...          : 依次是 GBK 地区节点 + strURL

本脚本对「响应」采取两种模式：

1. `--mode replay`  原样回放抓到的 774 字节（先证明链路可通）。
2. `--mode tree`    由 JSON 描述的节点树生成一份新的 DIRTREERESP。

安全
----
只监听本机 UDP/TCP 端口，不改动任何系统网络配置（无 netsh / 路由 / DNS /
防火墙 / 网卡）。默认绑定 0.0.0.0:10009 以便直接接住原本发往 tcls.qq.com 的
流量；如果只想本机自测，用 `--bind 127.0.0.1`。

注意：本脚本只负责「目录服务器」这一跳。它不能让客户端跳过登录票据、
CrossSvrID 或游戏本体大厅协议。
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import socket
import struct
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_RESPONSE = os.path.join(HERE, 'tcls_dirtree_response.bin')

MAGIC = b'\x0a\x09\x64\x1a'
DIR_REQ_LEN = 33
DIR_RSP_LEN = 774

SERVICE_ID_DEFAULT = 715019302  # 0x2A9E5426，来自 TCLSHost 日志

# 真实抓包的 33 字节请求（t=1790258907.310847，tcls_core PID 19144 -> 116.130.229.168:10009）
CAPTURED_REQUEST = bytes.fromhex(
    '0a09641a000000072a9e542600001771'
    '0000000100000000000000000002300000'
)


def _ts() -> str:
    return _dt.datetime.now().strftime('%H:%M:%S.%f')[:-3]


class JsonlLog:
    def __init__(self, path):
        self.path = path
        self._lock = threading.Lock()
        if path:
            parent = os.path.dirname(os.path.abspath(path))
            if parent:
                os.makedirs(parent, exist_ok=True)

    def write(self, event, **fields):
        rec = {'t': _ts(), 'event': event}
        rec.update(fields)
        line = json.dumps(rec, ensure_ascii=False, default=str)
        with self._lock:
            print(line, flush=True)
            if self.path:
                with open(self.path, 'a', encoding='utf-8') as fh:
                    fh.write(line + '\n')


def parse_dir_request(data):
    """把 33 字节目录请求拆成字段。短包也能解析（缺失字段不出现）。"""
    info = {
        'raw_len': len(data),
        'hex': data.hex(' '),
        'magic_ok': data[:4] == MAGIC,
    }
    if len(data) >= 8:
        info['body_len'] = struct.unpack_from('>I', data, 4)[0]
    if len(data) >= 12:
        info['service_id'] = struct.unpack_from('>I', data, 8)[0]
    if len(data) >= 16:
        info['txn'] = struct.unpack_from('>I', data, 12)[0]
    if len(data) >= 20:
        info['field_16'] = struct.unpack_from('>I', data, 16)[0]
    if len(data) >= 33:
        info['tail'] = int.from_bytes(data[30:33], 'big')
    return info


def build_response_from_request(req, payload):
    """用请求里的 ServiceID/txn 生成响应头，接上给定载荷。"""
    service_id = SERVICE_ID_DEFAULT
    txn = 0x1771
    if len(req) >= 16:
        service_id = struct.unpack_from('>I', req, 8)[0]
        txn = struct.unpack_from('>I', req, 12)[0]

    body_len = len(payload)
    head = bytearray()
    head += MAGIC
    head += struct.pack('>I', body_len)
    head += struct.pack('>I', service_id)
    head += struct.pack('>I', (txn + 1) & 0xFFFFFFFF)
    head += struct.pack('>I', 1)
    head += fixed_head_tail()
    return bytes(head) + payload


def strip_response_header(rsp):
    """从抓到的 774 字节响应里取出载荷部分（头 26 字节之后）。"""
    return rsp[26:]


def bare_tree_payload():
    """
    只保留 dir_root 的最小合法目录树。

    用途：对照实验。如果 TGP 对这个也回 result: true，说明它不校验目录内容，
    `[100]` 完全属于游戏本体那一层。
    """
    rsp = open(DEFAULT_RESPONSE, 'rb').read()
    # 偏移 26..54 是根节点头（29 字节），偏移 55..63 是 09 "dir_root" 00。
    root_head = rsp[26:54]
    name = rsp[54:63]
    return root_head + name


def fixed_head_tail():
    """
    取抓包响应头里 20..25 这 6 个「固定」字节，避免硬编码跑偏。

    实测抓包值：00 00 00 00 02 06
    """
    try:
        rsp = open(DEFAULT_RESPONSE, 'rb').read()
        if len(rsp) >= 26:
            return bytes(rsp[20:26])
    except OSError:
        pass
    return b'\x00\x00\x00\x00\x02\x06'


def describe_response(rsp):
    out = {'len': len(rsp)}
    if len(rsp) >= 26:
        out['magic_ok'] = rsp[:4] == MAGIC
        out['body_len'] = struct.unpack_from('>I', rsp, 4)[0]
        out['service_id'] = struct.unpack_from('>I', rsp, 8)[0]
        out['txn'] = struct.unpack_from('>I', rsp, 12)[0]
        out['field_16'] = struct.unpack_from('>I', rsp, 16)[0]
    out['dir_root_at'] = rsp.find(b'dir_root')
    nodes = []
    for name in (b'\xb1\xb1\xbe\xa9\xb5\xe7\xd0\xc5',      # 北京电信
                 b'\xb1\xb1\xbe\xa9\xc1\xaa\xcd\xa8',      # 北京联通
                 b'\xc9\xcf\xba\xa3\xb5\xe7\xd0\xc5',      # 上海电信
                 b'\xb9\xe3\xd6\xdd\xb5\xe7\xd0\xc5',      # 广州电信
                 b'\xcf\xe3\xb8\xdb\xb5\xe7\xd0\xc5'):     # 香港电信
        pos = rsp.find(name)
        if pos >= 0:
            nodes.append({'name': name.decode('gbk'), 'offset': pos})
    out['known_gbk_nodes'] = nodes
    out['has_qq_test_url'] = b'www.qq.com:443' in rsp
    return out


def serve_tcp(args, log):
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((args.bind, args.port))
    srv.listen(16)
    log.write('tcp_listen', bind=args.bind, port=args.port)
    while True:
        try:
            conn, addr = srv.accept()
        except OSError as exc:
            log.write('tcp_accept_error', error=str(exc))
            return
        threading.Thread(target=_handle_tcp, args=(conn, addr, args, log),
                         daemon=True).start()


def _handle_tcp(conn, addr, args, log):
    peer = '%s:%d' % addr
    try:
        conn.settimeout(args.read_timeout)
        buf = b''
        while len(buf) < DIR_REQ_LEN:
            try:
                chunk = conn.recv(4096)
            except socket.timeout:
                break
            if not chunk:
                break
            buf += chunk
            if len(buf) >= DIR_REQ_LEN:
                break
        if not buf:
            log.write('tcp_no_data', peer=peer)
            return
        info = parse_dir_request(buf)
        log.write('tcp_request', peer=peer, **info)
        payload = _select_payload(args, info, log)
        rsp = build_response_from_request(buf, payload)
        conn.sendall(rsp)
        log.write('tcp_response', peer=peer, sent=len(rsp), payload=len(payload),
                  head=rsp[:26].hex(' '), mode=args.mode)
        try:
            conn.settimeout(0.5)
            extra = conn.recv(4096)
            if extra:
                log.write('tcp_extra', peer=peer, len=len(extra), hex=extra.hex(' '))
        except socket.timeout:
            pass
    except Exception as exc:  # noqa: BLE001 - 诊断服务器，宁可记日志
        log.write('tcp_error', peer=peer, error=repr(exc))
    finally:
        try:
            conn.close()
        except OSError:
            pass


def serve_udp(args, log):
    srv = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((args.bind, args.port))
    log.write('udp_listen', bind=args.bind, port=args.port)
    while True:
        try:
            data, addr = srv.recvfrom(65535)
        except OSError as exc:
            log.write('udp_recv_error', error=str(exc))
            return
        info = parse_dir_request(data)
        log.write('udp_datagram', peer='%s:%d' % addr, **info)
        if info.get('magic_ok'):
            payload = _select_payload(args, info, log)
            srv.sendto(build_response_from_request(data, payload), addr)


_TREE_CACHE = {}


def _select_payload(args, info, log):
    if args.mode == 'replay':
        return strip_response_header(args.replay_bytes)
    if args.mode == 'tree':
        path = os.path.abspath(args.tree)
        if path not in _TREE_CACHE:
            _TREE_CACHE[path] = build_tree_payload(path, log)
        return _TREE_CACHE[path]
    if args.mode == 'bare':
        return bare_tree_payload()
    if args.mode == 'empty':
        return b''
    raise ValueError('unknown mode: %s' % args.mode)


def build_tree_payload(tree_path, log):
    """
    从 JSON 生成目录载荷。

    先把抓包响应里的地区节点保留，再按 JSON 追加一个大厅节点。
    协议字段语义尚未完全标定（见 _subagent_tdr_protocol.md），
    因此先用 --mode replay 验证链路，再用本模式对比 tcls_core 的接受度。
    """
    with open(tree_path, 'r', encoding='utf-8') as fh:
        spec = json.load(fh)
    log.write('tree_loaded', path=tree_path, keys=sorted(spec.keys()))
    base = strip_response_header(open(DEFAULT_RESPONSE, 'rb').read())
    if not spec.get('append_lobby'):
        return base
    lobby = spec['append_lobby']
    name = lobby['name'].encode('gbk')
    url = lobby['url'].encode('ascii')
    entry = bytearray()
    entry += b'\x00' * 4
    entry += struct.pack('>H', len(name))
    entry += name
    entry += b'\x00' * 4
    entry += struct.pack('>H', len(url))
    entry += url
    entry += b'\x00' * 4
    return base + bytes(entry)


def main(argv=None):
    ap = argparse.ArgumentParser(description='CODOL TCLS directory server (local replica)')
    ap.add_argument('--bind', default='0.0.0.0')
    ap.add_argument('--port', type=int, default=10009)
    ap.add_argument('--mode', choices=('replay', 'tree', 'bare', 'empty'), default='replay')
    ap.add_argument('--replay-file', default=DEFAULT_RESPONSE)
    ap.add_argument('--tree', default=os.path.join(HERE, 'tcls_tree.json'))
    ap.add_argument('--log', default=os.path.join(HERE, 'logs', 'tcls_dir_server.jsonl'))
    ap.add_argument('--read-timeout', type=float, default=3.0)
    ap.add_argument('--tcp-only', action='store_true')
    ap.add_argument('--udp-only', action='store_true')
    ap.add_argument('--describe', action='store_true',
                    help='只打印抓包响应的解析结果后退出')
    args = ap.parse_args(argv)

    if args.describe:
        data = open(args.replay_file, 'rb').read()
        print(json.dumps(describe_response(data), ensure_ascii=False, indent=2))
        print()
        print('captured request:', CAPTURED_REQUEST.hex(' '))
        print(json.dumps(parse_dir_request(CAPTURED_REQUEST), ensure_ascii=False, indent=2))
        return 0

    args.replay_bytes = open(args.replay_file, 'rb').read()
    if args.mode == 'replay' and len(args.replay_bytes) < 26:
        print('replay file too short: %s' % args.replay_file, file=sys.stderr)
        return 2

    log = JsonlLog(args.log)
    log.write('start', mode=args.mode, bind=args.bind, port=args.port,
              replay_file=os.path.abspath(args.replay_file),
              replay_len=len(args.replay_bytes))
    log.write('response_shape', **describe_response(args.replay_bytes))

    threads = []
    if not args.udp_only:
        threads.append(threading.Thread(target=serve_tcp, args=(args, log), daemon=True))
    if not args.tcp_only:
        threads.append(threading.Thread(target=serve_udp, args=(args, log), daemon=True))
    for t in threads:
        t.start()
    try:
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        log.write('stop', reason='KeyboardInterrupt')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
