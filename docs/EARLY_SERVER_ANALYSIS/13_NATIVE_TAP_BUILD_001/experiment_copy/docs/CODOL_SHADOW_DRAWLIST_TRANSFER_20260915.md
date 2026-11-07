# C1 sun draw-list transfer audit

**Capture correction:** initial active capture reported key usage1 without
rejecting null frontend. That value was executable image memory at absolute
41940, not allocation usage. Discard it. Source lists8/31 in that capture were
retained globals and alone did not prove a current frame. Corrected capture below
requires the exact valid allocation and before/after identity coherence.

Status: exact offline C1 producer traced; passive instrumentation added. No native
change or claim of an observed rendering failure. No hooks, engine calls, input,
settings changes, builds or automated tests.

Earlier pose/brush/model captures prove eligibility inputs, not successful backend
transfer. The next distinct choke point is actual depth-pass draw-key transfer.

C1 ABCFB0, called at A84314, prepares two sun lists. It loads the technique index
from CF3F40, iterates with EDI=10h then14h, and supplies:

- source counts FAA928+EDI: FAA938 and FAA93C;
- source pointers FAA950+EDI: FAA960 and FAA964;
- destination descriptor at view+5FC, then +690 (94h stride).

ABCFEC calls ABD490, a direct jump to ABD420. This routine reads the *shared*
frontend key count at [CF4380]+41940, adds the requested count and compares with
4000h (16384). If exceeded, ABD43C emits warning ID15h through A97420 and returns
before writing destination pointer/count. Otherwise destination+40 receives
frontend+D3B00+oldCount*8, destination+44 receives the requested count, exactly
count*8 bytes are copied via61E640 and frontend+41940 advances.

This is a concrete capacity-dependent submission failure branch. It is separate
from ordinary caster bounds and would depend on scene workload. There is no
evidence that this branch fired in the user's frame; its existence alone does not
justify enlarging buffers, changing native model composition, or suppressing a
warning. Receiver shader sampling remains independently unresolved.

The guarded pose probe now captures active-only shared key usage/capacity, both
sun source list counts, pointer/key stability, key hashes and a bounded key prefix.
Additional exact-image guards validate ABCFB0 and ABD420 before these reads.
This provides a direct next check for absent/corrupt/oversubscribed submission,
instead of merely observing that an entity was sun-visible.

Capture `obj/killhouse-shadow-drawlists-100756.json` occurred during the parent's
native restart: verified C1 PID100756, commandTime0. Lists intentionally not read.
No stale allocation count or GPU result inferred. Active capture plus destination
descriptor timing would be needed to prove a transfer failure; source lists alone
do not establish successful rendering or the contents of the shadow texture.

## Corrected coherent active capture

C1 A7E695 masks the buffer index with1; A7E6C8 multiplies it by12BA80h and
A7E6CE adds CF4400. Therefore valid frontend allocations are CF4400 and E1FE80.
The probe now requires one of those exact addresses, verifies readable allocation
endpoints, and rejects null or unexpected pointers. It also captures the first
view descriptor pointer from frontend+419C8, derived from A83AEF/A83AF5 (view
strideFD0). This is explicitly view0, not an assumed active view index.

`obj/killhouse-shadow-drawlists-coherent-100756.json`: command472585, exact
Killhouse world, frontendE1FE80 stable before/after, view pointer stable. Shared
allocation usage128/16384. Near sun list8 keys, far31. Their destination pointers
EF3980/EF39C0 fall inside that frontend's key arena, destination counts match,
and full SHA256 hashes equal the respective source key hashes. Source/destination
bytes and metadata remained stable during the bounded read.

This establishes successful transfer of these two sun lists into view0 in the
captured allocation. No overflow, absent transfer, or corruption in this sample.
It does not inspect the resulting GPU depth textures, prove active view identity,
or establish that the user's shadow artifact was visible at that instant.
Receiver material/shader sampling remains unresolved; no native fix justified.
