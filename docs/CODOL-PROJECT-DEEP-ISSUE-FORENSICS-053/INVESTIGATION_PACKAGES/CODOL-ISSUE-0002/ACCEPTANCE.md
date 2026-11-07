# 验收标准

1. 任一 run 的 lobby_server.py 可由 受保护基线+补丁 确定性重建（哈希一致）。

# 回归

launcher 增加'kit 必须等于 基线+patch'的断言。
