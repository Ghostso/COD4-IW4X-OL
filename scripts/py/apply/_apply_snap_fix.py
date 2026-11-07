path = r"CODOL-Combat-Server-v0.1\src\Codol\MotionSnapshot.cs"
with open(path, "r", encoding="utf-8") as f:
    text = f.read()

# Replace field 20 PmFlagsValue with aiming ? 0x10u : 0u
old_f20 = "w.Index(20, prev); w.Scalar(PmFlagsValue, 32);"
new_f20 = "w.Index(20, prev); w.Scalar(aiming ? 0x10u : 0u, 32);"
assert old_f20 in text, "old_f20 not found"
text = text.replace(old_f20, new_f20, 1)

# Remove field 28
old_f28 = """            // [OLMOD-1649370] eFlags = field 28。codec -98 = presence + 30-bit raw。
            //   站立/行走 = 0；跳跃/传送位由客户端自己维护。此字段缺失会让客户端误判地面状态。
            w.Index(28, prev); w.Bits(1, 1); w.Bits(0, 30);"""
assert old_f28 in text, "old_f28 not found"
text = text.replace(old_f28, "", 1)

# Restore field 61 and remove field 47
old_f47_54_60_63 = """            w.Index(47, prev); w.Scalar(opt != null && opt.OnGround ? 2046 : 2047, 11);
            // [OLMOD-1649370] field 54 otherFlags: codec -102 = presence bit + 31 raw bits (NO baseline XOR).
            //   官方写入: if (otherFlags) { WriteBits(1,1); WriteBits(otherFlags,31); } else WriteBits(0,1);
            //   值: Playing 只写 POF_PLAYER(0x1000)。0x800 是 POF_FOLLOW(观战)，会让客户端进入观战叠加态。
            w.Index(54, prev); w.Bits(1, 1); w.Bits(OtherFlagsValue, 31);
            w.Index(56, prev); w.Scalar(139, 10);
            w.Index(60, prev); w.Scalar(190, 16);
            w.Index(63, prev); w.Scalar(800, 16);
            w.Index(68, prev); w.Scalar(2047, 11);
            // [OLMOD-1649370] pm_type = field 83, 8 bits. Playing 必须为 0(PM_NORMAL)。
            //   缺失时客户端走 spectator/noclip 分支 -> 无碰撞自由飞行（用户实测的"COD 飞行穿墙动作"）。
            w.Index(83, prev); w.Scalar(0, 8);"""

new_f54_61 = """            w.Index(54, prev); w.Bits(1, 1); w.Bits(0x1000, 31);
            w.Index(56, prev); w.Scalar(139, 10);
            w.Index(60, prev); w.Scalar(190, 16);
            w.Index(61, prev); w.Scalar((uint)(opt != null && opt.OnGround ? 2046 : 2047), 16);
            w.Index(63, prev); w.Scalar(800, 16);
            w.Index(68, prev); w.Scalar(2047, 11);"""

assert old_f47_54_60_63 in text, "old_f47_54_60_63 not found"
text = text.replace(old_f47_54_60_63, new_f54_61, 1)

with open(path, "w", encoding="utf-8") as f:
    f.write(text)

print("Successfully restored BuildVerifiedMotionSnapshot to clean 29-field baseline!")
