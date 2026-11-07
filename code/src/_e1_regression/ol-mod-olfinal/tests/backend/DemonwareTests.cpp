#include "Demonware/ByteBuffer.hpp"
#include "Demonware/CodolStartupTasks.hpp"
#include "Demonware/ContentUnlock2Service.hpp"
#include "Demonware/Friends2Service.hpp"
#include "Demonware/Auth3Protocol.hpp"
#include "Demonware/Auth3TlsTransport.hpp"
#include "Demonware/Crypto.hpp"
#include "Demonware/LobbyProtocol.hpp"
#include "Demonware/InstantMessageService.hpp"
#include "Demonware/IdentityConfig.hpp"
#include "Demonware/MatchmakingService.hpp"
#include "Demonware/MarketplaceService.hpp"
#include "Demonware/Profiles2Service.hpp"
#include "Demonware/RecoveredCatalog.hpp"
#include "Demonware/ServiceRegistry.hpp"
#include "Demonware/Storage2Service.hpp"
#include "Demonware/TencentService.hpp"
#include "Demonware/TitleUtilitiesService.hpp"
#include "Demonware/Unknown0BService.hpp"

#include <algorithm>
#include <array>
#include <chrono>
#include <ctime>
#include <cstdint>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <limits>
#include <span>
#include <stdexcept>
#include <string_view>
#include <utility>
#include <vector>

#pragma warning(push, 0)
#include <nlohmann/json.hpp>
#include <openssl/bio.h>
#include <openssl/evp.h>
#include <openssl/ssl.h>
#include <openssl/x509.h>
#pragma warning(pop)

namespace
{
    std::vector<std::uint8_t> fromHex(std::string_view value);

    void requireDw(const bool condition, const std::string_view message)
    {
        if (!condition)
        {
            std::cerr << "FAILED: " << message << '\n';
            std::exit(1);
        }
    }

    void testByteBuffer()
    {
        AlwaysofflineRe::Demonware::ByteBuffer output;
        output.writeU8(0xCB);
        output.writeU32(0x12345678);
        output.writeU64(0x0102030405060708ULL);
        output.writeI64(-2);
        const std::array<std::uint32_t, 4> array{ 0, 1, 2, 0x105 };
        output.writeU32Array(array);
        output.writeString("Alwaysoffline");
        const std::array<std::uint8_t, 3> blob{ 1, 2, 3 };
        output.writeBlob(blob);

        AlwaysofflineRe::Demonware::ByteBuffer input(output.data());
        std::uint8_t byte{};
        std::uint32_t dword{};
        std::uint64_t qword{};
        std::int64_t signedQword{};
        std::vector<std::uint32_t> decodedArray;
        std::string text;
        std::vector<std::uint8_t> decodedBlob;
        requireDw(input.readU8(byte) && byte == 0xCB, "typed byte round trip");
        requireDw(input.readU32(dword) && dword == 0x12345678, "typed uint32 round trip");
        requireDw(input.readU64(qword) && qword == 0x0102030405060708ULL, "typed uint64 round trip");
        requireDw(input.readI64(signedQword) && signedQword == -2, "typed int64 round trip");
        requireDw(input.readU32Array(decodedArray) &&
            decodedArray == std::vector<std::uint32_t>(array.begin(), array.end()),
            "typed uint32 array round trip");
        requireDw(input.readString(text) && text == "Alwaysoffline", "typed string round trip");
        requireDw(input.readBlob(decodedBlob) && decodedBlob == std::vector<std::uint8_t>(blob.begin(), blob.end()),
            "typed blob round trip");
        requireDw(input.empty() && input.valid(), "buffer consumed cleanly");
    }

    void testCapturedRequestParsing()
    {
        const std::array<std::uint8_t, 9> getInventory{
            0x50, 0x03, 0xCB, 0x10, 0x00, 0x06, 0x20, 0x4E, 0x00,
        };
        const auto request = AlwaysofflineRe::Demonware::parseServiceRequest(getInventory);
        requireDw(request.has_value(), "captured protocol 3 request parses");
        requireDw(request->service == 0x50 && request->task == 0xCB, "service and task are untyped prefix bytes");

        AlwaysofflineRe::Demonware::ByteBuffer payload(request->payload);
        std::string context;
        std::uint16_t maximumResults{};
        requireDw(payload.readString(context) && context.empty() && payload.readU16(maximumResults) &&
            maximumResults == 20000, "captured CODOL inventory payload parses");
    }

    void testServiceEnvelope()
    {
        AlwaysofflineRe::Demonware::ServiceRegistry registry;
        registry.registerTask(0x50, 0xCB, "Marketplace::getInventory", [](const auto &request)
        {
            return AlwaysofflineRe::Demonware::ServiceResponse{
                .transaction = 7,
                .error = 0,
                .task = request.task,
            };
        });

        AlwaysofflineRe::Demonware::ServiceRequest request{ .service = 0x50, .protocolVersion = 3, .task = 0xCB };
        const auto response = registry.dispatch(request);
        requireDw(response.has_value(), "registered service task dispatches");
        requireDw(!registry.dispatch({ .service = 0x15, .protocolVersion = 3, .task = 1 }).has_value(),
            "unknown service task stays explicit");
        requireDw(registry.taskName(0x50, 0xCB) == "Marketplace::getInventory", "task name retained");

        AlwaysofflineRe::Demonware::ByteBuffer envelope(response->serialize());
        std::uint64_t transaction{};
        std::uint32_t error{};
        std::uint8_t task{};
        std::uint32_t objectCount{};
        requireDw(envelope.readU64(transaction) && transaction == 7, "reply transaction");
        requireDw(envelope.readU32(error) && error == 0, "reply error");
        requireDw(envelope.readU8(task) && task == 0xCB, "reply task");
        requireDw(envelope.readU32(objectCount) && objectCount == 0, "reply object count");
        requireDw(envelope.empty(), "reply envelope consumed");
    }

    void testCodolStartupTasks()
    {
        using namespace AlwaysofflineRe::Demonware;

        ServiceRegistry registry;
        registerCodolStartupTasks(registry);

        constexpr std::array<std::pair<std::uint8_t, std::uint8_t>, 22> EmptyTasks{
            std::pair{ std::uint8_t{ 0x47 }, std::uint8_t{ 0x04 } },
            std::pair{ std::uint8_t{ 0x47 }, std::uint8_t{ 0x0A } },
            std::pair{ std::uint8_t{ 0x50 }, std::uint8_t{ 0x46 } },
            std::pair{ std::uint8_t{ 0x47 }, std::uint8_t{ 0x03 } },
            std::pair{ std::uint8_t{ 0x06 }, std::uint8_t{ 0x05 } },
            std::pair{ std::uint8_t{ 0x50 }, std::uint8_t{ 0x6B } },
            std::pair{ std::uint8_t{ 0x50 }, std::uint8_t{ 0xE6 } },
            std::pair{ std::uint8_t{ 0x5D }, std::uint8_t{ 0x01 } },
            std::pair{ std::uint8_t{ 0x09 }, std::uint8_t{ 0x10 } },
            std::pair{ std::uint8_t{ 0x44 }, std::uint8_t{ 0x01 } },
            std::pair{ std::uint8_t{ 0x09 }, std::uint8_t{ 0x0E } },
            std::pair{ std::uint8_t{ 0x03 }, std::uint8_t{ 0x35 } },
            std::pair{ std::uint8_t{ 0x1D }, std::uint8_t{ 0x0A } },
            std::pair{ std::uint8_t{ 0x50 }, std::uint8_t{ 0xAD } },
            std::pair{ std::uint8_t{ 0x50 }, std::uint8_t{ 0xAE } },
            std::pair{ std::uint8_t{ 0x66 }, std::uint8_t{ 0x01 } },
            std::pair{ std::uint8_t{ 0x09 }, std::uint8_t{ 0x09 } },
            std::pair{ std::uint8_t{ 0x09 }, std::uint8_t{ 0x0C } },
            std::pair{ std::uint8_t{ 0x47 }, std::uint8_t{ 0x07 } },
            std::pair{ std::uint8_t{ 0x03 }, std::uint8_t{ 0x2E } },
            std::pair{ std::uint8_t{ 0x03 }, std::uint8_t{ 0x30 } },
            std::pair{ std::uint8_t{ 0x47 }, std::uint8_t{ 0x0F } },
        };

        std::uint8_t transactionCounter = 1;
        for (const auto [service, task] : EmptyTasks)
        {
            const auto response = registry.dispatch(ServiceRequest{
                .service = service,
                .protocolVersion = 3,
                .task = task,
            });
            requireDw(response && response->transaction == (OriginalTransactionPrefix | transactionCounter) &&
                response->error == 0 && response->task == task && response->objects.empty(),
                "captured startup request returns an empty success envelope");
            requireDw(!registry.taskName(service, task).empty(),
                "captured empty startup task registration is explicit");
            ++transactionCounter;
        }

        requireDw(registry.taskName(0x5D, 1) == "Unknown93::task1",
            "captured startup task registration is explicit");

        const auto response = registry.dispatch(ServiceRequest{
            .service = 0x5D,
            .protocolVersion = 3,
            .task = 1,
        });
        ByteBuffer envelope(response->serialize());
        std::uint64_t transaction{};
        std::uint32_t error{};
        std::uint8_t task{};
        std::uint32_t objectCount{};
        requireDw(envelope.readU64(transaction) && transaction == (OriginalTransactionPrefix | 23) &&
            envelope.readU32(error) && error == 0 &&
            envelope.readU8(task) && task == 1 &&
            envelope.readU32(objectCount) && objectCount == 0 && envelope.empty(),
            "captured 0x5D/1 envelope matches the recovered field order");
    }

    void testTitleUtilitiesService()
    {
        using namespace AlwaysofflineRe::Demonware;

        AuthSession session;
        ServiceRegistry registry;
        TitleUtilitiesService service(session);
        service.registerTasks(registry);

        const auto before = static_cast<std::uint32_t>(std::time(nullptr));
        const auto response = registry.dispatch(ServiceRequest{
            .service = 0x0C,
            .protocolVersion = 3,
            .task = 6,
        });
        const auto after = static_cast<std::uint32_t>(std::time(nullptr));
        requireDw(response && response->transaction == (OriginalTransactionPrefix | 1) &&
            response->error == 0 && response->task == 6 && response->objects.size() == 1,
            "TitleUtilities getServerTime returns one timestamp object");
        requireDw(registry.taskName(0x0C, 6) == "TitleUtilities2::getServerTime",
            "TitleUtilities task registration is explicit");

        ByteBuffer object(response->objects.front());
        std::uint32_t serverTime{};
        requireDw(object.readU32(serverTime) && object.empty() && object.valid() &&
            serverTime >= before && serverTime <= after,
            "TitleUtilities timestamp is a typed current Unix uint32");

        AuthIdentity identity;
        identity.userId = 0x1100001DEADC0DEULL;
        identity.username = "Alwaysoffline";
        session.update(identity);
        ByteBuffer task9Payload;
        task9Payload.writeU64(identity.userId);
        const auto task9 = registry.dispatch(ServiceRequest{
            .service = 0x0C,
            .protocolVersion = 3,
            .task = 9,
            .payload = task9Payload.data(),
        });
        requireDw(task9 && task9->error == 0 && task9->task == 9 && task9->objects.size() == 1,
            "TitleUtilities2 task 9 returns one recovered identity object");
        requireDw(registry.taskName(0x0C, 9) == "TitleUtilities2::task9",
            "unnamed TitleUtilities2 task 9 remains explicitly labeled");

        ByteBuffer identityObject(task9->objects.front());
        std::uint64_t returnedUserId{};
        std::string encodedUsername;
        requireDw(identityObject.readU64(returnedUserId) && returnedUserId == identity.userId &&
            identityObject.readString(encodedUsername) && encodedUsername == "QWx3YXlzb2ZmbGluZQ==" &&
            identityObject.empty() && identityObject.valid(),
            "TitleUtilities2 task 9 matches the captured user ID and Base64 username object");
    }

    void testProfiles2Service()
    {
        using namespace AlwaysofflineRe::Demonware;

        AuthSession session;
        ServiceRegistry registry;
        const auto fixtures = std::filesystem::path(__FILE__).parent_path() / "Fixtures";
        Profiles2Service service(session, fixtures);
        service.registerTasks(registry);

        ByteBuffer publicPayload;
        publicPayload.writeU64(session.snapshot().userId);
        const std::array<std::uint8_t, 8> padding{};
        publicPayload.writeRaw(padding);
        const auto publicInfo = registry.dispatch(ServiceRequest{
            .service = 0x08,
            .protocolVersion = 3,
            .task = 1,
            .payload = publicPayload.data(),
        });
        requireDw(publicInfo && publicInfo->transaction == (OriginalTransactionPrefix | 1) &&
            publicInfo->error == 0 && publicInfo->task == 1 && publicInfo->objects.size() == 1,
            "Profiles2 public info returns the archived local profile");

        ByteBuffer publicObject(publicInfo->objects.front());
        std::uint64_t publicUserId{};
        requireDw(publicObject.readU64(publicUserId) && publicUserId == session.snapshot().userId,
            "Profiles2 public info starts with the requested typed user ID");
        const std::string archivedProfile(
            reinterpret_cast<const char *>(publicObject.remaining().data()), publicObject.remaining().size());
        requireDw(archivedProfile == "profile-data\n",
            "Profiles2 public info preserves the archived profile bytes verbatim");

        const auto response = registry.dispatch(ServiceRequest{
            .service = 0x08,
            .protocolVersion = 3,
            .task = 2,
        });
        requireDw(response && response->envelopeType == 1 &&
            response->transaction == (OriginalTransactionPrefix | 2) &&
            response->error == 0 && response->task == 2 && response->objects.empty(),
            "Profiles2 private info returns the captured empty success envelope");
        requireDw(registry.taskName(0x08, 2) == "Profiles2::getPrivateInfo",
            "Profiles2 private info registration is explicit");

        ByteBuffer envelope(response->serialize());
        std::uint64_t transaction{};
        std::uint32_t error{};
        std::uint8_t task{};
        std::uint32_t objectCount{};
        requireDw(envelope.readU64(transaction) && transaction == (OriginalTransactionPrefix | 2) &&
            envelope.readU32(error) && error == 0 &&
            envelope.readU8(task) && task == 2 &&
            envelope.readU32(objectCount) && objectCount == 0 &&
            envelope.empty() && envelope.valid(),
            "Profiles2 empty-success payload matches the recovered typed field order");

        const auto sandbox = std::filesystem::temp_directory_path() / "AlwaysofflineReProfiles2Tests";
        std::error_code filesystemError;
        std::filesystem::remove_all(sandbox, filesystemError);
        ServiceRegistry persistentRegistry;
        Profiles2Service persistentService(session, sandbox);
        persistentService.registerTasks(persistentRegistry);

        ByteBuffer updatedProfile;
        updatedProfile.writeU32(1);
        updatedProfile.writeU32(1);
        updatedProfile.writeU32(0x22E25925);
        const std::array<std::uint8_t, 4> profileBlob{ 0x78, 0x01, 0x02, 0x03 };
        updatedProfile.writeBlob(profileBlob);
        const auto setPublic = persistentRegistry.dispatch(ServiceRequest{
            .service = 0x08,
            .protocolVersion = 3,
            .task = 3,
            .payload = updatedProfile.data(),
        });
        const auto storedPath = sandbox / "1004" / "1100001DEADC0DE" / "Publicprofile";
        std::ifstream storedStream(storedPath, std::ios::binary);
        const auto storedProfile = std::vector<std::uint8_t>(
            std::istreambuf_iterator<char>(storedStream), std::istreambuf_iterator<char>());
        storedStream.close();
        requireDw(setPublic && setPublic->error == 0 && setPublic->objects.empty() &&
            storedProfile == updatedProfile.data(),
            "Profiles2 task 3 atomically persists the captured public-profile payload verbatim");

        constexpr auto otherUserId = 0x110000100000002ULL;
        ByteBuffer otherPublicProfile;
        otherPublicProfile.writeU32(0x12345678);
        ByteBuffer byUserPayload;
        byUserPayload.writeU64(otherUserId);
        byUserPayload.writeRaw(otherPublicProfile.data());
        const auto setPublicByUser = persistentRegistry.dispatch(ServiceRequest{
            .service = 0x08,
            .protocolVersion = 3,
            .task = 8,
            .payload = byUserPayload.data(),
        });
        const auto otherPublicPath = sandbox / "1004" / "110000100000002" / "Publicprofile";
        std::ifstream otherPublicStream(otherPublicPath, std::ios::binary);
        const auto storedOtherPublic = std::vector<std::uint8_t>(
            std::istreambuf_iterator<char>(otherPublicStream), std::istreambuf_iterator<char>());
        otherPublicStream.close();
        requireDw(setPublicByUser && setPublicByUser->error == 0 &&
            storedOtherPublic == otherPublicProfile.data() && storedProfile == updatedProfile.data() &&
            persistentRegistry.taskName(0x08, 3) == "Profiles2::setPublicInfo" &&
            persistentRegistry.taskName(0x08, 8) == "Profiles2::setPublicInfoByUserID",
            "Profiles2 task 8 persists the public profile under the explicit user ID");

        const auto missingPrivate = persistentRegistry.dispatch(ServiceRequest{
            .service = 0x08,
            .protocolVersion = 3,
            .task = 2,
        });
        requireDw(missingPrivate && missingPrivate->error == 0 && missingPrivate->objects.empty(),
            "Profiles2 task 2 returns empty success when the private profile is absent");

        ByteBuffer privatePayload;
        privatePayload.writeU32(2);
        privatePayload.writeBlob(std::array<std::uint8_t, 3>{ 0xAA, 0xBB, 0xCC });
        const auto setPrivate = persistentRegistry.dispatch(ServiceRequest{
            .service = 0x08,
            .protocolVersion = 3,
            .task = 4,
            .payload = privatePayload.data(),
        });
        const auto privatePath = sandbox / "1004" / "1100001DEADC0DE" / "Privateprofile";
        std::ifstream privateStream(privatePath, std::ios::binary);
        const auto storedPrivate = std::vector<std::uint8_t>(
            std::istreambuf_iterator<char>(privateStream), std::istreambuf_iterator<char>());
        privateStream.close();
        requireDw(setPrivate && setPrivate->error == 0 && storedPrivate == privatePayload.data(),
            "Profiles2 task 4 atomically persists the private-profile payload verbatim");

        const auto privateInfoForCurrentUser = persistentRegistry.dispatch(ServiceRequest{
            .service = 0x08,
            .protocolVersion = 3,
            .task = 2,
        });
        requireDw(privateInfoForCurrentUser && privateInfoForCurrentUser->error == 0 &&
            privateInfoForCurrentUser->objects.empty(),
            "Profiles2 task 2 remains an empty success when a private profile exists");

        ByteBuffer privateByUserPayload;
        privateByUserPayload.writeU64(session.snapshot().userId);
        const auto privateInfo = persistentRegistry.dispatch(ServiceRequest{
            .service = 0x08,
            .protocolVersion = 3,
            .task = 7,
            .payload = privateByUserPayload.data(),
        });
        requireDw(privateInfo && privateInfo->error == 0 && privateInfo->objects.size() == 1,
            "Profiles2 task 7 returns the persisted private profile");
        ByteBuffer privateObject(privateInfo->objects.front());
        std::uint64_t privateUserId{};
        requireDw(privateObject.readU64(privateUserId) && privateUserId == session.snapshot().userId &&
            std::ranges::equal(privateObject.remaining(), privatePayload.data()),
            "Profiles2 private-profile result contains the current user and raw file bytes");

        ByteBuffer otherPrivateProfile;
        otherPrivateProfile.writeU32(0x87654321);
        ByteBuffer setPrivateByUserPayload;
        setPrivateByUserPayload.writeU64(otherUserId);
        setPrivateByUserPayload.writeRaw(otherPrivateProfile.data());
        const auto setPrivateByUser = persistentRegistry.dispatch(ServiceRequest{
            .service = 0x08,
            .protocolVersion = 3,
            .task = 6,
            .payload = setPrivateByUserPayload.data(),
        });
        const auto otherPrivatePath = sandbox / "1004" / "110000100000002" / "Privateprofile";
        std::ifstream otherPrivateStream(otherPrivatePath, std::ios::binary);
        const auto storedOtherPrivate = std::vector<std::uint8_t>(
            std::istreambuf_iterator<char>(otherPrivateStream), std::istreambuf_iterator<char>());
        otherPrivateStream.close();
        requireDw(setPrivateByUser && setPrivateByUser->error == 0 &&
            storedOtherPrivate == otherPrivateProfile.data() && storedPrivate == privatePayload.data(),
            "Profiles2 task 6 persists the private profile under the explicit user ID");

        ByteBuffer getOtherPrivatePayload;
        getOtherPrivatePayload.writeU64(otherUserId);
        const auto otherPrivateInfo = persistentRegistry.dispatch(ServiceRequest{
            .service = 0x08,
            .protocolVersion = 3,
            .task = 7,
            .payload = getOtherPrivatePayload.data(),
        });
        requireDw(otherPrivateInfo && otherPrivateInfo->error == 0 &&
            otherPrivateInfo->objects.size() == 1,
            "Profiles2 task 7 returns one private profile for the explicit user ID");
        ByteBuffer otherPrivateObject(otherPrivateInfo->objects.front());
        std::uint64_t returnedOtherUserId{};
        requireDw(otherPrivateObject.readU64(returnedOtherUserId) &&
            returnedOtherUserId == otherUserId &&
            std::ranges::equal(otherPrivateObject.remaining(), otherPrivateProfile.data()),
            "Profiles2 task 7 loads the private profile for the explicit user ID");

        const auto malformedPrivateByUser = persistentRegistry.dispatch(ServiceRequest{
            .service = 0x08,
            .protocolVersion = 3,
            .task = 6,
        });
        requireDw(malformedPrivateByUser && malformedPrivateByUser->error == 1000,
            "Profiles2 task 6 rejects a missing user ID and profile payload");

        const auto deleteProfile = persistentRegistry.dispatch(ServiceRequest{
            .service = 0x08,
            .protocolVersion = 3,
            .task = 5,
        });
        requireDw(deleteProfile && deleteProfile->error == 0 &&
            !std::filesystem::exists(storedPath) && !std::filesystem::exists(privatePath) &&
            std::filesystem::exists(otherPublicPath) && std::filesystem::exists(otherPrivatePath),
            "Profiles2 task 5 removes only the current user's public and private profiles");

        requireDw(
            persistentRegistry.taskName(0x08, 1) == "Profiles2::getPublicInfos" &&
            persistentRegistry.taskName(0x08, 2) == "Profiles2::getPrivateInfo" &&
            persistentRegistry.taskName(0x08, 3) == "Profiles2::setPublicInfo" &&
            persistentRegistry.taskName(0x08, 4) == "Profiles2::setPrivateInfo" &&
            persistentRegistry.taskName(0x08, 5) == "Profiles2::deleteProfile" &&
            persistentRegistry.taskName(0x08, 6) == "Profiles2::setPrivateInfoByUserID" &&
            persistentRegistry.taskName(0x08, 7) == "Profiles2::getPrivateInfoByUserID" &&
            persistentRegistry.taskName(0x08, 8) == "Profiles2::setPublicInfoByUserID",
            "Profiles2 dispatcher registers all eight CODOL tasks");
        std::filesystem::remove_all(sandbox, filesystemError);
    }

    void testTencentService()
    {
        using namespace AlwaysofflineRe::Demonware;

        AuthSession session;
        ServiceRegistry registry;
        TencentService service(session);
        service.registerTasks(registry);

        const auto response = registry.dispatch(ServiceRequest{
            .service = 0x47,
            .protocolVersion = 3,
            .task = 5,
        });
        requireDw(response && response->transaction == (OriginalTransactionPrefix | 1) &&
            response->error == 0 && response->task == 5 && response->objects.size() == 1,
            "Tencent getAASRecord returns one recovered object");
        requireDw(registry.taskName(0x47, 5) == "Tencent::getAASRecord",
            "Tencent getAASRecord registration is explicit");

        ByteBuffer object(response->objects.front());
        std::uint8_t enabled{};
        std::uint64_t userId{};
        std::uint8_t code{};
        std::uint32_t firstInterval{};
        std::uint32_t secondInterval{};
        requireDw(object.readU8(enabled) && enabled == 1 &&
            object.readU64(userId) && userId == session.snapshot().userId &&
            object.readU8(code) && code == 0x58 &&
            object.readU32(firstInterval) && firstInterval == 60 &&
            object.readU32(secondInterval) && secondInterval == 30 &&
            object.empty() && object.valid(),
            "Tencent getAASRecord matches the captured typed field order");

        ByteBuffer task2Payload;
        task2Payload.writeString("Alwaysoffline");
        const auto task2 = registry.dispatch(ServiceRequest{
            .service = 0x47,
            .protocolVersion = 3,
            .task = 2,
            .payload = task2Payload.data(),
        });
        requireDw(task2 && task2->error == 0 && task2->objects.size() == 1,
            "Tencent task 2 returns the captured local identity object");

        ByteBuffer task2Object(task2->objects.front());
        bool firstLogin{};
        std::string username;
        requireDw(task2Object.readBool(firstLogin) && !firstLogin &&
            task2Object.readString(username) && username == "Alwaysoffline" &&
            task2Object.empty() && task2Object.valid(),
            "Tencent task 2 matches the recovered bool and username fields");

        ByteBuffer verifyPayload;
        verifyPayload.writeString("player supplied text");
        const auto verify = registry.dispatch(ServiceRequest{
            .service = 0x47,
            .protocolVersion = 3,
            .task = 1,
            .payload = verifyPayload.data(),
        });
        requireDw(verify && verify->error == 0 && verify->objects.size() == 1,
            "Tencent task 1 returns one archived verification result");
        ByteBuffer verifyObject(verify->objects.front());
        std::uint32_t verificationToken{};
        requireDw(verifyObject.readU32(verificationToken) && verificationToken == 0 &&
            verifyObject.empty() && verifyObject.valid(),
            "Tencent task 1 returns the archived zero verification token");

        for (const auto telemetryTask : { std::uint8_t{ 3 }, std::uint8_t{ 7 }, std::uint8_t{ 8 } })
        {
            ByteBuffer telemetryPayload;
            telemetryPayload.writeString("telemetry");
            const auto telemetry = registry.dispatch(ServiceRequest{
                .service = 0x47,
                .protocolVersion = 3,
                .task = telemetryTask,
                .payload = telemetryPayload.data(),
            });
            requireDw(telemetry && telemetry->error == 0 && telemetry->objects.empty(),
                "Tencent tasks 3, 7 and 8 consume one telemetry string and return empty success");
        }

        ByteBuffer rewardsPayload;
        rewardsPayload.writeU32(2);
        rewardsPayload.writeString("event_alpha");
        rewardsPayload.writeString("event_beta");
        const auto rewards = registry.dispatch(ServiceRequest{
            .service = 0x47,
            .protocolVersion = 3,
            .task = 11,
            .payload = rewardsPayload.data(),
        });
        requireDw(rewards && rewards->error == 0 && rewards->objects.empty(),
            "Tencent task 11 consumes every client-decided reward code");

        ByteBuffer truncatedRewardsPayload;
        truncatedRewardsPayload.writeU32(2);
        truncatedRewardsPayload.writeString("only_one_event");
        const auto truncatedRewards = registry.dispatch(ServiceRequest{
            .service = 0x47,
            .protocolVersion = 3,
            .task = 11,
            .payload = truncatedRewardsPayload.data(),
        });
        requireDw(truncatedRewards && truncatedRewards->error == 1000,
            "Tencent task 11 rejects a truncated reward-code list");

        const auto task9 = registry.dispatch(ServiceRequest{
            .service = 0x47,
            .protocolVersion = 3,
            .task = 9,
        });
        requireDw(task9 && task9->error == 0 && task9->objects.empty(),
            "Tencent task 9 matches the archived default empty success response");
        requireDw(registry.taskName(0x47, 1) == "Tencent::verifyString" &&
            registry.taskName(0x47, 8) == "Tencent::acceptTelemetry" &&
            registry.taskName(0x47, 11) == "Tencent::claimClientDecidedRewards",
            "Tencent recovered handlers have explicit registry names");
    }

    void testContentUnlock2Service()
    {
        using namespace AlwaysofflineRe::Demonware;

        ServiceRegistry registry;
        ContentUnlock2Service service;
        service.registerTasks(registry);

        const std::array<std::uint32_t, 5> contentIds{ 0, 1, 2, 9, 0x105 };
        ByteBuffer payload;
        payload.writeU32Array(contentIds);
        const auto response = registry.dispatch(ServiceRequest{
            .service = 0x1C,
            .protocolVersion = 3,
            .task = 4,
            .payload = payload.data(),
        });
        requireDw(response && response->transaction == (OriginalTransactionPrefix | 1) &&
            response->error == 0 && response->task == 4 && response->objects.size() == contentIds.size(),
            "ContentUnlock2 task 4 returns one object per requested ID");
        requireDw(registry.taskName(0x1C, 4) == "ContentUnlock2::task4",
            "unnamed ContentUnlock2 task 4 remains explicitly labeled");

        for (std::size_t index = 0; index != contentIds.size(); ++index)
        {
            ByteBuffer object(response->objects[index]);
            std::uint32_t contentId{};
            std::uint32_t value{};
            requireDw(object.readU32(contentId) && contentId == contentIds[index] &&
                object.readU32(value) && value == 32 && object.empty() && object.valid(),
                "ContentUnlock2 task 4 matches the recovered two-uint32 object");
        }

        const std::array<std::uint32_t, 1> roomContentIds{ 131 };
        ByteBuffer task1Payload;
        task1Payload.writeU32Array(roomContentIds);
        const auto task1 = registry.dispatch(ServiceRequest{
            .service = 0x1C,
            .protocolVersion = 3,
            .task = 1,
            .payload = task1Payload.data(),
        });
        requireDw(task1 && task1->error == 0 && task1->objects.empty(),
            "ContentUnlock2 task 1 consumes the room content array and returns empty success");

        std::array<std::uint32_t, 33> repeatedContentIds{};
        repeatedContentIds.fill(0x222);
        ByteBuffer task2Payload;
        task2Payload.writeU64(0x1100001DEADC0DEULL);
        task2Payload.writeU32Array(repeatedContentIds);
        const auto task2 = registry.dispatch(ServiceRequest{
            .service = 0x1C,
            .protocolVersion = 3,
            .task = 2,
            .payload = task2Payload.data(),
        });
        requireDw(task2 && task2->error == 0 && task2->objects.empty(),
            "ContentUnlock2 task 2 consumes a user ID and increments every content counter");

        ByteBuffer countedPayload;
        countedPayload.writeU32Array(std::array<std::uint32_t, 1>{ 0x222 });
        const auto counted = registry.dispatch(ServiceRequest{
            .service = 0x1C,
            .protocolVersion = 3,
            .task = 4,
            .payload = countedPayload.data(),
        });
        requireDw(counted && counted->error == 0 && counted->objects.size() == 1,
            "ContentUnlock2 task 4 returns the accumulated content counter");
        ByteBuffer countedObject(counted->objects.front());
        std::uint32_t countedId{};
        std::uint32_t countedValue{};
        requireDw(countedObject.readU32(countedId) && countedId == 0x222 &&
            countedObject.readU32(countedValue) && countedValue == 33 &&
            countedObject.empty() && countedObject.valid(),
            "ContentUnlock2 task 4 preserves counts above the minimum value of 32");

        ByteBuffer task3Payload;
        task3Payload.writeU64(0x1100001DEADC0DEULL);
        const auto task3 = registry.dispatch(ServiceRequest{
            .service = 0x1C,
            .protocolVersion = 3,
            .task = 3,
            .payload = task3Payload.data(),
        });
        requireDw(task3 && task3->error == 0 && task3->objects.empty(),
            "ContentUnlock2 task 3 consumes its typed user ID");
        requireDw(registry.taskName(0x1C, 1) == "ContentUnlock2::task1" &&
            registry.taskName(0x1C, 2) == "ContentUnlock2::task2" &&
            registry.taskName(0x1C, 3) == "ContentUnlock2::task3" &&
            registry.taskName(0x1C, 4) == "ContentUnlock2::task4",
            "ContentUnlock2 registers all four archived tasks");
    }

    void testRoomBoundaryServices()
    {
        using namespace AlwaysofflineRe::Demonware;

        LanDiscovery messageBus(0x1111, false);
        std::uint64_t receivedOrigin{};
        std::string receivedPayload;
        messageBus.subscribe("Demonware::Channelmessage",
            [&receivedOrigin, &receivedPayload](const std::uint64_t origin, const std::string_view payload)
            {
                receivedOrigin = origin;
                receivedPayload = payload;
            });
        constexpr auto busOrigin = std::uint64_t{ 0x2222 };
        constexpr std::string_view busPayload = "{\"Whisper\":false}";
        const auto busPacket = LanDiscovery::encodePacket(
            "Demonware::Channelmessage", busOrigin, busPayload);
        constexpr std::string_view expectedBusPacket =
            "MEEPeyJFdmVudCI6IkRlbW9ud2FyZTo6Q2hhbm5lbG1lc3NhZ2UiLCJPcmlnaW4iOjg3Mzgs"
            "IlBheWxvYWQiOiJleUpYYUdsemNHVnlJanBtWVd4elpYMD0ifQ==";
        requireDw(std::string_view(
            reinterpret_cast<const char *>(busPacket.data()), busPacket.size()) == expectedBusPacket,
            "legacy MEEP event reproduces the 2019 Base64 JSON wire envelope");
        requireDw(messageBus.ingestPacket(busPacket, 0x0100007F) &&
            receivedOrigin == busOrigin && receivedPayload == busPayload,
            "legacy MEEP bus dispatches a named event with its decoded payload");
        receivedPayload.clear();
        requireDw(!messageBus.ingestPacket(busPacket, 0x0200007F) && receivedPayload.empty(),
            "legacy MEEP bus rejects an established origin arriving from another address");
        const auto selfPacket = LanDiscovery::encodePacket(
            "Demonware::Channelmessage", 0x1111, busPayload);
        requireDw(!messageBus.ingestPacket(selfPacket, 0x0100007F),
            "legacy MEEP bus filters its own broadcast by process session ID");

        ServiceRegistry matchmakingRegistry;
        auto exposeNativeServer = false;
        std::vector<std::vector<std::uint8_t>> configuredServerDescriptors;
        std::vector<nlohmann::json> publishedSessions;
        std::uint32_t publishedTerminations{};
        MatchmakingService matchmaking(false, [&exposeNativeServer]()
            -> std::optional<GameServerEndpoint>
        {
            if (!exposeNativeServer)
                return std::nullopt;
            return GameServerEndpoint{ .ipv4 = 0x7F000001, .port = 28960 };
        }, [&configuredServerDescriptors](
            const std::span<const std::uint8_t> descriptor)
        {
            configuredServerDescriptors.emplace_back(
                descriptor.begin(), descriptor.end());
            return true;
        }, [&publishedSessions](const nlohmann::json &properties) {
            publishedSessions.push_back(properties);
        }, [&publishedTerminations] { ++publishedTerminations; });
        ByteBuffer canonicalSessionDescriptor;
        canonicalSessionDescriptor.writeString("CanonicalSession");
        matchmaking.setSessionDescriptorCanonicalizer(
            [canonical = canonicalSessionDescriptor.data()](
                const std::span<const std::uint8_t>) {
                return std::optional{ canonical };
            });
        matchmaking.registerTasks(matchmakingRegistry);

        const auto emptyFind = matchmakingRegistry.dispatch(ServiceRequest{
            .service = 0x15,
            .protocolVersion = 3,
            .task = 5,
        });
        requireDw(emptyFind && emptyFind->error == 0 && emptyFind->objects.empty(),
            "Matchmaking findSessions matches the captured no-session response");

        const std::array<std::uint8_t, 37> hostAddress{
            0xC0, 0xA8, 0x00, 0x72, 0x31, 0x75, 0x00, 0xFF, 0x00, 0xFF,
            0x00, 0x00, 0x00, 0xFF, 0x00, 0xFF, 0x00, 0x00, 0x00, 0xFF,
            0x00, 0xFF, 0x00, 0x00, 0x00, 0xFF, 0x00, 0xFF, 0x00, 0x00,
            0xF0, 0x00, 0x00, 0x01, 0xC4, 0x14, 0x02,
        };
        ByteBuffer createPayload;
        createPayload.writeBlob(hostAddress);
        createPayload.writeU32(0);
        createPayload.writeU32(6);
        createPayload.writeString("ClientOldName");
        const auto create = matchmakingRegistry.dispatch(ServiceRequest{
            .service = 0x15,
            .protocolVersion = 3,
            .task = 1,
            .payload = createPayload.data(),
        });
        requireDw(create && create->error == 0 && create->objects.size() == 1,
            "Matchmaking createSession accepts the captured room request");
        requireDw(publishedSessions.size() == 1 &&
            publishedSessions.back().value("Players.Max", 0u) == 6 &&
            publishedSessions.back().contains("Session.Demonware"),
            "Matchmaking createSession publishes the first room allocation to peers");
        requireDw(configuredServerDescriptors.size() == 1,
            "Matchmaking createSession configures one native session descriptor");
        ByteBuffer configuredDescriptor(configuredServerDescriptors.back());
        std::string configuredDescriptorText;
        requireDw(configuredDescriptor.readString(configuredDescriptorText) &&
            configuredDescriptorText == "CanonicalSession" &&
            configuredDescriptor.empty() && configuredDescriptor.valid(),
            "Matchmaking createSession preserves the opaque client descriptor");
        ByteBuffer sessionObject(create->objects.front());
        std::vector<std::uint8_t> sessionId;
        requireDw(sessionObject.readBlob(sessionId) && sessionId.size() == 8 &&
            std::ranges::any_of(sessionId, [](const auto value) { return value != 0; }) &&
            sessionObject.empty() && sessionObject.valid(),
            "Matchmaking createSession returns a nonzero native-style session ID");

        const auto find = matchmakingRegistry.dispatch(ServiceRequest{
            .service = 0x15,
            .protocolVersion = 3,
            .task = 5,
        });
        requireDw(find && find->error == 0 && find->objects.size() == 1,
            "Matchmaking findSessions includes the locally-created session like the archived shared container");
        ByteBuffer localFindFields(find->objects.front());
        std::vector<std::uint8_t> localHostAddress;
        std::vector<std::uint8_t> localSessionId;
        std::uint32_t localGameType{};
        std::uint32_t localMaxPlayers{};
        std::uint32_t localCurrentPlayers{};
        // SPLIT DELIBERATELY -- handoff SECTION 191g. This was ONE requireDw over seven
        // conjuncts, and requireDw exits on the first failure with the message it was given.
        // So a real regression printed a single sentence naming all seven fields and saying
        // nothing about WHICH of them moved, which is the failure mode of an instrument that
        // maps many answers onto one word. Seven lines cost nothing and name the field.
        requireDw(localFindFields.readBlob(localHostAddress),
            "Matchmaking local result starts with a host address blob");
        requireDw(localHostAddress == std::vector(hostAddress.begin(), hostAddress.end()),
            "Matchmaking local result echoes the host address the client sent");
        requireDw(localFindFields.readBlob(localSessionId),
            "Matchmaking local result carries a session ID blob");
        requireDw(localSessionId == sessionId,
            "Matchmaking local result repeats the session ID createSession returned");
        requireDw(localFindFields.readU32(localGameType) && localGameType == 0,
            "Matchmaking local result preserves the game type");
        requireDw(localFindFields.readU32(localMaxPlayers) && localMaxPlayers == 6,
            "Matchmaking local result preserves the player maximum");
        requireDw(localFindFields.readU32(localCurrentPlayers) && localCurrentPlayers == 1,
            "Matchmaking local result counts the host as one current player");
        // WHAT FOLLOWS THE BASE FIELDS IS A SESSION RECORD, NOT THE CLIENT'S DESCRIPTOR.
        //
        // This used to read one string and require it to be "CanonicalSession", because
        // findSessions once did `writeRaw(properties["Session.Demonware"])` and pasted the
        // opaque descriptor straight back. writeSessionRecordTail() replaced that on
        // 2026-08-30 for a measured reason: the descriptor put 37 in the field the client
        // requires to be 67, sub_B95C50 then left its out-pointer at 0, and sub_8071F0 read
        // *(0 + 0x10) -- the access violation in every QuickMatch and dev-panel crash dump.
        //
        // So the old assertion did not describe a contract, it described the crash, and it
        // has been failing ever since with a message that named seven fields and no value.
        // Asserted here instead are the two properties that analysis turned on, because they
        // are the ones a regression would break silently. That the CANONICAL descriptor still
        // reaches the game server is asserted above, where it belongs.
        std::string localRoomId;
        requireDw(localFindFields.readString(localRoomId),
            "Matchmaking local result continues into the session record with a room id");
        requireDw(!localRoomId.empty() && std::ranges::all_of(localRoomId,
                [](const unsigned char character) { return std::isdigit(character) != 0; }),
            "Matchmaking room id is a decimal string, saw \"" + localRoomId + '"');
        requireDw(std::stoull(localRoomId) != 0,
            "Matchmaking room id is non-zero -- MatchController.as compares it against an unset "
            "last_kick_room_id dvar, and 0 == 0 reports every join as a kick");
        std::uint64_t localRoomHostUid{};
        requireDw(localFindFields.readU64(localRoomHostUid) && localRoomHostUid != 0,
            "Matchmaking room record names a host UID, which must not be the player's own");
        std::string localMapName;
        requireDw(localFindFields.readString(localMapName) && !localMapName.empty(),
            "Matchmaking room record names a map");
        requireDw(localFindFields.valid(),
            "Matchmaking local result decodes cleanly through the session record");

        ByteBuffer findServersPayload;
        findServersPayload.writeU32(1);
        const auto findServers = matchmakingRegistry.dispatch(ServiceRequest{
            .service = 0x15,
            .protocolVersion = 3,
            .task = 5,
            .payload = findServersPayload.data(),
        });
        requireDw(findServers && findServers->error == 0 && findServers->objects.empty(),
            "Matchmaking FIND_SERVERS does not return the locally-created player lobby");
        requireDw(configuredServerDescriptors.size() == 2 &&
            configuredServerDescriptors.front() == configuredServerDescriptors.back(),
            "Matchmaking FIND_SERVERS retries the same session descriptor before discovery");

        exposeNativeServer = true;
        const auto nativeServerFind = matchmakingRegistry.dispatch(ServiceRequest{
            .service = 0x15,
            .protocolVersion = 3,
            .task = 5,
            .payload = findServersPayload.data(),
        });
        requireDw(nativeServerFind && nativeServerFind->error == 0 &&
            nativeServerFind->objects.size() == 1,
            "Matchmaking FIND_SERVERS exposes the in-process CODOL server");
        requireDw(configuredServerDescriptors.size() == 3 &&
            configuredServerDescriptors.front() == configuredServerDescriptors.back(),
            "Matchmaking server discovery configures the endpoint before advertising it");
        ByteBuffer nativeServerFields(nativeServerFind->objects.front());
        std::vector<std::uint8_t> nativeServerAddress;
        std::vector<std::uint8_t> nativeServerId;
        std::uint32_t nativeGameType{};
        std::uint32_t nativeMaxPlayers{};
        std::uint32_t nativeCurrentPlayers{};
        const std::vector<std::uint8_t> expectedNativeAddress{
            0x7F, 0x00, 0x00, 0x01, 0x20, 0x71,
            0x00, 0xFF, 0x00, 0xFF, 0x00, 0x00,
            0x00, 0xFF, 0x00, 0xFF, 0x00, 0x00,
            0x00, 0xFF, 0x00, 0xFF, 0x00, 0x00,
            0x00, 0xFF, 0x00, 0xFF, 0x00, 0x00,
            0x7F, 0x00, 0x00, 0x01, 0x20, 0x71, 0x01,
        };
        requireDw(nativeServerFields.readBlob(nativeServerAddress) &&
            nativeServerAddress == expectedNativeAddress,
            "native server candidate encodes loopback:28960 as bdCommonAddr");
        requireDw(nativeServerFields.readBlob(nativeServerId) && nativeServerId.size() == 8,
            "native server candidate has an eight-byte session ID");
        requireDw(nativeServerFields.readU32(nativeGameType) && nativeGameType == 0,
            "native server candidate uses CODOL game type zero");
        requireDw(nativeServerFields.readU32(nativeMaxPlayers) && nativeMaxPlayers == 18,
            "native server candidate exposes all native client slots");
        requireDw(nativeServerFields.readU32(nativeCurrentPlayers) && nativeCurrentPlayers == 0,
            "native server candidate starts without connected gameplay clients");
        // The same session record as the local result above, for the same measured reason --
        // writeSessionRecordTail(), not the room's opaque descriptor. See the note there.
        std::string nativeRoomId;
        requireDw(nativeServerFields.readString(nativeRoomId),
            "native server candidate continues into the session record with a room id");
        requireDw(!nativeRoomId.empty() && std::ranges::all_of(nativeRoomId,
                [](const unsigned char character) { return std::isdigit(character) != 0; }) &&
            std::stoull(nativeRoomId) != 0,
            "native server candidate room id is a non-zero decimal string, saw \"" +
                nativeRoomId + '"');
        std::uint64_t nativeRoomHostUid{};
        requireDw(nativeServerFields.readU64(nativeRoomHostUid) && nativeRoomHostUid != 0,
            "native server candidate names a host UID");
        std::string nativeMapName;
        requireDw(nativeServerFields.readString(nativeMapName) && !nativeMapName.empty(),
            "native server candidate names a map");
        requireDw(nativeServerFields.valid(),
            "native server candidate decodes cleanly through the session record");
        exposeNativeServer = false;

        ByteBuffer findPlaylistLobbiesPayload;
        findPlaylistLobbiesPayload.writeU32(3);
        const auto findPlaylistLobbies = matchmakingRegistry.dispatch(ServiceRequest{
            .service = 0x15,
            .protocolVersion = 3,
            .task = 5,
            .payload = findPlaylistLobbiesPayload.data(),
        });
        requireDw(findPlaylistLobbies && findPlaylistLobbies->error == 0 &&
            findPlaylistLobbies->objects.size() == 1,
            "Matchmaking FIND_LOBBIES_BY_PLAYLIST still returns the locally-created player lobby");

        ByteBuffer updatePayload;
        updatePayload.writeBlob(sessionId);
        updatePayload.writeBlob(hostAddress);
        updatePayload.writeU32(7);
        updatePayload.writeU32(18);
        updatePayload.writeString("UpdatedLocal");
        const auto update = matchmakingRegistry.dispatch(ServiceRequest{
            .service = 0x15,
            .protocolVersion = 3,
            .task = 2,
            .payload = updatePayload.data(),
        });
        requireDw(update && update->error == 0 && update->objects.empty(),
            "Matchmaking task 2 consumes the session ID and full local properties");
        requireDw(publishedSessions.size() == 2 &&
            publishedSessions.back().value("Players.Max", 0u) == 18,
            "Matchmaking updateSession republishes the changed room allocation");

        ByteBuffer playersPayload;
        playersPayload.writeBlob(sessionId);
        playersPayload.writeU32(4);
        const auto updatePlayers = matchmakingRegistry.dispatch(ServiceRequest{
            .service = 0x15,
            .protocolVersion = 3,
            .task = 12,
            .payload = playersPayload.data(),
        });
        requireDw(updatePlayers && updatePlayers->error == 0 && updatePlayers->objects.empty(),
            "Matchmaking task 12 consumes the session ID and current player count");
        requireDw(publishedSessions.size() == 3 &&
            publishedSessions.back().value("Players.Current", 0u) == 4,
            "Matchmaking updatePlayers republishes the authoritative player count");

        ByteBuffer remoteDemonware;
        remoteDemonware.writeString("SyntheticRemote");
        const auto remoteSessionId = std::uint64_t{ 0x1122334455667788ULL };
        const nlohmann::json remoteProperties{
            { "Demonware.Hostaddress", hostAddress },
            { "Session.Gametype", 7 },
            { "Players.Max", 18 },
            { "Players.Current", 3 },
            { "Session.Demonware", remoteDemonware.data() },
        };
        const auto updatePacket = LanDiscovery::encodePacket(
            "Matchmaking::Update",
            remoteSessionId,
            remoteProperties.dump());
        requireDw(matchmaking.ingestLanPacket(updatePacket, 0x0100007F),
            "LAN discovery accepts an original-format MEEP update packet");

        const auto remoteFind = matchmakingRegistry.dispatch(ServiceRequest{
            .service = 0x15,
            .protocolVersion = 3,
            .task = 5,
        });
        requireDw(remoteFind && remoteFind->error == 0 && remoteFind->objects.size() == 2,
            "Matchmaking findSessions returns the local and active remote LAN sessions");

        ByteBuffer findFields(remoteFind->objects.back());
        std::vector<std::uint8_t> foundHostAddress;
        std::vector<std::uint8_t> foundSessionId;
        std::uint32_t foundGameType{};
        std::uint32_t foundMaxPlayers{};
        std::uint32_t foundCurrentPlayers{};
        const std::array<std::uint8_t, 8> expectedRemoteSessionId{
            0x88, 0x77, 0x66, 0x55, 0x44, 0x33, 0x22, 0x11,
        };
        requireDw(findFields.readBlob(foundHostAddress) &&
            foundHostAddress == std::vector(hostAddress.begin(), hostAddress.end()),
            "Matchmaking remote result carries the remote host address");
        requireDw(findFields.readBlob(foundSessionId) && foundSessionId ==
            std::vector(expectedRemoteSessionId.begin(), expectedRemoteSessionId.end()),
            "Matchmaking remote result carries the remote session ID little-endian");
        requireDw(findFields.readU32(foundGameType) && foundGameType == 7,
            "Matchmaking remote result carries the remote game type");
        requireDw(findFields.readU32(foundMaxPlayers) && foundMaxPlayers == 18,
            "Matchmaking remote result carries the remote player maximum");
        requireDw(findFields.readU32(foundCurrentPlayers) && foundCurrentPlayers == 3,
            "Matchmaking remote result carries the remote player count");
        // Tail is the session record, not "SyntheticRemote" -- see writeSessionRecordTail().
        // Pinned to the DERIVATION rather than to a literal: the room id has to come from the
        // session so that two rooms differ, and a constant here would pass a bare non-zero test.
        std::string foundRoomId;
        requireDw(findFields.readString(foundRoomId),
            "Matchmaking remote result continues into the session record with a room id");
        requireDw(foundRoomId == std::to_string((remoteSessionId & 0x7FFFFFFFULL) | 1ULL),
            "Matchmaking remote room id derives from the remote session ID, saw \"" +
                foundRoomId + '"');
        std::uint64_t foundRoomHostUid{};
        requireDw(findFields.readU64(foundRoomHostUid) && foundRoomHostUid != 0,
            "Matchmaking remote result names a host UID");
        std::string foundMapName;
        requireDw(findFields.readString(foundMapName) && !foundMapName.empty(),
            "Matchmaking remote result names a map");
        requireDw(findFields.valid(),
            "Matchmaking remote result decodes cleanly through the session record");

        const auto matchmaking2Find = matchmakingRegistry.dispatch(ServiceRequest{
            .service = 0x8A,
            .protocolVersion = 3,
            .task = 5,
        });
        requireDw(matchmaking2Find && matchmaking2Find->error == 0 && matchmaking2Find->objects == remoteFind->objects,
            "Matchmaking2 task 5 reuses the recovered legacy findSessions result");

        const auto serverSessionId = std::uint64_t{ 0x8877665544332211ULL };
        auto serverProperties = remoteProperties;
        serverProperties["Session.Role"] = "server";
        serverProperties["Players.Current"] = 0;
        const auto serverUpdatePacket = LanDiscovery::encodePacket(
            "Matchmaking::Update",
            serverSessionId,
            serverProperties.dump());
        requireDw(matchmaking.ingestLanPacket(serverUpdatePacket, 0x0100007F),
            "LAN discovery accepts an explicitly-labelled gameplay server candidate");

        const auto explicitServerFind = matchmakingRegistry.dispatch(ServiceRequest{
            .service = 0x15,
            .protocolVersion = 3,
            .task = 5,
            .payload = findServersPayload.data(),
        });
        requireDw(explicitServerFind && explicitServerFind->error == 0 &&
            explicitServerFind->objects.size() == 1,
            "Matchmaking FIND_SERVERS returns only explicitly-labelled server candidates");
        ByteBuffer serverFindFields(explicitServerFind->objects.front());
        std::vector<std::uint8_t> serverHostAddress;
        std::vector<std::uint8_t> foundServerSessionId;
        requireDw(serverFindFields.readBlob(serverHostAddress) &&
            serverFindFields.readBlob(foundServerSessionId) &&
            foundServerSessionId == std::vector<std::uint8_t>{
                0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77, 0x88 },
            "Matchmaking FIND_SERVERS serializes the explicit server session ID");
        const auto explicitLobbyFind = matchmakingRegistry.dispatch(ServiceRequest{
            .service = 0x15,
            .protocolVersion = 3,
            .task = 5,
            .payload = findPlaylistLobbiesPayload.data(),
        });
        requireDw(explicitLobbyFind && explicitLobbyFind->error == 0 &&
            explicitLobbyFind->objects.size() == 2,
            "Matchmaking FIND_LOBBIES_BY_PLAYLIST excludes the gameplay server candidate");

        constexpr auto performanceContext = std::uint32_t{ 7 };
        constexpr auto firstPerformanceUser = std::uint64_t{ 0x1122334455667788ULL };
        constexpr auto secondPerformanceUser = std::uint64_t{ 0x0102030405060708ULL };
        ByteBuffer submitPerformancePayload;
        submitPerformancePayload.writeU32(performanceContext);
        submitPerformancePayload.writeU64(firstPerformanceUser);
        submitPerformancePayload.writeI64(123);
        submitPerformancePayload.writeU64(secondPerformanceUser);
        submitPerformancePayload.writeI64(-42);
        const auto submitPerformance = matchmakingRegistry.dispatch(ServiceRequest{
            .service = 0x15,
            .protocolVersion = 3,
            .task = 9,
            .payload = submitPerformancePayload.data(),
        });
        requireDw(submitPerformance && submitPerformance->error == 0 && submitPerformance->objects.empty(),
            "Matchmaking task 9 stores captured context, user ID, and signed performance tuples");

        ByteBuffer getPerformancePayload;
        getPerformancePayload.writeU32(performanceContext);
        getPerformancePayload.writeU64(firstPerformanceUser);
        getPerformancePayload.writeU64(0xDEADBEEFDEADBEEFULL);
        getPerformancePayload.writeU64(secondPerformanceUser);
        const auto getPerformance = matchmakingRegistry.dispatch(ServiceRequest{
            .service = 0x8A,
            .protocolVersion = 3,
            .task = 10,
            .payload = getPerformancePayload.data(),
        });
        ByteBuffer firstExpectedPerformance;
        firstExpectedPerformance.writeU64(firstPerformanceUser);
        firstExpectedPerformance.writeI64(123);
        ByteBuffer secondExpectedPerformance;
        secondExpectedPerformance.writeU64(secondPerformanceUser);
        secondExpectedPerformance.writeI64(-42);
        requireDw(getPerformance && getPerformance->error == 0 &&
            getPerformance->objects == std::vector<std::vector<std::uint8_t>>{
                firstExpectedPerformance.data(), secondExpectedPerformance.data() },
            "Matchmaking task 10 returns exact bdPerformanceValue objects and skips unknown users");

        ByteBuffer malformedPerformancePayload;
        malformedPerformancePayload.writeU32(performanceContext);
        malformedPerformancePayload.writeU64(firstPerformanceUser);
        const auto malformedPerformance = matchmakingRegistry.dispatch(ServiceRequest{
            .service = 0x15,
            .protocolVersion = 3,
            .task = 9,
            .payload = malformedPerformancePayload.data(),
        });
        requireDw(malformedPerformance && malformedPerformance->error == 1000,
            "Matchmaking task 9 rejects a performance tuple without its signed value");

        ByteBuffer deletePayload;
        deletePayload.writeBlob(sessionId);
        const auto remove = matchmakingRegistry.dispatch(ServiceRequest{
            .service = 0x15,
            .protocolVersion = 3,
            .task = 3,
            .payload = deletePayload.data(),
        });
        requireDw(remove && remove->error == 0 && remove->objects.empty(),
            "Matchmaking deleteSession matches the captured room-exit response");
        requireDw(publishedTerminations == 1,
            "Matchmaking deleteSession terminates the peer-visible room allocation");

        const auto recreated = matchmakingRegistry.dispatch(ServiceRequest{
            .service = 0x15,
            .protocolVersion = 3,
            .task = 1,
            .payload = createPayload.data(),
        });
        requireDw(recreated && recreated->error == 0 && recreated->objects.size() == 1,
            "Matchmaking recreates a room after deletion");
        requireDw(publishedSessions.size() == 4,
            "Matchmaking recreating a room publishes a new peer-visible allocation");
        ByteBuffer recreatedObject(recreated->objects.front());
        std::vector<std::uint8_t> recreatedSessionId;
        requireDw(recreatedObject.readBlob(recreatedSessionId) && recreatedSessionId == sessionId,
            "Matchmaking reuses the process session ID across room creation");

        ByteBuffer recreatedDeletePayload;
        recreatedDeletePayload.writeBlob(recreatedSessionId);
        const auto recreatedRemove = matchmakingRegistry.dispatch(ServiceRequest{
            .service = 0x15,
            .protocolVersion = 3,
            .task = 3,
            .payload = recreatedDeletePayload.data(),
        });
        requireDw(recreatedRemove && recreatedRemove->error == 0,
            "Matchmaking deletes a recreated room by its stable session ID");
        requireDw(publishedTerminations == 2,
            "Matchmaking deleting a recreated room republishes termination");

        const auto terminatePacket = LanDiscovery::encodePacket(
            "Matchmaking::Terminate",
            remoteSessionId,
            {});
        requireDw(matchmaking.ingestLanPacket(terminatePacket, 0x0100007F),
            "LAN discovery accepts a terminate packet from the remote session address");
        const auto serverTerminatePacket = LanDiscovery::encodePacket(
            "Matchmaking::Terminate",
            serverSessionId,
            {});
        requireDw(matchmaking.ingestLanPacket(serverTerminatePacket, 0x0100007F),
            "LAN discovery removes the explicit gameplay server candidate");

        const auto findAfterDelete = matchmakingRegistry.dispatch(ServiceRequest{
            .service = 0x15,
            .protocolVersion = 3,
            .task = 16,
        });
        requireDw(findAfterDelete && findAfterDelete->error == 0 && findAfterDelete->objects.empty(),
            "Matchmaking task 16 shares findSessions and observes remote termination");

        requireDw(matchmakingRegistry.taskName(0x8A, 2) == "Matchmaking2::updateSession" &&
            matchmakingRegistry.taskName(0x8A, 9) == "Matchmaking2::submitPerformance" &&
            matchmakingRegistry.taskName(0x8A, 10) == "Matchmaking2::getPerformanceValues" &&
            matchmakingRegistry.taskName(0x8A, 12) == "Matchmaking2::updatePlayers",
            "Matchmaking2 registers all recovered state and performance handlers");

        AuthSession session;
        ServiceRegistry unknownRegistry;
        std::vector<std::pair<std::uint8_t, std::vector<std::uint8_t>>> channelPushes;
        std::vector<std::string> bookingCommands;
        std::vector<Unknown0BService::RoomEvent> roomEvents;
        Unknown0BService unknown0B(session, [&channelPushes](auto payload, const std::uint8_t messageType)
        {
            channelPushes.emplace_back(messageType, std::move(payload));
        }, nullptr, [&bookingCommands](const std::string_view command)
        {
            bookingCommands.emplace_back(command);
        }, [&roomEvents](const Unknown0BService::RoomEvent event)
        {
            roomEvents.push_back(event);
            return true;
        });
        unknown0B.registerTasks(unknownRegistry);

        const auto task13 = unknownRegistry.dispatch(ServiceRequest{
            .service = 0x0B,
            .protocolVersion = 3,
            .task = 13,
        });
        requireDw(task13 && task13->error == 0 && task13->objects.size() == 1,
            "Unknown0B task 13 returns the recovered room-entry object");
        requireDw(roomEvents == std::vector{ Unknown0BService::RoomEvent::Enter },
            "Unknown0B task 13 commits shared-room entry before replying");
        const auto capturedTask13 = unknownRegistry.dispatch(ServiceRequest{
            .service = 0x0B,
            .protocolVersion = 3,
            .task = 13,
            .payload = { 0 },
        });
        requireDw(capturedTask13 && capturedTask13->error == 0,
            "Unknown0B task 13 accepts the captured single-zero empty argument");
        const auto invalidTask13 = unknownRegistry.dispatch(ServiceRequest{
            .service = 0x0B,
            .protocolVersion = 3,
            .task = 13,
            .payload = { 1 },
        });
        requireDw(invalidTask13 && invalidTask13->error == 1000,
            "Unknown0B task 13 rejects non-empty argument bytes");
        ByteBuffer task13Object(task13->objects.front());
        std::uint64_t lowUserId{};
        std::uint32_t zero{};
        std::uint32_t code{};
        std::uint64_t userId{};
        bool firstFlag{};
        bool secondFlag{};
        std::uint32_t enabled{};
        requireDw(task13Object.readU64(lowUserId) && lowUserId == 0xDEADC0DEULL &&
            task13Object.readU32(zero) && zero == 0 &&
            task13Object.readU32(code) && code == 18 &&
            task13Object.readU64(userId) && userId == session.snapshot().userId &&
            task13Object.readBool(firstFlag) && !firstFlag &&
            task13Object.readBool(secondFlag) && !secondFlag &&
            task13Object.readU32(enabled) && enabled == 1 &&
            task13Object.empty() && task13Object.valid(),
            "Unknown0B task 13 matches the recovered seven-field serializer");

        ByteBuffer task2Payload;
        task2Payload.writeU64(session.snapshot().userId);
        const auto task2 = unknownRegistry.dispatch(ServiceRequest{
            .service = 0x0B,
            .protocolVersion = 3,
            .task = 2,
            .payload = task2Payload.data(),
        });
        requireDw(task2 && task2->error == 0 && task2->objects.empty(),
            "Unknown0B task 2 consumes the room-exit user ID");
        requireDw(roomEvents.back() == Unknown0BService::RoomEvent::Leave,
            "Unknown0B task 2 commits shared-room exit before replying");

        const std::array<std::uint8_t, 16> readyRoomData{
            0x0C, 0x00, 0x00, 0x00, 0x02, 0x02, 0x00, 0x00,
            0x00, 0x08, 0x00, 0x00, 0x00, 0x80, 0x08, 0x00,
        };
        ByteBuffer task4Payload;
        task4Payload.writeU64(static_cast<std::uint32_t>(session.snapshot().userId));
        task4Payload.writeBlob(readyRoomData);
        task4Payload.writeU32(1);
        const std::array<std::uint8_t, 1> task4Trailing{};
        task4Payload.writeRaw(task4Trailing);
        const auto task4 = unknownRegistry.dispatch(ServiceRequest{
            .service = 0x0B,
            .protocolVersion = 3,
            .task = 4,
            .payload = task4Payload.data(),
        });
        requireDw(task4 && task4->error == 0 && task4->objects.empty(),
            "Unknown0B task 4 consumes the captured ready-state payload and returns empty success");
        requireDw(roomEvents.back() == Unknown0BService::RoomEvent::Ready,
            "captured task-4 ready message commits shared-room readiness");
        ByteBuffer expectedReadyPush;
        expectedReadyPush.writeU32(8);
        expectedReadyPush.writeU64(session.snapshot().userId);
        expectedReadyPush.writeString(session.snapshot().username);
        expectedReadyPush.writeU64(static_cast<std::uint32_t>(session.snapshot().userId));
        expectedReadyPush.writeBlob(readyRoomData);
        expectedReadyPush.writeU32(1);
        requireDw(channelPushes.size() == 1 && channelPushes.front().first == 2 &&
            channelPushes.front().second == expectedReadyPush.data(),
            "Unknown0B task 4 loops the room message back as the archived public event-8 push");
        channelPushes.clear();

        for (const auto pairTask : { std::uint8_t{ 1 }, std::uint8_t{ 9 }, std::uint8_t{ 11 } })
        {
            ByteBuffer pairPayload;
            pairPayload.writeU64(session.snapshot().userId);
            pairPayload.writeU64(0x110000100000002ULL);
            const auto pairResponse = unknownRegistry.dispatch(ServiceRequest{
                .service = 0x0B,
                .protocolVersion = 3,
                .task = pairTask,
                .payload = pairPayload.data(),
            });
            requireDw(pairResponse && pairResponse->error == 0 && pairResponse->objects.empty(),
                "Unknown0B tasks 1, 9 and 11 consume two typed user IDs");
        }

        ByteBuffer task10Payload;
        task10Payload.writeU64(session.snapshot().userId);
        task10Payload.writeU64(0x110000100000002ULL);
        task10Payload.writeU32(7);
        task10Payload.writeBool(true);
        const auto task10 = unknownRegistry.dispatch(ServiceRequest{
            .service = 0x0B,
            .protocolVersion = 3,
            .task = 10,
            .payload = task10Payload.data(),
        });
        requireDw(task10 && task10->error == 0 && task10->objects.empty(),
            "Unknown0B task 10 consumes its two IDs, uint32 and bool fields");

        ByteBuffer truncatedTask10Payload;
        truncatedTask10Payload.writeU64(session.snapshot().userId);
        truncatedTask10Payload.writeU64(0x110000100000002ULL);
        truncatedTask10Payload.writeU32(7);
        const auto truncatedTask10 = unknownRegistry.dispatch(ServiceRequest{
            .service = 0x0B,
            .protocolVersion = 3,
            .task = 10,
            .payload = truncatedTask10Payload.data(),
        });
        requireDw(truncatedTask10 && truncatedTask10->error == 1000,
            "Unknown0B task 10 rejects a truncated request");
        ByteBuffer task5Payload;
        task5Payload.writeU64(1);
        task5Payload.writeU64(session.snapshot().userId);
        const std::array<std::uint8_t, 2> channelMessage{ 'h', 'i' };
        task5Payload.writeBlob(channelMessage);
        task5Payload.writeU32(0);
        const auto task5 = unknownRegistry.dispatch(ServiceRequest{
            .service = 0x0B,
            .protocolVersion = 3,
            .task = 5,
            .payload = task5Payload.data(),
        });
        requireDw(task5 && task5->error == 0 && task5->objects.empty(),
            "Unknown0B task 5 returns the archived empty-success response");
        requireDw(channelPushes.size() == 1 && channelPushes.front().first == 2,
            "Unknown0B task 5 queues one type-2 private-message push for the local recipient");
        const auto expectedPrivatePush = fromHex(
            "08070000000adec0adde0100100110416c776179736f66666c696e6500"
            "0a010000000000000013080200000068690800000000");
        requireDw(channelPushes.front().second == expectedPrivatePush,
            "Unknown0B private-message push matches the archived event-7 serializer");
        requireDw(bookingCommands.empty(),
            "ordinary Unknown0B private messages do not enter the game booking path");

        ByteBuffer bookingPayload;
        bookingPayload.writeU64(1);
        bookingPayload.writeU64(session.snapshot().userId);
        constexpr std::string_view BookingCommand =
            "mmstart sv_resetServer; playlist 111; start_map_rotate_once 5";
        bookingPayload.writeBlob(std::span(
            reinterpret_cast<const std::uint8_t *>(BookingCommand.data()),
            BookingCommand.size()));
        bookingPayload.writeU32(0);
        const auto booking = unknownRegistry.dispatch(ServiceRequest{
            .service = 0x0B,
            .protocolVersion = 3,
            .task = 5,
            .payload = bookingPayload.data(),
        });
        requireDw(booking && booking->error == 0 && bookingCommands ==
            std::vector<std::string>{ std::string(BookingCommand) },
            "Unknown0B task 5 exposes the exact outbound mmstart booking command");
        requireDw(channelPushes.size() == 2,
            "booking capture preserves the normal private-message push path");
        channelPushes.pop_back();

        const nlohmann::json publicEvent{
            { "Sendername", "Remote" },
            { "SenderID", 0x110000100000002ULL },
            { "ChannelID", 9 },
            { "Recipient", 0 },
            { "Message", std::vector<std::uint8_t>{ 'o', 'k' } },
            { "Whisper", false },
            { "Type", 3 },
        };
        const auto publicPush = Unknown0BService::decodeChannelPush(
            publicEvent.dump(), session.snapshot().userId);
        requireDw(publicPush.has_value(),
            "remote non-whisper channel event is accepted for the local lobby");
        ByteBuffer publicPushFields(*publicPush);
        std::uint32_t publicEventCode{};
        std::uint64_t publicSender{};
        std::string publicSenderName;
        std::uint64_t publicChannel{};
        std::vector<std::uint8_t> publicMessage;
        std::uint32_t publicType{};
        requireDw(publicPushFields.readU32(publicEventCode) && publicEventCode == 8 &&
            publicPushFields.readU64(publicSender) && publicSender == 0x110000100000002ULL &&
            publicPushFields.readString(publicSenderName) && publicSenderName == "Remote" &&
            publicPushFields.readU64(publicChannel) && publicChannel == 9 &&
            publicPushFields.readBlob(publicMessage) && publicMessage == std::vector<std::uint8_t>({ 'o', 'k' }) &&
            publicPushFields.readU32(publicType) && publicType == 3 &&
            publicPushFields.empty() && publicPushFields.valid(),
            "remote channel event matches the archived event-8 field order");

        auto invalidEvent = publicEvent;
        invalidEvent["Message"] = nlohmann::json::array({ 256 });
        requireDw(!Unknown0BService::decodeChannelPush(
            invalidEvent.dump(), session.snapshot().userId),
            "channel event rejects message elements outside the byte range");

        ByteBuffer remoteTask5Payload;
        remoteTask5Payload.writeU64(1);
        remoteTask5Payload.writeU64(0x110000100000002ULL);
        remoteTask5Payload.writeBlob(channelMessage);
        remoteTask5Payload.writeU32(0);
        const auto remoteTask5 = unknownRegistry.dispatch(ServiceRequest{
            .service = 0x0B,
            .protocolVersion = 3,
            .task = 5,
            .payload = remoteTask5Payload.data(),
        });
        requireDw(remoteTask5 && remoteTask5->error == 0 && channelPushes.size() == 1,
            "Unknown0B private-message delivery filters non-local recipients");
        requireDw(unknownRegistry.taskName(0x0B, 1) == "Unknown0B::consumeUserPair" &&
            unknownRegistry.taskName(0x0B, 5) == "Unknown0B::publishChannelMessage" &&
            unknownRegistry.taskName(0x0B, 10) == "Unknown0B::task10" &&
            unknownRegistry.taskName(0x0B, 11) == "Unknown0B::consumeUserPair",
            "Unknown0B recovered scalar tasks have explicit registry names");
    }

    void testInstantMessageService()
    {
        using namespace AlwaysofflineRe::Demonware;

        AuthSession session;
        ServiceRegistry registry;
        LanDiscovery messageBus(0x1111, false);
        std::vector<std::pair<std::uint8_t, std::vector<std::uint8_t>>> directPushes;
        std::string bookingCommand;
        InstantMessageService service(session, [&directPushes](auto payload, const std::uint8_t messageType)
        {
            directPushes.emplace_back(messageType, std::move(payload));
        }, &messageBus, [&bookingCommand](const std::string_view command)
        {
            bookingCommand = command;
        });
        service.registerTasks(registry);

        const std::array<std::uint8_t, 2> message{ 'h', 'i' };
        ByteBuffer task14Payload;
        task14Payload.writeU64(0x1100001DEADC002ULL);
        task14Payload.writeBlob(message);
        const auto task14 = registry.dispatch(ServiceRequest{
            .service = 0x06,
            .protocolVersion = 3,
            .task = 14,
            .payload = task14Payload.data(),
        });
        requireDw(task14 && task14->error == 0 && task14->objects.empty() && directPushes.empty(),
            "Messaging task 14 accepts recipient and blob while filtering its remote local callback");

        ByteBuffer localTask14Payload;
        localTask14Payload.writeU64(session.snapshot().userId);
        localTask14Payload.writeBlob(message);
        const auto localTask14 = registry.dispatch(ServiceRequest{
            .service = 0x06,
            .protocolVersion = 3,
            .task = 14,
            .payload = localTask14Payload.data(),
        });
        requireDw(localTask14 && localTask14->error == 0 && directPushes.empty(),
            "Messaging task 14 preserves the local-command response boundary without a fabricated push");

        ByteBuffer malformedTask14Payload;
        malformedTask14Payload.writeU64(0x1100001DEADC002ULL);
        const auto malformedTask14 = registry.dispatch(ServiceRequest{
            .service = 0x06,
            .protocolVersion = 3,
            .task = 14,
            .payload = malformedTask14Payload.data(),
        });
        requireDw(malformedTask14 && malformedTask14->error == 1000,
            "Messaging task 14 rejects a request without its message blob");

        ByteBuffer task18Payload;
        task18Payload.writeBlob(message);
        task18Payload.writeU64(0x1100001DEADC002ULL);
        task18Payload.writeU64(0x1100001DEADC003ULL);
        const auto task18 = registry.dispatch(ServiceRequest{
            .service = 0x06,
            .protocolVersion = 3,
            .task = 18,
            .payload = task18Payload.data(),
        });
        requireDw(task18 && task18->error == 0 && task18->objects.empty() && directPushes.empty(),
            "Messaging task 18 consumes its blob and repeated recipient list");

        ByteBuffer malformedTask18Payload;
        malformedTask18Payload.writeBlob(message);
        malformedTask18Payload.writeU32(1);
        const auto malformedTask18 = registry.dispatch(ServiceRequest{
            .service = 0x06,
            .protocolVersion = 3,
            .task = 18,
            .payload = malformedTask18Payload.data(),
        });
        requireDw(malformedTask18 && malformedTask18->error == 1000,
            "Messaging task 18 rejects a non-uint64 recipient tail");

        ByteBuffer getMessagesPayload;
        getMessagesPayload.writeU32(0);
        getMessagesPayload.writeU32(10);
        getMessagesPayload.writeBool(false);
        const auto getMessages = registry.dispatch(ServiceRequest{
            .service = 0x06,
            .protocolVersion = 3,
            .task = 5,
            .payload = getMessagesPayload.data(),
        });
        requireDw(getMessages && getMessages->error == 0 && getMessages->objects.empty(),
            "Messaging task 5 parses non-destructive pagination and returns the archived empty queue");
        ByteBuffer consumeMessagesPayload;
        consumeMessagesPayload.writeU32(0);
        consumeMessagesPayload.writeU32(10);
        consumeMessagesPayload.writeBool(true);
        const auto consumeMessages = registry.dispatch(ServiceRequest{
            .service = 0x06,
            .protocolVersion = 3,
            .task = 5,
            .payload = consumeMessagesPayload.data(),
        });
        requireDw(consumeMessages && consumeMessages->error == 0 && consumeMessages->objects.empty(),
            "Messaging task 5 parses destructive pagination and returns the archived empty queue");
        ByteBuffer malformedGetMessagesPayload;
        malformedGetMessagesPayload.writeU32(0);
        malformedGetMessagesPayload.writeU32(10);
        const auto malformedGetMessages = registry.dispatch(ServiceRequest{
            .service = 0x06,
            .protocolVersion = 3,
            .task = 5,
            .payload = malformedGetMessagesPayload.data(),
        });
        requireDw(malformedGetMessages && malformedGetMessages->error == 1000,
            "Messaging task 5 rejects a request without its consume flag");

        constexpr std::string_view mmbook = "mmbook 796 VL9EglIzBwA= 0";
        ByteBuffer nestedCommand;
        nestedCommand.useDataTypes(false);
        nestedCommand.writeBlob(std::span(
            reinterpret_cast<const std::uint8_t *>(mmbook.data()), mmbook.size()));
        ByteBuffer localCommandPayload;
        localCommandPayload.writeU64(session.snapshot().userId);
        localCommandPayload.writeBlob(nestedCommand.data());
        const std::array<std::uint8_t, 1> localCommandTrailing{};
        localCommandPayload.writeRaw(localCommandTrailing);
        const auto localCommand = registry.dispatch(ServiceRequest{
            .service = 0x06,
            .protocolVersion = 3,
            .task = 14,
            .payload = localCommandPayload.data(),
        });
        requireDw(localCommand && localCommand->error == 0 && directPushes.size() == 1 &&
            directPushes.front().first == 2 && directPushes.front().second == fromHex(
                "08150000000adec0adde0100100110416c776179736f66666c696e6500"
                "1308130000000f0000006d6d626f6f6b206163636570746564"),
            "Messaging task 14 reproduces the archived local mmbook event-21 push exactly");

        constexpr std::string_view mmstart =
            "mmstart sv_resetServer; 2486 1; 3265 12; 2489 0; playlist 26; "
            "start_map_rotate_once 0";
        ByteBuffer nestedBooking;
        nestedBooking.useDataTypes(false);
        nestedBooking.writeBlob(std::span(
            reinterpret_cast<const std::uint8_t *>(mmstart.data()), mmstart.size()));
        ByteBuffer bookingPayload;
        bookingPayload.writeU64(session.snapshot().userId);
        bookingPayload.writeBlob(nestedBooking.data());
        const auto booking = registry.dispatch(ServiceRequest{
            .service = 0x06,
            .protocolVersion = 3,
            .task = 14,
            .payload = bookingPayload.data(),
        });
        requireDw(booking && booking->error == 0 && bookingCommand == mmstart &&
            directPushes.size() == 1,
            "Messaging task 14 routes the client's complete mmstart command to the game server");

        const nlohmann::json remoteEvent{
            { "Sendername", "Remote" },
            { "Recipient", session.snapshot().userId },
            { "SenderID", 0x1100001DEADC002ULL },
            { "Message", message },
        };
        const auto instantPush = InstantMessageService::decodeInstantPush(
            remoteEvent.dump(), session.snapshot().userId);
        requireDw(instantPush == fromHex(
            "08150000000a02c0adde010010011052656d6f7465001308020000006869"),
            "instant-message event 21 matches the archived field order and exact bytes");

        auto wrongRecipient = remoteEvent;
        wrongRecipient["Recipient"] = 0x1100001DEADC099ULL;
        requireDw(!InstantMessageService::decodeInstantPush(
            wrongRecipient.dump(), session.snapshot().userId),
            "instant-message receive filters events addressed to another user");
        auto invalidMessage = remoteEvent;
        invalidMessage["Message"] = nlohmann::json::array({ 256 });
        requireDw(!InstantMessageService::decodeInstantPush(
            invalidMessage.dump(), session.snapshot().userId) &&
            !InstantMessageService::decodeInstantPush("not-json", session.snapshot().userId),
            "instant-message receive rejects invalid JSON and message bytes outside uint8 range");

        std::vector<std::pair<std::uint8_t, std::vector<std::uint8_t>>> busPushes;
        messageBus.subscribe("Demonware::Instantmessage",
            [&busPushes, &session](const std::uint64_t, const std::string_view payload)
            {
                if (auto push = InstantMessageService::decodeInstantPush(payload, session.snapshot().userId))
                    busPushes.emplace_back(2, std::move(*push));
            });
        const auto busPacket = LanDiscovery::encodePacket(
            "Demonware::Instantmessage", 0x2222, remoteEvent.dump());
        requireDw(messageBus.ingestPacket(busPacket, 0x0100007F) &&
            busPushes.size() == 1 && busPushes.front().first == 2 &&
            busPushes.front().second == *instantPush,
            "legacy MEEP ingest converts a remote instant message to one type-2 lobby push");

        requireDw(registry.taskName(0x06, 5) == "Messaging::readQueuedMessages" &&
            registry.taskName(0x06, 14) == "Messaging::sendGlobalInstantMessage" &&
            registry.taskName(0x06, 18) == "Messaging::sendInstantMessage",
            "Messaging registers all three recovered service-0x06 tasks");
    }

    void testFriends2Service()
    {
        using namespace AlwaysofflineRe::Demonware;

        AuthSession session;
        ServiceRegistry registry;
        Friends2Service service(session);
        service.registerTasks(registry);

        ByteBuffer payload;
        payload.writeU32(100);
        const std::array<std::uint8_t, 3> capturedPadding{};
        payload.writeRaw(capturedPadding);
        const auto response = registry.dispatch(ServiceRequest{
            .service = 0x09,
            .protocolVersion = 3,
            .task = 0x1A,
            .payload = payload.data(),
        });
        requireDw(response && response->transaction == (OriginalTransactionPrefix | 1) &&
            response->error == 0 && response->task == 0x1A && response->objects.size() == 1,
            "Friends2 task 0x1A returns the archived local friend");
        requireDw(registry.taskName(0x09, 0x1A) == "Friends2::getFriends",
            "Friends2 task 0x1A registration is explicit");

        ByteBuffer object(response->objects.front());
        std::uint64_t userId{};
        std::string encodedUsername;
        std::uint8_t flag{};
        bool online{};
        std::vector<std::uint8_t> presence;
        requireDw(object.readU64(userId) && userId == session.snapshot().userId &&
            object.readString(encodedUsername) && encodedUsername == "QWx3YXlzb2ZmbGluZQ==" &&
            object.readU8(flag) && flag == 0 && object.readBool(online) && online &&
            object.readBlob(presence) && presence.size() == 136 && object.empty() && object.valid(),
            "Friends2 object matches the recovered five-field serializer");

        std::vector<std::uint8_t> expectedPresence(136);
        expectedPresence[28] = 0x6D;
        expectedPresence[29] = 0x75;
        expectedPresence[32] = 0x6B;
        expectedPresence[33] = 0x75;
        expectedPresence[36] = 0x6C;
        expectedPresence[37] = 0x75;
        expectedPresence[44] = 0x10;
        expectedPresence[120] = 0x04;
        expectedPresence[121] = 0x04;
        requireDw(presence == expectedPresence,
            "Friends2 presence blob matches the decrypted startup response");

        ByteBuffer pagedPayload;
        pagedPayload.writeU32(100);
        pagedPayload.writeU32(1);
        const auto paged = registry.dispatch(ServiceRequest{
            .service = 0x09,
            .protocolVersion = 3,
            .task = 0x1A,
            .payload = pagedPayload.data(),
        });
        requireDw(paged && paged->error == 0 && paged->objects.empty(),
            "Friends2 offset skips the single local friend");
    }

    void testStorage2Service()
    {
        using namespace AlwaysofflineRe::Demonware;

        AuthSession session;
        session.update(AuthIdentity{
            .titleId = 1004,
            .userId = 0x1100001DEADC0DEULL,
            .username = "Alwaysoffline",
        });
        ServiceRegistry registry;
        const auto fixtures = std::filesystem::path(__FILE__).parent_path() / "Fixtures";
        const auto sandbox = std::filesystem::temp_directory_path() / "AlwaysofflineReStorage2Tests";
        std::error_code filesystemError;
        std::filesystem::remove_all(sandbox, filesystemError);
        std::filesystem::copy(fixtures, sandbox,
            std::filesystem::copy_options::recursive | std::filesystem::copy_options::overwrite_existing);
        Storage2Service storage(session, sandbox);
        storage.registerTasks(registry);
        requireDw(registry.taskName(0x0A, 10) == "bdStorage::uploadFile" &&
            registry.taskName(0x0A, 12) == "bdStorage::getFile",
            "Storage2 user-file tasks use the recovered Demonware interface names");

        ByteBuffer listPayload;
        listPayload.writeString("");
        listPayload.writeU32(0);
        listPayload.writeU16(32);
        listPayload.writeU16(0);
        listPayload.writeString("broadcast.info");
        const auto list = registry.dispatch(ServiceRequest{
            .service = 0x0A,
            .protocolVersion = 3,
            .task = 20,
            .payload = listPayload.data(),
        });
        requireDw(list && list->transaction == (OriginalTransactionPrefix | 1) && list->error == 0,
            "Storage2 contextual list dispatches with an assigned transaction");
        requireDw(list->objects.size() == 1, "Storage2 filename filter returns one publisher file");

        ByteBuffer listEnvelope(list->serialize());
        std::uint64_t listTransaction{};
        std::uint32_t listError{};
        std::uint8_t listTask{};
        std::uint32_t totalResults{};
        std::uint32_t serializedResults{};
        requireDw(listEnvelope.readU64(listTransaction) && listTransaction == (OriginalTransactionPrefix | 1),
            "Storage2 response transaction envelope");
        requireDw(listEnvelope.readU32(listError) && listError == 0 &&
            listEnvelope.readU8(listTask) && listTask == 20, "Storage2 response status envelope");
        requireDw(listEnvelope.readU32(totalResults) && totalResults == 1 &&
            listEnvelope.readU32(serializedResults) && serializedResults == 1,
            "Storage2 response writes both result counts");
        requireDw(listEnvelope.remainingSize() == list->objects.front().size(),
            "Storage2 object follows the count envelope without another wrapper");

        ByteBuffer info(list->objects.front());
        std::uint32_t fileSize{};
        std::uint64_t id{};
        std::uint32_t createTime{};
        std::uint32_t modifiedTime{};
        bool visibility{ true };
        std::uint64_t owner{};
        std::string filename;
        std::string checksum;
        requireDw(info.readU32(fileSize) && fileSize != 0, "contextual file-info size");
        requireDw(info.readU64(id) && id == 0x2F2594CEULL, "contextual file-info FNV-1a ID");
        requireDw(info.readU32(createTime) && info.readU32(modifiedTime) && createTime == modifiedTime,
            "contextual file-info timestamps");
        requireDw(info.readBool(visibility) && !visibility, "contextual file-info visibility");
        requireDw(info.readU64(owner) && owner == 0, "contextual file-info publisher owner");
        requireDw(info.readString(filename) && filename == "broadcast.info", "contextual file-info name");
        requireDw(info.readString(checksum) && checksum.size() == 16,
            "contextual file-info binary MD5 field");
        requireDw(info.empty(), "contextual file-info field order consumed exactly");

        ByteBuffer getPayload;
        getPayload.writeString("");
        getPayload.writeString("mp_playlists_shipRetail.info");
        const auto get = registry.dispatch(ServiceRequest{
            .service = 0x0A,
            .protocolVersion = 3,
            .task = 21,
            .payload = getPayload.data(),
        });
        requireDw(get && get->transaction == (OriginalTransactionPrefix | 2) &&
            get->error == 0 && get->objects.size() == 1,
            "Storage2 playlist alias resolves to the release asset");
        ByteBuffer fileData(get->objects.front());
        std::vector<std::uint8_t> playlist;
        requireDw(fileData.readBlob(playlist) && !playlist.empty() && fileData.empty(),
            "Storage2 publisher file uses the original typed blob result");
        const auto playlistText = std::string_view(
            reinterpret_cast<const char *>(playlist.data()), playlist.size());
        requireDw(playlistText.find("rule 1011 1") != std::string_view::npos &&
            playlistText.find("rule 1011 6") == std::string_view::npos &&
            playlistText.find("rule 3265 12") != std::string_view::npos &&
            playlistText.find("mp_crash_tropical,sd,1") != std::string_view::npos,
            "Storage2 lowers only CODOL's offline playlist minimum player count");

        ByteBuffer missingPayload;
        missingPayload.writeString("");
        missingPayload.writeString("missing.info");
        const auto missing = registry.dispatch(ServiceRequest{
            .service = 0x0A,
            .protocolVersion = 3,
            .task = 21,
            .payload = missingPayload.data(),
        });
        requireDw(missing && missing->error == 1000 && missing->objects.empty(),
            "Storage2 missing publisher file returns error 1000");

        ByteBuffer userPayload;
        userPayload.writeString("");
        userPayload.writeString("the.json");
        userPayload.writeU64(0x1100001DEADC0DEULL);
        userPayload.writeString("");
        const auto userFile = registry.dispatch(ServiceRequest{
            .service = 0x0A,
            .protocolVersion = 3,
            .task = 12,
            .payload = userPayload.data(),
        });
        requireDw(userFile && userFile->transaction == (OriginalTransactionPrefix | 4) &&
            userFile->error == 0 && userFile->objects.size() == 1,
            "Storage2 captured user-file request resolves by title and owner");
        ByteBuffer userObject(userFile->objects.front());
        std::vector<std::uint8_t> userData;
        requireDw(userObject.readBlob(userData) && userObject.empty() && userData.size() == 85 &&
            std::string_view(reinterpret_cast<const char *>(userData.data()), 12) == "{\"blacklist\"",
            "Storage2 user file uses the captured typed-blob response");

        ByteBuffer missingUserPayload;
        missingUserPayload.writeString("");
        missingUserPayload.writeString("FileBriefMessage");
        missingUserPayload.writeU64(0x1100001DEADC0DEULL);
        missingUserPayload.writeString("");
        const auto missingUser = registry.dispatch(ServiceRequest{
            .service = 0x0A,
            .protocolVersion = 3,
            .task = 12,
            .payload = missingUserPayload.data(),
        });
        requireDw(missingUser && missingUser->transaction == (OriginalTransactionPrefix | 5) &&
            missingUser->error == 1000 && missingUser->objects.empty(),
            "Storage2 missing captured user file returns original error 1000");

        const std::string updatedUserJson =
            std::string(R"({"blacklist":[{"id":"76561201696194782","name":"dest1yo"}],"Recentmetlist":[]})") + '\0';
        ByteBuffer uploadPayload;
        uploadPayload.writeString("");
        uploadPayload.writeString("the.json");
        uploadPayload.writeBool(true);
        uploadPayload.writeBlob(std::span(
            reinterpret_cast<const std::uint8_t *>(updatedUserJson.data()), updatedUserJson.size()));
        uploadPayload.writeU64(0);
        uploadPayload.writeString("");
        uploadPayload.writeU32(0);
        constexpr std::array<std::uint8_t, 1> CapturedTerminator{ 0 };
        uploadPayload.writeRaw(CapturedTerminator);
        const auto upload = registry.dispatch(ServiceRequest{
            .service = 0x0A,
            .protocolVersion = 3,
            .task = 10,
            .payload = uploadPayload.data(),
        });
        requireDw(upload && upload->transaction == (OriginalTransactionPrefix | 6) &&
            upload->error == 0 && upload->objects.empty(),
            "Storage2 captured upload-file request persists the authenticated user's bytes");

        const auto updatedUserFile = registry.dispatch(ServiceRequest{
            .service = 0x0A,
            .protocolVersion = 3,
            .task = 12,
            .payload = userPayload.data(),
        });
        requireDw(updatedUserFile && updatedUserFile->error == 0 &&
            updatedUserFile->objects.size() == 1,
            "Storage2 returns the replaced user file");
        ByteBuffer updatedUserObject(updatedUserFile->objects.front());
        std::vector<std::uint8_t> updatedUserData;
        requireDw(updatedUserObject.readBlob(updatedUserData) && updatedUserObject.empty() &&
            std::string_view(reinterpret_cast<const char *>(updatedUserData.data()), updatedUserData.size()) ==
                updatedUserJson,
            "Storage2 reads back the atomically replaced user file");

        ByteBuffer foreignUserPayload;
        foreignUserPayload.writeString("");
        foreignUserPayload.writeString("the.json");
        foreignUserPayload.writeBool(true);
        foreignUserPayload.writeBlob(std::span(
            reinterpret_cast<const std::uint8_t *>(updatedUserJson.data()), updatedUserJson.size()));
        foreignUserPayload.writeU64(0x110000100000002ULL);
        foreignUserPayload.writeString("");
        foreignUserPayload.writeU32(0);
        const auto foreignUser = registry.dispatch(ServiceRequest{
            .service = 0x0A,
            .protocolVersion = 3,
            .task = 10,
            .payload = foreignUserPayload.data(),
        });
        requireDw(foreignUser && foreignUser->error == 1000 && foreignUser->objects.empty(),
            "Storage2 rejects writes to another user's file");

        std::filesystem::remove_all(sandbox, filesystemError);
    }

    void testMarketplaceBalance()
    {
        using namespace AlwaysofflineRe::Demonware;

        AuthSession session;
        ServiceRegistry registry;
        const auto fixtures = std::filesystem::path(__FILE__).parent_path() / "Fixtures";
        const auto sandbox = std::filesystem::temp_directory_path() / "AlwaysofflineReMarketplaceTests";
        std::error_code filesystemError;
        std::filesystem::remove_all(sandbox, filesystemError);
        std::filesystem::copy(fixtures, sandbox,
            std::filesystem::copy_options::recursive | std::filesystem::copy_options::overwrite_existing);
        const auto inventoryFixturePath = sandbox / "1004" / "1100001DEADC0DE" / "Inventory.json";
        {
            std::ifstream stream(inventoryFixturePath, std::ios::binary);
            auto document = nlohmann::json::parse(stream);
            document["items"].push_back({
                { "id", 10010 },
                { "quantity", 3 },
                { "expireDateTime", (std::numeric_limits<std::uint32_t>::max)() },
                { "expiryDuration", std::uint64_t{ 9223372036854776000ULL } },
                { "customSourceType", 2 },
            });
            std::ofstream output(inventoryFixturePath, std::ios::binary | std::ios::trunc);
            output << document.dump(2) << '\n';
        }
        // Registered in the SAME ORDER as Servers::registerServices (Servers.cpp): the
        // recovered-capture table first, the real services over the top of it. That order is
        // load-bearing rather than cosmetic -- registerTask is insert_or_assign, and the
        // startup table already claims 0x50/0x46 (task 70) and 0x5D/0x01 as bare empty
        // replies. Register it after the service and the parse below silently stops running.
        registerCodolStartupTasks(registry);
        MarketplaceService marketplace(session, sandbox);
        marketplace.registerTasks(registry);
        requireDw(registry.taskName(0x50, 0x46) == "Marketplace::getSkusPaginated" &&
            registry.taskName(0x5D, 0x01) == "Unknown93::getSecondaryBalance",
            "the real handlers override the recovered empty-task table, not the other way round");

        constexpr std::array DefaultItems{ 10001U, 10049U, 545U, 60185U };
        requireDw(marketplace.hasEntitlements(DefaultItems),
            "Marketplace accepts CODOL's recovered default entitlements");
        constexpr std::array PersistedItems{ 10009U, 30000U };
        requireDw(marketplace.hasEntitlements(PersistedItems),
            "Marketplace accepts live persisted inventory entitlements");
        constexpr std::array MissingItems{ 65000U };
        requireDw(!marketplace.hasEntitlements(MissingItems),
            "Marketplace rejects an item absent from inventory and CODOL defaults");
        constexpr std::uint64_t SecondUser = 0x01100001DEADC0DFull;
        const auto secondInventory = sandbox / "1004" / "1100001DEADC0DF" /
            "Inventory.json";
        std::filesystem::create_directories(secondInventory.parent_path());
        {
            nlohmann::json document{
                { "items", nlohmann::json::array({
                    { { "id", 65000 }, { "quantity", 1 } },
                }) },
            };
            std::ofstream output(secondInventory, std::ios::binary | std::ios::trunc);
            output << document.dump(2) << '\n';
        }
        requireDw(marketplace.hasEntitlements(SecondUser, MissingItems) &&
            !marketplace.hasEntitlements(session.snapshot().userId, MissingItems),
            "Marketplace resolves persisted entitlements by the requested XUID");

        const auto entitlementRoot = sandbox / "Entitlement";
        const auto entitlementInventory = entitlementRoot / "1004" /
            "1100001DEADC0DE" / "Inventory.json";
        std::filesystem::create_directories(entitlementInventory.parent_path());
        {
            nlohmann::json document{
                { "items", nlohmann::json::array({
                    {
                        { "id", 64000 },
                        { "quantity", 1 },
                        { "expireDateTime", 1 },
                    },
                    {
                        { "id", 64001 },
                        { "quantity", 0 },
                    },
                }) },
            };
            std::ofstream output(
                entitlementInventory, std::ios::binary | std::ios::trunc);
            output << document.dump(2) << '\n';
        }
        MarketplaceService restrictiveMarketplace(session, entitlementRoot);
        constexpr std::array ExpiredItems{ 64000U };
        requireDw(!restrictiveMarketplace.hasEntitlements(ExpiredItems),
            "Marketplace rejects an expired persisted entitlement");
        constexpr std::array EmptyItems{ 64001U };
        requireDw(!restrictiveMarketplace.hasEntitlements(EmptyItems),
            "Marketplace rejects a zero-quantity persisted entitlement");

        ByteBuffer payload;
        payload.writeU32(2);
        constexpr std::array<std::uint8_t, 3> CapturedPadding{};
        payload.writeRaw(CapturedPadding);
        const auto response = registry.dispatch(ServiceRequest{
            .service = 0x50,
            .protocolVersion = 3,
            .task = 130,
            .payload = payload.data(),
        });
        requireDw(response && response->error == 0 && response->objects.size() == 2,
            "Marketplace task 130 returns configured wallet balances");
        requireDw(registry.taskName(0x50, 32) == "Marketplace::getBalanceLegacy" &&
            registry.taskName(0x50, 130) == "Marketplace::getBalance",
            "legacy and CODOL balance task registrations coexist");

        std::array<std::uint8_t, 2> types{};
        std::array<std::uint32_t, 2> amounts{};
        for (std::size_t index = 0; index != response->objects.size(); ++index)
        {
            ByteBuffer wallet(response->objects[index]);
            requireDw(wallet.readU8(types[index]) && wallet.readU32(amounts[index]) && wallet.empty(),
                "Marketplace wallet object is uint8 type plus uint32 amount");
        }
        requireDw(types == std::array<std::uint8_t, 2>{ 1, 2 } &&
            amounts == std::array<std::uint32_t, 2>{ 2500, 50 },
            "Marketplace wallet asset values survive serialization");

        ByteBuffer inventoryPayload;
        inventoryPayload.writeString("");
        inventoryPayload.writeU16(20000);
        constexpr std::array<std::uint8_t, 1> InventoryPadding{};
        inventoryPayload.writeRaw(InventoryPadding);
        const auto inventory = registry.dispatch(ServiceRequest{
            .service = 0x50,
            .protocolVersion = 3,
            .task = 203,
            .payload = inventoryPayload.data(),
        });
        requireDw(inventory && inventory->error == 0 && inventory->objects.size() == 3,
            "Marketplace task 203 returns persistent player inventory");
        requireDw(registry.taskName(0x50, 203) == "Marketplace::getInventory",
            "CODOL inventory task registration is explicit");

        ByteBuffer pagedInventoryPayload;
        pagedInventoryPayload.writeString("");
        pagedInventoryPayload.writeRaw(InventoryPadding);
        const auto pagedInventory = registry.dispatch(ServiceRequest{
            .service = 0x50,
            .protocolVersion = 3,
            .task = 230,
            .payload = pagedInventoryPayload.data(),
        });
        requireDw(pagedInventory && pagedInventory->error == 0 &&
            pagedInventory->objects == inventory->objects,
            "Marketplace task 230 preserves persistent inventory during late CODOL initialization");
        requireDw(registry.taskName(0x50, 230) == "Marketplace::getInventoryPaged",
            "CODOL paged inventory task registration is explicit");

        constexpr std::array<std::uint32_t, 3> ExpectedIds{ 10009, 30000, 10010 };
        for (std::size_t index = 0; index != inventory->objects.size(); ++index)
        {
            ByteBuffer item(inventory->objects[index]);
            std::uint64_t owner{};
            std::string platform;
            std::uint32_t id{};
            std::uint32_t quantity{};
            std::uint32_t unknown{};
            std::vector<std::uint8_t> itemData;
            std::uint32_t expiration{};
            std::int64_t expiryTime{};
            std::uint16_t collisionField{};
            std::uint32_t modifiedTime{};
            std::uint8_t customSourceType{};
            requireDw(item.readU64(owner) && item.readString(platform) && item.readU32(id) &&
                item.readU32(quantity) && item.readU32(unknown) && item.readBlob(itemData) &&
                item.readU32(expiration) && item.readI64(expiryTime) && item.readU16(collisionField) &&
                item.readU32(modifiedTime) && item.readU8(customSourceType) && item.empty(),
                "CODOL inventory object matches the recovered field order");
            requireDw(owner == session.snapshot().userId && platform == "steam" && id == ExpectedIds[index] &&
                quantity == index + 1 && unknown == 0 && itemData == std::vector<std::uint8_t>{ 2 } &&
                expiration == (std::numeric_limits<std::uint32_t>::max)() &&
                expiryTime == (std::numeric_limits<std::int64_t>::max)() && collisionField == 2 &&
                modifiedTime == (std::numeric_limits<std::uint32_t>::max)() && customSourceType == index,
                "CODOL inventory values match the persistent fixture");
        }

        ByteBuffer purchaseInput;
        purchaseInput.writeString("");
        purchaseInput.writeU32(1);
        purchaseInput.writeU32(23556);
        purchaseInput.writeU32(1);
        purchaseInput.writeU32(1);
        purchaseInput.writeBool(false);
        purchaseInput.writeU32(1);
        purchaseInput.writeU64(0);
        purchaseInput.writeString("");
        purchaseInput.writeU32(0);
        purchaseInput.writeU32(0);
        purchaseInput.writeU8(0);
        purchaseInput.writeU32(1);
        constexpr std::array<std::uint8_t, 1> PurchasePadding{};
        purchaseInput.writeRaw(PurchasePadding);
        const auto purchasePayload = purchaseInput.data();
        const auto purchase = registry.dispatch(ServiceRequest{
            .service = 0x50,
            .protocolVersion = 3,
            .task = 154,
            .payload = purchasePayload,
        });
        requireDw(purchase && purchase->error == 0 && purchase->objects.empty(),
            "Marketplace task 154 commits a mapped immediate-purchase request");
        requireDw(registry.taskName(0x50, 154) == "Marketplace::purchaseSkus",
            "CODOL purchase task registration is explicit");

        auto invalidPurchasePayload = purchasePayload;
        std::fill(invalidPurchasePayload.begin() + 8, invalidPurchasePayload.begin() + 12, 0);
        const auto invalidPurchase = registry.dispatch(ServiceRequest{
            .service = 0x50,
            .protocolVersion = 3,
            .task = 154,
            .payload = invalidPurchasePayload,
        });
        requireDw(invalidPurchase && invalidPurchase->error == 1000,
            "Marketplace task 154 rejects a zero SKU");

        const auto storefrontPurchase = [&registry, &PurchasePadding](const std::uint32_t sku)
        {
            ByteBuffer input;
            input.writeString("");
            input.writeU32(1);
            input.writeU32(sku);
            input.writeU32(1);
            input.writeU32(1);
            input.writeBool(false);
            input.writeU32(1);
            input.writeU64(0);
            input.writeString("");
            input.writeU32(0);
            input.writeU32(0);
            input.writeU8(0);
            input.writeU32(0);
            input.writeRaw(PurchasePadding);
            return registry.dispatch(ServiceRequest{
                .service = 0x5D,
                .protocolVersion = 3,
                .task = 131,
                .payload = input.data(),
            });
        };
        const auto storefrontPurchase93Task4 = [&registry, &PurchasePadding](const std::uint32_t sku)
        {
            ByteBuffer input;
            input.writeString("");
            input.writeU32(1);
            input.writeU32(sku);
            input.writeU32(1);
            input.writeU32(1);
            input.writeBool(false);
            input.writeU32(1);
            input.writeU64(0);
            input.writeString("");
            input.writeU32(0);
            input.writeU32(0);
            input.writeU8(0);
            input.writeU32(0);
            input.writeRaw(PurchasePadding);
            return registry.dispatch(ServiceRequest{
                .service = 0x5D,
                .protocolVersion = 3,
                .task = 4,
                .payload = input.data(),
            });
        };
        const auto storePurchase = storefrontPurchase(23556);
        requireDw(storePurchase && storePurchase->error == 0 && storePurchase->objects.empty(),
            "Unknown93 task 131 commits the captured storefront purchase request");
        requireDw(registry.taskName(0x5D, 131) == "Unknown93::purchaseSkus",
            "CODOL storefront purchase task registration is explicit");

        const auto inventoryPath = sandbox / "1004" / "1100001DEADC0DE" / "Inventory.json";
        const auto loadSavedInventory = [&inventoryPath]
        {
            std::ifstream stream(inventoryPath, std::ios::binary);
            return nlohmann::json::parse(stream);
        };
        const auto savedInventory = loadSavedInventory();
        const auto purchased = std::ranges::find_if(savedInventory["items"], [](const nlohmann::json &item)
        {
            return item.value("id", 0) == 10036;
        });
        requireDw(purchased != savedInventory["items"].end() && purchased->value("quantity", 0) == 2,
            "repeated Marketplace purchases persist and accumulate the mapped inventory item");

        const auto unknownPurchase = storefrontPurchase(19332);
        requireDw(unknownPurchase && unknownPurchase->error == 1000,
            "an unmapped SKU fails without acknowledging a purchase that was not persisted");

        constexpr auto SecondsPerDay = std::uint32_t{ 24 * 60 * 60 };
        const auto beforePurchase = static_cast<std::uint32_t>(std::chrono::duration_cast<std::chrono::seconds>(
            std::chrono::system_clock::now().time_since_epoch()).count());
        const auto role30 = storefrontPurchase(25286);
        requireDw(role30 && role30->error == 0, "Black Lily 30-day SKU is mapped");
        const auto inventory30 = loadSavedInventory();
        const auto item30 = std::ranges::find_if(inventory30["items"], [](const nlohmann::json &item)
        {
            return item.value("id", 0) == 649;
        });
        requireDw(item30 != inventory30["items"].end() &&
            item30->value("expireDateTime", 0U) >= beforePurchase + 30 * SecondsPerDay &&
            item30->value("expireDateTime", 0U) <= beforePurchase + 30 * SecondsPerDay + 2 &&
            item30->value("expiryDuration", 0LL) == 30LL * SecondsPerDay,
            "limited character purchase persists its absolute expiration and duration");
        const auto expiration30 = item30->value("expireDateTime", 0U);

        const auto inventoryResponse30 = registry.dispatch(ServiceRequest{
            .service = 0x50,
            .protocolVersion = 3,
            .task = 203,
            .payload = inventoryPayload.data(),
        });
        bool serializedLimitedRole{};
        for (const auto &serialized : inventoryResponse30->objects)
        {
            ByteBuffer item(serialized);
            std::uint64_t owner{};
            std::string platform;
            std::uint32_t id{};
            std::uint32_t quantity{};
            std::uint32_t xp{};
            std::vector<std::uint8_t> data;
            std::uint32_t expiration{};
            std::int64_t duration{};
            if (item.readU64(owner) && item.readString(platform) && item.readU32(id) &&
                item.readU32(quantity) && item.readU32(xp) && item.readBlob(data) &&
                item.readU32(expiration) && item.readI64(duration) && id == 649)
            {
                serializedLimitedRole = expiration == expiration30 && duration == 30LL * SecondsPerDay;
            }
        }
        requireDw(serializedLimitedRole, "task 203 serializes limited character entitlement fields");

        const auto role90 = storefrontPurchase(197);
        requireDw(role90 && role90->error == 0, "Black Lily 90-day SKU is mapped");
        const auto inventory120 = loadSavedInventory();
        const auto item120 = std::ranges::find_if(inventory120["items"], [](const nlohmann::json &item)
        {
            return item.value("id", 0) == 649;
        });
        requireDw(item120 != inventory120["items"].end() &&
            item120->value("expireDateTime", 0U) == expiration30 + 90 * SecondsPerDay,
            "repeated limited character purchase extends the current entitlement");

        const auto rolePermanent = storefrontPurchase(1127);
        requireDw(rolePermanent && rolePermanent->error == 0, "Black Lily permanent SKU is mapped");
        const auto permanentInventory = loadSavedInventory();
        const auto permanentRole = std::ranges::find_if(permanentInventory["items"], [](const nlohmann::json &item)
        {
            return item.value("id", 0) == 649;
        });
        requireDw(permanentRole != permanentInventory["items"].end() &&
            permanentRole->value("expireDateTime", 0U) == (std::numeric_limits<std::uint32_t>::max)() &&
            permanentRole->value("expiryDuration", 0LL) == (std::numeric_limits<std::int64_t>::max)(),
            "permanent character purchase upgrades the entitlement without an expiration");

        const auto bundlePurchase = storefrontPurchase(60000);
        requireDw(bundlePurchase && bundlePurchase->error == 0, "multi-item Marketplace SKU is mapped");
        const auto bundleInventory = loadSavedInventory();
        const auto bundleItem7 = std::ranges::find_if(bundleInventory["items"], [](const nlohmann::json &item)
        {
            return item.value("id", 0) == 700;
        });
        const auto bundleItem30 = std::ranges::find_if(bundleInventory["items"], [](const nlohmann::json &item)
        {
            return item.value("id", 0) == 701;
        });
        const auto permanentBundleItem = std::ranges::find_if(
            bundleInventory["items"], [](const nlohmann::json &item)
        {
            return item.value("id", 0) == 702;
        });
        requireDw(bundleItem7 != bundleInventory["items"].end() &&
            bundleItem7->value("quantity", 0U) == 2 &&
            bundleItem7->value("expiryDuration", 0LL) == 7LL * SecondsPerDay &&
            bundleItem30 != bundleInventory["items"].end() &&
            bundleItem30->value("quantity", 0U) == 1 &&
            bundleItem30->value("expiryDuration", 0LL) == 30LL * SecondsPerDay &&
            permanentBundleItem != bundleInventory["items"].end() &&
            permanentBundleItem->value("expiryDuration", 0LL) ==
                (std::numeric_limits<std::int64_t>::max)(),
            "SKU-level duration applies unless an item overrides it, including permanent grants");

        // Service 93 task 4 rides the same cart as 131. Asserted separately because it was the
        // one arm the C# OLfinal server had and this backend did not, and an unregistered
        // purchase fails SILENTLY -- the client advances on the empty reply either way.
        const auto altPurchase = storefrontPurchase93Task4(23556);
        requireDw(altPurchase && altPurchase->error == 0 && altPurchase->objects.empty(),
            "service 93 task 4 commits a purchase on the same path as task 131");
        requireDw(registry.taskName(0x5D, 4) == "Unknown93::purchaseSkus",
            "service 93 task 4 is registered under the same handler as 131");

        // Service 93 task 1 -- the second wallet. The fixture holds {type 1, 2500} and
        // {type 2, 50}; the client's second getter (sub_6AF970) hunts for id 2 and returns
        // zero for anything else, so the ONE object here must be the id-2 record and not
        // whichever wallet happens to be first.
        ByteBuffer secondaryPayload;
        secondaryPayload.writeU32(1);
        const auto secondary = registry.dispatch(ServiceRequest{
            .service = 0x5D,
            .protocolVersion = 3,
            .task = 1,
            .payload = secondaryPayload.data(),
        });
        requireDw(secondary && secondary->error == 0 && secondary->objects.size() == 1,
            "service 93 task 1 answers with exactly one wallet");
        {
            ByteBuffer wallet(secondary->objects.front());
            std::uint8_t walletType{};
            std::uint32_t walletAmount{};
            requireDw(wallet.readU8(walletType) && wallet.readU32(walletAmount) && wallet.empty() &&
                walletType == 2 && walletAmount == 50,
                "service 93 task 1 answers with the SECOND currency, not the first");
        }

        // Marketplace task 70, byte for byte as an OLfinal client sent it at the menu
        // (lobby_tasks.log, 2026-08-17, frame 25000000 86 50 03 46 ...): context "", page 1,
        // 2000 per page, showAll true, no sku ids, no sku types, storeVersion "1625160".
        // Asserting against the CAPTURED buffer rather than one this test re-encodes is the
        // point: a round trip through our own writer would pass even with the field order
        // wrong.
        const std::vector<std::uint8_t> capturedSkuPage{
            0x10, 0x00,                                     // string  context ""
            0x08, 0x01, 0x00, 0x00, 0x00,                   // u32     pageNum 1
            0x08, 0xD0, 0x07, 0x00, 0x00,                   // u32     itemsPerPage 2000
            0x01, 0x01,                                     // bool    showAll true
            0x08, 0x00, 0x00, 0x00, 0x00,                   // u32     numSkuIds 0
            0x08, 0x00, 0x00, 0x00, 0x00,                   // u32     numSkuTypes 0
            0x10, '1', '6', '2', '5', '1', '6', '0', 0x00,  // string  storeVersion
        };
        const auto skuPage = registry.dispatch(ServiceRequest{
            .service = 0x50,
            .protocolVersion = 3,
            .task = 70,
            .payload = capturedSkuPage,
        });
        requireDw(skuPage && skuPage->error == 0 && skuPage->objects.empty(),
            "Marketplace task 70 parses the captured request and answers an empty page");
        requireDw(registry.taskName(0x50, 70) == "Marketplace::getSkusPaginated",
            "Marketplace task 70 registration is explicit");

        // Truncation must FAIL. Without this the parse above proves nothing -- a handler that
        // ignored its payload entirely would pass it.
        auto truncatedSkuPage = capturedSkuPage;
        truncatedSkuPage.resize(truncatedSkuPage.size() - 4);
        const auto truncatedPage = registry.dispatch(ServiceRequest{
            .service = 0x50,
            .protocolVersion = 3,
            .task = 70,
            .payload = truncatedSkuPage,
        });
        requireDw(truncatedPage && truncatedPage->error == 1000,
            "Marketplace task 70 rejects a request that ends early");

        requireDw(registry.taskName(0x50, 107) == "Marketplace::getDeletedSkus" &&
            registry.taskName(0x50, 174) == "Marketplace::getPendingCouponInventoryV3",
            "the two acknowledged Marketplace tasks are named rather than left to the fallback");

        // The fallback itself. A task nobody registered is still ANSWERED -- empty, error 0,
        // echoing the task id, with a transaction id drawn from the same counter -- while
        // dispatch() keeps returning nothing for it, so the log can still tell a deliberate
        // acknowledgement apart from a coverage hole.
        const ServiceRequest unregistered{ .service = 0x04, .protocolVersion = 3, .task = 13 };
        requireDw(!registry.dispatch(unregistered),
            "an unregistered task is still reported as unhandled to the caller");
        const auto acknowledged = registry.acknowledgeUnhandled(unregistered);
        requireDw(acknowledged.error == 0 && acknowledged.task == 13 &&
            acknowledged.objects.empty() && acknowledged.transaction != 0,
            "an unregistered task is acknowledged with an empty, transacted reply");

        std::filesystem::remove_all(sandbox, filesystemError);
    }

    void testRecoveredCatalog()
    {
        using AlwaysofflineRe::Demonware::Endpoint;
        using AlwaysofflineRe::Demonware::findRecoveredService;
        using AlwaysofflineRe::Demonware::recoveredServices;

        requireDw(recoveredServices().size() == 27, "all original service registrations recovered");
        const auto marketplace = findRecoveredService(Endpoint::lobby, 0x50);
        requireDw(marketplace && marketplace->legacyDispatcherRva == 0x4284C,
            "Marketplace dispatcher matches IDA");
        const auto matchmaking = findRecoveredService(Endpoint::lobby, 0x15);
        const auto matchmaking2 = findRecoveredService(Endpoint::lobby, 0x8A);
        requireDw(matchmaking && matchmaking2, "legacy and newer matchmaking services coexist");
        requireDw(findRecoveredService(Endpoint::auth, 0x0A)->legacyDispatcherRva !=
            findRecoveredService(Endpoint::lobby, 0x0A)->legacyDispatcherRva,
            "Auth and lobby registrations are endpoint scoped");
    }

    std::vector<std::uint8_t> fromHex(const std::string_view value)
    {
        std::vector<std::uint8_t> result;
        result.reserve(value.size() / 2);
        const auto digit = [](const char character) -> std::uint8_t
        {
            if (character >= '0' && character <= '9') return static_cast<std::uint8_t>(character - '0');
            return static_cast<std::uint8_t>(character - 'a' + 10);
        };
        for (std::size_t index = 0; index < value.size(); index += 2)
            result.push_back(static_cast<std::uint8_t>((digit(value[index]) << 4) | digit(value[index + 1])));
        return result;
    }

    void appendU32(std::vector<std::uint8_t> &output, const std::uint32_t value)
    {
        for (unsigned int index = 0; index != 4; ++index)
            output.push_back(static_cast<std::uint8_t>(value >> (index * 8)));
    }

    void testSessionKeyDerivation()
    {
        constexpr std::array<std::uint8_t, 24> sessionKey{
            'S', 'h', 'i', 'p', 'p', 'o', ' ', 'f', 'u', 'u', 't', 'e', ',', ' ', 'm', 'o',
            'f', 'u', '-', 'm', 'o', 'f', 'u', '!'
        };
        std::array<std::uint8_t, 64> transcript{};
        for (std::size_t index = 0; index != transcript.size(); ++index)
            transcript[index] = static_cast<std::uint8_t>(index);

        const auto keys = AlwaysofflineRe::Demonware::deriveSessionKeys(sessionKey, transcript);
        requireDw(std::vector(keys.responseId.begin(), keys.responseId.end()) == fromHex("ea09fd53518d4361"),
            "CLIENTCHAL response ID matches fixed vector");
        requireDw(std::vector(keys.requestHmac.begin(), keys.requestHmac.end()) ==
            fromHex("96548bb09f4bd93996465628b618c9d3ec09ddd5"),
            "BDDATA request HMAC key matches fixed vector");
        requireDw(std::vector(keys.responseHmac.begin(), keys.responseHmac.end()) ==
            fromHex("4395bd6340aa21bc95d9b77db1c04afc67061382"),
            "BDDATA response HMAC key matches fixed vector");
        requireDw(std::vector(keys.decrypt.begin(), keys.decrypt.end()) ==
            fromHex("71120733ba54e6ff13ded72c69deca7f"), "BDDATA decrypt key matches fixed vector");
        requireDw(std::vector(keys.encrypt.begin(), keys.encrypt.end()) ==
            fromHex("b1adf0f2663cde670df4f20fbe37fc2e"), "BDDATA encrypt key matches fixed vector");
    }

    void testCapturedLobbyCrypto()
    {
        using namespace AlwaysofflineRe::Demonware;

        std::array<std::uint8_t, 24> sessionKey{};
        constexpr std::string_view Ticket = "Tencentticket";
        std::copy(Ticket.begin(), Ticket.end(), sessionKey.begin());

        const auto clientHeader = fromHex(
            "c8000000c8000000d2000000d200000000000800117cc37079aef264");
        const auto serverHeader = fromHex(
            "16000000ab81d200000070e2fdc0b66a34927179fcb085931651");
        const auto clientAuth = fromHex(
            "95000000ab820711fb0000005a0bd20df26eed7d07601f000088d03553fbffffff03000000000000"
            "00f0066ef50e0080080862bb0bcb9b7b3333634b732b030000000000000000000000000000000000"
            "000000000000000000000000000000000000000000000000000000000000000000a02a731b2b73a3"
            "a34b1b5b2ba3030000000000000000000098a9120100000000d9e2077fac2bfe23");
        std::vector<std::uint8_t> transcript(clientHeader.begin() + 8, clientHeader.end());
        transcript.insert(transcript.end(), serverHeader.begin(), serverHeader.end());
        transcript.insert(transcript.end(), clientAuth.begin(), clientAuth.end() - 8);

        const auto keys = deriveSessionKeys(sessionKey, transcript);
        requireDw(std::vector(keys.responseId.begin(), keys.responseId.end()) ==
            fromHex("c90ed582eebb16ae"), "captured AB83 response ID is reproduced exactly");
        requireDw(std::vector(keys.requestHmac.begin(), keys.requestHmac.end()) ==
            fromHex("44a8f0765d50efb49563ab593a7c6308cec719cf"),
            "captured client request HMAC key is reproduced exactly");
        requireDw(std::vector(keys.responseHmac.begin(), keys.responseHmac.end()) ==
            fromHex("39aad030b8d22445063da2c914ae574939e2ab68"),
            "captured server response HMAC key is reproduced exactly");

        const auto requestFrame = fromHex(
            "9e000000ab8501000000377f511bae26027bd4dce2e76544d69e12126b361f8a6b4acc36a6824ce4"
            "f042d85b21d78ced8593c3e9e3bec58d9f5f48f0cfe69c9b7d462ab87bd5dedad38b2e2217736f51"
            "4f882826371f295c402366515d4546878af1647450afe11813872eab7ef5918375f36ad08d0d6ec10"
            "354c7450e08bfb2ad1890e90df180079398f77cc92ae8c77fa5356fc86b8cbc538a31aa59dd6805f00a");
        const auto request = decodeEncryptedLobbyMessage(requestFrame, keys.decrypt, keys.requestHmac);
        requireDw(request.sequence == 1 && request.messageType == 0x86 &&
            request.payload.size() >= 3 && request.payload[0] == 0x47 && request.payload[2] == 4,
            "captured client frame authenticates and decrypts");

        const auto responseFrame = fromHex(
            "3e000000ab8516000000019a32c6bd57a598c69af37f1482e40f3833e837204a36550b11b7edce6a"
            "f17ad72657dcd6df767193cb04bd9db19dcc07578adb08c11b01");
        const auto response = decodeEncryptedLobbyMessage(responseFrame, keys.encrypt, keys.responseHmac);
        ByteBuffer envelope(response.payload);
        std::uint64_t transaction{};
        std::uint32_t error{};
        std::uint8_t task{};
        std::uint32_t objectCount{};
        requireDw(response.sequence == 0x16 && response.messageType == 1 &&
            envelope.readU64(transaction) && transaction == (OriginalTransactionPrefix | 0x15) &&
            envelope.readU32(error) && error == 0 && envelope.readU8(task) && task == 1 &&
            envelope.readU32(objectCount) && objectCount == 0,
            "captured 0x5D/1 server frame authenticates as an empty success envelope");

        const ServiceResponse reconstructed{
            .transaction = OriginalTransactionPrefix | 0x15,
            .task = 1,
        };
        const auto encoded = encodeEncryptedLobbyMessage(
            reconstructed.serialize(),
            keys.encrypt,
            keys.responseHmac,
            0x16,
            std::span(responseFrame).subspan(10, 16),
            1);
        requireDw(encoded == responseFrame,
            "reconstructed 0x5D/1 response reproduces the original encrypted frame byte-for-byte");
    }

    void testEncryptedLobbyCodec()
    {
        const auto aesKey = fromHex("71120733ba54e6ff13ded72c69deca7f");
        const auto hmacKey = fromHex("4395bd6340aa21bc95d9b77db1c04afc67061382");
        const auto iv = fromHex("5eed5eed5eed5eed5eed5eed5eed5eed");
        const std::array<std::uint8_t, 7> payload{ 0x50, 0x03, 0xCB, 1, 2, 3, 4 };
        const auto frame = AlwaysofflineRe::Demonware::encodeEncryptedLobbyMessage(
            payload, aesKey, hmacKey, 17, iv);
        const auto decoded = AlwaysofflineRe::Demonware::decodeEncryptedLobbyMessage(
            frame, aesKey, hmacKey);
        requireDw(decoded.sequence == 17, "encrypted lobby sequence round trip");
        requireDw(decoded.messageType == 0x86, "encrypted lobby request type round trip");
        requireDw(decoded.payload == std::vector(payload.begin(), payload.end()),
            "encrypted lobby payload round trip");

        auto damaged = frame;
        damaged.back() ^= 1;
        bool rejected = false;
        try
        {
            static_cast<void>(AlwaysofflineRe::Demonware::decodeEncryptedLobbyMessage(
                damaged, aesKey, hmacKey));
        }
        catch (...)
        {
            rejected = true;
        }
        requireDw(rejected, "encrypted lobby HMAC damage is rejected");
    }

    void testLobbyStateMachine()
    {
        using namespace AlwaysofflineRe::Demonware;
        ServiceRegistry registry;
        registry.registerTask(0x50, 0xCB, "Marketplace::getInventory", [](const auto &request)
        {
            return ServiceResponse{ .transaction = 7, .error = 0, .task = request.task };
        });
        LobbyProtocol protocol(registry);

        std::vector<std::uint8_t> header;
        appendU32(header, 0xC8);
        appendU32(header, 0xC8);
        for (std::size_t index = 8; index != 28; ++index)
            header.push_back(static_cast<std::uint8_t>(index));

        std::vector<std::uint8_t> auth;
        appendU32(auth, 38);
        auth.push_back(0xAB);
        auth.push_back(0x82);
        auth.resize(42, 0x5A);

        protocol.receive(std::span(header).first(3));
        requireDw(protocol.takeOutput(4096).empty(), "fragmented header waits for completion");
        std::vector<std::uint8_t> combined(header.begin() + 3, header.end());
        combined.insert(combined.end(), auth.begin(), auth.end());
        protocol.receive(combined);
        const auto handshakeOutput = protocol.takeOutput(4096);
        requireDw(handshakeOutput.size() == 40, "header ACK and auth-done are queued together");
        requireDw(handshakeOutput[4] == 0xAB && handshakeOutput[5] == 0x81,
            "server header ACK type");
        requireDw(handshakeOutput[30] == 0xAB && handshakeOutput[31] == 0x83,
            "server auth-done type");
        requireDw(protocol.phase() == LobbyPhase::established, "lobby reaches established phase");

        const std::array<std::uint8_t, 3> request{ 0x50, 0x03, 0xCB };
        const std::array<std::uint8_t, 16> iv{};
        const auto requestFrame = encodeEncryptedLobbyMessage(
            request, protocol.keys().decrypt, protocol.keys().requestHmac, 1, iv);
        protocol.receive(requestFrame);
        const auto responseFrame = protocol.takeOutput(4096);
        requireDw(!responseFrame.empty(), "registered service produces an encrypted reply");
        const auto response = decodeEncryptedLobbyMessage(
            responseFrame, protocol.keys().encrypt, protocol.keys().responseHmac);
        requireDw(response.sequence == 1, "plaintext auth-done does not consume a server sequence");
        requireDw(response.messageType == 1, "service response uses original type-1 envelope");
        ByteBuffer envelope(response.payload);
        std::uint64_t transaction{};
        requireDw(envelope.readU64(transaction) && transaction == 7,
            "service registry response crosses the LSG transport");

        const auto pushPayload = fromHex(
            "08070000000adec0adde0100100110416c776179736f66666c696e6500"
            "0a010000000000000013080200000068690800000000");
        protocol.queuePush(pushPayload);
        const auto pushFrame = protocol.takeOutput(4096);
        requireDw(!pushFrame.empty(), "queued lobby push produces encrypted output while established");
        const auto push = decodeEncryptedLobbyMessage(
            pushFrame, protocol.keys().encrypt, protocol.keys().responseHmac);
        requireDw(push.sequence == 2 && push.messageType == 2,
            "lobby push uses the next server sequence and archived type-2 envelope");
        requireDw(push.payload.size() >= pushPayload.size() &&
            std::equal(pushPayload.begin(), pushPayload.end(), push.payload.begin()) &&
            std::all_of(push.payload.begin() + static_cast<std::ptrdiff_t>(pushPayload.size()),
                push.payload.end(), [](const std::uint8_t value) { return value == 0; }),
            "lobby type-2 payload preserves the event bytes followed only by archived block padding");
    }

    std::string base64(const std::span<const std::uint8_t> input)
    {
        std::string output(4 * ((input.size() + 2) / 3), '\0');
        const auto size = EVP_EncodeBlock(
            reinterpret_cast<unsigned char *>(output.data()),
            input.data(),
            static_cast<int>(input.size()));
        requireDw(size >= 0, "test base64 encoding");
        output.resize(static_cast<std::size_t>(size));
        return output;
    }

    std::vector<std::uint8_t> makeCodoRequest()
    {
        std::vector<std::uint8_t> request(56);
        const std::uint64_t userId = 0x1100001DEADC0DEULL;
        for (unsigned int index = 0; index != 8; ++index)
            request[6 + index] = static_cast<std::uint8_t>(userId >> (index * 8));
        constexpr std::string_view username = "Alwaysoffline";
        std::copy(username.begin(), username.end(), request.begin() + 14);
        for (std::size_t index = 0; index != 24; ++index)
            request[32 + index] = static_cast<std::uint8_t>(index + 1);
        return request;
    }

    std::string authRequestJson()
    {
        const auto codoRequest = makeCodoRequest();
        nlohmann::json extraData{
            { "token", "" },
            { "codo_request", base64(codoRequest) },
            { "codo_request_size_bits", codoRequest.size() * 8 },
        };
        nlohmann::json request{
            { "identity", "1020304" },
            { "title_id", "1004" },
            { "auth_task", "28" },
            { "iv_seed", "2295540364" },
            { "extra_data", extraData.dump() },
            { "machine_id", "" },
            { "version", "1" },
        };
        return request.dump();
    }

    std::string authTask32RequestJson()
    {
        return R"({"auth_task":"32","iv_seed":"122671949","title_id":"1004","identity":"356c4bc3","extra_data":"{\"codo_request_size_bits\": 510, \"codo_request\": \"TQMAVZnbWJkbHV3a2FoZXeiJGWxWTQUMmmU1hLkn9UG4FLgOmEEN4MRyoCi2+bglbepJ+6XGr4lGM/IrW+FUKw==\"}"})";
    }

    void testAuth3Protocol()
    {
        using namespace AlwaysofflineRe::Demonware;
        AuthSession session;
        Auth3Protocol protocol(session);
        const auto result = protocol.authenticate(authRequestJson());
        requireDw(result.titleId == 1004 && result.authTask == 28, "Auth3 request fields parse");
        requireDw(result.userId == 0x1100001DEADC0DEULL && result.username == "Alwaysoffline",
            "CODOL identity is recovered from codo_request");

        const auto response = nlohmann::json::parse(result.json);
        requireDw(response["code"] == "700" && response["auth_task"] == "29",
            "Auth3 success response contract");
        requireDw(response["identity"] == "1020304" && response["iv_seed"] == "2295540364",
            "Auth3 echoes identity and IV seed");
        requireDw(response["client_ticket"] == response["server_ticket"],
            "original CODOL client/server ticket behavior");
        requireDw(!response.contains("username") && !response.contains("extended_data"),
            "CODOL Auth3 extension fields are not emitted at the top level");
        const auto extraData = nlohmann::json::parse(response["extra_data"].get<std::string>());
        requireDw(extraData["username"] == "QWx3YXlzb2ZmbGluZQ==" && extraData["time_to_live"] == 9999,
            "CODOL Auth3 nested extra_data matches the archived response");
        requireDw(extraData["extended_data"].get<std::string>().size() == 350,
            "CODOL Auth3 extended_data token is complete");

        std::vector<std::uint8_t> decoded(256);
        const auto ticket = response["client_ticket"].get<std::string>();
        const auto size = EVP_DecodeBlock(
            decoded.data(),
            reinterpret_cast<const unsigned char *>(ticket.data()),
            static_cast<int>(ticket.size()));
        requireDw(size == 129 && ticket.back() == '=', "Auth3 ticket base64 encoded size");
        decoded.resize(128);
        requireDw(decoded.size() == 128, "Auth3 ticket decodes to exactly 128 bytes");
        constexpr std::array<std::uint8_t, 8> ArchivedFirstBlock{
            0xF9, 0x73, 0x96, 0x80, 0xE7, 0x77, 0xE3, 0xBB,
        };
        requireDw(std::equal(ArchivedFirstBlock.begin(), ArchivedFirstBlock.end(), decoded.begin()),
            "CODOL ticket encryption reproduces the archived stable first block");

        const auto snapshot = session.snapshot();
        requireDw(snapshot.titleId == 1004 && snapshot.userId == 0x1100001DEADC0DEULL,
            "Auth3 identity enters shared session state");
        requireDw(std::equal(snapshot.sessionKey.begin(), snapshot.sessionKey.end(), makeCodoRequest().begin() + 32),
            "task 28 copies its raw 24-byte session key");

        AuthSession task32Session;
        Auth3Protocol task32Protocol(task32Session);
        const auto task32Result = task32Protocol.authenticate(authTask32RequestJson());
        requireDw(task32Result.authTask == 32 && task32Result.userId == 0x1100001DEADC0DEULL &&
            task32Result.username == "Alwaysoffline", "real task 32 request preserves archived identity defaults");
        const auto task32Response = nlohmann::json::parse(task32Result.json);
        requireDw(task32Response["auth_task"] == "33" && task32Response["identity"] == "356c4bc3" &&
            task32Response["iv_seed"] == "122671949", "real task 32 response echoes request fields");
        std::vector<std::uint8_t> task32Ticket(256);
        const auto task32Ticket64 = task32Response["client_ticket"].get<std::string>();
        const auto task32TicketSize = EVP_DecodeBlock(
            task32Ticket.data(),
            reinterpret_cast<const unsigned char *>(task32Ticket64.data()),
            static_cast<int>(task32Ticket64.size()));
        requireDw(task32TicketSize == 129 && task32Ticket64.back() == '=', "task 32 ticket base64 size");
        task32Ticket.resize(128);
        constexpr std::string_view TencentTicket = "Tencentticket";
        requireDw(std::equal(TencentTicket.begin(), TencentTicket.end(), task32Ticket.begin() + 97) &&
            std::all_of(task32Ticket.begin() + 97 + TencentTicket.size(), task32Ticket.begin() + 121,
                [](const auto value) { return value == 0; }), "task 32 bitstream key enters the plaintext ticket");
        const auto task32Snapshot = task32Session.snapshot();
        requireDw(std::equal(TencentTicket.begin(), TencentTicket.end(), task32Snapshot.sessionKey.begin()) &&
            std::all_of(task32Snapshot.sessionKey.begin() + TencentTicket.size(), task32Snapshot.sessionKey.end(),
                [](const auto value) { return value == 0; }), "task 32 bitstream key enters shared session state");

        _putenv_s("OLMOD_PLATFORM_USER_ID", "01100001DEADC0DF");
        AuthSession processIdentitySession;
        _putenv_s("OLMOD_PLATFORM_USER_ID", "");
        Auth3Protocol processIdentityProtocol(processIdentitySession);
        const auto processIdentityResult = processIdentityProtocol.authenticate(authTask32RequestJson());
        requireDw(
            processIdentityResult.userId == 0x1100001DEADC0DFULL &&
            processIdentitySession.snapshot().userId == 0x1100001DEADC0DFULL,
            "task 32 preserves the launcher-owned process identity");
        const auto payloadIdentityResult = processIdentityProtocol.authenticate(authRequestJson());
        requireDw(
            payloadIdentityResult.userId == 0x1100001DEADC0DEULL,
            "task 28 remains authoritative when its native payload carries an identity");

        AuthSession configuredSession;
        auto configuredIdentity = configuredSession.snapshot();
        configuredIdentity.username = "ConfiguredPlayer";
        configuredSession.update(configuredIdentity);
        Auth3Protocol configuredProtocol(configuredSession);
        const auto configuredResult = configuredProtocol.authenticate(authRequestJson());
        requireDw(configuredResult.username == "ConfiguredPlayer" &&
            configuredSession.snapshot().username == "ConfiguredPlayer",
            "server identity config remains authoritative over the client auth username");
    }

    void testIdentityConfig()
    {
        using namespace AlwaysofflineRe::Demonware;

        const auto sandbox = std::filesystem::temp_directory_path() / "ol_mod_identity_config_test.json";
        std::error_code filesystemError;
        std::filesystem::remove(sandbox, filesystemError);
        requireDw(loadConfiguredUsername(sandbox) == DefaultUsername,
            "missing identity config uses the single source default username");

        {
            std::ofstream output(sandbox, std::ios::trunc);
            output << R"({"username":"ConfiguredPlayer"})";
        }
        requireDw(loadConfiguredUsername(sandbox) == "ConfiguredPlayer",
            "identity config loads the configured username");

        {
            std::ofstream output(sandbox, std::ios::trunc);
            output << R"({"username":"ThisNameIsFarTooLong"})";
        }
        bool rejected{};
        try
        {
            static_cast<void>(loadConfiguredUsername(sandbox));
        }
        catch (const std::runtime_error &)
        {
            rejected = true;
        }
        std::filesystem::remove(sandbox, filesystemError);
        requireDw(rejected, "identity config rejects usernames that cannot fit CODOL auth fields");

        const auto storeRoot = std::filesystem::temp_directory_path() /
            "ol_mod_player_identity_store_test";
        std::filesystem::remove_all(storeRoot, filesystemError);
        std::filesystem::create_directories(storeRoot, filesystemError);
        const auto seed = storeRoot / "Identity.json";
        {
            std::ofstream output(seed, std::ios::trunc);
            output << R"({"username":"MigratedPlayer"})";
        }
        PlayerIdentityStore store(storeRoot, seed);
        constexpr auto UserId = std::uint64_t{ 0x1100001DEADC0DEULL };
        requireDw(store.resolveDisplayName(1004, UserId) == "MigratedPlayer" &&
            std::filesystem::is_regular_file(store.identityPath(1004, UserId)),
            "player identity store migrates the legacy seed into the user profile");
        {
            std::ofstream output(seed, std::ios::trunc);
            output << R"({"username":"ChangedSeed"})";
        }
        requireDw(store.resolveDisplayName(1004, UserId) == "MigratedPlayer",
            "persisted player identity is authoritative over later migration seed changes");
        store.setDisplayName(1004, UserId, "RenamedPlayer");
        requireDw(store.resolveDisplayName(1004, UserId) == "RenamedPlayer",
            "backend display-name transaction persists for the authenticated user");

        AuthSession profileSession;
        Auth3Protocol profileProtocol(profileSession, &store);
        const auto profileResult = profileProtocol.authenticate(authRequestJson());
        requireDw(profileResult.username == "RenamedPlayer" &&
            profileSession.snapshot().username == "RenamedPlayer",
            "Auth3 resolves the server-owned player profile after reading client credentials");

        {
            std::ofstream output(store.identityPath(1004, UserId), std::ios::trunc);
            output << R"({"displayName":"NameThatIsFarTooLong"})";
        }
        rejected = false;
        try
        {
            static_cast<void>(store.resolveDisplayName(1004, UserId));
        }
        catch (const std::runtime_error &)
        {
            rejected = true;
        }
        std::filesystem::remove_all(storeRoot, filesystemError);
        requireDw(rejected, "invalid persisted player identity fails closed");
    }

    void transferClientOutput(SSL *client, AlwaysofflineRe::Demonware::Auth3TlsTransport &server)
    {
        std::array<std::uint8_t, 4096> buffer{};
        while (true)
        {
            const auto size = BIO_read(SSL_get_wbio(client), buffer.data(), static_cast<int>(buffer.size()));
            if (size <= 0)
                return;
            const auto split = std::min<int>(7, size);
            server.receive(std::span(buffer).first(static_cast<std::size_t>(split)));
            if (split != size)
                server.receive(std::span(buffer).subspan(split, static_cast<std::size_t>(size - split)));
        }
    }

    void transferServerOutput(AlwaysofflineRe::Demonware::Auth3TlsTransport &server, SSL *client)
    {
        while (true)
        {
            const auto output = server.takeOutput(4096);
            if (output.empty())
                return;
            requireDw(BIO_write(SSL_get_rbio(client), output.data(), static_cast<int>(output.size())) ==
                static_cast<int>(output.size()), "feed TLS server output to client");
        }
    }

    void testAuth3TlsTransport()
    {
        using namespace AlwaysofflineRe::Demonware;
        AuthSession session;
        Auth3TlsTransport server(session, "auth3.qq.com");
        SSL_CTX *context = SSL_CTX_new(TLS_client_method());
        requireDw(context != nullptr, "create TLS client context");
        SSL_CTX_set_verify(context, SSL_VERIFY_NONE, nullptr);
        SSL_CTX_set_security_level(context, 0);
        requireDw(SSL_CTX_set_min_proto_version(context, TLS1_VERSION) == 1,
            "enable legacy-compatible TLS client");
        requireDw(SSL_CTX_set_max_proto_version(context, TLS1_VERSION) == 1,
            "force TLS 1.0 compatibility coverage");
        requireDw(SSL_CTX_set_cipher_list(context, "ALL:@SECLEVEL=0") == 1,
            "enable legacy-compatible TLS ciphers");
        SSL *client = SSL_new(context);
        requireDw(client != nullptr, "create TLS client");
        BIO *read = BIO_new(BIO_s_mem());
        BIO *write = BIO_new(BIO_s_mem());
        requireDw(read && write, "create TLS client BIOs");
        BIO_set_nbio(read, 1);
        BIO_set_nbio(write, 1);
        SSL_set_bio(client, read, write);
        SSL_set_connect_state(client);

        for (unsigned int attempt = 0; attempt != 100 && !SSL_is_init_finished(client); ++attempt)
        {
            static_cast<void>(SSL_do_handshake(client));
            transferClientOutput(client, server);
            transferServerOutput(server, client);
        }
        requireDw(SSL_is_init_finished(client), "Auth3 TLS memory-BIO handshake completes");
        X509 *certificate = SSL_get1_peer_certificate(client);
        requireDw(certificate != nullptr, "Auth3 TLS server provides a certificate");
        requireDw(X509_get_version(certificate) == 0, "Auth3 certificate matches Ayria X.509 v1");
        requireDw(X509_get_signature_nid(certificate) == NID_sha1WithRSAEncryption,
            "Auth3 certificate matches Ayria RSA/SHA-1 signature");
        X509_free(certificate);

        const auto body = authRequestJson();
        std::string request = "POST /auth/ HTTP/1.1\r\nHost: auth3.qq.com\r\nContent-Type: application/json\r\n";
        request += "Content-Length: " + std::to_string(body.size()) + "\r\n\r\n" + body;
        std::size_t written{};
        requireDw(SSL_write_ex(client, request.data(), request.size(), &written) == 1 && written == request.size(),
            "write Auth3 HTTPS request");
        transferClientOutput(client, server);
        transferServerOutput(server, client);

        std::string response;
        std::array<char, 4096> buffer{};
        for (unsigned int attempt = 0; attempt != 20; ++attempt)
        {
            std::size_t readSize{};
            if (SSL_read_ex(client, buffer.data(), buffer.size(), &readSize) == 1)
                response.append(buffer.data(), readSize);
            transferClientOutput(client, server);
            transferServerOutput(server, client);
            if (response.find("\r\n\r\n") != std::string::npos && response.find("\"code\":\"700\"") != std::string::npos)
                break;
        }
        requireDw(response.starts_with("HTTP/1.1 200 OK\r\n"), "Auth3 HTTPS response status");
        requireDw(response.find("\"code\":\"700\"") != std::string::npos,
            "Auth3 HTTPS response reaches TLS client");

        SSL_free(client);
        SSL_CTX_free(context);
    }
}

void runDemonwareTests()
{
    testByteBuffer();
    testCapturedRequestParsing();
    testServiceEnvelope();
    testCodolStartupTasks();
    testTitleUtilitiesService();
    testProfiles2Service();
    testTencentService();
    testContentUnlock2Service();
    testFriends2Service();
    testInstantMessageService();
    testRoomBoundaryServices();
    testStorage2Service();
    testMarketplaceBalance();
    testRecoveredCatalog();
    testSessionKeyDerivation();
    testCapturedLobbyCrypto();
    testEncryptedLobbyCodec();
    testLobbyStateMachine();
    testIdentityConfig();
    testAuth3Protocol();
    testAuth3TlsTransport();
}
