#include "sv_zm_revive_hud_mp.hpp"
#include "sv_main_mp.hpp"
#include "sv_zm_power_motion_mp.hpp"
#include "sv_zm_perk_machines_mp.hpp"

#include <algorithm>
#include <charconv>
#include <chrono>
#include <cstring>
#include <cmath>
#include <iostream>
#include <limits>
#include <set>
#include <span>
#include <stdexcept>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

#include "../../shared/RuntimeLog.hpp"

namespace CodolGameServer
{
    namespace
    {
        using FrameClock = std::chrono::steady_clock;

        struct SvZmPerkMachine
        {
            std::string_view noteworthy;
            std::size_t word{};
            std::uint32_t mask{};
            std::uint32_t batteryUnits{};
        };

        // MEASURED FROM FACTORY, NOT COPIED FROM ANOTHER BUILD. In the retail
        // 7-31 Factory demo, use of trigger entities 259/256/263 adds bits
        // 23/24/22 respectively. mp_coperkstatstable rows 21..24 are the same
        // four specialties in armor/quick/fast/rof order, establishing rof as
        // the consecutive bit 25. The prompt literals are the battery prices.
        constexpr SvZmPerkMachine ZmPerkMachines[] = {
            { "specialty_armorvest", 0, 1u << 22u, 4 },
            { "specialty_quickrevive", 0, 1u << 23u, 2 },
            { "specialty_fastreload", 0, 1u << 24u, 3 },
            { "specialty_rof", 0, 1u << 25u, 2 },
        };

        const SvZmPerkMachine *zmPerkMachine(const SvMapTrigger &trigger)
        {
            if (trigger.targetname != "zombie_vending")
                return nullptr;
            const auto found = std::ranges::find(
                ZmPerkMachines, trigger.noteworthy,
                &SvZmPerkMachine::noteworthy);
            return found == std::ranges::end(ZmPerkMachines) ? nullptr : &*found;
        }

        constexpr std::uint32_t zmRawBatteryCost(
            const std::uint32_t displayUnits)
        {
            // battery_multiplier=1.2 in the retail demo. The client divides its
            // raw numerator by 1200 when it paints the battery counter.
            return displayUnits * 1200u;
        }

        std::uint64_t frameElapsedMicroseconds(
            const FrameClock::time_point start)
        {
            return static_cast<std::uint64_t>(
                std::chrono::duration_cast<std::chrono::microseconds>(
                    FrameClock::now() - start).count());
        }

        // AN INSTRUMENT THAT NAMES THE RIGHT SUSPECT, AND IS SILENT WHEN HEALTHY.
        //
        // beginFrame and endFrame both refuse by returning false, and both call sites
        // simply returned. A refusal publishes no playerStates, so the ONLY thing that
        // ever appeared in the log was the snapshot writer's
        // `failure=missing_playerstate` -- which is two layers downstream of the fault
        // and reads as "the snapshot is malformed" when the truth is "the world never
        // ran". Four hypotheses were built on that reading and all four died.
        //
        // Edge-triggered on the phase name: one line when a healthy server starts
        // refusing, one line when it recovers, nothing at 20 Hz in between. Pass an
        // empty name for "the frame completed".
        void reportWorldFrameRejection(const std::string_view phase)
        {
            static std::string current;
            if (current == phase)
                return;
            current = phase;
            if (phase.empty())
            {
                OlMod::RuntimeLog::write(
                    OlMod::RuntimeLog::Channel::GameServer,
                    "world frame publishing again");
                return;
            }
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer,
                "WORLD FRAME REJECTED in " + std::string(phase) +
                    " - nothing is published, so every snapshot will report "
                    "missing_playerstate. The fault is upstream: look for a native "
                    "entity mirror failure on the lines above.");
        }
    }

    bool SV_ShouldDiscardRejectedUserCmd(
        const SvClientThinkFailureStage stage)
    {
        // A NON-FATAL THINK FAILURE MUST NOT PIN THE QUEUE. When clientThink fails and the
        // stage is not listed here, the caller BREAKS without discarding, so the same
        // command is retried forever, commitExecutedUserCmd is never reached,
        // lastExecutedUserCmd stays empty (`cmdAge=-1`), pending stops draining and the
        // server's authoritative position can never follow the player -- which on screen is
        // a permanent snap back to the spawn point.
        //
        // This is also why fixing the pmove looked like it changed nothing.
        // NativePmoveNativeException was already listed, so while the pmove crashed on every
        // command the queue still drained. With the pmove working, the next failure in line
        // -- WeaponMovementRejected -- took over the jam instead, and the symptom was
        // identical.
        //
        // WeaponMovementRejected joins the list on the same grounds the
        // ClientEventsUnsupported branch below already states: a subsystem that is not
        // finished may refuse a command, and refusing a command must cost that command
        // rather than all movement after it. Remove it once weapon movement stops rejecting.
        //
        // THE THREE BELOW ARE PINS BY CONSTRUCTION, not by policy. Each compares the
        // command against something that cannot move while that command sits at the front
        // of the queue, so retrying it is a guaranteed infinite loop:
        //
        //   NonIncreasingCommandTime             cmd.commandTime <= ps.commandTime, and
        //   NativePmoveNonIncreasingCommandTime  ps.commandTime only advances when a
        //                                        command executes -- which this one cannot
        //   NativePmoveInvalidCommand            validNativeCommand() reads the command and
        //                                        nothing else
        //
        // This is also the reference behaviour, not a workaround. ClientThink_real clamps
        // cmd.serverTime into [level.time - 1000, level.time + 200] and then RETURNS when
        // `cmd.serverTime - ps.commandTime < 1`: the stale command was already consumed by
        // SV_ClientThink and is never replayed. The native pmove already carries the clamp
        // (MaximumBacklog); this is the consume half of the same contract.
        return stage == SvClientThinkFailureStage::ClientEventsRejected ||
            stage == SvClientThinkFailureStage::NativePmoveNativeException ||
            stage == SvClientThinkFailureStage::WeaponMovementRejected ||
            stage == SvClientThinkFailureStage::NonIncreasingCommandTime ||
            stage == SvClientThinkFailureStage::
                NativePmoveNonIncreasingCommandTime ||
            stage == SvClientThinkFailureStage::NativePmoveInvalidCommand;
    }

    std::uint32_t SV_ChargeClientThinkTime(
        const std::uint32_t cumulativeThinkTime,
        const std::uint32_t commandTime,
        const std::uint32_t playerCommandTime)
    {
        // CODREF(sv_process_client_thinks): Ghosts charges max(cmd.serverTime
        // - ps.commandTime, 0). Com_ServerPacketEvent 0x14019AE70 drains the
        // network packets and then invokes SV_ProcessClientThinks 0x1401F4450;
        // SV_BuildSnapshots 0x140205FB0 resets client_t.cumulThinkTime before
        // that client's snapshot cycle. The default budget is 100 ms.
        const auto delta = commandTime >= playerCommandTime
            ? commandTime - playerCommandTime
            : 0;
        return cumulativeThinkTime >
                std::numeric_limits<std::uint32_t>::max() - delta
            ? std::numeric_limits<std::uint32_t>::max()
            : cumulativeThinkTime + delta;
    }

    std::array<SvObjective, 32> SV_BuildSdObjectives(
        const std::span<const SvSdBombSite> sites,
        const SvTeam viewerTeam,
        const SvSdObjectiveMaterials &materials,
        const bool visible)
    {
        std::array<SvObjective, 32> objectives{};
        if (!visible || sites.size() != 2 ||
            (viewerTeam != SvTeam::Tf && viewerTeam != SvTeam::Sc))
        {
            return objectives;
        }
        const auto attacker = viewerTeam == SvTeam::Tf;
        objectives[0] = {
            .state = SvObjectiveState::Active,
            .origin = sites[0].origin,
            .icon = attacker ? materials.targetA : materials.defendA,
            .entityNum = EntityNumNone,
        };
        objectives[1] = {
            .state = SvObjectiveState::Active,
            .origin = sites[1].origin,
            .icon = attacker ? materials.targetB : materials.defendB,
            .entityNum = EntityNumNone,
        };
        return objectives;
    }

    std::array<SvObjective, 32> SV_BuildSdPlantedObjectives(
        const std::string_view siteLabel,
        const std::array<float, 3> &origin,
        const SvTeam viewerTeam,
        const SvSdObjectiveMaterials &materials,
        const bool visible)
    {
        std::array<SvObjective, 32> objectives{};
        if (!visible ||
            (viewerTeam != SvTeam::Tf && viewerTeam != SvTeam::Sc) ||
            (siteLabel != "_a" && siteLabel != "_b") ||
            !std::ranges::all_of(origin, [](const float value) {
                return std::isfinite(value);
            }))
        {
            return objectives;
        }
        const auto siteA = siteLabel == "_a";
        objectives[0] = {
            .state = SvObjectiveState::Active,
            .origin = origin,
            .icon = viewerTeam == SvTeam::Sc
                ? siteA ? materials.defuseA : materials.defuseB
                : siteA ? materials.defendA : materials.defendB,
            .entityNum = EntityNumNone,
        };
        return objectives;
    }

    bool SV_AddSdBombObjective(
        std::array<SvObjective, 32> &objectives,
        const SvSdBombPhase phase,
        const std::array<float, 3> &origin,
        const SvTeam viewerTeam,
        const SvSdObjectiveMaterials &materials,
        const bool visible)
    {
        if (!visible || viewerTeam != SvTeam::Tf ||
            (phase != SvSdBombPhase::Available &&
                phase != SvSdBombPhase::Dropped &&
                phase != SvSdBombPhase::Carried) ||
            !std::ranges::all_of(origin, [](const float value) {
                return std::isfinite(value);
            }))
        {
            return false;
        }
        const auto empty = std::ranges::find(
            objectives, SvObjectiveState::Empty, &SvObjective::state);
        if (empty == objectives.end())
            return false;
        *empty = {
            .state = SvObjectiveState::Active,
            .origin = origin,
            .icon = phase == SvSdBombPhase::Carried
                ? materials.escort
                : materials.bomb,
            .entityNum = EntityNumNone,
        };
        return true;
    }

    std::array<SvHudElem, 31> SV_BuildObjectiveHudElems(
        const std::array<SvObjective, 32> &objectives)
    {
        std::array<SvHudElem, 31> hudElems{};
        auto destination = hudElems.begin();
        for (const auto &objective : objectives)
        {
            if (objective.state == SvObjectiveState::Empty)
                continue;
            if (objective.state != SvObjectiveState::Active ||
                !objective.icon || destination == hudElems.end())
            {
                continue;
            }
            *destination++ = {
                .type = SvHudElemType::Waypoint,
                .origin = objective.origin,
                .targetEntNum = EntityNumNone,
                .materialIndex = objective.icon,
                // MEASURED, not ported. The dm demo's only world-coordinate
                // element with a material - which is what a waypoint is - reads
                // complete as:
                //
                //   TYPE=14  x=7924 y=2161 z=50  w=10 h=10  material=151
                //            targetEnt=2047  color=alpha25  flags=0x4000
                //
                // 10x10, not 8x8.
                .width = 10,
                .height = 10,
                // alpha 25 of the -85 codec's five bits, so 25*8 = 200. The
                // previous 0x80 was IW's "objpoints use half alpha", which is
                // a reasonable guess and not what this server sent.
                .color = 0xC8FFFFFFu,
                .value = 1.0f,
                // FLAGS ARE 0x4000, AND THE COMMENT THAT USED TO BE HERE SAID
                // THE OPPOSITE - CONFIDENTLY, WITH ADDRESSES.
                //
                // It read: "0x00BD8B12 test ecx,4000h / jnz default -> 0x4000
                // must be CLEAR on that path ... the previous value 0x4000
                // therefore failed twice". Every one of those addresses is a
                // 3.3.3.3 address. In out.exe the function containing them is
                // sub_BD7780, a dvar registrar that installs r_picmip and
                // r_specular - it has nothing to do with HUD drawing. The
                // reading was true of dest1yo's client and was imported here
                // unchecked, which is exactly what
                // codol-constants-are-unguarded-per-build warns about.
                //
                // A retail OLfinal server sets 0x4000 on its waypoint and its
                // client draws it. That is the only evidence about THIS build's
                // drawer that anyone has, and it says the imported rule is
                // inverted here.
                .flags = 0x4000,
            };
        }
        return hudElems;
    }

    std::uint32_t SV_CalculateDmMatchBonus(
        const std::uint16_t zeroBasedRank,
        const std::uint32_t participationMilliseconds,
        const bool placedTopThree)
    {
        // CODREF(IW4 _gamelogic.gsc/_rank.gsc):
        //   spm = (3 + ((rank + 1) * 0.5)) * 10 = 35 + 5*rank
        //   bonus = int(scale * spm * timePlayed / 60)
        // where FFA's top three use win scale 1 and everybody else loss scale
        // 0.5. Keep the half in the denominator so this stays exact integer
        // arithmetic. Retail's rank-29 recorder participating for just under
        // 600 seconds produces the independently decoded HudElem value 1799.
        const auto spmTimesTwo =
            70ull + 10ull * static_cast<std::uint64_t>(zeroBasedRank);
        const auto denominator = placedTopThree ? 120'000ull : 240'000ull;
        const auto value = spmTimesTwo * participationMilliseconds / denominator;
        return static_cast<std::uint32_t>(std::min<std::uint64_t>(
            value, std::numeric_limits<std::uint32_t>::max()));
    }

    bool SV_IsDmOutcomeTie(
        const std::uint32_t viewerClientNum,
        const std::span<const std::uint32_t> rankedClientNums,
        const std::span<const SvClientScore> rankedScores)
    {
        // CODREF(IW4 _hud_message.gsc::outcomeNotify): first and second both
        // receive TIE when their score and deaths match. Third receives TIE
        // when it matches first on the same pair. Players below the displayed
        // top three receive defeat even if a larger tie exists.
        if (rankedClientNums.size() < 2 || rankedScores.size() < 2)
            return false;
        const auto tiedWithFirst = [&rankedScores](const std::size_t place) {
            return place < rankedScores.size() &&
                rankedScores[0].score == rankedScores[place].score &&
                rankedScores[0].deaths == rankedScores[place].deaths;
        };
        if (tiedWithFirst(1) &&
            (viewerClientNum == rankedClientNums[0] ||
                viewerClientNum == rankedClientNums[1]))
        {
            return true;
        }
        return rankedClientNums.size() >= 3 &&
            viewerClientNum == rankedClientNums[2] && tiedWithFirst(2);
    }

    std::array<SvHudElem, 31> SV_BuildDmOutcomeHudElems(
        const std::span<const std::uint32_t> rankedClientNums,
        const std::optional<float> matchBonus,
        const std::uint32_t birthServerTime,
        const std::uint16_t titleText,
        const std::uint16_t reasonText)
    {
        std::array<SvHudElem, 31> hudElems{};
        auto destination = hudElems.begin();
        *destination++ = {
            .type = SvHudElemType::Text,
            .origin = { 0.0f, 20.0f, 0.0f },
            // Retail inherits the no-target sentinel in this reused slot. A
            // zero target names entity 0 and moves the title out of the
            // screen-space layout (observed live at the lower-left edge).
            .targetEntNum = EntityNumNone,
            .color = 0xFFFFFFFFu,
            .flags = 0x1,
            .alignOrg = 0x4,
            .alignScreen = 0x98,
            .fontScale = 3.0f,
            .font = 3,
            // Type 1 consumes this source slot as field 22 `text`, not field
            // 33 `label`; the writer performs that projection by type.
            .label = titleText,
            .glowColor = 0xFFB24D33u,
        };
        // The title carries the same pulse descriptor as the first-place
        // player name, except retail gives it soundID 1.
        (destination - 1)->materialIndex = 1;           // soundID
        (destination - 1)->width = 100;                 // fxLetterTime
        (destination - 1)->fadeStartTime = birthServerTime; // fxBirthTime
        (destination - 1)->scaleStartTime = 60'000;     // fxDecayStartTime
        (destination - 1)->scaleTime = 1'000;           // fxDecayDuration

        *destination++ = {
            .type = SvHudElemType::Text,
            .origin = { 0.0f, 66.0f, 0.0f },
            .targetEntNum = EntityNumNone,
            .color = 0xFFFFFFFFu,
            .flags = 0x1,
            .alignOrg = 0x4,
            .alignScreen = 0x98,
            .fontScale = 2.0f,
            .font = 3,
            .label = reasonText, // projected to field 22 `text`
            .glowColor = 0xFFB24D33u,
        };
        if (matchBonus)
        {
            *destination++ = {
                .type = SvHudElemType::Value,
                .origin = { 0.0f, 230.0f, 0.0f },
                .targetEntNum = EntityNumNone,
                .color = 0xFFFFFFFFu,
                .value = *matchBonus,
                .flags = 0x1,
                .alignOrg = 0x4,
                .alignScreen = 0x98,
                .fontScale = 2.0f,
                .font = 3,
                .label = SvDmMatchBonusLabel,
                .glowColor = 0xFF000000u,
            };
        }

        constexpr std::array<float, 3> PlacementY{ 110.0f, 154.0f, 192.0f };
        constexpr std::array<float, 3> PlacementScale{ 2.0f, 1.5f, 1.5f };
        constexpr std::array<std::uint32_t, 3> PlacementGlow{
            0xFF33B24Du, 0xFFB24D33u, 0xFFB24D33u };
        const auto count = std::min(rankedClientNums.size(), PlacementY.size());
        for (std::size_t place{}; place < count; ++place)
        {
            if (rankedClientNums[place] >= MaximumGameClients)
                continue;
            *destination++ = {
                .type = SvHudElemType::PlayerName,
                .origin = { 0.0f, PlacementY[place], 0.0f },
                .targetEntNum = EntityNumNone,
                .color = 0xFFFFFFFFu,
                .value = static_cast<float>(rankedClientNums[place]),
                .flags = 0x1,
                .alignOrg = 0x4,
                .alignScreen = 0x98,
                .fontScale = PlacementScale[place],
                .font = 3,
                // Type 3 never consumes these five ordinary drawing fields.
                // The writer aliases them to descriptor rows 28..32 so
                // SvHudElem, and therefore the address-sensitive native
                // WorldClientState node, does not grow.
                .fadeStartTime = birthServerTime,
                .scaleStartTime = 60'000,
                .scaleTime = 1'000,
                .label = SvDmPlacementLabels[place],
                .glowColor = PlacementGlow[place],
            };
            // These two aliases occur earlier than the fields above in the
            // aggregate declaration, so assign after construction rather than
            // violating C++ designated-initializer order.
            (destination - 1)->materialIndex =
                static_cast<std::uint16_t>(place + 2); // soundID
            (destination - 1)->width = 100;            // fxLetterTime
        }
        return hudElems;
    }

    std::array<SvHudElem, 31> SV_BuildFeedbackHudElems(
        const std::uint16_t markerMaterialIndex,
        const std::uint32_t markerStartTime,
        const std::optional<float> scorePopupValue,
        const std::uint32_t scoreStartTime,
        const std::uint32_t serverTime)
    {
        std::array<SvHudElem, 31> hudElems{};
        auto destination = hudElems.begin();
        if (markerMaterialIndex)
        {
            *destination++ = {
            .type = SvHudElemType::Icon,
            // Screen-space, not world-space. alignScreen mode 2 resolves both
            // axes to the screen centre (sub_B236A0 case 2 / sub_B237C0 case
            // 2), so the origin is an offset from the crosshair in the virtual
            // 640x480 units the client scales by 1.6 - resolution-independent.
            //
            // These are IW4 _damagefeedback.gsc's own two numbers, x = -12 and
            // y = -12 against a 24x48 shader with a top-left origin. Note the
            // vertical offset is a QUARTER of the height, not half: the mark
            // sits high in the material and the script hangs the rest below
            // the crosshair. Centring the whole box instead lifts the mark 12
            // units, which is exactly the "slightly above the crosshair"
            // placement this replaced.
            .origin = {
                -static_cast<float>(SvDamageFeedbackWidth) / 2.0f,
                -static_cast<float>(SvDamageFeedbackHeight) / 4.0f,
                0.0f,
            },
            // The icon drawer never reads targetEntNum; carry the same
            // "no target entity" sentinel the waypoint producer uses rather
            // than leaving a value that names entity 0.
            .targetEntNum = EntityNumNone,
            .materialIndex = markerMaterialIndex,
            // IW4 _damagefeedback.gsc: setShader("damage_feedback", 24, 48).
            // BO1 maps/_damagefeedback.gsc carries the same two numbers.
            .width = SvDamageFeedbackWidth,
            .height = SvDamageFeedbackHeight,
            // The END of the fade - sub_AB4490 lerps fromColor to color and
            // then holds here, so the marker finishes invisible.
            .color = SvFeedbackFadeToColor,
            // CODREF: same client filter the waypoint producer cites. Flags at
            // [elem+0A4h]: 0x00BD7C4C "test cl,1 / jz default" makes bit 0
            // mandatory, and 0x00BD7C55 "test cl,cl / js default" means this
            // drawer group only takes elems with bit 0x80 clear.
            .flags = 0x1,
            // Sub-index 0 on both axes -> flt_12F7860[0] = 0.0, so the client
            // subtracts nothing and the origin above is the elem's top-left
            // corner. That is the frame IW's x/y constants are written in;
            // letting alignOrg centre the box as well would apply the offset
            // twice.
            .alignOrg = 0x0,
            // High nibble = horizontal mode, low nibble = vertical mode.
            .alignScreen = 0x22,
            // IW4 runs fadeOverTime(1) on this elem; the retail demo shows the
            // same thing done on the wire, full alpha to nothing over 1000 ms.
            .fromColor = SvDamageFeedbackFromColor,
            .fadeStartTime = markerStartTime,
            .fadeTime = SvDamageFeedbackFadeMilliseconds,
            };
        }
        if (scorePopupValue)
        {
            // Which phase of the retail animation this frame lands in. The
            // client runs each lerp itself; the server just states the current
            // one, exactly as the retail server's own updates do.
            const auto elapsed = serverTime >= scoreStartTime
                ? serverTime - scoreStartTime
                : 0u;
            auto fromScale = SvScoreFeedbackSmallScale;
            auto toScale = SvScoreFeedbackLargeScale;
            auto scaleStart = scoreStartTime;
            auto scaleLength = SvScoreFeedbackGrowMilliseconds;
            if (elapsed >= SvScoreFeedbackGrowMilliseconds)
            {
                // The shrink window opens exactly where the grow window
                // closed, so the client's lerp hands 3.0 straight to the next
                // lerp and the number never jumps.
                fromScale = SvScoreFeedbackLargeScale;
                toScale = SvScoreFeedbackSmallScale;
                scaleStart = scoreStartTime + SvScoreFeedbackGrowMilliseconds;
                scaleLength = SvScoreFeedbackSettleMilliseconds;
            }
            // The fade only starts a full second in; before that the number
            // holds at its visible alpha with no fade window at all, because
            // sub_AB4490 takes the "duration <= 0" branch and uses `color`
            // directly.
            const auto fading = elapsed >= SvScoreFeedbackVisibleMilliseconds;
            *destination++ = {
                // Type 2 renders the value field through sub_BB4B70's
                // sprintf(ctx+276, 256, "%g", elem+128) at 0x00BB4E53. No
                // material, no width and no height: sub_BB4670 sizes a text
                // elem from the measured glyph run instead.
                .type = SvHudElemType::Value,
                .origin = { 0.0f, SvScoreFeedbackOffsetY, 0.0f },
                .targetEntNum = EntityNumNone,
                .color = fading
                    ? SvScoreFeedbackFadeToColor
                    : SvScoreFeedbackFromColor,
                .value = *scorePopupValue,
                .flags = 0x1,
                // Centre the number on the anchor in both axes. Unlike the
                // marker this really is a centring job, and for a text elem
                // the fraction multiplies the measured width, so a number that
                // grows from 100 to 1000 stays centred.
                .alignOrg = 0x5,
                .alignScreen = 0x22,
                .fontScale = toScale,
                // Retail's popup asserts no font, so it keeps the default
                // branch of sub_BB4B70's first switch: handle 0, factor 0.25.
                .font = 0,
                .fromColor = fading ? SvScoreFeedbackFromColor : 0u,
                .fadeStartTime = fading
                    ? scoreStartTime + SvScoreFeedbackVisibleMilliseconds
                    : 0u,
                .fadeTime = fading ? SvScoreFeedbackFadeMilliseconds : 0u,
                .fromFontScale = fromScale,
                .scaleStartTime = scaleStart,
                .scaleTime = scaleLength,
                .label = SvScoreFeedbackLabel,
                // Retail sets its third colour field to the same bytes at zero
                // alpha rather than leaving it whatever the slot last held.
                .glowColor = SvScoreFeedbackGlowColor,
                .sort = SvScoreFeedbackSort,
            };
        }
        return hudElems;
    }

    SvHudElem SV_BuildZmScoreHudElem(
        const std::optional<SvZmScoreFeedback> score, const std::uint32_t serverTime)
    {
        // CODREF(538B70,538250,514880): exact OLFinal native Value formatter,
        // label+952 then one-based localized lookup. Original Factory label385
        // resolves to MP_PLUS at constant type4/index384 in this loaded map.
        // Native recording: x30/y-50, grow100ms, settle200ms, hold1000/fade750.
        // Reuse the proven HUD transport/color projection, not MP's reward policy.
        const bool active=score && score->active && serverTime>=score->startedAt &&
            serverTime-score->startedAt<1750;
        auto elem=SV_BuildFeedbackHudElems(0,0,
            active?static_cast<float>(score->value):0.0f,
            active?score->startedAt:0,serverTime)[0];
        elem.origin[0]=30.0f;elem.label=385;
        if(active && serverTime-score->startedAt>=100)elem.scaleTime=200;
        if(!active)
        {
            // OLMOD(zm-score-slot-owner): invisible reservation keeps objective
            // slots stable while the score starts/expires; no invented visible0.
            elem.color=elem.fromColor=elem.glowColor=0;
            elem.fadeTime=0;elem.scaleTime=0;elem.fontScale=0.9f;
        }
        return elem;
    }

    bool SV_BeginSdBombRound(
        SvSdBombStatus &status,
        const std::uint32_t serverTime)
    {
        if (!status.configured || status.phase != SvSdBombPhase::Inactive ||
            status.sites.size() != 2)
        {
            return false;
        }
        status.phase = SvSdBombPhase::Available;
        status.carrierClientNum.reset();
        status.planterClientNum.reset();
        status.defuserClientNum.reset();
        status.plantedSiteLabel.reset();
        status.plantedOrigin.reset();
        status.phaseStartServerTime = serverTime;
        status.plantedServerTime = 0;
        return true;
    }

    bool SV_PickUpSdBomb(
        SvSdBombStatus &status,
        const std::uint32_t carrierClientNum,
        const std::uint32_t serverTime)
    {
        if (!status.configured ||
            (status.phase != SvSdBombPhase::Available &&
                status.phase != SvSdBombPhase::Dropped) ||
            serverTime < status.phaseStartServerTime)
        {
            return false;
        }
        status.phase = SvSdBombPhase::Carried;
        status.carrierClientNum = carrierClientNum;
        status.phaseStartServerTime = serverTime;
        return true;
    }

    bool SV_DropSdBomb(
        SvSdBombStatus &status,
        const std::uint32_t carrierClientNum,
        const std::uint32_t serverTime)
    {
        if (!status.configured || status.phase != SvSdBombPhase::Carried ||
            status.carrierClientNum != carrierClientNum ||
            serverTime < status.phaseStartServerTime)
        {
            return false;
        }
        status.phase = SvSdBombPhase::Dropped;
        status.carrierClientNum.reset();
        status.phaseStartServerTime = serverTime;
        return true;
    }

    bool SV_CommitSdBombPlant(
        SvSdBombStatus &status,
        const std::uint32_t planterClientNum,
        const std::string_view siteLabel,
        const std::array<float, 3> &plantedOrigin,
        const std::uint32_t serverTime)
    {
        const auto site = std::ranges::find(
            status.sites, siteLabel, &SvSdBombSite::label);
        if (!status.configured || status.phase != SvSdBombPhase::Carried ||
            !status.carrierClientNum ||
            *status.carrierClientNum != planterClientNum ||
            site == status.sites.end() ||
            !std::ranges::all_of(plantedOrigin, [](const float value) {
                return std::isfinite(value);
            }) ||
            serverTime < status.phaseStartServerTime)
        {
            return false;
        }
        status.phase = SvSdBombPhase::Planted;
        status.carrierClientNum.reset();
        status.planterClientNum = planterClientNum;
        status.plantedSiteLabel = std::string(siteLabel);
        status.plantedOrigin = plantedOrigin;
        status.phaseStartServerTime = serverTime;
        status.plantedServerTime = serverTime;
        return true;
    }

    bool SV_CommitSdBombDefuse(
        SvSdBombStatus &status,
        const std::uint32_t defuserClientNum,
        const std::uint32_t serverTime)
    {
        if (!status.configured || status.phase != SvSdBombPhase::Planted ||
            serverTime < status.plantedServerTime)
        {
            return false;
        }
        status.phase = SvSdBombPhase::Defused;
        status.defuserClientNum = defuserClientNum;
        status.phaseStartServerTime = serverTime;
        return true;
    }

    bool SV_AdvanceSdBombTimer(
        SvSdBombStatus &status,
        const SvSdBombRules &rules,
        const std::uint32_t serverTime)
    {
        if (!status.configured || status.phase != SvSdBombPhase::Planted ||
            !rules.bombMilliseconds || serverTime < status.plantedServerTime ||
            serverTime - status.plantedServerTime < rules.bombMilliseconds)
        {
            return false;
        }
        status.phase = SvSdBombPhase::Exploded;
        status.phaseStartServerTime = serverTime;
        return true;
    }

    std::optional<std::pair<SvTeam, SvSdRoundEndReason>>
        SV_EvaluateSdBombOutcome(const SvSdBombPhase phase)
    {
        if (phase == SvSdBombPhase::Defused)
            return std::pair{ SvTeam::Sc, SvSdRoundEndReason::BombDefused };
        if (phase == SvSdBombPhase::Exploded)
            return std::pair{ SvTeam::Tf, SvSdRoundEndReason::BombExploded };
        return std::nullopt;
    }

    std::optional<std::pair<SvTeam, SvSdRoundEndReason>>
        SV_EvaluateSdElimination(const SvSdEliminationState &state)
    {
        if (!state.attackers || !state.defenders)
            return std::nullopt;
        if (!state.attackersAlive && !state.defendersAlive)
        {
            return std::pair{
                state.bombPlanted ? SvTeam::Tf : SvTeam::Sc,
                SvSdRoundEndReason::SimultaneousElimination };
        }
        if (!state.attackersAlive && !state.bombPlanted)
        {
            return std::pair{
                SvTeam::Sc, SvSdRoundEndReason::AttackersEliminated };
        }
        if (!state.defendersAlive)
        {
            return std::pair{
                SvTeam::Tf, SvSdRoundEndReason::DefendersEliminated };
        }
        return std::nullopt;
    }

    std::optional<std::pair<SvTeam, SvSdRoundEndReason>>
        SV_EvaluateSdTimeLimit(
            const SvSdEliminationState &state,
            const std::uint32_t startedServerTime,
            const std::uint32_t currentServerTime,
            const std::uint32_t timeLimitMinutes)
    {
        // CODREF(sd_round_timer): IW4 sd.gsc and Ghosts sd.gsc both route the
        // mode timer through onTimeLimit. Planting pauses that timer and uses
        // the bomb end time instead, so this is round policy, not match policy.
        if (!startedServerTime || !timeLimitMinutes || state.bombPlanted ||
            currentServerTime < startedServerTime)
        {
            return std::nullopt;
        }
        const auto timeLimitMilliseconds =
            static_cast<std::uint64_t>(timeLimitMinutes) * 60u * 1000u;
        if (currentServerTime - startedServerTime < timeLimitMilliseconds)
            return std::nullopt;
        return std::pair{ SvTeam::Sc, SvSdRoundEndReason::TimeLimit };
    }

    std::optional<std::pair<SvTeam, SvSdRoundEndReason>>
        SV_EvaluateSdRoundOutcome(
            const SvSdBombPhase bombPhase,
            const SvSdEliminationState &state,
            const std::uint32_t startedServerTime,
            const std::uint32_t currentServerTime,
            const std::uint32_t timeLimitMinutes)
    {
        if (const auto bomb = SV_EvaluateSdBombOutcome(bombPhase))
            return bomb;
        if (const auto elimination = SV_EvaluateSdElimination(state))
            return elimination;
        return SV_EvaluateSdTimeLimit(
            state, startedServerTime, currentServerTime, timeLimitMinutes);
    }

    bool SV_UpdateMatchTimeLimit(
        SvMatchStatus &status,
        const std::string_view gameType,
        const std::uint32_t currentServerTime,
        const std::int32_t tfScore,
        const std::int32_t scScore)
    {
        status.elapsedMilliseconds = status.startServerTime &&
                currentServerTime >= status.startServerTime
            ? currentServerTime - status.startServerTime
            : 0;
        // SD owns a fresh timer for every round. Treating scr_sd_timelimit as
        // this match-level limit prevents all later rounds from completing.
        // ZM HAS NO MATCH CLOCK AT ALL, and the booking hands zombies the MP
        // limits anyway. MEASURED, every full-length zm session in
        // CodolGameServer.log:
        //
        //   match complete gametype=zm reason=timeLimit elapsed=600000ms
        //       limitMinutes=10 scoreLimit=30 best=client0:0
        //   ui screen podium ui -> s ui_match_complete "1"
        //   match ended gametype=zm t="EXE_MATCHENDED"
        //   client timeout client=0
        //
        // This fired at exactly ten minutes of match clock, pushed the podium,
        // and left the player on the end-of-match screen waiting for a round
        // that never comes -- join-to-drop 10:51 (600s of clock plus the
        // pre-match load) on EVERY clean session going back to the oldest one
        // in the log, with the client's packet counter frozen from that
        // moment. Zombies ends when the players die, not on a timer.
        //
        // The limits cannot be zeroed at the booking instead:
        // DedicatedSession::valid rejects rules carrying no limits and the
        // whole booking is refused. Gating the evaluator also leaves
        // ui_timelimit and the gamestate fixture byte-identical, which zeroing
        // the rules would not.
        if (!status.configured || status.completed || gameType == "sd" ||
            gameType == "zm" || !status.startServerTime ||
            !status.rules.timeLimitMinutes)
        {
            return false;
        }
        const auto timeLimitMilliseconds =
            static_cast<std::uint64_t>(status.rules.timeLimitMinutes) *
            60u * 1000u;
        if (status.elapsedMilliseconds < timeLimitMilliseconds)
            return false;
        status.completed = true;
        status.endReason = SvMatchEndReason::TimeLimit;
        status.winner = tfScore == scScore
            ? SvTeam::None
            : tfScore > scScore ? SvTeam::Tf : SvTeam::Sc;
        return true;
    }

    SvAnnouncerCues SV_UpdateMatchAnnouncer(
        SvAnnouncerState &state,
        const std::string_view gameType,
        const SvMatchStatus &status,
        const std::uint32_t currentServerTime)
    {
        SvAnnouncerCues cues{};
        // FREE-FOR-ALL IS THE ONLY GAMETYPE THIS IS MEASURED FOR. Both demos
        // are dm and both open with `uk_1mc_free_for_all`; a team mode opens
        // with a line this project has not decoded, and guessing one would put
        // "free for all" over a team match.
        if (!status.configured || gameType != "dm" || !status.startServerTime)
            return cues;
        // A DECIDED MATCH IS SILENT. The end-of-match schedule owns the screen
        // and the speakers from here (section 140d), and the victory/defeat
        // stinger goes out on the completion transition instead.
        if (status.completed)
            return cues;
        if (currentServerTime < status.startServerTime)
            return cues;
        const auto elapsed = currentServerTime - status.startServerTime;
        if (!state.matchStartSent)
        {
            state.matchStartSent = true;
            cues.matchStart = true;
        }
        if (!state.timesUpSent && status.rules.timeLimitMinutes)
        {
            const auto limit =
                static_cast<std::uint64_t>(status.rules.timeLimitMinutes) *
                60u * 1000u;
            // NOT `remaining == 30000`. A frame is 50 ms and the clock is
            // sampled, so an equality test fires on no frame at all in most
            // matches - the countdown is due once the remaining time has
            // FALLEN THROUGH the mark, which is also what makes a late-starting
            // clock or a paused frame still announce.
            if (elapsed + SvAnnouncerTimesUpRemainingMs >= limit)
            {
                state.timesUpSent = true;
                cues.timesUp = true;
            }
        }
        return cues;
    }

    ServerCore::ServerCore(
        SvClientSystem::GameStateBuilder gameStateBuilder,
        SvClientSystem::SnapshotBuilder snapshotBuilder,
        SvScriptBuiltinRegistry::ModelResolver modelResolver,
        SvScriptBuiltinRegistry::WeaponResolver weaponResolver,
        SvScriptBuiltinRegistry::SoundResolver soundResolver)
        : clients_(
            18, 30'000, std::move(gameStateBuilder), std::move(snapshotBuilder)),
          // COPIED, then moved on. See the member's declaration.
          modelResolver_(modelResolver),
          factorySoundResolver_(soundResolver),
          scriptBuiltins_(world_, {
              .addClientScore = [this](const auto clientNum, const auto delta) {
                  return addClientScore(clientNum, delta);
              },
              .addClientXp = [this](const auto clientNum, const auto delta) {
                  return addClientXp(clientNum, delta);
              },
              .addTeamScoreForClient = [this](const auto clientNum, const auto delta) {
                  return addTeamScoreForClient(clientNum, delta);
              },
              .addKillForClient = [this](const auto clientNum, const auto delta) {
                  return addKillForClient(clientNum, delta);
              },
          },
          // NOT WRAPPED TO PUBLISH THE MODEL CONFIGSTRING HERE. That was tried
          // and it BROKE JOINING: publishing cs 2876 at first-zombie-spawn time
          // (plus its `|` precache) left the client unable to enter --
          // 无法加入游戏会话, "unable to join game session", reproduced twice.
          // publishActorModelConfigString still exists and works (the log shows
          // `actor model PUBLISHED index=308 cs=2876 name=c_zom_ger_body1`), so
          // the mechanism is fine and the TIMING is what is wrong: retail carries
          // its model band IN THE GAMESTATE -- Appmain's brushmodel census notes
          // retail zm_factory_sh sending 34 of them at cs 2979/2980 and
          // 2995..3026 -- i.e. before any client connects, not mid-session.
          // See re/demo-re/20-zm-actor-lifecycle.md 12.21.
          modelResolver,
          weaponResolver,
          // The zone model lives on ServerCore, not in SvServerWorld: it is map data
          // parsed once at world spawn, not per-frame world state.
          [this] { return zmZones(); },
          // precachemodel(name). Resolves through the SAME resolver zmspawnactor
          // uses, so the published index and the index that goes out in the agent
          // element are the same number by construction -- an allocated slot would
          // disagree and the client would resolve a different name.
          [this, resolve = modelResolver](const std::string &name) {
              if (!resolve)
                  return false;
              const auto index = resolve(name);
              if (!index)
                  return false;
              return publishActorModelConfigString(*index, name);
          },
          {
              .sendServerCommand = [this](
                  const std::uint32_t clientNum,
                  const std::string_view command) {
                  return clients_.queueReliableCommand(
                      clientNum, std::string(command));
              },
              .setConfigString = [this](
                  const std::uint16_t index,
                  const std::string_view value) {
                  static_cast<void>(clients_.SV_SetConfigString(
                      index, std::string(value)));
                  const auto stored = clients_.configString(index);
                  return stored && *stored == value;
              },
              .finishMission = [this] {
                  return finishCampaignMissionFromScript();
              },
          }, std::move(soundResolver)),
          scriptRuntime_(scriptBuiltins_)
    {
        world_.setReliableCommandSender(
            [this](const std::uint32_t clientNum, const std::string &command) {
                return clients_.queueReliableCommand(clientNum, command);
            });
        world_.setClientImpactsScriptDispatcher(
            [this](const SvClientImpactScriptNotificationBatch &notifications) {
                static_cast<void>(
                    scriptRuntime_.dispatchTouchNotifications(notifications));
            });
    }

    std::uint32_t SV_FrameMilliseconds()
    {
        // Read once. This decides the server's whole cadence, so it must not be
        // able to change under a running match.
        static const std::uint32_t milliseconds = [] {
            // 50 STILL, AND 100 IS PROVEN -- OLMOD_SV_FRAME_MS=100. See the block below.
            //
            // Retail's cadence IS 100 ms -- measured 2026-09-05 by decoding both sides with the
            // same tool: retail 6160 snapshots / 621.4 s = 9.9/s against ours at 19.9/s, exactly
            // double, which is also why a match dies at ~55 minutes on a 16-bit sequence
            // (codol-a-match-dies-at-65536-packets). All of that still stands.
            //
            // IT WAS TRIED LIVE AND THE PLAYER FELT IT IMMEDIATELY: "movement feels somewhat
            // faster, but not as smooth, it kind of jerks me because the server needs to keep up
            // with my fast directional changes." Confirmed at 8.1 snapshots/s measured on the
            // client, so the cadence really was live, and the log said why:
            //
            //     pending=8   cmdAge=143..155   thinkCommands=257..300
            //
            // pending 8 IS the queue capacity, and cmdAge ~150 ms is the server executing input
            // a seventh of a second old.
            //
            // THE CAUSE IS A COUPLED CONSTANT I MOVED ALONE. SV_ChargeClientThinkTime spends a
            // fixed 100 ms budget of simulated command time per snapshot cycle -- Ghosts' default,
            // paired with Ghosts' tick rate. At a 50 ms frame that is 100 ms of budget every
            // 50 ms, TWICE real time, and the headroom is what absorbs a burst of commands. At a
            // 100 ms frame it is 100 ms every 100 ms: exactly real time, no headroom at all. A
            // fast direction change produces a burst, and the burst has nowhere to go.
            //
            // So the frame interval and the think budget are one decision, not two, and BOTH
            // coupled constants have since moved:
            //
            //   PendingUserCmdCapacity          8 -> 32   CODOL's own MAX_PACKET_USERCMDS, read
            //                                             off CL_WritePacket 0x005B2C10
            //   SV_ClientThinkBudgetMilliseconds  -> 0 (drain the bounded queue)
            //
            // The larger queue was byte-for-byte inert at 50 because it peaked at 7 of 8
            // across every runtime-perf sample. Removing the artificial budget now matches
            // CODOL's command loop and prevents a remote burst from carrying into later frames.
            //
            // MEASURED AT 100 WITH BOTH MOVED, 2026-09-06, before the player was asked anything:
            //
            //   cadence       50 frames per 5 s window = 10.0/s   (retail's own 9.9/s)
            //   pending       mean 6.7, MAX 19        -- against max EXACTLY 8 in the run that
            //                                            felt bad, because 8 was the ceiling and
            //                                            everything above it was being deleted
            //   dropped       12, ALL of them inside the world-spawn stall, and ZERO since;
            //                 earlier runs reached 1009
            //   cmdAge        mean 168 ms, max 550 -- inside the 50 ms runs' own band of
            //                 120..316 mean, whose max spikes were 9-12 SECONDS
            //
            // and only then: "this feels good compared to what i experienced last time. repeated
            // movements left to right actually feel good and not like the same complaint."
            //
            // That is the same player and the same test that produced the complaint at the top of
            // this comment. Retail's cadence also halves our snapshot rate, which is the whole of
            // codol-a-match-dies-at-65536-packets: 110 minutes to the 16-bit wrap instead of 55.
            //
            // KNOWN AND LEFT: world spawn stalls the frame ~76 ms (prepareUs 71,723) and about a
            // dozen commands overflow even 32 there. It is one burst at spawn, not a steady leak.
            //
            // SO WHY IS THE DEFAULT STILL 50? Because the suite encodes a 50 ms TIMELINE, not
            // just the constant. Flipping the default was tried here and immediately failed three
            // tests in a row -- the scheduler recursion guard, its residual drain, and the SD
            // round-arming integration test -- because they advance a fixed number of
            // onComFrame calls and assert a specific serverTime. Two of those are now scaled off
            // SV_FrameMilliseconds() and are honest at any frame; the integration timelines are
            // not, and patching them one failure at a time is how a test stops measuring the
            // thing it names. That sweep is its own piece of work, deliberately not done in the
            // middle of a live match.
            //
            // Until then 100 is a one-variable decision and it is fully measured:
            //     OLMOD_SV_FRAME_MS=100   set INSIDE the elevated process that runs
            //                             host-nuked.ps1, never in a caller of it.
            constexpr std::uint32_t fallback = 100;
            std::size_t length{};
            char value[16]{};
            if (getenv_s(&length, value, sizeof(value), "OLMOD_SV_FRAME_MS") != 0 ||
                length == 0)
            {
                return fallback;
            }
            std::uint32_t parsed{};
            const auto *first = value;
            const auto *last = value + std::strlen(value);
            const auto &[pointer, error] = std::from_chars(first, last, parsed);
            if (error != std::errc{} || pointer != last || parsed < 1 || parsed > 1000)
                return fallback;
            return parsed;
        }();
        return milliseconds;
    }

    std::uint32_t SV_ClientThinkBudgetMilliseconds()
    {
        // Read once, for the same reason SV_FrameMilliseconds is: this must not
        // change under a running match.
        static const std::uint32_t milliseconds = [] {
            std::size_t length{};
            char value[16]{};
            if (getenv_s(&length, value, sizeof(value), "OLMOD_SV_THINK_BUDGET_MS") == 0 &&
                length != 0)
            {
                std::uint32_t parsed{};
                const auto *first = value;
                const auto *last = value + std::strlen(value);
                const auto &[pointer, error] = std::from_chars(first, last, parsed);
                // 0 is meaningful: no budget, drain the bounded queue.
                if (error == std::errc{} && pointer == last && parsed <= 10000)
                    return parsed;
            }
            // CODOL has no separate think budget. The queue is hard-bounded at
            // 32 commands, so drain the received burst this frame instead of
            // carrying a high-ping player's input into another 100 ms frame.
            return 0u;
        }();
        return milliseconds;
    }

    FixedFrameScheduler::FixedFrameScheduler(const std::uint32_t frameMilliseconds)
        : frameMilliseconds_(frameMilliseconds)
    {
        if (!frameMilliseconds_)
            throw std::invalid_argument("server frame duration must be non-zero");
    }

    std::uint32_t FixedFrameScheduler::advance(
        const std::uint32_t nowMilliseconds,
        const std::function<void(std::uint32_t)> &runFrame)
    {
        if (!initialized_)
        {
            previousMilliseconds_ = nowMilliseconds;
            initialized_ = true;
            return 0;
        }

        auto elapsed = nowMilliseconds - previousMilliseconds_;
        previousMilliseconds_ = nowMilliseconds;
        elapsed = std::min(elapsed, 500u);
        residualMilliseconds_ += elapsed;

        if (residualMilliseconds_ < frameMilliseconds_)
            return 0;

        // CODREF(sv_frame): BO2 SV_FrameInternal 0x006F91C0 and Ghosts
        // 0x1401FA4B0 fold all complete 50 ms residual slices into the target
        // level time, then wake the server exactly once. BO1 0x007159E0 is the
        // older branch that waits/runs once per residual slice in one call.
        // CODDIFF(sv_frame): ol-mod currently has no independent server thread,
        // so retain the residual but execute at most one complete world frame
        // per host callback. This prevents a slow frame from recursively
        // multiplying gameplay, native mirror and snapshot work while keeping
        // every authoritative 50 ms step available to later callbacks.
        residualMilliseconds_ -= frameMilliseconds_;
        runFrame(frameMilliseconds_);
        return 1;
    }

    void FixedFrameScheduler::reset()
    {
        previousMilliseconds_ = 0;
        residualMilliseconds_ = 0;
        initialized_ = false;
    }

    void ServerCore::setEnabled(const bool enabled)
    {
        const std::lock_guard lock(mutex_);
        if (status_.enabled == enabled)
            return;
        // THIS TRANSITION WIPES EVERY CONNECTED CLIENT -- clients_.reset() is thirteen lines
        // below. A client that connected before it lands keeps sending on a slot that no longer
        // exists, and the only symptom is "netchan packet has no connected client slot" with
        // nothing to say the server threw the slot away. Say it.
        OlMod::RuntimeLog::write(
            OlMod::RuntimeLog::Channel::GameServer,
            std::string("server enabled ") +
                (status_.enabled ? "true" : "false") + " -> " +
                (enabled ? "true" : "false") +
                "; RESETTING every connected client, connectedClients was " +
                std::to_string(status_.connectedClients));
        status_ = {
            .enabled = enabled,
            .sessionConfigured = dtlsConfig_.configured(),
            .gameStateConfigured = clients_.gameStateConfigured(),
        };
        connectionlessDiagnostics_ = {};
        scheduler_.reset();
        static_cast<void>(frameTotalTiming_.take());
        static_cast<void>(framePrepareTiming_.take());
        static_cast<void>(frameBeginWorldTiming_.take());
        static_cast<void>(frameClientThinkTiming_.take());
        static_cast<void>(frameModeTiming_.take());
        static_cast<void>(frameEndAndPublishTiming_.take());
        frameClientThinkCommands_ = 0;
        clients_.reset();
        world_.reset();
        livingWeaponRightTagInitialized_ = false;
        scriptRuntime_.reset();
        hintStringSlots_.clear();
        cursorHintTrigger_.clear();
        lootHintTarget_.clear();
        lootActivateHeld_.clear();
        mapTriggerHintTarget_.clear();
        barrierRepairHintTarget_.clear();
        zmUseActivateHeld_.clear();
        factoryAmmoHolds_.clear();
        zmRepairReadyTime_.clear();
        openedMapTriggers_.clear();
        zmPowerOn_ = false;
        matchStatus_ = {};
        // A NEW MATCH IS A NEW ANNOUNCER. Leaving matchStartSent set
        // would make the second match of a session open in silence, and
        // leaving `leader` set would suppress the first lead change.
        announcer_ = {};
        battleChatterSpeakers_.clear();
        battleChatterSequence_.clear();
        battleChatterVoiceFemale_.clear();
        matchCompletionAnnounced_ = false;
        matchCompletionServerTime_ = 0;
        matchEndedAnnounced_ = false;
        outroVisionAnnounced_ = false;
        outroScreenAsked_ = false;
        podiumScreenAsked_ = false;
        podiumRosterAsked_ = false;
        podiumWeaponsAsked_ = false;
        podiumCameraLogged_ = false;
        podiumFiguresSpawned_ = false;
        podiumAnimations_ = {};
        podiumAnimationEvent_ = 0;
        podiumCameraEntity_.reset();
        podiumCameraMotionContinued_ = false;
        matchEndFreezeLogged_ = false;
        matchEndScoresAsked_ = false;
        world_.clearMatchEndFreeze();
        world_.setMatchCompleted(false);
        soundAliasesAssigned_ = false;
        perkLives_.clear();
        uiClientLife_.clear();
        equipmentLives_.clear();
        uavOwners_.clear();
        firstBloodAwarded_ = false;
        dmMatchBonuses_.clear();
        sdRoundStatus_ = {};
        sdBombStatus_ = {};
        sdBombPickupTrigger_.reset();
        sdBombPickupHomeOrigin_ = {};
        sdBombSiteRuntime_.clear();
        sdBombVisualHandle_.reset();
        useObjects_.reset();
        sdSoundPresentation_ = {};
        sdSoundQueues_.clear();
        sdSoundReadyTime_.clear();
        sdRoundStartAnnounced_ = false;
        sdTfLastAliveAnnounced_ = false;
        sdScLastAliveAnnounced_ = false;
        sdPreviousTfAlive_ = 0;
        sdPreviousScAlive_ = 0;
        sdSideSwitchPending_ = false;
        matchGameType_.clear();
        matchMapName_.clear();
        visionAnnounced_.clear();
        factoryEntries_.clear();
        factoryEntryEnabled_ = false;
        factoryClockMaterials_={};
        factoryInteractablesEnabled_=false;factoryBox_={};
        factoryTeleportersEnabled_=false;factoryBo1TravelEnabled_=false;factoryTeleporters_={};factoryTeleporterResources_={};factoryTeleportEffects_.clear();
        factoryBoxResources_={};
        factorySounds_.clear();factoryInteractionHintCache_.clear();
        resolvedLoadouts_.clear();
        matchParticipation_.clear();
        dtlsPeers_.reset();
        dtlsPeerDiagnostics_.clear();
        dtlsRejectDiagnostics_.clear();
        dtlsNatDiagnostics_.clear();
        plaintextDiagnostics_.clear();
        netchanRejectDiagnostics_.clear();
    }

    std::vector<SvOutboundPacket> ServerCore::onComFrame(
        const std::uint32_t nowMilliseconds)
    {
        const std::lock_guard lock(mutex_);
        if (!status_.enabled)
            return {};
        std::vector<SvOutboundPacket> outbound;
        static_cast<void>(clients_.SV_CheckTimeouts(nowMilliseconds));
        // Headless bring-up: pick a class for anyone who has not, so a test cycle can
        // reach a spawned player with nobody at the keyboard. No-op unless
        // OLMOD_AUTO_LOADOUT=1; see SvClientSystem::autoSelectMissingLoadouts.
        // OLMOD(factory-class-confirmation): the retail Factory join requests
        // changeclass_marines before Playing. Never let the diagnostic automatic
        // class pick bypass that confirmation, even if the host sets AUTO_LOADOUT.
        if (!factoryEntryEnabled_)
            static_cast<void>(clients_.autoSelectMissingLoadouts(nowMilliseconds));
        scheduler_.advance(nowMilliseconds, [this](const auto frameMilliseconds) {
            runFrame(frameMilliseconds);
        });
        for (auto &message : clients_.SV_SendClientMessages(nowMilliseconds))
        {
            auto data = dtlsPeers_.NET_DtlsBuildData(message.peer, message.plaintext);
            if (!data.empty())
            {
                outbound.push_back({
                    .peer = message.peer,
                    .data = std::move(data),
                });
            }
        }
        status_.snapshotMessagesSent = clients_.snapshotMessagesSent();
        status_.fullSnapshotMessagesSent = clients_.fullSnapshotMessagesSent();
        status_.deltaSnapshotMessagesSent = clients_.deltaSnapshotMessagesSent();
        status_.messageAcknowledge = clients_.latestMessageAcknowledge();
        status_.outgoingSequence = clients_.latestOutgoingSequence();
        status_.connectedClients = static_cast<std::uint32_t>(
            clients_.connectedClientCount());
        status_.clientsReadyForGameState = static_cast<std::uint32_t>(
            clients_.gameStateReadyClientCount());
        status_.activeClients = static_cast<std::uint32_t>(clients_.activeClientCount());
        return outbound;
    }

    ConnectionlessResult ServerCore::SV_ConnectionlessPacket(
        const PeerAddress peer,
        const std::span<const std::uint8_t> packet,
        const std::uint32_t nowMilliseconds,
        const std::uint32_t entropy)
    {
        const std::lock_guard lock(mutex_);
        if (!status_.enabled)
            return {};
        auto result = clients_.SV_ConnectionlessPacket(
            peer, packet, nowMilliseconds, entropy);
        if (result.kind != ConnectionlessResultKind::Ignored)
            ++connectionlessDiagnostics_.handled;
        if (result.kind == ConnectionlessResultKind::Connected)
        {
            ++connectionlessDiagnostics_.connected;
            connectionlessDiagnostics_.lastConnectedPeer = peer;
            connectionlessDiagnostics_.lastConnectedClientSlot =
                static_cast<std::uint32_t>(result.clientSlot);
        }
        else if (result.kind == ConnectionlessResultKind::Rejected)
        {
            ++connectionlessDiagnostics_.rejected;
            connectionlessDiagnostics_.lastRejectedPeer = peer;
            connectionlessDiagnostics_.lastRejectedReason = result.reason;
        }
        status_.connectedClients = static_cast<std::uint32_t>(
            clients_.connectedClientCount());
        status_.gameStateMessagesSent = clients_.gameStateMessagesSent();
        status_.clientsReadyForGameState = static_cast<std::uint32_t>(
            clients_.gameStateReadyClientCount());
        status_.activeClients = static_cast<std::uint32_t>(clients_.activeClientCount());
        status_.gameStateUpdatesReceived = clients_.gameStateUpdatesReceived();
        status_.snapshotMessagesSent = clients_.snapshotMessagesSent();
        status_.fullSnapshotMessagesSent = clients_.fullSnapshotMessagesSent();
        status_.deltaSnapshotMessagesSent = clients_.deltaSnapshotMessagesSent();
        status_.messageAcknowledge = clients_.latestMessageAcknowledge();
        status_.outgoingSequence = clients_.latestOutgoingSequence();
        return result;
    }

    DtlsPacketResult ServerCore::NET_DtlsPacket(
        const PeerAddress peer,
        const std::span<const std::uint8_t> packet,
        const std::uint32_t nowMilliseconds,
        const std::uint32_t entropy)
    {
        const std::lock_guard lock(mutex_);
        if (!status_.enabled || !dtlsConfig_.configured())
            return {};

        auto result = dtlsPeers_.NET_DtlsPacket(
            peer, packet, dtlsConfig_.securityKey(), nowMilliseconds, entropy);
        const auto peerKey = static_cast<std::uint64_t>(peer.ipv4) << 16 | peer.port;
        const auto state = dtlsPeers_.peerState(peer);
        const auto packetType = packet.empty()
            ? 0u
            : static_cast<unsigned int>(packet.front());
        const auto previous = dtlsPeerDiagnostics_.find(peerKey);
        const auto emitNat = packetType == 0x0D && dtlsNatDiagnostics_[peerKey]++ < 4;
        if (emitNat || previous == dtlsPeerDiagnostics_.end() || previous->second != state)
        {
            dtlsPeerDiagnostics_[peerKey] = state;
            const char *stateName = "empty";
            if (state == DtlsPeerState::CookieIssued)
                stateName = "cookie-issued";
            else if (state == DtlsPeerState::Established)
                stateName = "established";
            std::clog << "[dedicated/game-server] dtls peer="
                      << peer.ipv4 << ':' << peer.port
                      << " packetType="
                      << packetType
                      << " state=" << stateName
                      << " replyBytes=" << result.reply.size() << '\n';
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer,
                "dtls peer=" + std::to_string(peer.ipv4) + ":" +
                    std::to_string(peer.port) + " packetType=" +
                    std::to_string(packetType) + " state=" + stateName +
                    " replyBytes=" + std::to_string(result.reply.size()));
        }
        if (result.kind == DtlsPacketResultKind::Rejected)
        {
            const auto diagnostic = std::to_string(
                packet.empty() ? 0u : static_cast<unsigned int>(packet.front())) +
                ":" + result.reason;
            const auto found = dtlsRejectDiagnostics_.find(peerKey);
            if (found == dtlsRejectDiagnostics_.end() || found->second != diagnostic)
            {
                dtlsRejectDiagnostics_[peerKey] = diagnostic;
                std::clog << "[dedicated/game-server] dtls rejected peer="
                          << peer.ipv4 << ':' << peer.port
                          << " packetType="
                          << packetType
                          << " reason=" << result.reason << '\n';
                OlMod::RuntimeLog::write(
                    OlMod::RuntimeLog::Channel::GameServer,
                    "dtls rejected peer=" + std::to_string(peer.ipv4) + ":" +
                        std::to_string(peer.port) + " packetType=" +
                        std::to_string(packetType) + " reason=" + result.reason);
            }
        }
        if (result.kind != DtlsPacketResultKind::AuthenticatedData)
            return result;

        std::vector<std::uint8_t> plaintextReply;
        const auto connectionlessPacket = NET_IsConnectionlessPacket(result.plaintext);
        if (plaintextDiagnostics_[peerKey]++ < 4)
        {
            std::clog << "[dedicated/game-server] plaintext peer="
                      << peer.ipv4 << ':' << peer.port
                      << " bytes=" << result.plaintext.size()
                      << " oob=" << connectionlessPacket
                      << " prefix=";
            for (std::size_t index{}; index < std::min<std::size_t>(4, result.plaintext.size()); ++index)
                std::clog << (index ? ":" : "")
                          << static_cast<unsigned int>(result.plaintext[index]);
            std::clog << '\n';
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer,
                "plaintext peer=" + std::to_string(peer.ipv4) + ":" +
                    std::to_string(peer.port) + " bytes=" +
                    std::to_string(result.plaintext.size()) + " oob=" +
                    std::to_string(connectionlessPacket ? 1 : 0));
        }
        if (connectionlessPacket)
        {
            auto connectionless = clients_.SV_ConnectionlessPacket(
                peer, result.plaintext, nowMilliseconds, entropy);
            if (connectionless.kind != ConnectionlessResultKind::Ignored)
                ++connectionlessDiagnostics_.handled;
            if (connectionless.kind == ConnectionlessResultKind::Connected)
            {
                ++connectionlessDiagnostics_.connected;
                connectionlessDiagnostics_.lastConnectedPeer = peer;
                connectionlessDiagnostics_.lastConnectedClientSlot =
                    static_cast<std::uint32_t>(connectionless.clientSlot);
                std::clog << "[dedicated/game-server] connectionless connected peer="
                          << peer.ipv4 << ":" << peer.port
                          << " slot=" << connectionless.clientSlot << '\n';
                OlMod::RuntimeLog::write(
                    OlMod::RuntimeLog::Channel::GameServer,
                    "connectionless connected peer=" + std::to_string(peer.ipv4) +
                        ":" + std::to_string(peer.port) + " slot=" +
                        std::to_string(connectionless.clientSlot));
            }
            else if (connectionless.kind == ConnectionlessResultKind::Rejected)
            {
                ++connectionlessDiagnostics_.rejected;
                connectionlessDiagnostics_.lastRejectedPeer = peer;
                connectionlessDiagnostics_.lastRejectedReason =
                    connectionless.reason;
                std::clog << "[dedicated/game-server] connectionless rejected peer="
                          << peer.ipv4 << ":" << peer.port
                          << " reason=" << connectionless.reason << '\n';
                OlMod::RuntimeLog::write(
                    OlMod::RuntimeLog::Channel::GameServer,
                    "connectionless rejected peer=" + std::to_string(peer.ipv4) +
                        ":" + std::to_string(peer.port) + " reason=" +
                        connectionless.reason);
            }
            plaintextReply = std::move(connectionless.reply);
        }
        else
        {
            auto clientPacket = clients_.SV_PacketEvent(
                peer, result.plaintext, nowMilliseconds);
            plaintextReply = std::move(clientPacket.reply);
            if (clientPacket.kind == NetchanProcessKind::Accepted)
            {
                ++status_.netchanPacketsReceived;
                status_.reliableCommandsReceived += static_cast<std::uint32_t>(
                    clientPacket.reliableCommands.size());
                // ALT-FIRE ARRIVES HERE, AS A COMMAND, NOT AS A BUTTON.
                //
                // The player's controls call it "Weapon Attachments" and bind
                // it to 3, beside the killstreaks on 4-7 -- none of which are
                // `+` binds, so none of them reach a usercmd at all. Two
                // button hunts failed on that: sect.190's 0x100000 is aim down
                // sights, and 0x08000000 fires 63 times in three minutes on an
                // IDLE client. A control settled it -- two left-clicks gave
                // exactly two 0x00000001 edges while five presses of 3 gave
                // NONE.
                //
                // `n 89` is the command, and the evidence is a count rather
                // than a plausible-looking bit: ten presses, ten commands, in
                // two bursts of five. Queued on the world and consumed by the
                // next clientThink as a single rising edge, so the toggle that
                // sect.190 already built is driven unchanged.
                for (const auto &command : clientPacket.reliableCommands)
                {
                    if (command.command == "n 89" &&
                        clientPacket.clientSlot !=
                            static_cast<std::size_t>(-1))
                    {
                        world_.requestAltWeaponToggle(
                            static_cast<std::uint32_t>(clientPacket.clientSlot));
                    }
                }
            }
            else if (clientPacket.kind == NetchanProcessKind::FragmentPending)
            {
                // Fragment buffering is normal netchan traffic.  It is not a
                // rejected packet and must not inflate drop diagnostics.
            }
            else
            {
                ++status_.netchanPacketsDropped;
                if (netchanRejectDiagnostics_[peerKey]++ < 4)
                {
                    std::clog << "[dedicated/game-server] netchan rejected peer="
                              << peer.ipv4 << ':' << peer.port
                              << " reason=" << clientPacket.reason << '\n';
                    OlMod::RuntimeLog::write(
                        OlMod::RuntimeLog::Channel::GameServer,
                        "netchan rejected peer=" + std::to_string(peer.ipv4) +
                            ":" + std::to_string(peer.port) + " reason=" +
                            clientPacket.reason);
                }
            }
            if (clientPacket.kind == NetchanProcessKind::Rejected)
                result.reason = std::move(clientPacket.reason);
        }
        status_.connectedClients = static_cast<std::uint32_t>(
            clients_.connectedClientCount());
        status_.gameStateMessagesSent = clients_.gameStateMessagesSent();
        status_.clientsReadyForGameState = static_cast<std::uint32_t>(
            clients_.gameStateReadyClientCount());
        status_.activeClients = static_cast<std::uint32_t>(clients_.activeClientCount());
        status_.gameStateUpdatesReceived = clients_.gameStateUpdatesReceived();
        status_.snapshotMessagesSent = clients_.snapshotMessagesSent();
        status_.fullSnapshotMessagesSent = clients_.fullSnapshotMessagesSent();
        status_.deltaSnapshotMessagesSent = clients_.deltaSnapshotMessagesSent();
        status_.messageAcknowledge = clients_.latestMessageAcknowledge();
        status_.outgoingSequence = clients_.latestOutgoingSequence();
        if (!plaintextReply.empty())
            result.reply = dtlsPeers_.NET_DtlsBuildData(peer, plaintextReply);
        return result;
    }

    bool ServerCore::configureSessionDescriptor(
        const std::span<const std::uint8_t> descriptor)
    {
        const std::lock_guard lock(mutex_);
        const auto previousKey = dtlsConfig_.securityKey();
        const auto wasConfigured = dtlsConfig_.configured();
        const auto updated = dtlsConfig_.configureFromDemonwareDescriptor(descriptor);
        if (updated)
            dtlsPeers_.rememberSecurityKey(dtlsConfig_.securityKey());
        status_.sessionConfigured = dtlsConfig_.configured();
        std::clog << "[dedicated/game-server] ConfigureSession key=";
        for (const auto byte : dtlsConfig_.securityKey())
            std::clog << std::hex << static_cast<unsigned int>(byte);
        std::clog << std::dec << " changed="
                  << (previousKey != dtlsConfig_.securityKey() ? 1 : 0)
                  << " wasConfigured=" << (wasConfigured ? 1 : 0) << '\\n';
        std::clog << std::endl;
        std::string keyFingerprint;
        for (std::size_t index = 0; index < 4; ++index)
            keyFingerprint += std::to_string(dtlsConfig_.securityKey()[index]) +
                (index == 3 ? "" : ":");
        OlMod::RuntimeLog::write(
            OlMod::RuntimeLog::Channel::GameServer,
            "ConfigureSession keyFingerprint=" + keyFingerprint +
                " updated=" + std::to_string(updated ? 1 : 0) +
                " changed=" + std::to_string(previousKey != dtlsConfig_.securityKey() ? 1 : 0));
        // ConfigureSession can arrive once per native client while one match is
        // being assembled. Do not destroy an established peer when the repeated
        // descriptor is re-parsed; the session key is shared by the match.
        const auto keyChanged = previousKey != dtlsConfig_.securityKey();
        if (updated && (!wasConfigured || (keyChanged && dtlsPeers_.sessionCount() == 0)))
        {
            dtlsPeers_.reset();
            dtlsPeerDiagnostics_.clear();
            dtlsRejectDiagnostics_.clear();
            dtlsNatDiagnostics_.clear();
            plaintextDiagnostics_.clear();
            netchanRejectDiagnostics_.clear();
        }
        return updated;
    }

    bool ServerCore::stageSessionRoster(
        const std::uint64_t generation,
        const std::span<const SessionRosterMember> members)
    {
        const std::lock_guard lock(mutex_);
        return clients_.stageSessionRoster(generation, members);
    }

    bool ServerCore::commitSessionRoster(const std::uint64_t generation)
    {
        const std::lock_guard lock(mutex_);
        return clients_.commitSessionRoster(generation);
    }

    bool ServerCore::rollbackSessionRoster(const std::uint64_t generation)
    {
        const std::lock_guard lock(mutex_);
        return clients_.rollbackSessionRoster(generation);
    }

    std::optional<std::uint16_t> ServerCore::registerDynamicWeaponConfigString(
        SvModularWeaponConfigString configString,
        const std::uint16_t firstDynamicWeaponAssetIndex,
        const SvClientSystem::WeaponConfigStringCommandBuilder &buildCommand)
    {
        const std::lock_guard lock(mutex_);
        return clients_.registerDynamicWeaponConfigString(
            std::move(configString), firstDynamicWeaponAssetIndex, buildCommand);
    }

    bool ServerCore::configureGameState(
        SvGameState gameState,
        const std::uint64_t sessionGeneration)
    {
        const std::lock_guard lock(mutex_);
        if (matchStatus_.configured && gameState.gameType == matchGameType_ &&
            (gameState.gameType == "sd" || gameState.gameType == "cha" ||
                gameState.gameType == "dm"))
        {
            gameState.uiGameRules = {
                // sd's scoreboard limit is rounds won; the scored modes show the
                // score limit itself.
                .scoreLimit = gameState.gameType == "sd"
                    ? matchStatus_.rules.winLimit
                    : matchStatus_.rules.scoreLimit,
                .timeLimitMinutes = matchStatus_.rules.timeLimitMinutes,
                .halfTime = false,
            };
            // The HUD clock is an absolute end time, so it needs the match
            // start. It is NOT matchStatus_.startServerTime: that is reset to 0
            // further down this same function and only filled later, when a
            // client first reaches Playing, so at this point it holds nothing.
            //
            // configureGameState calls world_.reset(), which does `snapshot_ =
            // {}`, so the world this gamestate describes begins at serverTime 0.
            // That is also what CODOL does natively - the level start time is
            // fixed at map load, not at first spawn - so 0 is the correct base
            // and the clock simply runs from the moment the world starts.
            gameState.matchStartServerTime = 0;
            SV_PopulateRequiredConfigStrings(gameState);
        }
        const auto mapCenter = gameState.mapCenter;
        const auto mapName = gameState.mapName;
        const auto zombieMode = gameState.gameType == "zm";
        const auto objectiveMaterials = gameState.sdObjectiveMaterials;
        const auto factoryAmmoMaterials = gameState.factoryAmmoMaterials;
        const auto factoryClockMaterials = gameState.factoryClockMaterials;
        const auto zombieReviveMaterials = gameState.zombieReviveMaterials;
        const auto zombieFallbackPistol = gameState.zombieFallbackPistol;
        const auto damageFeedbackMaterial = gameState.damageFeedbackMaterial;
        const auto killFeedbackMaterial = gameState.killFeedbackMaterial;
        const auto damageFeedbackSound = gameState.damageFeedbackSound;
        const auto killFeedbackSound = gameState.killFeedbackSound;
        const auto scavengerBagWeaponAssetIndex =
            gameState.scavengerBagWeaponAssetIndex;
        const auto scavengerPickupSound = gameState.scavengerPickupSound;
        const auto splashSound = gameState.splashSound;
        const auto soundAuditions = gameState.soundAuditions;
        const auto *entry = std::getenv("OLMOD_FACTORY_ENTRY");
        const bool factoryEntry = zombieMode && mapName == "zm_factory_sh" &&
            entry && std::string_view(entry) == "1";
        if (factoryEntry)
        {
            // CODDIFF(sv_send_client_gamestate): out.exe 610A30/6111E0 use
            // NCS menu indexes. common_mp's 1/2/3 are changeclass/marines/opfor;
            // the legacy three-slot parser table is different. This is the
            // response-name lookup only; do not overwrite native menu assets.
            gameState.scriptMenus[1] = "changeclass";
            gameState.scriptMenus[2] = "changeclass_marines";
            gameState.scriptMenus[3] = "changeclass_opfor";
        }
        const auto configured = clients_.configureGameState(
            std::move(gameState), sessionGeneration);
        if (configured)
        {
            world_.reset();
            livingWeaponRightTagInitialized_ = false;
            world_.setZmActorNamespaceEnabled(zombieMode);
            world_.setZombieFallbackPistol(zombieMode?zombieFallbackPistol:0);
            // OLMOD(reconstructed-zm-feedback): opt-in presentation only.
            const char *feedback = std::getenv("OLMOD_ZM_RECONSTRUCTED_FEEDBACK");
            world_.setZmReconstructedFeedbackEnabled(zombieMode && feedback && std::string_view(feedback)=="1");
            if (!world_.configureMapCenter(mapCenter))
                return false;
            scriptRuntime_.reset();
            resolvedLoadouts_.clear();
            matchMapName_ = mapName;
            visionAnnounced_.clear();
            factoryEntries_.clear();
            factoryEntryEnabled_ = factoryEntry;
            const auto *interactables=std::getenv("OLMOD_FACTORY_INTERACTABLES");
            factoryInteractablesEnabled_=zombieMode && mapName=="zm_factory_sh" &&
                interactables && std::string_view(interactables)=="1";
            factoryBox_={}; factoryBoxResources_={};
            const auto *teleporters=std::getenv("OLMOD_FACTORY_TELEPORTERS");
            factoryTeleportersEnabled_=factoryInteractablesEnabled_ && teleporters && std::string_view(teleporters)=="1";
            const auto *bo1Travel=std::getenv("OLMOD_FACTORY_BO1_TELEPORT_TRAVEL");
            factoryBo1TravelEnabled_=factoryTeleportersEnabled_ && bo1Travel && std::string_view(bo1Travel)=="1";
            factoryTeleporters_={};factoryTeleporterResources_={};factoryTeleportEffects_.clear();
            factorySounds_.clear(); factoryInteractionHintCache_.clear();
            status_.worldSpawnConfigured = false;
            matchStatus_.completed = false;
            matchStatus_.endReason = SvMatchEndReason::None;
            matchStatus_.winner = SvTeam::None;
            matchStatus_.winnerClientNum.reset();
            matchStatus_.startServerTime = 0;
            matchStatus_.elapsedMilliseconds = 0;
            sdRoundStatus_ = {
                .configured = matchGameType_ == "sd",
            };
            sdBombStatus_ = {};
            sdBombPickupTrigger_.reset();
            sdBombPickupHomeOrigin_ = {};
            sdBombSiteRuntime_.clear();
            sdBombVisualHandle_.reset();
            sdObjectiveMaterials_ = objectiveMaterials;
            factoryAmmoMaterials_ = factoryAmmoMaterials;
            factoryClockMaterials_ = factoryClockMaterials;
            zombieReviveMaterials_ = zombieReviveMaterials;
            damageFeedbackMaterial_ = damageFeedbackMaterial;
            killFeedbackMaterial_ = killFeedbackMaterial;
            damageFeedbackSound_ = damageFeedbackSound;
            killFeedbackSound_ = killFeedbackSound;
            scavengerBagWeaponAssetIndex_ = scavengerBagWeaponAssetIndex;
            scavengerPickupSound_ = scavengerPickupSound;
            splashSound_ = splashSound;
            headshotSound_.reset();
            soundAuditions_ = soundAuditions;
            soundAuditionCursor_ = 0;
            clientFeedback_.clear();
            useObjects_.reset();
            hintStringSlots_.clear();
            cursorHintTrigger_.clear();
            lootHintTarget_.clear();
            lootActivateHeld_.clear();
            mapTriggerHintTarget_.clear();
            barrierRepairHintTarget_.clear();
            zmUseActivateHeld_.clear();
            factoryAmmoHolds_.clear();
            zmRepairReadyTime_.clear();
            openedMapTriggers_.clear();
            zmPowerOn_ = false;
        }
        status_.gameStateConfigured = clients_.gameStateConfigured();
        return configured;
    }

    bool ServerCore::configureMatchRules(
        OlMod::DedicatedSession::MatchRules rules,
        const std::string_view gameType)
    {
        const std::lock_guard lock(mutex_);
        if (!OlMod::DedicatedSession::valid(rules, gameType))
            return false;
        matchStatus_ = {
            .configured = true,
            .rules = rules,
        };
        announcer_ = {};
        battleChatterSpeakers_.clear();
        battleChatterSequence_.clear();
        battleChatterVoiceFemale_.clear();
        matchCompletionAnnounced_ = false;
        matchCompletionServerTime_ = 0;
        matchEndedAnnounced_ = false;
        outroVisionAnnounced_ = false;
        outroScreenAsked_ = false;
        podiumScreenAsked_ = false;
        podiumRosterAsked_ = false;
        podiumWeaponsAsked_ = false;
        podiumCameraLogged_ = false;
        podiumFiguresSpawned_ = false;
        podiumAnimations_ = {};
        podiumAnimationEvent_ = 0;
        podiumCameraEntity_.reset();
        podiumCameraMotionContinued_ = false;
        matchEndFreezeLogged_ = false;
        matchEndScoresAsked_ = false;
        world_.clearMatchEndFreeze();
        world_.setMatchCompleted(false);
        soundAliasesAssigned_ = false;
        perkLives_.clear();
        uiClientLife_.clear();
        equipmentLives_.clear();
        uavOwners_.clear();
        firstBloodAwarded_ = false;
        matchParticipation_.clear();
        dmMatchBonuses_.clear();
        lastKilledBy_.clear();
        splashQueue_.clear();
        lastSplashRelease_.clear();
        matchGameType_ = gameType;
        // BATTLE ROYALE STARTS YOU WITH NOTHING. Set here rather than at the spawn
        // because the world owns the spawn and has no gametype. OLMOD_DMZ_UNARMED=0
        // puts the class loadout back for a session without a rebuild.
        {
            const auto *const disabled = std::getenv("OLMOD_DMZ_UNARMED");
            const auto unarmed = gameType == "dmz" &&
                !(disabled && disabled[0] == '0');
            world_.setUnarmedSpawns(unarmed);
            if (unarmed)
            {
                OlMod::RuntimeLog::write(
                    OlMod::RuntimeLog::Channel::GameServer,
                    "dmz spawns UNARMED -- loadout resolved and validated as usual, "
                    "then not equipped; loot is the only way to arm");
            }
        }
        sdRoundStatus_ = {
            .configured = gameType == "sd",
        };
        sdBombStatus_ = {};
        sdBombPickupTrigger_.reset();
        sdBombPickupHomeOrigin_ = {};
        sdBombSiteRuntime_.clear();
        sdBombVisualHandle_.reset();
        useObjects_.reset();
        sdSoundPresentation_ = {};
        sdSoundQueues_.clear();
        sdSoundReadyTime_.clear();
        sdRoundStartAnnounced_ = false;
        sdTfLastAliveAnnounced_ = false;
        sdScLastAliveAnnounced_ = false;
        sdPreviousTfAlive_ = 0;
        sdPreviousScAlive_ = 0;
        sdSideSwitchPending_ = false;
        return true;
    }

    bool ServerCore::configureSdSoundPresentation(
        SvSdSoundPresentation presentation)
    {
        const std::lock_guard lock(mutex_);
        const auto validTeam = [](const SvSdTeamSoundPresentation &team) {
            const std::array values{
                team.searchDestroy, team.objectiveDestroy,
                team.objectiveDefend, team.bombTaken, team.bombLost,
                team.bombPlanted, team.bombDefused, team.lastAlive,
                team.roundWon, team.roundLost, team.matchWon,
                team.matchLost, team.draw, team.sideSwitch,
            };
            return std::ranges::all_of(values, [](const auto value) {
                return value <= LocalSoundEventParameterMaximum;
            });
        };
        if (matchGameType_ != "sd" || sdRoundStatus_.armed ||
            (!presentation.objectiveLost && !presentation.objectiveTaken &&
                presentation.tf == SvSdTeamSoundPresentation{} &&
                presentation.sc == SvSdTeamSoundPresentation{}) ||
            presentation.objectiveLost > LocalSoundEventParameterMaximum ||
            presentation.objectiveTaken > LocalSoundEventParameterMaximum ||
            !validTeam(presentation.tf) || !validTeam(presentation.sc))
        {
            return false;
        }
        sdSoundPresentation_ = presentation;
        sdSoundQueues_.clear();
        sdSoundReadyTime_.clear();
        return true;
    }

    void ServerCore::setZmZones(std::vector<SvZmZone> zones)
    {
        // zmZonesMutex_, NOT mutex_. See the member declaration: the gametype script
        // reads this while loadGameplayScript already holds mutex_.
        // The player starts in receiver_zone on Factory. Every other zone is
        // authored in the map but remains closed until the corresponding
        // door/debris enter_* flag fires. Do not confuse geometric adjacency with
        // progression: two volumes can touch while a closed door separates them.
        for (auto &zone : zones)
            zone.active = zone.name == "receiver_zone";
        if (!zones.empty() &&
            std::ranges::none_of(zones, &SvZmZone::active))
        {
            // Other zm maps retain a usable start until their own flag mappings are
            // measured. Factory never takes this fallback.
            zones.front().active = true;
        }
        const std::lock_guard lock(zmZonesMutex_);
        zmZones_ = std::move(zones);
    }

    bool ServerCore::activateZmZone(const std::string_view zoneName)
    {
        if (zoneName.empty())
            return false;
        const std::lock_guard lock(zmZonesMutex_);
        const auto zone = std::ranges::find(zmZones_, zoneName, &SvZmZone::name);
        if (zone == zmZones_.end())
            return false;
        const auto changed = !zone->active;
        zone->active = true;
        return changed;
    }

    void ServerCore::setZmNavGraph(SvZmNavGraph graph)
    {
        const std::lock_guard lock(mutex_);
        world_.setZmNavGraph(std::move(graph));
    }

    void ServerCore::setZmActorWalkAnim(const std::uint16_t animIndex)
    {
        const std::lock_guard lock(mutex_);
        world_.setZmActorWalkAnim(animIndex);
    }

    void ServerCore::setZmActorTearAnim(const std::uint16_t animIndex)
    {
        const std::lock_guard lock(mutex_);
        world_.setZmActorTearAnim(animIndex);
    }

    void ServerCore::setZmTearClips(const SvZmTearClips &clips)
    {
        const std::lock_guard lock(mutex_);
        world_.setZmTearClips(clips);
    }

    void ServerCore::setZmBoardTrajectoryEvaluator(SvTrajectoryEvaluator evaluate)
    {
        const std::lock_guard lock(mutex_);
        world_.setZmBoardTrajectoryEvaluator(std::move(evaluate));
    }

    void ServerCore::setZmPresentation(std::span<const SvZmOutfit> outfits,
        std::span<const SvZmDeathClip> deaths, SvZmDeathFx fx)
    {
        const std::lock_guard lock(mutex_);
        world_.setZmPresentation(outfits,deaths,fx);
    }

    void ServerCore::setFactoryArrivalFx(std::uint16_t model,
        std::array<std::uint16_t,3> effects, std::uint8_t bone)
    {
        const std::lock_guard lock(mutex_);
        factoryArrivalModel_ = model;
        factoryArrivalFx_ = effects;
        factoryArrivalBone_ = bone;
    }

    void ServerCore::setZmActorDeathAnim(const std::uint16_t animIndex)
    {
        const std::lock_guard lock(mutex_);
        world_.setZmActorDeathAnim(animIndex);
    }

    void ServerCore::setZmActorAttackAnim(const std::uint16_t animIndex)
    {
        const std::lock_guard lock(mutex_);
        world_.setZmActorAttackAnim(animIndex);
    }

    void ServerCore::setZmBarriers(const std::span<const SvZmBarrier> barriers)
    {
        const std::lock_guard lock(mutex_);
        world_.setZmBarriers(barriers);
    }

    std::size_t ServerCore::zmBarrierCount() const
    {
        const std::lock_guard lock(mutex_);
        return world_.zmBarrierCount();
    }

    std::vector<SvZmZone> ServerCore::zmZones() const
    {
        const std::lock_guard lock(zmZonesMutex_);
        return zmZones_;
    }

    bool ServerCore::configureSdBombPresentation(
        const SvScriptModelEntityDefinition &visualDefinition,
        const std::uint16_t presentationModelIndex,
        const std::string_view presentationModelName)
    {
        const std::lock_guard lock(mutex_);
        if (!status_.worldSpawnConfigured || !sdBombStatus_.configured ||
            sdBombStatus_.phase != SvSdBombPhase::Inactive ||
            sdBombVisualHandle_)
        {
            return false;
        }
        const auto handle = world_.findScriptModel(visualDefinition);
        if (!handle || !world_.setScriptModelPresentation(
                *handle,
                presentationModelIndex,
                presentationModelName,
                visualDefinition.origin,
                visualDefinition.angles,
                false))
        {
            return false;
        }
        sdBombVisualHandle_ = *handle;
        sdBombVisualHomeOrigin_ = visualDefinition.origin;
        sdBombVisualAngles_ = visualDefinition.angles;
        return true;
    }

    bool ServerCore::configureSdBombRuntime(
        const std::span<const SvSdBombSite> sites,
        SvTriggerVolume pickupTrigger,
        const std::span<const SvSdBombSiteRuntime> siteRuntime)
    {
        const std::lock_guard lock(mutex_);
        const auto finiteOrigin = [](const SvSdBombSite &site) {
            return std::ranges::all_of(site.origin, [](const float value) {
                return std::isfinite(value);
            });
        };
        const auto finiteVector = [](const auto &vector) {
            return std::ranges::all_of(vector, [](const float value) {
                return std::isfinite(value);
            });
        };
        const auto validVolume = [&](const SvTriggerVolume &volume) {
            return volume.objectId && volume.collision.clipHandle == volume.objectId &&
                volume.collision.contents && finiteVector(volume.origin) &&
                finiteVector(volume.angles);
        };
        const auto matchesSite = [](const SvSdBombSite &site,
                                    const SvSdBombSiteRuntime &runtime) {
            return runtime.label == site.label &&
                runtime.plantTrigger.objectId == site.triggerModel &&
                runtime.plantTrigger.origin == site.origin &&
                runtime.plantTrigger.angles == site.angles &&
                runtime.defuseTrigger.objectId == site.defuseTriggerModel &&
                runtime.defuseTrigger.origin == site.defuseOrigin &&
                runtime.defuseTrigger.angles == site.defuseAngles;
        };
        if (!clients_.gameStateConfigured() || matchGameType_ != "sd" ||
            status_.worldSpawnConfigured || sites.size() != 2 ||
            siteRuntime.size() != 2 || !validVolume(pickupTrigger) ||
            sites[0].label != "_a" || sites[1].label != "_b" ||
            !matchesSite(sites[0], siteRuntime[0]) ||
            !matchesSite(sites[1], siteRuntime[1]) ||
            !validVolume(siteRuntime[0].plantTrigger) ||
            !validVolume(siteRuntime[0].defuseTrigger) ||
            !validVolume(siteRuntime[1].plantTrigger) ||
            !validVolume(siteRuntime[1].defuseTrigger) ||
            sites[0].target.empty() || sites[1].target.empty() ||
            !finiteOrigin(sites[0]) || !finiteOrigin(sites[1]))
        {
            return false;
        }
        sdBombStatus_ = {
            .configured = true,
            .sites = { sites.begin(), sites.end() },
        };
        sdBombPickupTrigger_ = std::move(pickupTrigger);
        sdBombPickupHomeOrigin_ = sdBombPickupTrigger_->origin;
        sdBombSiteRuntime_.assign(siteRuntime.begin(), siteRuntime.end());
        const std::array useDefinitions{
            SvUseObjectDefinition{
                .objectId = sdBombSiteRuntime_[0].plantTrigger.objectId,
                .ownerTeam = SvTeam::Sc,
                .allowedRelation = SvUseTeamRelation::Enemy,
                .useDurationMilliseconds = sdBombRules_.plantMilliseconds,
                .requiresKeyObject = true,
            },
            SvUseObjectDefinition{
                .objectId = sdBombSiteRuntime_[1].plantTrigger.objectId,
                .ownerTeam = SvTeam::Sc,
                .allowedRelation = SvUseTeamRelation::Enemy,
                .useDurationMilliseconds = sdBombRules_.plantMilliseconds,
                .requiresKeyObject = true,
            },
            SvUseObjectDefinition{
                .objectId = sdBombSiteRuntime_[0].defuseTrigger.objectId,
                .ownerTeam = SvTeam::Sc,
                .allowedRelation = SvUseTeamRelation::Friendly,
                .useDurationMilliseconds = sdBombRules_.defuseMilliseconds,
            },
            SvUseObjectDefinition{
                .objectId = sdBombSiteRuntime_[1].defuseTrigger.objectId,
                .ownerTeam = SvTeam::Sc,
                .allowedRelation = SvUseTeamRelation::Friendly,
                .useDurationMilliseconds = sdBombRules_.defuseMilliseconds,
            },
        };
        if (!useObjects_.configure(useDefinitions))
        {
            sdBombStatus_ = {};
            sdBombPickupTrigger_.reset();
            sdBombPickupHomeOrigin_ = {};
            sdBombSiteRuntime_.clear();
            return false;
        }
        return true;
    }

    bool ServerCore::configureWorldSpawn(
        const std::array<float, 3> origin,
        const std::array<float, 3> angles,
        const std::span<const SvBrushModelEntityDefinition> brushModels,
        const std::span<const SvScriptModelEntityDefinition> scriptModels,
        const std::span<const SvScriptModelDamageOwnerDefinition>
            scriptModelDamageOwners)
    {
        const std::array spawnPoints{
            SvWorldSpawnPoint{
                .origin = origin,
                .angles = angles,
            },
        };
        return configureWorldSpawn(
            spawnPoints,
            brushModels,
            scriptModels,
            scriptModelDamageOwners);
    }

    bool ServerCore::configureWorldSpawn(
        const std::span<const SvWorldSpawnPoint> spawnPoints,
        const std::span<const SvBrushModelEntityDefinition> brushModels,
        const std::span<const SvScriptModelEntityDefinition> scriptModels,
        const std::span<const SvScriptModelDamageOwnerDefinition>
            scriptModelDamageOwners,
        std::optional<SvWorldSpawnPoint> waitingForLoadoutPoint,
        const std::string_view mapName,
        const std::string_view gameType,
        const std::span<const SvLogicalMapEntityDefinition>
            logicalMapEntities)
    {
        const std::lock_guard lock(mutex_);
        const auto finiteVector = [](const auto &vector) {
            return std::ranges::all_of(vector, [](const float value) {
                return std::isfinite(value);
            });
        };
        if (!clients_.gameStateConfigured() || spawnPoints.empty() ||
            std::ranges::any_of(spawnPoints, [&](const auto &spawnPoint) {
                return !finiteVector(spawnPoint.origin) ||
                    !finiteVector(spawnPoint.angles) ||
                    (spawnPoint.team != SvTeam::None &&
                        spawnPoint.team != SvTeam::Tf &&
                        spawnPoint.team != SvTeam::Sc);
            }) ||
            !world_.configureSpawnAndBrushModelEntities(
                spawnPoints.front().origin,
                spawnPoints.front().angles,
                FirstDynamicServerEntityNum,
                brushModels,
                scriptModels,
                scriptModelDamageOwners,
                mapName,
                gameType,
                logicalMapEntities) ||
            !world_.configureSpawnPoints(
                spawnPoints, std::move(waitingForLoadoutPoint)))
        {
            return false;
        }
        // Null on a map with no extracted trigger table. driveCursorHints returns
        // immediately on null rather than falling back to guessed geometry.
        mapTriggers_ = SV_MapTriggerTable(mapName);
        hintStringSlots_.clear();
        cursorHintTrigger_.clear();
        lootHintTarget_.clear();
        lootActivateHeld_.clear();
        mapTriggerHintTarget_.clear();
        barrierRepairHintTarget_.clear();
        zmUseActivateHeld_.clear();
        factoryAmmoHolds_.clear();
        zmRepairReadyTime_.clear();
        openedMapTriggers_.clear();
        zmPowerOn_ = false;
        OlMod::RuntimeLog::write(
            OlMod::RuntimeLog::Channel::GameServer,
            "map triggers map=" + std::string{ mapName } + " triggers=" +
                std::to_string(mapTriggers_ ? mapTriggers_->triggers.size() : 0));
        status_.worldSpawnConfigured = world_.spawnConfigured();
        return status_.worldSpawnConfigured;
    }

    std::size_t ServerCore::constBaselineScriptModelCount() const
    {
        const std::lock_guard lock(mutex_);
        return world_.constBaselineScriptModelCount();
    }

    bool ServerCore::configureGlassMap(
        SvGlassMapMetadata metadata,
        const SvGlassDamageThresholds thresholds)
    {
        const std::lock_guard lock(mutex_);
        if (!clients_.gameStateConfigured() || status_.worldSpawnConfigured)
            return false;
        return world_.configureGlassMap(metadata, thresholds);
    }

    void ServerCore::setSharedPmoveRunner(SvSharedPmoveRunner runner)
    {
        const std::lock_guard lock(mutex_);
        world_.setSharedPmoveRunner(std::move(runner));
        clients_.setGameplayAuthorityReady(world_.sharedPmoveAvailable());
    }

    void ServerCore::setWeaponMovementRunner(SvWeaponMovementRunner runner)
    {
        const std::lock_guard lock(mutex_);
        world_.setWeaponMovementRunner(std::move(runner));
        clients_.setGameplayAuthorityReady(world_.sharedPmoveAvailable());
    }

    void ServerCore::setPlayerStateToEntityStateConverter(
        SvPlayerStateToEntityStateConverter converter)
    {
        const std::lock_guard lock(mutex_);
        world_.setPlayerStateToEntityStateConverter(std::move(converter));
        clients_.setGameplayAuthorityReady(world_.sharedPmoveAvailable());
    }

    void ServerCore::setDeathAnimationRunner(SvDeathAnimationRunner runner)
    {
        const std::lock_guard lock(mutex_);
        world_.setDeathAnimationRunner(std::move(runner));
    }

    void ServerCore::requestAltWeaponToggle(const std::uint32_t clientNum)
    {
        const std::lock_guard lock(mutex_);
        world_.requestAltWeaponToggle(clientNum);
    }

    void ServerCore::setSpawnAnimationRunner(SvSpawnAnimationRunner runner)
    {
        world_.setSpawnAnimationRunner(std::move(runner));
    }

    void ServerCore::setClientEventsHandler(SvClientEventsHandler handler)
    {
        const std::lock_guard lock(mutex_);
        world_.setClientEventsHandler(std::move(handler));
        clients_.setGameplayAuthorityReady(world_.sharedPmoveAvailable());
    }

    void ServerCore::setAltFireResolver(SvServerWorld::SvAltFireResolver resolver)
    {
        const std::lock_guard lock(mutex_);
        world_.setAltFireResolver(std::move(resolver));
    }

    void ServerCore::setCapsuleTraceRunner(SvCapsuleTraceRunner runner)
    {
        const std::lock_guard lock(mutex_);
        world_.setCapsuleTraceRunner(std::move(runner));
    }

    void ServerCore::setPointTraceRunner(SvPointTraceRunner runner)
    {
        const std::lock_guard lock(mutex_);
        world_.setPointTraceRunner(std::move(runner));
    }

    void ServerCore::setRadiusDamageVisibilityRunner(SvRadiusDamageVisibilityRunner runner)
    {
        const std::lock_guard lock(mutex_);
        world_.setRadiusDamageVisibilityRunner(std::move(runner));
    }

    void ServerCore::setTriggerContactRunner(SvTriggerContactRunner runner)
    {
        const std::lock_guard lock(mutex_);
        triggerContactRunner_ = std::move(runner);
    }

    void ServerCore::setNativeEntityMirrorSynchronizer(
        SvNativeEntityMirrorSynchronizer synchronizer)
    {
        const std::lock_guard lock(mutex_);
        world_.setNativeEntityMirrorSynchronizer(std::move(synchronizer));
    }

    bool ServerCore::sharedPmoveAvailable() const
    {
        const std::lock_guard lock(mutex_);
        return world_.sharedPmoveAvailable();
    }

    void ServerCore::setLoadoutProvider(LoadoutProvider provider)
    {
        const std::lock_guard lock(mutex_);
        loadoutProvider_ = std::move(provider);
        resolvedLoadouts_.clear();
    }

    void ServerCore::setUavWeaponProvider(std::function<std::optional<SvRewardWeapon>()> provider)
    {
        const std::lock_guard lock(mutex_);
        uavWeaponProvider_ = std::move(provider);
    }

    bool ServerCore::configureUavRadar(std::uint32_t durationMilliseconds)
    {
        const std::lock_guard lock(mutex_);
        if (durationMilliseconds > 3'600'000) return false;
        uavRadarDuration_ = durationMilliseconds;
        return true;
    }

    bool ServerCore::configureUavRadarTest(std::uint32_t durationMilliseconds, bool grantOneTestReward)
    {
        const std::lock_guard lock(mutex_);
        if (durationMilliseconds > 3'600'000) return false;
        uavRadarDuration_ = durationMilliseconds;
        uavRadarTestOverride_ = true;
        uavRadarTestGrant_ = grantOneTestReward;
        return true;
    }

    void ServerCore::setUavDiagnosticGrant(const bool enabled)
    {
        const std::lock_guard lock(mutex_);
        uavRadarTestGrant_ = enabled;
    }

    void ServerCore::setRewardLoadoutProvider(RewardLoadoutProvider provider)
    {
        const std::lock_guard lock(mutex_);
        rewardLoadoutProvider_ = std::move(provider);
    }

    void ServerCore::setEquipmentLoadoutProvider(EquipmentLoadoutProvider provider)
    {
        const std::lock_guard lock(mutex_);
        equipmentLoadoutProvider_ = std::move(provider);
        equipmentLives_.clear();
    }

    void ServerCore::setPerkLoadoutProvider(PerkLoadoutProvider provider)
    {
        const std::lock_guard lock(mutex_);
        perkLoadoutProvider_ = std::move(provider);
        perkLives_.clear();
    }

    void ServerCore::setCharacterCustomizationProvider(
        CharacterCustomizationProvider provider)
    {
        const std::lock_guard lock(mutex_);
        characterCustomizationProvider_ = std::move(provider);
    }

    void ServerCore::setCharacterModelNamesProvider(
        CharacterModelNamesProvider provider)
    {
        const std::lock_guard lock(mutex_);
        characterModelNamesProvider_ = std::move(provider);
    }

    void ServerCore::setScriptAnimationResolver(ScriptAnimationResolver resolver)
    {
        const std::lock_guard lock(mutex_);
        scriptBuiltins_.setAnimationResolver(resolver);
        scriptAnimationResolver_ = std::move(resolver);
    }

    void ServerCore::setCharacterOptionMaskProvider(
        CharacterOptionMaskProvider provider)
    {
        const std::lock_guard lock(mutex_);
        characterOptionMaskProvider_ = std::move(provider);
    }

    bool ServerCore::loadGameplayScript(
        const std::string_view sourceName,
        const std::string_view source)
    {
        const std::lock_guard lock(mutex_);
        if (!status_.enabled || !clients_.gameStateConfigured())
            return false;
        // A failed generation must not retain map-mode activation performed by
        // a partially executed source. Other gameplay mutations remain owned
        // by their individual builtin contracts.
        if (!world_.setMapGameObjects({}))
            return false;
        if (scriptRuntime_.reload(sourceName, source))
            return true;
        static_cast<void>(world_.setMapGameObjects({}));
        return false;
    }

    void ServerCore::unloadGameplayScript()
    {
        const std::lock_guard lock(mutex_);
        scriptRuntime_.reset();
    }

    SvLuaRuntimeStatus ServerCore::gameplayScriptStatus() const
    {
        const std::lock_guard lock(mutex_);
        return scriptRuntime_.status();
    }

    std::vector<SvLuaLogEntry> ServerCore::takeGameplayScriptLogs()
    {
        const std::lock_guard lock(mutex_);
        return scriptRuntime_.takeLogs();
    }

    SvBrushModelActivationStatus
        ServerCore::worldBrushModelActivationStatus() const
    {
        const std::lock_guard lock(mutex_);
        return world_.brushModelActivationStatus();
    }

    ServerStatus ServerCore::status() const
    {
        const std::lock_guard lock(mutex_);
        return status_;
    }

    SvServerFrameTimingStatus ServerCore::takeFrameTimingStatus()
    {
        const std::lock_guard lock(mutex_);
        SvServerFrameTimingStatus status{
            .total = frameTotalTiming_.take(),
            .prepare = framePrepareTiming_.take(),
            .beginWorld = frameBeginWorldTiming_.take(),
            .clientThink = frameClientThinkTiming_.take(),
            .mode = frameModeTiming_.take(),
            .endAndPublish = frameEndAndPublishTiming_.take(),
            .clientThinkCommands = frameClientThinkCommands_,
        };
        frameClientThinkCommands_ = 0;
        return status;
    }

    SvConnectionlessDiagnostics ServerCore::connectionlessDiagnostics() const
    {
        const std::lock_guard lock(mutex_);
        return connectionlessDiagnostics_;
    }

    std::optional<ClientIngressStatus> ServerCore::clientIngressStatus(
        const std::uint32_t clientNum) const
    {
        const std::lock_guard lock(mutex_);
        return clients_.clientIngressStatus(clientNum);
    }

    std::vector<SvClientSystem::TimeoutDrop> ServerCore::takeTimeoutDrops()
    {
        const std::lock_guard lock(mutex_);
        return clients_.takeTimeoutDrops();
    }

    bool ServerCore::debugGrantFactoryBattery(std::uint32_t senderIpv4,
        std::optional<std::uint32_t> targetClient)
    {
        // OLMOD(debug_battery): local debug control, fixed amount, no ambiguous
        // address fallback. Same mutex as authoritative frame ownership.
        const std::lock_guard lock(mutex_);
        if(senderIpv4!=0x7F000001u || matchGameType_!="zm" || matchMapName_!="zm_factory_sh")return false;
        std::optional<std::uint32_t> target;
        const auto &slots=clients_.clients();
        if(targetClient) {
            const auto i=*targetClient;
            return i<slots.size() && slots[i].state==ClientState::Active &&
                slots[i].peer.ipv4==senderIpv4 && world_.debugGrantFactoryBattery(i);
        }
        for(std::size_t i=0;i<slots.size();++i) {
            if(slots[i].state!=ClientState::Active)continue;
            if(target || slots[i].peer.ipv4!=senderIpv4)return false;
            target=static_cast<std::uint32_t>(i);
        }
        return target && world_.debugGrantFactoryBattery(*target);
    }

    std::optional<ServerCore::NoclipResolution>
        ServerCore::setPlayerNoclipForSender(
            const std::uint64_t xuid,
            const std::uint32_t senderIpv4,
            const bool enabled,
            const std::uint32_t holdMilliseconds)
    {
        const std::lock_guard lock(mutex_);
        const auto &slots = clients_.clients();
        const auto playing = [&](const std::size_t slot) {
            return slots[slot].state == ClientState::Active;
        };
        std::optional<std::size_t> resolved;
        std::size_t matches{};
        for (std::size_t slot = 0; slot < slots.size(); ++slot)
        {
            if (!playing(slot))
                continue;
            // EXACTLY ONE RULE APPLIES, NEVER BOTH. A named xuid that matches
            // nothing must FAIL rather than quietly fall through to the address
            // -- falling through would fly whoever happens to share the address
            // with the caller, which is the worst possible way to be wrong.
            if (xuid)
            {
                if (slots[slot].xuid != xuid)
                    continue;
                resolved = slot;
                matches = 1;
                break;
            }
            if (!senderIpv4 || slots[slot].peer.ipv4 != senderIpv4)
                continue;
            ++matches;
            if (!resolved)
                resolved = slot;
        }
        if (!resolved)
            return std::nullopt;
        const auto clientNum = static_cast<std::uint32_t>(*resolved);
        if (!world_.setPlayerNoclip(clientNum, enabled, holdMilliseconds))
            return std::nullopt;
        return NoclipResolution{
            .clientNum = clientNum,
            .xuid = slots[*resolved].xuid,
            .ambiguous = matches > 1,
        };
    }

    std::optional<SvPlayerState> ServerCore::worldPlayerState(
        const std::uint32_t clientNum) const
    {
        const std::lock_guard lock(mutex_);
        return world_.playerState(clientNum);
    }

    std::optional<SvWorldPlayerSample> ServerCore::worldPlayerSample(
        const std::uint32_t clientNum) const
    {
        const std::lock_guard lock(mutex_);
        const auto playerState = world_.playerState(clientNum);
        if (!playerState)
            return std::nullopt;
        const auto &clientSlots = clients_.clients();
        const auto lastReceivedUserCmd = clientNum < clientSlots.size()
            ? clientSlots[clientNum].lastReceivedUserCmd
            : std::nullopt;
        std::optional<SvWorldWeaponSample> weaponSample;
        const auto loadout = world_.resolvedLoadout(clientNum);
        if (loadout)
        {
            const auto *const weapon = SV_FindResolvedWeapon(
                *loadout,
                playerState->currentWeaponAssetIndex);
            if (weapon)
            {
                const auto clip = std::ranges::find_if(
                    playerState->ammoClips,
                    [weapon](const SvAmmoClipState &candidate) {
                        return candidate.clipIndex == weapon->clipIndex;
                    });
                if (clip != playerState->ammoClips.end())
                {
                    weaponSample = SvWorldWeaponSample{
                        .currentWeaponAssetIndex =
                            playerState->currentWeaponAssetIndex,
                        .weaponTime = playerState->weaponTime[0],
                        .weaponDelay = playerState->weaponDelay[0],
                        .weaponState = playerState->weaponState[0],
                        .weaponAnim = playerState->weaponAnim[0],
                        .clipAmmo = clip->count[0],
                        .weaponType = weapon->weaponType,
                        .fireType = weapon->fireType,
                        .definitionFireDelay = weapon->fireDelayMilliseconds,
                        .definitionFireTime = weapon->fireTimeMilliseconds,
                    };
                }
            }
        }
        return SvWorldPlayerSample{
            .frameNumber = status_.frameNumber,
            .serverTime = status_.serverTime,
            .lastReceivedUserCmd = lastReceivedUserCmd,
            .playerState = *playerState,
            .weapon = weaponSample,
        };
    }

    std::optional<SvGameEntity> ServerCore::worldPlayerEntity(
        const std::uint32_t clientNum) const
    {
        const std::lock_guard lock(mutex_);
        return world_.playerEntity(clientNum);
    }

    bool ServerCore::worldNativeEntityMirrorSynchronized() const
    {
        const std::lock_guard lock(mutex_);
        return world_.nativeEntityMirrorSynchronized();
    }

    std::optional<TraceResult> ServerCore::traceWorldPoint(
        const SvPointTraceRequest &request) const
    {
        const std::lock_guard lock(mutex_);
        return world_.tracePoint(request);
    }

    std::optional<TraceResult> ServerCore::traceWorldCapsule(
        const std::array<float, 3> &start,
        const std::array<float, 3> &end,
        const TraceBounds &bounds,
        const std::uint32_t contentMask,
        const SvTraceEntityFilter &filter) const
    {
        const std::lock_guard lock(mutex_);
        return world_.traceCapsule(start, end, bounds, contentMask, filter);
    }

    void ServerCore::setWeaponDefinitionResolver(
        SvServerWorld::WeaponDefinitionResolver resolver)
    {
        world_.setWeaponDefinitionResolver(std::move(resolver));
    }

    void ServerCore::setUnarmedSpawnWeapon(
        const std::uint16_t weaponAssetIndex)
    {
        world_.setUnarmedSpawnWeapon(weaponAssetIndex);
    }

    std::optional<SvResolvedLoadout> ServerCore::worldResolvedLoadout(
        const std::uint32_t clientNum) const
    {
        const std::lock_guard lock(mutex_);
        return world_.resolvedLoadout(clientNum);
    }

    std::optional<SvClientThinkStatus> ServerCore::worldClientThinkStatus(
        const std::uint32_t clientNum) const
    {
        const std::lock_guard lock(mutex_);
        return world_.clientThinkStatus(clientNum);
    }

    std::optional<SvPredictableEventStatus>
        ServerCore::worldPredictableEventStatus(
            const std::uint32_t clientNum) const
    {
        const std::lock_guard lock(mutex_);
        return world_.predictableEventStatus(clientNum);
    }

    std::optional<SvBulletExecutionStatus>
        ServerCore::worldBulletExecutionStatus(
            const std::uint32_t clientNum) const
    {
        const std::lock_guard lock(mutex_);
        return world_.bulletExecutionStatus(clientNum);
    }

    std::optional<SvWorldEvent> ServerCore::worldLastEvent() const
    {
        const std::lock_guard lock(mutex_);
        return world_.lastEvent();
    }

    std::optional<SvEntityDamageRuntimeStatus>
        ServerCore::worldEntityDamageStatus(
            const std::uint32_t entityNum) const
    {
        const std::lock_guard lock(mutex_);
        return world_.entityDamageRuntimeStatus(entityNum);
    }

    SvMatchStatus ServerCore::matchStatus() const
    {
        const std::lock_guard lock(mutex_);
        return matchStatus_;
    }

    SvSdRoundStatus ServerCore::sdRoundStatus() const
    {
        const std::lock_guard lock(mutex_);
        return sdRoundStatus_;
    }

    SvSdBombStatus ServerCore::sdBombStatus() const
    {
        const std::lock_guard lock(mutex_);
        return sdBombStatus_;
    }

    SvSdRuntimeStatus ServerCore::sdRuntimeStatus() const
    {
        const std::lock_guard lock(mutex_);
        SvSdEliminationState teams;
        const auto &clients = clients_.clients();
        for (std::uint32_t clientNum = 0; clientNum < clients.size(); ++clientNum)
        {
            const auto &client = clients[clientNum];
            if (client.gameplayState != ClientGameplayState::Playing)
                continue;
            const auto playerState = world_.playerState(clientNum);
            if (!playerState || !playerState->spawnGeneration)
                continue;
            auto *const total = client.team == SvTeam::Tf
                ? &teams.attackers
                : client.team == SvTeam::Sc ? &teams.defenders : nullptr;
            auto *const alive = client.team == SvTeam::Tf
                ? &teams.attackersAlive
                : client.team == SvTeam::Sc ? &teams.defendersAlive : nullptr;
            if (!total || !alive)
                continue;
            ++*total;
            if (playerState->health > 0)
                ++*alive;
        }
        teams.bombPlanted = sdBombStatus_.phase == SvSdBombPhase::Planted;
        return {
            .round = sdRoundStatus_,
            .bomb = sdBombStatus_,
            .teams = teams,
        };
    }

    SvGameplayPresentationStatus ServerCore::gameplayPresentationStatus() const
    {
        const std::lock_guard lock(mutex_);
        SvGameplayPresentationStatus status{ .serverTime = status_.serverTime };
        std::uint32_t snapshotPlayerEntityMask{};
        std::uint32_t snapshotClientInfoMask{};
        for (const auto &entity : world_.snapshot().entities)
        {
            if (entity.eType == EntityTypePlayer && entity.number < 32)
                snapshotPlayerEntityMask |= 1u << entity.number;
        }
        for (const auto &clientInfo : world_.snapshot().clientInfos)
        {
            if (clientInfo.clientNum < 32)
                snapshotClientInfoMask |= 1u << clientInfo.clientNum;
        }
        SvSdEliminationState teams;
        const auto &slots = clients_.clients();
        for (std::uint32_t clientNum{}; clientNum < slots.size(); ++clientNum)
        {
            const auto &client = slots[clientNum];
            if (client.state == ClientState::Free)
                continue;
            const auto reliable = clients_.serverReliableCommandStatus(
                clientNum, 32);
            if (!reliable)
                continue;
            SvGameplayPresentationClientStatus clientStatus{
                .clientNum = clientNum,
                .gameplayState = client.gameplayState,
                .team = client.team,
                .reliable = *reliable,
                .pendingUserCmdCount = static_cast<std::uint32_t>(
                    client.pendingUserCmds.size()),
                .oldestPendingUserCmdTime = client.pendingUserCmds.empty()
                    ? std::nullopt
                    : std::optional{ client.pendingUserCmds.front().commandTime },
                .newestPendingUserCmdTime = client.pendingUserCmds.empty()
                    ? std::nullopt
                    : std::optional{ client.pendingUserCmds.back().commandTime },
                .lastReceivedUserCmdTime = client.lastReceivedUserCmd
                    ? std::optional{ client.lastReceivedUserCmd->commandTime }
                    : std::nullopt,
                .lastDispatchedUserCmdTime = client.lastDispatchedUserCmd
                    ? std::optional{ client.lastDispatchedUserCmd->commandTime }
                    : std::nullopt,
                .lastExecutedUserCmdTime = client.lastExecutedUserCmd
                    ? std::optional{ client.lastExecutedUserCmd->commandTime }
                    : std::nullopt,
                .lastDiscardedUserCmdTime =
                    client.lastDiscardedUnsupportedUserCmd
                    ? std::optional{
                          client.lastDiscardedUnsupportedUserCmd->commandTime }
                    : std::nullopt,
                .discardedUnsupportedUserCmds =
                    client.discardedUnsupportedUserCmds,
                .snapshotPlayerEntityMask = snapshotPlayerEntityMask,
                .snapshotClientInfoMask = snapshotClientInfoMask,
            };
            if (const auto playerState = world_.playerState(clientNum))
            {
                std::copy_n(
                    playerState->objectives.begin(),
                    clientStatus.objectives.size(),
                    clientStatus.objectives.begin());
                if (client.gameplayState == ClientGameplayState::Playing &&
                    playerState->spawnGeneration)
                {
                    auto *const total = client.team == SvTeam::Tf
                        ? &teams.attackers
                        : client.team == SvTeam::Sc ? &teams.defenders : nullptr;
                    auto *const alive = client.team == SvTeam::Tf
                        ? &teams.attackersAlive
                        : client.team == SvTeam::Sc ? &teams.defendersAlive : nullptr;
                    if (total && alive)
                    {
                        ++*total;
                        if (playerState->health > 0)
                            ++*alive;
                    }
                }
            }
            status.clients.push_back(std::move(clientStatus));
        }
        teams.bombPlanted = sdBombStatus_.phase == SvSdBombPhase::Planted;
        status.sd = {
            .round = sdRoundStatus_,
            .bomb = sdBombStatus_,
            .teams = teams,
        };
        return status;
    }

    bool ServerCore::addClientScore(
        const std::uint32_t clientNum,
        const std::int32_t delta)
    {
        // Display score only. It is 100 per kill and the limit is 30, so this must
        // NOT drive the limit - see addKillForClient, which is what does.
        return !matchStatus_.completed && clients_.addClientScore(clientNum, delta);
    }

    bool ServerCore::addKillForClient(
        const std::uint32_t clientNum,
        const std::int32_t delta)
    {
        if (matchStatus_.completed || !clients_.addClientKills(clientNum, delta))
            return false;
        // CODREF: iw4 level.bcSounds["kill"] = "inform_killfirm_infantry".
        // Only a positive award speaks - a suicide subtracts, and confirming a
        // kill you did not make would be worse than silence.
        if (delta > 0)
            sayBattleChatter(clientNum, SvBattleChatterLine::KillfirmInfantry);
        // The teamless counterpart of addTeamScoreForClient below. Free-for-all
        // never awards team score - dm.lua drops the addteamscore cha.lua has,
        // because there are no teams to award it to - so without evaluating here
        // the one mode whose limit reads per-client counters was the one mode that
        // never triggered the check.
        if (!matchStatus_.startServerTime)
            matchStatus_.startServerTime = world_.snapshot().serverTime;
        evaluateMatchLimits();
        return true;
    }

    bool ServerCore::addTeamScoreForClient(
        const std::uint32_t clientNum,
        const std::int32_t delta)
    {
        if (matchStatus_.completed ||
            !clients_.addTeamScoreForClient(clientNum, delta))
        {
            return false;
        }
        if (!matchStatus_.startServerTime)
            matchStatus_.startServerTime = world_.snapshot().serverTime;
        evaluateMatchLimits();
        return true;
    }

    bool ServerCore::finishCampaignMissionFromScript()
    {
        if (!matchStatus_.configured || matchGameType_ != "coop" ||
            matchStatus_.completed)
        {
            return false;
        }
        matchStatus_.completed = true;
        matchStatus_.endReason = SvMatchEndReason::None;
        matchStatus_.winner = SvTeam::Tf;
        matchStatus_.winnerClientNum.reset();
        OlMod::RuntimeLog::write(
            OlMod::RuntimeLog::Channel::GameServer,
            "campaign mission complete requested by gameplay script");
        return true;
    }

    void ServerCore::evaluateMatchLimits()
    {
        if (!matchStatus_.configured || matchStatus_.completed)
            return;
        // Zombies has no score limit either -- see SV_UpdateMatchTimeLimit for
        // the clock. The booking hands zm scoreLimit 30, which is a couple of
        // kills' worth of points, and the ONLY reason it has never ended a zm
        // match is that nothing awards zm team score yet. Gate it before
        // something does.
        if (matchGameType_ == "zm")
            return;
        if (matchGameType_ == "dm")
        {
            // Free-for-all is scored per player, and because every FFA player is
            // left teamless BOTH team scores stay 0 - so the team-scored check
            // below can never fire and the match would run forever. The shipped
            // description is "First player to reach the score limit wins", which
            // is what this evaluates.
            const auto best = clients_.bestClientKills();
            if (matchStatus_.rules.scoreLimit && best &&
                best->second >=
                    static_cast<std::int32_t>(matchStatus_.rules.scoreLimit))
            {
                matchStatus_.completed = true;
                matchStatus_.endReason = SvMatchEndReason::ScoreLimit;
                matchStatus_.winner = SvTeam::None;
                matchStatus_.winnerClientNum = best->first;
                // A completed match silently refuses all further score, which
                // presents as the scoreboard freezing rather than as the match
                // having been won. Nothing recorded the end at all before this.
                OlMod::RuntimeLog::write(
                    OlMod::RuntimeLog::Channel::GameServer,
                    "match complete gametype=dm reason=scoreLimit winner=client" +
                        std::to_string(best->first) + " score=" +
                        std::to_string(best->second) + " limit=" +
                        std::to_string(matchStatus_.rules.scoreLimit));
            }
            return;
        }
        const auto tfScore = clients_.teamScore(SvTeam::Tf).value_or(0);
        const auto scScore = clients_.teamScore(SvTeam::Sc).value_or(0);
        if (matchStatus_.rules.scoreLimit &&
            (tfScore >= static_cast<std::int32_t>(matchStatus_.rules.scoreLimit) ||
                scScore >= static_cast<std::int32_t>(matchStatus_.rules.scoreLimit)))
        {
            matchStatus_.completed = true;
            matchStatus_.endReason = SvMatchEndReason::ScoreLimit;
            matchStatus_.winner = tfScore == scScore
                ? SvTeam::None
                : tfScore > scScore ? SvTeam::Tf : SvTeam::Sc;
        }
    }

    void ServerCore::announceMatchRules()
    {
        // MEASURED (dm demo, serverTime 0): `s ui_DMKillScore "50"`, and it is
        // dm's alone - it appears in no cha, war or dom demo. The score limit
        // and time limit already reach the client as ui_scorelimit and
        // ui_timelimit in serverinfo, but nothing carried the per-kill award.
        //
        // Sent per client on the frame it becomes active rather than once at
        // serverTime 0, so a late join gets it too. The dvar NAME is portable
        // where the demo's numeric ids are not.
        const auto &slots = clients_.clients();
        // ZOMBIES' OWN CONNECT BLOCK, MEASURED. All five zm demos send exactly these,
        // once, as plain `s` setDvars (re/demo-re/15-zm-inventory.md sec.2). The 3.3.3.3
        // project recorded that zm "has no such dvars at all"; on this build it is four
        // commands, and `ui_hud_round_goal` is 8 rather than the 16 that was guessed.
        //
        // `battery_multiplier` matters because the client does not merely display it --
        // sub_466450 DIVIDES by it. Dvar_FindVar missing it yields 0.0, `fldz` at
        // 0x4665AF, and the `idiv` at 0x4665EC faults the client with 0xC0000094 on any
        // zm map. That is the crash `out.exe`'s byte patch at VA 0x46659C papers over by
        // jumping the whole lookup; supplying the dvar makes the real path work.
        //
        // THE VALUE IS 1.2, AND IT IS IN THE DEMOS AFTER ALL. This comment used to say
        // "no demo carries it" and sent 1. Both were wrong: the zm captures pair a NAME
        // band with a VALUE band at a FIXED +320 OFFSET, so the dvar is present but not
        // greppable by name. Verified on C-2021-7-31[15-32-16]zm:
        //
        //     cs 189 battery_multiplier   ->  cs 509 = 1.2      (189 + 320)
        //     cs 190 scr_spy_round_state  ->  cs 510 = end
        //     cs 195 ui_cpoffsety         ->  cs 515 = 0
        //     cs 206 ui_zhunt_zombie_hp   ->  cs 526 = (empty)
        //
        // Eighteen zm names at 189..206, alphabetically sorted. THE INDICES ARE
        // PER-GAMETYPE and do not transfer -- dm publishes twelve at 189..200, where
        // 189 is ui_bossBodyDestroyedInfo and ui_cpoffsety is 190 rather than 195. So
        // never hardcode 189; it is battery_multiplier only because it sorts first in
        // zm's list.
        //
        // Sending 1 did not crash -- the divisor was 1000 instead of retail's 1200 --
        // so the battery economy ran ~20% off retail with nothing to show for it.
        if (matchGameType_ == "zm")
        {
            for (std::uint32_t clientNum{}; clientNum < slots.size(); ++clientNum)
            {
                if (slots[clientNum].state != ClientState::Active ||
                    matchRulesAnnounced_.contains(clientNum))
                {
                    continue;
                }
                matchRulesAnnounced_.insert(clientNum);
                for (const auto *const command : {
                         "s battery_multiplier \"1.2\"",
                         "s ui_allow_ingamepurchase \"1\"",
                         "s ui_hud_final_round \"0\"",
                         "s ui_hud_special_round \"0\"",
                     })
                {
                    static_cast<void>(
                        clients_.queueReliableCommand(clientNum, command));
                }
                // The round pair is re-sent as a PAIR on every round change; this is the
                // opening assertion so the HUD reads 1/8 rather than nothing.
                static_cast<void>(clients_.queueReliableCommand(
                    clientNum, "s ui_hud_round \"1\""));
                static_cast<void>(clients_.queueReliableCommand(
                    clientNum,
                    "s ui_hud_round_goal \"" +
                        std::to_string(SvZombieRoundGoal) + "\""));
            }
            return;
        }
        if (matchGameType_ != "dm")
            return;
        for (std::uint32_t clientNum{}; clientNum < slots.size(); ++clientNum)
        {
            if (slots[clientNum].state != ClientState::Active ||
                matchRulesAnnounced_.contains(clientNum))
            {
                continue;
            }
            matchRulesAnnounced_.insert(clientNum);
            // dmz AWARDS 1, NOT 50, AND IT IS MEASURED THE SAME WAY THE 50 WAS.
            // C-2021-7-25[22-0-7]dmz opens with `s ui_DMKillScore "1"` where the dm
            // capture opens with "50" -- battle royale scores in KILLS, not in dm's
            // 50-a-kill display points, so a 50 here would read as 50 eliminations.
            const auto killScore = matchGameType_ == "dmz"
                ? 1
                : static_cast<int>(SvDmScoreFeedbackKillPoints);
            static_cast<void>(clients_.queueReliableCommand(
                clientNum,
                "s ui_DMKillScore \"" + std::to_string(killScore) + "\""));
        }
    }

    void ServerCore::announceSoundAliases()
    {
        // THE SERVER HANDS THE CLIENT ITS SOUND ALIAS TABLE, and nothing did
        // this before, so `p <n>` named an empty slot and every UI sound was
        // silent - the hit marker's included, which had been "wired" since the
        // damage feedback work and never once made a noise. `grep -c "damage
        // feedback sound alias=" is 0 across the whole runtime log.
        //
        // `p <n>` plays alias INDEX n, and alias n is configstring 3624+n, a
        // table the SERVER owns. resolveSoundAliasEventParameters asks the
        // CLIENT for a name, and a client only has what a server put there.
        // Retail's client could resolve mp_hit_alert because retail's server
        // had written it: its gamestate ships 79 alias entries spanning indices
        // 9..3628 and its match hands out 45 more live. This server ships 22
        // configstrings in total, none in that range.
        //
        // Assigned once per match and only after a client holds a gamestate:
        // SV_SetConfigString stores the value for anyone who connects later AND
        // pushes `d` to everyone already past it, so one call covers both.
        // WAIT FOR EVERY CONNECTED CLIENT TO BE ACTIVE. The first attempt
        // required only that a gamestate had been SENT, which is true while the
        // client is still loading the map - and a configstring write landing in
        // that window is what killed the join. Active means the client is in
        // the game and parsing snapshots, which is the earliest moment a `d` is
        // safe.
        //
        // Requiring ALL of them, not any, also stops the write going out at
        // clients=1 and leaving the second client to pick the value up from a
        // gamestate built at a different instant.
        if (soundAliasesAssigned_ || SV_PerfBaseline())
            return;
        const auto &slots = clients_.clients();
        const auto connected = std::ranges::count_if(slots, [](const auto &slot) {
            return slot.state != ClientState::Free;
        });
        const auto active = std::ranges::count_if(slots, [](const auto &slot) {
            return slot.state == ClientState::Active;
        });
        if (!connected || active != connected)
            return;
        soundAliasesAssigned_ = true;

        struct Alias
        {
            std::uint16_t index;
            const char *name;
        };
        for (const auto &alias : {
                 Alias{ SvHitAlertSoundAliasIndex, "mp_hit_alert" },
                 Alias{ SvKillSoundAliasIndex, "mp_hit_kill" },
                 Alias{ SvHeadshotSoundAliasIndex, "mp_headshot" },
                 Alias{ SvSplashSoundAliasIndex, "mp_last_stand" },
             })
        {
            const auto sent = clients_.SV_SetConfigString(
                static_cast<std::uint16_t>(
                    SoundAliasConfigStringBase + alias.index),
                alias.name);
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer,
                "sound alias " + std::to_string(alias.index) + " = " +
                    alias.name + " -> cs " +
                    std::to_string(SoundAliasConfigStringBase + alias.index) +
                    " clients=" + std::to_string(sent));
        }

        // THE OBITUARY FORMATS, on the same gate and for the same reason. The
        // three names are retail's own configstring VALUES, read straight off
        // 13-dm-gamestate-configstrings.tsv rather than guessed -- the client
        // resolves them through its localize assets, so the value is the NAME.
        // DM ONLY. THIS BAND KICKS ANY MODE WHOSE CCS ASSET ASSIGNS A
        // DIFFERENT TYPE TO THE SAME NUMERIC SLOT.
        // ONLY ON THE MODES WHERE THIS BAND WAS MEASURED. THIS BAND IS WHAT
        // KICKS A CLIENT WHO LOADED A DIFFERENT CONFIGSTRING LAYOUT.
        //
        // MEASURED 2026-09-05 by hooking the client's own configstring validator
        // (sub_514540, which raises XBOXLIVE_CANTJOINSESSION as ERR_SERVERDISCONNECT):
        //
        //     CS VALIDATE index=2866/2867/3649..3652  typeByte=0xFF   accepted
        //     CS VALIDATE index=1413                  typeByte=0x04   REJECTED -> kick
        //
        // The validator accepts a type byte of 0x15 or >= 0x17 and rejects everything
        // else, reading it from the CCS block at `0x77D8250 + index`. Those types come
        // from the CLIENT'S OWN loaded asset set, so what an index MEANS moves with the
        // gametype -- the same lesson the model band taught. On dm, 1413 is the
        // measured obituary format band and this is correct. On dmz AND zm it is
        // type 0x04, and writing a localized-string name into it makes the client
        // refuse the session about a second after it enters. The zm rejection was
        // captured live at 2026-09-08 01:22:49: the client reached cls.state 10,
        // validated 1413 as 0x04, raised error code 2 from sub_514540+0xA5, then
        // returned to the menu with an empty dialog.
        //
        // Skipped rather than relocated: where another mode keeps its obituary formats
        // (if it has them) is not measured, and inventing an index is how this bug was
        // created.
        // The kill feed is cosmetic; being able to stay in the match is not.
        // MEASURED 2026-09-09 ON WETWORK: the coop client reaches CA_ACTIVE, consumes
        // the live configstring burst, then raises the same
        // XBOXLIVE_CANTJOINSESSION error through that same validator and clears
        // CA_ACTIVE to CA_DISCONNECTED at sub_5BF3E0+0x2DE. Retail's Wetwork join
        // burst contains no 1413..1415 writes. These three names came exclusively
        // from the DM capture, so sending them to coop was a cross-mode invention.
        //
        // Skipped rather than relocated: where dmz or coop keeps its obituary formats
        // (if either has them) is not measured, and inventing an index is how this bug
        // was created.
        // The kill feed is cosmetic; being able to stay in the match is not.
        if (matchGameType_ != "dm")
        {
            static std::string reportedGameType;
            if (reportedGameType != matchGameType_)
            {
                reportedGameType = matchGameType_;
                OlMod::RuntimeLog::write(
                    OlMod::RuntimeLog::Channel::GameServer,
                    "obituary formats SKIPPED on " + matchGameType_ +
                        " -- cs 1413 is only measured as an obituary string in dm; "
                        "writing it in this asset set makes the client reject the session");
            }
        }
        else
        {
            for (const auto &obituary : {
                     Alias{ 0, "MP_OBITUARY_NEUTRAL" },
                     Alias{ 1, "MP_OBITUARY_FRIENDLY" },
                     Alias{ 2, "MP_OBITUARY_ENEMY" },
                 })
            {
                const auto index = static_cast<std::uint16_t>(
                    ObituaryConfigStringBase + obituary.index);
                const auto sent = clients_.SV_SetConfigString(index, obituary.name);
                OlMod::RuntimeLog::write(
                    OlMod::RuntimeLog::Channel::GameServer,
                    "obituary format cs " + std::to_string(index) + " = " +
                        obituary.name + " clients=" + std::to_string(sent));
            }
        }

        // Appmain still asks the client to resolve these by name, and that is
        // kept: a client that DOES already carry an alias should be played its
        // own index. These are the fallback for what has actually been
        // happening, which is that it carries nothing.
        if (!damageFeedbackSound_)
            damageFeedbackSound_ = SvHitAlertSoundAliasIndex;
        if (!killFeedbackSound_)
            killFeedbackSound_ = SvKillSoundAliasIndex;
        // splashSound_ has been empty on every level load this project has ever
        // run - "splash sound unresolved; medals stay silent" is in the log
        // going back hours - because it too was asked for by a name the client
        // had no table entry for.
        if (!splashSound_)
            splashSound_ = SvSplashSoundAliasIndex;
        if (!headshotSound_)
            headshotSound_ = SvHeadshotSoundAliasIndex;
    }

    std::optional<std::uint16_t> ServerCore::registerHintString(
        const std::string_view text)
    {
        if (text.empty())
            return std::nullopt;
        std::size_t free = hintStrings_.size();
        for (std::size_t slot = HintStringFirstServerSlot;
             slot < hintStrings_.size();
             ++slot)
        {
            if (hintStrings_[slot] == text)
                return static_cast<std::uint16_t>(slot);
            if (hintStrings_[slot].empty() && free == hintStrings_.size())
                free = slot;
        }
        if (free == hintStrings_.size())
            return std::nullopt;
        hintStrings_[free].assign(text);
        // SV_SetConfigString stores the value for anyone who connects later AND
        // pushes `d` to everyone already past the gamestate, so registering
        // mid-match is safe and one call covers both -- the same property
        // announceSoundAliases relies on.
        const auto sent = clients_.SV_SetConfigString(
            static_cast<std::uint16_t>(HintStringConfigStringBase + free),
            std::string{ text });
        OlMod::RuntimeLog::write(
            OlMod::RuntimeLog::Channel::GameServer,
            "hint string " + std::to_string(free) + " = " + std::string{ text } +
                " -> cs " +
                std::to_string(HintStringConfigStringBase + free) +
                " clients=" + std::to_string(sent));
        return static_cast<std::uint16_t>(free);
    }

    void ServerCore::driveCursorHints(
        const std::span<const SvWorldClientInput> activeClients)
    {
        // NO EARLY RETURN ON A MAP WITH NO TRIGGER TABLE ANY MORE. This used to bail
        // out immediately when mapTriggers_ was null, which is every map but
        // zm_factory_sh -- including mp_battlecity, where the loot lives. The trigger
        // half is guarded individually below instead.
        //
        // ONE WRITER FOR cursorHint, and it has to be this function. Two drivers that
        // each only act when THEIR answer changes will leave a stale prompt on screen
        // the moment they disagree: loot stops offering, says nothing because it has
        // nothing new to say, and the crate's prompt stays up.
        const auto loot = world_.lootItems();
        for (const auto &client : activeClients)
        {
            // A DEAD PLAYER IS NOT OFFERED ANYTHING. The prompt is an offer to spend
            // batteries on something, and the client draws it regardless of pmType.
            const auto playing =
                client.gameplayState == ClientGameplayState::Playing;
            const auto playerState = playing ? world_.playerState(client.clientNum)
                                             : std::nullopt;
            const auto reviveTarget = world_.zombieReviveTarget(client.clientNum);
            const auto down = world_.zombieDownedState(client.clientNum);
            if (reviveTarget || down || world_.zombieTeamWiped())
            {
                const auto targetState=reviveTarget?world_.zombieDownedState(*reviveTarget):std::nullopt;
                const auto treating=targetState && targetState->reviver &&
                    *targetState->reviver==client.clientNum;
                if (world_.zombieTeamWiped() || treating || (down && !down->bledOut))
                    static_cast<void>(world_.clearPlayerCursorHint(client.clientNum));
                else if (const auto hint=registerHintString(down?"Waiting for next round":"PLATFORM_REVIVE"))
                    static_cast<void>(world_.setPlayerCursorHint(client.clientNum,
                        SvCursorHint::NoIcon,*hint,reviveTarget.value_or(SvNoHintEntityNum)));
                lootHintTarget_.erase(client.clientNum);
                barrierRepairHintTarget_.erase(client.clientNum);
                mapTriggerHintTarget_.erase(client.clientNum);
                cursorHintTrigger_.erase(client.clientNum);
                continue;
            }
            const auto alive = playerState && playerState->health;
            // LOOT FIRST, AND THE NEAREST OF IT. Crates overlap -- the bring-up ring
            // puts nine of them within a few hundred units -- and offering whichever
            // one happened to be registered first would make the prompt depend on
            // spawn order rather than on where the player is standing.
            const SvLootItem *nearestLoot = nullptr;
            float nearestLootDistanceSquared = 0.0f;
            if (alive)
            {
                for (const auto &item : loot)
                {
                    const auto x = item.origin[0] - playerState->origin[0];
                    const auto y = item.origin[1] - playerState->origin[1];
                    const auto z = item.origin[2] - playerState->origin[2];
                    const auto distanceSquared = x * x + y * y + z * z;
                    if (distanceSquared > item.radius * item.radius)
                        continue;
                    if (!nearestLoot || distanceSquared < nearestLootDistanceSquared)
                    {
                        nearestLoot = &item;
                        nearestLootDistanceSquared = distanceSquared;
                    }
                }
            }
            if (nearestLoot)
                lootHintTarget_[client.clientNum] = *nearestLoot;
            else
                lootHintTarget_.erase(client.clientNum);

            std::optional<std::string> repairBarrier;
            if (!nearestLoot && alive && matchGameType_ == "zm")
                repairBarrier = world_.repairableZmBarrierAt(playerState->origin);
            if (repairBarrier)
                barrierRepairHintTarget_[client.clientNum] = *repairBarrier;
            else
                barrierRepairHintTarget_.erase(client.clientNum);

            const SvMapTrigger *trigger = nullptr;
            const SvTriggerHintRule *rule = nullptr;
            if (!nearestLoot && !repairBarrier && mapTriggers_ && alive)
            {
                trigger = SV_PromptableTriggerAt(
                    mapTriggers_,
                    playerState->origin,
                    StandingPlayerTraceBounds.midpoint,
                    StandingPlayerTraceBounds.halfSize,
                    &rule);
            }
            // OLMOD(factory_perk_machines): solid cabinets prevent touching the
            // authored use hull. A bounded machine-only fallback reaches the
            // original hull from its accessible edge; other prompts keep priority.
            if(!trigger && !nearestLoot && !repairBarrier && mapTriggers_ && alive &&
                world_.factoryPerkMachinesEnabled()) {
                trigger=SV_FactoryPerkTriggerAt(mapTriggers_,playerState->origin,
                    StandingPlayerTraceBounds.midpoint,StandingPlayerTraceBounds.halfSize);
                if(trigger)rule=SV_TriggerHintRule(*trigger);
            }
            if (!trigger && !nearestLoot && !repairBarrier && mapTriggers_ && alive &&
                factoryInteractablesEnabled_) {
                auto reach=StandingPlayerTraceBounds.halfSize;reach[0]+=12;reach[1]+=12;
                for(const auto &t:mapTriggers_->triggers) {
                    if(t.targetname!="treasure_chest_use")continue;
                    if(!SV_MapTriggerTouches(*mapTriggers_,t,playerState->origin,
                        StandingPlayerTraceBounds.midpoint,reach))continue;
                    trigger=&t;rule=SV_TriggerHintRule(t);break;
                }
            }
            const auto unopened = trigger &&
                !openedMapTriggers_.contains(trigger->triggerIndex);
            const auto ordinaryDoor = unopened && rule &&
                (trigger->targetname == "zombie_door" ||
                    trigger->targetname == "zombie_debris") &&
                trigger->noteworthy != "factory_electric_door" &&
                trigger->cost && !trigger->target.empty();
            const auto powerSwitch = unopened && rule && !zmPowerOn_ &&
                trigger->targetname == "use_elec_switch";
            const auto perk = trigger ? zmPerkMachine(*trigger) : nullptr;
            const auto perkOwned = perk &&
                (playerState->perks[perk->word] & perk->mask) != 0;
            // A powered machine is still promptable before the switch: retail
            // answers it with ZOMBIE_NEED_POWER. After power it changes to the
            // machine's price string, unless this life already owns the perk.
            const auto perkPrompt = unopened && rule && perk && !perkOwned;
            const auto ammoBox = rule && trigger && world_.factoryPerkMachinesEnabled() &&
                trigger->noteworthy == "ammobox_trigger";
            std::string interactionHint;
            if(trigger && factoryInteractablesEnabled_) {
                if(factoryTeleportersEnabled_)interactionHint=factoryTeleportHint(client.clientNum,*trigger);
                if(interactionHint.empty())interactionHint=factoryBoxHint(client.clientNum,*trigger);
            }
            const auto actionable = ordinaryDoor || powerSwitch || perkPrompt || ammoBox || !interactionHint.empty();
            if (!actionable)
            {
                trigger = nullptr;
                rule = nullptr;
                mapTriggerHintTarget_.erase(client.clientNum);
            }
            else
            {
                mapTriggerHintTarget_[client.clientNum] = trigger;
            }
            if (ammoBox) {
                const auto hold = factoryAmmoHolds_.find(client.clientNum);
                if (hold != factoryAmmoHolds_.end() && hold->second.active &&
                    world_.snapshot().serverTime - hold->second.lastSeen <= 500) {
                    cursorHintTrigger_.erase(client.clientNum);
                    static_cast<void>(world_.clearPlayerCursorHint(client.clientNum));
                    continue;
                }
            }
            // NOTHING GOES ON THE WIRE UNLESS THE ANSWER CHANGED. The playerstate
            // delta already suppresses an unchanged field, so this is not about bytes
            // -- it is so the log says something once per doorway instead of thirty
            // times a second, and so a failure is legible in it.
            const auto previous = cursorHintTrigger_.find(client.clientNum);
            auto current = nearestLoot
                ? SvLootHintKeyBase | nearestLoot->handle.entityNum
                : (repairBarrier ? 0x40000000u
                                 : (trigger ? trigger->triggerIndex : 0xFFFFu));
            // The same trigger changes text when power changes. Include that
            // state in the cache key so a second player's live prompt cannot
            // remain stuck on NEED_POWER after the switch is thrown.
            if (perkPrompt) {
                current |= zmPowerOn_ ? 0x00010000u : 0x00020000u;
                if(world_.factoryPerkMachinesEnabled())
                    current |= SV_FactoryPerkPriceUnits(playerState->perks[0])<<20;
            }
            const bool interactionChanged=factoryInteractionHintCache_[client.clientNum]!=interactionHint;
            factoryInteractionHintCache_[client.clientNum]=interactionHint;
            if (!interactionChanged && previous != cursorHintTrigger_.end() && previous->second == current)
                continue;
            cursorHintTrigger_[client.clientNum] = current;
            if (nearestLoot)
            {
                // THE WEAPON PROMPT, NOT A TEXT ONE. cursorHint carries the gun
                // itself, so the client draws the weapon's own icon and its own
                // pick-up line; there is no hint string to register and no band slot
                // to spend. See setPlayerWeaponCursorHint.
                const auto set = world_.setPlayerWeaponCursorHint(
                    client.clientNum,
                    nearestLoot->weaponAssetIndex,
                    nearestLoot->handle.entityNum);
                OlMod::RuntimeLog::write(
                    OlMod::RuntimeLog::Channel::GameServer,
                    "loot HINT client=" + std::to_string(client.clientNum) +
                        " entity=" +
                        std::to_string(nearestLoot->handle.entityNum) +
                        " weapon=" +
                        std::to_string(nearestLoot->weaponAssetIndex) +
                        " cursorHint=" +
                        std::to_string(
                            nearestLoot->weaponAssetIndex +
                            SvCursorHintWeaponBase) +
                        " set=" + std::to_string(set));
                continue;
            }
            if (!repairBarrier && (!trigger || !rule))
            {
                static_cast<void>(world_.clearPlayerCursorHint(client.clientNum));
                continue;
            }
            if(!interactionHint.empty() && trigger && trigger->targetname=="treasure_chest_use" &&
                factoryBox_.phase==SvFactoryBoxPhase::Offer && factoryBox_.owner==client.clientNum &&
                factoryBox_.rewardKind==SvFactoryBoxRewardKind::Weapon) {
                static_cast<void>(world_.setPlayerWeaponCursorHint(client.clientNum,factoryBox_.offer,
                    factoryBox_.display ? factoryBox_.display->entityNum : SvNoHintEntityNum));
                continue;
            }
            // THE GAME'S OWN KEYS, NOT TEXT THIS SERVER MADE UP -- see
            // TriggerHintRules, where every string is either pinned by the shipped
            // `ncs_hnt_localized_common_gametype_zm` block or is a value retail's own
            // server was measured writing into this band.
            //
            // SENT AS A KEY IN THIS SERVER'S OWN SLOT rather than by pointing
            // cursorHintString at the client's preloaded index. Both would work, but
            // the preloaded index depends on how many hint entries the zones loaded
            // ahead of zm contributed, which is a property of the CLIENT's load order
            // that this server cannot see. Writing the key into a slot we own is
            // independent of all that, and the client localizes a key from a
            // configstring exactly the same way -- C-2021-8-30[22-12-10]zm's server
            // does it for ZOMBIE_RANDOM_WEAPON_1000 and a dozen others.
            //
            // KEYED BY THE STRING, NOT BY THE TRIGGER. Seven ammo crates and four
            // doors share one prompt each, and the band is only 96 wide -- one slot
            // per distinct string is what retail does and what fits.
            // OLMOD(factory_perk_machines): own a separate localized string per
            // price, so one buyer never rewrites another buyer's displayed cost.
            std::string pricedPerkHint;
            if(perkPrompt && zmPowerOn_ && world_.factoryPerkMachinesEnabled()) {
                pricedPerkHint=rule->hintString;
                const auto begin=pricedPerkHint.find('\x15'),end=pricedPerkHint.find('\x14');
                if(begin!=std::string::npos && end!=std::string::npos && end>begin)
                    pricedPerkHint.replace(begin+1,end-begin-1,
                        std::to_string(SV_FactoryPerkPriceUnits(playerState->perks[0])));
            }
            const std::string_view hintText = !interactionHint.empty() ? std::string_view{interactionHint} : repairBarrier
                ? std::string_view{"ZOMBIE_BUTTON_REWARD_BARRIER"}
                : (perkPrompt && !zmPowerOn_
                        ? std::string_view{"ZOMBIE_NEED_POWER"}
                        : (!pricedPerkHint.empty()?std::string_view{pricedPerkHint}:rule->hintString));
            auto hintString = hintStringSlots_.find(std::string{ hintText });
            if (hintString == hintStringSlots_.end())
            {
                const auto index = registerHintString(hintText);
                if (!index)
                    continue;
                hintString = hintStringSlots_
                                 .emplace(std::string{ hintText }, *index)
                                 .first;
            }
            // ENTITYNUM_NONE FOR THE ENTITY, because this server has no entity for a
            // trigger and will not invent one. The client multiplies this by 624 and
            // indexes its centity array, and 2047 is the value retail itself parks
            // there when there is no hint -- so it is in bounds by construction. It
            // only matters on the weapon-pickup path, which a HINT_NOICON text prompt
            // never takes. Giving triggers real numbers is the entity-numbering change
            // in 19-entity-numbering-and-triggers.md, and it is deliberately not this.
            const auto set = world_.setPlayerCursorHint(
                client.clientNum,
                SvCursorHint::NoIcon,
                hintString->second,
                SvNoHintEntityNum);
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer,
                "cursor hint client=" + std::to_string(client.clientNum) +
                    (repairBarrier
                         ? " barrier=" + *repairBarrier
                         : " trigger=" + std::to_string(trigger->triggerIndex) +
                               " " + std::string{trigger->targetname} +
                               (trigger->noteworthy.empty()
                                    ? std::string{}
                                    : "/" + std::string{trigger->noteworthy})) +
                    " hintString=" + std::to_string(hintString->second) +
                    " cs=" +
                    std::to_string(
                        HintStringConfigStringBase + hintString->second) +
                    " set=" + std::to_string(set));
        }
    }

    void ServerCore::driveClientEquipment(const std::span<const SvWorldClientInput> activeClients)
    {
        const auto &slots = clients_.clients();
        std::erase_if(equipmentLives_, [&](const auto &entry) {
            return std::ranges::none_of(activeClients, [&](const auto &client) {
                return client.clientNum == entry.first;
            });
        });
        for (const auto &client : activeClients)
        {
            const auto ps = world_.playerState(client.clientNum);
            if (!ps || client.clientNum >= slots.size()) continue;
            if (ps->pmType == SvPmTypeDead || client.gameplayState != ClientGameplayState::Playing)
            {
                equipmentLives_.erase(client.clientNum);
                continue;
            }
            if (world_.zombieDownedState(client.clientNum)) continue;
            const auto &slot = slots[client.clientNum];
            auto life = equipmentLives_.find(client.clientNum);
            if (life == equipmentLives_.end() || life->second.xuid != slot.xuid ||
                life->second.spawnGeneration != ps->spawnGeneration)
            {
                const auto equipment = equipmentLoadoutProvider_
                    ? equipmentLoadoutProvider_(slot.xuid, slot.selectedLoadout) : std::nullopt;
                if (!equipment || !world_.equipPlayerEquipment(client.clientNum, *equipment)) continue;
                life = equipmentLives_.insert_or_assign(client.clientNum,
                    EquipmentLife{slot.xuid, ps->spawnGeneration, false}).first;
                OlMod::RuntimeLog::write(OlMod::RuntimeLog::Channel::GameServer,
                    "equipment granted client=" + std::to_string(client.clientNum) +
                    " lethal=" + std::to_string(equipment->weapons[0].weaponAssetIndex) +
                    " tactical=" + std::to_string(equipment->weapons[1].weaponAssetIndex));
            }
            if (!life->second.announced)
            {
                // CODREF(1649370): y updates equipped-offhand at cg+C7FB0,
                // which feeds usercmd+18; retail sends y906 on each spawn.
                const auto equipped = world_.playerState(client.clientNum);
                if (equipped)
                    life->second.announced = clients_.queueReliableCommand(client.clientNum,
                        "y " + std::to_string(equipped->offhandWeaponAssetIndex));
            }
        }
    }

    bool ServerCore::addClientXp(
        const std::uint32_t clientNum,
        const std::int32_t delta)
    {
        return !matchStatus_.completed && clients_.addClientXp(clientNum, delta);
    }

    void ServerCore::observeUavWeaponChanges(std::span<const SvWorldEvent> events)
    {
        for (const auto &event : events)
        {
            if (event.type != SvWorldEventType::WeaponChanged ||
                event.clientNum >= clients_.clients().size()) continue;
            auto &owner = uavOwners_[event.clientNum];
            const auto xuid = clients_.clients()[event.clientNum].xuid;
            if (owner.xuid != xuid) owner = {xuid, {}};
            if (owner.committedLife != event.spawnGeneration)
            {
                owner.lastGun = 0;
                owner.returning = owner.returnQueued = false;
            }
            owner.committedLife = event.spawnGeneration;
            owner.committedWeapon = event.weaponAssetIndex;
            if (event.weaponAssetIndex && event.weaponName != "killstreak_uav_mp")
            {
                owner.lastGun = event.weaponAssetIndex;
                owner.returning = owner.returnQueued = false;
            }
        }
    }

    void ServerCore::driveClientUav(std::span<const SvWorldClientInput> activeClients)
    {
        std::erase_if(uavOwners_, [&](const auto &entry) {
            return std::ranges::none_of(activeClients, [&](const auto &client) {
                return client.clientNum == entry.first;
            });
        });
        const auto &slots = clients_.clients();
        const auto now = world_.snapshot().serverTime;
        // The implementation milestone is FFA. Explicit test configuration
        // may exercise the same owner in another fixture without changing the
        // production mode boundary.
        const bool uavRadarEnabled = uavRadarDuration_ &&
            (matchGameType_ == "dm" || uavRadarTestOverride_);
        for (const auto &client : activeClients)
        {
            if (client.clientNum >= slots.size()) continue;
            const auto ps = world_.playerState(client.clientNum);
            if (!ps) continue;
            auto &owner = uavOwners_[client.clientNum];
            const auto xuid = slots[client.clientNum].xuid;
            if (owner.xuid != xuid) owner = {xuid, {}};
            std::erase_if(owner.radarExpiries, [&](auto expiry) {
                return !uavRadarEnabled || matchStatus_.completed ||
                    static_cast<std::int32_t>(now - expiry) >= 0;
            });
            // INFERRED test values: native bit0 enables radar and mask0C
            // selects normal/fast sweep (checkpoint74). IW4 FFA counts UAVs
            // per GUID and preserves active aircraft across the owner's death.
            const auto radar = owner.radarExpiries.empty() ? 0 :
                owner.radarExpiries.size() == 1 ? 5 : 9;
            if (!owner.radarExpiries.empty())
            {
                (void)world_.setPlayerRadarFlags(client.clientNum, static_cast<std::uint8_t>(radar));
                owner.radarManaged = true;
            }
            else if (owner.radarManaged)
            {
                (void)world_.setPlayerRadarFlags(client.clientNum, 0);
                owner.radarManaged = false;
            }
            if (matchStatus_.completed) continue;
            const auto life = perkLives_.find(client.clientNum);
            const bool alive = client.gameplayState == ClientGameplayState::Playing && ps->pmType != SvPmTypeDead;
            // Persistent character progress is not the death-reset streak.
            const bool eligible = life != perkLives_.end() && !life->second.persistentRewards &&
                ps->rewardIds()[1] == 1;
            const auto score = clients_.clientScore(client.clientNum);
            owner.state.observe(ps->spawnGeneration, alive, eligible,
                static_cast<std::uint32_t>(std::max(score ? score->killstreak : 0, 0)), ps->rewardTargets()[1]);
            if (!alive)
            {
                owner.returning = owner.returnQueued = false;
                owner.committedLife.reset();
                owner.lastGun = 0;
                continue;
            }
            const bool heldGun = owner.lastGun && std::ranges::any_of(ps->heldWeapons,
                [&](const auto &held) { return held.weaponAssetIndex == owner.lastGun; });
            // Explicit single-player diagnostic, never ordinary earning.
            if (uavRadarEnabled && uavRadarTestGrant_ && !owner.testRewardGranted &&
                owner.state.owned != UINT32_MAX)
            {
                ++owner.state.owned;
                owner.testRewardGranted = true;
            }
            if (uavRadarEnabled && !owner.returning && owner.weapon && heldGun &&
                owner.state.owned && owner.state.grantedLife == ps->spawnGeneration &&
                owner.committedLife == ps->spawnGeneration &&
                owner.committedWeapon == owner.weapon->weaponAssetIndex &&
                ps->currentWeaponAssetIndex == owner.committedWeapon)
            {
                // A committed end-frame notification is required, not a
                // requested usercmd or WeaponSwitchStarted. The next fixed
                // frame supplies the IW4 waittillframeend use boundary.
                owner.radarExpiries.reserve(owner.radarExpiries.size() + 1);
                if (world_.consumePlayerUavAction(client.clientNum, owner.weapon->weaponAssetIndex))
                {
                    owner.radarExpiries.push_back(now + uavRadarDuration_);
                    --owner.state.owned;
                    owner.state.grantedLife.reset();
                    owner.returning = true;
                    owner.returnQueued = false;
                    (void)world_.setPlayerRadarFlags(client.clientNum,
                        owner.radarExpiries.size() == 1 ? 5 : 9);
                }
            }
            if (owner.returning)
            {
                // Do not re-grant a queued charge while still holding UAV:
                // re-enabling it can otherwise auto-consume the next reward.
                // Reliable queue failure retries without spending again.
                if (!owner.returnQueued && heldGun)
                    owner.returnQueued = clients_.queueReliableCommand(client.clientNum,
                        "a " + std::to_string(owner.lastGun));
                continue;
            }
            if (!owner.state.owned || owner.state.grantedLife == ps->spawnGeneration) continue;
            const auto weapon = uavWeaponProvider_ ? uavWeaponProvider_() : std::nullopt;
            if (weapon && world_.grantPlayerUav(client.clientNum, *weapon))
            {
                owner.weapon = weapon;
                owner.state.grantedLife = ps->spawnGeneration;
            }
        }
    }

    void ServerCore::driveClientPerks(
        const std::uint32_t serverTime,
        const std::span<const SvWorldClientInput> activeClients)
    {
        // CODREF(1649370): sub_52B8E0 observes rising bits at ps+0x584.
        // Retail DM clears these on death and asserts them again after spawn.
        // Capture the class once per life so changing class while alive takes
        // effect with the same respawn that installs its weapons.
        const auto &slots = clients_.clients();
        std::erase_if(perkLives_, [&](const auto &entry) {
            return std::ranges::none_of(activeClients, [&](const auto &client) {
                return client.clientNum == entry.first;
            });
        });
        for (const auto &client : activeClients)
        {
            const auto playerState = world_.playerState(client.clientNum);
            if (!playerState || client.clientNum >= slots.size())
                continue;
            // Zombie Siege has no multiplayer reward loadout. Clear all five
            // runtime slots, not only the three profile-owned slots: slots 0/4
            // can retain state from the front-end/player profile and make the
            // client draw the vertical MP scorestreak stack in a zm match.
            // Repeat before every fixed-frame projection because native Pmove
            // imports the client's predicted playerState between snapshots.
            if (matchGameType_ == "zm")
                (void)world_.clearPlayerRewardState(client.clientNum);
            if (playerState->pmType == SvPmTypeDead ||
                client.gameplayState != ClientGameplayState::Playing)
            {
                perkLives_.erase(client.clientNum);
                (void)world_.setPlayerAbilities(client.clientNum, {});
                (void)world_.setPlayerEquippedRewards(client.clientNum, {}, {});
                continue;
            }
            if (matchGameType_ == "zm")
            {
                // Zombie perks are bought from map machines and persist only
                // for this life. Applying the selected multiplayer class here
                // overwrote those purchases a moment later and also exposed MP
                // perk presentation in Zombie Siege. Spawn/death already clears
                // ps.perks; leave the live machine-owned mask alone.
                perkLives_.erase(client.clientNum);
                (void)world_.setPlayerAbilities(client.clientNum, {});
                (void)world_.setPlayerEquippedRewards(client.clientNum, {}, {});
                continue;
            }
            const auto &slot = slots[client.clientNum];
            auto life = perkLives_.find(client.clientNum);
            if (life == perkLives_.end() || life->second.xuid != slot.xuid ||
                life->second.spawnGeneration != playerState->spawnGeneration)
            {
                const auto perks = perkLoadoutProvider_
                    ? perkLoadoutProvider_(slot.xuid, slot.selectedLoadout)
                    : std::nullopt;
                if (!perks)
                    continue;
                if (!world_.setPlayerAbilities(client.clientNum, perks->abilities))
                    continue;
                // Capture rewards alongside this life's perks: Hardline must
                // not change while alive when the pending class changes.
                // Zombie Siege owns its battery/ability HUD and has no MP
                // scorestreak loadout.  Publishing the profile's three reward
                // slots in zm makes the client draw the vertical multiplayer
                // killstreak stack over the mode HUD.
                const auto rewards = matchGameType_ != "zm" && rewardLoadoutProvider_
                    ? rewardLoadoutProvider_(slot.xuid) : std::nullopt;
                const auto targets = rewards
                    ? SV_EquippedRewardTargets(*rewards, perks->abilities.killstreakShift)
                    : std::nullopt;
                std::array<std::uint8_t, 3> rewardIds{}, rewardCosts{};
                if (targets)
                    for (std::size_t i = 0; i < targets->size(); ++i)
                    {
                        rewardIds[i] = (*targets)[i].id;
                        rewardCosts[i] = (*targets)[i].target;
                    }
                (void)world_.setPlayerEquippedRewards(client.clientNum, rewardIds, rewardCosts);
                life = perkLives_.insert_or_assign(client.clientNum, PerkLife{
                    .xuid = slot.xuid,
                    .spawnGeneration = playerState->spawnGeneration,
                    .assertAt = serverTime + SvPerkAssertDelayMilliseconds,
                    .perks = *perks,
                    .persistentRewards = rewards && rewards->persistentCosts,
                }).first;
            }
            auto &state = life->second;
            if (state.asserted || serverTime < state.assertAt)
                continue;
            if (world_.setPlayerPerks(client.clientNum, state.perks.bits))
            {
                state.asserted = true;
                OlMod::RuntimeLog::write(
                    OlMod::RuntimeLog::Channel::GameServer,
                    "perks asserted client=" + std::to_string(client.clientNum) +
                    " bits=" + std::to_string(state.perks.bits[0]) + "," +
                    std::to_string(state.perks.bits[1]) + "," +
                    std::to_string(state.perks.bits[2]));
            }
        }
    }

    void ServerCore::driveClientUiScreens(
        const std::uint32_t serverTime,
        const std::span<const SvWorldClientInput> activeClients)
    {
        // THE ASKING HALF (section 109c). `r`/`u`/`v`/`q` each carry one index
        // bounded at 0x3F and the client answers with `cmd mr ...`, which
        // SV_ParseMenuResponse has handled all along. Nothing here is a new
        // capability; it is a request that was never made.
        //
        // THE SEQUENCE BELOW IS COPIED FROM THE DEMO, NOT COMPOSED. See
        // re/demo-re/12-dm-timeline.txt: the first spawn puts u 11 FIRST and
        // sends no u 9, and every one of the 24 respawns puts it LAST and does.
        // That asymmetry is measured, so it is reproduced rather than tidied
        // away. What each index MEANS is section 109d's co-occurrence reading
        // and is INFERRED - which is why this sends the retail sequence exactly
        // instead of picking indices that seem right.
        // MEASURED (12-dm-timeline.txt seq 15/16/17, serverTime 43100): the
        // connect trio rides in the SAME message as the gamestate, before any
        // spawn. Verified in out.exe rather than assumed: `9` is a sub-verb
        // dispatcher (sub_60D210) over six tokens -- ready, cinematic_wait,
        // purchase, consume, refresh_loadouts, and a numeric default -- and
        // `ready` is the cheapest of them: it sets ONE byte, HIBYTE of
        // word_34F41A8, which sub_5C98C0 hands to the UI as a variant. So
        // `9 ready 0` tells the client's menus the server is ready and does
        // nothing else. Its `0` argument is read by the OTHER branches only.
        //
        // CORRECTS SECTION 109c on one point: it is `9 cinematic_wait`, not
        // `9 ready`, that builds "cmd mr %i %i cinematic_done" -- so the
        // connect trio does NOT close the request/response loop. Nothing here
        // depends on a reply; SV_ParseMenuResponse still has no asker.
        static constexpr std::array ConnectScreens{
            "9 ready 0", "q 2", "u 18" };
        static constexpr std::array FirstSpawnScreens{
            "u 11", "r 2", "r 3", "r 1", "v 18" };

        // THE JOIN SEQUENCE IS PER GAMETYPE, AND `dmz` DOES NOT GET THE dm ONE.
        //
        // MEASURED 2026-09-04 with `demoq.py cmds` over the first burst of two retail
        // captures, Essential/demos (see the demo-library note):
        //
        //   dm  C-2021-7-25[1-19-26]dm    s ui_DMKillScore "50"  S 1214  9 ready 0  q 2  u 18
        //   dmz C-2021-7-25[22-0-7]dmz    s ui_DMKillScore "1"           9 ready 0  L 13 6
        //                                 r 2  r 3  r 1  v 18  u 11  I 0 0 0
        //
        // Three differences, all of them ours to fix: retail's dmz join sends `L 13 6`
        // and `I 0 0 0`, sends NEITHER `q 2` NOR `u 18`, and orders `u 11` AFTER the
        // r/v cluster rather than before it. We sent the dm sequence on every map.
        //
        // WHY IT MATTERS: on mp_battlecity the client took the gamestate and then never
        // sent a usercmd (no `pmove-slice`) and never acked a baseline (no
        // `snapshot baseline source=acked`), so no playerstate was ever built for it --
        // `snapshot build rejected failure=missing_playerstate init=1` -- and it ended on
        // 无法加入游戏会话, "Unable to join game session". mp_nuked on the same stack minutes
        // later produced all of those lines. A client waiting on a handshake it never
        // receives is exactly that shape.
        //
        // `L` and `I` ARE NOT DECODED. They are reproduced from the capture verbatim,
        // arguments included, which is the same rule the dm sequence above was written
        // under: send what retail sent, do not invent indices that seem right. `I 0 0 0`
        // is the dmz join's own form -- the dm RESPAWN cluster's `I <s1> <s2> 0` carries
        // two numbers that differ per respawn and stays unsent because those are undecoded.
        static constexpr std::array DmzConnectScreens{
            "9 ready 0", "L 13 6" };
        // `s 0201 "1"` IS THE ONE COMMAND RETAIL SENDS ON EVERY MODE AND WE SEND ON NONE.
        //
        // MEASURED in both captures -- dm at serverTime 43100 (seq 35) and dmz at 23000
        // (seq 51), once each, a few seconds after the join burst. A grep of the whole
        // ol-mod tree for "0201" returns nothing, so this server has never sent it.
        //
        // This project already named it: the C# GameServer's status-command work called
        // it the thing that "lets the client into the match", and its own fix was gated
        // behind server-commands.txt (default 0), so it has stayed inert there too.
        //
        // WHY IT IS TRIED HERE AND NOT EVERYWHERE. mp_nuked reaches a live match without
        // it, so it is demonstrably not required on cha -- our client gets in by some
        // other route. dmz has no such route: the client takes the gamestate, sends 68
        // packets, then waits 46 SECONDS and tears the session down (MatchMaking 21/3),
        // which is a client waiting for a signal that never comes, not one refusing
        // anything. This is the most conspicuous signal we never send. Scoped to dmz so
        // a mode that currently works cannot regress on it.
        //
        // TIMING IS APPROXIMATED. Retail sends it seconds AFTER the join burst, not
        // inside it; this rides the first-spawn cluster, which is the closest existing
        // hook. If it changes the failure but does not fix it, the delay is the next
        // variable to move, not the command.
        // THE WHOLE RETAIL dmz JOIN BURST, REPLAYED IN ORDER. DELIBERATELY A SHOTGUN.
        //
        // Sending one missing command per build-and-run cost four cycles and four
        // negatives (the ui-screen order, the loot band, `I 0 0 0`, `s 0201`). Counting
        // what retail actually sends in the window ending at its `s 0201` shows why that
        // was hopeless: 24 commands against our 10.
        //
        // MEASURED, C-2021-7-25[22-0-7]dmz, serverTime 18500..23000, in this order --
        // `demoq.py cmds`. `f "MP_CONNECTED..."` and `s ui_DMKillScore` are omitted
        // because this server already sends both by other paths.
        //
        // NOTHING HERE IS DECODED, and that is on purpose. `r`, `H`, `i`, `w`, `o` and
        // the numeric `s` dvars are reproduced byte for byte from the capture rather
        // than reasoned about -- the same rule the dm sequence was written under. The
        // point is to learn whether the burst as a whole is what the client waits on;
        // if it is, BISECT THIS LIST, do not keep it as-is.
        //
        // `a 1213` is retail's own weapon grant for that match and is the one value here
        // that may not port -- `a <n>` is the spawning player's weapon, and this build
        // reports firstDynamicWeapon=1147 on mp_battlecity. Suspect it first if the
        // client's weapon comes out wrong rather than the join failing.
        // THE REST OF RETAIL'S JOIN BURST WAS TRIED AND WITHDRAWN. Retail sends 24
        // commands in the window ending at `s 0201`; this sends 10. The other 14 --
        // `r`, `H`, `i 300 4.000000 0 1`, `a 1213`, `w 0 12 0`, `9 refresh_loadouts`,
        // `s 605 "0"`, `s 0195 "UK_F1_"`, `{ n\amb_dmz_ext_wind_med_tonal\t\20000`,
        // `o 1 "plain" 1 0.3 1.4`, `s 478/480/479` -- were replayed verbatim in retail's
        // order on 2026-09-04 and changed NOTHING: the client still sent 65 packets,
        // stopped, produced no `pmove-slice`, and timed out on `missing_playerstate`.
        // Removed rather than kept, because 14 undecoded commands that demonstrably do
        // nothing are a trap for whoever reads this next. They are listed here so the
        // experiment is not run twice; the capture has them if they are ever wanted.
        static constexpr std::array DmzFirstSpawnScreens{
            "r 2", "r 3", "r 1", "v 18", "u 11", "I 0 0 0", "s 0201 \"1\"" };

        // WETWORK'S OWN JOIN BURSTS, FROM THE COMPLETE RETAIL COOP DEMO.
        //
        // C-2021-7-25[22-11-33]coop sends these at its first snapshot (10250),
        // then the second list at 10950. In particular it sends neither `q 2`
        // nor the connect-time `u 18` used by DM. `9 cinematic_wait 0` opens the
        // campaign cinematic handshake, and `s 0201 "1"` is the admission
        // signal the old C# server also identified as letting the client enter.
        // Replaying the DM burst on coop left out both signals and the client
        // stopped sending immediately after its first populated snapshot.
        //
        // Retail also sends `d 12246 1201`, but 12246 is the exclusive upper
        // bound of the client's weapon-definition registry. out.exe
        // sub_590A60 immediately initializes every newly exposed index through
        // sub_58F370. Our current session registers through 1168, so replaying
        // retail's bound made sub_58F370 dereference the first absent entry,
        // index 1169, at 0x58F3C0. Keep the bound produced by this gamestate
        // until the captured campaign weapon tail is registered as real assets.
        static constexpr std::array WetworkConnectScreens{
            "9 ready 0",
            "s ui_hide_pausemenu_class \"1\"",
            "s 2831 \"1\"",
            "d 2555 \"compass_map_cargoship\" 4264.000000 4033.000244 -3968.000000 -4199.000000",
            "s 0189 \"mp/coFieldOrderMapCargoship.csv\"",
            "9 cinematic_wait 0",
            "s 0201 \"1\"",
            "d 394 3",
            "d 403 0.45",
            "d 404 0.5",
            "d 427 1",
        };
        static constexpr std::array WetworkFirstSpawnScreens{
            "d 2493 -3",
            "s ui_hide_pausemenu_class \"1\"",
            "r 2",
            "r 3",
            "r 1",
            "v 18",
            "u 11",
            "I 0 0 0",
            "d 756 none",
            "d 2557 \"coop_training_mp_cargoship\" 0",
            "d 2557 \"coop_training_mp_cargoship\" 1000",
        };
        static constexpr std::array WetworkActivationAfterSpawnTime{
            "s pve_set_activated_info \"\"",
            "d 5924 tag_stowed_back",
            "d 12249 tag_stow_back_mid_attach",
            "s 0193 \"0\"",
            "d 2552 n\\storm_cargoship_intro\\t\\12000",
            "s 0195 \"UK_M2_\"",
            "d 12250 tag_weapon_right",
        };

        // Only modes with their own captured burst are switched. Other gametypes
        // keep the sequence they have been playing on.
        const auto dmz = matchGameType_ == "dmz";
        const auto wetwork = matchGameType_ == "coop" &&
            matchMapName_ == "coop_training_mp_cargoship";
        const auto connectScreens = wetwork
            ? std::span<const char *const>(WetworkConnectScreens)
            : (dmz ? std::span<const char *const>(DmzConnectScreens)
                   : std::span<const char *const>(ConnectScreens));
        const auto firstSpawnScreens = wetwork
            ? std::span<const char *const>(WetworkFirstSpawnScreens)
            : (dmz ? std::span<const char *const>(DmzFirstSpawnScreens)
                   : std::span<const char *const>(FirstSpawnScreens));
        // SPLIT AROUND `a`, WHICH CARRIES A VALUE. Retail's respawn cluster is
        //     r 2, r 3, r 1, v 18, u 11, I <s1> <s2> 0, y 906, a 1297, u 9
        // and `a <n>` is the spawning player's WEAPON: the dm demo sends
        // `a 1297` on all 24 respawns and the first spawn, and `a 1281` once
        // more at 365600 -- the one frame its player changed weapon. `u 9`
        // comes after it, so the cluster cannot be one flat array any more.
        //
        // `I` and `y` are still not sent. `I <s1> <s2> 0` carries two numbers
        // that differ on every respawn and are undecoded; `y 906` lands in
        // playerState +0x3E4 and +0x3E8 with a 2 at +0x3F4 on the same frames
        // -- an offhand grant and a count, most likely -- and 906 is that
        // match's asset, not a constant to port. Both are named here rather
        // than invented.
        static constexpr std::array RespawnScreensBeforeWeapon{
            "r 2", "r 3", "r 1", "v 18", "u 11" };
        static constexpr std::array RespawnScreensAfterWeapon{ "u 9" };
        static constexpr auto DeathScreen = "u 10";

        const auto ask = [&](const std::uint32_t clientNum,
                             const std::string &command,
                             const char *why) {
            const auto queued =
                clients_.queueReliableCommand(clientNum, command);
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer,
                std::string("ui screen client ") + std::to_string(clientNum) +
                    " -> " + command + " (" + why + ")" +
                    (queued ? "" : " REJECTED") + " serverTime=" +
                    std::to_string(serverTime));
        };

        // THE ALIVE/DEAD EDGE IS THE RIGHT ONE, AND IT ONLY LOOKED WRONG
        // BECAUSE DEATH LASTED ONE FRAME. The first version of this keyed both
        // edges on pmType and the respawn cluster went out 50 ms after `u 10`,
        // which read as "pmType stops saying dead too early". It was not: the
        // player really was alive again, because a -1 death-animation duration
        // collapsed the engine's respawn hold to 1 ms and overrode dm.lua's
        // 3000 (see sv_snapshot_mp.cpp's respawnTime arming). With that fixed
        // the same edge measures 3050 ms, and spawnSequence -- which the second
        // version keyed on -- turned out never to change at all after the first
        // spawn, so it fired the death screen and no respawn ever.
        //
        // TWO WRONG READINGS OF ONE SYMPTOM, and neither was about this loop.
        // A trigger that looks unreliable is worth suspecting BEFORE the thing
        // it is reading is confirmed to work.
        for (const auto &client : activeClients)
        {
            const auto playerState = world_.playerState(client.clientNum);
            if (!playerState)
                continue;
            auto &life = uiClientLife_[client.clientNum];
            const auto playing =
                client.gameplayState == ClientGameplayState::Playing;
            const auto alive = playing && playerState->pmType != SvPmTypeDead;
            const auto sendFirstSpawn = [&]() {
                life.firstSpawnAt.reset();
                for (const auto *command : firstSpawnScreens)
                    ask(client.clientNum, command, "first spawn");
                if (wetwork)
                {
                    life.wetworkSpawnTime = serverTime;
                    life.wetworkActivationAt = serverTime + 100;
                }
            };
            const auto sendWetworkActivation = [&]() {
                life.wetworkActivationAt.reset();
                // `a` asks cgame to draw a weapon it must already own in the
                // authoritative playerState. Hold the retail command until the
                // same snapshot actually contains weapon 1198.
                const auto ownsActivationWeapon = std::ranges::any_of(
                    playerState->heldWeapons,
                    [](const SvHeldWeaponState &held) {
                        return held.weaponAssetIndex == 1198;
                    });
                if (ownsActivationWeapon)
                    ask(client.clientNum, "a 1198", "Wetwork activation");
                else
                    OlMod::RuntimeLog::write(
                        OlMod::RuntimeLog::Channel::GameServer,
                        "Wetwork activation weapon 1198 withheld: playerState does not own it");
                ask(
                    client.clientNum,
                    "d 15 " + std::to_string(life.wetworkSpawnTime),
                    "Wetwork activation");
                for (const auto *command : WetworkActivationAfterSpawnTime)
                    ask(client.clientNum, command, "Wetwork activation");
            };
            const auto scheduleFirstSpawn = [&]() {
                if (wetwork)
                {
                    life.firstSpawnAt = serverTime + 700;
                    OlMod::RuntimeLog::write(
                        OlMod::RuntimeLog::Channel::GameServer,
                        "Wetwork first-spawn burst scheduled client=" +
                            std::to_string(client.clientNum) +
                            " due=" + std::to_string(*life.firstSpawnAt));
                    return;
                }
                sendFirstSpawn();
            };
            // A slot reaches activeClients only once it is Active, which is
            // after its gamestate has gone out -- so this is the first frame
            // on which retail's connect trio could be queued, and reliable
            // commands keep their order behind the gamestate anyway.
            if (!life.connected)
            {
                life.connected = true;
                for (const auto *command : connectScreens)
                    ask(client.clientNum, command, "connect");
            }
            // OLMOD(factory-class-confirmation): Escape/back/noop are not class
            // selections. Keep waiting and re-request the native menu once for
            // each rejected response; never poll/reopen it over a valid choice.
            if (factoryEntryEnabled_ && !playing && !life.everAlive)
            {
                const auto &slot = clients_.clients()[client.clientNum];
                if (slot.lastMenuResponse &&
                    slot.lastMenuResponse->sequence != life.classMenuResponseSequence)
                {
                    const auto sequence = slot.lastMenuResponse->sequence;
                    if (!slot.pendingSelectedLoadout.empty() ||
                        clients_.queueReliableCommand(client.clientNum, "q 2"))
                    {
                        life.classMenuResponseSequence = sequence;
                        OlMod::RuntimeLog::write(
                            OlMod::RuntimeLog::Channel::GameServer,
                            "Factory class confirmation client=" +
                                std::to_string(client.clientNum) + " menu=" +
                                slot.lastMenuResponse->menuName + " response=" +
                                slot.lastMenuResponse->response +
                                (slot.pendingSelectedLoadout.empty()
                                    ? " waiting; menu re-requested" : " valid selection pending"));
                    }
                }
            }
            if (life.firstSpawnAt && serverTime >= *life.firstSpawnAt && alive)
                sendFirstSpawn();
            if (life.wetworkActivationAt &&
                serverTime >= *life.wetworkActivationAt)
            {
                sendWetworkActivation();
            }
            if (!life.seen)
            {
                life.seen = true;
                life.alive = alive;
                // Only a client already alive has had a spawn we missed; one
                // that is not gets nothing until it lives, so a client sitting
                // out is not sent a respawn it never had.
                if (alive)
                {
                    life.everAlive = true;
                    scheduleFirstSpawn();
                }
                continue;
            }
            // THE KILLCAM FIRES 1500 ms AFTER THE DEATH SCREEN, IF STILL DEAD.
            // Armed on the death edge below and fired here so that a respawn
            // arriving first simply disarms it -- which is exactly what retail
            // does: seven of its twenty-four deaths get a killcam and the other
            // seventeen are the ones whose respawn cluster went out at the same
            // 1500 ms mark. The delay is constant; the selection is the race.
            // THE FINAL KILL GETS NO PRIVATE KILLCAM. Its victim's death edge
            // lands one frame BEFORE the match is announced complete, so the
            // arm happens and then the outro starts -- and 1500 ms later a
            // death killcam fired for one player while everybody else was
            // already in the end-of-match hold. Measured: armed at serverTime
            // 15000, `match complete` at 15050, fired at 16500.
            //
            // Suppressing the EDGE is not enough, because the edge is what got
            // in first. The FIRE has to check too, and the match-end killcam at
            // +11100 is the one everybody sees.
            if (life.killCamAt && matchStatus_.completed)
            {
                life.killCamAt.reset();
                OlMod::RuntimeLog::write(
                    OlMod::RuntimeLog::Channel::GameServer,
                    "killcam DISARMED client=" +
                        std::to_string(client.clientNum) +
                        " -- this was the final kill, and the outro killcam at "
                        "+11100 is the one everybody sees serverTime=" +
                        std::to_string(serverTime));
            }
            if (life.killCamAt && serverTime >= *life.killCamAt)
            {
                const auto armedAt = *life.killCamAt;
                life.killCamAt.reset();
                const auto subject = killCamSubjects_.find(client.clientNum);
                if (!alive && subject == killCamSubjects_.end())
                {
                    OlMod::RuntimeLog::write(
                        OlMod::RuntimeLog::Channel::GameServer,
                        "killcam SKIPPED client=" +
                            std::to_string(client.clientNum) +
                            " -- nothing killed them, so there is no view to "
                            "replay serverTime=" + std::to_string(serverTime));
                }
                if (!alive && subject != killCamSubjects_.end())
                {
                    // deltaTime is a REWIND, and retail's is five seconds of
                    // footage before the kill plus however long it waited to
                    // start. Computed rather than pinned so a longer death hold
                    // still replays from the same point in the fight.
                    const auto sinceKill = serverTime >= subject->second.serverTime
                        ? serverTime - subject->second.serverTime
                        : 0u;
                    const auto deltaTime =
                        sinceKill + SvKillCamPreKillMilliseconds;
                    if (world_.setPlayerKillCam(
                            client.clientNum,
                            client.clientNum,
                            subject->second.killerClientNum,
                            deltaTime))
                    {
                        life.killCamActive = true;
                        // ONE RELIABLE COMMAND, ON THE SAME FRAME AS THE FOUR
                        // FIELDS. In the demo `i 0 0.000000 0 1` appears on
                        // exactly the eight frames the killcam fields are
                        // asserted on and on no other frame in ten minutes.
                        ask(client.clientNum, "i 0 0.000000 0 1", "killcam");
                        OlMod::RuntimeLog::write(
                            OlMod::RuntimeLog::Channel::GameServer,
                            "killcam client=" +
                                std::to_string(client.clientNum) + " killer=" +
                                std::to_string(
                                    subject->second.killerClientNum) +
                                " deltaTime=" + std::to_string(deltaTime) +
                                "ms armedAt=" + std::to_string(armedAt) +
                                " serverTime=" + std::to_string(serverTime));
                    }
                }
            }
            if (life.alive == alive)
                continue;
            life.alive = alive;
            // NO DEATH OR RESPAWN SCREENS ONCE THE MATCH IS DECIDED. The
            // intermission at +17000 changes pm_type, which is an ALIVE EDGE,
            // and this loop answered it with retail's six-command respawn
            // cluster -- `r 2`, `r 3`, `r 1`, `v 18`, `u 11`, `u 9` -- in the
            // same frame as the podium's own `q 19`. Measured in this server's
            // own demo at match-end + 17400; retail sends no such thing there.
            //
            // The edge is still CONSUMED above, so the life state stays honest
            // and the next match's first spawn is still a first spawn.
            if (matchStatus_.completed)
            {
                OlMod::RuntimeLog::write(
                    OlMod::RuntimeLog::Channel::GameServer,
                    "ui screen client " + std::to_string(client.clientNum) +
                        " -> life edge SUPPRESSED (alive=" +
                        std::to_string(alive ? 1 : 0) +
                        ") -- the match is over and the outro owns the screen "
                        "serverTime=" + std::to_string(serverTime));
                continue;
            }
            if (!alive)
            {
                ask(client.clientNum, DeathScreen, "death");
                // ARM UNCONDITIONALLY AND DECIDE AT FIRE TIME. The first version
                // of this armed only when killCamSubjects_ already named a
                // killer, and it never fired once: the death EDGE is pmType
                // going Dead, which happens on the frame the damage lands, and
                // queuePlayerKilledEvent defers the kill event by ONE FRAME. So
                // the map was always empty here and always populated 50 ms
                // later. A live match with two deaths produced two death
                // screens and zero killcams, and the log said nothing because
                // there was nothing to say.
                //
                // A death with no killer at all -- a fall, a trigger, a suicide
                // -- still arms, and the check 1500 ms later finds no subject
                // and skips. Same outcome, no race.
                //
                // OLMOD_KILLCAM=0 SUPPRESSES THE ARM, AND IT EXISTS TO SETTLE ONE QUESTION.
                //
                // A client crashes on being killed with 0xC0000005 in a TAG-MATRIX lookup
                // against a DObj that is not there (HANDOFF 144a, 150b). That crash is OLDER
                // than the killcam -- it fired on a build with no killcam, no `a <weapon>` and
                // no event ring, and on 2026-08-20 two negative controls reproduced it from an
                // earlier dll -- so the killcam did not CAUSE it. What is unmeasured is whether
                // the killcam is what makes it reliably REACHABLE, by pointing the client's view
                // at the victim's own entity across the respawn that rebuilds it.
                //
                // Cause and reachability are different questions and only the second one is
                // cheap to answer: play one match with this off. If deaths stop crashing, the
                // killcam is the trigger and the fix belongs in how it is cleared; if they still
                // crash, it is the respawn alone and the killcam can be ruled out for good.
                //
                // Default ON, so an unset environment is byte-identical to every run before it.
                static const bool killCamEnabled = [] {
                    char *value{};
                    std::size_t size{};
                    if (_dupenv_s(&value, &size, "OLMOD_KILLCAM") != 0 || !value)
                        return true;
                    const auto off = value[0] == '0';
                    std::free(value);
                    return !off;
                }();
                if (!killCamEnabled)
                {
                    OlMod::RuntimeLog::write(
                        OlMod::RuntimeLog::Channel::GameServer,
                        "killcam SUPPRESSED client=" +
                            std::to_string(client.clientNum) +
                            " -- OLMOD_KILLCAM=0. If this death does not crash the client, the "
                            "killcam is the trigger for HANDOFF 144a's tag-matrix fault "
                            "serverTime=" + std::to_string(serverTime));
                    continue;
                }
                life.killCamAt = serverTime + SvKillCamDelayMilliseconds;
                continue;
            }
            // THE RESPAWN CLEARS THE KILLCAM, and all four fields go back to
            // zero together -- the demo never shows a partial clear.
            life.killCamAt.reset();
            if (life.killCamActive)
            {
                life.killCamActive = false;
                world_.clearPlayerKillCam(client.clientNum);
            }
            killCamSubjects_.erase(client.clientNum);
            // THE FIRST SPAWN IS NOT A RESPAWN, and on this stack it almost
            // never arrives on the first-sight branch: a client is Active (so
            // it is in activeClients) while it is still WaitingForLoadout, and
            // only becomes alive once it has picked a class. That is an alive
            // edge, so before everAlive existed every first spawn was sent
            // retail's respawn cluster -- ordered differently and carrying a
            // `u 9` retail does not send on a first spawn.
            if (!life.everAlive)
            {
                life.everAlive = true;
                scheduleFirstSpawn();
                continue;
            }
            for (const auto *command : RespawnScreensBeforeWeapon)
                ask(client.clientNum, command, "respawn");
            // `a <weapon>` USED TO GO HERE AND IS WITHDRAWN. It was added in
            // 140j from the demo -- retail sends `a 1297` on the first spawn
            // and all 24 respawns -- and what `a` DOES was inferred from the
            // value, never measured.
            //
            // A player: "killing the guy still crashed his client". The client's
            // own crash report puts the access violation on the respawn frame,
            // microseconds after this cluster, in a TAG-MATRIX lookup against a
            // DObj that is not there (141d/141e). `a` is the one command in the
            // cluster this session added, it is the least established thing in
            // it, and a weapon command resolving a hand tag on a player whose
            // model is still being rebuilt is exactly that fault's shape.
            //
            // THIS IS A NARROW REVERT, NOT A DIAGNOSIS. The same crash fired
            // once on a build with no `a` at all, so removing it may change
            // nothing -- in which case it has still eliminated the newest
            // suspect, which is worth one cycle. Nothing a player can see is
            // lost: the weapon already reaches the client as playerState field
            // 39 and on the entity.
            for (const auto *command : RespawnScreensAfterWeapon)
                ask(client.clientNum, command, "respawn");
        }
        // A slot that frees up must not carry its old life state into whoever
        // reuses it, or the next occupant's first spawn reads as a respawn.
        for (auto it = uiClientLife_.begin();
             it != uiClientLife_.end();)
        {
            const auto stillActive = std::ranges::any_of(
                activeClients, [&](const SvWorldClientInput &candidate) {
                    return candidate.clientNum == it->first;
                });
            if (!stillActive)
                killCamSubjects_.erase(it->first);
            it = stillActive ? std::next(it) : uiClientLife_.erase(it);
        }
    }

    void ServerCore::announceLoadoutDvars()
    {
        for (auto &[clientNum, life] : perkLives_)
        {
            if (!life.asserted || life.announced)
                continue;
            bool queued = true;
            for (std::size_t slot = 0; slot < life.perks.itemIds.size(); ++slot)
            {
                // CODOL uses item 1 for an empty profile slot.
                const auto item = std::max(1u, life.perks.itemIds[slot]);
                queued &= clients_.queueReliableCommand(clientNum,
                    "s perkSlot_" + std::to_string(slot) + " \"" +
                    std::to_string(item) + "\"");
            }
            life.announced = queued;
        }
    }

    void ServerCore::queueAnnouncerLine(
        const std::uint32_t clientNum,
        const std::uint16_t announcerParameter,
        const bool statusGroup)
    {
        auto &dialog = announcerDialog_[clientNum];
        if (statusGroup && dialog.statusSlot &&
            *dialog.statusSlot < dialog.queue.size())
        {
            // GROUP COALESCING (_globallogic_audio.gsc leaderDialogOnPlayer):
            // a pending line of the same group is REPLACED, not followed. Two
            // lead changes inside one 3 s window must not become "you're
            // winning" then "you're losing" three seconds later, describing a
            // board that has already moved on.
            dialog.queue[*dialog.statusSlot] = announcerParameter;
            return;
        }
        if (statusGroup)
            dialog.statusSlot = dialog.queue.size();
        dialog.queue.push_back(announcerParameter);
    }

    void ServerCore::broadcastAnnouncerLine(
        const std::uint16_t announcerParameter,
        const bool statusGroup)
    {
        const auto &slots = clients_.clients();
        for (std::uint32_t clientNum{}; clientNum < slots.size(); ++clientNum)
        {
            if (slots[clientNum].state != ClientState::Active)
                continue;
            queueAnnouncerLine(clientNum, announcerParameter, statusGroup);
        }
    }

    void ServerCore::pumpAnnouncerDialog()
    {
        const auto now = world_.snapshot().serverTime;
        const auto &slots = clients_.clients();
        for (auto &[clientNum, dialog] : announcerDialog_)
        {
            if (dialog.queue.empty())
                continue;
            if (clientNum >= slots.size() ||
                slots[clientNum].state != ClientState::Active)
            {
                // A CLIENT THAT LEFT KEEPS NOTHING. Draining into a free slot
                // would send into another player's ring when the slot is reused.
                dialog.queue.clear();
                dialog.statusSlot.reset();
                continue;
            }
            if (dialog.nextPlayServerTime && now < dialog.nextPlayServerTime)
                continue;
            const auto announcerParameter = dialog.queue.front();
            dialog.queue.pop_front();
            if (dialog.statusSlot)
            {
                if (!*dialog.statusSlot)
                    dialog.statusSlot.reset();
                else
                    --*dialog.statusSlot;
            }
            dialog.nextPlayServerTime = now + SvAnnouncerDialogSpacingMs;
            // THE BANNER AND THE VOICE ARE ONE GESTURE. All fourteen `w 2 4 0`
            // in the dm demo carry a high-band `p` on the same frame; splash
            // row 4 is blank in every column, so the banner alone draws nothing.
            static_cast<void>(
                clients_.queueLocalSound(clientNum, announcerParameter));
            static_cast<void>(clients_.queueReliableCommand(
                clientNum,
                SV_BuildSplashCommand(
                    SvSplashSlotCallout,
                    SvSplashAnnouncerLine,
                    SvSplashAnnouncerLinePoints)));
        }
    }

    void ServerCore::setBattleChatterVoiceFemale(
        const std::uint32_t clientNum, const bool female)
    {
        // NO LOCK. This is called from the character customization provider,
        // which the frame loop invokes while already holding mutex_ -- taking
        // it again is "resource deadlock would occur" on a non-recursive
        // std::mutex, and it KILLED THE SERVER FRAME: `server frame terminated
        // by C++ exception`, two clients stuck on the loading screen at
        // active=0. That is the second time this feature has hit the same
        // mutex from a caller that already owned it.
        //
        // The rule for this file, learned twice: a public ServerCore method
        // takes mutex_ because the control thread may call it; anything the
        // FRAME reaches must not. This one is frame-only.
        battleChatterVoiceFemale_[clientNum] = female;
    }

    bool ServerCore::selectPlayerWeapon(std::uint32_t clientNum,
        std::uint16_t weaponAssetIndex)
    {
        const std::lock_guard lock(mutex_);
        if (!weaponAssetIndex || weaponAssetIndex > 2047 ||
            clientNum >= clients_.clients().size() ||
            clients_.clients()[clientNum].state != ClientState::Active)
            return false;
        const auto ps = world_.playerState(clientNum);
        if (!ps || std::ranges::none_of(ps->heldWeapons, [&](const auto &held) {
                return held.weaponAssetIndex == weaponAssetIndex;
            }))
            return false;
        // CODREF(1649370): reliable 'a' at 613AF9..613B0E calls the native
        // selector 59B8D0; it writes cg selection, not committed ps.weapon.
        // BO1 PlayerCmd_switchToWeapon 604BF0 / G_SelectWeaponIndex 699980
        // and Ghosts Player_SwitchToWeapon 140121180 / G_SelectWeapon
        // 14016AC80 check held ownership and send this same text command.
        return clients_.queueReliableCommand(clientNum,
            "a " + std::to_string(weaponAssetIndex));
    }

    std::uint32_t ServerCore::sendRawCommand(
        const std::span<const std::uint8_t> payload)
    {
        // Locks, like playAnnouncerLine and for the same reason: the CONTROL
        // thread's drain calls this, and that drain does not hold mutex_.
        const std::lock_guard lock(mutex_);
        if (payload.empty())
            return 0;
        // THE CALLER STATES THE CHANNEL. It used to be inferred from the first
        // byte -- printable ASCII means text -- and that was WRONG for the one
        // command this tool exists to replay: `@` is 0x40, printable, and the
        // demo records it as BINARY. The first live test sent it down the text
        // path, hit CL_ServerCommand_Dispatch's default case, did nothing, and
        // looked exactly like a negative result.
        //
        // A heuristic that is wrong for the subject of the experiment is worse
        // than no tool, so payload[0] is now an explicit channel byte:
        // 0 = text, 1 = binary. The bytes to send follow it.
        const auto binary = payload[0] != 0;
        const auto command = payload.subspan(1);
        if (command.empty())
            return 0;
        const auto &slots = clients_.clients();
        std::uint32_t reached{};
        for (std::uint32_t clientNum{}; clientNum < slots.size(); ++clientNum)
        {
            if (slots[clientNum].state != ClientState::Active)
                continue;
            const auto sent = binary
                ? clients_.queueReliableBinaryCommand(
                    clientNum,
                    std::vector<std::uint8_t>(command.begin(), command.end()))
                : clients_.queueReliableCommand(
                    clientNum,
                    std::string(
                        reinterpret_cast<const char *>(command.data()),
                        command.size()));
            reached += sent ? 1u : 0u;
        }
        return reached;
    }

    std::uint32_t ServerCore::playAnnouncerLine(
        const std::uint16_t announcerParameter)
    {
        const std::lock_guard lock(mutex_);
        const auto &slots = clients_.clients();
        std::uint32_t reached{};
        for (std::uint32_t clientNum{}; clientNum < slots.size(); ++clientNum)
        {
            if (slots[clientNum].state != ClientState::Active)
                continue;
            // The VOICE only. No `w 2 4 0` banner: an audition is asking what a
            // clip says, and a banner on screen is one more thing to mistake for
            // the answer.
            if (clients_.queueLocalSound(clientNum, announcerParameter))
                ++reached;
        }
        return reached;
    }

    void ServerCore::driveMatchAnnouncer()
    {
        const auto cues = SV_UpdateMatchAnnouncer(
            announcer_,
            matchGameType_,
            matchStatus_,
            world_.snapshot().serverTime);
        if (cues.matchStart)
        {
            // THE SPAWN SEQUENCE, and it is IW4's own, in this order.
            //
            // CODREF: iw4 raw, maps/mp/gametypes/_music_and_dialog.gsc, the
            // `spawned_player` thread --
            //     playLocalSound( game["music"]["spawn_" + self.team] );
            //     leaderDialogOnPlayer( "gametype" );        <- "Free-for-all"
            //     gameFlagWait( "prematch_done" );
            //     leaderDialogOnPlayer( "offense_obj" / "defense_obj" );
            //
            // BOTH LINES ARE QUEUED HERE AND NEITHER IS SCHEDULED. `on_your_own`
            // is free-for-all's OBJECTIVE line - the mode with no objective
            // still gets one - so it follows the gametype line through the same
            // queue rather than after a delay this project invented. The demo's
            // 3.0 s gap is the queue; demo 2's 12.5 s is a later prematch.
            //
            // The music is not dialogue and does not go through the queue: IW4
            // plays it with a bare playLocalSound on the spawn frame. MEASURED
            // in dm demo 2 at serverTime 19700, `p 2130` beside `p 1414`.
            const auto &slots = clients_.clients();
            for (std::uint32_t clientNum{}; clientNum < slots.size();
                 ++clientNum)
            {
                if (slots[clientNum].state != ClientState::Active)
                    continue;
                static_cast<void>(clients_.queueLocalSound(
                    clientNum, SvAnnouncerSpawnMusic));
            }
            broadcastAnnouncerLine(SvAnnouncerFreeForAll);
            broadcastAnnouncerLine(SvAnnouncerOnYourOwn);
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer,
                "announcer match start: p " +
                    std::to_string(SvAnnouncerSpawnMusic) +
                    " uk_spawn_music, queued p " +
                    std::to_string(SvAnnouncerFreeForAll) +
                    " uk_1mc_free_for_all then p " +
                    std::to_string(SvAnnouncerOnYourOwn) +
                    " uk_1mc_on_your_own");
        }
        if (cues.timesUp)
        {
            broadcastAnnouncerLine(SvAnnouncerTimesUp);
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer,
                "announcer p " + std::to_string(SvAnnouncerTimesUp) +
                    " uk_1mc_timesup at 30s remaining");
        }
        driveLeadChangeAnnouncer();
        pumpAnnouncerDialog();
    }

    void ServerCore::sayBattleChatter(
        const std::uint32_t speakerClientNum,
        const SvBattleChatterLine line)
    {
        const auto now = world_.snapshot().serverTime;
        // THE VOICE IS THE SPEAKER'S OWN. A player on a male character was
        // answered by a woman because this used to be a fixed `uk_f1`
        // parameter; `f1` is FEMALE VOICE 1, not a prefix. Faction and gender
        // both come from the customization this server already resolves every
        // frame and caches here for exactly this kind of late reader.
        //
        // The cache rather than the provider: characterCustomizationProvider_
        // fills a table other readers depend on and its call site documents an
        // ordering dependency, so re-invoking it from here would be reaching
        // into the middle of that. A one-frame-stale gender cannot be wrong.
        const auto customization =
            lastCharacterCustomizations_.find(speakerClientNum);
        if (customization == lastCharacterCustomizations_.end())
            return;
        // The pushed-in gender wins. customization.female is the fallback and
        // it is KNOWN WRONG on this build -- a female character reported false
        // in a live match -- so it is used only when nothing has published a
        // body model name for this client yet.
        const auto pushed = battleChatterVoiceFemale_.find(speakerClientNum);
        const auto female = pushed != battleChatterVoiceFemale_.end()
            ? pushed->second
            : customization->second.customization.female;
        const auto announcerParameter = SvBattleChatterParameter(
            customization->second.customization.faction, female, line);
        // world_ DIRECTLY, NOT worldPlayerSample. Both callers already hold
        // mutex_ - the frame loop for the reload trigger, the script builtin
        // for the kill one - and the public accessor takes it again, which on
        // a non-recursive std::mutex is "resource deadlock would occur". The
        // test suite caught it on the first run; a live match would have taken
        // the server down on the first kill. driveMatchAnnouncer reads
        // world_.snapshot() the same way for the same reason.
        const auto speakerState = world_.playerState(speakerClientNum);
        if (!speakerState)
            return;
        const auto speakerOrigin = speakerState->origin;
        if (SV_BattleChatterSuppressed(
                speakerClientNum, speakerOrigin, battleChatterSpeakers_, now))
        {
            return;
        }
        const auto &slots = clients_.clients();
        if (speakerClientNum >= slots.size())
            return;
        std::vector<SvBattleChatterListener> listeners;
        listeners.reserve(slots.size());
        for (std::uint32_t clientNum{}; clientNum < slots.size(); ++clientNum)
        {
            if (slots[clientNum].state != ClientState::Active)
                continue;
            const auto listenerState = world_.playerState(clientNum);
            if (!listenerState)
                continue;
            listeners.push_back({
                .clientNum = clientNum,
                .origin = listenerState->origin,
                .team = slots[clientNum].team,
                .alive = slots[clientNum].gameplayState ==
                    ClientGameplayState::Playing,
            });
        }
        const auto receivers = SV_BattleChatterAudience(
            speakerClientNum,
            speakerOrigin,
            slots[speakerClientNum].team,
            listeners,
            battleChatterAudience_);
        // THE SPEAKER HOLDS THE FLOOR EVEN WHEN NOBODY IS LISTENING. IW4's
        // doSound adds the speaker before playSoundToTeam and removes it after
        // the hold, with no reference to who received anything - so a line with
        // an empty audience still costs the speaker their two seconds. Making
        // the hold conditional on receivers would let a player alone in a
        // corner bank up chatter and fire it the moment someone walks in.
        battleChatterSpeakers_.erase(
            std::remove_if(
                battleChatterSpeakers_.begin(),
                battleChatterSpeakers_.end(),
                [now](const SvBattleChatterSpeaker &speaker) {
                    return now >= speaker.untilServerTime;
                }),
            battleChatterSpeakers_.end());
        battleChatterSpeakers_.push_back({
            .clientNum = speakerClientNum,
            .origin = speakerOrigin,
            .untilServerTime = now + SvBattleChatterSpeakerHoldMs,
        });
        for (const auto clientNum : receivers)
        {
            static_cast<void>(
                clients_.queueLocalSound(clientNum, announcerParameter));
        }
        if (!receivers.empty())
        {
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer,
                "battlechatter client" + std::to_string(speakerClientNum) +
                    " " +
                    (customization->second.customization.faction ==
                            SvCharacterFaction::Tf
                        ? "uk_"
                        : "ab_") +
                    (female ? "f1" : "m1") +
                    " p " + std::to_string(announcerParameter) + " heard by " +
                    std::to_string(receivers.size()));
        }
    }

    namespace
    {
        // Read once. The audience is a deployment decision, not something that
        // may change under a running match -- a line already queued against one
        // setting must not be delivered under another.
        [[nodiscard]] SvBattleChatterAudience SV_ConfiguredBattleChatterAudience()
        {
            const auto flag = [](const char *const name) {
                std::size_t length{};
                char value[8]{};
                if (getenv_s(&length, value, sizeof(value), name) != 0 ||
                    length == 0)
                {
                    return false;
                }
                return value[0] == '1';
            };
            // Team is the faithful one and wins when asked for. Otherwise the
            // speaker hears their own callouts, which is this project's own
            // choice and not IW4's -- see the enum. EXCLUDE_SELF restores
            // retail's behaviour without going all the way to team-only.
            if (flag("OLMOD_BATTLECHATTER_TEAM"))
                return SvBattleChatterAudience::Team;
            if (flag("OLMOD_BATTLECHATTER_EXCLUDE_SELF"))
                return SvBattleChatterAudience::Everyone;
            return SvBattleChatterAudience::EveryoneIncludingSpeaker;
        }
    }

    void ServerCore::driveBattleChatter()
    {
        if (!matchStatus_.configured || matchStatus_.completed)
            return;
        static const auto configuredAudience =
            SV_ConfiguredBattleChatterAudience();
        battleChatterAudience_ = configuredAudience;
        const auto &slots = clients_.clients();
        for (std::uint32_t clientNum{}; clientNum < slots.size(); ++clientNum)
        {
            if (slots[clientNum].state != ClientState::Active ||
                slots[clientNum].gameplayState != ClientGameplayState::Playing)
            {
                continue;
            }
            const auto status = world_.predictableEventStatus(clientNum);
            if (!status)
                continue;
            auto &spoken = battleChatterSequence_[clientNum];
            if (spoken == status->currentSequence)
                continue;
            spoken = status->currentSequence;
            const auto count = std::min<std::size_t>(
                status->count, status->events.size());
            for (std::size_t index{}; index < count; ++index)
            {
                // CODREF: iw4 _battlechatter_mp.gsc reloadTracking --
                // `self waittill ( "reload_start" )`. EV_RELOAD_START is 27 in
                // re/olfinal-events.tsv, and this build's own event ring
                // carries it, so the trigger needs no new plumbing at all.
                //
                // RELOAD_START, not RELOAD: the ring also carries EV_RELOAD
                // (25), EV_RELOAD_FROM_EMPTY (26) and EV_RELOAD_END (28), and
                // a player who empties a magazine produces more than one of
                // them for a single reload.
                if (status->events[index].event != SvEventReloadStartNotify)
                    continue;
                sayBattleChatter(
                    clientNum, SvBattleChatterLine::ReloadingGeneric);
                break;
            }
        }
    }

    void ServerCore::driveLeadChangeAnnouncer()
    {
        // FREE-FOR-ALL ONLY, and for the same reason the rest of the schedule
        // is: `uk_1mc_winning_fight` and `uk_1mc_losing_fight` were measured in
        // dm demos, one each, and each landed on the same frame as its own
        // music. A team mode's lead-change line is a different string this
        // project has not decoded.
        if (!matchStatus_.configured || matchStatus_.completed ||
            matchGameType_ != "dm" || !matchStatus_.startServerTime)
        {
            return;
        }
        const auto best = clients_.bestClientKills();
        // NOT `bestClientKills()` ALONE. At 0-0 it returns the lowest occupied
        // slot, so an unguarded watch announces a lead change on the first
        // frame of every match and again every time that slot changes hands
        // while nobody has scored. A lead exists once somebody is ahead of
        // nothing.
        if (!best || best->second <= 0)
            return;
        if (announcer_.leader && *announcer_.leader == best->first)
            return;
        // THE FLOOR. The leader is still recorded when the cooldown swallows the
        // announcement - otherwise the NEXT flip back would look like a fresh
        // change and announce immediately, which is the spam this prevents
        // arriving one flip later.
        const auto now = world_.snapshot().serverTime;
        const auto previous = announcer_.leader;
        announcer_.leader = best->first;
        if (announcer_.lastLeadChangeServerTime &&
            now >= *announcer_.lastLeadChangeServerTime &&
            now - *announcer_.lastLeadChangeServerTime <
                SvAnnouncerLeadChangeCooldownMs)
        {
            return;
        }
        announcer_.lastLeadChangeServerTime = now;
        // MEASURED, dm demo 1 serverTime 102000: the winning line and the
        // winning music on the same frame. Demo 1's music was the MAP's
        // (UK_winning_music_mp_cross_fire, low band); this sends the generic
        // one, and 2132 is the single value in this whole feature chosen by
        // symmetry rather than measured - see sv_gamestate_mp.hpp.
        queueAnnouncerLine(best->first, SvAnnouncerWinningFight, true);
        static_cast<void>(
            clients_.queueLocalSound(best->first, SvAnnouncerWinningMusic));
        if (previous)
        {
            // MEASURED, dm demo 2 serverTime 92600: `p 2129` and `p 1494` on
            // the same frame, to the recorder who had just been passed.
            queueAnnouncerLine(*previous, SvAnnouncerLosingFight, true);
            static_cast<void>(
                clients_.queueLocalSound(*previous, SvAnnouncerLosingMusic));
        }
        OlMod::RuntimeLog::write(
            OlMod::RuntimeLog::Channel::GameServer,
            "announcer lead change: client" + std::to_string(best->first) +
                " takes it on " + std::to_string(best->second) +
                (previous ? " from client" + std::to_string(*previous)
                          : std::string(" from nobody")));
    }

    std::array<SvHudElem, 4> SV_BuildFactoryEntryHud(
        const std::uint32_t birth, const std::uint32_t serverTime)
    {
        // CODREF(g_run_frame): out.exe 0x538B70 type1 and 0x538250 resolve
        // text+952; 0x514880 resolves the map's native constant-string table.
        // Original solo Factory demo: four current HUD rows 516..519, fade
        // births20500/21500/21750/23000 after first spawn20250; all fade out
        // at40300 for500ms. This is a recorded presentation, not recovered GSC.
        std::array<SvHudElem, 4> result{};
        if (serverTime < birth || serverTime - birth >= 20550)
            return result;
        constexpr std::array<std::uint32_t, 4> offsets{250,1250,1500,2750};
        const auto elapsed = serverTime - birth;
        for (std::size_t i{}; i < result.size(); ++i)
        {
            if (elapsed < offsets[i])
                break; // Keep a contiguous HUD prefix.
            auto &elem = result[i];
            elem.type = SvHudElemType::Text;
            elem.origin = {10.0f, -192.0f + 20.0f * static_cast<float>(i), 0.0f};
            elem.targetEntNum = EntityNumNone;
            elem.label = static_cast<std::uint16_t>(516 + i);
            elem.fontScale = 1.6f;
            elem.font = 11;
            elem.alignScreen = 0x8A;
            elem.alignOrg = 2;
            elem.flags = 5;
            elem.sort = 1.0f;
            const bool fadingOut = elapsed >= 20050;
            elem.color = fadingOut ? 0x00FFB240u : 0xFFFFB240u;
            elem.fromColor = fadingOut ? 0xFFFFB240u : 0x00FFB240u;
            elem.fadeStartTime = birth + (fadingOut ? 20050 : offsets[i]);
            elem.fadeTime = fadingOut ? 500 : 300;
        }
        return result;
    }

    void ServerCore::announceVisionSet()
    {
        // MEASURED (out.exe): the map's colour grade is the SERVER'S decision on
        // this engine, and it reaches the client as one reliable command.
        //
        // CODREF: the client's server-command dispatcher is 0x00613A40 and it
        // switches on the verb CHARACTER. Six cases are the vision family, each
        // the same five instructions -- copy argv(1) into a 0x40-byte name
        // buffer, atoi argv(2) as a blend time in milliseconds, call the applier
        // at 0x0046CEF0 with a vision TYPE index:
        //
        //     'N' 78 -> type 0   name buffer +0x192578      <- the map grade
        //     'O' 79 -> type 1   +0x1925B8
        //     'P' 80 -> type 2   +0x1925F8
        //     'Q' 81 -> type 3   +0x192638
        //     'R' 82 -> type 4   +0x192678
        //     '3' 51 -> type 5   +0x1926B8
        //
        // 0x0046CEF0 blends when the time is positive and hands a zero straight
        // to the instant setter at 0x0046CE80; both load "vision/%s.vision"
        // (0x00DB44BC) through DB_FindXAssetHeader asset type 0x24 via
        // 0x0046BFD0. A client nobody tells keeps the engine's fallback name
        // 'default' (0x00DADE10) -- a neutral grade with none of the map's sun
        // colour, contrast or filmtweaks, which is the flat look every map has
        // had in this project (HANDOFF section 98).
        //
        // MEASURED (retail 2021 demos, re/demo-re/01-reliable-commands.txt):
        // `N "mp_mountain" 0`, `N "mp_mideast" 0`, `N "mp_fav_tropical" 0` --
        // the plain map name with a zero blend, which is what stock CoD's
        // maps/mp/_load::main() produces with visionSetNaked(mapname, 0). The
        // same corpus carries the named sets on the same verb (`N "zm_begin"
        // 100`, `N "coup_sunblind" 400`) and type 5's overlays under '3'
        // (`3 "grayscale" 1000`, `3 "near_death" 20000`), which is the
        // independent confirmation that the verb letters mean what the
        // disassembly says.
        //
        // ONE NAME IS REFUSED: case 'N' compares argv(1) against "black_bw" and
        // drops the command when two no-argument predicates on one global
        // (0x005AB9A0 tests it == 1, 0x005ABA00 tests it == 2) say the client is
        // in either of those states. No other name is filtered.
        //
        // CODDIFF(vision): dest1yo's 3.3.3.3 server does not send this either,
        // so this is not a port gap being closed (section 98a) -- it is a
        // deliberate OLfinal-only addition, and the only one in this path.
        //
        // Sent per client on the frame it becomes active, the same shape as
        // announceMatchRules, so a late join is graded too.
        if (matchMapName_.empty() || SV_PerfBaseline())
            return;
        const auto &slots = clients_.clients();
        for (std::uint32_t clientNum{}; clientNum < slots.size(); ++clientNum)
        {
            if (slots[clientNum].state != ClientState::Active ||
                visionAnnounced_.contains(clientNum))
            {
                continue;
            }
            visionAnnounced_.insert(clientNum);
            const auto command = "N \"" + matchMapName_ + "\" 0";
            const auto queued =
                clients_.queueReliableCommand(clientNum, command);
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer,
                "vision set client " + std::to_string(clientNum) + " -> " +
                    command + (queued ? " queued" : " REJECTED"));
        }
        // CODREF(g_run_frame): exact client0x46CEF0/46CE80 and three original
        // Factory recordings agree: zm_begin100, then400ms later map2000.
        // OLMOD(factory-entry): first Playing is our readiness adapter. It
        // keeps stationary FX/camera separate from the generation-owned native
        // arrival movement hold established at ClientSpawn. MP is unchanged.
        if (factoryEntryEnabled_)
        {
            const auto now = world_.snapshot().serverTime;
            for (std::uint32_t n{}; n < slots.size(); ++n)
            {
                if (slots[n].state == ClientState::Free)
                {
                    if (const auto old = factoryEntries_.find(n); old != factoryEntries_.end())
                        for (const auto &carrier : old->second.arrivalCarriers)
                            if (carrier) static_cast<void>(world_.freeEntity(*carrier));
                    factoryEntries_.erase(n);
                    continue;
                }
                if (slots[n].state != ClientState::Active ||
                    slots[n].gameplayState != ClientGameplayState::Playing)
                    continue;
                auto [it, inserted] = factoryEntries_.try_emplace(n, FactoryEntryState{now});
                auto &entry = it->second;
                if (inserted)
                    OlMod::RuntimeLog::write(OlMod::RuntimeLog::Channel::GameServer,
                        "Factory entry ready client=" + std::to_string(n) +
                        " birth=" + std::to_string(now));
                // CODREF(factory-arrival): original solo snapshot carriers715/716
                // stay fixed at spawn, with FX147/174 then173 after500ms. Resolved
                // names/root replace recorded indices; first Playing is our clock.
                if (inserted && factoryArrivalModel_ && factoryArrivalFx_[0] &&
                    factoryArrivalFx_[1] && factoryArrivalFx_[2])
                {
                    if (const auto player = world_.playerState(n))
                    {
                        auto portal = player->origin;
                        portal[2] += 52.0f;
                        auto flash = player->origin;
                        const auto yaw = player->viewAngles[1] * 0.017453292519943295f;
                        flash[0] += 20.0f * std::cos(yaw);
                        flash[1] += 20.0f * std::sin(yaw);
                        flash[2] += 62.0f;
                        entry.arrivalOrigins = {portal, flash};
                        entry.arrivalCarriers[0] = world_.spawnScriptModel(
                            factoryArrivalModel_, "tag_origin", portal, {0,0,0});
                        entry.arrivalCarriers[1] = world_.spawnScriptModel(
                            factoryArrivalModel_, "tag_origin", flash, {0,player->viewAngles[1],0});
                    }
                }
                const auto age = now - entry.birth;
                for (std::size_t fx{}; fx < 3; ++fx)
                {
                    const auto carrier = fx == 0 ? 0u : 1u;
                    const auto due = fx == 2 ? 600u : 100u;
                    if (!entry.arrivalQueued[fx] && age >= due && age < 1100 &&
                        entry.arrivalCarriers[carrier])
                    {
                        entry.arrivalQueued[fx] = world_.queueScriptModelFxEvent(
                            *entry.arrivalCarriers[carrier], factoryArrivalFx_[fx],
                            factoryArrivalBone_);
                        if (entry.arrivalQueued[fx])
                            OlMod::RuntimeLog::write(OlMod::RuntimeLog::Channel::GameServer,
                                "Factory arrival FX client=" + std::to_string(n) +
                                " stage=" + std::to_string(fx) + " age=" + std::to_string(age));
                    }
                }
                // Original carriers disappear at spawn+3600 and+6100. Freeing
                // their generation-owned entities bounds attached FX lifetime.
                for (std::size_t carrier{}; carrier < 2; ++carrier)
                    if (entry.arrivalCarriers[carrier] && age >= (carrier == 0 ? 6100u : 3600u))
                    {
                        static_cast<void>(world_.freeEntity(*entry.arrivalCarriers[carrier]));
                        entry.arrivalCarriers[carrier].reset();
                    }
                if (!entry.flashQueued && now - entry.birth >= 4100)
                {
                    entry.flashQueued = clients_.queueReliableCommand(n, "N \"zm_begin\" 100");
                    if (entry.flashQueued) entry.flashAt = now;
                }
                // Measure from the actual enqueue so a late frame cannot
                // collapse both commands into one unrendered flash.
                if (entry.flashQueued && !entry.restored && now - entry.flashAt >= 400)
                {
                    entry.restored = clients_.queueReliableCommand(n, "N \"zm_factory_sh\" 2000");
                    if (entry.restored)
                        OlMod::RuntimeLog::write(OlMod::RuntimeLog::Channel::GameServer,
                            "Factory entry vision restored client=" + std::to_string(n));
                }
            }
        }
        // A slot that frees up has to be told again if it is reused.
        for (auto it = visionAnnounced_.begin(); it != visionAnnounced_.end();)
        {
            it = *it < slots.size() && slots[*it].state != ClientState::Free
                ? std::next(it)
                : visionAnnounced_.erase(it);
        }
    }

    void ServerCore::projectDeathVision()
    {
        // MEASURED (retail 2021 corpus, verb '3', 15 occurrences):
        //   3 "grayscale" 1000        3 "near_death" 20000
        // Verb '3' is case 51 of the dispatcher at 0x00613A40 and it is the
        // vision family's TYPE 5 -- the same five instructions as 'N', with the
        // name buffer at base+0x1926B8. vision/grayscale.vision and
        // vision/near_death.vision both ship in common_mp.ff, so both names
        // resolve on every MP map.
        //
        // OLMOD(death-vision): WHAT the retail server keyed those two on is NOT
        // established -- the corpus has the traffic, not its trigger, and the
        // thirteen demos are zm/sd/spy/cha. Desaturating on death and restoring
        // on spawn is the standard CoD behaviour and it is the reading the
        // configstring supports: 2562 sets type 5's baseline to the MAP's own
        // grade, which is exactly what "restore to normal" needs to mean.
        // Anything keyed on a health THRESHOLD would be an invented constant,
        // so near_death is deliberately not sent.
        //
        // The blend times are retail's own: 1000 ms into grayscale, instant
        // back, so a respawn is not spent watching the world fade in.
        if (matchMapName_.empty() || SV_PerfBaseline())
            return;
        for (const auto &event : world_.frameEvents())
        {
            const auto clientNum = event.type == SvWorldEventType::PlayerKilled
                ? (event.playerKilled
                       ? std::optional{ event.playerKilled->damage.targetClientNum }
                       : std::nullopt)
                : event.type == SvWorldEventType::ClientSpawned
                    ? std::optional{ event.clientNum }
                    : std::nullopt;
            if (!clientNum || *clientNum >= clients_.clients().size() ||
                clients_.clients()[*clientNum].state == ClientState::Free)
            {
                continue;
            }
            // WHETHER THIS IS SENT HAS NEVER BEEN MEASURED. The `3` trigger is an
            // INVENTION (see the OLMOD note above) and retail dm sends no `3` at
            // all, so nothing in this project's record shows the grayscale death
            // effect working live -- section 99's live verification was type 0
            // and the six configstrings, not this. On 2026-08-23 a player
            // reported not seeing it, and there was no instrument that could
            // separate "never queued" from "queued and not applied" from
            // "applied but nobody was looking at that client's window".
            //
            // Deaths are rare, so this logs one line per death rather than
            // sampling. It reports the CONDITION (which client, which command,
            // accepted or rejected by the ring), not the stimulus.
            const auto downedOwner=world_.zombieDownedState(*clientNum);
            // A bled-out co-op player now views a surviving teammate. Last-stand
            // blur/gray belongs to the injured life, not that spectator camera.
            const auto visionCommand =
                event.type == SvWorldEventType::PlayerKilled && !(downedOwner && downedOwner->bledOut)
                    ? std::string("3 \"grayscale\" 1000")
                    : "3 \"" + matchMapName_ + "\" 0";
            const auto visionQueued =
                clients_.queueReliableCommand(*clientNum, visionCommand);
            if (event.type == SvWorldEventType::PlayerKilled)
            {
                OlMod::RuntimeLog::write(
                    OlMod::RuntimeLog::Channel::GameServer,
                    "death vision client " + std::to_string(*clientNum) +
                        " -> " + visionCommand +
                        (visionQueued ? " queued" : " REJECTED"));
            }

            // MEASURED (dm demo, re/demo-re/12-dm-timeline.txt) -- and this one
            // IS the retail trigger, not an inference. A ten-minute retail
            // free-for-all sends `N "mp_cross_fire" 0` twenty-five times:
            //
            //   24 mid-match, each followed by an `r 2` spawn cluster 1.5-2.2 s
            //      later -- 24 consecutive pairs, no exceptions
            //   1  in the end-of-match sequence at 9:59.8
            //
            // DEATH, not spawn, and the demo proves which. There are 24 `r 2`
            // clusters; the FIRST is at 0:02.5 and has no `N` before it, which
            // is exactly the initial spawn. So the counts read 24 deaths, and
            // 1 initial spawn + 23 respawns after them. A spawn trigger would
            // have put an `N` in front of that first cluster.
            //
            // WHY a server re-asserts the map's own type-0 grade at the moment
            // of death is NOT established: the client changes vision locally for
            // its killcam and this puts it back, which is the reading that fits,
            // but the demo carries the traffic and not the reasoning. What is
            // established is when it is sent, which is what this needed.
            //
            // CODDIFF(vision): retail dm sends no `3` at all - its type-5 slot
            // is left to configstring 2562. The grayscale pair above is an
            // OLfinal-only addition and stays, because it is the death effect
            // this project actually wanted; the `N` is what retail did.
            if (event.type == SvWorldEventType::PlayerKilled)
            {
                static_cast<void>(clients_.queueReliableCommand(
                    *clientNum, "N \"" + matchMapName_ + "\" 0"));
            }
        }
    }

    void ServerCore::announceMatchCompletion()
    {
        // Four different paths set matchStatus_.completed, so the transition is
        // watched here rather than announced at each of them.
        if (!matchStatus_.completed || matchCompletionAnnounced_)
            return;
        matchCompletionAnnounced_ = true;
        matchCompletionServerTime_ = world_.snapshot().serverTime;
        clients_.setAarRoundNumber(matchGameType_=="zm"?
            static_cast<std::int32_t>(world_.zmPresentationRound()):1);
        // NOBODY RESPAWNS AFTER THIS POINT. The kill that ends a match still
        // arms a respawn three seconds out, so without this the loser stands
        // back up in the middle of the end-of-match hold -- reported by a
        // player as "after the kill and then freeze, the player respawned in
        // front of me where he died".
        world_.setMatchCompleted(true);

        if (matchGameType_=="zm" && world_.zombieTeamWiped())
        {
            // CODREF(factory-zombie-results): five original zm recordings close
            // menus and assert479 at outcome, then ui_match_complete at+1500ms.
            // No victory music, reward grants or FFA podium on this defeat path.
            static_cast<void>(clients_.SV_SetConfigString(MatchEndTimeConfigStringIndex,"0"));
            static_cast<void>(clients_.SV_SetConfigString(UiTimeLimitConfigStringIndex,"0"));
            static_cast<void>(clients_.SV_SetConfigString(MatchEndUiConfigStringIndex,"1"));
            for (std::uint32_t n=0;n<clients_.clients().size();++n)
                if (clients_.clients()[n].state!=ClientState::Free)
                    for (const auto *command:{"r","H","m 0"})
                        static_cast<void>(clients_.queueReliableCommand(n,command));
            clients_.pushScoreboardToConnected();
            return;
        }

        // MEASURED (C-2021-7-25[22-11-33]coop.demo, 480850): Wetwork
        // does not enter the competitive 32.7-second outro. On its completion
        // frame retail clears the clock, closes the current menu, selects the
        // mpOutro vision, and arms the rewards transition. The final localized
        // command follows exactly one second later in driveMatchEndSequence.
        if (matchGameType_ == "coop")
        {
            static_cast<void>(clients_.SV_SetConfigString(
                MatchEndTimeConfigStringIndex, "0"));
            const auto &campaignSlots = clients_.clients();
            std::size_t notified{};
            for (std::uint32_t clientNum{};
                 clientNum < campaignSlots.size(); ++clientNum)
            {
                if (campaignSlots[clientNum].state == ClientState::Free)
                    continue;
                notified += clients_.queueReliableCommand(clientNum, "r") ? 1u : 0u;
                static_cast<void>(clients_.queueReliableCommand(clientNum, "H"));
            }
            static_cast<void>(clients_.SV_SetConfigString(
                VisionNakedConfigStringIndex, "\"mpOutro\" 500"));
            for (std::uint32_t clientNum{};
                 clientNum < campaignSlots.size(); ++clientNum)
            {
                if (campaignSlots[clientNum].state == ClientState::Free)
                    continue;
                static_cast<void>(clients_.queueReliableCommand(
                    clientNum, "s show_random_rewards_screen \"1\""));
                static_cast<void>(clients_.queueReliableCommand(
                    clientNum, "s dw_roomJoin \"nohotjoin\""));
                static_cast<void>(clients_.queueReliableCommand(
                    clientNum, "s ui_match_complete \"1\""));
            }
            static_cast<void>(clients_.SV_SetConfigString(
                MatchEndUiConfigStringIndex, "1"));
            static_cast<void>(clients_.SV_SetConfigString(
                UiTimeLimitConfigStringIndex, "0"));
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer,
                "campaign outro armed notified=" + std::to_string(notified));
            return;
        }

        // MEASURED (dm demo, serverTime 631800, re/demo-re/12-dm-timeline.txt):
        // the FIRST thing a retail server does when the match is decided is
        // stop the clock, with two live configstring updates on the same frame:
        //
        //     d 15 0        the HUD countdown's absolute end time
        //     d 464 0       ui_timelimit
        //
        // Both indices are this project's own MatchEndTimeConfigStringIndex and
        // UiTimeLimitConfigStringIndex, which is an independent confirmation of
        // two numbers that were read off out.exe rather than off the wire.
        // Until SV_SetConfigString existed there was no way to send either, so
        // the countdown carried on ticking through a decided match.
        static_cast<void>(clients_.SV_SetConfigString(
            MatchEndTimeConfigStringIndex, "0"));
        static_cast<void>(clients_.SV_SetConfigString(
            UiTimeLimitConfigStringIndex, "0"));

        // MEASURED (retail dm, serverTime 631700/631800): immediately before
        // outcomeNotify is born, the recorder's aarScoreboard row changes from
        // xp 5997 to 7796. The +1799 is byte-for-byte the match-bonus number
        // shown by the HudElem at +1100. Freeze and award it on this one-shot
        // transition, before the match-end scoreboard push below. Recomputing
        // at +1100 used to leave the AAR at zero and could also disagree if a
        // slot or rank changed during the delay.
        if (matchGameType_ == "dm")
        {
            std::vector<std::uint32_t> topThree;
            for (const auto &[clientNum, kills] :
                clients_.topClientsByKills(SvDmPlacementLabels.size()))
            {
                static_cast<void>(kills);
                topThree.push_back(clientNum);
            }
            const auto &bonusSlots = clients_.clients();
            for (std::uint32_t clientNum{};
                 clientNum < bonusSlots.size(); ++clientNum)
            {
                if (bonusSlots[clientNum].state != ClientState::Active)
                    continue;
                const auto participation = matchParticipationMilliseconds(
                    clientNum, matchCompletionServerTime_);
                if (participation < 1'000)
                    continue;
                const auto placedTopThree = std::ranges::find(
                    topThree, clientNum) != topThree.end();
                const auto bonus = SV_CalculateDmMatchBonus(
                    bonusSlots[clientNum].rank,
                    participation,
                    placedTopThree);
                dmMatchBonuses_.insert_or_assign(clientNum, bonus);
                static_cast<void>(clients_.addClientXp(
                    clientNum, static_cast<std::int32_t>(std::min<std::uint32_t>(
                        bonus,
                        static_cast<std::uint32_t>(
                            std::numeric_limits<std::int32_t>::max())))));
            }
        }

        // `s ui_match_complete "1"` AND `H` USED TO GO OUT HERE, AT +0. THE
        // DEMO PUTS BOTH SOMEWHERE ELSE, and both moved to driveMatchEndSequence
        // where the rest of the schedule already lives:
        //
        //   `s ui_match_complete "1"`   retail sends it at +17000, on the frame
        //                               the podium scene is set up -- SEVENTEEN
        //                               SECONDS after this one. It names the
        //                               podium, not the end of the match
        //   `H`                         retail sends it three times and every
        //                               one of them lands immediately after a
        //                               bare `r`: +0, +11100 and +17400. `r`
        //                               closes (125) and `H` is cppCloseAll, so
        //                               the pair is one gesture and sending the
        //                               second half without the first was never
        //                               what a real server does
        //
        // CODREF: CG_ServerCommand 0x0057D560 case 's' reads argv as name/value
        // pairs; case 'H' calls cppCloseAll.
        //
        // THE STINGER, AND IT IS PER PLAYER. MEASURED: dm demo 1 sends `p 2131`
        // (uk_victory_music) on the exact frame the match ends, and that
        // recorder came first; dm demo 2's LAST command is `p 2128`
        // (uk_defeat_music), and that recorder lost. Same event, opposite
        // sound, decided by who is reading it - which is why this cannot be a
        // broadcast.
        //
        // Free-for-all's outcome is a SLOT (winnerClientNum) and the team modes
        // leave that empty and report a winning team instead, so both are read.
        // A draw, or a match with no winner recorded at all, gets the defeat
        // stinger for everyone: retail's own behaviour there is unmeasured, and
        // playing victory music to a player who did not win is the worse error.
        const auto &slots = clients_.clients();
        std::uint32_t victors{};
        for (std::uint32_t clientNum{}; clientNum < slots.size(); ++clientNum)
        {
            if (slots[clientNum].state != ClientState::Active)
                continue;
            const bool won = matchStatus_.winnerClientNum
                ? *matchStatus_.winnerClientNum == clientNum
                : matchStatus_.winner != SvTeam::None &&
                    slots[clientNum].team == matchStatus_.winner;
            victors += won ? 1u : 0u;
            static_cast<void>(clients_.queueLocalSound(
                clientNum,
                won ? SvAnnouncerVictoryMusic : SvAnnouncerDefeatMusic));
        }
        OlMod::RuntimeLog::write(
            OlMod::RuntimeLog::Channel::GameServer,
            "announcer match end: p " +
                std::to_string(SvAnnouncerVictoryMusic) + " to " +
                std::to_string(victors) + ", p " +
                std::to_string(SvAnnouncerDefeatMusic) + " to the rest");

        // The scoreboard is what the player looks at when the match ends, and
        // nothing else pushes it - the client only asks with a reliable 's'.
        clients_.pushScoreboardToConnected();
    }

    namespace
    {
        // THE DEATH-ANIMATION WATCHDOG. Section 187r, and it took TWO tries.
        //
        // FIRST IT COULD NOT SEE. It lived inside logPlayerPresentation behind
        // `if (++presentationLogCounter_ < 300) return;`, so a guard whose whole
        // job is to shout the instant a living player's animIndex hits zero only
        // LOOKED once every 300 frames. It sat silent through ten consecutive
        // T-posed deaths on 2026-09-04 and the player found them.
        //
        // THEN IT CRIED WOLF. Moved out here and asked "is the index zero", it
        // fired TWENTY TIMES IN TWO SECONDS at 13:33:08 -- at world spawn, where
        // zero is CORRECT: ClientSpawn zeroes playerState +0x0C8 and the legs
        // only come back once PmoveSingle's locomotion selector runs. It burned
        // its entire rate limit on the one state that is not a fault and had
        // nothing left for the deaths seven seconds later.
        //
        // SO IT LATCHES, PER CLIENT. Section 188's condition is not "the index
        // IS zero", it is "a living player's index WENT to zero" -- a player
        // that has animated this life and then stopped. A client is armed by its
        // first non-zero index and reports only on the fall, which is silent
        // through every spawn and loud exactly once when the thing that breaks
        // deaths actually happens. PER CLIENT and not one shared flag, because a
        // shared edge-trigger latches on whoever gets there first and blinds the
        // rest (codol-dobj-latch-blinded-three-states).
        //
        // Still cheap enough to run every frame: a modulo, a compare and one
        // map lookup per player entity, and nothing allocates unless it fires.
        void checkDeathAnimationRisk(const std::vector<SvEntityState> &entities)
        {
            static std::unordered_map<std::uint32_t, bool> animatedThisLife;
            static std::unordered_map<std::uint32_t, std::uint32_t> reports;
            std::array<bool, MaximumGameClients> seen{};
            for (const auto &entity : entities)
            {
                if (entity.eType != EntityTypePlayer)
                    continue;
                if (entity.clientNum < seen.size())
                    seen[entity.clientNum] = true;
                // Death legitimately clears the animation index before the
                // next spawn rebuilds the playerState and animation tree. Drop
                // the per-life latch here so that the next spawn's one-frame
                // zero cannot be misreported as a live pose collapse.
                if (entity.eFlags & SvDeadPlayerHiddenFlag)
                {
                    animatedThisLife[entity.clientNum] = false;
                    continue;
                }
                // `legs` is (flags << 10) | animIndex, so `% 1024` IS the index.
                auto &armed = animatedThisLife[entity.clientNum];
                if (entity.legsAnim % 1024 != 0)
                {
                    armed = true;
                    continue;
                }
                if (!armed)
                    continue;      // never animated yet -- the spawn zero
                armed = false;     // report the FALL once, not every frame after
                auto &reported = reports[entity.clientNum];
                if (reported >= 5)
                    continue;
                ++reported;
                OlMod::RuntimeLog::write(
                    OlMod::RuntimeLog::Channel::GameServer,
                    "DEATH ANIMATION AT RISK client=" +
                        std::to_string(entity.clientNum) + " legs=" +
                        std::to_string(entity.legsAnim) +
                        " (a LIVING player that WAS animating has fallen to"
                        " animIndex 0 -- a death in this state returns"
                        " durationMs=-1 and T-poses; section 187r) " +
                        std::to_string(reported) + "/5");
            }
            // A dead player entity is deliberately absent from the published
            // snapshot once its corpse takes over. Disarm on that absence;
            // otherwise its next spawn reappears at the legitimate one-frame
            // animation zero and looks like a live fall from the prior life.
            for (std::size_t clientNum{}; clientNum != seen.size(); ++clientNum)
            {
                if (!seen[clientNum])
                    animatedThisLife[static_cast<std::uint32_t>(clientNum)] = false;
            }
        }
    }

    void ServerCore::logPlayerPresentation()
    {
        // EVERY FRAME, BEFORE THE SAMPLING. The line below reports what a remote
        // client is told to draw and is deliberately 1-in-300; the watchdog is
        // not a report and must not inherit that cadence.
        checkDeathAnimationRisk(world_.snapshot().entities);
        // OLMOD(player-presentation-diagnostics): what a remote client is
        // actually told to draw. The weapon reaches the wire as ET_PLAYER field
        // 17, a single 32-bit word at entityState +0xD0 holding the current
        // weapon and, in its high half at +0xD2, the third-person presentation
        // selector BG_UpdatePlayerDObj falls back to. A zero there draws a
        // player with no gun, and nothing in the think path checks it - the
        // conversion is only asserted against currentWeaponAssetIndex.
        if (++presentationLogCounter_ < 300)
            return;
        presentationLogCounter_ = 0;
        std::string line;
        std::string corpses;
        for (const auto &entity : world_.snapshot().entities)
        {
            if (entity.eType == EntityTypeCorpse)
            {
                // eFlags and trType are what the three wire stages are made
                // of, so log them: the re-initialise bit must clear once, and
                // trType must move 1 -> 13 with aprType -> 10 about a second in.
                corpses += " #" + std::to_string(entity.number) + "{client=" +
                    std::to_string(entity.clientNum) + " legs=" +
                    std::to_string(entity.legsAnim) + " torso=" +
                    std::to_string(entity.torsoAnim) + " eFlags=" +
                    std::to_string(entity.eFlags) + " trType=" +
                    std::to_string(entity.positionTrajectoryType) + " aprType=" +
                    std::to_string(entity.angleTrajectoryType) + " ground=" +
                    std::to_string(entity.groundEntityNum) + "}";
                continue;
            }
            if (entity.eType != EntityTypePlayer)
                continue;
            line += " " + std::to_string(entity.clientNum) + "{weapon=" +
                std::to_string(entity.weaponAssetIndex) + " presentation=" +
                std::to_string(entity.presentationWeaponAssetIndex) +
                " offhand=" + std::to_string(entity.offhandWeaponAssetIndex) +
                " knife=" + std::to_string(entity.coKnifeStatsIndex) +
                " legs=" + std::to_string(entity.legsAnim) + " torso=" +
                std::to_string(entity.torsoAnim) +
                // BG_UpdatePlayerDObj zeroes the weapon outright, with no
                // fallback, when eFlags & 0xC00 is set. That is the one
                // remaining explanation for an empty-handed remote player
                // that static reading cannot rule out.
                " eFlags=" + std::to_string(entity.eFlags) + "}";
        }
        if (!corpses.empty())
        {
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer,
                "player-corpses" + corpses);
        }
        if (!line.empty())
        {
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer,
                "player-presentation" + line);
        }
    }

    void ServerCore::driveMatchEndSequence()
    {
        // MEASURED (dm demo, re/demo-re/12-dm-timeline.txt). Retail's end of
        // match is a 32.7-second SCHEDULE hung off the frame the match was
        // decided (serverTime 631800), not one frame of commands:
        //
        //   +0 ms       d 15 0; d 464 0; H; r; L 6 1, L 3 2, L 1 3 (the top
        //               three); sixteen `|` precaches of those three players'
        //               character models; d 479 1; p 2131
        //   +11100 ms   r; H; N "mp_cross_fire" 0; i; u 10; L 2 7
        //   +13950 ms   d 11861 645750 1000 1 0.25      timescale 1 -> 0.25
        //   +15450 ms   d 11861 647250 1000 0.25 1      and back
        //   +17000 ms   s ui_match_complete "1"; > 161; s 2972 "1";
        //               d 2557 "mp_cross_fire_tp" 0; d 13 <fog>; d 792
        //   +17400 ms   r; H; I; i; the four top3_*_current_weapon dvars; q 19
        //   +32700 ms   t "EXE_MATCHENDED"
        //
        // THE TWO SCREEN REQUESTS ARE SENT -- section 109e corrected the note
        // that used to sit here. `u 10` at +11100 and `q 19` at +17400 are not
        // content this server lacks; they are a REQUEST it never made. The
        // client draws the outro and the podium from menus and models already
        // in our shipped zones, exactly as `u 10` on death draws the death
        // camera (section 118, player-confirmed). Offsets are the demo's own,
        // measured against the frame the match was decided.
        //
        // STILL NOT SENT, each for a stated reason rather than for lack of a
        // value: the sixteen `|` precaches and the four top3_* dvars name the
        // podium players' character-model and weapon assets, and per-client
        // character customization is the one blocked subsystem (section 82e);
        // the timescale ramp at +13950/+15450 slows time for a camera move
        // whose framing we have not measured; `>`, `s 2972`, `d 479` and
        // `d 13` are that match's values on handlers that are still unnamed.
        //
        // WATCH THE AFTER-MATCH SCOREBOARD WHEN THIS FIRST RUNS. It is a
        // confirmed-working screen and `q 19` opens a full-screen layout over
        // the top of it, so a regression here shows up as the scoreboard
        // disappearing rather than as an error -- which is the shape of both
        // wrong changes section 112 caught.
        //
        // CODDIFF(match-end): `s ui_match_complete "1"` and the scoreboard go
        // out at +0 here, not at retail's +17000. Retail fills those seventeen
        // seconds with the outro; this server would show the player nothing.
        // The offset is recorded so it is a move rather than a re-measurement
        // when the outro lands.
        //
        // AND `d 2557 "<map>_tp"` IS SENT, because the asset question got an
        // answer. MEASURED offline from the shipped fastfiles, no launch:
        //
        //     common_mp.ff        193 vision assets, none ending in _tp
        //     mp_rust_long.ff     vision/mp_rust_long.vision
        //                         vision/mp_rust_long_tp.vision      <-- exists
        //     mp_cross_fire.ff    vision/mp_cross_fire_tp.vision     <-- the
        //                         exact name the retail dm demo sends at +17000
        //
        // A map's `_tp` grade ships in the MAP's own fastfile, not in common,
        // which is why the earlier search of common_mp found nothing. A map that
        // does not ship one is safe: 0x0046CEF0 and 0x0046CE80 write their state
        // record ONLY if DB_FindXAssetHeader succeeded (§99), so a missing asset
        // leaves the previous grade in place instead of falling back to
        // 'default'. Sent as `d` on configstring 2557 exactly as retail does,
        // rather than as the `N` command, so it is also what a client connecting
        // during the hold would read.
        // Three places, which is what "top3" means and what the demo sends.
        constexpr std::size_t PodiumPlaces = 3;
        constexpr std::uint32_t OutroScreenMilliseconds = 11'100;
        // MEASURED (dm demo): `d 11861 645750 1000 1 0.25` at 645800 and
        // `d 11861 647250 1000 0.25 1` at 647300, against a match decided at
        // 631800 -- so +14000 and +15500.
        constexpr std::uint32_t OutroSlowMotionStartMilliseconds = 14'000;
        constexpr std::uint32_t OutroSlowMotionEndMilliseconds = 15'500;
        // Retail's ramp start time is 50 ms BEFORE the frame carrying it, on
        // both writes -- one server frame, so the ramp is already running by
        // the time the client reads the configstring.
        constexpr std::uint32_t OutroTimescaleBackdateMilliseconds = 50;
        // MEASURED (dm demo, serverTime 648700 against a match decided at
        // 631800): the killcam's four playerState fields go back to zero here,
        // 500 ms before the podium screen and on the frame retail sends its
        // first `I 17433 0 0`.
        constexpr std::uint32_t OutroKillCamEndMilliseconds = 16'900;
        constexpr std::uint32_t OutroVisionMilliseconds = 17'000;
        constexpr std::uint32_t PodiumScreenMilliseconds = 17'400;
        constexpr std::uint32_t OutroFinalScoresMilliseconds = 31'500;
        constexpr std::uint32_t MatchEndedMilliseconds = 32'700;
        if (!matchStatus_.completed || !matchCompletionAnnounced_ ||
            matchEndedAnnounced_)
        {
            return;
        }
        const auto elapsed =
            world_.snapshot().serverTime - matchCompletionServerTime_;
        if (matchGameType_=="zm" && world_.zombieTeamWiped())
        {
            const auto sendAll=[&](const char *command) {
                for (std::uint32_t n=0;n<clients_.clients().size();++n)
                    if (clients_.clients()[n].state!=ClientState::Free)
                        static_cast<void>(clients_.queueReliableCommand(n,command));
            };
            if (elapsed>=SvZombieResultsMilliseconds && !outroVisionAnnounced_)
            {
                outroVisionAnnounced_=true;
                clients_.pushScoreboardToConnected();
                // Arm native after-action UI only after scoreboard profile patches.
                sendAll("s ui_match_complete \"1\"");
                OlMod::RuntimeLog::write(OlMod::RuntimeLog::Channel::GameServer,
                    "ZM REVIVE results armed: native AAR, no reward grant");
            }
            if (elapsed>=SvZombieMatchEndedMilliseconds)
            {
                matchEndedAnnounced_=true;
                sendAll("t \"EXE_MATCHENDED\"");
                OlMod::RuntimeLog::write(OlMod::RuntimeLog::Channel::GameServer,
                    "ZM REVIVE match ended: EXE_MATCHENDED");
            }
            return;
        }
        if (matchGameType_ == "coop")
        {
            // MEASURED (Wetwork demo): 481850 - 480850 = 1000 ms.
            constexpr std::uint32_t CampaignMatchEndedMilliseconds = 1'000;
            if (elapsed < CampaignMatchEndedMilliseconds)
                return;
            matchEndedAnnounced_ = true;
            const auto &campaignSlots = clients_.clients();
            std::size_t notified{};
            for (std::uint32_t clientNum{};
                 clientNum < campaignSlots.size(); ++clientNum)
            {
                if (campaignSlots[clientNum].state == ClientState::Free)
                    continue;
                if (clients_.queueReliableCommand(
                        clientNum, "t \"EXE_MATCHENDED\""))
                {
                    ++notified;
                }
            }
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer,
                "campaign ended t=\"EXE_MATCHENDED\" held=" +
                    std::to_string(elapsed) + "ms notified=" +
                    std::to_string(notified));
            return;
        }
        const auto askEveryone = [&](const char *command, const char *why) {
            const auto &slots = clients_.clients();
            std::size_t asked{};
            for (std::uint32_t clientNum{}; clientNum < slots.size(); ++clientNum)
            {
                if (slots[clientNum].state == ClientState::Free)
                    continue;
                if (clients_.queueReliableCommand(clientNum, command))
                    ++asked;
            }
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer,
                std::string("ui screen ") + why + " -> " + command +
                    " asked=" + std::to_string(asked) + " elapsed=" +
                    std::to_string(elapsed) + "ms");
        };
        // THE ROSTER GOES AT +0, WITH THE `|` PRECACHES IN THE DEMO. `L
        // <clientNum> <slot>` binds a client to one of nineteen presentation
        // slots and the client fills that slot out of its OWN clientInfo -- see
        // sub_7494A0 and sub_7C3280 on out.exe, reached from CG_ServerCommand's
        // case 'L' at 0x006141E9. Slots 1..3 are the podium's three places;
        // retail's own `L 6 1` / `L 3 2` / `L 1 3` put the match winner, who is
        // that demo's recording client, in slot 1.
        //
        // The sixteen `|` precaches that ride alongside are asset RESIDENCY
        // (case 124 -> sub_49CF30(4, name, 1)), and sub_7C31B0 reads clientInfo
        // rather than those names. Both players in a local two-client match are
        // already rendered in the map, so this is testable without the
        // per-client character customization section 82e records as blocked. If
        // the stage is still empty with a roster sent, the precaches are the
        // next question -- not the first one.
        // No elapsed test: this is the +0 step, and `elapsed >= 0` on an
        // unsigned is a tautology that reads like a threshold. The flag is
        // the whole guard.
        if (!podiumRosterAsked_ && !SV_PerfBaseline())
        {
            podiumRosterAsked_ = true;
            const auto ranked = clients_.topClientsByKills(PodiumPlaces);
            // THE `|` PRECACHES, AND THEY NEEDED NO NEW SUBSYSTEM. Retail's
            // match-end frame carries sixteen of these -- five or six component
            // models per podium player, in the fpa/fja/han/hea/heg/boo/ves
            // families -- and 109e read them as blocked on per-client character
            // customization (82e). The server's own log says otherwise: every
            // live match already prints `character models RESOLVED entity=N ...
            // names=fpa_goose_ss_m_11,boo_empty_ss_s,fja_infbasea_tf_m_wht_00,
            // han_infbasea_tf_m_00,hea_socomb_sc_m`. Same families, same shape.
            // The resolver ran and the strings were thrown away.
            //
            // `|` is CG_ServerCommand case 124 -> sub_49CF30(4, name, 1), an
            // XModel load BY NAME, so the one real risk is naming a model the
            // client cannot find -- which is why these are exactly the names the
            // client's own resolver produced from its own tables.
            //
            // Deduped across players: two clients wearing the same character
            // resolve to the same five names, and precaching one model twice is
            // a wasted reliable command in a sequence that already carries
            // twenty.
            if (characterModelNamesProvider_)
            {
                std::set<std::string> precached;
                for (const auto &[clientNum, kills] : ranked)
                {
                    for (auto &name : characterModelNamesProvider_(clientNum))
                    {
                        if (name.empty() || !precached.insert(name).second)
                            continue;
                        askEveryone(("| " + name).c_str(), "podium model");
                    }
                }
                if (precached.empty())
                {
                    OlMod::RuntimeLog::write(
                        OlMod::RuntimeLog::Channel::GameServer,
                        "podium models NONE RESOLVED -- no `|` precache sent, so "
                        "the stage can only draw what is already resident");
                }
            }
            for (std::size_t place = 0; place < ranked.size(); ++place)
            {
                askEveryone(
                    ("L " + std::to_string(ranked[place].first) + " " +
                        std::to_string(place + 1)).c_str(),
                    "podium roster");
            }
            if (ranked.empty())
            {
                OlMod::RuntimeLog::write(
                    OlMod::RuntimeLog::Channel::GameServer,
                    "podium roster EMPTY -- no scored client to stand anyone up");
            }
        }
        if (!matchEndScoresAsked_ && !SV_PerfBaseline())
        {
            matchEndScoresAsked_ = true;
            // MEASURED (dm demo, serverTime 631800): `r 19` rides with the
            // roster on the frame the match is decided, eleven seconds before
            // the killcam and seventeen before the podium. A player named it
            // from the other side -- "it will show the two factions with what
            // score they got" -- which is the screen this opens. `r` and `q`
            // share section 109c's request family; 19 is the same index the
            // podium later uses on `q`, on a different sink.
            askEveryone("r 19", "match end scores");
            // AND A BARE `r`, WITH NO ARGUMENT, IMMEDIATELY AFTER. Measured by
            // diffing our own demo against the retail one at match end
            // (HANDOFF 138): retail sends `r 19` AND three bare `r` in the +0
            // burst, and this server has only ever sent the first. `r` is the
            // CLOSE half of 109c's request family (125), so a bare one is
            // "close the current screen" -- which is what has to happen before
            // a different one can be shown.
            //
            // A player has reported the faction score screen missing at match
            // end ever since the outro existed. This is the cheapest candidate
            // for it and it is one reliable command.
            askEveryone("r", "match end screen close");
            // AND `H` BELONGS TO THAT BARE `r`, NOT TO THE MATCH-COMPLETE DVAR.
            // Retail sends `r` then `H` three times in the outro -- +0, +11100
            // and +17400 -- and never one without the other. This server sent
            // the `H` at +0 alone, from announceMatchCompletion, and neither of
            // the other two at all.
            askEveryone("H", "match end popups close");
            // CONFIGSTRING 479, SET TO 1, AND IT IS THE ONLY WRITE TO IT IN THE
            // WHOLE MATCH. The band is CL_ApplyConfigStringDvars' name/value
            // pairing -- names at 24..343, values at 344..663 -- so 479 is the
            // value slot for the dvar named at 159, in the same band as
            // ui_scorelimit (463) and ui_timelimit (464) this file already
            // owns. Its NAME is not in this demo's gamestate and is not read
            // here; what is measured is that a real server sets it to 1 in the
            // match-decided frame and never touches it again.
            static_cast<void>(clients_.SV_SetConfigString(
                MatchEndUiConfigStringIndex, "1"));
        }
        if (elapsed >= PodiumScreenMilliseconds && !podiumWeaponsAsked_ &&
            !SV_PerfBaseline())
        {
            // MEASURED (seq 1464..1467): four dvars, sent in the same frame as
            // `q 19` and immediately before it. player0/1/2 are podium slots
            // 1/2/3; `self` is the viewer's own, which in the demo equals
            // player0 because the recording client won.
            podiumWeaponsAsked_ = true;
            // THE THIRD AND LAST `r` + `H` PAIR, THE SECOND `I 17433 0 0`, AND
            // THE EIGHTH `i`. Retail's +17400 frame runs `r`, `H`,
            // `I 17433 0 0`, `i 0 0.000000 0 1`, the four top3 weapon dvars,
            // then `q 19` -- so all four go out here, ahead of the dvars, and
            // `q 19` stays in the step below that owns it.
            //
            // The `i` here carries no killcam: its four playerState fields were
            // cleared 500 ms earlier, at +16900, which is what retail does too.
            // So this one is the same camera command asking for the podium's
            // view rather than a replay.
            askEveryone("r", "podium screen close");
            askEveryone("H", "podium popups close");
            askEveryone("I 17433 0 0", "podium");
            askEveryone("i 0 0.000000 0 1", "podium camera");
            const auto ranked = clients_.topClientsByKills(PodiumPlaces);
            const auto weaponOf = [&](const std::uint32_t clientNum) {
                const auto entity = world_.playerEntity(clientNum);
                return std::to_string(
                    entity ? entity->networkState.weaponAssetIndex : 0);
            };
            for (std::size_t place = 0; place < PodiumPlaces; ++place)
            {
                const auto value = place < ranked.size()
                    ? weaponOf(ranked[place].first)
                    : std::string("0");
                askEveryone(
                    ("s top3_player" + std::to_string(place) +
                        "_current_weapon \"" + value + "\"").c_str(),
                    "podium weapon");
            }
            // `self` is PER CLIENT -- it is the viewer's own weapon, not the
            // winner's -- so it cannot go through askEveryone.
            const auto &slots = clients_.clients();
            for (std::uint32_t clientNum{}; clientNum < slots.size(); ++clientNum)
            {
                if (slots[clientNum].state == ClientState::Free)
                    continue;
                static_cast<void>(clients_.queueReliableCommand(
                    clientNum,
                    "s top3_self_current_weapon \"" + weaponOf(clientNum) +
                        "\""));
            }
        }
        if (elapsed >= OutroScreenMilliseconds && !outroScreenAsked_ &&
            !SV_PerfBaseline())
        {
            outroScreenAsked_ = true;
            // THE SAME `r` + `H` PAIR THAT OPENS THE OUTRO OPENS THE KILLCAM.
            // Retail's +11100 frame is `r`, `H`, `N "<map>" 0`, `i ...`,
            // `u 10`, `L 2 7` -- in that order, close first.
            askEveryone("r", "outro killcam screen close");
            askEveryone("H", "outro killcam popups close");
            // THE KILLCAM NEEDS ITS VISION SET, AND `u 10` ALONE IS NOT ENOUGH.
            // Retail's +11100 frame carries `N "<map>" 0` alongside `u 10` --
            // the naked vision set, the same command 99 recovered and this
            // server already builds for map load. Measured by diffing our own
            // demo against retail's (138): retail sends it here, we never have.
            //
            // A player has reported no killcam on death and none at match end.
            // `u 10` is live-confirmed working for the DEATH camera (118), so
            // the missing half at match end is more likely the presentation
            // state than the request.
            if (!matchMapName_.empty())
                askEveryone(("N \"" + matchMapName_ + "\" 0").c_str(),
                            "outro vision");
            // SLOT 7 IS THE ONE `L` TREATS SPECIALLY, and retail sends it in
            // this exact frame -- `L 2 7` rides alongside `u 10` at +11100.
            // sub_7C3280's slot-7 branch does something no other slot does: it
            // reads a per-client dword at session+0x393C+4*clientNum and, if it
            // is set, writes dword_CA28050[clientNum] from a switch on the
            // global dword_CA27AC8 (1->4, 2->5, 3->6, 4->7). That is a
            // presentation MODE selector, and it is the only candidate this
            // sequence has for the outro's camera.
            //
            // INFERRED, NOT MEASURED, and the difference matters: retail sends
            // client 2 there, which is the client its `cl_shoutcastSelectedClient
            // "2"` at connect also names -- so retail's choice is "whoever the
            // shoutcast is watching", not "the winner". This server has no
            // shoutcast selection, and the winner is the podium's own subject,
            // so the winner is what it sends. If the camera moves to the wrong
            // player, THIS is the line to change, not the verb.
            //
            // ORDER IS RETAIL'S OWN: `r`, `H`, `N`, `i`, `u 10`, `L 2 7`. The
            // camera selection is LAST, after the killcam has been asked for
            // and the screen opened, so it is resolved here and emitted below.
            const auto outroCameraClient = clients_.bestClientKills();
            // AND THE MATCH-END KILLCAM IS THE SAME FOUR FIELDS AS A DEATH'S,
            // ON THE SAME FRAME AS THE SAME COMMAND. Retail's eighth and last
            // `i 0 0.000000 0 1` is here, at match-end + 11100, with the killcam
            // fields carrying deltaTime 16450 instead of a death's 6000..6500.
            //
            // 16450 is 11100 + 5350, so it is the same rule the deaths follow --
            // rewind past the kill by about five seconds -- measured from the
            // FINAL KILL rather than from a death of your own. Every client sees
            // it, which is why this one is not per-victim.
            //
            // With no final kill (a time-limit end, which is how this server's
            // own test matches finish) there is nothing to replay and nothing is
            // sent, rather than a killcam of a kill that did not happen.
            if (lastMatchKill_)
            {
                const auto sinceKill =
                    world_.snapshot().serverTime >= lastMatchKill_->serverTime
                        ? world_.snapshot().serverTime -
                            lastMatchKill_->serverTime
                        : 0u;
                const auto deltaTime =
                    sinceKill + SvKillCamPreKillMilliseconds;
                const auto &outroSlots = clients_.clients();
                std::size_t shown{};
                for (std::uint32_t clientNum{}; clientNum < outroSlots.size();
                     ++clientNum)
                {
                    if (outroSlots[clientNum].state == ClientState::Free)
                        continue;
                    if (world_.setPlayerKillCam(
                            clientNum,
                            lastMatchKill_->victimClientNum,
                            lastMatchKill_->killerClientNum,
                            deltaTime))
                    {
                        ++shown;
                    }
                }
                askEveryone("i 0 0.000000 0 1", "outro killcam");
                OlMod::RuntimeLog::write(
                    OlMod::RuntimeLog::Channel::GameServer,
                    "outro killcam killer=" +
                        std::to_string(lastMatchKill_->killerClientNum) +
                        " victim=" +
                        std::to_string(lastMatchKill_->victimClientNum) +
                        " deltaTime=" + std::to_string(deltaTime) +
                        "ms clients=" + std::to_string(shown));
            }
            else
            {
                OlMod::RuntimeLog::write(
                    OlMod::RuntimeLog::Channel::GameServer,
                    "outro killcam SKIPPED -- no kill was recorded this match, "
                    "so there is nothing to replay");
            }
            askEveryone("u 10", "outro");
            if (outroCameraClient)
            {
                askEveryone(
                    ("L " + std::to_string(outroCameraClient->first) +
                        " 7").c_str(),
                    "outro camera");
            }
        }
        // THE MATCH ENDS IN SLOW MOTION AND THEN COMES BACK, and it is two
        // writes to the timescale configstring this file already owns:
        //
        //   +14000   d 11861 <serverTime-50> 1000 1 0.25     down to a quarter
        //   +15500   d 11861 <serverTime-50> 1000 0.25 1     back to normal
        //
        // "%i %i %g %g" is start time, duration, from, to (see
        // TimescaleConfigStringIndex). Retail's start time is 50 ms BEFORE the
        // frame that carries it -- 645750 sent at 645800 -- which is one server
        // frame, so the ramp is already running when the client reads it.
        if (elapsed >= OutroSlowMotionStartMilliseconds &&
            !outroSlowMotionStarted_ && !SV_PerfBaseline())
        {
            outroSlowMotionStarted_ = true;
            const auto start = world_.snapshot().serverTime >=
                    OutroTimescaleBackdateMilliseconds
                ? world_.snapshot().serverTime -
                    OutroTimescaleBackdateMilliseconds
                : 0u;
            static_cast<void>(clients_.SV_SetConfigString(
                TimescaleConfigStringIndex,
                std::to_string(start) + " 1000 1 0.25"));
        }
        if (elapsed >= OutroSlowMotionEndMilliseconds &&
            !outroSlowMotionEnded_ && !SV_PerfBaseline())
        {
            outroSlowMotionEnded_ = true;
            const auto start = world_.snapshot().serverTime >=
                    OutroTimescaleBackdateMilliseconds
                ? world_.snapshot().serverTime -
                    OutroTimescaleBackdateMilliseconds
                : 0u;
            static_cast<void>(clients_.SV_SetConfigString(
                TimescaleConfigStringIndex,
                std::to_string(start) + " 1000 0.25 1"));
        }
        if (elapsed >= OutroKillCamEndMilliseconds && !outroKillCamCleared_ &&
            !SV_PerfBaseline())
        {
            outroKillCamCleared_ = true;
            // `I 17433 0 0`, TWICE: here and again at +17400 with the podium.
            // The verb is undecoded (109b lists its callees) and every other
            // use of it in the match carries two DIFFERENT numbers on a respawn
            // -- `I 1551 4422 0`, `I 2236 50885 0` -- while both of these carry
            // the same 17433 and a zero. Sent verbatim, which is the standard
            // this project holds itself to: the demo says what a real server
            // SENT, and inferring what the client does with it is what has gone
            // wrong every time (112).
            askEveryone("I 17433 0 0", "podium prologue");
            const auto &killCamSlots = clients_.clients();
            for (std::uint32_t clientNum{}; clientNum < killCamSlots.size();
                 ++clientNum)
            {
                if (killCamSlots[clientNum].state == ClientState::Free)
                    continue;
                world_.clearPlayerKillCam(clientNum);
            }
        }
        if (elapsed >= PodiumScreenMilliseconds && !podiumScreenAsked_ &&
            !SV_PerfBaseline())
        {
            podiumScreenAsked_ = true;
            askEveryone("q 19", "podium");
        }
        if (elapsed >= OutroVisionMilliseconds && !outroVisionAnnounced_ &&
            !matchMapName_.empty() && !SV_PerfBaseline())
        {
            outroVisionAnnounced_ = true;
            const auto value = "\"" + matchMapName_ + "_tp\" 0";
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer,
                "match end vision -> d " +
                    std::to_string(VisionNakedConfigStringIndex) + " " + value +
                    " clients=" +
                    std::to_string(clients_.SV_SetConfigString(
                        VisionNakedConfigStringIndex, value)));
        }
        // THE REST OF RETAIL'S +17000 FRAME, WHICH IS WHERE THE PODIUM SCENE IS
        // ACTUALLY SET UP. Everything here is sent verbatim or derived from
        // this server's own state; nothing is transplanted from the demo's map.
        if (elapsed >= OutroVisionMilliseconds && !outroPodiumStateAsked_ &&
            !SV_PerfBaseline())
        {
            outroPodiumStateAsked_ = true;
            // MEASURED AT +17000, NOT AT +0, and this server sent it at +0 for
            // as long as the outro existed. `ui_match_complete` names the
            // PODIUM -- retail sets it on the frame it sets up the podium
            // scene, seventeen seconds after the match is decided.
            askEveryone("s ui_match_complete \"1\"", "podium ui");
            // `> 161` and `s 2972 "1"` ride the same frame. Both are sent
            // verbatim: `>` is undecoded (its two gating flags are unread) and
            // 2972 is a numeric dvar NAME, which is a thing this build has
            // (dvar names are numeric here). The demo is this build, so its
            // dvar-name ids and configstring indices are this build's -- which
            // is the same reasoning that made `d 15`, `d 464`, `d 2557` and
            // `d 11861` correct, each independently confirmed against out.exe.
            askEveryone("> 161", "podium accumulator");
            askEveryone("s 2972 \"1\"", "podium dvar");
            // `d 792` WITH NO VALUE IS A CLEAR. During the match retail puts
            // `\ent\381\offs\0 0 0\mat\-1\offmat\-1\flags\8` there -- an icon
            // attached to an entity -- and the podium frame empties it. This
            // server never writes it, so this only matters when a map has.
            static_cast<void>(clients_.SV_SetConfigString(
                ObjectiveMarkerConfigStringIndex, ""));
            // AND THE FOG IS ZEROED, NOT REPLACED. Retail re-sends the fog
            // configstring with its first token -- a START TIME -- set to 0 and
            // the other ten unchanged, which turns the fade off rather than
            // changing the fog.
            //
            // ITS TEN VALUES ARE THE MAP'S, so retail's cannot be copied: this
            // demo is mp_cross_fire and a match here is not. If this server has
            // never set configstring 13 there is nothing to rewrite and it says
            // so, rather than inventing a fog.
            if (const auto fog =
                    clients_.configString(FogConfigStringIndex))
            {
                const auto space = fog->find(' ');
                if (space != std::string::npos)
                {
                    static_cast<void>(clients_.SV_SetConfigString(
                        FogConfigStringIndex, "0" + fog->substr(space)));
                }
            }
            else
            {
                OlMod::RuntimeLog::write(
                    OlMod::RuntimeLog::Channel::GameServer,
                    "podium fog NOT REWRITTEN -- this server has never set "
                    "configstring 13, so there is no start time to zero and "
                    "retail's own eleven tokens belong to its map, not this one");
            }
        }
        // MEASURED at +31500: one last `r 19`, 1200 ms before EXE_MATCHENDED.
        // The same request the +0 frame opens the outro with, repeated as the
        // podium ends.
        if (elapsed >= OutroFinalScoresMilliseconds && !outroFinalScoresAsked_ &&
            !SV_PerfBaseline())
        {
            outroFinalScoresAsked_ = true;
            askEveryone("r 19", "podium end scores");
        }
        if (elapsed < MatchEndedMilliseconds)
            return;
        matchEndedAnnounced_ = true;

        // CODREF: CG_ServerCommand 0x00613A40 case 't' is the localized
        // notification the client prints and acts on; the dm demo's last
        // reliable record of the whole match is `t "EXE_MATCHENDED"`.
        const auto &slots = clients_.clients();
        std::size_t notified{};
        for (std::uint32_t clientNum{}; clientNum < slots.size(); ++clientNum)
        {
            if (slots[clientNum].state == ClientState::Free)
                continue;
            if (clients_.queueReliableCommand(clientNum, "t \"EXE_MATCHENDED\""))
                ++notified;
        }
        // `clients=` counted slots.size() on 2026-08-23 and printed 18 for a
        // two-player match -- maxClients, not a client count. An instrument that
        // reports the size of the array it walked has told you nothing about the
        // thing it walked.
        OlMod::RuntimeLog::write(
            OlMod::RuntimeLog::Channel::GameServer,
            "match ended gametype=" + matchGameType_ + " t=\"EXE_MATCHENDED\"" +
                " held=" + std::to_string(elapsed) + "ms notified=" +
                std::to_string(notified));
    }

    void ServerCore::setTopPlayersCamera(std::optional<SvWorldSpawnPoint> camera)
    {
        topPlayersCamera_ = std::move(camera);
    }

    void ServerCore::setTopPlayersPlaces(std::vector<SvWorldSpawnPoint> places)
    {
        topPlayersPlaces_ = std::move(places);
    }

    void ServerCore::setPodiumFallbackModel(
        const std::uint16_t index, std::string name)
    {
        podiumFallbackModelIndex_ = index;
        podiumFallbackModelName_ = std::move(name);
    }

    void ServerCore::precacheCharacterModels(
        const std::uint32_t clientNum, const std::uint16_t characterItemId)
    {
        // MAKE EVERY PLAYER'S CHARACTER MODELS RESIDENT ON EVERY CLIENT.
        //
        // BG_UpdatePlayerDObj builds a player from characterInfo's model NAMES: it
        // registers the base name at +0x18 and then walks ten attachment names at
        // +0x20. A name whose XModel is not loaded registers to nothing and the player
        // draws as nothing -- valid characterInfo, a resolved name, a live DObj handle,
        // and no visible body. Every one of those was measured on a client that was
        // not drawing a player.
        //
        // AND THE MAP DOES NOT CARRY THESE. mp_nuked's model band publishes exactly one
        // fpa_ entry, `fpa_pro_ss_m_light`, while a character 545 player resolves to
        // `fpa_goose_ss_m_15`. So whether a client can draw another player has been
        // down to whether that asset happened to be resident already -- and the two
        // clients are SEPARATE PROCESSES, which is why it alternated between them from
        // run to run and looked random.
        //
        // `|` is CG_ServerCommand case 124 -> an XModel load BY NAME, the same command
        // the podium already uses to make three players' characters resident before it
        // stands them up. This does it for the living, which is where it was always
        // needed.
        if (!characterModelNamesProvider_)
            return;
        // ONCE PER CHARACTER PER CLIENT. The provider allocates a vector of strings, so
        // calling it per frame is the same mistake the outfit resolve made; the answer
        // only changes when the player's character does.
        const auto seen = precachedCharacterFor_.find(clientNum);
        if (seen != precachedCharacterFor_.end() && seen->second == characterItemId)
            return;

        // DO NOT LATCH ON AN EMPTY ANSWER. The names are filled by the DObj build,
        // which runs LATER than the first frame on which a customization exists, so the
        // first call here returns nothing. Marking the character done at that point --
        // which the first version did, before looking -- means the real names never get
        // precached at all and the guard hides it forever. Latch only once there is
        // something to latch.
        const auto names = characterModelNamesProvider_(clientNum);
        if (names.empty())
            return;
        precachedCharacterFor_[clientNum] = characterItemId;

        const auto &slots = clients_.clients();
        std::size_t sent = 0;
        for (const auto &name : names)
        {
            if (name.empty() || !precachedCharacterModels_.insert(name).second)
                continue;
            const auto command = "| " + name;
            for (std::uint32_t target = 0; target < slots.size(); ++target)
            {
                if (slots[target].state == ClientState::Free)
                    continue;
                static_cast<void>(
                    clients_.queueReliableCommand(target, command.c_str()));
            }
            ++sent;
        }
        if (sent)
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer,
                "character models PRECACHED client=" + std::to_string(clientNum) +
                    " character=" + std::to_string(characterItemId) +
                    " new=" + std::to_string(sent) + " total=" +
                    std::to_string(precachedCharacterModels_.size()));
    }

    void ServerCore::setOutfitModelSlots(std::vector<std::uint16_t> freeSlots)
    {
        // NO LOCK, deliberately -- see registerOutfitModelConfigString.
        outfitModelSlots_ = std::move(freeSlots);
        outfitModelIndexes_.clear();
    }

    std::optional<std::uint16_t> ServerCore::registerOutfitModelConfigString(
        const std::string &name)
    {
        // GIVE AN OUTFIT MODEL A SLOT IN THE BAND AND TELL EVERY CLIENT ABOUT IT.
        //
        // The model configstrings are SLOT-KEYED with no counter behind them -- unlike
        // the weapon range, whose monotonic index counter is what makes a mid-match
        // append error 181 -- so setting one live is safe and needs no re-host. Only
        // slots the MAP left empty are handed out, so nothing the map published is
        // ever overwritten.
        //
        // The `|` precache rides with it because the two do different jobs: the
        // configstring gives the client an INDEX to resolve, and `|` (CG_ServerCommand
        // case 124 -> an XModel load by name) makes sure the asset is actually
        // resident. The podium already pairs them the same way.
        if (name.empty() || name.size() >= 128 || name.front() == '*')
            return std::nullopt;
        // NO LOCK. THIS IS CALLED WITH mutex_ ALREADY HELD, from the character
        // customization provider on the game thread, and mutex_ is not recursive:
        // taking it here threw `resource deadlock would occur`, which terminated the
        // server frame and left one player stuck on 等待玩家数据 with no player data.
        // setPodiumFallbackModel next door takes no lock for the same reason -- the
        // convention in this class is that provider-side helpers run under the
        // caller's lock.
        if (const auto known = outfitModelIndexes_.find(name);
            known != outfitModelIndexes_.end())
        {
            return known->second;
        }
        if (outfitModelSlots_.empty())
            return std::nullopt;
        const auto slot = outfitModelSlots_.back();
        outfitModelSlots_.pop_back();
        if (!clients_.SV_SetConfigString(
                static_cast<std::uint16_t>(ModelConfigStringBase + slot), name))
        {
            // PUT THE SLOT BACK. A failed publish that still consumed a slot would
            // leak the band away one outfit at a time and the next model would be
            // refused for a reason that has nothing to do with it.
            outfitModelSlots_.push_back(slot);
            return std::nullopt;
        }
        outfitModelIndexes_.emplace(name, slot);
        const auto &slots = clients_.clients();
        const auto precache = "| " + name;
        for (std::uint32_t clientNum = 0; clientNum < slots.size(); ++clientNum)
        {
            if (slots[clientNum].state == ClientState::Free)
                continue;
            static_cast<void>(
                clients_.queueReliableCommand(clientNum, precache.c_str()));
        }
        OlMod::RuntimeLog::write(
            OlMod::RuntimeLog::Channel::GameServer,
            "outfit model REGISTERED index=" + std::to_string(slot) +
                " name=" + name + " (" +
                std::to_string(outfitModelSlots_.size()) + " band slots left)");
        return slot;
    }

    bool ServerCore::publishActorModelConfigString(
        const std::uint16_t index, const std::string &name)
    {
        // SAME TWO STEPS AS registerOutfitModelConfigString, and for the same
        // reason: the configstring gives the client an INDEX to resolve, and the
        // `|` precache (CG_ServerCommand case 124 -> an XModel load by name) makes
        // sure the asset is resident. The difference is that the index is NOT
        // allocated here -- it is the one the dedicated already resolved, so the
        // agent element's model field and the client band agree by construction.
        if (name.empty() || name.size() >= 128 || name.front() == '*' ||
            index == 0 || index >= ModelConfigStringCount)
        {
            return false;
        }
        if (const auto known = publishedActorModels_.find(name);
            known != publishedActorModels_.end())
        {
            return known->second == index;
        }
        if (!clients_.SV_SetConfigString(
                static_cast<std::uint16_t>(ModelConfigStringBase + index), name))
        {
            return false;
        }
        publishedActorModels_.emplace(name, index);
        // NO `|` PRECACHE HERE, DELIBERATELY. registerOutfitModelConfigString pairs
        // the configstring with `| name` (CG_ServerCommand case 124, an XModel load
        // by name) because an outfit model may not be resident. This path does NOT:
        // sending both at once is what attempt 2 did and the client TIMED OUT a few
        // seconds in (12.22). They are two different actions and only ONE of them is
        // needed for the empty-name early-out -- sub_514880 reads the CONFIGSTRING,
        // and that is all sub_530C90 needs to fill record+568. If a model later turns
        // out not to be resident, add the precache back deliberately and measure it on
        // its own, not bundled with this.
        OlMod::RuntimeLog::write(
            OlMod::RuntimeLog::Channel::GameServer,
            "actor model PUBLISHED index=" + std::to_string(index) +
                " cs=" + std::to_string(ModelConfigStringBase + index) +
                " name=" + name);
        return true;
    }

    void ServerCore::spawnPodiumFigures()
    {
        // ONE SHOT PER MATCH. resolveModelConfigStringIndex behind this is a
        // DB_FindXAssetHeader plus a linear scan of up to 1024 configstrings,
        // and section 119q is the record of what calling it per frame does to
        // the frame rate.
        podiumFiguresSpawned_ = true;
        if (topPlayersPlaces_.empty())
        {
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer,
                "podium figures SKIPPED -- this map publishes no top_players_loc");
            return;
        }
        const auto ranked = clients_.topClientsByKills(topPlayersPlaces_.size());
        // CODREF(1649370 4EAAD0/523910): entity-link tags use the separate
        // 256-slot band at 12248, not the character attachment CCS band 5896.
        // Reuse an existing name or publish into an empty slot before the reveal.
        constexpr std::uint16_t linkTagBase = 12248;
        std::uint8_t weaponTag{};
        std::uint8_t emptyTag{};
        for (std::uint16_t tag = 1; tag < 256; ++tag)
        {
            const auto name = clients_.configString(linkTagBase + tag);
            if (name && *name == "tag_weapon_right")
            {
                weaponTag = static_cast<std::uint8_t>(tag);
                break;
            }
            if ((!name || name->empty()) && !emptyTag)
                emptyTag = static_cast<std::uint8_t>(tag);
        }
        if (!weaponTag && emptyTag)
        {
            weaponTag = emptyTag;
            static_cast<void>(clients_.SV_SetConfigString(linkTagBase + weaponTag, "tag_weapon_right"));
        }
        for (std::size_t place = 0;
             place < ranked.size() && place < topPlayersPlaces_.size();
             ++place)
        {
            const auto clientNum = ranked[place].first;
            // THE BASE MODEL, BY NAME AND NEVER BY RETAIL'S NUMBER. Try the
            // character models this server already resolved for that client and
            // take the first this map's band actually publishes. Report every
            // refusal: "no figure" and "a figure with the wrong model" look the
            // same on screen and must not look the same in the log.
            // A FIGURE NEEDS A BODY, NOT WHATEVER RESOLVES FIRST. The first
            // version took the first of the player's five component models that
            // this map's band publishes, and on mp_rust_long that is
            // `hea_socomb_sc_m` -- a HEAD. Section 67 names the slots
            // (0 cha, 1 fpa, 2 boo, 3 fja, 4 han, 5 hea, 6 ves, 7 heg) and the
            // demo's sixteen precaches carry an `fpa_` for every one of its
            // three players, so `fpa_` is the body and it is what a base model
            // has to be.
            //
            // Preference order, most specific first:
            //   1  this player's OWN fpa_ model, if the band publishes it
            //   2  the band's own fpa_ model -- a generic body, right shape,
            //      wrong outfit, and section 124 says the outfit is field 49's
            //      job anyway
            //   3  any of this player's models that resolves, so a wrong figure
            //      still beats no figure
            std::uint16_t modelIndex{};
            std::string chosen;
            std::string refused;
            // AND THE DEMO SAYS THE BASE MODEL IS EMPTY. All three of retail's
            // podium figures carry modelIndex 121, and 121 in this build's model
            // index space is `tag_origin` -- a model with no mesh at all. The
            // character is built ENTIRELY from field 49 and that client's own
            // clientInfo, which is why the sixteen `|` precaches ride alongside
            // and why nothing on the entity names an outfit.
            //
            // So the preference order below is a FALLBACK LADDER now, not the
            // policy. It stays because it is what runs when a map's band does
            // not publish tag_origin, and because "a wrong figure beats no
            // figure" was true then and is true now -- but a character part as
            // the base is measurably not what a real server sends. Section 125
            // reasoned `fpa_` was "the body"; the model table says slot 4 is
            // LEGS and slot 3 is the torso, and retail uses neither.
            //
            // BY NAME, NEVER BY RETAIL'S NUMBER. Model indices are per map and
            // per band; 121 is what this demo's map produced and is not a
            // constant to port.
            if (modelResolver_)
            {
                if (const auto empty = modelResolver_(PodiumBaseModelName))
                {
                    modelIndex = *empty;
                    chosen = std::string(PodiumBaseModelName) +
                        " (retail's own empty base)";
                }
                else
                {
                    refused += (refused.empty() ? "" : ",") +
                        std::string(PodiumBaseModelName);
                }
            }
            if (!modelIndex && characterModelNamesProvider_ && modelResolver_)
            {
                std::uint16_t anyIndex{};
                std::string anyName;
                for (const auto &name : characterModelNamesProvider_(clientNum))
                {
                    if (name.empty())
                        continue;
                    const auto resolved = modelResolver_(name);
                    if (!resolved)
                    {
                        refused += (refused.empty() ? "" : ",") + name;
                        continue;
                    }
                    if (name.rfind("fpa_", 0) == 0)
                    {
                        modelIndex = *resolved;
                        chosen = name;
                        break;
                    }
                    if (!anyIndex)
                    {
                        anyIndex = *resolved;
                        anyName = name;
                    }
                }
                if (!modelIndex && podiumFallbackModelIndex_)
                {
                    modelIndex = podiumFallbackModelIndex_;
                    chosen = podiumFallbackModelName_ + " (generic body)";
                }
                if (!modelIndex && anyIndex)
                {
                    modelIndex = anyIndex;
                    chosen = anyName + " (NOT A BODY)";
                }
            }
            if (!modelIndex)
            {
                OlMod::RuntimeLog::write(
                    OlMod::RuntimeLog::Channel::GameServer,
                    "podium figure SKIPPED place=" + std::to_string(place + 1) +
                        " client=" + std::to_string(clientNum) +
                        " -- no character model of this client's resolves in "
                        "the model configstring band; refused=[" + refused + "]");
                continue;
            }
            const auto spawned = world_.spawnPodiumFigure(
                topPlayersPlaces_[place],
                static_cast<std::uint8_t>(clientNum + 1),
                modelIndex);
            if (spawned && weaponTag)
            {
                const auto player = world_.playerEntity(clientNum);
                const auto weapon = player ? player->networkState.weaponAssetIndex : 0;
                if (weapon)
                {
                    const auto attached = world_.spawnPodiumWeapon(*spawned, weapon, weaponTag);
                    OlMod::RuntimeLog::write(OlMod::RuntimeLog::Channel::GameServer,
                        "podium held weapon parent=" + std::to_string(*spawned) +
                        " asset=" + std::to_string(weapon) + " tag=" + std::to_string(weaponTag) +
                        " entity=" + (attached ? std::to_string(*attached) : "FAILED"));
                }
            }
            // CODREF(retail DM +17000..+32600): every rank has an idle,
            // emote-in and emote-out, while the equipped victory emote comes
            // from the shared marketplace namespace. Resolve all names in the
            // current level's CCS namespace; the observed keys are not IDs a
            // producer may assume on another level.
            constexpr std::array<std::string_view, 3> idleNames{
                "post_game_1st_rifle_idle", "post_game_2nd_rifle_idle",
                "post_game_3rd_rifle_idle" };
            constexpr std::array<std::string_view, 3> emoteInNames{
                "post_game_1st_rifle_emote_in", "post_game_2nd_rifle_emote_in",
                "post_game_3rd_rifle_emote_in" };
            constexpr std::array<std::string_view, 3> emoteNames{
                "post_game_emote_threaten_cut_throat_t7",
                "post_game_emote_russian_dance", "post_game_emote_zalebaba" };
            constexpr std::array<std::string_view, 3> emoteOutNames{
                "post_game_1st_rifle_emote_out", "post_game_2nd_rifle_emote_out",
                "post_game_3rd_rifle_emote_out" };
            if (spawned && scriptAnimationResolver_ && place < idleNames.size())
            {
                const auto resolve = [this](const std::string_view name) {
                    const auto key = scriptAnimationResolver_(name);
                    return key && *key && *key <= 0xFFF ? *key : std::uint16_t{};
                };
                const PodiumAnimationSet animations{
                    .entityNum = *spawned,
                    .idle = resolve(idleNames[place]),
                    .emoteIn = resolve(emoteInNames[place]),
                    .emote = resolve(emoteNames[place]),
                    .emoteOut = resolve(emoteOutNames[place]),
                };
                podiumAnimations_[place] = animations;
                OlMod::RuntimeLog::write(OlMod::RuntimeLog::Channel::GameServer,
                    "podium animation entity=" + std::to_string(*spawned) +
                    " place=" + std::to_string(place + 1) +
                    " idle=" + std::to_string(animations.idle) +
                    " in=" + std::to_string(animations.emoteIn) +
                    " emote=" + std::to_string(animations.emote) +
                    " out=" + std::to_string(animations.emoteOut));
            }
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer,
                "podium figure place=" + std::to_string(place + 1) +
                    " client=" + std::to_string(clientNum) +
                    " field49=" + std::to_string(clientNum + 1) +
                    " model=" + std::to_string(modelIndex) + " (" + chosen + ")" +
                    " origin " +
                    std::to_string(topPlayersPlaces_[place].origin[0]) + "," +
                    std::to_string(topPlayersPlaces_[place].origin[1]) + "," +
                    std::to_string(topPlayersPlaces_[place].origin[2]) +
                    (spawned ? " entity=" + std::to_string(*spawned)
                             : std::string(" SPAWN FAILED")) +
                    (refused.empty() ? "" : " refused=[" + refused + "]"));
        }
    }

    void ServerCore::holdMatchCompletionState()
    {
        // Intermission has to be re-applied every frame, not written once: the
        // world rebuilds each client's playerState from pmove, so a single write
        // is overwritten on the very next frame and the player keeps running
        // around after the match has ended.
        if (!matchStatus_.completed)
            return;
        // Wetwork exits after one second and retail never enters the
        // competitive podium/intermission state on this path.
        if (matchGameType_ == "coop" || (matchGameType_=="zm" && world_.zombieTeamWiped()))
            return;
        // INTERMISSION STARTS AT +17000, NOT AT +0, AND A PLAYER CAUGHT THIS
        // AFTER IT HAD BEEN WRONG FOR DAYS: "when the game is technically over
        // it removes the players instead of keeping your viewhands and guns on
        // the screen while it waits for the podium scene, it drops your head
        // down to the floor and removes everything, you can still move but it's
        // janky and you're invisible."
        //
        // This function used to apply pm_type 5 and eFlags 16 the instant
        // matchStatus_.completed went true and hold them for the whole
        // 32.7-second schedule. The demo puts the player into intermission on
        // ONE frame -- serverTime 648700, the `s ui_match_complete "1"` frame,
        // +17000 -- and leaves them entirely alone before it. The outro at
        // +11100 is meant to play over a NORMAL player, which is the whole
        // reason `u 10` shows your own body in third person.
        //
        // Everything the player described follows from the early flag: pm_type
        // 5 stops the viewmodel being drawn, an intermission with no view
        // height puts the eye at the feet, and the SERVER's own pmove keeps
        // simulating the player as pmType 0 while the snapshot claims 5, so the
        // client predicts a frozen player against a moving one.
        constexpr std::uint32_t PodiumIntermissionMilliseconds = 17'000;
        // The camera entity is born with the +17000 intermission snapshot, but
        // retail does not put its entity/tag into playerState until +17400.
        // PlayerState is parsed before packet entities, so publishing both in
        // the same snapshot can make the client resolve a camera that is not in
        // its centity set yet and leave the view on the stationary fallback
        // origin. Four snapshots of lead time match the demo and let the client
        // bind before the 16.5-second tracking phase begins.
        constexpr std::uint32_t PodiumViewMilliseconds = 17'400;
        // THE FIGURES GO UP 400 MS BEFORE THE PLAYERS COME DOWN, AND THAT GAP IS
        // THE POINT. Retail's three podium figures begin at match-end + 16600 and
        // its intermission lands at +17000 -- section 120 wrote down "the figures
        // spawn 400 ms BEFORE the players are removed" and nothing ever acted on
        // it. This server spawned them on the SAME frame as the intermission.
        //
        // A retail figure carries `tag_origin` as its base model (140b): it has no
        // mesh of its own and the client builds the character from field 49 and
        // that client's live presentation. Doing that on the frame the players are
        // torn down leaves nothing to build from, which is exactly what a player
        // reports -- "they are not present at all in the podium camera".
        //
        // MEASURED, not reasoned: `demoq phases` reads outro-figures at +16600 on
        // retail's demo and +17000 on ours, against the same match-end anchor.
        constexpr std::uint32_t PodiumFiguresMilliseconds = 16'600;
        // MEASURED (dm demo): pm_flags becomes 2048 at 632800, one second after
        // the match is decided at 631800, and the origin is not asserted again
        // until the killcam at 642900. A player put the same thing in words --
        // "players will freeze in place" -- and it is a DIFFERENT mechanism from
        // the intermission that follows: pm_type does not change until +17000.
        constexpr std::uint32_t MatchEndFreezeMilliseconds = 1'000;
        const auto elapsed = matchCompletionAnnounced_
            ? world_.snapshot().serverTime - matchCompletionServerTime_
            : 0u;
        // BEFORE the intermission gate below, because it has to happen before the
        // intermission does.
        if (elapsed >= PodiumFiguresMilliseconds && !podiumFiguresSpawned_ &&
            !SV_PerfBaseline())
        {
            spawnPodiumFigures();
        }
        if (elapsed < PodiumIntermissionMilliseconds)
        {
            // The killcam at +11100 plays over a player who is standing still,
            // not over one who can still run around -- which is what this
            // server did until a player pointed it out.
            if (elapsed >= MatchEndFreezeMilliseconds)
            {
                const auto &frozen = clients_.clients();
                for (std::uint32_t clientNum{};
                     clientNum < frozen.size(); ++clientNum)
                {
                    if (frozen[clientNum].state == ClientState::Active)
                    {
                        static_cast<void>(
                            world_.setPlayerMatchEndFreeze(clientNum));
                    }
                }
                if (!matchEndFreezeLogged_)
                {
                    matchEndFreezeLogged_ = true;
                    OlMod::RuntimeLog::write(
                        OlMod::RuntimeLog::Channel::GameServer,
                        "match end freeze -> pm_flags |= 0x800 elapsed=" +
                            std::to_string(elapsed) + "ms");
                }
            }
            return;
        }
        const auto camera = topPlayersCamera_;
        if (camera && !podiumCameraLogged_)
        {
            podiumCameraLogged_ = true;
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer,
                "podium camera -> origin " +
                    std::to_string(camera->origin[0]) + "," +
                    std::to_string(camera->origin[1]) + "," +
                    std::to_string(camera->origin[2]) + " angles " +
                    std::to_string(camera->angles[0]) + "," +
                    std::to_string(camera->angles[1]) + "," +
                    std::to_string(camera->angles[2]) +
                    " elapsed=" + std::to_string(elapsed) + "ms");
        }
        // The figures are already up by now -- the gate above put them there 400 ms
        // ago. This stays as the backstop for a match whose completion is
        // announced later than +16600.
        if (!podiumFiguresSpawned_)
            spawnPodiumFigures();
        world_.revealPodiumFigures();
        // CODREF(retail DM packet animations): this is the complete captured
        // podium sequence before EXE_MATCHENDED at +32700. The 50 ms command
        // ages are intentional: those operations first appear in the next
        // 100 ms snapshot. Each world transition then supplies the measured
        // four-frame redundancy.
        enum class PodiumAnimationPhase : std::uint8_t
        {
            Idle,
            EmoteIn,
            Emote,
            EmoteOut,
        };
        struct PodiumAnimationEvent
        {
            std::uint32_t publishOffset{};
            std::uint32_t commandOffset{};
            std::uint8_t place{};
            PodiumAnimationPhase phase{};
            bool clearTree{};
        };
        constexpr std::array<PodiumAnimationEvent, 12> animationSchedule{
            PodiumAnimationEvent{ 17'000, 16'950, 0, PodiumAnimationPhase::Idle, false },
            PodiumAnimationEvent{ 17'000, 16'950, 1, PodiumAnimationPhase::Idle, false },
            PodiumAnimationEvent{ 17'000, 16'950, 2, PodiumAnimationPhase::Idle, false },
            PodiumAnimationEvent{ 20'000, 19'950, 0, PodiumAnimationPhase::EmoteIn, true },
            PodiumAnimationEvent{ 20'700, 20'650, 1, PodiumAnimationPhase::EmoteIn, true },
            PodiumAnimationEvent{ 21'400, 21'350, 2, PodiumAnimationPhase::EmoteIn, true },
            PodiumAnimationEvent{ 21'600, 21'600, 0, PodiumAnimationPhase::Emote, true },
            PodiumAnimationEvent{ 22'500, 22'500, 1, PodiumAnimationPhase::Emote, true },
            PodiumAnimationEvent{ 22'800, 22'800, 2, PodiumAnimationPhase::Emote, true },
            PodiumAnimationEvent{ 26'200, 26'150, 0, PodiumAnimationPhase::EmoteOut, true },
            PodiumAnimationEvent{ 27'700, 27'700, 0, PodiumAnimationPhase::Idle, true },
            PodiumAnimationEvent{ 32'600, 32'600, 2, PodiumAnimationPhase::EmoteOut, true },
        };
        while (podiumAnimationEvent_ < animationSchedule.size() &&
            elapsed >= animationSchedule[podiumAnimationEvent_].publishOffset)
        {
            const auto &event = animationSchedule[podiumAnimationEvent_++];
            const auto &slot = podiumAnimations_[event.place];
            if (!slot)
                continue;
            std::uint16_t key{};
            std::uint16_t fadeOutKey{};
            std::uint8_t flags = 3;
            std::string_view phaseName;
            switch (event.phase)
            {
            case PodiumAnimationPhase::Idle:
                key = slot->idle;
                flags = 1;
                phaseName = "idle";
                break;
            case PodiumAnimationPhase::EmoteIn:
                key = slot->emoteIn;
                phaseName = "emote-in";
                break;
            case PodiumAnimationPhase::Emote:
                key = slot->emote;
                phaseName = "emote";
                break;
            case PodiumAnimationPhase::EmoteOut:
                key = slot->emoteOut;
                fadeOutKey = slot->emote;
                phaseName = "emote-out";
                break;
            }
            if (!key || (event.phase == PodiumAnimationPhase::EmoteOut && !fadeOutKey))
            {
                OlMod::RuntimeLog::write(
                    OlMod::RuntimeLog::Channel::GameServer,
                    "podium animation SKIPPED place=" +
                        std::to_string(event.place + 1) + " phase=" +
                        std::string(phaseName) + " -- CCS name unresolved");
                continue;
            }
            const auto commandTime =
                matchCompletionServerTime_ + event.commandOffset;
            const auto applied = world_.setPodiumFigureAnimation(
                slot->entityNum, key, commandTime, flags,
                event.clearTree, fadeOutKey);
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer,
                "podium animation event place=" +
                    std::to_string(event.place + 1) + " phase=" +
                    std::string(phaseName) + " entity=" +
                    std::to_string(slot->entityNum) + " key=" +
                    std::to_string(key) + " commandTime=" +
                    std::to_string(commandTime) + " elapsed=" +
                    std::to_string(elapsed) +
                    (applied ? "ms" : "ms REFUSED"));
        }
        // THE CAMERA AS AN ENTITY (HANDOFF 129). Retail does not move the
        // player onto `top_players_camera`; it hands the player's VIEW to an
        // entity through playerState fields 168 and 169 (+0x068 and +0x06C),
        // both asserted EXACTLY ONCE in the whole retail dm demo, on the frame
        // the podium camera takes over, carrying entity 713 and tag 20.
        //
        // ADDITIVE ON PURPOSE. 121's origin-move is player-confirmed working
        // and is left in place below, so if the client declines this the view
        // is still held where it already was. One-shot: spawnEntity allocates,
        // and calling it per frame would leak the pool in seconds.
        if (camera && !podiumCameraEntity_ && !SV_PerfBaseline())
        {
            // Resolve the empty tag carrier by NAME in this map's model band.
            // The numeric index is map-specific (121 on both measured DM
            // maps). A character body is still a viable hidden DObj fallback
            // because it carries tag_origin too.
            auto cameraTagCarrier = podiumFallbackModelIndex_;
            if (modelResolver_)
            {
                if (const auto empty =
                        modelResolver_(PodiumBaseModelName);
                    empty && *empty)
                {
                    cameraTagCarrier = *empty;
                }
            }
            podiumCameraEntity_ = world_.spawnPodiumCamera(
                *camera, cameraTagCarrier,
                matchCompletionServerTime_ + 16'950);
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer,
                podiumCameraEntity_
                    ? "podium camera entity -> " +
                          std::to_string(*podiumCameraEntity_) + " model " +
                          std::to_string(cameraTagCarrier) + " tag " +
                          std::to_string(SvPodiumViewTag) +
                          " elapsed=" + std::to_string(elapsed) + "ms"
                    : "podium camera entity NOT SPAWNED -- the entity pool "
                      "refused, so the view falls back to 121's origin move");
        }
        // CODREF(retail DM camera entity 713): the +17000 snapshot starts both
        // trajectories at command time +16950 with type 7 / duration 500. The
        // +17500 snapshot advances the base to that endpoint and replaces both
        // with type 4 / duration 16500, command time +17450.
        if (podiumCameraEntity_ && !podiumCameraMotionContinued_ &&
            elapsed >= 17'500)
        {
            podiumCameraMotionContinued_ = world_.continuePodiumCameraMotion(
                *podiumCameraEntity_, matchCompletionServerTime_ + 17'450);
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer,
                "podium camera trajectory -> type 4 duration 16500 entity=" +
                    std::to_string(*podiumCameraEntity_) + " elapsed=" +
                    std::to_string(elapsed) +
                    (podiumCameraMotionContinued_ ? "ms" : "ms REFUSED"));
        }
        const auto &slots = clients_.clients();
        for (std::uint32_t clientNum{}; clientNum < slots.size(); ++clientNum)
        {
            if (slots[clientNum].state != ClientState::Active)
                continue;
            static_cast<void>(world_.setPlayerIntermission(clientNum, camera));
            if (podiumCameraEntity_ && elapsed >= PodiumViewMilliseconds)
            {
                static_cast<void>(world_.setPlayerPodiumView(
                    clientNum, *podiumCameraEntity_, SvPodiumViewTag));
            }
        }
    }

    void ServerCore::completeSdRound(
        const SvTeam winner,
        const SvSdRoundEndReason reason)
    {
        if (!sdRoundStatus_.configured || sdRoundStatus_.completed ||
            matchStatus_.completed ||
            (winner != SvTeam::Tf && winner != SvTeam::Sc) ||
            reason == SvSdRoundEndReason::None)
        {
            throw std::logic_error("invalid authoritative SD round completion");
        }

        sdRoundStatus_.completed = true;
        sdRoundStatus_.winner = winner;
        sdRoundStatus_.endReason = reason;
        sdRoundStatus_.completedServerTime = world_.snapshot().serverTime;
        ++sdRoundStatus_.roundsPlayed;
        world_.appendSdEvent(SvWorldEventType::SdRoundEnded, {
            .winner = winner,
            .reason = static_cast<std::uint32_t>(reason),
        });
        const auto score = clients_.teamScore(winner).value_or(0);
        if (!clients_.setTeamScore(winner, score + 1))
            throw std::logic_error("SD round winner has no authoritative team score");

        const auto loser = winner == SvTeam::Tf ? SvTeam::Sc : SvTeam::Tf;
        const auto &winnerSounds = winner == SvTeam::Tf
            ? sdSoundPresentation_.tf
            : sdSoundPresentation_.sc;
        const auto &loserSounds = loser == SvTeam::Tf
            ? sdSoundPresentation_.tf
            : sdSoundPresentation_.sc;
        queueSdSoundForTeam(winner, winnerSounds.roundWon);
        queueSdSoundForTeam(loser, loserSounds.roundLost);

        const auto winnerScore = clients_.teamScore(winner).value_or(0);
        if (winnerScore >= static_cast<std::int32_t>(matchStatus_.rules.winLimit))
        {
            matchStatus_.completed = true;
            matchStatus_.winner = winner;
            matchStatus_.endReason = SvMatchEndReason::WinLimit;
            queueSdSoundForTeam(winner, winnerSounds.matchWon);
            queueSdSoundForTeam(loser, loserSounds.matchLost);
            return;
        }
        if (sdRoundStatus_.roundsPlayed < matchStatus_.rules.roundLimit)
        {
            sdSideSwitchPending_ = matchStatus_.rules.roundSwitch &&
                sdRoundStatus_.roundsPlayed % matchStatus_.rules.roundSwitch == 0;
            return;
        }

        const auto tfScore = clients_.teamScore(SvTeam::Tf).value_or(0);
        const auto scScore = clients_.teamScore(SvTeam::Sc).value_or(0);
        matchStatus_.completed = true;
        matchStatus_.winner = tfScore == scScore
            ? SvTeam::None
            : tfScore > scScore ? SvTeam::Tf : SvTeam::Sc;
        matchStatus_.endReason = SvMatchEndReason::RoundLimit;
        if (matchStatus_.winner == SvTeam::None)
        {
            queueSdSoundForTeam(SvTeam::Tf, sdSoundPresentation_.tf.draw);
            queueSdSoundForTeam(SvTeam::Sc, sdSoundPresentation_.sc.draw);
        }
        else
        {
            const auto matchLoser = matchStatus_.winner == SvTeam::Tf
                ? SvTeam::Sc
                : SvTeam::Tf;
            queueSdSoundForTeam(
                matchStatus_.winner,
                matchStatus_.winner == SvTeam::Tf
                    ? sdSoundPresentation_.tf.matchWon
                    : sdSoundPresentation_.sc.matchWon);
            queueSdSoundForTeam(
                matchLoser,
                matchLoser == SvTeam::Tf
                    ? sdSoundPresentation_.tf.matchLost
                    : sdSoundPresentation_.sc.matchLost);
        }
    }

    bool ServerCore::advanceSdRound()
    {
        constexpr std::uint32_t RoundEndDelayMilliseconds = 5000;
        if (!sdRoundStatus_.configured || !sdRoundStatus_.completed ||
            matchStatus_.completed ||
            world_.snapshot().serverTime -
                    sdRoundStatus_.completedServerTime <
                RoundEndDelayMilliseconds)
        {
            return false;
        }
        if (!sdBombPickupTrigger_ || sdBombSiteRuntime_.size() != 2)
            return false;

        auto candidateClients = std::make_unique<SvClientSystem>(clients_);
        if (!candidateClients->beginNextRound(sdSideSwitchPending_))
            return false;

        SvUseObjectSystem candidateUseObjects;
        const std::array useDefinitions{
            SvUseObjectDefinition{ sdBombSiteRuntime_[0].plantTrigger.objectId,
                SvTeam::Sc, SvUseTeamRelation::Enemy,
                sdBombRules_.plantMilliseconds, true },
            SvUseObjectDefinition{ sdBombSiteRuntime_[1].plantTrigger.objectId,
                SvTeam::Sc, SvUseTeamRelation::Enemy,
                sdBombRules_.plantMilliseconds, true },
            SvUseObjectDefinition{ sdBombSiteRuntime_[0].defuseTrigger.objectId,
                SvTeam::Sc, SvUseTeamRelation::Friendly,
                sdBombRules_.defuseMilliseconds },
            SvUseObjectDefinition{ sdBombSiteRuntime_[1].defuseTrigger.objectId,
                SvTeam::Sc, SvUseTeamRelation::Friendly,
                sdBombRules_.defuseMilliseconds },
        };
        if (!candidateUseObjects.configure(useDefinitions) ||
            !setSdBombVisual(sdBombVisualHomeOrigin_, false))
            return false;

        auto candidateRoundStatus = sdRoundStatus_;
        candidateRoundStatus.completed = false;
        candidateRoundStatus.armed = false;
        candidateRoundStatus.winner = SvTeam::None;
        candidateRoundStatus.endReason = SvSdRoundEndReason::None;
        candidateRoundStatus.startedServerTime = 0;
        candidateRoundStatus.completedServerTime = 0;

        auto candidateBombStatus = sdBombStatus_;
        candidateBombStatus.phase = SvSdBombPhase::Inactive;
        candidateBombStatus.plantedSiteLabel.reset();
        candidateBombStatus.carrierClientNum.reset();
        candidateBombStatus.planterClientNum.reset();
        candidateBombStatus.defuserClientNum.reset();
        candidateBombStatus.plantedOrigin.reset();
        candidateBombStatus.phaseStartServerTime = 0;
        candidateBombStatus.plantedServerTime = 0;

        clients_ = std::move(*candidateClients);
        useObjects_ = std::move(candidateUseObjects);
        sdRoundStatus_ = candidateRoundStatus;
        sdBombStatus_ = candidateBombStatus;
        sdBombPickupTrigger_->origin = sdBombPickupHomeOrigin_;
        if (sdSideSwitchPending_)
        {
            queueSdSoundForTeam(
                SvTeam::Tf, sdSoundPresentation_.tf.sideSwitch);
            queueSdSoundForTeam(
                SvTeam::Sc, sdSoundPresentation_.sc.sideSwitch);
        }
        sdRoundStartAnnounced_ = false;
        sdTfLastAliveAnnounced_ = false;
        sdScLastAliveAnnounced_ = false;
        sdPreviousTfAlive_ = 0;
        sdPreviousScAlive_ = 0;
        sdSideSwitchPending_ = false;
        return true;
    }

    void ServerCore::queueSdSoundForClient(
        const std::uint32_t clientNum,
        const std::uint16_t eventParameter)
    {
        if (eventParameter)
            sdSoundQueues_[clientNum].push_back(eventParameter);
    }

    void ServerCore::queueSdSoundForTeam(
        const SvTeam team,
        const std::uint16_t eventParameter)
    {
        if (!eventParameter)
            return;
        const auto &slots = clients_.clients();
        for (std::uint32_t clientNum{}; clientNum < slots.size(); ++clientNum)
        {
            if (slots[clientNum].state == ClientState::Active &&
                slots[clientNum].team == team)
            {
                queueSdSoundForClient(clientNum, eventParameter);
            }
        }
    }

    void ServerCore::sendSdSoundToTeam(
        const SvTeam team,
        const std::uint16_t eventParameter)
    {
        if (!eventParameter)
            return;
        const auto &slots = clients_.clients();
        for (std::uint32_t clientNum{}; clientNum < slots.size(); ++clientNum)
        {
            if (slots[clientNum].state == ClientState::Active &&
                slots[clientNum].team == team)
            {
                static_cast<void>(
                    clients_.queueLocalSound(clientNum, eventParameter));
            }
        }
    }

    void ServerCore::announceSdRoundStart(
        const std::span<const SvWorldClientInput> activeClients)
    {
        if (sdRoundStartAnnounced_)
            return;
        for (const auto &client : activeClients)
        {
            if (client.gameplayState != ClientGameplayState::Playing)
                continue;
            const auto *sounds = client.team == SvTeam::Tf
                ? &sdSoundPresentation_.tf
                : client.team == SvTeam::Sc ? &sdSoundPresentation_.sc : nullptr;
            if (!sounds)
                continue;
            queueSdSoundForClient(client.clientNum, sounds->searchDestroy);
            queueSdSoundForClient(
                client.clientNum,
                client.team == SvTeam::Tf
                    ? sounds->objectiveDestroy
                    : sounds->objectiveDefend);
        }
        sdRoundStartAnnounced_ = true;
    }

    void ServerCore::announceSdLastAlive(
        const std::span<const SvWorldClientInput> activeClients,
        const SvSdEliminationState &state)
    {
        const auto announce = [&](const SvTeam team,
                                  const std::uint32_t alive,
                                  std::uint32_t &previousAlive,
                                  bool &announced,
                                  const std::uint16_t sound) {
            const auto transitionedToLastAlive = previousAlive > 1 && alive == 1;
            previousAlive = alive;
            if (announced || !transitionedToLastAlive || !sound)
                return;
            const auto survivor = std::ranges::find_if(
                activeClients, [&](const SvWorldClientInput &client) {
                    if (client.team != team ||
                        client.gameplayState != ClientGameplayState::Playing)
                    {
                        return false;
                    }
                    const auto state = world_.playerState(client.clientNum);
                    return state && state->spawnGeneration && state->health > 0;
                });
            if (survivor != activeClients.end())
            {
                queueSdSoundForClient(survivor->clientNum, sound);
                announced = true;
            }
        };
        announce(SvTeam::Tf, state.attackersAlive, sdPreviousTfAlive_,
            sdTfLastAliveAnnounced_,
            sdSoundPresentation_.tf.lastAlive);
        announce(SvTeam::Sc, state.defendersAlive, sdPreviousScAlive_,
            sdScLastAliveAnnounced_,
            sdSoundPresentation_.sc.lastAlive);
    }

    void ServerCore::pumpSdSoundQueues(
        const std::span<const SvWorldClientInput> activeClients)
    {
        constexpr std::uint32_t LeaderDialogSpacingMilliseconds = 3000;
        const auto serverTime = world_.snapshot().serverTime;
        for (const auto &client : activeClients)
        {
            auto queue = sdSoundQueues_.find(client.clientNum);
            if (queue == sdSoundQueues_.end() || queue->second.empty() ||
                sdSoundReadyTime_[client.clientNum] > serverTime)
            {
                continue;
            }
            if (clients_.queueLocalSound(client.clientNum, queue->second.front()))
            {
                queue->second.pop_front();
                sdSoundReadyTime_[client.clientNum] =
                    serverTime + LeaderDialogSpacingMilliseconds;
            }
        }
    }

    bool ServerCore::setSdBombVisual(
        const std::array<float, 3> &origin,
        const bool active)
    {
        return sdBombVisualHandle_ &&
            world_.setScriptModelTransformAndActive(
                *sdBombVisualHandle_, origin, sdBombVisualAngles_, active);
    }

    void ServerCore::evaluateSdRound(
        const std::span<const SvWorldClientInput> activeClients)
    {
        if (!sdRoundStatus_.configured || sdRoundStatus_.completed ||
            matchStatus_.completed)
        {
            return;
        }

        SvSdEliminationState state;
        for (const auto &client : activeClients)
        {
            if (client.gameplayState != ClientGameplayState::Playing)
                continue;
            const auto playerState = world_.playerState(client.clientNum);
            if (!playerState || !playerState->spawnGeneration)
                continue;
            auto *const total = client.team == SvTeam::Tf
                ? &state.attackers
                : client.team == SvTeam::Sc ? &state.defenders : nullptr;
            auto *const alive = client.team == SvTeam::Tf
                ? &state.attackersAlive
                : client.team == SvTeam::Sc ? &state.defendersAlive : nullptr;
            if (!total || !alive)
                continue;
            ++*total;
            if (playerState->health > 0)
                ++*alive;
        }

        const auto wasArmed = sdRoundStatus_.armed;
        sdRoundStatus_.armed = state.attackers && state.defenders;
        if (!wasArmed && sdRoundStatus_.armed)
        {
            const auto message =
                "sd round armed attackers=" + std::to_string(state.attackers) +
                " defenders=" + std::to_string(state.defenders) +
                " serverTime=" +
                std::to_string(world_.snapshot().serverTime);
            std::clog << "[dedicated/game-server] " << message << '\n';
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer, message);
        }
        if (!sdRoundStatus_.armed)
            return;

        if (sdBombStatus_.phase == SvSdBombPhase::Inactive)
        {
            auto candidate = sdBombStatus_;
            if (!SV_BeginSdBombRound(candidate, world_.snapshot().serverTime) ||
                !setSdBombVisual(sdBombVisualHomeOrigin_, true))
            {
                throw std::logic_error("armed SD round could not expose its bomb");
            }
            sdBombStatus_ = std::move(candidate);
            sdRoundStatus_.startedServerTime = world_.snapshot().serverTime;
            announceSdRoundStart(activeClients);
        }
        if (sdBombStatus_.phase == SvSdBombPhase::Carried &&
            sdBombStatus_.carrierClientNum)
        {
            const auto carrier = std::ranges::find(
                activeClients, *sdBombStatus_.carrierClientNum,
                &SvWorldClientInput::clientNum);
            const auto playerState = carrier != activeClients.end()
                ? world_.playerState(carrier->clientNum)
                : std::nullopt;
            if (carrier == activeClients.end() ||
                carrier->gameplayState != ClientGameplayState::Playing ||
                !playerState || playerState->health <= 0)
            {
                if (playerState && sdBombPickupTrigger_)
                    sdBombPickupTrigger_->origin = playerState->origin;
                const auto clientNum = *sdBombStatus_.carrierClientNum;
                static_cast<void>(useObjects_.cancelClient(
                    clientNum, world_.snapshot().serverTime));
                auto candidate = sdBombStatus_;
                if (!SV_DropSdBomb(
                        candidate, clientNum, world_.snapshot().serverTime) ||
                    !setSdBombVisual(sdBombPickupTrigger_->origin, true))
                {
                    throw std::logic_error(
                        "dead SD carrier bomb drop could not publish");
                }
                sdBombStatus_ = std::move(candidate);
                world_.appendSdEvent(SvWorldEventType::SdBombDropped, {
                    .actorClientNum = clientNum,
                    .origin = sdBombPickupTrigger_->origin,
                });
                sendSdSoundToTeam(
                    SvTeam::Tf, sdSoundPresentation_.objectiveLost);
                queueSdSoundForTeam(
                    SvTeam::Tf, sdSoundPresentation_.tf.bombLost);
            }
        }
        auto expiryCandidate = sdBombStatus_;
        if (SV_AdvanceSdBombTimer(
                expiryCandidate, sdBombRules_, world_.snapshot().serverTime))
        {
            if (!setSdBombVisual(*expiryCandidate.plantedOrigin, false))
                throw std::logic_error("exploded SD bomb visual could not hide");
            sdBombStatus_ = std::move(expiryCandidate);
            world_.appendSdEvent(SvWorldEventType::SdBombExploded, {
                .siteLabel = sdBombStatus_.plantedSiteLabel,
                .origin = sdBombStatus_.plantedOrigin,
            });
        }
        state.bombPlanted =
            sdBombStatus_.phase == SvSdBombPhase::Planted;
        announceSdLastAlive(activeClients, state);
        const auto outcome = SV_EvaluateSdRoundOutcome(
            sdBombStatus_.phase,
            state,
            sdRoundStatus_.startedServerTime,
            world_.snapshot().serverTime,
            matchStatus_.rules.timeLimitMinutes);
        if (!outcome)
            return;
        completeSdRound(outcome->first, outcome->second);
    }

    void ServerCore::processLootCommittedCommand(
        const SvWorldClientInput &client,
        const UserCmd &command)
    {
        // A hint from the preceding frame must not grant loot after downing.
        if (world_.zombieDownedState(client.clientNum) || world_.zombieTeamWiped())
        {
            lootHintTarget_.erase(client.clientNum);
            lootActivateHeld_[client.clientNum] = (command.buttons & UserCmdButtonActivate) != 0;
            return;
        }
        const auto held = (command.buttons & UserCmdButtonActivate) != 0;
        const auto previouslyHeld = lootActivateHeld_[client.clientNum];
        lootActivateHeld_[client.clientNum] = held;
        const auto target = lootHintTarget_.find(client.clientNum);
        if (target == lootHintTarget_.end())
            return;
        // WHAT THE BUTTONS ACTUALLY ARE, once per change, and only while a crate is
        // being offered. UserCmdButtonActivate is 0x8 and that value arrived with the
        // SD plant/defuse path, which nothing in this project has independently
        // confirmed on this build. If use turns out to be a different bit this line
        // names it in one press instead of costing another build.
        {
            static std::map<std::uint32_t, std::uint32_t> lastButtons;
            auto &last = lastButtons[client.clientNum];
            if (last != command.buttons)
            {
                last = command.buttons;
                // HEX, PROPERLY. The whole value of this line is being able to read
                // which BIT moved, and a decimal number behind an "0x" would say the
                // opposite of what it looks like.
                char hex[16]{};
                std::snprintf(hex, sizeof(hex), "0x%08X", command.buttons);
                OlMod::RuntimeLog::write(
                    OlMod::RuntimeLog::Channel::GameServer,
                    "loot BUTTONS client=" + std::to_string(client.clientNum) +
                        " buttons=" + hex +
                        " activate=" + std::to_string(held));
            }
        }
        // A RISING EDGE. Everything above runs on every command; only this does not.
        if (!held || previouslyHeld)
            return;
        const auto item = target->second;
        if (!world_.entity(item.handle))
        {
            lootHintTarget_.erase(target);
            return;
        }
        // THE GRANT GOES FIRST AND THE CRATE ONLY DIES IF IT SUCCEEDS. A crate freed
        // ahead of a refused grant is loot deleted for nothing, and the player has no
        // way to ask again.
        if (!world_.givePlayerWeapon(client.clientNum, item.weaponAssetIndex))
        {
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer,
                "loot PICKUP REFUSED client=" + std::to_string(client.clientNum) +
                    " entity=" + std::to_string(item.handle.entityNum) +
                    " weapon=" + std::to_string(item.weaponAssetIndex));
            return;
        }
        static_cast<void>(world_.removeLootItem(item.handle));
        static_cast<void>(world_.freeEntity(item.handle));
        lootHintTarget_.erase(client.clientNum);
        // FORGET WHAT WE TOLD THEM, or the next frame decides the answer has not
        // changed -- the crate is gone, so nothing is offered, so `current` becomes
        // 0xFFFF, which is a change; but the client is still drawing the prompt for an
        // entity that no longer exists until that lands. Clearing here closes the gap.
        cursorHintTrigger_.erase(client.clientNum);
        static_cast<void>(world_.clearPlayerCursorHint(client.clientNum));
        OlMod::RuntimeLog::write(
            OlMod::RuntimeLog::Channel::GameServer,
            "loot PICKED UP client=" + std::to_string(client.clientNum) +
                " entity=" + std::to_string(item.handle.entityNum) +
                " weapon=" + std::to_string(item.weaponAssetIndex));
    }

    void ServerCore::processZmUseCommittedCommand(
        const SvWorldClientInput &client,
        const UserCmd &command)
    {
        if (matchGameType_ != "zm")
            return;
        const auto held = (command.buttons & UserCmdButtonActivate) != 0;
        const auto reviveTarget = world_.zombieReviveTarget(client.clientNum);
        if (world_.processZombieReviveUse(client.clientNum, held))
            static_cast<void>(clients_.addClientRevives(client.clientNum));
        if (reviveTarget || world_.zombieDownedState(client.clientNum) || world_.zombieTeamWiped())
        {
            zmUseActivateHeld_[client.clientNum] = held;
            factoryAmmoHolds_.erase(client.clientNum);
            return;
        }
        const auto previouslyHeld = zmUseActivateHeld_[client.clientNum];
        zmUseActivateHeld_[client.clientNum] = held;
        const auto player = world_.playerState(client.clientNum);
        const auto ammoTarget = mapTriggerHintTarget_.find(client.clientNum);
        const auto *ammoTrigger = ammoTarget == mapTriggerHintTarget_.end() ? nullptr : ammoTarget->second;
        const auto now = world_.snapshot().serverTime;
        auto &hold = factoryAmmoHolds_[client.clientNum];
        const bool ammoEligible = world_.factoryPerkMachinesEnabled() && player && player->health &&
            client.gameplayState == ClientGameplayState::Playing &&
            !barrierRepairHintTarget_.contains(client.clientNum) && ammoTrigger &&
            ammoTrigger->noteworthy == "ammobox_trigger" && factoryAmmoMaterials_[0] && factoryAmmoMaterials_[1] &&
            mapTriggers_ && SV_MapTriggerTouches(*mapTriggers_, *ammoTrigger, player->origin,
                StandingPlayerTraceBounds.midpoint, StandingPlayerTraceBounds.halfSize);
        // OLMOD(factory_ammo): require uninterrupted committed input in the same
        // authored hull/life. Completion rechecks funds and stock atomically.
        const bool canStart = ammoEligible && (hold.active || hold.completed ||
            world_.canRefillFactoryAmmo(client.clientNum, zmRawBatteryCost(1)));
        if (hold.update(held, canStart, ammoEligible ? ammoTrigger->triggerIndex : 0,
                        player ? player->spawnGeneration : 0, now)) {
            const auto refilled = world_.refillFactoryAmmo(client.clientNum, zmRawBatteryCost(1));
            OlMod::RuntimeLog::write(OlMod::RuntimeLog::Channel::GameServer,
                "ZM AMMO completed client="+std::to_string(client.clientNum)+" trigger="+
                std::to_string(hold.trigger)+" refilled="+std::to_string(refilled)+" cost="+
                std::to_string(refilled?zmRawBatteryCost(1):0));
            cursorHintTrigger_.erase(client.clientNum);
        }
        if (!held || ammoEligible)
            return;

        // Barrier repair is deliberately level-triggered with a cadence. Retail lets
        // a player hold use and rebuild successive boards; a rising-edge-only handler
        // would repair exactly one board per key press. The motion itself is 250 ms,
        // and the measured interaction has breathing room between boards.
        if (const auto barrier = barrierRepairHintTarget_.find(client.clientNum);
            barrier != barrierRepairHintTarget_.end())
        {
            const auto now = world_.snapshot().serverTime;
            if (now < zmRepairReadyTime_[client.clientNum])
                return;
            if (world_.repairZmBarrier(barrier->second))
            {
                constexpr std::uint32_t RepairCadenceMilliseconds = 750;
                zmRepairReadyTime_[client.clientNum] =
                    now + RepairCadenceMilliseconds;
                cursorHintTrigger_.erase(client.clientNum);
            }
            return;
        }

        // A door purchase is an edge: one press, one atomic target group, one spend.
        if (previouslyHeld)
            return;
        const auto target = mapTriggerHintTarget_.find(client.clientNum);
        if (target == mapTriggerHintTarget_.end() || !target->second)
            return;
        const auto trigger = *target->second;
        if(factoryTeleportersEnabled_ && trigger.targetname.starts_with("trigger_teleport_")) {
            if(!player || !player->health || player->pmType!=0 || !mapTriggers_)return;
            if(!SV_MapTriggerTouches(*mapTriggers_,trigger,player->origin,
                StandingPlayerTraceBounds.midpoint,StandingPlayerTraceBounds.halfSize))return;
            static_cast<void>(processFactoryTeleportUse(client,trigger));
            cursorHintTrigger_.erase(client.clientNum);return;
        }
        if(factoryInteractablesEnabled_ && trigger.targetname=="treasure_chest_use") {
            if(!player || !player->health || client.gameplayState!=ClientGameplayState::Playing || !mapTriggers_)return;
            auto reach=StandingPlayerTraceBounds.halfSize;
            reach[0]+=12;reach[1]+=12;
            if(!SV_MapTriggerTouches(*mapTriggers_,trigger,player->origin,StandingPlayerTraceBounds.midpoint,reach))return;
            static_cast<void>(processFactoryBoxUse(client,trigger));
            cursorHintTrigger_.erase(client.clientNum);
            return;
        }
        if (trigger.targetname == "use_elec_switch")
        {
            if (zmPowerOn_)
                return;
            // OLMOD(factory_power): only publish logical power after the native
            // mover transaction succeeds. The legacy disabled route is retained.
            const bool recordedPower=world_.factoryPowerMotionEnabled();
            if(recordedPower) {
                const auto lever=modelResolver_?modelResolver_("zombie_power_lever_handle_arm03").value_or(0):0;
                const auto body=modelResolver_?modelResolver_("codo_asylum_electric_switch").value_or(0):0;
                // CODREF(actor_grounded_adapter): IDA532910 case130 reads
                // configstring11990+eventParm; group500 owns four authored jets.
                // Keep the recorded slot, but never overwrite another owner.
                const auto previous=clients_.configString(FactorySteamConfigString);
                if(!lever || !body || (previous && !previous->empty() && *previous!="500")) {
                    OlMod::RuntimeLog::write(OlMod::RuntimeLog::Channel::GameServer,
                        "ZMPOWER presentation unavailable: model or group-slot conflict");
                    return;
                }
                // CODREF(actor_grounded_adapter): native 514540 rejects reliable
                // 'd' updates for static NCS category0 with CANTJOINSESSION, even
                // when the string is unchanged. Both names were resolved from
                // the already-loaded model band: only change entity model IDs.
                // Reliable registration is queued before the event-bearing snapshot.
                static_cast<void>(clients_.SV_SetConfigString(FactorySteamConfigString,"500"));
                const auto group=clients_.configString(FactorySteamConfigString);
                if(!group || *group!="500" || !world_.activateFactoryPower(lever,body)) {
                    OlMod::RuntimeLog::write(OlMod::RuntimeLog::Channel::GameServer,
                        "ZMPOWER activation refused; state unchanged");
                    return;
                }
            }
            zmPowerOn_ = true;
            std::size_t electricDoorsOpened{};
            std::set<std::string_view> zonesUnlocked;
            if (mapTriggers_)
            {
                std::set<std::string_view> electricDoorTargets;
                for (const auto &candidate : mapTriggers_->triggers)
                {
                    if (candidate.targetname == "use_elec_switch")
                        openedMapTriggers_.insert(candidate.triggerIndex);
                    if (candidate.noteworthy == "factory_electric_door" &&
                        !candidate.target.empty())
                    {
                        openedMapTriggers_.insert(candidate.triggerIndex);
                        electricDoorTargets.insert(candidate.target);
                        if (const auto zone =
                                SV_ZmZoneUnlockedByTrigger(candidate);
                            !zone.empty())
                            zonesUnlocked.insert(zone);
                    }
                }
                for (const auto targetName : electricDoorTargets)
                    // The power owner moves these doors; a second owner would
                    // hide them immediately and discard the recorded trajectory.
                    if (recordedPower || world_.openMapTargetGroup(targetName))
                        ++electricDoorsOpened;
            }
            // Factory's electric-door triggers deliberately have no script_flag.
            // The authored player volumes immediately beyond both doors are the
            // outside_south_zone union (map ?3/?10/?12 and the remaining volumes).
            // Retail opens the two target groups together on the power frame, so
            // that same transaction makes their adjacent spawner zone eligible.
            std::size_t zonesActivated{};
            for (const auto zone : zonesUnlocked)
                if (activateZmZone(zone))
                    ++zonesActivated;
            mapTriggerHintTarget_.erase(client.clientNum);
            cursorHintTrigger_.erase(client.clientNum);
            static_cast<void>(world_.clearPlayerCursorHint(client.clientNum));
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer,
                "ZM POWER ON client=" + std::to_string(client.clientNum) +
                    " trigger=" + std::to_string(trigger.triggerIndex) +
                    " electricDoorsOpened=" +
                    std::to_string(electricDoorsOpened) +
                    " zonesActivated=" + std::to_string(zonesActivated));
            return;
        }

        if (const auto perk = zmPerkMachine(trigger))
        {
            if (!zmPowerOn_)
                return;
            const auto player=world_.playerState(client.clientNum);
            if(!player)return;
            const auto price=world_.factoryPerkMachinesEnabled()
                ? SV_FactoryPerkPriceUnits(player->perks[0]) : perk->batteryUnits;
            const auto rawCost = zmRawBatteryCost(price);
            if (!world_.purchaseZombiePerk(
                    client.clientNum, rawCost, perk->word, perk->mask))
            {
                OlMod::RuntimeLog::write(
                    OlMod::RuntimeLog::Channel::GameServer,
                    "ZM PERK REFUSED client=" +
                        std::to_string(client.clientNum) + " trigger=" +
                        std::to_string(trigger.triggerIndex) + " perk=" +
                        std::string{perk->noteworthy} + " rawCost=" +
                        std::to_string(rawCost));
                return;
            }
            mapTriggerHintTarget_.erase(client.clientNum);
            cursorHintTrigger_.erase(client.clientNum);
            static_cast<void>(world_.clearPlayerCursorHint(client.clientNum));
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer,
                "ZM PERK PURCHASED client=" +
                    std::to_string(client.clientNum) + " trigger=" +
                    std::to_string(trigger.triggerIndex) + " perk=" +
                    std::string{perk->noteworthy} + " word=" +
                    std::to_string(perk->word) + " mask=" +
                    std::to_string(perk->mask) + " batteryUnits=" +
                    std::to_string(price) + " rawCost=" +
                    std::to_string(rawCost));
            return;
        }

        // Retail's HUD divides the raw battery numerator by 1.2*1000. Door KVP
        // costs are display units, so a 1000 door consumes 1200 raw battery.
        constexpr std::uint32_t BatteryMultiplierNumerator = 6;
        constexpr std::uint32_t BatteryMultiplierDenominator = 5;
        const auto rawCost64 =
            static_cast<std::uint64_t>(trigger.cost) * BatteryMultiplierNumerator /
            BatteryMultiplierDenominator;
        if (rawCost64 > std::numeric_limits<std::uint32_t>::max())
            return;
        const auto rawCost = static_cast<std::uint32_t>(rawCost64);
        if (!world_.purchaseMapTargetGroup(
                client.clientNum, rawCost, trigger.target))
        {
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer,
                "ZM USE REFUSED client=" + std::to_string(client.clientNum) +
                    " trigger=" + std::to_string(trigger.triggerIndex) +
                    " target=" + std::string{trigger.target} +
                    " cost=" + std::to_string(trigger.cost) +
                    " rawCost=" + std::to_string(rawCost));
            return;
        }

        const auto zoneActivated =
            activateZmZone(SV_ZmZoneUnlockedByTrigger(trigger));

        if (mapTriggers_)
            for (const auto &candidate : mapTriggers_->triggers)
                if (candidate.target == trigger.target)
                    openedMapTriggers_.insert(candidate.triggerIndex);
        mapTriggerHintTarget_.erase(client.clientNum);
        cursorHintTrigger_.erase(client.clientNum);
        static_cast<void>(world_.clearPlayerCursorHint(client.clientNum));
        OlMod::RuntimeLog::write(
            OlMod::RuntimeLog::Channel::GameServer,
            "ZM USE PURCHASED client=" + std::to_string(client.clientNum) +
                " trigger=" + std::to_string(trigger.triggerIndex) +
                " target=" + std::string{trigger.target} +
                " cost=" + std::to_string(trigger.cost) +
                " rawCost=" + std::to_string(rawCost) +
                " scriptFlag=" + std::string{trigger.scriptFlag} +
                " zoneActivated=" + (zoneActivated ? "1" : "0"));
    }

    void ServerCore::processSdCommittedCommand(
        const SvWorldClientInput &client,
        const UserCmd &command)
    {
        if (!sdRoundStatus_.configured || !sdRoundStatus_.armed ||
            sdRoundStatus_.completed || !sdBombStatus_.configured ||
            !sdBombPickupTrigger_ || !triggerContactRunner_)
        {
            return;
        }
        const auto playerState = world_.playerState(client.clientNum);
        const auto playerEntity = world_.playerEntity(client.clientNum);
        if (!playerState || !playerEntity)
            return;
        const auto playing = client.gameplayState == ClientGameplayState::Playing;
        const auto alive = playerState->health > 0;
        const auto serverTime = world_.snapshot().serverTime;
        const auto contacts = [&](const SvTriggerVolume &trigger) {
            return triggerContactRunner_(
                playerState->origin, playerEntity->collisionBounds, trigger)
                .value_or(false);
        };

        if (sdBombStatus_.phase == SvSdBombPhase::Carried &&
            sdBombStatus_.carrierClientNum == client.clientNum)
        {
            sdBombPickupTrigger_->origin = playerState->origin;
        }

        if ((sdBombStatus_.phase == SvSdBombPhase::Available ||
                sdBombStatus_.phase == SvSdBombPhase::Dropped) &&
            playing && alive && client.team == SvTeam::Tf &&
            contacts(*sdBombPickupTrigger_))
        {
            auto candidate = sdBombStatus_;
            if (!SV_PickUpSdBomb(
                    candidate, client.clientNum, serverTime) ||
                !setSdBombVisual(sdBombPickupTrigger_->origin, false))
            {
                throw std::logic_error("picked-up SD bomb visual could not hide");
            }
            sdBombStatus_ = std::move(candidate);
            world_.appendSdEvent(SvWorldEventType::SdBombPickedUp, {
                .actorClientNum = client.clientNum,
                .origin = playerState->origin,
            });
            sendSdSoundToTeam(
                SvTeam::Tf, sdSoundPresentation_.objectiveTaken);
            queueSdSoundForTeam(
                SvTeam::Tf, sdSoundPresentation_.tf.bombTaken);
        }

        std::vector<SvUseObjectCandidate> candidates;
        if (sdBombStatus_.phase == SvSdBombPhase::Carried &&
            sdBombStatus_.carrierClientNum == client.clientNum)
        {
            for (const auto &site : sdBombSiteRuntime_)
            {
                candidates.push_back({
                    .objectId = site.plantTrigger.objectId,
                    .insideTrigger = contacts(site.plantTrigger),
                    .hasKeyObject = true,
                });
            }
        }
        else if (sdBombStatus_.phase == SvSdBombPhase::Planted &&
            sdBombStatus_.plantedSiteLabel)
        {
            const auto site = std::ranges::find(
                sdBombSiteRuntime_, *sdBombStatus_.plantedSiteLabel,
                &SvSdBombSiteRuntime::label);
            if (site != sdBombSiteRuntime_.end())
            {
                candidates.push_back({
                    .objectId = site->defuseTrigger.objectId,
                    .insideTrigger = contacts(site->defuseTrigger),
                });
            }
        }

        for (const auto &event : useObjects_.processCommittedCommand({
                 .clientNum = client.clientNum,
                 .team = client.team,
                 .commandTime = command.commandTime,
                 .buttons = command.buttons,
                 .playing = playing,
                 .alive = alive,
                 .candidates = candidates,
             }))
        {
            const auto plantSite = std::ranges::find_if(
                sdBombSiteRuntime_, [&](const SvSdBombSiteRuntime &site) {
                    return site.plantTrigger.objectId == event.objectId;
            });
            if (plantSite != sdBombSiteRuntime_.end())
            {
                if (event.type == SvUseObjectEventType::Begin ||
                    event.type == SvUseObjectEventType::Cancel)
                {
                    world_.appendSdEvent(
                        event.type == SvUseObjectEventType::Begin
                            ? SvWorldEventType::SdPlantStarted
                            : SvWorldEventType::SdPlantCancelled,
                        {
                            .actorClientNum = event.clientNum,
                            .objectId = event.objectId,
                            .siteLabel = plantSite->label,
                            .elapsedMilliseconds = event.elapsedMilliseconds,
                        });
                    continue;
                }
                auto candidate = sdBombStatus_;
                if (!SV_CommitSdBombPlant(
                        candidate, event.clientNum, plantSite->label,
                        playerState->origin, serverTime) ||
                    !setSdBombVisual(playerState->origin, true))
                {
                    throw std::logic_error(
                        "completed SD plant could not publish");
                }
                sdBombStatus_ = std::move(candidate);
                plantSite->defuseTrigger.origin = playerState->origin;
                world_.appendSdEvent(SvWorldEventType::SdBombPlanted, {
                    .actorClientNum = event.clientNum,
                    .objectId = event.objectId,
                    .siteLabel = plantSite->label,
                    .origin = playerState->origin,
                    .elapsedMilliseconds = event.elapsedMilliseconds,
                });
                queueSdSoundForTeam(
                    SvTeam::Tf, sdSoundPresentation_.tf.bombPlanted);
                queueSdSoundForTeam(
                    SvTeam::Sc, sdSoundPresentation_.sc.bombPlanted);
                continue;
            }
            const auto defuseSite = std::ranges::find_if(
                sdBombSiteRuntime_, [&](const SvSdBombSiteRuntime &site) {
                    return site.defuseTrigger.objectId == event.objectId;
                });
            if (defuseSite != sdBombSiteRuntime_.end())
            {
                if (event.type == SvUseObjectEventType::Begin ||
                    event.type == SvUseObjectEventType::Cancel)
                {
                    world_.appendSdEvent(
                        event.type == SvUseObjectEventType::Begin
                            ? SvWorldEventType::SdDefuseStarted
                            : SvWorldEventType::SdDefuseCancelled,
                        {
                            .actorClientNum = event.clientNum,
                            .objectId = event.objectId,
                            .siteLabel = defuseSite->label,
                            .elapsedMilliseconds = event.elapsedMilliseconds,
                        });
                    continue;
                }
                if (!SV_CommitSdBombDefuse(
                        sdBombStatus_, event.clientNum, serverTime))
                {
                    throw std::logic_error(
                        "completed SD defuse could not commit lifecycle");
                }
                world_.appendSdEvent(SvWorldEventType::SdBombDefused, {
                    .actorClientNum = event.clientNum,
                    .objectId = event.objectId,
                    .siteLabel = defuseSite->label,
                    .origin = playerState->origin,
                    .elapsedMilliseconds = event.elapsedMilliseconds,
                });
                queueSdSoundForTeam(
                    SvTeam::Tf, sdSoundPresentation_.tf.bombDefused);
                queueSdSoundForTeam(
                    SvTeam::Sc, sdSoundPresentation_.sc.bombDefused);
            }
        }
    }

    void ServerCore::projectSdObjectives(
        const std::span<const SvWorldClientInput> activeClients)
    {
        if (!sdBombStatus_.configured || !sdObjectiveMaterials_ ||
            sdBombStatus_.sites.size() != 2)
        {
            return;
        }
        const auto visible = sdRoundStatus_.armed && !sdRoundStatus_.completed;
        for (const auto &client : activeClients)
        {
            const auto playerVisible = visible &&
                client.gameplayState == ClientGameplayState::Playing;
            const auto objectives = sdBombStatus_.phase == SvSdBombPhase::Planted &&
                    sdBombStatus_.plantedSiteLabel &&
                    sdBombStatus_.plantedOrigin
                ? SV_BuildSdPlantedObjectives(
                    *sdBombStatus_.plantedSiteLabel,
                    *sdBombStatus_.plantedOrigin,
                    client.team,
                    *sdObjectiveMaterials_,
                    playerVisible)
                : SV_BuildSdObjectives(
                    sdBombStatus_.sites,
                    client.team,
                    *sdObjectiveMaterials_,
                    playerVisible &&
                        sdBombStatus_.phase != SvSdBombPhase::Defused &&
                        sdBombStatus_.phase != SvSdBombPhase::Exploded);
            auto projectedObjectives = objectives;
            auto bombOrigin = sdBombVisualHomeOrigin_;
            if (sdBombStatus_.phase == SvSdBombPhase::Dropped &&
                sdBombPickupTrigger_)
            {
                bombOrigin = sdBombPickupTrigger_->origin;
            }
            else if (sdBombStatus_.phase == SvSdBombPhase::Carried &&
                sdBombStatus_.carrierClientNum)
            {
                if (const auto carrierState =
                        world_.playerState(*sdBombStatus_.carrierClientNum))
                {
                    bombOrigin = carrierState->origin;
                }
            }
            static_cast<void>(SV_AddSdBombObjective(
                projectedObjectives,
                sdBombStatus_.phase,
                bombOrigin,
                client.team,
                *sdObjectiveMaterials_,
                playerVisible));
            if (!world_.setPlayerObjectives(
                    client.clientNum, projectedObjectives))
                throw std::logic_error("SD objective lost world player ownership");
        }
    }

    void ServerCore::trackMatchParticipation(const std::uint32_t serverTime)
    {
        const auto &slots = clients_.clients();
        for (std::uint32_t clientNum{}; clientNum < slots.size(); ++clientNum)
        {
            const auto &slot = slots[clientNum];
            const auto playing = slot.state == ClientState::Active &&
                slot.gameplayState == ClientGameplayState::Playing;
            auto found = matchParticipation_.find(clientNum);
            if (!playing)
            {
                if (found != matchParticipation_.end() &&
                    found->second.activeSince)
                {
                    found->second.accumulatedMilliseconds +=
                        serverTime - *found->second.activeSince;
                    found->second.activeSince.reset();
                }
                continue;
            }
            if (found == matchParticipation_.end() ||
                found->second.xuid != slot.xuid)
            {
                found = matchParticipation_.insert_or_assign(
                    clientNum,
                    MatchParticipation{
                        .xuid = slot.xuid,
                        .activeSince = serverTime,
                    }).first;
            }
            else if (!found->second.activeSince)
            {
                found->second.activeSince = serverTime;
            }
        }
    }

    std::uint32_t ServerCore::matchParticipationMilliseconds(
        const std::uint32_t clientNum,
        const std::uint32_t endServerTime) const
    {
        const auto found = matchParticipation_.find(clientNum);
        if (found == matchParticipation_.end())
            return 0;
        auto total = static_cast<std::uint64_t>(
            found->second.accumulatedMilliseconds);
        if (found->second.activeSince &&
            endServerTime >= *found->second.activeSince)
        {
            total += endServerTime - *found->second.activeSince;
        }
        return static_cast<std::uint32_t>(std::min<std::uint64_t>(
            total, std::numeric_limits<std::uint32_t>::max()));
    }

    void ServerCore::projectClientHudElems(
        const std::span<const SvWorldClientInput> activeClients)
    {
        // CODREF(g_run_frame): HUD projection follows objective projection and
        // precedes ClientEndFrame, the same ordering BO1 G_RunFrame 0x0062B320
        // and Ghosts G_RunFrame 0x140131C80 use. It owns BOTH elem arrays for
        // every client, so it must run in every gametype - unlike
        // projectSdObjectives, which returns early without an SD bomb.
        const auto serverTime = world_.snapshot().serverTime;
        const auto outcomeBirth = matchCompletionServerTime_ +
            SvDmOutcomeDelayMilliseconds;
        const auto outcomeActive = matchGameType_ == "dm" &&
            matchCompletionAnnounced_ && serverTime >= outcomeBirth &&
            serverTime < outcomeBirth + SvDmOutcomeDurationMilliseconds;
        std::vector<std::uint32_t> outcomePlayers;
        std::vector<SvClientScore> outcomeScores;
        if (outcomeActive)
        {
            for (const auto &[clientNum, kills] :
                clients_.topClientsByKills(SvDmPlacementLabels.size()))
            {
                static_cast<void>(kills);
                outcomePlayers.push_back(clientNum);
                outcomeScores.push_back(
                    clients_.clientScore(clientNum).value_or(SvClientScore{}));
            }
        }
        std::vector<std::uint32_t> alertedAttackers;
        // Committed damage only. finishPlayerDamage appends PlayerDamage
        // inside the usercmd candidate transaction and beginFrame restores the
        // whole event list when that transaction is withdrawn, so an event
        // still present here belongs to a command the world accepted.
        for (const auto &event : world_.frameEvents())
        {
            if (event.type != SvWorldEventType::PlayerDamage ||
                !event.playerDamage)
            {
                continue;
            }
            const auto &damage = *event.playerDamage;
            if (damage.damage <= 0 || !damage.attackerEntityNum)
                continue;
            const auto attacker = *damage.attackerEntityNum;
            // IW4 _damage.gsc gates the feedback on an attacking PLAYER that is
            // not the victim and not a team mate; BO1 _damagefeedback.gsc keeps
            // the same three conditions. Player entities occupy their own
            // client slot number, so a non-client inflictor has no gameplay
            // state and drops out here.
            if (attacker == damage.targetClientNum ||
                !world_.gameplayState(attacker) ||
                world_.onSameTeam(attacker, damage.targetClientNum))
            {
                continue;
            }
            auto &damageFeedback = clientFeedback_[attacker];
            damageFeedback.markerStart = serverTime;
            damageFeedback.markerExpiry =
                serverTime + SvDamageFeedbackDurationMilliseconds;
            // The marker and the alert are the two independent side effects of
            // IW4 _damagefeedback.gsc; neither waits on the other. One alert
            // per attacker per frame keeps a burst weapon from spending the
            // reliable-command ring on a single trigger pull.
            // The audition harness that walked all 75 networked aliases lived
            // here and is removed: it hijacked the hit sound, and its answer is
            // recorded - none of them is a hit marker or a medal.
            if (damageFeedbackSound_ &&
                std::ranges::find(alertedAttackers, attacker) ==
                    alertedAttackers.end())
            {
                alertedAttackers.push_back(attacker);
                static_cast<void>(clients_.queueLocalSound(
                    attacker, *damageFeedbackSound_));
            }
        }
        // The kill is a separate event from its damage, and queuePlayerKilledEvent
        // defers it one frame so it cannot invalidate the Lua dispatch span it
        // was raised inside. The marker therefore spends one server frame in
        // its damage colour before turning into the kill marker.
        for (const auto &event : world_.frameEvents())
        {
            if (event.type != SvWorldEventType::PlayerKilled ||
                !event.playerKilled)
            {
                continue;
            }
            const auto &damage = event.playerKilled->damage;
            // The death is counted before any of the attacker tests below, so a
            // suicide, a fall and a team kill all still cost the victim a death.
            static_cast<void>(clients_.addClientDeaths(damage.targetClientNum, 1));
            // THE KILL FEED (section 191q). One EV_OBITUARY temp entity per
            // DEATH -- before every attacker test below, because retail sends
            // one for all 145 of the dm demo's deaths and its ET_PLAYER lives
            // number exactly 145 too. A suicide, a fall and a team kill each
            // get a line; only the client decides whether to draw text for it.
            //
            // The head-shot promotion is this server's, not the payload's: the
            // bullet path files MOD_PISTOL_BULLET/MOD_RIFLE_BULLET and never
            // MOD_HEAD_SHOT, so the obituary would show a rifle where retail
            // shows a skull. The test is the SAME hit-location pair the headshot
            // medal below already fires on, so the icon and the medal cannot
            // disagree.
            // OFF BY DEFAULT, AND THE PLAYER DECIDED THAT (2026-09-04).
            //
            // The obituary entity is archived on every kill and the wire half
            // is proven against a foreign decoder -- but it produced NO KILL
            // FEED and the player reported a new lag between the last white
            // hitmarker and the red kill marker. The server log shows the death
            // registering on the killing bullet and the obituary one frame
            // later, so I could not reproduce the lag from this side and asked
            // for an A/B. The answer was: *"im not even gonna test this. I
            // guarantee you the lag was caused by your stupid obituary thing
            // that didn't even give me a killfeed."*
            //
            // That is the right call whether or not the diagnosis is: a feature
            // that delivers nothing has no claim on a live match. It stays in
            // the tree because the mechanism is decoded and the remaining
            // question is client-side (section 191q), and it turns on with
            // OLMOD_KILL_FEED=1 for a bench run.
            //
            // AND THE BLOCKER WAS FOUND ON 2026-09-04, WHICH CHANGES THE ODDS.
            // There are THREE independent eType allow-lists and the third one's
            // own comment says "adding an eType means touching all three";
            // section 191q touched two. The one it missed is the frame-wide
            // list, and an eType missing THERE does not drop the entity -- it
            // rejects the WHOLE FRAME, every field for every client, on every
            // snapshot carrying a kill.
            //
            // That explains BOTH halves of the player's report at once: no feed
            // (the obituary never reached anyone) AND a hitch between the white
            // hitmarker and the red kill marker (a dropped snapshot at exactly
            // the instant of a kill). The diagnosis I could not reproduce from
            // the server side was real, and it was not the obituary -- it was
            // the missing gate. Fixed in the same commit that added the flesh
            // hit.
            //
            // AND IT WORKS. Player-confirmed 2026-09-04 on the very next bench
            // run after the gate fix: *"kill feed works"*. So the default
            // follows the demonstration, as promised, and OLMOD_KILL_FEED=0
            // turns it off again.
            //
            // The mechanism was never wrong. sect.191q decoded EV_OBITUARY
            // correctly, proved the wire against a foreign decoder, and shipped
            // it off because a correct feature that shows nothing has no claim
            // on a live match. What it could not see was the third allow-list,
            // and one missing eType there was enough to delete every frame the
            // obituary rode in on.
            static const bool killFeedEnabled = [] {
                const char *const value = std::getenv("OLMOD_KILL_FEED");
                return !(value && value[0] == '0' && !value[1]);
            }();
            if (killFeedEnabled)
            {
                const auto headshot =
                    damage.hitLocation == SvHitLocationHelmet ||
                    damage.hitLocation == SvHitLocationHead;
                const auto methodOfDeath = headshot
                    ? SvMethodOfDeathHeadShot
                    : damage.methodOfDeath;
                const auto obituaryAttacker =
                    damage.attackerEntityNum &&
                        *damage.attackerEntityNum < MaximumGameClients
                    ? *damage.attackerEntityNum
                    : EntityNumWorld;
                if (!world_.spawnObituaryEvent(
                        damage.targetClientNum,
                        obituaryAttacker,
                        SV_ObituaryEventParameter(
                            methodOfDeath, damage.weaponAssetIndex)))
                {
                    // SILENT WHEN HEALTHY. The only way this fails is a spent
                    // entity pool or a state the writer would refuse, and both
                    // are worth a line because the feed then just stops.
                    OlMod::RuntimeLog::write(
                        OlMod::RuntimeLog::Channel::GameServer,
                        "obituary REFUSED victim=" +
                            std::to_string(damage.targetClientNum) +
                            " attacker=" + std::to_string(obituaryAttacker) +
                            " mod=" + std::to_string(methodOfDeath) +
                            " weapon=" +
                            std::to_string(damage.weaponAssetIndex));
                }
            }
            if (!damage.attackerEntityNum)
                continue;
            const auto attacker = *damage.attackerEntityNum;
            if (attacker == damage.targetClientNum ||
                !world_.gameplayState(attacker) ||
                world_.onSameTeam(attacker, damage.targetClientNum))
            {
                continue;
            }
            if (scavengerBagWeaponAssetIndex_ &&
                !world_.spawnScavengerBag(
                    damage.targetClientNum, *scavengerBagWeaponAssetIndex_))
            {
                OlMod::RuntimeLog::write(
                    OlMod::RuntimeLog::Channel::GameServer,
                    "scavenger bag REFUSED victim=" +
                        std::to_string(damage.targetClientNum));
            }
            const auto victim = damage.targetClientNum;
            // THE KILLCAM'S SUBJECT, RECORDED HERE BECAUSE THIS IS THE ONLY
            // PLACE THAT KNOWS IT. driveClientUiScreens sees a player go from
            // alive to dead and nothing else; who did it and when lives on this
            // event, one frame earlier, and was thrown away by everything that
            // consumed it. The victim's OWN entity number is what retail points
            // the camera at -- killCamLookAtEntity is 6 on all seven of the
            // recording client's deaths, and 6 is its clientNum -- so only the
            // killer and the time need carrying.
            killCamSubjects_[victim] = { attacker, serverTime };
            lastMatchKill_ = SvMatchEndKill{ attacker, victim, serverTime };
            // OLMOD(splash-queue): a medal is ENQUEUED, not sent. The client
            // holds one splash per display slot, so two on the same frame means
            // the second overwrites the first before it draws - which is what
            // "it will not give me both revenge and headshot" looks like from
            // the screen. releasePendingSplashes drains one every
            // SvSplashReleaseIntervalMilliseconds, which is the interval the
            // retail demo spaces its own multi-medal kills by.
            //
            // The sound moves with the banner rather than firing per kill, so
            // each medal keeps its own sting and they cannot drift apart. That
            // also matches the demo: 18 splash sounds against 20 slot-0
            // splashes, not one per kill.
            const auto awardSplash = [&](const std::uint32_t row,
                                         const std::int32_t points) {
                auto &queue = splashQueue_[attacker];
                if (queue.size() >= SvSplashQueueLimit)
                {
                    OlMod::RuntimeLog::write(
                        OlMod::RuntimeLog::Channel::GameServer,
                        "splash queue full client=" + std::to_string(attacker) +
                            " dropped row=" + std::to_string(row));
                    return;
                }
                queue.push_back({ .row = row, .points = points });
            };
            // Retail aarScoreboard.killstreak is the current streak, not the
            // match maximum: it rises on kills and resets on each death.
            static_cast<void>(clients_.addClientStreak(attacker, 1));
            if (!firstBloodAwarded_)
            {
                firstBloodAwarded_ = true;
                awardSplash(SvSplashFirstBlood, SvSplashFirstBloodPoints);
            }
            // CONFIRMED LIVE. This was a hypothesis - the payload's hitLocation
            // is a trace PART GROUP and section 51h had not established that
            // partGroup is the hit-location NAME index - and the log line below
            // is what settled it: one played match, 17 kills, and the HEADSHOT
            // medal firing when the player took a headshot. The kill line stays
            // because it is the only place part groups are observable at all.
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer,
                "kill attacker=" + std::to_string(attacker) +
                    " victim=" + std::to_string(victim) +
                    " partGroup=" + std::to_string(damage.hitLocation) +
                    " bone=" + std::to_string(damage.boneIndex) +
                    " mod=" + std::to_string(damage.methodOfDeath) +
                    // The obituary's two inputs, because "mod=2" alone cannot
                    // say which of the two branches the client will take.
                    " weapon=" + std::to_string(damage.weaponAssetIndex) +
                    " obitparm=" +
                    std::to_string(SV_ObituaryEventParameter(
                        damage.hitLocation == SvHitLocationHelmet ||
                                damage.hitLocation == SvHitLocationHead
                            ? SvMethodOfDeathHeadShot
                            : damage.methodOfDeath,
                        damage.weaponAssetIndex)));
            if (damage.hitLocation == SvHitLocationHelmet ||
                damage.hitLocation == SvHitLocationHead)
            {
                // Retail DM updates aarScoreboard.headshots on the lethal
                // event (recorder row 6 reaches four). The field already had
                // a serializer but no producer. Count once here, after the
                // suicide/invalid-attacker/team checks, independently of the
                // presentation queue and its capacity.
                static_cast<void>(clients_.addClientHeadshots(attacker, 1));
                awardSplash(SvSplashHeadshot, SvSplashHeadshotPoints);
                if (headshotSound_)
                {
                    static_cast<void>(
                        clients_.queueLocalSound(attacker, *headshotSound_));
                }
            }
            // Revenge: the victim is the last player to have killed the
            // attacker. Consumed on use, so one death buys one revenge.
            if (const auto avenged = lastKilledBy_.find(attacker);
                avenged != lastKilledBy_.end() && avenged->second == victim)
            {
                lastKilledBy_.erase(avenged);
                awardSplash(SvSplashRevenge, SvSplashRevengePoints);
            }
            // First-place kill: the victim held the top of the scoreboard.
            // bestClientKills is the same reading the score limit uses, so the
            // medal and the win condition can never disagree about who is
            // leading. It needs a kill on the board, which also stops it firing
            // on the first kill of a match where everyone is on zero.
            //
            // ORDERING: dm.lua credits the attacker's kill during the world
            // frame, so an attacker who takes the lead with this very kill is
            // already ahead of the victim by the time this runs and the medal
            // is missed. That is one frame of skew, not a wrong trigger, and
            // fixing it would mean keeping a shadow copy of the scoreboard.
            if (const auto best = clients_.bestClientKills();
                best && best->first == victim && best->second > 0)
            {
                awardSplash(SvSplashFirstPlaceKill,
                            SvSplashFirstPlaceKillPoints);
            }
            lastKilledBy_[victim] = attacker;
            // MEASURED: the retail dm server plays `p 15` -- alias
            // `mp_hit_kill` -- 28 times against 84 `mp_hit_alert`, which is the
            // ratio of kills to hits and is what the alias name says anyway.
            // It goes to the ATTACKER, beside the kill marker and the score
            // popup, which are the two things it is the audio for.
            if (killFeedbackSound_)
            {
                static_cast<void>(
                    clients_.queueLocalSound(attacker, *killFeedbackSound_));
            }
            auto &feedback = clientFeedback_[attacker];
            feedback.markerStart = serverTime;
            feedback.markerIsKill = true;
            feedback.scoreStart = serverTime;
            feedback.scoreExpiry =
                serverTime + SvScoreFeedbackDurationMilliseconds;
            // dm awards 50, the team modes 100. Both are measured; see the
            // constants. This is still the awarded AMOUNT rather than what the
            // script actually gave, which is a separate seam worth closing.
            feedback.scoreValue = matchGameType_ == "dm"
                ? SvDmScoreFeedbackKillPoints
                : SvScoreFeedbackKillPoints;
            // Hold the marker for as long as the popup lives even though its
            // own fade finishes sooner. These elems are POSITIONAL - the
            // client keys them by slot - so retiring the marker first would
            // slide the popup from slot 1 down to slot 0 and restart its
            // animation mid-flight. Retail never moves an elem either; it
            // leaves the faded one in place. By then the marker has reached
            // alpha 0, so holding it costs nothing on screen.
            feedback.markerExpiry = feedback.scoreExpiry;
        }
        driveClientPerks(serverTime, activeClients);
        for (const auto collector : world_.updateScavengerBags())
        {
            if (scavengerPickupSound_)
            {
                static_cast<void>(clients_.queueLocalSound(
                    collector, *scavengerPickupSound_));
            }
        }
        driveClientEquipment(activeClients);
        if(factoryInteractablesEnabled_) {
            if(factoryTeleportersEnabled_)driveFactoryTeleporters(activeClients);
            driveFactoryBox(activeClients);
        }
        driveCursorHints(activeClients);
        driveClientUiScreens(serverTime, activeClients);
        // Drain the medal queues before the feedback pass. One release per
        // client per interval; the first medal after a quiet spell goes out on
        // the frame it was earned, because nothing is pending against it.
        for (auto &[splashClient, queue] : splashQueue_)
        {
            if (queue.empty())
                continue;
            const auto released = lastSplashRelease_.find(splashClient);
            if (released != lastSplashRelease_.end() &&
                serverTime - released->second <
                    SvSplashReleaseIntervalMilliseconds)
            {
                continue;
            }
            const auto pending = queue.front();
            queue.erase(queue.begin());
            lastSplashRelease_[splashClient] = serverTime;
            static_cast<void>(clients_.queueReliableCommand(
                splashClient,
                SV_BuildSplashCommand(
                    SvSplashSlotDefault, pending.row, pending.points)));
            if (splashSound_)
            {
                static_cast<void>(
                    clients_.queueLocalSound(splashClient, *splashSound_));
            }
        }
        for (const auto &client : activeClients)
        {
            const auto playerState = world_.playerState(client.clientNum);
            if (!playerState)
                continue;
            if (world_.consumeZombieDown(client.clientNum))
                static_cast<void>(clients_.addClientDowns(client.clientNum));
            std::uint16_t markerMaterial{};
            std::uint32_t markerStart{};
            std::uint32_t scoreStart{};
            std::optional<float> scorePopup;
            const auto entry = clientFeedback_.find(client.clientNum);
            if (entry != clientFeedback_.end())
            {
                auto &feedback = entry->second;
                if (client.gameplayState != ClientGameplayState::Playing)
                {
                    clientFeedback_.erase(entry);
                }
                else
                {
                    if (serverTime < feedback.markerExpiry)
                    {
                        // Fall back to the damage marker when the kill material
                        // is missing rather than dropping the feedback: they
                        // are separate configstrings and only one may be absent.
                        const auto &material = feedback.markerIsKill &&
                                killFeedbackMaterial_
                            ? killFeedbackMaterial_
                            : damageFeedbackMaterial_;
                        markerMaterial = material.value_or(0);
                        markerStart = feedback.markerStart;
                    }
                    else
                    {
                        feedback.markerIsKill = false;
                    }
                    if (serverTime < feedback.scoreExpiry)
                    {
                        scorePopup = feedback.scoreValue;
                        scoreStart = feedback.scoreStart;
                    }
                    if (serverTime >= feedback.markerExpiry &&
                        serverTime >= feedback.scoreExpiry)
                    {
                        clientFeedback_.erase(entry);
                    }
                }
            }
            auto currentHud = SV_BuildFeedbackHudElems(
                markerMaterial, markerStart, scorePopup, scoreStart,
                serverTime);
            if (factoryEntryEnabled_)
            {
                const auto entry = factoryEntries_.find(client.clientNum);
                if (entry != factoryEntries_.end())
                {
                    auto dst = std::ranges::find(currentHud, SvHudElemType::Free, &SvHudElem::type);
                    for (const auto &elem : SV_BuildFactoryEntryHud(entry->second.birth, serverTime))
                    {
                        if (elem.type == SvHudElemType::Free || dst == currentHud.end()) break;
                        *dst++ = elem;
                    }
                }
            }
            if (world_.factoryPerkMachinesEnabled()) {
                const auto hold = factoryAmmoHolds_.find(client.clientNum);
                if (hold != factoryAmmoHolds_.end()) {
                    if (!playerState->health || playerState->spawnGeneration != hold->second.generation)
                        factoryAmmoHolds_.erase(hold);
                    else {
                        auto dst = std::ranges::find(currentHud, SvHudElemType::Free, &SvHudElem::type);
                        if (currentHud.end() - dst >= 2)
                            for (const auto &elem : SV_BuildFactoryAmmoHud(hold->second,serverTime,factoryAmmoMaterials_)) {
                                if (elem.type == SvHudElemType::Free) break;
                                *dst++ = elem;
                            }
                    }
                }
            }
            if (world_.zombieRevivalActive() && !world_.zombieTeamWiped())
            {
                const auto target=world_.zombieReviveTarget(client.clientNum);
                const auto down=target?world_.zombieDownedState(*target):std::nullopt;
                if (down && world_.zombieReviveHeld(client.clientNum))
                {
                    auto dst=std::ranges::find(currentHud,SvHudElemType::Free,&SvHudElem::type);
                    const auto treatment=SV_BuildZombieTreatmentHud(*down,serverTime,client.clientNum,factoryAmmoMaterials_);
                    if (currentHud.end()-dst>=3)
                        for (const auto &elem:treatment) { if(elem.type==SvHudElemType::Free)break; *dst++=elem; }
                }
            }
            // Project after all committed lethal events, including victim resets.
            const auto score = clients_.clientScore(client.clientNum);
            static_cast<void>(world_.setPlayerKillstreak(
                client.clientNum,
                matchGameType_ == "zm"
                    ? std::uint8_t{}
                    : static_cast<std::uint8_t>(
                          std::clamp(score ? score->killstreak : 0, 0, 255))));
            // The objectives this frame already committed to the world are the
            // waypoint source; rebuilding from them keeps one HUD owner without
            // making the archival array depend on the SD projector running.
            auto archivalHud =
                SV_BuildObjectiveHudElems(playerState->objectives);
            if(matchGameType_=="zm" && archivalHud.back().type==SvHudElemType::Free)
            {
                // Reserve one stable prefix slot, preserving every objective.
                // If all31 slots are occupied, omit optional score feedback.
                std::move_backward(archivalHud.begin(),archivalHud.end()-1,archivalHud.end());
                archivalHud[0]=SV_BuildZmScoreHudElem(
                    world_.zombieScoreFeedback(client.clientNum),serverTime);
            }
            if (world_.zombieRevivalActive())
            {
                if (world_.zombieTeamWiped())
                {
                    currentHud={}; archivalHud={};
                    archivalHud[0]=SV_BuildZombieGameOverHud();
                }
                else
                {
                    auto dst=std::ranges::find(archivalHud,SvHudElemType::Free,&SvHudElem::type);
                    for (const auto &other:activeClients)
                    {
                        if (other.clientNum==client.clientNum || dst==archivalHud.end()) continue;
                        const auto down=world_.zombieDownedState(other.clientNum);
                        if (!down || down->bledOut) continue;
                        const auto marker=SV_BuildZombieReviveMarker(static_cast<std::uint16_t>(other.clientNum),
                            down->reviver && serverTime-down->lastSeen<=500,zombieReviveMaterials_);
                        if (marker.type!=SvHudElemType::Free) *dst++=marker;
                    }
                }
            }
            if(factoryTeleportersEnabled_ && factoryTeleporters_.showsClock(
                    client.clientNum,playerState->spawnGeneration,serverTime) &&
                !world_.zombieTeamWiped()) {
                auto free=std::ranges::find(archivalHud,SvHudElemType::Free,&SvHudElem::type);
                const auto clock=SV_BuildFactoryLinkClock(factoryTeleporters_.linkExpiry,factoryTeleporterResources_);
                if (archivalHud.end()-free>=2 && clock[0].type!=SvHudElemType::Free) {
                    *free++=clock[0]; *free=clock[1];
                }
            }
            if (outcomeActive)
            {
                std::optional<float> bonus;
                if (const auto found = dmMatchBonuses_.find(client.clientNum);
                    found != dmMatchBonuses_.end())
                    bonus = static_cast<float>(found->second);
                archivalHud = SV_BuildDmOutcomeHudElems(
                    outcomePlayers,
                    bonus,
                    outcomeBirth,
                    SV_IsDmOutcomeTie(
                        client.clientNum, outcomePlayers, outcomeScores)
                        ? SvDmTieText
                        : matchStatus_.winnerClientNum == client.clientNum
                            ? SvDmVictoryText
                            : SvDmDefeatText,
                    matchStatus_.endReason == SvMatchEndReason::ScoreLimit
                        ? SvDmScoreLimitText
                        : SvDmTimeLimitText);
            }
            if (!world_.setPlayerHudElems(
                    client.clientNum, currentHud, archivalHud))
            {
                throw std::logic_error("HudElem lost world player ownership");
            }
        }
    }

    void ServerCore::runFrame(const std::uint32_t frameMilliseconds)
    {
        const auto totalTimingStart = FrameClock::now();
        auto phaseTimingStart = totalTimingStart;
        ++status_.frameNumber;
        // 12.132: the zm round HUD, published once per client on a settled tick.
        // Deliberately NOT at enter-world -- 12.131 did that and stalled the
        // client at "waiting for connection".
        clients_.publishZmRoundHud(status_.frameNumber);
        const auto sharedPmoveAvailable = world_.sharedPmoveAvailable();
        std::vector<SvWorldClientInput> activeClients;
        const auto &clientSlots = clients_.clients();
        activeClients.reserve(clientSlots.size());
        for (std::size_t index = 0; index < clientSlots.size(); ++index)
        {
            if (clientSlots[index].state == ClientState::Active)
            {
                const auto clientNum = static_cast<std::uint32_t>(index);
                std::optional<SvResolvedLoadout> resolvedLoadout;
                if (sharedPmoveAvailable &&
                    clientSlots[index].pendingLoadoutSequence &&
                    !clientSlots[index].pendingSelectedLoadout.empty() &&
                    loadoutProvider_)
                {
                    auto pendingLoadout = clients_.resolveAndCommitPendingLoadout(
                        clientNum, loadoutProvider_);
                    if (pendingLoadout)
                    {
                        resolvedLoadouts_[clientNum] = {
                            .sequence = clientSlots[index].loadoutSequence,
                            .loadout = std::move(pendingLoadout),
                        };
                    }
                }
                if (clientSlots[index].gameplayState == ClientGameplayState::Playing &&
                    clientSlots[index].loadoutSequence &&
                    !clientSlots[index].selectedLoadout.empty())
                {
                    auto resolution = resolvedLoadouts_.find(clientNum);
                    if ((resolution == resolvedLoadouts_.end() ||
                            resolution->second.sequence !=
                                clientSlots[index].loadoutSequence) &&
                        loadoutProvider_)
                    {
                        auto committedLoadout = loadoutProvider_(
                            clientSlots[index].xuid,
                            clientSlots[index].selectedLoadout);
                        if (committedLoadout &&
                            SV_IsResolvedLoadoutValid(*committedLoadout))
                        {
                            resolvedLoadouts_[clientNum] = {
                                .sequence = clientSlots[index].loadoutSequence,
                                .loadout = std::move(committedLoadout),
                            };
                            resolution = resolvedLoadouts_.find(clientNum);
                        }
                    }
                    if (resolution != resolvedLoadouts_.end() &&
                        resolution->second.sequence ==
                            clientSlots[index].loadoutSequence)
                    {
                        resolvedLoadout = resolution->second.loadout;
                    }
                }
                // BATTLE ROYALE SPAWN LOADOUT: TRIED, REVERTED, FINDING KEPT.
                //
                // The player's first words on getting into mp_battlecity were "I spawned
                // in with my TDM class", and they are right -- `dmz.lua` is a copy of
                // `dm.lua`, so BattleCity runs deathmatch rules and hands out the saved
                // class. Retail grants ONE weapon on the first spawn instead (`a 1213`,
                // seq 34 of C-2021-7-25[22-0-7]dmz) and the rest is looted.
                //
                // The obvious small step -- copy `secondary` over `primary` so the player
                // keeps only a sidearm -- was tried 2026-09-05 03:23 AND IS WRONG ON THIS
                // BUILD. Measured: the player spawned holding `weap=1148`, which is the
                // FIRST LOOT-BAND INDEX, with no weapon name and 0 ammo on the HUD. The
                // secondary slot does not resolve to a usable sidearm here, so the swap
                // trades a working CheyTac for an unusable weapon.
                //
                // AND "SPAWN WITH NOTHING" IS NOT AVAILABLE EITHER. Section 152y: an
                // Active client with no loadout gets `viewmodelIndex = 0`, a zero
                // viewmodel makes the client's sub_53F5F0 return null, and sub_59CC70
                // writes through it unchecked -- an access violation, not an empty
                // inventory.
                //
                // So the real BR spawn needs the LOOT SYSTEM able to hand a weapon back
                // before the class can be taken away. Until then the class stays: it is
                // wrong for the mode but it is playable, which is the better of the two.

                activeClients.push_back({
                    .clientNum = clientNum,
                    // TODO(CODOL): Recover the native SV_ClientEnterWorld
                    // baseline. The project checkpoint takes precedence so a
                    // respawn cannot absorb an unexecuted received command.
                    .spawnUserCmdBaseline =
                        clientSlots[index].lastExecutedUserCmd
                            ? clientSlots[index].lastExecutedUserCmd
                            : clientSlots[index].lastReceivedUserCmd,
                    .gameplayState = clientSlots[index].gameplayState,
                    .team = clientSlots[index].team,
                    .loadoutSequence = clientSlots[index].loadoutSequence,
                    .spawnSequence = clientSlots[index].spawnSequence,
                    .resolvedLoadout = resolvedLoadout,
                    .characterCustomization = characterCustomizationProvider_
                        ? characterCustomizationProvider_(
                            clientNum,
                            clientSlots[index].xuid,
                            clientSlots[index].characterFaction)
                        : std::nullopt,
                    // AFTER the customization provider, because that is what fills the
                    // table this reads -- both run on the same frame for the same
                    // client and the order is the dependency.
                    .characterOptionMask = characterOptionMaskProvider_
                        ? characterOptionMaskProvider_(clientNum)
                        : std::array<std::uint32_t, 12>{},
                    .factoryClassSelection = factoryEntryEnabled_,
                });
                // AND A PLAYER WHO HAS RESOLVED ONCE NEVER STOPS BEING PUBLISHED.
                // Section 166: this provider answers per frame and nothing retained
                // its answer, so one frame it could not answer removed that client's
                // clientInfo from every observer and left them invisible. Remember
                // the last good one and fall back to it; a NEW answer always wins,
                // so a mid-match character change still lands.
                {
                    auto &memory =
                        lastCharacterCustomizations_[clientNum];
                    auto &resolvedNow =
                        activeClients.back().characterCustomization;
                    if (resolvedNow)
                    {
                        memory.xuid = clientSlots[index].xuid;
                        memory.customization = *resolvedNow;
                    }
                    else if (memory.xuid &&
                        memory.xuid == clientSlots[index].xuid)
                    {
                        resolvedNow = memory.customization;
                    }
                }
                // AND MAKE THIS PLAYER'S MODELS RESIDENT EVERYWHERE. Guarded on the
                // character inside, so a steady player costs one map lookup a frame.
                if (const auto &resolved = activeClients.back().characterCustomization)
                    precacheCharacterModels(
                        clientNum, resolved->characterItemId);
            }
        }
        std::erase_if(
            lastCharacterCustomizations_, [&activeClients](const auto &entry) {
                return std::ranges::none_of(
                    activeClients,
                    [&entry](const SvWorldClientInput &client) {
                        return client.clientNum == entry.first;
                    });
            });
        std::erase_if(resolvedLoadouts_, [&activeClients](const auto &entry) {
            return std::ranges::none_of(
                activeClients,
                [&entry](const SvWorldClientInput &client) {
                    return client.clientNum == entry.first &&
                        client.loadoutSequence == entry.second.sequence;
                });
        });
        framePrepareTiming_.record(
            frameElapsedMicroseconds(phaseTimingStart));
        phaseTimingStart = FrameClock::now();
        if (!world_.beginFrame(frameMilliseconds, activeClients))
        {
            frameBeginWorldTiming_.record(
                frameElapsedMicroseconds(phaseTimingStart));
            // SAY SO. A world phase that rejects publishes no playerStates, and the
            // only thing the log then showed was `missing_playerstate` from the
            // SNAPSHOT WRITER -- which is a symptom two layers downstream and names
            // the wrong suspect. That cost a session: the real fault was an access
            // violation inside BG_UpdatePlayerDObj poisoning the native entity
            // mirror. Edge-triggered, so a healthy server stays silent.
            reportWorldFrameRejection("beginFrame");
            return;
        }
        frameBeginWorldTiming_.record(
            frameElapsedMicroseconds(phaseTimingStart));
        phaseTimingStart = FrameClock::now();
        if (!matchStatus_.completed)
            trackMatchParticipation(world_.snapshot().serverTime);
        world_.stepZombieRevives();
        if (world_.zombieTeamWiped() && !matchStatus_.completed)
        {
            matchStatus_.completed=true;
            matchStatus_.endReason=SvMatchEndReason::TeamEliminated;
            matchStatus_.winner=SvTeam::None;
            matchStatus_.winnerClientNum.reset();
        }

        // CODREF(g_damage): BO1 G_DamageClient 0x00614250 and Ghosts
        // G_DamageClient 0x140126B70 call Scr_PlayerDamage synchronously from
        // the current weapon/damage stack. Their finishPlayerDamage methods
        // therefore commit health, pain or death before the next usercmd can
        // inspect that target. Preserve that command-order visibility even
        // though ol-mod currently represents script notifications as events.
        //
        // OLMOD(lua-world-event-batch): callbacks may append to frameEvents_.
        // Copy one stable suffix, advance ownership before invoking Lua, and
        // repeat until the suffix is empty. A callback error is intentionally
        // reported once rather than replayed after any earlier callback side
        // effects; replacing that policy requires the native script-thread
        // fatal-error owner, not an event retry heuristic.
        std::size_t dispatchedWorldEventCount{};
        const auto dispatchPendingWorldEvents = [this,
                                                    &dispatchedWorldEventCount] {
            while (true)
            {
                const auto events = world_.frameEvents();
                if (events.size() < dispatchedWorldEventCount)
                {
                    throw std::logic_error(
                        "world event queue shrank during frame dispatch");
                }
                if (events.size() == dispatchedWorldEventCount)
                    return;
                const std::vector<CodolGameServer::SvWorldEvent> pending(
                    events.begin() + dispatchedWorldEventCount, events.end());
                dispatchedWorldEventCount += pending.size();
                observeUavWeaponChanges(pending);
                for (const auto &event : pending)
                {
                    // OLMOD(zm-score-owner): this copied suffix is dispatched once,
                    // including pre-rotation headless deaths. Lua only owns wave
                    // counting; no parallel addscore/addkill path for zombies.
                    // CODREF(sv_write_snapshot_to_client):611AA0 reads these native
                    // aarScoreboard fields after J profile updates.
                    if (matchGameType_ == "zm" && event.zombieAward)
                    {
                        const auto &credit=*event.zombieAward;
                        const auto &slots=clients_.clients();
                        if (credit.clientNum < slots.size())
                        {
                            const auto &owner=slots[credit.clientNum];
                            const auto state=world_.playerState(credit.clientNum);
                            if (owner.gameplayState==ClientGameplayState::Playing &&
                                owner.spawnSequence==credit.spawnSequence && state &&
                                state->spawnGeneration==credit.spawnGeneration)
                            {
                                const auto &a=credit.award;
                                if(a.score)static_cast<void>(clients_.addClientScore(credit.clientNum,a.score));
                                if(a.kill)static_cast<void>(clients_.addClientKills(credit.clientNum,1));
                                if(a.headshot)static_cast<void>(clients_.addClientHeadshots(credit.clientNum,1));
                                if(a.kill)OlMod::RuntimeLog::write(OlMod::RuntimeLog::Channel::GameServer,
                                    "ZM_SCORE client="+std::to_string(credit.clientNum)+
                                    " score="+std::to_string(a.score)+" battery="+std::to_string(a.battery)+
                                    " headshot="+std::to_string(a.headshot));
                            }
                        }
                    }
                    if (event.type == SvWorldEventType::ZmRoundTick &&
                        event.serverTime <= 1000u)
                    {
                        OlMod::RuntimeLog::write(
                            OlMod::RuntimeLog::Channel::GameServer,
                            "ZMTICK dispatch serverTime=" +
                                std::to_string(event.serverTime) +
                                " sequence=" + std::to_string(event.sequence));
                    }
                }
                // TIMED, BECAUSE THIS IS COUNTED AS `thinkUs` AND IS NOT THINK.
                //
                // dispatchPendingWorldEvents runs inside the per-command loop that
                // frameClientThinkTiming_ wraps, so every microsecond a Lua callback
                // spends lands in the client-think window. 12.163 chased a 1.6 s
                // "client think" spike through collision linking and actor counts on
                // that reading before noticing the script was inside it.
                const auto scriptStart = FrameClock::now();
                static_cast<void>(scriptRuntime_.dispatchWorldEvents(pending));
                const auto scriptUs = frameElapsedMicroseconds(scriptStart);
                if (scriptUs >= 20000u)
                {
                    std::string types;
                    for (const auto &dispatched : pending)
                    {
                        types += " " + std::to_string(
                            static_cast<std::uint32_t>(dispatched.type));
                    }
                    OlMod::RuntimeLog::write(
                        OlMod::RuntimeLog::Channel::GameServer,
                        "SCRIPTSLOW us=" + std::to_string(scriptUs) +
                        " events=" + std::to_string(pending.size()) +
                        " types:" + types);
                }
            }
        };

        // Script threads resume only inside the authoritative fixed frame,
        // after world begin and before new client commands. A wait of zero
        // therefore resumes on the next server frame rather than recursively.
        static_cast<void>(
            scriptRuntime_.advance(world_.snapshot().serverTime));
        // ClientSpawned and the prior frame's deliberately deferred
        // PlayerKilled notifications own this point. They must run before a
        // newly admitted command observes the spawned/dead generation.
        dispatchPendingWorldEvents();
        if (sharedPmoveAvailable)
        {
            for (const auto &client : activeClients)
            {
                if (!world_.acceptsClientThink(client.clientNum))
                    continue;
                // CODDIFF(sv_process_client_thinks): CODOL has no retained
                // dedicated implementation. The embedded split receive/frame
                // architecture follows Ghosts' per-client cumulative budget so
                // one backlog cannot starve later clients or snapshot publish.
                // CODDIFF(sv_process_client_thinks): Ghosts can execute during
                // SV_UserMove and again after packet drain; this source waits
                // for the fixed frame because native world ownership exists
                // only inside beginFrame/endFrame. The local counter therefore
                // resets once per source snapshot-producing frame.
                const auto playerState = world_.playerState(client.clientNum);
                auto playerCommandTime = playerState
                    ? playerState->commandTime
                    : std::uint32_t{};
                std::uint32_t cumulativeThinkTime{};
                const auto thinkBudget = SV_ClientThinkBudgetMilliseconds();
                while (!thinkBudget || cumulativeThinkTime < thinkBudget)
                {
                    const auto command =
                        clients_.dispatchNextPendingUserCmd(client.clientNum);
                    if (!command)
                        break;
                    cumulativeThinkTime = SV_ChargeClientThinkTime(
                        cumulativeThinkTime,
                        command->commandTime,
                        playerCommandTime);
                    // AND THE BASE HAS TO ADVANCE WITH IT, OR THE BUDGET IS
                    // CHARGED THE SAME MILLISECONDS OVER AND OVER.
                    //
                    // Ghosts charges max(cmd.serverTime - ps.commandTime, 0)
                    // and ps.commandTime is advanced BY the pmove inside the
                    // think, so its next iteration measures from the command
                    // it just ran. This read ps.commandTime once before the
                    // loop and never moved it, so commands 8ms apart were
                    // charged 8, then 16, then 24, then 32 -- the 100ms budget
                    // gone after five instead of twelve.
                    //
                    // AND IT COMPOUNDS. The further behind a client falls, the
                    // larger the FIRST delta, until one command spends the
                    // whole budget and the server runs exactly one command per
                    // frame -- which puts it further behind again. Measured
                    // with one client tabbed in and both queues saturated:
                    //
                    //     pending=7 cmdAge=-513 recvExec=40   (capacity is 8)
                    //     pending=7 cmdAge=-464 recvExec=73
                    //     thinkCommands=85 per window, ~17/s executed against
                    //     ~140/s arriving
                    //
                    // cmdAge NEGATIVE is the symptom to remember: the client's
                    // newest command is half a second AHEAD of what the server
                    // has executed, which is exactly what a player feels.
                    playerCommandTime =
                        std::max(playerCommandTime, command->commandTime);
                    ++frameClientThinkCommands_;
                    if (!world_.clientThink(client.clientNum, *command))
                    {
                        const auto status =
                            world_.clientThinkStatus(client.clientNum);
                        if (!status)
                        {
                            break;
                        }
                        if (SV_ShouldDiscardRejectedUserCmd(
                                status->failureStage))
                        {
                            if (!clients_.discardRejectedUserCmd(
                                    client.clientNum, command->commandTime))
                            {
                                throw std::logic_error(
                                    "rejected usercmd lost dispatched queue ownership");
                            }
                            continue;
                        }
                        if (status->failureStage !=
                            SvClientThinkFailureStage::ClientEventsUnsupported)
                        {
                            break;
                        }
                        // TODO(CODOL): Delete this compatibility branch when
                        // every valid server-only event is authoritative. A
                        // missing handler must not permanently pin the queue
                        // while gameplay restoration is still incomplete.
                        if (!clients_.discardUnsupportedUserCmd(
                                client.clientNum, command->commandTime))
                        {
                            throw std::logic_error(
                                "unsupported usercmd lost dispatched queue ownership");
                        }
                        continue;
                    }
                    if (!clients_.commitExecutedUserCmd(
                            client.clientNum, command->commandTime))
                    {
                        throw std::logic_error(
                            "executed usercmd lost dispatched queue ownership");
                    }
                    playerCommandTime = command->commandTime;
                    processSdCommittedCommand(client, *command);
                    processLootCommittedCommand(client, *command);
                    processZmUseCommittedCommand(client, *command);
                    // CODDIFF(g_damage): the event carrier is project-owned,
                    // but the synchronous per-command mutation order matches
                    // native Scr_PlayerDamage/finishPlayerDamage ownership.
                    dispatchPendingWorldEvents();
                }
            }
        }
        frameClientThinkTiming_.record(
            frameElapsedMicroseconds(phaseTimingStart));
        phaseTimingStart = FrameClock::now();
        const auto advancedSdRound = advanceSdRound();
        if (!advancedSdRound)
            evaluateSdRound(activeClients);
        projectSdObjectives(activeClients);
        projectClientHudElems(activeClients);
        driveClientUav(activeClients);
        clients_.announceConnectionChanges();
        announceMatchRules();
        driveMatchAnnouncer();
        driveBattleChatter();
        // RE-ENABLED with the two things the bisect named fixed: free alias
        // indices instead of retail's occupied ones, and every client Active
        // instead of merely sent a gamestate.
        announceSoundAliases();
        announceFactorySoundAliases();
        if(factoryInteractablesEnabled_ && factoryBoxResources_.reconstructedPool)
            world_.stepFactoryWeaponLights(factoryBox_.teslaViewSlots);
        announceLoadoutDvars();
        announceVisionSet();
        projectDeathVision();
        announceMatchCompletion();
        driveMatchEndSequence();
        holdMatchCompletionState();
        pumpSdSoundQueues(activeClients);
        frameModeTiming_.record(
            frameElapsedMicroseconds(phaseTimingStart));
        phaseTimingStart = FrameClock::now();
        // CODREF(g_run_frame): BO1 G_RunFrame 0x0062B320 and Ghosts
        // G_RunFrame 0x140131C80 both run script threads and entity gameplay
        // before objective/HUD projection and ClientEndFrame. Damage policy
        // must therefore finish before endFrame snapshots playerstate/entity
        // state; dispatching it afterwards leaves the native world one frame
        // ahead of the snapshot being published.
        // Mode-owned events that were not produced by one exact command still
        // drain before ClientEndFrame. Notifications discovered by endFrame
        // drain at the second call below.
        dispatchPendingWorldEvents();

        // Entity links use the map-owned 12248 tag band.  Never carry a retail
        // numeric tag into another map; withholding the child until this name is
        // present is safer than attaching it to an arbitrary bone.
        if (!livingWeaponRightTagInitialized_)
        {
            constexpr std::uint16_t linkTagBase = 12248;
            std::uint8_t livingWeaponRightTag{};
            std::uint8_t emptyTag{};
            for (std::uint16_t tag = 1; tag < 256; ++tag)
            {
                const auto name = clients_.configString(linkTagBase + tag);
                if (name && *name == "tag_weapon_right")
                {
                    livingWeaponRightTag = static_cast<std::uint8_t>(tag);
                    break;
                }
                if ((!name || name->empty()) && !emptyTag)
                    emptyTag = static_cast<std::uint8_t>(tag);
            }
            if (!livingWeaponRightTag && emptyTag)
            {
                livingWeaponRightTag = emptyTag;
                static_cast<void>(clients_.SV_SetConfigString(
                    linkTagBase + livingWeaponRightTag, "tag_weapon_right"));
                const auto stored = clients_.configString(linkTagBase + livingWeaponRightTag);
                if (!stored || *stored != "tag_weapon_right")
                {
                    // The configstring owner refused the insertion. Keep the
                    // world tag at zero and retry on a later frame; no child is
                    // publishable without a real map-band name.
                    world_.setLivingWeaponRightTag(0);
                    livingWeaponRightTagInitialized_ = false;
                    livingWeaponRightTag = 0;
                }
            }
            world_.setLivingWeaponRightTag(livingWeaponRightTag);
            livingWeaponRightTagInitialized_ = livingWeaponRightTag != 0 || !emptyTag;
        }

        if (!world_.endFrame(activeClients))
        {
            // The rollback path: endFrame refuses when the native entity mirror is
            // not synchronized, restores the previous generation and publishes
            // nothing. See reportWorldFrameRejection.
            reportWorldFrameRejection("endFrame");
            return;
        }
        reportWorldFrameRejection({});

        // CODDIFF(g_run_frame): ol-mod's endFrame currently also discovers
        // disconnects and appends their project event. Preserve immediate
        // delivery without moving state-mutating gameplay callbacks back after
        // ClientEndFrame.
        dispatchPendingWorldEvents();
        // TODO(CODOL): replace the project event vectors with recovered script
        // notify/thread scheduling. Exit when nested notifications have an
        // explicit same-frame/deferred owner and no copied batch is required.
        // After endFrame, not before: world_.snapshot() is only the frame the
        // clients will actually be sent once endFrame has published it, and
        // reading it earlier found no ET_PLAYER entities at all.
        logPlayerPresentation();
        // AN OBITUARY THAT IS CREATED AND AN OBITUARY THAT IS SENT ARE
        // DIFFERENT CLAIMS, and spawnObituaryEvent only proves the first.
        // shouldArchiveWorldEntity is a fail-closed allow-list, so a missing
        // eType there drops the entity with no log anywhere. This reads the
        // PUBLISHED snapshot -- the one the clients are about to be sent.
        {
            std::set<std::uint32_t> present;
            for (const auto &entity : world_.snapshot().entities)
            {
                if (entity.eType != EntityTypeObituary)
                    continue;
                present.insert(entity.number);
                if (archivedObituaries_.contains(entity.number))
                    continue;
                OlMod::RuntimeLog::write(
                    OlMod::RuntimeLog::Channel::GameServer,
                    "obituary ARCHIVED num=" + std::to_string(entity.number) +
                        " victim=" + std::to_string(entity.otherEntityNum) +
                        " attacker=" + std::to_string(entity.groundEntityNum) +
                        " parm=" + std::to_string(entity.eventParm) +
                        " serverTime=" +
                        std::to_string(world_.snapshot().serverTime));
            }
            archivedObituaries_ = std::move(present);
        }
        status_.serverTime = world_.snapshot().serverTime;
        if (matchStatus_.configured)
        {
            const auto playing = std::ranges::any_of(
                activeClients, [](const SvWorldClientInput &client) {
                    return client.gameplayState == ClientGameplayState::Playing;
                });
            if (!matchStatus_.startServerTime && playing)
                matchStatus_.startServerTime = status_.serverTime;
            if (SV_UpdateMatchTimeLimit(
                    matchStatus_,
                    matchGameType_,
                    status_.serverTime,
                    clients_.teamScore(SvTeam::Tf).value_or(0),
                    clients_.teamScore(SvTeam::Sc).value_or(0)))
            {
                if (matchGameType_ == "dm")
                {
                    // The team scores it just compared are both 0 in a teamless
                    // mode, so it will have called the match a draw.
                    // Free-for-all's winner on time is whoever is ahead on their
                    // own score.
                    matchStatus_.winner = SvTeam::None;
                    if (const auto best = clients_.bestClientKills())
                        matchStatus_.winnerClientNum = best->first;
                }
                // THE SCORE-LIMIT PATH LOGS AND THIS ONE DID NOT, so a match
                // that ran out of clock was indistinguishable in the log from
                // one that was decided -- both simply start printing the
                // end-of-match schedule. That is exactly the gap that made
                // "twelve kills and no end of match" read as a scoring bug when
                // the limit in force was 30 and the clock was what ended it.
                const auto best = clients_.bestClientKills();
                OlMod::RuntimeLog::write(
                    OlMod::RuntimeLog::Channel::GameServer,
                    "match complete gametype=" + matchGameType_ +
                        " reason=timeLimit elapsed=" +
                        std::to_string(matchStatus_.elapsedMilliseconds) +
                        "ms limitMinutes=" +
                        std::to_string(matchStatus_.rules.timeLimitMinutes) +
                        " scoreLimit=" +
                        std::to_string(matchStatus_.rules.scoreLimit) +
                        " best=" +
                        (best ? "client" + std::to_string(best->first) + ":" +
                                std::to_string(best->second)
                              : std::string("none")));
            }
        }
        SvSnapshotFrameValidationFailure validationFailure{};
        if (!clients_.setWorldFrame(world_.snapshot(), &validationFailure))
        {
            status_.worldFrameValidationFailure = validationFailure;
            ++status_.worldFrameRejections;
        }
        else
        {
            status_.worldFrameValidationFailure =
                SvSnapshotFrameValidationFailure::None;
        }
        frameEndAndPublishTiming_.record(
            frameElapsedMicroseconds(phaseTimingStart));
        frameTotalTiming_.record(
            frameElapsedMicroseconds(totalTimingStart));
    }
}
