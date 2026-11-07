# -*- coding: utf-8 -*-
"""端到端: Python 扮演客户端, 与 C 服务器完成 NAT->init->密钥交换->数据帧->OOB"""
import socket, struct, sys, time, hashlib, hmac, os

KIT = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\CODOL_SERVER_319_TEST_20261021\kit'
sys.path.insert(0, KIT)
import codol_crypto as cc
src = open(os.path.join(KIT, 'battle_server.py'), encoding='utf-8').read()
i = src.index('P224_P'); j = src.index('def derive_transport_key')
ns = {'hashlib': hashlib, 'random': __import__('random')}
exec(src[i:j], ns)
_pmul, _G = ns['_pt_mul'], ns['P224_G']
exp, imp = ns['export_pubkey'], ns['import_pubkey']

def keystream(key16, seed6, data):
    w = cc._expand_key(key16)
    ctr = bytearray(hashlib.sha1(seed6).digest())
    out = bytearray(data)
    for off in range(0, len(out), 16):
        blk = cc._encrypt_block(w, bytes(ctr))
        for k in range(min(16, len(out)-off)): out[off+k] ^= blk[k]
        for k in range(16):
            ctr[k] = (ctr[k]+1) & 0xFF
            if ctr[k]: break
    return bytes(out)

HOST, PORT = '127.0.0.1', int(sys.argv[1])
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.settimeout(3.0)
fails = 0

# ① NAT
nat = bytearray(29)
nat[0] = 13; nat[1] = 2; nat[2] = 0
nat[23:29] = bytes([127,0,0,1,0x20,0x71])
s.sendto(bytes(nat), (HOST, PORT))
try:
    d, _ = s.recvfrom(2048)
    if d[0] == 12 and len(d) == 29: print('ok   NAT 回包 type=12')
    else: print('FAIL NAT', d[:4].hex()); fails += 1
except socket.timeout:
    print('FAIL NAT 超时'); fails += 1

# ② DTLS init
ctag = 0x1234
init = bytearray(16)
init[0] = 1; init[1] = 2
struct.pack_into('<H', init, 6, ctag)
struct.pack_into('<Q', init, 8, 1)
s.sendto(bytes(init), (HOST, PORT))
d, _ = s.recvfrom(2048)
if len(d) == 38 and d[0] == 2 and d[1] == 2 and struct.unpack_from('<H', d, 2)[0] == ctag:
    stag = struct.unpack_from('<H', d, 14)[0]
    print('ok   DTLS init 38B cookie, server_tag=0x%04X' % stag)
else:
    print('FAIL init', len(d), d[:8].hex()); fails += 1; sys.exit(1)
cookie = d

# ③ 密钥交换
priv = 0x0BADF00D1234567890ABCDEF0BADF00D1234567890ABCDEF1234567
pub = _pmul(priv, _G)
kx = bytearray(219)
kx[0] = 3; kx[1] = 2
struct.pack_into('<H', kx, 2, stag)
kx[6:44] = cookie
struct.pack_into('<Q', kx, 111, 1)
kx[119:219] = exp(pub)
s.sendto(bytes(kx), (HOST, PORT))
d, _ = s.recvfrom(2048)
if len(d) == 114 and d[0] == 4 and d[106] == 1:
    spub = imp(bytes(d[6:106]))
    shared = _pmul(priv, spub)
    key = hashlib.sha1(shared[0].to_bytes(28,'big') + b'\x01'*16).digest() + b'\x00'*4
    print('ok   密钥交换 114B, 传输密钥=%s...' % key[:4].hex())
else:
    print('FAIL keyex', len(d), d[:8].hex()); fails += 1; sys.exit(1)

# ④ 数据帧 + OOB getchallenge
seq = 0
def send_data(plain):
    global seq
    pkt = bytearray(16 + len(plain))
    pkt[0] = 6; pkt[1] = 2; pkt[2] = cookie[14]; pkt[3] = cookie[15]
    struct.pack_into('<H', pkt, 4, seq); seq = (seq+1) & 0xFFFF
    struct.pack_into('<H', pkt, 14, len(plain))
    seed = bytes([pkt[4], pkt[5], 0, 0, pkt[2], pkt[3]])
    pkt[16:16+len(plain)] = keystream(key[:16], seed, plain)
    auth = bytes(pkt[0:6]) + bytes(pkt[14:])
    pkt[6:14] = hmac.new(key[:24], auth, hashlib.sha1).digest()[:8]
    s.sendto(bytes(pkt), (HOST, PORT))

def read_data(pkt):
    n = struct.unpack_from('<H', pkt, 14)[0]
    seqn = struct.unpack_from('<H', pkt, 4)[0]
    seed = bytes([pkt[4], pkt[5], 0, 0, pkt[2], pkt[3]])
    return keystream(key[:16], seed, bytes(pkt[16:16+n]))

send_data(b'\xff\xff\xff\xff' + b'getchallenge 0 "abc"' + b'\x00')
d, _ = s.recvfrom(2048)
plain = read_data(d)
if plain[4:].startswith(b'challengeResponse'):
    print('ok   OOB getchallenge -> %r' % plain[4:].rstrip(b'\x00').decode())
else:
    print('FAIL challenge 应答', plain[:40]); fails += 1

send_data(b'\xff\xff\xff\xff' + b'connect abc "\\name\\x"' + b'\x00')
d, _ = s.recvfrom(2048)
plain = read_data(d)
if plain[4:].startswith(b'connectResponse'):
    print('ok   OOB connect -> %r' % plain[4:].rstrip(b'\x00').decode())
else:
    print('FAIL connect 应答', plain[:40]); fails += 1

send_data(b'\xff\xff\xff\xff' + b'heartbeat' + b'\x00')
d, _ = s.recvfrom(2048)
plain = read_data(d)
if plain[4:].startswith(b'heartbeatresponse'):
    print('ok   OOB heartbeat -> %r' % plain[4:].rstrip(b'\x00').decode())
else:
    print('FAIL heartbeat 应答', plain[:40]); fails += 1

print()
print('ALL PASSED' if not fails else 'FAILED (%d)' % fails)
sys.exit(1 if fails else 0)
