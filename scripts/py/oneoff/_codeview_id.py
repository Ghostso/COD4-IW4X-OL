import os,re
from pathlib import Path
D=Path('COD OL/codoMP_client_shipRetail.exe').read_bytes()
# parse CodeView RSDS only
idx=D.find(b'RSDS')
if idx>=0:
 import struct,uuid
 guid=b= None
 if idx+24<=len(D):
  g1,g2,g3,g4=struct.unpack_from('<IHH8s',D,idx+4)
  age=struct.unpack_from('<I',D,idx+20)[0]
  end=D.find(b'\0',idx+24)
  path=D[idx+24:end].decode('latin1','replace')
  guid=f'{g1:08X}{g2:04X}{g3:04X}{g4.hex().upper()}'
  print('PDB_PATH',path)
  print('PDB_GUID',guid)
  print('PDB_AGE',age)
  print('CODEVIEW_OFFSET',hex(idx))
