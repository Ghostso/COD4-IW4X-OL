#include "CodolPlaylist.hpp"

#include <algorithm>
#include <array>
#include <charconv>
#include <utility>

namespace OlMod::CodolPlaylist
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

        std::optional<RotationEntry> parseRotationEntry(const std::string_view line)
        {
            const auto firstComma = line.find(',');
            if (firstComma == std::string_view::npos)
                return std::nullopt;
            const auto secondComma = line.find(',', firstComma + 1);
            if (secondComma == std::string_view::npos ||
                line.find(',', secondComma + 1) != std::string_view::npos)
            {
                return std::nullopt;
            }

            const auto mapName = trim(line.substr(0, firstComma));
            const auto gameType = trim(line.substr(firstComma + 1, secondComma - firstComma - 1));
            const auto weight = parseU32(trim(line.substr(secondComma + 1)));
            if (!validName(mapName) || !validName(gameType) || !weight || !*weight)
                return std::nullopt;
            return RotationEntry{
                .mapName = std::string(mapName),
                .gameType = std::string(gameType),
                .weight = *weight,
            };
        }

        // See the header for where each pair was read from.
        using BookingTokenGameType = std::pair<std::string_view, std::string_view>;
        constexpr std::array<BookingTokenGameType, 3> BookingTokenGameTypes{ {
            { "ffa", "dm" },
            { "tdm", "war" },
            { "kc", "conf" },
        } };

        std::optional<Rule> parseRule(const std::string_view value)
        {
            const auto separator = value.find_first_of(" \t");
            if (separator == std::string_view::npos)
                return std::nullopt;
            const auto name = trim(value.substr(0, separator));
            const auto ruleValue = trim(value.substr(separator + 1));
            if (!validName(name) || ruleValue.empty())
                return std::nullopt;
            return Rule{ std::string(name), std::string(ruleValue) };
        }
    }

    const Playlist *Document::find(const std::uint32_t playlistId) const
    {
        const auto found = std::ranges::find(playlists, playlistId, &Playlist::id);
        return found == playlists.end() ? nullptr : &*found;
    }

    std::optional<Document> parse(const std::string_view text)
    {
        Document result;
        Playlist *current{};
        std::size_t cursor{};
        while (cursor <= text.size())
        {
            const auto end = text.find('\n', cursor);
            const auto line = trim(text.substr(
                cursor,
                end == std::string_view::npos ? text.size() - cursor : end - cursor));
            cursor = end == std::string_view::npos ? text.size() + 1 : end + 1;
            if (line.empty() || line.starts_with("//"))
                continue;

            const auto separator = line.find_first_of(" \t");
            const auto keyword = line.substr(0, separator);
            const auto value = separator == std::string_view::npos
                ? std::string_view{}
                : trim(line.substr(separator + 1));
            if (keyword == "version")
            {
                const auto version = parseU32(value);
                if (!version)
                    return std::nullopt;
                result.version = *version;
                continue;
            }
            if (keyword == "playlist")
            {
                const auto id = parseU32(value);
                if (!id || result.find(*id))
                    return std::nullopt;
                result.playlists.push_back(Playlist{ .id = *id });
                current = &result.playlists.back();
                continue;
            }
            if (!current)
                continue;
            if (keyword == "rule")
            {
                if (const auto rule = parseRule(value))
                    current->rules.push_back(*rule);
                continue;
            }
            if (const auto entry = parseRotationEntry(line))
                current->rotation.push_back(*entry);
        }
        if (!result.version || result.playlists.empty())
            return std::nullopt;
        return result;
    }

    std::string_view engineGameType(const std::string_view bookingToken)
    {
        const auto found = std::ranges::find(
            BookingTokenGameTypes, bookingToken, &BookingTokenGameType::first);
        return found == BookingTokenGameTypes.end() ? bookingToken : found->second;
    }

    std::string_view bookingToken(const std::string_view gameType)
    {
        const auto found = std::ranges::find(
            BookingTokenGameTypes, gameType, &BookingTokenGameType::second);
        return found == BookingTokenGameTypes.end() ? gameType : found->first;
    }

    std::optional<std::string_view> findRule(
        const Playlist &playlist,
        const std::string_view name)
    {
        const auto found = std::ranges::find(playlist.rules, name, &Rule::name);
        return found == playlist.rules.end()
            ? std::nullopt
            : std::optional<std::string_view>{ found->value };
    }
}
