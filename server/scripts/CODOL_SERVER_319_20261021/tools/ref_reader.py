"""Reference reader extracted verbatim from battle_server.py (kit), plus
an exact per-bit inverse ENCODER and a canonical formatter.
DO NOT EDIT the extracted region by hand.
"""
import struct

class _Trunc(Exception):
    pass


class _UserCommand(object):
    """照抄三方 `CodolClientCommandReader.UserCommand`。"""
    __slots__ = ("time", "buttons", "pitch", "yaw", "roll", "weapon",
                 "word22", "word24", "word34", "packed_angle", "move",
                 "byte32", "extra")

    def __init__(self):
        self.time = 0
        self.buttons = 0
        self.pitch = 0
        self.yaw = 0
        self.roll = 0
        self.weapon = 0
        self.word22 = 0
        self.word24 = 0
        self.word34 = 0
        self.packed_angle = 0
        self.move = 0
        self.byte32 = 0
        self.extra = [0] * 5

    def copy(self):
        c = _UserCommand()
        for k in _UserCommand.__slots__:
            v = getattr(self, k)
            setattr(c, k, list(v) if isinstance(v, list) else v)
        return c


class _MixedReader(object):
    """混合读写器 —— 逐行照抄 `CodolClientCommandReader.MixedReader`。

    ★ 与位写入器同源的怪癖: `Bytes()` 从 `cursor` 取并推进 cursor **不动 bit**;
      `Bits()` 只在字节对齐时把 `bit` 重置到 `cursor*8` —— 两套游标是**交错**的。
    """

    def __init__(self, data):
        self.data = data
        self.cursor = 0
        self.bit = 0

    def bits(self, n):
        v = 0
        for i in range(n):
            if (self.bit & 7) == 0:
                if self.cursor >= len(self.data):
                    raise _Trunc("Truncated bits")
                self.bit = self.cursor * 8
                self.cursor += 1
            v |= ((self.data[self.bit >> 3] >> (self.bit & 7)) & 1) << i
            self.bit += 1
        return v

    def bytes(self, n):
        if self.cursor + n > len(self.data):
            raise _Trunc("Truncated bytes")
        v = 0
        for i in range(n):
            v |= self.data[self.cursor] << (8 * i)
            self.cursor += 1
        return v

    def text(self):
        out = []
        for _ in range(1024):
            b = self.bytes(1)
            if b == 0:
                return "".join(out)
            if b < 32 or b > 126:
                raise _Trunc("Invalid command")
            out.append(chr(b))
        raise _Trunc("Command too long")

    def delta(self, old, key, width, aligned=False):
        if self.bits(1) == 0:
            return old
        v = self.bytes(width // 8) if aligned else self.bits(width)
        mask = 0xFFFFFFFF if width == 32 else ((1 << width) - 1)
        return (v ^ key) & mask


def read_reliable(data):
    """`CodolClientCommandReader.Read` —— 只解可靠命令 (seq, text)，失败即停。"""
    result = []
    cursor = 0
    state = {"bit": 0, "cursor": 0}

    def bits(width):
        value = 0
        for i in range(width):
            if (state["bit"] & 7) == 0:
                if state["cursor"] >= len(data):
                    raise _Trunc()
                state["bit"] = state["cursor"] * 8
                state["cursor"] += 1
            value |= ((data[state["bit"] >> 3] >> (state["bit"] & 7)) & 1) << i
            state["bit"] += 1
        return value

    try:
        for _ in range(512):
            if bits(3) != 2:
                break
            cursor = state["cursor"]
            if cursor + 4 > len(data):
                break
            seq = struct.unpack_from("<I", data, cursor)[0]
            cursor += 4
            start = cursor
            while cursor < len(data) and data[cursor] != 0 and cursor - start < 1024:
                if data[cursor] < 32 or data[cursor] > 126:
                    raise _Trunc()
                cursor += 1
            if cursor >= len(data) or data[cursor] != 0 or seq == 0 or seq > 1000000:
                break
            if result and seq != result[-1][0] + 1:
                break
            result.append((seq, data[start:cursor].decode("ascii", "replace")))
            cursor += 1
            state["cursor"] = cursor
    except _Trunc:
        pass
    return result


def read_input(data, key, baseline=None):
    """`CodolClientCommandReader.ReadInput` —— 返回 (用户命令列表, 可靠命令列表)。"""
    r = _MixedReader(data)
    reliable = []
    opcode = r.bits(3)
    while opcode == 2 and len(reliable) < 512:
        seq = r.bytes(4)
        text = r.text()
        if seq == 0 or seq > 1000000 or (reliable and seq != reliable[-1][0] + 1):
            raise _Trunc("Reliable sequence")
        reliable.append((seq, text))
        opcode = r.bits(3)
    result = []
    if opcode not in (0, 1):
        return result, reliable
    count = r.bytes(1)
    if count < 1 or count > 32:
        raise _Trunc("Input count")
    old = _UserCommand() if baseline is None else baseline.copy()
    for _ in range(count):
        c = old.copy()
        c.time = (old.time + r.bytes(1)) & 0xFFFFFFFF if r.bits(1) != 0 else r.bytes(4)
        if (r.bits(1) ^ (key & 1)) == 0:
            if r.bits(3) != 7:
                raise _Trunc("Idle terminator")
        else:
            full = (r.bits(1) ^ (key & 1)) != 0
            first_key = key if full else (key ^ c.time)
            c.buttons = (old.buttons & ~1) | (r.bits(1) ^ (first_key & 1))
            c.pitch = r.delta(old.pitch, first_key, 16, True) & 0xFFFF
            c.yaw = r.delta(old.yaw, first_key, 16, True) & 0xFFFF
            c.move = r.delta(old.move & 0xFFFFFFFF, first_key, 4) & 0xF
            if full:
                timed = (key ^ c.time) & 0xFFFFFFFF
                c.roll = r.delta(old.roll, timed, 16, True) & 0xFFFF
                c.buttons = ((c.buttons & 1) | ((r.delta(old.buttons >> 1, timed, 29) << 1)
                                                & 0xFFFFFFFF)) & 0xFFFFFFFF
                c.weapon = r.delta(old.weapon, timed, 11) & 0xFFFF
                c.word24 = r.delta(old.word24, timed, 11) & 0xFFFF
                c.word22 = r.delta(old.word22, timed, 11) & 0xFFFF
                if c.buttons & 0x20000:
                    for j in range(3):
                        c.extra[j] = r.delta(old.extra[j], timed, 8, True) & 0xFF
                if c.buttons & 0x200000:
                    for j in range(3, 5):
                        c.extra[j] = r.delta(old.extra[j], timed, 8, True) & 0xFF
                if c.buttons & 4:
                    c.packed_angle = r.delta(old.packed_angle, timed, 16, True) & 0xFFFF
                    c.byte32 = r.delta(old.byte32, timed, 8) & 0xFF
                    c.word34 = r.delta(old.word34, timed, 11) & 0xFFFF
            if r.bits(3) != (5 if full else 2):
                raise _Trunc("Input terminator")
        result.append(c)
        old = c
    return result, reliable



# =====================================================================
# BitWriter: exact per-bit inverse of _MixedReader (same interleaved
# cursor/bit discipline).  Mirrors the reader so that
# read_input(w.finish(), key) == the commands we encoded.
# =====================================================================
class BitWriter(object):
    def __init__(self):
        self.buf = bytearray()
        self.cursor = 0
        self.bit = 0

    def _ensure(self, idx):
        while len(self.buf) <= idx:
            self.buf.append(0)

    def bits(self, v, n):
        for i in range(n):
            if (self.bit & 7) == 0:
                self.bit = self.cursor * 8
                self.cursor += 1
            idx = self.bit >> 3
            self._ensure(idx)
            self.buf[idx] |= ((v >> i) & 1) << (self.bit & 7)
            self.bit += 1

    def bytes_(self, v, n):
        for i in range(n):
            idx = self.cursor
            self._ensure(idx)
            self.buf[idx] |= (v >> (8 * i)) & 0xFF
            self.cursor += 1

    def finish(self):
        return bytes(self.buf)


def _enc_delta(w, old_val, new_val, key, width, aligned):
    """Inverse of _MixedReader.delta: always emit the 'changed' path."""
    mask = 0xFFFFFFFF if width == 32 else ((1 << width) - 1)
    w.bits(1, 1)
    v = (new_val ^ key) & mask
    if aligned:
        w.bytes_(v, width // 8)
    else:
        w.bits(v, width)


def _move_nibble(forward, right):
    m = 0
    if forward > 0: m |= 1
    if forward < 0: m |= 2
    if right > 0:   m |= 4
    if right < 0:   m |= 8
    return m


class Cmd(object):
    __slots__ = ("time","buttons","pitch","yaw","roll","weapon",
                 "word22","word24","word34","packed_angle",
                 "forward","right","byte32","extra")
    def __init__(self, **kw):
        for k in self.__slots__:
            setattr(self, k, 0)
        self.extra = [0]*5
        for k, v in kw.items():
            setattr(self, k, v)

    def move(self):
        return _move_nibble(self.forward, self.right)


def encode_stream(cmds, key, opcode=0):
    w = BitWriter()
    w.bits(opcode, 3)
    w.bytes_(len(cmds), 1)
    old = Cmd()
    for c in cmds:
        d = (c.time - old.time) & 0xFFFFFFFF
        if 1 <= d <= 255:
            w.bits(1, 1); w.bytes_(d, 1)
        else:
            w.bits(0, 1); w.bytes_(c.time & 0xFFFFFFFF, 4)
        w.bits(1 ^ (key & 1), 1)
        full = True
        w.bits((1 if full else 0) ^ (key & 1), 1)
        first_key = key if full else (key ^ (c.time & 0xFFFFFFFF))
        w.bits((c.buttons & 1) ^ (first_key & 1), 1)
        _enc_delta(w, old.pitch, c.pitch & 0xFFFF, first_key, 16, True)
        _enc_delta(w, old.yaw,   c.yaw   & 0xFFFF, first_key, 16, True)
        _enc_delta(w, old.move(), c.move(), first_key, 4, False)
        if full:
            timed = (key ^ (c.time & 0xFFFFFFFF)) & 0xFFFFFFFF
            _enc_delta(w, old.roll, c.roll & 0xFFFF, timed, 16, True)
            _enc_delta(w, (old.buttons >> 1), (c.buttons >> 1) & 0x1FFFFFFF, timed, 29, False)
            _enc_delta(w, old.weapon, c.weapon & 0x7FF, timed, 11, False)
            _enc_delta(w, old.word24, c.word24 & 0x7FF, timed, 11, False)
            _enc_delta(w, old.word22, c.word22 & 0x7FF, timed, 11, False)
            if c.buttons & 0x20000:
                for j in range(3):
                    _enc_delta(w, old.extra[j], c.extra[j] & 0xFF, timed, 8, True)
            if c.buttons & 0x200000:
                for j in range(3, 5):
                    _enc_delta(w, old.extra[j], c.extra[j] & 0xFF, timed, 8, True)
            if c.buttons & 4:
                _enc_delta(w, old.packed_angle, c.packed_angle & 0xFFFF, timed, 16, True)
                _enc_delta(w, old.byte32, c.byte32 & 0xFF, timed, 8, False)
                _enc_delta(w, old.word34, c.word34 & 0x7FF, timed, 11, False)
        w.bits(5 if full else 2, 3)
        old = c
    return w.finish()


def canonical(cmds):
    out = []
    for c in cmds:
        mv = c.move() if callable(getattr(c, "move", None)) else (getattr(c, "move", 0) & 0xF)
        fwd = (1 if mv & 1 else 0) - (1 if mv & 2 else 0)
        rgt = (1 if mv & 4 else 0) - (1 if mv & 8 else 0)
        out.append("T%u,B%u,P%u,Y%u,R%u,W%u,A%u,H%u,X%u,K%u,F%u,S%u,B32%u,E%s" % (
            c.time & 0xFFFFFFFF, c.buttons & 0xFFFFFFFF,
            c.pitch & 0xFFFF, c.yaw & 0xFFFF, c.roll & 0xFFFF,
            c.weapon & 0xFFFF, c.word22 & 0xFFFF, c.word24 & 0xFFFF,
            c.word34 & 0xFFFF, c.packed_angle & 0xFFFF,
            fwd, rgt, c.byte32 & 0xFF,
            ",".join(str(x & 0xFF) for x in c.extra)))
    return ";".join(out)
