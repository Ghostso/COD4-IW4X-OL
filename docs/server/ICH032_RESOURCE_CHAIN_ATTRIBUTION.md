# ICH-032 — Resource Bootstrap → FastFile → Zone → Asset 全链路侦察

## Core Discovery: Data Pipeline Architecture

The CODOL data pipeline has a **three-stage architecture**:

```text
Stage 1: IIPS Download (Tencent CDN)
   IIPS downloads .ifs packages (974 files, 22.6 GB)
   Format: "nifs" magic, proprietary IIPS container
   Location: COD OL\IIPS\IIPSDownload\*.ifs
   Status: 974 files present (22.6 GB downloaded)

Stage 2: IIPS Extract/Convert (IFS2 virtual filesystem)
   IFS2 converts .ifs → .ff files
   Location: Expected in COD OL\main\ or similar
   Status: ZERO .ff files exist (conversion never happened)

Stage 3: Engine FastFile Load
   Engine loads .ff files via Zone system
   Expected first file: code_pre_gfx_mp.ff
   Search path: %s\%s%s.ff (directory + prefix + name + .ff)
   Status: Engine ready but no .ff files to load
```

## The Root Cause Chain

```text
IIPS QoS Failure (Tencent server unreachable)
       ↓
IIPS Pack Manager never initializes
       ↓
.ifs packages are NEVER converted to .ff files
       ↓
Engine looks for code_pre_gfx_mp.ff → FILE_NOT_FOUND
       ↓
Zone/Asset system never initializes
       ↓
Game never reaches playable state
```

## Key Evidence

### 1. Engine FastFile References

```text
First expected .ff:     code_pre_gfx_mp.ff (RVA 0x9BD0A0)
Search path format:     %s\%s%s.ff (RVA 0x9BDF74)
FF extension format:    %s.ff (RVA 0x9B617E)
Zone allocation:        DB_AllocXZoneMemory (RVA 0x9B61E8)
Zone error:             WIN_MAX_ZONE_ERROR (RVA 0x9B6408)
Asset error:            WIN_LOAD_ASSET_ERROR (RVA 0x9B63B8)
```

### 2. Complete Engine Config File List

```text
Config files Engine expects:
  config_mp.cfg
  fileSysCheck.cfg
  default_mp.cfg
  configure_mp.cfg
  safemode_mp.cfg
  default_xboxlive.cfg
```

### 3. Dvar System API

```text
  Dvar_GetBool, Dvar_GetInt, Dvar_GetFloat, Dvar_GetString
  Dvar_GetEnumLength, Dvar_GetEnumValue
  getdvar, setdvar, dvar_restart
```

### 4. Data Inventory

```text
.ifs files:  974 files, 22,673 MB (COD OL\IIPS\IIPSDownload\)
.ifs magic:  "nifs" (0x6E696673)
.ff files:   0 (NOWHERE in the entire workspace)
.iwd files:  0
.xpak files: 0
```

### 5. .ifs File Format

```text
Magic: "nifs" (4 bytes)
Header: Variable-length index + data blocks
Content: Contains compiled game zone data (equivalent to .ff)
IIPS/IFS2 must extract these to .ff format for the Engine
```

## Zone/Asset/Dvar Subsystem Confirmation

All subsystem strings exist in the raw EXE and are referenced by
VM-decrypted engine code (ICH-025 confirmed):

| Subsystem | Key Strings | Status |
|-----------|------------|--------|
| Zone | DB_AllocXZoneMemory, WIN_MAX_ZONE_ERROR, cross_zone | CONFIRMED |
| FastFile | loadfastfile, code_pre_gfx_mp.ff, %s.ff | CONFIRMED |
| Asset | WIN_LOAD_ASSET_ERROR, WIN_OVERRIDE_ERROR | CONFIRMED |
| Dvar | Dvar_GetBool/Int/Float/String, dvar_restart | CONFIRMED |
| Config | config_mp.cfg, fileSysCheck.cfg, default_mp.cfg | CONFIRMED |

## Resource Chain Status

```text
ENGINE_RESOURCE_CODE = CONFIRMED (all subsystems present in decrypted code)
ENGINE_RESOURCE_EXECUTION = PARTIAL (subsystem DLLs load: d3d9, bink2, mss32)
FASTFILE_DATA_AVAILABLE = NO (zero .ff files exist)
ZONE_INIT_STATUS = NOT_STARTED (no .ff files to load)
ASSET_INIT_STATUS = NOT_STARTED (no zone data)
DVAR_INIT_STATUS = UNKNOWN (config files exist but may not be read)
RESOURCE_CHAIN_STATUS = BLOCKED_AT_FASTFILE_STAGE

BLOCKING CAUSE = Missing .ff files
ROOT CAUSE = IIPS failure prevents .ifs → .ff conversion
ORIGINAL CAUSE = Tencent QoS server unreachable
```

## Solution Path

To make the Engine progress past the FastFile stage, one of these is needed:

1. **Convert .ifs → .ff**: Reverse engineer the IFS2 extraction format
2. **Obtain .ff files**: Find original .ff fastfiles from a CODOL installation
3. **Bypass FastFile**: Modify Engine to load data directly from .ifs or another source
4. **Implement IFS2 compatibility**: Create local IFS2 that maps .ifs → virtual .ff

## Final Fields

```text
ICH032_STATUS = COMPLETE

FIRST_RESOURCE_FUNCTION = 0x00CA0000 (global init, ICH-021)
FIRST_FILE_OPERATION = IMPLIED (142 modules loaded from disk)
FIRST_FF_NAME = code_pre_gfx_mp.ff (static evidence)
FIRST_FF_RESULT = FILE_NOT_FOUND (file doesn't exist)
FIRST_ZONE_FUNCTION = NOT_EXECUTED (no .ff to process)
FIRST_ASSET_FUNCTION = NOT_EXECUTED (no zone data)
FIRST_DVAR_OPERATION = UNKNOWN

FF_DATA_AVAILABLE = NO (zero .ff files in entire workspace)
ZONE_INIT_STATUS = NOT_STARTED
ASSET_INIT_STATUS = NOT_STARTED
RESOURCE_CHAIN_STATUS = BLOCKED_AT_FASTFILE_STAGE

DATA_INVENTORY:
  .ifs: 974 files, 22.6 GB (IIPS downloads, not yet converted)
  .ff:  0 files (needed by Engine, never created)
  .iwd: 0 files
  .pak: 120 files, 28.7 MB

NEXT_TARGET = ICH-033: IFS2 format analysis or .ff data acquisition
```
