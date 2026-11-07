# Shared lobby/game character data audit

## Proven data defect

Alpha0022 `playerdata_editor.py` and `model_configstrings.py` still declared the
old eye/pat/knp/elp/heg/boo/han/ves/fpa/fja/hea profile order. C1 694818 calls
590d00 for slots0..17 and694850 copies those shorts unchanged; the head is slot4.
Native `codol_character_composition.c` already recognizes the old complete
fingerprint and scatters into canonical slots13,9,8,7,6,1,3,5,0,2,4 on a local copy.
That compensation does not repair the profile consumed by the lobby client.

Read-only inspection of three saved public profiles found classes0/1/2 in the
complete legacy convention. Other populated classes were canonical, including
head-only defaults. The newest inspected profile selects TF6, SC1, ZM4; SC1 is
therefore a currently selected legacy record. No mixed fingerprint was found.
Profile identities are deliberately omitted from this report.

## Source changes

Actual reference root:
`D:/CoD/CODOL Builds/Call of Duty Online 1.1.1.13/CODOL/1.1.1.13_server/alpha0022`.

- New `character_slots.py`: canonical20-slot list, unknown slots represented as
  None; pure full-fingerprint legacy normalization preserving all other rows.
- `model_configstrings.py`: canonical profile decode and legacy normalization.
  Historical static snapshot explicitly retains its legacy convention.
- `playerdata_editor.py`: canonical labels; file-open normalizes recognized rows
  in the editor's private buffer only and marks it dirty. Unknown slots remain
  preserved without being mislabeled. Explicit save rejects a file changed since
  open and makes a content-addressed backup before replacing existing content.
- Original Python source backups are under `obj/character-slots-stage/source-backups`.
- Staged migration helper `obj/character-slots-stage/migrate_character_slots.py`
  defaults to report only. Optional output is exclusively created at a distinct
  path with original compressed bytes saved alongside it; input is never written.

The category fingerprint uses known item-name prefixes, because older Python
exported category cells contain a proven hash-collision artifact (item110 was
reported en2 despite the mounted C1 table classifying it as elp). Unknown names
fail recognition. Partial or mixed rows are never guessed into another layout.

## Dry-run evidence

Latest inspected compressed profile SHA256:
`92c0da12a30344caa46a0b2601c08f6aae443d91777e30f31d491b520334ccd6`.
Dry-run proposes only these decompressed byte ranges (end exclusive):

| Class | Start | End |
| --- | --- | --- |
| 0 | 2025 (0x7e9) | 2065 (0x811) |
| 1 | 2065 (0x811) | 2105 (0x839) |
| 2 | 2105 (0x839) | 2145 (0x861) |

CRC bytes0..3 also change on a proposed output. Item values are permuted, never
replaced. No active stored profile, C1 memory, or lobby process was modified.
Existing running Python imports do not automatically reload edited source.

## Distinguish remaining native symptom

This proves stale lobby input and a recurring editor producer defect. It does
not establish why a native character remains malformed after its successful
local normalization. Native and Python variant selection differ deliberately:
Python accepts other factions/genders as low-score fallback; C1/native rejects
nonmatching or nonshared variants. Do not copy Python fallback as a skeleton fix.
Native model order, missing-geometry handling and skin/gender context need a
specific bad character/model set before attributing the remaining symptom.
No skeleton-offset assumption or part-order rewrite was made. No tests/builds.
