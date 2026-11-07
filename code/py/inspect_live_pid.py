import ctypes, struct, sys, subprocess

k32 = ctypes.windll.kernel32

# Dynamically find PID of codoMP_client_shipRetail
out = subprocess.check_output(["powershell", "-NoProfile", "-Command", 
    "(Get-Process codoMP_client_shipRetail -ErrorAction SilentlyContinue).Id"], text=True).strip()

if not out:
    print("codoMP_client_shipRetail not found!")
    sys.exit(1)

pid = int(out.splitlines()[0])
print(f"Target Process PID: {pid}")

h = k32.OpenProcess(0x1F0FFF, False, pid)
if not h:
    err = k32.GetLastError()
    print(f"OpenProcess failed: {err}")
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
    err = k32.GetLastError()
    print(f"Failed to read [0x82E13FC], GetLastError={err}")
    sys.exit(1)

esi = struct.unpack("<I", raw_ptr)[0]
print(f"Matching singleton (esi) = 0x{esi:08X}")

if esi == 0:
    print("Matching singleton is NULL!")
    sys.exit(0)

# Read Gate 1: [esi + 0x278]
raw_g1 = rpm(esi + 0x278, 1)
g1 = raw_g1[0] if raw_g1 else -1

# Read Gate 2: [0x76446b0]
raw_g2 = rpm(0x76446b0, 4)
g2 = struct.unpack("<I", raw_g2)[0] if raw_g2 else -1

# Read Gate 3: [esi + 0xe360]
raw_k = rpm(esi + 0xe360, 4)
k = struct.unpack("<i", raw_k)[0] if raw_k else -999

# Read Gate 4 & 5: [esi + 0x3a048] and [esi + 0x3a04c]
raw_a = rpm(esi + 0x3a048, 4)
a_saved = struct.unpack("<I", raw_a)[0] if raw_a else 0

raw_b = rpm(esi + 0x3a04c, 4)
b_saved = struct.unpack("<I", raw_b)[0] if raw_b else 0

# Read Accepted Latch: [esi + 0x288]
raw_latch = rpm(esi + 0x288, 1)
latch = raw_latch[0] if raw_latch else -1

# Read total slots: [esi + 0x7230]
raw_slots = rpm(esi + 0x7230, 4)
total_slots = struct.unpack("<I", raw_slots)[0] if raw_slots else 0

print(f"Gate 1 [esi+0x278] (Active Flag) : {g1}")
print(f"Gate 2 [0x76446b0] (Conn State) : {g2}")
print(f"Gate 3 [esi+0xe360] (Slot index k): {k}")
print(f"Gate 4 [esi+0x3a048] (Saved A)    : {a_saved} (0x{a_saved:08X})")
print(f"Gate 5 [esi+0x3a04c] (Saved B)    : {b_saved} (0x{b_saved:08X})")
print(f"Accepted Latch [esi+0x288]       : {latch}")
print(f"Total Slots Found [esi+0x7230]   : {total_slots}")

if k >= 0 and k < 49:
    slot_base = esi + 0x7470 + k * 0x238
    print(f"\n--- Slot[{k}] Content (0x{slot_base:08X}) ---")
    slot_a = struct.unpack("<I", rpm(slot_base + 0x168, 4))[0]
    slot_b = struct.unpack("<I", rpm(slot_base + 0x16C, 4))[0]
    slot_addr_len = struct.unpack("<I", rpm(slot_base + 0x118, 4))[0]
    print(f"  Slot[{k}].A (+0x168)       : {slot_a} (0x{slot_a:08X})")
    print(f"  Slot[{k}].B (+0x16C)       : {slot_b} (0x{slot_b:08X})")
    print(f"  Slot[{k}].addr_len (+0x118): {slot_addr_len} (0x{slot_addr_len:02X})")
    if slot_addr_len == 67:
        addr_blob = rpm(slot_base + 0x18, 67)
        ip = f"{addr_blob[0]}.{addr_blob[1]}.{addr_blob[2]}.{addr_blob[3]}"
        port = struct.unpack_from("<H", addr_blob, 4)[0]
        print(f"  Slot[{k}].Endpoint         : {ip}:{port}")
    # Read string at +0x170
    str_raw = rpm(slot_base + 0x170, 64)
    token_str = str_raw.split(b"\x00")[0].decode("latin1", errors="replace")
    print(f"  Slot[{k}].Token (+0x170)   : '{token_str}'")
