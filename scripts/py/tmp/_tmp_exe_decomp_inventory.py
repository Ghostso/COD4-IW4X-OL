from __future__ import annotations

from pathlib import Path


def main() -> int:
    names = (
        "exe_section_map.csv",
        "exe_core004a_section_map.csv",
        "exe_core004_section_map.csv",
        "exe_core003_pe_analysis_map.csv",
        "exe_functions.csv",
        "exe_function_boundary_full.csv",
        "exe_callgraph.csv",
        "exe_strings_refs.csv",
        "exe_iat_external.csv",
        "exe_dynamic_loads.csv",
        "exe_external_symbols.csv",
        "exe_non_iat_external.csv",
        "exe_external_calls.csv",
        "exe_external_boundary.csv",
        "exe_globals.csv",
        "exe_renderer_candidates.csv",
        "exe_network_candidates.csv",
        "exe_game_init_candidates.csv",
        "exe_mainloop_candidates.csv",
        "exe_state_machine_candidates.csv",
        "exe_subsystems.csv",
    )
    for name in names:
        path = Path(name)
        print(f"{name}\texists={path.exists()}\tsize={path.stat().st_size if path.exists() else 0}")
        if not path.exists():
            continue
        try:
            lines = path.read_text(encoding="utf-8-sig").splitlines()
        except UnicodeDecodeError:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        for line in lines[:5]:
            print(" ", line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
