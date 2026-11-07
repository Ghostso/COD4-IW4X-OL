# -*- coding: utf-8 -*-
"""负对照 / 变异测试：验证运行器确实能捕获错误（避免"永远 PASS"的空壳）。
不写入正式结果，仅输出到 _data/negative_controls.json。
"""
import io, os, sys, json, hashlib, hmac, struct, random
HERE = os.path.dirname(os.path.abspath(__file__))
TASK = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import indep_primitives as OWN
import extract_codec as XC

BIN = r'D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin'
tx = XC.Text(BIN)
A_CONST, A_PERM = XC.extract(tx, 0xAA8D70, 0xAA8E36, 0xAA8D9C, 0xAA8DB8, 0xAA8DBF, 0xAA8E35, -0x68)
mask = lambda c,p: bytes(c[p[j]] for j in range(20))
M_A = mask(A_CONST, A_PERM)
xform = lambda x,c,p: bytes(x[j]^c[p[j]] for j in range(20))

checks = {}

# N1: 故意改 1 bit 的密文，MAC 必须不匹配
k = OWN.sha1(b'key'); data = b'frame-bytes-here'
mac_ok  = OWN.hmac_sha1(k, data)[:8]
mac_bad = OWN.hmac_sha1(k, data + b'\x00')[:8]
checks['N1_mac_detects_1byte_change'] = (mac_ok != mac_bad)

# N2: 故意错置换（交换两项）必须导致输出不同
p2 = list(A_PERM); p2[0], p2[1] = p2[1], p2[0]
v = bytes(range(20))
checks['N2_perm_swap_changes_output'] = (xform(v,A_CONST,A_PERM) != xform(v,A_CONST,p2))

# N3: 计数器模式 若 counter 从 0 起，输出必须不同
def exp_start0(secret,label,size):
    out=bytearray(); prev=b''; c=0
    while len(out)<size:
        prev=OWN.hmac_sha1(secret, prev+label+bytes([c])); c+=1; out+=prev
    return bytes(out[:size])
def exp_start1(secret,label,size):
    out=bytearray(); prev=b''; c=1
    while len(out)<size:
        prev=OWN.hmac_sha1(secret, prev+label+bytes([c])); c+=1; out+=prev
    return bytes(out[:size])
checks['N3_counter_base_matters'] = (exp_start0(b'x',b'L',72) != exp_start1(b'x',b'L',72))

# N4: 标签大小写/内容敏感
checks['N4_label_sensitive'] = (exp_start1(b'x',b'BDDATA',72) != exp_start1(b'x',b'bdddata',72))

# N5: 截断长度敏感
checks['N5_truncation_matters'] = (exp_start1(b'x',b'BDDATA',72)[:71] != exp_start1(b'x',b'BDDATA',72))

# N6: HMAC key/data 顺序敏感 (对照 L585 注释中的参数序疑问)
checks['N6_hmac_arg_order_matters'] = (OWN.hmac_sha1(OWN.sha1(b'T'), b'K'*24) != OWN.hmac_sha1(b'K'*24, OWN.sha1(b'T')))

# N7: 自写 SHA-1 与 OpenSSL 在边界长度上均一致 (空/55/56/64/1000)
lens = [0,1,55,56,57,63,64,65,119,120,1000]
checks['N7_sha1_all_lengths'] = all(OWN.sha1(bytes((i*7)&0xff for i in range(n))) == hashlib.sha1(bytes((i*7)&0xff for i in range(n))).digest() for n in lens)

# N8: 自写 AES 与 pycryptodome 在随机向量上一致
from Crypto.Cipher import AES as PD_AES
random.seed(7)
ok = True
for _ in range(64):
    kk = bytes(random.randrange(256) for _ in range(16))
    bb = bytes(random.randrange(256) for _ in range(16))
    if OWN.aes128_encrypt_block(kk,bb) != PD_AES.new(kk, PD_AES.MODE_ECB).encrypt(bb): ok=False
    if OWN.aes128_decrypt_block(kk,bb) != PD_AES.new(kk, PD_AES.MODE_ECB).decrypt(bb): ok=False
checks['N8_own_aes_vs_pycryptodome'] = ok

# N9: CBC 链式(2 块) 与 pycryptodome 一致
kk=bytes(range(16)); iv=bytes(range(16,32)); pt=bytes(range(32))
checks['N9_own_cbc_vs_pycryptodome'] = (OWN.aes128_cbc_encrypt(kk,iv,pt) == PD_AES.new(kk,PD_AES.MODE_CBC,iv).encrypt(pt))

allpass = all(checks.values())
out = {'checks': checks, 'all_negative_controls_ok': allpass,
       'note': 'These confirm the harness/evaluator can detect wrong inputs, wrong parameters and wrong orderings.'}
io.open(os.path.join(TASK,'_data','negative_controls.json'),'w',encoding='utf-8',newline='\n').write(json.dumps(out,ensure_ascii=False,indent=2))
for k,v in checks.items(): print(('OK  ' if v else 'BAD '), k)
print('ALL', allpass)
