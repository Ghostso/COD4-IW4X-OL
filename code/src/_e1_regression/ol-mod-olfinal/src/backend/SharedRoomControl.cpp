#include "SharedRoomControl.hpp"

#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <Windows.h>

#include <algorithm>
#include <array>
#include <charconv>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <limits>
#include <mutex>
#include <sstream>
#include <chrono>
#include <iomanip>
#include <vector>

namespace
{
    constexpr std::uint8_t SchemaVersion = 2;

    void appendU16(std::vector<std::uint8_t> &output, const std::uint16_t value)
    {
        output.push_back(static_cast<std::uint8_t>(value));
        output.push_back(static_cast<std::uint8_t>(value >> 8));
    }

    void appendU32(std::vector<std::uint8_t> &output, const std::uint32_t value)
    {
        for (std::uint32_t shift{}; shift < 32; shift += 8)
            output.push_back(static_cast<std::uint8_t>(value >> shift));
    }

    std::uint32_t readU32(
        const std::span<const std::uint8_t> input, const std::size_t offset)
    {
        std::uint32_t result{};
        for (std::uint32_t shift{}; shift < 32; shift += 8)
            result |= static_cast<std::uint32_t>(input[offset + shift / 8]) << shift;
        return result;
    }

    void appendU64(std::vector<std::uint8_t> &output, const std::uint64_t value)
    {
        for (std::uint32_t shift{}; shift < 64; shift += 8)
            output.push_back(static_cast<std::uint8_t>(value >> shift));
    }

    std::uint16_t readU16(
        const std::span<const std::uint8_t> input, const std::size_t offset)
    {
        return static_cast<std::uint16_t>(input[offset]) |
            static_cast<std::uint16_t>(input[offset + 1]) << 8;
    }

    std::uint64_t readU64(
        const std::span<const std::uint8_t> input, const std::size_t offset)
    {
        std::uint64_t result{};
        for (std::uint32_t shift{}; shift < 64; shift += 8)
            result |= static_cast<std::uint64_t>(input[offset + shift / 8]) << shift;
        return result;
    }

    std::string toString(const std::vector<std::uint8_t> &bytes)
    {
        return { reinterpret_cast<const char *>(bytes.data()), bytes.size() };
    }

    std::span<const std::uint8_t> bytes(const std::string_view payload)
    {
        return {
            reinterpret_cast<const std::uint8_t *>(payload.data()),
            payload.size(),
        };
    }
}

namespace AlwaysofflineRe::SharedRoomControl
{
    namespace
    {
        std::mutex RoomLogMutex;

        std::filesystem::path executableDirectory()
        {
            std::array<wchar_t, 32768> buffer{};
            const auto size = GetModuleFileNameW(
                nullptr, buffer.data(), static_cast<DWORD>(buffer.size()));
            return size && size < buffer.size()
                ? std::filesystem::path(buffer.data()).parent_path()
                : std::filesystem::current_path();
        }

        void logRoomEvent(const std::string_view event, const std::uint64_t userId,
            const std::uint16_t bridgePort, const std::size_t memberCount,
            const std::size_t readyCount, const bool accepted)
        {
            // Keep this in the standalone owner so multi-client room failures are
            // observable without parsing the game's unbounded backend log.
            const auto now = std::chrono::system_clock::now();
            const auto milliseconds = std::chrono::duration_cast<
                std::chrono::milliseconds>(now.time_since_epoch()).count() % 1000;
            const auto time = std::chrono::system_clock::to_time_t(now);
            std::tm local{};
            localtime_s(&local, &time);
            std::ostringstream line;
            line << '[' << std::put_time(&local, "%Y-%m-%d %H:%M:%S")
                 << '.' << std::setfill('0') << std::setw(3) << milliseconds
                 << "] [room-owner] " << event
                      << " user=" << userId
                      << " bridge=" << bridgePort
                      << " members=" << memberCount
                      << " ready=" << readyCount
                      << " accepted=" << (accepted ? 1 : 0);
            const auto text = line.str();
            std::lock_guard lock(RoomLogMutex);
            std::cerr << text << '\n';
            std::error_code error;
            const auto path = executableDirectory() /
                "Logs" / "ol-room-owner.log";
            std::filesystem::create_directories(path.parent_path(), error);
            if (error)
                return;
            std::ofstream output(path, std::ios::out | std::ios::app);
            if (output)
                output << text << '\n';
        }
    }

    std::string encode(const ConnectRequest &request)
    {
        if (request.displayName.empty() || request.displayName.size() > 0xFF)
            return {};
        std::vector<std::uint8_t> output{ SchemaVersion };
        appendU64(output, request.userId);
        appendU16(output, request.bridgePort);
        output.push_back(static_cast<std::uint8_t>(request.displayName.size()));
        output.insert(
            output.end(), request.displayName.begin(), request.displayName.end());
        return toString(output);
    }

    std::optional<ConnectRequest> decodeConnect(const std::string_view payload)
    {
        const auto input = bytes(payload);
        if (input.size() < 12 || input[0] != SchemaVersion ||
            input.size() != 12u + input[11])
        {
            return std::nullopt;
        }
        return ConnectRequest{
            .userId = readU64(input, 1),
            .displayName = std::string(payload.substr(12, input[11])),
            .bridgePort = readU16(input, 9),
        };
    }

    std::string encode(const MemberRequest &request)
    {
        std::vector<std::uint8_t> output{ SchemaVersion };
        appendU64(output, request.userId);
        appendU64(output, request.connectionToken);
        return toString(output);
    }

    std::optional<MemberRequest> decodeMember(const std::string_view payload)
    {
        const auto input = bytes(payload);
        if (input.size() != 17 || input[0] != SchemaVersion)
            return std::nullopt;
        return MemberRequest{
            .userId = readU64(input, 1),
            .connectionToken = readU64(input, 9),
        };
    }

    std::string encode(const ReadyRequest &request)
    {
        auto output = encode(MemberRequest{
            .userId = request.userId,
            .connectionToken = request.connectionToken,
        });
        output.push_back(static_cast<char>(request.ready ? 1 : 0));
        return output;
    }

    std::optional<ReadyRequest> decodeReady(const std::string_view payload)
    {
        if (payload.size() != 18 ||
            static_cast<unsigned char>(payload.back()) > 1)
        {
            return std::nullopt;
        }
        const auto member = decodeMember(payload.substr(0, 17));
        return member ? std::optional{ ReadyRequest{
            .userId = member->userId,
            .connectionToken = member->connectionToken,
            .ready = payload.back() != 0,
        } } : std::nullopt;
    }

    std::string encode(const SessionDescriptorRequest &request)
    {
        if (request.descriptor.empty() ||
            request.descriptor.size() > OlMod::DedicatedControl::MaximumPayloadSize - 17)
        {
            return {};
        }
        auto output = encode(MemberRequest{
            .userId = request.userId,
            .connectionToken = request.connectionToken,
        });
        output.append(request.descriptor);
        return output;
    }

    std::optional<SessionDescriptorRequest> decodeSessionDescriptor(
        const std::string_view payload)
    {
        if (payload.size() <= 17)
            return std::nullopt;
        const auto member = decodeMember(payload.substr(0, 17));
        return member ? std::optional{ SessionDescriptorRequest{
            .userId = member->userId,
            .connectionToken = member->connectionToken,
            .descriptor = std::string(payload.substr(17)),
        } } : std::nullopt;
    }

    std::string encode(const FreezeRequest &request)
    {
        std::vector<std::uint8_t> output{ SchemaVersion };
        appendU64(output, request.generation);
        appendU64(output, request.claimant.userId);
        appendU64(output, request.claimant.connectionToken);
        return toString(output);
    }

    std::optional<FreezeRequest> decodeFreeze(const std::string_view payload)
    {
        const auto input = bytes(payload);
        if (input.size() != 25 || input[0] != SchemaVersion)
            return std::nullopt;
        return FreezeRequest{
            .generation = readU64(input, 1),
            .claimant = {
                .userId = readU64(input, 9),
                .connectionToken = readU64(input, 17),
            },
        };
    }

    std::string encodeToken(const std::uint64_t token)
    {
        std::vector<std::uint8_t> output{ SchemaVersion };
        appendU64(output, token);
        return toString(output);
    }

    std::optional<std::uint64_t> decodeToken(const std::string_view payload)
    {
        const auto input = bytes(payload);
        return input.size() == 9 && input[0] == SchemaVersion
            ? std::optional{ readU64(input, 1) }
            : std::nullopt;
    }

    std::string encodeRoster(const FrozenRoomRoster &roster)
    {
        if (!roster.generation || roster.members.empty() ||
            roster.members.size() > 0xFF)
        {
            return {};
        }
        std::vector<std::uint8_t> output{ SchemaVersion };
        appendU64(output, roster.generation);
        appendU64(output, roster.ownerUserId);
        output.push_back(static_cast<std::uint8_t>(roster.members.size()));
        for (const auto &member : roster.members)
        {
            if (member.displayName.empty() || member.displayName.size() > 0xFF)
                return {};
            appendU64(output, member.userId);
            appendU16(output, member.bridgePort);
            appendU32(output, member.bridgeIpv4);
            appendU64(output, member.connectionToken);
            output.push_back(static_cast<std::uint8_t>(member.ready ? 1 : 0));
            output.push_back(static_cast<std::uint8_t>(member.displayName.size()));
            output.insert(
                output.end(), member.displayName.begin(), member.displayName.end());
        }
        return toString(output);
    }

    std::optional<FrozenRoomRoster> decodeRoster(const std::string_view payload)
    {
        const auto input = bytes(payload);
        if (input.size() < 18 || input[0] != SchemaVersion || !input[17])
            return std::nullopt;
        FrozenRoomRoster roster{
            .generation = readU64(input, 1),
            .ownerUserId = readU64(input, 9),
        };
        std::size_t offset = 18;
        for (std::uint32_t index{}; index < input[17]; ++index)
        {
            if (input.size() - offset < 24)
                return std::nullopt;
            const auto nameSize = input[offset + 23];
            if (!nameSize || input[offset + 22] > 1 ||
                input.size() - offset < 24u + nameSize)
            {
                return std::nullopt;
            }
            roster.members.push_back({
                .userId = readU64(input, offset),
                .displayName = std::string(payload.substr(offset + 24, nameSize)),
                .bridgePort = readU16(input, offset + 8),
                .bridgeIpv4 = readU32(input, offset + 10),
                .connectionToken = readU64(input, offset + 14),
                .ready = input[offset + 22] != 0,
            });
            offset += 24 + nameSize;
        }
        return roster.generation && roster.ownerUserId && offset == input.size()
            ? std::optional{ roster }
            : std::nullopt;
    }

    std::uint16_t configuredPort()
    {
        char *configured{};
        std::size_t size{};
        if (_dupenv_s(&configured, &size, "OLMOD_ROOM_OWNER_PORT") != 0 ||
            !configured || !*configured)
        {
            std::free(configured);
            return DefaultPort;
        }
        std::uint32_t value{};
        const auto end = configured + std::char_traits<char>::length(configured);
        const auto parsed = std::from_chars(configured, end, value);
        const auto valid = parsed.ec == std::errc{} && parsed.ptr == end &&
            value && value <= std::numeric_limits<std::uint16_t>::max();
        std::free(configured);
        return valid ? static_cast<std::uint16_t>(value) : DefaultPort;
    }

    OlMod::DedicatedControl::Response Handler::operator()(
        const OlMod::DedicatedControl::Message &message)
    {
        using namespace OlMod::DedicatedControl;
        if (message.type == MessageType::RoomConnect)
        {
            const auto request = decodeConnect(message.payload);
            const auto token = request ? owner_.connect(
                request->userId, request->displayName, request->bridgePort,
                // The address the member connected FROM, not one it named.
                message.peerIpv4)
                : std::nullopt;
            if (request)
            {
                const auto members = owner_.members();
                const auto ready = std::count_if(members.begin(), members.end(),
                    [](const auto &member) { return member.ready; });
                logRoomEvent("connect", request->userId, request->bridgePort,
                    members.size(), static_cast<std::size_t>(ready), token.has_value());
            }
            return token ? Response{
                .status = ResponseStatus::Accepted,
                .payload = encodeToken(*token),
            } : Response{ .status = request
                ? ResponseStatus::Rejected
                : ResponseStatus::InvalidMessage };
        }
        if (message.type == MessageType::RoomDisconnect)
        {
            const auto request = decodeMember(message.payload);
            const auto accepted = request && owner_.disconnect(
                request->userId, request->connectionToken);
            if (request)
            {
                // Keep the room lifecycle observable: a disconnect between
                // ready and booking is otherwise indistinguishable from a
                // stale client-side room state.
                const auto members = owner_.members();
                const auto ready = std::count_if(members.begin(), members.end(),
                    [](const auto &member) { return member.ready; });
                logRoomEvent("disconnect", request->userId, 0, members.size(),
                    static_cast<std::size_t>(ready), accepted);
            }
            return { .status = accepted
                ? ResponseStatus::Accepted
                : request ? ResponseStatus::Rejected
                          : ResponseStatus::InvalidMessage };
        }
        if (message.type == MessageType::RoomSetReady)
        {
            const auto request = decodeReady(message.payload);
            const auto accepted = request && owner_.setReady(
                request->userId, request->connectionToken, request->ready);
            if (request)
            {
                const auto members = owner_.members();
                const auto ready = std::count_if(members.begin(), members.end(),
                    [](const auto &member) { return member.ready; });
                logRoomEvent(request->ready ? "ready" : "unready",
                    request->userId, 0, members.size(),
                    static_cast<std::size_t>(ready), accepted);
            }
            return { .status = accepted
                ? ResponseStatus::Accepted
                : request ? ResponseStatus::Rejected : ResponseStatus::InvalidMessage };
        }
        if (message.type == MessageType::RoomFreeze)
        {
            const auto request = decodeFreeze(message.payload);
            const auto roster = request ? owner_.freeze(
                request->generation,
                request->claimant.userId,
                request->claimant.connectionToken) : std::nullopt;
            const auto members = owner_.members();
            const auto ready = std::count_if(members.begin(), members.end(),
                [](const auto &member) { return member.ready; });
            logRoomEvent("freeze", 0, 0, members.size(),
                static_cast<std::size_t>(ready), roster.has_value());
            return roster ? Response{
                .status = ResponseStatus::Accepted,
                .payload = encodeRoster(*roster),
            } : Response{ .status = request
                ? ResponseStatus::Rejected
                : ResponseStatus::InvalidMessage };
        }
        if (message.type == MessageType::RoomCanonicalizeSession)
        {
            const auto request = decodeSessionDescriptor(message.payload);
            const auto descriptor = request
                ? owner_.canonicalizeSessionDescriptor(
                    request->userId,
                    request->connectionToken,
                    request->descriptor)
                : std::nullopt;
            return descriptor ? Response{
                .status = ResponseStatus::Accepted,
                .payload = *descriptor,
            } : Response{ .status = request
                ? ResponseStatus::Rejected
                : ResponseStatus::InvalidMessage };
        }
        return { .status = ResponseStatus::UnsupportedMessage };
    }
}
