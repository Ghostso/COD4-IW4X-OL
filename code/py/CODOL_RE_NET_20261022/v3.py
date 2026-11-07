p='CODOL_SERVER_319_20261021/docs/SESSION_20261022_CLIENT_ARCH_AND_LOBBY_CHAIN.md'
s=open(p,encoding='utf-8',errors='replace').read()
print('chars',len(s))
print('bad',s.count('TEST3'),s.count('TEST2'),s.count('TEST-LINE'),s.count('PLACEHOLDER'))
