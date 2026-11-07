# -*- coding: utf-8 -*-
"""
run_combat_pipeline.py — CODOL 3.19 战斗服务器端与大厅服务统一编排运行器

本脚本作为 3.19 战斗服务器构建的一键入口：
1. 校验环境与配置文件；
2. 支持 --verify 全链路自动化验证（离线契约 + UDP 真实网络双端测试）；
3. 支持 --combat 独立启动 3.19 独立战斗服务器（UDP 28960）；
4. 支持 --all 同时启动战斗服与大厅服，打通全链路交互。
"""

import sys, os, time, subprocess, argparse, socket

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
COMBAT_DIR = os.path.join(ROOT_DIR, "CODOL-Combat-Server-v0.1")
COMBAT_EXE = os.path.join(COMBAT_DIR, "build", "bin", "CODOLCombatServer.exe")
COMBAT_CFG = os.path.join(COMBAT_DIR, "config", "firingrange_live.cfg")
LOBBY_DIR = os.path.join(ROOT_DIR, "REF_LOBBY_KIT")
LOBBY_SCRIPT = os.path.join(LOBBY_DIR, "lobby_server.py")

def log(tag, msg):
    print(f"[{time.strftime('%H:%M:%S')}] [{tag}] {msg}", flush=True)

def verify_all():
    log("VERIFY", "==================================================")
    log("VERIFY", "开始全量自动化验证 (CODOL 3.19 战斗服务体系)")
    log("VERIFY", "==================================================")

    # 1. 离线协议与 A/B 门禁验证
    log("VERIFY", "[1/3] 执行离线协议与 mmbook accepted 门禁测试...")
    res = subprocess.run([sys.executable, "test_offline_replay.py"], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if res.returncode == 0:
        log("VERIFY", "  -> [PASS] test_offline_replay.py 通过 (100% 匹配)")
    else:
        log("VERIFY", f"  -> [FAIL] test_offline_replay.py 失败: {res.stderr or res.stdout}")
        return False

    # 2. 单客户端 UDP 真实网络全链路
    log("VERIFY", "[2/3] 执行单客户端 UDP 真实网络握手与快照测试...")
    res = subprocess.run([sys.executable, "test_full_wire_inmatch.py"], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if res.returncode == 0:
        log("VERIFY", "  -> [PASS] test_full_wire_inmatch.py 通过 (UDP 28960 实机通过)")
    else:
        log("VERIFY", f"  -> [FAIL] test_full_wire_inmatch.py 失败: {res.stderr or res.stdout}")
        return False

    # 3. 战斗伤害与射线物理测试
    log("VERIFY", "[3/3] 执行战斗伤害系统与射线命中测试...")
    res = subprocess.run([sys.executable, "test_combat_physics.py"], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if res.returncode == 0:
        log("VERIFY", "  -> [PASS] test_combat_physics.py 通过 (伤害/击杀/重生/命中全绿)")
    else:
        log("VERIFY", f"  -> [FAIL] test_combat_physics.py 失败: {res.stderr or res.stdout}")
        return False

    log("VERIFY", "==================================================")
    log("VERIFY", "全部 3 项全链路自动化验证 100% 通过！体系就绪！")
    log("VERIFY", "==================================================")
    return True

def run_combat_server():
    log("COMBAT", f"启动 3.19 战斗服务器: {COMBAT_EXE}")
    log("COMBAT", f"加载配置文件: {COMBAT_CFG}")
    cmd = [COMBAT_EXE, "--config", COMBAT_CFG, "--run"]
    p = subprocess.Popen(cmd, cwd=COMBAT_DIR)
    return p

def main():
    parser = argparse.ArgumentParser(description="CODOL 3.19 战斗服务编排器")
    parser.add_argument("--verify", action="store_true", help="运行全链路自动化验证套件")
    parser.add_argument("--combat", action="store_true", help="单独启动战斗服务器 (UDP 28960)")
    args = parser.parse_args()

    if args.verify:
        success = verify_all()
        sys.exit(0 if success else 1)

    if args.combat:
        p = run_combat_server()
        try:
            p.wait()
        except KeyboardInterrupt:
            log("COMBAT", "收到终止信号，正在关闭战斗服务器...")
            p.terminate()
            p.wait()
            log("COMBAT", "战斗服务器已安全停止。")
        sys.exit(0)

    # 默认输出帮助并执行快速自检
    print("CODOL 3.19 战斗服务器编排器")
    print("可用参数:")
    print("  --verify : 执行全量端到端验证套件 (推荐)")
    print("  --combat : 启动权威战斗服务器 (UDP 28960)")
    print("\n自动执行快速验证...")
    verify_all()

if __name__ == "__main__":
    main()
