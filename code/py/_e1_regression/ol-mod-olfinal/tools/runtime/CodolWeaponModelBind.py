#!/usr/bin/env python3
"""Bind a published XModel to a weapon, so something finally asks for it.

Publishing an asset makes it findable. It does not make anything draw it. The
thing that asks for a weapon's mesh is its WeaponDef, and the two fields that name
it were not decoded in this tree - so they were found by what they point AT rather
than by transferring offsets from IW4 notes:

    build the address -> name map of every type-4 asset from the XAsset hash
    table, then scan a shipped WeaponDef's 4,124 bytes a dword at a time and
    report every offset that lands on one.

Across six weapons, four offsets held an XModel in all six:

    +16  0x10   viewModel     'viewmodel_trophy_system_bluing' on trophybluing_mp
    +24  0x18   worldModel    'mp_trophy_system_folded_bluing'
    +40  0x28   knife viewModel     'viewmodel_knife', identical in all 1,136
    +44  0x2c   knife worldModel    'weapon_parabolic_knife', identical in all
    +2656 0xa60 projectile model, in 3 of 6

873 of the 1,136 WeaponDefs carry `tag_origin` at +16 - CODOL composes most gun
meshes through the attachment system rather than from this field - so a binding has
to target one of the 263 that use it directly. `ump45ss_mp` is an SMG with real
`wea_ump45ss_ump45ss_blk_vmgun` / `..._blk` models in both slots, which makes it
the right class of analogue for a PPSh.

THIS WRITES TO THE CLIENT. Two dwords per slot pair, into fields that already hold
XModel pointers - the same values the zone loader puts there. The original
pointers are saved to a JSON file first and `--restore` puts them back exactly, so
the change is undoable without a restart. Nothing is written without --bind.

Every published asset is process-local: this binds in ONE client, and a restart
loses it.
"""
import sys
import json
import argparse
import pathlib

from CodolFridaRuntime import configure_frida_runtime

configure_frida_runtime()
import frida


AGENT = r"""
'use strict';
const ENTRIES = ptr(0x239B120);
const HEADS   = ptr(0x1E2D338);
const THUNKS  = ptr(0xE5C8C0);
const STRIDE  = 28;

const OFF_VIEW = 16, OFF_WORLD = 24, OFF_KNIFE_VIEW = 40, OFF_KNIFE_WORLD = 44;

function nameOffsetFor(type) {
    try {
        const fn = THUNKS.add(4 * type).readPointer().toUInt32();
        if (fn === 0x483390) return 0;
        if (fn === 0x4833A0) return 16;
        if (fn === 0x4833C0) return 48;
        return -1;
    } catch (e) { return -1; }
}

function hashName(type, name) {
    let h = type >>> 0;
    for (let i = 0; i < name.length; i++) {
        let c = name.charCodeAt(i);
        if (c >= 65 && c <= 90) c += 32;
        if (c === 92) c = 47;
        h = (Math.imul(31, h) + c) >>> 0;
    }
    return h % 0x1D4C0;
}

function readName(header, off) {
    try {
        const p = header.add(off).readPointer();
        if (p.isNull()) return null;
        let s = '';
        for (let i = 0; i < 128; i++) {
            const c = p.add(i).readU8();
            if (c === 0) return s.length ? s : null;
            if (c < 32 || c > 126) return null;
            s += String.fromCharCode(c);
        }
        return null;
    } catch (e) { return null; }
}

function findAsset(type, name) {
    const off = nameOffsetFor(type);
    if (off < 0) return NULL;
    let i;
    try { i = HEADS.add(4 * hashName(type, name)).readU32(); } catch (e) { return NULL; }
    for (let steps = 0; i !== 0 && steps < 4096; steps++) {
        const e = ENTRIES.add(STRIDE * i);
        let t, h, next;
        try { t = e.readU32(); h = e.add(8).readPointer(); next = e.add(20).readU32(); }
        catch (err) { return NULL; }
        if (t === type && !h.isNull()) {
            const f = readName(h, off);
            if (f !== null && f.toLowerCase() === name.toLowerCase()) return h;
        }
        i = next;
    }
    return NULL;
}

function modelName(p) {
    if (p.isNull()) return null;
    return readName(p, nameOffsetFor(4));
}

rpc.exports.inspect = function (weapon) {
    const w = findAsset(28, weapon);
    if (w.isNull()) return { error: "WeaponDef '" + weapon + "' is not in this client" };
    const slot = function (off) {
        const p = w.add(off).readPointer();
        return { offset: off, pointer: p.toString(), raw: p.toUInt32(), model: modelName(p) };
    };
    return {
        weapon: weapon, at: w.toString(),
        viewModel: slot(OFF_VIEW), worldModel: slot(OFF_WORLD),
        knifeView: slot(OFF_KNIFE_VIEW), knifeWorld: slot(OFF_KNIFE_WORLD),
    };
};

// Walks WeaponDef -> XModel -> Material -> GfxImage -> texture, so the answer is
// "the weapon reaches the port's art", not "a pointer was written".
rpc.exports.verify = function (weapon, offsets) {
    const w = findAsset(28, weapon);
    if (w.isNull()) return { error: 'weapon not found' };
    let refVtable = null;
    for (const n of [String.fromCharCode(36) + 'white', 'default', 'missing_fx']) {
        const img = findAsset(10, n);
        if (img.isNull()) continue;
        try {
            const tex = img.readPointer();
            if (!tex.isNull()) { refVtable = tex.readPointer().toString(); break; }
        } catch (e) {}
    }
    const out = { weapon: weapon, referenceVtable: refVtable, slots: [] };
    for (const off of offsets) {
        const model = w.add(off).readPointer();
        const rec = { offset: off, model: modelName(model), at: model.toString(),
                      surfaces: [] };
        if (model.isNull()) { rec.error = 'null'; out.slots.push(rec); continue; }
        try {
            const numsurfs = model.add(6).readU8();
            rec.numsurfs = numsurfs;
            rec.lodResource = readName(model, 72 + 12);
            rec.modelSurfs = '0x' + model.add(72 + 8).readU32().toString(16);
            const materials = model.add(68).readPointer();
            for (let i = 0; i < numsurfs; i++) {
                const mtl = materials.add(4 * i).readPointer();
                const srec = { surface: i, material: readName(mtl, 16), images: [] };
                const count = mtl.add(81).readU8();
                const table = mtl.add(92).readPointer();
                for (let k = 0; k < count && k < 16; k++) {
                    const img = table.add(12 * k).add(8).readPointer();
                    const irec = { image: readName(img, 48) };
                    try {
                        const tex = img.readPointer();
                        irec.hasTexture = !tex.isNull();
                        if (irec.hasTexture)
                            irec.vtableOk = tex.readPointer().toString() === refVtable;
                    } catch (e) { irec.hasTexture = false; }
                    srec.images.push(irec);
                }
                rec.surfaces.push(srec);
            }
        } catch (e) { rec.error = '' + e; }
        out.slots.push(rec);
    }
    return out;
};

// A model may be named OR given by address. Re-linking a name that already
// exists installs a fresh header but leaves the hash walk resolving to the old
// one, so after a zone transition the only way to reach the new data is its
// address - which DB_LinkXAssetEntry hands back at publish time.
function resolveModel(req) {
    if (req.address) {
        const p = ptr(req.address);
        return p.isNull() ? NULL : p;
    }
    return findAsset(4, req.model);
}

rpc.exports.bind = function (weapon, writes) {
    const w = findAsset(28, weapon);
    if (w.isNull()) return { error: 'weapon not found' };
    const out = { weapon: weapon, at: w.toString(), applied: [] };
    // Resolve every model BEFORE writing anything, so a missing one cannot leave
    // the WeaponDef half-patched.
    const resolved = [];
    for (const req of writes) {
        const m = resolveModel(req);
        if (m.isNull()) { out.error = "XModel '" + (req.model || req.address) + "' did not resolve"; return out; }
        resolved.push({ offset: req.offset, model: req.model, pointer: m });
    }
    for (const r of resolved) {
        const before = w.add(r.offset).readPointer();
        w.add(r.offset).writePointer(r.pointer);
        const after = w.add(r.offset).readPointer();
        out.applied.push({
            offset: r.offset, model: r.model,
            before: before.toString(), beforeModel: modelName(before),
            after: after.toString(), afterModel: modelName(after),
            ok: after.equals(r.pointer),
        });
    }
    return out;
};

// Every WeaponDef's knife pair, in one pass. +40/+44 are the only two model
// fields that are populated in ALL 1,136 of them, so this is the one binding that
// shows regardless of which weapon the player is holding.
rpc.exports.bindAllKnives = function (viewReq, worldReq) {
    const vm = resolveModel(viewReq), wm = resolveModel(worldReq);
    if (vm.isNull() || wm.isNull()) return { error: 'a model did not resolve' };
    const nameOff = nameOffsetFor(28);
    const out = { view: vm.toString(), world: wm.toString(), patched: [], skipped: [] };
    for (let b = 0; b < 0x1D4C0; b++) {
        let i;
        try { i = HEADS.add(4 * b).readU32(); } catch (e) { break; }
        let d = 0;
        while (i !== 0 && d < 64) {
            d++;
            const e = ENTRIES.add(STRIDE * i);
            let t, h;
            try { t = e.readU32(); h = e.add(8).readPointer(); } catch (err) { break; }
            if (t === 28 && !h.isNull()) {
                const wn = readName(h, nameOff);
                try {
                    const oldV = h.add(OFF_KNIFE_VIEW).readPointer();
                    const oldW = h.add(OFF_KNIFE_WORLD).readPointer();
                    // Only touch a slot that already holds a real XModel: a null
                    // or unreadable one is a weapon shaped differently, and
                    // writing into it would be inventing a field.
                    if (oldV.isNull() || oldW.isNull() || modelName(oldV) === null) {
                        out.skipped.push({ weapon: wn, why: 'slot is not a model' });
                    } else {
                        h.add(OFF_KNIFE_VIEW).writePointer(vm);
                        h.add(OFF_KNIFE_WORLD).writePointer(wm);
                        out.patched.push({ weapon: wn, at: h.toString(),
                                           view: oldV.toString(), world: oldW.toString() });
                    }
                } catch (err) { out.skipped.push({ weapon: wn, why: '' + err }); }
            }
            try { i = e.add(20).readU32(); } catch (err) { break; }
        }
    }
    return out;
};

rpc.exports.restoreAll = function (entries) {
    let ok = 0, bad = 0;
    for (const r of entries) {
        try {
            const h = ptr(r.at);
            h.add(OFF_KNIFE_VIEW).writePointer(ptr(r.view));
            h.add(OFF_KNIFE_WORLD).writePointer(ptr(r.world));
            ok++;
        } catch (e) { bad++; }
    }
    return { restored: ok, failed: bad };
};

rpc.exports.restore = function (weapon, writes) {
    const w = findAsset(28, weapon);
    if (w.isNull()) return { error: 'weapon not found' };
    const out = { weapon: weapon, restored: [] };
    for (const req of writes) {
        const target = ptr(req.pointer);
        const before = w.add(req.offset).readPointer();
        w.add(req.offset).writePointer(target);
        out.restored.push({
            offset: req.offset,
            from: before.toString(), fromModel: modelName(before),
            to: target.toString(), toModel: modelName(target),
            ok: w.add(req.offset).readPointer().equals(target),
        });
    }
    return out;
};
"""

OFF_VIEW, OFF_WORLD, OFF_KNIFE_VIEW, OFF_KNIFE_WORLD = 16, 24, 40, 44


_ATTACHED_PID = None


def pid_of(_session):
    return _ATTACHED_PID


def attach(pid_arg):
    global _ATTACHED_PID
    device = frida.get_local_device()
    procs = [q for q in device.enumerate_processes() if q.name.lower() == "out.exe"]
    pid = pid_arg or (procs[0].pid if procs else None)
    if pid is None:
        print("no client process found")
        return None, None
    print("clients:", [(p.pid, p.name) for p in procs], "-> using", pid)
    _ATTACHED_PID = pid
    session = device.attach(pid)
    script = session.create_script(AGENT)
    script.load()
    return session, script


def show_verify(v):
    if "error" in v:
        print("  verify failed:", v["error"])
        return False
    ok = True
    print("  reference texture vtable %s" % v["referenceVtable"])
    for slot in v["slots"]:
        print("  +%-3d %-16s %s  %s surfaces, resource=%r modelSurfs=%s"
              % (slot["offset"], slot.get("model"), slot["at"],
                 slot.get("numsurfs"), slot.get("lodResource"), slot.get("modelSurfs")))
        for s in slot.get("surfaces", []):
            imgs = ", ".join(
                "%s%s" % (i.get("image"), "" if i.get("vtableOk") else " [NO TEXTURE]")
                for i in s["images"])
            if any(not i.get("vtableOk") for i in s["images"]):
                ok = False
            print("        surface %d  %-22s %s" % (s["surface"], s["material"], imgs))
    return ok


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--weapon", default="ump45ss_mp")
    ap.add_argument("--view", default="vm_t4_ppsh1")
    ap.add_argument("--world", default="wm_t4_ppsh1")
    ap.add_argument("--knife", action="store_true",
                    help="also point the shared knife slots (+40/+44) at the model")
    ap.add_argument("--bind", action="store_true", help="actually write the pointers")
    ap.add_argument("--save", type=pathlib.Path,
                    default=pathlib.Path("weapon_model_bind_restore.json"))
    ap.add_argument("--restore", type=pathlib.Path,
                    help="undo a previous bind from its saved JSON")
    ap.add_argument("--view-addr", help="bind the view slot to this address instead of a name")
    ap.add_argument("--world-addr", help="bind the world slot to this address instead of a name")
    ap.add_argument("--all-knives", action="store_true",
                    help="point +40/+44 at the model on EVERY WeaponDef")
    ap.add_argument("--restore-all", type=pathlib.Path,
                    help="undo an --all-knives run from its saved JSON")
    ap.add_argument("--pid", type=int)
    a = ap.parse_args()

    def req(offset, name, addr):
        r = {"offset": offset, "model": name}
        if addr:
            r["address"] = addr
        return r

    session, script = attach(a.pid)
    if session is None:
        return 2

    if a.restore_all:
        saved = json.loads(a.restore_all.read_text(encoding="utf-8"))
        here = pid_of(session)
        if saved.get("pid") is not None and saved["pid"] != here:
            print("REFUSING: this file was saved from pid %s and the client is pid %s."
                  % (saved["pid"], here))
            print("Those are raw header addresses; they mean nothing in another "
                  "process. The old client is gone, so its bind went with it - "
                  "there is nothing to restore.")
            session.detach()
            return 2
        if saved.get("pid") is None:
            print("REFUSING: this file predates the pid check, so it cannot be "
                  "shown to belong to this client.")
            session.detach()
            return 2
        r = script.exports_sync.restore_all(saved["patched"])
        print("restored %d weapons, %d failed" % (r["restored"], r["failed"]))
        session.detach()
        return 0 if r["failed"] == 0 else 1

    if a.all_knives:
        view = req(OFF_KNIFE_VIEW, a.view, a.view_addr)
        world = req(OFF_KNIFE_WORLD, a.world, a.world_addr)
        if not a.bind:
            print()
            print("dry run; would point +40/+44 on EVERY WeaponDef at")
            print("   view  %s" % (a.view_addr or a.view))
            print("   world %s" % (a.world_addr or a.world))
            print("pass --bind to apply")
            session.detach()
            return 0
        r = script.exports_sync.bind_all_knives(view, world)
        if "error" in r:
            print("refused:", r["error"])
            session.detach()
            return 1
        # A restore file holds raw HEADER ADDRESSES. Applied to a different
        # process those addresses mean nothing, and writing them into 1,005
        # WeaponDefs would be worse than leaving the bind in place - so the file
        # carries the process it was taken from, and a restore checks it.
        r["pid"] = pid_of(session)
        a.save.write_text(json.dumps(r, indent=2), encoding="utf-8")
        print()
        print("knife slots pointed at view=%s world=%s" % (r["view"], r["world"]))
        print("   patched %d WeaponDefs, skipped %d" % (len(r["patched"]), len(r["skipped"])))
        for sk in r["skipped"][:6]:
            print("      skipped %-28s %s" % (sk.get("weapon"), sk.get("why")))
        # Every weapon shared the same two originals, so a single distinct pair
        # here is the signal that nothing unexpected was overwritten.
        pairs = {(x["view"], x["world"]) for x in r["patched"]}
        print("   distinct original pointer pairs replaced: %d %s"
              % (len(pairs), sorted(pairs)[:3]))
        print("   originals saved to %s" % a.save)
        print()
        print("chain from a sample weapon:")
        v = script.exports_sync.verify(r["patched"][0]["weapon"],
                                       [OFF_KNIFE_VIEW, OFF_KNIFE_WORLD])
        ok = show_verify(v)
        session.detach()
        print()
        print("bound and verified" if ok else "bound, but the chain has problems")
        print("undo:  python CodolWeaponModelBind.py --restore-all %s" % a.save)
        return 0 if ok else 1

    if a.restore:
        saved = json.loads(a.restore.read_text(encoding="utf-8"))
        here = pid_of(session)
        if saved.get("pid") not in (None, here):
            print("REFUSING: saved from pid %s, client is pid %s - the addresses "
                  "in it belong to a process that no longer exists."
                  % (saved["pid"], here))
            session.detach()
            return 2
        r = script.exports_sync.restore(saved["weapon"], saved["writes"])
        print(json.dumps(r, indent=2))
        session.detach()
        return 0 if "error" not in r else 1

    before = script.exports_sync.inspect(a.weapon)
    if "error" in before:
        print(before["error"])
        session.detach()
        return 1
    print()
    print("%s  %s" % (before["weapon"], before["at"]))
    for key, label in (("viewModel", "+16 viewModel"), ("worldModel", "+24 worldModel"),
                       ("knifeView", "+40 knife view"), ("knifeWorld", "+44 knife world")):
        s = before[key]
        print("   %-16s %-46s %s" % (label, s["model"], s["pointer"]))

    writes = [req(OFF_VIEW, a.view, a.view_addr),
              req(OFF_WORLD, a.world, a.world_addr)]
    if a.knife:
        writes += [req(OFF_KNIFE_VIEW, a.view, a.view_addr),
                   req(OFF_KNIFE_WORLD, a.world, a.world_addr)]

    if not a.bind:
        print()
        print("dry run; would write:")
        for w in writes:
            print("   +%-3d <- %s" % (w["offset"], w["model"]))
        print("pass --bind to apply")
        session.detach()
        return 0

    # Save the originals BEFORE writing, so a restore is exact even if the verify
    # step or the client dies afterwards.
    restore = {"weapon": a.weapon, "writes": []}
    key_for = {OFF_VIEW: "viewModel", OFF_WORLD: "worldModel",
               OFF_KNIFE_VIEW: "knifeView", OFF_KNIFE_WORLD: "knifeWorld"}
    for w in writes:
        s = before[key_for[w["offset"]]]
        restore["writes"].append({"offset": w["offset"], "pointer": s["pointer"],
                                  "model": s["model"]})
    restore["pid"] = pid_of(session)
    a.save.write_text(json.dumps(restore, indent=2), encoding="utf-8")
    print()
    print("originals saved to %s (pid %s)" % (a.save, restore["pid"]))

    r = script.exports_sync.bind(a.weapon, writes)
    if "error" in r:
        print("bind refused:", r["error"])
        session.detach()
        return 1
    print()
    for ap_ in r["applied"]:
        print("   +%-3d %-22s -> %-22s %s"
              % (ap_["offset"], str(ap_["beforeModel"]), str(ap_["afterModel"]),
                 "ok" if ap_["ok"] else "FAILED"))

    print()
    print("chain from the WeaponDef:")
    v = script.exports_sync.verify(a.weapon, [w["offset"] for w in writes])
    ok = show_verify(v)
    session.detach()
    print()
    print("bound and verified" if ok else "bound, but the chain has problems")
    print("undo:  python CodolWeaponModelBind.py --restore %s" % a.save)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
