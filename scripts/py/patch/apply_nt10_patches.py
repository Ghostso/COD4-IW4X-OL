with open("REF_LOBBY_KIT/nt10.py", "r", encoding="utf-8") as f:
    content = f.read()

old_b4 = """    # --- 4) LsgNonceCheck: 0x00BA3C1A 处 85 C0 75 44 -> 0x00BA3C1C 写 90 90
    b4 = rpm(h, 0x00BA3C1A, 4)
    if len(b4) == 4:
        if b4 == b"\\x85\\xC0\\x90\\x90":
            done.add(4)
        elif b4 == b"\\x85\\xC0\\x75\\x44" and _wpm_code(h, 0x00BA3C1C, b"\\x90\\x90"):
            done.add(4)
            notes.append("补丁4 LsgNonceCheck NOP @0x00BA3C1C (85 C0 75 44 -> 85 C0 90 90)")

    return done, notes"""

new_b4 = """    # --- 4) LsgNonceCheck: 0x00BA3C1A 处 85 C0 75 44 -> 0x00BA3C1C 写 90 90
    b4 = rpm(h, 0x00BA3C1A, 4)
    if len(b4) == 4:
        if b4 == b"\\x85\\xC0\\x90\\x90":
            done.add(4)
        elif b4 == b"\\x85\\xC0\\x75\\x44" and _wpm_code(h, 0x00BA3C1C, b"\\x90\\x90"):
            done.add(4)
            notes.append("补丁4 LsgNonceCheck NOP @0x00BA3C1C (85 C0 75 44 -> 85 C0 90 90)")

    # --- 5..11) 战斗连接触发门禁与重试跳跃全绕过 (3.19 核心直连补丁) ---
    battle_patches = [
        (5, 0x00632695, b"\\x0F\\x84\\x50\\x02\\x00\\x00", b"\\x90" * 6, "补丁5 BattleGate1 NOP @0x00632695"),
        (6, 0x006326B0, b"\\x0F\\x8C\\x37\\x02\\x00\\x00", b"\\x90" * 6, "补丁6 BattleGate3 NOP @0x006326B0"),
        (7, 0x006326BF, b"\\x0F\\x85\\x51\\x02\\x00\\x00", b"\\x90" * 6, "补丁7 BattleGate4 NOP @0x006326BF"),
        (8, 0x006326CE, b"\\x0F\\x85\\x42\\x02\\x00\\x00", b"\\x90" * 6, "补丁8 BattleGate5 NOP @0x006326CE"),
        (9, 0x00632705, b"\\x75\\x0B", b"\\x90\\x90", "补丁9 SlotMismatch NOP @0x00632705"),
        (10, 0x00632710, b"\\x74\\x24", b"\\xEB\\x24", "补丁10 SlotMatchJmp JMP @0x00632710"),
        (11, 0x00632822, b"\\x75\\x40", b"\\x90\\x90", "补丁11 BattleBridgeSkip NOP @0x00632822"),
    ]
    for p_id, p_addr, orig_bytes, patch_bytes, p_name in battle_patches:
        cur_bytes = rpm(h, p_addr, len(orig_bytes))
        if cur_bytes == patch_bytes:
            done.add(p_id)
        elif cur_bytes == orig_bytes and _wpm_code(h, p_addr, patch_bytes):
            done.add(p_id)
            notes.append(p_name)

    return done, notes"""

assert old_b4 in content, "old_b4 not found in nt10.py"
content = content.replace(old_b4, new_b4, 1)

# Update compat_patch_thread total count to 11
old_thread = """def compat_patch_thread(h, log, deadline=COMPAT_DEADLINE):
    \"\"\"后台线程: 反复尝试 4 个补丁, 直到全部成功或超时。
    ★ 一旦某个补丁成功就【latch】住不再复查 —— 照抄 Run-Session.ps1 的 patched[$i]。
      原因: 补丁3 会把 0xB9A7C7 的 E8 改成 E9, 于是补丁2 的模式(84 C0 .. 2A E8)
      再也匹配不到; 若每轮重新判定, 补丁2 就会"掉出计数"(上一轮日志里 3/4 变 2/4 就是这个)。\"\"\"
    done = set()
    t0 = time.time()
    while time.time() - t0 < deadline and len(done) < 4:
        try:
            cur, notes = compat_patch_once(h)
        except Exception as e:
            log("-- [兼容补丁] 异常: %r" % (e,))
            return
        for n in notes:
            log("-- [兼容补丁] %s" % n)
        new = cur - done
        done |= cur                      # latch
        if new:
            log("-- [兼容补丁] 进度 %d/4 (本轮新增 %s, 用时 %.1fs)"
                % (len(done), sorted(new), time.time() - t0))
        time.sleep(0.25)
    # 收尾回读: 确认 4 个补丁的字节还在(若被 TP3 完整性检查还原, 这里会直接暴露)
    for i, ad, want in ((1, 0x00B9A78E, b"\\x75"), (2, 0x00B9A7C5, b"\\xEB"),
                        (3, 0x00B9A7C7, b"\\xE9"), (4, 0x00BA3C1C, b"\\x90\\x90")):
        got = rpm(h, ad, len(want))
        log("-- [兼容补丁] 回读#%d @0x%08X = %-8s 期望 %-8s %s"
            % (i, ad, got.hex(" "), want.hex(" "),
               "OK" if got == want else "!! 不匹配(可能被 TP3 还原)"))
    if len(done) == 4:
        log("-- [兼容补丁] 4/4 全部成功 (用时 %.1fs)" % (time.time() - t0))
    else:
        log("-- [兼容补丁] 只完成 %d/4: %s  (超时 %.0fs)"
            % (len(done), sorted(done), deadline))
        for i in (1, 2, 3, 4):
            if i not in done:
                log("     !! 补丁%d 的字节模式始终没出现(该段可能还没解壳)" % i)"""

new_thread = """def compat_patch_thread(h, log, deadline=COMPAT_DEADLINE):
    \"\"\"后台线程: 反复尝试 11 个补丁, 直到全部成功或超时。\"\"\"
    done = set()
    t0 = time.time()
    target_count = 11
    while time.time() - t0 < deadline and len(done) < target_count:
        try:
            cur, notes = compat_patch_once(h)
        except Exception as e:
            log("-- [兼容补丁] 异常: %r" % (e,))
            return
        for n in notes:
            log("-- [兼容补丁] %s" % n)
        new = cur - done
        done |= cur                      # latch
        if new:
            log("-- [兼容补丁] 进度 %d/%d (本轮新增 %s, 用时 %.1fs)"
                % (len(done), target_count, sorted(new), time.time() - t0))
        time.sleep(0.25)
    # 收尾回读: 确认全部 11 个补丁
    check_list = [
        (1, 0x00B9A78E, b"\\x75"), (2, 0x00B9A7C5, b"\\xEB"),
        (3, 0x00B9A7C7, b"\\xE9"), (4, 0x00BA3C1C, b"\\x90\\x90"),
        (5, 0x00632695, b"\\x90" * 6), (6, 0x006326B0, b"\\x90" * 6),
        (7, 0x006326BF, b"\\x90" * 6), (8, 0x006326CE, b"\\x90" * 6),
        (9, 0x00632705, b"\\x90\\x90"), (10, 0x00632710, b"\\xEB\\x24"),
        (11, 0x00632822, b"\\x90\\x90")
    ]
    for i, ad, want in check_list:
        got = rpm(h, ad, len(want))
        log("-- [兼容补丁] 回读#%d @0x%08X = %-8s 期望 %-8s %s"
            % (i, ad, got.hex(" ") if got else "NONE", want.hex(" "),
               "OK" if got == want else "!! 不匹配"))
    if len(done) == target_count:
        log("-- [兼容补丁] %d/%d 全部成功 (用时 %.1fs)" % (target_count, target_count, time.time() - t0))
    else:
        log("-- [兼容补丁] 完成 %d/%d: %s  (超时 %.0fs)"
            % (len(done), target_count, sorted(done), deadline))"""

assert old_thread in content, "old_thread not found in nt10.py"
content = content.replace(old_thread, new_thread, 1)

with open("REF_LOBBY_KIT/nt10.py", "w", encoding="utf-8") as f:
    f.write(content)

print("nt10.py successfully patched with all 11 compatibility and battle connection patches!")
