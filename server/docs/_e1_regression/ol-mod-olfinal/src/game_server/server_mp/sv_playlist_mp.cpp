#include "sv_playlist_mp.hpp"

#include <algorithm>
#include <array>
#include <charconv>
#include <limits>
#include <string>
#include <vector>

namespace CodolGameServer
{
    namespace
    {
        std::string_view trim(const std::string_view value)
        {
            const auto first = value.find_first_not_of(" \t\r");
            if (first == std::string_view::npos)
                return {};
            const auto last = value.find_last_not_of(" \t\r");
            return value.substr(first, last - first + 1);
        }

        std::optional<std::uint32_t> parseU32(const std::string_view value)
        {
            std::uint32_t result{};
            const auto parsed = std::from_chars(
                value.data(), value.data() + value.size(), result);
            if (parsed.ec != std::errc{} || parsed.ptr != value.data() + value.size())
                return std::nullopt;
            return result;
        }

        bool validName(const std::string_view value)
        {
            return !value.empty() && std::ranges::all_of(value, [](const unsigned char character) {
                return character == '_' || character >= '0' && character <= '9' ||
                    character >= 'A' && character <= 'Z' ||
                    character >= 'a' && character <= 'z';
            });
        }

        std::optional<std::pair<std::string_view, std::string_view>> parseCommandToken(
            const std::string_view token)
        {
            const auto separator = token.find_first_of(" \t");
            if (separator == std::string_view::npos)
                return std::nullopt;
            const auto name = trim(token.substr(0, separator));
            const auto value = trim(token.substr(separator + 1));
            if (name.empty() || value.empty())
                return std::nullopt;
            return std::pair{ name, value };
        }
    }

    std::optional<SvPlaylistDocument> SV_ParsePlaylistDocument(const std::string_view text)
    {
        return OlMod::CodolPlaylist::parse(text);
    }

    std::string_view SV_EngineGameType(const std::string_view bookingToken)
    {
        return OlMod::CodolPlaylist::engineGameType(bookingToken);
    }

    std::string_view SV_BookingTokenForGameType(const std::string_view gameType)
    {
        return OlMod::CodolPlaylist::bookingToken(gameType);
    }

    std::optional<SvBookingCommand> SV_ParseBookingCommand(const std::string_view command)
    {
        // Both grammars are a `mmstart `-prefixed, semicolon-separated command
        // list. Split them the same way and decide which one it is from what
        // turned up, rather than committing to a shape up front.
        std::vector<std::pair<std::string_view, std::string_view>> pairs;
        bool sawReset = false;
        bool sawMmstart = false;
        std::size_t cursor{};
        bool first = true;
        while (cursor <= command.size())
        {
            const auto end = command.find(';', cursor);
            auto token = trim(command.substr(
                cursor,
                end == std::string_view::npos ? command.size() - cursor : end - cursor));
            cursor = end == std::string_view::npos ? command.size() + 1 : end + 1;
            if (token.empty())
                continue;
            if (first)
            {
                first = false;
                if (!token.starts_with("mmstart "))
                    return std::nullopt;
                sawMmstart = true;
                token = trim(token.substr(8));
                if (token == "sv_resetServer")
                {
                    sawReset = true;
                    continue;
                }
            }
            const auto parsedToken = parseCommandToken(token);
            if (!parsedToken)
                continue;
            pairs.emplace_back(*parsedToken);
        }
        if (!sawMmstart)
            return std::nullopt;

        const auto lookup = [&pairs](const std::string_view name)
            -> std::optional<std::string_view> {
            std::optional<std::string_view> found;
            for (const auto &[key, value] : pairs)
            {
                if (key != name)
                    continue;
                if (found)
                    return std::nullopt;      // a repeated name is malformed
                found = value;
            }
            return found;
        };
        const auto number = [&lookup](const std::string_view name)
            -> std::optional<std::uint32_t> {
            const auto text = lookup(name);
            return text ? parseU32(*text) : std::nullopt;
        };

        const auto mapName = lookup("map");
        const auto gameType = lookup("g_gametype");
        if (mapName && gameType)
        {
            // CODOL's own form. 2486/2481/2489/2500/2483 are numeric dvar ids;
            // only the two that also appear in 3.3.3.3's form are read, and
            // even those are not assumed to mean the same thing -- nothing
            // downstream uses them, and the map and gametype below are the
            // payload. Do not name the others without deriving them.
            if (!validName(*mapName) || !validName(*gameType))
                return std::nullopt;
            SvBookingCommand parsed{};
            if (const auto playerCount = number("2486"))
                parsed.playerCount = *playerCount;
            if (const auto maxPlayers = number("2481"))
                parsed.maxPlayers = *maxPlayers;
            if (const auto privateMatch = number("2489"))
                parsed.privateMatch = *privateMatch;
            parsed.mapName = std::string(*mapName);
            parsed.gameType = std::string(*gameType);
            return parsed;
        }

        // 3.3.3.3's form: a leading sv_resetServer and five required names.
        if (!sawReset)
            return std::nullopt;
        const auto playerCount = number("2486");
        const auto maxPlayers = number("3265");
        const auto privateMatch = number("2489");
        const auto playlistId = number("playlist");
        const auto rotationIndex = number("start_map_rotate_once");
        if (!playerCount || !maxPlayers || !privateMatch || !playlistId || !rotationIndex)
            return std::nullopt;
        SvBookingCommand parsed{};
        parsed.playerCount = *playerCount;
        parsed.maxPlayers = *maxPlayers;
        parsed.privateMatch = *privateMatch;
        parsed.playlistId = *playlistId;
        parsed.rotationIndex = *rotationIndex;
        parsed.hasPlaylistId = true;
        parsed.hasRotationIndex = true;
        return parsed;
    }

    std::optional<SvResolvedBooking> SV_ResolveBooking(
        const std::string_view command,
        const SvPlaylistDocument &playlists)
    {
        return SV_ResolveBooking(command, playlists, std::nullopt);
    }

    std::optional<SvResolvedBooking> SV_ResolveBooking(
        const std::string_view command,
        SvPlaylistEntry authoritativeSelection)
    {
        const auto parsed = SV_ParseBookingCommand(command);
        if (!parsed || !validName(authoritativeSelection.mapName) ||
            !validName(authoritativeSelection.gameType) ||
            !authoritativeSelection.weight)
        {
            return std::nullopt;
        }
        return SvResolvedBooking{
            .command = *parsed,
            .rotation = std::move(authoritativeSelection),
        };
    }

    std::optional<SvResolvedBooking> SV_ResolveBooking(
        const std::string_view command,
        const SvPlaylistDocument &playlists,
        std::optional<SvPlaylistEntry> nativeSelection)
    {
        const auto parsed = SV_ParseBookingCommand(command);
        if (!parsed)
            return std::nullopt;
        // When the command names the map and the gametype outright there is
        // nothing to look up: that IS the rotation entry, and consulting a
        // playlist id the command never carried would be inventing one.
        if (!parsed->mapName.empty() && !parsed->gameType.empty())
        {
            return SvResolvedBooking{
                .command = *parsed,
                .rotation = SvPlaylistEntry{
                    .mapName = parsed->mapName,
                    .gameType = parsed->gameType,
                    .weight = 1,
                },
            };
        }
        const auto *playlist = playlists.find(parsed->playlistId);
        if (playlist && parsed->rotationIndex < playlist->rotation.size())
        {
            return SvResolvedBooking{
                .command = *parsed,
                .rotation = playlist->rotation[parsed->rotationIndex],
            };
        }
        return nativeSelection
            ? SV_ResolveBooking(command, std::move(*nativeSelection))
            : std::nullopt;
    }

    void SvPendingBooking::assign(
        SvPlaylistEntry rotation,
        const std::uint32_t initialConfigStringChecksum,
        const SvConfigStringGenerationRequirement generationRequirement)
    {
        rotation_ = std::move(rotation);
        initialConfigStringChecksum_ = initialConfigStringChecksum;
        generationRequirement_ = generationRequirement;
        sawReset_ = false;
    }

    std::optional<SvReadyBooking> SvPendingBooking::observeConfigStrings(
        const bool initialized,
        const std::uint32_t checksum,
        const bool allowReady)
    {
        if (!rotation_)
            return std::nullopt;
        if (!initialized || !checksum)
        {
            sawReset_ = true;
            return std::nullopt;
        }
        if (!allowReady)
            return std::nullopt;
        if (generationRequirement_ ==
                SvConfigStringGenerationRequirement::NewGeneration &&
            !sawReset_ && initialConfigStringChecksum_ &&
            checksum == initialConfigStringChecksum_)
        {
            return std::nullopt;
        }
        SvReadyBooking ready{
            .rotation = *rotation_,
            .configStringChecksum = checksum,
        };
        return ready;
    }

    bool SvPendingBooking::commit(const SvReadyBooking &ready)
    {
        if (!rotation_ || *rotation_ != ready.rotation)
            return false;
        rotation_.reset();
        return true;
    }

    void SvPendingBooking::cancel()
    {
        rotation_.reset();
        initialConfigStringChecksum_ = 0;
        sawReset_ = false;
    }

    bool SvPendingBooking::pending() const
    {
        return rotation_.has_value();
    }
}
