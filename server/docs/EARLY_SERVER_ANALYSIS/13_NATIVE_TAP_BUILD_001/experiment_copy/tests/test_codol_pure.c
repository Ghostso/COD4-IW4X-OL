#include "server.h"
#include "codol_pure.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

server_t sv;
unsigned codol_previous_checksum_feed;
void SV_VerifyPaks_f(client_t *client);
void Com_DPrintf(conChannel_t channel, const char *format, ...) { (void)channel; (void)format; }
static int command_argc;
static const char *const *command_argv;
static const char *loaded;
int SV_Cmd_Argc(void) { return command_argc; }
char *SV_Cmd_Argv(int i) { assert(i >= 0 && i < command_argc); return (char *)command_argv[i]; }
const char *FS_LoadedIwdPureChecksums(char *out, int capacity)
{
    assert(strlen(loaded) < (size_t)capacity);
    strcpy(out, loaded); return out;
}

int main(void)
{
    static client_t client;
    const char *args[] = {"cp", "@", "-2147483648", "2147483647", "-3"};
    const char *bad[] = {"", "-", "+1", "2147483648", "-2147483649", "0x1", "1x", "1 2", "99999999999999999999"};
    const char *large[CODOL_MAX_PURE_IWDS + 3];
    char numbers[CODOL_MAX_PURE_IWDS][12], list[0x4000], aggregate[12];
    unsigned i;
    loaded = "-2147483648 2147483647 42 ";
    assert(CODOL_VerifyPureChecksums(5, args, loaded, 0));
    assert(!CODOL_VerifyPureChecksums(5, args, "-2147483648 42 ", 0));
    assert(!CODOL_VerifyPureChecksums(5, args, loaded, 1));
    assert(!CODOL_VerifyPureChecksums(5, args, "-2147483648 2147483647x", 0));
    for (i = 0; i < sizeof(bad)/sizeof(*bad); ++i) {
        args[2] = bad[i];
        assert(!CODOL_VerifyPureChecksums(5, args, loaded, 0));
    }
    args[2] = "-2147483648";
    args[3] = "-2147483648"; args[4] = "2";
    assert(!CODOL_VerifyPureChecksums(5, args, loaded, 0));
    args[3] = "2147483647"; args[4] = "-3";
    args[1] = "#"; assert(!CODOL_VerifyPureChecksums(5, args, loaded, 0)); args[1] = "@";
    assert(!CODOL_VerifyPureChecksums(CODOL_MAX_PURE_IWDS + 4, args, loaded, 0));
    assert(!CODOL_VerifyPureChecksums(2, args, loaded, 0));
    assert(!CODOL_VerifyPureChecksums(5, NULL, loaded, 0));

    command_argc = 5; command_argv = args; sv.checksumFeed = 0;
    client.localization = 8; client.pureAuthentic = 0;
    SV_VerifyPaks_f(&client);
    assert(client.pureAuthentic == 1 && client.localization == 8);
    {
        uint32_t feed;
        assert(CODOL_PureCommandFeed(5, args, &feed) && feed == 0);
        assert(!CODOL_PureCommandFeed(2, args, &feed));
        args[2] = "x"; assert(!CODOL_PureCommandFeed(5, args, &feed)); args[2] = "-2147483648";
    }
    /* C1's first cp of a gamestate is built for the previous feed: it is no
     * verdict, whatever the state was before. */
    sv.checksumFeed = 1;
    client.pureAuthentic = 0; SV_VerifyPaks_f(&client); assert(client.pureAuthentic == 0);
    client.pureAuthentic = 1; SV_VerifyPaks_f(&client); assert(client.pureAuthentic == 1);
    args[4] = "-4"; client.pureAuthentic = 0;
    SV_VerifyPaks_f(&client); assert(client.pureAuthentic == 1);
    /* Built for the current feed but naming an archive the server does not
     * have: a genuine mismatch stays impure. */
    loaded = "-2147483648 42 "; SV_VerifyPaks_f(&client); assert(client.pureAuthentic == 2);
    loaded = "-2147483648 2147483647 42 ";
    command_argc = 2; SV_VerifyPaks_f(&client); assert(client.pureAuthentic == 2);

    large[0] = "cp"; large[1] = "@"; list[0] = 0;
    for (i = 0; i < CODOL_MAX_PURE_IWDS; ++i) {
        sprintf(numbers[i], "%u", i); large[i + 2] = numbers[i];
        strcat(list, numbers[i]); strcat(list, " ");
    }
    sprintf(aggregate, "%u", CODOL_MAX_PURE_IWDS);
    large[CODOL_MAX_PURE_IWDS + 2] = aggregate;
    assert(CODOL_VerifyPureChecksums(CODOL_MAX_PURE_IWDS + 3, large, list, 0));
    strcat(list, "1024 ");
    assert(!CODOL_VerifyPureChecksums(CODOL_MAX_PURE_IWDS + 3, large, list, 0));
    puts("PASS: native CoDOL cp parser, signed limits, aggregate/feed, membership, duplicates, bounds and client purity state, stale-feed cp ignored");
    return 0;
}
