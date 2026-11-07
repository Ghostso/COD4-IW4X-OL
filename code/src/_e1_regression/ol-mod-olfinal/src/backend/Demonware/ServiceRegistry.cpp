#include "ServiceRegistry.hpp"

#include <utility>

namespace AlwaysofflineRe::Demonware
{
    std::optional<ServiceRequest> parseServiceRequest(const std::span<const std::uint8_t> decoded)
    {
        if (decoded.size() < 3)
            return std::nullopt;

        ServiceRequest request{
            .service = decoded[0],
            .protocolVersion = decoded[1],
            .task = decoded[2],
            .payload = std::vector<std::uint8_t>(decoded.begin() + 3, decoded.end()),
        };
        if (request.protocolVersion != 3)
            return std::nullopt;
        return request;
    }

    std::vector<std::uint8_t> ServiceResponse::serialize() const
    {
        ByteBuffer output;
        output.writeU64(transaction);
        output.writeU32(error);
        output.writeU8(task);
        if (error != 0)
        {
            output.writeU64(transaction);
            return output.data();
        }

        output.writeU32(static_cast<std::uint32_t>(objects.size()));
        if (!objects.empty())
        {
            output.writeU32(static_cast<std::uint32_t>(objects.size()));
            for (const auto &object : objects)
                output.writeRaw(object);
        }
        return output.data();
    }

    void ServiceRegistry::registerTask(
        const std::uint8_t service,
        const std::uint8_t task,
        std::string name,
        Handler handler)
    {
        tasks_.insert_or_assign({ service, task }, Entry{ std::move(name), std::move(handler) });
    }

    std::optional<ServiceResponse> ServiceRegistry::dispatch(const ServiceRequest &request) const
    {
        const auto iterator = tasks_.find({ request.service, request.task });
        if (iterator == tasks_.end())
            return std::nullopt;
        auto response = iterator->second.handler(request);
        stampTransaction(response);
        return response;
    }

    ServiceResponse ServiceRegistry::acknowledgeUnhandled(const ServiceRequest &request) const
    {
        ServiceResponse response{ .task = request.task };
        stampTransaction(response);
        return response;
    }

    void ServiceRegistry::stampTransaction(ServiceResponse &response) const
    {
        if (response.transaction != 0)
            return;
        const auto counter = static_cast<std::uint8_t>(nextTransaction_.fetch_add(1) + 1);
        response.transaction = OriginalTransactionPrefix | counter;
    }

    std::string ServiceRegistry::taskName(const std::uint8_t service, const std::uint8_t task) const
    {
        const auto iterator = tasks_.find({ service, task });
        return iterator == tasks_.end() ? std::string{} : iterator->second.name;
    }
}
