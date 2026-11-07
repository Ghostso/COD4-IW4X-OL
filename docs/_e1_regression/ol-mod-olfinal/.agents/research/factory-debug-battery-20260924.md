> October1 CZ correction: CY apostrophe was detected, but the client checked
> ps+20C, which is zero in both live clients. Settled IDA9.3 MCP (35783 functions,
> CODOL044c396c...57f9),411360 reads health from+1A4 and maxHealth+1AC. Live cg
> +1A4=100 for slots0/1 while+20C=0. CZ uses the replicated stat; server-side
> life/mode/loopback/opt-in validation remains authoritative. A synthetic local
> message12 request on CY accepted both slots and logged330->1530 and100->1300
> raw. This proves control-route grants, NOT foreground key acceptance on CZ.
> F6 is now the default configurable key (OLMOD_ZM_DEBUG_BATTERY_KEY, hexadecimal
> Windows VK); apostrophe and Numpad+ remain aliases. Focus, physical rising edge,
> 500ms debounce, fixed amount and cap are retained. Exact CZ human test pending.
> CY按键已检测，但误读客户端恒为零的+20C；CZ改读IDA及实时验证的+1A4生命值。
> 默认F6，可配置虚拟键码；旧键保留。合成控制请求不等于真实按键验收。

> October1 CY: CX key test FAILED. The lookup incorrectly treated the native
> cg root selector as a local-player index and rejected values>=4. Live Player1
> used selector5; Player2 used3. IDA613A40 indexes the encoded root table directly.
> CY uses the existing diagnostic bound64 (not a claimed native array size),
> checked reads and separate ps+158 player-slot validation. Failed lookup now logs
> a refusal. Synthetic regressions exercise selector5/player0, selector3/player1,
> unreadable memory, oversized selectors, dead/non-playing state and invalid slots.
> Foreground apostrophe and actual two-client balance changes remain pending.
> CX误把根表选择器当玩家编号；CY修正读界限并加入拒绝日志，真实按键/余额待验收。

> September25 acceptance: combined Factory and same-build two-client Nuketown
> FFA playtests passed on DLL5C1232D09C67EA580246485BE6D487D769FB637871CD29A515A72DD166855E1F.
> Seven canonical suites, Release,50ms and source audit passed. Earlier pending
> and failed-attempt statements below describe development history, not current acceptance.
> 同构建Factory与双客户端FFA实测通过；下文待测及失败记录保留为历史。

# Local Factory battery test aid

Status: optional development tool; not reconstructed retail behavior. No native
ABI/netfields are changed. `OLMOD_ZM_DEBUG_BATTERY=1` must be explicitly set in
the client and server environments. Factory perk-machine mode must also be on.

Press **F6**, **apostrophe** (US-layout key) or **Numpad +** while the client owns the foreground window to add1 display
battery (1200 raw), capped at100 display batteries. Holding the key sends one
request; releasing/repressing permits another after500ms. Physical key state is
tracked in the background so returning focus while held cannot synthesize a press.
Alt noclip keeps its original behavior, including when the battery aid is disabled.

The existing control transport uses message12 with a decimal client slot. On a
focused key edge the client reads its decoded local cg/playerState clientNum
(613A40 cg accessor, ps+158) with checked ReadProcessMemory. Failed reads send
nothing. The server requires loopback, zm/zm_factory_sh, an Active slot on the
same loopback address, an alive Playing world player and the explicit option.
This is a local debug privilege, not an authenticated remote economy protocol.
Legacy empty requests remain exactly-one-active-client only. Malformed slots,
remote peers and FFA refuse. The world retains500ms cooldown and saturation.
Only the focused process sends; two local players no longer make the aid unusable.
Grants use authoritative currency storage under the existing server mutex and
replicate on the next snapshot. No memory patching, kills, score award or native
blue reward event is involved. The HUD and diagnostic log show the balance change.

Source assertions cover disabled option, invalid client, accepted fixed grant,
immediate repeat refusal, exact balance publication, unchanged score feedback,
saturation and FFA exclusion. Foreground/key handling and visible HUD remain
manual checks. Test-launch scripts stay local; preserve the earlier perk-only
package so this tool can be reviewed separately from the perk implementation.

## 中文摘要

仅限本地Factory测试，默认关闭。显式开启后按小键盘加号增加1电池，上限100；
按住不重复触发，客户端焦点检查和服务端500ms限频独立执行。支持明确本地玩家槽位，拒绝远程、无效槽位、
FFA、未进入游戏及无效请求；不增加分数或击杀。不宣称原版行为，不修改原生ABI。
