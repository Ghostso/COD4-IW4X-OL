#include "AckOnlyServices.hpp"

#include <array>
#include <cstdint>
#include <string>

namespace AlwaysofflineRe::Demonware
{
    namespace
    {
        struct AckTask
        {
            std::uint8_t service;
            std::uint8_t task;
            const char *name;
        };

        // service, task, name. The trailing count is how many times an OLfinal client sent it
        // in the measured menu session of 2026-08-17 (lobby_tasks.log, 659 lines). None of them
        // is retried in a way that reads as rejection, and the menu draws.
        constexpr std::array AckTasks{
            // Teams (3). 53 is the only one the C# server named (getIncomingProposals, itself a
            // bare reply); 46 and 48 arrive beside it just after the profile download.
            // 46: (string "", u64 0, string "", u32 10, u32 0)
            // 48: (string "", u64 0, string "", u32 0, u32 100, u32 0)
            AckTask{ 0x03, 53, "Teams::getIncomingProposals" },   // x1
            AckTask{ 0x03, 46, "Teams::task46" },                 // x8
            AckTask{ 0x03, 48, "Teams::task48" },                 // x8

            // Mail (29). (string "", u32 0, u32 100, bool true) -- an unread-count poll shape.
            AckTask{ 0x1D, 10, "Mail::getUnreadCount" },          // x1

            // RichPresence (68). (string "", u64 userId, string "", u8 1, blob{...,"EDITz"}).
            AckTask{ 0x44, 3, "RichPresence::setPresence" },      // x15

            // Messaging2 (102). Four tasks, all periodic:
            //   1: (u32 0, u32 1, u8 3, u64 0)
            //   2: no payload at all -- the whole frame is 04000000 86 66 03 02
            //   5: (u32 2, u8 1, u8 2)
            //   7: (u32 50) then 50 x (u8 1, u64 i) for i in 0..49 -- a bulk query by index
            AckTask{ 0x66, 1, "Messaging2::task1" },              // x13
            AckTask{ 0x66, 2, "Messaging2::task2" },              // x2
            AckTask{ 0x66, 5, "Messaging2::task5" },              // x7
            AckTask{ 0x66, 7, "Messaging2::task7" },              // x10
        };
    }

    void AckOnlyServices::registerTasks(ServiceRegistry &registry) const
    {
        for (const auto &entry : AckTasks)
        {
            registry.registerTask(
                entry.service,
                entry.task,
                entry.name,
                [](const ServiceRequest &request) { return acknowledge(request); });
        }
    }

    ServiceResponse AckOnlyServices::acknowledge(const ServiceRequest &request)
    {
        // error 0, zero result objects.
        return ServiceResponse{ .task = request.task };
    }
}
