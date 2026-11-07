#include "Storage2Service.hpp"

#include "ByteBuffer.hpp"
#include "Crypto.hpp"

#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <Windows.h>

#include <algorithm>
#include <array>
#include <atomic>
#include <charconv>
#include <chrono>
#include <fstream>
#include <iterator>
#include <limits>

namespace AlwaysofflineRe
{
    void log(std::string_view message);
}

namespace
{
    constexpr std::uint32_t MissingFileError = 1000;
    constexpr std::size_t MaximumUserFileSize = 16 * 1024 * 1024;
    std::atomic_uint64_t TemporaryFileSequence{};

    void reportStorageError(const std::string_view message);

    std::uint64_t fileId(const std::string_view name)
    {
        std::uint32_t result = 0x811C9DC5;
        for (const unsigned char character : name)
        {
            result ^= character;
            result *= 0x01000193;
        }
        return result;
    }

    std::uint32_t unixTime(const std::filesystem::file_time_type value)
    {
        const auto systemTime = std::chrono::time_point_cast<std::chrono::system_clock::duration>(
            value - std::filesystem::file_time_type::clock::now() + std::chrono::system_clock::now());
        const auto seconds = std::chrono::duration_cast<std::chrono::seconds>(
            systemTime.time_since_epoch()).count();
        if (seconds <= 0)
            return 0;
        return static_cast<std::uint32_t>(std::min<std::int64_t>(
            seconds, (std::numeric_limits<std::uint32_t>::max)()));
    }

    std::vector<std::uint8_t> readFile(const std::filesystem::path &path)
    {
        std::ifstream stream(path, std::ios::binary);
        if (!stream)
            return {};
        return std::vector<std::uint8_t>(
            std::istreambuf_iterator<char>(stream),
            std::istreambuf_iterator<char>());
    }

    bool isHorizontalSpace(const char value)
    {
        return value == ' ' || value == '\t';
    }

    std::vector<std::uint8_t> makeOfflinePlaylist(
        const std::span<const std::uint8_t> data)
    {
        constexpr std::string_view RuleName = "rule";
        constexpr std::string_view MinimumPlayersKey = "1011";

        if (data.empty())
            return {};

        const auto text = std::string_view(
            reinterpret_cast<const char *>(data.data()), data.size());
        std::string output;
        output.reserve(text.size());
        auto offset = std::size_t{};
        while (offset < text.size())
        {
            const auto newline = text.find('\n', offset);
            const auto next = newline == std::string_view::npos ? text.size() : newline + 1;
            auto lineEnd = newline == std::string_view::npos ? text.size() : newline;
            if (lineEnd > offset && text[lineEnd - 1] == '\r')
                --lineEnd;
            const auto line = text.substr(offset, lineEnd - offset);

            auto cursor = std::size_t{};
            while (cursor < line.size() && isHorizontalSpace(line[cursor]))
                ++cursor;
            if (line.substr(cursor).starts_with(RuleName))
            {
                cursor += RuleName.size();
                if (cursor < line.size() && isHorizontalSpace(line[cursor]))
                {
                    while (cursor < line.size() && isHorizontalSpace(line[cursor]))
                        ++cursor;
                    if (line.substr(cursor).starts_with(MinimumPlayersKey))
                    {
                        cursor += MinimumPlayersKey.size();
                        if (cursor < line.size() && isHorizontalSpace(line[cursor]))
                        {
                            while (cursor < line.size() && isHorizontalSpace(line[cursor]))
                                ++cursor;
                            const auto valueBegin = cursor;
                            while (cursor < line.size() && line[cursor] >= '0' && line[cursor] <= '9')
                                ++cursor;

                            std::uint32_t minimumPlayers{};
                            const auto parsed = std::from_chars(
                                line.data() + valueBegin,
                                line.data() + cursor,
                                minimumPlayers);
                            if (parsed.ec == std::errc{} && parsed.ptr == line.data() + cursor &&
                                minimumPlayers > 1)
                            {
                                output.append(text.substr(offset, valueBegin));
                                output.push_back('1');
                                output.append(text.substr(offset + cursor, next - offset - cursor));
                                offset = next;
                                continue;
                            }
                        }
                    }
                }
            }

            output.append(text.substr(offset, next - offset));
            offset = next;
        }
        return std::vector<std::uint8_t>(output.begin(), output.end());
    }

    std::vector<std::uint8_t> serializeContextualFileInfo(
        const std::string &name,
        const std::uint32_t modifiedTime,
        const std::span<const std::uint8_t> data)
    {
        AlwaysofflineRe::Demonware::ByteBuffer output;
        output.writeU32(static_cast<std::uint32_t>(data.size()));
        output.writeU64(fileId(name));
        output.writeU32(modifiedTime);
        output.writeU32(modifiedTime);
        output.writeBool(false);
        output.writeU64(0);
        output.writeString(name);
        const auto checksum = AlwaysofflineRe::Demonware::md5(data);
        output.writeString(std::string_view(
            reinterpret_cast<const char *>(checksum.data()), checksum.size()));
        return output.data();
    }

    std::string userIdDirectory(const std::uint64_t userId)
    {
        std::array<char, 16> buffer{};
        const auto result = std::to_chars(buffer.data(), buffer.data() + buffer.size(), userId, 16);
        if (result.ec != std::errc{})
            return {};
        std::string value(buffer.data(), result.ptr);
        std::transform(value.begin(), value.end(), value.begin(), [](const unsigned char character)
        {
            return character >= 'a' && character <= 'f'
                ? static_cast<char>(character - 'a' + 'A')
                : static_cast<char>(character);
        });
        return value;
    }

}

namespace AlwaysofflineRe::Demonware
{
    Storage2Service::Storage2Service(AuthSession &session, std::filesystem::path assetRoot)
        : session_(session), assetRoot_(std::move(assetRoot))
    {
    }

    void Storage2Service::registerTasks(ServiceRegistry &registry)
    {
        registry.registerTask(0x0A, 10, "bdStorage::uploadFile", [this](const auto &request)
        {
            return uploadFile(request);
        });
        registry.registerTask(0x0A, 12, "bdStorage::getFile", [this](const auto &request)
        {
            return getFile(request);
        });
        registry.registerTask(0x0A, 20, "Storage2::listAllPublisherFiles", [this](const auto &request)
        {
            return listAllPublisherFiles(request);
        });
        registry.registerTask(0x0A, 21, "Storage2::getPublisherFile", [this](const auto &request)
        {
            return getPublisherFile(request);
        });
    }

    ServiceResponse Storage2Service::getFile(const ServiceRequest &request) const
    {
        ByteBuffer input(request.payload);
        std::string game;
        std::string name;
        std::uint64_t owner{};
        std::string platform;
        if (!input.readString(game) || !input.readString(name) || !input.readU64(owner) ||
            !input.readString(platform) || !input.valid())
        {
            return ServiceResponse{ .error = MissingFileError, .task = request.task };
        }

        const auto data = loadUserFile(owner, name);
        if (!data)
            return ServiceResponse{ .error = MissingFileError, .task = request.task };

        AlwaysofflineRe::log(
            "STORAGE2 getFile name=" + name + " owner=" +
            std::to_string(owner) + " bytes=" + std::to_string(data->size()));

        ByteBuffer object;
        object.writeBlob(*data);
        return ServiceResponse{ .task = request.task, .objects = { object.data() } };
    }

    ServiceResponse Storage2Service::uploadFile(const ServiceRequest &request) const
    {
        ByteBuffer input(request.payload);
        std::string context;
        std::string name;
        bool visibility{};
        std::vector<std::uint8_t> data;
        std::uint64_t owner{};
        std::string platform;
        std::uint32_t flags{};
        if (!input.readString(context) || !input.readString(name) ||
            !input.readBool(visibility) || !input.readBlob(data) ||
            !input.readU64(owner) || !input.readString(platform) ||
            !input.readU32(flags) || !input.valid() ||
            !(input.empty() || (input.remainingSize() == 1 && input.remaining().front() == 0)) ||
            data.size() > MaximumUserFileSize)
        {
            reportStorageError("rejected malformed uploadFile request");
            return ServiceResponse{ .error = MissingFileError, .task = request.task };
        }

        const auto identity = session_.snapshot();
        if (owner == 0)
            owner = identity.userId;
        if (identity.userId == 0 || owner != identity.userId)
        {
            reportStorageError("rejected uploadFile request for a non-authenticated owner");
            return ServiceResponse{ .error = MissingFileError, .task = request.task };
        }
        if (!saveUserFile(owner, name, data))
            return ServiceResponse{ .error = MissingFileError, .task = request.task };
        AlwaysofflineRe::log(
            "STORAGE2 uploadFile name=" + name + " owner=" +
            std::to_string(owner) + " bytes=" + std::to_string(data.size()));
        return ServiceResponse{ .task = request.task };
    }

    ServiceResponse Storage2Service::listAllPublisherFiles(const ServiceRequest &request) const
    {
        ByteBuffer input(request.payload);
        std::string context;
        std::uint32_t startDate{};
        std::uint16_t maximumResults{};
        std::uint16_t offset{};
        std::string filter;
        if (!input.readString(context) || !input.readU32(startDate) ||
            !input.readU16(maximumResults) || !input.readU16(offset) ||
            !input.readString(filter) || !input.valid())
        {
            return ServiceResponse{ .error = MissingFileError, .task = request.task };
        }

        ServiceResponse response{ .task = request.task };
        for (const auto &file : listPublisherFiles())
        {
            if (file.modifiedTime < startDate || (!filter.empty() && file.name != filter))
                continue;
            if (offset != 0)
            {
                --offset;
                continue;
            }
            if (response.objects.size() == maximumResults)
                break;
            response.objects.push_back(serializeContextualFileInfo(file.name, file.modifiedTime, file.data));
        }
        return response;
    }

    ServiceResponse Storage2Service::getPublisherFile(const ServiceRequest &request) const
    {
        ByteBuffer input(request.payload);
        std::string context;
        std::string name;
        if (!input.readString(context) || !input.readString(name) || !input.valid())
            return ServiceResponse{ .error = MissingFileError, .task = request.task };

        const auto file = loadPublisherFile(name);
        if (!file)
            return ServiceResponse{ .error = MissingFileError, .task = request.task };

        auto payload = file->data;
        encodePublisherFile(name, payload);

        ByteBuffer object;
        object.writeBlob(payload);
        return ServiceResponse{ .task = request.task, .objects = { object.data() } };
    }

    // configs_s.info IS ENCRYPTED ON THIS BUILD; every other publisher file is plaintext.
    //
    // Serving it as plaintext does not fail visibly and that is the trap: the client
    // DECRYPTS this one on receipt, so plaintext decrypts to garbage, the parse yields
    // nothing, and the config store ends up empty WHILE STILL FLAGGED LOADED. The client
    // then runs on happily and dies much later in atof(NULL) on a missing config key,
    // with nothing connecting the crash to this reply. Symptom seen here on 2026-08-28:
    // the lobby handshake and twenty service calls all succeed, and out.exe then
    // disappears with a 254 MB dump and not one error line anywhere.
    //
    // Established in the C# reference (LobbyServer/Services/Storage.cs) from a dump scan,
    // not assumed: the content of every publisher file served is resident in client
    // memory afterwards EXCEPT configs_s, which is alone in being absent.
    //
    // The cipher is content-independent, deterministic and position-keyed, so encrypting
    // is a plain XOR against a captured keystream of at least the plaintext's length.
    void Storage2Service::encodePublisherFile(
        const std::string &name,
        std::vector<std::uint8_t> &payload) const
    {
        if (_stricmp(name.c_str(), "configs_s.info") != 0)
            return;

        // readFile returns an empty vector when the file is missing or unreadable.
        const auto keystream = readFile(
            assetRoot_ / std::to_string(session_.snapshot().titleId) /
                "Keystreams" / "configs_s.keystream");
        if (keystream.size() < payload.size())
        {
            // Loudly, because the alternative is a silent crash minutes later that looks
            // like anything but a storage problem.
            AlwaysofflineRe::log(
                "STORAGE2 WARNING: '" + name + "' needs a keystream of at least " +
                std::to_string(payload.size()) + " bytes but got " +
                std::to_string(keystream.size()) +
                ". Serving PLAINTEXT - the client will discard it and crash later.");
            return;
        }

        for (std::size_t index = 0; index < payload.size(); ++index)
            payload[index] ^= keystream[index];

        AlwaysofflineRe::log(
            "STORAGE2 encrypted '" + name + "' (" +
            std::to_string(payload.size()) + " bytes)");
    }

    std::filesystem::path Storage2Service::serverDirectory() const
    {
        return assetRoot_ / std::to_string(session_.snapshot().titleId) / "Server";
    }

    std::optional<std::vector<std::uint8_t>> Storage2Service::loadUserFile(
        const std::uint64_t owner,
        const std::string &name) const
    {
        if (name.empty() || std::filesystem::path(name).filename().string() != name)
            return std::nullopt;
        const auto ownerDirectory = userIdDirectory(owner);
        if (ownerDirectory.empty())
            return std::nullopt;

        const auto path = assetRoot_ / std::to_string(session_.snapshot().titleId) / ownerDirectory / name;
        std::error_code error;
        if (!std::filesystem::is_regular_file(path, error) || error)
            return std::nullopt;
        return readFile(path);
    }

    bool Storage2Service::saveUserFile(
        const std::uint64_t owner,
        const std::string &name,
        const std::span<const std::uint8_t> data) const
    {
        if (name.empty() || std::filesystem::path(name).filename().string() != name)
        {
            reportStorageError("rejected unsafe uploadFile filename");
            return false;
        }
        const auto ownerDirectory = userIdDirectory(owner);
        if (ownerDirectory.empty())
        {
            reportStorageError("could not encode uploadFile owner directory");
            return false;
        }

        const auto path = assetRoot_ / std::to_string(session_.snapshot().titleId) /
            ownerDirectory / name;
        std::error_code error;
        std::filesystem::create_directories(path.parent_path(), error);
        if (error)
        {
            reportStorageError("could not create uploadFile owner directory: " + error.message());
            return false;
        }

        auto temporary = path;
        temporary += L".writing." + std::to_wstring(GetCurrentProcessId()) + L"." +
            std::to_wstring(TemporaryFileSequence.fetch_add(1, std::memory_order_relaxed));
        {
            std::ofstream stream(temporary, std::ios::binary | std::ios::trunc);
            if (!stream)
            {
                reportStorageError("could not create uploadFile temporary file");
                return false;
            }
            stream.write(reinterpret_cast<const char *>(data.data()),
                static_cast<std::streamsize>(data.size()));
            if (!stream)
            {
                stream.close();
                std::filesystem::remove(temporary, error);
                reportStorageError("could not write uploadFile temporary file");
                return false;
            }
        }
        if (!MoveFileExW(temporary.c_str(), path.c_str(),
            MOVEFILE_REPLACE_EXISTING | MOVEFILE_WRITE_THROUGH))
        {
            const auto nativeError = GetLastError();
            std::filesystem::remove(temporary, error);
            reportStorageError("could not commit uploadFile: win32=" + std::to_string(nativeError));
            return false;
        }
        return true;
    }

    std::optional<Storage2Service::PublisherFile> Storage2Service::loadPublisherFile(std::string name) const
    {
        if (name == "mp_playlists_shipRetail.info")
            name = "mp_playlists_shipRetail_release.info";
        if (name.empty() || std::filesystem::path(name).filename().string() != name)
            return std::nullopt;

        const auto path = serverDirectory() / name;
        std::error_code error;
        if (!std::filesystem::is_regular_file(path, error) || error)
            return std::nullopt;
        auto data = readFile(path);
        if (session_.snapshot().titleId == 1004 &&
            name == "mp_playlists_shipRetail_release.info")
        {
            data = makeOfflinePlaylist(data);
        }
        return PublisherFile{
            .name = std::move(name),
            .path = path,
            .modifiedTime = unixTime(std::filesystem::last_write_time(path, error)),
            .data = std::move(data),
        };
    }

    std::vector<Storage2Service::PublisherFile> Storage2Service::listPublisherFiles() const
    {
        std::vector<PublisherFile> result;
        std::error_code error;
        for (std::filesystem::directory_iterator iterator(serverDirectory(), error), end;
             !error && iterator != end; iterator.increment(error))
        {
            if (!iterator->is_regular_file(error) || error)
                continue;
            const auto name = iterator->path().filename().string();
            if (const auto file = loadPublisherFile(name))
                result.push_back(*file);
        }
        std::sort(result.begin(), result.end(), [](const PublisherFile &left, const PublisherFile &right)
        {
            return left.name < right.name;
        });
        return result;
    }
}

namespace
{
    void reportStorageError(const std::string_view message)
    {
        AlwaysofflineRe::log(std::string("STORAGE2 ") + std::string(message));
    }
}
