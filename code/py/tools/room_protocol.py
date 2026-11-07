"""把客户端房间上行结构写成可复用的解析库, 并对所有已知样本验证。

这是整个房间协议的核心规格。写成库而不是一次性脚本,
因为后续所有构造/校验都要用它。

用法:
    from room_protocol import parse_room_upstream
    r = parse_room_upstream(blob)
"""
import struct


class Field:
    def __init__(self, name, offset, size, value, note=''):
        self.name = name
        self.offset = offset
        self.size = size
        self.value = value
        self.note = note

    def __repr__(self):
        if self.size == 8:
            v = '0x%016X' % self.value
        elif self.size == 4:
            v = '%d (0x%X)' % (self.value, self.value)
        else:
            v = str(self.value)
        return '%-22s +0x%03X %s %s' % (self.name, self.offset, v, self.note)


def _u32(b, o):
    return struct.unpack_from('<I', b, o)[0] if o + 4 <= len(b) else None


def _u64(b, o):
    return struct.unpack_from('<Q', b, o)[0] if o + 8 <= len(b) else None


def parse_envelope(buf):
    """L1: 08 <service> | 0a <senderId> | 10 <name> | 13 08 <len> <payload>"""
    out = {'raw_len': len(buf)}
    i = 0
    assert buf[0] == 0x08, 'L1[0] 应为 0x08'
    out['service'] = _u32(buf, 1)
    i = 5
    if i < len(buf) and buf[i] == 0x0A:
        out['sender_id'] = _u64(buf, i + 1)
        i += 9
    if i < len(buf) and buf[i] == 0x10:
        e = buf.find(b'\x00', i + 1)
        out['sender_name'] = buf[i + 1:e]
        i = e + 1
    if i + 6 <= len(buf) and buf[i] == 0x13 and buf[i + 1] == 0x08:
        ln = _u32(buf, i + 2)
        out['payload_len'] = ln
        out['payload_off'] = i + 6
        out['payload'] = buf[i + 6:i + 6 + ln]
    return out


def parse_payload(p):
    """L2: 0a <roomId> | 13 08 <len> <inner> | 08 <tail>"""
    out = {}
    i = 0
    if i < len(p) and p[i] == 0x0A:
        out['room_id'] = _u64(p, i + 1)
        i += 9
    if i + 6 <= len(p) and p[i] == 0x13 and p[i + 1] == 0x08:
        ln = _u32(p, i + 2)
        out['inner_len'] = ln
        out['inner_off'] = i + 6
        out['inner'] = p[i + 6:i + 6 + ln]
        i += 6 + ln
    if i + 5 <= len(p) and p[i] == 0x08:
        out['tail'] = _u32(p, i + 1)
    return out


def parse_inner(inner):
    """L3: u32 declared | room data

    declared 恒等于 len(inner) - 4（实测 145 -> 141）。
    """
    out = {'blob_len': len(inner)}
    out['declared'] = _u32(inner, 0)
    out['consistent'] = (out['declared'] == len(inner) - 4)
    out['body'] = inner[4:]
    return out


def describe(body):
    """列出房间数据块里的非零 u32，作为结构勘察。"""
    rows = []
    for k in range(0, len(body) - 3, 4):
        v = struct.unpack_from('<I', body, k)[0]
        if v:
            f = struct.unpack_from('<f', body, k)[0]
            as_f = ''
            if 0.001 < abs(f) < 1e6 and v > 0x3F000000:
                as_f = '  f=%.4f' % f
            rows.append((k, v, as_f))
    return rows


def parse_room_upstream(buf):
    """一条完整的 11/4 上行 -> 结构化字典。"""
    env = parse_envelope(buf)
    pay = parse_payload(env.get('payload', b''))
    inn = parse_inner(pay.get('inner', b''))
    return {'envelope': env, 'payload': pay, 'inner': inn,
            'body': inn.get('body', b'')}


if __name__ == '__main__':
    import json
    import os
    RUN = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\EARLIEST2_20261027_132645'
    meta = json.load(open(os.path.join(RUN, 'snap_003.json'), encoding='utf-8'))
    lo = meta['lo']
    cov = open(os.path.join(RUN, 'snap_003_cover.bin'), 'r+b')
    f = open(os.path.join(RUN, 'snap_003.bin'), 'rb')
    off = 0x3AC62E40 - lo
    cov.seek(off)
    f.seek(off)
    buf = f.read(0x100)
    r = parse_room_upstream(buf)
    e, p, i = r['envelope'], r['payload'], r['inner']
    print('L1 service=%d sender_id=%d name=%r payload_len=%d'
          % (e['service'], e['sender_id'], e['sender_name'], e['payload_len']))
    print('L2 room_id=0x%016X inner_len=%d tail=%s'
          % (p['room_id'], p['inner_len'], p.get('tail')))
    print('L3 declared=%d len=%d consistent=%s body=%d B'
          % (i['declared'], i['blob_len'], i['consistent'], len(i['body'])))
    print()
    print('房间数据非零字段:')
    for k, v, as_f in describe(i['body']):
        print('  +0x%03X  %10d  0x%08X%s' % (k, v, v, as_f))
    cov.close()
    f.close()
