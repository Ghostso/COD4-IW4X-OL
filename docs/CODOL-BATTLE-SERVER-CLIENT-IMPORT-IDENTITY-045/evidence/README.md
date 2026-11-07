# evidence/ — 原始证据索引

本目录为**原始脚本输出**(只读分析产物)。所有地址一律显式标注 RVA 或 VA;
**本任务的核心勘误是 VA/RVA 换算**(见 `../01_SAMPLE_IDENTITY_AND_ADDRESS_MAPPING.md` §3–§4)。

| 证据文件 | 生成脚本 | 内容 |
|---|---|---|
| `a01_identity.txt` | `(consolidated)` | 镜像长度/SHA-256 + 槽 VA→RVA 在文件内 + 与旧任务误判对照 |
| `b02_strings.txt` | `b02_strings2.py` | 镜像 ASCII 串上下文(`ReadFileEx`/`WIN_FILE_READ_ERROR`/`net-buffer`) |
| `b11_slotresolve.txt` | `b11_slotresolve.py` | 磁盘 EXE 序号表槽 → ws2_32 API 名 |
| `c02_iat_link.txt` | `c02_iat_link.py` | 磁盘序号表 vs 运行期绑定槽逐槽对照 |
| `c04_resolve.txt` | `c04_resolve.py` | 序号 → ws2_32 名称 + 导出 RVA + 运行期值 |
| `c05_base.txt` | `c05_base.py` | 运行期值与 ws2_32 导出 RVA 的隐含基址一致性 |
| `d03_ordslots.txt` | `d03_refs.py` | 三段序号表(6/23/11 项)完整解码 |
| `h01_exports.txt` | `h01_exports.py` | EXE 导出表(22 项,Scaleform)+ 原始 rel32 扫描 |
| `k01_modid.txt` | `k01_modid.py` | 块 A/B 运行期指针相对各 Winsock 提供方的基址评分 |
| `m01_callers.txt` | `m01_callers_corrected.py` | VA-空间校正后的 E8/E9 调用者扫描 |
| `n01_callers_ctx.txt` | `n01_callers_ctx.py` | 调用者 `0x85D96E` / `0x85E71A` 上下文反汇编 |
| `p01_fragment_constants.txt` | `(one-shot)` | 节区 #1 中 `1154/1162/0x1fffffff` 立即数出现位置 |
| `p02_fragment_context.txt` | `(one-shot)` | 上述立即数的上下文(证其为无关函数,未绑定 netchan) |
| `q01_receive_to_decode.txt` | `q01_receive_path.py` | 接收→解码边闭合证据(select/recv → 0x87D5A0) |
| `s01_blockA_owner.txt` | `(one-shot)` | 块 A 指针宿主模块探询(结论:`UNKNOWN`,不影响序号判定) |
| `t01_select_recv_proof.txt` | `(one-shot)` | `select`/`recv` 参数压栈与 `/1000` 魔数、WSA 错误码说明 |
| `z01_identity_and_pe.txt` | `z01_final_identity.py` | 三份样本完整 SHA-256 + PE 结构 + `0x87BE00` 完整反汇编(含 API 标注) |

## scripts/ 中保留的只读脚本

`b02_strings2.py` · `b11_slotresolve.py` · `c02_iat_link.py` · `c04_resolve.py` · `c05_base.py` · `d03_refs.py` · `h01_exports.py` · `k01_modid.py` · `m01_callers_corrected.py` · `n01_callers_ctx.py` · `q01_receive_path.py` · `verify_045.py` · `z01_final_identity.py`

> 早期用**错误地址空间**(把裸 VA 当 RVA)反汇编 netchan 的探索性输出与脚本已删除,
> 原因见 `../06_CAUSAL_DIFFERENCE_ANALYSIS.md` §4。
