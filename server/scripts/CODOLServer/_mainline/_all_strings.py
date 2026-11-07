import re, os
p = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\ENGINE_DUMP_20260925_111537\engine\engine_best.bin'
b = open(p,'rb').read()
base = 0x00994000
ascii_rows=[]
for m in re.finditer(rb'[\x20-\x7e]{5,}', b):
    s=m.group().decode('ascii','replace')
    ascii_rows.append((base+m.start(),s))
print('ascii strings >=5:', len(ascii_rows))
for va,s in ascii_rows:
    low=s.lower()
    if any(k in low for k in ['config','lobby','blaze','demonware','dvar','host','port','server','http','iips','qos','stun','match','party','master','login','auth','ticket','session','online','codol','tencent','qq.com','127.0.0.1','localhost','connect','socket']):
        print('%08x %s' % (va,s[:180]))
