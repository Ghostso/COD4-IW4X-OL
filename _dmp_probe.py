from pathlib import Path
p=Path('COD OL/tqm/dump/GbDump.2.8975234.codomp_client_shipretail.exe.dmp.dat')
D=p.read_bytes()
print('len',len(D))
for sig in [b'MDMP',b'PAGE',b'GBD',b'TQM',b'BM']:
 print(sig, D.find(sig))
print('first',D[:256].hex(' '))
