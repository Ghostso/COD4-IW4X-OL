import time, sys
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests

PATH = "project/mingw-w64/Toolchains%20targetting%20Win32/Personal%20Builds/mingw-builds/8.1.0/threads-posix/dwarf/i686-8.1.0-release-posix-dwarf-rt_v6-rev0.7z"
TOTAL = 45050859
CHUNK = 1024*1024
def mirror_url(m):
    return f"https://{m}.dl.sourceforge.net/{PATH}"

def fetch_range(args):
    url, start, end = args
    h = {"Range": f"bytes={start}-{end}", "User-Agent": "curl/8.0"}
    t0 = time.time()
    r = requests.get(url, headers=h, stream=True, timeout=30)
    n = 0
    for c in r.iter_content(65536):
        n += len(c)
    return (start, r.status_code, n, time.time()-t0)

def probe(mirror, n=8):
    url = mirror_url(mirror)
    jobs = [(url, i*CHUNK, min((i+1)*CHUNK, TOTAL)-1) for i in range(n)]
    t0 = time.time()
    tot = 0; codes = {}
    with ThreadPoolExecutor(max_workers=n) as ex:
        futs = [ex.submit(fetch_range, j) for j in jobs]
        for f in as_completed(futs):
            try:
                s, code, nb, dt = f.result()
                tot += nb
                codes[code] = codes.get(code, 0) + 1
            except Exception as e:
                codes[f"ERR:{type(e).__name__}"] = codes.get(f"ERR:{type(e).__name__}", 0) + 1
    el = time.time()-t0
    print(f"{mirror:16} n={n} bytes={tot} secs={el:.1f} agg={tot/el/1024:.1f}KB/s codes={codes}")

if __name__ == "__main__":
    for m in sys.argv[1:]:
        try:
            probe(m)
        except Exception as e:
            print(f"{m:16} probe failed: {e}")
