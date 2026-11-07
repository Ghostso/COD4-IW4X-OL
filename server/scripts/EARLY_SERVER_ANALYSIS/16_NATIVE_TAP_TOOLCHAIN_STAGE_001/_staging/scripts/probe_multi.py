import sys, time
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests

PATH = "project/mingw-w64/Toolchains%20targetting%20Win32/Personal%20Builds/mingw-builds/8.1.0/threads-posix/dwarf/i686-8.1.0-release-posix-dwarf-rt_v6-rev0.7z"
TOTAL = 45050859
CHUNK = 512*1024
H = {"User-Agent": "curl/8.0", "Accept": "*/*"}

def one(url, start, end, timeout):
    h = dict(H); h["Range"] = f"bytes={start}-{end}"
    t0 = time.time(); n = 0; code = None
    r = requests.get(url, headers=h, stream=True, timeout=timeout)
    code = r.status_code
    for c in r.iter_content(65536):
        n += len(c)
    return code, n, time.time()-t0

def probe(mirror, workers=12, chunk=CHUNK, budget=25.0):
    url = f"https://{mirror}.dl.sourceforge.net/{PATH}"
    jobs = [(url, i*chunk, min((i+1)*chunk, TOTAL)-1) for i in range(workers)]
    tot = 0; ok = 0; errs = {}
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = [ex.submit(one, u, s, e, budget) for (u, s, e) in jobs]
        for f in as_completed(futs):
            try:
                code, n, dt = f.result()
                tot += n
                if code == 206: ok += 1
                else: errs[f"HTTP{code}"] = errs.get(f"HTTP{code}", 0)+1
            except Exception as e:
                k = type(e).__name__; errs[k] = errs.get(k, 0)+1
    el = time.time()-t0
    print(f"{mirror:18} w={workers} bytes={tot:>9} secs={el:5.1f} agg={tot/max(el,0.1)/1024:7.1f}KB/s ok={ok} err={errs}", flush=True)
    return tot/max(el,0.1)/1024

if __name__ == "__main__":
    mirrors = sys.argv[1:]
    for m in mirrors:
        try:
            probe(m)
        except Exception as e:
            print(f"{m:18} probe-fail {e}", flush=True)
