#include "RecoveredCatalog.hpp"

#include <algorithm>
#include <array>

namespace
{
    using AlwaysofflineRe::Demonware::Endpoint;
    using AlwaysofflineRe::Demonware::RecoveredService;

    // Recovered from every xref to Alwaysoffline sub_10035B81. RVAs point to
    // the service dispatchers in the 2019-12-08 x86 DLL (image base 0x10000000).
    constexpr std::array Services{
        RecoveredService{ Endpoint::auth,  0x1A, 0x03758B, "UnknownAuth1A" },
        RecoveredService{ Endpoint::auth,  0x07, 0x037C6A, "UnknownAuth07" },
        RecoveredService{ Endpoint::auth,  0x00, 0x038AA3, "UnknownAuth00" },
        RecoveredService{ Endpoint::auth,  0x0A, 0x039373, "UnknownAuth0A" },
        RecoveredService{ Endpoint::auth,  0x0C, 0x039956, "UnknownAuth0C" },
        RecoveredService{ Endpoint::auth,  0x1C, 0x03A090, "SteamTicketAuth" },

        RecoveredService{ Endpoint::lobby, 0x47, 0x03AA63, "Tencent" },
        RecoveredService{ Endpoint::lobby, 0x21, 0x03B6B0, "Unknown21" },
        RecoveredService{ Endpoint::lobby, 0x32, 0x03E23E, "Unknown32" },
        RecoveredService{ Endpoint::lobby, 0x43, 0x03FB77, "Unknown43" },
        RecoveredService{ Endpoint::lobby, 0x50, 0x04284C, "Marketplace" },
        RecoveredService{ Endpoint::lobby, 0x0A, 0x04B5B9, "Storage2" },
        RecoveredService{ Endpoint::lobby, 0x12, 0x04BE08, "Unknown12" },
        RecoveredService{ Endpoint::lobby, 0x1B, 0x04C493, "Unknown1B" },
        RecoveredService{ Endpoint::lobby, 0x15, 0x04D2EC, "Matchmaking" },
        RecoveredService{ Endpoint::lobby, 0x8A, 0x04D555, "Matchmaking2" },
        RecoveredService{ Endpoint::lobby, 0x09, 0x04EB2F, "Friends2" },
        RecoveredService{ Endpoint::lobby, 0x06, 0x051C27, "BandwidthTest" },
        RecoveredService{ Endpoint::lobby, 0x0B, 0x051C90, "Unknown0B" },
        RecoveredService{ Endpoint::lobby, 0x66, 0x051D4F, "Unknown66" },
        RecoveredService{ Endpoint::lobby, 0x08, 0x053742, "Profiles2" },
        RecoveredService{ Endpoint::lobby, 0x44, 0x053AFA, "RichPresence" },
        RecoveredService{ Endpoint::lobby, 0x0C, 0x054624, "TitleUtilities2" },
        RecoveredService{ Endpoint::lobby, 0x26, 0x054F74, "Unknown26" },
        RecoveredService{ Endpoint::lobby, 0x17, 0x0551A5, "Unknown17" },
        RecoveredService{ Endpoint::lobby, 0x1C, 0x055866, "ContentUnlock2" },
        RecoveredService{ Endpoint::lobby, 0x0F, 0x056083, "Unknown0F" },
    };
}

namespace AlwaysofflineRe::Demonware
{
    std::span<const RecoveredService> recoveredServices()
    {
        return Services;
    }

    std::optional<RecoveredService> findRecoveredService(const Endpoint endpoint, const std::uint8_t id)
    {
        const auto iterator = std::find_if(Services.begin(), Services.end(), [=](const RecoveredService &service)
        {
            return service.endpoint == endpoint && service.id == id;
        });
        return iterator == Services.end() ? std::nullopt : std::optional(*iterator);
    }
}
