# 03 - 黄金向量目录

> 以下向量分为“由已确认字段规则构造”的结构黄金向量，不是原版完整消息抓包。
> 完整 2697 消息尚未取得原版黄金向量。

| 向量 ID | 测试名 | 输入 | 预期输出 | 来源/等级 |
|---|---|---|---|---|
| RC-BIN-001 | reliable 0x02 golden | seq 0x11223344; payload 10 20 30 | 02 44 33 22 11 03 00 10 20 30 | E3 RVA 0x8612E/0x8616B/0x8617D/0x86189/0x8619F; VERIFIED |
| RC-TEXT-001 | reliable 0x01 golden | seq 0x01020304; text abc | 01 04 03 02 01 61 62 63 00 | E3 RVA 0x861D0/0x861E2/0x861EE; VERIFIED |
| RC-BIN-EMPTY | empty payload | seq 0; payload empty | 02 00 00 00 00 00 00 | E3 field rule; constructed |
| RC-BIN-MAX | max payload | payload length 0x3FC | 7-byte header + 0x3FC bytes | E3 capacity constraint; boundary test |
| CF-001 | configstring frame | count 0x1234; body 01 02 03 | 04 34 12 01 02 03 06 | E1 RVA 0xA07F8/0xA0807/0xA0997; header/trailer VERIFIED, body synthetic |
| GS-001 | gamestate confirmed fields | version 0x01020304; map mp_cross_fire; field4 0x11223344; CF-001; fieldC 0x55667788; field8 0x99AABBCC | 03 04 03 02 01 6d705f63726f73735f66697265 00 6d70 00 44 33 22 11 04 34 12 01 02 03 06 88 77 66 55 cc bb aa 99 06 | E1 RVA 0xA224C..0xA22F8; field order VERIFIED, state semantics BLOCKED |
| SN-TOKEN-001 | snapshot inner token | none | 06 | E2 RVA 0xA4CAF; VERIFIED write |
| SN-OUTER-001 | outer end selector | active=false/true | 05/06 | E2 RVA 0x87104; VERIFIED selector |

## 向量来源规则

- VERIFIED: 字段/值直接来自 E1-E3 指令。
- CONSTRUCTED: 由已确认字段规则构造的结构向量。
- BLOCKED: 未给出默认编码，测试只验证未决语义没有被自动选择。

## 没有声明的向量

- 没有把 C#/Python 自己生成的完整首帧快照称为原版 2697 黄金向量。
- 没有把旧版 1.1.1.13 或 3.3.3.3 的消息当成 2697 黄金向量。
- 没有为客户端 0x02 -> 0xA2E50 分派伪造输入输出。
