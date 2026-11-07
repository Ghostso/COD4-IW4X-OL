# 已证明的事实

- 成功形态：`mmstart … g_gametype coop; g_difficulty 1; ; map coop_train_mp_firingrange;2654 ; roomChatChannelID 0;`
- 失败形态（区间 D）：`mmstart … playlist 37; start_map_rotate_once 7; roomChatChannelID 1800154382;`
- 官方 playlist 表 123 项里没有 37，也没有 50。
- 服务端在 `_map` 为空时静默跳过 coop_map.txt 写入（源码行 1116）。
- findSessions 发生在 mmstart 之前，所以 coop_map 自校正只在下一轮生效。
