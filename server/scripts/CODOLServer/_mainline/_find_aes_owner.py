import os
ROOT=r'D:\BaiduNetdiskDownload\使命召唤OL\COD OL'
INV=bytes.fromhex('52096ad53036a538bf40a39e81f3d7fb7ce339829b2fff87348e4344c4dee9cb547b9432a6c2233dee4c950b42fac34e082ea16628d924b2765ba2496d8bd12572f8f66486689816d4a45ccc5d65b6926c704850fdedb9da5e154657a78d9d8490d8ab008cbcd30af7e45805b8b34506d02c1e8fca3f0f02c1afbd0301138a6b3a9111414f67dcea97f2cfcef0b4e67396ac7422e7ad3585e2f937e81c75df6e47f11a711d29c5896fb7620eaa18be1bfc563e4bc6d279209adbc0fe78cd5af41fdda8338807c731b11210592780ec5f60517fa919b54a0d2de57a9f93c99cefa0e03b4dae2af5b0c8ebbb3c83539961172b047eba77d626e169146355210c7d')
FWD=bytes.fromhex('637c777bf26b6fc53001672bfed7ab76ca82c97dfa5947f0add4a2af9ca472c0b7fd9326363ff7cc34a5e5f171d8311504c723c31896059a071280e2eb27b27509832c1a1b6e5aa0523bd6b329e32f8453d100ed20fcb15b6acbbe394a4c58cfd0efaafb434d338545f9027f503c9fa851a3408f929d38f5bcb6da2110fff3d2cd0c13ec5f974417c4a77e3d645d197360814fdc222a908846eeb814de5e0bdbe0323a0a4906245cc2d3ac629195e479e7c8376d8dd54ea96c56f4ea657aae08ba78252e1ca6b4c6e8dd741f4bbd8b8a703eb5664803f60e613557b986c11d9ee1f8981169d98e949b1e87e9ce5528df8ca1890dbfe6426841992d0fb054bb16')
for rel in ['IIPS\\iips.dll','IIPS\\IIPSHost.dll','IIPS\\p2papp.dll','IIPS\\IIPSLaunchRestore.dll','IIPS\\Tenio\\ScriptManager.dll','Cross\\CrossShell.dll','Cross\\CrossProxy.exe','tqm\\TQMCenter.exe','tqm\\SSOPlatform.dll','Cross\\ProtocalHandler.dll']:
    p=os.path.join(ROOT,rel)
    if not os.path.isfile(p): continue
    d=open(p,'rb').read()
    inv=[hex(i) for i in range(len(d)) if d.startswith(INV,i)][:3]
    fwd=[hex(i) for i in range(len(d)) if d.startswith(FWD,i)][:3]
    print('%-32s size=%8d inv=%s fwd=%s qos=%d 8081=%d'%(rel,len(d),inv or '-',fwd or '-',d.count(b'qos'),d.count(b'8081')))
