#pragma once

#include <cstdint>
#include <optional>
#include <string>
#include <string_view>
#include <vector>

namespace OlMod::CodolPlaylist
{
    struct Rule
    {
        std::string name;
        std::string value;

        bool operator==(const Rule &) const = default;
    };

    struct RotationEntry
    {
        std::string mapName;
        std::string gameType;
        std::uint32_t weight{};

        bool operator==(const RotationEntry &) const = default;
    };

    struct Playlist
    {
        std::uint32_t id{};
        std::vector<Rule> rules;
        std::vector<RotationEntry> rotation;
    };

    struct Document
    {
        std::uint32_t version{};
        std::vector<Playlist> playlists;

        [[nodiscard]] const Playlist *find(std::uint32_t playlistId) const;
    };

    [[nodiscard]] std::optional<Document> parse(std::string_view text);
    [[nodiscard]] std::optional<std::string_view> findRule(
        const Playlist &playlist,
        std::string_view name);

    // A rotation entry names what the client BOOKS. For three modes the engine
    // gametype is a different string, and it is the engine name that every
    // derived name is built from - g_gametype, mp_<x>_spawn, scr_<x>_* and the
    // shipped per-gametype assets.
    //
    // CODREF, three independent sources in the shipped 3.3.3.3 install:
    //  - 262 mp_constbaselines_bl_pc_<map>_<gametype>.bin rawfiles across the
    //    fastfiles name dm (25 maps), war (23) and conf (24). None is named ffa,
    //    tdm or kc.
    //  - every playlist whose rotation says tdm declares scr_war_scorelimit and
    //    scr_war_timelimit (e.g. playlist 30, "Ground War").
    //  - the retail demo C-2021-7-25[1-19-26]dm.demo carries serverinfo
    //    \g_gametype\dm on mp_cross_fire, which is entry [3] of playlist 23's ffa
    //    rotation.
    //
    // These are the stock IW names - dm.gsc is free-for-all and war.gsc is team
    // deathmatch in CoD4/MW2/MW3 - kept underneath CODOL's booking vocabulary.
    // Anything unlisted is returned unchanged, and both directions are total, so
    // callers can normalise without knowing which vocabulary they were handed.
    [[nodiscard]] std::string_view engineGameType(std::string_view bookingToken);
    [[nodiscard]] std::string_view bookingToken(std::string_view gameType);
}
