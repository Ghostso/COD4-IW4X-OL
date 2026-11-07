with open(r"REF_LOBBY_KIT\nt10.py", "r", encoding="utf-8") as f:
    text = f.read()

# 1. Replace native_server_inject_thread definition with native_server_trigger_thread
start_m = "def native_server_inject_thread("
end_m = "for _f in (\"WriteProcessMemory\", \"ReadProcessMemory\"):"

start_pos = text.find(start_m)
end_pos = text.find(end_m)
assert start_pos != -1, "start_m not found"
assert end_pos != -1, "end_m not found"

new_trigger_def = """def native_server_trigger_thread(h, log, inj_pend, inj_hmod, stop, deadline=60.0):
    t0 = time.time()
    triggered = False
    while not stop.is_set() and time.time() - t0 < deadline:
        b = rpm(h, 0x0077F6EF, 2)
        if b == b"\\xeb\\x36" and not triggered:
            time.sleep(0.5)
            wpm(h, inj_pend, b"\\x01")
            triggered = True
            log("-- [NATIVE-SERVER] 内存已解壳，已置 pending=1 请求游戏主线程加载 CodolGameServer.dll...")
            for _ in range(120):
                time.sleep(0.1)
                hm = rpm(h, inj_hmod, 4)
                if hm and any(hm):
                    hmod = struct.unpack("<I", hm)[0]
                    log("-- [NATIVE-SERVER] ★ 游戏主线程一趟式加载 DLL 成功! HMODULE=0x%08X" % hmod)
                    return
            log("-- [NATIVE-SERVER] 等待游戏主线程加载 DLL 超时")
            return
        time.sleep(0.2)

"""

text = text[:start_pos] + new_trigger_def + text[end_pos:]

# 2. Update run_client where hooks are built
# Search for code = build_tramp(
hook_call = "code = build_tramp(cnt, cnt + 4, stolen, tgt + n, cave, str_off, mode,\n                               trace_pending=tr_pend, trace_work=tr_work)"
assert hook_call in text, "hook_call not found"

new_hook_call = """inj_p = inj_w = None
            if nm in ("sendto", "WSASendTo", "connect", "recvfrom", "recv"):
                inj_p = inj_pend
                inj_w = inj_work
            code = build_tramp(cnt, cnt + 4, stolen, tgt + n, cave, str_off, mode,
                               trace_pending=tr_pend, trace_work=tr_work,
                               inject_pending=inj_p, inject_work=inj_w)"""

text = text.replace(hook_call, new_hook_call, 1)

# 3. Add stub setup before hook loop
loop_start = 'for nm in apis:'
pos_loop = text.find(loop_start)
assert pos_loop != -1, "loop_start not found"

stub_setup = """inj_work = page + (len(apis) + 5) * SLOT
        inj_pend = inj_work + 0x200
        inj_hmod = inj_work + 0x204
        inj_str = inj_work + 0x100
        p_load_lib = (k32_base + 0x20E70) & 0xFFFFFFFF

        stub = bytearray()
        stub += b"\\xC6\\x05" + struct.pack("<I", inj_pend) + b"\\x00"
        stub += b"\\x68" + struct.pack("<I", inj_str)
        stub += b"\\xB8" + struct.pack("<I", p_load_lib)
        stub += b"\\xFF\\xD0"
        stub += b"\\xA3" + struct.pack("<I", inj_hmod)
        stub += b"\\xC3"
        _wpm_code(h, inj_work, bytes(stub))
        wpm(h, inj_str, b"CodolGameServer.dll\\x00")
        wpm(h, inj_pend, b"\\x00")
        wpm(h, inj_hmod, b"\\x00\\x00\\x00\\x00")
        log("-- [NATIVE-SERVER] 主线程加载跳板就绪 @ 0x%08X (LoadLibraryA=0x%08X)" % (inj_work, p_load_lib))
        threading.Thread(target=native_server_trigger_thread,
                         args=(h, log, inj_pend, inj_hmod, stop), daemon=True).start()

        """

text = text[:pos_loop] + stub_setup + text[pos_loop:]

# 4. Remove the old thread call around line 2538
old_spawn = """k32_wow64 = next((b for n, b, s in ml if n.lower().startswith("kernel32")), 0)
        threading.Thread(target=native_server_inject_thread,
                         args=(h, log, page, len(apis) + 5, stop, "CodolGameServer.dll", a.root, k32_wow64),
                         daemon=True).start()"""
if old_spawn in text:
    text = text.replace(old_spawn, "# (old injection removed, now using main thread trampoline)", 1)

with open(r"REF_LOBBY_KIT\nt10.py", "w", encoding="utf-8") as f:
    f.write(text)

print("Successfully applied main-thread trampoline injection to nt10.py!")
