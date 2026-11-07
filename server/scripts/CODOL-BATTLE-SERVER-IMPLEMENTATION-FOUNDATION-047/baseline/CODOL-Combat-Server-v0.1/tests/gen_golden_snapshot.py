# -*- coding: utf-8 -*-
"""生成"首帧快照"黄金向量（由 Python 参考实现产出）。

用法（在 REF_LOBBY_KIT 目录里跑，或用 --kit 指向它）:
    python tests/gen_golden_snapshot.py --kit "D:\...\REF_LOBBY_KIT" --out tests/golden_first_snapshot.hex

入参固定为 C# 自测里的同一组值，因此两边可直接逐字节比较：
    ack=0 serverTime=1000 commandTime=1000 first=True
    x=48 y=-572 z=-116 pitch=0 yaw=0 roll=0 vx=0 vy=0 aimFraction=0 aiming=False
    equipment = 默认（custom1: M4A1 1156）
开关全部关闭: client_movement / spawn_from_map / static_spawn / omit_viewangles /
              slot_events_legacy / idx45 / idx219 都对应"文件不存在"。
"""
import argparse
import os
import sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kit", required=True, help="REF_LOBBY_KIT 目录（含 battle_server.py）")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    kit = os.path.abspath(a.kit)
    sys.path.insert(0, kit)
    # 确保所有 .on / .txt 开关都不存在（黄金向量必须是"全默认"基线）
    for f in ("client_movement.on", "spawn_from_map.on", "static_spawn.on", "omit_viewangles.on",
              "slot_events_legacy.on", "idx45.on", "idx219.on", "spawn_at.txt", "dir_bias.txt",
              "force_dir.txt", "mirror_predicted.on"):
        p = os.path.join(kit, f)
        if os.path.exists(p):
            print("!! 开关文件存在，黄金向量可能不是基线: %s" % p)
    import battle_server as bs

    # 逐项复刻 snake 的入参
    eq = bs._Equipment()
    snap, nbits = bs._build_motion_snapshot(
        0, 1000, 1000, True,
        48.0, -572.0, -116.0, 0, 0, 0,
        0.0, 0.0, 0.0, False, eq, omit_motion=False)

    out = os.path.abspath(a.out)
    d = os.path.dirname(out)
    if d and not os.path.isdir(d):
        os.makedirs(d)
    with open(out, "w", encoding="ascii") as f:
        f.write(snap.hex())
    print("写出 %s" % out)
    print("  len=%d bytes, bits=%d" % (len(snap), nbits))
    print("  hex=%s" % snap.hex())


if __name__ == "__main__":
    main()
