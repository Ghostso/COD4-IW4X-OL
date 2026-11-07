import sys,json,io,re
def load(p): return json.load(open(p,encoding='utf-8'))
new=load(r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\_data\syms_NEW.json')
old=load(r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\_data\syms_OLD.json')
c13=load(r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\_data\syms_1113.json')
def index(e):
    m={}
    for s in e['symbols']:
        m.setdefault(s['name'],[]).append(s)
    return m
N,O,C=index(new),index(old),index(c13)
toks=sys.argv[1:]
out=io.open(r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\_data\symquery.txt','w',encoding='utf-8',newline='\n')
for t in toks:
    rx=re.compile(t)
    out.write('\n### query: %s\n'%t)
    for lbl,M in (('NEW',N),('OLD',O),('1113',C)):
        hits=[(k,v) for k,v in M.items() if rx.search(k)]
        for k,v in sorted(hits):
            for s in v[:1]:
                out.write('  %-5s %-60s rva=0x%08x va=0x%08x sec=%s\n'%(lbl,k[:60],s['rva'],s['va'],s['section']))
out.close()
print(open(r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\_data\symquery.txt',encoding='utf-8').read())
