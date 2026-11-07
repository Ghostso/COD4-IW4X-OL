r"""Capture C1 1.1.1.13's live scope-bob inputs without attaching a debugger.

    python tools/codol_bob_probe.py --pid <C1 PID> --out bob_capture.jsonl
    python tools/codol_bob_probe.py --pid <C1 PID> --out bob_capture.jsonl --seconds 60
    python tools/codol_bob_probe.py --summarize bob_capture.jsonl

YOU MUST BE IN A MATCH, NOT THE MENU.  cg_t is memset at C1 0x0044E152 when the
front end takes over, so between matches every field below reads 0, ps.weapon is
`none` and the capture is worthless.  Join a game, spawn, then start the probe;
it prints `cg is zeroed: client is in the menu, not in a match` for every sample
taken outside a live match and those samples are not written.  For the sniper
question specifically: hold a SNIPER, scope it, and move -- the drawn scope bob
(C1 0x00424D90) is gated on WeaponDef+0x694 and its amplitude is
`0.16 * |velocity.xy|`, so a standing player draws no bob at all.

What it samples, every --interval seconds (default 25 ms):

* the PREDICTED playerstate at `cg+0` -- the copy C1's own pmove integrates and
  the copy the sway/bob models actually read;
* the SNAPSHOT playerstate reached through `*(cg+0x35e4)` -- what this server
  published, which OVERRIDES the predicted copy for every changeHint-3 field
  (origin, velocity, viewangles and `ps->bobCycle`) on any frame the snapshot
  carries the forced-origin bit;
* `bg_weaponDefs[ps.weapon]`, and from it `+0x670 moveSpeedScale`,
  `+0x674 adsMoveSpeedScale` and `+0x694 overlayReticle`.

`+0x670` / `+0x674` are the point of the tool.  C1 feeds both into PM_CmdScale
(0x41023f / 0x410266) AND into the `ps->bobCycle` divisor of PM_Footsteps
(0x413734 / 0x413749).  If this server's WeaponDef copy of either differs from
the client's, the two pmoves integrate bobCycle at different rates, the player's
authoritative origin drifts from the predicted one, and the resulting forced
snapshot re-seeds the bob phase several times a second -- which through a scope
reads as the sway being yanked back.  Compare these numbers against the server's
own with `codol_checkpmovedef <weapon name>` (rcon or console), which prints the
same three offsets out of the definition BG_GetWeaponDef hands the server pmove.

ZONE-RESOLUTION DISCRIMINATOR.  `cheytac_mp` is defined three times on disk
(common_gametype_mp, patch_common_gametype_mp, ui_viewer_mp) but all three carry
the same +0x670 / +0x674, so the sniper cannot tell which zone C1 resolved.
`javelin_mp`, `rpg_mp` and `stinger_mp` CAN: their `+0x670 moveSpeedScale` is
1.0 in common_gametype_mp and 0.8 in patch_common_gametype_mp (verified offline
with tools/codol_weapondef_zone_diff.py).  Hold one of those three and read the
`msS` column: 0.8 means the client resolved the PATCH zone, which is the zone
this server's registry also searches first; 1.0 would mean the base zone wins on
the client and the server's order is inverted.

`--dump-defs N` walks the client bg_weaponDefs table instead of sampling,
printing +0x670/+0x674/+0x678/+0x694 for every slot whose pointer resolves to a
readable definition.  The front end registers its OWN small index space (its
`count` at 0x015369E8 is ~18 and slot 3 is `m4_mp`), so slot numbers read
between matches are NOT the slots this server publishes -- only the names and
the values are meaningful there.  In a match the count is the published weapon
count and the slots line up with `ps->weapon`.

`--summarize` re-reads a capture and reports, at MATCHED `commandTime` (the only
frame of reference in which a difference means anything), how often the
predicted and the published `bobCycle` agree and how the disagreement is
distributed.  bobCycle is an 8-bit integrator mod 256, so the signed difference
is reported wrapped into [-128, 127]: a rate difference shows as a distribution
that walks away from 0, while a pure phase offset parks at one value.

Addresses (live, 1.1.1.13; same derivation as tools/codol_crosshair_probe.py):
    cg            = [0x06C3D2AC]*4 + 0x016D3B58, dereferenced, ^ 0x490B400C
    bg_weaponDefs = 0x0150D720 (pointer array), count at 0x015369E8
    composed records 0x01536C68, stride 0xE78, definition at record+0x98
Playerstate offsets are the C1 wire layout (playerStateFields 0xC38CA8), the
same table src/codol/snapshot/codol_player_fields.inc carries.
"""
import argparse
import ctypes
import json
import math
import struct
import sys
import time

CG_INDEX = 0x06C3D2AC
CG_TABLE = 0x016D3B58
CG_KEY = 0x490B400C
WEAPON_DEFS = 0x0150D720
WEAPON_DEF_COUNT = 0x015369E8
COMPOSED_RECORDS = 0x01536C68
COMPOSED_STRIDE = 0xE78
COMPOSED_DEF = 0x98

CG_TIME = 0xB0350          # cg.time; zero means the front end memset cg_t
CG_SNAP = 0x35E4           # cg.snap -- the published snapshot

# Playerstate, C1 wire layout.
PS_COMMAND_TIME = 0x000
PS_PM_FLAGS = 0x00C
PS_BOBCYCLE = 0x018
PS_ORIGIN = 0x01C
PS_VELOCITY = 0x028
PS_LEANF = 0x094
PS_SPEED = 0x098
PS_HOLD_BREATH_SCALE = 0x24C
PS_WEAPON = 0x33C
PS_WEAPFLAGS = 0x344
PS_WEAPON_POS_FRAC = 0x348
PS_BLOCK = 0x360           # enough to cover every offset above in one read

# WeaponDef.
WD_NAME = 0x000
WD_MOVE_SPEED_SCALE = 0x670
WD_ADS_MOVE_SPEED_SCALE = 0x674
WD_SPRINT_DURATION_SCALE = 0x678
WD_OVERLAY_RETICLE = 0x694


class Reader(object):
    """PROCESS_VM_READ only; never writes to the client."""

    def __init__(self, pid):
        self.kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        self.kernel.OpenProcess.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32]
        self.kernel.OpenProcess.restype = ctypes.c_void_p
        self.kernel.ReadProcessMemory.argtypes = [
            ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p,
            ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
        self.handle = self.kernel.OpenProcess(0x10, False, pid)
        if not self.handle:
            raise ctypes.WinError(ctypes.get_last_error())

    def read(self, address, size):
        if not address:
            return None
        buffer = ctypes.create_string_buffer(size)
        got = ctypes.c_size_t()
        if not self.kernel.ReadProcessMemory(self.handle, ctypes.c_void_p(address), buffer,
                                             size, ctypes.byref(got)) or got.value != size:
            return None
        return buffer.raw

    def word(self, address):
        raw = self.read(address, 4)
        return None if raw is None else struct.unpack("<I", raw)[0]

    def text(self, address, limit=96):
        raw = self.read(address, limit)
        if raw is None:
            return None
        return raw.split(b"\0")[0].decode("latin1", "replace")


def u32(raw, off):
    return struct.unpack_from("<I", raw, off)[0]


def i32(raw, off):
    return struct.unpack_from("<i", raw, off)[0]


def f32(raw, off):
    return struct.unpack_from("<f", raw, off)[0]


def vec3(raw, off):
    return list(struct.unpack_from("<3f", raw, off))


def finite(values):
    return all(isinstance(v, float) and math.isfinite(v) for v in values)


def playerstate(raw):
    if raw is None:
        return None
    origin, velocity = vec3(raw, PS_ORIGIN), vec3(raw, PS_VELOCITY)
    if not finite(origin) or not finite(velocity):
        return None
    return {
        "commandTime": i32(raw, PS_COMMAND_TIME),
        "bobCycle": u32(raw, PS_BOBCYCLE) & 0xFF,
        "bobCycleRaw": u32(raw, PS_BOBCYCLE),
        "origin": origin,
        "velocity": velocity,
        "xyspeed": math.hypot(velocity[0], velocity[1]),
        "speed": f32(raw, PS_SPEED),
        "leanf": f32(raw, PS_LEANF),
        "pm_flags": u32(raw, PS_PM_FLAGS),
        "weapon": u32(raw, PS_WEAPON),
        "weapFlags": u32(raw, PS_WEAPFLAGS),
        "fWeaponPosFrac": f32(raw, PS_WEAPON_POS_FRAC),
        "holdBreathScale": f32(raw, PS_HOLD_BREATH_SCALE),
    }


def weapon_def(reader, index, cache):
    """bg_weaponDefs[index] plus the three offsets both pmoves consume."""
    if index in cache:
        return cache[index]
    count = reader.word(WEAPON_DEF_COUNT)
    address = reader.word(WEAPON_DEFS + index * 4) if index < 4096 else None
    entry = {"index": index, "registered": count, "definition": address}
    raw = reader.read(address, WD_OVERLAY_RETICLE + 4) if address else None
    if raw is not None:
        entry["name"] = reader.text(u32(raw, WD_NAME))
        entry["moveSpeedScale"] = f32(raw, WD_MOVE_SPEED_SCALE)
        entry["adsMoveSpeedScale"] = f32(raw, WD_ADS_MOVE_SPEED_SCALE)
        entry["sprintDurationScale"] = f32(raw, WD_SPRINT_DURATION_SCALE)
        entry["overlayReticle"] = u32(raw, WD_OVERLAY_RETICLE)
    else:
        entry["name"] = None
    # Composed weapons also live in the record table; report where the pointer
    # came from so a mismatch between the two views is visible rather than
    # guessed.  record+0x98 is the definition the client built for that name.
    if address and count and index < count:
        record = COMPOSED_RECORDS + index * COMPOSED_STRIDE
        entry["composedRecordDefinition"] = record + COMPOSED_DEF
        entry["fromComposedRecord"] = (record + COMPOSED_DEF) == address
    cache[index] = entry
    return entry


def find_snapshot_ps(reader, cg, predicted_time, forced=None):
    """cg.snap is a pointer; the published playerstate sits inside it.  Locate
    it once by matching a plausible commandTime rather than hard-coding a
    struct offset, and report what was chosen."""
    base = reader.word(cg + CG_SNAP)
    if not base:
        return None, None
    if forced is not None:
        return base + forced, forced
    for offset in range(0, 0x80, 4):
        raw = reader.read(base + offset, PS_BLOCK)
        state = playerstate(raw)
        if state is None:
            continue
        if state["bobCycleRaw"] > 0xFF:
            continue
        if abs(state["commandTime"] - predicted_time) > 5000:
            continue
        if not 0 <= state["weapon"] < 4096:
            continue
        return base + offset, offset
    return None, None


DISCRIMINATORS = {
    "javelin_mp": (1.0, 0.8), "rpg_mp": (1.0, 0.8), "stinger_mp": (1.0, 0.8)}


def dump_defs(args):
    """Every registered client weapon definition, with the pmove inputs."""
    reader = Reader(args.pid)
    count = reader.word(WEAPON_DEF_COUNT)
    print("bg_weaponDefs count at 0x%08X = %s" % (WEAPON_DEF_COUNT, count))
    if not count:
        print("count is 0: the client is in the menu, not in a match")
        return 1
    limit = args.dump_defs if args.dump_defs > 0 else max(count, 700)
    cache, verdicts = {}, []
    for index in range(limit):
        entry = weapon_def(reader, index, cache)
        name = entry.get("name")
        # Slots past `count` can still hold a readable definition the client
        # loaded but has not (re)registered; print those, drop garbage.
        if not name or len(name) < 3 or any(c < " " for c in name):
            continue
        print("  slot %-4d %-46s +0x670 %-10.6g +0x674 %-10.6g +0x678 %-10.6g +0x694 %d"
              % (index, entry["name"], entry.get("moveSpeedScale", float("nan")),
                 entry.get("adsMoveSpeedScale", float("nan")),
                 entry.get("sprintDurationScale", float("nan")),
                 entry.get("overlayReticle", 0)))
        base, patch = DISCRIMINATORS.get((entry["name"] or "").lower(), (None, None))
        if base is not None:
            value = entry.get("moveSpeedScale")
            verdicts.append((entry["name"], value,
                             "patch_common_gametype_mp" if abs(value - patch) < 1e-6 else
                             "common_gametype_mp" if abs(value - base) < 1e-6 else
                             "NEITHER shipped zone"))
    print("")
    if verdicts:
        print("zone-resolution verdict (see the module docstring):")
        for name, value, zone in verdicts:
            print("  %-16s +0x670 = %-8.6g -> the client resolved %s" % (name, value, zone))
    else:
        print("no discriminator weapon (javelin_mp / rpg_mp / stinger_mp) is registered;")
        print("this client build cannot be told which zone it resolved from this table.")
    return 0


def capture(args):
    reader = Reader(args.pid)
    out = open(args.out, "a", encoding="utf-8") if args.out else None
    cache = {}
    snap_offset = args.snap_ps_offset
    written = skipped = 0
    deadline = time.time() + args.seconds if args.seconds else None
    sample = 0
    try:
        while (args.samples <= 0 or sample < args.samples) and \
              (deadline is None or time.time() < deadline):
            sample += 1
            index = reader.word(CG_INDEX)
            raw = None if index is None or index > 1024 else reader.word(CG_TABLE + index * 4)
            if raw is None:
                print("no cg pointer (is the PID right?)")
                time.sleep(args.interval)
                continue
            cg = raw ^ CG_KEY
            if not reader.word(cg + CG_TIME):
                skipped += 1
                if skipped % 40 == 1:
                    print("cg is zeroed: client is in the menu, not in a match")
                time.sleep(args.interval)
                continue
            predicted = playerstate(reader.read(cg, PS_BLOCK))
            if predicted is None:
                time.sleep(args.interval)
                continue
            address, chosen = find_snapshot_ps(reader, cg, predicted["commandTime"], snap_offset)
            if chosen is not None and snap_offset is None:
                snap_offset = chosen
                print("cg.snap playerstate found at *(cg+0x35e4) + 0x%02x" % chosen)
            published = playerstate(reader.read(address, PS_BLOCK)) if address else None
            record = {
                "t": round(time.time(), 4),
                "sample": sample,
                "cg": cg,
                "pred": predicted,
                "snap": published,
                "weapondef": weapon_def(reader, predicted["weapon"], cache),
            }
            if out:
                out.write(json.dumps(record) + "\n")
                out.flush()
            written += 1
            if args.verbose or not out:
                wd = record["weapondef"]
                print("[%5d] ct %8d bob %3d | snap ct %8s bob %3s | xy %7.1f pmf %#010x "
                      "wp %3d %-34s msS %.4g adsMsS %.4g ret %s"
                      % (sample, predicted["commandTime"], predicted["bobCycle"],
                         published["commandTime"] if published else "-",
                         published["bobCycle"] if published else "-",
                         predicted["xyspeed"], predicted["pm_flags"], predicted["weapon"],
                         repr(wd.get("name")), wd.get("moveSpeedScale", float("nan")),
                         wd.get("adsMoveSpeedScale", float("nan")),
                         wd.get("overlayReticle")))
            time.sleep(args.interval)
    except KeyboardInterrupt:
        pass
    finally:
        if out:
            out.close()
    print("wrote %d samples to %s (%d skipped: client not in a match)"
          % (written, args.out, skipped))
    return 0


def wrapped(delta):
    """bobCycle is mod 256; report the shortest signed distance."""
    delta &= 0xFF
    return delta - 256 if delta > 127 else delta


def summarize(path):
    predicted, published, defs = {}, {}, {}
    samples = 0
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except ValueError:
                continue
            samples += 1
            pred, snap = record.get("pred"), record.get("snap")
            wd = record.get("weapondef") or {}
            if wd.get("name"):
                defs[(wd.get("index"), wd["name"])] = (
                    wd.get("moveSpeedScale"), wd.get("adsMoveSpeedScale"),
                    wd.get("sprintDurationScale"), wd.get("overlayReticle"))
            if pred:
                predicted.setdefault(pred["commandTime"], pred)
            if snap:
                published.setdefault(snap["commandTime"], snap)
    print("%s: %d samples, %d distinct predicted commandTimes, %d published"
          % (path, samples, len(predicted), len(published)))
    print("")
    print("weapon definitions the CLIENT held during this capture")
    print("  (compare with the server's `codol_checkpmovedef <name>`)")
    for (index, name), values in sorted(defs.items(), key=lambda kv: kv[0][0]):
        print("  slot %-4s %-40s +0x670 %-10s +0x674 %-10s +0x678 %-10s +0x694 %s"
              % (index, name, values[0], values[1], values[2], values[3]))
    print("")
    shared = sorted(set(predicted) & set(published))
    if not shared:
        print("no matched commandTime: nothing to compare.  A capture taken in the")
        print("menu, or one whose snapshot playerstate was never located, does this.")
        return 0
    agree = 0
    histogram = {}
    origin_error = []
    for when in shared:
        delta = wrapped(predicted[when]["bobCycle"] - published[when]["bobCycle"])
        if delta == 0:
            agree += 1
        histogram[delta] = histogram.get(delta, 0) + 1
        a, b = predicted[when]["origin"], published[when]["origin"]
        origin_error.append(math.dist(a[:2], b[:2]))
    print("bobCycle at matched commandTime: %d matched samples, %d agree (%.1f%%), "
          "%d disagree" % (len(shared), agree, 100.0 * agree / len(shared),
                           len(shared) - agree))
    worst = max(histogram.items(), key=lambda kv: (kv[0] != 0, kv[1]))
    print("  most common disagreement: %+d on %d samples" % (worst[0], worst[1]))
    print("  |delta| distribution:")
    buckets = [(0, 0), (1, 4), (5, 16), (17, 64), (65, 128)]
    for low, high in buckets:
        count = sum(n for d, n in histogram.items() if low <= abs(d) <= high)
        print("    %3d..%-3d : %5d  (%.1f%%)" % (low, high, count,
                                                 100.0 * count / len(shared)))
    print("  full histogram (delta: count), largest first:")
    for delta, count in sorted(histogram.items(), key=lambda kv: -kv[1])[:16]:
        print("    %+4d : %d" % (delta, count))
    if origin_error:
        origin_error.sort()
        print("")
        print("horizontal origin error at the same matched times: mean %.4f, "
              "median %.4f, p95 %.4f, max %.4f units"
              % (sum(origin_error) / len(origin_error),
                 origin_error[len(origin_error) // 2],
                 origin_error[int(len(origin_error) * 0.95)], origin_error[-1]))
        over = sum(1 for e in origin_error if e > 0.1)
        print("  %d of %d exceed C1's own 0.1-unit prediction tolerance (%.1f%%)"
              % (over, len(origin_error), 100.0 * over / len(origin_error)))
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--pid", type=int, help="C1.exe process id")
    parser.add_argument("--out", default="bob_capture.jsonl",
                        help="JSONL output (appended); empty string prints only")
    parser.add_argument("--interval", type=float, default=0.025,
                        help="seconds between samples (default 0.025)")
    parser.add_argument("--samples", type=int, default=0,
                        help="stop after this many samples (0 = until Ctrl-C)")
    parser.add_argument("--seconds", type=float, default=0.0,
                        help="stop after this many seconds (0 = until Ctrl-C)")
    parser.add_argument("--snap-ps-offset", type=lambda s: int(s, 0), default=None,
                        help="byte offset of the playerstate inside cg.snap; "
                             "auto-detected by matching commandTime when omitted")
    parser.add_argument("--verbose", action="store_true", help="also print every sample")
    parser.add_argument("--summarize", metavar="CAPTURE.jsonl",
                        help="analyse a capture instead of taking one")
    parser.add_argument("--dump-defs", type=int, nargs="?", const=-1, default=0,
                        metavar="N", help="dump the client's bg_weaponDefs table "
                                          "(optionally only the first N slots) and exit")
    args = parser.parse_args(argv)
    if args.summarize:
        return summarize(args.summarize)
    if not args.pid:
        parser.error("--pid is required when capturing "
                     "(find it with: tasklist | findstr /i C1.exe)")
    if args.dump_defs:
        return dump_defs(args)
    return capture(args)


if __name__ == "__main__":
    sys.exit(main())
