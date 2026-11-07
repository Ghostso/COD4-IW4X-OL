with open("REF_LOBBY_KIT/lobby_server.py", "r", encoding="utf-8") as f:
    content = f.read()

old_func = """    script = os.path.join(OUTDIR, "battle_server.py")
    if not os.path.exists(script):
        log("  战斗服: 开关在, 但找不到 %s" % script)
        return None
    try:
        out = open(os.path.join(OUTDIR, "_battle_out.txt"), "w")
        err = open(os.path.join(OUTDIR, "_battle_err.txt"), "w")
        p = subprocess.Popen([sys.executable, script, "--bind", bind, "--port", str(port)],
                             stdout=out, stderr=err, stdin=subprocess.DEVNULL,
                             creationflags=0x08000000)
        log("  ★ 战斗服已启动: battle_server.py --bind %s --port %d (pid=%s, UDP)"
            % (bind, port, p.pid))
        return p
    except Exception as e:
        log("  战斗服启动失败: %r" % (e,))
        return None"""

new_func = """    csharp_exe = os.path.abspath(os.path.join(OUTDIR, "..", "CODOL-Combat-Server-v0.1", "build", "bin", "CODOLCombatServer.exe"))
    csharp_cfg = os.path.abspath(os.path.join(OUTDIR, "..", "CODOL-Combat-Server-v0.1", "config", "firingrange_live.cfg"))
    csharp_workdir = os.path.dirname(os.path.dirname(os.path.dirname(csharp_exe)))

    if os.path.exists(csharp_exe) and os.path.exists(csharp_cfg):
        try:
            out = open(os.path.join(OUTDIR, "_battle_out.txt"), "w", encoding="utf-8", errors="replace")
            err = open(os.path.join(OUTDIR, "_battle_err.txt"), "w", encoding="utf-8", errors="replace")
            cmd = [csharp_exe, "--config", csharp_cfg, "--run"]
            p = subprocess.Popen(cmd, cwd=csharp_workdir,
                                 stdout=out, stderr=err, stdin=subprocess.DEVNULL,
                                 creationflags=0x08000000)
            log("  ★ 权威 3.19 战斗服已启动: CODOLCombatServer.exe --config %s --run (pid=%s, UDP 28960)"
                % (csharp_cfg, p.pid))
            return p
        except Exception as e:
            log("  C# 战斗服启动失败: %r，尝试 Python 回退..." % (e,))

    script = os.path.join(OUTDIR, "battle_server.py")
    if not os.path.exists(script):
        log("  战斗服: 开关在, 但找不到 %s 或 C# 独立服务器" % script)
        return None
    try:
        out = open(os.path.join(OUTDIR, "_battle_out.txt"), "w")
        err = open(os.path.join(OUTDIR, "_battle_err.txt"), "w")
        p = subprocess.Popen([sys.executable, script, "--bind", bind, "--port", str(port)],
                             stdout=out, stderr=err, stdin=subprocess.DEVNULL,
                             creationflags=0x08000000)
        log("  ★ 战斗服(Python回退)已启动: battle_server.py --bind %s --port %d (pid=%s, UDP)"
            % (bind, port, p.pid))
        return p
    except Exception as e:
        log("  战斗服启动失败: %r" % (e,))
        return None"""

assert old_func in content, "old_func not found in lobby_server.py"
content = content.replace(old_func, new_func, 1)

with open("REF_LOBBY_KIT/lobby_server.py", "w", encoding="utf-8") as f:
    f.write(content)

print("lobby_server.py updated to prioritize CODOLCombatServer.exe!")
