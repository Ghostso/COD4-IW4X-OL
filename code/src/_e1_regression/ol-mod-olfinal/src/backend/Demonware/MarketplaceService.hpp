#pragma once

#include "AuthSession.hpp"
#include "ServiceRegistry.hpp"

#include <filesystem>
#include <limits>
#include <memory>
#include <mutex>
#include <span>
#include <vector>

namespace AlwaysofflineRe::Demonware
{
    class MarketplaceService
    {
    public:
        explicit MarketplaceService(
            AuthSession &session,
            std::filesystem::path assetRoot = L"./Ayria/Assets/Alwaysoffline");

        void registerTasks(ServiceRegistry &registry);
        [[nodiscard]] bool hasEntitlements(
            std::span<const std::uint32_t> itemIds) const;
        [[nodiscard]] bool hasEntitlements(
            std::uint64_t userId,
            std::span<const std::uint32_t> itemIds) const;

    private:
        struct Wallet
        {
            std::uint8_t type{};
            std::uint32_t amount{};
        };

        struct InventoryItem
        {
            std::uint32_t id{};
            std::uint32_t quantity{ 1 };
            std::uint32_t expireDateTime{ (std::numeric_limits<std::uint32_t>::max)() };
            std::int64_t expiryDuration{ (std::numeric_limits<std::int64_t>::max)() };
            std::uint32_t modifiedTime{ (std::numeric_limits<std::uint32_t>::max)() };
            std::uint8_t customSourceType{};
        };

        struct ItemGrant
        {
            InventoryItem item;
            std::uint32_t durationSeconds{};
        };

        struct SkuGrant
        {
            std::uint32_t sku{};
            std::vector<ItemGrant> items;
        };

        /// The currency id the client's second wallet getter (sub_6AF970) hunts for. It
        /// returns 0 for every id it does not find, so this constant is what decides whether
        /// the second balance readout has a number in it at all.
        static constexpr std::uint8_t SecondaryCurrencyId = 2;

        [[nodiscard]] ServiceResponse getBalance(const ServiceRequest &request) const;
        [[nodiscard]] ServiceResponse getSecondaryBalance(const ServiceRequest &request) const;
        [[nodiscard]] ServiceResponse getSkusPaginated(const ServiceRequest &request) const;
        [[nodiscard]] ServiceResponse getInventory(const ServiceRequest &request) const;
        [[nodiscard]] ServiceResponse purchaseSkus(const ServiceRequest &request) const;
        [[nodiscard]] std::vector<Wallet> loadWallets() const;
        [[nodiscard]] std::vector<InventoryItem> loadInventory(
            std::uint64_t userId) const;
        [[nodiscard]] std::shared_ptr<const std::vector<SkuGrant>> loadSkuGrants() const;
        [[nodiscard]] bool applyPurchase(
            const std::vector<std::uint32_t> &skus,
            const std::vector<std::uint32_t> &quantities) const;
        [[nodiscard]] std::filesystem::path inventoryPath(
            std::uint64_t userId) const;

        AuthSession &session_;
        std::filesystem::path assetRoot_;
        mutable std::mutex inventoryMutex_;
        mutable std::mutex skuGrantsMutex_;
        mutable std::filesystem::path skuGrantsCachePath_;
        mutable std::filesystem::file_time_type skuGrantsCacheWriteTime_{};
        mutable std::uintmax_t skuGrantsCacheSize_{};
        mutable std::shared_ptr<const std::vector<SkuGrant>> skuGrantsCache_;
    };
}
