path = r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_VERIFIED_GOLDEN_20261019\nt10.py'
text = open(path, encoding='utf-8').read()

old_p = """    # --- 4) LsgNonceCheck: 0x00BA3C1A 处 85 C0 75 44 -> 0x00BA3C1C 写 90 90
    b4 = rpm(h, 0x00BA3C1A, 4)
    if len(b4) == 4:
        if b4 == b"\\x85\\xC0\\x90\\x90":
            done.add(4)
        elif b4 == b"\\x85\\xC0\\x75\\x44" and _wpm_code(h, 0x00BA3C1C, b"\\x90\\x90"):
            done.add(4)
            notes.append("补丁4 LsgNonceCheck NOP @0x00BA3C1C (85 C0 75 44 -> 85 C0 90 90)")

    return done, notes"""

new_p = """    # --- 4) LsgNonceCheck: 0x00BA3C1A 处 85 C0 75 44 -> 0x00BA3C1C 写 90 90
    b4 = rpm(h, 0x00BA3C1A, 4)
    if len(b4) == 4:
        if b4 == b"\\x85\\xC0\\x90\\x90":
            done.add(4)
        elif b4 == b"\\x85\\xC0\\x75\\x44" and _wpm_code(h, 0x00BA3C1C, b"\\x90\\x90"):
            done.add(4)
            notes.append("补丁4 LsgNonceCheck NOP @0x00BA3C1C (85 C0 75 44 -> 85 C0 90 90)")

    # --- 5) GateB: 0x0062FE80 处 80 B9 14 06 01 00 00 0F 95 C0 C3 -> B0 01 C3
    b5 = rpm(h, 0x0062FE80, 11)
    if len(b5) == 11:
        if b5.startswith(b"\\xB0\\x01\\xC3"):
            done.add(5)
        elif b5.startswith(b"\\x80\\xB9\\x14\\x06\\x01\\x00\\x00\\x0F\\x95\\xC0\\xC3") and _wpm_code(h, 0x0062FE80, b"\\xB0\\x01\\xC3"):
            done.add(5)
            notes.append("补丁5 GateB 放行 @0x0062FE80 (80 B9 ... -> B0 01 C3)")

    return done, notes"""

if old_p in text:
    text = text.replace(old_p, new_p, 1)
    text = text.replace('len(done) < 4', 'len(done) < 5')
    text = text.replace('进度 %d/4', '进度 %d/5')
    text = text.replace('(4, 0x00BA3C1C, b"\\x90\\x90")', '(4, 0x00BA3C1C, b"\\x90\\x90"), (5, 0x0062FE80, b"\\xB0\\x01\\xC3")')
    text = text.replace('4/4 全部成功', '5/5 全部成功')
    text = text.replace('只完成 %d/4', '只完成 %d/5')
    text = text.replace('for i in (1, 2, 3, 4):', 'for i in (1, 2, 3, 4, 5):')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(text)
    print('REPLACED OK')
else:
    print('OLD PATTERN NOT FOUND')
