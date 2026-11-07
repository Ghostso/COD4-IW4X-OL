import sys,re,json,hashlib
def strings(data, mn=4):
    # ascii printable runs
    out=set()
    for m in re.finditer(rb'[\x20-\x7e]{%d,}'%mn, data):
        out.add(m.group().decode('latin1'))
    for m in re.finditer(rb'(?:[\x20-\x7e]\x00){%d,}'%mn, data):
        try: out.add(m.group().decode('utf-16-le'))
        except Exception: pass
    return out
if __name__=='__main__':
    src=sys.argv[1]; dst=sys.argv[2]
    d=open(src,'rb').read()
    s=strings(d)
    with open(dst,'w',encoding='utf-8') as f:
        for x in sorted(s): f.write(x+'\n')
    print('strings', len(s), '->', dst)
