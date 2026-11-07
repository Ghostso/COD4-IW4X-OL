#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fake_tqos_server.py -- local TQoS/IIPS stand-in for CODOL.

Listens on 127.0.0.1 for the UDP "ur" protocol the client sends after the
hostname redirect, logs every datagram, and replies with a best-effort echo
plus an ACK-shaped response so we can observe how the client reacts.

Observation/harness only: no system network configuration is changed.

Usage:
    python fake_tqos_server.py --out <dir> [--seconds 120] [--ports 8000,8081]
"""

import argparse
import json
import os
import socket
import struct
import sys
import threading
import time


def hexdump(data):
    return data.hex()


def try_parse_ur(data):
    """Best-effort decode of the observed 'ur' header."""
    if len(data) < 8:
        return {'raw': hexdump(data)}
    out = {'magic': data[:2].decode('ascii', 'replace')}
    if len(data) >= 16:
        head = struct.unpack_from('>HHHHH', data, 2)
        out.update({'ruHeadLen': head[0], 'bodyLen': head[1],
                    'cmd': head[2], 'protoVer': head[3],
                    'reserved': head[4], 'seq': struct.unpack_from('>I', data, 12)[0]})
    if len(data) >= 20:
        out['businessID'] = struct.unpack_from('>I', data, 16)[0]
    if len(data) >= 24:
        out['body_u16_1'] = struct.unpack_from('>H', data, 20)[0]
        out['body_u16_2'] = struct.unpack_from('>H', data, 22)[0]
    out['tail'] = hexdump(data[24:])
    return out


def build_response(req, variant):
    """Build a QOS_GET_RES-shaped reply from a QOS_GET_REQ request."""
    seq = struct.unpack_from('>I', req, 12)[0] if len(req) >= 16 else 0
    business = struct.unpack_from('>I', req, 16)[0] if len(req) >= 20 else 100
    if variant == 0:
        # Minimal QOS_GET_RES: BusinessID + QosResFlag=0.
        body = struct.pack('>II', business, 0)
    elif variant == 1:
        # All four flag bits set, no nested records yet.
        body = struct.pack('>II', business, 0xF)
    elif variant == 2:
        # One GameSvr pointing back at the local fake TCP/UDP stack.
        ip = b'127.0.0.1\x00'
        body = (struct.pack('>II', business, 0xF) +
                struct.pack('>H', 1) +
                struct.pack('>H', len(ip)) + ip +
                struct.pack('>I', 0x7F000001) +
                struct.pack('>H', 8000) +
                struct.pack('>I', 0))
    elif variant in (3, 4, 5):
        # QOS_GET_RES with 24 ConndIPPort entries pointing at loopback.
        n = 24
        if variant == 3:
            entry = struct.pack('>IHI', 0x7F000001, 8000, 0)
        elif variant == 4:
            entry = struct.pack('>IHHI', 0x7F000001, 8000, 0, 0)
        else:
            entry = struct.pack('>IH', 0x7F000001, 8000)
        body = (struct.pack('>II', business, 0xF) +
                struct.pack('>HH', 0, n) +
                entry * n)
    else:
        body = struct.pack('>II', business, 0)
    header = b'ur' + struct.pack('>HHHHH', 16, len(body), 4, 0, 0) + struct.pack('>I', seq)
    return header + body


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--seconds', type=float, default=120.0)
    ap.add_argument('--ports', default='8000,8081')
    ap.add_argument('--reply', action='store_true',
                    help='send a synthetic response back to the client')
    ap.add_argument('--variant', type=int, default=0)
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    trace = open(os.path.join(args.out, 'fake_tqos.jsonl'), 'w', encoding='utf-8')
    log = open(os.path.join(args.out, 'fake_tqos.log'), 'w', encoding='utf-8')

    def emit(obj):
        trace.write(json.dumps(obj, ensure_ascii=False) + '\n')
        trace.flush()
        log.write(json.dumps(obj, ensure_ascii=False) + '\n')
        log.flush()
        print(json.dumps(obj, ensure_ascii=False), flush=True)

    stop = threading.Event()
    ports = [int(p) for p in args.ports.split(',') if p.strip()]

    def udp_loop(port):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(('127.0.0.1', port))
            s.settimeout(0.5)
        except Exception as exc:
            emit({'proto': 'udp', 'port': port, 'bind_error': repr(exc)})
            return
        while not stop.is_set():
            try:
                data, addr = s.recvfrom(65535)
            except socket.timeout:
                continue
            except Exception:
                break
            rec = {'proto': 'udp', 'port': port, 'peer': list(addr),
                   'len': len(data), 'data_hex': hexdump(data),
                   'parsed': try_parse_ur(data), 't': time.time()}
            emit(rec)
            if args.reply:
                try:
                    resp = build_response(data, args.variant)
                    s.sendto(resp, addr)
                    emit({'proto': 'udp', 'port': port, 'sent_reply_len': len(resp),
                          'sent_hex': resp.hex(), 'to': list(addr)})
                except Exception as exc:
                    emit({'proto': 'udp', 'port': port, 'reply_error': repr(exc)})
        s.close()

    threads = [threading.Thread(target=udp_loop, args=(p,), daemon=True)
               for p in ports]
    for t in threads:
        t.start()

    def tcp_loop(port):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(('127.0.0.1', port))
            s.listen(16)
            s.settimeout(0.5)
        except Exception as exc:
            emit({'proto': 'tcp', 'port': port, 'bind_error': repr(exc)})
            return
        while not stop.is_set():
            try:
                conn, addr = s.accept()
            except socket.timeout:
                continue
            except Exception:
                break
            try:
                conn.settimeout(0.5)
                data = conn.recv(16384)
                emit({'proto': 'tcp', 'port': port, 'peer': list(addr),
                      'len': len(data), 'data_hex': data.hex(),
                      'data_text': data.decode('latin-1', 'replace')})
                conn.sendall(b'HTTP/1.1 200 OK\r\nContent-Length: 0\r\n\r\n')
            except Exception as exc:
                emit({'proto': 'tcp', 'port': port, 'error': repr(exc)})
            try:
                conn.close()
            except Exception:
                pass
        s.close()

    for p in [80, 443, 3074, 8000, 8081, 10009, 10010]:
        t = threading.Thread(target=tcp_loop, args=(p,), daemon=True)
        t.start()
        threads.append(t)
    emit({'event': 'listening', 'ports': ports})
    t0 = time.time()
    while time.time() - t0 < args.seconds:
        time.sleep(1)
    stop.set()
    time.sleep(1)
    trace.close()
    log.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
