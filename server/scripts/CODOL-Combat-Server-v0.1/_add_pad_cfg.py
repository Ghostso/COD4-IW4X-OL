# -*- coding: utf-8 -*-
import io
p = r"src\Engine\ServerConfig.cs"
s = io.open(p, encoding="utf-8").read()
old = '''        /// <summary>单帧最大步长（秒），防止长暂停后一次积分过远。</summary>
        public double MaxFrameTime = 0.25;'''
assert s.count(old) == 1
new = old + '''
        // ---- [LEN-SCAN 2026-10-16] 快照体长度扫描实验 (纯实验开关, 默认关) ----
        /// <summary>固定追加到快照体尾部的字节数 (0=关)。</summary>
        public int SnapshotPadBytes = 0;
        /// <summary>长度扫描: >0 时每 25 帧把 pad 增加该值, 上限由 SnapshotPadMax 限制。</summary>
        public int SnapshotPadStep = 0;
        public int SnapshotPadMax = 400;
        /// <summary>扫描时每多少帧换一档。</summary>
        public int SnapshotPadEvery = 25;'''
s = s.replace(old, new)

old2 = '''                case "max_frame_time": MaxFrameTime = double.Parse(value, CultureInfo.InvariantCulture); break;'''
assert s.count(old2) == 1
new2 = old2 + '''
                case "snap_pad": SnapshotPadBytes = int.Parse(value, CultureInfo.InvariantCulture); break;
                case "snap_pad_step": SnapshotPadStep = int.Parse(value, CultureInfo.InvariantCulture); break;
                case "snap_pad_max": SnapshotPadMax = int.Parse(value, CultureInfo.InvariantCulture); break;
                case "snap_pad_every": SnapshotPadEvery = int.Parse(value, CultureInfo.InvariantCulture); break;'''
s = s.replace(old2, new2)
io.open(p, "w", encoding="utf-8", newline="\n").write(s)
print("ServerConfig.cs patched")
