# ICH-033 - Decision

## NIFS 格式确认

.ifs 文件 = NIFS 容器格式（"nifs" 魔数）：
- 172 字节固定 header（版本、大小、条目数、块计数）
- Null 分隔的 .ff 文件路径清单
- 多个 IWff0100 数据块（每块 = 一个 .ff fastfile）

## IFS2 角色

IFS2.dll = **虚拟文件系统 + 解包器**
- 输入: .ifs 文件路径
- 输出: 虚拟 .ff 文件内容（IWff 数据块）
- Engine 通过 IFS2 读取 .ff 内容，无需 .ff 物理文件存在

## FF 映射确认

code_pre_gfx_mp.ff 存在于 ff_init_common_gfx_V109.ifs 的 manifest 中。
所有 10 个 .ff 条目对应 10 个 IWff 数据块。

## FF 恢复路径

最优路径：**从 .ifs 提取 IWff 块 → 写为独立 .ff 文件**

方法：
1. 读取每个 .ifs 的 NIFS manifest（null 分隔的 .ff 路径）
2. 定位每个 .ff 对应的 IWff 数据块（通过 IWff 魔数搜索）
3. 提取 IWff 数据（从 IWff 魔数到下一个 IWff 或文件尾）
4. 保存为独立 .ff 文件到 Engine 搜索路径（main\）
5. Engine 即可通过正常 FastFile 加载机制读取

## 下一步

ICH-034: 从 .ifs 提取 IWff 块 → 生成 .ff 文件 → 部署到 COD OL\main\ → 重新运行 Engine → 监控 FastFile/Zone/Asset 加载。
