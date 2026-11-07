#include "CodolStartupTasks.hpp"

#include "ServiceRegistry.hpp"

#include <array>
#include <string_view>

namespace AlwaysofflineRe::Demonware
{
    void registerCodolStartupTasks(ServiceRegistry &registry)
    {
        struct EmptyTask
        {
            std::uint8_t service;
            std::uint8_t task;
            std::string_view name;
        };

        // Every entry below was observed returning a type-1 empty-success
        // envelope in the recovered CODOL startup capture.
        constexpr std::array EmptyTasks{
            EmptyTask{ 0x47, 0x04, "RecoveredEmpty::0x47/0x04" },
            EmptyTask{ 0x47, 0x0A, "RecoveredEmpty::0x47/0x0A" },
            EmptyTask{ 0x50, 0x46, "RecoveredEmpty::0x50/0x46" },
            EmptyTask{ 0x47, 0x03, "RecoveredEmpty::0x47/0x03" },
            EmptyTask{ 0x06, 0x05, "RecoveredEmpty::0x06/0x05" },
            EmptyTask{ 0x50, 0x6B, "RecoveredEmpty::0x50/0x6B" },
            EmptyTask{ 0x50, 0xE6, "RecoveredEmpty::0x50/0xE6" },
            EmptyTask{ 0x5D, 0x01, "Unknown93::task1" },
            EmptyTask{ 0x09, 0x10, "RecoveredEmpty::0x09/0x10" },
            EmptyTask{ 0x44, 0x01, "RecoveredEmpty::0x44/0x01" },
            EmptyTask{ 0x09, 0x0E, "RecoveredEmpty::0x09/0x0E" },
            EmptyTask{ 0x03, 0x35, "RecoveredEmpty::0x03/0x35" },
            EmptyTask{ 0x1D, 0x0A, "RecoveredEmpty::0x1D/0x0A" },
            EmptyTask{ 0x50, 0xAD, "RecoveredEmpty::0x50/0xAD" },
            EmptyTask{ 0x50, 0xAE, "RecoveredEmpty::0x50/0xAE" },
            EmptyTask{ 0x66, 0x01, "RecoveredEmpty::0x66/0x01" },
            EmptyTask{ 0x09, 0x09, "RecoveredEmpty::0x09/0x09" },
            EmptyTask{ 0x09, 0x0C, "RecoveredEmpty::0x09/0x0C" },
            EmptyTask{ 0x47, 0x07, "RecoveredEmpty::0x47/0x07" },
            EmptyTask{ 0x03, 0x2E, "RecoveredEmpty::0x03/0x2E" },
            EmptyTask{ 0x03, 0x30, "RecoveredEmpty::0x03/0x30" },
            EmptyTask{ 0x47, 0x0F, "RecoveredEmpty::0x47/0x0F" },
        };

        for (const auto &entry : EmptyTasks)
        {
            registry.registerTask(entry.service, entry.task, std::string(entry.name),
                [](const ServiceRequest &request)
                {
                    return ServiceResponse{ .task = request.task };
                });
        }
    }
}
