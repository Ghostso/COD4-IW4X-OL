import sys, os, re, collections
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\07_PROTOCOL_BIDIRECTIONAL_TRACE\_tools")
import c_common as c

KEYS = [b"gamestate", b"Gamestate", b"GameState", b"snapshot", b"Snapshot", b"configstring", b"ConfigString",
        b"serverCommand", b"ServerCommand", b"reliable", b"Reliable", b"SV_SendMessageToClient",
        b"CL_ParseGamestate", b"CL_ParseSnapshot", b"CL_ParseServerMessage", b"svc_", b"CL_ParseServerCommand",
        b"CL_ConfigstringModified", b"EOF", b"Netchan", b"NETCHAN", b"demo", b"delta", b"cl_parse"]
def scan(path):
    im = c.load(path, name=os.path.basename(path))
    print("="*70)
    print(im.name, "size", len(im.data), "IB", hex(im.ib))
    # find ASCII strings in each section
    for key in KEYS:
        hits = []
        start = 0
        while True:
            i = im.data.find(key, start)
            if i < 0: break
            hits.append(i)
            start = i+1
            if len(hits) > 40: break
        if hits:
            print("  [%s] %d hits" % (key.decode(), len(hits)))
            for off in hits[:8]:
                # map file offset -> rva
                rva = None
                for nm, va, vsz, ptr, rsz in im.sections:
                    if rsz and ptr <= off < ptr+rsz:
                        rva = va + (off-ptr); sec=nm; break
                ctx = im.data[max(0,off-40):off+60]
                print("     off=0x%x rva=%s sec=%s :: %r" % (off, hex(rva) if rva else "?", locals().get('sec'), ctx.decode('latin1','replace')))
if __name__=="__main__":
    for p in sys.argv[1:] or [c.CLIENT_CAND]:
        scan(p)
