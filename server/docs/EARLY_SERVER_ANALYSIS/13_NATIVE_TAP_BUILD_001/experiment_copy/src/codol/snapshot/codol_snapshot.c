/* Native CoDOL section assembly. No engine structs are sent verbatim. */
#include "codol_snapshot.h"
static const codol_player_fields_t zero_player;
/* Which section refused the last CODOL_WriteSnapshot, for the server trace. */
static const char *write_failure;
const char *CODOL_WriteSnapshotFailure(void) { return write_failure; }
#define SECTION(name,call) (write_failure=name,(call))
int CODOL_WriteSnapshotDeltaNumber(codol_msg_t *m, const codol_snapshot_state_t *to,
                        const codol_snapshot_state_t *base, uint32_t delta,
                        const codol_player_array_updates_t *updates,
                        const codol_animcmd_t *commands, size_t command_count,
                        unsigned flags, int rov, codol_delta_context_t *ctx)
{
    if (!m) return 0;
    write_failure="arguments";
    if (!to || !to->player || !ctx || flags > 255 || !to->sequence ||
        to->sequence > 0x1fffffff) goto fail;
    write_failure="delta base";
    if (delta > 31 || (base && (!base->player || !base->sequence ||
        base->sequence >= to->sequence || (flags & 8) ||
        (delta && delta != to->sequence - base->sequence))) || (!base && delta)) goto fail;
    m->bit = 0; /* section byte header starts a new bit pool */
    CODOL_WriteByte(m, 0);
    CODOL_WriteLong(m, ctx->server_time);
    CODOL_WriteByte(m, delta);
    CODOL_WriteByte(m, flags);
    CODOL_WriteBits(m, base != NULL, 1);
    if (!SECTION("player state",CODOL_WritePlayerState(m, base ? base->player : &zero_player, to->player,
        updates, base ? base->hud : NULL, to->hud, rov, ctx))) goto fail;
    if (!SECTION("anim commands",CODOL_WriteAnimCommands(m, commands, command_count, ctx->server_time))) goto fail;
    if (!SECTION("actors",CODOL_WriteActors(m, base ? base->actors : NULL, base ? base->actor_count : 0,
        to->actors, to->actor_count, ctx))) goto fail;
    if (!SECTION("entities",CODOL_WriteEntities(m, base ? base->entities : NULL, base ? base->entity_count : 0,
        to->entities, to->entity_count, ctx))) goto fail;
    if (!SECTION("clients",CODOL_WriteClients(m, base ? base->clients : NULL, base ? base->client_count : 0,
        to->clients, to->client_count, ctx))) goto fail;
    /* C1 glass is a monotonic map-wide system, not an entity archive. The
     * server bridge supplies a full immutable capture; retransmission is safe
     * because client448170 only applies increasing destruction states. */
    if (!SECTION("glass",CODOL_WriteGlass(m,to->glass,to->glass_count,NULL,0))) goto fail;
    CODOL_WriteByte(m, 5);
    write_failure=m->failed ? "message full" : NULL;
    return !m->failed;
fail:
    m->failed = 1; return 0;
}
int CODOL_WriteSnapshot(codol_msg_t *m, const codol_snapshot_state_t *to,
                        const codol_snapshot_state_t *base,
                        const codol_player_array_updates_t *updates,
                        const codol_animcmd_t *commands, size_t command_count,
                        unsigned flags, int rov, codol_delta_context_t *ctx)
{
    uint32_t delta = 0;
    if (base && to && to->sequence > base->sequence) {
        delta = to->sequence - base->sequence;
        if (delta > 31) { if (m) m->failed = 1; return 0; }
    }
    return CODOL_WriteSnapshotDeltaNumber(m, to, base, delta, updates, commands,
                                           command_count, flags, rov, ctx);
}
