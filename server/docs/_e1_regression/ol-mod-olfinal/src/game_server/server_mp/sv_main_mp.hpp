#pragma once

#include "sv_client_mp.hpp"
#include "sv_frame_diagnostics.hpp"
#include "sv_map_triggers_mp.hpp"
#include "sv_mapents_mp.hpp"
#include "sv_battlechatter_mp.hpp"
#include "sv_splash_mp.hpp"
#include "sv_use_object_mp.hpp"
#include "sv_perks_mp.hpp"
#include "sv_zm_ammo_mp.hpp"
#include "sv_zm_box_mp.hpp"
#include "sv_zm_teleporters_mp.hpp"
#include "sv_rewards_mp.hpp"
#include "../../shared/DedicatedSession.hpp"
#include "sv_script_lua_mp.hpp"
#include "qcommon/net_dtls_cod.hpp"

#include <cstdint>
#include <deque>
#include <functional>
#include <mutex>
#include <optional>
#include <set>
#include <span>
#include <string>
#include <string_view>
#include <unordered_map>

namespace CodolGameServer
{
    [[nodiscard]] bool SV_ShouldDiscardRejectedUserCmd(
        SvClientThinkFailureStage stage);
    // THIS IS OURS, NOT CODOL'S, AND IT IS LABELLED AS SUCH. CODOL has NO think
    // budget at all: CG_PredictPlayerState 0x00464A90 runs one Pmove per pending
    // command with nothing counting them, and Pmove 0x0041DCD0's 1000 ms clamp
    // and 66 ms slice are its only backlog limits
    // (re/demo-re/30-codols-own-usercmd-numbers.md). Ours exists because native
    // world ownership lives only inside beginFrame/endFrame, so one client's
    // backlog must not starve later clients or the snapshot publish.
    //
    // ZERO is therefore the default: drain the whole pending queue. Work stays
    // bounded because PendingUserCmdCapacity is 32. OLMOD_SV_THINK_BUDGET_MS
    // can still impose a diagnostic budget for an A/B without a rebuild.
    [[nodiscard]] std::uint32_t SV_ClientThinkBudgetMilliseconds();
    [[nodiscard]] std::uint32_t SV_ChargeClientThinkTime(
        std::uint32_t cumulativeThinkTime,
        std::uint32_t commandTime,
        std::uint32_t playerCommandTime);

    // THE WORLD FRAME INTERVAL, AND WHY IT IS A KNOB.
    //
    // KisakCoD registers CoD4's own default: `sv_fps 20`, i.e. 50 ms
    // (src/server_mp/sv_init_mp.cpp). So 50 is the right generation default and
    // this returns it unless told otherwise.
    //
    // BUT 50 DOES NOT DIVIDE THIS HOST. out.exe drives the plugin from Com_Frame
    // at 30 Hz (section 97g measured hostGap 33.4 ms), and FixedFrameScheduler
    // runs AT MOST ONE world frame per callback. A 50 ms target therefore lands
    // on callbacks 2, 4, 5, 7, ... -- two frames per three callbacks, an average
    // of 20 Hz delivered at alternating 33/67 ms intervals. The average is a
    // perfect 50 and not one frame is at 50, which is section 97g's finding.
    //
    // MEASURED (re/demo-re/01-container.md, 54,682 retail snapshots): the real
    // server stepped serverTime by 100 ms in 97.4% of them -- 10 Hz, REGULAR.
    // 100 ms is exactly three host callbacks, which is presumably why.
    //
    // So OLMOD_SV_FRAME_MS=100 is not "a slower server", it is retail's own
    // cadence and the only one this host can deliver evenly. Clamped to
    // KisakCoD's own sv_fps limits, 10..1000 Hz expressed as 1..100 ms.
    // ROUNDS RUN 1..8 AND ROUND 9 IS THE FINAL. `ui_hud_round_goal` reads 8 in all five
    // retail zm demos across all three maps, and round 9 is announced in the same frame
    // as `ui_hud_final_round "1"` -- so the final round is goal + 1, not goal. The
    // 3.3.3.3 project guessed 16; the measurement is 8
    // (re/demo-re/15-zm-inventory.md sec.2).
    inline constexpr std::uint32_t SvZombieRoundGoal = 8;

    [[nodiscard]] std::uint32_t SV_FrameMilliseconds();

    class FixedFrameScheduler
    {
    public:
        explicit FixedFrameScheduler(std::uint32_t frameMilliseconds = 50);

        std::uint32_t advance(
            std::uint32_t nowMilliseconds,
            const std::function<void(std::uint32_t)> &runFrame);
        void reset();

    private:
        std::uint32_t frameMilliseconds_;
        std::uint32_t previousMilliseconds_{};
        std::uint32_t residualMilliseconds_{};
        bool initialized_{};
    };

    struct ServerStatus
    {
        bool enabled{};
        std::uint32_t frameNumber{};
        std::uint32_t serverTime{};
        std::uint32_t connectedClients{};
        std::uint32_t netchanPacketsReceived{};
        std::uint32_t netchanPacketsDropped{};
        std::uint32_t reliableCommandsReceived{};
        bool sessionConfigured{};
        bool gameStateConfigured{};
        std::uint32_t gameStateMessagesSent{};
        std::uint32_t clientsReadyForGameState{};
        std::uint32_t activeClients{};
        std::uint32_t gameStateUpdatesReceived{};
        std::uint32_t snapshotMessagesSent{};
        std::uint32_t fullSnapshotMessagesSent{};
        std::uint32_t deltaSnapshotMessagesSent{};
        std::uint32_t messageAcknowledge{};
        std::uint32_t outgoingSequence{};
        bool worldSpawnConfigured{};
        SvSnapshotFrameValidationFailure worldFrameValidationFailure{};
        std::uint64_t worldFrameRejections{};
    };

    struct SvServerFrameTimingStatus
    {
        SvTimingWindow total;
        SvTimingWindow prepare;
        SvTimingWindow beginWorld;
        SvTimingWindow clientThink;
        SvTimingWindow mode;
        SvTimingWindow endAndPublish;
        std::uint64_t clientThinkCommands{};
    };

    struct SvConnectionlessDiagnostics
    {
        std::uint32_t handled{};
        std::uint32_t connected{};
        std::uint32_t rejected{};
        PeerAddress lastConnectedPeer{};
        std::uint32_t lastConnectedClientSlot{ static_cast<std::uint32_t>(-1) };
        PeerAddress lastRejectedPeer{};
        std::string lastRejectedReason;
    };

    struct SvWorldWeaponSample
    {
        std::uint16_t currentWeaponAssetIndex{};
        std::int32_t weaponTime{};
        std::int32_t weaponDelay{};
        std::uint8_t weaponState{};
        std::uint16_t weaponAnim{};
        std::uint16_t clipAmmo{};
        std::uint8_t weaponType{};
        std::uint8_t fireType{};
        std::uint16_t definitionFireDelay{};
        std::uint16_t definitionFireTime{};
    };

    struct SvWorldPlayerSample
    {
        std::uint32_t frameNumber{};
        std::uint32_t serverTime{};
        std::optional<UserCmd> lastReceivedUserCmd;
        SvPlayerState playerState;
        std::optional<SvWorldWeaponSample> weapon;
    };

    struct SvOutboundPacket
    {
        PeerAddress peer{};
        std::vector<std::uint8_t> data;
    };

    enum class SvMatchEndReason
    {
        None,
        ScoreLimit,
        TimeLimit,
        WinLimit,
        RoundLimit,
        TeamEliminated,
    };

    enum class SvSdRoundEndReason
    {
        None,
        AttackersEliminated,
        DefendersEliminated,
        SimultaneousElimination,
        BombDefused,
        BombExploded,
        TimeLimit,
    };

    struct SvSdRoundStatus
    {
        bool configured{};
        bool armed{};
        bool completed{};
        std::uint32_t roundsPlayed{};
        SvTeam winner{SvTeam::None};
        SvSdRoundEndReason endReason{SvSdRoundEndReason::None};
        std::uint32_t startedServerTime{};
        std::uint32_t completedServerTime{};
    };

    struct SvSdEliminationState
    {
        std::uint32_t attackers{};
        std::uint32_t defenders{};
        std::uint32_t attackersAlive{};
        std::uint32_t defendersAlive{};
        bool bombPlanted{};
    };

    enum class SvSdBombPhase
    {
        Inactive,
        Available,
        Carried,
        Dropped,
        Planted,
        Defused,
        Exploded,
    };

    struct SvSdBombStatus
    {
        bool configured{};
        SvSdBombPhase phase{SvSdBombPhase::Inactive};
        std::vector<SvSdBombSite> sites;
        std::optional<std::string> plantedSiteLabel;
        std::optional<std::uint32_t> carrierClientNum;
        std::optional<std::uint32_t> planterClientNum;
        std::optional<std::uint32_t> defuserClientNum;
        std::optional<std::array<float, 3>> plantedOrigin;
        std::uint32_t phaseStartServerTime{};
        std::uint32_t plantedServerTime{};
    };

    struct SvSdBombRules
    {
        // TODO(CODOL): Replace or confirm these IW4/Ghosts shared defaults
        // when CODOL's server-side match-rules asset is recovered.
        std::uint32_t plantMilliseconds{ 5000 };
        std::uint32_t defuseMilliseconds{ 5000 };
        std::uint32_t bombMilliseconds{ 45000 };

        bool operator==(const SvSdBombRules &) const = default;
    };

    struct SvSdRuntimeStatus
    {
        SvSdRoundStatus round;
        SvSdBombStatus bomb;
        SvSdEliminationState teams;
    };

    struct SvGameplayPresentationClientStatus
    {
        std::uint32_t clientNum{};
        ClientGameplayState gameplayState{ ClientGameplayState::Inactive };
        SvTeam team{ SvTeam::None };
        ServerReliableCommandStatus reliable;
        std::uint32_t pendingUserCmdCount{};
        std::optional<std::uint32_t> oldestPendingUserCmdTime;
        std::optional<std::uint32_t> newestPendingUserCmdTime;
        std::optional<std::uint32_t> lastReceivedUserCmdTime;
        std::optional<std::uint32_t> lastDispatchedUserCmdTime;
        std::optional<std::uint32_t> lastExecutedUserCmdTime;
        std::optional<std::uint32_t> lastDiscardedUserCmdTime;
        std::uint32_t discardedUnsupportedUserCmds{};
        std::uint32_t snapshotPlayerEntityMask{};
        std::uint32_t snapshotClientInfoMask{};
        std::array<SvObjective, 3> objectives{};
    };

    struct SvGameplayPresentationStatus
    {
        std::uint32_t serverTime{};
        SvSdRuntimeStatus sd;
        std::vector<SvGameplayPresentationClientStatus> clients;
    };

    struct SvSdTeamSoundPresentation
    {
        std::uint16_t searchDestroy{};
        std::uint16_t objectiveDestroy{};
        std::uint16_t objectiveDefend{};
        std::uint16_t bombTaken{};
        std::uint16_t bombLost{};
        std::uint16_t bombPlanted{};
        std::uint16_t bombDefused{};
        std::uint16_t lastAlive{};
        std::uint16_t roundWon{};
        std::uint16_t roundLost{};
        std::uint16_t matchWon{};
        std::uint16_t matchLost{};
        std::uint16_t draw{};
        std::uint16_t sideSwitch{};

        bool operator==(const SvSdTeamSoundPresentation &) const = default;
    };

    struct SvSdSoundPresentation
    {
        std::uint16_t objectiveLost{};
        std::uint16_t objectiveTaken{};
        SvSdTeamSoundPresentation tf;
        SvSdTeamSoundPresentation sc;

        bool operator==(const SvSdSoundPresentation &) const = default;
    };

    [[nodiscard]] std::array<SvObjective, 32> SV_BuildSdObjectives(
        std::span<const SvSdBombSite> sites,
        SvTeam viewerTeam,
        const SvSdObjectiveMaterials &materials,
        bool visible);
    [[nodiscard]] std::array<SvObjective, 32> SV_BuildSdPlantedObjectives(
        std::string_view siteLabel,
        const std::array<float, 3> &origin,
        SvTeam viewerTeam,
        const SvSdObjectiveMaterials &materials,
        bool visible);
    [[nodiscard]] bool SV_AddSdBombObjective(
        std::array<SvObjective, 32> &objectives,
        SvSdBombPhase phase,
        const std::array<float, 3> &origin,
        SvTeam viewerTeam,
        const SvSdObjectiveMaterials &materials,
        bool visible);
    [[nodiscard]] std::array<SvHudElem, 31> SV_BuildObjectiveHudElems(
        const std::array<SvObjective, 32> &objectives);

    // IW4 _damagefeedback.gsc sizes the hit marker with
    // setShader("damage_feedback", 24, 48); BO1 maps/_damagefeedback.gsc uses
    // the same pair. Both are virtual 640x480 units that the client scales.
    constexpr std::uint16_t SvDamageFeedbackWidth = 24;
    constexpr std::uint16_t SvDamageFeedbackHeight = 48;
    // CODREF(demo): the numbers below are no longer ported from IW's scripts -
    // they are read off a RETAIL CODOL server's own hudElem traffic, mined out
    // of C-2021-7-25[1-19-26]dm.demo. Two complete elements decode there:
    //
    //   x=-12 y=-12 w=24 h=48 align=0x22 target=2047
    //         color=alpha0  fromColor=alpha31  fadeTime=1000     <- hit marker
    //   type=2 y=-50 value=50 align=0x22 alignOrg=5 label=397
    //         fontScale=0.9 fromFontScale=3.0 scaleTime=200
    //         color=alpha0  fromColor=alpha27  fadeTime=750      <- score popup
    //
    // The marker's -12/-12 offsets and 24x48 size match what was already
    // derived from IW4's script, so the retail server and the IW script agree
    // and this is a confirmation rather than a correction.
    //
    // Retail lets the CLIENT animate both elems: the colour lerp in
    // sub_AB4490 and the scale lerp in sub_BB4B70 run from the "from" value to
    // the plain one across their own window. So the server publishes the whole
    // animation once and simply holds the elem until it has played out.
    constexpr std::uint32_t SvDamageFeedbackDurationMilliseconds = 1000;
    // THE PODIUM FIGURE'S BASE MODEL, MEASURED. All three of the retail dm
    // demo's figures carry modelIndex 121, and 121 in this build's model index
    // space is `tag_origin` -- an EMPTY model. The character comes from field 49
    // (podiumClient) and that client's clientInfo, not from the base.
    constexpr std::string_view PodiumBaseModelName = "tag_origin";
    // MEASURED (retail dm): outcomeNotify appears 1100 ms after the match is
    // decided and reset_outcome destroys it at +11100, for a ten-second life.
    inline constexpr std::uint32_t SvDmOutcomeDelayMilliseconds = 1'100;
    inline constexpr std::uint32_t SvDmOutcomeDurationMilliseconds = 10'000;
    // These are the OLfinal localized-string indexes carried by the four
    // outcome rows, verified against the NCS names and the decoded HudElems.
    inline constexpr std::uint16_t SvDmMatchBonusLabel = 365;
    inline constexpr std::array<std::uint16_t, 3> SvDmPlacementLabels{
        339, 416, 434 };
    // Hudelem field 22 uses the localized constant-string number rather than
    // field 33's adjacent-value label. Victory and time-limit are present in
    // the captured FFA outcome. Defeat and score-limit are the same OLfinal
    // list entries used by the shipped GSC and keep the measured list base.
    inline constexpr std::uint16_t SvDmDefeatText = 326;
    inline constexpr std::uint16_t SvDmTieText = 367;
    inline constexpr std::uint16_t SvDmScoreLimitText = 413;
    inline constexpr std::uint16_t SvDmTimeLimitText = 435;
    inline constexpr std::uint16_t SvDmVictoryText = 442;
    [[nodiscard]] std::uint32_t SV_CalculateDmMatchBonus(
        std::uint16_t zeroBasedRank,
        std::uint32_t participationMilliseconds,
        bool placedTopThree);
    [[nodiscard]] bool SV_IsDmOutcomeTie(
        std::uint32_t viewerClientNum,
        std::span<const std::uint32_t> rankedClientNums,
        std::span<const SvClientScore> rankedScores);
    [[nodiscard]] std::array<SvHudElem, 31> SV_BuildDmOutcomeHudElems(
        std::span<const std::uint32_t> rankedClientNums,
        std::optional<float> matchBonus,
        std::uint32_t birthServerTime,
        std::uint16_t titleText,
        std::uint16_t reasonText);
    constexpr std::uint16_t SvDamageFeedbackFadeMilliseconds = 1000;
    // CoD4 and IW4 both award 100 for a kill in their shipped _rank.gsc, which is
    // what the team modes use.
    constexpr float SvScoreFeedbackKillPoints = 100.0f;
    // Free-for-all awards 50, and that is MEASURED rather than inherited. An
    // earlier note here read the demo's 50 as "that server's own award for
    // whatever event it recorded" and kept IW's 100; two independent places in
    // the same demo say otherwise. The server sets `ui_DMKillScore "50"` at
    // serverTime 0, and the score popup's own value field reads 50 - and
    // ui_DMKillScore appears in no cha, war or dom demo, so it is dm's.
    constexpr float SvDmScoreFeedbackKillPoints = 50.0f;
    constexpr float SvScoreFeedbackOffsetY = -50.0f;
    // The popup scales, and both durations below are retail's, read off one
    // elem followed through its whole life:
    //
    //   t+0     fontScale 3.0, fromFontScale 0.9, scaleTime 100   grow
    //   t+100   fromFontScale 3.0                 scaleTime 200   flat at 3.0
    //   t+300   fontScale 0.9, fromFontScale 3.0, scaleTime 172   settle
    //   t+1000  colour alpha 27 -> 0              fadeTime  750   fade
    //
    // The two scale windows there do NOT meet. The third update reuses the
    // second window's start time, so by the time it is sent its window has
    // already elapsed - the number holds flat at 3.0 and then jumps. Copying
    // that literally is what made this look choppy.
    //
    // So the flat middle is dropped and the shrink window is started exactly
    // where the grow window ends. Both durations stay retail's; the change is
    // only that the windows now ABUT, which makes the scale continuous:
    // sub_BB4B70 finishes the grow lerp at 3.0 and begins the settle lerp at
    // 3.0 in the same instant. The server frame is 50ms and the grow is 100ms,
    // so the boundary lands on a frame exactly and no jump is possible.
    constexpr float SvScoreFeedbackSmallScale = 0.9f;
    constexpr float SvScoreFeedbackLargeScale = 3.0f;
    constexpr std::uint16_t SvScoreFeedbackGrowMilliseconds = 100;
    constexpr std::uint16_t SvScoreFeedbackSettleMilliseconds = 172;
    constexpr std::uint32_t SvScoreFeedbackVisibleMilliseconds = 1000;
    constexpr std::uint16_t SvScoreFeedbackFadeMilliseconds = 750;
    constexpr std::uint32_t SvScoreFeedbackDurationMilliseconds =
        SvScoreFeedbackVisibleMilliseconds + SvScoreFeedbackFadeMilliseconds;
    // Descriptor 21 is the qsort key in sub_BB5F60, so this draws above the
    // rest of the HUD. Retail gives its popup exactly 10000.
    constexpr float SvScoreFeedbackSort = 10000.0f;
    // The "+" in "+50". IW4's _rank.gsc labels its score popup with &"MP_PLUS".
    //
    // THIS WAS 524 AND THE REASONING FOR IT WAS EXACTLY BACKWARDS. The old
    // comment read: "it is a per-build index - the retail demo's own label 397
    // belongs to OLfinal's table and would print whatever happens to sit at 397
    // here, so it was NOT copied", and took 524 from a live 3.3.3.3 client's
    // localized configstrings instead.
    //
    // Both halves of that are right except for which build "here" is. Section
    // 109 establishes that the demo IS this build: four configstring indices
    // match out.exe's own (2557..2562, 2452+clientNum, 15, 464), all sixteen of
    // its precache names are present verbatim in this install's zones, and its
    // SVC_EOF is 5 rather than 3.3.3.3's 6. So 397 is OLfinal's index used on
    // an OLfinal client, and 524 was 3.3.3.3's index used on an OLfinal client
    // - the very mistake the comment set out to avoid, committed in the other
    // direction.
    //
    // MEASURED: label=397 on the score popup, six times, in the same element
    // that carries value=50 and y=-50.
    constexpr std::uint16_t SvScoreFeedbackLabel = 397;
    // The -85 codec carries alpha in five bits, so a retail alpha of 27 is
    // 27 * 8 on the wire. Both feedback elems fade to fully transparent.
    //
    // The demo's shared -85 decoder discards RGB and returns only that alpha,
    // which is why the colours looked like bare numbers at first. Decoding the
    // three colour bytes as well shows the marker is white but the SCORE POPUP
    // IS NOT: retail writes the bytes 0x29, 0xA6, 0xFF for it, on all three of
    // its colour fields.
    //
    // writeHudColor emits value&0xFF, then >>8, then >>16, so those wire bytes
    // come from 0x__FFA629. Reproducing the byte ORDER is the whole job here -
    // which byte the renderer treats as red is not something this has to
    // decide, and guessing at it would be how the colour comes out inverted.
    constexpr std::uint32_t SvFeedbackFadeToColor = 0x00FFFFFFu;
    constexpr std::uint32_t SvDamageFeedbackFromColor = 0xFFFFFFFFu;
    constexpr std::uint32_t SvScoreFeedbackFromColor = 0xD8FFA629u;
    constexpr std::uint32_t SvScoreFeedbackFadeToColor = 0x00FFA629u;
    constexpr std::uint32_t SvScoreFeedbackGlowColor = 0x00FFA629u;

    // OLMOD(factory-entry): adapter clock starts at the first Playing snapshot.
    // Native recorded offsets/layout are documented in factory-entry-20260923.md.
    [[nodiscard]] std::array<SvHudElem, 4> SV_BuildFactoryEntryHud(
        std::uint32_t birth, std::uint32_t serverTime);

    [[nodiscard]] SvHudElem SV_BuildZmScoreHudElem(
        std::optional<SvZmScoreFeedback> score, std::uint32_t serverTime);

    // Both feedback elems in one contiguous prefix. The client's collector
    // sub_BB5FB0 walks each array and stops at the first type 0, so a gap
    // would hide everything after it.
    [[nodiscard]] std::array<SvHudElem, 31> SV_BuildFeedbackHudElems(
        std::uint16_t markerMaterialIndex,
        std::uint32_t markerStartTime,
        std::optional<float> scorePopupValue,
        std::uint32_t scoreStartTime,
        std::uint32_t serverTime);

    struct SvTriggerVolume
    {
        std::uint32_t objectId{};
        std::array<float, 3> origin{};
        std::array<float, 3> angles{};
        SvBrushModelCollision collision;

        bool operator==(const SvTriggerVolume &) const = default;
    };

    struct SvSdBombSiteRuntime
    {
        std::string label;
        SvTriggerVolume plantTrigger;
        SvTriggerVolume defuseTrigger;

        bool operator==(const SvSdBombSiteRuntime &) const = default;
    };

    using SvTriggerContactRunner = std::function<std::optional<bool>(
        const std::array<float, 3> &playerOrigin,
        const TraceBounds &playerBounds,
        const SvTriggerVolume &trigger)>;

    [[nodiscard]] bool SV_BeginSdBombRound(
        SvSdBombStatus &status,
        std::uint32_t serverTime);
    [[nodiscard]] bool SV_PickUpSdBomb(
        SvSdBombStatus &status,
        std::uint32_t carrierClientNum,
        std::uint32_t serverTime);
    [[nodiscard]] bool SV_DropSdBomb(
        SvSdBombStatus &status,
        std::uint32_t carrierClientNum,
        std::uint32_t serverTime);
    [[nodiscard]] bool SV_CommitSdBombPlant(
        SvSdBombStatus &status,
        std::uint32_t planterClientNum,
        std::string_view siteLabel,
        const std::array<float, 3> &plantedOrigin,
        std::uint32_t serverTime);
    [[nodiscard]] bool SV_CommitSdBombDefuse(
        SvSdBombStatus &status,
        std::uint32_t defuserClientNum,
        std::uint32_t serverTime);
    [[nodiscard]] bool SV_AdvanceSdBombTimer(
        SvSdBombStatus &status,
        const SvSdBombRules &rules,
        std::uint32_t serverTime);
    [[nodiscard]] std::optional<std::pair<SvTeam, SvSdRoundEndReason>>
        SV_EvaluateSdBombOutcome(SvSdBombPhase phase);

    [[nodiscard]] std::optional<std::pair<SvTeam, SvSdRoundEndReason>>
        SV_EvaluateSdElimination(const SvSdEliminationState &state);
    [[nodiscard]] std::optional<std::pair<SvTeam, SvSdRoundEndReason>>
        SV_EvaluateSdTimeLimit(
            const SvSdEliminationState &state,
            std::uint32_t startedServerTime,
            std::uint32_t currentServerTime,
            std::uint32_t timeLimitMinutes);
    [[nodiscard]] std::optional<std::pair<SvTeam, SvSdRoundEndReason>>
        SV_EvaluateSdRoundOutcome(
            SvSdBombPhase bombPhase,
            const SvSdEliminationState &state,
            std::uint32_t startedServerTime,
            std::uint32_t currentServerTime,
            std::uint32_t timeLimitMinutes);

    struct SvMatchStatus
    {
        bool configured{};
        bool completed{};
        SvMatchEndReason endReason{SvMatchEndReason::None};
        SvTeam winner{SvTeam::None};
        // Free-for-all has no winning TEAM - every player is teamless - so the
        // outcome is a slot instead. Set only by the teamless modes; the team
        // modes leave it empty and keep reporting `winner`.
        std::optional<std::uint32_t> winnerClientNum;
        std::uint32_t startServerTime{};
        std::uint32_t elapsedMilliseconds{};
        OlMod::DedicatedSession::MatchRules rules;
    };

    [[nodiscard]] bool SV_UpdateMatchTimeLimit(
        SvMatchStatus &status,
        std::string_view gameType,
        std::uint32_t currentServerTime,
        std::int32_t tfScore,
        std::int32_t scScore);

    // THE ANNOUNCER SCHEDULE. What retail's dm server said, and when it said
    // it - the constants and their measurements are in sv_gamestate_mp.hpp.
    // Kept as a free function over its own state so the schedule can be tested
    // without a live match, which is the only part of this that a test can
    // reach: whether a client hears it is the player's to report.
    struct SvAnnouncerState
    {
        bool matchStartSent{};
        bool timesUpSent{};
        // The slot that is currently top of the board. Empty until somebody has
        // actually scored - at 0-0 every player is "leading" and announcing it
        // would fire on the first frame of every match.
        std::optional<std::uint32_t> leader;
        std::optional<std::uint32_t> lastLeadChangeServerTime;
    };

    struct SvAnnouncerCues
    {
        bool matchStart{};
        bool timesUp{};

        [[nodiscard]] bool any() const { return matchStart || timesUp; }
    };

    // One client's dialog state: what is waiting to be spoken, and when the
    // next line may be. `status` is Black Ops' group coalescing - a newer
    // lead-change line REPLACES a pending one rather than queueing behind it,
    // so nobody ever hears "you're winning" chased by "you're losing".
    struct SvAnnouncerClientDialog
    {
        std::deque<std::uint16_t> queue;
        std::optional<std::size_t> statusSlot;
        std::uint32_t nextPlayServerTime{};
    };

    // THE ANNOUNCER IS A QUEUE, NOT A SCHEDULE, AND BLACK OPS' OWN SOURCE SAYS SO.
    //
    // CODREF: Black Ops mod tools, raw/maps/mp/gametypes/_globallogic_audio.gsc
    // `playLeaderDialogOnPlayer` -- play the sound, then `wait ( 3.0 )` before
    // the next line for that player, with `leaderDialogQueue` holding the rest.
    // So NO announcer line ever lands within 3 s of another on one client, and
    // a second line does not overwrite the first, it follows it.
    //
    // THIS DISSOLVES A CONSTANT THAT WAS WRITTEN DOWN AS UNEXPLAINED. The demo's
    // `on_your_own` follows the match-start line by 3.0 s in demo 1 and 12.5 s
    // in demo 2, which was recorded here as "not a fixed offset, whatever
    // selects it is something else". It is not a delay at all: both are queued
    // at spawn and the queue drains at 3 s. Demo 2's gap is a longer queue.
    // A SCHEDULE WAS THE WRONG MODEL and it produced a constant with no meaning.
    constexpr std::uint32_t SvAnnouncerDialogSpacingMs = 3'000;
    // `timesUp` is exact: 30.0 s remaining, to the frame (dm demo 1).
    constexpr std::uint32_t SvAnnouncerTimesUpRemainingMs = 30'000;
    // CODREF: _globallogic_score.gsc `onTeamScore` --
    //     `getTime() - level.lastStatusTime > 5000`
    // one shared floor across the match, exactly this shape, and SIX TIMES
    // SHORTER than the 30 s invented here before the source was read.
    //
    // WHAT IT IS NOT EVIDENCE FOR: that block is the TEAM path, and lead_taken /
    // lead_lost appear nowhere else in Black Ops - it has no free-for-all lead
    // callout at all. CODOL added one (both dm demos carry it), so CODOL's own
    // floor is unmeasured. 5000 is the same engine family's number rather than
    // this project's guess, which is the whole improvement.
    constexpr std::uint32_t SvAnnouncerLeadChangeCooldownMs = 5'000;

    [[nodiscard]] SvAnnouncerCues SV_UpdateMatchAnnouncer(
        SvAnnouncerState &state,
        std::string_view gameType,
        const SvMatchStatus &status,
        std::uint32_t currentServerTime);

    class ServerCore
    {
    public:
        using LoadoutProvider = SvClientSystem::LoadoutProvider;
        using RewardLoadoutProvider = std::function<std::optional<SvResolvedRewards>(std::uint64_t)>;
        using PerkLoadoutProvider = std::function<std::optional<SvResolvedPerks>(
            std::uint64_t, std::string_view)>;
        using EquipmentLoadoutProvider = std::function<std::optional<SvResolvedEquipment>(
            std::uint64_t, std::string_view)>;
        using CharacterCustomizationProvider = std::function<
            std::optional<SvCharacterCustomization>(
                std::uint32_t clientNum,
                std::uint64_t xuid,
                SvCharacterFaction faction)>;

        explicit ServerCore(
            SvClientSystem::GameStateBuilder gameStateBuilder = {},
            SvClientSystem::SnapshotBuilder snapshotBuilder = {},
            SvScriptBuiltinRegistry::ModelResolver modelResolver = {},
            SvScriptBuiltinRegistry::WeaponResolver weaponResolver = {},
            SvScriptBuiltinRegistry::SoundResolver soundResolver = {});

        // THE PARSED zm ZONE MODEL, handed in at world spawn and read by the zm
        // script builtins. Empty on a non-zm map or when the parse failed.
        // re/demo-re/21-zm-zones-and-spawners.md.
        void setZmZones(std::vector<SvZmZone> zones);
        [[nodiscard]] std::vector<SvZmZone> zmZones() const;
        [[nodiscard]] std::size_t zmBarrierCount() const;

        // THE MEASURED zm NAVIGATION GRAPH, handed in at world spawn beside the
        // zones. An empty graph is legitimate and normal -- the actors then park on
        // their spawners. re/demo-re/20-zm-actor-lifecycle.md 12.57 / 12.58.
        void setZmNavGraph(SvZmNavGraph graph);
        // SvActorWalkAnimName as this engine's own index, or 0 when it did not
        // resolve -- in which case actors keep SvActorAnimIndex rather than the
        // T-pose a zero index guarantees.
        void setZmActorWalkAnim(std::uint16_t animIndex);
        void setZmActorTearAnim(std::uint16_t animIndex);
        void setZmTearClips(const SvZmTearClips &clips);
        void setZmBoardTrajectoryEvaluator(SvTrajectoryEvaluator evaluate);
        void setZmPresentation(std::span<const SvZmOutfit> outfits,
            std::span<const SvZmDeathClip> deaths, SvZmDeathFx fx = {});
        void setFactoryBoxResources(SvFactoryBoxResources resources);
        void setFactoryTeleporterResources(SvFactoryTeleporterResources resources) {
            const std::lock_guard lock(mutex_);
            resources.clockFace=factoryClockMaterials_[0];
            resources.clockGlass=factoryClockMaterials_[1];
            factoryTeleporterResources_=resources;
        }
        void setFactorySpecialWeapons(std::map<std::uint16_t,SvFactorySpecialKind> weapons,
            std::map<std::uint16_t,SvFactorySpecialCombat> combat = {}, SvFactoryTrapFx fx = {}) {
            const std::lock_guard lock(mutex_);
            world_.setFactorySpecialWeapons(std::move(weapons),std::move(combat),fx);
        }
        // Like playerEquipment: synchronous client-event callback already owns
        // this core's mutex; do not recursively acquire it from the callback.
        [[nodiscard]] std::optional<SvFactorySpecialKind> factorySpecialWeapon(std::uint16_t asset) const {
            return world_.factorySpecialWeapon(asset);
        }
        void setFactoryArrivalFx(std::uint16_t model,
            std::array<std::uint16_t,3> effects, std::uint8_t bone);
        void setZmActorDeathAnim(std::uint16_t animIndex);
        void setZmActorAttackAnim(std::uint16_t animIndex);
        // The parsed barriers, resolved to nav-graph edges by the world.
        void setZmBarriers(std::span<const SvZmBarrier> barriers);

        void setEnabled(bool enabled);
        [[nodiscard]] std::vector<SvOutboundPacket> onComFrame(
            std::uint32_t nowMilliseconds);
        ConnectionlessResult SV_ConnectionlessPacket(
            PeerAddress peer,
            std::span<const std::uint8_t> packet,
            std::uint32_t nowMilliseconds,
            std::uint32_t entropy);
        DtlsPacketResult NET_DtlsPacket(
            PeerAddress peer,
            std::span<const std::uint8_t> packet,
            std::uint32_t nowMilliseconds,
            std::uint32_t entropy);
        bool configureSessionDescriptor(std::span<const std::uint8_t> descriptor);
        // AUDITION one announcer line to every Active client, returning how many
        // it reached. The COUNT is the point: a diagnostic that logged "sent"
        // while nobody was active would read exactly like a clip that plays
        // nothing, and this whole exercise exists because a name is not a sound.
        // THE VOICE GENDER, PUSHED IN FROM OUTSIDE. A side map and not a
        // field on SvCharacterCustomization: that struct is embedded in the
        // address-keyed WorldClientState and its size is pinned by a
        // static_assert whose comment records that growing it once broke the
        // death animation. A sound is not worth that.
        void setBattleChatterVoiceFemale(std::uint32_t clientNum, bool female);
        // Replay one raw reliable command to every Active client; returns how
        // many it reached. Binary when the first byte is not printable ASCII,
        // text otherwise -- the two channels have different dispatchers in the
        // client and `@`/`J`/`K` are binary.
        [[nodiscard]] std::uint32_t sendRawCommand(
            std::span<const std::uint8_t> payload);
        // Request a native client transition; success means reliably queued,
        // not that pmove has committed the selected weapon.
        [[nodiscard]] bool selectPlayerWeapon(std::uint32_t clientNum,
            std::uint16_t weaponAssetIndex);
        [[nodiscard]] std::uint32_t playAnnouncerLine(
            std::uint16_t announcerParameter);
        [[nodiscard]] bool stageSessionRoster(
            std::uint64_t generation,
            std::span<const SessionRosterMember> members);
        [[nodiscard]] bool commitSessionRoster(std::uint64_t generation);
        [[nodiscard]] bool rollbackSessionRoster(std::uint64_t generation);
        bool configureGameState(
            SvGameState gameState,
            std::uint64_t sessionGeneration = 0);
        // Append a modular weapon into the live gamestate's dynamic block and
        // broadcast its config string to connected clients (the retail seamless
        // path), no world rebuild. Forwards to SvClientSystem under the server
        // lock. See §161a and [[codol-181-is-weapon-index-vs-slot]].
        [[nodiscard]] std::optional<std::uint16_t> registerDynamicWeaponConfigString(
            SvModularWeaponConfigString configString,
            std::uint16_t firstDynamicWeaponAssetIndex,
            const SvClientSystem::WeaponConfigStringCommandBuilder &buildCommand);
        bool configureMatchRules(
            OlMod::DedicatedSession::MatchRules rules,
            std::string_view gameType);
        bool configureSdBombRuntime(
            std::span<const SvSdBombSite> sites,
            SvTriggerVolume pickupTrigger,
            std::span<const SvSdBombSiteRuntime> siteRuntime);
        bool configureSdBombPresentation(
            const SvScriptModelEntityDefinition &visualDefinition,
            std::uint16_t presentationModelIndex,
            std::string_view presentationModelName);
        bool configureSdSoundPresentation(SvSdSoundPresentation presentation);
        bool configureWorldSpawn(
            std::array<float, 3> origin,
            std::array<float, 3> angles,
            std::span<const SvBrushModelEntityDefinition> brushModels = {},
            std::span<const SvScriptModelEntityDefinition> scriptModels = {},
            std::span<const SvScriptModelDamageOwnerDefinition>
                scriptModelDamageOwners = {});
        // Diagnostic passthrough: how many script models the last world spawn put on
        // retail's own entity numbers. See sv_const_baselines_mp.hpp.
        [[nodiscard]] std::size_t constBaselineScriptModelCount() const;
        bool configureWorldSpawn(
            std::span<const SvWorldSpawnPoint> spawnPoints,
            std::span<const SvBrushModelEntityDefinition> brushModels = {},
            std::span<const SvScriptModelEntityDefinition> scriptModels = {},
            std::span<const SvScriptModelDamageOwnerDefinition>
                scriptModelDamageOwners = {},
            std::optional<SvWorldSpawnPoint> waitingForLoadoutPoint = std::nullopt,
            // Selects the map's shipped const-baseline table so brush models are
            // published on retail's entity numbers. See sv_const_baselines_mp.hpp.
            std::string_view mapName = {},
            // The table is keyed on (map, gametype); an MP map ships one per
            // gametype and the entity numbering differs between them.
            std::string_view gameType = {},
            std::span<const SvLogicalMapEntityDefinition>
                logicalMapEntities = {});
        // Set at map load from the map's own entities; empty on a map that
        // ships no `top_players_camera`, which is not an error.
        void setTopPlayersCamera(std::optional<SvWorldSpawnPoint> camera);
        void setTopPlayersPlaces(std::vector<SvWorldSpawnPoint> places);
        // A generic body from this map's own model band, for a podium figure
        // whose own body model the band does not publish.
        void setPodiumFallbackModel(std::uint16_t index, std::string name);
        // OUTFIT MODELS THE MAP DOES NOT PUBLISH. The map's own band is what
        // resolveModelConfigStringIndex can answer from; anything else has to be given
        // a slot and broadcast before a clientInfo attachment can name it.
        // `|` precache a player's character models to every client, once per
        // character. Without it a client can hold a valid characterInfo naming a model
        // it has never loaded, and the player draws as nothing.
        void precacheCharacterModels(
            std::uint32_t clientNum, std::uint16_t characterItemId);
        void setOutfitModelSlots(std::vector<std::uint16_t> freeSlots);
        [[nodiscard]] std::optional<std::uint16_t>
            registerOutfitModelConfigString(const std::string &name);

        // PUBLISH AN ACTOR MODEL TO THE CLIENTS AT THE INDEX THE DEDICATED ALREADY
        // RESOLVED. resolveModelConfigStringIndex scans the DEDICATED's own band and
        // returns the index it finds there; nothing sends that configstring to the
        // clients, so the client band stays EMPTY at that index. sub_514880 then
        // resolves the agent element's model to "", sub_530C90 leaves record+568
        // empty, and sub_52FBE0 takes its `!*(BYTE *)(v3 + 568)` early-out and builds
        // no DObj at all -- measured, re/demo-re/20-zm-actor-lifecycle.md 12.21.
        // Idempotent per name.
        bool publishActorModelConfigString(
            std::uint16_t index, const std::string &name);
        void spawnPodiumFigures();
        bool configureGlassMap(
            SvGlassMapMetadata metadata,
            SvGlassDamageThresholds thresholds);
        void setSharedPmoveRunner(SvSharedPmoveRunner runner);
        void setWeaponMovementRunner(SvWeaponMovementRunner runner);
        void setPlayerStateToEntityStateConverter(
            SvPlayerStateToEntityStateConverter converter);
        void setDeathAnimationRunner(SvDeathAnimationRunner runner);
        void requestAltWeaponToggle(std::uint32_t clientNum);
        void setSpawnAnimationRunner(SvSpawnAnimationRunner runner);
        void setClientEventsHandler(SvClientEventsHandler handler);
        // SECTION 190: weapon -> its alt, for the alt-fire switch in
        // clientThinkReal. Forwarded to the world like every other handler.
        void setAltFireResolver(SvServerWorld::SvAltFireResolver resolver);
        void setPointTraceRunner(SvPointTraceRunner runner);
        void setRadiusDamageVisibilityRunner(SvRadiusDamageVisibilityRunner runner);
        void setCapsuleTraceRunner(SvCapsuleTraceRunner runner);
        void setTriggerContactRunner(SvTriggerContactRunner runner);
        void setNativeEntityMirrorSynchronizer(
            SvNativeEntityMirrorSynchronizer synchronizer);
        [[nodiscard]] bool sharedPmoveAvailable() const;
        void setLoadoutProvider(LoadoutProvider provider);
        void setPerkLoadoutProvider(PerkLoadoutProvider provider);
        void setRewardLoadoutProvider(RewardLoadoutProvider provider);
        void setUavWeaponProvider(std::function<std::optional<SvRewardWeapon>()> provider);
        // FFA production policy. Zero disables; the duration is reference
        // policy until a complete CODOL capture exposes a natural expiry.
        [[nodiscard]] bool configureUavRadar(std::uint32_t durationMilliseconds);
        // Explicit cross-mode/test override and optional one-time free reward.
        [[nodiscard]] bool configureUavRadarTest(std::uint32_t durationMilliseconds,
            bool grantOneTestReward = false);
        void setUavDiagnosticGrant(bool enabled);
        void setEquipmentLoadoutProvider(EquipmentLoadoutProvider provider);
        [[nodiscard]] const SvResolvedEquipment *playerEquipment(
            std::uint32_t clientNum, std::uint8_t spawnGeneration) const
        {
            return world_.playerEquipment(clientNum, spawnGeneration);
        }
        void setCharacterCustomizationProvider(
            CharacterCustomizationProvider provider);
        // The component-model names one client's character resolves to. Used
        // ONLY by the match-end `|` precache burst; the DObj build has its own
        // path to the same strings and does not go through here.
        using CharacterModelNamesProvider =
            std::function<std::vector<std::string>(std::uint32_t clientNum)>;
        void setCharacterModelNamesProvider(
            CharacterModelNamesProvider provider);
        using ScriptAnimationResolver = std::function<std::optional<std::uint16_t>(std::string_view)>;
        void setScriptAnimationResolver(ScriptAnimationResolver resolver);
        // THE OUTFIT SELECTION MASK, netfields 21..32. A SEPARATE PROVIDER AND NOT A
        // FIELD ON SvCharacterCustomization, because that struct is held by value in
        // the unordered_map node that also holds the address-keyed native playerState:
        // forty-eight bytes there cost every death its animation. Section 184h.
        using CharacterOptionMaskProvider =
            std::function<std::array<std::uint32_t, 12>(std::uint32_t clientNum)>;
        void setCharacterOptionMaskProvider(
            CharacterOptionMaskProvider provider);
        [[nodiscard]] bool loadGameplayScript(
            std::string_view sourceName,
            std::string_view source);
        void unloadGameplayScript();
        [[nodiscard]] SvLuaRuntimeStatus gameplayScriptStatus() const;
        [[nodiscard]] std::vector<SvLuaLogEntry> takeGameplayScriptLogs();
        [[nodiscard]] ServerStatus status() const;
        [[nodiscard]] SvServerFrameTimingStatus takeFrameTimingStatus();
        [[nodiscard]] SvConnectionlessDiagnostics connectionlessDiagnostics() const;
        [[nodiscard]] SvMatchStatus matchStatus() const;
        [[nodiscard]] SvSdRoundStatus sdRoundStatus() const;
        [[nodiscard]] SvSdBombStatus sdBombStatus() const;
        [[nodiscard]] SvSdRuntimeStatus sdRuntimeStatus() const;
        [[nodiscard]] SvGameplayPresentationStatus
            gameplayPresentationStatus() const;
        [[nodiscard]] std::optional<ClientIngressStatus> clientIngressStatus(
            std::uint32_t clientNum) const;
        [[nodiscard]] std::vector<SvClientSystem::TimeoutDrop>
            takeTimeoutDrops();
        // NOCLIP, ADDRESSED BY WHOEVER SENT THE REQUEST.
        //
        // **THE SENDER CANNOT NAME ITSELF BY XUID AND THIS IS MEASURED, NOT
        // ASSUMED.** The client plugin knows OLMOD_PLATFORM_USER_ID
        // (0x01100001DEADC0DE) and the server knows the xuid out.exe put in its
        // connect string, which is the C# AuthServer's sequentially issued
        // account id -- a live match ran with xuid=69420 and xuid=69422 against
        // platform ids ...C0DE and ...C0DF. They are different numbers and
        // nothing in either process holds both.
        //
        // So resolution is BY PEER ADDRESS, which both halves do share: a
        // control request and that client's game connection arrive from the
        // same machine. It is exact for every remote player, and ambiguous only
        // between clients CO-LOCATED with each other -- the host's own second
        // test client -- where it takes the lowest Active slot and says so.
        // `xuid` is honoured when non-zero so a tool can address a slot
        // exactly; pass 0 to resolve by address.
        //
        // Safe to call from the control thread: ServerCore's mutex is the same
        // one the frame takes.
        struct NoclipResolution
        {
            std::uint32_t clientNum{};
            std::uint64_t xuid{};
            bool ambiguous{};
        };
        // OLMOD(debug_battery): explicit local slot; legacy empty requests are solo-only.
        [[nodiscard]] bool debugGrantFactoryBattery(std::uint32_t senderIpv4,
            std::optional<std::uint32_t> targetClient = std::nullopt);
        [[nodiscard]] std::optional<NoclipResolution> setPlayerNoclipForSender(
            std::uint64_t xuid,
            std::uint32_t senderIpv4,
            bool enabled,
            std::uint32_t holdMilliseconds);
        [[nodiscard]] std::optional<SvPlayerState> worldPlayerState(
            std::uint32_t clientNum) const;
        [[nodiscard]] std::optional<SvGameEntity> worldPlayerEntity(
            std::uint32_t clientNum) const;
        [[nodiscard]] std::optional<SvWorldPlayerSample> worldPlayerSample(
            std::uint32_t clientNum) const;
        [[nodiscard]] bool worldNativeEntityMirrorSynchronized() const;
        [[nodiscard]] std::optional<TraceResult> traceWorldPoint(
            const SvPointTraceRequest &request) const;
        [[nodiscard]] std::optional<TraceResult> traceWorldCapsule(
            const std::array<float, 3> &start,
            const std::array<float, 3> &end,
            const TraceBounds &bounds,
            std::uint32_t contentMask,
            const SvTraceEntityFilter &filter) const;
        [[nodiscard]] std::optional<SvClientThinkStatus> worldClientThinkStatus(
            std::uint32_t clientNum) const;
        [[nodiscard]] std::optional<SvPredictableEventStatus>
            worldPredictableEventStatus(std::uint32_t clientNum) const;
        [[nodiscard]] std::optional<SvBulletExecutionStatus>
            worldBulletExecutionStatus(std::uint32_t clientNum) const;
        // Give the world the index for `dmz_empty_mp` once the asset owner has
        // resolved it; the mode flag itself is set at gametype configure.
        void setUnarmedSpawnWeapon(std::uint16_t weaponAssetIndex);
        void setWeaponDefinitionResolver(
            SvServerWorld::WeaponDefinitionResolver resolver);
        [[nodiscard]] std::optional<SvResolvedLoadout> worldResolvedLoadout(
            std::uint32_t clientNum) const;
        [[nodiscard]] std::optional<SvWorldEvent> worldLastEvent() const;
        [[nodiscard]] std::optional<SvEntityDamageRuntimeStatus>
        worldEntityDamageStatus(std::uint32_t entityNum) const;
        [[nodiscard]] SvBrushModelActivationStatus worldBrushModelActivationStatus()
            const;

    private:
        void runFrame(std::uint32_t frameMilliseconds);
        [[nodiscard]] bool addClientScore(
            std::uint32_t clientNum,
            std::int32_t delta);
        [[nodiscard]] bool addClientXp(
            std::uint32_t clientNum,
            std::int32_t delta);
        // The counter a teamless gametype's limit reads; see the .cpp for why it
        // cannot be the display score.
        bool addKillForClient(std::uint32_t clientNum, std::int32_t delta);
        [[nodiscard]] bool addTeamScoreForClient(
            std::uint32_t clientNum,
            std::int32_t delta);
        // Called only by the local campaign script builtin. The authored
        // objective decides when the mission is complete; ServerCore still
        // owns the network transition which follows that decision.
        [[nodiscard]] bool finishCampaignMissionFromScript();
        void evaluateMatchLimits();
        // Watches matchStatus_.completed rather than being called from the
        // four places that set it.
        void announceMatchCompletion();
        void driveMatchEndSequence();
        void holdMatchCompletionState();
        void logPlayerPresentation();
        void announceMatchRules();
        // The announcer: the schedule above, plus the lead change, turned into
        // `p` commands. Every parameter it sends is in sv_gamestate_mp.hpp with
        // the demo frame it was measured on.
        void driveMatchAnnouncer();
        void driveLeadChangeAnnouncer();
        // BATTLECHATTER. driveBattleChatter watches each client's predictable
        // event ring for EV_RELOAD_START; sayBattleChatter is the one place a
        // line is spoken, so suppression and audience cannot be bypassed by a
        // new trigger forgetting to check them.
        void driveBattleChatter();
        void sayBattleChatter(
            std::uint32_t speakerClientNum, SvBattleChatterLine line);
        // ENQUEUE, never send. Every announcer line goes through the per-client
        // dialog queue so the 3 s spacing holds no matter who queued it.
        // `statusGroup` marks the lead-change group, whose pending entry is
        // REPLACED rather than followed.
        void queueAnnouncerLine(
            std::uint32_t clientNum,
            std::uint16_t announcerParameter,
            bool statusGroup = false);
        void broadcastAnnouncerLine(
            std::uint16_t announcerParameter, bool statusGroup = false);
        // Drains one line per client per 3 s. Called every frame.
        void pumpAnnouncerDialog();
        void announceVisionSet();
        void announceSoundAliases();
        // THE USABLE PROMPT. Each frame, for each living client, decides whether they
        // are standing in a usable trigger and publishes the hint that names it.
        //
        // ONLY `zombie_door` FOR NOW, on purpose. The shipped table carries all 54 of
        // zm_factory_sh's trigger_use -- perk machines, the mystery box, the ammo boxes,
        // the teleporter -- and every one of them is a piece of gameplay that does not
        // exist yet. A prompt offering to open something this server cannot open is
        // worse than no prompt, so the rest stay dark until the thing behind them works.
        void driveCursorHints(std::span<const SvWorldClientInput> activeClients);

    public:
        // THE HINT STRING TABLE. Hands back the RELATIVE index into configstring
        // band 856 -- which is what playerState.cursorHintString carries -- for
        // a piece of hint text, registering it on first use.
        //
        // Deliberately the same shape as the client's own allocator
        // (sub_4EC5D0): scan from the low end, return the slot that already
        // holds this text, otherwise take the first free one. Returns nullopt
        // when the band is full, because the band is 96 wide and a 97th hint is
        // a caller bug rather than something to wrap around on.
        //
        // The text may be a localization key (`ZOMBIE_BUTTON_REWARD_BARRIER`)
        // or literal text -- the retail zm captures carry both, and a key the
        // client cannot resolve is drawn as-is.
        [[nodiscard]] std::optional<std::uint16_t> registerHintString(
            std::string_view text);

    private:
        // Publishes the class into perkSlot_0..5 - the dvars the client's own
        // UI publishes and the menus read. See sv_splash_mp's neighbours: the
        // name table is at out.exe 0x00E77298.
        void announceLoadoutDvars();
        // Re-asserts perks a moment after a spawn zeroed them, which is the
        // clear->set edge the client's perk HUD keys on.
        void driveClientPerks(
            std::uint32_t serverTime,
            std::span<const SvWorldClientInput> activeClients);
        // Asks the client to open the death and respawn screens, which is the
        // half of the menu protocol this server has never sent.
        void driveClientUiScreens(
            std::uint32_t serverTime,
            std::span<const SvWorldClientInput> activeClients);
        void projectDeathVision();
        void completeSdRound(SvTeam winner, SvSdRoundEndReason reason);
        void evaluateSdRound(std::span<const SvWorldClientInput> activeClients);
        [[nodiscard]] bool advanceSdRound();
        void processSdCommittedCommand(
            const SvWorldClientInput &client,
            const UserCmd &command);
        // THE PICKUP. Runs on every committed usercmd, next to the SD plant/defuse
        // for the same reason: this is the only place the server sees the buttons the
        // player actually pressed, on a command the world has already accepted.
        void processLootCommittedCommand(
            const SvWorldClientInput &client,
            const UserCmd &command);
        void processZmUseCommittedCommand(
            const SvWorldClientInput &client,
            const UserCmd &command);
        [[nodiscard]] bool activateZmZone(std::string_view zoneName);
        void projectSdObjectives(
            std::span<const SvWorldClientInput> activeClients);
        void projectClientHudElems(
            std::span<const SvWorldClientInput> activeClients);
        void trackMatchParticipation(std::uint32_t serverTime);
        [[nodiscard]] std::uint32_t matchParticipationMilliseconds(
            std::uint32_t clientNum,
            std::uint32_t endServerTime) const;
        void announceSdRoundStart(
            std::span<const SvWorldClientInput> activeClients);
        void announceSdLastAlive(
            std::span<const SvWorldClientInput> activeClients,
            const SvSdEliminationState &state);
        void queueSdSoundForClient(
            std::uint32_t clientNum,
            std::uint16_t eventParameter);
        void sendSdSoundToTeam(SvTeam team, std::uint16_t eventParameter);
        void queueSdSoundForTeam(SvTeam team, std::uint16_t eventParameter);
        void pumpSdSoundQueues(std::span<const SvWorldClientInput> activeClients);
        [[nodiscard]] bool setSdBombVisual(
            const std::array<float, 3> &origin,
            bool active);

        struct ClientLoadoutResolution
        {
            std::uint32_t sequence{};
            std::optional<SvResolvedLoadout> loadout;
        };

        FixedFrameScheduler scheduler_{ SV_FrameMilliseconds() };
        SvTimingAccumulator frameTotalTiming_;
        SvTimingAccumulator framePrepareTiming_;
        SvTimingAccumulator frameBeginWorldTiming_;
        SvTimingAccumulator frameClientThinkTiming_;
        SvTimingAccumulator frameModeTiming_;
        SvTimingAccumulator frameEndAndPublishTiming_;
        std::uint64_t frameClientThinkCommands_{};
        SvClientSystem clients_;
        SvServerWorld world_;
        // A COPY of the model resolver handed to the script builtins. The
        // podium needs to turn a model NAME into this map's own configstring
        // index (section 124: retail's 121 is an index into a DIFFERENT map's
        // band and cannot be ported as a number). Declared before
        // scriptBuiltins_ so the constructor can copy it here and move it there.
        // ITS OWN LOCK, AND THIS IS NOT AN OPTIMISATION -- IT IS THE FIX FOR A
        // DEADLOCK. ServerCore::loadGameplayScript holds mutex_ while it executes the
        // gametype script, and that script calls the zm zone builtins, which read this
        // model. Reading it under mutex_ therefore re-locks a NON-RECURSIVE mutex on
        // the same thread and hangs the world spawn with no error logged -- observed
        // 2026-09-01, the log stopping dead between "map triggers" and
        // "gameplay script loaded".
        //
        // Safe because the order is one-way: a zone read never takes mutex_, so no
        // cycle exists. Do not merge this back into mutex_.
        mutable std::mutex zmZonesMutex_;
        std::vector<SvZmZone> zmZones_;
        SvScriptBuiltinRegistry::ModelResolver modelResolver_;
        SvScriptBuiltinRegistry::SoundResolver factorySoundResolver_;
        SvScriptBuiltinRegistry scriptBuiltins_;
        SvLuaRuntime scriptRuntime_;
        LoadoutProvider loadoutProvider_;
        PerkLoadoutProvider perkLoadoutProvider_;
        RewardLoadoutProvider rewardLoadoutProvider_;
        std::function<std::optional<SvRewardWeapon>()> uavWeaponProvider_;
        struct UavOwner {
            std::uint64_t xuid{};
            SvUavEarningState state;
            std::optional<SvRewardWeapon> weapon;
            std::uint16_t lastGun{}, committedWeapon{};
            std::optional<std::uint8_t> committedLife;
            bool returning{}, returnQueued{};
            bool testRewardGranted{};
            bool radarManaged{};
            std::vector<std::uint32_t> radarExpiries;
        };
        std::unordered_map<std::uint32_t, UavOwner> uavOwners_;
        std::uint32_t uavRadarDuration_{};
        bool uavRadarTestOverride_{};
        bool uavRadarTestGrant_{};
        void observeUavWeaponChanges(std::span<const SvWorldEvent> events);
        void driveClientUav(std::span<const SvWorldClientInput> activeClients);
        EquipmentLoadoutProvider equipmentLoadoutProvider_;
        CharacterCustomizationProvider characterCustomizationProvider_;
        CharacterModelNamesProvider characterModelNamesProvider_;
        ScriptAnimationResolver scriptAnimationResolver_;
        CharacterOptionMaskProvider characterOptionMaskProvider_;
        std::unordered_map<std::uint32_t, ClientLoadoutResolution> resolvedLoadouts_;
        struct MatchParticipation
        {
            std::uint64_t xuid{};
            std::uint32_t accumulatedMilliseconds{};
            std::optional<std::uint32_t> activeSince;
        };
        std::unordered_map<std::uint32_t, MatchParticipation> matchParticipation_;
        // Frozen at the match decision and keyed by client slot. The same
        // value feeds both the outcome HudElem and aarScoreboard.xp, so a
        // roster/rank change during the 1.1-second delay cannot make the two
        // disagree.
        std::unordered_map<std::uint32_t, std::uint32_t> dmMatchBonuses_;
        // THE LAST CUSTOMIZATION THAT RESOLVED, PER PLAYER. Section 166: the
        // provider runs EVERY FRAME and its answer is not retained anywhere, so a
        // single frame on which it cannot answer drops that client out of the
        // snapshot's clientInfos -- and writeClientInfos then tells every observer
        // to REMOVE a clientInfo it already has. A removed clientInfo is a player
        // with modelIndex zero, which is a player with no model name, which is a
        // player nobody can see. Keyed on XUID so a reused client slot cannot
        // inherit the previous occupant's character.
        struct ClientCustomizationMemory
        {
            std::uint64_t xuid{};
            SvCharacterCustomization customization{};
        };
        std::unordered_map<std::uint32_t, ClientCustomizationMemory>
            lastCharacterCustomizations_;
        DtlsSessionConfig dtlsConfig_;
        DtlsPeerSystem dtlsPeers_;
        std::unordered_map<std::uint64_t, DtlsPeerState> dtlsPeerDiagnostics_;
        std::unordered_map<std::uint64_t, std::string> dtlsRejectDiagnostics_;
        std::unordered_map<std::uint64_t, std::uint32_t> dtlsNatDiagnostics_;
        std::unordered_map<std::uint64_t, std::uint32_t> plaintextDiagnostics_;
        std::unordered_map<std::uint64_t, std::uint32_t> netchanRejectDiagnostics_;
        ServerStatus status_{};
        SvConnectionlessDiagnostics connectionlessDiagnostics_{};
        SvMatchStatus matchStatus_{};
        bool matchCompletionAnnounced_{};
        // The serverTime the match was DECIDED. Retail's end-of-match sequence
        // is a schedule hung off that instant, not a single frame's worth of
        // commands - see driveMatchEndSequence.
        std::uint32_t matchCompletionServerTime_{};
        bool matchEndedAnnounced_{};
        bool outroVisionAnnounced_{};
        // The two end-of-match SCREEN requests, section 109e's asking half:
        // `u 10` at +11100 and `q 19` at +17400. Separate flags because they
        // are 6.3 seconds apart on retail's own schedule.
        bool outroScreenAsked_{};
        bool podiumScreenAsked_{};
        // The outro killcam ENDS before the podium begins: retail clears all
        // four killcam playerState fields at match-end + 16900, on the same
        // frame it sends the first `I 17433 0 0`, 500 ms before `q 19`.
        bool outroKillCamCleared_{};
        // The two timescale writes that put the end of the match into slow
        // motion and take it back out, at +14000 and +15500.
        bool outroSlowMotionStarted_{};
        bool outroSlowMotionEnded_{};
        // The rest of retail's +17000 frame: `s ui_match_complete "1"`,
        // `> 161`, `s 2972 "1"`, the objective-marker clear and the fog's
        // start-time zero.
        bool outroPodiumStateAsked_{};
        // One last `r 19` at +31500, 1200 ms before EXE_MATCHENDED.
        bool outroFinalScoresAsked_{};
        // The podium ROSTER (`L <clientNum> <slot>`) at +0 and the four
        // top3_*_current_weapon dvars at +17400. Separate from the screen
        // requests because they carry content rather than opening a layout.
        bool podiumRosterAsked_{};
        bool podiumWeaponsAsked_{};
        // The map's own `top_players_camera` (section 121), and a one-shot so
        // the log says where the player was sent exactly once per match rather
        // than every frame of a 32-second hold.
        std::optional<SvWorldSpawnPoint> topPlayersCamera_;
        bool podiumCameraLogged_{};
        // The map's three podium places, already ordered first/second/third.
        std::vector<SvWorldSpawnPoint> topPlayersPlaces_;
        bool podiumFiguresSpawned_{};
        struct PodiumAnimationSet
        {
            std::uint32_t entityNum{};
            std::uint16_t idle{};
            std::uint16_t emoteIn{};
            std::uint16_t emote{};
            std::uint16_t emoteOut{};
        };
        std::array<std::optional<PodiumAnimationSet>, 3> podiumAnimations_{};
        std::size_t podiumAnimationEvent_{};
        // The outro camera's entity number, once spawned. One per match.
        std::optional<std::uint32_t> podiumCameraEntity_{};
        bool podiumCameraMotionContinued_{};
        std::uint16_t podiumFallbackModelIndex_{};
        std::string podiumFallbackModelName_;
        // Character models already `|` precached to every client, and the character
        // each client was last precached FOR. See precacheCharacterModels.
        std::set<std::string> precachedCharacterModels_;
        std::map<std::uint32_t, std::uint16_t> precachedCharacterFor_;
        std::vector<std::uint16_t> outfitModelSlots_;
        std::map<std::string, std::uint16_t> outfitModelIndexes_;
        std::map<std::string, std::uint16_t> publishedActorModels_;
        bool matchEndFreezeLogged_{};
        bool matchEndScoresAsked_{};
        std::uint32_t presentationLogCounter_{};
        bool firstBloodAwarded_{};
        // victim -> whoever last killed them, for SPLASHES_REVENGE. Exact, and
        // the only state a revenge medal needs: no window, no threshold. Only
        // kills that already passed the suicide and team-kill gates get in, so
        // a team kill can never arm a revenge.
        std::unordered_map<std::uint32_t, std::uint32_t> lastKilledBy_;
        // The medal queue. One release per client per
        // SvSplashReleaseIntervalMilliseconds, because the client holds ONE
        // splash per display slot and a second on the same frame replaces it.
        struct PendingSplash
        {
            std::uint32_t row{};
            std::int32_t points{};
        };
        std::unordered_map<std::uint32_t, std::vector<PendingSplash>> splashQueue_;
        std::unordered_map<std::uint32_t, std::uint32_t> lastSplashRelease_;
        // clientNum -> the serverTime at which perks should be re-asserted
        // after a spawn zeroed them. See driveClientPerks.
        struct PerkLife
        {
            std::uint64_t xuid{};
            std::uint8_t spawnGeneration{};
            std::uint32_t assertAt{};
            SvResolvedPerks perks;
            bool persistentRewards{};
            bool asserted{};
            bool announced{};
        };
        std::unordered_map<std::uint32_t, PerkLife> perkLives_;
        struct EquipmentLife
        {
            std::uint64_t xuid{};
            std::uint8_t spawnGeneration{};
            bool announced{};
        };
        std::unordered_map<std::uint32_t, EquipmentLife> equipmentLives_;
        void driveClientEquipment(std::span<const SvWorldClientInput> activeClients);
        // What driveClientUiScreens remembers about one client's current life.
        // The alive/dead edge is the whole state, and it is trustworthy only
        // because a death now lasts the gametype's respawn delay rather than
        // one frame -- see driveClientUiScreens for the two wrong readings that
        // took. spawnSequence is NOT usable here: it never changes after the
        // first spawn.
        struct SvUiClientLife
        {
            // The connect trio is sent once per OCCUPANCY of a slot, not once
            // per life: retail sends it in the gamestate's own message and
            // never again.
            bool connected{};
            bool seen{};
            bool alive{};
            // Retail's first spawn and its respawns send DIFFERENT clusters
            // (see driveClientUiScreens), and `seen` alone cannot tell them
            // apart -- a client that becomes Active a frame before it becomes
            // alive takes the alive edge, not the first-sight branch, so its
            // first spawn read as a respawn.
            bool everAlive{};
            // OLMOD(factory-class-confirmation): consume each cancellation once.
            std::uint32_t classMenuResponseSequence{};
            // Retail Wetwork leaves 700 ms between the campaign admission
            // burst in the first snapshot and the first-spawn burst. The
            // multiplayer path sends both immediately, which presents the
            // player before campaign cgame has completed its cinematic setup.
            std::optional<std::uint32_t> firstSpawnAt;
            // Wetwork follows that first-spawn burst 100 ms later with its
            // weapon, stow-tag and intro-sound setup. The timestamp carried by
            // `d 15` is the first-spawn frame, not the follow-up frame.
            std::optional<std::uint32_t> wetworkActivationAt;
            std::uint32_t wetworkSpawnTime{};
            // THE KILLCAM IS ARMED ON THE DEATH EDGE AND FIRES 1500 ms LATER,
            // and only if the player is STILL DEAD then. That is not a policy
            // choice: retail's seven killcams all land at death + 1500 ms
            // exactly, and its seventeen killcam-less deaths are the ones whose
            // respawn cluster went out at that same instant.
            std::optional<std::uint32_t> killCamAt;
            bool killCamActive{};
        };
        std::unordered_map<std::uint32_t, SvUiClientLife> uiClientLife_;
        // WHO KILLED WHOM, AND WHEN. The killcam needs the KILLER's clientNum
        // and how far back to rewind, and neither survives the death edge --
        // the PlayerKilled event is consumed a frame earlier by the medal and
        // scoring path, which throws both away.
        struct SvKillCamSubject
        {
            std::uint32_t killerClientNum{};
            std::uint32_t serverTime{};
        };
        std::unordered_map<std::uint32_t, SvKillCamSubject> killCamSubjects_;
        // THE KILL FEED'S OWN WITNESS (section 191q). An obituary that is
        // created but never ARCHIVED reaches no client, and the two failures
        // look identical from the kill log alone -- so this reports the entity
        // numbers the published snapshot actually carries, once per obituary.
        // Silent in a match where nobody dies, three lines a minute otherwise.
        std::set<std::uint32_t> archivedObituaries_;
        // THE MATCH-END KILLCAM REPLAYS THE LAST KILL OF THE MATCH, so the last
        // one has to survive the respawn that erases it from killCamSubjects_.
        // Retail's match-end frame names a killer (killCamClientNum 2, and the
        // same client on `L 2 7`) and a victim (killCamLookAtEntity 8) that are
        // not the winner and not the recording client, which is what a final
        // kill looks like.
        struct SvMatchEndKill
        {
            std::uint32_t killerClientNum{};
            std::uint32_t victimClientNum{};
            std::uint32_t serverTime{};
        };
        std::optional<SvMatchEndKill> lastMatchKill_;
        std::set<std::uint32_t> matchRulesAnnounced_;
        SvAnnouncerState announcer_;
        SvBattleChatterAudience battleChatterAudience_{
            SvBattleChatterAudience::Everyone
        };
        std::vector<SvBattleChatterSpeaker> battleChatterSpeakers_;
        // The event ring is re-read every frame and re-presents the same batch
        // until it advances, so a line would fire on every frame of a reload
        // without this. Keyed by client, holding the sequence already spoken
        // for.
        std::unordered_map<std::uint32_t, std::int32_t> battleChatterSequence_;
        std::unordered_map<std::uint32_t, bool> battleChatterVoiceFemale_;
        std::unordered_map<std::uint32_t, SvAnnouncerClientDialog>
            announcerDialog_;
        std::set<std::uint32_t> visionAnnounced_;
        // OLMOD(factory-entry): source-owned, never part of the native world ABI.
        struct FactoryEntryState
        {
            std::uint32_t birth{};
            std::uint32_t flashAt{};
            std::array<std::optional<SvEntityHandle>,2> arrivalCarriers{};
            std::array<std::array<float,3>,2> arrivalOrigins{};
            std::array<bool,3> arrivalQueued{};
            bool flashQueued{};
            bool restored{};
        };
        std::uint16_t factoryArrivalModel_{};
        std::array<std::uint16_t,3> factoryArrivalFx_{};
        std::uint8_t factoryArrivalBone_{};
        bool factoryEntryEnabled_{};
        bool factoryInteractablesEnabled_{};
        bool factoryTeleportersEnabled_{};
        bool factoryBo1TravelEnabled_{};
        bool beginFactoryTravel(std::uint32_t,std::uint8_t,std::size_t,const std::array<float,3>&);
        void driveFactoryTravel();
        SvFactoryTeleporterState factoryTeleporters_{};
        SvFactoryTeleporterResources factoryTeleporterResources_{};
        std::vector<std::pair<SvEntityHandle,std::uint32_t>> factoryTeleportEffects_;
        void emitFactoryTeleportFx(std::uint16_t,const std::array<float,3>&,const std::array<float,3>& angles={});
        std::string factoryTeleportHint(std::uint32_t,const SvMapTrigger&) const;
        bool processFactoryTeleportUse(const SvWorldClientInput&,const SvMapTrigger&);
        void driveFactoryTeleporters(std::span<const SvWorldClientInput>);
        SvFactoryBoxRuntime factoryBox_{};
        SvFactoryBoxResources factoryBoxResources_{};
        std::map<std::string,std::uint16_t,std::less<>> factorySounds_;
        std::map<std::uint32_t,std::string> factoryInteractionHintCache_;
        std::string factoryBoxHint(std::uint32_t,const SvMapTrigger&) const;
        bool processFactoryBoxUse(const SvWorldClientInput&,const SvMapTrigger&);
        void driveFactoryBox(std::span<const SvWorldClientInput>);
        void closeFactoryBox(std::uint32_t);
        void factoryInteractionSound(std::uint32_t,std::string_view);
        void announceFactorySoundAliases();

        std::unordered_map<std::uint32_t, FactoryEntryState> factoryEntries_;
        SvSdRoundStatus sdRoundStatus_{};
        SvSdBombStatus sdBombStatus_{};
        SvSdBombRules sdBombRules_{};
        std::optional<SvTriggerVolume> sdBombPickupTrigger_;
        std::array<float, 3> sdBombPickupHomeOrigin_{};
        std::vector<SvSdBombSiteRuntime> sdBombSiteRuntime_;
        std::optional<SvEntityHandle> sdBombVisualHandle_;
        std::array<float, 3> sdBombVisualHomeOrigin_{};
        std::array<float, 3> sdBombVisualAngles_{};
        SvTriggerContactRunner triggerContactRunner_;
        SvUseObjectSystem useObjects_;
        std::optional<SvSdObjectiveMaterials> sdObjectiveMaterials_;
        struct ClientFeedbackState
        {
            // The client runs both animations off these start times, so they
            // are wire state, not just bookkeeping: rewriting one mid-fade
            // restarts the animation.
            std::uint32_t markerStart{};
            std::uint32_t markerExpiry{};
            bool markerIsKill{};
            std::uint32_t scoreStart{};
            std::uint32_t scoreExpiry{};
            float scoreValue{};
        };

        std::optional<std::uint16_t> damageFeedbackMaterial_;
        std::optional<std::uint16_t> killFeedbackMaterial_;
        std::optional<std::uint16_t> damageFeedbackSound_;
        std::optional<std::uint16_t> killFeedbackSound_;
        std::optional<std::uint16_t> scavengerBagWeaponAssetIndex_;
        std::optional<std::uint16_t> scavengerPickupSound_;
        bool soundAliasesAssigned_{};
        // Map/session-owned entity-link tag. Resolved once after each gamestate
        // configuration; it must never be a copied retail numeric index.
        bool livingWeaponRightTagInitialized_{};
        // Slot n is hint string n, which is configstring 856 + n. Empty means
        // free. Reset with the rest of the match state on a level load.
        std::array<std::string, HintStringConfigStringCount> hintStrings_{};
        // The map's shipped trigger volumes, or null on a map with no extracted table.
        const SvMapTriggerTable *mapTriggers_{};
        // ONE BAND SLOT PER DISTINCT STRING, not per trigger. Retail's own capture
        // gives all four of zm_factory_sh's 1000-point doors the same relative index,
        // and the band is only 96 wide against 54 triggers on this map alone.
        std::map<std::string, std::uint16_t, std::less<>> hintStringSlots_;
        // What each client is currently being told, so the wire only carries a change.
        // WIDENED TO 32 BITS to hold a loot key as well as a trigger index -- one
        // function owns cursorHint and it now has two kinds of answer to remember.
        // SvLootHintKeyBase separates them; a trigger index can never collide with it.
        std::map<std::uint32_t, std::uint32_t> cursorHintTrigger_;
        // WHICH CRATE EACH CLIENT IS STANDING AT, so a use press has something to
        // answer. Written by driveCursorHints, read by processLootCommittedCommand at
        // most one frame later -- which is also the lag the player already sees,
        // because the prompt they are reacting to came off the previous snapshot.
        std::map<std::uint32_t, SvLootItem> lootHintTarget_;
        // ACTIVATE IS A LEVEL, NOT AN EDGE. The bit stays set for as long as the key
        // is down and usercmds arrive faster than anyone can let go, so without this
        // one press would empty the whole ring.
        std::map<std::uint32_t, bool> lootActivateHeld_;
        // Map purchases and barrier repairs share the physical use key but retain
        // their own target: driveCursorHints guarantees only one is offered.
        std::map<std::uint32_t, const SvMapTrigger *> mapTriggerHintTarget_;
        std::map<std::uint32_t, std::string> barrierRepairHintTarget_;
        std::map<std::uint32_t, bool> zmUseActivateHeld_;
        std::map<std::uint32_t, SvFactoryAmmoHold> factoryAmmoHolds_;
        std::array<std::uint16_t, 2> factoryAmmoMaterials_{};
        std::array<std::uint16_t, 2> factoryClockMaterials_{};
        std::array<std::uint16_t, 2> zombieReviveMaterials_{};
        std::map<std::uint32_t, std::uint32_t> zmRepairReadyTime_;
        std::set<std::uint16_t> openedMapTriggers_;
        // Match-owned Factory progression. It resets on every server/world
        // configure; no powered interaction may consult stale state from a prior map.
        bool zmPowerOn_{};
        bool loadoutDvarsAssigned_{};
        std::optional<std::uint16_t> splashSound_;
        // MEASURED: the retail dm demo plays mp_headshot AND
        // bullet_impact_headshot_2 AND mp_hit_kill AND the splash sound on the
        // same frame as `w 0 16 50`, so the headshot sound is an ADDITION to
        // the medal's own sound, not a replacement for it.
        std::optional<std::uint16_t> headshotSound_;
        std::vector<std::pair<std::uint16_t, std::string>> soundAuditions_;
        std::size_t soundAuditionCursor_{};
        std::unordered_map<std::uint32_t, ClientFeedbackState> clientFeedback_;
        SvSdSoundPresentation sdSoundPresentation_{};
        std::unordered_map<std::uint32_t, std::deque<std::uint16_t>>
            sdSoundQueues_;
        std::unordered_map<std::uint32_t, std::uint32_t> sdSoundReadyTime_;
        bool sdRoundStartAnnounced_{};
        bool sdTfLastAliveAnnounced_{};
        bool sdScLastAliveAnnounced_{};
        std::uint32_t sdPreviousTfAlive_{};
        std::uint32_t sdPreviousScAlive_{};
        bool sdSideSwitchPending_{};
        std::string matchGameType_;
        std::string matchMapName_;
        mutable std::mutex mutex_;
    };
}
