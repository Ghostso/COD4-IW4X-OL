#pragma once

#include "../../shared/CodolPlaylist.hpp"

#include <cstdint>
#include <optional>
#include <string>
#include <string_view>
#include <vector>

namespace CodolGameServer
{
    using SvPlaylistEntry = OlMod::CodolPlaylist::RotationEntry;
    using SvPlaylist = OlMod::CodolPlaylist::Playlist;
    using SvPlaylistDocument = OlMod::CodolPlaylist::Document;

    // CODOL sends TWO booking grammars and this build's is not 3.3.3.3's.
    //
    //   3.3.3.3  mmstart sv_resetServer; 2486 1; 3265 12; 2489 0;
    //            playlist 26; start_map_rotate_once 0
    //   CODOL    mmstart 2486 1; 2481 18; 2489 1; 2500 0;
    //            g_gametype war; 2483 1; map mp_bloc
    //
    // The second is MEASURED, not inferred: it is the literal instant-message
    // verb in re/alpha0022/dw-capture-*.log, several sessions, with 2481
    // varying (12, 18) while the rest hold. It carries NO playlist id and NO
    // rotation index -- it names the map and the gametype outright, which is
    // strictly better evidence than an index into a rotation this server would
    // then have to look up. So those two fields are optional, and a consumer
    // must ask whether they are present rather than compare a defaulted zero.
    struct SvBookingCommand
    {
        std::uint32_t playerCount{};
        std::uint32_t maxPlayers{};
        std::uint32_t privateMatch{};
        std::uint32_t playlistId{};
        std::uint32_t rotationIndex{};
        bool hasPlaylistId{};
        bool hasRotationIndex{};
        // empty unless the command named them outright
        std::string mapName;
        std::string gameType;
    };

    struct SvResolvedBooking
    {
        SvBookingCommand command;
        SvPlaylistEntry rotation;
    };

    struct SvReadyBooking
    {
        SvPlaylistEntry rotation;
        std::uint32_t configStringChecksum{};
    };

    enum class SvConfigStringGenerationRequirement
    {
        NewGeneration,
        CurrentGeneration,
    };

    class SvPendingBooking
    {
    public:
        void assign(
            SvPlaylistEntry rotation,
            std::uint32_t initialConfigStringChecksum,
            SvConfigStringGenerationRequirement generationRequirement =
                SvConfigStringGenerationRequirement::NewGeneration);
        [[nodiscard]] std::optional<SvReadyBooking> observeConfigStrings(
            bool initialized,
            std::uint32_t checksum,
            bool allowReady = true);
        [[nodiscard]] bool commit(const SvReadyBooking &ready);
        void cancel();
        [[nodiscard]] bool pending() const;

    private:
        std::optional<SvPlaylistEntry> rotation_;
        std::uint32_t initialConfigStringChecksum_{};
        SvConfigStringGenerationRequirement generationRequirement_{
            SvConfigStringGenerationRequirement::NewGeneration };
        bool sawReset_{};
    };

    [[nodiscard]] std::optional<SvPlaylistDocument> SV_ParsePlaylistDocument(
        std::string_view text);
    // Booking token -> engine gametype (ffa -> dm, tdm -> war, kc -> conf), and
    // back. Anything unlisted is returned unchanged. See the table in the .cpp
    // for where each pair was read from.
    [[nodiscard]] std::string_view SV_EngineGameType(std::string_view bookingToken);
    [[nodiscard]] std::string_view SV_BookingTokenForGameType(std::string_view gameType);
    [[nodiscard]] std::optional<SvBookingCommand> SV_ParseBookingCommand(
        std::string_view command);
    [[nodiscard]] std::optional<SvResolvedBooking> SV_ResolveBooking(
        std::string_view command,
        const SvPlaylistDocument &playlists);
    [[nodiscard]] std::optional<SvResolvedBooking> SV_ResolveBooking(
        std::string_view command,
        SvPlaylistEntry authoritativeSelection);
    [[nodiscard]] std::optional<SvResolvedBooking> SV_ResolveBooking(
        std::string_view command,
        const SvPlaylistDocument &playlists,
        std::optional<SvPlaylistEntry> nativeSelection);
}
