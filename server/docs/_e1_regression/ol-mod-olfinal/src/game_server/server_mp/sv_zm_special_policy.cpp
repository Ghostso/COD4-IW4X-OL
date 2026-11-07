#include "sv_zm_special_policy.hpp"
#include <limits>

namespace CodolGameServer {
// OLMOD(factory_special_pool): bounded relative-weight selection. Original
// CODOL weights and monkey reward eligibility have not been recovered.
std::uint16_t SV_FactoryPreviewWeight(std::string_view name) {
    return name=="tesla_gun_zm"?1:8;
}
const SvFactorySpecialEntry *SV_FactorySpecialEntry(std::string_view name) {
    for(const auto &entry:FactoryReconstructedBoxPool)
        if(!entry.weapon.empty() && entry.weapon==name)return &entry;
    return nullptr;
}
std::optional<std::size_t> SV_SelectFactorySpecialReward(
    std::span<const std::uint16_t> weights, std::uint32_t random) {
    std::uint32_t total{};
    for(const auto weight:weights) {
        if(total>std::numeric_limits<std::uint32_t>::max()-weight)return std::nullopt;
        total+=weight;
    }
    if(!total)return std::nullopt;
    auto ticket=random%total;
    for(std::size_t i=0;i<weights.size();++i) {
        if(ticket<weights[i])return i;
        ticket-=weights[i];
    }
    return std::nullopt;
}
}
