#pragma once

#include "ServiceRegistry.hpp"

#include <cstdint>
#include <mutex>
#include <span>
#include <unordered_map>

namespace AlwaysofflineRe::Demonware
{
    class ContentUnlock2Service
    {
    public:
        void registerTasks(ServiceRegistry &registry) const;

    private:
        [[nodiscard]] ServiceResponse task1(const ServiceRequest &request) const;
        [[nodiscard]] ServiceResponse task2(const ServiceRequest &request) const;
        [[nodiscard]] ServiceResponse task3(const ServiceRequest &request) const;
        [[nodiscard]] ServiceResponse task4(const ServiceRequest &request) const;
        void incrementUnlockCounts(std::span<const std::uint32_t> contentIds) const;

        mutable std::mutex mutex_;
        mutable std::unordered_map<std::uint32_t, std::uint32_t> unlockCounts_;
    };
}
