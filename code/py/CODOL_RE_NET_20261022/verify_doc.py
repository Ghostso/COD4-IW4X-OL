p = 'CODOL_SERVER_319_20261021/docs/SESSION_20261022_CLIENT_ARCH_AND_LOBBY_CHAIN.md'
raw = open(p,'rb').read()
print('bytes', len(raw))
print('bom', raw[:3] == b'\xef\xbb\xbf')
try:
    s = raw.decode('utf-8-sig')
    print('utf8 ok, chars', len(s))
    # print first Chinese heading as unicode escapes to prove integrity
    print(ascii(s.splitlines()[0]))
    print(ascii(s.splitlines()[2]))
except Exception as e:
    print('decode fail', e)
