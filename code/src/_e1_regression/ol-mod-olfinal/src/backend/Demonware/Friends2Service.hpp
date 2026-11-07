#pragma once

#include "AuthSession.hpp"
#include "ServiceRegistry.hpp"

namespace AlwaysofflineRe::Demonware
{
    class Friends2Service
    {
    public:
        explicit Friends2Service(AuthSession &session);

        void registerTasks(ServiceRegistry &registry) const;

    private:
        [[nodiscard]] ServiceResponse getFriends(const ServiceRequest &request) const;

        AuthSession &session_;
    };
}
