# Shadow artifact: primary-light state and surface flags

Status: no incorrect producer identified. Bounded offline C1/native review; no process writes, UI changes, tests, builds or gameplay edits.

## Verified C1 light consumer

C1 entity dispatch at0x443c70 routes type10 to0x4427f0 through0x443d19. This is the dynamic primary-light consumer, separate from brush submission and fog/vision:

-0x442807 reads centity+0x17c (entityState+0x98) as the BSP light index. It selects the client light record at `cg+0xb05fc+index*64` and the common-world reference light at `[0x250bda0]+index*68`.
-0x442820..0x442934 converts previous/current RGB bytes to floats, multiplies each by its corresponding intensity and interpolates the resulting RGB into client-light+4/+8/+0xc. Previous/current fields are centity+0xc0/+0x13c for color and+0xc4/+0x140 for intensity, matching entityState+0x58/+0x5c.
-0x442a38..0x442a86 interpolates radius and cone cosines into client-light+0x28/+0x2c/+0x30. Previous/current pairs+0xc8/+0x144,+0xcc/+0x148,+0xd0/+0x14c match entityState+0x60/+0x64/+0x68.
-0x442a89..0x442ab0 interpolates the fourth color byte into client-light+0x34. The consumer reads this byte as an unsigned value.
-Direction/origin updates at0x442947..0x442a35 use entity trajectories, with movement/rotation constraints from the indexed common-world light. The selector is a BSP light index, not a model configstring or arbitrary scene light-set identifier.

Current native `CODOL_OverlayEngineEntityVisible` writes the same index, packed color bytes, intensity, radius and cone cosines to these C1 offsets. `CODOL_EngineEntityCanPublish` admits ET_PRIMARY_LIGHT without a model-bank lookup. No offset, selector-domain or color/intensity producer mismatch was established. The earlier Killhouse entity capture contained zero ET_PRIMARY_LIGHT entities; that observation is historical and does not prove all later frames lack them.

## nocastshadow is not an entity-state flag

C1's `nocastshadow` string at0xc6ff10 is referenced by the surface-parameter table at0xccfa54. The row's surface flag is0x40000, matching `SURF_NOCASTSHADOW` in `src/game/surfaceflags.h` and its surface-parameter row. This does not establish entityState.eFlags0x40000 as a shadow-disable bit. Copying that constant into networked entity flags would conflate separate domains.

Map surface material flags and the common-world light data are client asset inputs. No server publication that replaces those surface flags or a light-set selector was identified in this bounded audit. Native light script setters can update the verified light entity fields above; they are not evidence of modifying the world's shadow-caster material classification.

## Limits

This audit did not capture dynamic light records during an exact artifact frame or decode downstream sun-shadow projection matrices. It supplies no evidence for a speculative shadow flag or bias change. The verified brush submission and this verified primary-light field contract leave the reported dark region's cause unresolved.
