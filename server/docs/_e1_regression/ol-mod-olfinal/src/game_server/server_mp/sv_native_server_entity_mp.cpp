#include "sv_native_server_entity_mp.hpp"

#include "sv_entity_mp.hpp"

#include <cstring>
#include <type_traits>

namespace CodolGameServer
{
    namespace
    {
        // CODREF(sv_link_entity): CODOL SV_LinkEntity 0x005FAE70 fixes the
        // embedded gentity_s runtime block at +0x110..+0x15F. BO1
        // 0x0071F960 and Ghosts 0x14020A6C0 confirm the same solid -> bounds
        // -> DObj/brush contents -> spatial-link responsibility, but their
        // layouts and ABIs are deliberately not reused here.
        // CODDIFF(1649370): gentity_t embeds entityState_s at offset 0, and that
        // grew 0x110 -> 0x118 here, so EVERY field past it moves +8. SV_LinkEntity
        // (A sub_1FAE70 <-> C sub_34EF10) reads them line for line and settles all
        // of them at once: linked 0x110 -> 0x118, svFlags 0x112 -> 0x11A, bounds
        // 0x114 -> 0x11C, contents 0x12C -> 0x134, absolute bounds 0x130 -> 0x138,
        // origin 0x148 -> 0x150. The gentity STRIDE is 712 on both builds -- both
        // functions divide by it to recover the entity number -- so the eight bytes
        // the entityState gained came back out of the tail.
        // The offsets inside the embedded entityState follow the ET_PLAYER netfield
        // map instead: solid 0x0A4 -> 0x0AC and the model index 0x098 -> 0x09C.
        constexpr std::size_t EntityNumberOffset = 0x000;
        constexpr std::size_t EntityTypeOffset = 0x004;
        // CODREF(client_think_real): CODOL
        // BG_PlayerToEntity_SetTrajectory 0x00413360 encrypts these three
        // entityState origin words with their field addresses.
        // OLMOD(section-84): the three OFFSETS are out.exe's own -- its
        // ET_PLAYER netfield table carries 0x18/0x1C/0x20 as the trajectory
        // triple (bits -83/-82/-81, types 6/7/8) and so does ET_GENERAL. The
        // cited address is 3.3.3.3's; the numbers are this build's.
        constexpr std::array<std::size_t, 3> SecureOriginOffsets{
            0x018, 0x01C, 0x020,
        };
        constexpr std::size_t BrushModelIndexOffset = 0x09C;
        constexpr std::size_t SolidOffset = 0x0AC;
        constexpr std::size_t ScriptMoverScaleOffset = 0x054;
        constexpr std::size_t IsLinkedOffset = 0x118;
        constexpr std::size_t ModelTypeOffset = 0x119;
        constexpr std::size_t ServerFlagsOffset = 0x11A;
        constexpr std::size_t IsInUseOffset = 0x11B;
        constexpr std::size_t BoundsOffset = 0x11C;
        constexpr std::size_t ContentsOffset = 0x134;
        constexpr std::size_t CurrentOriginOffset = 0x150;
        constexpr std::size_t CurrentAnglesOffset = 0x15C;
        constexpr std::uint8_t EntityTypePlayer = 1;
        constexpr std::uint8_t EntityTypeActor = 19;
        constexpr std::uint8_t EntityTypeActorCorpse = 21;
        constexpr std::uint8_t ModelTypeBrush = 4;

        template <typename Value>
        void writeValue(
            SvNativeServerEntity &entity,
            const std::size_t offset,
            const Value &value)
        {
            static_assert(std::is_trivially_copyable_v<Value>);
            std::memcpy(entity.bytes.data() + offset, &value, sizeof(value));
        }

        template <typename Value>
        Value readValue(
            const SvNativeServerEntity &entity,
            const std::size_t offset)
        {
            static_assert(std::is_trivially_copyable_v<Value>);
            Value value{};
            std::memcpy(&value, entity.bytes.data() + offset, sizeof(value));
            return value;
        }

        std::optional<std::uint32_t> expectedSolid(
            const SvCollisionEntity &entity)
        {
            // CODREF(sv_link_entity): brush models publish 0xFFFFFF; ordinary
            // player capsules pack max-x, 1-min-z, and max-z+32. Script-model
            // DObjs remain nonsolid on the packet while native DObj contents
            // own their locational collision.
            if (entity.shape == SvCollisionShape::ScriptModelDObj)
                return 0;
            if (entity.shape == SvCollisionShape::BrushModel)
            {
                if (!entity.brushModelClipHandle)
                    return std::nullopt;
                return SV_EncodeBrushModelSolid({
                    .clipHandle = *entity.brushModelClipHandle,
                    .bounds = entity.bounds,
                    .contents = entity.contents,
                });
            }
            if (entity.brushModelClipHandle)
                return std::nullopt;
            return SV_EncodePlayerSolid(entity.bounds, entity.contents);
        }
    }

    std::optional<SvNativeServerEntity> SV_BuildNativeServerEntity(
        const SvCollisionEntity &entity,
        const SvNativeEntityState *const entityState)
    {
        // OLMOD(native-gentity-projection): this builds a controlled pre-link
        // image for CODOL's real SV_LinkEntity; it is not a source replacement
        // for that function. Role checks below protect the fixed player,
        // reserved, and dynamic slot ranges owned by the current server.
        const auto solid = expectedSolid(entity);
        const auto bodyState = entity.shape == SvCollisionShape::Capsule
            ? entityState
            : nullptr;
        const auto bodyProjection = bodyState
            ? SV_ReadNativeEntityState(*bodyState)
            : std::nullopt;
        const auto playerBody =
            entity.bodyRole == SvCollisionBodyRole::Player;
        const auto actorBody =
            entity.bodyRole == SvCollisionBodyRole::Actor;
        const auto validCapsuleRole = [&] {
            if (entity.shape != SvCollisionShape::Capsule)
                return true;
            if (!bodyProjection ||
                bodyProjection->number != entity.entityNum)
            {
                return false;
            }
            if (playerBody)
            {
                return entity.entityNum < 18 &&
                    bodyProjection->eType == EntityTypePlayer;
            }
            if (actorBody)
            {
                return entity.entityNum >= FirstDynamicServerEntityNum &&
                    (bodyProjection->eType == EntityTypeActor ||
                        bodyProjection->eType == EntityTypeActorCorpse);
            }
            return false;
        }();
        if (!SV_IsCollisionEntityValid(entity) || !entity.linked ||
            !entity.contents || !solid ||
            (entity.shape != SvCollisionShape::ScriptModelDObj && !*solid &&
                !(entity.shape == SvCollisionShape::Capsule &&
                    entity.contents == DeadPlayerCollisionContents)) ||
            entity.entityNum >= EntityNumWorld ||
            (entity.entityNum >= 18 &&
                entity.entityNum < FirstDynamicServerEntityNum) ||
            !validCapsuleRole ||
            (entity.shape == SvCollisionShape::BrushModel &&
                (entity.entityNum < FirstDynamicServerEntityNum ||
                    entityState)) ||
            (entity.shape == SvCollisionShape::ScriptModelDObj &&
                (entity.entityNum < FirstDynamicServerEntityNum ||
                    entityState || entity.modelName.empty())))
        {
            return std::nullopt;
        }

        SvNativeServerEntity result;
        if (bodyState)
        {
            std::memcpy(
                result.bytes.data(),
                bodyState->bytes.data(),
                SvNativeEntityState::Size);
        }
        writeValue(result, EntityNumberOffset, entity.entityNum);
        writeValue(
            result,
            EntityTypeOffset,
            entity.shape == SvCollisionShape::Capsule
                ? static_cast<std::uint32_t>(bodyProjection->eType)
                : entity.shape == SvCollisionShape::ScriptModelDObj
                    ? std::uint32_t{ 6 }
                    : std::uint32_t{});
        writeValue(result, SolidOffset, *solid);
        if (entity.shape == SvCollisionShape::ScriptModelDObj)
            writeValue(result, ScriptMoverScaleOffset, entity.modelScale);
        writeValue(result, IsLinkedOffset, std::uint8_t{});
        writeValue(
            result,
            ModelTypeOffset,
            entity.shape == SvCollisionShape::BrushModel
                ? ModelTypeBrush
                : std::uint8_t{});
        // CODOL SV_LinkEntity only admits server DObj bounds/locational data
        // when svFlags carries the live-player bit used by BO1 ClientEndFrame.
        writeValue(
            result,
            ServerFlagsOffset,
            // CODREF(sv_link_entity): CODOL's locational DObj branch tests
            // svFlags bit 2. CODOL sub_4E74D0 sets bit 4 for script_model
            // before its DObj update and SV_LinkEntity call.
            entity.shape == SvCollisionShape::Capsule
                ? std::uint8_t{ 2 }
                : entity.shape == SvCollisionShape::ScriptModelDObj
                    ? std::uint8_t{ 4 }
                    : std::uint8_t{});
        writeValue(result, IsInUseOffset, std::uint8_t{ 1 });
        writeValue(result, BoundsOffset, entity.bounds);
        writeValue(result, ContentsOffset, entity.contents);
        writeValue(result, CurrentOriginOffset, entity.origin);
        writeValue(result, CurrentAnglesOffset, entity.angles);
        if (entity.brushModelClipHandle)
        {
            writeValue(
                result,
                BrushModelIndexOffset,
                *entity.brushModelClipHandle);
        }
        return result;
    }

    void SV_CopyNativeServerEntityToSlot(
        SvNativeServerEntity &destination,
        const SvNativeServerEntity &source,
        const SvNativeEntityState *const entityState)
    {
        std::memcpy(
            destination.bytes.data(),
            source.bytes.data(),
            SvNativeServerEntity::Size);
        if (entityState)
            SV_CopyNativeEntityStateToServerEntity(destination, *entityState);
    }

    void SV_CopyNativeEntityStateToServerEntity(
        SvNativeServerEntity &destination,
        const SvNativeEntityState &source)
    {
        // CODDIFF(client_think_real): source and destination are
        // different allocations, so copying the encrypted words verbatim
        // would decode against the wrong field addresses. Relocation keeps the
        // same plaintext while preserving CODOL's native address-bound form.
        std::memcpy(
            destination.bytes.data(),
            source.bytes.data(),
            SvNativeEntityState::Size);
        if (!source.secureOriginAddressBound)
            return;
        for (const auto offset : SecureOriginOffsets)
        {
            std::uint32_t encoded{};
            std::memcpy(
                &encoded, source.bytes.data() + offset, sizeof(encoded));
            const auto sourceAddress = static_cast<std::uint32_t>(
                reinterpret_cast<std::uintptr_t>(
                    source.bytes.data() + offset));
            const auto destinationAddress = static_cast<std::uint32_t>(
                reinterpret_cast<std::uintptr_t>(
                    destination.bytes.data() + offset));
            writeValue(
                destination,
                offset,
                encoded ^ sourceAddress ^ destinationAddress);
        }
    }

    bool SV_ValidateNativeServerEntityLinkResult(
        const SvNativeServerEntity &entity,
        const SvCollisionEntity &source)
    {
        // OLMOD(native-link-postcondition): validate the minimum fields that
        // establish a successful native link without rejecting fields that
        // SV_LinkEntity is expected to derive or normalize itself.
        // TODO(CODOL): recover role-specific postconditions for brush model,
        // live-player DObj and script-model DObj links. Exit when eType,
        // svFlags, bounds/origin, model identity and native link contents have
        // proven invariants plus failure-injection coverage.
        const auto solid = expectedSolid(source);
        if (!solid)
            return false;
        const auto expectedModelType =
            source.shape == SvCollisionShape::BrushModel
            ? ModelTypeBrush
            : std::uint8_t{};
        return readValue<std::uint32_t>(entity, EntityNumberOffset) ==
                source.entityNum &&
            readValue<std::uint32_t>(entity, SolidOffset) == *solid &&
            readValue<std::uint8_t>(entity, IsLinkedOffset) == 1 &&
            readValue<std::uint8_t>(entity, ModelTypeOffset) ==
                expectedModelType &&
            readValue<std::uint8_t>(entity, IsInUseOffset) == 1 &&
            readValue<std::uint32_t>(entity, ContentsOffset) ==
                source.contents;
    }

    bool SV_IsNativeServerEntityAvailableBaseline(
        const SvNativeServerEntity &entity)
    {
        // OLMOD(native-fixed-slot-admission): an unlinked, not-in-use native
        // slot is the current takeover boundary. This is project ownership,
        // not a recovered COD allocation function.
        // TODO(CODOL): replace this predicate with the recovered fixed-slot
        // lifecycle owner once G_Spawn/G_FreeEntity integration can prove
        // generation, script, DObj and subsystem references are all absent.
        return !readValue<std::uint8_t>(entity, IsLinkedOffset) &&
            !readValue<std::uint8_t>(entity, IsInUseOffset);
    }

    bool SV_IsNativeServerEntityLinked(const SvNativeServerEntity &entity)
    {
        return readValue<std::uint8_t>(entity, IsLinkedOffset) != 0;
    }

    void SV_ClearNativeServerEntityLinkedFlag(SvNativeServerEntity &entity)
    {
        writeValue(entity, IsLinkedOffset, std::uint8_t{});
    }
}
