"""Hook the /auth/ response parser branches to see which one writes 735.

0xB9A470 parses the auth reply.  It has two places that set 0x2DF (735):
    0xB9A59B  auth_task validator rejected
    0xB9A7C7  ticket/tag path rejected
Memory sampling cannot distinguish them (the compared value lives in a
stack local), so hook the instruction instead and log the registers.

Usage (through the elevated agent):
    python -X utf8 CODOLServer/_mainline/frida_auth_branch.py \
        --cwd run_codol_001/sandbox_ifs1_20260923 --seconds 60
"""
import argparse
import json
import os
import sys
import time

import frida

IMAGE_BASE = 0x400000

JS = r"""
const BASE = 0x400000;
function addr(va) { return ptr(va - BASE).add(Process.mainModule.base); }

const targets = [
  {va: 0xB9A470, name: 'parse_entry'},
  {va: 0xB9A59B, name: 'set735_auth_task_validator'},
  {va: 0xB9A796, name: 'compare_ticket_tag'},
  {va: 0xB9A7C7, name: 'set735_ticket_path'},
  {va: 0xB9A809, name: 'compare_obj_d8'},
  {va: 0xB9A917, name: 'code_mismatch_path'},
];

for (const t of targets) {
  try {
    Interceptor.attach(addr(t.va), {
      onEnter: function () {
        const ctx = this.context;
        const rec = {
          kind: 'auth_branch',
          site: t.name,
          va: '0x' + t.va.toString(16),
          eax: ctx.eax.toString(),
          ecx: ctx.ecx.toString(),
          edx: ctx.edx.toString(),
          ebx: ctx.ebx.toString(),
          esi: ctx.esi.toString(),
          edi: ctx.edi.toString(),
        };
        try {
          rec.esi_18 = ctx.esi.add(0x18).readU32().toString();
          rec.esi_30 = ctx.esi.add(0x30).readU32().toString();
          rec.esi_d8 = ctx.esi.add(0xd8).readU32().toString();
        } catch (e) { rec.read_error = String(e); }
        send(rec);
      }
    });
    send({kind: 'hook_ok', site: t.name});
  } catch (e) {
    send({kind: 'hook_error', site: t.name, error: String(e)});
  }
}
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cwd", required=True)
    ap.add_argument("--seconds", type=float, default=60.0)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    gd = os.path.abspath(a.cwd)
    exe = os.path.join(gd, "codoMP_client_shipRetail.exe")
    if not os.path.exists(exe):
        print("missing exe: " + exe, file=sys.stderr)
        return 2

    out = open(a.out or os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                     "frida_auth_branch.jsonl"),
               "w", encoding="utf-8")

    def emit(obj):
        line = json.dumps(obj, ensure_ascii=False)
        print(line, flush=True)
        out.write(line + "\n")
        out.flush()

    dev = frida.get_local_device()
    pid = dev.spawn([exe], cwd=gd)
    emit({"kind": "spawned", "pid": pid})
    session = dev.attach(pid)
    script = session.create_script(JS)
    script.on("message", lambda m, d: emit(m))
    script.load()
    dev.resume(pid)
    emit({"kind": "resumed"})
    t0 = time.time()
    while time.time() - t0 < a.seconds:
        time.sleep(0.5)
    emit({"kind": "done", "elapsed": round(time.time() - t0, 1)})
    out.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
