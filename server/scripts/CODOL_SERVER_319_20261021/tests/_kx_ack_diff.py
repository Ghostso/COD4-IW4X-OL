"""对实机抓到的 219B 密钥交换 + 我们回的 114B ACK 做逐字段对账。
   usage: python -I kx_ack_diff.py
"""
KX = ("0302460D00000202AC760000A792640100000000460D460DAC76000000007F000001FB5588776655443322"
      "11C0A85501FB5500FF00FF000000FF00FF000000FF00FF000000FF00FF000000FF00FF000000FF00FF00"
      "0000FF00FF000000FF00FF000000FF00FF000000FF00FF00003C01FC5E52070188776655443322113045"
      "0302070002011C021D00AEF5B75D20A3A1C45E2049B1B7BCBF8693D616955CA20FF313AA65CE021D00"
      "E44CFDCEFF638D2E5D92E4BB57995E62741341DCF63C60BCCBCBC8F8"
      "0000000000000000000000000000000000000000000000000000000000")
INIT = "010200000000AC768877665544332211"
COOKIE = ("0202AC760000A792640100000000460D460DAC76000000007F000001FB55"
          "8877665544332211")

kx = bytes.fromhex(KX)
init = bytes.fromhex(INIT)
cookie = bytes.fromhex(COOKIE)

print('init   len=%d  %s' % (len(init), init.hex()))
print('cookie len=%d  %s' % (len(cookie), cookie.hex()))
print('kx     len=%d' % len(kx))
print()

print('=== 记录头 (6B, 客户端解析器 0xBC25F0 的布局) ===')
print('  [0]      type      = 0x%02X' % kx[0])
print('  [1]                = 0x%02X' % kx[1])
print('  [2..4]   tag16(BE) = 0x%04X      (LE 解读 0x%04X)' % (int.from_bytes(kx[2:4], 'big'), int.from_bytes(kx[2:4], 'little')))
print('  [4..6]             = 0x%04X' % int.from_bytes(kx[4:6], 'big'))
print()
print('  cookie 回带 [6..44] == COOKIE ? %s' % (kx[6:44] == cookie))
print('  cookie[2..4] = %s   kx[2..4] = %s' % (cookie[2:4].hex(), kx[2:4].hex()))
print('  cookie[14..16] = %s (=server_tag)  kx[2..4] == that ? %s' % (cookie[14:16].hex(), kx[2:4] == cookie[14:16]))
print()
print('=== 初始化报文对比 ===')
print('  init[0]=0x%02X init[1]=0x%02X  init[2..4]=%s init[4..6]=%s' % (init[0], init[1], init[2:4].hex(), init[4:6].hex()))
print('  init[6..8] = %s   (客户端自己 tag?)' % init[6:8].hex())
print('  init[8..16]= %s   (大厅会话 id)' % init[8:16].hex())
print('  cookie[2..4]= %s == init[6..8] ? %s' % (cookie[2:4].hex(), cookie[2:4] == init[6:8]))
print()
print('=== 219B 主体切分 (6 + 38 cookie + 67 addr + 8 sid + key) ===')
off = 6
print('  [%3d..%3d] cookie(38) : %s' % (off, off + 38, kx[off:off + 38].hex()))
off += 38
print('  [%3d..%3d] bdCommonAddr(67): %s' % (off, off + 67, kx[off:off + 67].hex()))
off += 67
print('  [%3d..%3d] u64         : %s  (= 大厅会话 id ? %s)' % (off, off + 8, kx[off:off + 8].hex(), kx[off:off + 8] == bytes.fromhex('8877665544332211')))
off += 8
rest = kx[off:]
print('  [%3d..%3d] 余下 %d 字节: %s' % (off, len(kx), len(rest), rest[:24].hex()))
if len(rest) >= 4 and rest[0] == 0x30:
    ln = rest[1]
    print('       DER SEQUENCE len=0x%02X -> 真正公钥 %d 字节, 之后 %d 个填充 0' % (ln, 2 + ln, len(rest) - 2 - ln))
    der = rest[:2 + ln]
    print('       DER: %s' % der.hex())
    # 解析
    i = 2
    while i < len(der):
        t = der[i]; l = der[i + 1]
        body = der[i + 2:i + 2 + l]
        print('         tag 0x%02X len %2d : %s%s' % (t, l, body.hex(), '' if t == 2 else ''))
        i += 2 + l
print()
COORD = rest[2:2 + rest[1]] if rest[:1] == b'\x30' else b''
print('=== 参照: 我们自己 114B ACK 的构造 (battle.c) ===')
print('  out[0]=4 out[1]=2 out[2..4]=cookie[2..4]=%s out[4..6]=0' % cookie[2:4].hex())
print('  out[6..106]=100B DER 公钥  out[106]=1  out[107..114]=0')
print()
print('  客户端 type-4 处理器 0xBBE2B0 的检查:')
print('    (a) [parse+6] == [DTLS+0x502]   -> 我们的 [2..4]=%s' % cookie[2:4].hex())
print('    (b) [+0x4d4] == 2               -> cookie 处理器 0xBBEC80 置 2')
print('    (c) 0xBBDE10(100B 载荷, 8B 尾) 验证')
