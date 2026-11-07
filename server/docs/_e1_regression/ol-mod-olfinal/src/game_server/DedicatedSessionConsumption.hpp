#pragma once

#include <cstdint>

namespace CodolGameServer
{
    enum class DedicatedSessionConsumeStage : std::uint32_t
    {
        None,
        Queued,
        Processing,
        MapAssetLoadFailed,
        WaitingForMapAssets,
        ConfigStringGenerationResetFailed,
        WaitingForClientReadiness,
        WaitingForConfigStringGeneration,
        ConstantConfigStringsInitializationFailed,
        WeaponRegistryUnavailable,
        WeaponRegistryInitializationFailed,
        CharacterPresentationFailed,
        WeaponLoadoutFailed,
        ConfigureBookingFailed,
        Accepted,
        WorldInitializationFailed,
        SessionRosterRejected,
    };

    struct DedicatedSessionConsumptionStatus
    {
        std::uint64_t queuedRequestId{};
        std::uint64_t processedRequestId{};
        DedicatedSessionConsumeStage stage{};
        std::int32_t failedClassIndex{-1};
        std::uint32_t requestedClassMask{};
        std::uint32_t resolvedClassMask{};
        std::uint32_t characterFailure{};
        std::uint32_t characterRecordIndex{0xFFFFFFFFu};
        std::uint32_t characterItemId{};

        bool operator==(const DedicatedSessionConsumptionStatus &) const = default;
    };

    class DedicatedSessionConsumptionTracker
    {
    public:
        void queued(const std::uint64_t requestId)
        {
            status_.queuedRequestId = requestId;
            if (!status_.processedRequestId)
                status_.stage = DedicatedSessionConsumeStage::Queued;
        }

        void processing(
            const std::uint64_t requestId,
            const std::uint32_t requestedClassMask)
        {
            status_.processedRequestId = requestId;
            status_.stage = DedicatedSessionConsumeStage::Processing;
            status_.failedClassIndex = -1;
            status_.requestedClassMask = requestedClassMask;
            status_.resolvedClassMask = 0;
            status_.characterFailure = 0;
            status_.characterRecordIndex = 0xFFFFFFFFu;
            status_.characterItemId = 0;
        }

        void failed(
            const DedicatedSessionConsumeStage stage,
            const std::int32_t failedClassIndex,
            const std::uint32_t resolvedClassMask)
        {
            status_.stage = stage;
            status_.failedClassIndex = failedClassIndex;
            status_.resolvedClassMask = resolvedClassMask;
        }

        void waiting(const DedicatedSessionConsumeStage stage)
        {
            status_.stage = stage;
            status_.failedClassIndex = -1;
            status_.resolvedClassMask = 0;
        }

        void accepted(const std::uint32_t resolvedClassMask)
        {
            status_.stage = DedicatedSessionConsumeStage::Accepted;
            status_.failedClassIndex = -1;
            status_.resolvedClassMask = resolvedClassMask;
        }

        void characterFailure(
            const std::uint32_t failure,
            const std::uint32_t recordIndex,
            const std::uint32_t itemId)
        {
            status_.characterFailure = failure;
            status_.characterRecordIndex = recordIndex;
            status_.characterItemId = itemId;
        }

        [[nodiscard]] DedicatedSessionConsumptionStatus status() const
        {
            return status_;
        }

    private:
        DedicatedSessionConsumptionStatus status_;
    };
}
