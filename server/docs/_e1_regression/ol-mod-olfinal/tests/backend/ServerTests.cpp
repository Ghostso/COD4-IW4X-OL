#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <WinSock2.h>

#include "Servers.hpp"
#include "DedicatedBookingDispatcher.hpp"
#include "SharedRoomSessionOwner.hpp"
#include "SharedRoomControl.hpp"
#include "SharedRoomClient.hpp"
#include "Demonware/Auth3ClientPatches.hpp"
#include "Demonware/CodolClientPatches.hpp"
#include "shared/CodolPlaylist.hpp"
#include "shared/DedicatedSession.hpp"
#include "shared/RuntimeLog.hpp"

#include <array>
#include <chrono>
#include <condition_variable>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <mutex>
#include <optional>
#include <string_view>
#include <vector>

namespace
{
    void require(const bool condition, const std::string_view message)
    {
        if (!condition)
        {
            std::cerr << "FAILED: " << message << '\n';
            std::exit(1);
        }
    }

    void testHostnameClassification()
    {
        using AlwaysofflineRe::ServerKind;
        using AlwaysofflineRe::classifyHostname;

        require(classifyHostname("example.com") == ServerKind::none, "unrelated host");
        require(classifyHostname("stun.eu.demonware.net") == ServerKind::stun, "original STUN host");
        require(classifyHostname("stun1-prod.codol.qq.com") == ServerKind::stun, "CODOL STUN host");
        require(classifyHostname("auth3.codol.qq.com") == ServerKind::auth3, "Auth3 host");
        require(classifyHostname("auth.codol.qq.com") == ServerKind::legacyAuth, "legacy Auth host");
        require(classifyHostname("cs.codol.qq.com") == ServerKind::content, "content host");
        require(classifyHostname("lsg.codol.qq.com") == ServerKind::lobby, "LSG host");
        require(classifyHostname("glutton.codol.qq.com") == ServerKind::none, "unimplemented original glutton branch");
    }

    void testRuntimeConsoleSwitch()
    {
        _putenv_s("OLMOD_CONSOLE_LOG", "");
        require(!OlMod::RuntimeLog::consoleEnabled(),
            "runtime console is opt-in outside the launcher");
        _putenv_s("OLMOD_CONSOLE_LOG", "0");
        require(!OlMod::RuntimeLog::consoleEnabled(),
            "runtime console rejects a disabled value");
        _putenv_s("OLMOD_CONSOLE_LOG", "TRUE");
        require(OlMod::RuntimeLog::consoleEnabled(),
            "runtime console accepts a case-insensitive enabled value");
        _putenv_s("OLMOD_CONSOLE_LOG", "");
    }

    void testFactoryLifetime()
    {
        AlwaysofflineRe::ServerFactory factory;
        require(factory.create("auth.codol.qq.com") == factory.create("auth2.auth.codol.qq.com"),
            "legacy Auth is a singleton");
        require(factory.create("lsg.codol.qq.com") == factory.create("lobby.codol.qq.com"),
            "LSG/lobby is a singleton");
        require(factory.create("auth3.a.codol.qq.com") == factory.create("auth3.a.codol.qq.com"),
            "HTTP server is retained per host");
        require(factory.create("auth3.a.codol.qq.com") != factory.create("auth3.b.codol.qq.com"),
            "HTTP hosts have separate TLS state");
    }

    void testStunBinding()
    {
        AlwaysofflineRe::StunServer server;
        IServer::Endpoints endpoints{};
        endpoints.client.ipv4 = htonl(0x0A010203);
        endpoints.client.port = htons(3074);
        endpoints.server.ipv4 = htonl(0xCB007109);
        endpoints.server.port = htons(3075);

        constexpr std::array<std::uint8_t, 4> natRequest{ 0x14, 0x02, 0x00, 0x00 };
        require(server.onPacketwrite(natRequest.data(), static_cast<std::uint32_t>(natRequest.size()), &endpoints),
            "DW STUN type-20 request accepted");
        std::array<std::uint8_t, 64> response{};
        std::uint32_t responseSize = static_cast<std::uint32_t>(response.size());
        require(server.onPacketread(response.data(), &responseSize), "DW STUN type-21 response available");
        constexpr std::array<std::uint8_t, 15> ExpectedNatResponse{
            0x15, 0x02, 0x00, 0xF0, 0x00, 0x00, 0x01, 0x02, 0x0C,
            0xCB, 0x00, 0x71, 0x09, 0x03, 0x0C,
        };
        require(responseSize == ExpectedNatResponse.size() &&
            std::equal(ExpectedNatResponse.begin(), ExpectedNatResponse.end(), response.begin()),
            "DW STUN type-21 response matches archived bytes");

        constexpr std::array<std::uint8_t, 3> addressRequest{ 0x1E, 0x03, 0x00 };
        require(server.onPacketwrite(
            addressRequest.data(), static_cast<std::uint32_t>(addressRequest.size()), &endpoints),
            "DW STUN type-30 request accepted");
        responseSize = static_cast<std::uint32_t>(response.size());
        require(server.onPacketread(response.data(), &responseSize), "DW STUN type-31 response available");
        constexpr std::array<std::uint8_t, 9> ExpectedAddressResponse{
            0x1F, 0x02, 0x00, 0xF0, 0x00, 0x00, 0x01, 0x02, 0x0C,
        };
        require(responseSize == ExpectedAddressResponse.size() &&
            std::equal(ExpectedAddressResponse.begin(), ExpectedAddressResponse.end(), response.begin()),
            "DW STUN type-31 response matches archived bytes");

        auto secondEndpoints = endpoints;
        secondEndpoints.client.port = htons(4000);
        secondEndpoints.server.ipv4 = htonl(0xC633642A);
        secondEndpoints.server.port = htons(4001);
        require(server.onPacketwrite(natRequest.data(), static_cast<std::uint32_t>(natRequest.size()), &endpoints),
            "first DW STUN burst request accepted");
        require(server.onPacketwrite(
            natRequest.data(), static_cast<std::uint32_t>(natRequest.size()), &secondEndpoints),
            "second DW STUN burst request accepted");
        responseSize = static_cast<std::uint32_t>(response.size());
        require(server.onPacketread(response.data(), &responseSize), "first DW STUN burst response available");
        require(responseSize == ExpectedNatResponse.size() &&
            std::equal(ExpectedNatResponse.begin(), ExpectedNatResponse.end(), response.begin()),
            "first DW STUN burst response preserves request order");
        responseSize = static_cast<std::uint32_t>(response.size());
        require(server.onPacketread(response.data(), &responseSize), "second DW STUN burst response available");
        constexpr std::array<std::uint8_t, 15> ExpectedSecondNatResponse{
            0x15, 0x02, 0x00, 0xF0, 0x00, 0x00, 0x01, 0xA0, 0x0F,
            0xC6, 0x33, 0x64, 0x2A, 0xA1, 0x0F,
        };
        require(responseSize == ExpectedSecondNatResponse.size() &&
            std::equal(ExpectedSecondNatResponse.begin(), ExpectedSecondNatResponse.end(), response.begin()),
            "second DW STUN burst response matches archived queue behavior");

        std::array<std::uint8_t, 20> request{
            0x00, 0x01, 0x00, 0x00,
            0x21, 0x12, 0xA4, 0x42,
            0x01, 0x02, 0x03, 0x04,
            0x05, 0x06, 0x07, 0x08,
            0x09, 0x0A, 0x0B, 0x0C,
        };
        require(server.onPacketwrite(request.data(), static_cast<std::uint32_t>(request.size()), &endpoints),
            "STUN request accepted");

        responseSize = static_cast<std::uint32_t>(response.size());
        require(server.onPacketread(response.data(), &responseSize), "STUN response available");
        require(responseSize == 32, "STUN response size");
        require(response[0] == 0x01 && response[1] == 0x01, "binding success type");
        require(response[2] == 0x00 && response[3] == 0x0C, "attribute payload length");
        require(std::equal(request.begin() + 4, request.end(), response.begin() + 4), "transaction ID preserved");
        require(response[20] == 0x00 && response[21] == 0x01, "MAPPED-ADDRESS attribute");
        require(response[26] == 0x0C && response[27] == 0x02, "mapped client port");
        require(response[28] == 0x0A && response[29] == 0x01 && response[30] == 0x02 && response[31] == 0x03,
            "mapped client address");
    }

    void testAuth3ClientPatches()
    {
        constexpr std::array<std::uint8_t, 11> call{
            0x68, 1, 2, 3, 4, 0x0F, 0x95, 0xC2, 0x52, 0x50, 0xE8,
        };
        constexpr std::array<std::uint8_t, 10> certificate{
            0x74, 5, 0x83, 0xBE, 0x78, 0x02, 0x00, 0x00, 0x00, 0x74,
        };
        constexpr std::array<std::uint8_t, 18> authentication{
            0x8B, 0x86, 6, 7, 8, 9, 0x83, 10, 11, 0x85, 0xC0, 0x0F,
            0x84, 12, 13, 14, 15, 0x68,
        };
        std::vector<std::uint8_t> image(256, 0xCC);
        std::copy(call.begin(), call.end(), image.begin() + 16);
        std::copy(certificate.begin(), certificate.end(), image.begin() + 96);
        std::copy(authentication.begin(), authentication.end(), image.begin() + 176);
        require(AlwaysofflineRe::Demonware::patchAuth3ValidationBuffer(image),
            "three unique Auth3 signatures are patched");
        require(std::all_of(image.begin() + 26, image.begin() + 31,
            [](const auto value) { return value == 0x90; }), "Auth3 certificate call is NOPed");
        require(image[96] == 0x71, "Auth3 certificate branch matches the archived patch");
        require(image[188] == 0x81, "Auth3 authentication branch matches the archived patch");

        std::vector<std::uint8_t> ambiguous(320, 0xCC);
        std::copy(call.begin(), call.end(), ambiguous.begin() + 16);
        std::copy(call.begin(), call.end(), ambiguous.begin() + 48);
        std::copy(certificate.begin(), certificate.end(), ambiguous.begin() + 128);
        std::copy(authentication.begin(), authentication.end(), ambiguous.begin() + 224);
        const auto original = ambiguous;
        require(!AlwaysofflineRe::Demonware::patchAuth3ValidationBuffer(ambiguous),
            "ambiguous Auth3 signatures are rejected");
        require(ambiguous == original, "signature rejection does not partially patch the image");
    }

    void testCodolStartupPatches()
    {
        struct Fixture
        {
            std::size_t rva;
            std::vector<std::uint8_t> original;
            std::vector<std::uint8_t> patched;
        };
        const std::array fixtures{
            Fixture{0x2422C1,
                {0x75, 0x27, 0x68, 0xDC, 0x6E, 0xC7, 0x00, 0x68},
                {0xEB, 0x27, 0x68, 0xDC, 0x6E, 0xC7, 0x00, 0x68}},
            Fixture{0x24283D,
                {0x0F, 0x85, 0x11, 0xFD, 0xFF, 0xFF, 0x68, 0x2C},
                {0xE9, 0x12, 0xFD, 0xFF, 0xFF, 0xFF, 0x68, 0x2C}},
            Fixture{0x2D2AD1, {0x75, 0x12, 0x68, 0x88}, {0xEB, 0x12, 0x68, 0x88}},
            Fixture{0x2D2B07, {0x75, 0x12, 0x68, 0xA8}, {0xEB, 0x12, 0x68, 0xA8}},
            Fixture{0x2D2B42, {0x75, 0x12, 0x68, 0xD8}, {0xEB, 0x12, 0x68, 0xD8}},
            Fixture{0x2D2B8D, {0x75, 0x4B, 0x68, 0xFC}, {0xEB, 0x4B, 0x68, 0xFC}},
            Fixture{0x2D2C18, {0x7D, 0x0F, 0x68, 0x3C}, {0xEB, 0x0F, 0x68, 0x3C}},
        };

        std::vector<std::uint8_t> image(0x2D2C20, 0xCC);
        for (const auto &fixture : fixtures)
            std::copy(fixture.original.begin(), fixture.original.end(), image.begin() + fixture.rva);
        require(AlwaysofflineRe::Demonware::patchCodolStartupBuffer(image),
            "known CODOL startup sites are patched");
        for (const auto &fixture : fixtures)
        {
            require(std::equal(fixture.patched.begin(), fixture.patched.end(), image.begin() + fixture.rva),
                "CODOL startup site matches archived patched executable");
        }
        require(AlwaysofflineRe::Demonware::patchCodolStartupBuffer(image),
            "CODOL startup patches are idempotent");

        std::vector<std::uint8_t> rejected(0x2D2C20, 0xCC);
        for (const auto &fixture : fixtures)
            std::copy(fixture.original.begin(), fixture.original.end(), rejected.begin() + fixture.rva);
        rejected[fixtures.back().rva] = 0x90;
        const auto before = rejected;
        require(!AlwaysofflineRe::Demonware::patchCodolStartupBuffer(rejected),
            "unknown CODOL startup bytes are rejected");
        require(rejected == before, "CODOL startup signature rejection does not partially patch the image");

        using AlwaysofflineRe::Demonware::shouldRequestCodolInventory;
        require(shouldRequestCodolInventory(1, 1, true, 0),
            "successful public-profile download requests startup inventory");
        require(shouldRequestCodolInventory(1, 1, false, 800),
            "missing public profile still requests startup inventory");
        require(!shouldRequestCodolInventory(1, 1, false, 1000),
            "failed public-profile download does not request inventory");
        require(!shouldRequestCodolInventory(2, 1, true, 0),
            "private-profile download does not request inventory");
        require(!shouldRequestCodolInventory(1, 2, true, 0),
            "public-profile upload does not request inventory");

        using AlwaysofflineRe::Demonware::shouldInvalidateCodolCurrentCharacterCache;
        require(shouldInvalidateCodolCurrentCharacterCache(1, 1, true, 0),
            "successful public-profile download invalidates the current-character cache");
        require(!shouldInvalidateCodolCurrentCharacterCache(2, 1, true, 0),
            "private-profile download preserves the current-character cache");
        require(!shouldInvalidateCodolCurrentCharacterCache(1, 2, true, 0),
            "public-profile upload preserves the current-character cache");
        require(!shouldInvalidateCodolCurrentCharacterCache(1, 1, false, 0),
            "unsuccessful public-profile download preserves the current-character cache");
        require(!shouldInvalidateCodolCurrentCharacterCache(1, 1, true, 800),
            "errored public-profile download preserves the current-character cache");
    }

    void testDedicatedBookingDispatcher()
    {
        using namespace AlwaysofflineRe;
        using namespace OlMod::DedicatedControl;
        using namespace OlMod::DedicatedSession;

        Demonware::AuthSession authSession;
        auto identity = authSession.snapshot();
        identity.username = "DispatcherTest";
        authSession.update(identity);

        LoadoutRequest loadout{
            .characterIndex = 3,
            .classMask = 1,
            .characterItemIds = { 545, 789, 792 },
        };
        loadout.classes[0].weapons[0] = {
            .itemId = 10001,
            .attachmentItemIds = { 20379, 20782 },
        };
        loadout.classes[0].weapons[1] = {
            .itemId = 10049,
            .attachmentItemIds = { 25684 },
        };
        const ClientSessionCapture captured{
            .booking = {
                .playlistId = 26,
                .rotationIndex = 0,
                .mapName = "mp_crash_tropical",
                .gameType = "sd",
            },
            .loadout = loadout,
        };
        const auto encodedCapture = encode(captured);
        require(!encodedCapture.empty(), "dispatcher client capture encodes");
        constexpr std::string_view PlaylistFixture = R"(
version 796
playlist 26
rule scr_cha_scorelimit 100
rule scr_cha_timelimit 20
mp_nuked,cha,1
playlist 133
rule scr_sd_roundswitch 1
rule scr_sd_roundlimit 7
rule scr_sd_winlimit 4
mp_crash_tropical,sd,1
)";
        BookingSelection chaSelection{
            .playlistId = 26,
            .rotationIndex = 0,
            .mapName = "mp_nuked",
            .gameType = "cha",
        };
        const auto resolvedRules = resolveMatchRules(PlaylistFixture, chaSelection);
        require(
            resolvedRules && resolvedRules->playlistVersion == 796 &&
                resolvedRules->scoreLimit == 100 &&
                resolvedRules->timeLimitMinutes == 20,
            "dispatcher resolves CHA rules from the exact captured playlist rotation");
        chaSelection.mapName = "mp_crash_tropical";
        require(
            !resolveMatchRules(PlaylistFixture, chaSelection) &&
                !resolveMatchRules(
                    "version 796\nplaylist 26\nmp_nuked,cha,1\n",
                    BookingSelection{
                        .playlistId = 26,
                        .rotationIndex = 0,
                        .mapName = "mp_nuked",
                        .gameType = "cha",
                    }),
            "dispatcher rejects capture/rotation mismatch and absent CHA limits");
        const BookingSelection sdSelection{
            .playlistId = 133,
            .rotationIndex = 0,
            .mapName = "mp_crash_tropical",
            .gameType = "sd",
        };
        const auto resolvedSdRules = resolveMatchRules(PlaylistFixture, sdSelection);
        require(
            resolvedSdRules && resolvedSdRules->playlistVersion == 796 &&
                resolvedSdRules->timeLimitMinutes == 2 &&
                resolvedSdRules->roundSwitch == 1 &&
                resolvedSdRules->roundLimit == 7 &&
                resolvedSdRules->winLimit == 4,
            "dispatcher resolves SD round rules and the native two-minute default");
        const auto resolvedLegacySdRules = resolveMatchRules(
            PlaylistFixture,
            BookingSelection{
                .playlistId = 999,
                .rotationIndex = 0,
                .mapName = "mp_crash_tropical",
                .gameType = "sd",
            });
        require(
            resolvedLegacySdRules == resolvedSdRules,
            "dispatcher resolves an absent legacy ID from unanimous publisher map/mode rules");
        require(
            !resolveMatchRules(
                std::string(PlaylistFixture) +
                    "playlist 134\nrule scr_sd_roundswitch 1\n"
                    "rule scr_sd_roundlimit 9\nrule scr_sd_winlimit 5\n"
                    "mp_crash_tropical,sd,1\n",
                BookingSelection{
                    .playlistId = 999,
                    .rotationIndex = 0,
                    .mapName = "mp_crash_tropical",
                    .gameType = "sd",
                }),
            "dispatcher rejects conflicting publisher rules for an absent legacy ID");
        require(
            resolveMatchRules(
                std::string(PlaylistFixture) +
                    "playlist 134\nmp_crash_tropical,sd,1\n",
                BookingSelection{
                    .playlistId = 999,
                    .rotationIndex = 0,
                    .mapName = "mp_crash_tropical",
                    .gameType = "sd",
                }) == resolvedSdRules,
            "dispatcher ignores rotation-only candidates when complete legacy rules agree");

        // Free-for-all is the one shipped mode whose playlists declare no scr_*
        // rule at all - playlist 23 ("Free For All") and 154 ("Snipers Only")
        // carry only numeric rules - so a rule-less rotation has to resolve
        // rather than fail the way a rule-less cha rotation does above.
        const BookingSelection ffaSelection{
            .playlistId = 23,
            .rotationIndex = 3,
            .mapName = "mp_cross_fire",
            .gameType = "ffa",
        };
        const auto resolvedFfaRules = resolveMatchRules(
            std::string(PlaylistFixture) +
                "playlist 23\nmp_afghan,ffa,1\nmp_cargoship,ffa,1\n"
                "mp_crash_tropical,ffa,1\nmp_cross_fire,ffa,1\n",
            ffaSelection);
        require(
            resolvedFfaRules && resolvedFfaRules->playlistVersion == 796 &&
                resolvedFfaRules->scoreLimit == 30 &&
                // OLMOD(ffa-test-limits): 60, not the retail 10, while this
                // branch is under development. The retail value is recorded in
                // the dispatcher's TODO(CODOL) alongside the demo configstring
                // it came from.
                resolvedFfaRules->timeLimitMinutes == 60 &&
                !resolvedFfaRules->roundSwitch && !resolvedFfaRules->roundLimit &&
                !resolvedFfaRules->winLimit,
            "dispatcher gives a rule-less FFA rotation the gametype's own score "
            "default and the development time limit");

        // The booking token and the engine gametype are different strings, and
        // valid() is reached from both sides. Assert the mapping and that the
        // validator answers the same for either spelling - the failure of it not
        // doing so is silent, because an unrecognised name is accepted wholesale.
        require(
            OlMod::CodolPlaylist::engineGameType("ffa") == "dm" &&
                OlMod::CodolPlaylist::engineGameType("tdm") == "war" &&
                OlMod::CodolPlaylist::engineGameType("kc") == "conf" &&
                OlMod::CodolPlaylist::engineGameType("sd") == "sd" &&
                OlMod::CodolPlaylist::bookingToken("dm") == "ffa" &&
                OlMod::CodolPlaylist::bookingToken("war") == "tdm" &&
                OlMod::CodolPlaylist::bookingToken("cha") == "cha",
            "booking tokens map to their engine gametypes in both directions");
        require(
            valid(*resolvedFfaRules, "ffa") && valid(*resolvedFfaRules, "dm") &&
                !valid(MatchRules{ .playlistVersion = 796, .timeLimitMinutes = 10 }, "dm") &&
                !valid(MatchRules{ .playlistVersion = 796, .scoreLimit = 30 }, "ffa"),
            "FFA rules validate under either spelling and reject a missing limit");

        // A live client booked playlist 11 - an id absent from the publisher file -
        // and the whole selection was refused. The resolver has to normalise the
        // gametype too: rotation entries are written in the booking vocabulary, so
        // an engine name matches no rotation, and the consensus path then finds no
        // candidate playlist at all. That is indistinguishable from "no playlist
        // offers this mode", which is why it presented as a bare rejection.
        const auto ffaFixture =
            std::string(PlaylistFixture) +
            "playlist 23\nmp_afghan,ffa,1\nmp_cargoship,ffa,1\n"
            "mp_crash_tropical,ffa,1\nmp_cross_fire,ffa,1\n";
        auto engineNameSelection = ffaSelection;
        engineNameSelection.gameType = "dm";
        require(
            resolveMatchRules(ffaFixture, engineNameSelection) == resolvedFfaRules,
            "a selection carrying the engine gametype resolves the same as the booking token");
        auto absentIdSelection = engineNameSelection;
        absentIdSelection.playlistId = 11;
        require(
            resolveMatchRules(ffaFixture, absentIdSelection) == resolvedFfaRules,
            "an absent playlist id still resolves FFA through the consensus path");

        std::mutex mutex;
        std::condition_variable ready;
        std::vector<std::pair<MessageType, std::uint64_t>> requests;
        std::vector<SessionStart> sessions;
        std::vector<SessionMember> loadoutUpdates;
        std::vector<std::vector<std::uint32_t>> entitlementRequests;
        std::size_t entitlementChecks{};
        std::size_t acceptedDiagnostics{};
        std::size_t rejectedDiagnostics{};
        std::size_t captureCalls{};

        DedicatedBookingDispatcher dispatcher(
            authSession,
            [&](const std::uint64_t userId,
                const std::span<const std::uint32_t> items) {
                std::lock_guard lock(mutex);
                require(userId == authSession.snapshot().userId,
                    "single-member dispatcher checks the authenticated XUID");
                require(!items.empty(), "dispatcher validates a non-empty entitlement set");
                entitlementRequests.emplace_back(items.begin(), items.end());
                return entitlementChecks++ != 1;
            },
            {},
            [](const BookingSelection &selection) {
                return std::optional{ MatchRules{
                    .playlistVersion = 796,
                    .scoreLimit = selection.gameType == "cha" ? 100u : 0u,
                    .timeLimitMinutes = selection.gameType == "cha" ? 20u : 0u,
                    .roundSwitch = selection.gameType == "sd" ? 1u : 0u,
                    .roundLimit = selection.gameType == "sd" ? 7u : 0u,
                    .winLimit = selection.gameType == "sd" ? 4u : 0u,
                } };
            },
            [&](const std::uint32_t,
                const std::uint16_t,
                const Message &message,
                const std::uint32_t) {
                std::lock_guard lock(mutex);
                requests.emplace_back(message.type, message.requestId);
                if (message.type == MessageType::CaptureLoadout)
                {
                    if (captureCalls++ == 0)
                    {
                        return SubmitResult{
                            .delivered = true,
                            .status = ResponseStatus::Rejected,
                            .requestId = message.requestId,
                        };
                    }
                    return SubmitResult{
                        .delivered = true,
                        .status = ResponseStatus::Accepted,
                        .requestId = message.requestId,
                        .payload = std::string(
                            reinterpret_cast<const char *>(encodedCapture.data()),
                            encodedCapture.size()),
                    };
                }
                if (message.type == MessageType::UpdateLoadout)
                {
                    require(message.payload.size() >= sizeof(std::uint64_t),
                        "loadout refresh carries its member XUID");
                    std::uint64_t userId{};
                    std::memcpy(&userId, message.payload.data(), sizeof(userId));
                    const auto updated = decodeLoadout({
                        reinterpret_cast<const std::uint8_t *>(
                            message.payload.data()) + sizeof(userId),
                        message.payload.size() - sizeof(userId),
                    });
                    require(updated.has_value(),
                        "dedicated receives a valid UpdateLoadout payload");
                    loadoutUpdates.push_back({
                        .userId = userId,
                        .loadout = *updated,
                    });
                    return SubmitResult{
                        .delivered = true,
                        .status = ResponseStatus::Rejected,
                        .requestId = message.requestId,
                    };
                }
                const auto decoded = decodeSessionStart({
                    reinterpret_cast<const std::uint8_t *>(message.payload.data()),
                    message.payload.size(),
                });
                require(decoded.has_value(), "dedicated receives a valid SessionStart payload");
                sessions.push_back(*decoded);
                return SubmitResult{
                    .delivered = true,
                    .status = ResponseStatus::Accepted,
                    .requestId = message.requestId,
                };
            },
            [&](const std::string_view message) {
                {
                    std::lock_guard lock(mutex);
                    if (message.starts_with("CODOL_GAME_SESSION accepted=true request_id="))
                        ++acceptedDiagnostics;
                    if (message.starts_with(
                            "CODOL_GAME_SESSION entitlement_rejected request_id="))
                        ++rejectedDiagnostics;
                }
                ready.notify_all();
            });

        require(dispatcher.submit("mmstart first") &&
            dispatcher.submit("mmstart rejected") &&
            dispatcher.submit("mmstart third"),
            "dispatcher queues bounded booking work");
        {
            std::unique_lock lock(mutex);
            require(ready.wait_for(lock, std::chrono::seconds(2), [&] {
                return acceptedDiagnostics == 2 && rejectedDiagnostics == 1;
            }), "dispatcher retries a transient capture and completes accepted and rejected bookings");

            require(requests == std::vector<std::pair<MessageType, std::uint64_t>>{
                    { MessageType::CaptureLoadout, 1 },
                    { MessageType::CaptureLoadout, 1 },
                    { MessageType::UpdateLoadout, 1 },
                    { MessageType::SessionStart, 1 },
                    { MessageType::CaptureLoadout, 2 },
                    { MessageType::CaptureLoadout, 3 },
                    { MessageType::UpdateLoadout, 3 },
                    { MessageType::SessionStart, 3 },
                },
                "dispatcher retries capture with the same ID and assigns one increasing ID per booking transaction");
            require(sessions.size() == 2 &&
                sessions[0].members.size() == 1 &&
                sessions[0].members[0].username == "DispatcherTest" &&
                sessions[0].bookingCommand == "mmstart first" &&
                sessions[1].bookingCommand == "mmstart third" &&
                sessions[0].booking == captured.booking &&
                sessions[1].booking == captured.booking &&
                sessions[0].members[0].loadout == loadout &&
                sessions[1].members.size() == 1 &&
                sessions[1].members[0].loadout == loadout,
                "dispatcher transfers identity, native booking selection, and approved loadout");
            require(loadoutUpdates.size() == 2 &&
                std::ranges::all_of(loadoutUpdates, [&](const auto &update) {
                    return update.userId == authSession.snapshot().userId &&
                        update.loadout == loadout;
                }),
                "dispatcher refreshes the captured member without requiring a live-state mutation");
            const std::vector<std::uint32_t> expectedEntitlements{
                545, 10001, 10049, 20379, 20782, 25684,
            };
            require(entitlementRequests.size() == 3 &&
                std::ranges::all_of(entitlementRequests, [&](const auto &items) {
                    return items == expectedEntitlements;
                }),
                "dispatcher validates the base character but not derived presentation parts");
        }
    }

    void testMultiMemberBookingDispatcher()
    {
        using namespace AlwaysofflineRe;
        using namespace OlMod::DedicatedControl;
        using namespace OlMod::DedicatedSession;

        constexpr std::uint64_t FirstUser = 0x01100001DEADC0DEull;
        constexpr std::uint64_t SecondUser = 0x01100001DEADC0DFull;
        Demonware::AuthSession authSession;
        ClientSessionCapture firstCapture{
            .booking = {
                .playlistId = 26,
                .rotationIndex = 0,
                .mapName = "mp_crash_tropical",
                .gameType = "sd",
            },
        };
        firstCapture.loadout.classMask = 1;
        firstCapture.loadout.characterItemIds[0] = 10001;
        firstCapture.loadout.classes[0].weapons[0].itemId = 545;
        firstCapture.loadout.classes[0].weapons[1].itemId = 789;
        auto secondCapture = firstCapture;
        secondCapture.loadout.characterItemIds[0] = 10010;
        secondCapture.loadout.classes[0].weapons[0].itemId = 592;
        const auto firstBytes = encode(firstCapture);
        const auto secondBytes = encode(secondCapture);

        std::mutex mutex;
        std::condition_variable ready;
        std::vector<std::pair<std::uint64_t, std::vector<std::uint32_t>>> entitlements;
        std::vector<std::uint16_t> capturePorts;
        std::vector<SessionStart> sessions;
        std::vector<SessionMember> loadoutUpdates;
        std::size_t terminalDiagnostics{};
        std::atomic_size_t rosterCalls{};
        DedicatedBookingDispatcher dispatcher(
            authSession,
            [&](const std::uint64_t userId,
                const std::span<const std::uint32_t> items) {
                std::lock_guard lock(mutex);
                entitlements.emplace_back(
                    userId, std::vector<std::uint32_t>(items.begin(), items.end()));
                return true;
            },
            [&rosterCalls](const std::uint64_t generation) {
                if (rosterCalls++ < 2)
                    return std::optional<FrozenRoomRoster>{};
                return std::optional{ FrozenRoomRoster{
                    .generation = generation,
                    .members = {
                        { .userId = FirstUser, .displayName = "first", .bridgePort = 28963,
                          .connectionToken = 10, .ready = true },
                        { .userId = SecondUser, .displayName = "second", .bridgePort = 28962,
                          .connectionToken = 11, .ready = true },
                    },
                } };
            },
            [](const BookingSelection &) {
                return std::optional{ MatchRules{
                    .playlistVersion = 796,
                    .roundSwitch = 1,
                    .roundLimit = 7,
                    .winLimit = 4,
                } };
            },
            [&](const std::uint32_t, const std::uint16_t port,
                const Message &message, const std::uint32_t) {
                std::lock_guard lock(mutex);
                if (message.type == MessageType::CaptureLoadout)
                {
                    capturePorts.push_back(port);
                    const auto &bytes = port == 28963 ? firstBytes : secondBytes;
                    return SubmitResult{
                        .delivered = true,
                        .status = ResponseStatus::Accepted,
                        .requestId = message.requestId,
                        .payload = std::string(
                            reinterpret_cast<const char *>(bytes.data()), bytes.size()),
                    };
                }
                if (message.type == MessageType::UpdateLoadout)
                {
                    std::uint64_t userId{};
                    require(message.payload.size() >= sizeof(userId),
                        "multi-member refresh carries its XUID");
                    std::memcpy(&userId, message.payload.data(), sizeof(userId));
                    const auto updated = decodeLoadout({
                        reinterpret_cast<const std::uint8_t *>(
                            message.payload.data()) + sizeof(userId),
                        message.payload.size() - sizeof(userId),
                    });
                    require(updated.has_value(),
                        "multi-member refresh carries a valid loadout");
                    loadoutUpdates.push_back({
                        .userId = userId,
                        .loadout = *updated,
                    });
                    return SubmitResult{
                        .delivered = true,
                        .status = ResponseStatus::Accepted,
                        .requestId = message.requestId,
                    };
                }
                const auto decoded = decodeSessionStart({
                    reinterpret_cast<const std::uint8_t *>(message.payload.data()),
                    message.payload.size(),
                });
                require(decoded.has_value(), "multi-member descriptor decodes");
                sessions.push_back(*decoded);
                return SubmitResult{
                    .delivered = true,
                    .status = ResponseStatus::Accepted,
                    .requestId = message.requestId,
                };
            },
            [&](const std::string_view message) {
                if (message.starts_with("CODOL_GAME_SESSION accepted=true"))
                {
                    std::lock_guard lock(mutex);
                    ++terminalDiagnostics;
                    ready.notify_all();
                }
            });

        require(dispatcher.submit("mmstart multi"),
            "multi-member dispatcher accepts one booking transaction");
        std::unique_lock lock(mutex);
        require(ready.wait_for(lock, std::chrono::seconds(2), [&] {
            return terminalDiagnostics == 1;
        }), "multi-member dispatcher atomically submits the frozen roster");
        require(capturePorts == std::vector<std::uint16_t>{ 28963, 28962 },
            "dispatcher captures every frozen member's bridge endpoint");
        require(rosterCalls >= 3,
            "dispatcher waits for the room roster to become ready");
        require(entitlements.size() == 2 &&
            entitlements[0].first == FirstUser &&
            entitlements[1].first == SecondUser,
            "dispatcher validates each loadout against its own XUID");
        require(sessions.size() == 1 && sessions[0].members.size() == 2 &&
            sessions[0].members[0].userId == FirstUser &&
            sessions[0].members[0].loadout == firstCapture.loadout &&
            sessions[0].members[1].userId == SecondUser &&
            sessions[0].members[1].loadout == secondCapture.loadout,
            "dispatcher preserves frozen roster identity and per-member loadout");
        require(loadoutUpdates.size() == 2 &&
            loadoutUpdates[0].userId == FirstUser &&
            loadoutUpdates[0].loadout == firstCapture.loadout &&
            loadoutUpdates[1].userId == SecondUser &&
            loadoutUpdates[1].loadout == secondCapture.loadout,
            "dispatcher refreshes each in-progress roster member independently");

        auto nonOwnerIdentity = authSession.snapshot();
        nonOwnerIdentity.userId = FirstUser;
        authSession.update(nonOwnerIdentity);
        std::size_t nonOwnerSubmits{};
        std::size_t nonOwnerDiagnostics{};
        DedicatedBookingDispatcher nonOwnerDispatcher(
            authSession,
            [](const std::uint64_t, const std::span<const std::uint32_t>) {
                return true;
            },
            [](const std::uint64_t generation) {
                return std::optional{ FrozenRoomRoster{
                    .generation = generation,
                    .members = {
                        { .userId = SecondUser, .displayName = "second", .bridgePort = 28963,
                          .connectionToken = 11, .ready = true },
                        { .userId = FirstUser, .displayName = "first", .bridgePort = 28962,
                          .connectionToken = 10, .ready = true },
                    },
                } };
            },
            [](const BookingSelection &) {
                return std::optional{ MatchRules{} };
            },
            [&](const std::uint32_t, const std::uint16_t, const Message &,
                const std::uint32_t) {
                ++nonOwnerSubmits;
                return SubmitResult{};
            },
            [&](const std::string_view message) {
                if (message.find("non_owner_booking_ignored") != std::string_view::npos)
                {
                    std::lock_guard diagnosticLock(mutex);
                    ++nonOwnerDiagnostics;
                    ready.notify_all();
                }
            });
        require(nonOwnerDispatcher.submit("mmstart duplicate"),
            "non-owner dispatcher accepts the duplicate booking notification");
        require(ready.wait_for(lock, std::chrono::seconds(2), [&] {
            return nonOwnerDiagnostics == 1;
        }), "non-owner dispatcher terminates without submitting a session");
        require(nonOwnerSubmits == 0,
            "non-owner booking produces no bridge or dedicated side effect");
    }

    void testMultiMemberBookingFailureIsAtomic()
    {
        using namespace AlwaysofflineRe;
        using namespace OlMod::DedicatedControl;
        using namespace OlMod::DedicatedSession;

        ClientSessionCapture capture{
            .booking = {
                .playlistId = 26,
                .rotationIndex = 0,
                .mapName = "mp_crash_tropical",
                .gameType = "sd",
            },
        };
        capture.loadout.classMask = 1;
        capture.loadout.characterItemIds[0] = 10001;
        capture.loadout.classes[0].weapons[0].itemId = 545;
        capture.loadout.classes[0].weapons[1].itemId = 789;
        const auto matchingBytes = encode(capture);
        // This used to differ only in rotationIndex, which a live client has since
        // been measured NOT to track - it reported 5 against a booking command of
        // 8, and 12 against 0, while its map matched the command every time. So a
        // difference there is no longer treated as a disagreement at all, and the
        // fixture has to diverge on something that actually means something.
        auto mismatchedCapture = capture;
        mismatchedCapture.booking.rotationIndex = 1;
        mismatchedCapture.booking.mapName = "mp_seatown";
        const auto mismatchedBytes = encode(mismatchedCapture);

        for (const bool rejectEntitlement : { false, true })
        {
            Demonware::AuthSession authSession;
            auto ownerIdentity = authSession.snapshot();
            ownerIdentity.userId = 1;
            authSession.update(ownerIdentity);
            std::mutex mutex;
            std::condition_variable ready;
            std::size_t dedicatedSubmits{};
            std::size_t terminalDiagnostics{};
            DedicatedBookingDispatcher dispatcher(
                authSession,
                [&, checks = std::size_t{}](const std::uint64_t,
                    const std::span<const std::uint32_t>) mutable {
                    return !(rejectEntitlement && checks++ == 1);
                },
                [](const std::uint64_t generation) {
                    return std::optional{ FrozenRoomRoster{
                        .generation = generation,
                        .members = {
                            { .userId = 1, .displayName = "first", .bridgePort = 28962,
                              .connectionToken = 1, .ready = true },
                            { .userId = 2, .displayName = "second", .bridgePort = 28963,
                              .connectionToken = 2, .ready = true },
                        },
                    } };
                },
                [](const BookingSelection &) {
                    return std::optional{ MatchRules{
                        .playlistVersion = 796,
                        .roundSwitch = 1,
                        .roundLimit = 7,
                        .winLimit = 4,
                    } };
                },
                [&](const std::uint32_t, const std::uint16_t port,
                    const Message &message, const std::uint32_t) {
                    if (message.type == MessageType::UpdateLoadout)
                    {
                        return SubmitResult{
                            .delivered = true,
                            .status = ResponseStatus::Rejected,
                            .requestId = message.requestId,
                        };
                    }
                    if (message.type == MessageType::SessionStart)
                    {
                        // Notified, because the diagnostic and the submit are
                        // separate steps on the dispatcher thread: waiting only on
                        // the diagnostic wakes the test before the submit lands and
                        // reads a count that is still zero.
                        std::lock_guard lock(mutex);
                        ++dedicatedSubmits;
                        ready.notify_all();
                        return SubmitResult{};
                    }
                    const auto &bytes = port == 28963 && !rejectEntitlement
                        ? mismatchedBytes
                        : matchingBytes;
                    return SubmitResult{
                        .delivered = true,
                        .status = ResponseStatus::Accepted,
                        .requestId = message.requestId,
                        .payload = std::string(
                            reinterpret_cast<const char *>(bytes.data()), bytes.size()),
                    };
                },
                [&](const std::string_view message) {
                    if (message.find(rejectEntitlement
                            ? "entitlement_rejected"
                            : "member selection differs") != std::string_view::npos)
                    {
                        std::lock_guard lock(mutex);
                        ++terminalDiagnostics;
                        ready.notify_all();
                    }
                });
            require(dispatcher.submit("mmstart rejected multi"),
                "multi-member failure fixture accepts booking work");
            std::unique_lock lock(mutex);
            require(ready.wait_for(lock, std::chrono::seconds(2), [&] {
                return terminalDiagnostics == 1 &&
                    dedicatedSubmits == (rejectEntitlement ? 0u : 1u);
            }), "a diverging member selection and a failed entitlement are both reported");
            // The two are deliberately NOT the same severity any more. An
            // entitlement failure is still atomic - that member may not play at
            // all. A member whose client rolled a different map is not: the roster
            // OWNER's booking command is already the only one honoured, so its
            // selection is the match's selection and the others follow it.
            //
            // Requiring unanimity here held only because search and destroy books
            // a slot whose rotation always rolls index 0, so every client trivially
            // agreed. Free-for-all offers 14 maps under playlistMapRotateSequentially
            // 0 and each client rolls its own - observed live as one client on
            // rotation 7 and the other on 8 - so no session could ever be assembled.
            require(dedicatedSubmits == (rejectEntitlement ? 0u : 1u),
                rejectEntitlement
                    ? "a failed entitlement produces no dedicated side effect"
                    : "a diverging member selection still starts the owner's match");
        }
    }

    void testSharedRoomSessionOwner()
    {
        using AlwaysofflineRe::SharedRoomSessionOwner;

        constexpr std::uint64_t FirstUser = 0x01100001DEADC0DEull;
        constexpr std::uint64_t SecondUser = 0x01100001DEADC0EEull;
        SharedRoomSessionOwner owner(2);
        require(
            !owner.connect(0, "first", 28962) &&
                !owner.connect(FirstUser, "", 28962) &&
                !owner.connect(FirstUser, "first", 0),
            "shared room rejects incomplete authenticated endpoints");
        const auto firstToken = owner.connect(FirstUser, "first", 28962);
        require(!owner.connect(SecondUser, "duplicate-port", 28962),
            "shared room rejects ambiguous duplicate bridge endpoints");
        {
            // THE REMOTE CASE, and the one the port-only key used to refuse:
            // two friends on two PCs both run the DEFAULT bridge port.
            SharedRoomSessionOwner remote(2);
            const auto here = remote.connect(FirstUser, "here", 28962, 0x7F000001);
            const auto there = remote.connect(SecondUser, "there", 28962, 0xC0A801FA);
            require(here && there && *here != *there,
                "same bridge port on two machines is two members, not a duplicate");
            require(!remote.connect(0x01100001DEADC0FEull, "again", 28962, 0xC0A801FA),
                "the same port on the SAME machine is still a duplicate");
            const auto members = remote.members();
            require(members.size() == 2 &&
                    members[0].bridgeIpv4 == 0x7F000001 &&
                    members[1].bridgeIpv4 == 0xC0A801FA,
                "the owner keeps the address each member connected from");
        }
        const auto secondToken = owner.connect(SecondUser, "second", 28963);
        require(firstToken && secondToken && *firstToken != *secondToken,
            "shared room assigns a connection generation to each member");
        require(!owner.connect(0x01100001DEADC0FEull, "third", 28964),
            "shared room enforces its general member capacity");
        require(!owner.freeze(1),
            "room roster cannot freeze until every current member is ready");
        require(
            owner.setReady(SecondUser, *secondToken, true) &&
                owner.setReady(FirstUser, *firstToken, true),
            "members can become ready in any order");
        const auto claimedFrozen = owner.freeze(6, SecondUser, *secondToken);
        require(claimedFrozen && claimedFrozen->ownerUserId == SecondUser,
            "ready member can claim the shared room allocation owner");
        const auto frozen = owner.freeze(7);
        require(
            frozen && frozen->generation == 7 && frozen->members.size() == 2 &&
                frozen->members[0].userId == FirstUser &&
                frozen->members[0].bridgePort == 28962 &&
                frozen->members[1].userId == SecondUser &&
                frozen->members[1].bridgePort == 28963 &&
                owner.freeze(7) == frozen,
            "frozen room roster is stable, sorted by XUID, and idempotent");

        const auto replacementToken = owner.connect(FirstUser, "renamed", 28964);
        require(
            replacementToken && *replacementToken != *firstToken &&
                !owner.disconnect(FirstUser, *firstToken) &&
                !owner.setReady(FirstUser, *firstToken, true) &&
                owner.freeze(7) == frozen,
            "stale disconnect and ready events cannot mutate a replacement login");
        require(!owner.freeze(8),
            "replacement login starts unready and invalidates the old room view");
        require(
            owner.setReady(FirstUser, *replacementToken, true) &&
                owner.disconnect(SecondUser, *secondToken),
            "current connection tokens control ready and disconnect mutations");
        const auto finalRoster = owner.freeze(8);
        require(
            finalRoster && finalRoster->members.size() == 1 &&
                finalRoster->members[0].displayName == "renamed" &&
                finalRoster->members[0].bridgePort == 28964,
            "room freeze reflects the latest authenticated member state");
    }

    void testSharedRoomControl()
    {
        using namespace AlwaysofflineRe;
        using namespace AlwaysofflineRe::SharedRoomControl;
        using namespace OlMod::DedicatedControl;

        constexpr std::uint64_t UserId = 0x01100001DEADC0DEull;
        const ConnectRequest connect{
            .userId = UserId,
            .displayName = "room-client",
            .bridgePort = 28962,
        };
        require(decodeConnect(encode(connect)) ==
            std::optional{ connect }, "room connect codec roundtrips");
        require(!decodeConnect(encode(connect) + "tail") &&
            !decodeConnect("bad"), "room connect rejects trailing and truncated payloads");

        SharedRoomSessionOwner owner;
        Handler handler(owner);
        OlMod::DedicatedControl::Server server;
        require(server.start(0, [&handler](const auto &message) {
            return handler(message);
        }), "room owner binds an isolated loopback endpoint");
        const auto connected = submit("127.0.0.1", server.port(), {
            .type = MessageType::RoomConnect,
            .requestId = 1,
            .payload = encode(connect),
        });
        const auto token = decodeToken(connected.payload);
        require(connected.delivered && connected.status == ResponseStatus::Accepted &&
            token, "room client registers through bounded control transport");
        const ReadyRequest ready{
            .userId = UserId,
            .connectionToken = *token,
            .ready = true,
        };
        require(decodeReady(encode(ready)) == std::optional{ ready },
            "room ready codec roundtrips the connection token");
        require(submit("127.0.0.1", server.port(), {
            .type = MessageType::RoomSetReady,
            .requestId = 2,
            .payload = encode(ready),
        }).status == ResponseStatus::Accepted,
            "room ready mutation reaches the shared owner");
        const SessionDescriptorRequest sessionDescriptor{
            .userId = UserId,
            .connectionToken = *token,
            .descriptor = "first-session-descriptor",
        };
        require(decodeSessionDescriptor(encode(sessionDescriptor)) ==
                std::optional{ sessionDescriptor },
            "room session descriptor codec roundtrips member authorization");
        const auto canonical = submit("127.0.0.1", server.port(), {
            .type = MessageType::RoomCanonicalizeSession,
            .requestId = 3,
            .payload = encode(sessionDescriptor),
        });
        require(canonical.status == ResponseStatus::Accepted &&
                canonical.payload == sessionDescriptor.descriptor,
            "room owner accepts the first authorized session descriptor");
        auto alternate = sessionDescriptor;
        alternate.descriptor = "second-session-descriptor";
        const auto repeatedCanonical = submit("127.0.0.1", server.port(), {
            .type = MessageType::RoomCanonicalizeSession,
            .requestId = 4,
            .payload = encode(alternate),
        });
        require(repeatedCanonical.status == ResponseStatus::Accepted &&
                repeatedCanonical.payload == sessionDescriptor.descriptor,
            "room owner returns one canonical descriptor to every member");
        const auto frozen = submit("127.0.0.1", server.port(), {
            .type = MessageType::RoomFreeze,
            .requestId = 5,
            .payload = encode(FreezeRequest{
                .generation = 7,
                .claimant = {
                    .userId = UserId,
                    .connectionToken = *token,
                },
            }),
        });
        require(frozen.status == ResponseStatus::Accepted,
            "room freeze accepts an authenticated claimant");
        const auto roster = decodeRoster(frozen.payload);
        require(frozen.status == ResponseStatus::Accepted && roster &&
            roster->generation == 7 && roster->ownerUserId == UserId &&
            roster->members.size() == 1 &&
            roster->members[0].userId == UserId &&
            roster->members[0].displayName == "room-client",
            "room freeze returns the authoritative generation roster");
        require(!decodeRoster(frozen.payload.substr(0, frozen.payload.size() - 1)) &&
            !decodeRoster(frozen.payload + "tail"),
            "room roster rejects truncated and trailing bytes");
        require(submit("127.0.0.1", server.port(), {
            .type = MessageType::RoomDisconnect,
            .requestId = 6,
            .payload = encode(MemberRequest{
                .userId = UserId,
                .connectionToken = *token,
            }),
        }).status == ResponseStatus::Accepted && owner.members().empty(),
            "room disconnect releases the current connection through IPC");
        server.stop();
    }

    void testSharedRoomClientLifecycle()
    {
        using namespace AlwaysofflineRe;

        SharedRoomSessionOwner owner;
        SharedRoomControl::Handler handler(owner);
        OlMod::DedicatedControl::Server server;
        require(server.start(0, [&handler](const auto &message) {
            return handler(message);
        }), "room client fixture binds a loopback owner");
        _putenv_s("OLMOD_ROOM_OWNER_PORT", std::to_string(server.port()).c_str());

        constexpr std::uint64_t UserId = 0x01100001DEADC0DEull;
        SharedRoomClient client;
        require(client.connect(Demonware::AuthIdentity{
            .userId = UserId,
            .username = "room-client",
        }, 28962), "room client registers authenticated identity and bridge endpoint");
        require(client.setReady(UserId, true) && owner.freeze(1).has_value(),
            "room client commits readiness with its current connection token");
        require(!client.disconnect(UserId + 1) && owner.members().size() == 1,
            "room client rejects a different authenticated identity");
        require(client.disconnect(UserId) && owner.members().empty(),
            "room client disconnects its current token safely");
        require(!client.setReady(UserId, true),
            "room client cannot reuse a disconnected token");

        _putenv_s("OLMOD_ROOM_OWNER_PORT", "");
        server.stop();
    }
}

void runDemonwareTests();

int main()
{
    runDemonwareTests();
    testHostnameClassification();
    testRuntimeConsoleSwitch();
    testFactoryLifetime();
    testStunBinding();
    testAuth3ClientPatches();
    testCodolStartupPatches();
    testDedicatedBookingDispatcher();
    testMultiMemberBookingDispatcher();
    testMultiMemberBookingFailureIsAtomic();
    testSharedRoomSessionOwner();
    testSharedRoomControl();
    testSharedRoomClientLifecycle();
    std::cout << "AlwaysofflineRe server tests passed.\n";
    return 0;
}
