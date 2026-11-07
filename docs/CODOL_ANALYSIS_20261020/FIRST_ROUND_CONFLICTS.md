# CODOL 第一轮证据冲突
| ID | 冲突 | 当前处理 |
|---|---|---|
| C-01 | 目标 EXE 的 3.19.26.22 与 3.3.3.3 标签 | 当前实例采用 3.19.26.22；旧标签保留但标为对本实例已反驳 |
| C-02 | 加壳件与缺失的去壳 out.exe | 不比较哈希，登记缺件 |
| C-03 | 旧 RVA 与目标镜像错配 | 不沿用，重新定位 |
| C-04 | 1.1.1.13 源码与 EXE 无 PDB/MAP 绑定 | 源码与二进制结论分开 |
| C-05 | 2697 原始目录不可见 | 只使用派生证据 |
| C-06 | IW4X rawfiles 误入第一轮 | 标为第二轮输入 |
| C-07 | 冻结控制面基线已有偏差 | 只读保留，不修复 |
| C-08 | REF_LOBBY_KIT duplicate memory slices | Reconcile by unique hash and lineage |
| C-09 | Target runtime image absent | Keep static and runtime evidence separate |
| C-10 | 2697 and 3.19 differ | Do not promote writer chain to target consumer chain |
| C-11 | 3.3.3.3 and 3.19 differ | Use only as historical or algorithmic reference |
| C-12 | Startup, selftest and playable match are not equivalent | Count separately |
