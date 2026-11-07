# -*- coding: utf-8 -*-
import io
p = r"src\Engine\ClientLogic.cs"
s = io.open(p, encoding="utf-8").read()

old = '''                int mask = (int)((seq ^ 1u) & 0xFFu);
                byte[] cmd = Encoding.ASCII.GetBytes(s.ClientReliableCommand);
                for (int i = 8; i < payload.Length; i++)
                {
                    if (cmd.Length > 0)
                        mask = (mask ^ ((cmd[(i - 8) % cmd.Length] << ((i - 8) & 1)) & 0xFF)) & 0xFF;
                    payload[i] ^= (byte)mask;
                }'''
assert s.count(old) == 1, s.count(old)

new = '''                // [MASK-FIX 2026-10-16] 客户端解码器 = 0x470A60（image_best.bin 实测）:
                //     dl  = byte[base+0x80148](= 本包 seq 低字节) ^ byte[base+0x138](= seedA)
                //     演化项 = keyT[i] << (i&1);  实测 keyT 整表 512KB 全 0 -> 无演化
                //     for i: payload[8+i] ^= dl
                // 即：与常数 (seq ^ seedA) 逐字节 XOR。gamestate 路径已是这一套（seedA 恰为 1），
                // snapshot 原先多了一个"按 ClientReliableCommand 逐字节演化"的项，判官没有该逻辑，
                // 导致 offset8(应=0 snapshot opcode) 被解成 0x73('s') > 3，进 0x473C1C 错误路径整条丢弃。
                // 故此处与 gamestate 完全对齐。
                int mask = (int)((seq ^ 1u) & 0xFFu);
                for (int i = 8; i < payload.Length; i++) payload[i] ^= (byte)mask;'''
s = s.replace(old, new)
io.open(p, "w", encoding="utf-8", newline="\n").write(s)
print("ClientLogic.cs patched")
