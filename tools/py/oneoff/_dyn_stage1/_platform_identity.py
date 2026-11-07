import hashlib, os, struct
paths = [
    r".\WeGame\wegame.exe",
    r".\WeGame\tgp_daemon.exe",
    r".\COD OL\WeGameLauncher\launcher.exe",
    r".\COD OL\TCLS\Client.exe",
    r".\COD OL\codoMP_client_shipRetail.exe",
]
for p in paths:
    if not os.path.exists(p):
        print(p, "MISSING")
        continue
    data = open(p, "rb").read()
    print(p)
    print("  size", len(data))
    print("  sha256", hashlib.sha256(data).hexdigest())
    if len(data) >= 0x40 and data[:2] == b"MZ":
        peoff = struct.unpack_from("<I", data, 0x3c)[0]
        if peoff + 0x5c <= len(data) and data[peoff:peoff+4] == b"PE\0\0":
            ts = struct.unpack_from("<I", data, peoff + 8)[0]
            nsec = struct.unpack_from("<H", data, peoff + 6)[0]
            optsz = struct.unpack_from("<H", data, peoff + 20)[0]
            magic = struct.unpack_from("<H", data, peoff + 24)[0]
            ep = struct.unpack_from("<I", data, peoff + 24 + 16)[0]
            image = struct.unpack_from("<I", data, peoff + 24 + 56)[0]
            print("  timestamp", hex(ts), "sections", nsec, "entrypoint", hex(ep), "sizeofimage", hex(image), "optmagic", hex(magic))

a = open(paths[0], "rb").read()
b = open(paths[1], "rb").read()
n = min(len(a), len(b))
diffs = [i for i in range(n) if a[i] != b[i]]
print("WEGAME_DAEMON_COMPARE")
print("  same_hash", hashlib.sha256(a).digest() == hashlib.sha256(b).digest())
print("  same_size", len(a) == len(b))
print("  differing_byte_count", len(diffs))
print("  first_diffs", [hex(i) for i in diffs[:64]])
print("  last_diffs", [hex(i) for i in diffs[-64:]])
