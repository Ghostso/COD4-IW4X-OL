#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <functional>
#include <optional>

namespace CodolGameServer
{
    struct SvPlayerState;
    struct SvAbilityModifiers;
    struct SvHoldBreathState;

    struct SvNativePlayerState
    {
        // CODDIFF(1649370): 0x3564 is 3.3.3.3's per-client image. This build's
        // is 0x3BBC: the engine's own clear loop bounds at 32 * stride --
        // `cmp ebx, 0x6AC80` in A sub_464490 against `cmp ebx, 0x77780` in
        // C sub_5BEB50 -- and 0x77780 / 32 = 0x3BBC. PmoveSingle writes
        // through this buffer, so the old size was 1624 bytes short of what
        // the engine believes it owns.
        static constexpr std::size_t Size = 0x3BBC;

        // OLMOD(native-playerstate-byte-image): exact-size persistent CODOL
        // image. Only explicitly projected fields are named; all other bytes
        // remain native-owned across command candidates and are reset only at
        // the reviewed spawn lifetime boundary.
        alignas(std::uint32_t) std::array<std::byte, Size> bytes{};

        bool operator==(const SvNativePlayerState &) const = default;
    };

    static_assert(sizeof(SvNativePlayerState) == SvNativePlayerState::Size);
    static_assert(alignof(SvNativePlayerState) == alignof(std::uint32_t));

    // A transient view, not another field in WorldClientState. The cooking
    // timer at +48 differs from the nearby throwback timer at +50.
    struct SvNativeOffhandState
    {
        std::uint32_t weaponAssetIndex{};
        std::int32_t grenadeTimeLeft{};
        std::uint32_t field004C{}; // 429450 writes entity-none sentinel; owner meaning unconfirmed.
        std::int32_t throwbackTimeLeft{};
        std::uint32_t throwbackWeaponAssetIndex{};
        bool operator==(const SvNativeOffhandState &) const = default;
    };
    [[nodiscard]] SvNativeOffhandState SV_ReadNativeOffhandState(
        const SvNativePlayerState &source);
    // Only after a grenade launch has been staged successfully, on the native
    // command candidate. Failure of a later stage must roll this image back.
    void SV_ClearNativeGrenadeTimer(SvNativePlayerState &candidate);

    struct SvNativePredictableEvent
    {
        std::int32_t event{};
        std::int32_t parameter{};

        bool operator==(const SvNativePredictableEvent &) const = default;
    };

    static_assert(sizeof(SvNativePredictableEvent) == 8);

    struct SvNativePredictableEventBatch
    {
        std::int32_t currentSequence{};
        std::array<SvNativePredictableEvent, 4> events{};
        std::size_t count{};

        bool operator==(const SvNativePredictableEventBatch &) const = default;
    };

    struct SvNativePlayerStateActionDiagnostics
    {
        std::int32_t pmType{};
        std::int32_t clientNum{};
        std::uint32_t viewmodelIndex{};
        std::uint32_t currentWeaponAssetIndex{};
        std::array<std::uint32_t, 2> weaponAnimation{};
        std::array<std::int32_t, 2> weaponState{};
        std::array<std::uint32_t, 2> weaponShotCount{};

        bool operator==(const SvNativePlayerStateActionDiagnostics &) const = default;
    };

    // These projections only touch CODOL-local fields whose offsets are
    // confirmed. Unknown bytes remain owned by the persistent native buffer.
    void SV_SetNativeAbilityModifiers(
        SvNativePlayerState &state, const SvAbilityModifiers &abilities);

    void SV_OverlayPlayerStateToNative(
        const SvPlayerState &source,
        SvNativePlayerState &destination);
    // SECTION 190: THE ALT WEAPON, FOR THE MODE SLOTS AT +0x3E8 AND +0x3F0.
    //
    // Only EngineBindings has the module base, so it reads weaponDefinition
    // +3720 (the index sub_42EF60 links from the name at +3716) and this
    // resolver carries the answer down. A FUNCTION, NOT A FIELD: adding a
    // member to a struct the address-keyed native buffer contains is what
    // broke the death animation twice (section 184h), and nothing here needs
    // to be stored.
    //
    // Unset, or returning 0, means "this weapon has no alt", which is the
    // correct answer for most of them and leaves the slots exactly as they
    // are today.
    using SvAltWeaponResolver =
        std::function<std::uint16_t(std::uint16_t weaponAssetIndex)>;
    void SV_SetAltWeaponResolver(SvAltWeaponResolver resolver);
    // Re-assert ol-mod's plaintext otherFlags at ps+0x10 after a native stage has
    // overwritten it with the engine's protected storage. SV_OverlayPlayerStateToNative
    // already writes it once per think; the native pmove writes over it.
    // Put the current weapon back into the NATIVE buffer, for the same reason
    // SV_SetNativePlayerStateOtherFlags exists: the think re-projects native ->
    // source after the pmove AND again after the weapon-movement stage, so a value
    // corrected only in the source copy is read back off the native buffer and lost
    // before the snapshot is built. Also writes slot 0 of the fifteen-entry weapon
    // list at +0x2F4, because a current weapon the player does not hold is a state
    // the native converter does not have to respect.
    void SV_SetNativePlayerStateCurrentWeapon(
        SvNativePlayerState &destination,
        std::uint32_t weaponAssetIndex);
    // AND THE AMMO WITH IT. Same trap as the current weapon, one step further along:
    // the think projects native -> source AGAIN after the weapon-movement stage, and
    // that projection reads the clips at +0x494 and the pools at +0x41C straight back
    // out of the native buffer. A grant that filled only the source copy was therefore
    // erased before the snapshot was built, which is exactly what "gun in hand, Out of
    // ammo" looks like from the player's side.
    //
    // WHY THE CLIP AND THE POOL ARE BOTH NEEDED: the clip is the magazine the HUD's
    // left-hand number reads and the only thing the weapon can fire from; the pool is
    // the reserve behind the slash. A clip with no pool reads as a gun that can never
    // reload. `heldBefore` is written too, at +0x330, because it lives in the held-weapon
    // state record and not in the index list at +0x2F4 that
    // SV_SetNativePlayerStateCurrentWeapon covers.
    void SV_SetNativePlayerStateWeaponAmmo(
        SvNativePlayerState &destination,
        std::size_t slot,
        std::uint16_t clipIndex,
        std::uint16_t clipCount,
        std::uint16_t ammoIndex,
        std::uint16_t ammoCount);
    void SV_SetNativePlayerStateOtherFlags(
        SvNativePlayerState &destination,
        std::uint32_t otherFlags);
    void SV_SetNativeHoldBreathState(
        SvNativePlayerState &destination,
        float swayScale,
        std::uint32_t timer);
    [[nodiscard]] SvHoldBreathState SV_ReadNativeHoldBreathState(
        const SvNativePlayerState &source,
        std::uint32_t clientNum);
    // Re-assert the five motion fields owned by a mission's scripted player
    // track after Pmove has consumed the user's command. This deliberately
    // does not round-trip the complete native image: predictable events,
    // weapon state and every unknown engine-owned byte remain exactly as the
    // retained movement code produced them.
    void SV_SetNativePlayerStateScriptedMotion(
        SvNativePlayerState &destination,
        const std::array<float, 3> &origin,
        std::uint8_t pmType,
        std::uint32_t pmFlags,
        std::uint32_t groundEntityNum);
    // SetClientViewAngle's authoritative half for a mission-owned camera.
    // Both arrays must be written after Pmove: viewAngles is what the snapshot
    // publishes, while deltaAngles keeps the client's next usercmd from
    // immediately turning the view back to the mouse-owned angle.
    void SV_SetNativePlayerStateScriptedViewAngles(
        SvNativePlayerState &destination,
        const std::array<float, 3> &viewAngles,
        const std::array<float, 3> &deltaAngles);
    // Publishes the mission camera's free-look clamp and linked-camera state.
    // These fields sit in the native player image but remain side storage in
    // SvServerWorld so its address-sensitive client node cannot grow.
    void SV_SetNativePlayerStateScriptedViewLink(
        SvNativePlayerState &destination,
        const std::array<float, 2> &viewAngleClampBase,
        const std::array<float, 2> &viewAngleClampRange,
        const std::array<float, 3> &linkAngles,
        std::uint8_t linkFlags);
    [[nodiscard]] bool SV_OverlayNativePlayerStateToPlayerState(
        const SvNativePlayerState &source,
        SvPlayerState &destination,
        const char **failureReason = nullptr);
    [[nodiscard]] std::int32_t SV_ReadNativePredictableEventSequence(
        const SvNativePlayerState &source);
    [[nodiscard]] std::optional<SvNativePredictableEventBatch>
        SV_ReadNativePredictableEvents(
            const SvNativePlayerState &source,
            std::int32_t oldEventSequence);
    // The four ring slots as the WIRE carries them -- indices 21..24, playerState
    // +0x10C/+0x114/+0x11C/+0x124 -- rather than the batch order
    // SV_ReadNativePredictableEvents returns.
    // PUT AN EVENT INTO THE PLAYER'S OWN RING, the way the engine's Pmove does:
    // write the slot the current cursor names, then advance the cursor. Both live in
    // the NATIVE buffer, so writing them there is what makes the addition survive --
    // the think re-reads the ring and the cursor out of it after every stage.
    //
    // WHY THIS EXISTS AT ALL. Forcing a weapon into the playerState makes the client
    // DRAW it, and that is not the same as the client having TAKEN it. Retail's own
    // dmz capture sends a reliable `a <weapon>` and then, about 300 ms later, a
    // playerState event carrying the same weapon number -- once per pickup and again
    // on every weapon switch. That event is the client running its own acquire path,
    // which is what fills its inventory. Without it the gun is in the hands and in no
    // list.
    void SV_AppendNativePlayerStatePredictableEvent(
        SvNativePlayerState &destination,
        std::int32_t event,
        std::int32_t parameter);
    [[nodiscard]] std::array<SvNativePredictableEvent, 4>
        SV_ReadNativePredictableEventRing(const SvNativePlayerState &source);
    [[nodiscard]] SvNativePlayerStateActionDiagnostics
        SV_ReadNativePlayerStateActionDiagnostics(
            const SvNativePlayerState &source);
}
