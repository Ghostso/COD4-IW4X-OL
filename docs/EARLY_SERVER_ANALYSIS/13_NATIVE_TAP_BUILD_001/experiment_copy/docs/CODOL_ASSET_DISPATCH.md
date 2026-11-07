# C1 asset loader dispatch evidence

Measured on 2026-09-07 with the existing local lobby service and `ui_viewer_mp`.

Client SHA256: `d990610732258b1d00dd6fe63d6691f294312a2e0562955a01ce16216115390d`.

`Load_XAssetHeader` is at `0x004c8ed0`; the current asset pointer is stored at `0x017c6a60`, and the current header slot pointer at `0x017c6b48`. Top-level asset records have stride 16 bytes, with the header at +8. The caller returns at `0x004b5d24`.

Static dispatch contains 38 type IDs with load calls, across 37 distinct callsites. Runtime traces verify 34 routes and corresponding resolved headers. Type names come from the reference Python server; the measured routes come from C1. This establishes dispatch mappings, not complete binary field layouts.

The initial hardware trace stalled startup. A bounded software-breakpoint capture completed startup in 4.556 seconds, with ui_viewer_mp taking 2.826 seconds. All breakpoints were cleared and CDB detached; C1 remained running. No client file was modified and no runtime hooks were added to the server.

The clean capture had one instrumentation anomaly: the shared clipmap epilogue was first reached by no-op type 29, consuming its POST probe. The earlier ui_viewer_mp capture independently supplies a matching type 15 PRE/ROUTE/POST with a resolved header and zero parser issues. The generator now filters types before removing each probe; that revised filter has not been rerun against C1.

| ID | Reference name | Loader VA | Runtime route + resolved header |
|---:|---|---|---|
| 0 | physpreset | 0x004bb4d0 | Verified |
| 1 | phys_collmap | 0x004bb710 | Verified |
| 2 | xanim | 0x004b7ce0 | Verified |
| 3 | xmodelsurfs | 0x004bb950 | Verified |
| 4 | xmodel | 0x004bbef0 | Verified |
| 5 | material | 0x004ba420 | Verified |
| 6 | pixelshader | 0x004b9a30 | Verified |
| 7 | vertexshader | 0x004b98a0 | Verified |
| 8 | vertexdecl | 0x004b9bb0 | Verified |
| 9 | techset | 0x004ba1f0 | Verified |
| 10 | image | 0x004b93a0 | Verified |
| 11 | sound | 0x004b8830 | Verified |
| 12 | sndcurve | 0x004b8350 | Verified |
| 13 | loaded_sound | 0x004b8170 | Verified |
| 14 | col_map_sp | 0x004bfb50 | Not observed |
| 15 | col_map_mp | 0x004bfb50 | Verified |
| 16 | com_map | 0x004bff80 | Verified |
| 17 | game_map_sp | 0x004bcb30 | Not observed |
| 18 | game_map_mp | 0x004bcc20 | Verified |
| 19 | map_ents | 0x004be9f0 | Not observed |
| 20 | fx_map | 0x004be2e0 | Verified |
| 21 | gfx_map | 0x004c8730 | Verified |
| 22 | lightdef | 0x004babf0 | Verified |
| 23 | ui_map | No load call | Not observed |
| 24 | font | 0x004c8d10 | Verified |
| 25 | menufile | 0x004c1980 | Verified |
| 26 | menu | 0x004c17b0 | Verified |
| 27 | localize | 0x004c1f80 | Verified |
| 28 | weapon | 0x004c3c10 | Verified |
| 29 | snddriverglobals | No load call | Not observed |
| 30 | fx | 0x004bcdf0 | Verified |
| 31 | impactfx | 0x004c2230 | Verified |
| 32 | aitype | No load call | Not observed |
| 33 | mptype | No load call | Not observed |
| 34 | character | No load call | Not observed |
| 35 | xmodelalias | No load call | Not observed |
| 36 | rawfile | 0x004c59b0 | Verified |
| 37 | stringtable | 0x004c5c50 | Verified |
| 38 | leaderboarddef | 0x004c65a0 | Verified |
| 39 | structureddatadef | 0x004c6280 | Verified |
| 40 | tracer | 0x004c2490 | Verified |
| 41 | vehicle | 0x004c54a0 | Verified |
| 42 | addon_map_ents | 0x004bebf0 | Not observed |
| 43 | weaponattach | 0x004c3e90 | Verified |

IDs 14 and 15 share a callsite. IDs 14, 17, 19 and 42 need another corpus or targeted analysis; nested map-entity loading is not established by the top-level trace.

## Reproduce

Use `tools/codol_trace_assets.py prepare C1.exe OUTPUT_DIRECTORY` with Python and Capstone. The output directory must have no spaces. Launch 32-bit CDB, stop at the executable entry point with `g @$exentry`, clear existing analysis breakpoints (`bc *`), then execute `$<OUTPUT_DIRECTORY\arm.cdb`. The script owns breakpoint IDs 0 through 73. Each matching probe removes itself after its first hit. After loading, interrupt, run `bc *`, `.logclose`, and `qd` to detach while leaving the client running. Use the tool's `summarize` command on the closed log and generated manifest.

Raw debugger logs remain in ignored obj/codol directories because client diagnostics can contain account information. The adjacent JSON contains only sanitized mapping evidence.
