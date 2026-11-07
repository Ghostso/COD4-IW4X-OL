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

for idx, (svc, tsk, pl) in enumerate(tasks):
    if svc == 71 and tsk == 7:
        print(f"\n=== Task {idx}: Service 71/7 len={len(pl)} ===")
        # Look for readable strings
        # In Demonware, strings are tagged with 0x10 or pipe-separated
        s = pl.decode("latin1", errors="replace")
        for part in s.split("|"):
            if len(part) > 2:
                clean = "".join(c if 32 <= ord(c) < 127 else " " for c in part).strip()
                if clean:
                    print(f"  {clean}")
