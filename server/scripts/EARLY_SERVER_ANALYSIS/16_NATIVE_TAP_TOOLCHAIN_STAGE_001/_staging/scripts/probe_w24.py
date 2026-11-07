import sys, time
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
PATH = "project/mingw-w64/Toolchains%20targetting%20Win32/Personal%20Builds/mingw-builds/8.1.0/threads-posix/dwarf/i686-8.1.0-release-posix-dwarf-rt_v6-rev0.7z"
TOTAL = 45050859; CHUNK = 512*1024
H = {"User-Agent": "curl/8.0", "Accept": "*/*"}
def one(url, start, end, timeout):
    h = dict(H); h["Range"] = f"bytes={start}-{end}"
    n = 0
    r = requests.get(url, headers=h, stream=True, timeout=timeout)
    for c in r.iter_content(65536): n += len(c)
    return r.status_code, n
def probe(mirror, workers, budget):
    url = f"https://{mirror}.dl.sourceforge.net/{PATH}"
    jobs = [(url, i*CHUNK, min((i+1)*CHUNK, TOTAL)-1) for i in range(workers)]
    tot=0; ok=0; errs={}; t0=time.time()
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs=[ex.submit(one,u,s,e,budget) for (u,s,e) in jobs]
        for f in as_completed(futs):
            try:
                c,n=f.result(); tot+=n
                if c==206: ok+=1
                else: errs[f"H{c}"]=errs.get(f"H{c}",0)+1
            except Exception as e:
                k=type(e).__name__; errs[k]=errs.get(k,0)+1
    el=time.time()-t0
    print(f"{mirror:14} w={workers:3} bytes={tot:>9} secs={el:5.1f} agg={tot/max(el,0.1)/1024:7.1f}KB/s ok={ok} err={errs}", flush=True)
if __name__=="__main__":
    for m in sys.argv[1:]:
        try: probe(m, 24, 30.0)
        except Exception as e: print(m,"fail",e)
