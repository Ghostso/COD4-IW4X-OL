import pefile, struct, re
p = r'D:\BaiduNetdiskDownload\使命召唤OL\COD OL\codoMP_client_shipRetail.exe'
data = open(p,'rb').read()
pe = pefile.PE(p, fast_load=True)
ib = pe.OPTIONAL_HEADER.ImageBase
print('filesize', len(data), 'imagebase', hex(ib), 'size_of_image', hex(pe.OPTIONAL_HEADER.SizeOfImage))

# locate all interesting strings and their file offsets
targets = [b'config_mp.cfg', b'config.cfg', b'dwlobbyhost', b'blazehost', b'lobbyhost',
           b'dw_config', b'onlinegame', b'title_id', b'dw_nfsConfig_local_url',
           b'demonware', b'blaze', b'IIPS', b'iips', b'127.0.0.1', b'localhost']
for t in targets:
    offs = [m.start() for m in re.finditer(re.escape(t), data)]
    print('STR %-24s count=%d' % (t.decode(), len(offs)), [hex(o) for o in offs[:12]])
