#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <deque>
#include <optional>
#include <vector>

namespace CodolGameServer
{
    // CODREF(g_spawn): CODOL reserves 2046/2047 as world/none and returns only
    // slots 27..2045 to G_FreeEntity's dynamic FIFO.
    inline constexpr std::uint32_t EntityNumWorld = 2046;
    inline constexpr std::uint32_t EntityNumNone = 2047;
    inline constexpr std::uint32_t EntityReuseDelayMilliseconds = 500;
    inline constexpr std::uint32_t EntityEventLifetimeMilliseconds = 300;
    // CODOL G_FreeEntity only returns slots 37 and above to the dynamic
    // entity FIFO. Slots 19..36 are the player-corpse ring, not map-brush
    // allocation space.
    //
    // CODDIFF(1649370): THIRTY-SEVEN, not 27. The corpse ring is 18 slots on
    // this build and 8 on 3.3.3.3, and this number is the one immediately
    // above it -- see PlayerCorpseRingSize below for the measurement. The
    // arithmetic in the comment there is 3.3.3.3's own and it still holds:
    // 19 + 18 == 37, so the ring exactly fills the reserved gap between the
    // client slots and the dynamic region.
    inline constexpr std::uint32_t FirstDynamicServerEntityNum = 37;

    // CODREF(player_die): a corpse's entity number IS its slot index in
    // the client's corpseinfo array - CODOL's accessor sub_BB9EE0 does
    // `globals + 952 * entityState->number + 639904` with NO subtraction and NO
    // bounds check (IW3 subtracts 64 and asserts; the assert is compiled out of
    // a retail build). Allocating a corpse from the dynamic FIFO produced entity
    // 396, which wrote 396*952 bytes past that array and crashed the client.
    //
    // Reference shape only: BO1 Windows x86 G_SpawnPlayerClone 0x00693840 uses
    // `&level.gentities[currentPlayerClone + 32]` with `% 4`; Ghosts PS4 x64
    // G_SpawnPlayerClone 0x140168DC0 uses `+ 42` with `% 8`. They disagree, so
    // neither base nor count may be ported - together they establish only that
    // the shape is "a static counter, a fixed base, a power-of-two ring".
    //
    // CODOL's own base and count ARE recovered, four independent ways:
    //   1. Client corpseinfo bound. CG_ResetEntity sub_BBAD90 case 2 and the
    //      initial-snapshot loop sub_BBB3F0 (ida 0xBBB588: `imul ecx, 3B8h`)
    //      both address it as `cgs + 1455144 + 952 * es.number`. Records for
    //      numbers 19..26 span cgs+0x167AD0..0x169890, and cgs+0x169890 is the
    //      next referenced global in the image (15 xrefs) - so the array holds
    //      exactly the eight entity numbers 19..26 and cannot hold more.
    //   2. Embedded-server corpse pool. G_RunCorpseAnimate 0x004E8460 linearly
    //      searches records based at 0xBC22708 with stride 1016 against bound
    //      0xBC246C8; 0x1FC0 / 1016 == 8 slots exactly.
    //   3. Client-side literal. sub_BA6A80 branches on `es.number < 19` - the
    //      same boundary, hardcoded in the client.
    //   4. Retail traffic. The dm demo's corpses are entities 19, 20, 21, 22,
    //      23, 24 in death order: base 19, allocated sequentially.
    // CODOL G_FreeEntity 0x004E8E70 returning only slots 27+ to the dynamic
    // FIFO closes the arithmetic: 19 + 8 == 27, so the ring exactly fills the
    // reserved gap between the client slots and the dynamic region.
    // CODREF(cg_reset_entity): sub_BBAD90 case 2 is CODOL's own corpse branch,
    // found by following BO1's CG_ResetEntity -> CG_CopyCorpseInfo to the
    // equivalent shape here:
    //
    //     v15 = (es.eFlags & 0x80000) == 0;
    //     v22 = 952 * es.number + base + 1455144;      // corpseinfo
    //     if (v15) { if (!ci->model[0] || ...) sub_BB9F70(v22); }
    //     else     { sub_BB9F70(v22); XAnimClearTree; XAnimCloneAnimTree; }
    //     *(v22 + 560) = 1;                            // dobjDirty
    //
    // TWO earlier conclusions were wrong and are corrected here.
    //
    // The gate is 0x80000, NOT 0x200000. There is no two-bit shift for this
    // flag. The 0x200000 test at ida 0x00BB86BD is an unrelated flag inside
    // sub_BB8050, and reading it as the corpse bit was a misattribution - which
    // also means the dm demo's 0xA0206 was right all along and "correcting" it
    // to 0x280000 broke a working value.
    //
    // A populator DOES exist: sub_BB9F70. It was missed because it writes
    // corpseinfo at base 1455144, not the 639904 the accessor sub_BB9EE0 uses -
    // the same struct in a second array - so a scan of one base concluded
    // "nothing ever populates it", which was false.
    inline constexpr std::uint32_t SvCorpseReinitialiseFlag = 0x80000;
    inline constexpr std::uint32_t SvCorpseSpawnFlags = 0xA0000;

    // CODREF(cg_dead_player_hidden): entityState eFlags bit set on death.
    // MEASURED on the wire: a live player's entity carries eFlags 2 or 0, a
    // dead one carries 0x20002, constant for the full three seconds it stays
    // archived. In the client, sub_BB89E0 skips the ENTIRE per-client
    // animation-state initialisation - the XAnim setup, the lerp reset and both
    // 0x40 memsets - when this bit is set:
    //
    //     v5 = 952 * centity[99] + base + 1433256;   // per-client anim state
    //     if ( (centity[62] & 0x20000) == 0 )        // centity+0xF8 = es.eFlags
    //     { ...initialise... }
    //
    // That is IW's EF_DEAD behaviour: the client stops presenting the player
    // entity because the CORPSE is meant to take over, so leaving this bit set
    // on the player entity means the player entity itself stops being drawn -
    // which is the "enemy just disappears" symptom if no corpse takes over.
    //
    // An earlier revision claimed 3.3.3.3 can never render a corpse because
    // nothing populates corpseinfo's model. That was FALSE and is deleted:
    // sub_BB9F70 is the populator, and it was missed only because it writes at
    // base 1455144 while the accessor sub_BB9EE0 reads the second array at
    // 639904. Whether the corpse path is REACHED at runtime is still open and
    // tracked by TODO(CODOL) below - it is not a settled impossibility.
    //
    // The bit stays in the playerState, where pmove needs it. It is masked only
    // out of the entityState that goes on the wire, and only while the death
    // animation is being held.
    inline constexpr std::uint32_t SvDeadPlayerHiddenFlag = 0x20000;

    // A corpse spawns with trType 1 and holds it while the body settles, then is
    // handed to the ragdoll on BOTH trajectories - the shape is measured off the
    // dm demo (slot 20 spawns at t=216700 and ragdolls at t=217700).
    //
    // The demo's ragdoll VALUE is 13 and that value DOES NOT EXIST IN THIS
    // BUILD. CODREF(bg_evaluate_trajectory) sub_AB29C0 switches on trType and
    // handles only 0..12; everything else falls to
    //     Com_Error(2, "90 %i", trType)
    // which is the error dialog a live client raised on the first kill after
    // 13 was sent. Sending a demo constant straight across builds is exactly
    // the trap this project keeps hitting: the demo gave the SHAPE correctly
    // and the NUMBER wrongly.
    //
    // 9 is this build's ragdoll type. Its switch groups case 9 with 0, 1 and 12
    // as "hold the position", which is what a client-simulated ragdoll needs
    // from the server, and IW3 names 9 TR_RAGDOLL / TR_FIRST_RAGDOLL with
    // 10 TR_RAGDOLL_GRAVITY - the apos value the demo pairs with it, and one
    // this build's switch does accept, which is why aprType 10 never errored.
    inline constexpr std::uint8_t SvCorpseSpawnTrajectoryType = 1;
    inline constexpr std::uint8_t SvCorpseRagdollTrajectoryType = 9;
    inline constexpr std::uint8_t SvCorpseRagdollAngleTrajectoryType = 10;
    inline constexpr std::uint32_t SvCorpseRagdollDelayMilliseconds = 1000;

    // CODREF(player_die): the corpse's settle must NOT land on the frame the
    // player respawns, or the body is destroyed the instant it settles.
    //
    // The chain, proven from the client image:
    //   1. respawnTime      = serverTime + max(deathAnimMs, 1)
    //      clearReinitTime  = serverTime + max(deathAnimMs, 50)
    //      Identical expressions, so both fire on the SAME server frame.
    //   2. On that frame the client updates the respawning player's clientInfo.
    //      CG_UpdateCharacterModelsFromClientInfo 0x0051BC80 CLEARS ALL TEN
    //      character model slots when modelIndex is zero.
    //   3. The corpse's eFlags change on that same frame re-triggers
    //      CG_ResetEntity sub_BBAD90 case 2, which calls CG_CopyCorpseInfo
    //      sub_BB9F70 and copies that just-cleared clientinfo into corpseinfo.
    //   4. BG_UpdatePlayerDObj 0x0040B700 opens with
    //          if (!*(_DWORD *)a5 || !**(_BYTE **)(a5 + 24))  // !valid || !model[0]
    //      and FREES the DObj on that branch.
    //   5. Nothing re-copies corpseinfo afterwards - the array has exactly three
    //      code references in the whole image and all are read/copy paths - so
    //      the body never comes back.
    //
    // Retail never hits this. Its settle is 1.4..2.9 s after the CORPSE spawn
    // (measured across ~18 dm-demo corpse lives) while its respawn is a separate
    // gametype timer, so the two are never on the same frame - which is why a
    // retail corpse survives its owner's respawn and lives ~80 s until the slot
    // is reused.
    //
    // Separating them keeps the settle inside the measured retail window
    // (deathAnimMs 1616..1818 plus this offset is 1.87..2.07 s after spawn)
    // while guaranteeing the corpse is never reset on a respawn frame.
    inline constexpr std::uint32_t SvCorpseSettleRespawnSeparationMs = 250;
    // No server-side test can catch a regression here: the damage is done in the
    // CLIENT, which frees the corpse DObj after copying a cleared clientinfo, and
    // the server's own snapshot still contains a perfectly valid corpse. So the
    // invariant is enforced at compile time instead - zeroing this separation
    // silently restores "the body vanishes the moment it settles".
    static_assert(
        SvCorpseSettleRespawnSeparationMs > 0,
        "the corpse settle must not share a frame with the respawn: "
        "CG_UpdateCharacterModelsFromClientInfo 0x0051BC80 clears all ten model "
        "slots on a zero modelIndex, CG_ResetEntity case 2 would copy that empty "
        "clientinfo into corpseinfo, and BG_UpdatePlayerDObj 0x0040B700 frees the "
        "DObj on its !model[0] branch");

    inline constexpr std::uint32_t FirstPlayerCorpseEntityNum = 19;
    // CODDIFF(1649370): EIGHTEEN, not eight. The base is unchanged; the ring
    // is not.
    //
    // MEASURED on this build's own retail traffic, offline, 6160/6160
    // snapshots decoded with no desync (CODOL-main Tools/demo-re):
    //
    //     ET_PLAYER          1..8      the eight players in that match
    //     ET_PLAYER_CORPSE   19..36    CONTIGUOUS, 18 distinct numbers
    //     everything else    37..750   and the LOWEST of them is exactly 37
    //
    // That reproduces every step of the argument above with 18 in place of 8:
    // base 19, allocated sequentially, and 19 + 18 == 37 closes the gap to the
    // dynamic region exactly as 19 + 8 == 27 did there. Eighteen is also this
    // build's client-slot count -- EngineBindings.hpp's
    // ServerCharacterInfoSlotCount, the 18 in `0xAF350 + 18 * 0x450`, and the
    // room capacity the lobby reports.
    //
    // The four derivations above it are 3.3.3.3's and were never re-run here:
    // out.exe's 0x004E8460 is a dvar registration, not G_RunCorpseAnimate, so
    // the corpseinfo bound, the pool stride and the `es.number < 19` literal
    // are all unchecked on this build. The demo needs none of them.
    //
    // What the carried 8 cost: this server would hand a DYNAMIC entity number
    // 27..36, which the client stores as a CORPSE -- sub_BB9EE0 indexes
    // corpseinfo by the entity number with no subtraction and no bounds check
    // -- and it would recycle corpse slots after eight bodies where retail
    // uses eighteen.
    inline constexpr std::uint32_t PlayerCorpseRingSize = 18;
    // Pin the ring to the gap rather than bounding it. `<=` would pass for any
    // ring at or below the real one, which is the direction a carried constant
    // is wrong in.
    static_assert(
        FirstPlayerCorpseEntityNum + PlayerCorpseRingSize ==
            FirstDynamicServerEntityNum,
        "the corpse ring must exactly fill the reserved gap between the client "
        "slots and the dynamic region: retail traffic puts corpses at 19..36 "
        "and the lowest dynamic entity at 37");

    struct SvEntityHandle
    {
        // OLMOD(generation-safe-entity-pool): generation is source capability
        // identity corresponding to CODOL's incremented slot-use count.
        std::uint32_t entityNum{};
        std::uint32_t generation{};

        bool operator==(const SvEntityHandle &) const = default;
    };

    struct SvEntityLifetime
    {
        // OLMOD(generation-safe-entity-pool): normalized source lifetime, not
        // the native 0x2C8-byte CODOL gentity_s.
        std::uint32_t entityNum{};
        std::uint32_t generation{};
        std::uint32_t otherEntityNum{ EntityNumNone };
        std::uint32_t birthTime{};
        std::uint32_t eventTime{};
        bool inUse{};
        bool freeAfterEvent{};

        bool operator==(const SvEntityLifetime &) const = default;
    };

    // OLMOD(generation-safe-entity-pool): source transaction owner mirroring
    // CODOL allocation lifetime; this is not the native gentity_s array.
    class SvEntityPool
    {
    public:
        [[nodiscard]] bool reset(std::uint32_t firstDynamicEntityNum);
        // TAKE A NUMBER OUT OF SEQUENTIAL ALLOCATION'S REACH.
        //
        // Retail's static map entities do not occupy a contiguous run: factory's
        // are 37, 42..46, 48, 53, 55, 56, 59.. -- and the client resolves
        // cl.entityBaselines BY NUMBER (snapshot flag 0x10). A dynamic entity
        // handed 42 would inherit that slot's origin, model and solid, so every
        // number the map's const-baseline table names has to be withheld from
        // spawn() whether or not a static entity is published on it.
        //
        // Reserved slots stay reachable through spawnAt and never enter the free
        // list. Call before the first spawn; reset() clears every reservation.
        [[nodiscard]] bool reserve(std::uint32_t entityNum);
        [[nodiscard]] std::optional<SvEntityHandle> spawn(
            std::uint32_t serverTime);
        // Allocate one specific number. Only a reserved, unused slot is
        // eligible -- taking an arbitrary number would let a static entity land
        // on a slot sequential allocation has already promised to someone.
        [[nodiscard]] std::optional<SvEntityHandle> spawnAt(
            std::uint32_t entityNum,
            std::uint32_t serverTime);
        [[nodiscard]] bool free(
            SvEntityHandle handle,
            std::uint32_t serverTime);
        [[nodiscard]] bool rollbackFree(
            SvEntityHandle handle,
            const SvEntityLifetime &previousLifetime);
        [[nodiscard]] bool markFreeAfterEvent(
            SvEntityHandle handle,
            std::uint32_t eventTime,
            std::uint32_t otherEntityNum);
        [[nodiscard]] std::vector<SvEntityHandle> expiredEventEntities(
            std::uint32_t serverTime) const;
        [[nodiscard]] const SvEntityLifetime *resolve(
            SvEntityHandle handle) const;
        [[nodiscard]] const SvEntityLifetime *resolve(
            std::uint32_t entityNum) const;
        [[nodiscard]] std::uint32_t firstDynamicEntityNum() const;
        [[nodiscard]] std::uint32_t highWaterEntityNum() const;
        [[nodiscard]] std::size_t freeEntityCount() const;

    private:
        std::array<SvEntityLifetime, EntityNumWorld> entities_{};
        std::array<bool, EntityNumWorld> reserved_{};
        std::deque<std::uint32_t> freeEntities_;
        std::uint32_t firstDynamicEntityNum_{};
        std::uint32_t highWaterEntityNum_{};
        bool configured_{};
    };
}
