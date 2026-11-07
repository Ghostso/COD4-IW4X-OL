import re
p=r'COD OL\codoMP_client_shipRetailBase.dll'
d=open(p,'rb').read()
for q in [b'CA_GAMESTATE',b'gamestateupdate',b'northyaw',b'configstring',b'ConfigString',b'compass_map',b'cl_packet',b'CL_Packet',b'NET_OutOfBand',b'netchan',b'NET_',b'svc_',b'clc_']:
    n=d.count(q); print('%-18s %d'%(q.decode(),n))
