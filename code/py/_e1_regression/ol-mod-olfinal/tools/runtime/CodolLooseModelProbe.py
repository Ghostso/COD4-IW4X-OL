#!/usr/bin/env python3
"""Does the engine's loose-file search path actually find a model we dropped in?

A published XModel carries `lodInfo[0].modelSurfs = 0xFFFFFFFE` and a resource
name, so its mesh arrives through the `models/%s` loose channel rather than from a
zone. Copying a file into `main/models/` is only useful if that is the directory
the engine's search path resolves against - and a wrong directory is a SILENT
no-op until something tries to draw.

`sub_499EC0` is the loader: it formats `models/%s`, opens the file with
`sub_4F4D30`, and rejects it unless the first dword is 1 and the second equals
`dword_E1F84C0`. This probe stops at the open, which answers the search-path
question without allocating or registering anything:

    sub_4F4D30(const char *path, int *handleOut)   ->  handle > 0 on success
    sub_4F4870(int handle)                          ->  close

THREAD-GATED, and this is the trap. `sub_4F4D30` compares GetCurrentThreadId()
against three stored ids and, from any other thread, sets *handleOut = 0 and
returns -7. Called from an injected thread it reports NOT FOUND for a file that is
sitting right there. So the call rides the render-frame hook at sub_BE21F0, the
same door the image upload uses.

Two names are opened every run: the one being tested and a SHIPPED one as a
control. A run where the control also fails is a broken probe, not a missing file.
"""
import sys
import time
import argparse

from CodolFridaRuntime import configure_frida_runtime

configure_frida_runtime()
import frida


AGENT = r"""
'use strict';
const RENDER_FRAME = ptr(0xBE21F0);
const OPEN_RVA  = 0x0F4D30;   // sub_4F4D30
const CLOSE_RVA = 0x0F4870;   // sub_4F4870
const READ_RVA  = 0x0F4F20;   // sub_4F4F20(buf, bytes, handle)
const VERSION_GLOBAL = ptr(0xE1F84C0);
const THREAD_IDS = [ptr(0x7886E68), ptr(0x7886E94), ptr(0x7886E6C)];

let state = null;

rpc.exports.start = function (names) {
    const base = Process.findModuleByName('out.exe').base;
    state = {
        open: new NativeFunction(base.add(OPEN_RVA), 'int32', ['pointer', 'pointer']),
        close: new NativeFunction(base.add(CLOSE_RVA), 'int32', ['int32']),
        read: new NativeFunction(base.add(READ_RVA), 'int32', ['pointer', 'uint32', 'int32']),
        names: names, results: null,
    };
    Interceptor.attach(RENDER_FRAME, {
        onEnter: function () {
            if (state.results !== null) return;
            const out = { thread: Process.getCurrentThreadId(), opens: [] };
            try {
                out.knownThreadIds = THREAD_IDS.map(function (p, i) {
                    // the third is a pointer TO the id; the first two hold it directly
                    try { return i === 2 ? p.readPointer().readU32() : p.readU32(); }
                    catch (e) { return null; }
                });
            } catch (e) {}
            try { out.expectedVersion = '0x' + VERSION_GLOBAL.readU32().toString(16); }
            catch (e) {}

            for (const n of state.names) {
                const rec = { name: n, path: 'models/' + n };
                try {
                    const path = Memory.allocUtf8String(rec.path);
                    const handleOut = Memory.alloc(4);
                    handleOut.writeU32(0);
                    rec.rc = state.open(path, handleOut);
                    rec.handle = handleOut.readU32();
                    rec.found = rec.handle > 0;
                    if (rec.found) {
                        // Read the 88-byte header sub_499EC0 validates, so the
                        // answer is "the engine can open AND accept it", not just
                        // "a file exists".
                        const buf = Memory.alloc(88);
                        rec.readBytes = state.read(buf, 88, rec.handle);
                        if (rec.readBytes === 88) {
                            rec.magic = '0x' + buf.readU32().toString(16);
                            rec.version = '0x' + buf.add(4).readU32().toString(16);
                        }
                        state.close(rec.handle);
                        rec.closed = true;
                    }
                } catch (e) { rec.error = '' + e; }
                out.opens.push(rec);
            }
            state.results = out;
        }
    });
    return { attached: true };
};

rpc.exports.collect = function () {
    Interceptor.detachAll();
    return state ? state.results : null;
};
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("name", nargs="+", help="resource names, without models/")
    ap.add_argument("--control", default="aa12ss_drone_110",
                    help="a shipped resource that must succeed")
    ap.add_argument("--pid", type=int)
    ap.add_argument("--seconds", type=float, default=6.0)
    a = ap.parse_args()

    device = frida.get_local_device()
    procs = [q for q in device.enumerate_processes() if q.name.lower() == "out.exe"]
    pid = a.pid or (procs[0].pid if procs else None)
    if pid is None:
        print("no client process found")
        return 2
    print("clients:", [(p.pid, p.name) for p in procs], "-> using", pid)

    names = [a.control] + list(a.name)
    session = device.attach(pid)
    script = session.create_script(AGENT)
    script.load()
    script.exports_sync.start(names)
    deadline = time.time() + a.seconds
    r = None
    while time.time() < deadline:
        time.sleep(0.2)
        r = script.exports_sync.collect()
        if r:
            break
    session.detach()

    if not r:
        print("the render frame never fired; nothing was opened")
        return 1
    print()
    # A successful open IS the proof the thread was accepted: sub_4F4D30 returns
    # -7 with a null handle from anything but its three known threads. The stored
    # ids are printed for context only, and the third is read through a pointer
    # that is not always resolvable.
    print("ran on thread %s; stored ids %s (the third is read indirectly)"
          % (r["thread"], r.get("knownThreadIds")))
    print("expected surfs version %s" % r.get("expectedVersion"))
    print()
    ok = True
    for rec in r["opens"]:
        tag = "control" if rec["name"] == a.control else "       "
        if rec.get("error"):
            print("  %s %-28s ERROR %s" % (tag, rec["name"], rec["error"]))
            ok = False
            continue
        line = ("  %s %-28s rc=%-4s handle=%-4s %s"
                % (tag, rec["name"], rec.get("rc"), rec.get("handle"),
                   "FOUND" if rec.get("found") else "NOT FOUND"))
        if rec.get("readBytes") == 88:
            accepted = (rec.get("magic") == "0x1" and
                        rec.get("version") == r.get("expectedVersion"))
            line += ("  magic=%s version=%s  %s"
                     % (rec.get("magic"), rec.get("version"),
                        "accepted" if accepted else "REJECTED by the version check"))
            if not accepted:
                ok = False
        if not rec.get("found"):
            ok = False
        print(line)
    control = next(x for x in r["opens"] if x["name"] == a.control)
    if not control.get("found"):
        print()
        print("the CONTROL failed, so this run says nothing about the others")
        return 2
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
