# -*- coding: utf-8 -*-
"""Multi-port listener: accept whatever the game sends after redirection.

Listens on a set of TCP ports (and one UDP port) and dumps every byte received,
per connection, to a JSONL log. Responds with nothing by default so we can see
the client's first bytes without influencing it.

Usage:
    python port_sniffer.py --tcp 443,8000,8001,8080,8081,14309,2331,7272 \
                           --udp 8000,8081 --log logs/ports.jsonl --out logs/ports_dump.txt
"""

import argparse
import datetime as dt
import json
import os
import socket
import threading
import time


def ts():
    return dt.datetime.now().strftime('%H:%M:%S.%f')[:-3]


class Sink:
    def __init__(self, log_path, dump_path):
        self.log_path = log_path
        self.dump_path = dump_path
        self.lock = threading.Lock()
        os.makedirs(os.path.dirname(os.path.abspath(log_path)) or '.', exist_ok=True)

    def rec(self, **kw):
        rec = {'t': ts()}
        rec.update(kw)
        line = json.dumps(rec, ensure_ascii=False, default=str)
        with self.lock:
            print(line, flush=True)
            with open(self.log_path, 'a', encoding='utf-8') as fh:
                fh.write(line + '\n')

    def dump(self, tag, peer, data):
        ascii_ = ''.join(chr(b) if 32 <= b < 127 else '.' for b in data)
        with self.lock:
            with open(self.dump_path, 'a', encoding='utf-8') as fh:
                fh.write('=' * 90 + '\n')
                fh.write('%s  %s  %s  len=%d\n' % (ts(), tag, peer, len(data)))
                for off in range(0, len(data), 32):
                    ch = data[off:off + 32]
                    fh.write('  %04x  %-95s  %s\n' % (
                        off, ' '.join('%02x' % b for b in ch),
                        ''.join(chr(b) if 32 <= b < 127 else '.' for b in ch)))


def serve_tcp(port, sink, hold):
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        srv.bind(('0.0.0.0', port))
    except OSError as exc:
        sink.rec(event='tcp_bind_failed', port=port, error=str(exc))
        return
    srv.listen(32)
    sink.rec(event='tcp_listen', port=port)
    while True:
        try:
            conn, addr = srv.accept()
        except OSError as exc:
            sink.rec(event='tcp_accept_error', port=port, error=str(exc))
            return
        threading.Thread(target=_handle, args=(conn, addr, port, sink, hold),
                         daemon=True).start()


def _handle(conn, addr, port, sink, hold):
    peer = '%s:%d' % addr
    sink.rec(event='tcp_accept', port=port, peer=peer)
    try:
        conn.settimeout(hold)
        buf = b''
        deadline = time.time() + hold
        while time.time() < deadline:
            try:
                chunk = conn.recv(4096)
            except socket.timeout:
                break
            if not chunk:
                break
            buf += chunk
            sink.rec(event='tcp_data', port=port, peer=peer, len=len(chunk))
            if len(buf) > 65536:
                break
        if buf:
            sink.dump('TCP :%d' % port, peer, buf[:4096])
            sink.rec(event='tcp_closed', port=port, peer=peer, total=len(buf))
            # Optionally answer with a zero-ACK so the client does not hang.
            try:
                conn.sendall(b'')
            except OSError:
                pass
    except Exception as exc:  # noqa: BLE001
        sink.rec(event='tcp_error', port=port, peer=peer, error=repr(exc))
    finally:
        try:
            conn.close()
        except OSError:
            pass


def serve_udp(port, sink):
    srv = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        srv.bind(('0.0.0.0', port))
    except OSError as exc:
        sink.rec(event='udp_bind_failed', port=port, error=str(exc))
        return
    sink.rec(event='udp_listen', port=port)
    while True:
        try:
            data, addr = srv.recvfrom(65535)
        except OSError as exc:
            sink.rec(event='udp_recv_error', port=port, error=str(exc))
            return
        peer = '%s:%d' % addr
        sink.rec(event='udp_data', port=port, peer=peer, len=len(data),
                 head=data[:48].hex(' '))
        sink.dump('UDP :%d' % port, peer, data[:4096])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tcp', default='18443,18000,18001,18080,18081,14309,12331,17272,11009')
    ap.add_argument('--udp', default='18000,18081,12331')
    ap.add_argument('--hold', type=float, default=45.0)
    ap.add_argument('--log', default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                  'logs', 'ports.jsonl'))
    ap.add_argument('--out', default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                  'logs', 'ports_dump.txt'))
    args = ap.parse_args()

    sink = Sink(args.log, args.out)
    sink.rec(event='sink_start', tcp=args.tcp, udp=args.udp)
    for p in args.tcp.split(','):
        p = p.strip()
        if p:
            threading.Thread(target=serve_tcp, args=(int(p), sink, args.hold),
                             daemon=True).start()
    for p in args.udp.split(','):
        p = p.strip()
        if p:
            threading.Thread(target=serve_udp, args=(int(p), sink), daemon=True).start()
    try:
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        sink.rec(event='sink_stop')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
