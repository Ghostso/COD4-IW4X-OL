#include "MarketplaceService.hpp"

#include "ByteBuffer.hpp"

#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <Windows.h>

#include <algorithm>
#include <array>
#include <charconv>
#include <chrono>
#include <fstream>
#include <limits>
#include <optional>
#include <system_error>
#include <unordered_map>
#include <unordered_set>

#include <nlohmann/json.hpp>

namespace AlwaysofflineRe::Demonware
{
    namespace
    {
        constexpr std::uint32_t InvalidRequestError = 1000;

        // Recovered from CODOL_DefaultAvailableItems_Init (0x7052F0).
        constexpr std::array<std::uint32_t, 43> DefaultEntitlements{
            10001, 10010, 10015, 10049,
            20379, 20782, 20416, 21037, 20394, 25075, 25684,
            60043, 60040, 60137,
            60076, 60080, 60083,
            60000, 60005, 60003, 60128, 60144, 60162, 12243,
            545, 789, 792, 686, 1945, 612, 592,
            60178, 60179, 60180, 60181, 60182, 60183, 60184, 60185,
            30059, 30060, 30061,
            50000,
        };

        bool isDefaultEntitlement(const std::uint32_t itemId)
        {
            return std::ranges::find(DefaultEntitlements, itemId) !=
                DefaultEntitlements.end();
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

        std::optional<std::uint64_t> jsonUnsigned(const nlohmann::json &value)
        {
            if (value.is_number_unsigned())
                return value.get<std::uint64_t>();
            if (value.is_number_integer())
            {
                const auto result = value.get<std::int64_t>();
                if (result >= 0)
                    return static_cast<std::uint64_t>(result);
            }
            return std::nullopt;
        }

        std::optional<nlohmann::json> loadJson(const std::filesystem::path &path)
        {
            std::ifstream stream(path, std::ios::binary);
            if (!stream)
                return std::nullopt;
            auto document = nlohmann::json::parse(stream, nullptr, false);
            if (document.is_discarded())
                return std::nullopt;
            return document;
        }

        bool replaceJson(const std::filesystem::path &path, const nlohmann::json &document)
        {
            std::error_code error;
            std::filesystem::create_directories(path.parent_path(), error);
            if (error)
                return false;

            auto temporary = path;
            temporary += L".writing";
            {
                std::ofstream stream(temporary, std::ios::binary | std::ios::trunc);
                if (!stream)
                    return false;
                stream << document.dump(2) << '\n';
                if (!stream)
                {
                    stream.close();
                    std::filesystem::remove(temporary, error);
                    return false;
                }
            }

            if (!MoveFileExW(temporary.c_str(), path.c_str(),
                MOVEFILE_REPLACE_EXISTING | MOVEFILE_WRITE_THROUGH))
            {
                std::filesystem::remove(temporary, error);
                return false;
            }
            return true;
        }
    }

    MarketplaceService::MarketplaceService(AuthSession &session, std::filesystem::path assetRoot)
        : session_(session), assetRoot_(std::move(assetRoot))
    {
    }

    void MarketplaceService::registerTasks(ServiceRegistry &registry)
    {
        const auto registerBalance = [this, &registry](const std::uint8_t task, std::string name)
        {
            registry.registerTask(0x50, task, std::move(name), [this](const auto &request)
            {
                return getBalance(request);
            });
        };
        registerBalance(32, "Marketplace::getBalanceLegacy");
        registerBalance(130, "Marketplace::getBalance");
        registry.registerTask(0x50, 70, "Marketplace::getSkusPaginated", [this](const auto &request)
        {
            return getSkusPaginated(request);
        });
        registry.registerTask(0x50, 154, "Marketplace::purchaseSkus", [this](const auto &request)
        {
            return purchaseSkus(request);
        });

        // Service 93 is the second half of the wallet-and-purchase pair. It stays Unknown93
        // here on purpose: 93 is absent from MW19 (which has 91/92/95/96), so it is a Tencent
        // addition that no source we have names, and the C# server's "Commerce" is labelled a
        // HYPOTHESIS in its own enum. What is measured is what it DOES. CODOL builds ONE
        // cart in sub_4A6550 and splits it by whether sub_707480 prices the sku, then hands
        // both halves the same argument list -- so 93/4 and 93/131 carry Marketplace 154's
        // request byte for byte and take the same path. 93/4 was answered by the C# OLfinal
        // server and was missing here, which is not harmless: an unregistered purchase is
        // dropped on the floor and still looks like a success, because the client's UI only
        // needs the empty reply to advance.
        registry.registerTask(0x5D, 4, "Unknown93::purchaseSkus", [this](const auto &request)
        {
            return purchaseSkus(request);
        });
        registry.registerTask(0x5D, 131, "Unknown93::purchaseSkus", [this](const auto &request)
        {
            return purchaseSkus(request);
        });
        registry.registerTask(0x5D, 1, "Unknown93::getSecondaryBalance", [this](const auto &request)
        {
            return getSecondaryBalance(request);
        });

        // Two tasks the C# OLfinal server answers with a bare empty reply and nothing else.
        // Registering them keeps that a deliberate choice instead of letting it hide in the
        // unhandled fallback, which is where a task that genuinely owes a body would sit too.
        // Both were observed exactly once each at the menu, 2026-08-17.
        const auto registerAck = [&registry](const std::uint8_t task, std::string name)
        {
            registry.registerTask(0x50, task, std::move(name), [](const auto &request)
            {
                return ServiceResponse{ .task = request.task };
            });
        };
        registerAck(107, "Marketplace::getDeletedSkus");
        registerAck(174, "Marketplace::getPendingCouponInventoryV3");
        registry.registerTask(0x50, 203, "Marketplace::getInventory", [this](const auto &request)
        {
            return getInventory(request);
        });
        registry.registerTask(0x50, 230, "Marketplace::getInventoryPaged", [this](const auto &request)
        {
            return getInventory(request);
        });
    }

    ServiceResponse MarketplaceService::getInventory(const ServiceRequest &request) const
    {
        std::size_t maximumResults{};
        ByteBuffer contextual(request.payload);
        std::string context;
        if (!contextual.readString(context))
            return ServiceResponse{ .error = InvalidRequestError, .task = request.task };
        if (request.task == 230 && contextual.valid())
        {
            maximumResults = (std::numeric_limits<std::size_t>::max)();
        }
        else
        {
            std::uint16_t contextualMaximum{};
            if (!contextual.readU16(contextualMaximum) || !contextual.valid())
                return ServiceResponse{ .error = InvalidRequestError, .task = request.task };
            maximumResults = contextualMaximum;
        }

        ServiceResponse response{ .task = request.task };
        const auto identity = session_.snapshot();
        constexpr std::array<std::uint8_t, 1> ItemData{ 2 };
        const auto inventory = loadInventory(identity.userId);
        const auto count = std::min(maximumResults, inventory.size());
        response.objects.reserve(count);
        for (std::size_t index = 0; index != count; ++index)
        {
            const auto &item = inventory[index];
            ByteBuffer object;
            object.writeU64(identity.userId);
            object.writeString("steam");
            object.writeU32(item.id);
            object.writeU32(item.quantity);
            object.writeU32(0);
            object.writeBlob(ItemData);
            object.writeU32(item.expireDateTime);
            object.writeI64(item.expiryDuration);
            object.writeU16(2);
            object.writeU32(item.modifiedTime);
            object.writeU8(item.customSourceType);
            response.objects.push_back(object.data());
        }
        return response;
    }

    ServiceResponse MarketplaceService::purchaseSkus(const ServiceRequest &request) const
    {
        ByteBuffer input(request.payload);
        std::string context;
        std::uint32_t skuCount{};
        if (!input.readString(context) || !input.readU32(skuCount) || skuCount == 0 || skuCount > 255)
            return ServiceResponse{ .error = InvalidRequestError, .task = request.task };

        std::vector<std::uint32_t> skus;
        skus.reserve(skuCount);
        for (std::uint32_t index = 0; index != skuCount; ++index)
        {
            std::uint32_t sku{};
            if (!input.readU32(sku) || sku == 0)
                return ServiceResponse{ .error = InvalidRequestError, .task = request.task };
            skus.push_back(sku);
        }

        std::uint32_t quantityCount{};
        if (!input.readU32(quantityCount) || quantityCount != skuCount)
            return ServiceResponse{ .error = InvalidRequestError, .task = request.task };
        std::vector<std::uint32_t> quantities;
        quantities.reserve(quantityCount);
        for (std::uint32_t index = 0; index != quantityCount; ++index)
        {
            std::uint32_t quantity{};
            if (!input.readU32(quantity) || quantity == 0)
                return ServiceResponse{ .error = InvalidRequestError, .task = request.task };
            quantities.push_back(quantity);
        }

        bool gift{};
        std::uint32_t accountCount{};
        if (!input.readBool(gift) || !input.readU32(accountCount) || accountCount != skuCount)
            return ServiceResponse{ .error = InvalidRequestError, .task = request.task };
        for (std::uint32_t index = 0; index != accountCount; ++index)
        {
            std::uint64_t accountId{};
            std::string accountType;
            if (!input.readU64(accountId) || !input.readString(accountType))
                return ServiceResponse{ .error = InvalidRequestError, .task = request.task };
        }

        // The remaining zero-valued fields are present in CODOL's immediate-purchase form.
        // Nonzero variants carry optional coupon/blob data whose contract is not recovered yet.
        std::uint32_t couponCount{};
        std::uint32_t metadataCount{};
        std::uint8_t sourceType{};
        std::uint32_t resultCount{};
        const auto expectedResultCount = request.service == 0x50 ? skuCount : 0;
        if ((request.service != 0x50 && request.service != 0x5D) ||
            !input.readU32(couponCount) || couponCount != 0 ||
            !input.readU32(metadataCount) || metadataCount != 0 ||
            !input.readU8(sourceType) || sourceType != 0 ||
            !input.readU32(resultCount) || resultCount != expectedResultCount)
        {
            return ServiceResponse{ .error = InvalidRequestError, .task = request.task };
        }

        const auto trailing = input.remaining();
        if (!input.valid() || (!trailing.empty() &&
            (trailing.size() != 1 || trailing.front() != 0)))
        {
            return ServiceResponse{ .error = InvalidRequestError, .task = request.task };
        }

        // Commit every grant before acknowledging the request. CODOL's success callback
        // immediately clears its cache and starts task 203 to repopulate the inventory.
        if (!applyPurchase(skus, quantities))
            return ServiceResponse{ .error = InvalidRequestError, .task = request.task };
        return ServiceResponse{ .task = request.task };
    }

    /// Marketplace task 70, getSkusPaginated -- the store listing.
    ///
    /// The request is parsed IN FULL and the reply is deliberately EMPTY. Both halves of that
    /// are decisions rather than omissions.
    ///
    /// The parse is validated against a real request instead of inherited from the C#
    /// server's reader. From an OLfinal client at the menu, 2026-08-17:
    ///
    ///     25000000 86 50 03 46          size, 0x86, service 80, proto 3, task 70
    ///     10 00                         string  context      ""
    ///     08 01000000                   u32     pageNum      1
    ///     08 D0070000                   u32     itemsPerPage 2000
    ///     01 01                         bool    showAll      true
    ///     08 00000000                   u32     numSkuIds    0
    ///     08 00000000                   u32     numSkuTypes  0
    ///     10 "1625160"                  string  storeVersion
    ///
    /// The 7 trailing zero bytes of that 48-byte frame are padding, not a field: the length
    /// prefix says 0x25 and 4 + 0x25 = 41.
    ///
    /// The EMPTY page is what the C# OLfinal server ships by default, for a reason worth
    /// carrying over verbatim: a well-formed empty reply leaves the store browsable, but a
    /// reply the client cannot deserialize marks the WHOLE marketplace service dead -- STORE
    /// and INVENTORY grey out with a warning triangle and the client does not recover in
    /// session. CODOL's SKU record is not MW19's bdMarketplaceSku; it carries two extra fields
    /// (a u8 after rentalDuration, a u32 after couponEnabled), and writing the sibling title's
    /// order is exactly how that failure was produced once already.
    ///
    /// TODO(CODOL): emit real SKUs once the record is written in the order CODOL's own
    /// deserializer reads it -- sub_A497F0 in codoMP_client_shipRetail.exe, reached from
    /// getSkusPaginated at sub_A462A0. Done when a non-empty page renders in the store and the
    /// service stays alive.
    ServiceResponse MarketplaceService::getSkusPaginated(const ServiceRequest &request) const
    {
        ByteBuffer input(request.payload);
        std::string context;
        std::uint32_t pageNumber{};
        std::uint32_t itemsPerPage{};
        bool showAll{};
        std::uint32_t skuIdCount{};
        if (!input.readString(context) || !input.readU32(pageNumber) ||
            !input.readU32(itemsPerPage) || !input.readBool(showAll) ||
            !input.readU32(skuIdCount))
        {
            return ServiceResponse{ .error = InvalidRequestError, .task = request.task };
        }

        // Read element by element rather than through readU32Array: the client writes a bare
        // count followed by individually tagged values, not a bd array (tag 0x6C), so
        // readU32Array would reject a request that is perfectly well formed.
        for (std::uint32_t index = 0; index != skuIdCount; ++index)
        {
            std::uint32_t skuId{};
            if (!input.readU32(skuId))
                return ServiceResponse{ .error = InvalidRequestError, .task = request.task };
        }

        std::uint32_t skuTypeCount{};
        if (!input.readU32(skuTypeCount))
            return ServiceResponse{ .error = InvalidRequestError, .task = request.task };
        for (std::uint32_t index = 0; index != skuTypeCount; ++index)
        {
            std::uint8_t skuType{};
            if (!input.readU8(skuType))
                return ServiceResponse{ .error = InvalidRequestError, .task = request.task };
        }

        std::string storeVersion;
        if (!input.readString(storeVersion) || !input.valid())
            return ServiceResponse{ .error = InvalidRequestError, .task = request.task };

        return ServiceResponse{ .task = request.task };
    }

    /// Service 93 task 1 -- the SECOND wallet, which is a different currency and not a second
    /// copy of the first.
    ///
    /// That 93/1 is a balance poll at all: sub_B49160 constructs TWO objects at
    /// unk_BA0B2B8 with a 32-byte stride, and sub_4A71B0 -- the only balance poller -- passes
    /// both to sub_4A4930, which issues Marketplace/130 for the first and 93/1 for the
    /// second. One poll, two services, one array. In the measured menu session the client sent
    /// 15 of these against 12 task 130s.
    ///
    /// THE CURRENCY ID IS A SELECTOR, NOT A VERSION. sub_6AF970 and sub_6AF9E0 are twin
    /// getters that walk that same two-element array for a specific id and return ZERO when
    /// they do not find it:
    ///
    ///     v2 = &byte_BA0B2C8;                 // wallet[0].currencyId
    ///     while (*v2 != 2) {                  // ...and != 1 in the other one
    ///         v2 += 32;
    ///         if (v2 >= &byte_BA0B308) { v3 = 0; goto done; }
    ///     }
    ///     v3 = dword_BA0B2CC[8 * v1];         // that wallet's amount
    ///
    /// So answering this with the id-1 record leaves the id-2 readout at zero however large
    /// its amount is. That is what the "Top Up" button covering the second balance was: a
    /// zero, correctly displayed.
    ///
    /// Which wallet is served stays data-driven -- whichever entry of the Marketplace asset
    /// carries SecondaryCurrencyId -- so a title that numbers its currencies differently is a
    /// data change rather than a code change.
    ServiceResponse MarketplaceService::getSecondaryBalance(const ServiceRequest &request) const
    {
        ByteBuffer input(request.payload);
        std::uint32_t maximumResults{};
        if (!input.readU32(maximumResults) || !input.valid())
            return ServiceResponse{ .error = InvalidRequestError, .task = request.task };

        ServiceResponse response{ .task = request.task };
        if (maximumResults == 0)
            return response;

        const auto wallets = loadWallets();
        const auto wallet = std::find_if(wallets.begin(), wallets.end(), [](const Wallet &entry)
        {
            return entry.type == SecondaryCurrencyId;
        });
        if (wallet == wallets.end())
            return response;

        ByteBuffer object;
        object.writeU8(wallet->type);
        object.writeU32(wallet->amount);
        response.objects.push_back(object.data());
        return response;
    }

    ServiceResponse MarketplaceService::getBalance(const ServiceRequest &request) const
    {
        ByteBuffer input(request.payload);
        std::uint32_t maximumResults{};
        if (!input.readU32(maximumResults) || !input.valid())
            return ServiceResponse{ .error = 1000, .task = request.task };

        const auto wallets = loadWallets();
        ServiceResponse response{ .task = request.task };
        const auto count = std::min<std::size_t>(maximumResults, wallets.size());
        response.objects.reserve(count);
        for (std::size_t index = 0; index != count; ++index)
        {
            ByteBuffer object;
            object.writeU8(wallets[index].type);
            object.writeU32(wallets[index].amount);
            response.objects.push_back(object.data());
        }
        return response;
    }

    std::vector<MarketplaceService::Wallet> MarketplaceService::loadWallets() const
    {
        const auto path = assetRoot_ / std::to_string(session_.snapshot().titleId) / "Marketplace";
        std::ifstream stream(path, std::ios::binary);
        if (!stream)
            return {};

        const auto document = nlohmann::json::parse(stream, nullptr, false);
        if (document.is_discarded() || !document.contains("Wallets") || !document["Wallets"].is_array())
            return {};

        std::vector<Wallet> result;
        for (const auto &entry : document["Wallets"])
        {
            if (!entry.is_object() || !entry.contains("Type") || !entry["Type"].is_number_unsigned() ||
                !entry.contains("Amount") || !entry["Amount"].is_number_unsigned())
                continue;
            const auto type = entry["Type"].get<std::uint64_t>();
            const auto amount = entry["Amount"].get<std::uint64_t>();
            if (type > (std::numeric_limits<std::uint8_t>::max)() ||
                amount > (std::numeric_limits<std::uint32_t>::max)())
            {
                continue;
            }
            const auto walletType = static_cast<std::uint8_t>(type);
            const auto existing = std::find_if(result.begin(), result.end(), [walletType](const Wallet &wallet)
            {
                return wallet.type == walletType;
            });
            if (existing != result.end())
                existing->amount = static_cast<std::uint32_t>(amount);
            else
                result.push_back(Wallet{ .type = walletType, .amount = static_cast<std::uint32_t>(amount) });
        }
        return result;
    }

    std::vector<MarketplaceService::InventoryItem> MarketplaceService::loadInventory(
        const std::uint64_t userId) const
    {
        const std::scoped_lock lock(inventoryMutex_);
        const auto document = loadJson(inventoryPath(userId));
        if (!document || !document->contains("items") || !(*document)["items"].is_array())
            return {};

        std::vector<InventoryItem> result;
        for (const auto &entry : (*document)["items"])
        {
            if (!entry.is_object() || !entry.contains("id"))
                continue;
            const auto id = jsonUnsigned(entry["id"]);
            if (!id || *id == 0 || *id > (std::numeric_limits<std::uint32_t>::max)())
                continue;

            InventoryItem item{ .id = static_cast<std::uint32_t>(*id) };
            if (entry.contains("quantity"))
            {
                const auto quantity = jsonUnsigned(entry["quantity"]);
                if (!quantity || *quantity == 0 || *quantity > (std::numeric_limits<std::uint32_t>::max)())
                    continue;
                item.quantity = static_cast<std::uint32_t>(*quantity);
            }
            if (entry.contains("customSourceType"))
            {
                const auto source = jsonUnsigned(entry["customSourceType"]);
                if (!source || *source > (std::numeric_limits<std::uint8_t>::max)())
                    continue;
                item.customSourceType = static_cast<std::uint8_t>(*source);
            }
            if (entry.contains("expireDateTime"))
            {
                const auto expiration = jsonUnsigned(entry["expireDateTime"]);
                if (!expiration || *expiration > (std::numeric_limits<std::uint32_t>::max)())
                    continue;
                item.expireDateTime = static_cast<std::uint32_t>(*expiration);
            }
            if (entry.contains("expiryDuration"))
            {
                const auto duration = jsonUnsigned(entry["expiryDuration"]);
                if (!duration)
                    continue;
                const auto maximumDuration = static_cast<std::uint64_t>(
                    (std::numeric_limits<std::int64_t>::max)());
                if (*duration > maximumDuration)
                {
                    if (item.expireDateTime != (std::numeric_limits<std::uint32_t>::max)())
                        continue;
                    item.expiryDuration = (std::numeric_limits<std::int64_t>::max)();
                }
                else
                {
                    item.expiryDuration = static_cast<std::int64_t>(*duration);
                }
            }
            if (entry.contains("modifiedTime"))
            {
                const auto modified = jsonUnsigned(entry["modifiedTime"]);
                if (!modified || *modified > (std::numeric_limits<std::uint32_t>::max)())
                    continue;
                item.modifiedTime = static_cast<std::uint32_t>(*modified);
            }

            const auto duplicate = std::find_if(result.begin(), result.end(), [item](const InventoryItem &existing)
            {
                return existing.id == item.id;
            });
            if (duplicate == result.end())
                result.push_back(item);
        }
        return result;
    }

    bool MarketplaceService::hasEntitlements(
        const std::span<const std::uint32_t> itemIds) const
    {
        return hasEntitlements(session_.snapshot().userId, itemIds);
    }

    bool MarketplaceService::hasEntitlements(
        const std::uint64_t userId,
        const std::span<const std::uint32_t> itemIds) const
    {
        if (!userId)
            return false;
        const auto inventory = loadInventory(userId);
        const auto now = static_cast<std::uint64_t>(
            std::chrono::duration_cast<std::chrono::seconds>(
                std::chrono::system_clock::now().time_since_epoch()).count());
        return std::ranges::all_of(itemIds, [&](const auto itemId) {
            if (!itemId)
                return true;
            if (isDefaultEntitlement(itemId))
                return true;
            const auto item = std::ranges::find_if(
                inventory, [itemId](const auto &candidate) {
                    return candidate.id == itemId && candidate.quantity != 0;
                });
            return item != inventory.end() &&
                (item->expireDateTime ==
                    (std::numeric_limits<std::uint32_t>::max)() ||
                 item->expireDateTime > now);
        });
    }

    std::shared_ptr<const std::vector<MarketplaceService::SkuGrant>> MarketplaceService::loadSkuGrants() const
    {
        const auto identity = session_.snapshot();
        const auto path = assetRoot_ / std::to_string(identity.titleId) / "MarketplaceSkus.json";
        std::error_code error;
        const auto fileSize = std::filesystem::file_size(path, error);
        if (error)
            return std::make_shared<const std::vector<SkuGrant>>();
        const auto writeTime = std::filesystem::last_write_time(path, error);
        if (error)
            return std::make_shared<const std::vector<SkuGrant>>();

        const std::scoped_lock cacheLock(skuGrantsMutex_);
        if (skuGrantsCache_ && skuGrantsCachePath_ == path &&
            skuGrantsCacheSize_ == fileSize && skuGrantsCacheWriteTime_ == writeTime)
        {
            return skuGrantsCache_;
        }

        const auto document = loadJson(path);
        if (!document || !document->contains("skus") || !(*document)["skus"].is_array())
            return std::make_shared<const std::vector<SkuGrant>>();

        std::vector<SkuGrant> result;
        result.reserve((*document)["skus"].size());
        std::unordered_map<std::uint32_t, const nlohmann::json *> products;
        if (document->contains("products") && (*document)["products"].is_array())
        {
            products.reserve((*document)["products"].size());
            for (const auto &product : (*document)["products"])
            {
                if (!product.is_object() || !product.contains("productId") ||
                    !product.contains("grants") || !product["grants"].is_array())
                {
                    continue;
                }
                const auto productId = jsonUnsigned(product["productId"]);
                if (!productId || *productId == 0 ||
                    *productId > (std::numeric_limits<std::uint32_t>::max)())
                {
                    continue;
                }
                products.emplace(static_cast<std::uint32_t>(*productId), &product);
            }
        }

        std::unordered_set<std::uint32_t> seenSkus;
        seenSkus.reserve((*document)["skus"].size());
        for (const auto &entry : (*document)["skus"])
        {
            if (!entry.is_object() || !entry.contains("sku"))
                continue;
            const auto sku = jsonUnsigned(entry["sku"]);
            if (!sku || *sku == 0 || *sku > (std::numeric_limits<std::uint32_t>::max)())
                continue;

            const auto durationSeconds = [](const nlohmann::json &value, const std::uint32_t fallback)
                -> std::optional<std::uint32_t>
            {
                if (!value.contains("durationDays"))
                    return fallback;
                const auto days = jsonUnsigned(value["durationDays"]);
                constexpr auto SecondsPerDay = std::uint64_t{ 24 * 60 * 60 };
                if (!days ||
                    *days > (std::numeric_limits<std::uint32_t>::max)() / SecondsPerDay)
                {
                    return std::nullopt;
                }
                return static_cast<std::uint32_t>(*days * SecondsPerDay);
            };

            const auto offerDuration = durationSeconds(entry, 0);
            if (!offerDuration)
                continue;

            const auto parseItem = [&](const nlohmann::json &value) -> std::optional<ItemGrant>
            {
                if (!value.is_object() || !value.contains("itemId"))
                    return std::nullopt;
                const auto itemId = jsonUnsigned(value["itemId"]);
                if (!itemId || *itemId == 0 || *itemId > (std::numeric_limits<std::uint32_t>::max)())
                    return std::nullopt;

                ItemGrant itemGrant{
                    .item = InventoryItem{ .id = static_cast<std::uint32_t>(*itemId) },
                    .durationSeconds = *offerDuration,
                };
                if (value.contains("quantity"))
                {
                    const auto quantity = jsonUnsigned(value["quantity"]);
                    if (!quantity || *quantity == 0 ||
                        *quantity > (std::numeric_limits<std::uint32_t>::max)())
                    {
                        return std::nullopt;
                    }
                    itemGrant.item.quantity = static_cast<std::uint32_t>(*quantity);
                }
                if (value.contains("customSourceType"))
                {
                    const auto source = jsonUnsigned(value["customSourceType"]);
                    if (!source || *source > (std::numeric_limits<std::uint8_t>::max)())
                        return std::nullopt;
                    itemGrant.item.customSourceType = static_cast<std::uint8_t>(*source);
                }
                const auto itemDuration = durationSeconds(value, *offerDuration);
                if (!itemDuration)
                    return std::nullopt;
                itemGrant.durationSeconds = *itemDuration;
                return itemGrant;
            };

            SkuGrant grant{ .sku = static_cast<std::uint32_t>(*sku) };
            const nlohmann::json *grantSource = &entry;
            if (!entry.contains("grants") && entry.contains("productId"))
            {
                const auto productId = jsonUnsigned(entry["productId"]);
                if (!productId || *productId == 0 ||
                    *productId > (std::numeric_limits<std::uint32_t>::max)())
                {
                    continue;
                }
                const auto product = products.find(static_cast<std::uint32_t>(*productId));
                if (product == products.end())
                    continue;
                grantSource = product->second;
            }

            if (grantSource->contains("grants"))
            {
                if (!(*grantSource)["grants"].is_array() || (*grantSource)["grants"].empty())
                    continue;
                bool valid = true;
                for (const auto &value : (*grantSource)["grants"])
                {
                    const auto item = parseItem(value);
                    if (!item)
                    {
                        valid = false;
                        break;
                    }
                    grant.items.push_back(*item);
                }
                if (!valid)
                    continue;
            }
            else if (const auto item = parseItem(entry))
                grant.items.push_back(*item);
            else
                continue;

            if (seenSkus.insert(grant.sku).second)
                result.push_back(grant);
        }

        auto parsed = std::make_shared<const std::vector<SkuGrant>>(std::move(result));
        skuGrantsCachePath_ = path;
        skuGrantsCacheWriteTime_ = writeTime;
        skuGrantsCacheSize_ = fileSize;
        skuGrantsCache_ = parsed;
        return parsed;
    }

    bool MarketplaceService::applyPurchase(
        const std::vector<std::uint32_t> &skus,
        const std::vector<std::uint32_t> &quantities) const
    {
        if (skus.empty() || skus.size() != quantities.size())
            return false;

        const auto grants = loadSkuGrants();
        std::vector<InventoryItem> additions;
        const auto nowValue = std::chrono::duration_cast<std::chrono::seconds>(
            std::chrono::system_clock::now().time_since_epoch()).count();
        if (nowValue < 0 || nowValue > (std::numeric_limits<std::uint32_t>::max)())
            return false;
        const auto now = static_cast<std::uint32_t>(nowValue);
        for (std::size_t index = 0; index != skus.size(); ++index)
        {
            const auto grant = std::ranges::find_if(*grants, [sku = skus[index]](const SkuGrant &value)
            {
                return value.sku == sku;
            });
            if (grant == grants->end())
                return false;
            for (const auto &itemGrant : grant->items)
            {
                if (quantities[index] >
                    (std::numeric_limits<std::uint32_t>::max)() / itemGrant.item.quantity)
                {
                    return false;
                }
                auto item = itemGrant.item;
                item.quantity *= quantities[index];
                if (itemGrant.durationSeconds != 0)
                {
                    const auto totalDuration = std::uint64_t{ itemGrant.durationSeconds } * quantities[index];
                    if (totalDuration > (std::numeric_limits<std::uint32_t>::max)() - now)
                        return false;
                    item.expireDateTime = now + static_cast<std::uint32_t>(totalDuration);
                    item.expiryDuration = static_cast<std::int64_t>(totalDuration);
                    item.modifiedTime = now;
                }
                additions.push_back(item);
            }
        }

        const std::scoped_lock lock(inventoryMutex_);
        const auto path = inventoryPath(session_.snapshot().userId);
        auto document = loadJson(path).value_or(nlohmann::json{ { "items", nlohmann::json::array() } });
        if (!document.is_object() || !document.contains("items") || !document["items"].is_array())
            return false;

        for (const auto &addition : additions)
        {
            auto existing = std::ranges::find_if(document["items"], [addition](const nlohmann::json &entry)
            {
                if (!entry.is_object() || !entry.contains("id"))
                    return false;
                const auto id = jsonUnsigned(entry["id"]);
                return id && *id == addition.id;
            });
            if (existing == document["items"].end())
            {
                document["items"].push_back({
                    { "id", addition.id },
                    { "quantity", addition.quantity },
                    { "expireDateTime", addition.expireDateTime },
                    { "expiryDuration", addition.expiryDuration },
                    { "modifiedTime", addition.modifiedTime },
                    { "customSourceType", addition.customSourceType },
                });
                continue;
            }

            const auto oldQuantity = existing->contains("quantity")
                ? jsonUnsigned((*existing)["quantity"]).value_or(1)
                : 1;
            if (oldQuantity > (std::numeric_limits<std::uint32_t>::max)() - addition.quantity)
                return false;
            (*existing)["quantity"] = oldQuantity + addition.quantity;
            (*existing)["customSourceType"] = addition.customSourceType;

            constexpr auto PermanentExpiration = (std::numeric_limits<std::uint32_t>::max)();
            constexpr auto PermanentDuration = (std::numeric_limits<std::int64_t>::max)();
            const auto oldExpiration = existing->contains("expireDateTime")
                ? jsonUnsigned((*existing)["expireDateTime"]).value_or(PermanentExpiration)
                : PermanentExpiration;
            if (addition.expireDateTime == PermanentExpiration || oldExpiration == PermanentExpiration)
            {
                (*existing)["expireDateTime"] = PermanentExpiration;
                (*existing)["expiryDuration"] = PermanentDuration;
            }
            else
            {
                const auto base = std::max<std::uint64_t>(oldExpiration, now);
                const auto extension = static_cast<std::uint64_t>(addition.expiryDuration);
                if (base + extension > PermanentExpiration)
                    return false;
                const auto expiration = base + extension;
                (*existing)["expireDateTime"] = expiration;
                (*existing)["expiryDuration"] = expiration - now;
            }
            (*existing)["modifiedTime"] = now;
        }
        return replaceJson(path, document);
    }

    std::filesystem::path MarketplaceService::inventoryPath(
        const std::uint64_t userId) const
    {
        const auto identity = session_.snapshot();
        const auto ownerDirectory = userIdDirectory(userId);
        if (ownerDirectory.empty())
            return {};
        return assetRoot_ / std::to_string(identity.titleId) / ownerDirectory / "Inventory.json";
    }
}
