import random, sys, copy
import ref_reader as R

OUT = sys.argv[1] if len(sys.argv) > 1 else "cases.txt"
random.seed(0x51ED)

def add_rel(w, seq, text):
    w.bits(2, 3)
    w.bytes_(seq, 4)
    for ch in text:
        w.bytes_(ord(ch), 1)
    w.bytes_(0, 1)

def encode_with_reliable(cmds, key, reliable):
    w = R.BitWriter()
    for seq, text in reliable:
        add_rel(w, seq, text)
    # now the normal opcode+count path, but reusing the same writer state
    w.bits(0, 3)
    w.bytes_(len(cmds), 1)
    old = R.Cmd()
    for c in cmds:
        d = (c.time - old.time) & 0xFFFFFFFF
        if 1 <= d <= 255:
            w.bits(1, 1); w.bytes_(d, 1)
        else:
            w.bits(0, 1); w.bytes_(c.time & 0xFFFFFFFF, 4)
        w.bits(1 ^ (key & 1), 1)
        w.bits(1 ^ (key & 1), 1)
        first_key = key
        w.bits((c.buttons & 1) ^ (first_key & 1), 1)
        R._enc_delta(w, old.pitch, c.pitch & 0xFFFF, first_key, 16, True)
        R._enc_delta(w, old.yaw,   c.yaw   & 0xFFFF, first_key, 16, True)
        R._enc_delta(w, old.move(), c.move(), first_key, 4, False)
        timed = (key ^ (c.time & 0xFFFFFFFF)) & 0xFFFFFFFF
        R._enc_delta(w, old.roll, c.roll & 0xFFFF, timed, 16, True)
        R._enc_delta(w, (old.buttons >> 1), (c.buttons >> 1) & 0x1FFFFFFF, timed, 29, False)
        R._enc_delta(w, old.weapon, c.weapon & 0x7FF, timed, 11, False)
        R._enc_delta(w, old.word24, c.word24 & 0x7FF, timed, 11, False)
        R._enc_delta(w, old.word22, c.word22 & 0x7FF, timed, 11, False)
        if c.buttons & 0x20000:
            for j in range(3): R._enc_delta(w, old.extra[j], c.extra[j] & 0xFF, timed, 8, True)
        if c.buttons & 0x200000:
            for j in range(3, 5): R._enc_delta(w, old.extra[j], c.extra[j] & 0xFF, timed, 8, True)
        if c.buttons & 4:
            R._enc_delta(w, old.packed_angle, c.packed_angle & 0xFFFF, timed, 16, True)
            R._enc_delta(w, old.byte32, c.byte32 & 0xFF, timed, 8, False)
            R._enc_delta(w, old.word34, c.word34 & 0x7FF, timed, 11, False)
        w.bits(5, 3)
        old = c
    return w.finish()

def rand_cmd(prev_t):
    c = R.Cmd()
    c.time = (prev_t + random.choice([0, 1, 16, 17, 33, 100, 255, 256, 1000])) & 0xFFFFFFFF
    c.buttons = random.choice([0, 1, 2, 4, 0x40, 0x20000, 0x200000,
                               0x20000|0x200000|4, 0x20002, 0x200004, 0x40000000])
    c.pitch = random.randrange(65536)
    c.yaw   = random.randrange(65536)
    c.roll  = random.randrange(65536)
    c.weapon = random.randrange(2048)
    c.word22 = random.randrange(2048)
    c.word24 = random.randrange(2048)
    c.word34 = random.randrange(2048)
    c.packed_angle = random.randrange(65536)
    c.byte32 = random.randrange(256)
    c.forward = random.choice([-1, 0, 1])
    c.right   = random.choice([-1, 0, 1])
    c.extra = [random.randrange(256) for _ in range(5)]
    return c

def expected_from(cmds):
    out = []; old = R.Cmd()
    for c in cmds:
        e = copy.deepcopy(old)
        e.time = c.time & 0xFFFFFFFF
        e.buttons = c.buttons & 0x3FFFFFFF
        e.pitch = c.pitch & 0xFFFF
        e.yaw = c.yaw & 0xFFFF
        e.forward = c.forward; e.right = c.right
        e.roll = c.roll & 0xFFFF
        e.weapon = c.weapon & 0x7FF
        e.word24 = c.word24 & 0x7FF
        e.word22 = c.word22 & 0x7FF
        if c.buttons & 0x20000:
            for j in range(3): e.extra[j] = c.extra[j] & 0xFF
        if c.buttons & 0x200000:
            for j in range(3, 5): e.extra[j] = c.extra[j] & 0xFF
        if c.buttons & 4:
            e.packed_angle = c.packed_angle & 0xFFFF
            e.byte32 = c.byte32 & 0xFF
            e.word34 = c.word34 & 0x7FF
        out.append(e); old = e
    return out

lines = []
for trial in range(600):
    key = random.randrange(0x20000000)
    n = random.randrange(1, 9)
    t = random.randrange(0, 5000)
    cmds = []
    for i in range(n):
        c = rand_cmd(t); t = c.time; cmds.append(c)
    reliable = []
    if random.random() < 0.25:
        for k in range(random.randrange(1, 3)):
            reliable.append((100 + k, random.choice(
                ["mr 1 1 custom2", "mr 2 0 custom1", "vs 3", "mr 5 1 custom3"])))
    body = encode_with_reliable(cmds, key, reliable)
    # self-validate with the reference reader before emitting
    got, rel = R.read_input(body, key, None)
    exp = R.canonical(expected_from(cmds))
    act = R.canonical(got)
    if exp != act:
        print("GEN SELFCHECK MISMATCH trial=%d" % trial)
        print("  body=", body.hex()); print("  exp=", exp); print("  act=", act)
        sys.exit(2)
    lines.append("%08X %s %s" % (key, body.hex(), exp))

open(OUT, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
print("wrote %d cases to %s (all self-validated against the reference reader)" % (len(lines), OUT))
