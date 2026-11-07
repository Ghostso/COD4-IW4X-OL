# 修复进度

- **R0：静态完整性完成。** 详见 `R0_BASELINE_INTEGRITY.md` / `R0_BASELINE_MANIFEST.json`。默认 GOLDEN 清单与实际 lobby 不一致，不能直接启动；独立 Kit 已生成匹配清单。
- **R1：PENDING_LIVE_VALIDATION。** 已实际启动四次官方客户端；两次稳定复现 B1 房间路径，零战斗 UDP。纯 PvE A 路径尚未复现。
- **候选最小补丁：** 隔离在 `PATCHES/work`，coop GameType 修复未经实机验证，不得作为已修复成果。
- **日志：** 已实现阶段事件与业务元数据；后续工作版本含真实请求 seq。完整验收仍需运行该最终版本。
- **自动测试：** `python -I -B -m unittest discover -s CODOL-LOBBY-FULL-LIFECYCLE-REPAIR-056\TESTS -v`，最后结果 4/4 通过。仅离线单元/序列化测试。
- **回滚：** `PATCHES/baseline/lobby_server.py` 保持 GOLDEN 实际原件；每轮使用独立 Kit；REF/GOLDEN/历史日志未改。
- **R2–R6：** 未开始，未验收。
