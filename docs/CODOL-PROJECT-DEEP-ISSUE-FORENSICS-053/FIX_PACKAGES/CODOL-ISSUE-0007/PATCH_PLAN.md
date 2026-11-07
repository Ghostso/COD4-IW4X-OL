# 修改计划

**方案A**：方案A：preflight 校验 iips.ini 的 enable_iips，并记录该文件哈希。

**方案B**：方案B：把 iips.ini 复制进 kit 并由 launcher 覆盖写入。

## 影响

消除'换机器/重装后莫名 6 秒崩'这一类问题。
