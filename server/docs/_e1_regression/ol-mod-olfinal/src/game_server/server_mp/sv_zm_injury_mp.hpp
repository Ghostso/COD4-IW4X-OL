#pragma once
#include <algorithm>
#include <array>
#include <cstdint>

namespace CodolGameServer
{
    // CODREF(1649370): reader674114..674183, ps+3812, eight four-byte
    // records. Renderer562070..562493 selects zombie_claw%d for style1.
    // Original zombie recordings independently carry (sequence,1,actor).
    struct SvZombieInjury
    {
        std::uint8_t sequence{}, style{};
        std::uint16_t entity{};
        bool operator==(const SvZombieInjury &) const = default;
    };
    using SvZombieInjuryRing = std::array<SvZombieInjury,8>;
    struct SvClientZombieInjuries
    {
        std::uint32_t clientNum{}, spawnSequence{};
        std::uint8_t spawnGeneration{}, cursor{};
        SvZombieInjuryRing records{};
        bool operator==(const SvClientZombieInjuries &) const = default;
    };
    inline bool SV_AppendZombieInjury(SvClientZombieInjuries &owner, std::uint32_t actor)
    {
        if (actor >= 2047 || owner.cursor >= owner.records.size()) return false;
        auto &record=owner.records[owner.cursor];
        // OLMOD(injury-producer): bounded sequence/cursor policy; native client
        // owns random claw artwork, placement and450ms fade, not the server.
        record={static_cast<std::uint8_t>(record.sequence%15+1),1,
            static_cast<std::uint16_t>(actor)};
        owner.cursor=static_cast<std::uint8_t>((owner.cursor+1)%owner.records.size());
        return true;
    }
    inline bool SV_ValidZombieInjuries(const SvClientZombieInjuries &owner)
    {
        return owner.clientNum<32 && owner.cursor<8 &&
            std::ranges::all_of(owner.records,[](const auto &r) {
                return r.sequence<=15 && r.style<=1 && r.entity<2047;
            });
    }
    template<class Writer>
    void SV_WriteZombieInjuries(Writer &message,const SvZombieInjuryRing *current,
        const SvZombieInjuryRing *baseline)
    {
        // Same acknowledged immutable frame as playerstate. Explicit zeros
        // clear an old life/subject; repeated packets never create extra hits.
        const SvZombieInjuryRing empty{};
        const auto &now=current?*current:empty, &old=baseline?*baseline:empty;
        for (unsigned i=0;i<now.size();++i)
        {
            if (now[i]==old[i]) continue;
            message.MSG_WriteBits(1,1); message.MSG_WriteBits(i,3);
            message.MSG_WriteBits(now[i].sequence,4);
            message.MSG_WriteBits(now[i].style,4);
            message.MSG_WriteBits(now[i].entity,12);
        }
        message.MSG_WriteBits(0,1);
    }
}
