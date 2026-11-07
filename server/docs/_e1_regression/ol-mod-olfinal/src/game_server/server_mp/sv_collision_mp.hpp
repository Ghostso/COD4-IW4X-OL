#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <functional>
#include <optional>
#include <span>
#include <string>
#include <vector>

namespace CodolGameServer
{
    // OLMOD(source-trace-schema): normalized source geometry and result views;
    // neither type is a binary declaration of CODOL Bounds or trace_t.
    struct TraceBounds
    {
        std::array<float, 3> midpoint{};
        std::array<float, 3> halfSize{};

        bool operator==(const TraceBounds &) const = default;
    };

    struct TraceResult
    {
        float fraction{};
        std::array<float, 3> normal{};
        std::uint32_t surfaceFlags{};
        std::uint32_t contents{};
        std::uint32_t hitType{};
        std::uint16_t hitId{};
        std::uint16_t modelIndex{};
        std::uint16_t partName{};
        std::uint16_t partGroup{};
        bool allSolid{};
        bool startSolid{};
        bool walkable{};

        bool operator==(const TraceResult &) const = default;
    };

    // OLMOD(native-trace-comparison): diagnostic classification for shadow
    // comparisons. It is not a CODOL trace result or error enum.
    enum class SvTraceComparisonDifference : std::uint8_t
    {
        None,
        Fraction,
        Normal,
        SurfaceFlags,
        Contents,
        HitType,
        HitId,
        ModelIndex,
        PartName,
        PartGroup,
        AllSolid,
        StartSolid,
        Walkable,
    };

    inline constexpr TraceBounds StandingPlayerTraceBounds{
        .midpoint = { 0.0f, 0.0f, 35.0f },
        .halfSize = { 15.0f, 15.0f, 35.0f },
    };
    inline constexpr TraceBounds DeadPlayerTraceBounds{
        .midpoint = { 0.0f, 0.0f, 15.0f },
        .halfSize = { 15.0f, 15.0f, 15.0f },
    };
    inline constexpr std::uint32_t PlayerCollisionContentMask = 0x02814011;
    inline constexpr std::uint32_t PlayerCollisionContents = 0x02000000;
    inline constexpr std::uint32_t DeadPlayerCollisionContents = 0x04000000;
    inline constexpr std::uint32_t PlayerSolidEncodingContents = 0x02004001;
    inline constexpr std::uint32_t MaximumServerCollisionEntityNum = 2045;
    inline constexpr std::uint32_t TraceHitTypeEntity = 1;
    inline constexpr std::uint32_t TraceHitTypeGlass = 4;
    inline constexpr TraceBounds PointTraceBounds{};
    inline constexpr std::uint32_t BrushModelSolid = 0x00FFFFFF;

    // CODREF(sv_trace): out.exe 0x46D6E0 decodes entityState+0xAC for
    // 0x46DAE0's client capsule. This is the inset trace box, not a gentity.
    [[nodiscard]] std::optional<TraceBounds> SV_DecodePackedSolidBounds(
        std::uint32_t solid);

    // OLMOD(source-collision-view): only shapes currently projected into the
    // native fixed-slot mirror. This is not a complete CODOL entity taxonomy.
    enum class SvCollisionShape : std::uint8_t
    {
        Capsule,
        BrushModel,
        ScriptModelDObj,
    };

    // A capsule describes geometry, not ownership. Players and campaign actors
    // both use body capsules, but occupy different native slot ranges and
    // publish different entity types.
    enum class SvCollisionBodyRole : std::uint8_t
    {
        None,
        Player,
        Actor,
    };

    struct SvBrushModelCollision
    {
        std::uint32_t clipHandle{};
        TraceBounds bounds;
        std::uint32_t contents{};

        bool operator==(const SvBrushModelCollision &) const = default;
    };

    // OLMOD(source-collision-view): normalized source projection used to
    // validate and feed the retained CODOL SV_LinkEntity/SV_Trace boundary;
    // it is not a native gentity_s or svEntity_s layout.
    // OLMOD(actor_hit_pose): source-only pose identity; no network layout changes.
    struct SvActorHitPose
    {
        std::uint32_t generation{};
        std::uint16_t body{}, head{}, animation{};
        std::uint32_t animationStartTime{};
        std::uint16_t lower{};
        bool operator==(const SvActorHitPose &) const = default;
    };

    struct SvCollisionEntity
    {
        std::uint32_t entityNum{};
        std::optional<std::uint32_t> ownerEntityNum;
        std::array<float, 3> origin{};
        TraceBounds bounds;
        TraceBounds absoluteBounds;
        std::uint32_t contents{};
        bool linked{};
        SvCollisionShape shape{ SvCollisionShape::Capsule };
        SvCollisionBodyRole bodyRole{ SvCollisionBodyRole::None };
        std::optional<SvActorHitPose> actorHitPose;
        std::array<float, 3> angles{};
        std::optional<std::uint32_t> brushModelClipHandle;
        std::string modelName;
        float modelScale{ 1.0f };

        bool operator==(const SvCollisionEntity &) const = default;
    };

    struct SvTraceEntityFilter
    {
        std::optional<std::uint32_t> passEntityNum;
        std::optional<std::uint32_t> passOwnerEntityNum;

        bool operator==(const SvTraceEntityFilter &) const = default;
    };

    // OLMOD(source-point-trace-request): selects retained collision-only or
    // locational native consumers without reproducing pointtrace_t layout.
    enum class SvPointTraceMode : std::uint8_t
    {
        CollisionOnly,
        BulletLocational,
        RifleLocational,
    };

    // CODDIFF(1649370): TWENTY, not 22, and it is not a per-build number - both
    // images hold the same twenty-byte table (sv_collision_mp.cpp names the two
    // addresses). 22 came from Ghosts and made indexes 20 and 21 look like
    // classifications this engine can produce; on 3.3.3.3 index 20 is the first
    // byte of the NEXT table.
    inline constexpr std::size_t KnownLocationalPriorityCount = 20;
    inline constexpr std::size_t LocationalPriorityMapSize = 256;

    struct SvPointTraceRequest
    {
        std::array<float, 3> start{};
        std::array<float, 3> end{};
        std::uint32_t contentMask{};
        SvTraceEntityFilter filter;
        SvPointTraceMode mode{ SvPointTraceMode::CollisionOnly };
        bool allowChildren{};
        // Penetration reverse traces need the static BSP exit face without a
        // player or script model in front of it changing the measured depth.
        bool worldOnly{};
        // A penetration trace starts just inside its entry plane. CODOL's
        // retained WorldTrace reports that wall at fraction zero, hiding a
        // player beyond it. This mode runs only the locational entity walker.
        bool entitiesOnly{};

        bool operator==(const SvPointTraceRequest &) const = default;
    };

    [[nodiscard]] bool SV_IsCollisionEntityValid(
        const SvCollisionEntity &entity);
    // CODREF(client_think_real): a live player's gentity_s::r.currentAngles is
    // yaw only. BO1 ClientThink_real 0x005F9980 writes all three components
    // zero at 0x005FAAAE and then only currentAngles[1] = ps.viewangles[1] at
    // 0x005FAAE7; Ghosts ClientThink_real 0x140114E10 does the same at
    // 0x140115783 (pitch), 0x14011578A (roll) and 0x1401157B8 (yaw). CODOL
    // consumes exactly that field: SV_PointTraceToEntity 0x005FB510 calls
    // AnglesToAxis on gentity_s +0x154 and transposes the trace start/end into
    // that frame before DObjTraceline, so the yaw here IS the orientation of
    // the server's hit skeleton.
    [[nodiscard]] std::optional<SvCollisionEntity>
        SV_LinkPlayerCollisionEntity(
            std::uint32_t entityNum,
            std::optional<std::uint32_t> ownerEntityNum,
            const std::array<float, 3> &origin,
            const std::array<float, 3> &angles,
            const TraceBounds &bounds,
            std::uint32_t contents);
    [[nodiscard]] std::optional<SvCollisionEntity>
        SV_LinkActorCollisionEntity(
            std::uint32_t entityNum,
            std::optional<std::uint32_t> ownerEntityNum,
            const std::array<float, 3> &origin,
            const std::array<float, 3> &angles,
            const TraceBounds &bounds,
            std::uint32_t contents);
    [[nodiscard]] std::optional<SvCollisionEntity>
        SV_LinkBrushModelCollisionEntity(
            std::uint32_t entityNum,
            std::optional<std::uint32_t> ownerEntityNum,
            const std::array<float, 3> &origin,
            const std::array<float, 3> &angles,
            const SvBrushModelCollision &model);
    [[nodiscard]] std::optional<SvCollisionEntity>
        SV_LinkScriptModelCollisionEntity(
            std::uint32_t entityNum,
            std::optional<std::uint32_t> ownerEntityNum,
            const std::array<float, 3> &origin,
            const std::array<float, 3> &angles,
            std::string modelName,
            float modelScale,
            std::uint32_t contents);
    [[nodiscard]] std::optional<std::uint32_t> SV_EncodePlayerSolid(
        const TraceBounds &bounds,
        std::uint32_t contents);
    [[nodiscard]] std::optional<std::uint32_t> SV_EncodeBrushModelSolid(
        const SvBrushModelCollision &model);
    [[nodiscard]] bool SV_IsTraceEntityFilterValid(
        const SvTraceEntityFilter &filter);
    [[nodiscard]] bool SV_IsPointTraceRequestValid(
        const SvPointTraceRequest &request);
    [[nodiscard]] std::span<const std::uint8_t>
        SV_GetLocationalPriorityMap(SvPointTraceMode mode);
    [[nodiscard]] bool SV_ShouldClipToEntity(
        const SvCollisionEntity &entity,
        const SvTraceEntityFilter &filter,
        std::uint32_t contentMask);
    [[nodiscard]] bool SV_ShouldBroadphaseClipToEntity(
        const std::array<float, 3> &start,
        const std::array<float, 3> &end,
        const TraceBounds &movingBounds,
        const SvCollisionEntity &entity);
    [[nodiscard]] bool SV_ApplyEntityTraceHit(
        TraceResult &aggregate,
        const TraceResult &entityTrace,
        const SvCollisionEntity &entity);
    [[nodiscard]] SvTraceComparisonDifference SV_CompareTraceResults(
        const TraceResult &source,
        const TraceResult &native,
        float floatTolerance = 0.0001f);

    // CODREF(fxglass): 1024 is out.exe's OWN number, in two independent places, and it was
    // carried from 3.3.3.3 with no comment until section 93.
    //   the WIRE     the sparse glass list is terminated by writing this value as an 11-bit
    //                index. out.exe's reader sub_447500 @0x447527 is `i = BITS(11); 1024 ends
    //                it`, hardcoded -- and an index ABOVE 1024 is not fatal there, it printfs
    //                at 0x447546 and carries on, so only the exact value terminates.
    //   the MAP      every map the game ships sizes its glass array as
    //                pieceLimit == initialPieceCount + 1024, on 27 of 27 maps that have glass
    //                (CODOL-main Tools/olfinal/fxglass-map-survey.py). 1024 is the engine's
    //                fixed headroom for the fragments breaking a pane creates.
    // Two uses, one number, and the second is what makes MaximumFxGlassPieceLimit derivable
    // rather than guessed. Observed maximum initialPieceCount across every map: 879, mp_conflict.
    constexpr std::uint32_t SvGlassPieceCount = 1024;

    // OLMOD(glass-map-projection): fields copied from the retained glass map
    // for server-owned validation/quantization, not the native map structure.
    struct SvGlassInitialPieceGeometry
    {
        std::array<float, 4> quaternion{};
        std::array<float, 3> origin{};
        float radius{};
        std::array<float, 2> textureCoordinateOrigin{};
        std::uint32_t supportMask{};
        float doubledArea{};
        std::uint8_t definitionIndex{};
        std::uint8_t vertexCount{};
        std::uint8_t fanDataCount{};

        bool operator==(const SvGlassInitialPieceGeometry &) const = default;
    };

    struct SvGlassMapMetadata
    {
        std::uint32_t definitionCount{};
        std::vector<SvGlassInitialPieceGeometry> initialPieces;

        bool operator==(const SvGlassMapMetadata &) const = default;
    };

    [[nodiscard]] bool SV_IsGlassMapMetadataValid(
        const SvGlassMapMetadata &metadata);

    enum class SvGlassPieceState : std::uint8_t
    {
        Pristine = 0,
        Weakened = 1,
        Destroyed = 2,
        Deleted = 3,
    };

    struct SvGlassImpact
    {
        std::uint8_t direction{};
        std::uint8_t positionX{};
        std::uint8_t positionY{};

        bool operator==(const SvGlassImpact &) const = default;
    };

    struct SvGlassImpactQuantization
    {
        std::optional<SvGlassImpact> impact;

        bool operator==(const SvGlassImpactQuantization &) const = default;
    };

    using SvGlassDirectionEncoder = std::function<std::optional<std::uint8_t>(
        const std::array<float, 3> &direction)>;

    [[nodiscard]] std::optional<SvGlassImpactQuantization>
        SV_QuantizeGlassImpact(
            const SvGlassMapMetadata &metadata,
            std::uint32_t pieceIndex,
            const std::array<float, 3> &hitPosition,
            const std::array<float, 3> &damageDirection,
            const SvGlassDirectionEncoder &directionEncoder);
    [[nodiscard]] bool SV_ShouldSendGlassImpact(
        std::int32_t lastStateChangeTime,
        std::int32_t snapshotTime);

    struct SvGlassPieceStateRecord
    {
        std::uint16_t pieceIndex{};
        SvGlassPieceState state{ SvGlassPieceState::Pristine };
        std::optional<SvGlassImpact> impact;

        bool operator==(const SvGlassPieceStateRecord &) const = default;
    };

    // OLMOD(server-glass-state): server-owned sparse state. Collision-map
    // piece indexes are supplied by CM_WorldTrace. Pristine and weakened
    // pieces remain solid; destroyed and deleted pieces do not. Pristine
    // pieces are implicit in pieceStates(). This is not native G_GlassData.
    class SvGlassState
    {
    public:
        void reset();
        [[nodiscard]] bool setPieceState(
            std::uint32_t pieceIndex,
            SvGlassPieceState state,
            std::optional<SvGlassImpact> impact = std::nullopt);
        [[nodiscard]] SvGlassPieceState pieceState(
            std::uint32_t pieceIndex) const;
        [[nodiscard]] bool isPieceSolid(std::uint32_t pieceIndex) const;
        [[nodiscard]] std::size_t nonSolidPieceCount() const;
        [[nodiscard]] const std::vector<SvGlassPieceStateRecord> &pieceStates()
            const;

    private:
        std::vector<SvGlassPieceStateRecord> pieceStates_;
    };

    struct SvGlassDamageThresholds
    {
        std::uint16_t weaken{};
        std::uint16_t destroy{};

        bool operator==(const SvGlassDamageThresholds &) const = default;
    };

    struct SvGlassDamagePiece
    {
        std::uint16_t damageTaken{};
        std::uint16_t collapseTime{};
        std::int32_t lastStateChangeTime{};

        bool operator==(const SvGlassDamagePiece &) const = default;
    };

    struct SvGlassDamageResult
    {
        std::uint32_t pieceIndex{};
        SvGlassPieceState state{ SvGlassPieceState::Pristine };
        bool stateChanged{};

        bool operator==(const SvGlassDamageResult &) const = default;
    };

    // OLMOD(server-glass-damage-candidate): copyable command candidate. Callers
    // commit this and SvGlassState only after FireWeapon succeeds. Thresholds
    // remain source policy until CODOL dedicated glass definitions are found.
    class SvGlassDamageState
    {
    public:
        [[nodiscard]] bool configure(
            std::uint32_t pieceCount,
            SvGlassDamageThresholds thresholds);
        void reset();
        [[nodiscard]] std::optional<SvGlassDamageResult> damagePiece(
            std::uint32_t pieceIndex,
            std::uint32_t damage,
            std::int32_t levelTime);
        [[nodiscard]] std::uint32_t pieceCount() const;
        [[nodiscard]] SvGlassDamageThresholds thresholds() const;
        [[nodiscard]] std::optional<SvGlassDamagePiece> piece(
            std::uint32_t pieceIndex) const;

    private:
        SvGlassDamageThresholds thresholds_{};
        std::vector<SvGlassDamagePiece> pieces_;
    };
}
