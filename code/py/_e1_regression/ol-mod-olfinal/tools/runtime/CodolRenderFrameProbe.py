#!/usr/bin/env python3
"""READ-ONLY: confirm the render-frame hook site before anything patches it.

The chain established by CodolRenderThreadProbe / …Probe2:

    thread 43208  StartAddress 0x67C6A0 -> ... -> sub_BE21F0   (one per frame)
                    sub_BE21F0 + 0x1E : call sub_BE2150        <- the hook site
                                          sub_BE2150 calls BeginScene
    thread 16016  Com_Frame 0x4FEA20                            (one per frame)

so the render frame runs on a DIFFERENT thread from Com_Frame, and ol-mod's
existing frame hook cannot drive a Direct3D call. `0xBE220E` is a five-byte
`call rel32`, which is the shape ClientAnimtreeHook already replaces safely: the
bytes are verified before anything is written, and the replacement calls the
original.

Three things have to hold before that patch is worth writing, and all three are
readable:

  1. the site really is E8 rel32, and its target really is sub_BE2150;
  2. sub_BE21F0 runs on the same thread as the device calls, once per frame;
  3. the fiber context there is already the one sub_BE7470 switches to.

(3) matters because sub_BE7470 opens with `sub_67C170(1, sub_BE0900)`, a fiber
switch that returns immediately when the caller is ALREADY on context 1 and
otherwise yields until the scheduler grants it. Reading the current context id
from the same TLS slot sub_67C170 reads says which of those happens.
"""
import sys
import time
import argparse

from CodolFridaRuntime import configure_frida_runtime

configure_frida_runtime()
import frida


AGENT = r"""
'use strict';
const RENDER_FRAME = 0xBE21F0;   // one call per rendered frame, on the device thread
const CALL_SITE    = 0xBE220E;   // call sub_BE2150, five bytes
const CALL_TARGET  = 0xBE2150;
const COM_FRAME    = 0x4FEA20;
const UPLOAD       = 0xBE7470;

let samples = [];
let counts = {};

// sub_67C170 reads the current fiber context as
//     *(DWORD *)(*(DWORD *)(TEB->ThreadLocalStoragePointer) + 8)
// This mirrors that read exactly, from x86 fs:[0x2C].
function currentContext() {
    try {
        const tlsArray = ptr(Process.getCurrentThreadId()); // placeholder, replaced below
        return null;
    } catch (e) { return null; }
}

rpc.exports.inspect = function () {
    const out = {};
    const site = ptr(CALL_SITE);
    let bytes = [];
    for (let i = 0; i < 5; i++) bytes.push(site.add(i).readU8());
    out.bytes = bytes.map(b => b.toString(16).padStart(2, '0')).join(' ');
    out.isCall = bytes[0] === 0xE8;
    if (out.isCall) {
        const rel = site.add(1).readS32();
        out.target = '0x' + site.add(5).add(rel).toString(16).replace('0x', '');
        out.targetMatches = site.add(5).add(rel).equals(ptr(CALL_TARGET));
    }
    return out;
};

rpc.exports.start = function () {
    const out = {};
    [['renderFrame', RENDER_FRAME], ['comFrame', COM_FRAME], ['upload', UPLOAD]].forEach(function (e) {
        Interceptor.attach(ptr(e[1]), {
            onEnter: function (args) {
                const t = Process.getCurrentThreadId();
                const key = e[0] + ':' + t;
                counts[key] = (counts[key] || 0) + 1;
                if (e[0] === 'renderFrame' && samples.length < 3) {
                    const rec = { thread: t };
                    try {
                        // TEB->ThreadLocalStoragePointer is at fs:[0x2C] on x86.
                        const tlsPtr = ptr(Memory.queryAccess ? 0 : 0);
                        const teb = Process.getCurrentThreadId();
                        rec.note = 'context read below';
                    } catch (err) { rec.err = '' + err; }
                    samples.push(rec);
                }
            }
        });
    });
    return out;
};

// The fiber context has to be read with real code, because Frida's JS cannot
// touch fs:[0x2C]. A tiny stub does it: eax = *(*(DWORD*)fs:[0x2C]) + 8.
rpc.exports.contextReader = function () {
    const size = Process.pageSize;
    const code = Memory.alloc(size);
    Memory.protect(code, size, 'rwx');
    code.writeByteArray([
        0x64, 0xA1, 0x2C, 0x00, 0x00, 0x00,   // mov eax, fs:[0x2C]
        0x85, 0xC0,                           // test eax, eax
        0x74, 0x0A,                           // jz  fail
        0x8B, 0x00,                           // mov eax, [eax]
        0x85, 0xC0,                           // test eax, eax
        0x74, 0x04,                           // jz  fail
        0x8B, 0x40, 0x08,                     // mov eax, [eax+8]
        0xC3,                                 // ret
        0x83, 0xC8, 0xFF,                     // fail: or eax, -1
        0xC3                                  // ret
    ]);
    return code.toString();
};

rpc.exports.startWithContext = function (readerAddr) {
    const reader = new NativeFunction(ptr(readerAddr), 'uint32', []);
    [['renderFrame', RENDER_FRAME], ['comFrame', COM_FRAME], ['upload', UPLOAD]].forEach(function (e) {
        Interceptor.attach(ptr(e[1]), {
            onEnter: function () {
                const t = Process.getCurrentThreadId();
                const key = e[0] + ':' + t;
                counts[key] = (counts[key] || 0) + 1;
                if (samples.length < 8) {
                    let ctx = null;
                    try { ctx = reader(); } catch (err) { ctx = -1; }
                    samples.push({ what: e[0], thread: t, context: ctx });
                }
            }
        });
    });
    return true;
};

rpc.exports.collect = function () {
    Interceptor.detachAll();
    return { counts: counts, samples: samples };
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

    site = script.exports_sync.inspect()
    print()
    print("hook site 0xBE220E   bytes: %s" % site["bytes"])
    print("  E8 rel32:            %s" % site["isCall"])
    print("  target:              %s   matches sub_BE2150: %s"
          % (site.get("target"), site.get("targetMatches")))

    reader = script.exports_sync.context_reader()
    print("  fiber-context stub:  %s" % reader)
    script.exports_sync.start_with_context(reader)
    print("sampling %.1fs ..." % a.seconds)
    time.sleep(a.seconds)
    r = script.exports_sync.collect()
    session.detach()

    print()
    for key, n in sorted(r["counts"].items(), key=lambda kv: -kv[1]):
        what, tid = key.rsplit(":", 1)
        print("  %-14s thread %-8s %d calls" % (what, tid, n))
    print()
    print("fiber context at each entry (sub_67C170 switches to context 1):")
    for s in r["samples"]:
        print("  %-14s thread %-8s context %s" % (s["what"], s["thread"], s["context"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
