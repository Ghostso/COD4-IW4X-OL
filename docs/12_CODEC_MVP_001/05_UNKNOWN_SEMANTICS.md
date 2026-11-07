# 05 - 未决协议语义

## 1. 客户端 reliable 0x02 分派

- 现状: 服务端 _SV_WriteReliableCommand RVA 0x8612E 已确认写 0x02 + long + short + payload。
- 未决: 客户端是否存在 0x02 -> 0xA2E50 的直接/间接调用。
- 已有搜索: 阶段 F/G 的直接 E8、绝对 VA、裸 RVA、已解析跳转表均未命中；恢复镜像缺最后 .tp3 且有 .rimp 指针修复伪影。
- 等级: BLOCKED。
- 需要证据: 客户端 opcode 读取点、条件/跳转表、目标调用点、缓冲区同一性。

## 2. 客户端 0x06 语义

- 现状: E2 确认服务端在 0xA4CAF 写 0x06；外层 0x87104 选择 0x05/0x06。
- 未决: 客户端读取位置、游标推进、终止循环和 EOF/EOS 语义。
- 等级: NOT-OBSERVED / BLOCKED。
- 需要证据: 客户端读取该字节的指令和分支。

## 3. Gamestate 长字段

- 已确认: state[0]、state+4、state+0xC、state+8 的写入顺序和宽度。
- 未决: 字段名称、业务含义、取值范围和状态机依赖。
- 等级: BLOCKED。
- 需要证据: 客户端消费者、运行时状态、或 2697 服务端数据流追踪。

## 4. Configstring body

- 已确认: opcode 0x04、count、0x06 终止符；count 上限 0x1DD7。
- 未决: 索引 bit 布局、字符串编码、数组/配方 10/7/4/12-bit 字段边界。
- 当前 codec: 只实现 frame header/count/body/terminator，body 是不透明字节。
- 等级: BLOCKED。
- 需要证据: writer helper 的完整位级反向工程和客户端 consumer。

## 5. Snapshot 完整布局

- 已确认: A4860 的调用顺序、0xA4CAF 的 0x06、多个输出区域和 outer 0x05/0x06 选择。
- 未决: 完整网络 opcode、delta/字段边界、子段拼接、0x06 后的写入如何映射到 wire。
- 当前 codec: 只提供已确认的 0x06 token 和 outer selector；不生成完整 snapshot。
- 等级: STATIC-INFERENCE/BLOCKED。
- 需要证据: 客户端 snapshot parser 和完整消息边界。

## 6. 2697 原生注册/激活

- 已知: registration 文件由 _CODOL2697_ReadRegistration RVA 0xA3EA0 读取；门控 +0x78F4、+0x6408。
- 未决: 合法、可复现、非绕过式的完整配置路径。
- 等级: BLOCKED/NOT-OBSERVED。
- 需要证据: 隔离运行观察或完整调用链。

## 7. Codec 处理原则

- 默认 codec 只编码已确认字段。
- 未决字段不自动选择 opcode、终止符或 bit 布局。
- 实验分支若建立，必须显式命名为 EXPERIMENTAL 并使用独立测试入口。
- 不把字段形状相似升级为协议一致。
