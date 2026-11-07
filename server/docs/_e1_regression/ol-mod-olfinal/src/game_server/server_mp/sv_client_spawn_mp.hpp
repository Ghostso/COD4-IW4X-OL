#pragma once

#include <array>
#include <cstdint>

namespace CodolGameServer
{
    struct SvPlayerState;
    struct SvNativePlayerState;
    struct SvResolvedLoadout;
    struct UserCmd;

    // OLMOD(client-spawn-source-config): source-owned input to the confirmed
    // spawn subset; this is not a recovered CODOL gclient/gentity structure.
    struct SvClientSpawnConfig
    {
        std::uint32_t clientNum{};
        std::uint32_t serverTime{};
        std::array<float, 3> origin{};
        std::array<float, 3> angles{};
        std::uint32_t groundEntityNum{};
        std::uint32_t gravity{ 800 };
        std::uint32_t speed{ 190 };
        float moveSpeedScaleMultiplier{ 1.0f };
        std::uint16_t viewmodelIndex{};
        std::uint32_t maxHealth{ 100 };
        // SPAWN WITH FISTS. Battle royale hands you nothing -- retail BattleCity
        // footage shows an empty HUD and bare hands until the first crate -- so the
        // resolved loadout is validated as usual and then deliberately NOT equipped.
        //
        // It is a spawn flag rather than an empty loadout because both admission
        // (SV_ClientSpawn) and equip (equipResolvedLoadout) run
        // SV_IsResolvedLoadoutValid first: a loadout with no weapons is refused
        // before it can mean anything, and the refusal reads as a broken class pick.
        bool unarmed{};
        // WHAT EMPTY HANDS ACTUALLY HOLD. Weapon index 0 has no viewmodel, so a
        // spawn with no weapon draws no arms at all -- which is what the first
        // unarmed build looked like, and is NOT what retail does: BattleCity footage
        // shows bare gloved hands. The client models "nothing equipped" as a real
        // weapon, `dmz_empty_mp`, and this carries its index. Zero keeps the
        // no-viewmodel behaviour, so an unresolved name degrades instead of failing.
        std::uint16_t unarmedWeaponAssetIndex{};
        const UserCmd *userCmd{};
    };

    // CODREF(client_spawn): source reconstruction of the confirmed atomic
    // playerState/native-playerState subset, not the complete native function.
    // failureReason, when given, receives a static string naming WHICH of the four
    // returns refused. Every one of them used to be an unqualified `return false` into
    // a caller with no else branch, so a spawn that could not happen was indistinguishable
    // from a spawn nobody asked for -- for the player, picking a class simply did nothing.
    [[nodiscard]] bool SV_ClientSpawn(
        SvPlayerState &playerState,
        SvNativePlayerState &nativePlayerState,
        const SvClientSpawnConfig &config,
        const SvResolvedLoadout &loadout,
        const char **failureReason = nullptr);
    // OLMOD(client-loadout-refresh-adapter): source-only compatibility refresh;
    // native projection occurs at the next command boundary.
    [[nodiscard]] bool SV_EquipResolvedLoadout(
        SvPlayerState &playerState,
        const SvResolvedLoadout &loadout);
}
