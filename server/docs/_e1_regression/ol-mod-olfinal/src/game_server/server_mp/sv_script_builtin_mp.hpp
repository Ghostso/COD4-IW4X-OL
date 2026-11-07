#pragma once

#include "sv_snapshot_mp.hpp"
#include "sv_mapents_mp.hpp"

#include <array>
#include <cstdint>
#include <functional>
#include <map>
#include <optional>
#include <span>
#include <string>
#include <string_view>
#include <variant>
#include <vector>

namespace CodolGameServer
{
    enum class SvScriptBuiltinKind : std::uint8_t
    {
        Function,
        Method,
    };

    enum class SvScriptObjectKind : std::uint8_t
    {
        Player,
        Entity,
    };

    struct SvScriptObjectRef
    {
        SvScriptObjectKind kind{};
        std::uint32_t id{};
        std::optional<std::uint32_t> entityGeneration;

        bool operator==(const SvScriptObjectRef &) const = default;
    };

    using SvScriptVector = std::array<float, 3>;
    using SvScriptObjectArray = std::vector<SvScriptObjectRef>;

    using SvScriptValue = std::variant<
        std::monostate,
        bool,
        std::int64_t,
        double,
        std::string,
        SvScriptVector,
        SvScriptObjectRef,
        SvScriptObjectArray>;

    struct SvScriptBuiltinId
    {
        SvScriptBuiltinKind kind{};
        std::string name;

        auto operator<=>(const SvScriptBuiltinId &) const = default;
    };

    struct SvScriptBuiltinCall
    {
        SvScriptBuiltinId id;
        std::optional<SvScriptObjectRef> self;
        std::vector<SvScriptValue> arguments;
    };

    enum class SvScriptBuiltinErrorCode : std::uint8_t
    {
        None,
        UnknownBuiltin,
        InvalidArgumentCount,
        InvalidArgumentType,
        InvalidArgumentValue,
        MissingSelf,
        InvalidSelf,
        ObjectNotFound,
        InvalidObjectState,
        WeaponNotOwned,
        InvalidAmmoState,
        WorldMutationFailed,
        DeathTransitionUnavailable,
        MatchStateUnavailable,
    };

    struct SvScriptBuiltinError
    {
        SvScriptBuiltinErrorCode code{};
        std::string message;
    };

    struct SvScriptBuiltinResult
    {
        SvScriptValue value;
        SvScriptBuiltinError error;

        [[nodiscard]] bool succeeded() const;
    };

    class SvScriptBuiltinRegistry
    {
    public:
        struct MatchScoreCallbacks
        {
            std::function<bool(std::uint32_t clientNum, std::int32_t delta)>
                addClientScore;
            std::function<bool(std::uint32_t clientNum, std::int32_t delta)>
                addClientXp;
            std::function<bool(std::uint32_t clientNum, std::int32_t delta)>
                addTeamScoreForClient;
            // The counter a teamless gametype's score limit reads, kept apart
            // from the display score for the same reason cha keeps team score
            // apart from it: they are in different units.
            std::function<bool(std::uint32_t clientNum, std::int32_t delta)>
                addKillForClient;
        };

        // Server presentation and lifecycle operations that a map script can
        // request but SvServerWorld cannot own. Reliable commands and
        // configstrings belong to SvClientSystem, while mission completion
        // belongs to ServerCore's match state. Keeping these callbacks here
        // preserves that ownership boundary instead of teaching the world
        // about network clients or match orchestration.
        struct MissionCallbacks
        {
            std::function<bool(
                std::uint32_t clientNum, std::string_view command)>
                sendServerCommand;
            std::function<bool(
                std::uint16_t index, std::string_view value)>
                setConfigString;
            std::function<bool()> finishMission;
        };

        using ModelResolver = std::function<std::optional<std::uint16_t>(
            std::string_view modelName)>;
        // A weapon asset index from its name, so a script names `ak104dmz_mp` rather
        // than hardcoding a number out of a per-map band.
        using WeaponResolver = std::function<std::optional<std::uint16_t>(
            std::string_view weaponName)>;
        using SoundResolver = std::function<std::optional<std::uint16_t>(
            std::string_view aliasName)>;
        using AnimationResolver = std::function<std::optional<std::uint16_t>(
            std::string_view animationName)>;

        // THE PARSED zm ZONE MODEL, or an empty vector when the map is not zm or the
        // parse failed. re/demo-re/21-zm-zones-and-spawners.md.
        //
        // Returns BY VALUE and is read under the server's own lock, so a script cannot
        // hold a reference into the world while the world changes. The zone model is a
        // few dozen entries and the script reads it a handful of times per round, so
        // the copy is not worth removing; it would be if a per-frame caller appeared.
        // PUBLISH A MODEL INTO THE GAMESTATE'S CONFIGSTRING BAND, BY NAME.
        //
        // The client's band is whatever the SERVER transmits -- loading the same map
        // does NOT give it the dedicated's native band. Without this the agent
        // element's model index resolves to "" on the client, sub_530C90 leaves
        // record+568 empty and sub_52FBE0 builds no DObj at all, which is exactly why
        // zombies did not draw. re/demo-re/20-zm-actor-lifecycle.md 12.21.
        //
        // THE SCRIPT OWNS THE NAME, which is why this is a builtin and not a C++ list:
        // the map's own actor_* entities name DIFFERENT models from the ones zm.lua
        // spawns, and driving it off the map published the wrong ones (12.22).
        // Call it at script init -- it must run before a client is served a gamestate.
        using ModelPrecacher = std::function<bool(const std::string &modelName)>;
        using ZmZoneProvider = std::function<std::vector<SvZmZone>()>;

        explicit SvScriptBuiltinRegistry(
            SvServerWorld &world,
            MatchScoreCallbacks matchScoreCallbacks = {},
            ModelResolver modelResolver = {},
            WeaponResolver weaponResolver = {},
            ZmZoneProvider zmZoneProvider = {},
            ModelPrecacher modelPrecacher = {},
            MissionCallbacks missionCallbacks = {},
            SoundResolver soundResolver = {},
            AnimationResolver animationResolver = {});

        void setAnimationResolver(AnimationResolver resolver);

        [[nodiscard]] bool contains(
            SvScriptBuiltinKind kind,
            std::string_view name) const;
        [[nodiscard]] std::size_t size() const;
        [[nodiscard]] SvScriptBuiltinResult invoke(
            SvScriptBuiltinKind kind,
            std::string_view name,
            std::optional<SvScriptObjectRef> self = std::nullopt,
            std::span<const SvScriptValue> arguments = {}) const;

    private:
        using Handler = std::function<SvScriptBuiltinResult(
            SvServerWorld &world,
            const SvScriptBuiltinCall &call)>;

        SvServerWorld &world_;
        MatchScoreCallbacks matchScoreCallbacks_;
        MissionCallbacks missionCallbacks_;
        ModelResolver modelResolver_;
        WeaponResolver weaponResolver_;
        ZmZoneProvider zmZoneProvider_;
        ModelPrecacher modelPrecacher_;
        SoundResolver soundResolver_;
        AnimationResolver animationResolver_;
        std::map<SvScriptBuiltinId, Handler> handlers_;
    };
}
