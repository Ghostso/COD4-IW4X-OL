#!/usr/bin/env python3
"""READ-ONLY: locate the engine function that owns the render thread.

CodolRenderThreadProbe established that the device is not MULTITHREADED and that
its calls come from a thread that is NOT the one running Com_Frame - so ol-mod's
existing frame hook is the wrong place to drive an image upload, and the right
place is whatever the render thread itself runs every frame.

This takes a backtrace from inside BeginScene (which by definition is on the
device thread) and maps every out.exe return address to an RVA, so the render
loop can be read in IDA and hooked the same way Com_Frame is. It also samples
which thread calls the image entry points, in case an image happens to load
during the window.

Attaches, samples, detaches. Nothing is written.
"""
import sys
import time
import argparse

from CodolFridaRuntime import configure_frida_runtime

configure_frida_runtime()
import frida


AGENT = r"""
'use strict';
const DEVICE_PTR = ptr(0x11C0E8C);

let stacks = [];
let imageCalls = [];
let want = 0;

function frames(ctx, base, size) {
    return Thread.backtrace(ctx, Backtracer.ACCURATE).map(function (a) {
        const off = a.sub(base);
        const n = off.toUInt32();
        if (!a.compare(base) < 0 && n < size) {
            return { rva: '0x' + n.toString(16), file: '0x' + (n + 0x400000).toString(16) };
        }
        const m = Process.findModuleByAddress(a);
        return { module: m ? m.name : '?', at: a.toString() };
    });
}

rpc.exports.start = function (samples) {
    const out = {};
    want = samples;
    const mod = Process.findModuleByName('out.exe');
    const base = mod.base, size = mod.size;
    out.base = base.toString();
    out.size = size;

    const dev = DEVICE_PTR.readPointer();
    const vt = dev.readPointer();
    const beginScene = vt.add(4 * 41).readPointer();
    out.beginScene = beginScene.toString();

    Interceptor.attach(beginScene, {
        onEnter: function () {
            if (stacks.length >= want) return;
            stacks.push({
                thread: Process.getCurrentThreadId(),
                frames: frames(this.context, base, size),
            });
        }
    });

    // The image entry points, to catch the thread a real load runs on.
    [['sub_BE7470 upload', 0x7E7470],
     ['sub_BE6F40 CreateTexture2D', 0x7E6F40],
     ['sub_487380 Load_GfxImage', 0x87380],
     ['sub_C204B0 streamed', 0x8204B0]].forEach(function (e) {
        try {
            Interceptor.attach(base.add(e[1]), {
                onEnter: function () {
                    if (imageCalls.length >= 64) return;
                    imageCalls.push({ what: e[0], thread: Process.getCurrentThreadId() });
                }
            });
        } catch (err) { }
    });
    return out;
};

rpc.exports.collect = function () {
    Interceptor.detachAll();
    return { stacks: stacks, imageCalls: imageCalls };
};
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pid", type=int)
    ap.add_argument("--seconds", type=float, default=5.0)
    ap.add_argument("--samples", type=int, default=2)
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
    started = script.exports_sync.start(a.samples)
    print("out.exe base %s size 0x%x   BeginScene %s"
          % (started["base"], started["size"], started["beginScene"]))
    time.sleep(a.seconds)
    r = script.exports_sync.collect()
    session.detach()

    for i, st in enumerate(r["stacks"]):
        print()
        print("backtrace %d  (thread %d)" % (i, st["thread"]))
        for f in st["frames"]:
            if "rva" in f:
                print("    out.exe  rva %-10s  ida %s" % (f["rva"], f["file"]))
            else:
                print("    %-10s %s" % (f["module"], f["at"]))
    print()
    if r["imageCalls"]:
        seen = {}
        for c in r["imageCalls"]:
            seen.setdefault(c["what"], {}).setdefault(c["thread"], 0)
            seen[c["what"]][c["thread"]] += 1
        print("image entry points seen:")
        for what, threads in seen.items():
            print("   %-28s %s" % (what, threads))
    else:
        print("no image entry points hit in the window (nothing loaded an image)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
