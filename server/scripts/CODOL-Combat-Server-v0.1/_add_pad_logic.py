# -*- coding: utf-8 -*-
import io
p = r"src\Engine\ClientLogic.cs"
s = io.open(p, encoding="utf-8").read()

# 1) 在 Build 之后、payload 组装之前插入 padding (legacy 路径)
old = '''            byte[] state = MotionSnapshot.Build(s.ClientReliableAck, (uint)serverTime, s.ProcessedInputTime,'''
assert s.count(old) == 1, s.count(old)

# 找 Build 调用的结束行
anchor = '''            uint seq;
            if (_cfg.ProtocolMode == CodolProtocolMode.Codol2697)'''
assert s.count(anchor) == 1, s.count(anchor)
ins = '''            // [LEN-SCAN 2026-10-16] 快照体长度扫描实验 (默认关: SnapshotPadBytes/Step 均为 0)
            if (_cfg.SnapshotPadBytes > 0 || _cfg.SnapshotPadStep > 0)
            {
                int pad = _cfg.SnapshotPadBytes;
                if (_cfg.SnapshotPadStep > 0)
                {
                    // 按帧号分档递增 (每 SnapshotPadEvery 帧 +Step, 上限 SnapshotPadMax)
                    long tier = (long)(_snapshotCount / Math.Max(1, _cfg.SnapshotPadEvery));
                    pad = _cfg.SnapshotPadBytes + (int)(tier * _cfg.SnapshotPadStep);
                    if (pad > _cfg.SnapshotPadMax) pad = _cfg.SnapshotPadMax;
                    if (pad < 0) pad = 0;
                }
                if (pad > 0)
                {
                    byte[] padded = new byte[state.Length + pad];
                    Buffer.BlockCopy(state, 0, padded, 0, state.Length);
                    state = padded;
                    if (!_padLogged || pad != _padLast)
                    {
                        _padLast = pad; _padLogged = true;
                        _log.Warn("LENSCAN", "快照体 padding = " + pad + "B -> state=" + state.Length +
                                             "B (tier=" + (pad - _cfg.SnapshotPadBytes) / Math.Max(1, _cfg.SnapshotPadStep) + ")");
                    }
                }
            }

''' + anchor
s = s.replace(anchor, ins)

# 2) 加字段 + 计数器自增
oldf = '''        private int _lastStatMs'''
if s.count(oldf) == 0:
    oldf = '''        private readonly PacketSender _send;'''
assert s.count(oldf) >= 1
s = s.replace(oldf, '''        // [LEN-SCAN 2026-10-16]
        private bool _padLogged;
        private int _padLast = -1;
        private long _snapshotCount;

''' + oldf, 1)
io.open(p, "w", encoding="utf-8", newline="\n").write(s)
print("ClientLogic.cs patched (fields + padding)")
