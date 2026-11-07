#include "ClientSessionBridge.hpp"

#include <condition_variable>
#include <deque>
#include <mutex>
#include <utility>

namespace OlMod
{
    struct ClientSessionBridge::State
    {
        struct Pending
        {
            std::mutex mutex;
            std::condition_variable ready;
            bool completed{};
            bool canceled{};
            DedicatedControl::Response response;
        };

        DedicatedControl::Server server;
        std::mutex queueMutex;
        std::deque<std::shared_ptr<Pending>> queue;
        std::chrono::milliseconds requestTimeout{1500};
        ClientSessionBridge::Diagnostic diagnostic;
    };

    ClientSessionBridge::ClientSessionBridge()
        : state_(std::make_unique<State>())
    {
    }

    ClientSessionBridge::~ClientSessionBridge()
    {
        stop();
    }

    void ClientSessionBridge::setDiagnostic(Diagnostic diagnostic)
    {
        if (state_)
            state_->diagnostic = std::move(diagnostic);
    }

    bool ClientSessionBridge::start(
        const std::uint16_t port,
        const std::chrono::milliseconds requestTimeout)
    {
        if (!state_ || requestTimeout.count() <= 0)
            return false;
        stop();
        state_->requestTimeout = requestTimeout;
        return state_->server.start(port, [state = state_.get()](
            const DedicatedControl::Message &message) {
            if (message.type == DedicatedControl::MessageType::RunDiagnostic)
            {
                // ANSWERED ON THIS THREAD ON PURPOSE, because the handler only starts the
                // work -- it must not join the game-thread queue below, which exists so a
                // CAPTURE can be served in step with the game.
                if (!state->diagnostic)
                {
                    return DedicatedControl::Response{
                        .status = DedicatedControl::ResponseStatus::UnsupportedMessage,
                    };
                }
                const std::string name(
                    message.payload.begin(), message.payload.end());
                const auto status = state->diagnostic(name);
                return DedicatedControl::Response{
                    .status = DedicatedControl::ResponseStatus::Accepted,
                    .payload = status,
                };
            }
            if (message.type != DedicatedControl::MessageType::CaptureLoadout)
            {
                return DedicatedControl::Response{
                    .status = DedicatedControl::ResponseStatus::UnsupportedMessage,
                };
            }
            if (!message.payload.empty())
            {
                return DedicatedControl::Response{
                    .status = DedicatedControl::ResponseStatus::InvalidMessage,
                };
            }

            auto pending = std::make_shared<State::Pending>();
            {
                const std::lock_guard lock(state->queueMutex);
                if (state->queue.size() >= 4)
                {
                    return DedicatedControl::Response{
                        .status = DedicatedControl::ResponseStatus::Rejected,
                    };
                }
                state->queue.push_back(pending);
            }

            std::unique_lock lock(pending->mutex);
            if (!pending->ready.wait_for(lock, state->requestTimeout, [&] {
                    return pending->completed;
                }))
            {
                pending->canceled = true;
                return DedicatedControl::Response{
                    .status = DedicatedControl::ResponseStatus::Rejected,
                };
            }
            return std::move(pending->response);
        });
    }

    void ClientSessionBridge::stop()
    {
        if (!state_)
            return;
        std::deque<std::shared_ptr<State::Pending>> pending;
        {
            const std::lock_guard lock(state_->queueMutex);
            pending.swap(state_->queue);
        }
        for (const auto &request : pending)
        {
            const std::lock_guard lock(request->mutex);
            request->completed = true;
            request->response = {
                .status = DedicatedControl::ResponseStatus::Rejected,
            };
            request->ready.notify_one();
        }
        state_->server.stop();
    }

    void ClientSessionBridge::process(const Capture &capture)
    {
        if (!state_ || !capture)
            return;
        std::deque<std::shared_ptr<State::Pending>> pending;
        {
            const std::lock_guard lock(state_->queueMutex);
            pending.swap(state_->queue);
        }
        const auto captured = pending.empty() ? std::nullopt : capture();
        const auto payload = captured
            ? DedicatedSession::encode(*captured)
            : std::vector<std::uint8_t>{};
        for (const auto &request : pending)
        {
            const std::lock_guard lock(request->mutex);
            if (request->canceled)
                continue;
            request->response = payload.empty()
                ? DedicatedControl::Response{
                    .status = DedicatedControl::ResponseStatus::Rejected,
                }
                : DedicatedControl::Response{
                    .status = DedicatedControl::ResponseStatus::Accepted,
                    .payload = std::string(
                        reinterpret_cast<const char *>(payload.data()),
                        payload.size()),
                };
            request->completed = true;
            request->ready.notify_one();
        }
    }

    bool ClientSessionBridge::running() const
    {
        return state_ && state_->server.running();
    }

    std::uint16_t ClientSessionBridge::port() const
    {
        return state_ ? state_->server.port() : 0;
    }
}
