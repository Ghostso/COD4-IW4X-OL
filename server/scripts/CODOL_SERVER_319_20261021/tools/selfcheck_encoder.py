# -*- coding: utf-8 -*-
"""Self-check: the encoder in ref_reader.py must round-trip through the
reference reader exactly.  Run this BEFORE trusting gen_cases.py output.

    python -X utf8 selfcheck_encoder.py
"""
import random, sys, copy
import ref_reader as R

random.seed(0xC0D01)


def rand_cmd(prev_t):
    c = R.Cmd()
    c.time = (prev_t + random.choice([0, 1, 16, 17, 33, 100, 255, 256, 1000])) & 0xFFFFFFFF
    c.buttons = random.choice([0, 1, 2, 4, 0x40, 0x20000, 0x200000,
                               0x20000 | 0x200000 | 4, 0x80000000, 0x20002, 0x200004])
    c.pitch = random.randrange(65536)
    c.yaw = random.randrange(65536)
    c.roll = random.randrange(65536)
    c.weapon = random.randrange(2048)
    c.word22 = random.randrange(2048)
    c.word24 = random.randrange(2048)
    c.word34 = random.randrange(2048)
    c.packed_angle = random.randrange(65536)
    c.byte32 = random.randrange(256)
    c.forward = random.choice([-1, 0, 1])
    c.right = random.choice([-1, 0, 1])
    c.extra = [random.randrange(256) for _ in range(5)]
    return c


def expected_from(cmds):
    """Mirror the reader's own semantics: conditional fields are refreshed
    only when the matching button bit is set (reader does c = old.copy())."""
    out = []
    old = R.Cmd()
    for c in cmds:
        e = copy.deepcopy(old)
        e.time = c.time & 0xFFFFFFFF
        # wire carries buttons as bit0 + 29-bit delta(old.buttons>>1)
        # => only bits 0..29 survive; bits 30/31 are unrepresentable.
        e.buttons = c.buttons & 0x3FFFFFFF
        e.pitch = c.pitch & 0xFFFF
        e.yaw = c.yaw & 0xFFFF
        e.forward = c.forward
        e.right = c.right
        e.roll = c.roll & 0xFFFF
        e.weapon = c.weapon & 0x7FF
        e.word24 = c.word24 & 0x7FF
        e.word22 = c.word22 & 0x7FF
        if c.buttons & 0x20000:
            for j in range(3):
                e.extra[j] = c.extra[j] & 0xFF
        if c.buttons & 0x200000:
            for j in range(3, 5):
                e.extra[j] = c.extra[j] & 0xFF
        if c.buttons & 4:
            e.packed_angle = c.packed_angle & 0xFFFF
            e.byte32 = c.byte32 & 0xFF
            e.word34 = c.word34 & 0x7FF
        out.append(e)
        old = e
    return out


def main():
    ok = bad = 0
    for trial in range(4000):
        key = random.randrange(0x20000000)
        n = random.randrange(1, 9)
        t = random.randrange(0, 5000)
        cmds = []
        for _ in range(n):
            c = rand_cmd(t)
            t = c.time
            cmds.append(c)
        body = R.encode_stream(cmds, key)
        got, rel = R.read_input(body, key, None)
        exp = R.canonical(expected_from(cmds))
        act = R.canonical(got)
        if exp == act and not rel:
            ok += 1
        else:
            bad += 1
            if bad <= 2:
                print("MISMATCH trial=%d key=%08X" % (trial, key))
                print("  body=", body.hex())
                print("  exp=", exp)
                print("  act=", act)
    print("selfcheck_encoder: ok=%d bad=%d" % (ok, bad))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
