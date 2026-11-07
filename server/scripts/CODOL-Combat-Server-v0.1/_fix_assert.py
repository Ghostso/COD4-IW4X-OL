# -*- coding: utf-8 -*-
import io
p = r"src\SelfTest.cs"
s = io.open(p, encoding="utf-8").read()

old3 = '''            // (3) 声明的 lastChangedField(offset 11/12) 必须原样被解出
            Check(decoded[11] == snap[11] && decoded[12] == snap[12],
                "判官解我方首帧快照: lastChangedField 两字节原样",
                "dec=" + decoded[11].ToString("X2") + decoded[12].ToString("X2") +
                " want=" + snap[11].ToString("X2") + snap[12].ToString("X2"));'''
assert s.count(old3) == 1, s.count(old3)
new3 = '''            // (3) 声明的 lastChangedField(快照体内偏移 11/12) 必须原样被解出。
            //     payload = seq(4) + snapshot，故 snapshot[k] <-> payload[4+k]。
            Check(decoded[4 + 11] == snap[11] && decoded[4 + 12] == snap[12],
                "判官解我方首帧快照: lastChangedField 两字节原样",
                "dec=" + decoded[4 + 11].ToString("X2") + decoded[4 + 12].ToString("X2") +
                " want=" + snap[11].ToString("X2") + snap[12].ToString("X2"));'''
s = s.replace(old3, new3)

old5 = '''            // (5) gamestate 路径同构性: seq=1 -> mask=0 -> 明文直达
            byte[] gs = new byte[259];
            gs[4] = 0x03;
            byte[] gpl = OursEncode(1, gs);
            byte[] gdc = JudgeDecode(gpl, JudgeSeedA);
            Check(gdc[8] == 0x00,
                "seq=1 时 mask==0, 判官看到原始字节 (对照: gamestate 首帧明文送达)",
                "op=" + gdc[8].ToString("X2"));'''
assert s.count(old5) == 1, s.count(old5)
new5 = '''            // (5) gamestate 路径同构性: 同一编码公式下，判官必须解出 gamestate opcode=3。
            //     gamestate.bin 布局 = 00 00 00 00 03 ...，其 [4] 落在 payload[8]。
            byte[] gs = new byte[259];
            gs[4] = 0x03;
            foreach (uint q in new uint[] { 1u, 2u, 3u, 29u })
            {
                byte[] gpl = OursEncode(q, gs);
                byte[] gdc = JudgeDecode(gpl, JudgeSeedA);
                Check(gdc[8] == 0x03,
                    "判官解我方 gamestate (seq=" + q + "): offset8 == 0x03 (gamestate opcode)",
                    "op=0x" + gdc[8].ToString("X2"));
            }'''
s = s.replace(old5, new5)
io.open(p, "w", encoding="utf-8", newline="\n").write(s)
print("assertions fixed")
