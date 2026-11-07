#include "sv_entity_mp.hpp"

namespace CodolGameServer
{
    bool SvEntityPool::reset(const std::uint32_t firstDynamicEntityNum)
    {
        // OLMOD(generation-safe-entity-pool): map/world transaction reset. The
        // production caller supplies CODOL's confirmed first dynamic slot 27.
        if (firstDynamicEntityNum >= EntityNumWorld)
            return false;

        entities_ = {};
        for (std::uint32_t entityNum = 0; entityNum < EntityNumWorld;
             ++entityNum)
        {
            entities_[entityNum].entityNum = entityNum;
            entities_[entityNum].otherEntityNum = EntityNumNone;
        }
        reserved_ = {};
        freeEntities_.clear();
        firstDynamicEntityNum_ = firstDynamicEntityNum;
        highWaterEntityNum_ = firstDynamicEntityNum;
        configured_ = true;
        return true;
    }

    bool SvEntityPool::reserve(const std::uint32_t entityNum)
    {
        // Reserving a slot sequential allocation has already handed out would
        // put two owners on one entity number, so this is only legal ahead of
        // the high-water mark. Re-reserving the same number is a no-op rather
        // than an error: a map may name one number in more than one table.
        if (!configured_ || entityNum < firstDynamicEntityNum_ ||
            entityNum >= EntityNumWorld || entities_[entityNum].inUse ||
            entityNum < highWaterEntityNum_)
        {
            return false;
        }
        reserved_[entityNum] = true;
        return true;
    }

    std::optional<SvEntityHandle> SvEntityPool::spawnAt(
        const std::uint32_t entityNum,
        const std::uint32_t serverTime)
    {
        if (!configured_ || entityNum >= EntityNumWorld ||
            !reserved_[entityNum] || entities_[entityNum].inUse)
        {
            return std::nullopt;
        }

        auto &entity = entities_[entityNum];
        const auto generation = entity.generation;
        entity = {
            .entityNum = entityNum,
            .generation = generation,
            .otherEntityNum = EntityNumNone,
            .birthTime = serverTime,
            .inUse = true,
        };
        return SvEntityHandle{
            .entityNum = entityNum,
            .generation = generation,
        };
    }

    std::optional<SvEntityHandle> SvEntityPool::spawn(
        const std::uint32_t serverTime)
    {
        // CODREF(g_spawn): CODOL G_Spawn 0x004E8C30 and Ghosts G_Spawn
        // 0x140168CA0 use the same 2046-slot, 500 ms FIFO reuse rule.
        if (!configured_)
            return std::nullopt;

        std::optional<std::uint32_t> entityNum;
        if (!freeEntities_.empty())
        {
            const auto candidate = freeEntities_.front();
            const auto &entity = entities_[candidate];
            if (serverTime - entity.eventTime >=
                    EntityReuseDelayMilliseconds ||
                highWaterEntityNum_ >= EntityNumWorld)
            {
                entityNum = candidate;
                freeEntities_.pop_front();
            }
        }
        if (!entityNum)
        {
            // Step over reserved numbers. They belong to the map's static
            // entities and the client resolves them against a baseline that is
            // specific to each one, so sequential allocation must not hand one
            // to a dynamic entity even while it sits unspawned.
            while (highWaterEntityNum_ < EntityNumWorld &&
                   reserved_[highWaterEntityNum_])
            {
                ++highWaterEntityNum_;
            }
            if (highWaterEntityNum_ >= EntityNumWorld)
                return std::nullopt;
            entityNum = highWaterEntityNum_++;
        }

        auto &entity = entities_[*entityNum];
        const auto generation = entity.generation;
        entity = {
            .entityNum = *entityNum,
            .generation = generation,
            .otherEntityNum = EntityNumNone,
            .birthTime = serverTime,
            .inUse = true,
        };
        return SvEntityHandle{
            .entityNum = *entityNum,
            .generation = generation,
        };
    }

    bool SvEntityPool::free(
        const SvEntityHandle handle,
        const std::uint32_t serverTime)
    {
        // CODREF(g_free_entity): CODOL G_FreeEntity 0x004E8E70 increments the
        // slot use count and returns only slots >= 27 to the FIFO. Subsystem,
        // DObj and script cleanup remain outside this source lifetime owner.
        // A reserved slot sits ABOVE the high-water mark by construction -- it
        // was withheld from sequential allocation -- so the ordinary bound
        // would refuse to free any static entity the map published through
        // spawnAt.
        if (!configured_ || handle.entityNum < firstDynamicEntityNum_ ||
            handle.entityNum >= EntityNumWorld ||
            (handle.entityNum >= highWaterEntityNum_ &&
                !reserved_[handle.entityNum]))
        {
            return false;
        }
        auto &entity = entities_[handle.entityNum];
        if (!entity.inUse || entity.generation != handle.generation)
            return false;

        const auto nextGeneration = entity.generation + 1;
        entity = {
            .entityNum = handle.entityNum,
            .generation = nextGeneration,
            .otherEntityNum = EntityNumNone,
            .eventTime = serverTime,
        };
        // A reserved number goes back to its reservation, not to the FIFO --
        // recycling it would hand a static entity's baseline to whatever spawns
        // next.
        if (!reserved_[handle.entityNum])
            freeEntities_.push_back(handle.entityNum);
        return true;
    }

    bool SvEntityPool::rollbackFree(
        const SvEntityHandle handle,
        const SvEntityLifetime &previousLifetime)
    {
        // OLMOD(entity-free-source-rollback): free() appends exactly one FIFO
        // entry. A rollback is valid only before another pool mutation and
        // restores the complete generation-owned lifetime in O(1).
        if (!configured_ || handle.entityNum < firstDynamicEntityNum_ ||
            handle.entityNum >= highWaterEntityNum_ ||
            previousLifetime.entityNum != handle.entityNum ||
            previousLifetime.generation != handle.generation ||
            !previousLifetime.inUse || freeEntities_.empty() ||
            freeEntities_.back() != handle.entityNum)
        {
            return false;
        }
        const auto &freed = entities_[handle.entityNum];
        if (freed.inUse || freed.generation != handle.generation + 1)
            return false;
        freeEntities_.pop_back();
        entities_[handle.entityNum] = previousLifetime;
        return true;
    }

    bool SvEntityPool::markFreeAfterEvent(
        const SvEntityHandle handle,
        const std::uint32_t eventTime,
        const std::uint32_t otherEntityNum)
    {
        // OLMOD(temp-event-lifetime): source scheduler metadata layered on the
        // allocator; native G_FreeEntity does not own this 300 ms policy.
        if (!configured_ || handle.entityNum < firstDynamicEntityNum_ ||
            handle.entityNum >= highWaterEntityNum_ ||
            otherEntityNum > EntityNumNone)
            return false;
        auto &entity = entities_[handle.entityNum];
        if (!entity.inUse || entity.generation != handle.generation)
            return false;
        entity.eventTime = eventTime;
        entity.otherEntityNum = otherEntityNum;
        entity.freeAfterEvent = true;
        return true;
    }

    std::vector<SvEntityHandle> SvEntityPool::expiredEventEntities(
        const std::uint32_t serverTime) const
    {
        // OLMOD(temp-event-lifetime): read-only collection; actual free and
        // native mirror removal remain one outer transaction.
        std::vector<SvEntityHandle> expired;
        if (!configured_)
            return expired;
        for (auto entityNum = firstDynamicEntityNum_;
             entityNum < highWaterEntityNum_; ++entityNum)
        {
            const auto &entity = entities_[entityNum];
            if (entity.inUse && entity.freeAfterEvent &&
                serverTime - entity.eventTime > EntityEventLifetimeMilliseconds)
            {
                expired.push_back({
                    .entityNum = entityNum,
                    .generation = entity.generation,
                });
            }
        }
        return expired;
    }

    const SvEntityLifetime *SvEntityPool::resolve(
        const SvEntityHandle handle) const
    {
        // OLMOD(generation-safe-entity-pool): stale generation fails closed.
        const auto *const entity = resolve(handle.entityNum);
        return entity && entity->generation == handle.generation
            ? entity
            : nullptr;
    }

    const SvEntityLifetime *SvEntityPool::resolve(
        const std::uint32_t entityNum) const
    {
        // OLMOD(generation-safe-entity-pool): numeric lookup is internal-only;
        // mutation APIs require a generation-bearing handle.
        //
        // The high-water mark bounds SEQUENTIAL allocation, and a reserved slot
        // is by construction outside it -- withholding the number from spawn()
        // is the whole point. Bounding lookup by it too would make every static
        // entity published through spawnAt unresolvable, and therefore invisible
        // to entity(), free() and the collision view.
        if (!configured_ || entityNum >= EntityNumWorld ||
            (entityNum >= highWaterEntityNum_ && !reserved_[entityNum]))
        {
            return nullptr;
        }
        const auto &entity = entities_[entityNum];
        return entity.inUse ? &entity : nullptr;
    }

    std::uint32_t SvEntityPool::firstDynamicEntityNum() const
    {
        return firstDynamicEntityNum_;
    }

    std::uint32_t SvEntityPool::highWaterEntityNum() const
    {
        return highWaterEntityNum_;
    }

    std::size_t SvEntityPool::freeEntityCount() const
    {
        return freeEntities_.size();
    }
}
