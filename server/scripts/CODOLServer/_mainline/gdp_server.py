#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gdp_server.py -- first-pass CODOL GDP server skeleton.

Uses the local GDPOpenProtocol.tdr schema as the authority:
  GDPPkg     = GDPPkgHead + GDPPkgBody
  GDPPkgHead = Version + CmdID + CmdType + headlen + bodylen + SubCmdId
  CODOL body = TGDPCODOLMainCmdHead(Version + SubCmd + BodyLen) + body

The exact integer widths are not yet proven, so the parser logs several
plausible header layouts and keeps the raw bytes. Requests are answered with a
synthetic response so the client can be observed.
"""

import argparse
import csv
import json
import os
import socket
import struct
import sys
import threading
import time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import suspend_host_redirect as S  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
CMD_MAP = os.path.join(HERE, '..', 'GDP_CMD_MAP.csv')

GDP_CMD_TDR_HELLO = 0x01
GDP_CMD_CODOL_COMMAND = 0x06
CMDTYPE = {0: 'NOTIFY', 1: 'TIMEOUT', 2: 'REQUEST', 3: 'RESPONSE'}


def load_cmd_map():
    names = {}
    try:
        for row in csv.DictReader(open(CMD_MAP, encoding='utf-8')):
            if row['name'].startswith('GDP_CF_'):
                names[int(row['enum'], 16)] = row['name']
    except Exception:
        pass
    return names


CMD_NAMES = load_cmd_map()


def parse_layouts(data):
    """Return candidate header interpretations for logging."""
    out = []
    if len(data) < 8:
        return out
    # candidate A: all fields u8/u8/u8/u16/u16/u16 (LE)
    if len(data) >= 9:
        v, cid, ctype, hlen, blen, sub = struct.unpack_from('<BBBHHH', data, 0)
        out.append({'layout': 'A', 'version': v, 'cmd': cid,
                    'cmd_name': CMD_NAMES.get(cid, ''),
                    'cmd_type': CMDTYPE.get(ctype, ctype),
                    'headlen': hlen, 'bodylen': blen, 'sub': sub})
    # candidate B: u16 fields
    if len(data) >= 12:
        v, cid, ctype, hlen, blen, sub = struct.unpack_from('<HHHHHH', data, 0)
        out.append({'layout': 'B', 'version': v, 'cmd': cid,
                    'cmd_name': CMD_NAMES.get(cid, ''),
                    'cmd_type': CMDTYPE.get(ctype, ctype),
                    'headlen': hlen, 'bodylen': blen, 'sub': sub})
    # candidate C: version u16, cmd u16, type u16, headlen u32, bodylen u32
    if len(data) >= 14:
        v, cid, ctype, hlen, blen = struct.unpack_from('<HHHII', data, 0)
        out.append({'layout': 'C', 'version': v, 'cmd': cid,
                    'cmd_name': CMD_NAMES.get(cid, ''),
                    'cmd_type': CMDTYPE.get(ctype, ctype),
                    'headlen': hlen, 'bodylen': blen})
    # candidate D: CODOL subheader at offset 0
    if len(data) >= 6:
        v, sub, blen = struct.unpack_from('<HHH', data, 0)
        out.append({'layout': 'CODOL', 'version': v, 'sub': sub,
                    'sub_name': CMD_NAMES.get(sub, ''), 'bodylen': blen})
    return out


def build_response(req):
    """Return a synthetic RESPONSE with command type flipped."""
    if not req:
        return b''
    # Try layout A first: keep the same header shape, flip CmdType to RESPONSE.
    if len(req) >= 9:
        out = bytearray(req)
        out[2] = 3  # CMDTYPE_RESPONSE
        return bytes(out)
    return bytes(req)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--ports', default='8000,8081,3074,10009')
    ap.add_argument('--seconds', type=float, default=300.0)
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    trace = open(os.path.join(args.out, 'gdp_server.jsonl'), 'w',
                 encoding='utf-8')

    def emit(obj):
        trace.write(json.dumps(obj, ensure_ascii=False) + '\n')
        trace.flush()
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
            emit({'proto': 'udp', 'port': port, 'peer': list(addr),
                  'len': len(data), 'data_hex': data.hex(),
                  'parsed': parse_layouts(data)})
            if data:
                try:
                    if data[:2] == b'ur':
                        resp = S.build_tqos_response(data, 3, 8000)
                        s.sendto(resp, addr)
                        emit({'proto': 'udp', 'port': port,
                              'sent_tqos': len(resp)})
                    else:
                        s.sendto(build_response(data), addr)
                except Exception:
                    pass
        s.close()

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
                data = conn.recv(16384)
                emit({'proto': 'tcp', 'port': port, 'peer': list(addr),
                      'len': len(data), 'data_hex': data.hex(),
                      'parsed': parse_layouts(data)})
                conn.sendall(b'HTTP/1.1 200 OK\r\nContent-Length: 0\r\n\r\n')
            except Exception:
                pass
            try:
                conn.close()
            except Exception:
                pass
        s.close()

    for p in ports:
        threading.Thread(target=udp_loop, args=(p,), daemon=True).start()
        threading.Thread(target=tcp_loop, args=(p,), daemon=True).start()
    emit({'event': 'listening', 'ports': ports,
          'cmd_map_size': len(CMD_NAMES)})
    t0 = time.time()
    while time.time() - t0 < args.seconds:
        time.sleep(1)
    stop.set()
    time.sleep(1)
    trace.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
