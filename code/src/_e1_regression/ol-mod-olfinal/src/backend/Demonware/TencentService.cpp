#include "TencentService.hpp"

#include "ByteBuffer.hpp"

namespace AlwaysofflineRe::Demonware
{
    TencentService::TencentService(AuthSession &session)
        : session_(session)
    {
    }

    void TencentService::registerTasks(ServiceRegistry &registry) const
    {
        registry.registerTask(0x47, 1, "Tencent::verifyString", [this](const auto &request)
        {
            return verifyString(request);
        });
        registry.registerTask(0x47, 2, "Tencent::task2", [this](const auto &request)
        {
            return task2(request);
        });
        for (const auto task : { std::uint8_t{ 3 }, std::uint8_t{ 7 }, std::uint8_t{ 8 } })
        {
            registry.registerTask(0x47, task, "Tencent::acceptTelemetry", [this](const auto &request)
            {
                return acceptTelemetry(request);
            });
        }
        registry.registerTask(0x47, 5, "Tencent::getAASRecord", [this](const auto &request)
        {
            return getAasRecord(request);
        });
        registry.registerTask(0x47, 9, "Tencent::task9", [](const auto &request)
        {
            return ServiceResponse{ .task = request.task };
        });
        registry.registerTask(0x47, 11, "Tencent::claimClientDecidedRewards", [this](const auto &request)
        {
            return claimClientDecidedRewards(request);
        });
    }

    ServiceResponse TencentService::verifyString(const ServiceRequest &request) const
    {
        ByteBuffer input(request.payload);
        std::string value;
        if (!input.readString(value) || !input.empty() || !input.valid())
            return ServiceResponse{ .error = 1000, .task = request.task };

        ByteBuffer object;
        object.writeU32(0);
        return ServiceResponse{ .task = request.task, .objects = { object.data() } };
    }

    ServiceResponse TencentService::task2(const ServiceRequest &request) const
    {
        ByteBuffer input(request.payload);
        std::string username;
        if (!input.readString(username))
            return ServiceResponse{ .error = 1000, .task = request.task };

        ByteBuffer object;
        object.writeBool(false);
        object.writeString(username);
        return ServiceResponse{ .task = request.task, .objects = { object.data() } };
    }

    ServiceResponse TencentService::getAasRecord(const ServiceRequest &request) const
    {
        ByteBuffer object;
        object.writeU8(1);
        object.writeU64(session_.snapshot().userId);
        object.writeU8(0x58);
        object.writeU32(60);
        object.writeU32(30);
        return ServiceResponse{ .task = request.task, .objects = { object.data() } };
    }

    ServiceResponse TencentService::acceptTelemetry(const ServiceRequest &request) const
    {
        ByteBuffer input(request.payload);
        std::string value;
        if (!input.readString(value) || !input.empty() || !input.valid())
            return ServiceResponse{ .error = 1000, .task = request.task };
        return ServiceResponse{ .task = request.task };
    }

    ServiceResponse TencentService::claimClientDecidedRewards(const ServiceRequest &request) const
    {
        ByteBuffer input(request.payload);
        std::uint32_t count{};
        if (!input.readU32(count))
            return ServiceResponse{ .error = 1000, .task = request.task };
        for (std::uint32_t index = 0; index != count; ++index)
        {
            std::string eventCode;
            if (!input.readString(eventCode))
                return ServiceResponse{ .error = 1000, .task = request.task };
        }
        if (!input.empty() || !input.valid())
            return ServiceResponse{ .error = 1000, .task = request.task };
        return ServiceResponse{ .task = request.task };
    }
}
