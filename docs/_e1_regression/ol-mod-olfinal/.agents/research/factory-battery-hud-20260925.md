> September25 acceptance: combined Factory and same-build two-client Nuketown
> FFA playtests passed on DLL5C1232D09C67EA580246485BE6D487D769FB637871CD29A515A72DD166855E1F.
> Seven canonical suites, Release,50ms and source audit passed. Earlier pending
> and failed-attempt statements below describe development history, not current acceptance.
> 同构建Factory与双客户端FFA实测通过；下文待测及失败记录保留为历史。

# Factory battery HUD units / Factory电池显示单位

Status: combined perk/ammo/HUD candidate; exact-build Factory and FFA pending.
This restores a native display conversion. It does not add a purchase surcharge.

## Native evidence

Exact distributed out.exe SHA256:
044c396c90a7cfa63eac32bea194bf4dfa4d1eab547d9082ae8a575eb49257f9.
IDA9.3 instance eeah, settled35783 functions. HUD466450 reads raw battery from
playerstate+164, then uses a whole/remainder divisor at4665EC and466610.
The retained path46659E..4665E5 looks up battery_multiplier through cdecl76F190,
reads type at+8 and current float/string at+12, multiplies by double1000.0
(DE7B98), then truncates to integer. The distributed EB4B at46659C skips this
path, leaving default1000. Live bytes confirm that bypass is active.

All three original Factory recordings explicitly set battery_multiplier1.2 and
round_goal8. Sumpf and Prototype set1 with the same goal8. Factory completed
ammo transactions at585000,716200,880900 in C-2021-8-30[20-21-43]zm deduct1200raw;
Sumpf339750 deducts1000raw. See factory-ammo-rate-20260924.md. Thus one displayed
Factory battery is1200raw, not1000. Live Chinese door/ammo prompts advertise
##1 with no extra20percent charge. Hidden difficulty ownership remains unknown;
no12-round surcharge is established. A reported video observation is consistent
but was not independently viewed and is not the basis of the patch.

## Implementation and boundary

ClientProcessPatches redirects only verified bytes8BC799F77C240C at4665E9,
requiring the known EB4B bypass and existing exact PE checks. A guarded divisor
lookup preserves the native whole count, remainder, fractional bar and text.
The trampoline saves registers, flags and x87/SSE state, writes original ESP+12,
executes the replaced divide and resumes4665F0. No server raw balance, price,
reward, netfield, gameplay timer or multiplayer path is changed.

The missing-dvar native path would produce a zero divisor; do not simply remove
the bypass. Missing, null-string, nonfinite, nonpositive, below-one-unit or
unrepresentable divisors retain1000. This guard is project compatibility policy.
Dvars are looked up on the HUD draw thread each time so a map change cannot use
a cached pointer. Only clients install the patch; unfamiliar code is refused.

For Factory:4080raw renders3 batteries+40%; spending1200 leaves2880raw and
2 batteries+40%. The existing Numpad+ grant1200 now displays exactly1 battery.
Earlier descriptions of1200 as one battery on the bypassed HUD were incorrect.

## Validation

Canonical source checks cover recorded1/1.2 settings, fraction preservation,
zero/negative/NaN/infinity/overflow fallback, unknown bytes and foreign detour
rejection, rel32 destination and idempotence. Runtime hook/visual testing must
still confirm the complete native HUD path; pure arithmetic is not a playtest.
Final Factory should check one-battery door/ammo charges, Numpad+ exact1,
held refill magazines/reserve and power/perk behavior. Repeat exact-build FFA
before publication. Launch tooling and native binaries/IDBs remain local.

## 中文摘要

IDA确认原生显示单位为1000×battery_multiplier；Factory录像为1.2，因此1200原始
单位等于1电池。分发客户端跳过该换算，造成购买显示多扣20%。本次只修复显示换算，
不调整价格或收益。保留缺失/无效参数回退，避免除零；同构建Factory与FFA仍待实测。
