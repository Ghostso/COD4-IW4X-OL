import os,struct
files=[r'COD OL\GDPOpenProtocol.tdr',r'COD OL\TCLS\config\gic_cs.tdr',r'COD OL\TCLS\config\tacc_client_protocol.tdr',r'COD OL\TCLS\mmog_data.tdr',r'COD OL\Cross\Apps\VideoEditor\plat_proto.tdr',r'COD OL\TCLS\tacc_datadef.tdr']
for f in files:
    if os.path.exists(f):
        d=open(f,'rb').read(16)
        print('%-52s size=%d magic=%s ascii=%r'%(f,os.path.getsize(f),d[:4].hex(),d[:12]))
    else: print(f,'MISSING')
