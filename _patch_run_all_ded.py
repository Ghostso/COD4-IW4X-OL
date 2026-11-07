# -*- coding: utf-8 -*-
path = r"REF_LOBBY_KIT\run_all.py"
with open(path, "r", encoding="utf-8", errors="ignore") as f:
    lines = f.readlines()

new_func = [
    'def start_battle_server(bind="0.0.0.0", port=28960):\n',
    '    """【途径 1】官方原生 Dedicated 引擎战斗服 (codol_dedrun.exe on UDP 127.0.0.1:28960)"""\n',
    '    print("=" * 70)\n',
    '    print("[*] 起【途径 1 原生专用战斗服】 UDP %s:%d : codol_dedrun.exe" % (bind, port))\n',
    '    print("=" * 70)\n',
    '    spawn_script = os.path.abspath(os.path.join(ROOT, "..", "_spawn_native_server_28960.py"))\n',
    '    try:\n',
    '        subprocess.Popen([sys.executable, spawn_script],\n',
    '                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,\n',
    '                         stdin=subprocess.DEVNULL, creationflags=0x08000000)\n',
    '    except Exception as e:\n',
    '        print("      !! 起原生专用战斗服失败: %r" % (e,))\n',
    '        return False\n',
    '    time.sleep(3.5)\n',
    '    print("      ★ 原生专用战斗服已启动, 正在监听 UDP 127.0.0.1:28960")\n',
    '    return True\n',
]

lines[395:425] = new_func

with open(path, "w", encoding="utf-8") as f:
    f.writelines(lines)

print("Successfully replaced start_battle_server in run_all.py with Native Dedicated Server!")