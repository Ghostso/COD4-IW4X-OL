# CODOL EXE-CORE-005 — EXE External Boundary

研究对象：`codoMP_client_shipRetail.exe`
范围：仅 EXE 自身外部边界；不进入 DLL 内部，不进入 `.tvm0`。

## Scope

- 扫描可解析 native 区域中的明确外部边界形式：`call [IAT]`、`jmp [IAT]`、`call absolute`、`jmp absolute`、可静态解析 indirect call、`LoadLibrary*`、`GetProcAddress`。
- IAT / non-IAT 分开记录。
- 仅 `EXE Entry -> Base.dll ordinal_1` 为已确认边界；`Base+0x149C`、`Base+0x1AA13B0`、`.tvm0` 仅记为 `EXTERNAL_SIDE_UNRESOLVED`。
- 动态加载 API 只记录机制/边界；不按 DLL 名称推导功能。

## 基础事实

- ImageBase: `0x400000`
- Entry RVA: `0xE5DC690`
- Entry bytes: `ff 15 65 c6 9d 0e`
- 自定义绑定地址: `0x0E9DC635`
- IAT VA: `0x0E9DC665`
- Base 导出: `Base+0x1D6582C` = `ordinal_1`
- Import directory size: `0`
- TLS callback count: `0`

## 1. Confirmed

### EXE -> Base.dll

- `0xE5DC690` -> `0x0E9DC665` -> `codoMP_client_shipRetailBase.dll` `ordinal_1`
- 证据：入口 `call dword ptr [0x0E9DC665]`；`0x0E9DC635` 为 custom binding 描述符；PE 导出表确认 `Base+0x1D6582C` 为 `ordinal_1`。
- 结论：这是当前唯一已确认的明确 Base 边界。

### 统计

- confirmed external calls：1
- confirmed Base calls：1
- confirmed dynamic loads：0
- confirmed GetProcAddress boundaries：0

## 2. Unresolved

### unresolved indirect / absolute call

- 在已扫描 native 区域中，除确认入口外，还存在若干 `call imm32` / `jmp imm32` / `call [disp32]`。
- 其中部分目标位于 EXE 图像外，但未解析到明确外部模块；其余目标仅能记为内部候选或未知。
- 统计：unresolved indirect calls = 2；unresolved absolute/jump candidates 参与总外部边界图时按 `UNKNOWN` 处理。

### 动态加载

- 未在 EXE 自身扫描范围内发现可证明的 `LoadLibrary*` / `GetProcAddress` call site。
- 结论：`DYNAMIC_MODULE_TARGET_UNKNOWN`；无 confirmed dynamic load。

### .tvm0

- `.tvm0` 边界存在，但不属于 DLL 外部依赖。
- 本轮只记录 `VM_BOUNDARY`，不继续分析。

## 3. Not Analyzed

- `Base.dll` 内部行为。
- `Base+0x149C`
- `Base+0x1AA13B0`
- `.tvm0` 入口及内部流程。
- `0x6212C0` 相关闭包。
- 任何 DLL 的内部实现。

## 问题 A

- 结果：否。
- 说明：当前静态扫描与现有证据只确认 `EXE Entry -> Base ordinal_1` 这一条明确 Base 边界；未发现其它可确认的 `EXE -> Base` 调用点。

## 问题 B

- 结果：未发现除 Base 外的其它确认 DLL 外部依赖。
- 说明：其它 `CANDIDATE`/`UNKNOWN` 目标均不足以标记为 confirmed external dependency。

## 问题 C

- 结果：存在 unresolved indirect call，但数量有限。
- 说明：当前不能将其视为大量外部依赖；它们仅说明边界图尚未闭合。

## 问题 D

- 结果：`EXTERNAL_BOUNDARY_SPARSE`
- 说明：可确认外部边界非常有限，现有证据不足以构成完整依赖图。

## 边界图

```
codoMP_client_shipRetail.exe
  -> codoMP_client_shipRetailBase.dll : ordinal_1
  -> UNKNOWN unresolved indirect/absolute
  -> .tvm0 : VM_BOUNDARY
```

## 结论

- 本轮只确认一条明确 EXE 外部边界：`EXE Entry -> Base.dll ordinal_1`。
- 其它外部边界仍待后续更完整的调用目标解析。
- 不重新追 `0x6212C0`，不分析 DLL 内部，不进入 `.tvm0`。

---
*本轮不对任何 DLL 内部行为作结论。*
