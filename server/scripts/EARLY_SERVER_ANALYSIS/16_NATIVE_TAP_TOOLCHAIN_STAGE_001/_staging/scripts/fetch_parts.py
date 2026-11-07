import os, sys, time, hashlib, threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests

URL = "https://downloads.sourceforge.net/mingw-w64/i686-8.1.0-release-posix-dwarf-rt_v6-rev0.7z"
TOTAL = 45050859
OUT = sys.argv[1]
PARTS = OUT + ".parts"
os.makedirs(PARTS, exist_ok=True)
CHUNK = 512 * 1024

def nparts():
    return (TOTAL + CHUNK - 1) // CHUNK

def part_path(i):
    return os.path.join(PARTS, f"p{i:04d}.bin")

def fetch(i, attempts=6):
    start = i * CHUNK
    end = min(start + CHUNK, TOTAL) - 1
    want = end - start + 1
    pp = part_path(i)
    if os.path.exists(pp) and os.path.getsize(pp) == want:
        return (i, want, "cached")
    for a in range(attempts):
        try:
            h = {"Range": f"bytes={start}-{end}", "User-Agent": "curl/8.0", "Accept": "*/*"}
            r = requests.get(URL, headers=h, stream=True, timeout=(15, 60), allow_redirects=True)
            if r.status_code != 206:
                r.raw.read()
                raise RuntimeError(f"status {r.status_code}")
            buf = bytearray()
            for c in r.iter_content(65536):
                if c:
                    buf += c
            if len(buf) != want:
                raise RuntimeError(f"short {len(buf)}/{want}")
            with open(pp, "wb") as f:
                f.write(buf)
            return (i, want, "ok")
        except Exception as e:
            last = e
            time.sleep(2 + a * 2)
    return (i, 0, f"fail:{type(last).__name__}:{last}")

def main():
    n = nparts()
    done = 0
    t0 = time.time()
    fails = []
    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = [ex.submit(fetch, i) for i in range(n)]
        for f in as_completed(futs):
            i, got, st = f.result()
            done += got
            if st.startswith("fail"):
                fails.append((i, st))
    el = time.time() - t0
    print(f"parts={n} assembled={done}/{TOTAL} secs={el:.1f} rate={done/el/1024:.1f}KB/s fails={len(fails)}")
    for i, st in fails[:10]:
        print("  FAIL", i, st)

if __name__ == "__main__":
    main()
