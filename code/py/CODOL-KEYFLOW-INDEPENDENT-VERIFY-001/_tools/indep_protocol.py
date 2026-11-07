# -*- coding: utf-8 -*-
"""独立协议层：KDF(expandKey/deriveSessionKeys) + Codec
- 原语来自自写 indep_primitives（SHA-1/HMAC-SHA1）
- Codec 参数来自 extract_codec（从冻结镜像机器码独立提取）
"""
import indep_primitives as P
import extract_codec as XC

BIN = r'D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin'


def sha1(data):
    return P.sha1(data)


def hmac_sha1(key, data):
    return P.hmac_sha1(key, data)


def expand_key(secret, label, size):
    """HMAC-SHA1 计数器模式。结构依据: PEER-REUSE-AUDIT-001/01 §5-6 的文字描述。
       prev = HMAC(secret, prev||label||counter), counter 自 1 递增, 拼接后截断。"""
    if isinstance(label, str):
        label = label.encode('ascii')
    out = bytearray(); prev = b''; counter = 1
    while len(out) < size:
        prev = hmac_sha1(secret, prev + label + bytes([counter & 0xff]))
        counter += 1
        out += prev
    return bytes(out[:size])


def derive_session_keys(session_key, transcript):
    th = sha1(transcript)
    secret = hmac_sha1(th, session_key)
    challenge = expand_key(secret, b'CLIENTCHAL', 16)
    data = expand_key(secret, b'BDDATA', 72)
    return {
        'transcript_hash': th, 'secret': secret, 'challenge': challenge,
        'response_id': challenge[8:16],
        'request_hmac': data[0:20], 'response_hmac': data[20:40],
        'decrypt': data[40:56], 'encrypt': data[56:72],
    }


def codec_transform(inp, const_bytes, perm):
    """out[j] = inp[j] ^ const_bytes[perm[j]]。依据 CODEC-KEYFLOW-001/01 §1 指令级语义。"""
    assert len(inp) == 20 and len(const_bytes) == 20 and len(perm) == 20
    return bytes(inp[j] ^ const_bytes[perm[j]] for j in range(20))


def codec_params():
    """返回 (A_CONST, A_PERM, B_CONST, B_PERM)，均由冻结镜像机器码提取。"""
    tx = XC.Text(BIN)
    A_CONST, A_PERM = XC.extract(tx, 0xAA8D70, 0xAA8E36, 0xAA8D9C, 0xAA8DB8, 0xAA8DBF, 0xAA8E35, -0x68)
    B_CONST, B_PERM = XC.extract(tx, 0xAA8BF0, 0xAA8CB7, 0xAA8C19, 0xAA8C35, 0xAA8C3C, 0xAA8CB6, -0x68)
    return A_CONST, A_PERM, B_CONST, B_PERM


if __name__ == '__main__':
    k = derive_session_keys(b'Shippo fuute, mofu-mofu!', bytes(range(64)))
    print('response_id  ', k['response_id'].hex())
    print('request_hmac ', k['request_hmac'].hex())
    A_CONST, A_PERM, B_CONST, B_PERM = codec_params()
    print('A_CONST', A_CONST.hex(), 'A_PERM', A_PERM)
    print('B_CONST', B_CONST.hex(), 'B_PERM', B_PERM)
