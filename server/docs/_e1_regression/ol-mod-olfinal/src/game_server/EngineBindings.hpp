#pragma once
#include "server_mp/sv_rewards_mp.hpp"

#include "qcommon/msg_mp.hpp"
#include "server_mp/sv_collision_mp.hpp"
#include "server_mp/sv_damage_mp.hpp"
#include "server_mp/sv_gamestate_mp.hpp"
#include "server_mp/sv_mapents_mp.hpp"
#include "server_mp/sv_native_characterinfo_mp.hpp"
#include "server_mp/sv_native_entitystate_mp.hpp"
#include "server_mp/sv_native_playerstate_mp.hpp"
#include "server_mp/sv_native_pmove_mp.hpp"
#include "server_mp/sv_native_server_entity_mp.hpp"
#include "server_mp/sv_weapon_fire_mp.hpp"
#include "server_mp/sv_alpha_weapon_port_mp.hpp"
#include "server_mp/sv_weapon_loadout_mp.hpp"
#include "server_mp/sv_weapon_movement_mp.hpp"
#include "server_mp/sv_perks_mp.hpp"
#include "server_mp/sv_equipment_mp.hpp"
#include "server_mp/sv_trajectory_mp.hpp"
#include "server_mp/sv_grenade_launch_mp.hpp"
#include "server_mp/sv_grenade_detonation_mp.hpp"
#include "server_mp/sv_radius_damage_mp.hpp"
#include "../shared/DedicatedSession.hpp"

#include <array>
#include <atomic>
#include <cstddef>
#include <cstdint>
#include <map>
#include <optional>
#include <span>
#include <string>
#include <string_view>
#include <unordered_map>
#include <vector>

namespace CodolGameServer
{
    // THE NAME OF THE NATIVE STAGE CURRENTLY EXECUTING, for the vectored fault witness.
    // Every clientThink stage calls into the same shared BG code, so a faulting RVA on its
    // own cannot say which of ol-mod's calls arrived there. Set by NativeStageScope around
    // each native invoke; read only by the witness.
    [[nodiscard]] const char *SV_CurrentNativeStage();
    void SV_SetCurrentNativeStage(const char *stage);

    struct NativeStageScope
    {
        explicit NativeStageScope(const char *const stage)
        {
            SV_SetCurrentNativeStage(stage);
        }
        ~NativeStageScope() { SV_SetCurrentNativeStage("none"); }
        NativeStageScope(const NativeStageScope &) = delete;
        NativeStageScope &operator=(const NativeStageScope &) = delete;
    };

    struct SvResolvedLoadout;
    struct SvResolvedWeapon;
    struct SvCharacterCustomization;

    // OLMOD(native-exception-diagnostics): source-owned SEH capture used by
    // guarded x86 adapters. This is not a CODOL exception or CPU-context type.
    struct NativeExceptionDetails
    {
        std::uint32_t code{};
        const void *address{};
        std::uintptr_t accessType{};
        const void *faultAddress{};
        std::uintptr_t eax{};
        std::uintptr_t ebx{};
        std::uintptr_t ecx{};
        std::uintptr_t edx{};
        std::uintptr_t esi{};
        std::uintptr_t edi{};
        std::uintptr_t ebp{};
        std::uintptr_t esp{};
        std::uintptr_t eip{};
    };

    // OLMOD(loadout-resolution-diagnostics): source failure taxonomy for the
    // native client inventory/weapon resolver bridge, not a CODOL enum.
    enum class ClientLoadoutResolveFailure : std::uint32_t
    {
        None,
        StagedSlot,
        NativeResolverUnavailable,
        ItemName,
        BaseWeaponLookup,
        BaseWeaponResolver,
        DefaultAttachments,
        EquippedAttachmentName,
        EquippedAttachmentSlot,
        AttachmentMerge,
        AttachmentLookup,
        AttachmentCapacity,
        ModularWeaponResolver,
        WeaponDefinition,
        ModularWeaponDependency,
        AttachmentModelResolution,
    };

    // OLMOD(native-initialization-diagnostics): source-visible lifecycle
    // results; retained CODOL initializers expose narrower scalar results.
    enum class WeaponRegistryInitializationStatus : std::uint32_t
    {
        Ready,
        CommonAssetsUnavailable,
        InitializationFailed,
    };

    enum class AlphaWeaponPortStatus : std::uint32_t
    {
        Disabled,
        WaitingForCommonAssets,
        WaitingForWeaponRegistry,
        WrongThread,
        SourceAssetMissing,
        InvalidDefinition,
        LinkFailed,
        RegistrationFailed,
        Ready,
    };

    enum class ServerAnimationInitializationStatus : std::uint32_t
    {
        NotInitialized,
        Ready,
        InvalidBinding,
        WrongThread,
        ContextBusy,
        BeginLoadAnimTreesFailed,
        LoadAnimTreesFailed,
        AnimationScriptAssetsUnavailable,
        FindAnimsFailed,
        ParseAnimScriptFailed,
        PrecacheAnimTreesFailed,
        FindAnimTreesFailed,
        EndLoadAnimTreesFailed,
        FinalizePlayerAnimsFailed,
        InvalidOutput,
    };

    [[nodiscard]] std::string_view ServerAnimationInitializationStatusName(
        ServerAnimationInitializationStatus status);

    // OLMOD(character-resolution-diagnostics): source failure and checkpoint
    // data, not a recovered CODOL character-system structure.
    enum class ClientCharacterPresentationResolveFailure : std::uint32_t
    {
        None,
        InvalidRequest,
        ItemName,
        Selection,
        BaseItemDefinition,
        CharacterDefinitionTable,
        CharacterDefinition,
        ViewmodelConfigString,
        ConstantConfigStrings,
    };

    struct ClientCharacterPresentationResolveStatus
    {
        ClientCharacterPresentationResolveFailure failure{};
        std::uint32_t recordIndex{0xFFFFFFFFu};
        std::uint32_t itemId{};
    };

    // CODREF(character_customization):
    // CODOL_CharacterCustomization_BuildLocalModelList 0x00569C50 maps the
    // secondary character definition byte at +3 to a color name, then
    // CODOL_CharacterCustomization_ColorNameToSelector 0x0040C4C0 maps that
    // name to the model-variant selector. This is a CODOL marketplace layer;
    // BO1/Ghosts generate their server character models without this enum.
    [[nodiscard]] constexpr std::optional<std::uint8_t>
        CODOL_CharacterColorSelectorFromDefinitionValue(
            const std::uint8_t definitionValue) noexcept
    {
        // CODREF(character_customization): BuildLocalModelList
        // 0x00569CFA..0x00569D20 maps 0/1/2/3 to wht/cau/yel/blk. The native
        // selector table at 0x0040C4C0 is wht/yel/blk/cau, hence this exact
        // permutation.
        constexpr std::array<std::uint8_t, 4> SelectorByDefinitionValue{
            0, 3, 1, 2,
        };
        if (definitionValue >= SelectorByDefinitionValue.size())
            return std::nullopt;
        return SelectorByDefinitionValue[definitionValue];
    }

    // OLMOD(engine-binding-catalog): CODOL XAssetHeader is a one-pointer
    // union in this x86 build; only the generic data view crosses this header.
    struct XAssetHeader
    {
        void *data{};
    };

    // OLMOD(client-booking-projection): normalized client room selection read
    // from retained UI state. It is not a native room/session object layout.
    struct ClientBookingSelection
    {
        std::string mapName;
        std::string gameType;
        std::uint8_t playlistSlot{};
        std::int8_t rotationIndex{};
    };

    // OLMOD(native-weapon-projection): validated source projection assembled
    // from CODOL item, WeaponDef, attachment, and CCS owners. It deliberately
    // does not reproduce any one native structure layout.
    struct ClientWeaponSelection
    {
        std::uint32_t itemId{};
        std::uint32_t baseWeaponAssetIndex{};
        std::uint32_t weaponAssetIndex{};
        std::uint32_t ammoIndex{};
        std::int32_t clipIndex{};
        std::uint32_t clipSize{};
        std::uint32_t maxAmmo{};
        std::uint32_t weaponType{};
        std::uint32_t weaponClass{};
        std::uint32_t penetrateType{};
        std::uint32_t impactType{};
        std::uint32_t fireType{};
        std::uint32_t shotCount{};
        std::uint32_t meleeDamage{};
        std::uint32_t fireDelayMilliseconds{};
        std::uint32_t fireTimeMilliseconds{};
        std::uint32_t dropTimeMilliseconds{};
        std::uint32_t raiseTimeMilliseconds{};
        float hipSpreadStandMin{};
        float hipSpreadCrouchMin{};
        float hipSpreadProneMin{};
        float hipSpreadStandMax{};
        float hipSpreadCrouchMax{};
        float hipSpreadProneMax{};
        float adsSpread{};
        SvWeaponDamageCurve damageCurve{};
        std::array<float, HitLocationCount> hitLocationMultipliers{};
        bool aimDownSight{};
        bool hasOverlayReticle{};
        bool rifleBullet{};
        bool bulletExplosiveDamage{};
        bool dualWieldCapable{};
        std::array<std::uint32_t, 6> attachmentItemIds{};
        std::array<std::uint32_t, MaximumModularWeaponAttachmentCount>
            attachmentAssetIndexes{};
        std::uint32_t attachmentCount{};
        std::uint32_t modularValue8{};
        std::uint32_t modularValue9{};
        std::vector<SvModularWeaponConfigString> modularDependencies;
        std::string weaponName;
    };

    struct ClientWeaponLoadout
    {
        std::uint32_t characterIndex{};
        std::uint32_t classIndex{};
        ClientWeaponSelection primary;
        ClientWeaponSelection secondary;
    };

    // OLMOD(character-presentation-projection): source request passed into the
    // retained character-model resolver; not native characterInfo storage.
    // The viewhands model every character falls back to. The client finds its own
    // viewmodelIndex by searching the model configstrings for this exact name, so
    // the server resolves it the same way rather than inventing an index.
    inline constexpr std::string_view GenericCharacterViewhandsName =
        "viewhands_tf141";

    struct ClientCharacterPresentation
    {
        std::uint32_t characterIndex{};
        bool female{};
        std::uint8_t color{};
        std::uint16_t viewmodelIndex{};
        std::array<std::uint16_t, 11> selectionIds{};
        // SECTION 67's INPUT, and it is the whole input. The engine derives the other
        // eleven record entries from the character's own per-slot defaults, so this one
        // id is what model resolution needs. It comes from
        // LoadoutRequest::characterItemIds[0], which captureClientLoadoutRequest fills
        // from characterClasses[<character>].slots[0].
        //
        // It is NOT a wire field and SV_PackCharacterCustomization does not touch it.
        std::uint16_t characterItemId{};
        // AND THE OTHER ELEVEN, when the player has equipped any. Entry 0 mirrors
        // characterItemId; entries 1..11 are the outfit pieces, each already at the
        // record entry its own item definition claims (see
        // placeCharacterItemsByRecordEntry). Zeroes are what sub_619AD0 fills from the
        // character's per-slot defaults, so an empty array is exactly the old behaviour.
        std::array<std::uint16_t, 12> recordItemIds{};
    };

    class EngineBindings
    {
    public:
        // THE AUDITS ARE PUBLIC because the client bridge can now trigger them on a
        // RUNNING client (DedicatedControl::MessageType::RunDiagnostic). Every one of
        // these used to cost a full cycle -- rebuild, relaunch, and the player queueing up
        // again -- to answer a question that is a loop over a table the client already
        // holds. See auditWeaponItemsTable / reportUnlockAllCoverage / auditItemNames for
        // what each measures and why it is written the way it is.
        void auditWeaponItemsTable() const;
        void auditRewardTable() const;
        [[nodiscard]] std::optional<SvRewardWeapon> resolveUavWeapon() const;
        [[nodiscard]] std::optional<std::uint16_t> resolveBaseWeaponAssetIndex(
            std::string_view weaponName) const;
        [[nodiscard]] std::optional<SvResolvedRewards> resolveSessionRewards(
            const OlMod::DedicatedSession::LoadoutRequest &request) const;
        void reportUnlockAllCoverage() const;
        void probeOwnership() const;
        void auditItemNames() const;
        void auditEquippedPerks() const;
        void auditEquippedEquipment() const;

        // SECTION 190: the weapon's ALT, straight off weaponDefinition +3720.
        // sub_42EF60 links it from the name at +3716 during registration, and
        // for a modular weapon it BUILDS the modular alt (sub_431490) rather
        // than looking one up -- so this is already correct for the `** ...`
        // weapons this server publishes. 0 means the weapon has no alt.
        [[nodiscard]] std::uint16_t altWeaponAssetIndex(
            std::uint32_t weaponAssetIndex) const;
        // The same read the loadout path already does, exposed so the alt
        // weapon -- which is a real weapon asset and not in any loadout -- can
        // be resolved on demand for the fire path.
        [[nodiscard]] bool readWeaponSelection(
            std::uint32_t weaponAssetIndex,
            ClientWeaponSelection &selection) const;
        // OLMOD(engine-binding-catalog): direct-call typedefs below have
        // CODOL-local x86 call-site evidence. Retained functions with custom
        // register ABIs stay void* and are callable only through their guarded
        // adapters in EngineBindings.cpp.
        // DB_FindXAssetHeader KEEPS its third parameter on 1649370. out.exe has
        // BOTH forms and DBFindXAssetHeaderRva names the three-argument one:
        //     sub_49CF30(type, name, allowDefault)   <- 0x09CF30, bound here
        //     sub_49D3B0(type, name)                 <- 0x09D3B0, a wrapper
        //                                               that hardcodes 1
        // The weapon resolver happens to call the wrapper, and reading only
        // that call site is how this was briefly declared with two parameters.
        // Under __cdecl the caller cleans up, so dropping the argument does not
        // crash either: the callee reads `allowDefault` out of whatever the
        // caller's stack happened to hold, and `if (a3)` then decides at random
        // whether a MISSING asset comes back as nullptr or as a freshly
        // created default placeholder with null strings in it.
        //
        // audit-binding-abi.py --reference reads +0x8, +0xC and +0x10 on BOTH
        // builds. It could not see that until it stopped ending its scan at the
        // first call: sub_49CF30 reads a3 at 0x49D335, a dozen calls in.
        // findXAsset() still asks DB_IsXAssetDefault separately, because
        // allowDefault=false suppresses the default only on the miss path -
        // an asset present but not yet loaded still comes back as the default.
        using DBFindXAssetHeader = XAssetHeader(__cdecl *)(
            std::uint32_t type,
            const char *name,
            bool allowDefault);
        using DBIsXAssetDefault = bool(__cdecl *)(
            std::uint32_t type,
            const char *name);
        // CODREF(alpha_weapon_port): DB_LinkXAssetEntry 0x49DA10 receives an
        // XAssetType and a pointer to XAssetHeader.data. For a new asset it
        // allocates an engine-owned entry/header, copies the type-dispatched
        // size, inserts the entry into the name hash, and replaces *header
        // with the published engine pointer. Its prologue reads the second
        // argument from [ebp+0xC], so this is ordinary __cdecl.
        using DBLinkXAssetEntry = void *(__cdecl *)(
            std::uint32_t type,
            void **header);
        using CCSInitialize = int(__cdecl *)();
        using CurrentCharacterGet = int(__cdecl *)();
        // sub_50FF30, cdecl, two int arguments -- the character index and the slot.
        // CodolMatchFlow.py declares it exactly this way and calls it live.
        using CharacterSlotGet = int(__cdecl *)(int characterIndex, int slot);
        // sub_7C5BA0: fills the client's 160-byte loadout record. Plain __cdecl with
        // one pointer, so it needs no register adapter.
        using LoadoutRecordBuild = unsigned short(__cdecl *)(unsigned short *record);
        // CODDIFF(1649370): sub_619E90 takes TWO arguments, not one, and the first is in
        // EAX -- so it has no C calling convention and is stored as a raw pointer, the
        // same way ConfigStringGet already is. The game's own call site says so outright:
        //
        //     618bbe  push ecx        ; the 144-byte destination record
        //     618bbf  mov eax, edi    ; <- the index, in EAX
        //     618bc1  call sub_619E90
        //     618bc6  add esp, 4      ; ONE stack argument, caller cleans
        //
        // and edi there is a loop counter running 0 .. dword_82E13A4 - 1, so the index is
        // a SESSION MEMBER index and not a character index. sub_619E90 scales it by 160
        // (`lea edi,[edi+edi*4]` then `shl edi,5`) into the member array at unk_C911424,
        // and sub_620B90 clears that array with the bound `v0 <= 0x11` -- eighteen
        // entries, which is MaximumSessionMembers, not the twelve of CharacterItemCount.
        //
        // Declared as void(__cdecl *)(void *) it ran with EAX holding whatever the last
        // expression left there, i.e. it indexed the member array at an arbitrary offset.
        // There is deliberately no `using` for it: a type that cannot express the ABI is
        // exactly what let the wrong one compile.
        // CODDIFF(1649370): CL_GetConfigString takes its index in ESI on this
        // build, not ECX, so it has NO C calling convention and is stored as a
        // raw pointer and reached through nativeConfigString(). 3.3.3.3's
        // sub_4F9850 opens `cmp ecx, 0x1B92`; out.exe's sub_514880 opens
        // `cmp esi, 0x31D9` and indexes the class table as [esi + 0x77D8250].
        // Declared __fastcall the index went to ECX and the callee read
        // whatever the caller had left in ESI, so EVERY index returned the same
        // unrelated string.
        using WeaponLookup = std::uint32_t(__cdecl *)(const char *name);
        using WeaponResolver = std::uint32_t(__cdecl *)(
            const char *name,
            void (__cdecl *registerCallback)(int));
        using AttachmentLookup = std::uint32_t(__cdecl *)(const char *name);
        using WeaponRegistryReset = void(__cdecl *)();
        // CODDIFF(1649370): BG_InitWeaponStrings GAINED a parameter. 3.3.3.3's
        // reads no stack slot at all; out.exe's sub_42FE80 reads [ebp+8], and
        // both of the game's own callers - CL_ParseGamestate at 0x454B3F and
        // the lazy Com_Frame rebuild at 0x4FE1AC - `push 1` before calling it.
        // Declared with no parameters it read that flag off the caller's stack.
        using WeaponRegistryInitialize = std::int32_t(__cdecl *)(
            std::int32_t completeRegistration);
        // sub_430670, "mp/coKnifeStatsTable.csv". Both of the game's rebuilds
        // call it immediately after BG_InitWeaponStrings; it self-guards on
        // byte_C7341DA and on the table's own column count.
        using WeaponKnifeStatsLoad = std::int32_t(__cdecl *)();
        using ZoneLoaded = bool(__cdecl *)(const char *name);
        using BGGetPlayerEyePosition = void(__cdecl *)(
            std::int32_t linkedEntityContext,
            const void *playerState,
            float *origin,
            std::int32_t time);
        using Trace = void(__cdecl *)(
            void *result,
            const float *start,
            const float *end,
            const TraceBounds *bounds,
            std::int32_t passEntityNum,
            std::uint32_t contentMask);

        // OLMOD(engine-binding-catalog): fixed identity and DB/qcommon/CCS
        // entry points for the 0x57611E31, 0x0C72A000 CODOL executable only.
        // Prefix guards in bind() reject another build but do not by themselves
        // prove complete ABI or pointed-to global layout semantics.
        static constexpr std::uint32_t ExpectedTimestamp = 0x6096930A;
        static constexpr std::size_t ExpectedImageSize = 0x0E5D6000;
        static constexpr std::size_t ComFrameRva = 0x0FEA20;
        static constexpr std::size_t DBFindXAssetHeaderRva = 0x09CF30;
        static constexpr std::size_t DBIsXAssetDefaultRva = 0x09D3D0;
        static constexpr std::size_t DBLinkXAssetEntryRva = 0x09DA10;
        static constexpr std::size_t MsgInitRva = 0x26E720;
        static constexpr std::size_t MsgWriteBitsRva = 0x26E840;
        static constexpr std::size_t MsgWriteStringRva = 0x26EA90;
        static constexpr std::size_t LevelZoneLoadRva = 0x09E600;
        static constexpr std::size_t CCSClearRva = 0x261610;
        static constexpr std::size_t CCSInitializeRva = 0x261A30;
        static constexpr std::size_t CCSGetConstantStringRva = 0x261C50;

        // CODREF(section-79-ui-dvar-cache): the CLIENT's gametype dvar POINTER
        // CACHE and the one function that fills it. `sub_4E8990` is the only
        // writer of every slot in that table, it has exactly one caller, and
        // the chain above it -- sub_616F60 <- sub_6172E0 <- sub_617700 <-
        // sub_4757D0 -- is gated on DB_IsZoneLoaded("ui_mp"). A client driven
        // into a match without the legacy UI zone ever loading therefore
        // reaches CL_ParseGamestate with the cache still NULL, and the level
        // load faults at 0x0043204F reading [cache + 0x0C]. These four are
        // CLIENT-process addresses; the dedicated never touches them.
        static constexpr std::size_t RegisterGameplayDvarsRva = 0x0E8990;
        static constexpr std::size_t GametypeDvarCacheRva = 0x2EAA908;
        static constexpr std::size_t IsZoneLoadedRva = 0x09F180;
        static constexpr std::size_t UiZoneNameRva = 0x9B5F58;
        static constexpr std::size_t UiZoneStateFlagsRva = 0x18DAF1C;

        // CODREF(sv_link_entity): collision, entity mirror, locational DObj,
        // and retained server trace entry/global addresses for this build.
        static constexpr std::size_t TraceRva = 0x06EA60;
        static constexpr std::size_t WorldTraceRva = 0x268220;
        static constexpr std::size_t TransformedBrushModelTraceRva = 0x268470;
        static constexpr std::size_t TransformedCapsuleTraceRva = 0x268560;
        static constexpr std::size_t CalcTraceExtentsRva = 0x269460;
        static constexpr std::size_t PointTraceToEntitiesRva = 0x06E6D0;
        static constexpr std::size_t DObjGeomTracelinePartBitsRva = 0x3831C0;
        // CODREF(sv_trace): the contents variant SV_PointTraceToEntity uses for
        // any entity whose svFlags bit 2 is set - which this project sets for
        // every ScriptModelDObj (sv_native_server_entity_mp.cpp). Posing those
        // with the locational variant's bones leaves the ones the trace
        // actually reads uncomputed, and an uncomputed bone keeps the zeroed
        // matrix and collapses onto the model origin.
        static constexpr std::size_t DObjContentsTracelinePartBitsRva = 0x383360;
        // CODREF(sv_trace): DObjTraceline, byte-identical to 3.3.3.3's
        // 0x00645DD0. THIS BUILD HAS NO SV_PointTraceToEntity, so nothing in
        // out.exe calls it against a SERVER entity and this project has to be
        // the caller - see traceServerLocationalEntities and section 73.
        static constexpr std::size_t DObjTracelineRva = 0x3825F0;
        // CODREF(out.exe 46E235..46E24E): five cdecl arguments, contents-based
        // script-model geometry. The player priority-map tracer is separate.
        static constexpr std::size_t DObjContentsTracelineRva = 0x383290;
        // CODREF(out.exe 46E807..46E816): point trace against static map models,
        // called after WorldTrace. EDX mask, ECX end, EDI trace, stack start.
        static constexpr std::size_t PointTraceStaticModelsRva = 0x26A3D0;
        static constexpr std::size_t DObjCalcSkelRva = 0x3847A0;
        static constexpr std::size_t GEntitiesRva = 0x2D437A0;
        static constexpr std::size_t ServerGameEntitiesPointerRva = 0x76BAC74;
        static constexpr std::size_t ServerGameEntityCountRva = 0x76BAC78;
        static constexpr std::size_t SVLinkEntityRva = 0x34EF10;
        static constexpr std::size_t SVUnlinkEntityRva = 0x34ECE0;
        static constexpr std::size_t SVTraceRva = 0x06E780;
        static constexpr std::size_t CollisionMapRva = 0x73E1C00;

        // CODREF(fire_weapon): retained eye, bullet-endpoint, view/weapon
        // movement, matrix, Pmove, and playerstate conversion entry points.
        // Custom register contracts remain isolated in the .cpp adapters.
        static constexpr std::size_t BGGetPlayerEyePositionRva = 0x0123B0;
        static constexpr std::size_t BulletEndposRva = 0x192230;
        static constexpr std::size_t ViewMovementDamageKickRva = 0x0353E0;
        static constexpr std::size_t ViewMovementIdleAnglesRva = 0x0355D0;
        static constexpr std::size_t ViewMovementBobAnglesRva = 0x035770;
        static constexpr std::size_t ViewMovementAdsBobRva = 0x035910;
        static constexpr std::size_t WeaponMovementBaseRva = 0x034520;
        static constexpr std::size_t WeaponMovementSwayRva = 0x034680;
        static constexpr std::size_t WeaponMovementRecoilRva = 0x034C20;
        static constexpr std::size_t WeaponMovementBobRva = 0x034E20;
        static constexpr std::size_t SetWeaponMovementAnglesRva = 0x034F90;
        // NOT AnglesToAxis, whatever it used to be called here. sub_7853E0
        // reads three angles through ESI and writes FOUR floats through EDX;
        // 3.3.3.3's nine-float AnglesToAxis 0x0062C1A0 has no counterpart on
        // this build. Kept bound and guarded, called by nothing. Section 73f.
        static constexpr std::size_t AnglesToQuaternionRva = 0x3853E0;
        // CODREF(sv_trace): AngleVectors, `void __cdecl(const float angles[3],
        // float *forward, float *right, float *up)` - four STACK arguments,
        // three separate destinations. The counterpart of 3.3.3.3's
        // AnglesToAxis 0x0062C1A0 (one contiguous nine-float destination) does
        // not exist on this build; this is what does, and Quake-derived engines
        // define AnglesToAxis as AngleVectors plus VectorInverse on the second
        // row, which is what traceServerLocationalEntities does.
        //
        // AnglesToQuaternionRva 0x3853E0 ABOVE IS NOT AnglesToAxis. sub_7853E0 reads
        // its angles through ESI, writes FOUR floats through EDX, and is an
        // angles-to-QUATERNION. See section 73f.
        static constexpr std::size_t AngleVectorsRva = 0x367890;
        static constexpr std::size_t MatrixMultiplyRva = 0x3653E0;
        static constexpr std::size_t AxisToAnglesRva = 0x3667B0;
        static constexpr std::size_t PmoveSingleRva = 0x01CB40;
        static constexpr std::size_t PMSetPitchValuesRva = 0x01DB40;
        static constexpr std::size_t PlayerStateToEntityStateRva = 0x0116F0;

        // CODREF(bg_update_player_dobj): retained animation, character model,
        // XAnim, DObj, handler-table, and backing-global addresses. Scratch
        // storage sizes below are ol-mod owners, not recovered native structs.
        static constexpr std::size_t BGAnimScriptEventRva = 0x007E10;
        static constexpr std::size_t BGFindAnimsRva = 0x004D80;
        static constexpr std::size_t BGAnimParseAnimScriptRva = 0x007530;
        static constexpr std::size_t BGLoadAnimTreesRva = 0x00B130;
        static constexpr std::size_t ScrCreateObjectRva = 0x34CED0;
        // CODDIFF(1649370): this was bound to sub_74AAF0, which is the INNER
        // per-tree worker, not Scr_PrecacheAnimTrees. sub_74AAF0's only caller
        // is sub_74AF50:
        //     for (i = 1; i <= dword_789C634[a1]; ++i) sub_74AAF0(i, a2, a1);
        // and CL_ParseGamestate calls THAT one, with the anim user in EDI and
        // the allocator on the stack:
        //     454cef  mov edi, [eax+0AF314h]
        //     454cf5  push edx
        //     454cf6  call sub_74AF50
        // Bound to the worker and called with two cdecl arguments, the loop
        // never ran and the worker read a third argument nobody pushed.
        static constexpr std::size_t ScrPrecacheAnimTreesRva = 0x34AF50;
        static constexpr std::size_t BGFindAnimTreesRva = 0x00B210;
        static constexpr std::size_t BGFinalizePlayerAnimsRva = 0x004FE0;
        static constexpr std::size_t NativeLerpFrameAccessorInitializeRva =
            0x003C70;
        static constexpr std::size_t BGPlayerAnimationRva = 0x00A960;
        static constexpr std::size_t BGUpdatePlayerDObjRva = 0x00AB30;
        static constexpr std::size_t MantleCreateAnimsRva = 0x00CCA0;
        static constexpr std::size_t MantleAnimsRva = 0x1574568;
        static constexpr std::size_t HunkAllocXAnimRva = 0x368220;
        // CODREF(client_spawn): the two XAnim walkers CODOL's own per-client
        // animation reset uses. sub_BB89E0 (VA 0x005189E0), gated on
        // !(eFlags & 0x20000), zeroes the tree's goal weights BEFORE it
        // memsets the lerp frames:
        //   edx = characterInfo[+0x320]          the tree
        //   ax  = word[edx+4]                    its root node; skip if 0
        //   n   = XAnimFindNode(tree, 0, root)   VA 0x0064B490
        //   if (n) XAnimSetCompleteGoalWeight(tree, n, 0.0f, 1, -1)
        //                                        VA 0x0064BD90
        // The per-node worker VA 0x0064BC90 writes BOTH node +0x24 and +0x28,
        // so this is an instant zero of the whole subtree, not a blend.
        // CODREF(client_spawn): XAnimFreeInfo. BO1 names the whole shape -
        // XAnimClearTree 0x007F3D30 is just
        //     if (tree->children) { XAnimFreeInfo(tree, tree->children);
        //                           assert(!tree->children); }
        // and CODOL's is VA 0x006497C0: it indexes the 56-byte node pool at
        // VA 0x0374DB08, recurses over children at 0x00649879 and siblings at
        // 0x00649813, returns each node to the pool, and finally writes
        //     mov edx, [ebp+8] / mov word [edx+4], ax        (0x006498B2)
        // so the tree's own children field ends at 0. That restores the tree
        // to EXACTLY its post-creation state - `{anims, 0}` - with no node
        // leak, which zeroing goal weights does not do.
        static constexpr std::size_t XAnimFreeInfoRva = 0x386340;
        static constexpr std::size_t DObjFreeRva = 0x381A80;
        static constexpr std::size_t ServerDObjGetRva = 0x34E160;
        static constexpr std::size_t ServerDObjCreateRva = 0x26BEE0;
        static constexpr std::size_t ServerDObjMapRva = 0x73E7F20;
        static constexpr std::size_t ServerDObjInUseRva = 0x73E8F20;
        static constexpr std::size_t ServerDObjPoolRva = 0x73E9720;
        static constexpr std::size_t ServerDObjFreeCountRva = 0x73E7F1C;
        // CODREF(bg_update_player_dobj): the SECOND entity-to-DObj table. One
        // 0xCC-stride pool at VA 0x02E8E850 is reached through two different
        // maps: ServerDObjGet VA 0x0059E570 divides a gentity POINTER down to
        // an index and reads VA 0x02E8D050 (ServerDObjMapRva above), while the
        // callback this project installs at animBase+0x96E04 (RVA 0x0455D0)
        // indexes VA 0x02EF4858 by entityState.number directly.
        // BG_SetLerpFrameAnimation VA 0x00409BF0 resolves its DObj through that
        // callback and BAILS at 0x00409C2E when it returns null - so a player
        // absent from THIS table never has an animation set at all, however
        // healthy the other table looks. TODO(CODOL): diagnostic only; remove
        // once both words are confirmed populated for a live player.
        static constexpr std::size_t ServerAnimDObjMapRva = 0x7455720;
        static constexpr std::size_t NativeLerpFrameZeroVectorRva = 0x9A2B2C;
        static constexpr std::size_t NativeLerpFrameSetKeyRva = 0xA60B3C;
        // CODREF(playerstate_accessor): THE PLAYERSTATE CARRIES ITS OWN ACCESSOR PAIR,
        // keyed on two DIFFERENT cookies from the same CryptGenRandom pool. The engine's
        // playerState initializer sub_5BEB50 -- the clear loop this project already cites
        // for the 0x3BBC stride -- sets it up per state:
        //     mov edx, dword_E60B74      ; setKey
        //     lea eax, [edi+ebx+20h]     ; SET slot  = playerState + 0x20
        //     lea ecx, [edi+ebx+24h]     ; GET slot  = playerState + 0x24
        //     mov edx, dword_E60B78      ; getKey
        //     call sub_403C70
        // and PmoveSingle decodes the GET slot with exactly that second cookie.
        static constexpr std::size_t NativePlayerStateAccessorSetKeyRva = 0xA60B74;
        static constexpr std::size_t NativePlayerStateAccessorGetKeyRva = 0xA60B78;
        static constexpr std::size_t NativeLerpFrameGetKeyRva = 0xA60B40;
        static constexpr std::size_t PmoveHandlersRva = 0xA5FCD0;
        static constexpr std::size_t AnimConditionBasePointerRva = 0x7E7F730;
        static constexpr std::size_t AnimScriptDataPointerRva = 0x7E7F734;
        // CODDIFF(1649370): THIS BUFFER WAS SMALLER THAN WHAT THE GAME WRITES
        // INTO IT. It was 0xA6000, and BG_FindAnimTrees opens with
        //     40b21e  push 0ACE70h; Size
        //     40b225  push eax          ; eax = dword_827F730, i.e. this array
        //     40b226  call _memset
        // which is 0xACE70 = 708,208 bytes - 28,272 past the end. The live log
        // shows serverLoadAnimStorage_ starting at exactly base + 0xA6000, so
        // the overrun lands in the next member rather than in unmapped memory,
        // which is why it corrupted rather than crashed.
        //
        // The reads go further still, and all of them are off this same base:
        //     +0xAF31C  sub_407530's script-mode byte
        //     +0xAF314  sub_74AF50's anim user     +0xAF338 its allocator
        //     +0xAF350  sub_407E10's per-entry array, stride 0x450
        //     +0xAF318  CL_ParseGamestate writes here at 0x454CD4
        // 0xAF350 + 18 * 0x450 = 0xB4200 for this project's client count, and
        // the game's own block is `ebx + 0xD1900` inside a larger allocation
        // whose extent is not visible. So this is rounded UP well past every
        // measured offset rather than fitted to them: over-allocating costs
        // address space, under-allocating hands the engine someone else's
        // memory and the failure looks like anything at all.
        static constexpr std::size_t ServerAnimConditionStorageSize = 0x100000;
        static_assert(
            ServerAnimConditionStorageSize >= 0xACE70,
            "BG_FindAnimTrees memsets 0xACE70 bytes at this base");
        static_assert(
            ServerAnimConditionStorageSize >= 0xAF350 + 18 * 0x450,
            "sub_407E10 indexes +0xAF350 with a 0x450 stride, per client");
        // WHERE scriptEvents SITS RELATIVE TO THE TWO REGIONS ABOVE, because
        // that is what makes the init order legal. BG_AnimParseAnimScript
        // sub_407530 clears the movetype table at +0x1A004 and one scrap script
        // at +0x25D7C and DOES NOT clear scriptEvents, so parses accumulate
        // into it; the only thing that ever zeroes it is BG_FindAnimTrees
        // sub_40B210's `memset(dword_827F730, 0, 0xACE70)` at 0x0040B226.
        // initializeServerAnimation runs parse -> BG_FindAnimTrees ->
        // BG_FinalizePlayerAnims, which is CL_ParseGamestate's own order
        // (0x00454CDF, 0x00454D38, 0x00454D42) and leaves finalize's re-parse
        // as the one that populates the event table. That is only true while
        // the whole event table falls inside the memset and outside the
        // characterInfo array; assert it rather than trusting the comment.
        static_assert(
            SvNativeAnimScriptEventTableOffset +
                    SvNativeAnimScriptEventCount * SvNativeAnimScriptStride <=
                0xACE70,
            "BG_FindAnimTrees' 0xACE70 memset must cover the whole event "
            "table, or finalize's re-parse would append to a stale one");
        static_assert(
            SvNativeAnimScriptEventTableOffset +
                    SvNativeAnimScriptEventCount * SvNativeAnimScriptStride <=
                0xAF350,
            "the event table must not overlap the per-client characterInfo "
            "array sub_407E10 derives at +0xAF350");
        // CODREF(bg_update_player_dobj): the locomotion anim-script state setter
        // indexes the per-client characterInfo_t array from the anim-condition
        // base at this fixed byte offset, with a sizeof(characterInfo) stride.
        //
        // CODDIFF(1649370): 618016 (0x96E20) is 3.3.3.3's; this build derives
        // the array at 717648 (0xAF350). Both builds state it in the same
        // instruction pair -- 3.3.3.3 at 0x004094C0
        //     mov ecx,[eax+0x144] ; imul ecx,ecx,0x3B8 ; lea edi,[ecx+edx+0x96E20]
        // and this build with clientNum at ps+0x158 and a 0x450 stride. Scanning
        // every such site: 0x96E20 in 12 of 14 on 3.3.3.3, 0xAF350 in 11 of 16
        // here, the outliers in both being field reads INSIDE the struct
        // (base + 0x2D0 / 0x308 there, base + 0x334 / 0x37C here). It also
        // agrees with the animation projection at 0x53DE1F, which reaches the
        // same array as `lea edi, [ecx + eax + 0xAF350]`.
        //
        // The measurement was already in this file -- the storage comment above
        // lists "+0xAF350 sub_407E10's per-entry array, stride 0x450" and the
        // static_assert below it is written against those exact numbers. The
        // constant the code actually places the array with was simply never
        // moved to match, so the storage was sized for the right region and the
        // array was put somewhere else inside it.
        //
        // TODO(CODOL): on 3.3.3.3 this relocation was NECESSARY BUT PROVEN
        // INSUFFICIENT.
        // Measured live on 2026-08-16 immediately after it landed: torsoAnim
        // still carries a real index in only 5% of samples against legsAnim's
        // 98%, so sub_AA94C0 still bails before selecting a locomotion
        // animation and the hit skeleton is still one stance low. It is NOT
        // the other anim global - CODOL's loader does `mov esi, [0x7817B80]`
        // at 0x00445DAF and BG_AnimParseAnimScript stores it straight into
        // 0x7817B84 at 0x0040905E, so the two names hold one pointer and
        // initializeServerAnimation already gates on their being equal. Of the
        // four bail-outs only the script count at +0x1A004 + 0x204 * movetype
        // survives static elimination; logServerAnimScriptTable reports it.
        // Exit when torsoAnim varies with movement and a neck hit resolves near
        // 58 rather than 36. That measurement was taken on 3.3.3.3, where the
        // array at least landed at the offset the engine derives; here it did
        // not, so it says nothing about this build yet.
        static constexpr std::size_t ServerCharacterInfoBaseOffset = 0xAF350;
        static constexpr std::size_t ServerCharacterInfoSlotCount = 18;
        static_assert(
            ServerCharacterInfoBaseOffset +
                    ServerCharacterInfoSlotCount * SvNativeCharacterInfoSize <=
                ServerAnimConditionStorageSize,
            "the derived characterInfo array must fit inside the installed "
            "anim-condition storage: sub_AA94C0 reads it there whether or not "
            "this project put anything at that offset");
        // CONFIRMED against out.exe, and it is 1024 x 72 exactly.
        //
        // This buffer is the `loadAnims` array BG_AnimParseAnimScript takes in
        // ECX, and CL_ParseGamestate's own call states both of its dimensions:
        //     454c6d  mov [ebp+var_100], 400h     ; the animation CAPACITY
        //     454cca  mov esi, dword_827F730      ; the anim-condition base
        //     454cd6  push 0
        //     454cd8  push ecx                    ; &var_100
        //     454cd9  mov ecx, [ebp+var_10C]      ; the loadAnims array
        //     454cdf  call sub_407530
        // sub_407530 stores that array in dword_1971E04 and saves the capacity
        // in dword_196DB0C before zeroing the caller's count, and sub_404FE0
        // walks the array with `v5 += 72`. So 0x400 slots of 72 bytes is
        // 0x12000, and MaximumPlayerAnimations is the same 1024 the engine
        // passes. This value is IDENTICAL to 3.3.3.3's and is nonetheless
        // right -- which is the whole reason a match is a suspicion and only a
        // check is a result.
        static constexpr std::size_t ServerLoadAnimStorageSize = 0x12000;

        // CODREF(fire_weapon): retained weapon registry and zone/collision
        // initialization functions plus weapon/attachment backing globals.
        static constexpr std::size_t WeaponLookupRva = 0x02F2F0;
        static constexpr std::size_t WeaponResolverRva = 0x02F3E0;
        static constexpr std::size_t AttachmentLookupRva = 0x02F650;
        static constexpr std::size_t WeaponRegistryResetRva = 0x02F160;
        static constexpr std::size_t WeaponRegistryInitializeRva = 0x02FE80;
        static constexpr std::size_t ZoneLoadedRva = 0x09F180;
        static constexpr std::size_t CollisionMapLoadRva = 0x262D90;
        static constexpr std::size_t CollisionWorldLinkRva = 0x269A40;
        static constexpr std::size_t WeaponDefinitionsRva = 0x1588B50;
        static constexpr std::size_t WeaponRegistryCountRva = 0x7E7F738;
        // CODDIFF(1649370): WeaponLookup 0x42F2F0 reads BOTH of these - the
        // count as its upper bound and this one as a memo of the last index it
        // found - and 0x827F73C has exactly two references in the whole image,
        // both inside that function. Nothing else owns it.
        static constexpr std::size_t WeaponRegistryLookupCacheRva = 0x7E7F73C;
        // CODREF(cl_parse_gamestate): the game's OWN weapon-registry rebuild is
        // sub_453760+0x12D0 (CL_ParseGamestate, "gamestateupdate %d") and the
        // lazy Com_Frame one is sub_4FE120. Both set this mode word to 2 before
        // resetting, and both call BG_InitWeaponStrings with 1 and then load
        // the knife stats table. Nothing here is inferred from 3.3.3.3.
        static constexpr std::size_t WeaponRegistryModeRva = 0x7ECA52C;
        static constexpr std::size_t WeaponKnifeStatsLoadRva = 0x030670;
        // CODREF(gameplay_dvars): THE GAMEPLAY DVARS ARE REGISTERED BY CG_Init,
        // AND CG_Init NEVER RUNS IN A DEDICATED PROCESS. sub_616F60 calls eight
        // registration blocks back to back at 0x61701D..0x617040, and in a
        // driven server NONE of them have run - so every dvar pointer they
        // cache is still null, and the native code that reads one does it the
        // way sub_432000 does: `mov ecx, [edx+0Ch]`, no null check.
        //
        // That is what faulted. The weapon registry's per-weapon gametype
        // filter reads `*(char **)(g_gametype + 0xC)` to test the weapon's
        // '|'-separated gametype list, and read address 0xC.
        //
        // SEVEN of the eight are called here, in CG_Init's order. Each was
        // disassembled first and each is nothing but `push "name"; call
        // Dvar_Register*; mov dword_..., eax` - no device state, no allocation,
        // and idempotent, because Dvar_Register hands back an existing dvar.
        // THE EIGHTH IS NOT ONE OF THEM: sub_4EAC90 opens with
        // memset(unk_31437A0, 0, 0x164000) and is a state initializer that
        // happens to sit in the same run of calls. It is left out on purpose.
        static constexpr std::size_t GameplayDvarsRegisterRva = 0x00E8990;
        static constexpr std::size_t GameLogDvarsRegisterRva = 0x00EA390;
        static constexpr std::size_t VehicleDvarsRegisterRva = 0x03BC5C0;
        static constexpr std::size_t PlayerDvarsRegisterRva = 0x00EAF30;
        static constexpr std::size_t ActorDvarsRegisterRva = 0x000FAF0;
        static constexpr std::size_t MiscDvarsRegisterRva = 0x03C2240;
        static constexpr std::size_t ScoreDvarsRegisterRva = 0x00E83F0;
        static constexpr std::size_t GametypeDvarRva = 0x2EAA908;
        // The walk's own base and count, read off the game's loop rather than
        // derived: sub_59B560 opens `lea esi, [edi+1748h]` before calling
        // CL_GetConfigString, and CL_ParseGamestate bounds the loop with
        // `cmp edi, 6A4h`. 0x1748 = 5960 and 0x6A4 = 1700, which is exactly
        // what sv_gamestate_mp.hpp derived a different way in §26.
        static constexpr std::size_t WeaponConfigStringWalkRva = 0x019B560;
        static constexpr std::uint32_t WeaponWalkConfigStringBase = 0x1748;
        static constexpr std::uint32_t WeaponWalkEntryCount = 0x6A4;
        // Com_Error's own state. sub_4F82E0 formats into the text buffer, keeps
        // the level, bumps the depth, and then LONGJMPS - so after a native
        // fault a non-zero depth says the engine raised an error rather than
        // dereferencing something, and the text says which one.
        static constexpr std::size_t ComErrorTextRva = 0x2FE7958;
        static constexpr std::size_t ComErrorLevelRva = 0x2FE7904;
        static constexpr std::size_t ComErrorDepthRva = 0x31053DC;
        static constexpr std::size_t AttachmentModelCountRva = 0x1588B4C;
        // CODDIFF(1649370): the per-weapon attachment count array is 1300
        // entries here and 500 on 3.3.3.3, and it is bounded by the two RVAs
        // either side of it - so the static_assert below is the measurement,
        // not a comment about one. It lives here because it was written out
        // twice and only ONE copy got updated, which quietly rejected every
        // base weapon from 500 up as out of range.
        static constexpr std::uint32_t BaseWeaponAssetCount = 0x514;
        // CODDIFF(1649370): every weapon-index sanity check in this project
        // was `> 0x3FF`, which is 3.3.3.3's. That number is a WIRE WIDTH, not
        // a table size: the weapon index is ten bits there and ELEVEN here
        // (sv_gamestate_mp.cpp's WeaponIndexBits, section 26), and the registry
        // table went 900 -> 1700 entries with it. A modular weapon is
        // registered dynamically and lands near the END of that table, so
        // rejecting anything above 1023 rejected exactly the weapons a real
        // loadout produces.
        // Defined in sv_gamestate_mp.hpp; ALIASED here, never re-derived.
        static constexpr std::uint32_t MaximumWeaponAssetIndex =
            ::CodolGameServer::MaximumWeaponAssetIndex;
        static constexpr std::size_t PerWeaponAttachmentCountsRva = 0x1588638;
        static constexpr std::size_t AttachmentModelDefinitionsRva = 0x158B8A0;
        static constexpr std::size_t AttachmentMappingsRva = 0x158C0A0;
        // dword_1978640, the interned-string table sub_42F4C0/sub_42F650 hash into.
        // Entry [id] is the char* for that id, which makes the attachment mapping
        // table READABLE AS TEXT instead of as two opaque halves. Section 187.
        static constexpr std::size_t InternedStringTableRva = 0x1578640;
        static constexpr std::size_t NoneAttachmentModelIndexRva = 0x15DDECC;
        static_assert(
            AttachmentModelCountRva - PerWeaponAttachmentCountsRva ==
                BaseWeaponAssetCount,
            "the per-weapon attachment counts are one byte each and fill the "
            "gap between these two globals: change a base weapon count without "
            "the RVAs and this is what says so");

        // OLMOD(engine-binding-catalog): retained client loadout, character,
        // config-string, item table, secure-origin, and room-state addresses.
        // OLMOD(client-state-capture): these are read-side migration inputs;
        // authoritative server ownership must not be inferred from them.
        static constexpr std::size_t CharacterCurrentItemsCopyRva = 0x219E90;
        // CODDIFF(client_loadout_capture): "no address is established on 1649370" was
        // WRONG for this one, and the address was in this repository the whole time.
        // tools/runtime/CodolMatchFlow.py's 1649370 block carries
        // CURRENT_CHARACTER_GET_RVA = 0x2B87C0 and calls it every run; it returned
        // current_character_index 4 on a live client this session. Same file, same tree,
        // opposite claim -- the class section 35 calls "the same constant living in more
        // than one file", which has already cost a bind() failure once.
        //
        // sub_6B87C0 confirms it: int __cdecl(), no arguments, caching
        // sub_512120("currentCharacterIndex", 0) -- a lookup BY NAME, which is why it did
        // not move with the rest of the character scheme.
        static constexpr std::size_t CurrentCharacterGetRva = 0x2B87C0;
        // And its companion, from the same block. sub_50FF30 is a PROFILE read: it
        // formats the path characterClasses[<character>].slots[<slot>] and pulls the
        // value out of the public profile, then de-obfuscates with
        // ROL32(value ^ *(dword *)(profile + 69944), 8) when profile[69948] is set.
        //
        // This is section 64c's "profile-blob route", and it is a function that already
        // exists on this build rather than a port that has to be written.
        static constexpr std::size_t CharacterSlotGetRva = 0x10FF30;
        // THE WEAPON-CLASS FIELD READER, and it is what makes a real loadout
        // reachable on this build at all.
        //
        // captureClientLoadoutRequest used to need weaponSlotReadStaged_, whose
        // only known address is 3.3.3.3's 0x1945B0 and which is NOT PORTABLE:
        // that function decodes an obfuscated staged array with a ROL-8 ladder
        // over rotations 15/14/13/12/11 of a key global, and out.exe contains no
        // such ladder anywhere -- a scan for each rotation finds no cluster,
        // because the obfuscation is re-rolled per build. Left null, every class
        // read failed, classMask stayed 0, and capture answered NO_LOADOUT no
        // matter how good the stored profile was.
        //
        // sub_50FC20 reaches the same values a better way. It is the sibling of
        // CharacterSlotGetRva's sub_50FF30 -- same family, same profile document
        // -- and it resolves a PATH rather than indexing a shadow array:
        //
        //     weaponClasses[<class>].<field>            (ecx == -1)
        //     weaponClasses[<class>].<field>[<element>] (ecx == element)
        //
        // ecx = element index or -1, edx = the field NAME, and one stack byte is
        // the class index. It un-obfuscates the result itself with the profile's
        // own key at +0x11138 gated by +0x1113C, and RETURNS THE VALUE MINUS ONE
        // -- the document stores id+1 so 0 can mean "nothing here". Plain `retn`,
        // so the CALLER pops the stack argument.
        //
        // The field names are not guessed. They are read out of
        // `mp/playerdata.def`, the StructuredDataDef asset in code_post_gfx_mp:
        // weaponClasses carries name, primaryBase, primaryAttach, secondaryBase,
        // secondaryAttach, perks, lethal, tactical, killstreaks, deathstreak,
        // meleeWpn, swordWpn, special, wildcards, characterIndex.
        //
        // Reading the SAVED profile rather than a staged array is also the more
        // correct source now that the lobby persists one: what this returns is
        // what the player actually built and kept.
        static constexpr std::size_t WeaponClassFieldGetRva = 0x10FC20;
        // THE CLIENT'S OWN LOADOUT RECORD BUILDER, and it is what finally makes a real
        // class reachable on this build.
        //
        // THE COMMENT ABOVE IS WRONG AND THIS IS THE CORRECTION. It says out.exe
        // "contains no such ladder anywhere -- a scan for each rotation finds no
        // cluster, because the obfuscation is re-rolled per build". The ladder is
        // there. sub_6BB0F0 decodes six attachments with exactly 3.3.3.3's rotations
        // 16/15/14/13/12/11 of a key global (dword_E57A70) and the same ROL-8. The
        // earlier scan could not see it because it looked for 3.3.3.3's ADDRESSING,
        // not its arithmetic:
        //
        //     3.3.3.3   stride 40, table a GLOBAL      cmp byte_2E74038[eax*8], 0
        //     OLfinal   stride 76, table an ARGUMENT   cmp [ecx+eax*76+280], 0
        //
        // A byte signature keyed on the global is unfindable when the table arrives in
        // ECX. Matching on the ladder alone finds exactly ONE site in out.exe, and it
        // is this one.
        //
        // sub_7C5BA0 is the entry point: sub_7C6480 calls it to fill the 160-byte
        // record it then qmemcpy's. It writes, as u16:
        //
        //     word 12..23   twelve character item ids
        //     word 24..30   weapon 0: itemId then SIX attachment ids
        //     word 31..37   weapon 1        (stride 7 words = 14 bytes)
        //     word 38..44   weapon 2
        //     word 45..51   weapon 3
        //
        // Seven words per weapon is WeaponRequest field for field, which is why this
        // maps across with no reinterpretation. The offsets are read off the WRITES in
        // sub_7C5A50 (v14 = a3+48 advancing 7 words; v8 = a3+52 writing v8-1..v8[3]
        // then v8-3 after the advance), not inferred from the shape of the struct.
        static constexpr std::size_t LoadoutRecordBuildRva = 0x3C5BA0;
        // Where the weapons and the character items sit inside that record, in u16.
        // THE BUILT RECORD IS CACHED, AND READING IT BEATS REBUILDING IT.
        //
        // sub_7C5500 is a 38-slot cache keyed by two dwords; sub_7C6480 fetches a slot,
        // memcpy's 160 bytes out of `slot + 8`, and only then calls sub_7C5BA0 to rebuild
        // into that same place. So `slot + 8` holds the last record the CLIENT built for
        // itself, and it persists.
        //
        //     slot stride  42 dwords = 168 bytes
        //     slot + 4     flag byte        slot + 8/+12  the two keys
        //     slot + 8     the 160-byte record starts here (its first two dwords ARE the
        //                  keys -- sub_7C6480 writes them through the same pointer it
        //                  hands to sub_7C5BA0, which is why the character items land at
        //                  word 12 and the weapons at word 24)
        //
        // Reading it is a bounded memory read. REBUILDING it is a native call on the
        // bridge thread, which is the exact hazard that made profileSlotProbeEnabled()
        // default to off. Prefer the read; keep the call only as a fallback.
        // WHICH SLOT IS THE PLAYER'S, without calling anything. sub_7C6480 picks the
        // cache keys by a plain pointer chase, and the record's first two dwords ARE
        // those keys, so the owner's slot is identifiable from memory alone:
        //
        //     mov ecx, dword_84ABB08      ; else dword_84ABB14 when that is null
        //     call sub_B9A0F0             ; returns ecx + 216
        //     mov esi, [eax+20h]          ; key 1  ->  owner + 248
        //     mov edi, [eax+24h]          ; key 2  ->  owner + 252
        //
        // Without this the read takes the FIRST populated slot, which in a lobby with
        // other members is a coin toss between their class and the player's -- and a
        // wrong-but-plausible class is the hardest kind of wrong to notice.
        static constexpr std::size_t LoadoutOwnerPrimaryRva = 0x40ABB08;
        static constexpr std::size_t LoadoutOwnerFallbackRva = 0x40ABB14;
        static constexpr std::size_t LoadoutOwnerKeyOffset = 248;
        static constexpr std::size_t LoadoutRecordCacheRva = 0xDF72D60;
        static constexpr std::size_t LoadoutRecordCacheSlots = 38;
        static constexpr std::size_t LoadoutRecordCacheStride = 168;
        static constexpr std::size_t LoadoutRecordCacheOffset = 8;
        static constexpr std::size_t LoadoutRecordCharacterWord = 12;
        static constexpr std::size_t LoadoutRecordWeaponWord = 24;
        static constexpr std::size_t LoadoutRecordWeaponStride = 7;
        // Four weapon groups / two weapons per class = two classes in the record.
        static constexpr std::size_t LoadoutRecordClasses = 2;
        static constexpr std::size_t LoadoutRecordWords = 80;
        // AND THE ARRAY IS NINE WIDE, NOT TWELVE. Measured through CodolMatchFlow.py,
        // which reads the same function on the same build and catches the fault in JS
        // instead of dying of it:
        //
        //     character_slots: [545, 0, 0, 0, 0, 0, 0, 0, 0, null, null, null]
        //
        // Slots 0..8 return; slots 9, 10 and 11 THROW. So characterClasses[N].slots is
        // nine entries, and CharacterItemCount's twelve is a DIFFERENT array's size --
        // the item record sub_619E90 fills. Looping a 12-wide index over a 9-wide array
        // is a read past the end, and __try cannot save you from it here.
        static constexpr std::size_t CharacterProfileSlotCount = 9;
        // THE FIVE CLASSES, STRAIGHT OUT OF THE PROFILE DOCUMENT -- and the reason
        // an in-match class switch can finally change the weapon. The cache/record
        // path (LoadoutRecordBuildRva) only ever holds the ONE class the player has
        // selected, so mirroring it left custom1..custom5 identical and a switch a
        // no-op. The structured profile document the client itself edits holds all
        // five, per character, and reading it is a PURE MEMORY READ -- not the
        // sub_50FF30 native call that profileSlotProbeEnabled() gates off.
        //
        // sub_7F9090 returns &dword_E54BC48, the profile manager global. sub_50FF30
        // reads its +0xA0 as the document, +0x11138 as the obfuscation key and
        // +0x1113C as the flag; a stored dword decodes as ROL32(raw ^ key, 8). All
        // three offsets and the rotate are read off sub_50FF30 / sub_76BCF0, and the
        // whole scheme is validated offline against a live dump by
        // Tools/olfinal/decode-profile-blob.py, which reads distinct per-class
        // weapons this way. Per-build (def formatChecksum 0x4A6CC345).
        // ProfileManagerRva is already defined with the public-profile constants.
        static constexpr std::size_t ProfileDataBufferOffset = 0xA0;
        static constexpr std::size_t ProfileDecodeKeyOffset = 0x11138;
        static constexpr std::size_t ProfileObfuscatedFlagOffset = 0x1113C;
        static constexpr std::size_t ProfileDocumentSize = 0x8000;
        // The def carries the index -> byte-offset table sub_50F410 converts a path
        // through: byteOffset = *(*(def + 0x38) + 4 * index), and def itself is
        // *(DB_FindXAssetHeader(39, "mp/playerdata.def") + 8). Reading the table at
        // runtime -- rather than hardcoding sixty packed byte offsets -- is what makes
        // this survive a def change: the byte stride is NOT uniform across characters.
        static constexpr std::uint32_t AssetTypeStructuredDataDef = 39;
        static constexpr std::size_t PlayerDataDefBufferPointerOffset = 8;
        static constexpr std::size_t PlayerDataDefOffsetTablePtrOffset = 0x38;
        // NO LONGER THE ANSWER -- THE FALLBACK, AND THE CROSS-CHECK.
        //
        // resolveProfileLayout() reads all of these off the loaded def BY NAME and logs
        // any that disagree; these values are used only when that walk fails. They are
        // this build's, measured from the decoded def (Tools/olfinal/playerdata-def.py)
        // and cross-checked by the scoreboard reproduction in
        // decode-playerdata-offsets.py -- and they are WRONG for 3.3.3.3, which puts
        // weaponClasses at 1154 with a stride of 36. That is the whole reason the walk
        // exists.
        //
        // weaponClasses is a flat array of 60 = 12 characters x 5 classes of struct#2,
        // whose per-element index stride is 37; the current character's five classes
        // are slots [character*5 + 0 .. +4]. primaryBase / secondaryBase are the child
        // ordinals 22 / 29 within the class. Base index 1607.
        static constexpr std::uint32_t WeaponClassesBaseIndex = 1607;
        static constexpr std::uint32_t WeaponClassIndexStride = 37;
        static constexpr std::uint32_t WeaponClassesPerCharacter = 5;
        static constexpr std::uint32_t WeaponClassPrimaryBaseOrdinal = 22;
        static constexpr std::uint32_t WeaponClassSecondaryBaseOrdinal = 29;
        // The character items live in the SAME document: characterClasses is a
        // 12-element array (base index 605, per-element index stride 14) of a
        // struct whose `slots` array (child ordinal 5) is nine wide -- exactly
        // CharacterProfileSlotCount. Reading them here is what lets the capture
        // work with NO room: the record path needs the room cache, the document
        // does not. Measured from the same decoded def, and a fallback for the same
        // reason as the block above -- on 3.3.3.3 these are 576, 10 and 1.
        static constexpr std::uint32_t CharacterClassesBaseIndex = 605;
        static constexpr std::uint32_t CharacterClassIndexStride = 14;
        static constexpr std::uint32_t CharacterSlotsOrdinal = 5;
        // CODDIFF(section-67): OLfinal's model resolution, and the reason the port is
        // small. sub_619AD0 makes TWO passes over the twelve-entry item record, and the
        // second one fills every EMPTY entry from a per-slot default table the CHARACTER
        // itself carries -- twelve uint16 at +0xC of a 0x34-byte character record, reached
        // through the same bucket scheme with def[+5] == 2 as the type check. So the
        // server writes ONE value, entry 0, and the engine derives the other eleven.
        //
        // That is also why every character on this account reads
        // slots = [545,0,0,0,0,0,0,0,0]: the zeros are not a bare profile, they are the
        // NORMAL case and they mean "use the character's defaults here" (section 66a).
        //
        // The slots are named, and the names are a GOLDEN for this port because they came
        // out of the client's own tables and share no code with it:
        //     0 cha   1 fpa   2 boo   3 fja   4 han   5 hea   6 ves   7 heg
        //     545 cha_infbasea -> fpa_infbasea, boo_infbasea, fja_infbasea,
        //                        han_infbasea00, hea_socomb
        // tools/runtime/CodolCharacterCategoryDump.py --resolve prints them.
        static constexpr std::size_t CharacterRecordFillDefaultsRva = 0x219AD0;
        static constexpr std::size_t CharacterRecordToSelectionNamesRva = 0x21B6C0;
        // sub_61B6C0's FOURTH argument. It reaches sub_80DEF0 and contributes one bit to a
        // variant bitmask; out.exe's own frontend caller keeps the value only when it is
        // 1 or 2 and OTHERWISE SUBSTITUTES 2 (0x61D81B, `lea eax, [ecx+2]` with ecx zero).
        //
        // SECTION 166 NAMED THE SEMANTICS AND MOVED THE OWNER. The IN-MATCH caller is
        // CG_SetupClientCharacterInfo 0x00541800, and it passes
        // `*(int *)(clientState + 0x154) + 1` -- THE FACTION FIELD THIS SERVER SENDS,
        // PLUS ONE. So the selector is not a constant this side may choose: it is a
        // function of the wire, and characterVariantSelector(faction) in the .cpp is the
        // one place that computes it. This constant is deliberately GONE rather than
        // left as a default nobody reads -- a stale default is exactly how the dedicated
        // came to resolve variant 2 while the client resolved variant 1 for a whole
        // session. Section 67d, corrected by section 166.
        // Twelve entries of twelve bytes. The size is CharacterItemCount's, and the entry
        // layout is NativeCharacterItemRecord's -- see the CODDIFF on that struct, which
        // is where the eight-versus-twelve stack overrun was found.
        static constexpr std::size_t CharacterSelectionNameCount = 11;
        // AND THE GUARD THAT HAS TO COME WITH IT. sub_50FF30 opens with
        //     v2 = sub_7F9090() + 160; if (!v2) return 0;
        // which does NOT catch a null profile -- a null manager makes v2 = 160, the
        // check passes, and 160 is then dereferenced. Calling it without a parsed
        // public profile is an access violation, and __try does not save you: CODOL's
        // own crash reporter takes the fault first and writes a ClientException.
        //
        // CodolMatchFlow.py never calls either accessor without checking the profile
        // (readCurrentCharacter returns null unless publicProfile.ready), and that
        // guard is load-bearing -- porting the call without it killed the client.
        // These are its 1649370 constants.
        static constexpr std::size_t ProfileManagerRva = 0xE14BC48;
        static constexpr std::size_t PublicProfileOffset = 16;
        static constexpr std::size_t ProfileChunkMaskOffset = 0x1008C;
        static constexpr std::size_t ProfileOperationOffset = 116;
        static constexpr std::size_t ProfileParsedOffset = 0x1112C;
        static constexpr std::uint32_t ProfileRequiredChunkMask = 0x07FFFFFF;
        static constexpr std::size_t ConfigStringGetRva = 0x114880;
        static constexpr std::size_t ByteDirectionsRva = 0xA51C70;
        // CODDIFF(1649370): THESE WERE 3.3.3.3's, AND THEY ARE NOT EVEN CONSECUTIVE HERE.
        // Read straight out of this build's BG_PlayerToEntity_SetTrajectory at 0x0041167A:
        //     mov ecx, ds:0x00E51A84 / not ecx / xor ecx, [ebp-10h]   ; origin[0]
        //     lea eax, [esi+18h]     / xor ecx, eax / mov [eax], ecx   ; ^ ITS OWN ADDRESS
        //     mov edx, ds:0x00E51B1C / not edx / xor edx, [ebp-0Ch]   ; origin[1]
        //     mov ecx, ds:0x00E51B20 / not ecx / xor ecx, [ebp-08h]   ; origin[2]
        // which also confirms OriginOffsets {0x18,0x1C,0x20} and the decode this project
        // already uses, `encoded ^ fieldAddress ^ ~key`. Only the key ADDRESSES were wrong.
        //
        // The first key sits 0x98 bytes away from the other two, so the old triple being
        // three consecutive dwords was never a layout this build has. Any port that
        // assumed "three in a row" -- including reading one and adding 4 -- lands on the
        // wrong global twice out of three times.
        static constexpr std::array<std::size_t, 3> EntityOriginKeyRvas{
            0xA51A84, 0xA51B1C, 0xA51B20,
        };
        static constexpr std::size_t CharacterItemDefinitionTableRva = 0x73988FC;
        static constexpr std::size_t CharacterItemDefinitionCountRva = 0x7398900;
        // CODDIFF(character_item_decode_key): was 0xA57A70, which is a real runtime key on
        // this build but NOT the one that decodes a character item record. It was the only
        // address in this block with no derivation beside it -- section 51k, in its mildest
        // form: an undocumented constant sitting between two documented ones.
        //
        // The record's own copier settles it. sub_619E90 finishes at 0x619f20 with
        //     ROL32(dword_E4DD90 ^ *(dword *)entry ^ *(dword *)(entry + 8), 8)
        // and its only caller repeats the same three-way XOR against dword_E4DD90 at four
        // further sites (0x618c8e, 0x618cb2, 0x618e5a, 0x619161). dword_E4DD90 is VA
        // 0xE4DD90, so RVA 0xA4DD90.
        //
        // NEITHER ADDRESS CAN BE TOLD FROM THE OTHER BY ITS IMAGE VALUE: both read
        // 0xFFFFFFFF, because both are runtime-initialised. Only the call site
        // discriminates, which is why the rule is to confirm against one.
        static constexpr std::size_t CharacterItemDecodeKeyRva = 0xA4DD90;
        static constexpr std::size_t ItemDefinitionsRva = 0x739583C;
        static constexpr std::size_t ItemDefinitionCountRva = 0x7395840;
        static constexpr std::size_t ItemLookupRva = 0x7395844;
        static constexpr std::size_t ItemLookupCountRva = 0x7395848;
        static constexpr std::size_t ItemBucketOffsetsRva = 0x739584C;
        static constexpr std::size_t ConstantConfigStringChecksumRva = 0x73D8240;
        static constexpr std::size_t ConfigStringTypesRva = 0x73D8250;
        static constexpr std::size_t ConstantConfigStringsInitializedRva = 0x73DB42C;
        static constexpr std::size_t RoomSingletonRva = 0x7EE13FC;
        // OLMOD(section-48-input-probe): the room's MEMBER ROSTER, which is where a
        // character item id would have to come from if one exists on this build.
        // Read-only, and the two addresses corroborate each other: the count at
        // 0x82E13A4 is 0x58 bytes below RoomSingletonRva's 0x82E13FC, sub_618A00 loops
        // on the count while sub_620700 reads the singleton, and sub_620B90 clears the
        // roster with the bound `v0 <= 0x11` -- eighteen, which is MaximumSessionMembers.
        //
        // sub_619E90 walks the SOURCE at stride 4 and the destination at stride 12
        // (`add edi,4` / `add ebx,0Ch` at 0x619efd), so the source is twelve PLAIN
        // dwords -- item handles, 48 bytes of the 160-byte member record. It is the
        // 12-byte destination record that carries the obfuscation, and the engine
        // applies it itself in sub_810B20.
        static constexpr std::size_t SessionMemberCountRva = 0x7EE13A4;
        static constexpr std::size_t SessionMemberItemHandlesRva = 0xC511424;
        static constexpr std::size_t SessionMemberStride = 160;
        static constexpr std::size_t SessionMemberCapacity = 18;
        static constexpr std::size_t SessionMemberItemHandleCount = 12;

        // OLMOD(engine-binding-boundary): public methods validate source data,
        // thread/build state, and native outputs around retained CODOL calls.
        // They are adapters, not reconstructed native subsystem interfaces.
        [[nodiscard]] bool bind();
        [[nodiscard]] bool valid() const;
        // CODDIFF(client_loadout_capture): the loadout-capture helpers are
        // unbound on OLfinal, so their presence is reported separately rather
        // than folded into valid() -- their absence degrades one client path,
        // it does not mean the engine is unbound.
        [[nodiscard]] bool clientLoadoutBindingsAvailable() const;
        [[nodiscard]] bool observeGameThread() noexcept;
        [[nodiscard]] bool nativeServerEntityBindingsAvailable() const;
        [[nodiscard]] std::uint8_t *module() const;
        [[nodiscard]] DBFindXAssetHeader dbFindXAssetHeader() const;
        void MSG_Init(msg_t &message, std::uint8_t *data, std::int32_t length) const;
        void MSG_WriteBits(msg_t &message, std::int32_t value, std::uint32_t bits) const;
        void MSG_WriteString(msg_t &message, const char *value) const;
        [[nodiscard]] bool beginLevelZoneLoad(
            std::string_view mapName,
            std::string_view gameType) const;
        [[nodiscard]] bool zoneLoaded(std::string_view name) const;
        [[nodiscard]] bool initializeLevelWorld(
            std::string_view mapName,
            std::string_view gameType) const;
        [[nodiscard]] bool synchronizeNativeServerEntities(
            SvNativeEntityMirrorPhase phase,
            std::span<const SvCollisionEntity> entities,
            std::span<const SvNativeEntityStateSource> entityStates,
            std::uint32_t serverTime) const;
        [[nodiscard]] bool initializeMantleAnimations() const;
        [[nodiscard]] ServerAnimationInitializationStatus
            initializeServerAnimationContext(
                std::string_view mapName,
                std::string_view gameType) const;
        [[nodiscard]] ServerAnimationInitializationStatus
            serverAnimationInitializationStatus() const;
        [[nodiscard]] bool CCS_Clear() const;
        [[nodiscard]] bool CCS_Initialized() const;
        [[nodiscard]] bool CCS_EnsureInitialized() const;
        [[nodiscard]] std::uint32_t CCS_GetChecksum() const;
        // The raw native accessor. Returns CODOL's own pointer, which may be
        // into either the parsed gamestate table or the constant-configstring
        // chunks depending on the index's class.
        [[nodiscard]] const char *nativeConfigString(std::uint32_t index) const;
        [[nodiscard]] std::optional<std::uint16_t> resolveScriptAnimation(
            std::string_view name) const;
        // DB_FindXAssetHeader with the allowDefault distinction this build's
        // two-parameter version cannot express on its own.
        [[nodiscard]] XAssetHeader findXAsset(
            std::uint32_t type,
            const char *name,
            bool allowDefault) const;
        [[nodiscard]] std::optional<std::string> readConfigString(
            std::uint16_t index,
            std::size_t maximumLength = 1024) const;
        [[nodiscard]] std::optional<std::uint16_t>
            firstDynamicWeaponAssetIndex() const;
        [[nodiscard]] std::optional<std::vector<SvModularWeaponConfigString>>
            readDynamicWeaponConfigStrings(
                std::uint16_t firstDynamicWeaponAssetIndex) const;
        // Ask CODOL's native weapon registry to materialize one complete
        // modular definition.  Campaign recordings refer to the dense slot
        // that definition occupied in their own session; the returned index
        // is the slot it occupies in this session, after the player's actual
        // multiplayer loadouts have already registered their variants.
        [[nodiscard]] std::optional<std::uint16_t>
            registerModularWeaponConfigString(
                std::string_view configString) const;
        [[nodiscard]] std::optional<ClientBookingSelection> readClientBookingSelection() const;
        [[nodiscard]] std::optional<std::uint32_t> currentCharacterIndex() const;
        // OLMOD(section-48-input-probe): what the room roster actually holds, as one log
        // line. This is a MEASUREMENT and not a health check, so it reports on every call
        // including the empty case -- "count=0" and "unreadable" are different answers and
        // silence would be neither. Section 44a: a reporter that cannot fire reads as
        // innocence.
        // Every caller of currentCharacterGet_ and characterSlotGet_ must pass this
        // first. It is not defensive style -- see the CODDIFF on CharacterSlotGetRva.
        // OLMOD_PROBE_PROFILE_SLOTS=1. Off by default: the native profile call's
        // safety on the bridge thread is not established. See the definition.
        [[nodiscard]] static bool profileSlotProbeEnabled();
        [[nodiscard]] bool publicProfileReady() const;
        [[nodiscard]] std::string reportSessionMemberItemHandles() const;
        // The risky half, separated so the safe half has already reported. Empty unless
        // OLMOD_PROBE_PROFILE_SLOTS=1.
        // What the CLIENT will hand BG_UpdatePlayerDObj for each clientNum: whether
        // its characterInfo is valid and what base model it resolved. The one
        // instrument that reads the side an invisible player actually fails on.
        [[nodiscard]] std::string reportClientCharacterInfo() const;
        [[nodiscard]] std::string reportProfileCharacterSlots() const;
        [[nodiscard]] std::optional<OlMod::DedicatedSession::LoadoutRequest>
            captureClientLoadoutRequest() const;
        [[nodiscard]] std::optional<ClientCharacterPresentation>
            resolveClientCharacterPresentation(
                std::uint32_t characterIndex) const;
        [[nodiscard]] std::optional<ClientCharacterPresentation>
            resolveSessionCharacterPresentation(
                const OlMod::DedicatedSession::LoadoutRequest &request) const;
        [[nodiscard]] std::optional<ClientWeaponLoadout>
            resolveSessionWeaponLoadout(
                const OlMod::DedicatedSession::LoadoutRequest &request,
                std::uint32_t classIndex) const;
        [[nodiscard]] WeaponRegistryInitializationStatus
            ensureWeaponRegistryInitialized() const;
        // Installs the two measured descendants, eight explicit compatibility
        // aliases and the converted Barrett under their original alpha names
        // when OLMOD_ALPHA_WEAPONS=1. Ordinary aliases clone their source model
        // table; Barrett publishes the exact four-row alpha table after its
        // converted model family is resident.
        [[nodiscard]] AlphaWeaponPortStatus installAlphaWeaponPorts() const;
        // Pure, opt-in historical layout evidence for the Barrett port. Once
        // common_mp is resident, OLMOD_ALPHA_WEAPON_MODEL_AUDIT=1 logs the
        // early pointer-bearing fields in as50_mp. CODOL's gun itself is built
        // by the modular coWeapModels path, so this does not patch or link.
        void auditAlphaWeaponModelPointers() const;
        // Read-only, opt-in XModel/XModelSurfs evidence used by the alpha
        // Barrett converter. Once common_mp is resident,
        // OLMOD_XMODEL_SURFACE_AUDIT=1 writes the loaded riot-shield surface
        // headers and their CPU-side geometry arrays beside the runtime log.
        // The shared alpha/final model is the control that proves the binary
        // layouts before any missing model is linked.
        void auditXModelSurfaces() const;
        // Read-only final-build evidence for converting alpha Barrett
        // materials and images. The client bridge diagnostic
        // `alpha-barrett-templates` writes the exact 104-byte Material and
        // 52-byte GfxImage headers, texture rows, and retained 16-byte image
        // load definitions beside the runtime log. It never links or changes
        // an asset.
        void auditAlphaBarrettAssetTemplates() const;
        [[nodiscard]] std::optional<SvResolvedPerks> resolveSessionPerks(
            const OlMod::DedicatedSession::LoadoutRequest &request,
            std::uint32_t classIndex) const;
        [[nodiscard]] std::optional<SvResolvedEquipment> resolveSessionEquipment(
            const OlMod::DedicatedSession::LoadoutRequest &request,
            std::uint32_t classIndex) const;
        [[nodiscard]] std::optional<SvOffhandWeapon> resolveFactorySpecialEquipment(std::string_view name) const;
        // Runs CG_Init's dvar registration blocks, which a dedicated process
        // never reaches. Returns how many of the seven completed.
        std::uint32_t registerGameplayDvars() const;
        [[nodiscard]] std::optional<std::array<float, 3>> evaluateTrajectory(
            const SvNativeTrajectory &trajectory, std::int32_t atTime) const;
        [[nodiscard]] std::optional<std::array<float,3>> directionToAngles(
            const std::array<float,3> &direction) const;
        [[nodiscard]] std::optional<SvGrenadeLaunchParameters> resolveGrenadeLaunchParameters(
            std::uint16_t weapon) const;
        [[nodiscard]] std::optional<SvGrenadeBlastParameters> resolveGrenadeBlastParameters(
            std::uint16_t weapon) const;
        // Whether the character-model resolver exists on this build at all.
        // On OLfinal it does not - see the CODDIFF in
        // resolveSessionCharacterPresentation and handoff section 16a - so
        // "resolve failed" and "there is nothing here to resolve with" are
        // different answers and the caller has to be able to tell them apart.
        [[nodiscard]] bool characterPresentationResolverAvailable() const;
        [[nodiscard]] std::optional<ClientWeaponLoadout> resolveClientWeaponLoadout(
            std::string_view selectedLoadout) const;
        [[nodiscard]] std::optional<ClientWeaponLoadout> resolveClientWeaponLoadout(
            std::string_view selectedLoadout,
            std::uint32_t characterIndex) const;
        // PUBLIC wrapper over resolveWeaponRequest: resolve one captured weapon
        // (item id + attachments) into a native selection, for the live loadout
        // refresh which already holds the item ids and does not need the staged
        // per-slot path. See §157c.
        [[nodiscard]] std::optional<ClientWeaponSelection> resolveWeaponSelection(
            const OlMod::DedicatedSession::WeaponRequest &request) const;
        [[nodiscard]] ClientLoadoutResolveFailure loadoutResolveFailure() const;
        [[nodiscard]] ClientCharacterPresentationResolveStatus
            characterPresentationResolveStatus() const;
        [[nodiscard]] std::optional<std::string> readMapEntityString(
            std::string_view mapName) const;
        [[nodiscard]] std::optional<SvGlassMapMetadata>
            resolveGlassMapMetadata(std::string_view mapName) const;
        [[nodiscard]] std::optional<std::uint8_t> directionToByte(
            const std::array<float, 3> &direction) const;
        [[nodiscard]] std::optional<std::uint16_t>
            resolveModelConfigStringIndex(std::string_view modelName) const;
        // A weapon asset index from its name, by walking the weapon configstring
        // band the same way the model lookup walks the model band. Weapons have no
        // findXAsset precheck here: the band IS the registry the client parsed, so a
        // name that is not in it is not a weapon this match can reference.
        [[nodiscard]] std::optional<std::uint16_t>
            resolveWeaponConfigStringIndex(std::string_view weaponName) const;
        // An XANIM NAME to the index the agentState anim field carries. Same shape as
        // the model resolver and for the same reason: the client rebuilds its own band
        // at map load, so a number recorded anywhere else names a different animation.
        // Returns nullopt when this engine does not hold the xanim, which callers must
        // treat as "play nothing" rather than substituting a neighbour.
        [[nodiscard]] std::optional<std::uint16_t>
            resolveAnimConfigStringIndex(std::string_view animName) const;
        [[nodiscard]] std::optional<std::uint8_t> resolveScriptModelAnimationTree(
            std::span<const std::uint16_t> aliases) const;
        // Read-only resident XAnim marker timings. IDs are native string IDs,
        // NOT animation keys or board slots. No release marker is presumed.
        [[nodiscard]] std::optional<std::vector<std::pair<std::uint16_t, float>>>
            animationNotifyTimes(std::string_view animName) const;
        [[nodiscard]] std::optional<std::string>
            animationNotifyName(std::uint16_t nameId) const;
        // Every non-empty entry of the model configstring band, for choosing a
        // podium base model by NAME rather than porting retail's per-map index
        // (section 124). Map load only.
        [[nodiscard]] std::vector<std::pair<std::uint16_t, std::string>>
            modelConfigStringBand() const;

        // Every non-empty entry in the animation configstring band, as
        // (index, name). Map load only -- 4096 reads.
        std::vector<std::pair<std::uint16_t, std::string>>
            animConfigStringBand() const;
        [[nodiscard]] std::optional<std::uint16_t>
            resolveEffectEventParameter(std::string_view effectName) const;
        [[nodiscard]] std::optional<std::uint8_t> attachmentBoneIndex(
            std::string_view body, std::string_view attachment, std::string_view bone) const;
        [[nodiscard]] std::optional<std::uint8_t> modelBoneIndex(
            std::string_view modelName, std::string_view boneName) const;
        // Map setup only. Root world-mesh centre, not attachment or viewmodel bounds.
        [[nodiscard]] std::optional<std::array<float,3>> weaponDisplayBodyCenter(
            std::uint16_t weaponAssetIndex) const;
        [[nodiscard]] std::optional<std::uint16_t>
            resolveSoundAliasEventParameter(std::string_view aliasName) const;
        [[nodiscard]] std::vector<std::optional<std::uint16_t>>
            resolveSoundAliasEventParameters(
                std::span<const std::string> aliasNames) const;
        // TODO(CODOL): diagnostic. Every alias asked for by name has come back
        // unresolved on every level load, so report what the two index sources
        // actually CONTAIN rather than guessing more names. Remove once a
        // sound alias resolves.
        void logServerSoundAliasTables(std::size_t limit) const;
        // TODO(CODOL): audition support. Returns every non-voice-over alias
        // in the networked table with its event parameter, so a sound can be
        // identified BY EAR instead of by guessing at a name. Remove with the
        // audition mode itself.
        [[nodiscard]] std::vector<std::pair<std::uint16_t, std::string>>
            collectServerSoundAliasAuditions() const;
        [[nodiscard]] std::optional<std::uint16_t>
            resolveServerMaterialConfigStringIndex(
                std::string_view materialName) const;
        [[nodiscard]] std::optional<std::uint16_t>
            firstDynamicServerMaterialIndex() const;
        [[nodiscard]] std::optional<SvBrushModelCollision>
            resolveBrushModelCollision(std::uint32_t clipHandle) const;

        // EVERY HULL OF ONE `?N` TRIGGER MODEL, out of MapEnts.trigger.
        //
        // THIS EXISTS BECAUSE resolveBrushModelCollision CANNOT DO IT. `?N` indexes
        // MapEnts.trigger; that function indexes the clipmap's cmodel list. Feeding it
        // a trigger index returns an unrelated brush and reports SUCCESS -- measured
        // 2026-09-01 on zm_factory_sh, where all 32 zone volumes "resolved" and every
        // one was wrong (`?2` is half (187.0, 6.5, 67.0) in the map and came back as
        // (3.0, 45.5, 57.5)). Do not route trigger volumes through the cmodel lookup.
        //
        // Returns the hulls EXACTLY, slabs included, so a caller can test containment
        // properly instead of settling for their bounding box.
        [[nodiscard]] std::optional<std::vector<SvZmVolumeHull>>
            resolveTriggerModelHulls(
                std::string_view mapName,
                std::uint32_t triggerModel) const;
        [[nodiscard]] std::optional<bool> contactBrushModel(
            const std::array<float, 3> &origin,
            const TraceBounds &bounds,
            const std::array<float, 3> &brushOrigin,
            const std::array<float, 3> &brushAngles,
            const SvBrushModelCollision &brushModel) const;
        [[nodiscard]] std::optional<TraceResult> traceCapsule(
            const std::array<float, 3> &start,
            const std::array<float, 3> &end,
            const TraceBounds &bounds,
            std::int32_t passEntityNum,
            std::uint32_t contentMask) const;
        [[nodiscard]] std::optional<TraceResult> traceWorld(
            const std::array<float, 3> &start,
            const std::array<float, 3> &end,
            const TraceBounds &bounds,
            std::uint32_t contentMask,
            const SvGlassState &glassState) const;
        [[nodiscard]] std::optional<TraceResult> traceServerCapsule(
            const std::array<float, 3> &start,
            const std::array<float, 3> &end,
            const TraceBounds &bounds,
            std::uint32_t contentMask,
            const SvGlassState &glassState,
            std::span<const SvCollisionEntity> entities,
            const SvTraceEntityFilter &filter) const;
        [[nodiscard]] std::optional<TraceResult> traceServerPoint(
            const SvPointTraceRequest &request,
            const SvGlassState &glassState,
            std::span<const SvCollisionEntity> entities) const;
        [[nodiscard]] std::optional<bool> traceRadiusDamageVisibility(
            const SvRadiusDamageTraceRequest &request,
            const SvGlassState &glassState,
            std::span<const SvCollisionEntity> entities) const;
        [[nodiscard]] std::optional<std::array<float, 3>>
            getPlayerEyePosition(
                const SvNativePlayerState &playerState,
                std::int32_t time) const;
        [[nodiscard]] std::optional<SvWeaponFireBasis>
            buildServerWeaponFireBasis(
                const SvNativePlayerState &playerState,
                const SvWeaponAimState &aimState,
                const SvResolvedWeapon &weapon,
                std::int32_t time) const;
        [[nodiscard]] std::optional<SvBulletEndposResult>
            calculateBulletEndpos(const SvBulletEndposRequest &request) const;
        [[nodiscard]] std::optional<float> surfacePenetrationDepth(
            std::uint16_t weaponAssetIndex,
            std::uint8_t surfaceType) const;
        [[nodiscard]] std::optional<SvWeaponFireBasis>
            buildServerOffhandFireBasis(
                const SvNativePlayerState &playerState,
                const SvWeaponAimState &aimState,
                const SvOffhandWeapon &weapon,
                std::int32_t time) const;
        [[nodiscard]] std::optional<SvNativeWeaponMovementOutput>
            runServerWeaponMovement(
                const SvWeaponMovementFrameInput &input,
                SvWeaponMovementClientState &clientState,
                const SvResolvedLoadout *resolvedLoadout) const;
        [[nodiscard]] std::optional<SvNativePmoveOutput> runServerPmove(
            SvNativePlayerState &playerState,
            const UserCmd &command,
            const std::optional<UserCmd> &oldCommand,
            std::uint32_t traceMask,
            bool finalSlice,
            const SvGlassState &glassState,
            std::span<const SvCollisionEntity> entities,
            SvNativePmoveFailure *failure = nullptr) const;
        // Re-key a playerState's obfuscated accessor pair for the address it now
        // lives at. MUST be called on any buffer that was COPIED before native
        // code is allowed to decode a pointer out of it.
        [[nodiscard]] bool rebindNativePlayerStateAccessors(
            SvNativePlayerState &state) const;
        // Store playerState +0x10's flags through the engine's own SET accessor.
        // Writing them plaintext publishes every player as ET_INVISIBLE.
        // The engine's storage REPLACES the plaintext dword ol-mod reads otherFlags
        // from, so the caller must hand the buffer back to its plaintext model with
        // captureNativeProtectedPlayerStateFlags once the native call has returned.
        [[nodiscard]] bool writeNativeProtectedPlayerStateFlags(
            SvNativePlayerState &state,
            std::uint32_t &plaintextFlags) const;
        // Read the engine's OWN view of playerState +0x10 back through the GET
        // accessor and hand out its second dword -- the flags word. This is the
        // half section 44d left unmodelled, and it is not optional: the engine
        // keeps state in that word, so writing it blind loses whatever it put there.
        [[nodiscard]] bool readNativeProtectedPlayerStateFlags(
            const SvNativePlayerState &state,
            std::uint32_t &flags) const;
        // After a native stage: take the engine's updated flags back through the
        // getter and leave them at ps+0x10 as ol-mod's plaintext view. Falls back to
        // the value that was protected if the read fails, which is the old behaviour.
        void captureNativeProtectedPlayerStateFlags(
            SvNativePlayerState &state,
            std::uint32_t fallbackPlaintextFlags) const;

        [[nodiscard]] bool playerStateToEntityState(
            SvNativePlayerState &playerState,
            SvNativeEntityState &entityState,
            SvNativeEntityStateProjection &projection) const;
        // Writes the three conditions the anim script selects a death by, then
        // runs the event. See the .cpp for where every constant comes from.
        [[nodiscard]] std::optional<std::int32_t> runServerDeathAnimation(
            SvNativePlayerState &playerState,
            std::uint32_t randomSeed,
            const SvDeathAnimationConditions &conditions) const;
        // CODREF(client_spawn): the torso animation is event-driven and has no
        // per-frame writer, so a new life must fire RAISEWEAPON to re-establish
        // it. See runServerSpawnAnimation for the measurement.
        [[nodiscard]] std::optional<std::int32_t> runServerSpawnAnimation(
            SvNativePlayerState &playerState,
            std::uint32_t randomSeed) const;
        [[nodiscard]] std::optional<std::int32_t> runServerAnimationEvent(
            SvNativePlayerState &playerState,
            std::int32_t animationEvent,
            std::uint32_t randomSeed,
            const SvDeathAnimationConditions *conditions = nullptr) const;
        // Writes the three ANIM_CONDTYPE_VALUE conditions a death is selected
        // by, into whatever anim-condition storage is currently installed.
        void writeServerAnimSelectionConditions(
            const SvNativePlayerState &playerState,
            const SvDeathAnimationConditions &conditions) const;

        // The names resolveCharacterModelNames last produced for one entity,
        // kept so the match-end `|` precache burst does not have to re-run the
        // resolver (which needs the engine's own record fill, and therefore the
        // game thread). Empty for an entity that has never resolved.
        // The models an outfit ADDS on top of what the client derives for itself from
        // the character item id. Empty when the player wears their character's defaults.
        [[nodiscard]] std::vector<std::string> characterOutfitAttachmentModels(
            const SvCharacterCustomization &customization) const;
        // THE CHARACTER'S BODY MODEL NAME, from the character record and NOT from the
        // DObj. Section 168: characterModelNames reads what the DObj build cached, and
        // that arrives a frame or more after the first customization exists, so anything
        // derived from it is zero in the first clientInfo written for a player. This
        // answers on the first frame. Empty when the character does not resolve.
        // THE TWELVE WORDS AT clientState +0x4C ARE A 384-BIT SELECTION MASK, and this
        // is the only thing that can build it. Read straight off sub_80E600, which is
        // what CG_SetupClientCharacterInfo 0x541800 hands those twelve dwords to:
        //
        //     80e729  cmp   [eax+24h], edi              ; charDef+36 = option COUNT
        //     80e732  mov   ecx, edi / and ecx, 1Fh
        //     80e737  mov   edx, 1  / shl edx, cl       ; 1 << (i & 31)
        //     80e743  test  [ebx+ecx*4+10h], edx        ; request+0x10 == the twelve
        //     80e74d  mov   edx, [eax+28h]              ; charDef+40 = option LIST
        //     80e750  movzx eax, word ptr [edx+edi*2]   ; optionList[i], an ITEM ID
        //
        // So bit `i` of dword `i/32` selects `optionList[i]`, and the character
        // definition -- reached from characterItemId, which is already on the wire as
        // field 20 -- supplies the list. THAT is why the block needs no decode key:
        // both sides index the same per-character table. Handoff section 184.
        //
        // An equipped id absent from the option list leaves its bit CLEAR, which is the
        // character's own default piece, never a wrong one. `witness` receives a
        // one-line account when it is non-null.
        [[nodiscard]] bool characterOptionSelectionMask(
            std::uint16_t characterItemId,
            std::span<const std::uint16_t> equippedItemIds,
            std::array<std::uint32_t, 12> &mask,
            std::string *witness = nullptr) const;
        [[nodiscard]] std::string characterBodyModelName(
            const SvCharacterCustomization &customization) const;
        // Every model the character resolves to, in the engine's own order, from the
        // character RECORD and not the DObj. `fpa_` is the body and `han_` the hands.
        [[nodiscard]] std::vector<std::string> characterResolvedModelNames(
            const SvCharacterCustomization &customization) const;
        [[nodiscard]] std::vector<std::string> characterModelNames(
            std::uint32_t entityNum) const;

    private:
        [[nodiscard]] std::optional<SvWeaponFireBasis> buildServerFireBasis(
            const SvNativePlayerState &playerState,
            const SvWeaponAimState &aimState,
            std::uint16_t weaponAssetIndex,
            std::uint8_t weaponType,
            bool offhand,
            std::int32_t time) const;
        // OLMOD(native-entity-mirror-transaction): source/native images needed
        // to validate and roll back fixed-slot entity publication.
        struct NativeServerEntityMirrorSlot
        {
            SvCollisionEntity source;
            SvNativeServerEntity baseline;
            SvNativeServerEntity sourceProjection;
            SvNativeServerEntity linkedImage;
        };

        // OLMOD(native-character-presentation-owner): source-owned storage that
        // embeds the separately audited exact characterInfo byte image plus
        // transaction metadata. The enclosing type is not native layout.
        struct NativeServerCharacterInfoSlot
        {
            static constexpr std::size_t Size = SvNativeCharacterInfoSize;
            // CODREF(bg_update_player_dobj): the characterInfo_t BYTES do not
            // live here. CODOL's locomotion anim-script state setter
            // sub_AA94C0 (VA 0x004094C0), which PM_Footsteps 0x0041A680 calls
            // from inside PmoveSingle, takes no characterInfo argument - it
            // derives one as
            //   dword_7EB7B80 + 618016 + 952 * playerState[+0x144]
            // so the whole per-client array has to sit inside the
            // anim-condition block this project installs. Only the ol-mod
            // bookkeeping stays in this struct.
            std::array<std::uint16_t, 11> selectionIds{};
            std::uint32_t worldModelContext{};
            std::uint8_t spawnGeneration{};
            bool lerpFramesInitialized{};
        };

        // OLMOD(engine-binding-internals): mirror, DObj, diagnostics, native
        // context, loadout, and trace helpers own adapter policy and rollback.
        // TODO(CODOL): Narrow helpers as removed dedicated owners and their
        // exact teardown/transaction contracts are recovered.
        [[nodiscard]] bool
            resetNativeServerEntityMirrorAfterWorldInitialization() const;
        [[nodiscard]] bool publishNativeServerEntityData(
            std::uint32_t entityCount) const;
        [[nodiscard]] bool nativeServerEntityMirrorMatches(
            std::span<const SvCollisionEntity> entities) const;
        [[nodiscard]] bool updateNativeServerPlayerDObj(
            std::uint32_t entityNum,
            const SvCharacterCustomization &customization,
            std::uint8_t spawnGeneration,
            std::string &failureStage,
            bool &irreversibleMutationStarted) const;
        // CODDIFF(character_customization): OLfinal replaced 3.3.3.3's
        // selector/slot-base/name-table model resolution with an item-driven
        // scheme, so this is the one binding in the port that must call a
        // DIFFERENT function rather than the same one at another address.
        // Currently returns false on 1649370 -- see the definition.
        // `filledRecord`, when given, receives the TWELVE decoded ids sub_619AD0 left in
        // the record -- the engine's own answer, not this side's view of it. Section 67's
        // first live run produced two names from the wrong family and the names could not
        // say whether the record was filled wrong or merely NAMED wrong.
        [[nodiscard]] bool resolveCharacterModelNames(
            const SvCharacterCustomization &customization,
            std::array<const char *, 11> &modelNames,
            std::size_t &resolvedModelCount,
            std::string *filledRecord = nullptr,
            int variantSelectorOverride = 0) const;
        [[nodiscard]] bool prepareNativeServerDObjPoses(
            std::span<const SvCollisionEntity> entities,
            std::uint32_t contentMask,
            NativeExceptionDetails &exceptionDetails) const;
        void synchronizeActorHitPoses(std::span<const SvCollisionEntity> entities,
            std::uint32_t serverTime) const;
        void releaseActorHitPoses() const;
        [[nodiscard]] bool prepareNativeServerDObjPose(
            void *dobj,
            const std::array<std::uint32_t, 8> &partBits,
            NativeExceptionDetails &exceptionDetails,
            std::uint32_t poseEntityNum) const;
        void logNativeServerDObjGeomDiagnostics(
            std::uint32_t entityNum,
            std::span<const std::uint8_t> priorityMap) const;
        void compareNativeServerCapsuleTrace(
            const std::array<float, 3> &start,
            const std::array<float, 3> &end,
            const TraceBounds &bounds,
            std::uint32_t contentMask,
            const SvGlassState &glassState,
            std::span<const SvCollisionEntity> entities,
            const SvTraceEntityFilter &filter,
            const TraceResult &sourceTrace) const;

        // OLMOD(locomotion-anim-diagnostics): read-only reports of the two
        // inputs CODOL's locomotion selector consumes. They mutate nothing and
        // exist only until that path is proven to select an animation live.
        void logServerAnimScriptTable(std::uint32_t animationCount) const;
        // Reports scriptEvents[event].numItems from BOTH anim-script bases --
        // this project's installed block and whatever dword_827F734 currently
        // holds. Called only on the -1 path, so a healthy event stays silent.
        void logServerAnimScriptEvent(std::int32_t animationEvent) const;
        enum class PlayerDObjState : std::uint8_t
        {
            Unknown,
            Healthy,
            CustomizationAbsent,
            DObjAbsent,
            NoTracelineBones,
        };
        void reportPlayerDObjState(
            std::uint32_t entityNum,
            PlayerDObjState state,
            const char *detail = nullptr) const;
        // Clears the latch ONLY if it still holds `state`, so a condition that
        // has cleared stops blinding every later stage that shares the slot.
        void releasePlayerDObjReportedState(
            std::uint32_t entityNum, PlayerDObjState state) const;
        void logNativeCapsuleCandidacy(
            std::span<const SvCollisionEntity> entities,
            const std::optional<TraceResult> &result) const;
        void logNativeServerDObjSkeleton(
            const std::byte *dobj, std::uint32_t entityNum) const;
        void logServerAnimConditions(
            const SvNativePlayerState &playerState) const;

        [[nodiscard]] bool installServerAnimConditionStorage(
            std::byte *&previousBase) const noexcept;
        [[nodiscard]] bool restoreServerAnimConditionStorage(
            std::byte *previousBase) const noexcept;
        [[nodiscard]] bool validateMessageBindings() const;
        // Fills classes[0] from the client's own loadout record. See
        // LoadoutRecordBuildRva.
        [[nodiscard]] bool readLoadoutRecord(
            OlMod::DedicatedSession::LoadoutRequest &request) const;
        // ALL FIVE CLASSES, from the profile document rather than the one-class
        // record. Fills request.classes and request.classMask for the current
        // character's five loadouts; leaves request untouched and returns false if
        // the document cannot be read or no class is complete. A class is complete
        // only when BOTH weapons resolve, because valid() requires it.
        [[nodiscard]] bool readProfileWeaponClasses(
            OlMod::DedicatedSession::LoadoutRequest &request) const;
        // WHERE THE PROFILE'S FIELDS ARE, ASKED OF THE DEF BY NAME.
        //
        // Every number here used to be a hand-measured constant of this build, and six
        // of the eight differ on 3.3.3.3 -- see PlayerDataDef.hpp. resolveProfileLayout
        // walks the def the game has already loaded and reads them off it, so a def
        // change moves them without anybody re-measuring anything. `byName` says whether
        // that walk succeeded; when it did not, the fields carry the OLfinal 1649370
        // constants below and the caller has already logged it.
        struct ProfileLayout
        {
            std::uint32_t characterSlotsBase{}; // characterClasses[0].slots
            std::uint32_t characterStride{};    // indices between two characters
            std::uint32_t characterCount{};     // how long characterClasses is
            std::uint32_t slotCount{};          // how wide `slots` is
            std::uint32_t weaponClassBase{};    // weaponClasses[0]
            std::uint32_t weaponClassStride{};  // indices between two classes
            std::uint32_t weaponClassCount{};   // how many classes the array holds
            std::uint32_t classesPerCharacter{};// weaponClassCount / characterCount
            std::uint32_t primaryBase{};        // ordinals inside one class
            std::uint32_t secondaryBase{};
            std::uint32_t primaryAttach{};
            std::uint32_t secondaryAttach{};
            std::uint32_t attachCount{};
            std::uint32_t perksBase{};
            std::uint32_t perksCount{};
            std::uint32_t perksStride{};
            std::optional<std::uint32_t> rewardsBase{};
            std::uint32_t rewardsStride{};
            std::array<std::optional<std::uint32_t>, 2> equipmentBase{};
            std::array<std::optional<std::uint32_t>, 2> equipmentDoubleAmmoBase{};
            bool byName{};
        };
        [[nodiscard]] static ProfileLayout resolveProfileLayout(const void *def);
        [[nodiscard]] bool readStagedWeaponSlot(
            std::uint32_t slotIndex,
            ClientWeaponSelection &selection) const;
        // Reads weaponClasses[classIndex].{primary,secondary}Base plus that
        // weapon's six attachment elements out of the STORED profile.
        [[nodiscard]] bool readProfileWeaponRequest(
            std::uint32_t classIndex,
            bool secondary,
            OlMod::DedicatedSession::WeaponRequest &request) const;
        [[nodiscard]] bool readStagedWeaponRequest(
            std::uint32_t slotIndex,
            OlMod::DedicatedSession::WeaponRequest &request) const;
        [[nodiscard]] bool resolveWeaponRequest(
            const OlMod::DedicatedSession::WeaponRequest &request,
            ClientWeaponSelection &selection) const;
        [[nodiscard]] bool resolveWeaponItem(
            std::uint32_t itemId,
            const std::array<std::uint32_t, 6> &attachmentItemIds,
            ClientWeaponSelection &selection) const;
        // A weapon name for an id no marketplace item names -- see the alias file. This
        // is how a weapon that cannot be sold (raygun_mp, thundergun_chicken_mp, both
        // loaded in every MP match) reaches a loadout.
        [[nodiscard]] std::optional<std::string> aliasedWeaponName(
            std::uint32_t itemId) const;
        [[nodiscard]] std::optional<std::string> readItemInternalName(
            std::uint32_t itemId) const;
        // Which entry of the twelve-wide character record this item belongs in:
        // 0 for a character, 1..11 for a piece, nothing for anything else.
        [[nodiscard]] std::optional<std::uint32_t> characterItemRecordEntry(
            std::uint32_t itemId) const;
        // Turn characterClasses[N].slots -- which the profile packs densely, in equip
        // order -- into the twelve-entry character record the engine addresses by slot.
        void placeCharacterItemsByRecordEntry(
            std::span<const std::uint32_t> profileSlots,
            std::array<std::uint32_t,
                OlMod::DedicatedSession::CharacterItemCount> &record) const;
        [[nodiscard]] const std::uint8_t *readItemDefinition(
            std::uint32_t itemId) const;
        [[nodiscard]] std::optional<std::vector<NamedWeaponAttachment>>
            readDefaultWeaponAttachments(std::string_view weaponName) const;
        // EVERY WEAPON IN THE TABLE, PARSED THE WAY THE LOADOUT PATH PARSES IT.
        //
        // readDefaultWeaponAttachments only ever runs for a weapon somebody EQUIPPED, so
        // "which guns are broken" was answerable only by a player picking each of 838 in
        // turn. This walks the whole table once and reports every row that would refuse,
        // and why. Runs when OLMOD_AUDIT_WEAPON_TABLE=1 -- off by default because it is a
        // few hundred log lines, not because it is unsafe.

        // IS "UNLOCK ALL" ACTUALLY ALL? With sub_5E3550 forced true, sub_5E3760 reduces
        // to: an item is owned UNLESS it is in the exclusion list. So reading that list
        // is the whole proof, and it is a pure memory read -- no native call, no bridge
        // thread risk. Empty list means every one of the catalogue's 21,753 ids resolves
        // as owned; a non-empty one names exactly which do not.

        // The measurement the coverage read is not: CALL the resolver for items the wire
        // cannot have delivered, and log what it answers.
        // SWEEP EVERY ITEM ID TO ITS INTERNAL NAME, once, to a CSV.
        //
        // Only 905 of the catalogue's 21,740 items carry a resolvable name in the
        // extracted marketplace tables, and that gap has blocked three separate questions
        // in a day: which items are outfit pieces for the elp/eye slots, which of the 657
        // primary weapons the inventory is missing, and what an id in a log actually is.
        // The client resolves all of them; it has just never been asked in bulk.


        // sub_5DE440 parses a comma-separated string of item ids into these: the array,
        // its length, and its capacity. VA 0xC9113CC / 0xC9113D4 at image base 0x400000.
        static constexpr std::size_t ExcludedItemsArrayRva = 0x8D113CC;
        static constexpr std::size_t ExcludedItemsCountRva = 0x8D113D4;

        // sub_5E3760, the ownership resolver behind 94 call sites.
        // int __usercall(int itemId@<eax>, void *outRecord@<edi>) -> eax; the record's
        // +4 is a u16 set to 1 when the item is owned.
        static constexpr std::size_t OwnershipResolverRva = 0x1E3760;
        [[nodiscard]] std::optional<std::uint8_t> readAttachmentModelSlot(
            std::string_view attachmentName) const;
        [[nodiscard]] bool weaponRegistryInitialized() const;
        [[nodiscard]] bool attachmentModelResolutionAvailable(
            std::uint32_t baseWeaponAssetIndex,
            std::uint32_t attachmentIndex) const;
        // DOES THIS WEAPON ACTUALLY HAVE A MODEL FOR THIS ATTACHMENT?
        //
        // attachmentModelResolutionAvailable answers "which model", and out.exe's own
        // lookup sub_42F9B0 returns the NONE model when the attachment is not in the
        // weapon's table -- a legitimate answer meaning "this weapon has no model for
        // it". Reading that as "available" is what put a red dot on an MSR and faulted
        // the client at spawn with `1073 tag_reticle_red_dot ..._vmchar` (section 187).
        //
        // The registration side settles which test is right: sub_42F910 appends
        // (attachment, model) pairs to word_198C0A0[128 * weapon] and SKIPS the append
        // entirely when the model is the none model, so the table holds exactly the
        // attachments a weapon genuinely has a model for. PRESENCE IN THE TABLE is the
        // support test, and that is the registration invariant rather than an inference.
        // TRANSLATE A GENERIC ATTACHMENT ITEM INTO THIS WEAPON'S OWN ID.
        //
        // The profile stores ONE attachment item for an optic and hangs it on several
        // different weapons -- item 25703 appears at ordinal 23 for three classes whose
        // primaries are two different guns. But the ids in the modular string are
        // PER-WEAPON: 6206 is `red_rmrtmp`, 14268 is `red_rmrm9`, and retail publishes
        // each on its own weapon.
        //
        // What ties them together is the MODEL INDEX. Both RMRs resolve to model 17,
        // both extended magazines to 10, `mag_fast*` to 11, `mag_fmj*` to 12. So the
        // model index is the weapon-independent identity of an attachment, and the
        // translation is: find the model this item names anywhere, then find the entry
        // in the TARGET weapon's table carrying that same model. Section 187h.
        //
        // Returns nothing when the target weapon has no entry for that model, which is
        // the honest answer for a red dot on a weapon that does not take one.
        // dword_1978640[id] -- the string an interned attachment id stands for. The
        // merged list is keyed by NAME downstream, so a translated id has to carry its
        // own name with it or the merge re-looks-up the one we just replaced.
        [[nodiscard]] std::optional<std::string> internedAttachmentName(
            std::uint32_t attachmentId) const;
        [[nodiscard]] std::optional<std::uint32_t> attachmentIdForWeapon(
            std::uint32_t targetWeaponAssetIndex,
            std::uint32_t canonicalAttachmentId) const;
        [[nodiscard]] std::uint32_t attachmentTableCountForWeapon(
            std::uint32_t baseWeaponAssetIndex) const;
        [[nodiscard]] bool attachmentSupportedByWeapon(
            std::uint32_t baseWeaponAssetIndex,
            std::uint32_t attachmentIndex) const;
        [[nodiscard]] std::optional<std::string> readWeaponDefinitionName(
            std::uint32_t weaponAssetIndex) const;
        [[nodiscard]] bool readWeaponDefinition(
            std::uint32_t weaponAssetIndex,
            ClientWeaponSelection &selection) const;
        [[nodiscard]] std::optional<TraceResult> traceTransformedCapsule(
            const TraceResult &initialTrace,
            const std::array<float, 3> &start,
            const std::array<float, 3> &end,
            const TraceBounds &bounds,
            const SvCollisionEntity &entity) const;
        // CODREF(sv_trace): what 3.3.3.3's SV_PointTraceToEntity 0x005FB510
        // does per entity, in this project, because 1649370 does not contain
        // that function at all (section 73). Bones are posed in MODEL space, so
        // the ray is carried into it by the entity's own origin and angles and
        // the hit normal is carried back out.
        [[nodiscard]] bool traceServerLocationalEntities(
            const SvPointTraceRequest &request,
            std::span<const std::uint8_t> priorityMap,
            std::span<const SvCollisionEntity> entities,
            TraceResult &aggregate,
            NativeExceptionDetails &exceptionDetails) const;
        [[nodiscard]] std::optional<TraceResult> traceTransformedBrushModel(
            const TraceResult &initialTrace,
            const std::array<float, 3> &start,
            const std::array<float, 3> &end,
            const TraceBounds &bounds,
            const SvCollisionEntity &entity,
            const SvGlassState &glassState) const;
        [[nodiscard]] std::optional<bool> traceTransformedDObjContentsPassed(
            const SvRadiusDamageTraceRequest &request,
            const SvCollisionEntity &entity) const;

        // OLMOD(engine-binding-state): resolved entry/global pointers and all
        // mutable maps, scratch arenas, diagnostics, caches, and atomic status
        // below belong to the source adapter. Pointer target layouts are only
        // native where their separately audited type or call adapter says so.
        std::uint8_t *module_{};
        DBFindXAssetHeader dbFindXAssetHeader_{};
        DBIsXAssetDefault dbIsXAssetDefault_{};
        DBLinkXAssetEntry dbLinkXAssetEntry_{};
        void *msgInit_{};
        void *msgWriteBits_{};
        void *msgWriteString_{};
        void *levelZoneLoad_{};
        void *collisionMapLoad_{};
        void *collisionWorldLink_{};
        void *ccsClear_{};
        CCSInitialize ccsInitialize_{};
        void *ccsGetConstantString_{};
        Trace trace_{};
        void *worldTrace_{};
        void *transformedBrushModelTrace_{};
        void *transformedCapsuleTrace_{};
        void *calcTraceExtents_{};
        void *pointTraceToEntities_{};
        void *dobjGeomTracelinePartBits_{};
        void *dobjContentsTracelinePartBits_{};
        void *dobjTraceline_{};
        void *dobjContentsTraceline_{};
        void *pointTraceStaticModels_{};
        void *dobjCalcSkel_{};
        void *gEntities_{};
        void **serverGameEntitiesPointer_{};
        std::uint32_t *serverGameEntityCount_{};
        void *svLinkEntity_{};
        void *svUnlinkEntity_{};
        void *svTrace_{};
        mutable std::unordered_map<std::uint32_t,
            NativeServerEntityMirrorSlot> nativeServerEntityMirror_;
        mutable std::string nativeServerEntityMirrorFailure_;
        mutable std::string scriptModelDObjFailure_;
        mutable bool nativeServerEntityMirrorObservedSuccess_{};
        // CODREF(bg_update_player_dobj): the server's own millisecond clock,
        // stamped into the anim-condition block every time it is installed.
        // Zero until the first mirror phase runs, which is correct - no native
        // animation call can happen before that.
        mutable std::uint32_t serverAnimationTimeMilliseconds_{};
        mutable std::uint64_t nativeTraceComparisonCount_{};
        mutable std::uint64_t nativeTraceMismatchCount_{};
        mutable std::uint64_t nativeTraceUnavailableCount_{};
        mutable std::uint32_t nativeTraceLoggedDifferenceMask_{};
        mutable std::string nativeTraceComparisonFailure_;
        mutable bool nativeTraceComparisonObservedSuccess_{};
        BGGetPlayerEyePosition bgGetPlayerEyePosition_{};
        void *bulletEndpos_{};
        void *viewMovementDamageKick_{};
        void *viewMovementIdleAngles_{};
        void *viewMovementBobAngles_{};
        void *viewMovementAdsBob_{};
        void *weaponMovementBase_{};
        void *weaponMovementSway_{};
        void *weaponMovementRecoil_{};
        void *weaponMovementBob_{};
        void *setWeaponMovementAngles_{};
        void *anglesToQuaternion_{};
        void *angleVectors_{};
        void *matrixMultiply_{};
        void *axisToAngles_{};
        void *pmoveSingle_{};
        void *pmSetPitchValues_{};
        void *playerStateToEntityState_{};
        void *bgAnimScriptEvent_{};
        void *bgFindAnims_{};
        void *bgAnimParseAnimScript_{};
        void *bgLoadAnimTrees_{};
        void *scrCreateObject_{};
        void *scrPrecacheAnimTrees_{};
        void *bgFindAnimTrees_{};
        void *bgFinalizePlayerAnims_{};
        void *nativeLerpFrameAccessorInitialize_{};
        void *bgPlayerAnimation_{};
        void *bgUpdatePlayerDObj_{};
        void *worldCharacterModelResolve_{};
        void *mantleCreateAnims_{};
        void **mantleAnims_{};
        void *hunkAllocXAnim_{};
        void *xanimFreeInfo_{};
        void *dobjFree_{};
        void *serverDObjGet_{};
        void *serverDObjCreate_{};
        // OLMOD(actor_hit_pose_lifetime): stable bounded owners; native XAnim
        // nodes are freed on removal/generation change. Tree headers are reused,
        // never allocated repeatedly from the level hunk on each respawn.
        struct ActorHitPoseOwner
        {
            alignas(8) std::array<std::uint32_t, 2> tree{};
            SvActorHitPose source{};
            void *dobj{};
            std::uint32_t updatedTime{};
            bool failed{};
        };
        mutable std::array<ActorHitPoseOwner, 2048> actorHitPoseOwners_{};
        mutable bool actorHitPosesEnabled_{};
        mutable std::uint32_t actorHitPoseLogCount_{};
        const std::byte *nativeLerpFrameZeroVector_{};
        const std::uint32_t *nativeLerpFrameSetKey_{};
        const std::uint32_t *nativePlayerStateAccessorSetKey_{};
        const std::uint32_t *nativePlayerStateAccessorGetKey_{};
        const std::uint32_t *nativeLerpFrameGetKey_{};
        Trace *pmoveTraceHandlerSlot_{};
        Trace clientPmoveTrace_{};
        std::byte **animConditionBasePointer_{};
        std::byte **animScriptDataPointer_{};
        alignas(16) mutable std::array<std::byte, ServerAnimConditionStorageSize>
            serverAnimConditionStorage_{};
        alignas(16) mutable std::array<std::byte, ServerLoadAnimStorageSize>
            serverLoadAnimStorage_{};
        mutable std::array<
            NativeServerCharacterInfoSlot, ServerCharacterInfoSlotCount>
            nativeServerCharacterInfo_{};
        // The last successfully resolved component-model names per entity. See
        // characterModelNames(); this exists so the match-end precache burst can
        // name the podium's models without re-entering the resolver.
        mutable std::array<
            std::vector<std::string>, ServerCharacterInfoSlotCount>
            characterModelNames_{};
        [[nodiscard]] std::span<std::byte, SvNativeCharacterInfoSize>
            serverCharacterInfo(std::size_t entityNum) const noexcept;
        mutable std::string nativeServerPlayerDObjFailure_;
        mutable bool nativeServerPlayerDObjObservedSuccess_{};
        mutable bool nativeServerPlayerDObjPoisoned_{};
        mutable std::array<bool, 18> nativeServerDObjGeomDiagnosticsLogged_{};
        static constexpr std::size_t NativeServerDObjSkelArenaSize =
            18 * 256 * 32;
        alignas(16) mutable std::array<std::byte, NativeServerDObjSkelArenaSize>
            nativeServerDObjSkelArena_{};
        mutable std::size_t nativeServerDObjSkelArenaUsed_{};
        mutable std::uint32_t nativeServerDObjSkeletonLogCounter_{};
        mutable std::array<std::int32_t, 64>
            nativeServerDObjSkeletonHeight_{};
        mutable std::int32_t nativeServerDObjSkeletonHeightScratch_{};
        mutable std::uint32_t nativeCapsuleCandidacyLogCounter_{};
        mutable std::uint32_t pointTraceRefusalLogCounter_{};
        mutable std::uint32_t mirrorMismatchLogCounter_{};
        mutable std::uint32_t locationalEntityTraceLogCounter_{};
        mutable std::uint32_t hitboxTraceLogCounter_{};
        mutable std::uint32_t capsuleEntityTraceLogCounter_{};
        mutable std::uint32_t bookingSelectionRefusalLogCounter_{};
        mutable std::array<PlayerDObjState, 64>
            playerDObjReportedState_{};
        // TODO(CODOL): edge-trigger state for the animation-state report.
        mutable std::array<std::string, 64> nativeServerAnimationReport_{};
        mutable std::uint32_t nativeServerDObjSkelEpoch_{};
        void *weaponSlotReadStaged_{};
        LoadoutRecordBuild loadoutRecordBuild_{};
        // Edge-trigger for the capture-refusal line. A literal each time, so pointer
        // comparison is the identity test and no allocation happens on the hot path.
        mutable const char *lastLoadoutRefusal_{};
        mutable std::string lastDefaultAttachmentRefusal_;
        // Deduped like the refusal above it: a blank  cell is a note, not a
        // failure, and it must not repeat once per weapon resolution.
        mutable std::string lastBlankEnabledNote_;
        // -2 means "no refusal on record"; -1 and 0 are real values this can see.
        mutable int lastCharacterIndexRefusal_{-2};
        void *weaponClassFieldGet_{};
        CurrentCharacterGet currentCharacterGet_{};
        CharacterSlotGet characterSlotGet_{};
        void *characterCurrentItemsCopy_{};
        // Both __cdecl with ordinary stack arguments, so both can be plain typed
        // pointers rather than guarded register adapters.
        void *characterRecordFillDefaults_{};
        void *characterRecordToSelectionNames_{};
        void *characterSelectionResolve_{};
        void *configStringGet_{};
        WeaponLookup weaponLookup_{};
        WeaponResolver weaponResolver_{};
        AttachmentLookup attachmentLookup_{};
        WeaponRegistryReset weaponRegistryReset_{};
        WeaponRegistryInitialize weaponRegistryInitialize_{};
        WeaponKnifeStatsLoad weaponKnifeStatsLoad_{};
        ZoneLoaded zoneLoaded_{};
        mutable std::atomic<std::uint32_t> constantConfigStringChecksum_{};
        mutable std::atomic<ClientLoadoutResolveFailure> loadoutResolveFailure_{};
        mutable std::atomic<ClientCharacterPresentationResolveFailure>
            characterPresentationResolveFailure_{};
        mutable std::atomic<ServerAnimationInitializationStatus>
            serverAnimationInitializationStatus_{
                ServerAnimationInitializationStatus::NotInitialized};
        mutable std::atomic<AlphaWeaponPortStatus> alphaWeaponPortStatus_{
            AlphaWeaponPortStatus::Disabled};
        mutable std::atomic<bool> alphaWeaponModelAuditComplete_{};
        mutable std::atomic<bool> xmodelSurfaceAuditComplete_{};
        mutable std::atomic<std::uint32_t>
            characterPresentationResolveRecordIndex_{0xFFFFFFFFu};
        mutable std::atomic<std::uint32_t>
            characterPresentationResolveItemId_{};
        mutable std::map<std::string, std::vector<SvModularWeaponConfigString>>
            modularDependencyCache_;
        std::atomic<std::uint32_t> gameThreadId_{};
        std::atomic<bool> bindingCommitted_{};
    };

    // OLMOD(engine-message-writer): C++ MsgWriter adapter over retained CODOL
    // MSG_* functions and native msg_t storage; not a native class/vtable.
    class EngineMsgWriter final : public MsgWriter
    {
    public:
        EngineMsgWriter(
            const EngineBindings &bindings,
            std::span<std::uint8_t> buffer);

        void MSG_WriteData(std::span<const std::uint8_t> value) override;
        void MSG_WriteBits(std::int32_t value, std::uint32_t bits) override;
        void MSG_WriteString(std::string_view value) override;
        [[nodiscard]] bool overflowed() const override;
        [[nodiscard]] std::span<const std::uint8_t> data() const;

    private:
        const EngineBindings &bindings_;
        msg_t message_{};
    };

    /// Install the vectored fault witness for this process.
    ///
    /// Costs nothing until a fault happens, which is why it is safe where a hook
    /// on the per-frame functions involved is not.
    void armNativeFaultWitness(void *module);
}
