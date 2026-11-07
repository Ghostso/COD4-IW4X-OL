import json,re,collections,os
p=r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\EARLY_HANDLE_SCAN\hits.jsonl'
rows=[json.loads(l) for l in open(p,encoding='utf-8') if l.strip()]
ips=collections.Counter(); domains=collections.Counter(); urls=collections.Counter()
ipre=re.compile(r'(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])')
domre=re.compile(r'\b(?:[A-Za-z0-9_-]+\.)+(?:com|net|org|cn|qq|io|local|gamesafe)\b',re.I)
urlre=re.compile(r'https?://[^\s"<>]+',re.I)
for r in rows:
    t=r['text']
    for m in ipre.findall(t): ips[m]+=1
    for m in domre.findall(t): domains[m]+=1
    for m in urlre.findall(t): urls[m]+=1
print('IPs:')
for k,n in ips.most_common(): print('  %-18s %d'%(k,n))
print('\nDomains:')
for k,n in domains.most_common(80): print('  %-40s %d'%(k,n))
print('\nURLs:')
for k,n in urls.most_common(40): print('  %-80s %d'%(k,n))
