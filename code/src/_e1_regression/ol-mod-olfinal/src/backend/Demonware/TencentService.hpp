#pragma once

#include "AuthSession.hpp"
#include "ServiceRegistry.hpp"

namespace AlwaysofflineRe::Demonware
{
    class TencentService
    {
    public:
        explicit TencentService(AuthSession &session);

        void registerTasks(ServiceRegistry &registry) const;

    private:
        [[nodiscard]] ServiceResponse verifyString(const ServiceRequest &request) const;
        [[nodiscard]] ServiceResponse task2(const ServiceRequest &request) const;
        [[nodiscard]] ServiceResponse getAasRecord(const ServiceRequest &request) const;
        [[nodiscard]] ServiceResponse acceptTelemetry(const ServiceRequest &request) const;
        [[nodiscard]] ServiceResponse claimClientDecidedRewards(const ServiceRequest &request) const;

        AuthSession &session_;
    };
}
