# 01_EXECUTIVE_SUMMARY — 客户端游戏业务消息入口

**目标模块:** CODOL 最终版客户端(恢复镜像 `image_best.bin` 为主)。
**性质:** 只读静态分析。未启动游戏,无动态调试/注入/hook/内存转储。

---

## 1. 核心结论

1. **游戏网络消息读取器已定位(CONFIRMED_DIRECT)。** 恢复镜像 `.text` 内存在一族函数,其诊断串为
   `; net-buffer NOT enough: real_len<%d> sizeinfo_size<%u> net_start<%p> net_end<%p>`(RVA `0x99EE98`)、
   `; string/wstring length error … net_start<%p> net_end<%p> custom_size<%u>`(`0x99EEF0/0x99EF50`)、
   `; wstring from net-buffer format error …`(`0x99F428`)。引用这些串的代码:
   - `0x87A890`(sizeinfo 帮助:按 `unit_size` 计算 sizeinfo 宽度 2/3/4/5,与外部 `[ebp+0x14]` 剩余长度比较),
   - `0x87C110`(解码器入口:`mov eax,0x17F4` 栈帧、参数 5 个、`[ebx + 8]` 类型/元素调度),
   - `0x87D5A0`(另一解码器入口:`0x180C` 栈帧、双缓冲参数校验)。
2. **net-buffer 语义由串与指令双重确认:** `net_start/net_end/real_len/sizeinfo_size` 均为内存指针/长度,
   被 `cmp/jbe/ja` 直接比较与推进 → 这是**网络消息缓冲的部分解析**(不是字符串/本地化/font)。
3. **游戏业务分派器:存在,但在本任务证据中仅确认平台 QoS 层。** RVA `0x85E6F0` 读取 `word [esp+6]`
   (消息类型)并按 `4`/`6` 分派到 `0x85E4F0`/`0x85E5C0`。该对象构造(`0x85D2E0`)使用字段名
   `QOSCSPkgHead/QOSCSPkgBody/QOSSSPkg…` 及 `udp://%s:%d`、`tqos_*` → **TQOS(QoS)平台层**,**非**游戏业务 netchan。
4. **真正的接收点(recv/WSARecv)本轮无法在镜像内取证:** 相关地址(`0x76xxxxxx` 等)属于镜像
   `.tp3 #3+#4+#5`(`VA 0x0E5C9000` 等),恢复镜像**未提供这些节区** → **BLOCKED**。
5. **未据服务器实现外推:** 本任务不使用 2697/legacy/CoD4x/IW4x 结构补客户端语义。

---

## 2. 关键 RVA 一览

| RVA | 角色 | 等级 |
|---|---|---|
| `0x87A890` | net-buffer sizeinfo 帮助 | CONFIRMED_DIRECT |
| `0x87C110` | netfield/元素解码器入口(#1) | CONFIRMED_DIRECT |
| `0x87D5A0` | netfield/元素解码器入口(#2) | CONFIRMED_DIRECT |
| `0x99EE98/0x99EEF0/0x99EF50/0x99EFB8/0x99F290/0x99F428` | net-buffer 诊断串 | CONFIRMED_DIRECT |
| `0x85E6F0` | 消息类型分派器(word[esp+6]→4/6) | CONFIRMED_DIRECT(TQOS 平台层) |
| `0x85E4F0/0x85E5C0` | 分派处理函数 | CONFIRMED_DIRECT |
| `0x85D2E0..0x85ED80` | TQOS QOSCSPkg/QOSSSPkg 对象族 | CONFIRMED_CROSSREF |
| `0x73180` | `gamestateupdate`/`EXE_*CONFIGSTRINGMISMATCH` 处理调用点 | CONFIRMED_CROSSREF |
| `0x1C05F0..0x1C2700` | OOB 连接命令族(`getchallenge`/`connect`/`connectResponse`/`challengeResponse`) | CONFIRMED_DIRECT(连接期,非 netchan) |

---

## 3. 限制

1. 恢复镜像 `image_best.bin` 覆盖 `.text`(`0x1000..0x8a8000`)与部分 `.rdata/.data`(`0x8a8000..0xa65000`);
   `.tp3 #3+#4+#5`(`VA 0x0E5C9000` 等,运行期地址 `0x76xxxxxx`)缺失 → recv/socket 证据 **BLOCKED**。
2. 磁盘 EXE 的 `.tp3` 为加壳/加密(低熵均匀 7.1,线性反汇编不含该处理函数),不能替代恢复镜像。
3. 主 DLL `.tvm0`(31MB)/`.tls`(15.5MB)未解码 → 不生成 x86 调用图。
4. 不据函数名/相邻字符串推断协议语义;net-buffer 结论以**指令 + 数据串**双重支撑。

---

## 4. 下一步(唯一最高价值)

> **补取覆盖 `.tp3 #3/#4/#5`(VA `0x0E5C9000`+)的客户端运行期内存镜像,定位对 `0x87C110/0x87D5A0`
   的调用者与 socket/recv→netchan 缓冲→该解码器的数据流。**

该步解除 `U-042-01`(接收点未闭环)。若无法补取,则退一步:在 `.text` 内做全量 `net_*/recv` 候选与
`0x87C110` 调用者(仅 `0x85D49D`,属 TQOS)之外的第二族调用者扫描。

---

## 5. 明确声明

未执行真实客户端 E2E;未启动游戏。**未宣布**与 OLD/2697/OL-mod/CoD4x/IW4x 任一协议相同。
