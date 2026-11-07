"""Extract official CoDOL UI/map IWI artwork from the installed encrypted IWDs.

Only reads the original installation. The 24-byte archive key is derived from
the exact installed C1.exe and is never printed or written to disk.
"""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import struct
import zipfile
import zlib
from PIL import Image

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


def archive_key(client: Path) -> bytes:
    with client.open("rb") as file:
        file.seek(0x838B20)
        blob = file.read(256)
        file.seek(0x83C248)
        der = file.read(1191)
    assert hashlib.sha256(blob).hexdigest() == "e0ad40d9aef669c1a49a5b7da0e316ff7042e271ffd61cf134012b4bfb393cb3"
    assert hashlib.sha256(der).hexdigest() == "3a2f7891ac98f1fdf6a9a221c5586725157df270d6831e0ff82c383cd262cbb5"
    key = serialization.load_der_private_key(der, password=None).decrypt(
        blob, padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None)
    )
    assert len(key) == 24
    return key


def crypt(key: bytes, *words: int, data: bytes) -> bytes:
    counter = struct.pack("<IIII", *words)
    ctx = Cipher(algorithms.AES(key), modes.CTR(counter)).encryptor()
    return ctx.update(data) + ctx.finalize()


def inspect_archive(path: Path, key: bytes, wanted: tuple[str, ...], output: Path | None) -> None:
    archive = zlib.crc32(path.name.encode())
    with path.open("rb") as file, zipfile.ZipFile(file) as z:
        for index, item in enumerate(z.infolist()):
            file.seek(item.header_offset)
            local = file.read(30)
            assert local[:4] == b"PK\x03\x04"
            name_size, extra_size = struct.unpack_from("<HH", local, 26)
            name = crypt(key, 0x01010101, archive, index, 0x01010101, data=file.read(name_size)).split(b"\0", 1)[0].decode("utf-8", "replace")
            if any(term in name.lower() for term in wanted):
                print(path.name, index, name, item.file_size)
                if output is not None:
                    offset = item.header_offset + 30 + name_size + extra_size
                    file.seek(offset)
                    encrypted = file.read(item.compress_size)
                    compressed = bytearray()
                    for part in range(0, len(encrypted), 0x4000):
                        compressed.extend(crypt(key, offset + part, archive, 0x01010101, 0x01010101, data=encrypted[part:part + 0x4000]))
                    data = zlib.decompress(compressed, -15) if item.compress_type == 8 else bytes(compressed)
                    assert len(data) == item.file_size and zlib.crc32(data) == item.CRC
                    output.mkdir(parents=True, exist_ok=True)
                    (output / f"{path.stem}-{Path(name).name}").write_bytes(data)


MAP_ART = {
    "killhouse": "loadscreen_mp_killhouse",
    "rust": "loadscreen_mp_rust",
    "nuketown": "loadscreen_mp_nuked",
    "prototype": "loadscreen_zm_prototype_sh",
    "asylum": "loadscreen_zm_asylum_sh",
    "zombie_training": "loadscreen_zm_zombie_training",
}


def build_maps(game: Path, output: Path, key: bytes) -> None:
    originals = Path(os.environ["TEMP"]) / "codol-discord-originals"
    inspect_archive(game / "main" / "iw_image_02.iwd", key, tuple(MAP_ART.values()), originals)
    for discord_key, name in MAP_ART.items():
        iwi = (originals / f"iw_image_02-{name}.iwi").read_bytes()
        assert iwi[:4] == b"IWi\x09" and struct.unpack_from("<H", iwi, 8)[0] == 2
        width, height = struct.unpack_from("<HH", iwi, 10)
        assert (width, height) == (1280, 720) and len(iwi) == 32 + width * height * 3
        image = Image.frombytes("RGB", (width, height), iwi[32:], "raw", "BGR")
        left = (width - height) // 2
        image.crop((left, 0, left + height, height)).resize((1024, 1024), Image.Resampling.LANCZOS).save(output / f"{discord_key}.png")
        print(f"official {discord_key}.png <- iw_image_02.iwd:images/{name}.iwi")
    splash = Image.open(game / "splash.bmp").convert("RGB")
    assert splash.size == (800, 510)
    splash.crop((195, 0, 605, 410)).resize((1024, 1024), Image.Resampling.LANCZOS).save(output / "codol.png")
    print("official codol.png <- splash.bmp (logo and character art)")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--game", type=Path, default=Path(r"E:\codol-classic"))
    p.add_argument("--archive", action="append")
    p.add_argument("--match", action="append")
    p.add_argument("--output", type=Path)
    p.add_argument("--build-maps", action="store_true")
    args = p.parse_args()
    client = args.game / "C1.exe.codol-pause-original"
    key = archive_key(client if client.exists() else args.game / "C1.exe")
    if args.build_maps:
        assert args.output is not None
        args.output.mkdir(parents=True, exist_ok=True)
        build_maps(args.game, args.output, key)
        return
    paths = [args.game / "main" / x for x in args.archive] if args.archive else sorted((args.game / "main").glob("*image*.iwd"))
    for path in paths:
        inspect_archive(path, key, tuple(x.lower() for x in (args.match or ["sfproto", "loadscreen", "loading", "codol", "logo"])), args.output)


if __name__ == "__main__":
    main()
