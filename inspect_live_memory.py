import ctypes, struct, sys

k32 = ctypes.windll.kernel32

pid = 9656
h = k32.OpenProcess(0x1F0FFF, False, pid)
if not h:
    print("OpenProcess failed:", k32.GetLastError())
    sys.exit(1)

def rpm(addr, size):
    buf = ctypes.create_string_buffer(size)
    read = ctypes.c_size_t(0)
    if k32.ReadProcessMemory(h, ctypes.c_void_p(addr), buf, size, ctypes.byref(read)):
        return bytes(buf.raw)
    return None

# 1. Read matching singleton pointer [0x82E13FC]
raw_ptr = rpm(0x82E13FC, 4)
if not raw_ptr:
    print("Failed to read [0x82E13FC]")
    sys.exit(1)

esi = struct.unpack("<I", raw_ptr)[0]
print("Matching singleton (esi) = 0x%08X" % esi)

if esi == 0:
    print("Matching singleton is NULL!")
    sys.exit(0)

# Read Gate 1: [esi + 0x278]
g1 = rpm(esi + 0x278, 1)[0]
# Read Gate 2: [0x76446b0]
g2 = struct.unpack("<I", rpm(0x76446b0, 4))[0]
# Read Gate 3: [esi + 0xe360]
k = struct.unpack("<i", rpm(esi + 0xe360, 4))[0]
# Read Gate 4 & 5: [esi + 0x3a048] and [esi + 0x3a04c]
a_saved = struct.unpack("<I", rpm(esi + 0x3a048, 4))[0]
b_saved = struct.unpack("<I", rpm(esi + 0x3a04c, 4))[0]
# Read Accepted Latch: [esi + 0x288]
latch = rpm(esi + 0x288, 1)[0]

print("Gate 1 [esi+0x278] (Active Flag): %d" % g1)
print("Gate 2 [0x76446b0] (Conn State): %d" % g2)
print("Gate 3 [esi+0xe360] (Slot index k): %d" % k)
print("Gate 4 [esi+0x3a048] (Saved A): %d (0x%08X)" % (a_saved, a_saved))
print("Gate 5 [esi+0x3a04c] (Saved B): %d (0x%08X)" % (b_saved, b_saved))
print("Accepted Latch [esi+0x288]: %d" % latch)

if k >= 0 and k < 49:
    slot_base = esi + 0x7470 + k * 0x238
    print("Slot[%d] Base: 0x%08X" % (k, slot_base))
    slot_a = struct.unpack("<I", rpm(slot_base + 0x168, 4))[0]
    slot_b = struct.unpack("<I", rpm(slot_base + 0x16C, 4))[0]
    slot_addr_len = struct.unpack("<I", rpm(slot_base + 0x118, 4))[0]
    print("Slot[%d].A (+0x168): %d (0x%08X)" % (k, slot_a, slot_a))
    print("Slot[%d].B (+0x16C): %d (0x%08X)" % (k, slot_b, slot_b))
    print("Slot[%d].addr_len (+0x118): %d (0x%02X)" % (k, slot_addr_len, slot_addr_len))
    if slot_addr_len == 67:
        addr_blob = rpm(slot_base + 0x18, 67)
        ip = "%d.%d.%d.%d" % (addr_blob[0], addr_blob[1], addr_blob[2], addr_blob[3])
        port = struct.unpack_from("<H", addr_blob, 4)[0]
        print("Slot[%d].Endpoint: %s:%d" % (k, ip, port))
