#include "DedicatedBookingDispatcher.hpp"

#include "../shared/DedicatedControl.hpp"
#include "../shared/DedicatedSession.hpp"
#include "../shared/CodolPlaylist.hpp"

#include <algorithm>
#include <chrono>
#include <condition_variable>
#include <deque>
#include <cstring>
#include <charconv>
#include <filesystem>
#include <fstream>
#include <iterator>
#include <mutex>
#include <span>
#include <string>
#include <string_view>
#include <thread>
#include <utility>
#include <vector>

namespace
{
    // OLMOD(ffa-test-limits): the free-for-all score limit, overridable for
    // testing with OLMOD_FFA_SCORE_LIMIT.
    //
    // WHY THIS EXISTS. Everything on the end-of-match schedule -- the clock
    // stop, the outro vision switch, `t "EXE_MATCHENDED"` (HANDOFF section 108d)
    // -- only fires when a match is DECIDED, and at 30 kills that is far past
    // what a two-person test session will play. Without a lever, one live cycle
    // verifies the death path and nothing else; with it, one cycle verifies the
    // whole schedule.
    //
    // Read once, like SV_FrameMilliseconds, so it cannot change under a running
    // match. Bounded at 1..1000: a zero would mean NO score limit and the match
    // could never end by score, which is the opposite of what a tester wants.
    std::uint32_t ffaScoreLimit()
    {
        static const std::uint32_t limit = [] {
            constexpr std::uint32_t fallback = 30;
            std::size_t length{};
            char value[16]{};
            if (getenv_s(&length, value, sizeof(value),
                    "OLMOD_FFA_SCORE_LIMIT") != 0 ||
                length == 0)
            {
                return fallback;
            }
            std::uint32_t parsed{};
            const auto *first = value;
            const auto *last = value + std::strlen(value);
            const auto &[pointer, error] = std::from_chars(first, last, parsed);
            if (error != std::errc{} || pointer != last || parsed < 1 ||
                parsed > 1000)
            {
                return fallback;
            }
            return parsed;
        }();
        return limit;
    }

    constexpr std::size_t ClientCaptureAttempts = 3;
    constexpr auto ClientCaptureRetryDelay = std::chrono::milliseconds(200);
    constexpr std::size_t RoomRosterAttempts = 150;
    constexpr auto RoomRosterRetryDelay = std::chrono::milliseconds(100);

    std::vector<std::uint32_t> requestedItems(
        const OlMod::DedicatedSession::LoadoutRequest &request)
    {
        std::vector<std::uint32_t> result;
        // Record zero is the marketplace-ownable base character. The remaining
        // records are presentation components resolved from that base definition.
        if (request.characterItemIds.front())
            result.push_back(request.characterItemIds.front());
        for (std::size_t classIndex = 0; classIndex < request.classes.size(); ++classIndex)
        {
            if (!(request.classMask & (1u << classIndex)))
                continue;
            for (const auto &weapon : request.classes[classIndex].weapons)
            {
                result.push_back(weapon.itemId);
                for (const auto itemId : weapon.attachmentItemIds)
                {
                    if (itemId)
                        result.push_back(itemId);
                }
            }
        }
        std::ranges::sort(result);
        result.erase(std::unique(result.begin(), result.end()), result.end());
        return result;
    }

    std::string sessionDiagnostic(
        const std::string_view result,
        const std::uint64_t requestId,
        const std::span<const std::uint32_t> items = {},
        const std::uint64_t localUserId = 0,
        const std::uint64_t ownerUserId = 0)
    {
        std::string message = "CODOL_GAME_SESSION ";
        message.append(result);
        message.append(" request_id=");
        message.append(std::to_string(requestId));
        if (!items.empty())
        {
            message.append(" items=");
            for (std::size_t index = 0; index < items.size(); ++index)
            {
                if (index)
                    message.push_back(',');
                message.append(std::to_string(items[index]));
            }
        }
        if (localUserId || ownerUserId)
        {
            message.append(" local_user=");
            message.append(std::to_string(localUserId));
            message.append(" roster_owner=");
            message.append(std::to_string(ownerUserId));
        }
        return message;
    }

    std::optional<std::uint32_t> parseRuleU32(const std::string_view value)
    {
        std::uint32_t result{};
        const auto parsed = std::from_chars(
            value.data(), value.data() + value.size(), result);
        if (parsed.ec != std::errc{} || parsed.ptr != value.data() + value.size())
            return std::nullopt;
        return result;
    }

    std::optional<OlMod::DedicatedSession::MatchRules> loadMatchRules(
        const OlMod::DedicatedSession::BookingSelection &selection,
        const std::filesystem::path &path =
            L"./Ayria/Assets/Alwaysoffline/1004/Server/mp_playlists_shipRetail_release.info")
    {
        std::ifstream stream(path, std::ios::binary);
        if (!stream)
            return std::nullopt;
        const std::string text{
            std::istreambuf_iterator<char>(stream),
            std::istreambuf_iterator<char>() };
        return AlwaysofflineRe::resolveMatchRules(text, selection);
    }
}

namespace
{
    std::string ipv4Text(const std::uint32_t address)
    {
        return std::to_string((address >> 24) & 0xFF) + '.' +
            std::to_string((address >> 16) & 0xFF) + '.' +
            std::to_string((address >> 8) & 0xFF) + '.' +
            std::to_string(address & 0xFF);
    }
}

namespace AlwaysofflineRe
{
    namespace
    {
        std::optional<OlMod::DedicatedSession::MatchRules> parseMatchRules(
            const OlMod::CodolPlaylist::Document &document,
            const OlMod::CodolPlaylist::Playlist &playlist,
            const std::string_view rawGameType)
        {
            // The client can hand us either vocabulary, and DedicatedSession::valid
            // normalises before checking. Without the same normalisation here the
            // two disagree: an engine name misses every branch below, so no limits
            // are read, and then valid() rejects for the limits being absent. That
            // presents as a bare "rules rejected" with nothing wrong in the data.
            const auto gameType = OlMod::CodolPlaylist::bookingToken(rawGameType);
            OlMod::DedicatedSession::MatchRules rules{
                .playlistVersion = document.version,
            };
            if (gameType == "cha")
            {
                const auto scoreLimit = OlMod::CodolPlaylist::findRule(
                    playlist, "scr_cha_scorelimit");
                const auto timeLimit = OlMod::CodolPlaylist::findRule(
                    playlist, "scr_cha_timelimit");
                if (!scoreLimit || !timeLimit)
                    return std::nullopt;
                const auto parsedScoreLimit = parseRuleU32(*scoreLimit);
                const auto parsedTimeLimit = parseRuleU32(*timeLimit);
                if (!parsedScoreLimit || !parsedTimeLimit)
                    return std::nullopt;
                rules.scoreLimit = *parsedScoreLimit;
                rules.timeLimitMinutes = *parsedTimeLimit;
            }
            else if (gameType == "ffa")
            {
                // Unlike cha and sd there is nothing to read: neither shipped
                // free-for-all playlist - 23 ("Free For All") or 154 ("Snipers
                // Only") - declares a single scr_* rule, so the limits are the
                // gametype's own defaults rather than playlist-driven.
                //
                // OLMOD: 30 and 10 are read from the retail demo
                // C-2021-7-25[1-19-26]dm.demo, configstrings 467 and 468. Those
                // two indices were identified with an oracle rather than by eye -
                // the shipped playlist pins scr_cha_scorelimit 50 and
                // scr_cha_timelimit 10, and 467/468 are the only candidates that
                // read exactly 50 and 10 in both cha demos while still separating
                // every other mode (war 75/10, dom 200/0, chicken 300/15).
                //
                // They cross a build boundary - that demo is OLfinal - so they are
                // a project choice here, not a constant recovered from 3.3.3.3. A
                // wrong limit is visible and harmless, unlike a wire constant.
                // OLMOD(ffa-test-limits): the time limit is raised to 60 for
                // development. SV_BuildGameState computes configstring 15 as
                // `matchStartServerTime + minutes * 60 * 1000` in uint64, so 60
                // is 3,600,000 ms and nowhere near an overflow; a zero here
                // would mean NO limit and erase the clock entirely.
                // TODO(CODOL): restore 10 before this branch is offered
                // upstream - it is the retail value, read from the dm demo's
                // configstring 468.
                rules.scoreLimit = ffaScoreLimit();
                rules.timeLimitMinutes = 60;
            }
            else if (gameType == "sd")
            {
                const auto timeLimit = OlMod::CodolPlaylist::findRule(
                    playlist, "scr_sd_timelimit");
                const auto roundSwitch = OlMod::CodolPlaylist::findRule(
                    playlist, "scr_sd_roundswitch");
                const auto roundLimit = OlMod::CodolPlaylist::findRule(
                    playlist, "scr_sd_roundlimit");
                const auto winLimit = OlMod::CodolPlaylist::findRule(
                    playlist, "scr_sd_winlimit");
                if (!roundSwitch || !roundLimit || !winLimit)
                    return std::nullopt;
                const auto parsedRoundSwitch = parseRuleU32(*roundSwitch);
                const auto parsedRoundLimit = parseRuleU32(*roundLimit);
                const auto parsedWinLimit = parseRuleU32(*winLimit);
                const auto parsedTimeLimit = timeLimit
                    ? parseRuleU32(*timeLimit)
                    : std::optional<std::uint32_t>{ 2 };
                if (!parsedTimeLimit || !parsedRoundSwitch ||
                    !parsedRoundLimit || !parsedWinLimit)
                    return std::nullopt;
                rules.timeLimitMinutes = *parsedTimeLimit;
                rules.roundSwitch = *parsedRoundSwitch;
                rules.roundLimit = *parsedRoundLimit;
                rules.winLimit = *parsedWinLimit;
            }
            return OlMod::DedicatedSession::valid(rules, gameType)
                ? std::optional{ rules }
                : std::nullopt;
        }
    }

    std::optional<OlMod::DedicatedSession::MatchRules> resolveMatchRules(
        const std::string_view playlistText,
        const OlMod::DedicatedSession::BookingSelection &selection)
    {
        const auto document = OlMod::CodolPlaylist::parse(playlistText);
        const auto *playlist = document ? document->find(selection.playlistId) : nullptr;
        if (!document)
            return std::nullopt;
        // Rotation entries are written in the BOOKING vocabulary, so a selection
        // carrying an engine gametype has to be normalised before it can match
        // one. Comparing the raw string finds nothing and is indistinguishable
        // from "this playlist does not offer that mode".
        const auto selectionGameType =
            OlMod::CodolPlaylist::bookingToken(selection.gameType);
        if (playlist)
        {
            if (selection.rotationIndex >= playlist->rotation.size())
                return std::nullopt;
            const auto &rotation = playlist->rotation[selection.rotationIndex];
            if (rotation.mapName != selection.mapName ||
                rotation.gameType != selectionGameType)
            {
                return std::nullopt;
            }
            return parseMatchRules(*document, *playlist, selectionGameType);
        }

        // Legacy native selections can use IDs absent from the shipped
        // publisher file. Accept only a unique rule value shared by every
        // publisher playlist that contains the captured native map/mode.
        std::optional<OlMod::DedicatedSession::MatchRules> consensus;
        for (const auto &candidate : document->playlists)
        {
            const auto containsSelection = std::ranges::any_of(
                candidate.rotation,
                [&selection, selectionGameType](const auto &entry) {
                    return entry.mapName == selection.mapName &&
                        entry.gameType == selectionGameType;
                });
            if (!containsSelection)
                continue;
            const auto rules = parseMatchRules(
                *document, candidate, selectionGameType);
            if (!rules)
                continue;
            if (consensus && *consensus != *rules)
                return std::nullopt;
            consensus = *rules;
        }
        return consensus;
    }

    struct DedicatedBookingDispatcher::State
    {
        State(
            Demonware::AuthSession &authSession,
            EntitlementCheck entitlementCallback,
            RosterProvider rosterCallback,
            MatchRulesProvider matchRulesCallback,
            ControlSubmit submitCallback,
            Diagnostic callback)
            : session(authSession),
              entitlementCheck(std::move(entitlementCallback)),
              rosterProvider(std::move(rosterCallback)),
              matchRulesProvider(std::move(matchRulesCallback)),
              controlSubmit(std::move(submitCallback)),
              diagnostic(std::move(callback))
        {
        }

        Demonware::AuthSession &session;
        EntitlementCheck entitlementCheck;
        RosterProvider rosterProvider;
        MatchRulesProvider matchRulesProvider;
        ControlSubmit controlSubmit;
        Diagnostic diagnostic;
        std::mutex mutex;
        std::condition_variable ready;
        std::deque<std::string> commands;
        bool stopping{};
        std::uint64_t nextRequestId{1};
        std::thread worker;
    };

    DedicatedBookingDispatcher::DedicatedBookingDispatcher(
        Demonware::AuthSession &session,
        Demonware::MarketplaceService &marketplace,
        Diagnostic diagnostic)
        : DedicatedBookingDispatcher(
            session, marketplace, {}, std::move(diagnostic))
    {
    }

    DedicatedBookingDispatcher::DedicatedBookingDispatcher(
        Demonware::AuthSession &session,
        Demonware::MarketplaceService &marketplace,
        RosterProvider rosterProvider,
        Diagnostic diagnostic)
        : DedicatedBookingDispatcher(
            session,
            [&marketplace](const std::uint64_t userId,
                           const std::span<const std::uint32_t> items) {
                return marketplace.hasEntitlements(userId, items);
            },
            std::move(rosterProvider),
            [](const OlMod::DedicatedSession::BookingSelection &selection) {
                return loadMatchRules(selection);
            },
            [](const std::uint32_t bridgeIpv4,
               const std::uint16_t port,
               const OlMod::DedicatedControl::Message &message,
               const std::uint32_t timeoutMilliseconds) {
                // Zero is what a member that never announced an address gets,
                // which is every member the owner has ever had on its own box.
                return OlMod::DedicatedControl::submit(
                    bridgeIpv4
                        ? ipv4Text(bridgeIpv4)
                        : OlMod::DedicatedControl::configuredHostAddress(),
                    port, message, timeoutMilliseconds);
            },
            std::move(diagnostic))
    {
    }

    DedicatedBookingDispatcher::DedicatedBookingDispatcher(
        Demonware::AuthSession &session,
        EntitlementCheck entitlementCheck,
        RosterProvider rosterProvider,
        MatchRulesProvider matchRulesProvider,
        ControlSubmit controlSubmit,
        Diagnostic diagnostic)
        : state_(std::make_unique<State>(
            session,
            std::move(entitlementCheck),
            std::move(rosterProvider),
            std::move(matchRulesProvider),
            std::move(controlSubmit),
            std::move(diagnostic)))
    {
        state_->worker = std::thread([state = state_.get()] {
            for (;;)
            {
                std::string command;
                {
                    std::unique_lock lock(state->mutex);
                    state->ready.wait(lock, [&] {
                        return state->stopping || !state->commands.empty();
                    });
                    if (state->stopping && state->commands.empty())
                        return;
                    command = std::move(state->commands.front());
                    state->commands.pop_front();
                }

                const auto requestId = state->nextRequestId++;
                if (!state->nextRequestId)
                    state->nextRequestId = 1;

                std::optional<FrozenRoomRoster> roster;
                if (state->rosterProvider)
                {
                    for (std::size_t attempt = 0; attempt < RoomRosterAttempts; ++attempt)
                    {
                        roster = state->rosterProvider(requestId);
                        if (roster)
                            break;
                        if (attempt + 1 < RoomRosterAttempts)
                            std::this_thread::sleep_for(RoomRosterRetryDelay);
                    }
                }
                else
                {
                    const auto identity = state->session.snapshot();
                    roster = FrozenRoomRoster{
                        .generation = requestId,
                        .members = {{
                            .userId = identity.userId,
                            .displayName = identity.username,
                            .bridgePort = OlMod::DedicatedControl::configuredClientBridgePort(),
                            .connectionToken = 1,
                            .ready = true,
                        }},
                    };
                }
                if (!roster || roster->generation != requestId || roster->members.empty())
                {
                    state->diagnostic(sessionDiagnostic("room_roster_failed", requestId));
                    continue;
                }
                std::vector<std::uint64_t> rosterUserIds;
                // THE PAIR, NOT THE PORT. Two members on two machines both using
                // the default bridge port are not ambiguous, and rejecting them
                // here would refuse the second friend to join.
                std::vector<std::pair<std::uint32_t, std::uint16_t>> rosterBridges;
                bool invalidRoster{};
                for (const auto &member : roster->members)
                {
                    const auto bridge = std::pair{ member.bridgeIpv4, member.bridgePort };
                    if (!member.userId || !member.bridgePort || !member.ready ||
                        std::ranges::find(rosterUserIds, member.userId) != rosterUserIds.end() ||
                        std::ranges::find(rosterBridges, bridge) != rosterBridges.end())
                    {
                        invalidRoster = true;
                        break;
                    }
                    rosterUserIds.push_back(member.userId);
                    rosterBridges.push_back(bridge);
                }
                if (invalidRoster)
                {
                    state->diagnostic(sessionDiagnostic("invalid_room_roster", requestId));
                    continue;
                }
                const auto localUserId = state->session.snapshot().userId;
                const auto ownerUserId = roster->ownerUserId
                    ? roster->ownerUserId
                    : roster->members.front().userId;
                if (localUserId != ownerUserId)
                {
                    state->diagnostic(sessionDiagnostic(
                        "non_owner_booking_ignored", requestId, {},
                        localUserId, ownerUserId));
                    continue;
                }

                std::optional<OlMod::DedicatedSession::BookingSelection> selection;
                std::vector<OlMod::DedicatedSession::BookingSelection> memberSelections;
                std::vector<OlMod::DedicatedSession::SessionMember> sessionMembers;
                sessionMembers.reserve(roster->members.size());
                bool memberFailed{};
                for (const auto &member : roster->members)
                {
                    OlMod::DedicatedControl::SubmitResult capture;
                    for (std::size_t attempt = 0; attempt < ClientCaptureAttempts; ++attempt)
                    {
                        capture = state->controlSubmit(
                            member.bridgeIpv4,
                            member.bridgePort,
                            {
                                .type = OlMod::DedicatedControl::MessageType::CaptureLoadout,
                                .requestId = requestId,
                            },
                            2500);
                        if (capture.delivered &&
                            capture.status == OlMod::DedicatedControl::ResponseStatus::Accepted)
                        {
                            break;
                        }
                        if (capture.delivered &&
                            capture.status != OlMod::DedicatedControl::ResponseStatus::Rejected)
                        {
                            break;
                        }
                        if (attempt + 1 < ClientCaptureAttempts)
                            std::this_thread::sleep_for(ClientCaptureRetryDelay);
                    }
                    if (!capture.delivered ||
                        capture.status != OlMod::DedicatedControl::ResponseStatus::Accepted)
                    {
                        state->diagnostic(sessionDiagnostic("client_capture_failed", requestId));
                        memberFailed = true;
                        break;
                    }
                    const auto captured =
                        OlMod::DedicatedSession::decodeClientSessionCapture({
                        reinterpret_cast<const std::uint8_t *>(capture.payload.data()),
                        capture.payload.size(),
                    });
                    if (!captured)
                    {
                        state->diagnostic(sessionDiagnostic("invalid_client_descriptor", requestId));
                        memberFailed = true;
                        break;
                    }
                    // The ROSTER OWNER's selection is the match's selection. Its
                    // booking command is already the only one honoured a few lines
                    // up (non_owner_booking_ignored), so requiring every member to
                    // have independently arrived at the same one was a stricter
                    // rule than the booking itself follows.
                    //
                    // It held only because search and destroy books a slot whose
                    // rotation always rolls index 0, so every client trivially
                    // agreed. Free-for-all offers 14 maps under
                    // playlistMapRotateSequentially 0, so each client rolls its own
                    // - observed as one client on rotation 7 and the other on 8 -
                    // and no free-for-all session could ever be assembled.
                    if (member.userId == ownerUserId)
                        selection = captured->booking;
                    else
                        memberSelections.push_back(captured->booking);
                    const auto items = requestedItems(captured->loadout);
                    if (!state->entitlementCheck(member.userId, items))
                    {
                        state->diagnostic(sessionDiagnostic(
                            "entitlement_rejected", requestId, items));
                        memberFailed = true;
                        break;
                    }
                    sessionMembers.push_back({
                        .userId = member.userId,
                        .username = member.displayName,
                        .loadout = captured->loadout,
                    });
                }
                if (memberFailed || !selection ||
                    sessionMembers.size() != roster->members.size())
                    continue;
                // Not fatal, but never silent: a member whose own client rolled a
                // different map is about to be sent somewhere it did not choose,
                // and that is worth seeing in the log rather than discovering as
                // two players standing on different maps.
                for (const auto &memberSelection : memberSelections)
                {
                    // rotationIndex is deliberately not compared: a live client
                    // reported 5 against a booking command of 8, and 12 against 0,
                    // while its map matched the command every time. Comparing a
                    // field measured not to track anything would report divergence
                    // on identical selections.
                    if (memberSelection.playlistId == selection->playlistId &&
                        memberSelection.mapName == selection->mapName &&
                        memberSelection.gameType == selection->gameType)
                    {
                        continue;
                    }
                    state->diagnostic(sessionDiagnostic(
                        "member selection differs from the roster owner's, using the owner's: member map=" +
                            memberSelection.mapName + " rotation=" +
                            std::to_string(memberSelection.rotationIndex) +
                            " owner map=" + selection->mapName + " rotation=" +
                            std::to_string(selection->rotationIndex),
                        requestId));
                }
                const auto matchRules = state->matchRulesProvider
                    ? state->matchRulesProvider(*selection)
                    : std::nullopt;
                if (!matchRules)
                {
                    // A bare verdict here cost a whole test cycle: the rejection
                    // could be an absent playlist id, a map/mode pair in no
                    // rotation at all, or rules that failed to validate, and the
                    // three need completely different fixes. Say which selection
                    // was refused so the next one does not.
                    state->diagnostic(sessionDiagnostic(
                        "match_rules_rejected playlist=" +
                            std::to_string(selection->playlistId) +
                            " rotation=" +
                            std::to_string(selection->rotationIndex) +
                            " map=" + selection->mapName +
                            " gametype=" + selection->gameType,
                        requestId));
                    continue;
                }

                // Refresh every captured member on the already-running server
                // before submitting the roster session. A first match has no
                // registered member yet, so this may be rejected harmlessly and
                // SessionStart below remains the owner. On a join-in-progress
                // booking the member already exists: UpdateLoadout replaces only
                // that registry entry, and the newly selected class is used on
                // the next spawn without mutating a live playerState.
                for (std::size_t index = 0;
                     index < sessionMembers.size(); ++index)
                {
                    const auto encodedLoadout =
                        OlMod::DedicatedSession::encode(
                            sessionMembers[index].loadout);
                    if (encodedLoadout.empty())
                        continue;
                    std::string payload(sizeof(std::uint64_t), '\0');
                    std::memcpy(
                        payload.data(),
                        &sessionMembers[index].userId,
                        sizeof(std::uint64_t));
                    payload.append(
                        reinterpret_cast<const char *>(encodedLoadout.data()),
                        encodedLoadout.size());
                    const auto refreshed = state->controlSubmit(
                        0,
                        OlMod::DedicatedControl::configuredPort(),
                        {
                            .type = OlMod::DedicatedControl::MessageType::UpdateLoadout,
                            .requestId = requestId,
                            .payload = std::move(payload),
                        },
                        2500);
                    if (refreshed.delivered &&
                        refreshed.status !=
                            OlMod::DedicatedControl::ResponseStatus::Accepted &&
                        refreshed.status !=
                            OlMod::DedicatedControl::ResponseStatus::Rejected)
                    {
                        state->diagnostic(sessionDiagnostic(
                            "loadout_refresh_invalid_response", requestId));
                    }
                }

                const OlMod::DedicatedSession::SessionStart sessionStart{
                    .bookingCommand = command,
                    .booking = *selection,
                    .matchRules = *matchRules,
                    .members = std::move(sessionMembers),
                };
                const auto encoded = OlMod::DedicatedSession::encode(sessionStart);
                if (encoded.empty())
                {
                    state->diagnostic(sessionDiagnostic("encode_failed", requestId));
                    continue;
                }
                const auto submitted = state->controlSubmit(
                    // ZERO, not a member's address: this one goes to the
                    // DEDICATED's control port, which lives wherever
                    // OLMOD_HOST_ADDRESS says the host is.
                    0,
                    OlMod::DedicatedControl::configuredPort(),
                    {
                        .type = OlMod::DedicatedControl::MessageType::SessionStart,
                        .requestId = requestId,
                        .payload = std::string(
                            reinterpret_cast<const char *>(encoded.data()),
                            encoded.size()),
                    },
                    2500);
                state->diagnostic(sessionDiagnostic(
                    submitted.delivered &&
                        submitted.status ==
                            OlMod::DedicatedControl::ResponseStatus::Accepted
                        ? "accepted=true"
                        : "dedicated_submit_failed",
                    requestId));
            }
        });
    }

    DedicatedBookingDispatcher::~DedicatedBookingDispatcher()
    {
        if (!state_)
            return;
        {
            const std::lock_guard lock(state_->mutex);
            state_->stopping = true;
        }
        state_->ready.notify_one();
        if (state_->worker.joinable())
            state_->worker.join();
    }

    bool DedicatedBookingDispatcher::submit(std::string command)
    {
        if (!state_ || command.empty())
            return false;
        {
            const std::lock_guard lock(state_->mutex);
            if (state_->stopping || state_->commands.size() >= 8)
                return false;
            state_->commands.push_back(std::move(command));
        }
        state_->ready.notify_one();
        return true;
    }
}
