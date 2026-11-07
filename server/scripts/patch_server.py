with open(r'CODOL-Combat-Server-v0.1\src\Engine\ClientLogic.cs', 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Update lines 841-858 in PumpSnapshot
old_snap_state = """            // ★ 客户端入场状态机（对齐 sv_snapshot_mp.cpp 与实机渲染链路）：
            // 1. Attempt 0: 发送 flags=0x0A (0x08 | 0x02)，触发 CL_FirstSnapshot 跃迁至 CA_ACTIVE (10)
            // 2. Attempt 1..2: 撤销 0x02 入场标志，发送 flags=0x08 (纯 baseline 帧，避免重入震荡)
            // 3. Attempt 3+ 或收到客户端 usercmd (InputPackets > 0): 跃迁为常规场景帧 (delta=1, flags=0x04)
            //    cgame 不再命中 SnapshotSceneBlockFlags (0x0A)，正式放行 3D 场景渲染并关闭“正在等待玩家数据”！
            if (!s.ClientEntered && s.SnapshotAttempts >= 3)
            {
                s.ClientEntered = true;
                _log.Info("SNAPSHOT", "★ Client armed for active 3D rendering (attempts=" + s.SnapshotAttempts + ") peer=" + s.PeerKey);
            }

            bool first = !s.ClientEntered;
            SnapshotOptions currentOpts = _snapOpts;
            if (first && s.SnapshotAttempts >= 1)
            {
                currentOpts = new SnapshotOptions();
                currentOpts.SnapshotEntryFlag = false; // Attempt >= 2: 撤销 0x02
            }"""

new_snap_state = """            // ★ 客户端权威入场状态机（严格对齐 sv_snapshot_mp.cpp 10290-10335 原生规则）：
            // 1. 在客户端明确回传有效确认（ack >= FirstSnapshotSeq）之前，s.ClientEntered 恒为 false。
            // 2. 期间每一帧快照都是自包含的全量基线帧（first = true, delta = 0, flags = 0x0A [0x08 | 0x02]），
            //    确保持续提供 CL_FirstSnapshot 的 0x02 入场凭证，绝不因尝试次数擅自撤销 0x02 或提前跃迁 delta=1 帧。
            // 3. 一旦客户端确认入场，s.ClientEntered 跃迁为 true，撤销 0x02，转入常规增量帧（delta = 1, flags = 0x04）。
            bool first = !s.ClientEntered;
            SnapshotOptions currentOpts = _snapOpts;
            currentOpts.SnapshotEntryFlag = !s.ClientEntered;"""

assert old_snap_state in text, 'old_snap_state not found in ClientLogic.cs!'
text = text.replace(old_snap_state, new_snap_state, 1)

# 2. Update lines 345-353 in HandleNetchan
old_netchan = """            if (s.ClientMessageAck != ack)
            {
                s.ClientMessageAck = ack;
                if (!s.ClientEntered && s.FirstSnapshotSeq > 0 && ack >= s.FirstSnapshotSeq)
                {
                    s.ClientEntered = true;
                    _log.Info("SNAPSHOT", "★ Client successfully entered world! (messageAck=" + ack + " >= firstSeq=" + s.FirstSnapshotSeq + ") peer=" + s.PeerKey);
                }
            }"""

new_netchan = """            if (s.ClientMessageAck != ack)
            {
                s.ClientMessageAck = ack;
            }
            if (!s.ClientEntered && s.FirstSnapshotSeq > 0 && ack >= s.FirstSnapshotSeq)
            {
                s.ClientEntered = true;
                _log.Info("SNAPSHOT", "★ Client successfully entered world! (messageAck=" + ack + " >= firstSeq=" + s.FirstSnapshotSeq + ") peer=" + s.PeerKey);
            }"""

assert old_netchan in text, 'old_netchan not found in ClientLogic.cs!'
text = text.replace(old_netchan, new_netchan, 1)

with open(r'CODOL-Combat-Server-v0.1\src\Engine\ClientLogic.cs', 'w', encoding='utf-8') as f:
    f.write(text)
print('ClientLogic.cs patched successfully!')

# 3. Patch SelfTest.cs line 1403
with open(r'CODOL-Combat-Server-v0.1\src\SelfTest.cs', 'r', encoding='utf-8') as f:
    st_text = f.read()

old_st = 'for (int i = 0; i < 40; i++) h.Tick();\n                int oldSend = s1.SendSeq;'
new_st = 'for (int i = 0; i < 80; i++) h.Tick();\n                int oldSend = s1.SendSeq;'
assert old_st in st_text, 'old_st not found in SelfTest.cs!'
st_text = st_text.replace(old_st, new_st, 1)

with open(r'CODOL-Combat-Server-v0.1\src\SelfTest.cs', 'w', encoding='utf-8') as f:
    f.write(st_text)
print('SelfTest.cs patched successfully!')
