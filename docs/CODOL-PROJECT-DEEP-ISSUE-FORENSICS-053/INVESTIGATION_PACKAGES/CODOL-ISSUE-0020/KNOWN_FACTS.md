# 已证明的事实

- 战斗服 UDP 28960 监听正常，协议栈可用（10-26 有 8 轮全链路 RX）。
- 战斗服 `codol_battle_service_on_packet` 对任何包都会打日志；失败轮零日志 ⇒ 包没来。
- 34 次带 mmstart 的运行里，`map==coop_train_mp_firingrange && 不建房` 与 RX 出现 100% 共变（8/8 vs 26/26）。
- 区间 B（10-26 23:31 起）带 map 仍零 RX ⇒ '没有 map' 不是充分条件。
- 区间 B 完全没有 102/7 ⇒ '102/7 回全 0' 不是区间 B 的原因。
- 区间 B 未推 StartGame ⇒ '推 StartGame 打断' 被排除。
- 成功轮根目录是沙箱 `sandbox_ifs1_20260923`；10-27 12:00 起是本体 `COD OL`。
