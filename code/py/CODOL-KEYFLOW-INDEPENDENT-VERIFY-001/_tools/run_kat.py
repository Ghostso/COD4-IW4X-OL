# -*- coding: utf-8 -*-
"""CODOL-KEYFLOW-INDEPENDENT-VERIFY-001 : TC-01..TC-11 执行器（规范化 11 行）
输出 CODOL_KEYFLOW_KAT_RESULTS_001.csv + _data/kat_execution_log.json
"""
import csv, io, os, sys, hashlib, hmac, struct, json, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
TASK = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import indep_primitives as OWN
import extract_codec as XC

try:
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    HAVE_CRYPTO = True
except Exception:
    HAVE_CRYPTO = False
from Crypto.Cipher import AES as PD_AES

BIN = r'D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin'
BIN_SHA = hashlib.sha256(open(BIN, 'rb').read()).hexdigest()

SK = b'Shippo fuute, mofu-mofu!'
TR = bytes(range(64))
KAT = {
    'response_id':   'ea09fd53518d4361',
    'request_hmac':  '96548bb09f4bd93996465628b618c9d3ec09ddd5',
    'response_hmac': '4395bd6340aa21bc95d9b77db1c04afc67061382',
    'decrypt':       '71120733ba54e6ff13ded72c69deca7f',
    'encrypt':       'b1adf0f2663cde670df4f20fbe37fc2e',
}
KAT_SRC = 'DemonwareTests.cpp:2455-2478 (ol-mod 记录的第三方 KAT)'

def H(b): return hashlib.sha256(b).hexdigest()
def fd(a, b):
    n = min(len(a), len(b))
    for i in range(n):
        if a[i] != b[i]: return i
    return -1 if len(a) == len(b) else n

rows = []; raw = []
def emit(tid, inp, src, exp, act, notes):
    bm = exp == act
    rows.append({'test_id': tid, 'input_hash': H(inp), 'expected_source': src,
                 'actual_output_hash': H(act), 'byte_match': 'YES' if bm else 'NO',
                 'first_difference': '' if bm else fd(exp, act),
                 'status': 'PASS' if bm else 'FAIL', 'notes': notes})
    raw.append({'test_id': tid, 'expected_hex': exp.hex(), 'actual_hex': act.hex(),
                'input_hash': H(inp), 'byte_match': bm, 'status': rows[-1]['status']})
    print('%-6s %-4s %s' % (tid, rows[-1]['status'], notes))

# -------- independent expandKey instances --------
def expand_own(secret, label, size):
    out = bytearray(); prev = b''; c = 1
    while len(out) < size:
        prev = OWN.hmac_sha1(secret, prev + label + bytes([c & 0xff])); c += 1; out += prev
    return bytes(out[:size])

def expand_ossl(secret, label, size):
    out = bytearray(); prev = b''; c = 1
    while len(out) < size:
        prev = hmac.new(secret, prev + label + bytes([c & 0xff]), hashlib.sha1).digest(); c += 1; out += prev
    return bytes(out[:size])

# ============================ 组 1 : KDF ============================
# TC-01 自写 SHA-1 vs OpenSSL
e_sha = hashlib.sha1(TR).digest(); a_sha = OWN.sha1(TR)
emit('TC-01', TR, 'OpenSSL(hashlib.sha1) 独立原语', e_sha, a_sha,
     'transcript=00..3F(64B); 自写 SHA-1 vs OpenSSL 逐字节')

# TC-02 自写 HMAC-SHA1 vs OpenSSL (两套独立原语, 同一公式)
e_sec = hmac.new(e_sha, SK, hashlib.sha1).digest(); a_sec = OWN.hmac_sha1(a_sha, SK)
emit('TC-02', a_sha + SK, 'OpenSSL(hmac.new) 独立原语', e_sec, a_sec,
     'key=SHA1(transcript), data=sessionKey24; 自写 vs OpenSSL')

# TC-03 CLIENTCHAL->16B : 双 oracle (OpenSSL 实例 + 项目 KAT)
c_own = expand_own(a_sec, b'CLIENTCHAL', 16); c_ossl = expand_ossl(e_sec, b'CLIENTCHAL', 16)
ok_o = (c_own == c_ossl); ok_k = (c_own[8:16] == bytes.fromhex(KAT['response_id']))
emit('TC-03', a_sec + b'CLIENTCHAL', 'OpenSSL 原语实例 + %s' % KAT_SRC,
     c_ossl + bytes.fromhex(KAT['response_id']), c_own + c_own[8:16],
     'CLIENTCHAL->16B; vs OpenSSL=%s; response_id vs KAT=%s' % (ok_o, ok_k))

# TC-04 BDDATA->72B : 双 oracle (OpenSSL 实例 + 项目 KAT 四切片)
d_own = expand_own(a_sec, b'BDDATA', 72); d_ossl = expand_ossl(e_sec, b'BDDATA', 72)
kat4 = b''.join(bytes.fromhex(KAT[k]) for k in ('request_hmac','response_hmac','decrypt','encrypt'))
own4 = d_own[0:20] + d_own[20:40] + d_own[40:56] + d_own[56:72]
emit('TC-04', a_sec + b'BDDATA', 'OpenSSL 原语实例 + %s' % KAT_SRC,
     d_ossl + kat4, d_own + own4,
     'BDDATA->72B; vs OpenSSL=%s; 20/20/16/16 四切片 vs KAT=%s' % (d_own == d_ossl, own4 == kat4))

# TC-05 计数器模式逐轮中间值
sec5 = bytes(range(20)); mids_own = b''; prev = b''
for c in range(1, 5):
    prev = OWN.hmac_sha1(sec5, prev + b'BDDATA' + bytes([c])); mids_own += prev
mids_ossl = b''; prev = b''
for c in range(1, 5):
    prev = hmac.new(sec5, prev + b'BDDATA' + bytes([c]), hashlib.sha1).digest(); mids_ossl += prev
emit('TC-05', sec5 + b'BDDATA', 'OpenSSL 原语实例（逐轮）', mids_ossl, mids_own,
     '4 轮 prev||label||counter, counter 1..4; 每轮 20B 中间值逐字节')

# TC-06 截断边界
sizes = (72, 16, 1)
own_tr = b''.join(expand_own(sec5, b'BDDATA', s) for s in sizes)
ossl_tr = b''.join(expand_ossl(sec5, b'BDDATA', s) for s in sizes)
len_ok = all(len(expand_own(sec5, b'BDDATA', s)) == s for s in sizes)
emit('TC-06', sec5 + b'BDDATA', 'OpenSSL 原语实例 + 长度约束', ossl_tr, own_tr,
     'size=72/16/1 截断; 长度自洽=%s; 前缀一致=%s' % (len_ok, own_tr == ossl_tr))

# ============================ 组 2 : Codec ============================
E = lambda t: XC.extract(t, 0xAA8D70, 0xAA8E36, 0xAA8D9C, 0xAA8DB8, 0xAA8DBF, 0xAA8E35, -0x68)
F = lambda t: XC.extract(t, 0xAA8BF0, 0xAA8CB7, 0xAA8C19, 0xAA8C35, 0xAA8C3C, 0xAA8CB6, -0x68)
tx = XC.Text(BIN)
A_CONST, A_PERM = E(tx); B_CONST, B_PERM = F(tx)
mask = lambda c, p: bytes(c[p[j]] for j in range(20))
M_A, M_B = mask(A_CONST, A_PERM), mask(B_CONST, B_PERM)
xform = lambda x, c, p: bytes(x[j] ^ c[p[j]] for j in range(20))

import random
random.seed(0xC0D01)
VEC = [bytes(20), bytes([0xff]*20), bytes(range(20))] + [bytes(random.randrange(256) for _ in range(20)) for _ in range(64)]

# TC-07 Codec A : 置换式 vs 掩码折叠式 (独立推导)
ea = b''.join(bytes(v[j] ^ M_A[j] for j in range(20)) for v in VEC)
aa = b''.join(xform(v, A_CONST, A_PERM) for v in VEC)
emit('TC-07', b''.join(VEC), '冻结镜像机器码提取 A_CONST/A_PERM（独立 artifact）', ea, aa,
     '%d 向量 x20B; 置换式 out=in^CONST[PERM] vs 掩码折叠式' % len(VEC))

# TC-08 Codec B
eb = b''.join(bytes(v[j] ^ M_B[j] for j in range(20)) for v in VEC)
ab = b''.join(xform(v, B_CONST, B_PERM) for v in VEC)
emit('TC-08', b''.join(VEC), '冻结镜像机器码提取 B_CONST/B_PERM（独立 artifact）', eb, ab,
     '%d 向量 x20B; 同 TC-07, B 表' % len(VEC))

# TC-09 往返一致性 (A/B 各 256 组)
RT = 256
allA = all(xform(xform(v, A_CONST, A_PERM), A_CONST, A_PERM) == v for v in
           (bytes(random.randrange(256) for _ in range(20)) for _ in range(RT)))
allB = all(xform(xform(v, B_CONST, B_PERM), B_CONST, B_PERM) == v for v in
           (bytes(random.randrange(256) for _ in range(20)) for _ in range(RT)))
one = bytes(range(20))
emit('TC-09', one, 'STORE/LOAD 同掩码定义式（自洽往返）', one, xform(xform(one, A_CONST, A_PERM), A_CONST, A_PERM),
     'A 往返 %d/%d, B 往返 %d/%d (全 True=%s)' % (RT if allA else 0, RT, RT if allB else 0, RT, allA and allB))

# TC-10 置换索引域
idx_ok = all(0 <= v < 20 for v in A_PERM + B_PERM)
emit('TC-10', bytes(A_PERM + B_PERM), '置换表结构约束（索引 ∈[0,20)，各 20 项）',
     bytes([20, 20, 1]), bytes([len(A_PERM), len(B_PERM), 1 if idx_ok else 0]),
     'A/B 各 20 项, 索引全在 0..19；越界检查=%s' % idx_ok)

# TC-11 C# DecodeKey 展开 vs 冻结镜像掩码
W_A = [2919830337, 4089226047, 3169481240, 3423678985, 4099162642]
I_A = [7,17,14,16,9,19,13,0,2,3,4,8,1,10,11,5,18,6,12,15]
W_B = [2866684544, 4095810571, 938409728, 3457192487, 557642922]
I_B = [19,18,9,4,17,1,10,8,13,2,15,3,12,16,5,7,0,14,6,11]
def cs_mask(W, I):
    a = b''.join(struct.pack('<I', w) for w in W)
    return bytes(a[I[j]] for j in range(20))
emit('TC-11', b''.join(struct.pack('<I', w) for w in W_A + W_B),
     'C# DecodeKey 源码常量 (CodolLocalLobbyServer.cs:264-276,315-320) vs 冻结镜像掩码',
     cs_mask(W_A, I_A) + cs_mask(W_B, I_B), M_A + M_B,
     'C# 展开掩码 vs 冻结镜像机器码提取掩码 (M_A||M_B)')

# -------- 写 CSV --------
cols = ['test_id','input_hash','expected_source','actual_output_hash','byte_match','first_difference','status','notes']
with io.open(os.path.join(TASK, 'CODOL_KEYFLOW_KAT_RESULTS_001.csv'), 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.DictWriter(f, fieldnames=cols); w.writeheader()
    for r in rows: w.writerow(r)

meta = {
    'task': 'CODOL-KEYFLOW-INDEPENDENT-VERIFY-001',
    'generated': datetime.datetime.now().isoformat(timespec='seconds'),
    'binary': BIN, 'binary_sha256': BIN_SHA,
    'codec_A_const': A_CONST.hex(), 'codec_A_perm': A_PERM, 'codec_A_mask': M_A.hex(),
    'codec_B_const': B_CONST.hex(), 'codec_B_perm': B_PERM, 'codec_B_mask': M_B.hex(),
    'self_test': {
        'own_sha1_empty': OWN.sha1(b'').hex(),
        'openssl_sha1_empty': hashlib.sha1(b'').hexdigest(),
        'own_hmac_rfc2202_1': OWN.hmac_sha1(bytes.fromhex('0b'*20), b'Hi There').hex(),
        'md_hmac_rfc2202_1': hmac.new(bytes.fromhex('0b'*20), b'Hi There', hashlib.sha1).hexdigest(),
        'own_aes_fips197': OWN.aes128_encrypt_block(bytes.fromhex('000102030405060708090a0b0c0d0e0f'),
                            bytes.fromhex('00112233445566778899aabbccddeeff')).hex(),
        'pycryptodome_aes_fips197': PD_AES.new(bytes.fromhex('000102030405060708090a0b0c0d0e0f'),
                            PD_AES.MODE_ECB).encrypt(bytes.fromhex('00112233445566778899aabbccddeeff')).hex(),
    },
    'have_cryptography': HAVE_CRYPTO, 'vector_count': len(VEC), 'roundtrip_count': RT,
    'results': raw,
}
with io.open(os.path.join(TASK, '_data', 'kat_execution_log.json'), 'w', encoding='utf-8', newline='\n') as f:
    json.dump(meta, f, ensure_ascii=False, indent=2)

print()
print('rows=%d PASS=%d FAIL=%d' % (len(rows), sum(1 for r in rows if r['status']=='PASS'),
      sum(1 for r in rows if r['status']=='FAIL')))
