# Factory native hit skeletons and death effects

Historical investigation below; final private acceptance is recorded in
factory-bo1-damage-profile-20260921.md. No current FFA PASS is claimed.

# Factory multipart deaths and blue effects

Status: live AK candidate FAILED head removal and blue FX; not accepted or
published. Based on cc2db75. Earlier release, seven suites, 50ms scheduler and
shipping agent-reader replay passed but did not exercise native hit production
or the resident bone-name resolver. Source correction is not deployed. Exact
candidate Factory and two-client FFA verification remain required.


The running AK build resolved neck FX197 and torso FX225 and all15 outfit
model sets, but every neck/torso bone resolved to sentinel255. The new resolver
incorrectly used the weapon attachment-name table for XModel script-string IDs.
Read-only server/client inspection found the resident bones in all three model
families: base-model bone20 is j_neck; bone5 is j_spinelower. On the server,
script ID2584 names j_neck while the attachment table returns a weapon optic.
CODOL IDA0x485300 retains XModel script IDs in the pool at0x789C524;
0x4EAAD0 resolves their text as pool+20*id+4. The corrected source uses that
pool and leaves the weapon attachment resolver unchanged.

A second independent blocker is hit classification. Twelve non-pausing samples
found no server DObj entries for zombie slots1114..1199, while player0 had a
valid entry. Initial live bullet trace records all reported partGroup0. The
actor fallback in traceServerLocationalEntities uses a capsule when no DObj
exists; sv_bullet_mp forwards that group into entity damage. This cannot select
the head/neck or torso branches. The later non-client capsule overlay can also
replace a finer hit with an earlier capsule intersection. Correcting lookup
alone is therefore insufficient. Restore a verified animated multipart actor
hit-test path and retain its partGroup/partName through aggregation. Do not
label arbitrary height bands or unposed model traces as native headshots.

The existing seven-clip weighted death cycle is independent of hitLocation;
a Tesla clip does not demonstrate that either special-damage branch ran.
The live game was not paused, injected, patched or restarted for these reads.
The synthetic fixtures supplied head/torso groups and valid bones; they proved
the downstream state lifecycle, not the missing natural producer.

The follow-up AL diagnostic uses the corrected script-string lookup and logs
the first64 lethal Factory bullet hits per presentation setup: entity generation,
hit group/bone, weapon, model and resolved effect bones. It changes no hit groups
and forces no presentation. This diagnostic is intentionally not presented as
a complete death-FX fix; it can verify resolution and the missing natural producer
in the same run. The exact AL gameplay and FFA results are not inherited from AK.




The follow-up Factory test confirms the split diagnosis: all15 outfits resolve
neck20/torso5, but all17 captured lethal ordinary-rifle hits report hitGroup0 and
hitBone0 (weapon1159, MOD2). No ZMFX play events occur. The visual result remains
FAIL for head removal and blue effects. This is now direct damage-payload
evidence, not an inference from a short generic trace sample. Bone lookup is
fixed; the natural actor hit-location producer is not. No further repetition of
this diagnostic is needed and no complete-fix/FFA acceptance is recorded.

Fresh exact-build IDA confirms that CG_UpdateAgentDObj0x52FBE0 is dispatched
for entity types19/21 by0x527A70 and creates a multipart client DObj with its
animation tree; CG_CopyAgentModelInfo0x530C90 supplies the model names. These
client routines depend on client entity/agent state and cannot simply be called
as a server hitbox initializer. Reuse verified shared model/skeleton primitives
under a server-owned lifecycle, with animated pose, hit-group propagation and
bounded work; do not redirect or overwrite the client globals.



Exact CODOL out.exe SHA256
044c396c90a7cfa63eac32bea194bf4dfa4d1eab547d9082ae8a575eb49257f9 was reviewed
with IDA. Three original player recordings provide 27,555 reconstructed snapshots.
The common_gametype_zm.ff hash is
7f49272825482e466f2782910aa2ee97e4b777ad36a528d7d7be5ae30c06b7c0.
No native binaries, databases or recordings are distributed here.

| Native presentation | Asset | Base-model bone |
| --- | --- | --- |
| Removed head, blue neck spray | `misc/fx_zombie_bloodspurt_codo` | `j_neck` |
| Broken torso, blue spray/debris | `weapon/bullet/fx_flesh_gib_fatal_01_blue` | `j_spinelower` |
| Electrical loop/crawl death (deferred) | `maps/zombie/fx_zombie_tesla_shock` | `j_spineupper` |

Original entity706 at40150ms in the July31 recording changes to garbageman
torso_1 + head + lowclean and emits the torso effect on bone5. At40650ms its
attachments become lowclean + behead; at40950ms it emits blue spray on bone20.
Other observed neck sprays use the complete body plus behead, without torso loss.
The current name table and all136 zombie FX names match the packed asset list.
Recording indices197/225/180 are evidence identifiers, never implementation IDs.
The similarly named Tesla neck-spurt asset contains ordinary blood materials;
it is not substituted for the demonstrated blue spray.

CODOL0x452970 decodes event113 as effect9bits/bone8bits/flag1bit and validates
effect1..399.0x5319B0/0x4DB5E0 attach it;0x4E0290 validates entity/DObj/bone.
0x452D60 stops the specific effect, with bone255 meaning any bone on that entity.
No global FX clearing is used. Original samples use flag0.

CG_CopyAgentModelInfo0x530C90 copies agent+0x34 to record+564;
CG_UpdateAgentDObj0x52FBE0 consumes its bits as attachment collision flags.
It is NOT a model count or a perk field. Native descriptor12 at0xDA6478 is
offset0x34,32bits. The packet extension retains default3 for unchanged actors
and emits the recorded mask1 for head/behead and head/lowclean arrangements.
Empty attachment tags preserve shared skeleton assembly. BO1 DObjCreateDuplicateParts
0x7E4210 and Ghosts0x140247490 corroborate that contract; they do not establish
CODOL dismemberment predicates or effect IDs. See the accepted head-attachment review.


`OLMOD_FACTORY_PRESENTATION=1` plus `OLMOD_FACTORY_DEATH_FX=1`, Factory only.
Names and named bone positions resolve once at map load. Missing components
preserve accepted presentation. Lethal ordinary bullet head/helmet/neck hits
select body+behead; lethal torso hits select torso_1+head+lowclean. These hit
rules are explicitly reconstructed, not recovered retail chance/thresholds.
The previously accepted seven-clip death selection is unchanged.

Each generation publishes its multipart model first, then one bone-attached
effect on a later tick. A1000ms producer stop bounds emission before corpse
transfer; this is candidate cleanup policy, not an original server timer claim.
The original sampled blue effects have no matched explicit stop within20seconds;
native asset lifetime and particle tail are independent. Review visual timing.
No effect table scan/allocation loop is added to actor ticks.

The Factory actor writer consumes actorField00B4, while the pre-existing campaign
event helper advanced eventSequence. The Factory branch now advances its actual
wire counter and preserves it for corpse handoff. Campaign behavior is unchanged.
The source tests cover source damage, model-before-event ordering, exactly one
play/stop, nonblocking death, corpse conversion and inactive/unsupported fallbacks.
The shipping x86 agent reader independently decoded whole -> broken torso ->
beheaded torso -> whole -> mask-only packets, preserving owner/model/attachments.
That is protocol evidence, not native rendering or gameplay acceptance.


AL's natural shooting diagnostic recorded17 lethal rifle hits, all group0/bone0,
despite resolved neck20/torso5 and resident effects. This was not an FX rendering
test PASS: dedicated actors had no server DObj and used capsule-only damage.

The next candidate adds a Factory/death-FX-scoped native DObj owner. The existing
BG_LoadAnimTrees (40B130 -> 785A70) registers the native CCS trees; family3 is
selected in BG_FindAnimTrees (40B210) and resolves generic_human. Body/head
descriptors match 52FBE0: empty shared-bone attachment tag and ignored head
attachment collision. The base model supplies native classified hit volumes.
Type8/flags0 calls 7891D0 with0.2s blend; 788200 advances the native tree clock.
Alias lookup follows785870. Existing7831C0/7847A0/7825F0 calculate the requested
bone pose and trace it. The coarse actor capsule overlay now defers to an admitted
skeletal trace, including misses between posed limbs. Player/FFA paths are unchanged.

Native tree headers have bounded stable ownership; generation0 is valid, not an
absence sentinel. Death/unlink, generation/model change and level cleanup release
native animation nodes and owned DObjs. Only bullet broadphase candidates have
their bone matrices calculated. No per-frame asset lookup or full-wave skeleton
posing is introduced. The source owner is reconstructed, not original server AI.

Private replay executed the exact image's type8,0.2s blend, animation clock,
DObj creation, skeleton calculation, trace and cleanup against a captured walking
cyborg. It produced head2/neck3, torso4/5 and limb groups; an offset ray missed.
Native animation children and server map returned to0 and free slots to1898.
This covers one captured family/clip and native ABI/math; it does not establish
natural server shots, other outfits, map startup, rendering or performance.
Earlier replay attempts stopped on uncaptured pages; a later complete capture
was used without substituting fabricated heap data or reading a live process.

Local raw IDA and replay evidence: animation-research-20260920/actor-hitbox-ida
and actor-hit-native-replay.log, outside Git. Seven source suites passed including
generation-zero pose identity and disabled-feature isolation. Factory visuals and
same-DLL two-client FFA remain required; no acceptance or publication is implied.



AM failed in two live Factory runs with the same execute access violation
(target `0x00200246`). A read-only sample from the second run found 791 queued
client animation notifications. Exact-build IDA `0x7869E0` and `0x786860` show
notifyType2 appending to `0x81AA7B0` without a capacity guard; client-side
consumers own draining/resetting this queue. Collision-only server DObjs must
not generate those client notifications. Their goal calls now use notifyType0
while retaining native pose blending and clock advancement. Serialized client
animation and FX events are unchanged.

A private native-code replay advances the corrected pose for 60 additional
seconds: queue count remains 0, real head/neck/torso traces still classify,
off-model rays miss, and cleanup returns pool resources. Live corrected-build
stability and visual FX remain separate verification gates. The queue defect
is confirmed; the exact invalid-jump corruption chain is not yet proven.



Electrical samples pair loops with several different down clips: e.g. a_loop
to e_down, d_loop to b_down, and e_loop to a_down. Matching suffix letters is
not a recovered rule. Do not attach electricity to every random Tesla base clip.
Nonlethal damage stages, limb loss, special weapon predicates, original weighted
selection, effect tail timing, eye-color coupling and ragdoll transitions remain
unresolved. This change does not claim full native special-death parity.
