#pragma once

#include "../shared/RuntimeLog.hpp"

#include <cstdint>
#include <mutex>
#include <string>

namespace CodolGameServer
{
    enum class GameStateConfigurationStage : std::uint32_t
    {
        None,
        Processing,
        InvalidChecksum,
        MapCenterUnavailable,
        CharacterUnavailable,
        PreparedLoadoutMismatch,
        DynamicWeaponRangeUnavailable,
        PrimaryDependencyRegistrationFailed,
        PrimaryWeaponRegistrationFailed,
        SecondaryDependencyRegistrationFailed,
        SecondaryWeaponRegistrationFailed,
        CharacterChanged,
        ServerCommitFailed,
        Accepted,
        DynamicWeaponRegistryUnavailable,
        DynamicWeaponRegistryRegistrationFailed,
        MiniMapUnavailable,
        ObjectiveMaterialUnavailable,
    };

    struct GameStateConfigurationStatus
    {
        std::uint32_t attemptCount{};
        GameStateConfigurationStage stage{};
        std::int32_t failedClassIndex{-1};
        std::uint32_t registeredClassMask{};
        std::uint32_t firstDynamicWeaponAssetIndex{};

        bool operator==(const GameStateConfigurationStatus &) const = default;
    };

    // Every stage below is a distinct way the gamestate can fail to configure, and NONE of them
    // was reported anywhere: not in the log, not over the dedicated control port. That was
    // survivable while the loadout resolver refused earlier and this code was unreachable. It
    // stopped being survivable the moment the booking started succeeding, because the frame thread
    // then stops somewhere in here and the last line printed is the only thing that says where.
    [[nodiscard]] inline const char *gameStateConfigurationStageName(
        const GameStateConfigurationStage stage)
    {
        switch (stage)
        {
        case GameStateConfigurationStage::None: return "none";
        case GameStateConfigurationStage::Processing: return "processing";
        case GameStateConfigurationStage::InvalidChecksum: return "invalid_checksum";
        case GameStateConfigurationStage::MapCenterUnavailable: return "map_center_unavailable";
        case GameStateConfigurationStage::CharacterUnavailable: return "character_unavailable";
        case GameStateConfigurationStage::PreparedLoadoutMismatch:
            return "prepared_loadout_mismatch";
        case GameStateConfigurationStage::DynamicWeaponRangeUnavailable:
            return "dynamic_weapon_range_unavailable";
        case GameStateConfigurationStage::PrimaryDependencyRegistrationFailed:
            return "primary_dependency_registration_failed";
        case GameStateConfigurationStage::PrimaryWeaponRegistrationFailed:
            return "primary_weapon_registration_failed";
        case GameStateConfigurationStage::SecondaryDependencyRegistrationFailed:
            return "secondary_dependency_registration_failed";
        case GameStateConfigurationStage::SecondaryWeaponRegistrationFailed:
            return "secondary_weapon_registration_failed";
        case GameStateConfigurationStage::CharacterChanged: return "character_changed";
        case GameStateConfigurationStage::ServerCommitFailed: return "server_commit_failed";
        case GameStateConfigurationStage::Accepted: return "accepted";
        case GameStateConfigurationStage::DynamicWeaponRegistryUnavailable:
            return "dynamic_weapon_registry_unavailable";
        case GameStateConfigurationStage::DynamicWeaponRegistryRegistrationFailed:
            return "dynamic_weapon_registry_registration_failed";
        case GameStateConfigurationStage::MiniMapUnavailable: return "minimap_unavailable";
        case GameStateConfigurationStage::ObjectiveMaterialUnavailable:
            return "objective_material_unavailable";
        }
        return "unknown";
    }

    class GameStateConfigurationTracker
    {
    public:
        void processing()
        {
            const std::lock_guard lock(mutex_);
            ++status_.attemptCount;
            status_.stage = GameStateConfigurationStage::Processing;
            status_.failedClassIndex = -1;
            status_.registeredClassMask = 0;
            status_.firstDynamicWeaponAssetIndex = 0;
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer,
                "gamestate configuration attempt=" +
                    std::to_string(status_.attemptCount) + " stage=processing");
        }

        void dynamicWeaponRange(const std::uint32_t firstAssetIndex)
        {
            const std::lock_guard lock(mutex_);
            status_.firstDynamicWeaponAssetIndex = firstAssetIndex;
        }

        void registeredClass(const std::uint32_t classIndex)
        {
            const std::lock_guard lock(mutex_);
            status_.registeredClassMask |= 1u << classIndex;
        }

        void failed(
            const GameStateConfigurationStage stage,
            const std::int32_t classIndex = -1)
        {
            const std::lock_guard lock(mutex_);
            status_.stage = stage;
            status_.failedClassIndex = classIndex;
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer,
                std::string("gamestate configuration FAILED stage=") +
                    gameStateConfigurationStageName(stage) +
                    " class=" + std::to_string(classIndex));
        }

        void accepted()
        {
            const std::lock_guard lock(mutex_);
            status_.stage = GameStateConfigurationStage::Accepted;
            status_.failedClassIndex = -1;
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer,
                "gamestate configuration ACCEPTED classMask=" +
                    std::to_string(status_.registeredClassMask) +
                    " firstDynamicWeapon=" +
                    std::to_string(status_.firstDynamicWeaponAssetIndex));
        }

        [[nodiscard]] GameStateConfigurationStatus status() const
        {
            const std::lock_guard lock(mutex_);
            return status_;
        }

    private:
        mutable std::mutex mutex_;
        GameStateConfigurationStatus status_;
    };
}
