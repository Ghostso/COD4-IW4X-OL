import struct, re
p = r'COD OL\codoMP_client_shipRetailBase.dll'
d = open(p,'rb').read()
base_rva = 0xb02000; raw = 0xaf7c00
names = []
for i in range(760):
    off = raw + i*4
    rva = struct.unpack_from('<I', d, off)[0]
    if not (0xb02000 <= rva < 0xb07000):
        break
    o = raw + (rva - base_rva)
    hint = struct.unpack_from('<H', d, o)[0]
    e = d.find(b'\x00', o+2)
    nm = d[o+2:e].decode('latin1','replace')
    names.append((i, 0x10b02000+i*4, rva, hint, nm))
print('entries', len(names))
pat = re.compile(r'^(connect|WSAConnect|ConnectEx|send|sendto|WSASend|WSASendTo|recv|recvfrom|WSARecv|WSARecvFrom|socket|WSASocketW|WSASocketA|bind|listen|accept|WSAAccept|select|ioctlsocket|WSAIoctl|getaddrinfo|gethostbyname|closesocket|shutdown|setsockopt|getsockopt|getpeername|getsockname|htons|ntohs|inet_addr|inet_ntoa|WSAEventSelect|WSAEnumNetworkEvents|WSAWaitForMultipleEvents|WSACreateEvent|WSACloseEvent|WSAResetEvent|WSASetEvent|WSAStartup|WSACleanup)\$', re.I)
for i, slot, rva, hint, nm in names:
    if pat.match(nm):
        print('  idx=%3d slot=%#010x hint=%-5d %s' % (i, slot, hint, nm))
print('\nall sock-ish names:')
for i, slot, rva, hint, nm in names:
    if any(k in nm.lower() for k in ['sock','connect','send','recv','wsa']):
        print('   ' + nm)
