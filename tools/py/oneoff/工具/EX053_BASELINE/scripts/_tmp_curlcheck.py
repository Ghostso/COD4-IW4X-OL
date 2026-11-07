# -*- coding: utf-8 -*-
import sys, os, re
sys.path.insert(0, os.path.abspath('scripts'))
from pe import Image
img = Image()
data = img.data

a, b = 0x7ac900, 0x7ad200
print('--- .rdata 串邻域 RVA 0x%x..0x%x ---' % (a, b))
for m in re.finditer(rb'[\x20-\x7e]{6,}', data[a:b]):
    print('  0x%08x  %s' % (a + m.start(), m.group(0).decode('latin-1')[:100]))
print()
pats = [b'libcurl', b'curl_easy', b'CURLOPT', b'curl_version', b'curl/', b'SSL certificate', b'schannel', b'OpenSSL', b'multi.c', b'sendf.c', b'connect.c', b'hostip.c', b'http.c', b'urlapi']
for pat in pats:
    ms = list(re.finditer(re.escape(pat), data))
    print('  %-16s %d' % (pat.decode('latin-1'), len(ms)))
    for m in ms[:5]:
        s = data[max(0, m.start()-40): m.start()+70]
        s = re.sub(rb'[^\x20-\x7e]', b'.', s)
        print('       0x%08x  %s' % (m.start(), s.decode('latin-1')))
