with open(r"REF_LOBBY_KIT\nt10.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

# Replace lines 2532 to 2544 with clean blocks
old_block = """        threading.Thread(target=kdf_hook_thread,
                         args=(h, log, page, len(apis) + 6, stop, pid), daemon=True).start()
        log("-- [KDF] 抓取线程已启动 (hook 0x%08X, 槽 %d)" % (KDF_HMAC_VA, len(apis) + 6))
    try:
        native_dll = os.path.join(a.root, "Ayria", "Plugins", "CodolGameServer.Localnet32")
        threading.Thread(target=native_server_inject_thread,
                         args=(h, log, page, len(apis) + 5, stop, native_dll),
                         daemon=True).start()
        log("-- [NATIVE-SERVER] 晚期注入监控线程已启动 (槽 %d, 目标=%s)" % (len(apis) + 5, native_dll))
    except Exception as _e:
        log("-- [NATIVE-SERVER] 注入线程启动异常: %r" % (_e,))
    except Exception as _e:
        log("-- [KDF] 线程启动失败: %r" % (_e,))"""

new_block = """        threading.Thread(target=kdf_hook_thread,
                         args=(h, log, page, len(apis) + 6, stop, pid), daemon=True).start()
        log("-- [KDF] 抓取线程已启动 (hook 0x%08X, 槽 %d)" % (KDF_HMAC_VA, len(apis) + 6))
    except Exception as _e:
        log("-- [KDF] 线程启动失败: %r" % (_e,))
    try:
        native_dll = os.path.join(a.root, "Ayria", "Plugins", "CodolGameServer.Localnet32")
        threading.Thread(target=native_server_inject_thread,
                         args=(h, log, page, len(apis) + 5, stop, native_dll),
                         daemon=True).start()
        log("-- [NATIVE-SERVER] 晚期注入监控线程已启动 (槽 %d, 目标=%s)" % (len(apis) + 5, native_dll))
    except Exception as _e:
        log("-- [NATIVE-SERVER] 注入线程启动异常: %r" % (_e,))"""

text = "".join(lines)
assert old_block in text, "old_block not found in nt10.py"
text = text.replace(old_block, new_block, 1)

with open(r"REF_LOBBY_KIT\nt10.py", "w", encoding="utf-8") as f:
    f.write(text)

print("Fixed syntax in nt10.py successfully!")
