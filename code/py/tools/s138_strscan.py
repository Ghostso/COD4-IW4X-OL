import re
d = open(r'E:\codol_re\client_image_20261027.bin', 'rb').read()
pats = [b'connect', b'sv_port', b'net_port', b'party_port', b'net_ip',
        b'qport', b'netchan', b'NET_', b'net_', b'port']
for p in pats:
    idx = [m.start() for m in re.finditer(re.escape(p), d)]
    print(p, len(idx), [hex(i) for i in idx[:10]])
