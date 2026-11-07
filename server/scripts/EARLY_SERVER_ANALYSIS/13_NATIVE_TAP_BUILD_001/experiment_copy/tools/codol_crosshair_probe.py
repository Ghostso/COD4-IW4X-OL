"""Read C1 1.1.1.13's live friend/foe crosshair state without attaching a debugger.

    python tools/codol_crosshair_probe.py --pid <C1 PID> [--samples 200]

Prints, per sample, every gate CG_GetCrosshairColor 0x0043C4A0 evaluates, in the
order the instructions evaluate them, plus the verdict colour.  A sample taken
in the menu is worthless: cg_t is memset at 0x0044E152, so every field reads 0
and the weapon gate fails on `none`.  Aim at a TEAMMATE while this runs.

Gate order (live disassembly, 2026-09-16):
  0x0043C4E1  ecx = ps[0x33c]                (ps.weapon, netfield 43, 10 bits)
  0x0043C4E7  edx = bg_weaponDefs[ecx]       (table 0x0150D720)
  0x0043C4F6  if (edx[0xBC3] == 0) -> WHITE  (IW4 crosshairColorChange)
  0x0043C503  ecx = ps[0x344]                (weapFlags, netfield 87, 21 bits)
  0x0043C509  if (!(ecx & 8)) -> enemy test
  0x0043C50E  edx = cg[0xBF050] - cg[0xBF054]
  0x0043C51F  if (edx < dvar "775") -> WHITE (SIGNED)
  0x0043C528  Dvar_GetUnpackedColor("291")   -> the friendly colour
  0x0043C546  if (!(ecx & 0x10)) -> ...
  0x0043C551  if (!dvar "690") -> ...
  0x0043C563  if (delta < 250) -> WHITE      (delta has no writer: always 0)
The returned float[4] tints the centre pic (0x0043CAE0) and the four crosshair
segments (0x0043CD60, four CG_DrawRotatedPic at 0x0043CE8D/CEE8/CF37/CF93).
"""
import argparse
import ctypes
import struct
import time

CG_INDEX = 0x06C3D2AC
CG_TABLE = 0x016D3B58
CG_KEY = 0x490B400C
WEAPON_DEFS = 0x0150D720
DVAR_291 = 0x0220CF98      # stored by the registration at 0x0052B1FF
DVAR_775 = 0x016D44DC
DVAR_690 = 0x016DA19C
DVAR_687 = 0x016D44D8
PS_WEAPON = 0x33C
PS_WEAPFLAGS = 0x344
CG_SETTLE_NOW = 0xBF050
CG_SETTLE_THEN = 0xBF054
CG_TIME = 0xB0350


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pid", type=int, required=True)
    parser.add_argument("--samples", type=int, default=200)
    parser.add_argument("--interval", type=float, default=0.25)
    args = parser.parse_args()

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32]
    kernel.OpenProcess.restype = ctypes.c_void_p
    kernel.ReadProcessMemory.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p,
                                         ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
    handle = kernel.OpenProcess(0x10, False, args.pid)  # PROCESS_VM_READ only
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())

    def read(address, size):
        buffer = ctypes.create_string_buffer(size)
        got = ctypes.c_size_t()
        if not kernel.ReadProcessMemory(handle, ctypes.c_void_p(address), buffer, size,
                                        ctypes.byref(got)) or got.value != size:
            return None
        return buffer.raw

    def word(address):
        raw = read(address, 4)
        return None if raw is None else struct.unpack("<I", raw)[0]

    def text(address, limit=64):
        raw = read(address, limit)
        return None if raw is None else raw.split(b"\0")[0].decode("latin1", "replace")

    def dvar(global_address):
        """Returns (name, type, current value dword) for a C1 dvar_t.
        Layout confirmed live: name +0, flags +4, type byte +8, current +0xC,
        latched +0x1C, reset +0x2C; DvarValue is 0x10 bytes."""
        pointer = word(global_address)
        if not pointer:
            return None
        raw = read(pointer, 0x40)
        if raw is None:
            return None
        return (text(struct.unpack_from("<I", raw, 0)[0]), raw[8],
                struct.unpack_from("<I", raw, 0xC)[0], struct.unpack_from("<I", raw, 0x2C)[0])

    def unpacked(value):
        return tuple(((value >> shift) & 0xFF) / 255.0 for shift in (0, 8, 16, 24))

    friendly = dvar(DVAR_291)
    settle = dvar(DVAR_775)
    enemy_on = dvar(DVAR_690)
    alpha = dvar(DVAR_687)
    print(f'dvar "291" friendly colour : {friendly and friendly[0]!r} type {friendly and friendly[1]} '
          f'current {friendly and friendly[2]:#010x} -> rgba {friendly and unpacked(friendly[2])} '
          f'(registered default {friendly and friendly[3]:#010x})')
    print(f'dvar "775" friendly settle : {settle and settle[2]} (signed threshold at 0x0043C51F)')
    print(f'dvar "690" enemy colour on : {enemy_on and enemy_on[2]}')
    print(f'dvar "687" crosshair alpha : {alpha and struct.unpack("<f", struct.pack("<I", alpha[2]))[0]}')

    for sample in range(args.samples):
        index = word(CG_INDEX)
        raw = None if index is None or index > 1024 else word(CG_TABLE + index * 4)
        if raw is None:
            print("no cg pointer")
            time.sleep(args.interval)
            continue
        cg = raw ^ CG_KEY
        if not word(cg + CG_TIME):
            print("cg is zeroed: client is in the menu, not in a match")
            time.sleep(args.interval)
            continue
        weapon = word(cg + PS_WEAPON)
        flags = word(cg + PS_WEAPFLAGS)
        definition = word(WEAPON_DEFS + weapon * 4) if weapon is not None else None
        gate = read(definition + 0xBC3, 1)[0] if definition else None
        name = text(word(definition)) if definition else None
        delta = (word(cg + CG_SETTLE_NOW) or 0) - (word(cg + CG_SETTLE_THEN) or 0)
        if not gate:
            verdict = f"WHITE (weapon gate: {name!r} +0xBC3 = {gate})"
        elif flags & 8:
            verdict = ("WHITE (friendly settle gate)" if delta < (settle[2] if settle else 0)
                       else f"FRIENDLY {unpacked(friendly[2]) if friendly else '?'}")
        elif flags & 0x10:
            if not (enemy_on and enemy_on[2]):
                verdict = "WHITE (cg_crosshairEnemyColor off)"
            elif delta < 250:
                verdict = "WHITE (enemy settle gate: delta < 250, unreachable on this build)"
            else:
                verdict = "ENEMY"
        else:
            verdict = "WHITE (no friend/foe bit in the client playerstate)"
        print(f"[{sample:3d}] ps.weapon {weapon} {name!r} +0xBC3 {gate} | "
              f"ps.weapFlags {flags:#x} bit8 {int(bool(flags & 8))} bit0x10 {int(bool(flags & 0x10))} | "
              f"settle delta {delta} | {verdict}")
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
