import re
d = open(r'run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin','rb').read()
B = 0x400000
# scan RTTI class names for bd*/Codo* related to net/dw
pat = re.compile(rb'\.\?AV[A-Za-z0-9_@?$]{3,80}@@')
seen=set()
for m in pat.finditer(d):
    s=m.group()[4:-2].decode('latin1','replace')
    if any(k in s for k in ['bd','BD','Codo','DW','Dw','Lobby','Lobby','Net','Conn','Socket','Transport','Session','Tcp','Udp','Reliable','Channel','Packet','Blaze','Match','Room','Party']):
        if s in seen: continue
        seen.add(s)
        print(s)
