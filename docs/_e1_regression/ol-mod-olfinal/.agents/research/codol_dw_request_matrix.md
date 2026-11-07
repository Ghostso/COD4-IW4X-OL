# CODOL DW3 request matrix

> Status: 2026-07-27 capture snapshot. This is wire evidence, not the current implementation ledger or roadmap.

Generated from `diagnostics\runs\20260727_140217\events.jsonl` by `references/client_probe/AnalyzeCodolTrace.py`.

A request begins with `service_id`, protocol version, then `task_id`. The
captured CODOL flow uses protocol version `3`. Service names are
cross-checked against CODOL revival notes and reference DW3 implementations;
task names remain `unknown` where the 2015 client contract is not confirmed.

- Requests: `4`
- Unique service/task pairs: `4`
- Serialized responses captured: `4`

## Aggregate

| Service | Task | Name | Count | First | Length | Evidence strings |
|---|---:|---|---:|---:|---:|---|
| `0x0A` Storage2 | `0x14` | listAllPublisherFiles | 1 | 1 | 27 | - |
| `0x50` Marketplace | `0x82` | getBalance | 1 | 2 | 11 | - |
| `0x5D` Unknown93 | `0x01` | unknown | 1 | 3 | 11 | - |
| `0x1C` ContentUnlock2 | `0x04` | unknown | 1 | 4 | 363 | - |

## Sequence

| # | Time ms | Service/task | Length | Evidence strings |
|---:|---:|---|---:|---|
| 1 | 0 | `0x0A/0x14` Storage2::listAllPublisherFiles | 27 | - |
| 2 | 4 | `0x50/0x82` Marketplace::getBalance | 11 | - |
| 3 | 4 | `0x5D/0x01` Unknown93::unknown | 11 | - |
| 4 | 7607 | `0x1C/0x04` ContentUnlock2::unknown | 363 | - |
