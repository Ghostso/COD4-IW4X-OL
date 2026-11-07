# Cyborg eye lens flare and mouth glow

Status: accepted opt-in BC candidate on collision commita9c1ac6.
Factory and exact-build two-client Nuketown FFA playtests PASS. No original server controller claim.

## Native evidence

Exact out.exe SHA256044c396c90a7cfa63eac32bea194bf4dfa4d1eab547d9082ae8a575eb49257f9;
IDA35,783 functions stable.0x532910 dispatches113 play,115 stop,116 kill.
0x452970 decodes effect low9 bits and bone next8 bits; effect1..399 required.
0x452D10/5319B0/4DB5E0 create the attached effect.0x452D60/452DF0 distinguish
stop from immediate kill;4DB720 filters asset,entity,bone;255 encodes all bones.
0x4E0290 requires a valid entity/DObj and bone below its count.0x781110 appends
XModel bone arrays and0x783440 resolves composed bones. Large54B3F0 could not
decompile; bounded IDA disassembly alone was retained for its eye-tag references.

Three original recordings/27,555 exact snapshots:3,437 deduplicated eye starts,
3,428 paired with a same-snapshot mouth start. Native ordinary names are
maps/zombie/zm_eye_lensflare_{blue,yellow,orange}, plus observed special
zombie/eye_glow_red. Mouth names are zombie/mouth_glow_{color}_small.
Starts use event113, eye86/mouth97; stops115 with bone255. All three extracted
head families place j_eyeball_le at local13 and tag_mouth24, appended to73 body
bones. Current resident aliases and asset names are resolved, not hardcoded IDs.
Names cross-reference the supplied NCS order against a preserved runtime table;
original recordings carry indices. This calibration is not recovered server code.

Same-body/head eye-color transitions exist. Their triggering game state and
possible synchronized switching are not yet proven. This preview pairs ordinary
glow with the accepted body color, leaving special red/global switching deferred.
Do not describe that selection adapter as a recovered full native glow controller.

## Implementation and checks

OLMOD_FACTORY_FACE_GLOW=1 alongside the existing Factory presentation enables
the preview. Resolve effects and composed attachment bones once at map load.
Cross-check body/torso/arm variants. Missing or ambiguous pairs fail closed.
Keep Tesla shock-eye parameters independent. No DObj rebuild or asset loads in ticks.

A generation-qualified source owner queues one left-eye effect and one mouth
effect using the existing actor event ring, after100ms publication allowance.
That allowance is adapter ordering, not recovered native delay. Death/head loss
stops the two owned assets, body swaps stop then restart after publication.
Reset/free/corpse ownership clears source state. Normal death stops before
corpse transfer; abrupt removal still relies on native invalid-entity/DObj cleanup.
No repeated starts each frame and no native structure layout modifications.
Diagnostics are capped128 lines per map. Tests cover start parameters, missing
pair, persistence, death cleanup and reset. Live head-loss/body-swap/respawn,
placement across outfits and dense-wave performance remain regression targets.
Factory run685173031 and same-build FFA run685807812 playtests passed.
Both FFA clients reached Playing; individual automated combat assertions are not claimed.
Seven suites, Release, 50ms server regression, source audit and frozen-source
checks passed. DLL SHA256 D0F0E1FFC149851896FC71369EDCB649DA2B0FC80F056A8075D23C0C45BCA78D.

## 中文摘要

原始录像支持左眼镜头光斑与嘴部辉光配对；同版本IDA确认事件113播放、115停止、
资源/实体/骨骼作用域及组合骨骼索引。候选仅恢复普通蓝/黄/橙配对，特殊红色及
全局切换条件未恢复。按代际管理生命周期，地图加载时解析资源，运行时不重复加载。
Factory和同构建双客户端FFA实测通过；七组套件、Release、50ms回归及证据审计通过。
不将重建适配器称为原版服务端控制器。
