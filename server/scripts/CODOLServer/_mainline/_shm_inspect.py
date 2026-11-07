"""Inspect / patch the TCLS TenProxy shared-memory image used by --tenproxy-shm.

The image is published verbatim as TCLS_SHAREDMEMEMORY<pid>.  The client's
TenProxy ApplySettings (0x641600) reads the "settings text" slot (key 8, via
provider method +0x30), splits it on ';' or ':' and switches on the FIELD
COUNT:
    9 fields : [0]=auth host  [1]=auth port  [2]=lobby host [3]=lobby port ...
    7 fields : [0]=auth host  [1]=auth port  [2]=lobby host [3]=lobby port ...
    5 fields : only the auth host/port are filled, so the lobby host/port
               (0xE51184 / [0xE513D4]) stay 0 and objC has nowhere to go.

Usage:
  python -X utf8 CODOLServer/_mainline/_shm_inspect.py --text
  python -X utf8 CODOLServer/_mainline/_shm_inspect.py --make-lobby
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SUB = os.path.abspath(os.path.join(HERE, "..", "_subagents"))
SRC = os.path.join(SUB, "_tenproxy_shm.bin")
DST = os.path.join(SUB, "_tenproxy_shm_lobby.bin")

# 7 fields: auth_host ; auth_port ; lobby_host ; lobby_port ; pad...
NEW_TEXT = b"127.0.0.1;443;127.0.0.1;8444;0;0;0"


def dump(data, start, end):
    for off in range(start, end, 16):
        row = data[off:off + 16]
        print("%06X  %-47s  %s" % (
            off, " ".join("%02X" % b for b in row),
            "".join(chr(b) if 32 <= b < 127 else "." for b in row)))


def find_text(data):
    needle = b"127.0.0.1;443;"
    off = data.find(needle)
    if off < 0:
        raise SystemExit("settings text not found")
    end = data.index(b"\x00", off)
    return off, data[off:end]


def main(argv):
    data = bytearray(open(SRC, "rb").read())
    off, text = find_text(data)
    print("image      : %s (%d bytes)" % (SRC, len(data)))
    print("text offset: 0x%X  %r (%d bytes)" % (off, text, len(text)))
    print("fields     : %d" % (text.count(b";") + 1))
    print()
    print("slot bytes:")
    dump(data, off - 0x20, off + 0x40)
    print()

    if "--make-lobby" not in argv:
        return 0

    slot_cap = 0x40
    if len(NEW_TEXT) + 1 > slot_cap:
        raise SystemExit("new text does not fit")
    print("patching: %r (%d fields)" % (NEW_TEXT, NEW_TEXT.count(b";") + 1))
    data[off:off + slot_cap] = NEW_TEXT + b"\x00" * (slot_cap - len(NEW_TEXT))
    # Any length field that used to say len(old) now says len(new).
    for pos in range(off + slot_cap, off + slot_cap + 0x40, 4):
        v = struct.unpack_from("<I", data, pos)[0]
        if v == len(text):
            struct.pack_into("<I", data, pos, len(NEW_TEXT))
            print("  length field at 0x%X: %d -> %d" % (pos, v, len(NEW_TEXT)))
    with open(DST, "wb") as f:
        f.write(bytes(data))
    print("wrote " + DST)
    print()
    print("new slot bytes:")
    dump(data, off - 0x20, off + 0x60)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
