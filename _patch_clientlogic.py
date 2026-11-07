import os

target_file = r"CODOL-Combat-Server-v0.1\src\Engine\ClientLogic.cs"
with open(target_file, "r", encoding="utf-8") as f:
    c = f.read()

old_block = """            bool first = !s.ClientEntered;
            bool omit = s.SnapshotSent && _snapOpts.ClientMovement && !first;
            if (_snapOpts.SpawnFromMap && !first) omit = true;

            double px = s.Player.X, py = s.Player.Y, pz = s.Player.Z;
            double pvx = s.Player.VX, pvy = s.Player.VY;
            if (_snapOpts.SpawnAt != null && _snapOpts.StaticSpawn)
            {
                px = _snapOpts.SpawnAt[0]; py = _snapOpts.SpawnAt[1]; pz = _snapOpts.SpawnAt[2];
                omit = false;
            }
            else if (_snapOpts.SpawnAt != null && first)
            {
                px = _snapOpts.SpawnAt[0]; py = _snapOpts.SpawnAt[1]; pz = _snapOpts.SpawnAt[2];
                omit = false;
            }

            int bits;
            byte[] state = MotionSnapshot.Build(s.ClientReliableAck, (uint)serverTime, s.ProcessedInputTime,
                first, px, py, pz, s.Player.Pitch, s.Player.Yaw, s.Player.Roll,
                pvx, pvy, s.AimFraction, s.IsAiming, s.Equipment, _snapOpts, omit, out bits);"""

new_block = """            // ★ 客户端入场状态机（对齐 sv_snapshot_mp.cpp 与实机渲染链路）：
            // 1. Attempt 0: 发送 flags=0x0A (0x08 | 0x02)，触发 CL_FirstSnapshot 跃迁至 CA_ACTIVE (10)
            // 2. Attempt 1..2: 撤销 0x02 入场标志，发送 flags=0x08 (纯 baseline 帧，避免重入震荡)
            // 3. Attempt 3+ 或收到客户端 usercmd (InputPackets > 0): 跃迁为常规场景帧 (delta=1, flags=0x04)
            //    cgame 不再命中 SnapshotSceneBlockFlags (0x0A)，正式放行 3D 场景渲染并关闭“正在等待玩家数据”！
            if (!s.ClientEntered && (s.InputPackets > 0 || s.SnapshotAttempts >= 3))
            {
                s.ClientEntered = true;
                _log.Info("SNAPSHOT", "★ Client armed for active 3D rendering (inputs=" + s.InputPackets +
                                      " attempts=" + s.SnapshotAttempts + ") peer=" + s.PeerKey);
            }

            bool first = !s.ClientEntered;
            SnapshotOptions currentOpts = _snapOpts;
            if (first && s.SnapshotAttempts >= 1)
            {
                currentOpts = new SnapshotOptions();
                currentOpts.SnapshotEntryFlag = false; // Attempt >= 2: 撤销 0x02
            }

            bool omit = s.SnapshotSent && _snapOpts.ClientMovement && !first;
            if (_snapOpts.SpawnFromMap && !first) omit = true;

            double px = s.Player.X, py = s.Player.Y, pz = s.Player.Z;
            double pvx = s.Player.VX, pvy = s.Player.VY;
            if (_snapOpts.SpawnAt != null && _snapOpts.StaticSpawn)
            {
                px = _snapOpts.SpawnAt[0]; py = _snapOpts.SpawnAt[1]; pz = _snapOpts.SpawnAt[2];
                omit = false;
            }
            else if (_snapOpts.SpawnAt != null && first)
            {
                px = _snapOpts.SpawnAt[0]; py = _snapOpts.SpawnAt[1]; pz = _snapOpts.SpawnAt[2];
                omit = false;
            }

            int bits;
            byte[] state = MotionSnapshot.Build(s.ClientReliableAck, (uint)serverTime, s.ProcessedInputTime,
                first, px, py, pz, s.Player.Pitch, s.Player.Yaw, s.Player.Roll,
                pvx, pvy, s.AimFraction, s.IsAiming, s.Equipment, currentOpts, omit, out bits);"""

assert old_block in c, "old_block not found in ClientLogic.cs"
c = c.replace(old_block, new_block, 1)

with open(target_file, "w", encoding="utf-8") as f:
    f.write(c)

print("ClientLogic.cs patched successfully!")
