import re,os
p=r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\ENGINE_DUMP_20260925_114204\engine\runtime_strings.bin'
b=open(p,'rb').read(); base=0x00CD0000
for m in re.finditer(rb'[\x20-\x7e]{5,}',b):
    s=m.group().decode('ascii','replace'); low=s.lower()
    if any(k in low for k in ['config','lobby','blaze','demonware','dvar','server','host','port','http','iips','qos','stun','match','party','master','login','auth','ticket','session','online','codol','tencent','qq.com','connect','socket','iw4','zone','playlist']):
        print('%08x %s'%(base+m.start(),s[:200]))
