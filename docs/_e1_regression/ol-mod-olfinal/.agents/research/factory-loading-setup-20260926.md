# Factory loading setup boundary / Factory 加载准备边界

Status: attempt-scoped lookup reuse retained in the accepted box-only build.
Factory and same-build two-client FFA loaded and passed. The initiating cause
of the earlier CC failure remains unproven; this is not a general startup fix.

The failed CC run completed server configuration with checksum 1952022900,
matching prior working Factory runs. Map setup started at 21:13:20; the world
was not ready until 21:14:44. One snapshot was sent, but the client never reached
Playing. A later read found EXE_CONFIGSTRINGMISMATCH, client checksum 4290080126,
and frontend NCS assets, whereas the server retained Factory assets. These are
post-failure observations: they do not prove which error occurred first or that
the special reward definitions caused the mismatch. Timeout during synchronous
world preparation is a hypothesis requiring the next live trace.

Fresh IDA analysis of owned out.exe (SHA-256
044C396C90A7CFA63EAC32BEA194BF4DFA4D1EAB547D9082AE8A575EB49257F9)
is stored locally. Relevant functions: 0x473260 reads the gamestate checksum;
0x473180 validates it against native CCS, initializing through 0x661A30 only
when needed. 0x661850 folds native NCS strings into that checksum. 0x456510
clears and rebuilds CCS for mp_ui_viewer. A frontend table read after an error
therefore cannot establish what the first checksum comparison saw.

This candidate preserves that validation and the existing transport. It only
reuses identical bone/attachment/effect lookup results within a single world
preparation attempt. Results, including misses, are discarded on return; no
pointers or indexes survive into another map generation. Existing native
resolvers and all outfit compatibility checks remain responsible for results.
The completion log records preparation time and avoided lookup count.

Release, seven regression suites and 50ms server suite passed. Those tests do
not exercise native loading. Separately, the isolated CE Factory and two-client
FFA playtests loaded and passed on the same binary; exact hashes and acceptance
boundaries are recorded in factory-interactables-20260925.md. This demonstrates
successful tested sessions, not proof of every earlier startup failure cause.

已确认失败后客户端处于前端NCS而服务端处于Factory；尚未确认首发错误。
本候选仅复用单次加载准备中的重复查询，保留原生校验及所有模型兼容检查。
自动回归不代替原生加载验证；CE构建另行通过Factory及双客户端FFA实测，
但先前CC运行的首发错误仍未证实，不应声称解决所有启动问题。
