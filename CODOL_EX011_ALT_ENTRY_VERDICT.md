# EX-011-P0 Alternate Entry Verdict

Experiment: EX-011-P0 (static entry audit + one short CDB entry breakpoint)

New dynamic node:
```text
EXE Entry RVA 0xE5DC690 EXECUTED
  call dword ptr [0xE9DC665]
  -> Base+0x1D6582C (Base export ordinal 1)
  -> crash at Base+0x306A inside that call
```

Static findings:
- EXE entry is a VM thunk that immediately calls Base export ordinal 1.
- Base entry and all three Base exports are VM thunks into `.tvm0`.
- Static CFG from PE exports/entry reaches only Scaleform exports and the entry thunk; no plain Game/Engine Init function is statically reachable.
- Game/Engine strings exist in EXE/Base data (`Renderer`, `RenderPipelineManagement`, `TextureManager`, `Initializing...`, `main\%s`, network ports), but their code is inside VM-protected sections.

Verdict:
```text
最后可执行节点：Base+0x306A（EXE Entry -> Base ordinal_1 内部）
候选 Game/Engine Init：字符串存在，但函数入口均在 VM 保护区内，无干净候选
是否存在可达入口：除 EXE Entry -> Base ordinal_1 外，未发现替代入口
是否需要 TenProxy：无法证明；Base ordinal_1 崩溃前未返回
是否依赖 TCLS：无法证明；Base ordinal_1 崩溃前未进入 TCLS 阶段
是否存在替代 Bootstrap：未发现；EXE Entry -> Base ordinal_1 是唯一观察到的主链
```

Evidence level:
L3/L4 partial: executed EXE Entry and confirmed the direct call into Base export ordinal 1.
