path = r"CODOL-Combat-Server-v0.1\src\Codol\MotionSnapshot.cs"
with open(path, "r", encoding="utf-8") as f:
    text = f.read()

old_block = """            w.Index(63, prev); w.Scalar(800, 16);
            w.Index(68, prev); w.Scalar(2047, 11);

            w.Index(219, prev);"""

new_block = """            w.Index(63, prev); w.Scalar(800, 16);
            w.Index(68, prev); w.Scalar(2047, 11);

            // [PM_TYPE 2026-10-17] 官方实测算法 (sv_snapshot_mp.cpp:18990):
            // 当 pm_type == 0 (PM_NORMAL) 时，writeUnsignedDelta 仅写入 1 个 bit (0)！
            // 这一位 0 彻底消除客户端 spectator/noclip 分支，恢复正常物理模式与奔跑脚步动画！
            w.Index(83, prev); w.Bits(0, 1);

            w.Index(219, prev);"""

assert old_block in text, "old_block not found in MotionSnapshot.cs"
text = text.replace(old_block, new_block, 1)

with open(path, "w", encoding="utf-8") as f:
    f.write(text)

print("Successfully injected official 1-bit pm_type=0 into BuildVerifiedMotionSnapshot!")
