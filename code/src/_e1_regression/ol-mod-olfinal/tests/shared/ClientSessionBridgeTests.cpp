#include "client_bridge/ClientSessionBridge.hpp"

#include <chrono>
#include <future>
#include <stdexcept>
#include <thread>

namespace
{
    void require(const bool condition, const char *const message)
    {
        if (!condition)
            throw std::runtime_error(message);
    }

    OlMod::DedicatedSession::LoadoutRequest fixtureLoadout()
    {
        OlMod::DedicatedSession::LoadoutRequest request{
            .characterIndex = 2,
            .classMask = 1,
            .characterItemIds = { 545 },
        };
        request.classes[0].weapons[0].itemId = 10001;
        request.classes[0].weapons[1].itemId = 10049;
        return request;
    }
}

void runClientSessionBridgeTests()
{
    using namespace std::chrono_literals;
    using namespace OlMod::DedicatedControl;
    OlMod::ClientSessionBridge bridge;
    require(bridge.start(0, 500ms) && bridge.port() != 0,
        "client bridge binds an ephemeral control port");

    const OlMod::DedicatedSession::ClientSessionCapture expected{
        .booking = {
            .playlistId = 26,
            .rotationIndex = 0,
            .mapName = "mp_crash_tropical",
            .gameType = "sd",
        },
        .loadout = fixtureLoadout(),
    };
    auto capture = std::async(std::launch::async, [&] {
        return submit("127.0.0.1", bridge.port(), {
            .type = MessageType::CaptureLoadout,
            .requestId = 91,
        }, 1000);
    });
    for (std::size_t attempt = 0;
         attempt < 100 && capture.wait_for(0ms) != std::future_status::ready;
         ++attempt)
    {
        bridge.process([&] { return std::optional{expected}; });
        std::this_thread::sleep_for(5ms);
    }
    const auto result = capture.get();
    const auto decoded = OlMod::DedicatedSession::decodeClientSessionCapture({
        reinterpret_cast<const std::uint8_t *>(result.payload.data()),
        result.payload.size(),
    });
    require(result.delivered && result.status == ResponseStatus::Accepted &&
        decoded && *decoded == expected,
        "client bridge returns one game-thread session capture");

    const auto unsupported = submit("127.0.0.1", bridge.port(), {
        .type = MessageType::Booking,
        .requestId = 92,
    });
    require(unsupported.delivered &&
        unsupported.status == ResponseStatus::UnsupportedMessage,
        "client bridge rejects non-capture messages");
    bridge.stop();

    require(bridge.start(0, 30ms), "client bridge restarts cleanly");
    const auto timedOut = submit("127.0.0.1", bridge.port(), {
        .type = MessageType::CaptureLoadout,
        .requestId = 93,
    }, 200);
    require(timedOut.delivered && timedOut.status == ResponseStatus::Rejected,
        "client bridge bounds a capture that the game thread does not service");
    bridge.stop();
}
