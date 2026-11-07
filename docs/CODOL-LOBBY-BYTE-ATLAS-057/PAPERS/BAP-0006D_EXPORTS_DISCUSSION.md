# BAP-0006D — 讨论：导出面暴露的架构，与三处不自洽

对应正论文：`BAP-0006_EXPORTS.md`

本篇要处理三个异常。第二个迫使我**修正 BAP-0005 的一个重大措辞**。

---

## 1. 我的判断可能错在哪

### 断言 A：EXE ↔ Base.dll 是双向绑定（EXE 导入 Base，Base 用 EXE 的 Scaleform 导出）

**替代假设 H1：Base.dll 根本不使用这些导出。**

导出表的存在只说明"这些符号可被 `GetProcAddress` 找到"，
不说明有谁真的去找。

**支持证据**：`NvOptimusEnablement` 是**明确给驱动读的**，
说明这个导出表里至少混合了"给外部用"和"给系统用"两类符号。

**反证尝试**：`Base.dll` = TP3Shell（BAP-0007 将证明），
而 TP3Shell 是**保护壳**。保护壳通常**不需要** Scaleform 分配器。
⇒ 若 Base 是壳，它不太可能是这些导出的消费者。

**替代假设 H2：这些 Scaleform 导出是给"另一个真正的游戏 DLL"用的。**

若客户端除了 `Base.dll` 还加载了别的模块（延迟加载、
或 `Base.dll` 内部再 `LoadLibrary`），消费者可能是那个模块。

⇒ **H2 更合理**。断言 A 应降级为：
"导出面存在，消费者身份未定"。

### 断言 B（**对 BAP-0005 的修正**）：`Base.dll` 是壳，不是游戏逻辑

`Base.dll` 的 PDB 是 `C:\jenkins\workspace\tenprotect3_master\output\Release\TP3Shell.pdb`。

**替代假设 H3：PDB 路径可以伪造/残留，Base.dll 其实还是游戏逻辑。**

**反证**：60 MB、8 个节、`.tvm0`（1.9 MB→32 MB）、`.idata2`、
`.rsrc2`、`.tls`（15 MB）—— 这套节名组合与 TP3 保护壳一致，
与"游戏代码"的节名习惯（`.text/.rdata/.data/.rsrc`）不符。
且 `EXPORT` 只有 3 个函数、`NumberOfNames = 0`（全按序号导出）。

⇒ **H3 被反证**（E3）。`Base.dll` = TP3Shell。

**但 H3 的一个弱形式必须保留**：
PDB 是 `TP3Shell.pdb`，说明**这个 DLL 是 TP3 的"外壳模块"**，
真正被保护的代码可能在它的 `.tvm0` 段里（1.9 MB VA → 32 MB 展开）。
⇒ **Base.dll 既是壳，也可能承载被保护的代码**。
不能说"Base.dll 里没有游戏逻辑"。

### 断言 C：导出表模块名 `.exe` 与导入描述符 `.dll` 不一致是异常

**替代假设 H4：这两个名字本来就该不同。**

PE 规范里 `EXPORT.Name` 是**本模块自己的名字**，
`IMPORT.Name` 是**被依赖模块的名字**。
所以：
- 导出表说"我是 `codoMP_client_shipRetail.exe`" ← **本模块名**
- 导入表说"我依赖 `codoMP_client_shipRetailBase.dll`" ← **依赖之名**

⇒ **完全正常，不是异常！** 断言 C 是**我搞错了**。
正论文 §2.1 的"残留/改写"描述**必须删除**。

---

## 2. 每个假设的证据

| 假设 | 关键证据 | 结果 |
|---|---|---|
| H1 Base.dll 不用这些导出 | Base = TP3Shell，是保护壳 | **支持，断言 A 降级** |
| H2 消费者是另一个模块 | 导出面是 Scaleform 运行时层 | **合理，待证** |
| H3 Base.dll 非壳 | PDB = TP3Shell；节名 = TP3 全套 | **反证：它就是壳** |
| H4 两名字本就不同 | PE 规范：EXPORT.Name 是本模块名 | **成立，断言 C 撤销** |

---

## 3. 若判断成立，下游会怎样

### 3.1 架构认识的重构（**重大**）

此前项目的默认假设是：

> 大厅逻辑在 EXE 里，`Base.dll` 是"CEF/平台层"。

现在必须改成：

```
codoMP_client_shipRetail.exe   （7.8 MB 装盘 / 230 MB 解包）
  ├─ 导出: Scaleform 内存/系统/矩阵 + NvOptimusEnablement
  ├─ 静态导入: 只声明 codoMP_client_shipRetailBase.dll
  └─ 节名全是 .tp3（被 TP3 加壳）

codoMP_client_shipRetailBase.dll  （60 MB，未加壳的正常 PE）
  ├─ PDB: tenprotect3_master/output/Release/TP3Shell.pdb
  ├─ ImageBase 0x10000000，有重定位、有完整导入表
  ├─ 导入: kernel32.dll + libcef.dll
  ├─ 节: .text .rdata .data .idata2 .rsrc2 .tls .tvm0 .reloc
  └─ 即 TP3 保护壳本体
```

**这批结论改变了对"哪里找大厅逻辑"的判断**：

- 若大厅逻辑被 TP3 保护，它在 **EXE 的 `.tp3` 节**（解包后的 219 MB 节 2）
  或 **Base.dll 的 `.tvm0`**（32 MB）里。
- `.tvm0` 是**已被识别为"密钥化分支派发器"**的区段（项目记忆）。
- ⇒ **大厅逻辑的静态逆向必须面对于这两处，且都不易读。**

### 3.2 `dir[12] = 0` 的谜团解开

BAP-0005 §7 说 EXE 的 `dir[12]=0` 与记忆里"`.idata2` 是隐藏 IAT"冲突。
现在 BAP-0007 显示：**`.idata2` 是 `Base.dll` 的节名**，
且 `Base.dll` 的 `dir[12].RVA = 0x00B02000` **正是 `.idata2` 的起点**。

⇒ **记忆里"隐藏 IAT 在 `.idata2`、已升级为 dir[12] 实测"完全正确，
只是它说的是 `Base.dll`，不是 EXE。** 我此前在 EXE 上测是找错了对象。
BAP-0005D §1 H2 的处理是对的，应在 BAP-0005 正文里更明确。

### 3.3 Scaleform 导出的意义

无论消费者是谁，"EXE 导出 Scaleform 运行时"意味着：

- **UI 层（大厅界面）是 Scaleform GFx**，与项目已知的 `UiCpp*` /
  `AS_*` 类（679 个 ActionScript 类）吻合。
- 大厅界面的**渲染与脚本执行**由 EXE 内的 Scaleform 提供。
- **UI 逻辑（AS3）在 `ui_mp.ff` 里，加密**（记忆：熵 7.95–8.00）。
- ⇒ **大厅 UI 的静态逆向止于"调用契约"**，脚本本体读不到。

---

## 4. 最小可证伪实验

### E1：`Base.dll` 是否真的加载 CEF

`Base.dll` 导入 `libcef.dll`（BAP-0007 已证）。
查 `libcef.dll` 是否存在于游戏目录。

### E2：EXE 是否还有其它运行时加载的 DLL

在 EXE 镜像里搜 `LoadLibrary` / `GetProcAddress` 的字面量或
通过 IAT 的调用点。若发现大量 `LoadLibraryA/W`，则"只依赖 Base.dll"
的静态结论会被运行时行为推翻。

### E3：Scaleform 导出的消费者

在 `Base.dll` 里搜这 22 个导出名。若一个都没有 ⇒ Base 不消费，
消费者在别处（或这些导出无人使用，是链接器 `/EXPORT` 强制保留的）。

---

## 5. 本次讨论改变了什么

1. **BAP-0006 §2.1 撤销"残留/改写"的说法**：
   `EXPORT.Name` = 本模块名，与 `IMPORT.Name` 不同**完全正常**。
2. **BAP-0005 §6/§7 措辞更正**：`.idata2` 属于 `Base.dll`，
   EXE 的 `dir[12]=0` 与该记忆**不冲突且印证了记忆**。
3. **架构认识更新**（见 §3.1）：`Base.dll` = TP3Shell，60 MB。
   这推翻了"Base.dll = CEF/平台层"的旧简单描述。
4. **断言 A 降级**：EXE ↔ Base 双向绑定 → 导出面存在、消费者未定。
