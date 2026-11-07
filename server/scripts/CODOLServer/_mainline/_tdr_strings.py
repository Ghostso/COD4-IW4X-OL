import os,re
files=[r'D:\BaiduNetdiskDownload\使命召唤OL\COD OL\GDPOpenProtocol.tdr',r'D:\BaiduNetdiskDownload\使命召唤OL\COD OL\Cross\mmog_data.tdr',r'D:\BaiduNetdiskDownload\使命召唤OL\COD OL\TCLS\mmog_data.tdr',r'D:\BaiduNetdiskDownload\使命召唤OL\COD OL\TCLS\tacc_datadef.tdr',r'D:\BaiduNetdiskDownload\使命召唤OL\COD OL\TCLS\config\gic_cs.tdr',r'D:\BaiduNetdiskDownload\使命召唤OL\COD OL\TCLS\config\tacc_client_protocol.tdr']
for p in files:
    d=open(p,'rb').read()
    print('\n#####',os.path.basename(p),len(d))
    # ascii
    a=[m.group().decode('ascii','replace') for m in re.finditer(rb'[\x20-\x7e]{4,}',d)]
    u=[]
    for m in re.finditer(rb'(?:[\x20-\x7e]\x00){4,}',d):
        u.append(m.group().decode('utf-16-le','replace'))
    print('ASCII:',a[:60])
    print('UTF16:',u[:80])
