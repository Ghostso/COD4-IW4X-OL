#!/usr/bin/env python3
"""READ-ONLY: which thread owns the Direct3D device, and is it Com_Frame's?

The device is created without D3DCREATE_MULTITHREADED (BehaviorFlags 0x42 -
FPU_PRESERVE | HARDWARE_VERTEXPROCESSING; see CodolRenderDeviceProbe.py), so
every call on it has to come from the thread that made it. An image upload
therefore cannot be driven from an injected thread; it has to ride a callback
the engine already runs on the right thread.

ol-mod installs a frame hook on Com_Frame (RVA 0x0FEA20), so the question is
exactly: does Com_Frame run on the same thread that calls IDirect3DDevice9::
Present? Present must be on the device thread or the client would not render, so
whichever thread calls it IS the device thread - no inference needed.

This attaches to both for a few seconds, counts calls per thread id, and detaches.
It writes nothing and changes no behaviour; both handlers only read
GetCurrentThreadId.
"""
import sys
import time
import argparse
from collections import Counter

from CodolFridaRuntime import configure_frida_runtime

configure_frida_runtime()
import frida


AGENT = r"""
'use strict';
const DEVICE_PTR = ptr(0x11C0E8C);
const COM_FRAME_RVA = 0x0FEA20;

const present = {};
const comFrame = {};

// IDirect3DDevice9 vtable indices. Every one of these has to run on the thread
// that created the device; whichever thread the engine calls them from IS that
// thread. Several are probed because a minimised or occluded client stops
// calling some of them.
const METHODS = [
    ['TestCooperativeLevel', 3],
    ['Present', 17],
    ['BeginScene', 41],
    ['EndScene', 42],
    ['Clear', 43],
    ['SetRenderTarget', 37],
];

rpc.exports.start = function () {
    const out = {};
    const base = Process.findModuleByName('out.exe').base;
    out.base = base.toString();

    const dev = DEVICE_PTR.readPointer();
    if (dev.isNull()) { out.error = 'no device'; return out; }
    const vt = dev.readPointer();
    out.comFrame = base.add(COM_FRAME_RVA).toString();
    out.methods = {};

    METHODS.forEach(function (m) {
        const nm = m[0];
        const addr = vt.add(4 * m[1]).readPointer();
        out.methods[nm] = addr.toString();
        Interceptor.attach(addr, {
            onEnter: function () {
                const t = Process.getCurrentThreadId();
                const key = nm + ':' + t;
                present[key] = (present[key] || 0) + 1;
            }
        });
    });
    Interceptor.attach(base.add(COM_FRAME_RVA), {
        onEnter: function () {
            const t = Process.getCurrentThreadId();
            comFrame[t] = (comFrame[t] || 0) + 1;
        }
    });
    return out;
};

rpc.exports.collect = function () {
    Interceptor.detachAll();
    return { present: present, comFrame: comFrame };
};
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pid", type=int)
    ap.add_argument("--seconds", type=float, default=4.0)
    a = ap.parse_args()

    device = frida.get_local_device()
    procs = [q for q in device.enumerate_processes() if q.name.lower() == "out.exe"]
    pid = a.pid or (procs[0].pid if procs else None)
    if pid is None:
        print("no client process found")
        return 2
    print("clients:", [(p.pid, p.name) for p in procs], "-> using", pid)

    session = device.attach(pid)
    script = session.create_script(AGENT)
    script.load()
    started = script.exports_sync.start()
    if "error" in started:
        print("start failed:", started["error"])
        return 1
    for nm, addr in started["methods"].items():
        print("  %-22s %s" % (nm, addr))
    print("  %-22s %s" % ("Com_Frame", started["comFrame"]))
    print("sampling %.1fs ..." % a.seconds)
    time.sleep(a.seconds)
    r = script.exports_sync.collect()
    session.detach()

    frame = {int(k): v for k, v in r["comFrame"].items()}
    present = {}
    print()
    if not r["present"]:
        print("no device calls seen at all - the client may be minimised or idle")
        return 1
    for key, n in sorted(r["present"].items(), key=lambda kv: -kv[1]):
        nm, tid = key.rsplit(":", 1)
        print("  %-22s thread %-8s %d calls" % (nm, tid, n))
        present[int(tid)] = present.get(int(tid), 0) + n
    print()
    print("Com_Frame calls by thread: %s" % dict(Counter(frame).most_common()))
    if not frame:
        print("no Com_Frame calls seen")
        return 1
    pt = set(present)
    ft = set(frame)
    print()
    if pt == ft and len(pt) == 1:
        print("SAME THREAD (%d): a Com_Frame callback may call the device directly."
              % next(iter(pt)))
        return 0
    print("DIFFERENT THREADS: device calls on %s, Com_Frame on %s."
          " A Com_Frame callback that touches the device would be off-thread."
          % (sorted(pt), sorted(ft)))
    return 1


if __name__ == "__main__":
    sys.exit(main())
