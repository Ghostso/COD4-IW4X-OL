#pragma once

#include "../shared/DedicatedControl.hpp"
#include "../shared/DedicatedSession.hpp"

#include <chrono>
#include <functional>
#include <memory>
#include <string>
#include <string_view>

namespace OlMod
{
    class ClientSessionBridge
    {
    public:
        using Capture = std::function<
            std::optional<DedicatedSession::ClientSessionCapture>()>;
        // Runs a named diagnostic in this process. Returns a short status for the caller;
        // the diagnostic's OUTPUT goes to the log or a CSV, not back over the wire.
        using Diagnostic = std::function<std::string(std::string_view name)>;

        void setDiagnostic(Diagnostic diagnostic);

        ClientSessionBridge();
        ~ClientSessionBridge();
        ClientSessionBridge(const ClientSessionBridge &) = delete;
        ClientSessionBridge &operator=(const ClientSessionBridge &) = delete;

        bool start(
            std::uint16_t port,
            std::chrono::milliseconds requestTimeout =
                std::chrono::milliseconds(1500));
        void stop();
        void process(const Capture &capture);
        [[nodiscard]] bool running() const;
        [[nodiscard]] std::uint16_t port() const;

    private:
        struct State;
        std::unique_ptr<State> state_;
    };
}
