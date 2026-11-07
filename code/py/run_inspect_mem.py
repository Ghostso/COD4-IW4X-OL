import sys, os, struct, json, socket

# We can run a script via elevated_agent to read process memory of PID 9656
# Let's inspect elevated_agent.py protocol
STATE = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\logs\elevated_agent.json"
st = json.load(open(STATE, encoding="utf-8"))

# Code to run inside elevated process
inspect_code = '''
import ctypes, struct
k32 = ctypes.windll.kernel32

pid = 9656
h = k32.OpenProcess(0x1F0FFF, False, pid)
if not h:
    print(f"OpenProcess failed: {k32.GetLastError()}")
    import sys; sys.exit(1)

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
    import sys; sys.exit(1)

esi = struct.unpack("<I", raw_ptr)[0]
print(f"Matching singleton (esi) = 0x{esi:08X}")

if esi == 0:
    print("Matching singleton is NULL!")
    import sys; sys.exit(0)

# Read Gate 1: [esi + 0x278]
g1 = rpm(esi + 0x278, 1)[0]
# Read Gate 2: [0x76446b0]
g2 = struct.unpack("<I", rpm(0x76446b0, 4))[0]
# Read Gate 3: [esi + 0xe360]
k = struct.unpack("<i", rpm(esi + 0xe360, 4))[0]
# Read Gate 4 & 5: [esi + 0x3a048] and [esi + 0x3a04c]
a_saved = struct.unpack("<I", rpm(esi + 0x3a048, 4))[0]
b_saved = struct.unpack("<I", rpm(esi + 0x3a04c, 4))[0]

print(f"Gate 1 [esi+0x278] (Active Flag): {g1}")
print(f"Gate 2 [0x76446b0] (Conn State): {g2}")
print(f"Gate 3 [esi+0xe360] (Slot index k): {k}")
print(f"Gate 4 [esi+0x3a048] (Saved A): {a_saved} (0x{a_saved:08X})")
print(f"Gate 5 [esi+0x3a04c] (Saved B): {b_saved} (0x{b_saved:08X})")

if k >= 0 and k < 49:
    slot_base = esi + 0x7470 + k * 0x238
    print(f"\nSlot[{k}] Base: 0x{slot_base:08X}")
    slot_a = struct.unpack("<I", rpm(slot_base + 0x168, 4))[0]
    slot_b = struct.unpack("<I", rpm(slot_base + 0x16C, 4))[0]
    slot_addr_len = struct.unpack("<I", rpm(slot_base + 0x118, 4))[0]
    print(f"Slot[{k}].A (+0x168): {slot_a} (0x{slot_a:08X})")
    print(f"Slot[{k}].B (+0x16C): {slot_b} (0x{slot_b:08X})")
    print(f"Slot[{k}].addr_len (+0x118): {slot_addr_len} (0x{slot_addr_len:02X})")
    if slot_addr_len == 67:
        addr_blob = rpm(slot_base + 0x18, 67)
        ip = f"{addr_blob[0]}.{addr_blob[1]}.{addr_blob[2]}.{addr_blob[3]}"
        port = struct.unpack_from("<H", addr_blob, 4)[0]
        print(f"Slot[{k}].Endpoint: {ip}:{port}")
'''

# Write script to temp file
script_path = os.path.abspath(r"D:\BaiduNetdiskDownload\使命召唤OL\inspect_live_memory.py")
with open(script_path, "w", encoding="utf-8") as f:
    f.write(inspect_code)

req = {
    "token": st["token"],
    "action": "run",
    "argv": [sys.executable, "-X", "utf8", script_path],
    "cwd": r"D:\BaiduNetdiskDownload\使命召唤OL",
    "timeout": 30
}

s = socket.create_connection(("127.0.0.1", int(st["port"])), timeout=30)
s.sendall((json.dumps(req) + "\n").encode("utf-8"))
data = b""
while not data.endswith(b"\n"):
    chunk = s.recv(65536)
    if not chunk: break
    data += chunk
s.close()

resp = json.loads(data.decode("utf-8"))
print(resp.get("stdout"))
if resp.get("stderr"):
    print("STDERR:", resp.get("stderr"))
