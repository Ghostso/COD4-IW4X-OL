#include "sv_collision_mp.hpp"

#include <algorithm>
#include <cmath>
#include <limits>
#include <utility>

namespace CodolGameServer
{
    namespace
    {
        // CODREF(sv_trace): DObjGeomTraceline indexes this table with an
        // unsigned byte stored by each XModel bone.
        //
        // THESE ARE CODOL'S OWN TABLES AND THEY ARE IN BOTH IMAGES. Section 51i
        // recorded them as FOREIGN - "BO1/Ghosts, in neither CODOL image" - and
        // that is refuted by the images themselves. The locational leaf passes a
        // static table to DObjTraceline at its own call site, and both builds
        // hold the same twenty bytes at the address it pushes:
        //
        //     3.3.3.3  bullet 0x00CDF430   rifle 0x00CDF444  (adjacent, stride 20)
        //     1649370  bullet 0x00E5AF9C   rifle 0x00E5B000  (100 bytes apart)
        //
        //     bullet  1 3 3 3 3 3 3 3 3 3 3 3 3 3 3 3 3 3 0 101
        //     rifle   1 9 9 9 8 7 6 6 6 6 5 5 4 4 4 4 3 3 0 101
        //
        // BYTE-IDENTICAL BETWEEN THE TWO BUILDS, so the eighteen leading values
        // this tree already carried were right. Index 19 was NOT: it held 201,
        // which is the Ghosts value, and the table is TWENTY entries, not 22 -
        // indexes 20 and 21 were invented and index 20 is the first byte of the
        // NEXT table on 3.3.3.3. The tail stays zero past 20 so an unknown CODOL
        // classification fails closed instead of reading whatever follows (on
        // 1649370 that is a pointer array).
        constexpr std::array<std::uint8_t, LocationalPriorityMapSize>
            BulletPriorityMap{
                1, 3, 3, 3, 3, 3, 3, 3, 3, 3,
                3, 3, 3, 3, 3, 3, 3, 3, 0, 101,
            };
        constexpr std::array<std::uint8_t, LocationalPriorityMapSize>
            RiflePriorityMap{
                1, 9, 9, 9, 8, 7, 6, 6, 6, 6,
                5, 5, 4, 4, 4, 4, 3, 3, 0, 101,
            };

        // OLMOD(source-collision-guards): finite/bounds checks and shadow link
        // geometry protect the native boundary. quatToAxis and packed glass
        // coordinates reproduce only the reviewed glass serialization subset.
        // TODO(CODOL): Replace shared math with retained CODOL helpers when the
        // exact glass server caller and ABI are recovered.
        bool finiteVector(const std::array<float, 3> &vector)
        {
            return std::ranges::all_of(vector, [](const float value) {
                return std::isfinite(value);
            });
        }

        std::optional<std::array<std::array<float, 3>, 3>> quatToAxis(
            const std::array<float, 4> &quaternion)
        {
            const auto normSquared =
                quaternion[0] * quaternion[0] +
                quaternion[1] * quaternion[1] +
                quaternion[2] * quaternion[2] +
                quaternion[3] * quaternion[3];
            if (!std::isfinite(normSquared) || normSquared <= 0.0f)
                return std::nullopt;

            const auto scale = 2.0f / normSquared;
            const auto xx = quaternion[0] * quaternion[0] * scale;
            const auto yy = quaternion[1] * quaternion[1] * scale;
            const auto zz = quaternion[2] * quaternion[2] * scale;
            const auto xy = quaternion[0] * quaternion[1] * scale;
            const auto xz = quaternion[0] * quaternion[2] * scale;
            const auto xw = quaternion[0] * quaternion[3] * scale;
            const auto yz = quaternion[1] * quaternion[2] * scale;
            const auto yw = quaternion[1] * quaternion[3] * scale;
            const auto zw = quaternion[2] * quaternion[3] * scale;
            const std::array<std::array<float, 3>, 3> axis{ {
                { 1.0f - (zz + yy), zw + xy, xz - yw },
                { xy - zw, 1.0f - (zz + xx), yz + xw },
                { xz + yw, yz - xw, 1.0f - (xx + yy) },
            } };
            if (!std::ranges::all_of(axis, [](const auto &row) {
                    return finiteVector(row);
                }))
            {
                return std::nullopt;
            }
            return axis;
        }

        std::uint8_t packGlassImpactPosition(const float position)
        {
            const auto packed = std::round(
                position * (63.0f / 512.0f) + 31.5f);
            return static_cast<std::uint8_t>(std::clamp(packed, 0.0f, 63.0f));
        }

        bool validBounds(const TraceBounds &bounds)
        {
            return finiteVector(bounds.midpoint) &&
                finiteVector(bounds.halfSize) &&
                std::ranges::none_of(
                    bounds.halfSize,
                    [](const float value) { return value < 0.0f; });
        }

        std::uint32_t clampSolidComponent(const float value)
        {
            return static_cast<std::uint32_t>(std::clamp(
                static_cast<std::int32_t>(value), 1, 255));
        }

        std::optional<TraceBounds> linkedPlayerBounds(
            const std::array<float, 3> &origin,
            const TraceBounds &bounds)
        {
            if (!finiteVector(origin) || !validBounds(bounds))
                return std::nullopt;
            TraceBounds result;
            for (std::size_t axis = 0; axis != result.midpoint.size(); ++axis)
            {
                result.midpoint[axis] = origin[axis] + bounds.midpoint[axis];
                result.halfSize[axis] = bounds.halfSize[axis] + 1.0f;
            }
            return validBounds(result) ? std::optional{ result } : std::nullopt;
        }

        std::optional<TraceBounds> linkedBrushBounds(
            const std::array<float, 3> &origin,
            const std::array<float, 3> &angles,
            const TraceBounds &bounds)
        {
            if (!finiteVector(origin) || !finiteVector(angles) ||
                !validBounds(bounds))
            {
                return std::nullopt;
            }

            TraceBounds result;
            const auto unrotated = std::ranges::all_of(
                angles, [](const float value) { return value == 0.0f; });
            if (unrotated)
            {
                for (std::size_t axis = 0; axis != result.midpoint.size(); ++axis)
                {
                    result.midpoint[axis] = origin[axis] + bounds.midpoint[axis];
                    result.halfSize[axis] = bounds.halfSize[axis] + 1.0f;
                }
            }
            else
            {
                float radiusSquared{};
                for (std::size_t axis = 0; axis != result.midpoint.size(); ++axis)
                {
                    const auto extent =
                        std::abs(bounds.midpoint[axis]) + bounds.halfSize[axis];
                    radiusSquared += extent * extent;
                    result.midpoint[axis] = origin[axis];
                }
                const auto radius = std::sqrt(radiusSquared);
                if (!std::isfinite(radius))
                    return std::nullopt;
                result.halfSize.fill(radius + 1.0f);
            }
            return validBounds(result) ? std::optional{ result } : std::nullopt;
        }
    }

    bool SV_IsCollisionEntityValid(const SvCollisionEntity &entity)
    {
        // OLMOD(source-collision-view): admission for the normalized mirror;
        // CODOL native gentity/svEntity validation remains inside bindings.
        const auto shape = static_cast<std::uint8_t>(entity.shape);
        const auto shapeValid = shape <=
            static_cast<std::uint8_t>(SvCollisionShape::ScriptModelDObj);
        const auto role = static_cast<std::uint8_t>(entity.bodyRole);
        const auto roleValid = role <=
                static_cast<std::uint8_t>(SvCollisionBodyRole::Actor) &&
            (entity.shape == SvCollisionShape::Capsule
                    ? true
                    : entity.bodyRole == SvCollisionBodyRole::None);
        const auto brushIdentityValid =
            entity.shape == SvCollisionShape::BrushModel
            ? entity.brushModelClipHandle.has_value() &&
                entity.modelName.empty()
            : !entity.brushModelClipHandle.has_value() &&
                (entity.shape == SvCollisionShape::ScriptModelDObj
                        ? !entity.modelName.empty() &&
                            entity.modelName.front() != '*' &&
                            entity.modelName.find('\0') == std::string::npos &&
                            std::isfinite(entity.modelScale) &&
                            entity.modelScale > 0.0f
                        : entity.modelName.empty()) &&
                // CODREF(client_think_real): a player capsule carries YAW ONLY.
                // BO1 0x005FAAAE zeroes all three components and 0x005FAAE7
                // writes only currentAngles[1]; Ghosts 0x140115783/0x14011578A
                // zero pitch/roll and 0x1401157B8 writes only yaw. Keeping
                // pitch and roll pinned to zero is therefore an invariant, not
                // a simplification - CODOL SV_PointTraceToEntity 0x005FB510
                // feeds this vector straight to AnglesToAxis, so a non-zero
                // pitch would tip the whole hit skeleton over.
                (entity.shape == SvCollisionShape::ScriptModelDObj ||
                    (entity.angles[0] == 0.0f && entity.angles[2] == 0.0f));
        return shapeValid && roleValid && brushIdentityValid &&
            entity.entityNum <= MaximumServerCollisionEntityNum &&
            (!entity.ownerEntityNum ||
                *entity.ownerEntityNum <= MaximumServerCollisionEntityNum) &&
            finiteVector(entity.origin) && finiteVector(entity.angles) &&
            validBounds(entity.bounds) &&
            validBounds(entity.absoluteBounds);
    }

    std::optional<SvCollisionEntity> SV_LinkPlayerCollisionEntity(
        const std::uint32_t entityNum,
        std::optional<std::uint32_t> ownerEntityNum,
        const std::array<float, 3> &origin,
        const std::array<float, 3> &angles,
        const TraceBounds &bounds,
        const std::uint32_t contents)
    {
        // CODREF(sv_link_entity): CODOL SV_LinkEntity 0x005FAE70 derives the
        // expanded absolute Bounds before publishing the native CM link.
        const auto absoluteBounds = linkedPlayerBounds(origin, bounds);
        if (!contents || !absoluteBounds)
            return std::nullopt;
        SvCollisionEntity entity{
            .entityNum = entityNum,
            .ownerEntityNum = ownerEntityNum,
            .origin = origin,
            .bounds = bounds,
            .absoluteBounds = *absoluteBounds,
            .contents = contents,
            .linked = true,
            .bodyRole = SvCollisionBodyRole::Player,
            .angles = angles,
        };
        return SV_IsCollisionEntityValid(entity)
            ? std::optional{ std::move(entity) }
            : std::nullopt;
    }

    std::optional<SvCollisionEntity> SV_LinkActorCollisionEntity(
        const std::uint32_t entityNum,
        std::optional<std::uint32_t> ownerEntityNum,
        const std::array<float, 3> &origin,
        const std::array<float, 3> &angles,
        const TraceBounds &bounds,
        const std::uint32_t contents)
    {
        auto entity = SV_LinkPlayerCollisionEntity(
            entityNum, ownerEntityNum, origin, angles, bounds, contents);
        if (!entity)
            return std::nullopt;
        entity->bodyRole = SvCollisionBodyRole::Actor;
        return SV_IsCollisionEntityValid(*entity)
            ? entity
            : std::nullopt;
    }

    std::optional<SvCollisionEntity> SV_LinkBrushModelCollisionEntity(
        const std::uint32_t entityNum,
        std::optional<std::uint32_t> ownerEntityNum,
        const std::array<float, 3> &origin,
        const std::array<float, 3> &angles,
        const SvBrushModelCollision &model)
    {
        // CODREF(sv_link_entity): BO1/BO2/Ghosts retain brush identity and use
        // expanded model bounds; rotated brushes receive a radius broadphase.
        // CODDIFF(sv_link_entity): this source shadow is validated again by
        // retained CODOL SV_LinkEntity before production trace publication.
        const auto absoluteBounds = linkedBrushBounds(origin, angles, model.bounds);
        if (!model.contents || !absoluteBounds)
            return std::nullopt;
        SvCollisionEntity entity{
            .entityNum = entityNum,
            .ownerEntityNum = ownerEntityNum,
            .origin = origin,
            .bounds = model.bounds,
            .absoluteBounds = *absoluteBounds,
            .contents = model.contents,
            .linked = true,
            .shape = SvCollisionShape::BrushModel,
            .angles = angles,
            .brushModelClipHandle = model.clipHandle,
        };
        return SV_IsCollisionEntityValid(entity)
            ? std::optional{ std::move(entity) }
            : std::nullopt;
    }

    std::optional<SvCollisionEntity> SV_LinkScriptModelCollisionEntity(
        const std::uint32_t entityNum,
        std::optional<std::uint32_t> ownerEntityNum,
        const std::array<float, 3> &origin,
        const std::array<float, 3> &angles,
        std::string modelName,
        const float modelScale,
        const std::uint32_t contents)
    {
        if (!contents || modelName.empty())
            return std::nullopt;

        // CODDIFF(sv_link_entity): CODOL SV_LinkEntity derives authoritative
        // broadphase bounds from the server DObj radius. Source collision must
        // not approximate the XModel with a player capsule.
        SvCollisionEntity entity{
            .entityNum = entityNum,
            .ownerEntityNum = ownerEntityNum,
            .origin = origin,
            .contents = contents,
            .linked = true,
            .shape = SvCollisionShape::ScriptModelDObj,
            .angles = angles,
            .modelName = std::move(modelName),
            .modelScale = modelScale,
        };
        return SV_IsCollisionEntityValid(entity)
            ? std::optional{ std::move(entity) }
            : std::nullopt;
    }

    std::optional<TraceBounds> SV_DecodePackedSolidBounds(const std::uint32_t solid)
    {
        // CODREF(sv_trace): exact 1649370 0x46D738..0x46D7AC. Brush handles
        // and zero solids belong to other paths; invalid geometry stays absent.
        if (!solid || solid >= BrushModelSolid)
            return std::nullopt;
        const float radius = static_cast<float>(solid & 255u) - 1.0f;
        const float bottom = 2.0f - static_cast<float>((solid >> 8) & 255u);
        const float top = static_cast<float>((solid >> 16) & 255u) - 33.0f;
        if (radius <= 0.0f || top <= bottom)
            return std::nullopt;
        return TraceBounds{ .midpoint = {0.0f, 0.0f, (top + bottom) * 0.5f},
            .halfSize = {radius, radius, (top - bottom) * 0.5f} };
    }

    std::optional<std::uint32_t> SV_EncodePlayerSolid(
        const TraceBounds &bounds,
        const std::uint32_t contents)
    {
        if (!validBounds(bounds))
            return std::nullopt;
        // CODREF(sv_link_entity): CODOL 0x005FAEC9 gates packet-solid
        // encoding with contents & 0x02004001. player_die in BO1/Ghosts sets
        // corpse contents to 0x04000000 before relinking, so a corpse remains
        // linked in the server collision tree but deliberately publishes zero
        // packet solid.
        if (!(contents & PlayerSolidEncodingContents))
            return 0;

        // CODREF(sv_link_entity): CODOL 0x005FAED5 packs the horizontal
        // component directly from Bounds::halfSize[0]. The local midpoint is
        // applied to absolute link bounds, not to the packet solid radius.
        const auto horizontalRadius = bounds.halfSize[0];
        const auto minZ = bounds.midpoint[2] - bounds.halfSize[2];
        const auto maxZ = bounds.midpoint[2] + bounds.halfSize[2];
        if (!std::isfinite(horizontalRadius) || !std::isfinite(minZ) ||
            !std::isfinite(maxZ))
        {
            return std::nullopt;
        }

        const auto horizontal = clampSolidComponent(horizontalRadius);
        const auto lower = clampSolidComponent(1.0f - minZ);
        const auto upper = clampSolidComponent(maxZ + 32.0f);
        const auto solid = horizontal | (lower << 8) | (upper << 16);
        return solid == 0xFFFFFF ? 1u : solid;
    }

    std::optional<std::uint32_t> SV_EncodeBrushModelSolid(
        const SvBrushModelCollision &model)
    {
        // CODREF(sv_link_entity): 0xFFFFFF is the native packet sentinel for a
        // brush model; its exact collision bounds stay out of this encoding.
        return validBounds(model.bounds)
            ? std::optional{ BrushModelSolid }
            : std::nullopt;
    }

    bool SV_IsTraceEntityFilterValid(const SvTraceEntityFilter &filter)
    {
        // OLMOD(source-trace-filter): normalized base/owner identity admission;
        // complete CODOL IgnoreEntParams flags remain TODO(CODOL).
        return (!filter.passEntityNum ||
                   *filter.passEntityNum <= MaximumServerCollisionEntityNum) &&
            (!filter.passOwnerEntityNum ||
                (filter.passEntityNum &&
                    *filter.passOwnerEntityNum <=
                        MaximumServerCollisionEntityNum));
    }

    bool SV_IsPointTraceRequestValid(const SvPointTraceRequest &request)
    {
        const auto mode = static_cast<std::uint8_t>(request.mode);
        return finiteVector(request.start) && finiteVector(request.end) &&
            request.contentMask && SV_IsTraceEntityFilterValid(request.filter) &&
            mode <= static_cast<std::uint8_t>(
                SvPointTraceMode::RifleLocational) &&
            !(request.worldOnly && request.entitiesOnly) &&
            (request.mode != SvPointTraceMode::CollisionOnly ||
                (!request.allowChildren && !request.entitiesOnly));
    }

    std::span<const std::uint8_t> SV_GetLocationalPriorityMap(
        const SvPointTraceMode mode)
    {
        switch (mode)
        {
        case SvPointTraceMode::BulletLocational:
            return BulletPriorityMap;
        case SvPointTraceMode::RifleLocational:
            return RiflePriorityMap;
        case SvPointTraceMode::CollisionOnly:
            return {};
        }
        return {};
    }

    bool SV_ShouldClipToEntity(
        const SvCollisionEntity &entity,
        const SvTraceEntityFilter &filter,
        const std::uint32_t contentMask)
    {
        // CODREF(sv_trace): CODOL SV_Trace 0x005FB940 passes base/parent
        // identity to native CM traversal. BO1 SV_SetupIgnoreEntParams
        // 0x00721F40 confirms self/child/sibling filtering with parent kept.
        if (!entity.linked || !(entity.contents & contentMask))
            return false;
        if (!filter.passEntityNum)
            return true;
        if (entity.entityNum == *filter.passEntityNum)
            return false;
        return !entity.ownerEntityNum ||
            (*entity.ownerEntityNum != *filter.passEntityNum &&
                (!filter.passOwnerEntityNum ||
                    *entity.ownerEntityNum != *filter.passOwnerEntityNum));
    }

    bool SV_ShouldBroadphaseClipToEntity(
        const std::array<float, 3> &start,
        const std::array<float, 3> &end,
        const TraceBounds &movingBounds,
        const SvCollisionEntity &entity)
    {
        // CODREF(sv_trace): conservative swept-AABB rejection mirrors the
        // reference server broadphase only; retained native code owns narrow
        // phase.
        if (!finiteVector(start) || !finiteVector(end) ||
            !validBounds(movingBounds) || !SV_IsCollisionEntityValid(entity))
        {
            return false;
        }
        for (std::size_t axis = 0; axis != start.size(); ++axis)
        {
            const auto movingMin = std::min(start[axis], end[axis]) +
                movingBounds.midpoint[axis] - movingBounds.halfSize[axis];
            const auto movingMax = std::max(start[axis], end[axis]) +
                movingBounds.midpoint[axis] + movingBounds.halfSize[axis];
            const auto targetMin = entity.absoluteBounds.midpoint[axis] -
                entity.absoluteBounds.halfSize[axis];
            const auto targetMax = entity.absoluteBounds.midpoint[axis] +
                entity.absoluteBounds.halfSize[axis];
            if (!std::isfinite(movingMin) || !std::isfinite(movingMax) ||
                !std::isfinite(targetMin) || !std::isfinite(targetMax))
            {
                return false;
            }
            if (movingMax < targetMin || movingMin > targetMax)
                return false;
        }
        return true;
    }

    bool SV_ApplyEntityTraceHit(
        TraceResult &aggregate,
        const TraceResult &entityTrace,
        const SvCollisionEntity &entity)
    {
        // OLMOD(source-trace-aggregation): normalized overlay used by fixtures
        // and diagnostics, not a replacement for production native SV_Trace.
        if (entityTrace.fraction >= aggregate.fraction)
            return false;
        aggregate = entityTrace;
        aggregate.hitType = TraceHitTypeEntity;
        aggregate.hitId = static_cast<std::uint16_t>(entity.entityNum);
        aggregate.contents = entity.contents;
        return true;
    }

    SvTraceComparisonDifference SV_CompareTraceResults(
        const TraceResult &source,
        const TraceResult &native,
        const float floatTolerance)
    {
        // OLMOD(native-trace-comparison): fail closed on non-finite native or
        // source floats so a corrupt trace cannot be reported as equivalent.
        if (!std::isfinite(floatTolerance) || floatTolerance < 0.0f ||
            !std::isfinite(source.fraction) ||
            !std::isfinite(native.fraction) ||
            std::abs(source.fraction - native.fraction) > floatTolerance)
        {
            return SvTraceComparisonDifference::Fraction;
        }
        for (std::size_t axis = 0; axis != source.normal.size(); ++axis)
        {
            if (!std::isfinite(source.normal[axis]) ||
                !std::isfinite(native.normal[axis]) ||
                std::abs(source.normal[axis] - native.normal[axis]) >
                floatTolerance)
            {
                return SvTraceComparisonDifference::Normal;
            }
        }
        if (source.surfaceFlags != native.surfaceFlags)
            return SvTraceComparisonDifference::SurfaceFlags;
        if (source.contents != native.contents)
            return SvTraceComparisonDifference::Contents;
        if (source.hitType != native.hitType)
            return SvTraceComparisonDifference::HitType;
        if (source.hitId != native.hitId)
            return SvTraceComparisonDifference::HitId;
        if (source.modelIndex != native.modelIndex)
            return SvTraceComparisonDifference::ModelIndex;
        if (source.partName != native.partName)
            return SvTraceComparisonDifference::PartName;
        if (source.partGroup != native.partGroup)
            return SvTraceComparisonDifference::PartGroup;
        if (source.allSolid != native.allSolid)
            return SvTraceComparisonDifference::AllSolid;
        if (source.startSolid != native.startSolid)
            return SvTraceComparisonDifference::StartSolid;
        if (source.walkable != native.walkable)
            return SvTraceComparisonDifference::Walkable;
        return SvTraceComparisonDifference::None;
    }

    void SvGlassState::reset()
    {
        pieceStates_.clear();
    }

    bool SV_IsGlassMapMetadataValid(const SvGlassMapMetadata &metadata)
    {
        // OLMOD(glass-map-projection): validates only fields copied from the
        // map; native glass definition and support-graph ownership is broader.
        if (metadata.definitionCount > 1024 ||
            metadata.initialPieces.size() > SvGlassPieceCount ||
            (!metadata.initialPieces.empty() && !metadata.definitionCount))
        {
            return false;
        }
        const auto finite = [](const auto &values) {
            return std::ranges::all_of(values, [](const float value) {
                return std::isfinite(value);
            });
        };
        return std::ranges::all_of(
            metadata.initialPieces,
            [&](const SvGlassInitialPieceGeometry &piece) {
                return finite(piece.quaternion) && finite(piece.origin) &&
                    finite(piece.textureCoordinateOrigin) &&
                    std::isfinite(piece.radius) && piece.radius >= 0.0f &&
                    std::isfinite(piece.doubledArea) &&
                    piece.doubledArea >= 0.0f &&
                    piece.definitionIndex < metadata.definitionCount;
            });
    }

    std::optional<SvGlassImpactQuantization> SV_QuantizeGlassImpact(
        const SvGlassMapMetadata &metadata,
        const std::uint32_t pieceIndex,
        const std::array<float, 3> &hitPosition,
        const std::array<float, 3> &damageDirection,
        const SvGlassDirectionEncoder &directionEncoder)
    {
        // CODREF(bullet_process): position uses the retained six-bit glass
        // impact encoding; direction stays delegated to CODOL DirToByte.
        // CODDIFF(bullet_process): quaternion projection is source math until
        // the removed dedicated glass caller is recovered.
        if (!SV_IsGlassMapMetadataValid(metadata) ||
            pieceIndex >= metadata.initialPieces.size() ||
            !finiteVector(hitPosition) || !finiteVector(damageDirection))
        {
            return std::nullopt;
        }

        const auto directionLengthSquared =
            damageDirection[0] * damageDirection[0] +
            damageDirection[1] * damageDirection[1] +
            damageDirection[2] * damageDirection[2];
        if (!std::isfinite(directionLengthSquared))
            return std::nullopt;
        if (directionLengthSquared == 0.0f)
            return SvGlassImpactQuantization{};
        if (!directionEncoder)
            return std::nullopt;
        const auto direction = directionEncoder(damageDirection);
        if (!direction)
            return std::nullopt;

        const auto &piece = metadata.initialPieces[pieceIndex];
        const auto axis = quatToAxis(piece.quaternion);
        if (!axis)
            return std::nullopt;
        const std::array offset{
            hitPosition[0] - piece.origin[0],
            hitPosition[1] - piece.origin[1],
            hitPosition[2] - piece.origin[2],
        };
        const auto project = [&offset](const std::array<float, 3> &row) {
            return offset[0] * row[0] + offset[1] * row[1] +
                offset[2] * row[2];
        };
        const auto positionX = project((*axis)[0]);
        const auto positionY = project((*axis)[1]);
        if (!std::isfinite(positionX) || !std::isfinite(positionY))
            return std::nullopt;
        return SvGlassImpactQuantization{
            .impact = SvGlassImpact{
                .direction = *direction,
                .positionX = packGlassImpactPosition(positionX),
                .positionY = packGlassImpactPosition(positionY),
            },
        };
    }

    bool SV_ShouldSendGlassImpact(
        const std::int32_t lastStateChangeTime,
        const std::int32_t snapshotTime)
    {
        // CODREF(bullet_process): reference glass snapshots retain impact data
        // for the inclusive one-second state-change window.
        return static_cast<std::int64_t>(lastStateChangeTime) + 1000 >=
            static_cast<std::int64_t>(snapshotTime);
    }

    bool SvGlassState::setPieceState(
        const std::uint32_t pieceIndex,
        const SvGlassPieceState state,
        std::optional<SvGlassImpact> impact)
    {
        if (pieceIndex >= SvGlassPieceCount ||
            static_cast<std::uint8_t>(state) >
                static_cast<std::uint8_t>(SvGlassPieceState::Deleted) ||
            (impact && (state != SvGlassPieceState::Destroyed ||
                impact->positionX > 0x3F || impact->positionY > 0x3F)))
        {
            return false;
        }

        const auto entry = std::lower_bound(
            pieceStates_.begin(), pieceStates_.end(), pieceIndex,
            [](const SvGlassPieceStateRecord &candidate,
                const std::uint32_t index) {
                return candidate.pieceIndex < index;
            });
        if (state == SvGlassPieceState::Pristine)
        {
            if (entry != pieceStates_.end() && entry->pieceIndex == pieceIndex)
                pieceStates_.erase(entry);
            return true;
        }

        const SvGlassPieceStateRecord replacement{
            .pieceIndex = static_cast<std::uint16_t>(pieceIndex),
            .state = state,
            .impact = std::move(impact),
        };
        if (entry != pieceStates_.end() && entry->pieceIndex == pieceIndex)
            *entry = replacement;
        else
            pieceStates_.insert(entry, replacement);
        return true;
    }

    SvGlassPieceState SvGlassState::pieceState(
        const std::uint32_t pieceIndex) const
    {
        const auto entry = std::lower_bound(
            pieceStates_.begin(), pieceStates_.end(), pieceIndex,
            [](const SvGlassPieceStateRecord &candidate,
                const std::uint32_t index) {
                return candidate.pieceIndex < index;
            });
        return entry != pieceStates_.end() && entry->pieceIndex == pieceIndex
            ? entry->state
            : SvGlassPieceState::Pristine;
    }

    bool SvGlassState::isPieceSolid(const std::uint32_t pieceIndex) const
    {
        return static_cast<std::uint8_t>(pieceState(pieceIndex)) <
            static_cast<std::uint8_t>(SvGlassPieceState::Destroyed);
    }

    std::size_t SvGlassState::nonSolidPieceCount() const
    {
        return std::ranges::count_if(
            pieceStates_, [](const SvGlassPieceStateRecord &piece) {
                return static_cast<std::uint8_t>(piece.state) >=
                    static_cast<std::uint8_t>(SvGlassPieceState::Destroyed);
            });
    }

    const std::vector<SvGlassPieceStateRecord> &SvGlassState::pieceStates() const
    {
        return pieceStates_;
    }

    bool SvGlassDamageState::configure(
        const std::uint32_t pieceCount,
        const SvGlassDamageThresholds thresholds)
    {
        // CODREF(bullet_process): 0xFFFF is reserved for the deleted sentinel;
        // a destroy threshold at that value is unreachable by accumulated
        // damage.
        if (pieceCount > SvGlassPieceCount || !thresholds.weaken ||
            thresholds.destroy == std::numeric_limits<std::uint16_t>::max() ||
            thresholds.weaken > thresholds.destroy)
        {
            return false;
        }
        thresholds_ = thresholds;
        pieces_.assign(pieceCount, {});
        return true;
    }

    void SvGlassDamageState::reset()
    {
        thresholds_ = {};
        pieces_.clear();
    }

    std::optional<SvGlassDamageResult> SvGlassDamageState::damagePiece(
        const std::uint32_t pieceIndex,
        const std::uint32_t damage,
        const std::int32_t levelTime)
    {
        if (pieceIndex >= pieces_.size() || !damage || !thresholds_.weaken ||
            thresholds_.weaken > thresholds_.destroy)
        {
            return std::nullopt;
        }

        auto &piece = pieces_[pieceIndex];
        const auto stateForDamage = [this](const std::uint16_t value) {
            if (value >= thresholds_.destroy)
                return SvGlassPieceState::Destroyed;
            if (value >= thresholds_.weaken)
                return SvGlassPieceState::Weakened;
            return SvGlassPieceState::Pristine;
        };
        const auto previousState = stateForDamage(piece.damageTaken);
        // Ghosts reserves 0xFFFF for the deleted sentinel; accumulated
        // damage saturates one value below it. CODOL's local thresholds are
        // still configurable until their native constants are recovered.
        constexpr auto MaximumAccumulatedDamage =
            std::numeric_limits<std::uint16_t>::max() - 1u;
        piece.damageTaken = static_cast<std::uint16_t>(std::min<std::uint64_t>(
            MaximumAccumulatedDamage,
            static_cast<std::uint64_t>(piece.damageTaken) + damage));
        const auto state = stateForDamage(piece.damageTaken);
        if (state != previousState)
            piece.lastStateChangeTime = levelTime;
        return SvGlassDamageResult{
            .pieceIndex = pieceIndex,
            .state = state,
            .stateChanged = state != previousState,
        };
    }

    std::uint32_t SvGlassDamageState::pieceCount() const
    {
        return static_cast<std::uint32_t>(pieces_.size());
    }

    SvGlassDamageThresholds SvGlassDamageState::thresholds() const
    {
        return thresholds_;
    }

    std::optional<SvGlassDamagePiece> SvGlassDamageState::piece(
        const std::uint32_t pieceIndex) const
    {
        return pieceIndex < pieces_.size()
            ? std::optional{ pieces_[pieceIndex] }
            : std::nullopt;
    }
}
