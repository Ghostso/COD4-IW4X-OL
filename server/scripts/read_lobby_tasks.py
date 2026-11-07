import sys, os, struct

path = r"D:\BaiduNetdiskDownload\使命召唤OL\REF_LOBBY_KIT\lobby_tasks.bin"
if not os.path.exists(path):
    print("lobby_tasks.bin not found")
    sys.exit(0)

data = open(path, "rb").read()
print(f"Total lobby_tasks.bin size: {len(data)} bytes")

offset = 0
tasks = []
while offset + 6 <= len(data):
    service = data[offset]
    task = data[offset + 1]
    length = struct.unpack_from("<I", data, offset + 2)[0]
    payload = data[offset + 6 : offset + 6 + length]
    tasks.append((service, task, payload))
    offset += 6 + length

print(f"Total tasks recorded: {len(tasks)}")
# Let's inspect the last 15 tasks
for svc, tsk, pl in tasks[-15:]:
    printable = "".join(chr(c) if 32 <= c < 127 else "." for c in pl)
    print(f"Service {svc}/{tsk} len={len(pl)}: {printable[:100]}")
    if b"UIException" in pl:
        print("\n=== FULL UIEXCEPTION ===")
        # decode latin1
        try:
            print(pl.decode("latin1"))
        except Exception as e:
            print(pl)
        print("========================\n")
