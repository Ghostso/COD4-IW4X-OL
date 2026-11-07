import os, re
p = r'C:\Users\Z7-CT5N1\AppData\Local\OpenAI\Codex\bin\896a0166b774037a\codex.exe'
data = open(p, 'rb').read()
keys = [b'stream_idle_timeout', b'idle_timeout', b'request_max_retries', b'stream_max_retries', b'request_timeout', b'connect_timeout']
for k in keys:
    occ = [m.start() for m in re.finditer(re.escape(k), data)]
    print('==', k.decode(), 'occurrences:', len(occ))
    for o in occ[:3]:
        s = max(0, o - 120); e = min(len(data), o + 120)
        chunk = ''.join(chr(c) if 32 <= c < 127 else '.' for c in data[s:e])
        print('   ...', chunk)
