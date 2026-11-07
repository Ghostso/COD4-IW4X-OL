#include "sv_gamestate_mp.hpp"

#include "qcommon/net_chan_mp.hpp"

#include <algorithm>
#include <charconv>
#include <cmath>
#include <limits>
#include <optional>
#include <cstdio>

namespace CodolGameServer
{
    // CODREF(actor_grounded_adapter): original Factory gamestate registers
    // stopwatchneedle/face/glass at5169..5171. CODOL514880 resolves dynamic
    // classes through the parsed string table;457350 and563043 consume names.
    // OLMOD(dynamic-server-materials): bounded transactional allocation from
    // the observed native boundary. Existing slots and constant entries survive.
    std::optional<std::vector<std::uint16_t>> SV_RegisterDynamicServerMaterials(
        SvGameState &gameState, const std::uint16_t firstDynamic,
        const std::span<const std::string> names,
        const std::map<std::uint16_t,std::string> &existing)
    {
        if (!firstDynamic || firstDynamic>=ServerMaterialConfigStringCount ||
            names.empty() || names.size()>16 ||
            (gameState.firstDynamicServerMaterial &&
             *gameState.firstDynamicServerMaterial!=firstDynamic)) return std::nullopt;
        auto strings=gameState.configStrings;
        for (const auto &[relative,name]:existing) {
            if (relative<firstDynamic || relative>=ServerMaterialConfigStringCount ||
                name.empty() || name.size()>=64 || name.find('\0')!=std::string::npos)
                return std::nullopt;
            const auto index=static_cast<std::uint16_t>(ServerMaterialConfigStringBase+relative);
            const auto found=strings.find(index);
            if (found!=strings.end() && found->second!=name) return std::nullopt;
            strings.insert_or_assign(index,name);
        }
        std::vector<std::uint16_t> result;
        for (const auto &name:names) {
            if (name.empty() || name.size()>=64 || name.find('\0')!=std::string::npos)
                return std::nullopt;
            std::optional<std::uint16_t> reuse;
            for (std::uint16_t i=firstDynamic;i<ServerMaterialConfigStringCount;++i) {
                const auto found=strings.find(ServerMaterialConfigStringBase+i);
                if (found!=strings.end() && found->second==name) {reuse=i;break;}
            }
            if (!reuse) {
                for (std::uint16_t i=firstDynamic;i<ServerMaterialConfigStringCount;++i)
                    if (!strings.contains(ServerMaterialConfigStringBase+i)) {
                        strings.emplace(static_cast<std::uint16_t>(ServerMaterialConfigStringBase+i),name);
                        reuse=i;break;
                    }
            }
            if (!reuse) return std::nullopt;
            result.push_back(*reuse);
        }
        gameState.configStrings=std::move(strings);
        gameState.firstDynamicServerMaterial=firstDynamic;
        return result;
    }

    std::optional<std::uint16_t> SV_EffectConfigStringToEventParameter(
        const std::uint16_t configStringIndex)
    {
        // CODREF(sv_send_client_gamestate): CODOL EV_PLAY_FX reserves event
        // parameter zero; relative server effect indexes are 1..399.
        if (configStringIndex <= EffectConfigStringBase ||
            configStringIndex >=
                EffectConfigStringBase + EffectConfigStringCount)
        {
            return std::nullopt;
        }
        return static_cast<std::uint16_t>(
            configStringIndex - EffectConfigStringBase);
    }

    std::optional<std::uint16_t> SV_EffectEventParameterToConfigString(
        const std::uint16_t eventParameter)
    {
        if (!eventParameter || eventParameter >= EffectConfigStringCount)
            return std::nullopt;
        return static_cast<std::uint16_t>(
            EffectConfigStringBase + eventParameter);
    }

    namespace
    {
        // CODREF(sv_send_client_gamestate): widths and table limits below come
        // from CODOL CL_ParseGameStateMessage and its weapon-table consumers.
        // On 1649370 that pair is A 0x46DB20 <-> C 0x472D80, line for line.
        //
        // CODDIFF(1649370): the configstring table grew 7058 -> 12761, so the
        // explicit index widened 13 -> 14 bits, and the weapon block grew
        // 900 -> 1700 entries, so the weapon index widened 10 -> 11.
        constexpr std::uint16_t MaxConfigStrings = 0x31D9;
        constexpr std::uint32_t ConfigStringIndexBits = 14;
        constexpr std::uint32_t WeaponIndexBits = 11;
        // '%' (37). out.exe's binary-command dispatcher sub_614AC0 switches on
        // (firstByte - 37); case 0 is the live config-string update. See §157c.
        constexpr std::uint8_t WeaponConfigStringUpdateVerb = 37;
        // CODDIFF(1649370): the two weapon tables carry SEPARATE count widths
        // and 3.3.3.3 could not show it - there all four of these fields were
        // ten bits, so one shared WeaponIndexBits was indistinguishable from
        // four constants. Here the simple table's count is still ten bits
        // (C 0x472E8C) while the modular table's is eleven (C 0x472F99).
        constexpr std::uint32_t SimpleWeaponTableCountBits = 10;
        constexpr std::uint32_t ModularWeaponTableCountBits = 11;
        constexpr std::uint32_t ModularValue8Bits = 8;
        constexpr std::uint32_t ModularValue9Bits = 9;
        constexpr std::uint32_t AttachmentCountBits = 4;
        constexpr std::uint32_t AttachmentIndexBits = 14;
        constexpr std::string_view Base64Alphabet =
            "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";

        bool validWeaponConfigStringIndex(const std::uint16_t index)
        {
            return index >= WeaponConfigStringBase &&
                index < WeaponConfigStringBase + WeaponConfigStringCount;
        }

        std::optional<std::uint16_t> highestWeaponAssetIndex(
            const SvGameState &gameState)
        {
            std::optional<std::uint16_t> highest;
            const auto visit = [&highest](const auto &records) {
                if (!records.empty())
                {
                    const auto assetIndex = static_cast<std::uint16_t>(
                        records.rbegin()->first - WeaponConfigStringBase);
                    highest = highest ? std::max(*highest, assetIndex) : assetIndex;
                }
            };
            visit(gameState.simpleWeaponConfigStrings);
            visit(gameState.modularWeaponConfigStrings);
            return highest;
        }

        void populateWeaponCountConfigString(SvGameState &gameState)
        {
            const auto highest = highestWeaponAssetIndex(gameState);
            if (highest)
            {
                gameState.configStrings.insert_or_assign(
                    WeaponCountConfigStringIndex,
                    std::to_string(static_cast<std::uint32_t>(*highest) + 1));
            }
        }

        std::optional<std::array<float, 3>> parseMapCenter(
            std::string_view value)
        {
            std::array<float, 3> result{};
            for (auto &component : result)
            {
                while (!value.empty() && value.front() == ' ')
                    value.remove_prefix(1);
                if (value.empty())
                    return std::nullopt;
                const auto parsed = std::from_chars(
                    value.data(), value.data() + value.size(), component);
                if (parsed.ec != std::errc{} || parsed.ptr == value.data() ||
                    !std::isfinite(component))
                {
                    return std::nullopt;
                }
                value.remove_prefix(static_cast<std::size_t>(
                    parsed.ptr - value.data()));
                if (!value.empty() && value.front() != ' ')
                    return std::nullopt;
            }
            while (!value.empty() && value.front() == ' ')
                value.remove_prefix(1);
            return value.empty() ? std::optional{ result } : std::nullopt;
        }

        std::optional<std::uint32_t> parseUnsignedToken(
            std::string_view &value)
        {
            while (!value.empty() && value.front() == ' ')
                value.remove_prefix(1);
            if (value.empty())
                return std::nullopt;

            const auto separator = value.find(' ');
            const auto token = value.substr(0, separator);
            std::uint32_t parsed{};
            const auto [pointer, error] = std::from_chars(
                token.data(), token.data() + token.size(), parsed);
            if (error != std::errc{} || pointer != token.data() + token.size())
                return std::nullopt;
            value = separator == std::string_view::npos
                ? std::string_view{}
                : value.substr(separator + 1);
            return parsed;
        }

        std::string formatFloat(const float value)
        {
            std::array<char, 64> buffer{};
            const auto length = std::snprintf(
                buffer.data(), buffer.size(), "%.6f", value);
            return length > 0 && static_cast<std::size_t>(length) < buffer.size()
                ? std::string(buffer.data(), static_cast<std::size_t>(length))
                : std::string{};
        }

        std::optional<std::string> formatMiniMap(
            const SvGameState::MiniMap &miniMap)
        {
            if (miniMap.material.empty() || miniMap.material.size() > 255 ||
                miniMap.material.find_first_of("\"\\") != std::string::npos ||
                miniMap.material.find('\0') != std::string::npos)
            {
                return std::nullopt;
            }
            for (const auto value : {
                     miniMap.upperLeft[0], miniMap.upperLeft[1],
                     miniMap.lowerRight[0], miniMap.lowerRight[1] })
            {
                if (!std::isfinite(value))
                    return std::nullopt;
            }
            return "\"" + miniMap.material + "\" " +
                formatFloat(miniMap.upperLeft[0]) + " " +
                formatFloat(miniMap.upperLeft[1]) + " " +
                formatFloat(miniMap.lowerRight[0]) + " " +
                formatFloat(miniMap.lowerRight[1]);
        }

        std::string formatServerInfo(const SvGameState &gameState)
        {
            // RETAIL'S OWN SERVERINFO KEYS, measured -- see
            // re/demo-re/20-zm-actor-lifecycle.md 12.13 and 12.19. `cs 0` on all
            // four zm captures carries these ten keys, byte-identical across
            // three maps, and in THIS order (serverinfo is sorted by key, which
            // is why the numeric keys lead and ui_* trails scr_*).
            //
            // THEY ARE NOT DECORATION. sub_515340 -- the client's gamestate
            // parse -- reads "mapname", "g_gametype", then atoi("2482"), then
            // calls the gametype classifier sub_514E70, then atoi("g_hardcore").
            // Two of the keys it reads are ones this server used to omit, so
            // they resolved to atoi("") == 0 where retail gets 24.
            //
            // IF YOU CHANGE THIS STRING YOU MUST REGENERATE SvGameStateFixtureBytes
            // IN THE HEADER IN THE SAME COMMIT. EngineBindings::bind() re-derives
            // this writer's output at every launch and compares it to that array;
            // a mismatch fails stage=message_bindings, the plugin never comes up
            // on EITHER side, and the client reports "your level file differs from
            // the server's" -- which looks nothing like a serverinfo problem and
            // has now cost three separate debugging sessions.
            auto result = std::string(
                    "\\2482\\24"
                    "\\2485\\4"
                    "\\2490\\214"
                    "\\2491\\0"
                    "\\3056\\2"
                    "\\g_gametype\\") + gameState.gameType +
                "\\g_hardcore\\0"
                "\\mapname\\" + gameState.mapName +
                "\\scr_game_allowkillcam\\0"
                "\\scr_team_fftype\\0";
            if (gameState.uiGameRules)
            {
                result += "\\ui_scorelimit\\" +
                    std::to_string(gameState.uiGameRules->scoreLimit) +
                    "\\ui_timelimit\\" +
                    std::to_string(gameState.uiGameRules->timeLimitMinutes) +
                    "\\ui_halftime\\" +
                    std::to_string(gameState.uiGameRules->halfTime ? 1 : 0);
            }
            return result;
        }

        std::string formatSystemInfo(const SvGameState &gameState)
        {
            if (!gameState.uiGameRules)
                return {};
            return "\\ui_scorelimit\\" +
                std::to_string(gameState.uiGameRules->scoreLimit) +
                "\\ui_timelimit\\" +
                std::to_string(gameState.uiGameRules->timeLimitMinutes) +
                "\\ui_halftime\\" +
                std::to_string(gameState.uiGameRules->halfTime ? 1 : 0);
        }

        std::optional<std::string> formatPlayerNameConfigString(
            const std::string_view username)
        {
            const auto encoded = SV_EncodePlayerName(username);
            if (!encoded)
                return std::nullopt;
            std::string result;
            result.reserve(encoded->size() + 2);
            result.push_back(static_cast<char>(0xFE));
            result.append(*encoded);
            result.push_back(static_cast<char>(0xFE));
            return result;
        }

        template <typename Records, typename WriteValue>
        void writeWeaponConfigStringTable(
            MsgWriter &message,
            const Records &records,
            const std::uint32_t countBits,
            WriteValue writeValue)
        {
            // CODREF(sv_send_client_gamestate): records use one sequential bit
            // or an explicit configstring index, then type-owned data. The
            // COUNT width is the caller's because the two tables differ - see
            // SimpleWeaponTableCountBits / ModularWeaponTableCountBits.
            message.MSG_WriteBits(
                static_cast<std::int32_t>(records.size()), countBits);
            auto previous = -1;
            for (const auto &[configStringIndex, value] : records)
            {
                const auto sequential =
                    static_cast<int>(configStringIndex) == previous + 1;
                message.MSG_WriteBits(sequential ? 1 : 0, 1);
                if (!sequential)
                {
                    message.MSG_WriteBits(
                        configStringIndex, ConfigStringIndexBits);
                }
                writeValue(message, value);
                previous = configStringIndex;
            }
        }
    }

    std::optional<std::string> SV_EncodePlayerName(
        const std::string_view username)
    {
        // CODREF(sv_send_client_gamestate): CODOL's player-name configstring
        // consumer expects printable identity bytes encoded as framed Base64.
        if (username.empty() || username.size() > 16 ||
            std::ranges::any_of(username, [](const unsigned char value) {
                return value < 0x20 || value > 0x7E;
            }))
        {
            return std::nullopt;
        }

        std::string encoded;
        encoded.reserve((username.size() + 2) / 3 * 4);
        for (std::size_t offset = 0; offset < username.size(); offset += 3)
        {
            const auto remaining = username.size() - offset;
            const auto first = static_cast<std::uint8_t>(username[offset]);
            const auto second = remaining > 1
                ? static_cast<std::uint8_t>(username[offset + 1])
                : 0;
            const auto third = remaining > 2
                ? static_cast<std::uint8_t>(username[offset + 2])
                : 0;
            const auto value = static_cast<std::uint32_t>(first) << 16 |
                static_cast<std::uint32_t>(second) << 8 | third;
            encoded.push_back(Base64Alphabet[(value >> 18) & 0x3F]);
            encoded.push_back(Base64Alphabet[(value >> 12) & 0x3F]);
            encoded.push_back(remaining > 1
                ? Base64Alphabet[(value >> 6) & 0x3F]
                : '=');
            encoded.push_back(remaining > 2
                ? Base64Alphabet[value & 0x3F]
                : '=');
        }
        return encoded;
    }

    bool SV_PerfBaseline()
    {
        static const bool baseline = [] {
            std::size_t length{};
            char value[8]{};
            return getenv_s(&length, value, sizeof(value), "OLMOD_PERF_BASELINE") == 0 &&
                length > 0 && value[0] == '1';
        }();
        return baseline;
    }

    void SV_PopulateRequiredConfigStrings(SvGameState &gameState)
    {
        // OLMOD(gamestate-required-projection): rebuild all derived strings
        // from authoritative source fields so stale identities/rules cannot
        // survive into a newly constructed gamestate.
        gameState.configStrings.insert_or_assign(
            ServerInfoConfigStringIndex,
            formatServerInfo(gameState));
        const auto systemInfo = formatSystemInfo(gameState);
        if (systemInfo.empty())
        {
            gameState.configStrings.erase(SystemInfoConfigStringIndex);
            gameState.configStrings.erase(UiScoreLimitConfigStringIndex);
            gameState.configStrings.erase(UiTimeLimitConfigStringIndex);
            gameState.configStrings.erase(UiHalfTimeConfigStringIndex);
        }
        else
        {
            gameState.configStrings.insert_or_assign(
                SystemInfoConfigStringIndex, systemInfo);
            gameState.configStrings.insert_or_assign(
                UiScoreLimitConfigStringIndex,
                std::to_string(gameState.uiGameRules->scoreLimit));
            gameState.configStrings.insert_or_assign(
                UiTimeLimitConfigStringIndex,
                std::to_string(gameState.uiGameRules->timeLimitMinutes));
            gameState.configStrings.insert_or_assign(
                UiHalfTimeConfigStringIndex,
                std::to_string(gameState.uiGameRules->halfTime ? 1 : 0));
            // CODREF(sv_send_client_gamestate): the HUD countdown reads
            // configstring 15 as an absolute match END time in server-time ms and
            // displays (end - serverTime) / 1000. A zero time limit means "no
            // limit", and the clock must then be absent rather than expired.
            if (gameState.uiGameRules->timeLimitMinutes)
            {
                gameState.configStrings.insert_or_assign(
                    MatchEndTimeConfigStringIndex,
                    std::to_string(
                        static_cast<std::uint64_t>(gameState.matchStartServerTime) +
                        static_cast<std::uint64_t>(
                            gameState.uiGameRules->timeLimitMinutes) *
                            60u * 1000u));
            }
            else
            {
                gameState.configStrings.erase(MatchEndTimeConfigStringIndex);
            }
        }
        gameState.configStrings.insert_or_assign(
            GameNameConfigStringIndex,
            GameNameConfigString);
        // OLMOD(vision): the map's colour grade. Section 99 proved the reliable
        // command path live; this is the one the RETAIL server uses, and it is
        // better for the base grade because it rides in the GAMESTATE -- it
        // applies while the map loads instead of on the frame a client goes
        // Active, and a reconnecting client gets it without being told again.
        //
        // ALL SIX, AND EVERY NAME IS MEASURED. Retail fills the naked, pain and
        // overlay slots with the map's own name and the other three with two
        // shared sets. Both of those ship in common_mp.ff -- extracted with the
        // section 93 pipeline from IIPS\IIPSDownload\ff_init_common_mp_V111.ifs,
        // whose zone carries 193 vision assets including
        // vision/default_night_mp.vision, vision/thermal_mp.vision,
        // vision/grayscale.vision, vision/near_death.vision and the
        // vision/black_bw.vision the client refuses -- so they are loaded for
        // every MP map, not just this one. The map's own grade rides in the
        // map fastfile and section 99b proved it loads.
        //
        // CODDIFF(vision-blend): retail sends 1000 ms here and this sends 0.
        // A blend at map load would fade in from vision/default.vision, which is
        // the flat look this whole change exists to remove; 0 is the instant
        // setter 0x0046CE80 and is what `visionSetNaked(mapname, 0)` means in
        // stock GSC.
        if (!gameState.mapName.empty() && !SV_PerfBaseline())
        {
            const auto visionSet = "\"" + gameState.mapName + "\" 0";
            for (const auto index : {
                     VisionNakedConfigStringIndex,
                     VisionPainConfigStringIndex,
                     VisionOverlayConfigStringIndex,
                 })
            {
                gameState.configStrings.insert_or_assign(index, visionSet);
            }
            // Retail names thermal_mp for BOTH missilecam and thermal, and
            // vision/missilecam.vision exists in the same zone -- so this is
            // retail's choice being copied, not the only name available.
            gameState.configStrings.insert_or_assign(
                VisionNightConfigStringIndex, "\"default_night_mp\" 0");
            gameState.configStrings.insert_or_assign(
                VisionMissilecamConfigStringIndex, "\"thermal_mp\" 0");
            gameState.configStrings.insert_or_assign(
                VisionThermalConfigStringIndex, "\"thermal_mp\" 0");
        }
        // TODO(CODOL): replace this initial server state through the recovered
        // setmapcenter producer after gameplay path-node setup is restored.
        // Exit when map startup supplies its native center before gamestate.
        gameState.configStrings.insert_or_assign(
            MapCenterConfigStringIndex,
            "0 0 0");
        for (std::uint16_t offset = 0;
             offset < PlayerNameConfigStringCount;
             ++offset)
        {
            gameState.configStrings.erase(
                static_cast<std::uint16_t>(PlayerNameConfigStringBase + offset));
        }
        for (std::size_t clientNum = 0;
             clientNum < gameState.playerNames.size();
             ++clientNum)
        {
            const auto value = formatPlayerNameConfigString(
                gameState.playerNames[clientNum]);
            if (value)
            {
                gameState.configStrings.insert_or_assign(
                    static_cast<std::uint16_t>(
                        PlayerNameConfigStringBase + clientNum),
                    *value);
            }
        }
        for (std::size_t index = 0; index < RequiredScriptMenus.size(); ++index)
            gameState.scriptMenus[index] = RequiredScriptMenus[index];
    }

    bool SV_SetMapCenterConfigString(
        SvGameState &gameState,
        const std::string_view value)
    {
        const auto parsed = parseMapCenter(value);
        if (!parsed || value.find('\0') != std::string_view::npos)
            return false;
        gameState.mapCenter = *parsed;
        gameState.configStrings.insert_or_assign(
            MapCenterConfigStringIndex, std::string(value));
        return true;
    }

    bool SV_SetMiniMapConfigStrings(
        SvGameState &gameState,
        const float northYawDegrees,
        SvGameState::MiniMap miniMap)
    {
        // CODREF(sv_send_client_gamestate): configstrings 2037/2038 are the
        // native compass north-yaw and material/bounds consumers.
        const auto miniMapText = formatMiniMap(miniMap);
        const auto northYawText = formatFloat(northYawDegrees);
        if (!std::isfinite(northYawDegrees) || !miniMapText ||
            northYawText.empty())
        {
            return false;
        }
        gameState.northYawDegrees = northYawDegrees;
        gameState.miniMap = std::move(miniMap);
        gameState.configStrings.insert_or_assign(
            NorthYawConfigStringIndex, northYawText);
        gameState.configStrings.insert_or_assign(
            MiniMapConfigStringIndex, *miniMapText);
        return true;
    }

    bool SV_AddSimpleWeaponConfigString(
        SvGameState &gameState,
        const std::uint16_t weaponAssetIndex,
        const std::uint16_t baseWeaponAssetIndex)
    {
        // OLMOD(gamestate-weapon-registry): maintain a disjoint validated
        // source registry before serializing the CODOL compact tables.
        if (!weaponAssetIndex || weaponAssetIndex >= WeaponConfigStringCount ||
            !baseWeaponAssetIndex || baseWeaponAssetIndex >= (1u << WeaponIndexBits))
        {
            return false;
        }
        const auto configStringIndex = static_cast<std::uint16_t>(
            WeaponConfigStringBase + weaponAssetIndex);
        if (gameState.modularWeaponConfigStrings.contains(configStringIndex))
            return false;
        const auto [iterator, inserted] = gameState.simpleWeaponConfigStrings.emplace(
            configStringIndex, baseWeaponAssetIndex);
        if (!inserted && iterator->second != baseWeaponAssetIndex)
            return false;
        populateWeaponCountConfigString(gameState);
        return true;
    }

    bool SV_AddModularWeaponConfigString(
        SvGameState &gameState,
        const std::uint16_t weaponAssetIndex,
        SvModularWeaponConfigString configString)
    {
        if (!weaponAssetIndex || weaponAssetIndex >= WeaponConfigStringCount ||
            !configString.baseWeaponAssetIndex ||
            configString.baseWeaponAssetIndex >= (1u << WeaponIndexBits) ||
            configString.optionalValue9 >= (1u << ModularValue9Bits) ||
            configString.attachmentAssetIndexes.size() >=
                (1u << AttachmentCountBits))
        {
            return false;
        }
        for (const auto attachmentAssetIndex : configString.attachmentAssetIndexes)
        {
            if (!attachmentAssetIndex ||
                attachmentAssetIndex >= (1u << AttachmentIndexBits) - 1)
            {
                return false;
            }
        }
        const auto configStringIndex = static_cast<std::uint16_t>(
            WeaponConfigStringBase + weaponAssetIndex);
        if (gameState.simpleWeaponConfigStrings.contains(configStringIndex))
            return false;
        const auto existing = gameState.modularWeaponConfigStrings.find(
            configStringIndex);
        if (existing != gameState.modularWeaponConfigStrings.end())
            return existing->second == configString;
        gameState.modularWeaponConfigStrings.emplace(
            configStringIndex, std::move(configString));
        populateWeaponCountConfigString(gameState);
        return true;
    }

    std::optional<SvModularWeaponConfigString>
        SV_ParseModularWeaponConfigString(std::string_view value)
    {
        if (!value.starts_with("** "))
            return std::nullopt;
        value.remove_prefix(3);

        const auto baseWeaponAssetIndex = parseUnsignedToken(value);
        const auto value8 = parseUnsignedToken(value);
        const auto optionalValue9 = parseUnsignedToken(value);
        if (!baseWeaponAssetIndex || !*baseWeaponAssetIndex ||
            *baseWeaponAssetIndex >= (1u << WeaponIndexBits) || !value8 ||
            *value8 >= (1u << ModularValue8Bits) || !optionalValue9 ||
            *optionalValue9 >= (1u << ModularValue9Bits))
        {
            return std::nullopt;
        }

        SvModularWeaponConfigString result{
            .baseWeaponAssetIndex = static_cast<std::uint16_t>(
                *baseWeaponAssetIndex),
            .value8 = static_cast<std::uint8_t>(*value8),
            .optionalValue9 = static_cast<std::uint16_t>(*optionalValue9),
        };
        while (!value.empty())
        {
            const auto attachmentAssetIndex = parseUnsignedToken(value);
            if (!attachmentAssetIndex || !*attachmentAssetIndex ||
                *attachmentAssetIndex >= (1u << AttachmentIndexBits) - 1 ||
                result.attachmentAssetIndexes.size() + 1 >=
                    (1u << AttachmentCountBits))
            {
                return std::nullopt;
            }
            result.attachmentAssetIndexes.push_back(
                static_cast<std::uint16_t>(*attachmentAssetIndex));
        }
        return result;
    }

    std::optional<std::uint16_t> SV_RegisterModularWeaponConfigString(
        SvGameState &gameState,
        const std::uint16_t firstDynamicWeaponAssetIndex,
        SvModularWeaponConfigString configString)
    {
        // CODDIFF(sv_send_client_gamestate): ol-mod allocates deterministic
        // contiguous dynamic indexes because the removed CODOL backend/server
        // registry is unavailable. Existing non-contiguous state fails closed.
        if (!firstDynamicWeaponAssetIndex ||
            firstDynamicWeaponAssetIndex >= WeaponConfigStringCount)
        {
            return std::nullopt;
        }
        for (const auto &[index, existing] : gameState.modularWeaponConfigStrings)
        {
            if (existing == configString)
            {
                const auto weaponAssetIndex = static_cast<std::uint16_t>(
                    index - WeaponConfigStringBase);
                return weaponAssetIndex >= firstDynamicWeaponAssetIndex
                    ? std::optional{ weaponAssetIndex }
                    : std::nullopt;
            }
        }

        std::size_t dynamicOffset{};
        for (const auto &[index, _] : gameState.modularWeaponConfigStrings)
        {
            const auto expectedIndex = static_cast<std::uint32_t>(
                WeaponConfigStringBase) + firstDynamicWeaponAssetIndex + dynamicOffset;
            if (index != expectedIndex)
                return std::nullopt;
            ++dynamicOffset;
        }

        const auto weaponAssetIndex = static_cast<std::uint32_t>(
            firstDynamicWeaponAssetIndex) + dynamicOffset;
        if (weaponAssetIndex >= WeaponConfigStringCount ||
            !SV_AddModularWeaponConfigString(
                gameState,
                static_cast<std::uint16_t>(weaponAssetIndex),
                std::move(configString)))
        {
            return std::nullopt;
        }
        return static_cast<std::uint16_t>(weaponAssetIndex);
    }

    bool SV_ValidateGameState(const SvGameState &gameState)
    {
        // OLMOD(gamestate-admission): validate every derived/raw table and
        // cross-field invariant before the writer mutates its output message.
        const auto serverInfo = gameState.configStrings.find(ServerInfoConfigStringIndex);
        const auto systemInfo = gameState.configStrings.find(SystemInfoConfigStringIndex);
        const auto uiScoreLimit = gameState.configStrings.find(
            UiScoreLimitConfigStringIndex);
        const auto uiTimeLimit = gameState.configStrings.find(
            UiTimeLimitConfigStringIndex);
        const auto uiHalfTime = gameState.configStrings.find(
            UiHalfTimeConfigStringIndex);
        const auto gameName = gameState.configStrings.find(GameNameConfigStringIndex);
        const auto mapCenter = gameState.configStrings.find(
            MapCenterConfigStringIndex);
        const auto northYaw = gameState.configStrings.find(
            NorthYawConfigStringIndex);
        const auto miniMap = gameState.configStrings.find(
            MiniMapConfigStringIndex);
        const auto expectedServerInfo = formatServerInfo(gameState);
        const auto expectedSystemInfo = formatSystemInfo(gameState);
        if (gameState.playerNames.size() > PlayerNameConfigStringCount)
            return false;
        for (std::size_t clientNum = 0;
             clientNum < PlayerNameConfigStringCount;
             ++clientNum)
        {
            const auto configString = gameState.configStrings.find(
                static_cast<std::uint16_t>(
                    PlayerNameConfigStringBase + clientNum));
            if (clientNum < gameState.playerNames.size())
            {
                const auto expected = formatPlayerNameConfigString(
                    gameState.playerNames[clientNum]);
                if (!expected || configString == gameState.configStrings.end() ||
                    configString->second != *expected)
                {
                    return false;
                }
            }
            else if (configString != gameState.configStrings.end())
            {
                return false;
            }
        }
        if (gameState.mapName.empty() || gameState.gameType.empty() ||
            gameState.mapName.find('\0') != std::string::npos ||
            gameState.gameType.find('\0') != std::string::npos ||
            gameState.mapName.find('\\') != std::string::npos ||
            gameState.gameType.find('\\') != std::string::npos ||
            serverInfo == gameState.configStrings.end() ||
            serverInfo->second != expectedServerInfo ||
            expectedSystemInfo.empty() !=
                (systemInfo == gameState.configStrings.end()) ||
            (!expectedSystemInfo.empty() &&
                systemInfo->second != expectedSystemInfo) ||
            gameState.uiGameRules.has_value() !=
                (uiScoreLimit != gameState.configStrings.end()) ||
            gameState.uiGameRules.has_value() !=
                (uiTimeLimit != gameState.configStrings.end()) ||
            gameState.uiGameRules.has_value() !=
                (uiHalfTime != gameState.configStrings.end()) ||
            (gameState.uiGameRules &&
                (uiScoreLimit->second !=
                        std::to_string(gameState.uiGameRules->scoreLimit) ||
                    uiTimeLimit->second !=
                        std::to_string(gameState.uiGameRules->timeLimitMinutes) ||
                    uiHalfTime->second !=
                        std::to_string(gameState.uiGameRules->halfTime ? 1 : 0))) ||
            gameName == gameState.configStrings.end() ||
            gameName->second != GameNameConfigString ||
            mapCenter == gameState.configStrings.end() ||
            parseMapCenter(mapCenter->second) !=
                std::optional{ gameState.mapCenter } ||
            gameState.northYawDegrees.has_value() != gameState.miniMap.has_value() ||
            gameState.northYawDegrees.has_value() !=
                (northYaw != gameState.configStrings.end()) ||
            gameState.miniMap.has_value() !=
                (miniMap != gameState.configStrings.end()) ||
            (gameState.northYawDegrees &&
                (!std::isfinite(*gameState.northYawDegrees) ||
                    northYaw->second != formatFloat(*gameState.northYawDegrees))) ||
            (gameState.miniMap &&
                formatMiniMap(*gameState.miniMap) !=
                    std::optional{ miniMap->second }) ||
            gameState.configStrings.size() >
                static_cast<std::size_t>(std::numeric_limits<std::int16_t>::max()))
        {
            return false;
        }
        if (gameState.firstDynamicServerMaterial &&
            (!*gameState.firstDynamicServerMaterial ||
             *gameState.firstDynamicServerMaterial>=ServerMaterialConfigStringCount))
            return false;
        for (const auto &[index, value] : gameState.configStrings)
        {
            if (index >= MaxConfigStrings || value.find('\0') != std::string::npos ||
                validWeaponConfigStringIndex(index) ||
                (index >= ServerMaterialConfigStringBase &&
                    index < ServerMaterialConfigStringBase +
                        ServerMaterialConfigStringCount &&
                    (!gameState.firstDynamicServerMaterial ||
                     index<ServerMaterialConfigStringBase+*gameState.firstDynamicServerMaterial ||
                     value.empty() || value.size()>=64)))
                return false;
        }
        if (gameState.gameType == "sd")
        {
            if (!gameState.sdObjectiveMaterials)
                return false;
            const auto &materials = *gameState.sdObjectiveMaterials;
            for (const auto index : {
                     materials.targetA, materials.targetB,
                     materials.defendA, materials.defendB,
                     materials.defuseA, materials.defuseB,
                     materials.bomb, materials.escort })
            {
                if (!index || index >= ServerMaterialConfigStringCount)
                    return false;
            }
        }
        // CODDIFF(1649370): each table's COUNT is bounded by that table's own
        // count field, not by the weapon index width. They were all ten bits
        // on 3.3.3.3, so one bound read correctly there by accident.
        if (gameState.simpleWeaponConfigStrings.size() >=
                (1u << SimpleWeaponTableCountBits) ||
            gameState.modularWeaponConfigStrings.size() >=
                (1u << ModularWeaponTableCountBits))
        {
            return false;
        }
        for (const auto &[index, baseWeaponAssetIndex] :
            gameState.simpleWeaponConfigStrings)
        {
            if (!validWeaponConfigStringIndex(index) || !baseWeaponAssetIndex ||
                baseWeaponAssetIndex >= (1u << WeaponIndexBits) ||
                gameState.modularWeaponConfigStrings.contains(index))
            {
                return false;
            }
        }
        for (const auto &[index, configString] :
            gameState.modularWeaponConfigStrings)
        {
            if (!validWeaponConfigStringIndex(index) ||
                !configString.baseWeaponAssetIndex ||
                configString.baseWeaponAssetIndex >= (1u << WeaponIndexBits) ||
                configString.optionalValue9 >= (1u << ModularValue9Bits) ||
                configString.attachmentAssetIndexes.size() >=
                    (1u << AttachmentCountBits))
            {
                return false;
            }
            for (const auto attachmentAssetIndex :
                configString.attachmentAssetIndexes)
            {
                if (!attachmentAssetIndex ||
                    attachmentAssetIndex >= (1u << AttachmentIndexBits) - 1)
                {
                    return false;
                }
            }
        }
        const auto highestWeapon = highestWeaponAssetIndex(gameState);
        const auto weaponCount = gameState.configStrings.find(
            WeaponCountConfigStringIndex);
        if (highestWeapon)
        {
            if (weaponCount == gameState.configStrings.end())
                return false;
            std::uint32_t parsedWeaponCount{};
            const auto &[pointer, error] = std::from_chars(
                weaponCount->second.data(),
                weaponCount->second.data() + weaponCount->second.size(),
                parsedWeaponCount);
            if (error != std::errc{} ||
                pointer != weaponCount->second.data() + weaponCount->second.size() ||
                parsedWeaponCount != static_cast<std::uint32_t>(*highestWeapon) + 1)
            {
                return false;
            }
        }
        else if (weaponCount != gameState.configStrings.end())
        {
            return false;
        }
        for (const auto &menu : gameState.scriptMenus)
        {
            if (menu.find('\0') != std::string::npos)
                return false;
        }
        return true;
    }

    bool SV_WriteWeaponConfigStrings(
        MsgWriter &message,
        const SvGameState &gameState)
    {
        // CODREF(sv_send_client_gamestate): CODOL parses simple then modular
        // weapon tables after raw dynamic configstrings.
        if (!SV_ValidateGameState(gameState))
            return false;
        writeWeaponConfigStringTable(
            message,
            gameState.simpleWeaponConfigStrings,
            SimpleWeaponTableCountBits,
            [](MsgWriter &writer, const std::uint16_t weaponAssetIndex) {
                writer.MSG_WriteBits(weaponAssetIndex, WeaponIndexBits);
            });
        writeWeaponConfigStringTable(
            message,
            gameState.modularWeaponConfigStrings,
            ModularWeaponTableCountBits,
            [](MsgWriter &writer, const SvModularWeaponConfigString &configString) {
                SV_WriteModularWeaponConfigStringValue(writer, configString);
            });
        return !message.overflowed();
    }

    void SV_WriteModularWeaponConfigStringValue(
        MsgWriter &message,
        const SvModularWeaponConfigString &configString)
    {
        message.MSG_WriteBits(
            configString.baseWeaponAssetIndex, WeaponIndexBits);
        message.MSG_WriteBits(configString.value8, ModularValue8Bits);
        message.MSG_WriteBits(configString.optionalValue9 ? 1 : 0, 1);
        if (configString.optionalValue9)
        {
            message.MSG_WriteBits(
                configString.optionalValue9, ModularValue9Bits);
        }
        message.MSG_WriteBits(
            static_cast<std::int32_t>(
                configString.attachmentAssetIndexes.size()),
            AttachmentCountBits);
        for (const auto attachmentAssetIndex :
            configString.attachmentAssetIndexes)
        {
            message.MSG_WriteBits(attachmentAssetIndex, AttachmentIndexBits);
        }
    }

    void SV_WriteWeaponConfigStringUpdateCommand(
        MsgWriter &message,
        const std::uint16_t weaponAssetIndex,
        const SvModularWeaponConfigString &configString)
    {
        // VERB then a BIT-ALIGNED payload. out.exe's dispatcher (sub_614AC0)
        // consumes the leading byte and hands the reader (sub_612640) a cursor at
        // byte 1, so the first bit written here is the first bit read there. The
        // 'J'/'K' scoreboard patches prove this framing on the same channel.
        message.MSG_WriteByte(WeaponConfigStringUpdateVerb);
        // bit==1 selects the high updatable range (base 5960); the 11-bit field is
        // then the index MINUS that base, which equals the weapon asset index.
        message.MSG_WriteBits(1, 1);
        message.MSG_WriteBits(weaponAssetIndex, WeaponIndexBits);
        SV_WriteModularWeaponConfigStringValue(message, configString);
    }

    bool SV_WriteGameState(
        MsgWriter &message,
        const SvGameState &gameState,
        const std::uint32_t clientNum,
        const std::uint32_t reliableSequence)
    {
        // CODREF(sv_send_client_gamestate): CODOL owns eighteen client slots,
        // numbered 0..17. PlayerNameConfigStringCount is the matching local
        // configstring domain; 18 itself is not a valid client number.
        if (clientNum >= PlayerNameConfigStringCount ||
            !SV_ValidateGameState(gameState))
            return false;

        // CODREF(sv_send_client_gamestate): CODOL client parsing fixes this
        // exact order. BO1 0x00708860 and Ghosts 0x1401F49C0 confirm the same
        // producer responsibilities but use generation-specific command ids
        // and extra sections that must not be copied into this wire format.
        message.MSG_WriteByte(ServerCommandGameState);
        message.MSG_WriteLong(reliableSequence);
        message.MSG_WriteString(gameState.mapName);
        message.MSG_WriteString(gameState.gameType);
        message.MSG_WriteLong(gameState.configStringChecksum);

        message.MSG_WriteByte(ServerCommandConfigString);
        message.MSG_WriteShort(static_cast<std::uint16_t>(gameState.configStrings.size()));
        auto previous = -1;
        for (const auto &[index, value] : gameState.configStrings)
        {
            const auto sequential = static_cast<int>(index) == previous + 1;
            message.MSG_WriteBits(sequential ? 1 : 0, 1);
            if (!sequential)
                message.MSG_WriteBits(index, ConfigStringIndexBits);
            message.MSG_WriteString(value);
            previous = index;
        }

        if (!SV_WriteWeaponConfigStrings(message, gameState))
            return false;
        message.MSG_WriteByte(ServerCommandEof);
        message.MSG_WriteLong(clientNum);
        message.MSG_WriteLong(gameState.checksumFeed);
        message.MSG_WriteByte(ServerCommandEof);
        // TODO(CODOL): append recovered baseline and mode-owned dynamic scene
        // sections only after their exact 3.3.3.3 client commands and payloads
        // are closed. BO1/Ghosts section ordering is reference evidence only.
        return !message.overflowed();
    }
}
