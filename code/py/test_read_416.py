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

for idx, (svc, tsk, pl) in enumerate(tasks):
    if svc == 71 and tsk == 7 and len(pl) == 416:
        print(f"=== Task {idx} (len={len(pl)}) ===")
        s = pl.decode("latin1", errors="replace")
        for part in s.split("|"):
            p_str = "".join(c if 32 <= ord(c) < 127 else " " for c in part).strip()
            if len(p_str) > 20 and " " not in p_str:
                try:
                    dec = base64.b64decode(p_str).decode("utf-8", errors="replace")
                    print("  [DECODED AS3 ERROR]:", dec)
                except Exception:
                    print("  ", p_str)
            else:
                print("  ", p_str)
