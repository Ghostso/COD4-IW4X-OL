#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <optional>

namespace CodolGameServer
{
    // CODDIFF(1649370): 170, was 162. This is the length of the event-parameter
    // width table dword_DA9410 -- the count of events that HAVE a declared parameter
    // width, and therefore the range of event entity types (ET_EVENTS + event).
    // It is NOT the bound on an event id in an entity's event ring: codec -94 writes
    // that id as a raw byte, and the client's own decoder gives any id at or past the
    // table a parameter width of zero rather than refusing the snapshot.
    constexpr std::size_t SvEntityEventCount = 170;
    constexpr std::int32_t SvMaximumEntityEventId = 0xFF;

    struct SvEntityEvent
    {
        std::int32_t event{};
        std::int32_t parameter{};

        bool operator==(const SvEntityEvent &) const = default;
    };

    // Uses this build's recovered event-parameter width table.
    [[nodiscard]] bool SV_IsEntityEventValid(const SvEntityEvent &event);

    struct SvNativeEntityState
    {
        // CODDIFF(1649370): 0x110 is 3.3.3.3's entityState_s. This build copies
        // 0x118 -- `mov ecx, 70; rep movsd` in eight places here against
        // `mov ecx, 68` in six on 3.3.3.3 -- which is the +8 the netfield
        // alignment predicts at the tail.
        static constexpr std::size_t Size = 0x118;

        alignas(std::uint32_t) std::array<std::byte, Size> bytes{};
        // OLMOD(address-bound-entitystate-owner): source-side metadata; not
        // part of CODOL's 0x110-byte entityState_s ABI.
        bool secureOriginAddressBound{};

        SvNativeEntityState() = default;
        SvNativeEntityState(const SvNativeEntityState &other);
        SvNativeEntityState(SvNativeEntityState &&other) noexcept;
        SvNativeEntityState &operator=(const SvNativeEntityState &other);
        SvNativeEntityState &operator=(
            SvNativeEntityState &&other) noexcept;

        bool operator==(const SvNativeEntityState &) const = default;
    };

    static_assert(alignof(SvNativeEntityState) == alignof(std::uint32_t));

    struct SvNativeEntityStateProjection
    {
        std::uint32_t number{};
        std::uint8_t eType{};
        std::uint8_t clientNum{};
        std::uint32_t eFlags{};
        float playerSizeScale{};
        std::array<float, 3> origin{};
        std::array<float, 3> angles{};
        std::int32_t movementDir{};
        std::uint8_t positionTrajectoryType{};
        std::uint32_t positionTrajectoryTime{};
        std::uint32_t positionTrajectoryDuration{};
        std::array<float, 3> positionTrajectoryDelta{};
        std::uint8_t angleTrajectoryType{};
        std::uint32_t angleTrajectoryTime{};
        std::uint32_t angleTrajectoryDuration{};
        std::array<float, 3> angleTrajectoryDelta{};
        std::uint32_t groundEntityNum{};
        // CODOL ET_PLAYER field 35 / entityState_s +0xA0. The native
        // conversion owns its value; exact gameplay semantics remain unknown.
        // CODDIFF(1649370): TWENTY-EIGHT bits, not 3.3.3.3's thirteen. Codec -55's
        // four present-bit groups reach bit 27 (2<<0, 4<<2, 11<<6, 5<<17, then single
        // bits at 22..27), so the value needs 32 bits to hold and 0x0FFFFFFF to bound.
        // The codec, the field index 37 and the offset 0xA4 were all ported; the TYPE
        // and its bounds were left at 3.3.3.3's two-group 13-bit shape.
        std::uint32_t unk00A0{};
        // entityState +0x7C, ET_PLAYER index 24, seven bits on the wire.
        std::uint8_t time2{};
        std::uint32_t solid{};
        std::uint8_t eventSequence{};
        std::array<SvEntityEvent, 4> events{};
        std::uint16_t weaponAssetIndex{};
        // CODOL entityState +0xD2 is the third-person presentation selector.
        // BG_PlayerToEntity_SetMisc normally copies current weapon, but its
        // WeaponDef-type-3 branch sources playerState +0x344 instead.
        std::uint16_t presentationWeaponAssetIndex{};
        // CODOL BG_PlayerToEntity_SetMisc writes +0x60 only for weapon states
        // 16..20 when WeaponDef +0x478 matches the build-local marker; zero
        // makes BG_UpdatePlayerDObj fall back to +0xD2. BO1 and Ghosts name
        // the equivalent state-owned candidate offhandWeapon, while CODOL's
        // exact WeaponDef member and accepted weapon family remain TODO.
        std::uint16_t offhandWeaponAssetIndex{};
        // CODDIFF(bg_update_player_dobj): CODOL playerState +0x33C is a
        // one-based index into mp/coKnifeStatsTable.csv, not BO1's
        // worldModel[] selector or a second WeaponDef asset index. The client
        // copies it through +0x64 to characterInfo +0x328 for knife overrides.
        std::uint16_t coKnifeStatsIndex{};
        // CODOL ET_PLAYER field 21 is the complete dword at +0xE0. The client
        // currently proves only that byte +0xE2 participates in the DObj dirty
        // comparison; preserve all bits rather than manufacturing a bool.
        std::uint32_t unk00E0{};
        std::uint16_t legsAnim{};
        std::uint16_t torsoAnim{};

        bool operator==(const SvNativeEntityStateProjection &) const = default;
    };

    // CODDIFF(1649370): 0x7FF is 3.3.3.3's ELEVEN-bit animation index. The extracted
    // ET_PLAYER netfield table for this build gives entityState +0xDC and +0xE0 TWELVE
    // bits each, and the live server refused real values of 2048 and 2796 against the old
    // bound -- both past 2047, neither past 4095. Defined once; two places read it.
    //
    // It also confirms those two offsets, which matters: audit-native-offsets.py wanted
    // legsAnim and torsoAnim moved to 0xE4/0xE8, and the netfield table has 8-bit and
    // 32-bit fields at exactly those offsets. The engine's own converter settles it --
    // sub_411360 does `mov [edi+0xDC], eax` and `mov [edi+0xE0], ecx`.
    constexpr std::uint32_t MaximumEntityAnimationIndex = 0xFFF;

    struct SvEntityOriginKeys
    {
        std::array<std::uint32_t, 3> values{};

        bool operator==(const SvEntityOriginKeys &) const = default;
    };

    // Only CODOL-local fields confirmed by conversion writes and the 0x110
    // whole-object copies are exposed. The remaining bytes stay opaque.
    // TODO(CODOL): SV_ResetNativeEntityState creates an unbound bootstrap
    // image. Recover the complete ClientSpawn -> initial ClientEndFrame/native
    // conversion order and stop publishing bootstrap states before their
    // first BG_PlayerStateToEntityState conversion.
    void SV_ResetNativeEntityState(
        SvNativeEntityState &state,
        std::uint32_t number,
        std::uint8_t eType,
        std::uint32_t eFlags,
        std::uint16_t weaponAssetIndex);
    [[nodiscard]] bool SV_SetNativeEntityStateSolid(
        SvNativeEntityState &state,
        std::uint32_t solid);
    [[nodiscard]] bool SV_SetNativeEntityStateModelIndex(
        SvNativeEntityState &state,
        std::uint16_t modelIndex);
    [[nodiscard]] bool SV_SetNativeEntityStatePlayerSizeScale(
        SvNativeEntityState &state,
        float playerSizeScale);
    [[nodiscard]] bool SV_SetNativeEntityStateUnknownA0(
        SvNativeEntityState &state,
        std::uint32_t value);
    void SV_MarkNativeEntityStateSecureOriginBound(
        SvNativeEntityState &state);
    [[nodiscard]] std::optional<SvNativeEntityStateProjection>
        SV_ReadNativeEntityState(const SvNativeEntityState &state);
    [[nodiscard]] std::optional<SvNativeEntityStateProjection>
        SV_ReadNativeEntityState(
            const SvNativeEntityState &state,
            const SvEntityOriginKeys &originKeys);
}
