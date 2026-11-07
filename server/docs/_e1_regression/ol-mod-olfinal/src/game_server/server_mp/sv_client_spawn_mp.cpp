#include "sv_client_spawn_mp.hpp"

#include "sv_client_events_mp.hpp"

#include "qcommon/com_math.hpp"
#include "sv_native_playerstate_mp.hpp"
#include "sv_snapshot_mp.hpp"

#include <algorithm>
#include <cmath>
#include <utility>
#include <vector>

namespace CodolGameServer
{
    namespace
    {
        // CODREF(client_spawn): CODOL-local entity/playerstate limits plus the
        // BO1/Ghosts common respawn transition constants used by this subset.
        constexpr std::uint32_t MaxClientNum = 63;
        constexpr std::uint32_t MaxEntityNum = 2047;
        constexpr std::uint32_t EFlagTeleportBit = 1u << 1;
        constexpr std::uint32_t PmFlagRespawned = 1u << 10;
        constexpr std::uint32_t SpawnClearedButtonMask = 0x300;
        constexpr std::uint16_t WeaponAnimationToggleBit = 0x400;

        // OLMOD(client-spawn-input-validation): source admission helper; native
        // ClientSpawn relies on engine assertions and already-owned vectors.
        bool finiteVector(const std::array<float, 3> &value)
        {
            return std::ranges::all_of(value, [](const float component) {
                return std::isfinite(component);
            });
        }

        bool equipResolvedLoadout(
            SvPlayerState &playerState,
            const SvResolvedLoadout &loadout,
            const bool unarmed = false,
            const std::uint16_t unarmedWeaponAssetIndex = 0)
        {
            // CODDIFF(client_spawn): BO1/Ghosts ClientSpawn rebuilds player and
            // entity state but does not perform this frozen-loadout projection.
            // The project combines them so source/native spawn publication is
            // atomic while the original script-side give-weapon owner is absent.
            if (!SV_IsResolvedLoadoutValid(loadout))
                return false;

            playerState.currentWeaponAssetIndex = unarmed
                ? unarmedWeaponAssetIndex
                : static_cast<std::uint16_t>(loadout.primary.weaponAssetIndex);
            for (auto &animation : playerState.weaponAnim)
            {
                animation = static_cast<std::uint16_t>(
                    (~animation) & WeaponAnimationToggleBit);
            }
            playerState.weaponTime = {};
            playerState.weaponDelay = {};
            playerState.weaponRestrictKickTime = {};
            playerState.weaponState = {};
            playerState.weaponHandFlags = {};
            playerState.weaponShotCount = {};
            playerState.heldWeapons = {};
            playerState.ammoClips = {};
            playerState.ammoPools = {};
            // EVERYTHING BELOW FILLS THE HANDS. An unarmed spawn keeps the zeroed
            // weapon state above -- no current weapon, no held weapons, no clips, no
            // pools -- and skips the loadout projection, the alt-weapon pass and the
            // ammo compaction entirely, because every one of them exists to place a
            // weapon the player is not supposed to have yet.
            if (unarmed)
            {
                // Held, so the client has something to draw and to switch back to.
                // heldBefore suppresses the first-pickup animation on a weapon the
                // player is simply standing there with.
                if (unarmedWeaponAssetIndex)
                {
                    playerState.heldWeapons[0].weaponAssetIndex =
                        unarmedWeaponAssetIndex;
                    playerState.heldWeapons[0].heldBefore = true;
                }
                return true;
            }
            playerState.heldWeapons[0].weaponAssetIndex = static_cast<std::uint16_t>(
                loadout.primary.weaponAssetIndex);
            playerState.heldWeapons[0].heldBefore = true;
            // ownedWeaponRecord[1] is the native pair-held flag. It is not the
            // partner weapon index; that distinct index comes from the client's
            // real usercmd and WeaponDef+0xE88 during a weapon change.
            playerState.heldWeapons[0].unknownState[0] =
                loadout.primary.dualWieldCapable;
            playerState.heldWeapons[1].weaponAssetIndex = static_cast<std::uint16_t>(
                loadout.secondary.weaponAssetIndex);
            playerState.heldWeapons[1].heldBefore = true;
            playerState.heldWeapons[1].unknownState[0] =
                loadout.secondary.dualWieldCapable;

            // SECTION 190: AND EACH WEAPON'S ALT, BECAUSE A GUN YOU CAN SWITCH
            // TO AND CANNOT FIRE IS NOT A WORKING ALT-FIRE.
            //
            // Most alts share the host's clip -- sub_42EF60 copies the host's
            // clip index onto the alt when the alt's +3866 is set, which is why
            // the CSG12's ammo does not change and the AK masterkey's does --
            // and those coalesce into the same slot below at no cost. The ones
            // with their OWN clip and ammo index would otherwise spawn empty.
            //
            // heldWeapons has fifteen slots and the loadout fills two, so there
            // is room; a weapon with no alt adds nothing.
            std::vector<SvResolvedWeapon> resolvedWeapons{
                loadout.primary, loadout.secondary };
            {
                auto held = std::size_t{ 2 };
                for (const auto &base : { loadout.primary, loadout.secondary })
                {
                    // SECTION 191z: ...FOR_HOST. `SV_LookupAltWeapon` takes an
                    // ALT and resolves it -- "returns false when the index is
                    // not an alt of anything", its own header says -- and this
                    // handed it the HOST. It returned false every time, for
                    // every weapon in every class, and the loop below never ran
                    // once since section 190 shipped it.
                    //
                    // Measured, not inferred: the always-on `weapon slots` line
                    // prints the held array and it read
                    // `list2F4=1224,1226,0,0,0,0` on every sample -- primary,
                    // secondary, and nothing. out.exe refuses a cmd.weapon that
                    // is not in that array and stores a ZERO instead
                    // (finish-weapon-change, 0x00424470), which is exactly
                    // what the alt-weapon trace caught:
                    // `03-post-pmove ps=1225 native=0`.
                    SvResolvedWeapon alt{};
                    if (!SV_LookupAltWeaponForHost(base.weaponAssetIndex, alt))
                        continue;
                    resolvedWeapons.push_back(alt);
                    if (held < playerState.heldWeapons.size())
                    {
                        playerState.heldWeapons[held].weaponAssetIndex =
                            alt.weaponAssetIndex;
                        playerState.heldWeapons[held].heldBefore = true;
                        ++held;
                    }
                }
            }
            for (const auto &weapon : resolvedWeapons)
            {
                // OLMOD(client-spawn-loadout-bootstrap): compact the two frozen
                // definitions into CODOL's confirmed 15 clip/pool slots. Shared
                // indexes deliberately coalesce into one slot.
                auto clip = std::ranges::find_if(
                    playerState.ammoClips,
                    [&weapon](const SvAmmoClipState &candidate) {
                        return candidate.clipIndex == weapon.clipIndex;
                    });
                if (clip == playerState.ammoClips.end())
                {
                    clip = std::ranges::find_if(
                        playerState.ammoClips,
                        [](const SvAmmoClipState &candidate) {
                            return !candidate.clipIndex;
                        });
                }
                if (clip != playerState.ammoClips.end())
                {
                    clip->clipIndex = weapon.clipIndex;
                    clip->count[0] = std::max(clip->count[0], weapon.clipSize);
                    if (weapon.dualWieldCapable)
                    {
                        clip->count[1] = std::max(
                            clip->count[1], weapon.clipSize);
                    }
                }

                auto pool = std::ranges::find_if(
                    playerState.ammoPools,
                    [&weapon](const SvAmmoPoolState &candidate) {
                        return candidate.ammoIndex == weapon.ammoIndex;
                    });
                if (pool == playerState.ammoPools.end())
                {
                    pool = std::ranges::find_if(
                        playerState.ammoPools,
                        [](const SvAmmoPoolState &candidate) {
                            return !candidate.ammoIndex;
                        });
                }
                if (pool != playerState.ammoPools.end())
                {
                    pool->ammoIndex = weapon.ammoIndex;
                    // TODO(CODOL): recover the exact script/give-ammo policy for
                    // two equipped weapons sharing one ammo index. The source
                    // currently sums their definition maxima, matching the
                    // existing setweaponammostock cap owner, but this is not
                    // claimed as native ClientSpawn behavior. Exit when the
                    // CODOL give-weapon/add-ammo chain and a shared-index loadout
                    // fixture establish the authoritative cap.
                    pool->count = static_cast<std::uint16_t>(
                        std::min<std::uint32_t>(
                            0x7FF,
                            static_cast<std::uint32_t>(pool->count) +
                                weapon.maxAmmo));
                }
            }
            return true;
        }
    }

    bool SV_ClientSpawn(
        SvPlayerState &playerState,
        SvNativePlayerState &nativePlayerState,
        const SvClientSpawnConfig &config,
        const SvResolvedLoadout &loadout,
        const char **const failureReason)
    {
        const auto refuse = [failureReason](const char *const reason) {
            if (failureReason)
                *failureReason = reason;
            return false;
        };
        // CODREF(client_spawn): BO1 ClientSpawn 0x00600EC0, Ghosts
        // 0x140119690 and BO2 0x005C2200 clear and rebuild player ownership,
        // toggle eFlags bit 2, set pm_flags 0x400, establish view/origin, then
        // run ClientEndFrame and the first ClientThink_real.
        // CODDIFF(client_spawn): this source function owns only the confirmed
        // playerState/native-playerState subset and resolved loadout. Native
        // gentity/gclient session, script fields, HUD and first-think ownership
        // remain outside this transaction.
        // OLMOD(client-spawn-admission): reject before constructing either
        // owner so invalid profile/runtime input cannot partially reset a player.
        if (config.clientNum > MaxClientNum)
            return refuse("admission/clientNum");
        if (!finiteVector(config.origin))
            return refuse("admission/origin_not_finite");
        if (!finiteVector(config.angles))
            return refuse("admission/angles_not_finite");
        if (config.groundEntityNum > MaxEntityNum)
            return refuse("admission/groundEntityNum");
        if (!config.gravity)
            return refuse("admission/gravity_zero");
        if (!config.speed)
            return refuse("admission/speed_zero");
        if (!std::isfinite(config.moveSpeedScaleMultiplier) ||
            config.moveSpeedScaleMultiplier <= 0.0f)
        {
            return refuse("admission/moveSpeedScaleMultiplier");
        }
        if (config.viewmodelIndex > 0x3FF)
            return refuse("admission/viewmodelIndex");
        if (!config.maxHealth || config.maxHealth > 0xFF)
            return refuse("admission/maxHealth");
        if (!SV_IsResolvedLoadoutValid(loadout))
            return refuse("admission/resolved_loadout_invalid");

        // OLMOD(client-spawn-source-candidate): rebuild the confirmed subset in
        // an isolated candidate; fields without evidence remain zero rather
        // than inheriting stale state across lives.
        SvPlayerState next{
            .clientNum = config.clientNum,
            .commandTime = config.userCmd
                ? config.userCmd->commandTime
                : config.serverTime,
            .pmType = 0,
            .pmFlags = PmFlagRespawned,
            .eFlags = playerState.eFlags ^ EFlagTeleportBit,
            .otherFlags = PlayerOtherFlagPlayer,
            // SvRetailLivePerks is a retail OLfinal player's own word triple,
            // and the perks it names ARE established now - mp/coPerkStatsTable
            // .csv, 77 rows, out of code_post_gfx_mp.ff, decoded by
            // Tools/olfinal/perk-bits.py:
            //
            //   word 0 bit 2  -> row 2   PERKS_LIGHTWEIGHT   modMoveSpeedScale
            //   word 0 bit 7  -> row 7   PERKS_EXTREMECOND   modSprintTime -7
            //   word 1 bit 24 -> row 56  specialty_destroyer_armor
            //
            // So it is TWO player-facing perks and one internal armor
            // specialty, NOT the "three perks, so three icons" the old comment
            // here claimed. Bit n of word w is row w*32+n, and the encoder
            // turns 2,7,56 straight back into {132, 16777216, 0}.
            //
            // It is still a carried literal rather than this player's loadout:
            // SvResolvedLoadout has no perks to resolve from. The die handler
            // zeroes these, so every spawn re-asserts them.
            // ZERO ON SPAWN, on purpose. The client's perk HUD adds a perk
            // only on the frame its bit goes clear-in-cache to set-in-ps
            // (sub_52B8E0), so writing the final value here would spend the
            // only edge there is before the HUD is necessarily alive.
            // ServerCore re-asserts the real value a moment later, which is
            // what retail's own traffic does on every life.
            .perks = {},
            .origin = config.origin,
            .gravity = config.gravity,
            .speed = config.speed,
            .moveSpeedScaleMultiplier = config.moveSpeedScaleMultiplier,
            .viewAngles = config.angles,
            .proneTransitionStartTime = 0,
            .weaponAnim = playerState.weaponAnim,
            .viewmodelIndex = config.viewmodelIndex,
            .damageEvent = 0,
            .damageYaw = 0,
            .damagePitch = 0,
            .damageCount = 0,
            .health = config.maxHealth,
            .maxHealth = config.maxHealth,
            .deadYaw = 0,
            .shellshockIndex = 0,
            .shellshockTime = 0,
            .shellshockDuration = 0,
            .spawnGeneration = static_cast<std::uint8_t>(
                playerState.spawnGeneration + 1),
            .viewHeightCurrent = 60.0f,
            .viewHeightTarget = 60,
            .viewHeightLerpTarget = 60,
            // CODDIFF(client_spawn): CODOL adds playerSizeScale at
            // playerState +0x98 and projects it through entityState +0x54 to
            // DObj_s +0xC8. BO1/Ghosts ClientSpawn do not provide this field.
            // OLMOD(section-84): +0x98 is 3.3.3.3's. On out.exe the field is at
            // +0xAC -- read off its own height family, seven functions at
            // 0x004104B0..0x004105D0 that all do `fld [eax+0ACh]` and multiply
            // by 15/70/50/30/60/40/11, the same seven constants in the same
            // order as 3.3.3.3's 0x00412410..0x00412530. So the 60 below is
            // this build's number too, not an inherited one.
            // Preserve the authoritative pre-spawn value established by the
            // player initializer instead of silently re-hardcoding normal
            // scale on every respawn.
            //
            // BUT ZERO IS NOT AN AUTHORITATIVE VALUE, IT IS AN UNSET ONE. The field
            // is `float playerSizeScale{}` and nothing in this tree ever assigns it,
            // so a first spawn preserved 0.0 and published it. EngineBindings records
            // the meaning: PM_GetStandHeight = round(playerSizeScale * 60), and this
            // same struct hardcodes viewHeightCurrent to 60.0f -- which IS scale 1.0.
            // A player was therefore published at zero size while standing 60 units
            // tall, and the client drew a viewmodel that filled the entire screen.
            // Preserve any positive value, which keeps the respawn intent intact, and
            // treat non-positive as unset.
            .playerSizeScale = playerState.playerSizeScale > 0.0f
                ? playerState.playerSizeScale
                : 1.0f,
            .groundEntityNum = config.groundEntityNum,
            .viewEntityNum = EntityNumNone,
            .movingPlatformEntityNum = EntityNumNone,
            .remoteEyesEntityNum = EntityNumNone,
            .remoteControlEntityNum = EntityNumNone,
            .remoteTurretEntityNum = EntityNumNone,
            .linkEntityNum = EntityNumNone,
        };
        if (config.userCmd)
        {
            for (std::size_t index = 0; index < next.deltaAngles.size(); ++index)
            {
                next.deltaAngles[index] = config.angles[index] -
                    BG_ShortToAngle(config.userCmd->angles[index]);
            }
            // BO1 bitarray resetBit(8/9) and Ghosts buttons &= ~0x300 agree
            // on this pre-first-think spawn gate. Preserve all other buttons.
            next.buttons = config.userCmd->buttons & ~SpawnClearedButtonMask;
            next.forwardMove = config.userCmd->forwardMove;
            next.rightMove = config.userCmd->rightMove;
        }
        // TODO(CODOL): recover SV_ClientEnterWorld/ClientSpawn's exact first
        // usercmd and commandTime baseline. This compatibility path uses the
        // caller-selected executed/received command and does not import the
        // reference servers' level.time - 100 assignment. Exit when a CODOL
        // server producer or natural wire/runtime capture closes that owner.
        if (!equipResolvedLoadout(
                next, loadout, config.unarmed, config.unarmedWeaponAssetIndex))
            return refuse("equip_resolved_loadout");

        // OLMOD(client-spawn-native-transaction): zero the entire 0x3564 native
        // buffer, project every confirmed field, and prove a lossless round trip
        // before publishing either source or native owner.
        SvNativePlayerState nextNative{};
        SV_OverlayPlayerStateToNative(next, nextNative);
        auto roundTrip = next;
        // THIS GATE IS A ROUND TRIP OVER A PER-BUILD NATIVE LAYOUT, and it is an
        // equality on the WHOLE struct: any single field the 1649370 projection loses
        // or reorders refuses the spawn outright, with a symptom miles from the cause.
        // Separate "the overlay refused" from "the overlay lost something".
        const char *overlayFailure = "unset";
        if (!SV_OverlayNativePlayerStateToPlayerState(
                nextNative, roundTrip, &overlayFailure))
        {
            if (failureReason)
                *failureReason = overlayFailure;
            return false;
        }
        if (roundTrip != next)
            return refuse("native_round_trip_mismatch");

        playerState = std::move(next);
        // AN UNARMED SPAWN HANDS THE ENGINE NO WEAPON AT ALL.
        //
        // The source copy keeps dmz_empty_mp, because that is what the CLIENT needs to
        // draw a pair of hands. The native buffer must not: the weapon-movement stage
        // reads the current weapon out of it and refuses any nonzero value that is not
        // in the frozen loadout, and empty hands can never be in a loadout -- the
        // validator demands a clip, an ammo pool and a fire time, and fists have none.
        // A refused stage discards the usercmd, and a discarded usercmd is the player
        // snapping back to spawn. MEASURED: 4,253 of them in one session, all
        // `weapon=1137`.
        //
        // AFTER THE ROUND TRIP, DELIBERATELY. The gate above compares the whole
        // projected struct back against the source and refuses the spawn on any
        // difference, so zeroing this before it would refuse every unarmed spawn.
        // This is the one field the two copies are allowed to disagree about, and the
        // think re-establishes the source side at the end of every frame.
        if (config.unarmed)
            SV_SetNativePlayerStateCurrentWeapon(nextNative, 0);
        // A zeroed native image disables scoped camera sway: sub_4355D0
        // multiplies it by this value. Retail starts every life at 1.0 and lets
        // PM_UpdateHoldBreath evolve both fields from there.
        SV_SetNativeHoldBreathState(nextNative, 1.0f, 0);
        nativePlayerState = std::move(nextNative);
        return true;
    }

    bool SV_EquipResolvedLoadout(
        SvPlayerState &playerState,
        const SvResolvedLoadout &loadout)
    {
        // OLMOD(client-loadout-refresh-adapter): compatibility owner for a
        // sequence change after spawn. The next command reprojects this source
        // state to native storage; this is not a recovered CODOL server entry.
        auto next = playerState;
        if (!equipResolvedLoadout(next, loadout))
            return false;
        playerState = std::move(next);
        return true;
    }
}
