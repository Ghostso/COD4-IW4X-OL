# Accepted playtest status — September22

Factory and same-build two-client Nuketown FFA: PASS. Candidate AS DLL SHA256
C6F431C1DBF9D8AB28187B12C07A3D95B90D3329025DC749F83D31CD622D2F0B.
Seven canonical suites and50ms checks passed; both real FFA slots reached Playing.
Visual/gameplay acceptance is human testing, not automated combat verification.
Natural Wunderwaffe acquisition/chain combat remains unverified. Seven inherited
source-audit anchors require final review; no commit/publication yet.

# Factory damage stages and recorded electrical death sequences

Status: AQ wrongly coupled base animations to lightning; AR overrestricted the base animation pool. Separated-presentation candidate on cc2db75; Factory and same-build two-client FFA accepted; final contribution review pending. No commit or publication. The preserved 6a53b38 work is included here
as an uncommitted diff; unrelated power/perk work remains in its old checkout.

## Scope and evidence

Enable Factory presentation, death FX, BO1 damage and the new
`OLMOD_FACTORY_REFINED_FX=1` option. Other maps and the disabled option retain
their previous behavior. No netfield layout, player movement, power switch,
navigation, currency or drop behavior changes.

Exact CODOL executable SHA256:
044c396c90a7cfa63eac32bea194bf4dfa4d1eab547d9082ae8a575eb49257f9.
IDA reviewed 0x7825F0 (posed hit classification), 0x452970/0x452D60 (actor
FX events), and 0x786E70 (native animation clock). Existing native replay and
multipart-reader evidence in factory-death-fx-20260921.md remains applicable
to those interfaces; it is not a new live gameplay PASS.

Owned BO1 `_zombiemode_spawner::zombie_gib` routes right upper/lower arm and
hand hits to right-arm damage, left equivalents to left-arm damage, and torso
hits to its equal guts/right-arm selection. CODOL frozen posed traces distinguish
groups6/8/10 (right) and7/9/11 (left); named shoulder/elbow/wrist bones establish
the side. Original CODOL demos also contain arm-off multipart states.

The refined adapter adds matching left/right arm removal using that reference
policy and native CODOL models. Existing 10%-of-pre-hit-health eligibility,
once-per-body damage, independent head loss and bounded headless lifetime stay.
The damaged body plus original lower part and head/behead retain their attachment
contract. Missing selected assets do not silently select a different side.
Blue shoulder emission placement is reconstructed from the named shoulder;
native CODOL arm-hit removal probability and precise shoulder FX timing are unknown.

## Electrical presentation

Original July31 recording SHA256
a8c461be9b8544eb041e95b37a4054a999642b34469cc3b0dda64d55fe2d4a97
contains body-shock event113 at bone10 at loop entry. Representative sequences:

| Actor / loop command time | Loop -> down | Observed interval |
| --- | --- | ---: |
| 808 / 244050ms | A -> E | 850ms |
| 727 / 298200ms | B -> B | 600ms |
| 799 / 249250ms | D -> B | 550ms |
| 743 / 302850ms | E -> A | 350ms |

These pairs refine four Tesla weapon-death choices. C retains its base clip;
no verified C-loop pair is invented. Weighted selection within a damage class
remains reconstructed, NOT recovered CODOL selection probabilities.

Corrections to AQ and AR: AQ incorrectly promoted random Tesla base choices to
electrical loops with body lightning; AR then excluded the entire animation
family from ordinary kills. Neither follows from the available evidence.

A fresh read-only join of three original-player Factory recordings found415
Tesla base-animation commands without a recorded body-shock event within2s on
that actor. The26 loop/down commands all had a nearby body-shock event. There
were35 base-command cases with a headless model observed250ms–5s earlier and
no nearby body-shock event. For example, July31 actor763 has a headless multipart
state at193650ms and Tesla-A base at194300ms; August30 20:21 actor779 has a
headless state at390100ms and Tesla-B base at391050ms.

These are command counts and temporal associations, not unique kills, weapon
causes, health/liveness proof or probabilities. The join cannot by itself rule
out entity reuse. Missing event observations do not prove absence of every
rendered effect. A complete head-loss -> walking -> death lifecycle still needs
focused replay. Nevertheless the evidence does not support weapon-exclusive
ownership of the base animation family. Even BO1's zombie_disintegrate reuses
Tesla-named crawl deaths outside the Tesla weapon routine.

The correction keeps the existing reconstructed seven-base-clip mix for ordinary
kills, including headless follow-up kills. It does not force one animation on
every headless death or claim an original selection probability. Native blue
head/arm/torso spray and debris remain independent. Merely selecting a Tesla
base clip NEVER adds electrical FX or replaces it with a loop/down sequence.

The separate electrical path still requires a lethal transaction carrying a
configured, map-resolved Tesla weapon identity. Only that path may select the
recorded electrical loop/down pairs and emit body shock or make the BO1-derived
delayed50% electrical head-loss decision. Explicit clip-family metadata survives
missing/reordered assets. Map power is not a trigger. BO1's
_zombiemode_weap_tesla::tesla_do_damage and is_tesla_damage support this bounded
weapon path; their predicates do not prove that every similarly named CODOL
animation is exclusive to the weapon.

Factory resolves a Tesla weapon identity and contains its assets. Natural
mystery-box acquisition and the chain-lightning controller are still unverified.
No synthetic weapon test establishes those gameplay outcomes.

Down lifetime is its measured native asset duration plus the existing250ms
settling allowance. Delayed server frames give the down clip its full duration.
The completed sequence transfers to the existing nonblocking retained-corpse
pool, releasing a live zombie slot. Per-generation state prevents reused IDs
from inheriting another actor's animation or emission. Asset resolution occurs
at map setup, not on each actor tick. An incomplete pair falls back to its base
clip. Body-shock indices are admitted only when all loaded damaged body variants
agree on the named spine bone. Composed eye-shock indices remain disabled.

Blue neck/body effects retain model-before-event ordering and the previous
1000ms producer stop. That stop is bounded cleanup policy, not measured retail
timing. Native particles may leave tails after emission stops.

## Deferred rather than guessed

The packaged blue neck FX references blue gush/drop/water-plume materials;
the torso effect includes blue bursts and debris models. That does not establish
the complete particle dependency graph. Separate spark/decal spawning, global
eye/body-color changes, orange/blue number semantics, repair currency and drops
are not added here. Their original triggers still require correlation.
This is not complete native death behavior: crawling, full ragdoll handling,
all multipart combinations and retail selection odds remain incomplete.

## Validation

AQ and AR each passed source tests that enforced an incorrect presentation
assumption; neither is visual acceptance of this correction. New tests exercise
ordinary headless kills selecting a Tesla BASE with no body shock, ordinary and
unknown-to-the-electrical-list weapons remaining out of the electrical loop,
and configured electrical weapons taking the loop/down/FX path. Existing limb
side, model-before-FX, late-frame duration and retained-corpse checks remain.
Synthetic classified weapon payloads use a matching owned test loadout; they do
not validate natural Wunderwaffe combat. Exact-candidate suite/build results and
human Factory/FFA acceptance must be recorded separately.

The source-evidence audit reports seven stale-anchor errors also reproduced on
untouched cc2db75; no additional candidate audit errors remain. This is not an
audit PASS or a claim of complete source coverage.

Publication requires exact-candidate Factory and FFA acceptance, review, and
the same normal fast-forward commit published to both authorized repositories.

工厂候选：按命中侧处理手臂损伤，并按原始录像播放电击循环/倒地阶段。
概率与部分时序仍为明确标注的重建策略；尚待同构建 Factory 和双客户端 FFA 验收。
