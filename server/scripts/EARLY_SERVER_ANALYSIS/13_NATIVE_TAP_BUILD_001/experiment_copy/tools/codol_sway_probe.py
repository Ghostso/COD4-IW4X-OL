r"""Sample what C1 1.1.1.13 actually DRAWS for scope sway/bob, once per rendered frame.

    python tools/codol_sway_probe.py --pid <C1 PID> --out sway.jsonl --seconds 40
    python tools/codol_sway_probe.py --summarize sway.jsonl

YOU MUST BE IN A MATCH.  cg_t is memset at C1 0x0044E152 for the front end, so
between matches every field reads 0 and the capture is worthless.

WHY THIS TOOL EXISTS (all of the following is read out of C1.exe, not guessed):

  CG_DrawActiveFrame (0x00478680)
    -> 0x004766e0
         0x00476959  call 0x416CE0(cg, cg.time)      ; |velocity.xy|
         0x0047695e  cg[0xBF998] = that              ; "sway speed"
         0x00476985  cg[0xB4418..0xB4420] = ps.viewangles (cg[0x14C..0x154])
         0x00476abc  call 0x00471150(cg)             ; <-- the sway block
         ...
    0x00471150 builds a 0x24-byte context on ITS OWN STACK and calls, in order,
         0x0047120f  0x00424A20   weapon-kick decay   (adds to out)
         0x0047121a  0x00424C10   BG_AddIdleSway      (adds to out)
         0x00471224  0x00424D90   scoped bob          (adds to out)
         0x0047122f  0x00424F30                       (adds to out)
    then 0x00471234..0x0047125d does cg[0xB4418..0xB4420] += out[0..2].

  So the drawn additive view offset for the frame is EXACTLY

        sway = cg.refdefViewAngles(0xB4418) - ps.viewangles(0x14C)

  which is what this probe samples.  It is a real memory location, unlike the
  stack-local `out` vector, so it can be read from outside the process.

  The context 0x00471150 builds (mirrored below as CTX_*):
        ctx+0x00 = cg                      (ps is at cg+0)
        ctx+0x04 = cg[0xBF96C] ? cg[0xBF96C]-cg[0xA50] : 0   kick start time
        ctx+0x08 = cg.time(0xB0350) - cg[0xA50]              now
        ctx+0x0C = cg[0xBF990]             kick pitch amplitude
        ctx+0x10 = cg[0xBF994]             kick roll amplitude
        ctx+0x14 = cg[0xBF998]             |velocity.xy|
        ctx+0x18 = cg.frametime(0xB034C) * 0.001             <-- PER FRAME
        ctx+0x1C = cg[0x3594]              stance ramp
        ctx+0x20 = &cg[0xBF980]            the int sway phase

  BG_AdvanceSwayPhase 0x00424B90 does  *(int*)ctx[0x20] += (int)(
      ps.holdBreathScale(0x24C) * ctx[0x18] * 1000.0 * swaySpeed )
  i.e. per RENDERED FRAME, by cg.frametime milliseconds -- there is no usercmd
  replay loop anywhere above it.  It returns 0 without advancing when
  ps.fWeaponPosFrac(0x348) == 0.0f exactly (fucompp against fldz at 0x424BC7).

  The scoped bob 0x00424D90 maps ps.bobCycle straight to a sine phase:
      angle = 2*PI*(bobCycle & 0xFF)/255.0 + 2*PI          (0xC84580 = PI,
                                                            0xC84588 = 255.0,
                                                            0xC84578 = 2*PI)
  amplitude = dvar(*0x1509D3C)+0xC  *  ctx+0x14 (|velocity.xy|)  * -1.0,
  then blended by ps.fWeaponPosFrac and weapondef+0x6B0.  One unit of bobCycle
  is 2*PI/255 rad = 1.41 degrees of bob phase, so a bobCycle correction of N
  moves the drawn bob by up to  amp * (sin(p+N*2pi/255) - sin(p)).

Addresses (live, 1.1.1.13; same derivation as tools/codol_bob_probe.py):
    cg = [0x06C3D2AC]*4 + 0x016D3B58, dereferenced, ^ 0x490B400C
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

# --- playerstate, at cg+0 (C1 wire layout) --------------------------------
PS_COMMAND_TIME = 0x000
PS_PM_TYPE = 0x004
PS_PM_FLAGS = 0x00C
PS_BOBCYCLE = 0x018
PS_ORIGIN = 0x01C
PS_VELOCITY = 0x028
PS_STANCE_FLAGS = 0x0EC      # BG_AddIdleSway tests bit 3 (prone) / bit 2 (duck)
PS_VIEWANGLES = 0x14C
PS_HOLD_BREATH = 0x24C
PS_ALT_WEAPON = 0x328
PS_WEAPON = 0x33C
PS_WEAPFLAGS = 0x344
PS_WEAPON_POS_FRAC = 0x348

PS_SWAY_REPL = 0x4A0         # replicated int lerped by CG_InterpolatePlayerState
                             # (0x0045E987..0x0045E9A6) and copied into the
                             # drawn phase cg[0xBF980] at 0x0046BECD
PS_OTHER_FLAGS = 0x010       # CG_SetNextSnap 0x0046CEBD tests this for 0x1800

# --- cg_t ------------------------------------------------------------------
CG_STANCE_RAMP = 0x3594      # ctx+0x1C
CG_SNAP = 0x35E0             # cg.snap     (0x0045D1F9 memcpy source)
CG_NEXT_SNAP = 0x35E4        # cg.nextSnap (0x0046BECB) -- what the probe reads
CG_TIME_BASE = 0x0A50        # ps[0xA50].  ctx+0x08 = cg.time - this, so it is the
                             # "now" the kick decay 0x00424A20 clocks against.  It
                             # is ALSO C1's killcam latch input: 0x0046BE37 /
                             # 0x0046BF0C set/clear cg[0xC8B60] on its 0<->nonzero
                             # edges, and the rising edge runs the store at
                             # 0x0046BECD: cg[0xBF980] = nextSnap->ps[0x4A0].
                             # This server publishes it as ps->deltaTime
                             # (codol_engine_state.c, netfield 0x0a50).
CG_FRAMETIME = 0xB034C
CG_TIME = 0xB0350
CG_OLDTIME = 0xB0354
CG_GATE = 0xB035C            # 0x476AAB: nonzero skips the whole sway block
CG_BOB_ACCUM = 0xB038C       # 0x4712A9: += f(bobCycle, |vel.xy|) every frame
CG_REFDEF_ANGLES = 0xB4418   # seeded from ps.viewangles at 0x476985
CG_KICK_START = 0xBF96C      # ctx+0x04
CG_SWAY_PHASE = 0xBF980      # ctx+0x20, the int BG_AdvanceSwayPhase increments
CG_SWAY_ENABLE = 0xBF984     # byte, gate in 0x0045E830
CG_KICK_PITCH = 0xBF990      # ctx+0x0C
CG_KICK_ROLL = 0xBF994       # ctx+0x10
CG_SWAY_SPEED = 0xBF998      # ctx+0x14, |velocity.xy| written at 0x0047695E
CG_RESPAWN_PATH = 0x1740A4   # CG_SetNextSnap: 1 = path A (0x0046D19F), 0 = the
                             # unconditional path B respawn at 0x0046D365
CG_REMOTE_MODE = 0xC8B60     # latch gating the 0x0046BECD store of ps[0x4A0]

WD_NAME = 0x000
WD_SCOPE_BOB_SCALE = 0x6B0   # blended with fWeaponPosFrac inside 0x424D90
WD_OVERLAY_RETICLE = 0x694   # the gate on every sway contributor

# cg.time - ps.commandTime above this means CG_PredictPlayerState did not reach
# the current frame, so refdefViewAngles and ps.viewangles are one prediction
# apart and their difference is not the sway.  See the note in summarize().
STALL_MS = 5

# One read per region; keep them few so a sample is close to atomic.
REGIONS = [
    ("ps", 0x0000, 0x0500),
    ("mid", 0x3580, 0x0080),
    ("base", 0x0A40, 0x0020),
    ("cg", 0xB0340, 0x0060),
    ("refdef", 0xB4410, 0x0020),
    ("sway", 0xBF960, 0x0050),
    ("remote", 0xC8B50, 0x0020),
    ("path", 0x1740A0, 0x0010),
]


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

    def cg(self):
        index = self.word(CG_INDEX)
        if index is None or index > 1024:
            return None
        raw = self.word(CG_TABLE + index * 4)
        return None if raw is None else raw ^ CG_KEY


class Blocks(object):
    """The six region reads, addressed by absolute cg offset."""

    def __init__(self, parts):
        self.parts = parts

    def _at(self, off, size):
        for _, base, length in REGIONS:
            if base <= off and off + size <= base + length:
                return self.parts[base], off - base
        raise KeyError(hex(off))

    def i32(self, off):
        raw, o = self._at(off, 4)
        return struct.unpack_from("<i", raw, o)[0]

    def u32(self, off):
        raw, o = self._at(off, 4)
        return struct.unpack_from("<I", raw, o)[0]

    def u8(self, off):
        raw, o = self._at(off, 1)
        return raw[o]

    def f32(self, off):
        raw, o = self._at(off, 4)
        return struct.unpack_from("<f", raw, o)[0]

    def vec3(self, off):
        raw, o = self._at(off, 12)
        return list(struct.unpack_from("<3f", raw, o))


def read_blocks(reader, cg):
    parts = {}
    for _, base, length in REGIONS:
        raw = reader.read(cg + base, length)
        if raw is None:
            return None
        parts[base] = raw
    return Blocks(parts)


def ang_delta(a, b):
    """Shortest signed difference of two angles in degrees."""
    d = (a - b + 180.0) % 360.0 - 180.0
    return d


def finite(values):
    return all(isinstance(v, float) and math.isfinite(v) for v in values)


def weapon_def(reader, index, cache):
    if index in cache:
        return cache[index]
    address = reader.word(WEAPON_DEFS + index * 4) if 0 <= index < 4096 else None
    entry = {"index": index, "definition": address}
    raw = reader.read(address, WD_SCOPE_BOB_SCALE + 4) if address else None
    if raw is not None:
        entry["name"] = reader.text(struct.unpack_from("<I", raw, WD_NAME)[0])
        entry["overlayReticle"] = struct.unpack_from("<I", raw, WD_OVERLAY_RETICLE)[0]
        entry["scopeBobScale"] = struct.unpack_from("<f", raw, WD_SCOPE_BOB_SCALE)[0]
    else:
        entry["name"] = None
    cache[index] = entry
    return entry


def snapshot(reader, cg, predicted_time, forced):
    """cg.snap is a pointer; find the published commandTime/bobCycle inside it."""
    base = reader.word(cg + CG_SNAP)
    if not base:
        return None, forced
    if forced is None:
        for offset in range(0, 0x80, 4):
            raw = reader.read(base + offset, PS_SWAY_REPL + 8)
            if raw is None:
                continue
            ct = struct.unpack_from("<i", raw, PS_COMMAND_TIME)[0]
            bob = struct.unpack_from("<I", raw, PS_BOBCYCLE)[0]
            if bob > 0xFF or abs(ct - predicted_time) > 5000:
                continue
            forced = offset
            break
        if forced is None:
            return None, None
    raw = reader.read(base + forced, PS_SWAY_REPL + 8)
    head = reader.read(base, 0x10)
    if raw is None:
        return None, forced
    return {
        "ptr": base,
        "psOffset": forced,
        "commandTime": struct.unpack_from("<i", raw, PS_COMMAND_TIME)[0],
        "bobCycle": struct.unpack_from("<I", raw, PS_BOBCYCLE)[0] & 0xFF,
        "swayRepl": struct.unpack_from("<i", raw, PS_SWAY_REPL)[0],
        "timeBase": struct.unpack_from("<i", raw, CG_TIME_BASE)[0],
        "otherFlags": struct.unpack_from("<I", raw, PS_OTHER_FLAGS)[0],
        "head": list(struct.unpack_from("<4i", head, 0)) if head else None,
    }, forced


def sample(reader, cg, defs, snap_offset):
    """One coherent frame sample, or None if cg moved under us."""
    before = reader.word(cg + CG_TIME)
    if not before:
        return None, snap_offset, "menu"
    blocks = read_blocks(reader, cg)
    if blocks is None:
        return None, snap_offset, "read"
    after = reader.word(cg + CG_TIME)
    if after != before:
        return None, snap_offset, "torn"
    # cg.time alone is live on the front end too; a real match also has a
    # playerstate.  Without this the loading screen writes useless records.
    if not blocks.i32(PS_COMMAND_TIME) or not blocks.u32(PS_WEAPON):
        return None, snap_offset, "menu"

    viewangles = blocks.vec3(PS_VIEWANGLES)
    refdef = blocks.vec3(CG_REFDEF_ANGLES)
    velocity = blocks.vec3(PS_VELOCITY)
    if not finite(viewangles + refdef + velocity):
        return None, snap_offset, "nan"

    weapon = blocks.u32(PS_WEAPON)
    alt = blocks.u32(PS_ALT_WEAPON)
    weapflags = blocks.u32(PS_WEAPFLAGS)
    held = alt if (weapflags & 2) else weapon      # the index every contributor uses
    published, snap_offset = snapshot(reader, cg, blocks.i32(PS_COMMAND_TIME), snap_offset)

    record = {
        "t": round(time.perf_counter(), 6),
        "cgTime": before,
        "frametime": blocks.i32(CG_FRAMETIME),
        "oldTime": blocks.i32(CG_OLDTIME),
        "gate": blocks.i32(CG_GATE),
        "commandTime": blocks.i32(PS_COMMAND_TIME),
        "pm_type": blocks.i32(PS_PM_TYPE),
        "pm_flags": blocks.u32(PS_PM_FLAGS),
        "stanceFlags": blocks.u32(PS_STANCE_FLAGS),
        "bobCycle": blocks.u32(PS_BOBCYCLE) & 0xFF,
        "origin": blocks.vec3(PS_ORIGIN),
        "velocity": velocity,
        "xyspeed": math.hypot(velocity[0], velocity[1]),
        "swaySpeed": blocks.f32(CG_SWAY_SPEED),      # cg[0xBF998], the ctx+0x14 input
        "viewangles": viewangles,
        "refdefAngles": refdef,
        # THE MEASUREMENT: the additive view offset this frame actually drew.
        "sway": [ang_delta(refdef[i], viewangles[i]) for i in range(3)],
        "swayPhase": blocks.i32(CG_SWAY_PHASE),      # cg[0xBF980]
        "psSwayRepl": blocks.i32(PS_SWAY_REPL),      # cg.ps[0x4A0], replicated
        "otherFlags": blocks.u32(PS_OTHER_FLAGS),    # tested for 0x1800 at 0x0046CEBD
        "respawnPath": blocks.u8(CG_RESPAWN_PATH),   # 1 = path A, 0 = path B
        "remoteMode": blocks.i32(CG_REMOTE_MODE),    # gates the 0x0046BECD store
        "swayEnable": blocks.u8(CG_SWAY_ENABLE),
        "timeBase": blocks.i32(CG_TIME_BASE),        # cg.ps[0xA50] = our deltaTime
        "ctxNow": before - blocks.i32(CG_TIME_BASE),  # ctx+0x08 at 0x004711A1
        "kickStart": blocks.i32(CG_KICK_START),
        "kickPitch": blocks.f32(CG_KICK_PITCH),
        "kickRoll": blocks.f32(CG_KICK_ROLL),
        "stanceRamp": blocks.f32(CG_STANCE_RAMP),
        "bobAccum": blocks.f32(CG_BOB_ACCUM),
        "holdBreathScale": blocks.f32(PS_HOLD_BREATH),
        "fWeaponPosFrac": blocks.f32(PS_WEAPON_POS_FRAC),
        "weapon": weapon,
        "altWeapon": alt,
        "weapFlags": weapflags,
        "heldIndex": held,
        "weapondef": weapon_def(reader, held, defs),
        "snap": published,
    }
    return record, snap_offset, None


def capture(args):
    reader = Reader(args.pid)
    out = open(args.out, "a", encoding="utf-8") if args.out else None
    defs, snap_offset = {}, args.snap_ps_offset
    written = 0
    reasons = {}
    last_cg_time = None
    deadline = time.time() + args.seconds if args.seconds else None
    announced = False
    try:
        while deadline is None or time.time() < deadline:
            cg = reader.cg()
            if cg is None:
                print("no cg pointer (is the PID right?)")
                time.sleep(0.25)
                continue
            record, snap_offset, why = sample(reader, cg, defs, snap_offset)
            if record is None:
                reasons[why] = reasons.get(why, 0) + 1
                if why == "menu" and reasons[why] % 200 == 1:
                    print("cg is zeroed: client is in the menu, not in a match")
                time.sleep(0.005 if why == "torn" else 0.05)
                continue
            if record["cgTime"] == last_cg_time:
                time.sleep(args.poll)      # same rendered frame; wait for the next
                continue
            last_cg_time = record["cgTime"]
            if not announced:
                wd = record["weapondef"]
                print("in a match: weapon %s (slot %d) overlayReticle=%s scopeBobScale=%s"
                      % (repr(wd.get("name")), record["heldIndex"],
                         wd.get("overlayReticle"), wd.get("scopeBobScale")))
                if not wd.get("overlayReticle"):
                    print("  WARNING: overlayReticle == 0 -- every sway contributor is")
                    print("  gated off for this weapon (0x424C46 / 0x424DC3).  Hold a scope.")
                announced = True
            if out:
                out.write(json.dumps(record) + "\n")
            written += 1
            if args.verbose:
                print("cgT %8d ft %3d bob %3d ph %9d fwpf %.3f spd %7.1f  sway %+8.4f %+8.4f %+8.4f"
                      % (record["cgTime"], record["frametime"], record["bobCycle"],
                         record["swayPhase"], record["fWeaponPosFrac"], record["swaySpeed"],
                         record["sway"][0], record["sway"][1], record["sway"][2]))
            time.sleep(args.poll)
    except KeyboardInterrupt:
        pass
    finally:
        if out:
            out.close()
    print("wrote %d frames to %s" % (written, args.out))
    if reasons:
        print("skipped: %s" % reasons)
    return 0


# --------------------------------------------------------------------------
# summary
# --------------------------------------------------------------------------

def load(path):
    rows = []
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except ValueError:
                continue
    rows.sort(key=lambda r: r["cgTime"])
    # keep one row per cg.time
    unique, seen = [], set()
    for row in rows:
        if row["cgTime"] in seen:
            continue
        seen.add(row["cgTime"])
        unique.append(row)
    return unique


def percentile(values, q):
    if not values:
        return float("nan")
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(q * len(ordered)))]


def bob_phase(bobcycle):
    """C1 0x424DD4..0x424E01: 2*PI*(bob/255) + 2*PI."""
    return 2.0 * math.pi * (bobcycle / 255.0) + 2.0 * math.pi


def summarize(path, jump_factor):
    rows = load(path)
    if len(rows) < 8:
        print("%s: only %d usable frames" % (path, len(rows)))
        return 1
    print("%s: %d rendered frames, cg.time %d..%d (%.1f s)"
          % (path, len(rows), rows[0]["cgTime"], rows[-1]["cgTime"],
             (rows[-1]["cgTime"] - rows[0]["cgTime"]) / 1000.0))
    gaps = [rows[i + 1]["cgTime"] - rows[i]["cgTime"] for i in range(len(rows) - 1)]
    consecutive = [i for i, g in enumerate(gaps) if g == rows[i + 1]["frametime"]]
    print("  frame gaps: median %d ms, p95 %d ms, max %d ms; %d/%d gaps equal the "
          "client's own frametime (no dropped frame in between)"
          % (percentile(gaps, 0.5), percentile(gaps, 0.95), max(gaps),
             len(consecutive), len(gaps)))
    wd = rows[-1].get("weapondef") or {}
    print("  weapon %s slot %s overlayReticle=%s scopeBobScale=%s"
          % (repr(wd.get("name")), wd.get("index"), wd.get("overlayReticle"),
             wd.get("scopeBobScale")))
    print("")

    # Only frames where the drawn sway can be nonzero at all.
    live = [r for r in rows if r["fWeaponPosFrac"] > 0.0 and (wd.get("overlayReticle") or 1)]
    print("frames with fWeaponPosFrac > 0 (ADS): %d of %d" % (len(live), len(rows)))

    # `sway` is only the additive view offset while the prediction has caught up.
    # cg[0xB4418] is seeded from ps.viewangles at 0x00476985 and then only added
    # to -- BUT when CG_PredictPlayerState skips its replay (0x0045F56E:
    # ps.commandTime >= latestCmdTime) it OVERWRITES ps.viewangles from
    # cg[0x1740C4] at 0x0045F7BB instead.  On those frames ps.viewangles and the
    # refdef angles are one prediction apart and the difference is dominated by
    # real camera rotation, not sway: in the 2026-09-16 capture that alone
    # produced the bogus 63-83 degree tail (72 frames, all with a 80-119 ms
    # prediction lag, all with ps.commandTime == cg.snap's commandTime).
    # A stalled frame is identifiable with no assumption about sway magnitude.
    lags = [r["cgTime"] - r["commandTime"] for r in rows]
    print("prediction lag (cg.time - ps.commandTime): median %d  p95 %d  max %d ms; "
          "%d of %d frames exceed %d ms and are EXCLUDED from the sway metric"
          % (percentile(lags, 0.5), percentile(lags, 0.95), max(lags),
             sum(1 for x in lags if x > STALL_MS), len(rows), STALL_MS))

    steps = []
    for i in range(len(rows) - 1):
        a, b = rows[i], rows[i + 1]
        if b["cgTime"] - a["cgTime"] != b["frametime"]:
            continue      # a frame was missed by the probe; its delta is not one frame
        if (a["cgTime"] - a["commandTime"] > STALL_MS or
                b["cgTime"] - b["commandTime"] > STALL_MS):
            continue      # prediction stalled; refdef - viewangles is not the sway
        d = [b["sway"][k] - a["sway"][k] for k in range(3)]
        steps.append({
            "i": i, "a": a, "b": b,
            "d": d,
            "mag": math.hypot(d[0], d[1]),
            "dBob": ((b["bobCycle"] - a["bobCycle"] + 128) % 256) - 128,
            "dPhase": b["swayPhase"] - a["swayPhase"],
            "dCmd": b["commandTime"] - a["commandTime"],
            "dFrac": b["fWeaponPosFrac"] - a["fWeaponPosFrac"],
            "dSpeed": b["swaySpeed"] - a["swaySpeed"],
            "newSnap": (a.get("snap") or {}).get("commandTime") !=
                       (b.get("snap") or {}).get("commandTime"),
            "kickChanged": (a["kickStart"] != b["kickStart"] or
                            abs(a["kickPitch"] - b["kickPitch"]) > 1e-6),
        })
    if not steps:
        print("no consecutive-frame pairs: raise --poll rate or capture longer")
        return 1
    ads = [s for s in steps if s["b"]["fWeaponPosFrac"] > 0.0]
    print("consecutive-frame deltas: %d total, %d while ADS" % (len(steps), len(ads)))
    if not ads:
        print("nothing was captured while aiming down sight; nothing to say about scope sway")
        return 0

    # The sway phase is advanced from TWO clocks: once per rendered frame inside
    # BG_AddIdleSway (0x424C6B, dt = cg.frametime) and, additionally, once per
    # REPLAYED usercmd inside CG_PredictPlayerState's replay loop
    # (0x0045F590..0x0045F7A4 -> 0x0045F78C -> 0x0045E830, which adds twice:
    # 0x00424BFE and 0x0045E8A5).  If the second source fires, the per-frame
    # phase step spikes on exactly the frames where a batch of commands was
    # replayed.  This is the direct test for that.
    phase_steps = [s["dPhase"] for s in ads]
    pm = percentile([abs(x) for x in phase_steps], 0.5)
    spikes = [s for s in ads if abs(s["dPhase"]) > 2 * max(pm, 1)]
    print("")
    print("SWAY PHASE STEP per frame  (cg[0xBF980], BG_AdvanceSwayPhase)")
    print("  median %s  p95 %s  max %s  min %s"
          % (percentile(phase_steps, 0.5), percentile(phase_steps, 0.95),
             max(phase_steps), min(phase_steps)))
    print("  expected if the render path alone advances it: "
          "holdBreathScale * frametime * swaySpeedScale")
    print("  %d of %d ADS frames step more than 2x the median (%.2f/s) -- these are "
          "the frames where the prediction replay loop also advanced it"
          % (len(spikes), len(ads), len(spikes) /
             max(1e-6, (rows[-1]["cgTime"] - rows[0]["cgTime"]) / 1000.0)))

    # Fit the render-path-only model  dPhase = round(K * holdBreathScale * frametime)
    # on frames that took no new snapshot and no backward commandTime, then report
    # the residual: every positive residual is an extra advance the replay loop
    # contributed, in units of the base per-frame step.
    quiet = [s for s in ads if not s["newSnap"] and s["dCmd"] >= 0]
    if quiet:
        ratios = sorted(s["dPhase"] / max(1, s["b"]["frametime"]) for s in quiet
                        if s["dPhase"] > 0)
        k = percentile(ratios, 0.5) if ratios else 0.0
        resid = [s["dPhase"] - round(k * s["b"]["holdBreathScale"] * s["b"]["frametime"])
                 for s in quiet]
        exact = sum(1 for e in resid if abs(e) <= 1)
        print("  fitted render-path rate K = dPhase/frametime = %.3f (median over %d "
              "quiet frames)" % (k, len(quiet)))
        print("  residual vs K*holdBreathScale*frametime: %.1f%% of quiet frames fit "
              "exactly (|err|<=1), %.1f%% exceed it by >10 -- the excess is the "
              "replay loop" % (100.0 * exact / len(resid),
                               100.0 * sum(1 for e in resid if e > 10) / len(resid)))
    drops = [s for s in ads if s["dPhase"] < 0]
    if drops:
        amounts = sorted(-s["dPhase"] for s in drops)
        with_snap = sum(1 for s in drops if s["newSnap"])
        to_zero = sum(1 for s in drops if s["b"]["swayPhase"] == 0)
        print("  phase DECREASED on %d of %d ADS frames: median drop %d, p95 %d, max %d; "
              "%d (%.0f%%) coincide with a new snapshot, %d land on exactly 0"
              % (len(drops), len(ads), percentile(amounts, 0.5),
                 percentile(amounts, 0.95), amounts[-1], with_snap,
                 100.0 * with_snap / len(drops), to_zero))
        print("  (a pure `phase += positive` cannot decrease; see the reset store at "
              "C1 0x0045D3AB)")

    mags = [s["mag"] for s in ads]
    med = percentile(mags, 0.5)
    print("")
    print("DRAWN SWAY STEP per frame  (refdefViewAngles - ps.viewangles), degrees")
    print("  median %.5f   p75 %.5f   p95 %.5f   p99 %.5f   max %.5f"
          % (med, percentile(mags, 0.75), percentile(mags, 0.95),
             percentile(mags, 0.99), max(mags)))
    threshold = max(jump_factor * med, 1e-4)
    jumps = [s for s in ads if s["mag"] > threshold]
    span = (rows[-1]["cgTime"] - rows[0]["cgTime"]) / 1000.0 or 1.0
    print("  jump threshold = %.1f x median = %.5f deg" % (jump_factor, threshold))
    print("  %d jumps in %.1f s = %.2f per second" % (len(jumps), span, len(jumps) / span))
    if not jumps:
        print("  -> the drawn sway advances smoothly; the jitter is NOT in this chain.")
        return 0

    # what each jump coincides with
    def share(pred):
        hit = sum(1 for s in jumps if pred(s))
        base = sum(1 for s in ads if pred(s))
        return hit, 100.0 * hit / max(1, len(jumps)), base, 100.0 * base / max(1, len(ads))

    print("")
    print("WHAT EACH JUMP COINCIDES WITH   (share of jumps vs share of all ADS frames;")
    print("a cause must be much commoner among jumps than among all frames)")
    tests = [
        ("bobCycle changed",            lambda s: s["dBob"] != 0),
        ("bobCycle changed by >2",      lambda s: abs(s["dBob"]) > 2),
        ("bobCycle changed by >8",      lambda s: abs(s["dBob"]) > 8),
        ("bobCycle went BACKWARDS",     lambda s: s["dBob"] < 0),
        ("sway phase DECREASED",        lambda s: s["dPhase"] < 0),
        ("prediction rebased backward", lambda s: s["dCmd"] < 0),
        ("new snapshot this frame",     lambda s: s["newSnap"]),
        ("fWeaponPosFrac changed",      lambda s: abs(s["dFrac"]) > 1e-7),
        ("swaySpeed |vel.xy| changed",  lambda s: abs(s["dSpeed"]) > 0.5),
        ("sway phase step != median",   lambda s: True),   # replaced below
        ("weapon kick re-armed",        lambda s: s["kickChanged"]),
        ("frametime > 2x median",       lambda s: s["b"]["frametime"] >
                                                  2 * percentile([x["b"]["frametime"] for x in ads], 0.5)),
    ]
    phase_med = percentile([abs(s["dPhase"]) for s in ads], 0.5)
    tests = [t for t in tests if t[0] != "sway phase step != median"]
    tests.insert(0, ("sway phase step off by >2x median",
                     lambda s: abs(abs(s["dPhase"]) - phase_med) > phase_med))
    for name, pred in tests:
        hit, hp, base, bp = share(pred)
        flag = "  <== " if hp > 2 * max(bp, 1.0) and hit >= max(3, 0.25 * len(jumps)) else ""
        print("  %-34s %4d/%4d jumps (%5.1f%%)   vs %5.1f%% of all ADS frames%s"
              % (name, hit, len(jumps), hp, bp, flag))
    unexplained = [s for s in jumps if s["dBob"] == 0 and not s["newSnap"]
                   and abs(s["dFrac"]) <= 1e-7 and not s["kickChanged"]]
    print("  %-34s %4d/%4d jumps (%5.1f%%)"
          % ("NOTHING changed on the wire", len(unexplained), len(jumps),
             100.0 * len(unexplained) / len(jumps)))

    # how much of the jump the bobCycle step alone explains
    print("")
    print("IS THE JUMP THE bobCycle TERM?  For each jump, the drawn step is compared")
    print("with the bob-phase step  2*PI*dBob/255  it would take at the same amplitude.")
    scored = []
    for s in jumps:
        if s["dBob"] == 0:
            continue
        p0, p1 = bob_phase(s["a"]["bobCycle"]), bob_phase(s["b"]["bobCycle"])
        shape = abs(math.sin(p1) - math.sin(p0))
        if shape > 1e-9:
            scored.append((s["mag"] / shape, s))
    if scored:
        implied = [v for v, _ in scored]
        print("  implied bob amplitude = drawn step / |sin(p1)-sin(p0)|, degrees:")
        print("    median %.4f  p95 %.4f  (a CONSISTENT value means the jump really is"
              % (percentile(implied, 0.5), percentile(implied, 0.95)))
        print("     the bobCycle term; a scattered one means it is something else)")
        lo, hi = percentile(implied, 0.25), percentile(implied, 0.75)
        print("    interquartile spread %.4f..%.4f -> %s"
              % (lo, hi, "CONSISTENT" if hi < 3 * max(lo, 1e-6) else "SCATTERED"))

    print("")
    print("WORST 12 JUMPS")
    print("  %8s %5s %8s %6s %6s %5s %8s %9s %6s" %
          ("cgTime", "ft", "sway.mag", "dBob", "bob", "dFrac", "dSpeed", "dPhase", "snap?"))
    for s in sorted(jumps, key=lambda s: -s["mag"])[:12]:
        print("  %8d %5d %8.4f %6d %6d %5.3f %8.1f %9d %6s"
              % (s["b"]["cgTime"], s["b"]["frametime"], s["mag"], s["dBob"],
                 s["b"]["bobCycle"], s["dFrac"], s["dSpeed"], s["dPhase"],
                 "YES" if s["newSnap"] else "no"))

    # predicted vs published bobCycle at matched commandTime
    matched = [(r["bobCycle"], r["snap"]["bobCycle"]) for r in rows
               if r.get("snap") and r["snap"]["commandTime"] == r["commandTime"]]
    if matched:
        agree = sum(1 for a, b in matched if a == b)
        print("")
        print("predicted vs published bobCycle at matched commandTime: %d/%d agree (%.1f%%)"
              % (agree, len(matched), 100.0 * agree / len(matched)))
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--pid", type=int, help="C1.exe process id")
    parser.add_argument("--out", default="sway_capture.jsonl")
    parser.add_argument("--poll", type=float, default=0.002,
                        help="seconds between polls; one record is kept per rendered "
                             "frame (default 0.002, i.e. ~8 polls per 60 Hz frame)")
    parser.add_argument("--seconds", type=float, default=0.0)
    parser.add_argument("--snap-ps-offset", type=lambda s: int(s, 0), default=None)
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--summarize", metavar="CAPTURE.jsonl")
    parser.add_argument("--jump-factor", type=float, default=4.0,
                        help="a frame step this many times the median counts as a jump")
    args = parser.parse_args(argv)
    if args.summarize:
        return summarize(args.summarize, args.jump_factor)
    if not args.pid:
        parser.error("--pid is required when capturing "
                     "(find it with: tasklist | findstr /i C1.exe)")
    return capture(args)


if __name__ == "__main__":
    sys.exit(main())
