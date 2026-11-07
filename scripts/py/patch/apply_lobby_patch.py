with open("REF_LOBBY_KIT/lobby_server.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update SEC_KEY
old_sec = """SEC_KEY = b"\\x00" * 16                   # 16B securityKey; 真游戏服要配对的另一半, 暂用全 0
# ★ 把它写给战斗服(battle_server.py) —— 战斗服的 ECDH 派生要用同一个 16B
SEC_KEY_FILE = os.path.join(OUTDIR, "battle_security_key.txt")"""

new_sec = """SEC_KEY_FILE = os.path.join(OUTDIR, "battle_security_key.txt")
_default_sk = b"\\x01" * 16
if os.path.exists(SEC_KEY_FILE):
    try:
        _sk_raw = open(SEC_KEY_FILE, "r", encoding="ascii").read().strip()
        if len(_sk_raw) == 32:
            _default_sk = bytes.fromhex(_sk_raw)
    except Exception:
        pass
SEC_KEY = _default_sk"""

assert old_sec in content, "old_sec not found"
content = content.replace(old_sec, new_sec, 1)

# 2. Update mmbook handling
old_mmbook = """            if re.search(rb"mmbook[^\\x00]{0,120}", body):
                pushes = []
                if os.path.exists(FR_BOOKING_FLAG):
                    accepted = struct.pack("<I", len(FR_BOOKING_ACCEPTED)) + FR_BOOKING_ACCEPTED
                    pushes = [(2, cc.instant_push_body(1, "localhost", accepted))]
                    return ack("6/%d 命中 'mmbook' -> push 'mmbook accepted'(data=%d)"
                               % (task, len(accepted)))[:2] + (pushes,)
                return ack("6/%d 命中 'mmbook' (booking 开关未开, 仅空应答)" % task)[:2] + ([],)"""

new_mmbook = """            if re.search(rb"mmbook[^\\x00]{0,120}", body):
                pushes = []
                if os.path.exists(FR_BOOKING_FLAG):
                    m_book = re.search(rb"mmbook\\s+(\\d+)\\s+([^\\s\\x00]+)\\s+(\\d+)", body)
                    if m_book:
                        book_a = int(m_book.group(1))
                        book_token = m_book.group(2)
                        book_b = int(m_book.group(3))
                        sender_id = (book_a & 0xFFFFFFFF) | ((book_b & 0xFFFFFFFF) << 32)
                    else:
                        sender_id = 796
                        book_a, book_b = 796, 0
                    accepted = struct.pack("<I", len(FR_BOOKING_ACCEPTED)) + FR_BOOKING_ACCEPTED
                    pushes = [(2, cc.instant_push_body(sender_id, "localhost", accepted))]
                    return ack("6/%d 命中 'mmbook'(A=%d B=%d sender_id=%d) -> push 'mmbook accepted'(data=%d)"
                               % (task, book_a, book_b, sender_id, len(accepted)))[:2] + (pushes,)
                return ack("6/%d 命中 'mmbook' (booking 开关未开, 仅空应答)" % task)[:2] + ([],)"""

assert old_mmbook in content, "old_mmbook not found"
content = content.replace(old_mmbook, new_mmbook, 1)

# 3. Update push frame sending sequence
old_push_send = """                        push_off = 1000
                        try:
                            _pf = os.path.join(OUTDIR, "push_seq_offset.txt")
                            if os.path.exists(_pf):
                                push_off = int(open(_pf, encoding="ascii").read().strip())
                        except Exception:
                            push_off = 1000
                        for _mt, _body in (pushes or []):
                            _pseq = (r["seq"] + push_off) & 0xFFFFFFFF
                            pf = cc.build_push(sec["aes_in"], sec["hmac_in"], _pseq, _body, _mt)
                            conn.sendall(pf)
                            log("  -> 0x85 推送 type=%d seq=%d(请求seq+%d, 避开客户端号段)"
                                " (%d 字节 body=%d)"
                                % (_mt, _pseq, push_off, len(pf), len(_body)))"""

new_push_send = """                        for _mt, _body in (pushes or []):
                            _pseq = out_seq
                            out_seq += 1
                            pf = cc.build_push(sec["aes_in"], sec["hmac_in"], _pseq, _body, _mt)
                            conn.sendall(pf)
                            log("  -> 0x85 推送 type=%d seq=%d(严格单调递增 S2C seq)"
                                " (%d 字节 body=%d)"
                                % (_mt, _pseq, len(pf), len(_body)))"""

assert old_push_send in content, "old_push_send not found"
content = content.replace(old_push_send, new_push_send, 1)

with open("REF_LOBBY_KIT/lobby_server.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Patch applied successfully!")
