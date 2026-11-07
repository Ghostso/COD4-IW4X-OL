"""Minimal room-message push encoder, built on the verified bit order.

Verified facts used (see 17_WA_ROOM_SUBSYSTEM.md §15):
  * bit stream is LSB-first
  * a message starts with  type = readBits(8)  then  readBits(3)
  * a field is   value  = readBits(8)  then  readBits(3)
  * 11/4 body sits after  0a<roomId:8B> 13 08 <len:4B> <len-4:4B>
  * room push envelope (build_room_push): service=8, senderId, name, roomId, blob, u32 0
"""


class BitWriter:
    """LSB-first bit writer; mirrors readData/readBits consumption order."""

    def __init__(self):
        self.buf = bytearray()
        self.bit = 0

    def _ensure(self, nbits):
        need = (self.bit + nbits + 7) // 8
        while len(self.buf) < need:
            self.buf.append(0)

    def write(self, value, nbits):
        self._ensure(nbits)
        for k in range(nbits):
            if (value >> k) & 1:
                self.buf[self.bit // 8] |= 1 << (self.bit % 8)
            self.bit += 1
        return self

    def data(self):
        return bytes(self.buf)


# Room message types (top-level, from the 47-entry dispatch table)
TYPE_START_GAME = 0x02
TYPE_READY = 0x10
TYPE_ROOM_INFO = 0x0F
TYPE_MEMBER_LIST = 0x0D


def frame_room_message(msg_type, fields, subtype=0):
    """msg_type(8) + subtype(3) + [value(8) + tag(3)]*  — verified bit order."""
    w = BitWriter()
    w.write(msg_type, 8)
    w.write(subtype, 3)
    for value, tag in fields:
        w.write(value, 8)
        w.write(tag, 3)
    return w.data()


def build_ready(member_id=1, is_ready=1, subtype=0):
    """dwRoomMessageReady: field1 = member id (8b), field2 = bool (8b)."""
    return frame_room_message(TYPE_READY, [(member_id & 0xFF, 0), (is_ready & 0xFF, 0)], subtype)


def build_room_info(room_id_lo=0x55667788, subtype=0):
    """dwRoomMessageRoomInfo: field1 = id (8b), then a sub-record via 0x624BF0."""
    return frame_room_message(TYPE_ROOM_INFO, [(room_id_lo & 0xFF, 0)], subtype)


def malformed_ready(member_id=1, is_ready=1):
    """MUTATED variant for the E8 contrast: truncate the trailing field.

    If the client truly parses the push, a truncated message must change its
    behaviour (reject / ignore / log). If behaviour is identical to the correct
    form, the push is being dropped before parsing.
    """
    w = BitWriter()
    w.write(TYPE_READY, 8)
    w.write(0, 3)
    w.write(member_id & 0xFF, 8)     # field 1 only; field 2 deliberately missing
    return w.data()


if __name__ == "__main__":
    for name, b in (("ready", build_ready()), ("ready-malformed", malformed_ready()),
                    ("roominfo", build_room_info())):
        print("%-16s %2d bytes  %s" % (name, len(b), b.hex(" ")))
