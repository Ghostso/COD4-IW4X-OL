#pragma once

#include "AuthSession.hpp"
#include "ServiceRegistry.hpp"

namespace AlwaysofflineRe::Demonware
{
    class TitleUtilitiesService
    {
    public:
        explicit TitleUtilitiesService(AuthSession &session);

        void registerTasks(ServiceRegistry &registry) const;

    private:
        [[nodiscard]] ServiceResponse getServerTime(const ServiceRequest &request) const;
        [[nodiscard]] ServiceResponse task9(const ServiceRequest &request) const;

        AuthSession &session_;
    };
}
