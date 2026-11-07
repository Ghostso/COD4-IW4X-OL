import os

target_file = r"CODOL-Combat-Server-v0.1\src\Engine\ClientLogic.cs"
with open(target_file, "r", encoding="utf-8") as f:
    c = f.read()

# 1. Patch stage == 6 block
old_stage6 = """                    if (stage == 6)
                    {
                        s.ClientEntered = false;
                        s.FirstSnapshotSeq = 0;
                        s.SnapshotSent = false;
                        s.SnapshotEpochMs = NowMs;
                        s.SnapshotDueMs = NowMs;
                        s.Ready = true;
                        _log.Info("SNAPSHOT", "Client reached stage 6 (Loading Complete)! Arming entry snapshots (flags 0x0A) peer=" + s.PeerKey);
                    }"""

new_stage6 = """                    if (stage == 6)
                    {
                        s.ClientEntered = false;
                        s.FirstSnapshotSeq = 0;
                        s.SnapshotSent = false;
                        s.SnapshotAttempts = 0;
                        s.SnapshotEpochMs = NowMs;
                        s.SnapshotDueMs = NowMs;
                        s.Ready = true;
                        _log.Info("SNAPSHOT", "Client reached stage 6 (Loading Complete)! Arming entry snapshots (flags 0x0A) peer=" + s.PeerKey);
                    }"""

assert old_stage6 in c, "old_stage6 not found in ClientLogic.cs"
c = c.replace(old_stage6, new_stage6, 1)

# 2. Patch PumpSnapshot gate and transition
old_pump = """        public void PumpSnapshot(ClientSession s, double now)
        {
            double dtMs = 1000.0 / _cfg.SnapshotHz;
            if (s.Cancelled || s.SnapshotDueMs < 0 || now < s.SnapshotDueMs) return;
            if (now - s.LastRxMs > _cfg.SessionTimeoutMs) return;"""

new_pump = """        public void PumpSnapshot(ClientSession s, double now)
        {
            if (!s.Ready) return; // 地图加载完成 (stage 6) 之前不下发快照，避免冲垮客户端加载器
            double dtMs = 1000.0 / _cfg.SnapshotHz;
            if (s.Cancelled || s.SnapshotDueMs < 0 || now < s.SnapshotDueMs) return;
            if (now - s.LastRxMs > _cfg.SessionTimeoutMs) return;"""

assert old_pump in c, "old_pump not found in ClientLogic.cs"
c = c.replace(old_pump, new_pump, 1)

# 3. Patch transition condition
old_trans = """            if (!s.ClientEntered && (s.InputPackets > 0 || s.SnapshotAttempts >= 3))
            {
                s.ClientEntered = true;
                _log.Info("SNAPSHOT", "★ Client armed for active 3D rendering (inputs=" + s.InputPackets +
                                      " attempts=" + s.SnapshotAttempts + ") peer=" + s.PeerKey);
            }"""

new_trans = """            if (!s.ClientEntered && s.SnapshotAttempts >= 3)
            {
                s.ClientEntered = true;
                _log.Info("SNAPSHOT", "★ Client armed for active 3D rendering (attempts=" + s.SnapshotAttempts + ") peer=" + s.PeerKey);
            }"""

assert old_trans in c, "old_trans not found in ClientLogic.cs"
c = c.replace(old_trans, new_trans, 1)

with open(target_file, "w", encoding="utf-8") as f:
    f.write(c)

print("Applied final snapshot transition fixes to ClientLogic.cs successfully!")
