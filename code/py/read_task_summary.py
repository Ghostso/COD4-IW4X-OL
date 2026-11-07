import sys, os, struct

path = r"D:\BaiduNetdiskDownload\使命召唤OL\REF_LOBBY_KIT\lobby_tasks.bin"
data = open(path, "rb").read()

offset = 0
tasks = []
while offset + 6 <= len(data):
    service = data[offset]
    task = data[offset + 1]
    length = struct.unpack_from("<I", data, offset + 2)[0]
    payload = data[offset + 6 : offset + 6 + length]
    tasks.append((service, task, payload))
    offset += 6 + length

print(f"Total tasks in lobby_tasks.bin: {len(tasks)}")
for idx in range(max(0, len(tasks) - 25), len(tasks)):
    svc, tsk, pl = tasks[idx]
    clean = "".join(chr(c) if 32 <= c < 127 else "." for c in pl[:80])
    print(f"Task {idx:02d}: service={svc:3d} task={tsk:3d} len={len(pl):4d} | {clean}")
