#include "ContentUnlock2Service.hpp"

#include "ByteBuffer.hpp"

#include <algorithm>

namespace AlwaysofflineRe::Demonware
{
    void ContentUnlock2Service::registerTasks(ServiceRegistry &registry) const
    {
        registry.registerTask(0x1C, 1, "ContentUnlock2::task1", [this](const auto &request)
        {
            return task1(request);
        });
        registry.registerTask(0x1C, 2, "ContentUnlock2::task2", [this](const auto &request)
        {
            return task2(request);
        });
        registry.registerTask(0x1C, 3, "ContentUnlock2::task3", [this](const auto &request)
        {
            return task3(request);
        });
        registry.registerTask(0x1C, 4, "ContentUnlock2::task4", [this](const auto &request)
        {
            return task4(request);
        });
    }

    ServiceResponse ContentUnlock2Service::task1(const ServiceRequest &request) const
    {
        ByteBuffer input(request.payload);
        std::vector<std::uint32_t> contentIds;
        if (!input.readU32Array(contentIds) || !input.valid())
            return ServiceResponse{ .error = 1000, .task = request.task };
        incrementUnlockCounts(contentIds);
        return ServiceResponse{ .task = request.task };
    }

    ServiceResponse ContentUnlock2Service::task2(const ServiceRequest &request) const
    {
        ByteBuffer input(request.payload);
        std::uint64_t userId{};
        std::vector<std::uint32_t> contentIds;
        if (!input.readU64(userId) || !input.readU32Array(contentIds) || !input.valid())
            return ServiceResponse{ .error = 1000, .task = request.task };
        incrementUnlockCounts(contentIds);
        return ServiceResponse{ .task = request.task };
    }

    ServiceResponse ContentUnlock2Service::task3(const ServiceRequest &request) const
    {
        ByteBuffer input(request.payload);
        std::uint64_t userId{};
        if (!input.readU64(userId) || !input.valid())
            return ServiceResponse{ .error = 1000, .task = request.task };
        return ServiceResponse{ .task = request.task };
    }

    ServiceResponse ContentUnlock2Service::task4(const ServiceRequest &request) const
    {
        ByteBuffer input(request.payload);
        std::vector<std::uint32_t> contentIds;
        if (!input.readU32Array(contentIds) || !input.valid())
            return ServiceResponse{ .error = 1000, .task = request.task };

        ServiceResponse response{ .task = request.task };
        response.objects.reserve(contentIds.size());
        std::scoped_lock lock(mutex_);
        for (const auto contentId : contentIds)
        {
            const auto entry = unlockCounts_.find(contentId);
            const auto count = entry == unlockCounts_.end() ? 0 : entry->second;
            ByteBuffer object;
            object.writeU32(contentId);
            object.writeU32((std::max)(count, std::uint32_t{ 32 }));
            response.objects.push_back(object.data());
        }
        return response;
    }

    void ContentUnlock2Service::incrementUnlockCounts(
        const std::span<const std::uint32_t> contentIds) const
    {
        std::scoped_lock lock(mutex_);
        for (const auto contentId : contentIds)
            ++unlockCounts_[contentId];
    }
}
