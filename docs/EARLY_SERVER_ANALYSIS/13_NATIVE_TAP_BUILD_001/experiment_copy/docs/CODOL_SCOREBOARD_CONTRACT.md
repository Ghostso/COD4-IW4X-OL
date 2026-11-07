# C1 scoreboard command contract (offline source/PE review, 2026-09-09)

Retained SendScoreboard in src/asmsource/_g_cmds_mp.asm emits seven integers per
normal multiplayer row. This is incompatible with C1's normal multiplayer parser.
Do not preserve the Python seven-column implementation as the protocol reference.

C1 producer starts at aligned 0x51faa0. Its comparison at 0x51faf5..0x51fb0a
selects the special format only for gametype `zm` (string 0xc689ac).

Normal command: `b <count> <team1> <team2> <scorelimit><rows>`.
Each row is ten integers, in this order:

1. client number
2. score (gclient +0x3380)
3. ping (-1 while connected field +0x33a4 equals 1)
4. deaths (+0x3384)
5. status icon (+0x3378)
6. integer conversion of floating-point kills (+0x3388)
7. assists (+0x338c)
8. headshots (+0x339c)
9. objectives (+0x3390)
10. result of 0x5d2480(client number)

The names/types above come from the actual 24-byte client-field records at
0xc3c0a8..0xc3c198, not equivalent offsets in another engine. Kills is type 3
(float), unlike the retained native integer field. Producer row pushes are at
0x51fba5..0x51fbff, format 0xc53a64; header is 0x51fcc9..0x51fcf1.

Consumer independently verified: command dispatcher 0x469320 reads byte map
0x46a118 then target table 0x46a024. `b` ->0x4693b5 ->0x465130.
Parser reads four header arguments; first row begins at argument 5. Row argument
cursor starts edi=7 and advances by TEN at 0x46557f, record stride64. The parser
currently caps displayed count at19 (0x46518d), although producer caps64.
Status icon 1..8 is looked up at 0x4654ba..0x4654dc through the mapped icon bank.

Special `zm` command: `4 <count><rows>`, each row is seven integers:
client, score, integer-converted kills, downs(+0x3394), revives(+0x3398),
headshots(+0x339c), ping. Producer 0x51fb5e..0x51fba0 and header0x51fca5.
Dispatcher `4` ->0x4693cb ->0x4655e0 (parser body not yet reviewed).

Tenth normal field: 0x5d2480 returns zero when dvar pointer0x16fc2a8 has false
current boolean, or client state is not5. Otherwise it calls0x590670 with
`skills` (0xc59920), `tdm` (0xc4a6a8), and native client data+0x6200d, then applies
signed integer division by100 and adds25. The input data/lookup and configuration
semantics still need tracing; do not invent a constant skill/rank value.

Next implementation work: add genuine native script-visible storage and lifecycle
for absent stats, reconcile float kills with retained native producers, implement
the skill lookup/configuration path, then replace the native scoreboard sender
with the measured normal/zm command formats. No padded-zero adapter has been
integrated. No builds, tests, assembly, emulation, or live client/server execution.
Helper parent-scoreboard-fields.py only reads PE tables offline.
