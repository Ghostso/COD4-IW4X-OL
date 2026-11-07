#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Hook the lobby frame codec in codoMP_client_shipRetail.exe.

Targets (image base 0x400000):
  0xBA20A0  RX: parse one lobby frame, then rebuild a 5-bit record
  0xBA4080  connect/start step ([req+0xC8]=1)
  0xBA4127  the only writer of [req+0xC8]=2
  0xBA21E4  the frame is rebuilt here -> dump [req+0xA8/B0/B4]
  0xBA0FF0  consumer of the parsed payload
  0x7F3800  lobby stage entry (result decides DW_LOBBY_CONNECTED)

Reads: [req+0xA8] type byte, [req+0xB0] bit reader, [req+0xB4] result
object and its first 0x80 bytes, [req+0xB8]/[req+0xBC] TX queue.

Usage (through the elevated agent):
  python -X utf8 CODOLServer/_mainline/frida_lobby_codec.py \\
      --exe "COD OL/codoMP_client_shipRetail.exe" \\
      --cwd run_codol_001/sandbox_ifs1_20260923 --seconds 70
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

import frida

IMAGE_BASE = 0x400000

JS = r"""
'use strict';
const BASE = 0x400000;
function va(x) { return ptr(x - BASE).add(Process.mainModule.base); }
function u32(p) { try { return p.readU32(); } catch (e) { return null; } }
function hex(p, n) {
  try { return buf2hex(p.readByteArray(n)); } catch (e) { return null; }
}
function buf2hex(ab) {
  if (!ab) return null;
  const b = new Uint8Array(ab); let s = '';
  for (let i = 0; i < b.length; i++)
    s += (b[i] < 16 ? '0' : '') + b[i].toString(16);
  return s;
}
function dump(tag, req) {
  if (!req || req.equals(ptr(0))) return;
  let o = { tag: tag, req: req.toString() };
  o.a8 = u32(req.add(0xa8));
  o.c8 = u32(req.add(0xc8));
  o.c4 = u32(req.add(0xc4));
  o.ac = u32(req.add(0xac));      // frame length from the u32 prefix
  o['644'] = u32(req.add(0x644));
  o['5e8'] = u32(req.add(0x5e8));
  const b0 = req.add(0xb0).readPointer();
  o.b0 = b0.toString();
  if (!b0.equals(ptr(0))) {
    o.rd_c  = u32(b0.add(0xc));
    o.rd_10 = u32(b0.add(0x10));
    o.rd_1c = u32(b0.add(0x1c));
    o.rd_24 = u32(b0.add(0x24));
  }
  const b4 = req.add(0xb4).readPointer();
  o.b4 = b4.toString();
  if (!b4.equals(ptr(0))) {
    o.b4_dump = hex(b4, 0x80);
    o.b4_obj = [u32(b4), u32(b4.add(4)), u32(b4.add(8)), u32(b4.add(0xc)),
                u32(b4.add(0x10)), u32(b4.add(0x14))];
  }
  o.b8 = req.add(0xb8).readPointer().toString();
  o.bc = u32(req.add(0xbc));
  send(o);
}

const H = [
  { a: 0xBA20A0, n: 'RX_parse',       mode: 'both' },
  { a: 0xBA21E4, n: 'RX_rebuild',     mode: 'enter' },
  { a: 0xBA4080, n: 'connect_start',  mode: 'both' },
  { a: 0xBA4127, n: 'C8_set2',        mode: 'enter' },
  { a: 0xBA0FF0, n: 'payload_consume',mode: 'enter' },
  { a: 0x7F3800, n: 'lobby_stage',    mode: 'both' }
];

for (const h of H) {
  try {
    Interceptor.attach(va(h.a), {
      onEnter: function () {
        if (h.mode === 'leave') return;
        this.req = this.context.ecx;
        send({ tag: h.n, phase: 'enter', ecx: this.context.ecx.toString() });
        dump(h.n + ':enter', this.context.ecx);
        if (this.context.edx)
          send({ tag: h.n, phase: 'edx', v: this.context.edx.toString() });
      },
      onLeave: function (ret) {
        if (h.mode === 'enter') return;
        send({ tag: h.n, phase: 'leave', ret: ret.toString(),
               ret32: ret.toInt32() });
        dump(h.n + ':leave', this.req);
      }
    });
    send({ tag: 'hooked', at: h.a.toString(16), name: h.n });
  } catch (e) {
    send({ tag: 'hook_fail', at: h.a.toString(16), name: h.n,
           err: String(e) });
  }
}
send({ tag: 'ready' });
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--exe", default=r"COD OL\codoMP_client_shipRetail.exe")
    ap.add_argument("--cwd", default="run_codol_001/sandbox_ifs1_20260923")
    ap.add_argument("--seconds", type=float, default=70.0)
    ap.add_argument("--log", default="")
    a = ap.parse_args()

    exe = os.path.abspath(a.exe)
    cwd = os.path.abspath(a.cwd)
    if not os.path.isfile(exe):
        print("missing exe:", exe)
        return 2

    dev = frida.get_local_device()
    pid = dev.spawn([exe], cwd=cwd)
    print("spawned", pid, flush=True)
    ses = dev.attach(pid)
    script = ses.create_script(JS)
    fh = open(a.log, "a", encoding="utf-8") if a.log else None

    def on_msg(m, data):
        line = json.dumps(m, ensure_ascii=False)
        print(line, flush=True)
        if fh:
            fh.write(line + "\n")
            fh.flush()

    script.on("message", on_msg)
    # ACE reaps the process if it stays suspended while the script loads, so
    # resume first and attach the interceptor immediately afterwards.  The
    # lobby codec is not reached until ~36 s in, so a few tens of milliseconds
    # of delay here is harmless.
    dev.resume(pid)
    print("resumed", pid, flush=True)
    time.sleep(0.05)
    script.load()
    print("script loaded", flush=True)

    deadline = time.time() + a.seconds
    while time.time() < deadline:
        time.sleep(0.5)
    try:
        dev.kill(pid)
    except Exception:
        pass
    if fh:
        fh.close()
    print("done", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
