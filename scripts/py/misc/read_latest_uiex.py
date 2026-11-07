import sys, os, struct, base64

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

# Find all UIException in the latest 30 tasks
for idx in range(max(0, len(tasks) - 30), len(tasks)):
    svc, tsk, pl = tasks[idx]
    if svc == 71 and tsk == 7 and b"UIException" in pl:
        s = pl.decode("latin1", errors="replace")
        parts = s.split("|")
        print(f"\n--- Task {idx} UIException ---")
        for p in parts:
            p_str = "".join(c if 32 <= ord(c) < 127 else " " for c in p).strip()
            # check if base64
            if len(p_str) > 20 and not " " in p_str:
                try:
                    dec_b64 = base64.b64decode(p_str).decode("utf-8", errors="replace")
                    print(f"  [DECODED B64] {dec_b64}")
                except Exception:
                    print(f"  {p_str}")
            else:
                print(f"  {p_str}")
