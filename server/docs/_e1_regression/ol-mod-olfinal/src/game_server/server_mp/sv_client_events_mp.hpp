#pragma once

#include "sv_melee_mp.hpp"
#include "sv_native_playerstate_mp.hpp"
#include "sv_weapon_fire_mp.hpp"

#include <cstddef>
#include <cstdint>
#include <functional>
#include <optional>
#include <span>

namespace CodolGameServer
{
    struct SvGameEntity;
    struct SvPlayerState;
    struct SvResolvedLoadout;
    struct SvResolvedWeapon;
    struct SvResolvedEquipment;
    struct SvOffhandWeapon;
    struct SvRewardWeapon;

    // CODREF(client_events): ClientEvents receives at most the four new
    // predictable events retained by the CODOL playerState ring.
    inline constexpr std::size_t MaximumClientEventsPerCommand = 4;

    // OLMOD(client-fire-event): decoded source view of CODOL's 0x31..0x34
    // event contract, not native entity/event storage.
    struct SvFireWeaponEvent
    {
        std::int32_t event{};
        SvPlayerHand hand{};
        bool lastShot{};

        bool operator==(const SvFireWeaponEvent &) const = default;
    };

    // OLMOD(client-fire-handler-result): source transaction result; CODOL's
    // native FireWeapon path does not return this enum.
    enum class SvFireWeaponResult : std::uint8_t
    {
        Applied,
        DeferredImpact,
        Failed,
    };

    // OLMOD(client-fire-handler): bounded mutation callback over the outer
    // command candidate, not a native CODOL function prototype.
    using SvFireWeaponHandler = std::function<SvFireWeaponResult(
        SvPlayerState &playerState,
        SvGameEntity &entity,
        const SvResolvedWeapon &weapon,
        const SvWeaponFireBasis &basis,
        const SvWeaponSpreadResult &spread,
        const SvFireWeaponEvent &event)>;

    using SvWeaponFireBasisBuilder = std::function<
        std::optional<SvWeaponFireBasis>(const SvResolvedWeapon &weapon)>;

    // CODREF(1649370): PM_OffHandUse 0x429AE0 emits event 73 with ps+3E4
    // and consumes ammo itself. This continuation stages effects on the command
    // candidate only; the enclosing clientThink owns publication and rollback.
    using SvOffhandUseHandler = std::function<SvFireWeaponResult(
        SvPlayerState &playerState,
        SvGameEntity &entity,
        const SvOffhandWeapon &weapon)>;

    // OLMOD(melee-handler): EV_FIRE_MELEE is NOT in out.exe's server-only event
    // table at 0x00DADC0C -- that array holds exactly ten ids and melee is not
    // among them -- so this is not a restoration of a CODOL dedicated dispatch.
    // It is a source-side producer reading an event out of the predictable ring,
    // which is the same thing section 156's fall damage does with
    // EV_LANDING_PAIN (0x9E, also absent from that table). Optional: when no
    // handler is installed the event is ignored and behaviour is unchanged.
    using SvMeleeAttackHandler = std::function<SvMeleeAttackResult(
        SvPlayerState &playerState,
        SvGameEntity &entity,
        const SvResolvedWeapon &weapon,
        const SvWeaponFireBasis &basis)>;

    // OLMOD(client-event-result): source admission/continuation result for the
    // complete ordered event slice, not a native HandleClientEvent return.
    enum class SvClientEventResult : std::uint8_t
    {
        Applied,
        // PM_Weapon state is authoritative and may commit, while the
        // cross-entity bullet impact transaction remains deliberately absent.
        DeferredImpact,
        Unsupported,
        Invalid,
        Failed,
    };

    [[nodiscard]] std::optional<SvFireWeaponEvent>
        SV_DecodeFireWeaponEvent(const SvNativePredictableEvent &event);

    [[nodiscard]] bool SV_IsRewindableAttackEvent(
        const SvNativePredictableEvent &event);

    // Per-command side context. It stays outside SvGameClient because that
    // address-sensitive native owner cannot grow safely.
    void SV_SetCurrentClientEventPerkSpreadScale(float scale);
    [[nodiscard]] float SV_CurrentClientEventPerkSpreadScale();

    [[nodiscard]] bool SV_IsServerOnlyClientEvent(std::int32_t event);

    // SECTION 190: THE ALT WEAPON IS NOT IN THE LOADOUT, AND MUST NOT HAVE TO BE.
    //
    // Once the server switches a player to their alt (sv_snapshot_mp.cpp, the
    // alt-fire rising edge), every fire event arrives naming a weapon
    // SV_FindResolvedWeapon cannot find -- and that path does not merely drop
    // the shot, it returns Invalid and rejects the whole clientThink candidate.
    // The player would freeze the moment they pulled the trigger.
    //
    // The obvious fix is to put the alt in SvResolvedLoadout, and that is the
    // one thing this file will not do: SvResolvedLoadout lives inside the
    // client state the address-keyed native buffer is sized against, and
    // growing a struct in that position is what broke the death animation
    // twice (section 184h). A lookup costs nothing and moves nothing.
    //
    // Returns false when the index is not an alt of anything, which is the
    // answer for every ordinary weapon and leaves the refusal exactly as it is.
    using SvAltWeaponLookup =
        std::function<bool(std::uint16_t weaponAssetIndex,
                           SvResolvedWeapon &resolved)>;
    void SV_SetAltWeaponLookup(SvAltWeaponLookup lookup);

    // Which of the fourteen refusals `client_events_rejected` actually was.
    // See the note in the implementation.
    SvClientEventResult SV_ClientEventRefused(
        SvClientEventResult result, const char *reason);
    [[nodiscard]] const char *SV_LastClientEventRefusal();
    // The same lookup, for the spawn path: an alt with its OWN clip index --
    // the AK's masterkey, not the shared-clip alts -- has no ammo unless the
    // bootstrap gives it some, and a gun you can switch to and cannot fire is
    // not a working alt-fire.
    [[nodiscard]] bool SV_LookupAltWeapon(
        std::uint16_t weaponAssetIndex, SvResolvedWeapon &resolved);

    // AND THE OTHER DIRECTION, WHICH IS WHAT THE SPAWN PATH ACTUALLY WANTED.
    //
    // `SV_LookupAltWeapon` takes an ALT and resolves it -- its own comment says
    // so -- and the spawn bootstrap was handing it the HOST, so it returned
    // false for every weapon in every loadout and the alt was never given a
    // heldWeapons slot. The name reads like "look up the alt OF this weapon"
    // and means "look this alt weapon up", which is the whole distance between
    // the two (section 191z).
    //
    // That is not cosmetic. out.exe's finish-weapon-change routine (0x00424470)
    // refuses any cmd.weapon that is not in ps+0x2F4 and stores a ZERO in its
    // place, so an alt outside the held list can never become the current
    // weapon no matter who asks.
    using SvHostAltWeaponLookup =
        std::function<bool(std::uint16_t hostAssetIndex,
                           SvResolvedWeapon &resolved)>;
    void SV_SetHostAltWeaponLookup(SvHostAltWeaponLookup lookup);
    [[nodiscard]] bool SV_LookupAltWeaponForHost(
        std::uint16_t hostAssetIndex, SvResolvedWeapon &resolved);

    // OLMOD(client-event-result): The caller owns the candidate transaction.
    // Applied and DeferredImpact may commit; Unsupported, Invalid and Failed
    // reject the complete candidate, including mutations made by an earlier
    // server-only event. DeferredImpact preserves native PM_Weapon state while
    // explicitly reporting an absent continuation after the recovered prefix.
    [[nodiscard]] SvClientEventResult SV_HandleClientEventsDetailed(
        SvPlayerState &playerState,
        SvGameEntity &entity,
        float currentAimSpreadScale,
        const SvResolvedLoadout *resolvedLoadout,
        std::span<const SvNativePredictableEvent> events,
        const SvWeaponFireBasisBuilder &fireBasisBuilder,
        const SvFireWeaponHandler &fireWeaponHandler,
        const SvMeleeAttackHandler &meleeAttackHandler = {},
        const SvResolvedEquipment *equipment = nullptr,
        const SvOffhandUseHandler &offhandUseHandler = {},
        const SvRewardWeapon *uavWeapon = nullptr,
        float perkSpreadScale = SV_CurrentClientEventPerkSpreadScale());

    [[nodiscard]] bool SV_HandleClientEvents(
        SvPlayerState &playerState,
        SvGameEntity &entity,
        float currentAimSpreadScale,
        const SvResolvedLoadout *resolvedLoadout,
        std::span<const SvNativePredictableEvent> events,
        const SvWeaponFireBasisBuilder &fireBasisBuilder,
        const SvFireWeaponHandler &fireWeaponHandler);

    // ADD ONE PRESENTATION EVENT TO A PLAYER'S ENTITY RING -- this build's
    // G_AddEvent. The client reads the ring with `slot = sequence & 3` and
    // dispatches every slot from its own cursor up to the sequence
    // (CG_CheckEntityEvents, out.exe 0x00537A00: eventSequence at cent+0x1A8,
    // the id at cent+slot*8+0x1AC), so an event is added by writing the CURRENT
    // sequence's slot and then advancing it.
    //
    // ORDERING IS WHY THIS WORKS. sv_snapshot_mp assigns the native projection
    // to the entity BEFORE it dispatches client events, so an append here
    // survives to the wire rather than being overwritten.
    void SV_AddEntityPresentationEvent(
        SvGameEntity &entity, std::int32_t eventId);

    // REMOTE GUNFIRE. Translate a SERVER-ONLY fire id into the one other
    // clients act on, for the ENTITY event ring only.
    //
    // WHAT WAS WRONG: nobody could hear anybody else shoot, and no enemy dot
    // ever appeared on the compass. Both come from the same place --
    // CG_EntityEvent case 41 feeds the weapon-fire scheduler (out.exe
    // sub_599000), which per queued shot plays the weapon sound AND raises the
    // compass ping. No event, no queue entry, neither output.
    //
    // THE DEMO SAYS WHAT A REAL SERVER SENDS. Across the retail dm match,
    // ET_PLAYER entities carry EV_FIRE_WEAPON (41) **2250 times** -- the second
    // most common event after footsteps -- plus EV_FIRE_WEAPON_LASTSHOT (42)
    // 85 times, and NO EV_SV_FIRE_WEAPON and NO EV_FAKE_FIRE at all.
    //
    // WHAT THIS SERVER SENT INSTEAD: id 54, twenty-one times in a whole match
    // log, and 41 never. 54 is one of the ten ids in out.exe's own SERVER-ONLY
    // array at 0x00DADC0C (1E 1D 23 17 | 36 37 38 39 | 3A 3B) -- the shooter's
    // client telling the DEDICATED SERVER that it fired. We consume those
    // correctly for the bullet path; they were also leaking onto the wire,
    // where no client acts on them.
    //
    // The mapping is read name-for-name off out.exe's own event name array
    // (re/olfinal-events.tsv), not by arithmetic on the ids:
    //
    //     54 EV_SV_FIRE_WEAPON                -> 41 EV_FIRE_WEAPON
    //     55 EV_SV_FIRE_WEAPON_LASTSHOT       -> 42 EV_FIRE_WEAPON_LASTSHOT
    //     56 EV_SV_FIRE_WEAPON_LEFT           -> 47 EV_FIRE_WEAPON_LEFT
    //     57 EV_SV_FIRE_WEAPON_LASTSHOT_LEFT  -> 48 EV_FIRE_WEAPON_LASTSHOT_LEFT
    //
    // 0x3A/0x3B are deliberately NOT mapped: they are in the same server-only
    // array, but what selects them is not established and inventing a
    // counterpart for them would be guessing a contract.
    //
    // APPLY THIS TO THE ENTITY PROJECTION ONLY, NEVER TO THE PLAYERSTATE. The
    // bullet path reads the server-only ids out of the playerState predictable
    // ring; rewriting them there would silently disarm every shot.
    [[nodiscard]] constexpr std::int32_t SV_PresentationFireEventId(
        const std::int32_t serverEventId)
    {
        switch (serverEventId)
        {
        case 0x36: return 0x29;
        case 0x37: return 0x2A;
        case 0x38: return 0x2F;
        case 0x39: return 0x30;
        default:   return serverEventId;
        }
    }

    static_assert(SV_PresentationFireEventId(54) == 41);
    static_assert(SV_PresentationFireEventId(55) == 42);
    static_assert(SV_PresentationFireEventId(56) == 47);
    static_assert(SV_PresentationFireEventId(57) == 48);
    // Everything else passes through untouched -- footsteps, reloads, jumps.
    static_assert(SV_PresentationFireEventId(152) == 152);
    static_assert(SV_PresentationFireEventId(0x3A) == 0x3A);
    static_assert(SV_PresentationFireEventId(0) == 0);
}
