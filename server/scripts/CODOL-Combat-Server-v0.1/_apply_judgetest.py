# -*- coding: utf-8 -*-
import io
p = r"src\SelfTest.cs"
s = io.open(p, encoding="utf-8").read()
marker = "        // ============================================================ 6. 端到端离线复放"
assert s.count(marker) == 1, ("marker", s.count(marker))

block = r'''        // ============================================ 5b. 客户端"判官"解码一致性
        // 依据: image_best.bin (O-4 运行时映像) 的收包解码器 0x470A60 实测反汇编:
        //
        //     base  = *(uint*)0x331C0C8 ^ 0xD362501F
        //     dl    = byte[base+0x80148] ^ byte[base+0x138]
        //     其中 byte[base+0x80148] 由 0x5C23D8 写入 = 报文前 4 字节(= 我方 seq)的低字节
        //     演化项 = keyT[i] << (i&1); keyT = base+0x148+block*0x400
        //     实测 keyT 全表 512KB 为零 -> 无演化
        //     0x5C242B 对 payload[8 .. cursize] 逐字节: payload[i] ^= dl
        //
        // 即：判官的解码 == 与常数 (seq_lo ^ seedA) 逐字节 XOR，从偏移 8 起。
        // 我方 gamestate 与 snapshot 必须都能被这条公式解回原始明文，
        // 且解出的 payload[8] 必须是对应 opcode（snapshot=0, gamestate=3）。
        private const byte JudgeSeedA = 0x01;   // 实测: live 对局转储 base+0x138 = 1

        /// <summary>复现客户端 0x470A60 的解码（keyT 恒零，故退化为常数 XOR）。</summary>
        private static byte[] JudgeDecode(byte[] payload, byte seedA)
        {
            byte[] r = new byte[payload.Length];
            Buffer.BlockCopy(payload, 0, r, 0, payload.Length);
            byte dl = (byte)(payload[0] ^ seedA);          // seedB(=payload[0]) ^ seedA
            for (int i = 8; i < r.Length; i++) r[i] ^= dl; // 演化项恒为零
            return r;
        }

        /// <summary>复现我方写出路径：payload = seq(4)+state，从偏移 8 起与 (seq^1) XOR。</summary>
        private static byte[] OursEncode(uint seq, byte[] state)
        {
            byte[] payload = new byte[4 + state.Length];
            Buffer.BlockCopy(BitConverter.GetBytes(seq), 0, payload, 0, 4);
            Buffer.BlockCopy(state, 0, payload, 4, state.Length);
            byte mask = (byte)((seq ^ 1u) & 0xFFu);
            for (int i = 8; i < payload.Length; i++) payload[i] ^= mask;
            return payload;
        }

        private static void SectionJudgeCodec()
        {
            Console.WriteLine("[5b] 客户端判官解码一致性 (0x470A60)");

            Equipment eq = new Equipment();
            SnapshotOptions opt = new SnapshotOptions();
            opt.SnapshotEntryFlag = false;
            int bits;
            List<int> order = new List<int>();
            byte[] snap = MotionSnapshot.Build(0, 1000, 1000, true, 48.0f, -572.0f, -116.0f,
                0, 0, 0, 0.0, 0.0, 0.0, false, eq, opt, false, order, out bits);

            // (1) 首帧快照: seq=4 -> 判官必须解出 opcode 0
            uint seq = 4;
            byte[] payload = OursEncode(seq, snap);
            byte[] decoded = JudgeDecode(payload, JudgeSeedA);
            Check(decoded[8] == 0x00,
                "判官解我方首帧快照: offset8 == 0x00 (snapshot opcode)",
                "got=0x" + decoded[8].ToString("X2"));

            // (2) 整帧必须与原始明文逐字节一致
            byte[] plain = new byte[4 + snap.Length];
            Buffer.BlockCopy(BitConverter.GetBytes(seq), 0, plain, 0, 4);
            Buffer.BlockCopy(snap, 0, plain, 4, snap.Length);
            int diff = 0, firstDiff = -1;
            for (int i = 8; i < plain.Length; i++)
                if (decoded[i] != plain[i]) { if (firstDiff < 0) firstDiff = i; diff++; }
            Check(diff == 0,
                "判官解我方首帧快照: 全帧逐字节 == 明文",
                "diffBytes=" + diff + " firstDiff=" + firstDiff);

            // (3) 声明的 lastChangedField(offset 11/12) 必须原样被解出
            Check(decoded[11] == snap[11] && decoded[12] == snap[12],
                "判官解我方首帧快照: lastChangedField 两字节原样",
                "dec=" + decoded[11].ToString("X2") + decoded[12].ToString("X2") +
                " want=" + snap[11].ToString("X2") + snap[12].ToString("X2"));

            // (4) 连续多帧(不同 seq) 都要解对 —— 覆盖 seq&0xFF 的各种取值
            bool allOk = true; string firstBad = null;
            foreach (uint q in new uint[] { 4, 5, 6, 7, 43, 100, 255, 256, 257, 1000 })
            {
                byte[] pl = OursEncode(q, snap);
                byte[] dc = JudgeDecode(pl, JudgeSeedA);
                byte[] pn = new byte[4 + snap.Length];
                Buffer.BlockCopy(BitConverter.GetBytes(q), 0, pn, 0, 4);
                Buffer.BlockCopy(snap, 0, pn, 4, snap.Length);
                bool ok = dc[8] == 0x00;
                for (int i = 8; ok && i < pl.Length; i++) if (dc[i] != pn[i]) ok = false;
                if (!ok) { allOk = false; if (firstBad == null) firstBad = "seq=" + q + " op=" + dc[8].ToString("X2"); }
            }
            Check(allOk, "判官解我方快照: seq∈{4,5,6,7,43,100,255,256,257,1000} 全部 opcode=0 且全帧一致", firstBad);

            // (5) gamestate 路径同构性: seq=1 -> mask=0 -> 明文直达
            byte[] gs = new byte[259];
            gs[4] = 0x03;
            byte[] gpl = OursEncode(1, gs);
            byte[] gdc = JudgeDecode(gpl, JudgeSeedA);
            Check(gdc[8] == 0x00,
                "seq=1 时 mask==0, 判官看到原始字节 (对照: gamestate 首帧明文送达)",
                "op=" + gdc[8].ToString("X2"));

            // (6) 反例锁定: 若恢复旧的 cmd-演化项, 判官必须解出 opcode>3 (必被丢弃)
            byte[] cmd = Ascii("stats");
            byte[] bad = new byte[4 + snap.Length];
            Buffer.BlockCopy(BitConverter.GetBytes((uint)4), 0, bad, 0, 4);
            Buffer.BlockCopy(snap, 0, bad, 4, snap.Length);
            int m = (int)((4u ^ 1u) & 0xFFu);
            for (int i = 8; i < bad.Length; i++)
            {
                m = (m ^ ((cmd[(i - 8) % cmd.Length] << ((i - 8) & 1)) & 0xFF)) & 0xFF;
                bad[i] ^= (byte)m;
            }
            byte[] badDec = JudgeDecode(bad, JudgeSeedA);
            Check(badDec[8] != 0x00 && (badDec[8] > 3),
                "反例: 旧 cmd-演化掩码会让判官解出 opcode>3 (必被丢弃)",
                "op=0x" + badDec[8].ToString("X2") + " (期望 >0x03)");
        }

'''
s = s.replace(marker, block + marker)
io.open(p, "w", encoding="utf-8", newline="\n").write(s)
print("inserted SectionJudgeCodec")

# 注册到 sections
old_names = 'string[] names = { "1-密码学", "2-大整数/P-224", "3-协议编解码", "4-客户端命令解析", "5-快照编码", "6-端到端复放"'
assert s.count(old_names) == 1
s = s.replace(old_names, 'string[] names = { "1-密码学", "2-大整数/P-224", "3-协议编解码", "4-客户端命令解析", "5-快照编码", "5b-判官解码", "6-端到端复放"')

old_acts = 'Action[] sections = { SectionCrypto, SectionBigIntAndEc, SectionProtocolCodec, SectionClientParser, SectionSnapshotEncoding, SectionEndToEndReplay'
assert s.count(old_acts) == 1
s = s.replace(old_acts, 'Action[] sections = { SectionCrypto, SectionBigIntAndEc, SectionProtocolCodec, SectionClientParser, SectionSnapshotEncoding, SectionJudgeCodec, SectionEndToEndReplay')
io.open(p, "w", encoding="utf-8", newline="\n").write(s)
print("registered SectionJudgeCodec")
