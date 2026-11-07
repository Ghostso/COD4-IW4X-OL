#include "sv_client_events_mp.hpp"
#include <algorithm>
#include "sv_gamestate_mp.hpp"

#include "../../shared/RuntimeLog.hpp"

#include <array>
#include <cstdlib>
#include <string>

#include "sv_snapshot_mp.hpp"

namespace CodolGameServer
{
    namespace
    {
        // CODREF(client_events): CODOL's server-only filter bytes at
        // 0x00C5BA9C, plus the inline first value 0x1D in
        // BG_PlayerToEntity_ProcessEventInternal 0x004130C0, establish this
        // complete set. These are not inferred from BO1/Ghosts event numbers.
        //
        // OLMOD(section-80-fire-event-ids): AND ALL FOUR OF THOSE ADDRESSES ARE
        // 3.3.3.3's. THE FIRE IDS ARE +5 ON 1649370.
        //
        // 3.3.3.3's sender is sub_4258B0; out.exe's is sub_426B20, found by the
        // one signature that is unique in both images -- a function containing
        // EXACTLY TWO `lea reg,[reg+reg+imm8]` whose immediates differ by one.
        // One hit in 3.3.3.3 (0x32/0x31), and of the two in out.exe only this
        // one has the sender's whole shape:
        //
        //   push ebx; test eax,eax; push eax; mov ecx,esi; sete bl; call ...
        //   mov eax,[esi+0x340 -> 0x3F8]      the weapon index
        //   mov ecx,[eax*4 + 0x17F5A40 -> 0x1988B50]   the weapon table
        //   cmp [ecx+0x48C -> 0x598], 5 -> 8  the weaponDef discriminator
        //   lea ecx,[ecx+ecx+0x32 -> 0x37]    pass branch  -> 0x32/0x34 -> 0x37/0x39
        //   lea ecx,[ecx+ecx+0x31 -> 0x36]    fail branch  -> 0x31/0x33 -> 0x36/0x38
        //   mov eax,[esi+0xF4 -> 0x108]; and eax,3        the event ring index
        //   mov [esi+eax*8+0xF8 -> 0x10C], ecx            the event
        //   mov [esi+eax*8+0xFC -> 0x110], 0              the parameter
        //
        // A UNIFORM +5, and the live ring agrees: a person emptied two
        // magazines on 2026-08-21 and `events@10C` carried 55 (0x37) at the end
        // of a magazine, immediately before the reload. Nothing in
        // sv_bullet_mp had ever run because the decoder was waiting for four
        // ids this build never emits.
        //
        // TWO MORE EXIST HERE AND ARE DELIBERATELY NOT HANDLED. out.exe adds
        // `cmp edi,1 / cmp edi,2 -> lea ecx,[edi+0x39]`, so 0x3A and 0x3B are
        // fire events this build can send and 3.3.3.3 has no counterpart for.
        // What selects them is an argument nothing here supplies yet; guessing
        // a hand or a last-shot flag for them would be inventing a contract.
        constexpr std::int32_t EventSvFireWeapon = 0x36;
        constexpr std::int32_t EventSvFireWeaponLastShot = 0x37;
        constexpr std::int32_t EventSvFireWeaponLeft = 0x38;
        constexpr std::int32_t EventSvFireWeaponLastShotLeft = 0x39;
        //
        // AND THE OTHER FOUR ARE WRONG TOO, BY ONE. The table the original
        // comment cites is a dword ARRAY of every server-only event, and both
        // builds have it whole:
        //
        //   3.3.3.3  0x00C5BA9C : 1D 1C 22 16 | 31 32 33 34 | 00 00 00 00
        //   out.exe  0x00DADC0C : 1E 1D 23 17 | 36 37 38 39 | 3A 3B 00 00
        //
        // Same order, same shape, TEN entries where 3.3.3.3 has eight. The four
        // notify ids are +1 and the four fire ids are +5, which is an
        // independent confirmation of the +5 read off the sender above -- two
        // sources sharing no code. **Every one of the four is corroborated by
        // the live ring** from the two-magazine run: 0x1E and 0x1D appear
        // around a reload, and 0x23 appears carrying parameter 1225, which is
        // the weapon index -- a weapon-switch event naming its own weapon.
        constexpr std::int32_t EventOffhandEndNotify = 0x17;
        constexpr std::int32_t EventReloadStartNotify = 0x1D;
        constexpr std::int32_t EventReloadAddAmmo = 0x1E;
        constexpr std::int32_t EventWeaponSwitchStarted = 0x23;
        // OLMOD(section-80): the two entries this build adds. They are in the
        // SERVER-ONLY list, so out.exe expects a dedicated server to consume
        // them, and sub_426B20 emits them from `cmp edi,1 / cmp edi,2`. What
        // selects them is not established, so they are named and filtered
        // rather than decoded -- see SV_IsServerOnlyClientEvent below.
        constexpr std::int32_t EventSvFireWeaponVariantA = 0x3A;
        constexpr std::int32_t EventSvFireWeaponVariantB = 0x3B;

        // MELEE, AND IT IS DELIBERATELY NOT IN SV_IsServerOnlyClientEvent.
        //
        // out.exe's server-only array at 0x00DADC0C is TEN entries --
        // 1E 1D 23 17 | 36 37 38 39 | 3A 3B -- and no melee id is among them,
        // so CODOL's own dedicated dispatcher never sees this event. Adding it
        // to that predicate would be a false claim about the engine.
        //
        // It is read anyway, out of the predictable ring, exactly as section
        // 156's fall damage reads EV_LANDING_PAIN 0x9E (also absent from that
        // array). The ring is the server's OWN playerState: the demo corpus
        // proves the server carries these, because a demo records what the
        // server sent.
        //
        // WHY THIS ID AND NOT ONE OF THE OTHER FIFTEEN. Measured with
        // Tools/demo-re/melee-events.py over 84 demos -- 1514 melee events in
        // 35 of them:
        //     EV_MELEE_TRACE 0x41  258     EV_MELEE_HIT  0x4B    0
        //     EV_MELEE_SWIPE 0x3C  249     EV_MELEE_MISS 0x4C    0
        //     EV_MELEE_END   0x47  238
        //     EV_FIRE_MELEE  0x3D  227
        // HIT and MISS never fire, so the client never reports a connection and
        // the server must trace. EV_FIRE_MELEE is the commit instant: it lands
        // on the same server time as EV_MELEE_SWIPE in every swing in the
        // corpus, and it is the direct analogue of EV_SV_FIRE_WEAPON, which is
        // what the bullet path below already triggers on.
        //
        // TODO(CODOL): the TRACE family (0x41/0x42/0x43 and the PRE_TRACE
        // 0x44/0x45/0x46 pair) are animation notetracks marking the sample
        // points of the swing arc. If one trace at commit proves too generous
        // or too strict against a lunging target, those are the refinement --
        // they are measured and present, just not yet needed.
        constexpr std::int32_t EventFireMelee = 0x3D;
    }

    namespace
    {
        SvAltWeaponLookup altWeaponLookup;
        SvHostAltWeaponLookup hostAltWeaponLookup{};
        thread_local float currentPerkSpreadScale = 1.0f;

        bool weaponSpreadLoggingEnabled()
        {
            static const bool enabled = [] {
                const auto *const value = std::getenv("OLMOD_LOG_WEAPON_SPREAD");
                return value && value[0] == '1' && !value[1];
            }();
            return enabled;
        }

        void logWeaponSpreadSample(
            const SvPlayerState &playerState,
            const SvResolvedWeapon &weapon,
            const SvWeaponFireBasis &basis,
            const SvWeaponSpreadResult &spread,
            const float preMoveAimSpreadScale,
            const float perkSpreadScale)
        {
            if (!weaponSpreadLoggingEnabled())
                return;

            // A bounded opt-in trace keeps the production path quiet while
            // preserving enough consecutive shots to distinguish bad weapon
            // data, a saturated native aim scale, and a fire-basis mismatch.
            static std::size_t sampleCount{};
            if (sampleCount >= 256)
                return;
            ++sampleCount;

            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer,
                "weapon-spread sample=" + std::to_string(sampleCount) +
                    " client=" + std::to_string(playerState.clientNum) +
                    " cmd=" + std::to_string(playerState.commandTime) +
                    " weapon=" + std::to_string(weapon.weaponAssetIndex) +
                    " name=" + weapon.weaponName +
                    " wpFrac=" + std::to_string(playerState.weaponPositionFraction) +
                    " aimPre=" + std::to_string(preMoveAimSpreadScale) +
                    " aimPost=" + std::to_string(playerState.aimSpreadScale / 255.0f) +
                    " perk=" + std::to_string(perkSpreadScale) +
                    " min=" + std::to_string(spread.minimum) +
                    " max=" + std::to_string(spread.maximum) +
                    " ads=" + std::to_string(weapon.adsSpread) +
                    " firing=" + std::to_string(spread.firing) +
                    " view=" + std::to_string(playerState.viewAngles[0]) + "," +
                        std::to_string(playerState.viewAngles[1]) +
                    " forward=" + std::to_string(basis.forward[0]) + "," +
                        std::to_string(basis.forward[1]) + "," +
                        std::to_string(basis.forward[2]));
        }
    }

    void SV_SetCurrentClientEventPerkSpreadScale(const float scale)
    {
        currentPerkSpreadScale = scale;
    }

    float SV_CurrentClientEventPerkSpreadScale()
    {
        return currentPerkSpreadScale;
    }

    // SECTION 191z: FOURTEEN WAYS TO REFUSE A COMMAND AND ONE WORD FOR ALL OF
    // THEM, one level above the bullet path's thirteen.
    //
    // `client-think rejected ... stage=client_events_rejected` is what the
    // player experiences as "it hits them and nothing happens, and I desync" --
    // a refused event rejects the WHOLE usercmd, so the staged damage AND the
    // frame's movement are both discarded. The stage name separates none of the
    // fourteen, and the first alt-fire burst produced 121 of them with no way
    // to tell which.
    //
    // Same shape as SV_BulletFireFailed: a pointer to a literal, written and
    // read on the frame thread, no field added to anything.
    namespace
    {
        thread_local const char *lastClientEventRefusal = nullptr;
    }

    SvClientEventResult SV_ClientEventRefused(
        const SvClientEventResult result, const char *const reason)
    {
        lastClientEventRefusal = reason;
        return result;
    }

    const char *SV_LastClientEventRefusal()
    {
        return lastClientEventRefusal ? lastClientEventRefusal : "unset";
    }

    void SV_SetAltWeaponLookup(SvAltWeaponLookup lookup)
    {
        altWeaponLookup = std::move(lookup);
    }

    bool SV_LookupAltWeapon(
        const std::uint16_t weaponAssetIndex,
        SvResolvedWeapon &resolved)
    {
        return weaponAssetIndex && altWeaponLookup &&
            altWeaponLookup(weaponAssetIndex, resolved);
    }

    void SV_SetHostAltWeaponLookup(SvHostAltWeaponLookup lookup)
    {
        hostAltWeaponLookup = std::move(lookup);
    }

    bool SV_LookupAltWeaponForHost(
        const std::uint16_t hostAssetIndex,
        SvResolvedWeapon &resolved)
    {
        return hostAssetIndex && hostAltWeaponLookup &&
            hostAltWeaponLookup(hostAssetIndex, resolved);
    }

    void SV_AddEntityPresentationEvent(
        SvGameEntity &entity, const std::int32_t eventId)
    {
        const auto slot =
            static_cast<std::size_t>(entity.networkState.eventSequence) & 3u;
        entity.networkState.events[slot] = { eventId, 0 };
        entity.networkState.eventSequence = static_cast<std::uint8_t>(
            entity.networkState.eventSequence + 1);
    }

    bool SV_IsServerOnlyClientEvent(const std::int32_t event)
    {
        // CODREF(client_events): presentation and single-client events remain
        // in native BG_PlayerStateToEntityState. Only this exact list crosses
        // the removed CODOL dedicated HandleClientEvent boundary.
        switch (event)
        {
        case EventOffhandEndNotify:
        case EventReloadStartNotify:
        case EventReloadAddAmmo:
        case EventWeaponSwitchStarted:
        case EventSvFireWeapon:
        case EventSvFireWeaponLastShot:
        case EventSvFireWeaponLeft:
        case EventSvFireWeaponLastShotLeft:
        // OLMOD(section-80): 1649370-only, and in out.exe's own server-only
        // array. Admitted here so the boundary matches the engine's; the fire
        // decoder still refuses them, so they are dropped deliberately rather
        // than by omission.
        case EventSvFireWeaponVariantA:
        case EventSvFireWeaponVariantB:
            return true;
        default:
            return false;
        }
    }

    std::optional<SvFireWeaponEvent> SV_DecodeFireWeaponEvent(
        const SvNativePredictableEvent &event)
    {
        // CODDIFF(client_events): BO1 passes eventParm to FireWeapon, whereas
        // Ghosts passes the event id. CODOL PM_Weapon_FireWeapon_SendFireWeaponEvent
        // 0x004258B0 writes parameter zero and encodes hand/last-shot in
        // 0x31..0x34, constraining this source adapter to the newer contract.
        if (event.parameter != 0)
            return std::nullopt;

        switch (event.event)
        {
        case EventSvFireWeapon:
            return SvFireWeaponEvent{
                .event = event.event,
                .hand = SvPlayerHand::Right,
            };
        case EventSvFireWeaponLastShot:
            return SvFireWeaponEvent{
                .event = event.event,
                .hand = SvPlayerHand::Right,
                .lastShot = true,
            };
        case EventSvFireWeaponLeft:
            return SvFireWeaponEvent{
                .event = event.event,
                .hand = SvPlayerHand::Left,
            };
        case EventSvFireWeaponLastShotLeft:
            return SvFireWeaponEvent{
                .event = event.event,
                .hand = SvPlayerHand::Left,
                .lastShot = true,
            };
        default:
            return std::nullopt;
        }
    }

    bool SV_IsRewindableAttackEvent(const SvNativePredictableEvent &event)
    {
        return event.event == EventFireMelee ||
            SV_DecodeFireWeaponEvent(event).has_value();
    }

    SvClientEventResult SV_HandleClientEventsDetailed(
        SvPlayerState &playerState,
        SvGameEntity &entity,
        const float currentAimSpreadScale,
        const SvResolvedLoadout *const resolvedLoadout,
        const std::span<const SvNativePredictableEvent> events,
        const SvWeaponFireBasisBuilder &fireBasisBuilder,
        const SvFireWeaponHandler &fireWeaponHandler,
        const SvMeleeAttackHandler &meleeAttackHandler,
        const SvResolvedEquipment *const equipment,
        const SvOffhandUseHandler &offhandUseHandler,
        const SvRewardWeapon *const uavWeapon,
        const float perkSpreadScale)
    {
        // CODREF(client_events): BO1/Ghosts/BO2 HandleClientEvent dispatch their
        // server-only predictable fire events into FireWeapon after native
        // PM_Weapon has advanced weapon state. CODOL event ids and payloads
        // are recovered locally from its predictable-event consumer.
        // OLMOD(client-event-result): DeferredImpact lets the deterministic
        // PM_Weapon candidate commit while preserving an explicit marker that
        // a server-only projectile, penetration, or damage branch is missing.
        // OLMOD(client-event-slice-admission): direct callers must preserve the
        // same four-entry bound as SvNativePredictableEventBatch; the outer
        // reader normally establishes this before dispatch.
        if (events.size() > MaximumClientEventsPerCommand)
            return SV_ClientEventRefused(SvClientEventResult::Invalid, "event-slice-too-large");

        auto deferredImpact = false;
        // SECTION 190: the loadout FIRST, then the alt. An alt weapon is a real
        // weapon asset with its own definition, and after the server switches a
        // player to one every fire event names it. Falling back here keeps the
        // refusal intact for a genuinely unknown index while letting an alt
        // shoot.
        SvResolvedWeapon altScratch;
        const auto findWeapon =
            [&](const std::uint16_t weaponAssetIndex) -> const SvResolvedWeapon * {
            const auto *const found = resolvedLoadout
                ? SV_FindResolvedWeapon(*resolvedLoadout, weaponAssetIndex)
                : nullptr;
            if (found)
                return found;
            if (weaponAssetIndex && altWeaponLookup &&
                altWeaponLookup(weaponAssetIndex, altScratch))
            {
                return &altScratch;
            }
            return nullptr;
        };
        for (const auto &event : events)
        {
            // MELEE FIRST, because it is not a server-only event and the
            // predicate below would drop it. See EventFireMelee above.
            if (event.event == EventFireMelee)
            {
                if (!meleeAttackHandler)
                    continue;
                // Every melee event in the corpus carries parameter 0; a
                // nonzero one is a contract this has not seen and is refused
                // rather than guessed at.
                if (event.parameter != 0)
                    return SV_ClientEventRefused(SvClientEventResult::Invalid, "melee-parameter-nonzero");
                const auto weaponAssetIndex =
                    entity.networkState.weaponAssetIndex;
                const auto *const weapon = findWeapon(weaponAssetIndex);
                if (!resolvedLoadout || !weapon ||
                    playerState.currentWeaponAssetIndex != weaponAssetIndex)
                {
                    return SV_ClientEventRefused(SvClientEventResult::Invalid, "melee-weapon-or-loadout");
                }
                if (!fireBasisBuilder)
                    return SV_ClientEventRefused(SvClientEventResult::Unsupported, "melee-no-fire-basis-builder");
                const auto meleeBasis = fireBasisBuilder(*weapon);
                if (!meleeBasis)
                    return SV_ClientEventRefused(SvClientEventResult::Failed, "melee-basis-build");
                const auto meleeResult = meleeAttackHandler(
                    playerState, entity, *weapon, *meleeBasis);
                // A miss is the common case and commits nothing. Only a
                // genuine execution fault rejects the candidate.
                if (meleeResult == SvMeleeAttackResult::Failed)
                    return SV_ClientEventRefused(SvClientEventResult::Failed, "melee-execution");
                continue;
            }

            // CODREF(1649370): 429AF9 emits EV_USE_OFFHAND=73 with ps+3E4.
            // Native PM_Weapon already consumes its ammo (429AE0/42C510).
            // Like melee, handle this before the server-only filter.
            if (event.event == 73)
            {
                const auto *offhand = equipment && event.parameter > 0 && event.parameter <= 0x7FF
                    ? SV_FindOffhandWeapon(*equipment, static_cast<std::uint16_t>(event.parameter))
                    : nullptr;
                if (!offhand || std::ranges::none_of(playerState.heldWeapons, [&](const auto &slot) {
                        return slot.weaponAssetIndex == offhand->weaponAssetIndex;
                    }))
                    return SV_ClientEventRefused(SvClientEventResult::Invalid, "offhand-use-not-owned");
                if (offhandUseHandler)
                {
                    switch (offhandUseHandler(playerState, entity, *offhand))
                    {
                    case SvFireWeaponResult::Applied:
                        break;
                    case SvFireWeaponResult::DeferredImpact:
                        deferredImpact = true;
                        break;
                    default:
                        return SV_ClientEventRefused(
                            SvClientEventResult::Failed, "offhand-use-execution");
                    }
                    continue;
                }
                // TODO(CODOL): install G_UseOffHand projectile owner. Preserve native
                // command/ammo state and report DeferredImpact, like the existing
                // projectile fire path; do not fabricate a hit or decrement twice.
                deferredImpact = true;
                OlMod::RuntimeLog::write(OlMod::RuntimeLog::Channel::GameServer,
                    "offhand use pending projectile client=" + std::to_string(playerState.clientNum) +
                    " weapon=" + std::to_string(offhand->weaponAssetIndex));
                continue;
            }
            if (!SV_IsServerOnlyClientEvent(event.event))
            {
                // SECTION 190: THE VOCABULARY OF WHAT WE THROW AWAY.
                //
                // Alt-fire moves the UI icon and nothing else, and the first
                // thing to establish is WHICH event the client sends when the
                // player presses it. `sub_429E10` -- the function that reads
                // `cmd.lastWeaponAltModeSwitch` out of pmove+0x1C and uses it
                // to index the weapon table `dword_1988B50` -- pushes event
                // **74** into the predictable ring, and 74 is not in out.exe's
                // server-only array at 0x00DADC0C, so this `continue` is where
                // it dies. But 74 is what ONE path emits; PM_BeginWeaponChange
                // emits 0x23, and which of them an alt press produces is not
                // established.
                //
                // So report the FIRST SIGHTING of each distinct id and then
                // never again. Silent once the vocabulary is known, which is
                // section 189c's rule, and it costs one array probe per event
                // on a path that already iterates them.
                static std::array<bool, 256> seenIgnoredEvent{};
                const auto id = static_cast<std::uint32_t>(event.event);
                if (id < seenIgnoredEvent.size() && !seenIgnoredEvent[id])
                {
                    seenIgnoredEvent[id] = true;
                    OlMod::RuntimeLog::write(
                        OlMod::RuntimeLog::Channel::GameServer,
                        "client event FIRST SIGHTING id=" + std::to_string(id) +
                            " param=" + std::to_string(event.parameter) +
                            " (not server-only, ignored)");
                }
                continue;
            }

            if (event.event == EventWeaponSwitchStarted)
            {
                // CODREF(client_events): CODOL PM_BeginWeaponChange writes the
                // target weapon asset into event 0x23 (OLfinal). BO2's corresponding
                // notify accepts weapon zero as the initialized "none" asset.
                // CODDIFF(client_events): the source resolves nonzero assets
                // through the frozen loadout, alt, offhand or explicitly
                // resolved owned UAV capability; arbitrary assets still refuse.
                if (event.parameter < 0 ||
                    event.parameter > MaximumWeaponAssetIndex)
                {
                    return SV_ClientEventRefused(SvClientEventResult::Invalid, "switch-notify-parameter-range");
                }
                const auto targetWeaponAssetIndex =
                    static_cast<std::uint16_t>(event.parameter);
                const auto *targetWeapon = targetWeaponAssetIndex
                    ? findWeapon(targetWeaponAssetIndex)
                    : nullptr;
                SvResolvedWeapon offhandNotification;
                if (!targetWeapon && equipment)
                {
                    const auto *offhand = SV_FindOffhandWeapon(*equipment, targetWeaponAssetIndex);
                    if (offhand && std::ranges::any_of(playerState.heldWeapons, [&](const auto &slot) {
                            return slot.weaponAssetIndex == targetWeaponAssetIndex;
                        }))
                    {
                        offhandNotification.weaponAssetIndex = targetWeaponAssetIndex;
                        offhandNotification.weaponName = offhand->weaponName;
                        targetWeapon = &offhandNotification;
                    }
                }
                // The granted reward is outside the gun/offhand loadout.
                // Admit only the resolved UAV named by the owned key4 action;
                // this supplies the existing switch notification, not a shot.
                SvResolvedWeapon rewardNotification;
                if (!targetWeapon && targetWeaponAssetIndex && uavWeapon &&
                    targetWeaponAssetIndex == uavWeapon->weaponAssetIndex &&
                    playerState.rewardActionType == 1 &&
                    playerState.rewardActionWeapon == targetWeaponAssetIndex &&
                    std::ranges::any_of(playerState.heldWeapons, [&](const auto &slot) {
                        return slot.weaponAssetIndex == targetWeaponAssetIndex;
                    }))
                {
                    rewardNotification.weaponAssetIndex = targetWeaponAssetIndex;
                    rewardNotification.weaponName = "killstreak_uav_mp";
                    targetWeapon = &rewardNotification;
                }
                if (targetWeaponAssetIndex && !targetWeapon)
                {
                    // SECTION 190: AND NAME THE REFUSAL, because this one does
                    // not merely drop the switch -- Invalid rejects the WHOLE
                    // clientThink candidate (sv_snapshot_mp.cpp,
                    // ClientEventsRejected), so a weapon the resolved loadout
                    // does not carry stops the player's command dead.
                    //
                    // An alt-mode weapon is a SEPARATE weapon asset -- out.exe
                    // has weapon names like `altfirepechenegss_mp`, a weapClass
                    // `altmode`, and `mp/coAltWeaponAttachmentTable.csv`
                    // (sub_42FA00) which copies the base weapon's attachments
                    // onto it -- and SV_FindResolvedWeapon knows only the
                    // primary and the secondary. If alt-fire switches through
                    // this event, this is the line that will say so.
                    static std::string lastSwitchRefusal;
                    auto line = "weapon switch REFUSED target=" +
                        std::to_string(targetWeaponAssetIndex) + " primary=" +
                        std::to_string(resolvedLoadout
                            ? resolvedLoadout->primary.weaponAssetIndex
                            : 0) +
                        " secondary=" +
                        std::to_string(resolvedLoadout
                            ? resolvedLoadout->secondary.weaponAssetIndex
                            : 0) +
                        " current=" +
                        std::to_string(playerState.currentWeaponAssetIndex) +
                        " (not in the resolved loadout)";
                    if (line != lastSwitchRefusal)
                    {
                        lastSwitchRefusal = line;
                        OlMod::RuntimeLog::write(
                            OlMod::RuntimeLog::Channel::GameServer, line);
                    }
                    return SV_ClientEventRefused(SvClientEventResult::Invalid, "switch-notify-target-weapon");
                }
                entity.pendingScriptNotifications.push_back({
                    .weaponAssetIndex = targetWeaponAssetIndex,
                    .weaponName = targetWeapon
                        ? targetWeapon->weaponName
                        : "none",
                });
                continue;
            }

            if (event.event == EventOffhandEndNotify ||
                event.event == EventReloadStartNotify ||
                event.event == EventReloadAddAmmo)
            {
                // BO1 and Ghosts HandleClientEvent only publish script
                // notifications for these events. PM_Weapon already owns the
                // authoritative timers and ammo mutation in this candidate.
                // TODO(CODOL): Publish the matching script notifications once
                // the game-script event owner is connected.
                continue;
            }

            // CODREF(fire_weapon): BO1 and Ghosts start FireWeapon from the
            // already converted gentity weapon. Requiring the projected entity
            // and authoritative playerState to agree prevents a stale source
            // loadout from selecting a different definition.
            const auto weaponAssetIndex =
                entity.networkState.weaponAssetIndex;
            const auto *const weapon = findWeapon(weaponAssetIndex);
            const auto fireEvent = SV_DecodeFireWeaponEvent(event);
            if (!fireEvent || !resolvedLoadout || !weapon ||
                playerState.currentWeaponAssetIndex != weaponAssetIndex)
            {
                return SV_ClientEventRefused(SvClientEventResult::Invalid, "fire-weapon-or-loadout-mismatch");
            }
            if (!fireBasisBuilder)
                return SV_ClientEventRefused(SvClientEventResult::Unsupported, "fire-no-basis-builder");
            // CODDIFF(fire_weapon): native FireWeapon builds muzzle axes and
            // spread from live gentity/gclient state. The source bridge keeps
            // that work behind evidence-constrained builders so no guessed
            // gclient layout leaks into this event dispatcher.
            const auto fireBasis = fireBasisBuilder(*weapon);
            const auto fireSpread = SV_CalculateWeaponSpread({
                .viewHeightCurrent = playerState.viewHeightCurrent,
                .playerSizeScale = playerState.playerSizeScale,
                .weaponPositionFraction = playerState.weaponPositionFraction,
                .normalizedAimSpreadScale = currentAimSpreadScale,
                .spreadOverride = playerState.spreadOverride,
                .spreadOverrideState = playerState.spreadOverrideState,
                .hipSpreadStandMin = weapon->hipSpreadStandMin,
                .hipSpreadCrouchMin = weapon->hipSpreadCrouchMin,
                .hipSpreadProneMin = weapon->hipSpreadProneMin,
                .hipSpreadStandMax = weapon->hipSpreadStandMax,
                .hipSpreadCrouchMax = weapon->hipSpreadCrouchMax,
                .hipSpreadProneMax = weapon->hipSpreadProneMax,
                .adsSpread = weapon->adsSpread,
                .perkSpreadScale = perkSpreadScale,
            });
            if (!fireBasis ||
                !fireSpread ||
                fireBasis->weaponAssetIndex != weaponAssetIndex ||
                fireBasis->weaponType != weapon->weaponType ||
                !SV_IsWeaponFireBasisValid(*fireBasis))
            {
                return SV_ClientEventRefused(SvClientEventResult::Failed, "fire-basis-or-spread");
            }
            logWeaponSpreadSample(
                playerState,
                *weapon,
                *fireBasis,
                *fireSpread,
                currentAimSpreadScale,
                perkSpreadScale);
            if (!fireWeaponHandler)
            {
                if (weapon->weaponType != WeaponTypeBullet)
                    return SV_ClientEventRefused(SvClientEventResult::Unsupported, "fire-non-bullet-no-handler");
                // Native PM_Weapon has already advanced weapon state, timers,
                // animation, spread and ammo. Commit that deterministic state
                // now, but do not pretend Bullet_Process/G_Damage ran.
                deferredImpact = true;
                continue;
            }
            // OLMOD(client-event-result): handlers mutate only the outer
            // command candidate. The original engines perform these effects
            // synchronously; publication is delayed here until the source and
            // native entity mirror can commit atomically.
            const auto fireResult = fireWeaponHandler(
                    playerState,
                    entity,
                    *weapon,
                    *fireBasis,
                    *fireSpread,
                    *fireEvent);
            if (playerState.currentWeaponAssetIndex != weaponAssetIndex ||
                entity.networkState.weaponAssetIndex != weaponAssetIndex)
            {
                return SV_ClientEventRefused(SvClientEventResult::Failed, "fire-weapon-changed-during-fire");
            }
            switch (fireResult)
            {
            case SvFireWeaponResult::Applied:
                break;
            case SvFireWeaponResult::DeferredImpact:
                deferredImpact = true;
                break;
            case SvFireWeaponResult::Failed:
            default:
                // OLMOD(client-fire-handler-result): fail closed if a corrupt
                // or version-skewed callback returns an unknown enum value.
                return SV_ClientEventRefused(SvClientEventResult::Failed, "fire-handler-result");
            }
            // EVERY OTHER CLIENT LEARNS ABOUT THIS SHOT HERE, AND NOWHERE ELSE.
            //
            // MEASURED, not assumed. An entity-event probe on two live clients
            // (Tools/olfinal/entity-event-probe.py) shows remote entity events
            // dispatching perfectly -- client 1 received 140 of client 0's
            // footsteps, jumps and weapon raises -- while a fire event NEVER
            // crosses: id 54 appears only ever on a client's OWN entity, which
            // is its own prediction. The server's own histogram agrees:
            //
            //     entity-events sent 25:4 31:86 32:3 33:85 152:183 153:90
            //                        154:31 156:58 157:43 158:17
            //
            // reload, raise, putaway, footsteps, jumps, landings -- and no fire
            // event of any kind. The playerState predictable ring carries the
            // server-only id (that is how the bullet path works); the ENTITY
            // ring never gets it, because BG_PlayerStateToEntityState does not
            // copy server-only ids into es.events.
            //
            // So this is an ADDITION, not a translation. Retail's dm demo sends
            // (41, 0) on ET_PLAYER 2250 times and (42, 0) 85 times -- parameter
            // always zero -- and CG_EntityEvent case 41 is what feeds both the
            // remote weapon sound and the compass blip (sub_595DF0 sets bit 0
            // of the blip flags at +0x70 with a freshness stamp at +0x58, which
            // is exactly what CG_DrawCompassBlip requires to draw a dot).
            SV_AddEntityPresentationEvent(
                entity, SV_PresentationFireEventId(event.event));
        }
        return deferredImpact
            ? SvClientEventResult::DeferredImpact
            : SvClientEventResult::Applied;
    }

    bool SV_HandleClientEvents(
        SvPlayerState &playerState,
        SvGameEntity &entity,
        const float currentAimSpreadScale,
        const SvResolvedLoadout *const resolvedLoadout,
        const std::span<const SvNativePredictableEvent> events,
        const SvWeaponFireBasisBuilder &fireBasisBuilder,
        const SvFireWeaponHandler &fireWeaponHandler)
    {
        // OLMOD(client-event-bool-adapter): compatibility wrapper used only by
        // callers that do not need the explicit deferred/unsupported reason.
        const auto result = SV_HandleClientEventsDetailed(
                   playerState,
                   entity,
                   currentAimSpreadScale,
                   resolvedLoadout,
                   events,
                   fireBasisBuilder,
                   fireWeaponHandler);
        return result == SvClientEventResult::Applied ||
            result == SvClientEventResult::DeferredImpact;
    }
}
