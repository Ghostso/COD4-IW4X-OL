"""Build the existing server-only IWD in the active development server home."""

import argparse
from pathlib import Path

import codol_package


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--home-main", type=Path, required=True)
    args = parser.parse_args()
    repo = args.repo.resolve()
    if not (repo / "bin/home/main/waypoints").is_dir():
        parser.error("server repository has no waypoint source directory")
    codol_package.REPO = str(repo)
    target = args.home_main.resolve() / codol_package.PACK
    target.parent.mkdir(parents=True, exist_ok=True)
    count = codol_package.build_pack(str(target))
    if count == 0:
        parser.error("server pack has no tracked source files")
    print(f"Server pack: {target} ({count} files)")


if __name__ == "__main__":
    main()
