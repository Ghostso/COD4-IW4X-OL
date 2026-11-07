import os, sys, time, hashlib, json
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests

TOTAL = 45050859
CHUNK = 512 * 1024
MIRRORS = [
    "phoenixnap", "gigenet", "pilotfiber", "netix", "twds", "master",
]
SF_PATH = "project/mingw-w64/Toolchains%20targetting%20Win32/Personal%20Builds/mingw-builds/8.1.0/threads-posix/dwarf/i686-8.1.0-release-posix-dwarf-rt_v6-rev0.7z"
CANONICAL = "https://downloads.sourceforge.net/mingw-w64/i686-8.1.0-release-posix-dwarf-rt_v6-rev0.7z"

OUT = sys.argv[1]
WORKERS = int(sys.argv[2]) if len(sys.argv) > 2 else 24
PARTS = OUT + ".parts"
PROGRESS = OUT + ".progress"
os.makedirs(PARTS, exist_ok=True)

def mirror_url(m):
    if m == "canonical":
        return CANONICAL
    return f"https://{m}.dl.sourceforge.net/{SF_PATH}"

def nparts():
    return (TOTAL + CHUNK - 1) // CHUNK

def part_path(i):
    return os.path.join(PARTS, f"p{i:05d}.bin")

def fetch(i, attempts=8):
    start = i * CHUNK
    end = min(start + CHUNK, TOTAL) - 1
    want = end - start + 1
    pp = part_path(i)
    if os.path.exists(pp) and os.path.getsize(pp) == want:
        return (i, want, "cached")
    last = None
    for a in range(attempts):
        m = MIRRORS[(i + a) % len(MIRRORS)]
        url = mirror_url(m)
        try:
            h = {"Range": f"bytes={start}-{end}", "User-Agent": "curl/8.0", "Accept": "*/*"}
            r = requests.get(url, headers=h, stream=True, timeout=(15, 45), allow_redirects=True)
            if r.status_code != 206:
                r.close()
                raise RuntimeError(f"HTTP {r.status_code} via {m}")
            buf = bytearray()
            for c in r.iter_content(65536):
                if c:
                    buf += c
            if len(buf) != want:
                raise RuntimeError(f"short {len(buf)}/{want} via {m}")
            tmp = pp + ".tmp"
            with open(tmp, "wb") as f:
                f.write(buf)
            os.replace(tmp, pp)
            return (i, want, "ok")
        except Exception as e:
            last = e
            time.sleep(min(1.0 + a * 1.5, 8.0))
    return (i, 0, f"fail:{type(last).__name__}:{last}")

def main():
    n = nparts()
    done = [0]
    fails = []
    t0 = time.time()
    last_report = t0
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = {ex.submit(fetch, i): i for i in range(n)}
        for f in as_completed(futs):
            i, got, st = f.result()
            done[0] += got
            if st.startswith("fail"):
                fails.append((i, st))
            now = time.time()
            if now - last_report >= 20:
                el = now - t0
                pct = 100.0 * done[0] / TOTAL
                rate = done[0] / el / 1024
                eta = (TOTAL - done[0]) / max(done[0] / el, 1)
                msg = f"{time.strftime('%H:%M:%S')} done={done[0]}/{TOTAL} ({pct:.1f}%) rate={rate:.1f}KB/s eta={eta/60:.1f}min fails={len(fails)}"
                print(msg, flush=True)
                with open(PROGRESS, "a", encoding="utf-8") as lf:
                    lf.write(msg + "\n")
                last_report = now
    print(f"DOWNLOAD_DONE parts={n} assembled={done[0]}/{TOTAL} fails={len(fails)}", flush=True)
    for i, st in fails[:20]:
        print("  FAIL", i, st, flush=True)
    sys.exit(0 if (done[0] == TOTAL and not fails) else 2)

if __name__ == "__main__":
    main()
