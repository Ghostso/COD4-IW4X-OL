#include "sv_native_playerstate_mp.hpp"

#include "sv_snapshot_mp.hpp"

#include "../../shared/RuntimeLog.hpp"

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <limits>
#include <type_traits>
#include <utility>

namespace CodolGameServer
{
    namespace
    {
        // CODREF(pmove): CODOL playerState_s is exactly 0x3564 bytes; Pmove
        // 0x0041E860 and its retained helpers mutate this caller-owned image.
        // BO1 Pmove 0x004385F0 and Ghosts 0x140082BE0 confirm ownership and
        // control-flow responsibility, but their field layouts are not used.
        // OLMOD(native-playerstate-source-view): only CODOL fields confirmed
        // by i64 producers/consumers or wire descriptors are named below.
        // CODDIFF(1649370): EVERY OFFSET BELOW WAS 3.3.3.3's. playerState_s
        // grew in eight places between the builds -- +0 at the head, then +20,
        // +72, +80, +184, +192, +196, +224 and on out to +1048 in the tail --
        // and the whole per-client image went 0x3564 -> 0x3BBC bytes. The map
        // came from aligning the two builds' EXTRACTED NETFIELD TABLES, which
        // are a byte-exact description of both layouts, and every offset the
        // alignment could not place on its own was then read out of out.exe:
        //
        //   BG_PlayerStateToEntityState  A sub_4131A0 <-> C sub_411360, line
        //     for line, gives clientNum 0x144 -> 0x158, legs 0x0C8 -> 0x0DC,
        //     torso 0x0D0 -> 0x0E4, health 0x190 -> 0x1A4, maxHealth 0x198 ->
        //     0x1AC and eFlags 0x0F0 -> 0x104.
        //   the held-weapon walker  A sub_55CFE0 <-> C sub_594840, identical
        //     `(v + 16) % 15` loop, gives heldWeapons 0x2A4 -> 0x2F4.
        //   the ammo-pool inserter  A sub_42F820 <-> C sub_4331A0, identical
        //     fifteen-entry stride-8 scan, gives ammoPools 0x364 -> 0x41C, and
        //     the clip base 0x3DC -> 0x494 falls out of the same +0x78.
        //   the objective block is 32 records on both builds: 32 * 0x24 fills
        //     A's gap exactly and 32 * 0x2C fills this one, so the stride grew
        //     with the two fields the objective netfield table gained.
        //
        // Re-derive any of it with `Tools/olfinal/audit-native-offsets.py`.
        // NOTE(1649370): +0x10 is read through an obfuscated getter here --
        // C sub_411360 calls `dword_E60B78 ^ ps[36] ^ (ps+32)` with `ps+16` as
        // its argument where 3.3.3.3 read the dword directly. The OFFSET is
        // unchanged; whether a plain write to it is still seen the same way is
        // NOT established.
        constexpr std::size_t CommandTimeOffset = 0x000;
        constexpr std::size_t PmTypeOffset = 0x004;
        constexpr std::size_t PmTimeOffset = 0x008;
        constexpr std::size_t PmFlagsOffset = 0x00C;
        constexpr std::size_t OtherFlagsOffset = 0x010;
        // CODREF(1649370): sub_4442E0 writes the same three words that
        // sub_52B8E0 reads for the HUD, at playerState +0x584.
        // BO1 BG_SetPerk 0x60E0E0 and Ghosts PlayerCmd_SetPerk 0x14011A760
        // agree on player-state ownership; neither supplies CODOL's layout.
        constexpr std::size_t PerksOffset = 0x584;
        // CODREF(1649370): 5954F7 reads type at ps+640+4*slot;
        // 595532 reads the weapon at ps+654+4*slot. Key4 (+actionslot2)
        // dispatches slot1 at 5B3AF9. These are native dwords, despite
        // their two/eleven-bit wire domains (fields187/204).
        constexpr std::size_t RewardActionTypeOffset = 0x644;
        constexpr std::size_t RewardActionWeaponOffset = 0x658;
        constexpr std::size_t BobCycleOffset = 0x02c;
        constexpr std::size_t LinkFlagsOffset = 0x028;
        constexpr std::size_t OriginOffset = 0x030;
        constexpr std::size_t VelocityOffset = 0x03c;
        constexpr std::size_t MovingPlatformEntityOffset = 0x058;
        constexpr std::size_t RemoteEyesEntityOffset = 0x05c;
        constexpr std::size_t RemoteControlEntityOffset = 0x064;
        constexpr std::size_t RemoteTurretEntityOffset = 0x068;
        constexpr std::size_t GravityOffset = 0x0a4;
        constexpr std::size_t PlayerSizeScaleOffset = 0x0ac;
        constexpr std::size_t SpeedOffset = 0x0b0;
        constexpr std::size_t DeltaAnglesOffset = 0x0b4;
        constexpr std::size_t LadderVectorOffset = 0x0c4;
        constexpr std::size_t GroundEntityOffset = 0x0c0;
        constexpr std::size_t JumpTimeOffset = 0x0d0;
        constexpr std::size_t JumpOriginZOffset = 0x0d4;
        // CODREF(bg_update_player_dobj): which of these two pairs is the legs
        // and which the torso is READ FROM THE ENGINE, not assumed.
        //
        // OLMOD(section-84): EVERY ADDRESS BELOW IS 3.3.3.3's, INCLUDING THE
        // TABLES. out.exe's own body-part table is at VA 0x00E60558 and its
        // movetype table at 0x00E60290 (3.3.3.3: 0x00CE4B30 and 0x00CE48A0),
        // found by pointer-to-string search, and the body-part encoding is the
        // SAME 0/1/2/3 -- `** UNUSED **`, LEGS, TORSO, BOTH, stride 8.
        //
        // And the four offsets are confirmed from a source that was already on
        // disk: out.exe's OWN playerState netfield table
        // (re/demo-re/netfields-ol/playerstate-0x00DA8540.tsv) carries
        //   0xD8 16 bits   0xDC 12 bits   0xE0 16 bits   0xE4 12 bits
        // i.e. timer/anim, timer/anim, in this order and at these offsets --
        // 16-bit durations and 12-bit animation indices. So the +0x14 shift
        // from 3.3.3.3's 0xC4/0xC8/0xCC/0xD0 is right, and it is now measured
        // rather than derived. The prose below is 3.3.3.3's derivation, kept
        // because it is what established WHICH pair is which:
        //
        // CODOL's body-part name table at 0x00CE4B30 (stride 8, the same layout
        // as the movetype table at 0x00CE48A0) is
        //   0 "** UNUSED **"   1 "LEGS"   2 "TORSO"   3 "BOTH"
        // and the animation writer sub_AA9260 (VA 0x00409260) dispatches on
        // that value at 0x00409283: type 1 enters the block that writes
        // +0x0C4/+0x0C8, type 2 the block that writes +0x0CC/+0x0D0, and type 3
        // runs both. sub_AA9370 0x00409370 independently confirms the sense -
        // it captures the returned duration only for types 1 and 3, which is
        // the LEGS/BOTH duration that paces movement. BO1 BG_AnimScriptEvent
        // 0x006F5A40 and Ghosts 0x1400E6210 keep the same legs/torso pair.
        // These four were named the other way round until 2026-08-17, which
        // cost one wrong hitbox root cause: it read the healthy legs animation
        // as a stuck torso and the legitimately-zero torso as stuck legs.
        constexpr std::size_t LegsTimerOffset = 0x0d8;
        constexpr std::size_t LegsAnimOffset = 0x0dc;
        constexpr std::size_t TorsoTimerOffset = 0x0e0;
        constexpr std::size_t TorsoAnimOffset = 0x0e4;
        // CODREF(sv_write_snapshot_to_client): CODOL playerstate descriptor
        // field 15 reads signed movementDir from playerState_s +0x0EC.
        constexpr std::size_t MovementDirOffset = 0x100;
        constexpr std::size_t EFlagsOffset = 0x104;
        constexpr std::size_t PredictableEventSequenceOffset = 0x108;
        constexpr std::size_t PredictableEventsOffset = 0x10c;
        constexpr std::size_t ClientNumOffset = 0x158;
        constexpr std::size_t ViewmodelIndexOffset = 0x15c;
        constexpr std::size_t ViewAnglesOffset = 0x160;
        constexpr std::size_t ViewAngleClampBaseOffset = 0x180;
        constexpr std::size_t ViewAngleClampRangeOffset = 0x188;
        constexpr std::size_t LinkAnglesOffset = 0x220;
        constexpr std::size_t ViewHeightTargetOffset = 0x16c;
        constexpr std::size_t ViewHeightCurrentOffset = 0x170;
        constexpr std::size_t ViewHeightLerpTimeOffset = 0x174;
        constexpr std::size_t ViewHeightLerpTargetOffset = 0x178;
        constexpr std::size_t ViewHeightLerpDownOffset = 0x17c;
        constexpr std::size_t HealthStatOffset = 0x1A4;
        constexpr std::size_t DeadYawStatOffset = 0x1A8;
        constexpr std::size_t MaxHealthStatOffset = 0x1AC;
        constexpr std::size_t SpawnCountStatOffset = 0x1B0;
        constexpr std::size_t ProneDirectionOffset = 0x1e8;
        constexpr std::size_t ProneDirectionPitchOffset = 0x1ec;
        constexpr std::size_t ProneTorsoPitchOffset = 0x1f0;
        constexpr std::size_t ProneTransitionStartTimeOffset = 0x1f4;
        constexpr std::size_t DamageEventOffset = 0x1fc;
        constexpr std::size_t DamageYawOffset = 0x200;
        constexpr std::size_t DamagePitchOffset = 0x204;
        constexpr std::size_t DamageCountOffset = 0x208;
        constexpr std::size_t HealthOffset = 0x20c;
        constexpr std::size_t MaxHealthOffset = 0x214;
        constexpr std::size_t ViewEntityOffset = 0x238;
        constexpr std::size_t LinkEntityOffset = 0x248;
        constexpr std::size_t SprintButtonUpRequiredOffset = 0x284;
        constexpr std::size_t SprintDelayOffset = 0x288;
        constexpr std::size_t LastSprintStartOffset = 0x28c;
        constexpr std::size_t LastSprintEndOffset = 0x290;
        constexpr std::size_t SprintStartMaxLengthOffset = 0x294;
        // CODREF(PM_UpdateHoldBreath_OLfinal): sub_422D90 reads and writes
        // these exact fields. swayScale starts at 1.0, rises toward 4.5 after
        // breath exhaustion, and multiplies the scoped camera sway.
        constexpr std::size_t HoldBreathSwayScaleOffset = 0x298;
        constexpr std::size_t HoldBreathTimerOffset = 0x29C;
        constexpr std::size_t MoveSpeedScaleMultiplierOffset = 0x2a8;
        constexpr std::size_t MantleYawOffset = 0x2ac;
        constexpr std::size_t MantleTimerOffset = 0x2b0;
        constexpr std::size_t MantleTransitionIndexOffset = 0x2b4;
        constexpr std::size_t MantleFlagsOffset = 0x2b8;
        constexpr std::size_t RightWeaponAnimOffset = 0x2bc;
        constexpr std::size_t RightWeaponTimeOffset = 0x2c0;
        constexpr std::size_t RightWeaponDelayOffset = 0x2c4;
        constexpr std::size_t RightWeaponRestrictKickTimeOffset = 0x2c8;
        constexpr std::size_t RightWeaponStateOffset = 0x2cc;
        constexpr std::size_t RightWeaponHandFlagsOffset = 0x2d0;
        constexpr std::size_t RightWeaponShotCountOffset = 0x2d4;
        constexpr std::size_t LeftWeaponAnimOffset = 0x2d8;
        constexpr std::size_t LeftWeaponTimeOffset = 0x2dc;
        constexpr std::size_t LeftWeaponDelayOffset = 0x2e0;
        constexpr std::size_t LeftWeaponRestrictKickTimeOffset = 0x2e4;
        constexpr std::size_t LeftWeaponStateOffset = 0x2e8;
        constexpr std::size_t LeftWeaponHandFlagsOffset = 0x2EC;
        constexpr std::size_t LeftWeaponShotCountOffset = 0x2F0;
        constexpr std::size_t HeldWeaponIndexesOffset = 0x2F4;
        constexpr std::size_t HeldWeaponStatesOffset = 0x330;
        // CODDIFF(1649370): TWELVE, not five. The held-weapon state record
        // grew on this build and the stride was carried.
        //
        // The array's extent is not a guess. The playerState netfield table
        // names the field that comes AFTER it -- index 53 at +0x3E4 here and
        // +0x32C on 3.3.3.3 -- so the region is known on both builds:
        //     3.3.3.3   0x2E0 .. 0x32B   =  76 bytes / 15 = 5, +1 pad
        //     OLfinal   0x330 .. 0x3E3   = 180 bytes / 15 = 12, no pad
        // and 12 is the only integer stride that fits 180 into fifteen slots.
        // The same arithmetic reproduces every other array on both builds
        // exactly (held-weapon indexes 4, ammo pools 8, ammo clips 12,
        // objectives 0x24 there and 0x2C here), which is what makes the one
        // that did not mean something. CODOL-main
        // Tools/olfinal/audit-array-strides.py is that check, and it
        // calibrates on dest1yo's finished tree before it reports anything.
        //
        // THE WIRE SAYS THE SAME. This build's held-weapon record carries a
        // twelve-bit value 3.3.3.3's does not -- five flag bits then Bits(12),
        // per T3 of Tools/demo-re/codol_snapshot.py's ps_trailing and measured
        // as 0 in all 469 of its reads across the demo corpus. Five bools,
        // three bytes of padding and one dword is twelve.
        //
        // What it cost: with a stride of five, slot 0 landed correctly and the
        // other FOURTEEN wrote their flags inside earlier slots' padding. The
        // ol-mod read path used the same wrong stride, so the round trip
        // through this file agreed with itself and nothing reported anything;
        // only the engine, which uses the real stride, saw it.
        constexpr std::size_t HeldWeaponStateStride = 12;
        constexpr std::size_t OffhandWeaponOffset = 0x3E4;
        constexpr std::size_t CurrentWeaponOffset = 0x3f8;
        constexpr std::size_t WeaponPositionFractionOffset = 0x404;
        constexpr std::size_t AimSpreadScaleOffset = 0x408;
        constexpr std::size_t SpreadOverrideOffset = 0x410;
        constexpr std::size_t SpreadOverrideStateOffset = 0x414;
        // Cached BG_DualWieldActive result. OLFinal playerstate netfield 106
        // maps directly to this dword; snapshots must preserve the same bit.
        constexpr std::size_t DualWieldActiveOffset = 0x418;
        constexpr std::size_t AmmoPoolsOffset = 0x41C;
        constexpr std::size_t AmmoPoolStride = 8;
        constexpr std::size_t AmmoClipsOffset = 0x494;
        constexpr std::size_t AmmoClipStride = 12;
        // TODO(CODOL): descriptor field 4 proves a -70 time value at +0x4A4,
        // but its CODOL gameplay owner is not recovered. Ghosts' analogous
        // field is weaponIdleTime; do not promote that name without an OL xref.
        constexpr std::size_t Unk04A4TimeOffset = 0x568;
        constexpr std::size_t ShellshockIndexOffset = 0x68c;
        constexpr std::size_t ShellshockTimeOffset = 0x690;
        constexpr std::size_t ShellshockDurationOffset = 0x694;
        constexpr std::size_t ObjectivesOffset = 0x6C8;
        constexpr std::size_t ObjectiveStride = 0x2C;
        constexpr std::size_t ObjectiveOriginOffset = 0x04;
        // CODOL objectiveFields @ 0x00C56A78, and 0x00DA90A8 on out.exe:
        // origin +0x04/+0x08/+0x0C,
        // entNum +0x10 (11 bits), teamNum +0x14 (4 bits), icon +0x20
        // (12 bits).  BO1 uses the same semantic order but a narrower entNum.
        constexpr std::size_t ObjectiveEntityNumOffset = 0x10;
        constexpr std::size_t ObjectiveTeamNumOffset = 0x14;
        constexpr std::size_t ObjectiveIconOffset = 0x20;

        constexpr std::uint32_t MaximumClientNum = 63;
        constexpr std::uint32_t MaximumEntityNum = 2047;
        constexpr std::uint32_t MaximumWeaponIndex = 0x7FF;
        // CODDIFF(1649370): THE VIEWMODEL INDEX DID NOT WIDEN WITH THE WEAPON
        // INDEX. On 3.3.3.3 both fields are ten bits, so one constant served
        // both and nothing distinguished them. Here the weapon index is eleven
        // bits (playerState field 39, `currentWeapon`) and the viewmodel index
        // is still TEN (field 56, offset 0x15C). Validating the viewmodel
        // against 0x7FF admits values the snapshot writer then refuses under
        // `playerstate domain refused: viewmodelIndex`, which reports the
        // failure a whole stage away from the field that caused it.
        constexpr std::uint32_t MaximumViewmodelIndex = 0x3FF;
        constexpr std::uint32_t MaximumWeaponAnimation = 0xFFF;
        constexpr std::uint32_t MaximumWeaponState = 0x3F;
        constexpr std::uint32_t MaximumObjectiveState = 5;

        // OLMOD(native-playerstate-typed-overlay): these helpers access only
        // fixed offsets in the CODOL byte image catalog above. They do not
        // claim that SvNativePlayerState is a complete native structure.
        template <typename Value>
        void writeValue(
            SvNativePlayerState &state,
            const std::size_t offset,
            const Value &value)
        {
            static_assert(std::is_trivially_copyable_v<Value>);
            std::memcpy(state.bytes.data() + offset, &value, sizeof(value));
        }

        template <typename Value>
        [[nodiscard]] Value readValue(
            const SvNativePlayerState &state,
            const std::size_t offset)
        {
            static_assert(std::is_trivially_copyable_v<Value>);
            Value value{};
            std::memcpy(&value, state.bytes.data() + offset, sizeof(value));
            return value;
        }

        template <std::size_t Count>
        void writeFloatArray(
            SvNativePlayerState &state,
            const std::size_t offset,
            const std::array<float, Count> &value)
        {
            std::memcpy(
                state.bytes.data() + offset,
                value.data(),
                sizeof(float) * Count);
        }

        template <std::size_t Count>
        [[nodiscard]] std::array<float, Count> readFloatArray(
            const SvNativePlayerState &state,
            const std::size_t offset)
        {
            std::array<float, Count> value{};
            std::memcpy(
                value.data(),
                state.bytes.data() + offset,
                sizeof(float) * Count);
            return value;
        }

        template <std::size_t Count>
        [[nodiscard]] bool finite(const std::array<float, Count> &value)
        {
            for (const auto component : value)
            {
                if (!std::isfinite(component))
                    return false;
            }
            return true;
        }

        [[nodiscard]] bool validEntity(const std::int32_t value)
        {
            return value >= 0 &&
                static_cast<std::uint32_t>(value) <= MaximumEntityNum;
        }

        void writeWeaponAuxiliaryState(
            const SvPlayerState &source,
            SvNativePlayerState &destination)
        {
            // CODREF(pmove): CODOL playerState descriptors and PM_Weapon
            // consumers establish fifteen held-weapon, ammo-pool and clip
            // records at these exact offsets. Source types are a projection,
            // not the native aggregate declarations.
            for (std::size_t index = 0; index < source.heldWeapons.size(); ++index)
            {
                const auto &weapon = source.heldWeapons[index];
                writeValue(
                    destination,
                    HeldWeaponIndexesOffset + index * sizeof(std::uint32_t),
                    static_cast<std::uint32_t>(weapon.weaponAssetIndex));
                const auto stateOffset =
                    HeldWeaponStatesOffset + index * HeldWeaponStateStride;
                writeValue(
                    destination,
                    stateOffset,
                    static_cast<std::uint8_t>(weapon.heldBefore));
                for (std::size_t flag = 0; flag < weapon.unknownState.size(); ++flag)
                {
                    writeValue(
                        destination,
                        stateOffset + flag + 1,
                        static_cast<std::uint8_t>(weapon.unknownState[flag]));
                }
            }
            for (std::size_t index = 0; index < source.ammoPools.size(); ++index)
            {
                const auto offset = AmmoPoolsOffset + index * AmmoPoolStride;
                writeValue(
                    destination,
                    offset,
                    static_cast<std::int32_t>(source.ammoPools[index].ammoIndex));
                writeValue(
                    destination,
                    offset + sizeof(std::int32_t),
                    static_cast<std::int32_t>(source.ammoPools[index].count));
            }
            for (std::size_t index = 0; index < source.ammoClips.size(); ++index)
            {
                const auto offset = AmmoClipsOffset + index * AmmoClipStride;
                writeValue(
                    destination,
                    offset,
                    static_cast<std::int32_t>(source.ammoClips[index].clipIndex));
                writeValue(
                    destination,
                    offset + sizeof(std::int32_t),
                    static_cast<std::int32_t>(source.ammoClips[index].count[0]));
                writeValue(
                    destination,
                    offset + sizeof(std::int32_t) * 2,
                    static_cast<std::int32_t>(source.ammoClips[index].count[1]));
            }
        }

        [[nodiscard]] bool readWeaponAuxiliaryState(
            const SvNativePlayerState &source,
            SvPlayerState &destination,
            const char **const failureReason = nullptr)
        {
            // THREE LOOPS, THREE MULTI-TERM RETURNS, ONE WORD. Say which record kind and
            // which term, and include the value -- a bound that rejects a legitimate
            // index looks identical to a genuinely corrupt read until you can see it.
            const auto refuse = [failureReason](const char *const reason) {
                if (failureReason)
                    *failureReason = reason;
                return false;
            };
            // OLMOD(native-playerstate-aux-admission): validate every record,
            // including uniqueness, before the caller publishes its candidate.
            // destination is itself the caller's private next-state copy.
            std::array<bool, MaximumWeaponIndex + 1> weaponIndexes{};
            std::array<bool, MaximumWeaponIndex + 1> ammoIndexes{};
            std::array<bool, MaximumWeaponIndex + 1> clipIndexes{};
            for (std::size_t index = 0; index < destination.heldWeapons.size(); ++index)
            {
                auto &weapon = destination.heldWeapons[index];
                const auto weaponIndex = readValue<std::uint32_t>(
                    source,
                    HeldWeaponIndexesOffset + index * sizeof(std::uint32_t));
                const auto stateOffset =
                    HeldWeaponStatesOffset + index * HeldWeaponStateStride;
                const auto heldBefore = readValue<std::uint8_t>(source, stateOffset);
                std::array<std::uint8_t, 4> flags{};
                for (std::size_t flag = 0; flag < flags.size(); ++flag)
                    flags[flag] = readValue<std::uint8_t>(
                        source, stateOffset + flag + 1);
                if (weaponIndex > MaximumWeaponIndex)
                    return refuse("heldWeapon/index_out_of_range");
                if (heldBefore > 1)
                    return refuse("heldWeapon/heldBefore_not_boolean");
                if (std::ranges::any_of(flags,
                        [](const std::uint8_t value) { return value > 1; }))
                {
                    return refuse("heldWeapon/flag_not_boolean");
                }
                if (weaponIndex && std::exchange(weaponIndexes[weaponIndex], true))
                    return refuse("heldWeapon/duplicate_index");
                weapon.weaponAssetIndex = static_cast<std::uint16_t>(weaponIndex);
                weapon.heldBefore = heldBefore != 0;
                for (std::size_t flag = 0; flag < flags.size(); ++flag)
                    weapon.unknownState[flag] = flags[flag] != 0;
            }
            for (std::size_t index = 0; index < destination.ammoPools.size(); ++index)
            {
                auto &pool = destination.ammoPools[index];
                const auto offset = AmmoPoolsOffset + index * AmmoPoolStride;
                const auto ammoIndex = readValue<std::int32_t>(source, offset);
                const auto count = readValue<std::int32_t>(
                    source, offset + sizeof(std::int32_t));
                // CODDIFF(1649370): 0x3FF and 0x7FF WERE 3.3.3.3's TEN- AND ELEVEN-BIT
                // WIDTHS. This build writes the pool index in 11 bits and the count in
                // 12 (AmmoPoolIndexBits/AmmoPoolCountBits in sv_snapshot_mp.cpp), and
                // EngineBindings already validates weapon defs against 0x7FF. This copy
                // was missed, so a legitimate ammo index -- the wire carries 1188 and
                // 1297, both past 0x3FF -- failed the reverse admission, which refused
                // the native round trip, which refused the spawn. One constant in more
                // than one file, exactly as section 36a wrote down.
                if (ammoIndex < 0 || ammoIndex > 0x7FF)
                    return refuse("ammoPool/index_out_of_range");
                if (count < 0 || count > 0xFFF)
                    return refuse("ammoPool/count_out_of_range");
                if (!ammoIndex && count)
                    return refuse("ammoPool/count_without_index");
                if (ammoIndex && std::exchange(ammoIndexes[ammoIndex], true))
                    return refuse("ammoPool/duplicate_index");
                pool.ammoIndex = static_cast<std::uint16_t>(ammoIndex);
                pool.count = static_cast<std::uint16_t>(count);
            }
            for (std::size_t index = 0; index < destination.ammoClips.size(); ++index)
            {
                auto &clip = destination.ammoClips[index];
                const auto offset = AmmoClipsOffset + index * AmmoClipStride;
                const auto clipIndex = readValue<std::int32_t>(source, offset);
                const std::array counts{
                    readValue<std::int32_t>(
                        source, offset + sizeof(std::int32_t)),
                    readValue<std::int32_t>(
                        source, offset + sizeof(std::int32_t) * 2),
                };
                // AmmoClipIndexBits is 11 on this build, so the last usable index is
                // 0x7FE and -1 stays the empty sentinel. EngineBindings agrees.
                if (clipIndex < -1 || clipIndex > 0x7FE)
                    return refuse("ammoClip/index_out_of_range");
                if (std::ranges::any_of(counts, [](const std::int32_t count) {
                        return count < 0 || count > 0x1FF;
                    }))
                {
                    return refuse("ammoClip/count_out_of_range");
                }
                if (!clipIndex && (counts[0] || counts[1]))
                    return refuse("ammoClip/count_without_index");
                if (clipIndex > 0 && std::exchange(clipIndexes[clipIndex], true))
                    return refuse("ammoClip/duplicate_index");
                // TODO(CODOL): recover the exact -1 versus 0 empty-clip
                // sentinel policy from MSG_ReadDeltaPlayerstate and the ammo
                // helpers before tightening nonzero counts for clipIndex -1.
                // Exit when both native read and write consumers agree and a
                // fixed wire/native fixture covers each sentinel.
                clip.clipIndex = static_cast<std::int16_t>(clipIndex);
                clip.count = {
                    static_cast<std::uint16_t>(counts[0]),
                    static_cast<std::uint16_t>(counts[1]),
                };
            }
            return true;
        }

        void writeObjectives(
            const SvPlayerState &source,
            SvNativePlayerState &destination)
        {
            // CODREF(sd_objectives): CODOL objectiveFields 0x00C56A78
            // (out.exe 0x00DA90A8) proves
            // the 32 records and their state/origin/entity/team/icon layout.
            for (std::size_t index = 0; index < source.objectives.size(); ++index)
            {
                const auto offset = ObjectivesOffset + index * ObjectiveStride;
                const auto &objective = source.objectives[index];
                writeValue(destination, offset,
                    static_cast<std::int32_t>(objective.state));
                writeFloatArray(destination, offset + ObjectiveOriginOffset,
                    objective.origin);
                writeValue(destination, offset + ObjectiveIconOffset,
                    static_cast<std::int32_t>(objective.icon));
                writeValue(destination, offset + ObjectiveEntityNumOffset,
                    static_cast<std::int32_t>(objective.entityNum));
                writeValue(destination, offset + ObjectiveTeamNumOffset,
                    static_cast<std::int32_t>(objective.teamNum));
            }
        }

        [[nodiscard]] bool readObjectives(
            const SvNativePlayerState &source,
            std::array<SvObjective, 32> &destination)
        {
            // OLMOD(native-playerstate-objective-admission): use a private
            // copy so a malformed late record cannot publish earlier records.
            auto next = destination;
            for (std::size_t index = 0; index < next.size(); ++index)
            {
                const auto offset = ObjectivesOffset + index * ObjectiveStride;
                const auto state = readValue<std::int32_t>(source, offset);
                const auto origin = readFloatArray<3>(
                    source, offset + ObjectiveOriginOffset);
                const auto icon = readValue<std::int32_t>(
                    source, offset + ObjectiveIconOffset);
                const auto entityNum = readValue<std::int32_t>(
                    source, offset + ObjectiveEntityNumOffset);
                const auto teamNum = readValue<std::int32_t>(
                    source, offset + ObjectiveTeamNumOffset);
                if (state < 0 ||
                    static_cast<std::uint32_t>(state) > MaximumObjectiveState ||
                    !finite(origin) || icon < 0 || icon > 0xFFF ||
                    entityNum < 0 || entityNum > 0x7FF ||
                    teamNum < 0 || teamNum > 0xF)
                {
                    return false;
                }
                next[index] = {
                    .state = static_cast<SvObjectiveState>(state),
                    .origin = origin,
                    .icon = static_cast<std::uint16_t>(icon),
                    .entityNum = static_cast<std::uint16_t>(entityNum),
                    .teamNum = static_cast<std::uint8_t>(teamNum),
                };
            }
            destination = std::move(next);
            return true;
        }

        static_assert(HeldWeaponIndexesOffset + 15 * sizeof(std::uint32_t) ==
            HeldWeaponStatesOffset);
        // Pin the array to its END, not merely below the next member. The
        // `<=` form alone passes for any stride at or under the real one, and
        // that is exactly how a stride of five survived a 180-byte region.
        // 0x3E4 is playerState netfield index 53, the first field above the
        // array in re/demo-re/netfields-ol/playerstate-0x00DA8540.tsv. (That
        // filename is OL.exe's address; the same table is at 0x00DA8520 on
        // out.exe and its CONTENT is byte-identical -- section 84.)
        static_assert(HeldWeaponStatesOffset + 15 * HeldWeaponStateStride ==
            0x3E4);
        static_assert(HeldWeaponStatesOffset + 15 * HeldWeaponStateStride <=
            CurrentWeaponOffset);
        // 0x548 is netfield index 53's OLfinal sibling block, the first field
        // above the ammo clips.
        static_assert(AmmoClipsOffset + 15 * AmmoClipStride == 0x548);
        static_assert(AmmoPoolsOffset + 15 * AmmoPoolStride == AmmoClipsOffset);
        static_assert(AmmoClipsOffset + 15 * AmmoClipStride <=
            ObjectivesOffset);
        static_assert(ObjectivesOffset + 32 * ObjectiveStride <=
            SvNativePlayerState::Size);
        static_assert(PredictableEventsOffset +
                4 * sizeof(SvNativePredictableEvent) <=
            ClientNumOffset);
    }

    namespace
    {
        SvAltWeaponResolver altWeaponResolver;
    }

    void SV_SetAltWeaponResolver(SvAltWeaponResolver resolver)
    {
        altWeaponResolver = std::move(resolver);
    }

    void SV_SetNativeAbilityModifiers(
        SvNativePlayerState &state, const SvAbilityModifiers &abilities)
    {
        // CODREF(1649370): identical destinations to the retail snapshot
        // consumer at 0x54C236 and 0x54C278; 0x4E8020 copies 36 floats.
        std::memcpy(state.bytes.data() + 0x590, abilities.mask.data(), 24);
        std::memcpy(state.bytes.data() + 0x5A8, abilities.values.data(), 144);
    }

    void SV_OverlayPlayerStateToNative(
        const SvPlayerState &source,
        SvNativePlayerState &destination)
    {
        // OLMOD(native-playerstate-forward-projection): source gameplay owners
        // maintain the recovered field domains; this overlay deliberately
        // preserves every unknown native byte. The reverse projection below
        // remains the fail-closed admission boundary after native mutation.
        writeValue(destination, 0x4C, static_cast<std::uint32_t>(source.grenadeEntityNum));
        writeValue(destination, 0x400, source.weaponFlags());
        writeValue(destination, 0x48, static_cast<std::int32_t>(source.grenadeTimeLeft));
        writeValue(destination, CommandTimeOffset, source.commandTime);
        writeValue(destination, PmTypeOffset, static_cast<std::int32_t>(source.pmType));
        writeValue(destination, PmTimeOffset, source.pmTime);
        writeValue(destination, PmFlagsOffset, source.pmFlags);
        for (std::size_t index = 0; index < source.perks.size(); ++index)
            writeValue(destination, PerksOffset + index * sizeof(std::uint32_t),
                source.perks[index]);
        // MERGE, DO NOT REPLACE. ps+0x10 carries the ENGINE's flags word -- stance and
        // toggle state among them -- captured back out through the GET accessor after
        // every native stage. This server owns only the two bits
        // BG_PlayerStateToEntityState tests to pick ET_PLAYER over ET_INVISIBLE.
        // Assigning the whole word here is what threw the engine's state away every
        // frame, and dest1yo's 3.3.3.3 server has none of this machinery at all -- ps+0x10
        // is a plain dword there, which is exactly why stance works on it.
        writeValue(
            destination,
            OtherFlagsOffset,
            (readValue<std::uint32_t>(destination, OtherFlagsOffset) &
                ~PlayerOtherFlagsServerOwnedMask) |
                (source.otherFlags & PlayerOtherFlagsServerOwnedMask));
        writeValue(destination, BobCycleOffset,
            static_cast<std::uint32_t>(source.bobCycle));
        writeFloatArray(destination, OriginOffset, source.origin);
        writeFloatArray(destination, VelocityOffset, source.velocity);
        writeValue(destination, MovementDirOffset,
            static_cast<std::int32_t>(source.movementDir));
        writeValue(destination, MovingPlatformEntityOffset,
            static_cast<std::int32_t>(source.movingPlatformEntityNum));
        writeValue(destination, RemoteEyesEntityOffset,
            static_cast<std::int32_t>(source.remoteEyesEntityNum));
        writeValue(destination, RemoteControlEntityOffset,
            static_cast<std::int32_t>(source.remoteControlEntityNum));
        writeValue(destination, RemoteTurretEntityOffset,
            static_cast<std::int32_t>(source.remoteTurretEntityNum));
        writeValue(destination, GravityOffset, source.gravity);
        writeValue(destination, PlayerSizeScaleOffset, source.playerSizeScale);
        writeValue(destination, SpeedOffset, source.speed);
        writeFloatArray(destination, DeltaAnglesOffset, source.deltaAngles);
        writeFloatArray(destination, LadderVectorOffset, source.ladderVector);
        writeValue(destination, GroundEntityOffset,
            static_cast<std::int32_t>(source.groundEntityNum));
        writeValue(destination, JumpTimeOffset, source.jumpTime);
        writeValue(destination, JumpOriginZOffset, source.jumpOriginZ);
        writeValue(destination, LegsTimerOffset, source.legsTimer);
        writeValue(destination, LegsAnimOffset,
            static_cast<std::uint32_t>(source.legsAnim));
        writeValue(destination, TorsoTimerOffset, source.torsoTimer);
        writeValue(destination, TorsoAnimOffset,
            static_cast<std::uint32_t>(source.torsoAnim));
        writeValue(destination, EFlagsOffset, source.eFlags);
        writeValue(destination, ClientNumOffset,
            static_cast<std::int32_t>(source.clientNum));
        writeValue(destination, ViewmodelIndexOffset,
            static_cast<std::uint32_t>(source.viewmodelIndex));
        writeFloatArray(destination, ViewAnglesOffset, source.viewAngles);
        writeValue(destination, ProneDirectionOffset, source.proneDirection);
        writeValue(
            destination, ProneDirectionPitchOffset, source.proneDirectionPitch);
        writeValue(destination, ProneTorsoPitchOffset, source.proneTorsoPitch);
        writeValue(destination, ProneTransitionStartTimeOffset,
            source.proneTransitionStartTime);
        writeValue(
            destination,
            SprintButtonUpRequiredOffset,
            static_cast<std::int32_t>(source.sprintButtonUpRequired));
        writeValue(destination, SprintDelayOffset,
            static_cast<std::int32_t>(source.sprintDelay));
        writeValue(destination, LastSprintStartOffset, source.lastSprintStart);
        writeValue(destination, LastSprintEndOffset, source.lastSprintEnd);
        writeValue(destination, SprintStartMaxLengthOffset,
            source.sprintStartMaxLength);
        writeValue(destination, MantleYawOffset, source.mantleYaw);
        writeValue(destination, MantleTimerOffset, source.mantleTimer);
        writeValue(
            destination,
            MantleTransitionIndexOffset,
            static_cast<std::uint32_t>(source.mantleTransitionIndex));
        writeValue(
            destination,
            MantleFlagsOffset,
            static_cast<std::uint32_t>(source.mantleFlags));
        writeValue(destination, ViewHeightTargetOffset, source.viewHeightTarget);
        writeValue(destination, ViewHeightCurrentOffset, source.viewHeightCurrent);
        writeValue(destination, ViewHeightLerpTimeOffset, source.viewHeightLerpTime);
        writeValue(destination, ViewHeightLerpTargetOffset,
            source.viewHeightLerpTarget);
        writeValue(destination, ViewHeightLerpDownOffset,
            static_cast<std::int32_t>(source.viewHeightLerpDown));
        writeValue(destination, HealthStatOffset,
            static_cast<std::int32_t>(source.health));
        writeValue(destination, DeadYawStatOffset, source.deadYaw);
        writeValue(destination, MaxHealthStatOffset,
            static_cast<std::int32_t>(source.maxHealth));
        writeValue(destination, SpawnCountStatOffset,
            static_cast<std::int32_t>(source.spawnGeneration));
        writeValue(destination, DamageEventOffset, source.damageEvent);
        writeValue(destination, DamageYawOffset, source.damageYaw);
        writeValue(destination, DamagePitchOffset, source.damagePitch);
        writeValue(destination, DamageCountOffset, source.damageCount);
        writeValue(destination, HealthOffset, source.health);
        writeValue(destination, MaxHealthOffset, source.maxHealth);
        writeValue(destination, ShellshockIndexOffset, source.shellshockIndex);
        writeValue(destination, ShellshockTimeOffset, source.shellshockTime);
        writeValue(destination, ShellshockDurationOffset, source.shellshockDuration);
        writeValue(destination, ViewEntityOffset,
            static_cast<std::int32_t>(source.viewEntityNum));
        writeValue(destination, LinkEntityOffset,
            static_cast<std::int32_t>(source.linkEntityNum));
        writeValue(destination, MoveSpeedScaleMultiplierOffset,
            source.moveSpeedScaleMultiplier);
        writeValue(destination, RightWeaponAnimOffset,
            static_cast<std::uint32_t>(source.weaponAnim[0]));
        writeValue(destination, RightWeaponTimeOffset, source.weaponTime[0]);
        writeValue(destination, RightWeaponDelayOffset, source.weaponDelay[0]);
        writeValue(destination, RightWeaponRestrictKickTimeOffset,
            source.weaponRestrictKickTime[0]);
        writeValue(destination, RightWeaponStateOffset,
            static_cast<std::int32_t>(source.weaponState[0]));
        writeValue(destination, RightWeaponHandFlagsOffset,
            static_cast<std::int32_t>(source.weaponHandFlags[0]));
        writeValue(destination, RightWeaponShotCountOffset,
            static_cast<std::uint32_t>(source.weaponShotCount[0]));
        writeValue(destination, LeftWeaponAnimOffset,
            static_cast<std::uint32_t>(source.weaponAnim[1]));
        writeValue(destination, LeftWeaponTimeOffset, source.weaponTime[1]);
        writeValue(destination, LeftWeaponDelayOffset, source.weaponDelay[1]);
        writeValue(destination, LeftWeaponRestrictKickTimeOffset,
            source.weaponRestrictKickTime[1]);
        writeValue(destination, LeftWeaponStateOffset,
            static_cast<std::int32_t>(source.weaponState[1]));
        writeValue(destination, LeftWeaponHandFlagsOffset,
            static_cast<std::int32_t>(source.weaponHandFlags[1]));
        writeValue(destination, LeftWeaponShotCountOffset,
            static_cast<std::uint32_t>(source.weaponShotCount[1]));
        writeWeaponAuxiliaryState(source, destination);
        writeObjectives(source, destination);
        writeValue(destination, CurrentWeaponOffset,
            static_cast<std::uint32_t>(source.currentWeaponAssetIndex));
        writeValue(destination, OffhandWeaponOffset,
            static_cast<std::uint32_t>(source.offhandWeaponAssetIndex));
        writeValue(destination, RewardActionTypeOffset,
            static_cast<std::uint32_t>(source.rewardActionType));
        writeValue(destination, RewardActionWeaponOffset,
            static_cast<std::uint32_t>(source.rewardActionWeapon));
        const auto offhandSlots = source.offhandWeaponSlots();
        for (std::size_t slot = 0; slot < offhandSlots.size(); ++slot)
            writeValue(destination, OffhandWeaponOffset + 4 + slot * 4,
                static_cast<std::uint32_t>(offhandSlots[slot]));
        // CORRECTION (2026-09-06, re/demo-re/35-equipped-equipment.md):
        // +0x3E4 is the selected OFFHAND, networked by field 53 (11 bits).
        // +0x3E8/+0x3EC/+0x3F0 are separate button-selected offhand slots,
        // ALSO networked: fields 109..111, each 32 bits. The first correction
        // only checked field 53; a full table audit disproved the remaining
        // absence claim too. The native delta reader is their client producer.
        //
        // sub_429DA0 is grenade THROWBACK: ps+0x50 is the fuse, +0x54 the
        // grenade weapon, and +0x254 the hint entity. It is not evidence for
        // ordinary gun alt-mode switching. sub_429640/429450/429AE0 are the
        // offhand prepare/init/use path despite their older IDB names.
        //
        // The old opt-in OLMOD_ALT_FORCE_TEST experiment below is retained
        // for reproducibility only; it seeds the throwback path with a gun's
        // alternate asset. Do not enable it for normal equipment gameplay.
        static const auto altForceTestEnabled = [] {
            const auto *const value = std::getenv("OLMOD_ALT_FORCE_TEST");
            return value && *value && *value != '0';
        }();
        if (altForceTestEnabled)
        {
            const auto current =
                static_cast<std::uint16_t>(source.currentWeaponAssetIndex);
            const auto alt = current && altWeaponResolver
                ? altWeaponResolver(current)
                : std::uint16_t{};
            if (alt)
            {
                writeValue(destination, 0x50, std::uint32_t{ 1 });
                writeValue(destination, 0x54, static_cast<std::uint32_t>(alt));
                writeValue(destination, 0x254, std::uint32_t{ 0 });
            }
        }
        // OFF BY DEFAULT, AND THE REASON IS THE RESULT. Measured 2026-09-02:
        // the write is CORRECT -- `weapon slots a3E8=1224 b3EC=0 c3F0=1225
        // current3F8=1224` against `1224 ** 306 (csg12ss) -> alt 1225
        // (** 139 0 0 4422 10545 9321)`, host and alt both right, and the same
        // for the AK -- and the player reported the server DESYNCING HEAVILY
        // with the switch still not happening.
        //
        // That is the finding, not a defect in the write. These four fields are
        // NOT in this build's playerState netfield table, so the client keeps
        // predicting against zeros while the server predicts against real
        // weapons, and the two diverge every frame. Filling them server-side
        // cannot work ALONE.
        //
        // Which puts retail's `y 906` back in frame: section 140j lists it as
        // one of THREE verbs in the dm demo this server has never sent, and it
        // lands in the playerState weapon block on exactly the frames it is
        // sent. Whatever fills these slots is something BOTH sides run.
        //
        // Kept, because the resolver and the offsets are measured and correct
        // and the next attempt needs them. OLMOD_ALT_WEAPON_SLOTS=1 to arm it.
        static const auto altWeaponSlotsEnabled = [] {
            const auto *const value = std::getenv("OLMOD_ALT_WEAPON_SLOTS");
            return value && *value && *value != '0';
        }();
        if (altWeaponSlotsEnabled)
        {
            const auto current =
                static_cast<std::uint16_t>(source.currentWeaponAssetIndex);
            const auto alt = current && altWeaponResolver
                ? altWeaponResolver(current)
                : std::uint16_t{};
            writeValue(destination, 0x3E8, static_cast<std::uint32_t>(current));
            writeValue(destination, 0x3F0, static_cast<std::uint32_t>(alt));
        }
        writeValue(destination, WeaponPositionFractionOffset,
            source.weaponPositionFraction);
        writeValue(destination, Unk04A4TimeOffset, source.unk04A4Time);
        writeValue(destination, AimSpreadScaleOffset, source.aimSpreadScale);
        writeValue(destination, SpreadOverrideOffset, source.spreadOverride);
        writeValue(destination, SpreadOverrideStateOffset,
            source.spreadOverrideState);
        const auto currentHeld = std::ranges::find_if(
            source.heldWeapons,
            [&source](const SvHeldWeaponState &weapon) {
                return weapon.weaponAssetIndex ==
                    source.currentWeaponAssetIndex;
            });
        const auto dualWieldActive =
            currentHeld != source.heldWeapons.end() &&
            currentHeld->unknownState[0];
        writeValue(destination, DualWieldActiveOffset,
            static_cast<std::int32_t>(dualWieldActive));
    }

    bool SV_OverlayNativePlayerStateToPlayerState(
        const SvNativePlayerState &source,
        SvPlayerState &destination,
        const char **const failureReason)
    {
        // OLMOD(native-playerstate-reverse-admission): read and validate the
        // complete recovered view before assigning destination. No failed
        // scalar, auxiliary record or objective may partially publish.
        const auto pmType = readValue<std::int32_t>(source, PmTypeOffset);
        const auto bobCycle = readValue<std::uint32_t>(source, BobCycleOffset);
        const auto movementDir =
            readValue<std::int32_t>(source, MovementDirOffset);
        const auto clientNum = readValue<std::int32_t>(source, ClientNumOffset);
        const auto groundEntity = readValue<std::int32_t>(source, GroundEntityOffset);
        const auto viewEntity = readValue<std::int32_t>(source, ViewEntityOffset);
        const auto linkEntity = readValue<std::int32_t>(source, LinkEntityOffset);
        const auto movingPlatform =
            readValue<std::int32_t>(source, MovingPlatformEntityOffset);
        const auto remoteEyes =
            readValue<std::int32_t>(source, RemoteEyesEntityOffset);
        const auto remoteControl =
            readValue<std::int32_t>(source, RemoteControlEntityOffset);
        const auto remoteTurret =
            readValue<std::int32_t>(source, RemoteTurretEntityOffset);
        const auto viewmodelIndex =
            readValue<std::uint32_t>(source, ViewmodelIndexOffset);
        const auto rightWeaponAnim =
            readValue<std::uint32_t>(source, RightWeaponAnimOffset);
        const auto leftWeaponAnim =
            readValue<std::uint32_t>(source, LeftWeaponAnimOffset);
        const auto rightWeaponState =
            readValue<std::int32_t>(source, RightWeaponStateOffset);
        const auto leftWeaponState =
            readValue<std::int32_t>(source, LeftWeaponStateOffset);
        const std::array weaponRestrictKickTime{
            readValue<std::int32_t>(source, RightWeaponRestrictKickTimeOffset),
            readValue<std::int32_t>(source, LeftWeaponRestrictKickTimeOffset),
        };
        const std::array weaponHandFlags{
            readValue<std::int32_t>(source, RightWeaponHandFlagsOffset),
            readValue<std::int32_t>(source, LeftWeaponHandFlagsOffset),
        };
        const std::array weaponShotCount{
            readValue<std::uint32_t>(source, RightWeaponShotCountOffset),
            readValue<std::uint32_t>(source, LeftWeaponShotCountOffset),
        };
        const auto currentWeapon =
            readValue<std::uint32_t>(source, CurrentWeaponOffset);
        const auto offhandWeapon =
            readValue<std::uint32_t>(source, OffhandWeaponOffset);
        const auto rewardActionType =
            readValue<std::uint32_t>(source, RewardActionTypeOffset);
        const auto rewardActionWeapon =
            readValue<std::uint32_t>(source, RewardActionWeaponOffset);
        const std::array offhandSlots{
            readValue<std::uint32_t>(source, 0x3E8),
            readValue<std::uint32_t>(source, 0x3EC),
            readValue<std::uint32_t>(source, 0x3F0),
        };
        const auto weaponPositionFraction =
            readValue<float>(source, WeaponPositionFractionOffset);
        const auto unk04A4Time =
            readValue<std::uint32_t>(source, Unk04A4TimeOffset);
        const auto aimSpreadScale = readValue<float>(source, AimSpreadScaleOffset);
        const auto spreadOverride =
            readValue<std::int32_t>(source, SpreadOverrideOffset);
        const auto spreadOverrideState =
            readValue<std::int32_t>(source, SpreadOverrideStateOffset);
        const auto viewHeightLerpDown =
            readValue<std::int32_t>(source, ViewHeightLerpDownOffset);
        const auto origin = readFloatArray<3>(source, OriginOffset);
        const auto velocity = readFloatArray<3>(source, VelocityOffset);
        const auto deltaAngles = readFloatArray<3>(source, DeltaAnglesOffset);
        const auto ladderVector = readFloatArray<3>(source, LadderVectorOffset);
        const auto viewAngles = readFloatArray<3>(source, ViewAnglesOffset);
        const auto proneDirection =
            readValue<float>(source, ProneDirectionOffset);
        const auto proneDirectionPitch =
            readValue<float>(source, ProneDirectionPitchOffset);
        const auto proneTorsoPitch =
            readValue<float>(source, ProneTorsoPitchOffset);
        const auto proneTransitionStartTime =
            readValue<std::uint32_t>(source, ProneTransitionStartTimeOffset);
        const auto sprintButtonUpRequired =
            readValue<std::int32_t>(source, SprintButtonUpRequiredOffset);
        const auto sprintDelay = readValue<std::int32_t>(source, SprintDelayOffset);
        const auto sprintStartMaxLength =
            readValue<std::uint32_t>(source, SprintStartMaxLengthOffset);
        const auto mantleYaw = readValue<float>(source, MantleYawOffset);
        const auto mantleTransitionIndex =
            readValue<std::uint32_t>(source, MantleTransitionIndexOffset);
        const auto mantleFlags =
            readValue<std::uint32_t>(source, MantleFlagsOffset);
        const auto playerSizeScale =
            readValue<float>(source, PlayerSizeScaleOffset);
        const auto moveSpeedScaleMultiplier =
            readValue<float>(source, MoveSpeedScaleMultiplierOffset);
        const auto jumpOriginZ = readValue<float>(source, JumpOriginZOffset);
        const auto viewHeightCurrent =
            readValue<float>(source, ViewHeightCurrentOffset);
        const auto torsoAnim = readValue<std::uint32_t>(source, TorsoAnimOffset);
        const auto legsAnim = readValue<std::uint32_t>(source, LegsAnimOffset);
        const auto legsTimer = readValue<std::uint32_t>(source, LegsTimerOffset);
        const auto torsoTimer = readValue<std::uint32_t>(source, TorsoTimerOffset);
        const auto healthStat =
            readValue<std::int32_t>(source, HealthStatOffset);
        const auto deadYawStat =
            readValue<std::int32_t>(source, DeadYawStatOffset);
        const auto maxHealthStat =
            readValue<std::int32_t>(source, MaxHealthStatOffset);
        const auto spawnCountStat =
            readValue<std::int32_t>(source, SpawnCountStatOffset);
        const auto damageEvent = readValue<std::uint32_t>(source, DamageEventOffset);
        const auto damageYaw = readValue<std::uint32_t>(source, DamageYawOffset);
        const auto damagePitch = readValue<std::uint32_t>(source, DamagePitchOffset);
        const auto damageCount = readValue<std::uint32_t>(source, DamageCountOffset);
        const auto health = readValue<std::uint32_t>(source, HealthOffset);
        const auto maxHealth = readValue<std::uint32_t>(source, MaxHealthOffset);
        const auto shellshockIndex =
            readValue<std::uint32_t>(source, ShellshockIndexOffset);
        const auto shellshockTime =
            readValue<std::uint32_t>(source, ShellshockTimeOffset);
        const auto shellshockDuration =
            readValue<std::uint32_t>(source, ShellshockDurationOffset);

        // ONE `return false` FOR FORTY TERMS. This is the reverse admission for the
        // native playerState, and it runs inside a ROUND TRIP: SV_ClientSpawn writes
        // this buffer from a struct it just built, reads it straight back, and refuses
        // the spawn if anything here trips. So a term failing does not mean the value
        // is bad -- it means the writer and the reader disagree about WHERE that field
        // lives, and on a per-build layout that is the likeliest thing in the file.
        // Naming the term turns "the player never spawns" into one offset to check.
        const auto refuse = [failureReason](const char *const reason) {
            if (failureReason)
                *failureReason = reason;
            return false;
        };
        if (pmType < 0 || pmType > std::numeric_limits<std::uint8_t>::max())
            return refuse("pmType");
        if (bobCycle > std::numeric_limits<std::uint8_t>::max())
            return refuse("bobCycle");
        if (movementDir < std::numeric_limits<std::int8_t>::min() ||
            movementDir > std::numeric_limits<std::int8_t>::max())
        {
            return refuse("movementDir");
        }
        if (clientNum < 0 ||
            static_cast<std::uint32_t>(clientNum) > MaximumClientNum)
        {
            return refuse("clientNum");
        }
        if (!validEntity(groundEntity))
            return refuse("groundEntity");
        if (!validEntity(viewEntity))
            return refuse("viewEntity");
        if (!validEntity(linkEntity))
            return refuse("linkEntity");
        if (!validEntity(movingPlatform))
            return refuse("movingPlatform");
        if (!validEntity(remoteEyes))
            return refuse("remoteEyes");
        if (!validEntity(remoteControl))
            return refuse("remoteControl");
        if (!validEntity(remoteTurret))
            return refuse("remoteTurret");
        if (viewmodelIndex > MaximumViewmodelIndex)
            return refuse("viewmodelIndex");
        if (rightWeaponAnim > MaximumWeaponAnimation)
            return refuse("rightWeaponAnim");
        if (leftWeaponAnim > MaximumWeaponAnimation)
            return refuse("leftWeaponAnim");
        if (rightWeaponState < 0 ||
            static_cast<std::uint32_t>(rightWeaponState) > MaximumWeaponState)
        {
            return refuse("rightWeaponState");
        }
        if (leftWeaponState < 0 ||
            static_cast<std::uint32_t>(leftWeaponState) > MaximumWeaponState)
        {
            return refuse("leftWeaponState");
        }
        if (currentWeapon > MaximumWeaponIndex)
            return refuse("currentWeapon");
        if (offhandWeapon > MaximumWeaponIndex)
            return refuse("offhandWeapon");
        if (rewardActionType > 3)
            return refuse("rewardActionType");
        if (rewardActionWeapon > MaximumWeaponIndex)
            return refuse("rewardActionWeapon");
        if (std::ranges::any_of(offhandSlots,
                [](auto value) { return value > MaximumWeaponIndex; }))
            return refuse("offhandWeaponSlots");
        if (!std::isfinite(weaponPositionFraction) ||
            weaponPositionFraction < 0.0f || weaponPositionFraction > 1.0f)
        {
            return refuse("weaponPositionFraction");
        }
        if (!std::isfinite(aimSpreadScale) || aimSpreadScale < 0.0f ||
            aimSpreadScale > 255.0f)
        {
            return refuse("aimSpreadScale");
        }
        if (spreadOverride < 0 || spreadOverride > 0x3F)
            return refuse("spreadOverride");
        if (spreadOverrideState < 0 || spreadOverrideState > 2)
            return refuse("spreadOverrideState");
        if (viewHeightLerpDown != 0 && viewHeightLerpDown != 1)
            return refuse("viewHeightLerpDown");
        if (legsTimer > 0xFFFF)
            return refuse("legsTimer");
        if (torsoTimer > 0xFFFF)
            return refuse("torsoTimer");
        if (torsoAnim > MaximumWeaponAnimation)
            return refuse("torsoAnim");
        if (legsAnim > MaximumWeaponAnimation)
            return refuse("legsAnim");
        if (std::ranges::any_of(
                weaponRestrictKickTime,
                [](const std::int32_t value) {
                    return value < std::numeric_limits<std::int16_t>::min() ||
                        value > std::numeric_limits<std::int16_t>::max();
                }))
        {
            return refuse("weaponRestrictKickTime");
        }
        if (std::ranges::any_of(weaponHandFlags,
                [](const std::int32_t value) { return value < 0 || value > 1; }))
        {
            return refuse("weaponHandFlags");
        }
        if (std::ranges::any_of(weaponShotCount,
                [](const std::uint32_t value) { return value > 7; }))
        {
            return refuse("weaponShotCount");
        }
        if (damageEvent > 0xFFFF)
            return refuse("damageEvent");
        if (damageYaw > 0xFF)
            return refuse("damageYaw");
        if (damagePitch > 0xFF)
            return refuse("damagePitch");
        if (damageCount > 0xFF)
            return refuse("damageCount");
        if (health > 0xFF)
            return refuse("health");
        if (maxHealth > 0xFF)
            return refuse("maxHealth");
        if (shellshockIndex > 0xF)
            return refuse("shellshockIndex");
        if (healthStat != static_cast<std::int32_t>(health))
            return refuse("healthStat_vs_health");
        if (maxHealthStat != static_cast<std::int32_t>(maxHealth))
            return refuse("maxHealthStat_vs_maxHealth");
        if (deadYawStat < std::numeric_limits<std::int16_t>::min() ||
            deadYawStat > std::numeric_limits<std::int16_t>::max())
        {
            return refuse("deadYawStat");
        }
        if (spawnCountStat < 0 ||
            spawnCountStat > std::numeric_limits<std::uint8_t>::max())
        {
            return refuse("spawnCountStat");
        }
        if (shellshockDuration > 0xFFFF)
            return refuse("shellshockDuration");
        if (!finite(origin))
            return refuse("origin");
        if (!finite(velocity))
            return refuse("velocity");
        if (!finite(deltaAngles))
            return refuse("deltaAngles");
        if (!finite(ladderVector))
            return refuse("ladderVector");
        if (!finite(viewAngles))
            return refuse("viewAngles");
        if (!std::isfinite(proneDirection))
            return refuse("proneDirection");
        if (!std::isfinite(proneDirectionPitch))
            return refuse("proneDirectionPitch");
        if (!std::isfinite(proneTorsoPitch))
            return refuse("proneTorsoPitch");
        if (sprintButtonUpRequired != 0 && sprintButtonUpRequired != 1)
            return refuse("sprintButtonUpRequired");
        if (sprintDelay != 0 && sprintDelay != 1)
            return refuse("sprintDelay");
        if (sprintStartMaxLength > 0xFFFF)
            return refuse("sprintStartMaxLength");
        if (!std::isfinite(mantleYaw))
            return refuse("mantleYaw");
        if (mantleTransitionIndex > 0xF)
            return refuse("mantleTransitionIndex");
        if (mantleFlags > 0xFF)
            return refuse("mantleFlags");
        if (!std::isfinite(playerSizeScale) || playerSizeScale < 0.0f)
            return refuse("playerSizeScale");
        if (!std::isfinite(moveSpeedScaleMultiplier) ||
            moveSpeedScaleMultiplier < 0.0f)
        {
            return refuse("moveSpeedScaleMultiplier");
        }
        if (!std::isfinite(jumpOriginZ))
            return refuse("jumpOriginZ");
        if (!std::isfinite(viewHeightCurrent))
            return refuse("viewHeightCurrent");
        auto next = destination;
        next.commandTime = readValue<std::uint32_t>(source, CommandTimeOffset);
        next.pmType = static_cast<std::uint8_t>(pmType);
        next.pmTime = readValue<std::uint32_t>(source, PmTimeOffset);
        next.pmFlags = readValue<std::uint32_t>(source, PmFlagsOffset);
        for (std::size_t index = 0; index < next.perks.size(); ++index)
            next.perks[index] = readValue<std::uint32_t>(source,
                PerksOffset + index * sizeof(std::uint32_t));
        // ps+0x10 IS NOT A PLAIN DWORD TO READ BACK. On this build it is the first word
        // of a three-dword PROTECTED value whose accessor pair lives at ps+0x20/+0x24,
        // and the engine writes it through that pair -- so whatever sits there after a
        // native stage is ciphertext, not flags. Reading it plaintext gave the server a
        // different random otherFlags every frame (`playerstate domain refused
        // otherFlags=1461489901`, then 1312251290, then 2934888368), which the snapshot
        // frame validator refused, so no snapshot ever reached the client. It only became
        // visible when clientThink started committing: while the conversion was still
        // refusing, nothing was ever written back and beginFrame's value survived.
        //
        // ol-mod owns the plaintext. It is written INTO the protected object before each
        // native call (writeNativeProtectedPlayerStateFlags) and kept in this DTO across
        // it. Reading the engine's own view back would mean calling the GET accessor and
        // taking the second dword of the result -- worth doing, but it is another native
        // ABI and not one to guess at; `next` already carries the previous value.
        static_assert(OtherFlagsOffset == 0x010);
        next.bobCycle = static_cast<std::uint8_t>(bobCycle);
        next.movementDir = static_cast<std::int8_t>(movementDir);
        next.origin = origin;
        next.velocity = velocity;
        next.movingPlatformEntityNum = static_cast<std::uint32_t>(movingPlatform);
        next.remoteEyesEntityNum = static_cast<std::uint32_t>(remoteEyes);
        next.remoteControlEntityNum = static_cast<std::uint32_t>(remoteControl);
        next.remoteTurretEntityNum = static_cast<std::uint32_t>(remoteTurret);
        next.gravity = readValue<std::uint32_t>(source, GravityOffset);
        next.playerSizeScale = playerSizeScale;
        next.speed = readValue<std::uint32_t>(source, SpeedOffset);
        next.deltaAngles = deltaAngles;
        next.ladderVector = ladderVector;
        next.groundEntityNum = static_cast<std::uint32_t>(groundEntity);
        next.jumpTime = readValue<std::uint32_t>(source, JumpTimeOffset);
        next.jumpOriginZ = jumpOriginZ;
        next.legsTimer = legsTimer;
        next.legsAnim = static_cast<std::uint16_t>(legsAnim);
        next.torsoTimer = torsoTimer;
        next.torsoAnim = static_cast<std::uint16_t>(torsoAnim);
        next.eFlags = readValue<std::uint32_t>(source, EFlagsOffset);
        next.clientNum = static_cast<std::uint32_t>(clientNum);
        next.viewmodelIndex = static_cast<std::uint16_t>(viewmodelIndex);
        next.viewAngles = viewAngles;
        next.proneDirection = proneDirection;
        next.proneDirectionPitch = proneDirectionPitch;
        next.proneTorsoPitch = proneTorsoPitch;
        next.proneTransitionStartTime = proneTransitionStartTime;
        next.sprintButtonUpRequired =
            static_cast<std::uint8_t>(sprintButtonUpRequired);
        next.sprintDelay = static_cast<std::uint8_t>(sprintDelay);
        next.lastSprintStart =
            readValue<std::uint32_t>(source, LastSprintStartOffset);
        next.lastSprintEnd =
            readValue<std::uint32_t>(source, LastSprintEndOffset);
        next.sprintStartMaxLength = sprintStartMaxLength;
        next.mantleYaw = mantleYaw;
        next.mantleTimer = readValue<std::uint32_t>(source, MantleTimerOffset);
        next.mantleTransitionIndex =
            static_cast<std::uint8_t>(mantleTransitionIndex);
        next.mantleFlags = static_cast<std::uint8_t>(mantleFlags);
        next.viewHeightTarget =
            readValue<std::int32_t>(source, ViewHeightTargetOffset);
        next.viewHeightCurrent = viewHeightCurrent;
        next.viewHeightLerpTime =
            readValue<std::int32_t>(source, ViewHeightLerpTimeOffset);
        next.viewHeightLerpTarget =
            readValue<std::int32_t>(source, ViewHeightLerpTargetOffset);
        next.viewHeightLerpDown = viewHeightLerpDown != 0;
        next.damageEvent = damageEvent;
        next.damageYaw = damageYaw;
        next.damagePitch = damagePitch;
        next.damageCount = damageCount;
        next.health = health;
        next.maxHealth = maxHealth;
        next.deadYaw = deadYawStat;
        next.spawnGeneration = static_cast<std::uint8_t>(spawnCountStat);
        next.shellshockIndex = shellshockIndex;
        next.shellshockTime = shellshockTime;
        next.shellshockDuration = shellshockDuration;
        next.viewEntityNum = static_cast<std::uint32_t>(viewEntity);
        next.linkEntityNum = static_cast<std::uint32_t>(linkEntity);
        next.moveSpeedScaleMultiplier = moveSpeedScaleMultiplier;
        next.weaponAnim[0] = static_cast<std::uint16_t>(rightWeaponAnim);
        next.weaponTime[0] =
            readValue<std::int32_t>(source, RightWeaponTimeOffset);
        next.weaponDelay[0] =
            readValue<std::int32_t>(source, RightWeaponDelayOffset);
        next.weaponRestrictKickTime[0] = weaponRestrictKickTime[0];
        next.weaponState[0] = static_cast<std::uint8_t>(rightWeaponState);
        next.weaponHandFlags[0] = static_cast<std::uint8_t>(weaponHandFlags[0]);
        next.weaponShotCount[0] = static_cast<std::uint8_t>(weaponShotCount[0]);
        next.weaponAnim[1] = static_cast<std::uint16_t>(leftWeaponAnim);
        next.weaponTime[1] =
            readValue<std::int32_t>(source, LeftWeaponTimeOffset);
        next.weaponDelay[1] =
            readValue<std::int32_t>(source, LeftWeaponDelayOffset);
        next.weaponRestrictKickTime[1] = weaponRestrictKickTime[1];
        next.weaponState[1] = static_cast<std::uint8_t>(leftWeaponState);
        next.weaponHandFlags[1] = static_cast<std::uint8_t>(weaponHandFlags[1]);
        next.weaponShotCount[1] = static_cast<std::uint8_t>(weaponShotCount[1]);
        next.currentWeaponAssetIndex =
            static_cast<std::uint16_t>(currentWeapon);
        next.offhandWeaponAssetIndex =
            static_cast<std::uint16_t>(offhandWeapon);
        next.offhandWeaponSlotA = static_cast<std::uint16_t>(offhandSlots[0]);
        next.rewardActionType = static_cast<std::uint8_t>(rewardActionType);
        next.rewardActionWeapon = static_cast<std::uint16_t>(rewardActionWeapon);
        next.offhandWeaponSlotB = static_cast<std::uint16_t>(offhandSlots[1]);
        next.offhandWeaponSlotC = static_cast<std::uint16_t>(offhandSlots[2]);
        next.weaponPositionFraction = weaponPositionFraction;
        next.unk04A4Time = unk04A4Time;
        const auto grenadeEntity = readValue<std::uint32_t>(source, 0x4C);
        const auto weaponFlags = readValue<std::uint32_t>(source, 0x400);
        const auto grenadeTime = readValue<std::int32_t>(source, 0x48);
        if (grenadeEntity > 2047 || weaponFlags > 0xFFFFFF ||
            grenadeTime < -32768 || grenadeTime > 32767)
            return refuse("offhandPredictionState");
        next.grenadeEntityNum = static_cast<std::uint16_t>(grenadeEntity);
        next.setWeaponFlags(weaponFlags);
        next.grenadeTimeLeft = static_cast<std::int16_t>(grenadeTime);
        next.aimSpreadScale = aimSpreadScale;
        next.spreadOverride = spreadOverride;
        next.spreadOverrideState = spreadOverrideState;
        // Offhand diagnostic, limited to tuple changes. The historical
        // "pending"/"alt" labels in its log are retained for old parsers:
        // +0x3E4 is selected offhand (now projected above), +0x3E8..3F0 are
        // offhand slots, and +0x50/+0x54 describe grenade throwback.
        {
            const auto pending = readValue<std::uint32_t>(source, 0x3E4);
            const auto slotA = readValue<std::uint32_t>(source, 0x3E8);
            const auto slotB = readValue<std::uint32_t>(source, 0x3EC);
            const auto slotC = readValue<std::uint32_t>(source, 0x3F0);
            static std::array<std::uint32_t, 7> lastSlots{
                0xFFFFFFFFu, 0, 0, 0, 0, 0, 0 };
            static std::uint32_t slotReports{};
            const std::array<std::uint32_t, 7> now{
                pending, slotA, slotB, slotC,
                readValue<std::uint32_t>(source, 0x50),
                readValue<std::uint32_t>(source, 0x54),
                readValue<std::uint32_t>(source, 0x2F4) };
            if (now != lastSlots && slotReports < 60)
            {
                ++slotReports;
                lastSlots = now;
                // Held weapon indexes at +0x2F4 ARE transmitted in the
                // playerstate trailing arrays, though not scalar netfields.
                const auto gate = readValue<std::uint32_t>(source, 0x50);
                const auto altField = readValue<std::uint32_t>(source, 0x54);
                const auto hint = readValue<std::uint32_t>(source, 0x254);
                char line[320]{};
                std::snprintf(
                    line, sizeof(line),
                    "weapon slots pending3E4=%u a3E8=%u b3EC=%u c3F0=%u "
                    "current3F8=%u | gate50=%u alt54=%u hint254=%u "
                    "list2F4=%u,%u,%u,%u,%u,%u",
                    pending, slotA, slotB, slotC, currentWeapon,
                    gate, altField, hint,
                    readValue<std::uint32_t>(source, 0x2F4),
                    readValue<std::uint32_t>(source, 0x2F8),
                    readValue<std::uint32_t>(source, 0x2FC),
                    readValue<std::uint32_t>(source, 0x300),
                    readValue<std::uint32_t>(source, 0x304),
                    readValue<std::uint32_t>(source, 0x308));
                OlMod::RuntimeLog::write(
                    OlMod::RuntimeLog::Channel::GameServer, line);
            }
            else if (now != lastSlots)
            {
                lastSlots = now;
            }
        }
        const char *auxFailure = "unset";
        if (!readWeaponAuxiliaryState(source, next, &auxFailure))
            return refuse(auxFailure);
        if (!readObjectives(source, next.objectives))
            return refuse("objectives");
        destination = std::move(next);
        return true;
    }

    void SV_SetNativePlayerStateCurrentWeapon(
        SvNativePlayerState &destination,
        const std::uint32_t weaponAssetIndex)
    {
        writeValue(destination, CurrentWeaponOffset, weaponAssetIndex);
        // +0x2F4 is the player's fifteen-entry weapon list; slot 0 is the one in
        // hand. Documented at the weapon-slot diagnostic in this file.
        writeValue(destination, 0x2F4, weaponAssetIndex);
    }

    void SV_SetNativePlayerStateWeaponAmmo(
        SvNativePlayerState &destination,
        const std::size_t slot,
        const std::uint16_t clipIndex,
        const std::uint16_t clipCount,
        const std::uint16_t ammoIndex,
        const std::uint16_t ammoCount)
    {
        // Fifteen slots, the same extent the round trip above walks. Silently doing
        // nothing on a bad slot rather than clamping: a caller asking for slot 20 has
        // a bug that a clamp would hide inside slot 14's ammo.
        if (slot >= 15)
            return;
        // heldBefore. The read path refuses anything but 0 or 1 here, and a weapon the
        // player has never held is one the client is entitled to treat as not yet drawn.
        writeValue(
            destination,
            HeldWeaponStatesOffset + slot * HeldWeaponStateStride,
            static_cast<std::uint8_t>(1));
        const auto clipOffset = AmmoClipsOffset + slot * AmmoClipStride;
        writeValue(destination, clipOffset, static_cast<std::int32_t>(clipIndex));
        writeValue(
            destination,
            clipOffset + sizeof(std::int32_t),
            static_cast<std::int32_t>(clipCount));
        const auto poolOffset = AmmoPoolsOffset + slot * AmmoPoolStride;
        writeValue(destination, poolOffset, static_cast<std::int32_t>(ammoIndex));
        writeValue(
            destination,
            poolOffset + sizeof(std::int32_t),
            static_cast<std::int32_t>(ammoCount));
    }

    void SV_SetNativePlayerStateOtherFlags(
        SvNativePlayerState &destination,
        const std::uint32_t otherFlags)
    {
        // Same merge as the overlay: force this server's two bits, leave the engine's.
        writeValue(
            destination,
            OtherFlagsOffset,
            (readValue<std::uint32_t>(destination, OtherFlagsOffset) &
                ~PlayerOtherFlagsServerOwnedMask) |
                (otherFlags & PlayerOtherFlagsServerOwnedMask));
    }

    void SV_SetNativeHoldBreathState(
        SvNativePlayerState &destination,
        const float swayScale,
        const std::uint32_t timer)
    {
        writeValue(destination, HoldBreathSwayScaleOffset, swayScale);
        writeValue(destination, HoldBreathTimerOffset, timer);
    }

    SvHoldBreathState SV_ReadNativeHoldBreathState(
        const SvNativePlayerState &source,
        const std::uint32_t clientNum)
    {
        return {
            .clientNum = clientNum,
            .swayScale = readValue<float>(source, HoldBreathSwayScaleOffset),
            .timer = readValue<std::uint32_t>(source, HoldBreathTimerOffset),
        };
    }

    void SV_SetNativePlayerStateScriptedMotion(
        SvNativePlayerState &destination,
        const std::array<float, 3> &origin,
        const std::uint8_t pmType,
        const std::uint32_t pmFlags,
        const std::uint32_t groundEntityNum)
    {
        writeValue(destination, PmTypeOffset, static_cast<std::int32_t>(pmType));
        writeValue(destination, PmFlagsOffset, pmFlags);
        writeFloatArray(destination, OriginOffset, origin);
        writeFloatArray(destination, VelocityOffset, std::array<float, 3>{});
        writeValue(destination, GroundEntityOffset,
            static_cast<std::int32_t>(groundEntityNum));
        writeValue(destination, SpeedOffset, std::uint32_t{});
        writeValue(destination, BobCycleOffset, std::uint32_t{});
        writeValue(destination, MovementDirOffset, std::int32_t{});
    }

    void SV_SetNativePlayerStateScriptedViewAngles(
        SvNativePlayerState &destination,
        const std::array<float, 3> &viewAngles,
        const std::array<float, 3> &deltaAngles)
    {
        writeFloatArray(destination, ViewAnglesOffset, viewAngles);
        writeFloatArray(destination, DeltaAnglesOffset, deltaAngles);
    }

    void SV_SetNativePlayerStateScriptedViewLink(
        SvNativePlayerState &destination,
        const std::array<float, 2> &viewAngleClampBase,
        const std::array<float, 2> &viewAngleClampRange,
        const std::array<float, 3> &linkAngles,
        const std::uint8_t linkFlags)
    {
        // CODREF(1649370 playerState table): these offsets are the exact
        // mission camera/link fields consumed by the client during Wetwork's
        // insertion. They are re-applied after Pmove just like the owned
        // position and view angle fields so a usercmd cannot clear the track.
        writeFloatArray(destination, ViewAngleClampBaseOffset,
            viewAngleClampBase);
        writeFloatArray(destination, ViewAngleClampRangeOffset,
            viewAngleClampRange);
        writeFloatArray(destination, LinkAnglesOffset, linkAngles);
        writeValue(destination, LinkFlagsOffset,
            static_cast<std::uint32_t>(linkFlags));
    }

    std::int32_t SV_ReadNativePredictableEventSequence(
        const SvNativePlayerState &source)
    {
        // CODREF(client_events): this is the saved pre-Pmove cursor consumed
        // by BO1/Ghosts ClientEvents, not the entityState event-bit encoding.
        return readValue<std::int32_t>(
            source, PredictableEventSequenceOffset);
    }

    std::optional<SvNativePredictableEventBatch>
        SV_ReadNativePredictableEvents(
            const SvNativePlayerState &source,
            const std::int32_t oldEventSequence)
    {
        // CODREF(client_events): Ghosts ClientEvents 0x140114940 and BO1
        // 0x005F82E0 clamp to the newest four events, repair the 8-bit cursor
        // discontinuity when old > current + 64, then consume sequence & 3.
        // CODDIFF(client_events): unlike the native void loop, the source
        // adapter rejects a future or oversized cursor before dispatch.
        const auto currentSequence = SV_ReadNativePredictableEventSequence(
            source);
        const auto current = static_cast<std::int64_t>(currentSequence);
        auto first = static_cast<std::int64_t>(oldEventSequence);
        if (first < current - 4)
            first = current - 4;
        if (first > current + 64)
            first -= 256;
        if (first > current || current - first > 4)
            return std::nullopt;

        SvNativePredictableEventBatch result{
            .currentSequence = currentSequence,
            .count = static_cast<std::size_t>(current - first),
        };
        for (std::size_t index = 0; index < result.count; ++index)
        {
            const auto sequence = first + static_cast<std::int64_t>(index);
            const auto ringIndex =
                static_cast<std::uint32_t>(sequence) & 3u;
            result.events[index] = readValue<SvNativePredictableEvent>(
                source,
                PredictableEventsOffset +
                    ringIndex * sizeof(SvNativePredictableEvent));
        }
        return result;
    }

    void SV_AppendNativePlayerStatePredictableEvent(
        SvNativePlayerState &destination,
        const std::int32_t event,
        const std::int32_t parameter)
    {
        // The cursor is 8-bit in effect -- the batch reader repairs a discontinuity by
        // subtracting 256 -- and the ring is indexed by `cursor & 3`, so the slot to
        // write is the one the CURRENT cursor names and the cursor moves after it.
        const auto sequence = SV_ReadNativePredictableEventSequence(destination);
        const auto ringIndex = static_cast<std::uint32_t>(sequence) & 3u;
        writeValue(
            destination,
            PredictableEventsOffset +
                ringIndex * sizeof(SvNativePredictableEvent),
            SvNativePredictableEvent{ .event = event, .parameter = parameter });
        // ONE STEP, NEVER MORE. SV_ReadNativePredictableEvents refuses a batch wider
        // than four and that refusal fails the whole client think, so an appender that
        // could jump the cursor would be a way to freeze the player.
        writeValue(
            destination, PredictableEventSequenceOffset, sequence + 1);
    }

    std::array<SvNativePredictableEvent, 4> SV_ReadNativePredictableEventRing(
        const SvNativePlayerState &source)
    {
        // THE WIRE SENDS THE RING, NOT THE BATCH. Netfield indices 21..24 are
        // playerState +0x10C, +0x114, +0x11C and +0x124 -- ring slots 0..3 --
        // and the client indexes them by `sequence & 3` exactly as
        // SV_ReadNativePredictableEvents does. Copying the batch reader's
        // output in batch order would put the right events in the wrong slots
        // whenever fewer than four fired.
        std::array<SvNativePredictableEvent, 4> ring{};
        for (std::size_t index = 0; index < ring.size(); ++index)
        {
            ring[index] = readValue<SvNativePredictableEvent>(
                source,
                PredictableEventsOffset +
                    index * sizeof(SvNativePredictableEvent));
        }
        return ring;
    }

    SvNativeOffhandState SV_ReadNativeOffhandState(
        const SvNativePlayerState &source)
    {
        // CODREF(1649370): 429450 sets +4C=2047 on offhand entry; 4297D0
        // loads WeaponDef+2284 into +48 while +4C=2047. 429DA0 separately
        // tests the throwback timer +50 and selects its weapon from +54.
        return {
            .weaponAssetIndex = readValue<std::uint32_t>(source, 0x3E4),
            .grenadeTimeLeft = readValue<std::int32_t>(source, 0x48),
            .field004C = readValue<std::uint32_t>(source, 0x4C),
            .throwbackTimeLeft = readValue<std::int32_t>(source, 0x50),
            .throwbackWeaponAssetIndex = readValue<std::uint32_t>(source, 0x54),
        };
    }

    void SV_ClearNativeGrenadeTimer(SvNativePlayerState &candidate)
    {
        // CODREF(grenade_timer): BO1 InitGrenadeTimer / Ghosts 140137E60
        // consume the cooked timer when the grenade becomes server-owned.
        // CODOL owns the offset; do not clear the distinct throwback state.
        writeValue(candidate, 0x48, std::int32_t{});
    }

    SvNativePlayerStateActionDiagnostics
        SV_ReadNativePlayerStateActionDiagnostics(
            const SvNativePlayerState &source)
    {
        // OLMOD(native-playerstate-action-diagnostics): raw read-only values
        // explain projection rejection without creating another state owner.
        return {
            .pmType = readValue<std::int32_t>(source, PmTypeOffset),
            .clientNum = readValue<std::int32_t>(source, ClientNumOffset),
            .viewmodelIndex = readValue<std::uint32_t>(
                source, ViewmodelIndexOffset),
            .currentWeaponAssetIndex = readValue<std::uint32_t>(
                source, CurrentWeaponOffset),
            .weaponAnimation = {
                readValue<std::uint32_t>(source, RightWeaponAnimOffset),
                readValue<std::uint32_t>(source, LeftWeaponAnimOffset),
            },
            .weaponState = {
                readValue<std::int32_t>(source, RightWeaponStateOffset),
                readValue<std::int32_t>(source, LeftWeaponStateOffset),
            },
            .weaponShotCount = {
                readValue<std::uint32_t>(source, RightWeaponShotCountOffset),
                readValue<std::uint32_t>(source, LeftWeaponShotCountOffset),
            },
        };
    }
}
