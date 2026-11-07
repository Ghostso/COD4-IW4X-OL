#!/usr/bin/env python3
"""Inspect and edit CODOL's persistent private player profile."""

from __future__ import annotations

import argparse
import ctypes
import json
import math
import os
import shutil
import struct
import sys
import threading
import webbrowser
import zlib
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from AnalyzeCodolProfile import PROFILE_SIZE, ProfileError, load_profile
from CodolInventory import load_inventory, write_inventory
from CodolRuntimeSync import RuntimeSyncError, synchronize


TARGET_NAME = "codoMP_client_shipRetail.exe"
DEFAULT_TITLE_ID = 1004
DEFAULT_USER_ID = 0x1100001DEADC0DE
SECURE_DDL_VERSION = 19
SECURE_DDL_CHECKSUM = 0x8A317D69
PROFILE_FORMAT_VERSION = 1
RANK_VERSION = 4
PUBLIC_DDL_VERSION = 233
PUBLIC_DDL_CHECKSUM = 0xE32D50D6

TYPE_U32 = 0x08
TYPE_U64 = 0x0A
TYPE_INT32 = 0x07
TYPE_FLOAT32 = 0x0D
TYPE_BLOB = 0x13

PUBLIC_FIELDS = {
    "badge": (0x0F02, "徽章"),
    "cardBackground": (0x0F06, "名片背景"),
    "cardIcon": (0x0F0A, "名片图标"),
    "cardNameplate": (0x0F0E, "名牌"),
    "cardTitle": (0x0F12, "称号"),
    "currentCharacterIndex": (0x1036, "当前角色栏位"),
    "onboardCharacterID": (0x257A, "角色物品 ID"),
}
PUBLIC_VALIDATED_FIELDS = (
    "badge", "cardBackground", "cardIcon", "cardNameplate", "cardTitle"
)


@dataclass(frozen=True)
class FieldSpec:
    name: str
    offset: int
    kind: str
    validated: bool
    label: str
    group: str
    visible: bool = True


@dataclass(frozen=True)
class Rank:
    index: int
    code: str
    start_xp: int
    target_xp: int


FIELD_SPECS = (
    FieldSpec("accuracy", 0x000C, "int", True, "命中率", "combat"),
    FieldSpec("assists", 0x02A4, "int", True, "助攻", "combat"),
    FieldSpec("bombDefuses", 0x02A8, "int", True, "拆除炸弹", "objectives"),
    FieldSpec("bombPlants", 0x02AC, "int", True, "安放炸弹", "objectives"),
    FieldSpec("challegeUpdateTime", 0x02B0, "int", False, "挑战更新时间", "advanced", False),
    FieldSpec("challenge_version", 0x32A7, "int", False, "挑战版本", "advanced", False),
    FieldSpec("clanActivePoint", 0x35A3, "float", False, "战队活跃度", "advanced"),
    FieldSpec("confirmed", 0x12D4, "int", True, "确认击杀", "objectives"),
    FieldSpec("currentWinStreak", 0x12D8, "int", True, "当前连胜", "matches"),
    FieldSpec("deaths", 0x12DC, "int", True, "死亡", "combat"),
    FieldSpec("denied", 0x12E0, "int", True, "拒绝确认", "objectives"),
    FieldSpec("elo", 0x12E4, "int", True, "ELO", "progression"),
    FieldSpec("escapes", 0x12E8, "int", True, "成功撤离", "objectives"),
    FieldSpec("experience", 0x12EC, "int", True, "经验值", "progression", False),
    FieldSpec("gdfRating", 0x3157, "float", False, "GDF 评分", "advanced"),
    FieldSpec("gdfVariance", 0x315B, "float", False, "GDF 方差", "advanced"),
    FieldSpec("headshots", 0x12F0, "int", True, "爆头", "combat"),
    FieldSpec("hits", 0x12F4, "int", True, "命中", "combat"),
    FieldSpec("kdRatio", 0x12F8, "int", True, "KD 比率", "combat"),
    FieldSpec("killStreak", 0x12FC, "int", True, "最高连续击杀", "combat"),
    FieldSpec("kills", 0x1300, "float", True, "击杀", "combat"),
    FieldSpec("lastClanIdHigh", 0x35A7, "int", False, "战队 ID 高位", "advanced", False),
    FieldSpec("lastClanIdLow", 0x35AB, "int", False, "战队 ID 低位", "advanced", False),
    FieldSpec("lastConnectionIDHigh", 0x1FAB, "int", False, "连接 ID 高位", "advanced", False),
    FieldSpec("lastConnectionIDLow", 0x1FAF, "int", False, "连接 ID 低位", "advanced", False),
    FieldSpec("lastMatchDateTime", 0x1FB3, "int", False, "最近比赛时间", "advanced"),
    FieldSpec("losses", 0x1304, "int", True, "失败", "matches"),
    FieldSpec("objectives", 0x1308, "int", True, "目标贡献", "objectives"),
    FieldSpec("prestige", 0x1313, "int", True, "转生", "progression", False),
    FieldSpec("rank", 0x1317, "int", True, "内部等级", "progression", False),
    FieldSpec("rankVersion", 0x131B, "int", True, "等级表版本", "progression", False),
    FieldSpec("recentRankedMatchNum", 0x148B, "int", False, "近期排位场次", "matches"),
    FieldSpec("score", 0x131F, "int", True, "总分", "progression"),
    FieldSpec("scorePerMinute", 0x1323, "int", True, "每分钟得分", "combat"),
    FieldSpec("secureDailyChallengeDay", 0x1483, "int", False, "每日挑战日期", "advanced", False),
    FieldSpec("secureDailyChallengeRowIndex", 0x1487, "int", False, "每日挑战索引", "advanced", False),
    FieldSpec("skill", 0x1327, "int", True, "技能评分", "progression"),
    FieldSpec("sosRating", 0x329F, "float", False, "SOS 评分", "advanced"),
    FieldSpec("sosWeight", 0x32A3, "float", False, "SOS 权重", "advanced"),
    FieldSpec("suicides", 0x132B, "int", True, "自杀", "combat"),
    FieldSpec("survivalTopScoreEasy", 0x132F, "int", True, "生存简单最高分", "survival"),
    FieldSpec("survivalTopScoreHard", 0x1333, "int", True, "生存困难最高分", "survival"),
    FieldSpec("survivalTopScoreMedium", 0x1337, "int", True, "生存普通最高分", "survival"),
    FieldSpec("ties", 0x133B, "int", True, "平局", "matches"),
    FieldSpec("timePlayed", 0x133F, "int", True, "游戏时间", "matches"),
    FieldSpec("timePlayedOverAll", 0x1343, "int", True, "总在线时间", "matches"),
    FieldSpec("timePlayedTotal", 0x1347, "int", True, "累计游玩时间", "matches"),
    FieldSpec("totalMatchPVE", 0x1FB7, "int", False, "PVE 场次", "matches"),
    FieldSpec("totalMatchPVP", 0x1FBB, "int", False, "PVP 场次", "matches"),
    FieldSpec("totalMatches", 0x205F, "int", False, "总场次", "matches"),
    FieldSpec("totalMatchesPlayedInLastConnectionID", 0x2063, "int", False, "本次连接场次", "advanced"),
    FieldSpec("totalShots", 0x134B, "int", True, "总射击数", "combat"),
    FieldSpec("userIDHigh", 0x134F, "int", False, "用户 ID 高位", "advanced", False),
    FieldSpec("userIDLow", 0x1353, "int", False, "用户 ID 低位", "advanced", False),
    FieldSpec("winRatio", 0x1357, "int", True, "胜率", "matches"),
    FieldSpec("winStreak", 0x135B, "int", True, "最高连胜", "matches"),
    FieldSpec("wins", 0x135F, "float", True, "胜利", "matches"),
)
FIELDS = {field.name: field for field in FIELD_SPECS}
VALIDATED_FIELDS = tuple(field for field in FIELD_SPECS if field.validated)

RANKS = (
    Rank(0, "pvt1", 0, 2000), Rank(1, "pvt2", 2000, 4000),
    Rank(2, "pvt3", 4000, 6000), Rank(3, "pvt4", 6000, 9000),
    Rank(4, "pfc1", 9000, 12000), Rank(5, "pfc2", 12000, 16000),
    Rank(6, "pfc3", 16000, 20000), Rank(7, "pfc4", 20000, 25000),
    Rank(8, "spc1", 25000, 30000), Rank(9, "spc2", 30000, 37400),
    Rank(10, "spc3", 37400, 46000), Rank(11, "spc4", 46000, 55750),
    Rank(12, "cpl1", 55750, 66700), Rank(13, "cpl2", 66700, 78900),
    Rank(14, "cpl3", 78900, 92350), Rank(15, "cpl4", 92350, 107050),
    Rank(16, "sgt1", 107050, 123050), Rank(17, "sgt2", 123050, 140400),
    Rank(18, "sgt3", 140400, 159050), Rank(19, "sgt4", 159050, 179050),
    Rank(20, "ssgt1", 179050, 200400), Rank(21, "ssgt2", 200400, 223150),
    Rank(22, "ssgt3", 223150, 247300), Rank(23, "ssgt4", 247300, 272900),
    Rank(24, "sfc1", 272900, 299900), Rank(25, "sfc2", 299900, 328400),
    Rank(26, "sfc3", 328400, 358400), Rank(27, "sfc4", 358400, 389900),
    Rank(28, "msgt1", 389900, 422900), Rank(29, "msgt2", 422900, 457750),
    Rank(30, "msgt3", 457750, 494400), Rank(31, "msgt4", 494400, 532900),
    Rank(32, "1stsgt1", 532900, 573300), Rank(33, "1stsgt2", 573300, 615600),
    Rank(34, "1stsgt3", 615600, 659800), Rank(35, "1stsgt4", 659800, 706000),
    Rank(36, "sgtmaj1", 706000, 754150), Rank(37, "sgtmaj2", 754150, 804300),
    Rank(38, "sgtmaj3", 804300, 856450), Rank(39, "sgtmaj4", 856450, 910650),
    Rank(40, "csm1", 910650, 966950), Rank(41, "csm2", 966950, 1025350),
    Rank(42, "csm3", 1025350, 1085850), Rank(43, "csm4", 1085850, 1148450),
    Rank(44, "wo1", 1148450, 1213250), Rank(45, "wo2", 1213250, 1280250),
    Rank(46, "wo3", 1280250, 1349450), Rank(47, "cwo1", 1349450, 1420900),
    Rank(48, "cwo2", 1420900, 1494600), Rank(49, "cwo3", 1494600, 1571050),
    Rank(50, "2ndlt1", 1571050, 1650250), Rank(51, "2ndlt2", 1650250, 1732250),
    Rank(52, "2ndlt3", 1732250, 1817050), Rank(53, "1stlt1", 1817050, 1904700),
    Rank(54, "1stlt2", 1904700, 1995250), Rank(55, "1stlt3", 1995250, 2088700),
    Rank(56, "capt1", 2088700, 2185100), Rank(57, "capt2", 2185100, 2284500),
    Rank(58, "capt3", 2284500, 2386900), Rank(59, "maj1", 2386900, 2492300),
    Rank(60, "maj2", 2492300, 2600800), Rank(61, "maj3", 2600800, 2712400),
    Rank(62, "ltcol1", 2712400, 2827100), Rank(63, "ltcol2", 2827100, 2944950),
    Rank(64, "ltcol3", 2944950, 3065950), Rank(65, "ltcol4", 3065950, 3190200),
    Rank(66, "col1", 3190200, 3317700), Rank(67, "col2", 3317700, 3448450),
    Rank(68, "col3", 3448450, 3582550), Rank(69, "col4", 3582550, 3732550),
)
PRESTIGE_MULTIPLIERS = (1.0, 1.25, 1.5, 1.75)


class SecureProfile:
    def __init__(self, data: bytes | bytearray, *, compressed: bool = True, optional_user_id: int | None = None):
        if len(data) != PROFILE_SIZE:
            raise ProfileError(f"secure profile must decode to 0x{PROFILE_SIZE:X} bytes")
        self.data = bytearray(data)
        self.compressed = compressed
        self.optional_user_id = optional_user_id

    @classmethod
    def create(cls, user_id: int = DEFAULT_USER_ID) -> "SecureProfile":
        data = bytearray(PROFILE_SIZE)
        struct.pack_into("<I", data, 4, SECURE_DDL_VERSION)
        struct.pack_into("<I", data, 8, SECURE_DDL_CHECKSUM)
        profile = cls(data)
        profile._write_raw_u32("userIDHigh", user_id >> 32)
        profile._write_raw_u32("userIDLow", user_id)
        profile.set_progression(level=1, prestige=0, experience=0)
        return profile

    @classmethod
    def load(cls, path: Path) -> "SecureProfile":
        loaded = load_profile(path)
        if not loaded.metadata.crc_valid:
            raise ProfileError("private profile CRC32 is invalid")
        profile = cls(
            loaded.data,
            compressed=loaded.metadata.compressed,
            optional_user_id=loaded.metadata.optional_user_id,
        )
        version = struct.unpack_from("<I", profile.data, 4)[0]
        checksum = struct.unpack_from("<I", profile.data, 8)[0]
        if version != SECURE_DDL_VERSION or checksum != SECURE_DDL_CHECKSUM:
            raise ProfileError(
                f"unsupported secure DDL version/checksum: {version}/0x{checksum:08X}"
            )
        profile._apply_trailing(loaded.trailing)
        return profile

    def _apply_trailing(self, trailing: bytes) -> None:
        cursor = 0
        for field in VALIDATED_FIELDS:
            expected = TYPE_INT32 if field.kind == "int" else TYPE_FLOAT32
            if cursor + 5 > len(trailing) or trailing[cursor] != expected:
                raise ProfileError(f"invalid trailing value for {field.name} at 0x{cursor:X}")
            self.data[field.offset:field.offset + 4] = trailing[cursor + 1:cursor + 5]
            cursor += 5
        if trailing[cursor:] not in (b"", b"\0"):
            raise ProfileError("private profile contains unexpected trailing data")

    def _write_raw_u32(self, name: str, value: int) -> None:
        struct.pack_into("<I", self.data, FIELDS[name].offset, value & 0xFFFFFFFF)

    def get(self, name: str) -> int | float:
        field = FIELDS[name]
        fmt = "<i" if field.kind == "int" else "<f"
        return struct.unpack_from(fmt, self.data, field.offset)[0]

    def set(self, name: str, value: int | float) -> None:
        field = FIELDS.get(name)
        if field is None:
            raise ValueError(f"unknown secure profile field: {name}")
        if field.name in {"rank", "rankVersion", "prestige", "experience"}:
            raise ValueError(f"{name} is managed through level, prestige and experience")
        if field.kind == "int":
            parsed = int(value)
            if parsed < 0 or parsed > 0x7FFFFFFF:
                raise ValueError(f"{name} must be between 0 and 2147483647")
            struct.pack_into("<i", self.data, field.offset, parsed)
        else:
            parsed = float(value)
            if not math.isfinite(parsed) or parsed < 0 or parsed > 1.0e9:
                raise ValueError(f"{name} must be a finite value between 0 and 1000000000")
            struct.pack_into("<f", self.data, field.offset, parsed)

    @staticmethod
    def xp_range(level: int, prestige: int) -> tuple[int, int]:
        if not 1 <= level <= len(RANKS):
            raise ValueError("level must be between 1 and 70")
        if not 0 <= prestige < len(PRESTIGE_MULTIPLIERS):
            raise ValueError("prestige must be between 0 and 3")
        rank = RANKS[level - 1]
        multiplier = PRESTIGE_MULTIPLIERS[prestige]
        return int(rank.start_xp * multiplier), int(rank.target_xp * multiplier)

    def set_progression(self, *, level: int, prestige: int, experience: int | None = None) -> None:
        start, target = self.xp_range(level, prestige)
        selected_xp = start if experience is None else int(experience)
        maximum = target if level == len(RANKS) else target - 1
        if selected_xp < start or selected_xp > maximum:
            raise ValueError(
                f"experience for level {level}, prestige {prestige} must be {start}..{maximum}"
            )
        struct.pack_into("<i", self.data, FIELDS["rank"].offset, level - 1)
        struct.pack_into("<i", self.data, FIELDS["prestige"].offset, prestige)
        struct.pack_into("<i", self.data, FIELDS["experience"].offset, selected_xp)
        struct.pack_into("<i", self.data, FIELDS["rankVersion"].offset, RANK_VERSION)

    def progression(self) -> dict[str, Any]:
        rank = max(0, min(len(RANKS) - 1, int(self.get("rank"))))
        prestige = max(0, min(len(PRESTIGE_MULTIPLIERS) - 1, int(self.get("prestige"))))
        start, target = self.xp_range(rank + 1, prestige)
        experience = int(self.get("experience"))
        return {
            "level": rank + 1,
            "rank": rank,
            "rankCode": RANKS[rank].code,
            "prestige": prestige,
            "experience": experience,
            "xpStart": start,
            "xpTarget": target,
            "rankVersion": int(self.get("rankVersion")),
            "consistent": start <= experience <= target,
        }

    def encode(self) -> bytes:
        trailing = bytearray()
        for field in VALIDATED_FIELDS:
            trailing.append(TYPE_INT32 if field.kind == "int" else TYPE_FLOAT32)
            trailing.extend(self.data[field.offset:field.offset + 4])
        trailing.append(0)
        return encode_profile(self.data, self.compressed, self.optional_user_id, bytes(trailing))


def encode_profile(
    data: bytearray,
    compressed: bool,
    optional_user_id: int | None,
    trailing: bytes,
) -> bytes:
    crc = zlib.crc32(data[4:]) & 0xFFFFFFFF
    struct.pack_into("<I", data, 0, crc)
    blob = zlib.compress(bytes(data), level=9) if compressed else bytes(data)
    result = bytearray()
    if optional_user_id is not None:
        result.extend(bytes([TYPE_U64]) + struct.pack("<Q", optional_user_id))
    result.extend(bytes([TYPE_U32]) + struct.pack("<I", int(compressed)))
    result.extend(bytes([TYPE_U32]) + struct.pack("<I", PROFILE_FORMAT_VERSION))
    result.extend(bytes([TYPE_U32]) + struct.pack("<I", crc))
    result.append(TYPE_BLOB)
    result.extend(bytes([TYPE_U32]) + struct.pack("<I", len(blob)))
    result.extend(blob)
    result.extend(trailing)
    return bytes(result)


class PublicProfile:
    def __init__(
        self,
        data: bytes,
        trailing: bytes,
        *,
        compressed: bool,
        optional_user_id: int | None,
    ):
        if len(data) != PROFILE_SIZE:
            raise ProfileError(f"public profile must decode to 0x{PROFILE_SIZE:X} bytes")
        if len(trailing) != 626 or trailing[-1:] != b"\0":
            raise ProfileError("unsupported Publicprofile validation trailer")
        self.data = bytearray(data)
        self.trailing = bytearray(trailing)
        self.compressed = compressed
        self.optional_user_id = optional_user_id
        for index, name in enumerate(PUBLIC_VALIDATED_FIELDS):
            cursor = index * 5
            if self.trailing[cursor] != TYPE_INT32:
                raise ProfileError(f"invalid trailing value for {name}")
            offset = PUBLIC_FIELDS[name][0]
            self.data[offset:offset + 4] = self.trailing[cursor + 1:cursor + 5]

    @classmethod
    def load(cls, path: Path) -> "PublicProfile":
        loaded = load_profile(path)
        if not loaded.metadata.crc_valid:
            raise ProfileError("Publicprofile CRC32 is invalid")
        version = struct.unpack_from("<I", loaded.data, 4)[0]
        checksum = struct.unpack_from("<I", loaded.data, 8)[0]
        if version != PUBLIC_DDL_VERSION or checksum != PUBLIC_DDL_CHECKSUM:
            raise ProfileError(
                f"unsupported public DDL version/checksum: {version}/0x{checksum:08X}"
            )
        return cls(
            loaded.data,
            loaded.trailing,
            compressed=loaded.metadata.compressed,
            optional_user_id=loaded.metadata.optional_user_id,
        )

    def get(self, name: str) -> int:
        offset, _label = PUBLIC_FIELDS[name]
        if name == "currentCharacterIndex":
            return self.data[offset]
        return struct.unpack_from("<i", self.data, offset)[0]

    def set(self, name: str, value: Any) -> None:
        if name not in PUBLIC_FIELDS:
            raise ValueError(f"unknown public profile field: {name}")
        parsed = int(value)
        offset, _label = PUBLIC_FIELDS[name]
        if name == "currentCharacterIndex":
            if not 0 <= parsed < 12:
                raise ValueError("currentCharacterIndex must be between 0 and 11")
            self.data[offset] = parsed
            return
        if not 0 <= parsed <= 0x7FFFFFFF:
            raise ValueError(f"{name} must be between 0 and 2147483647")
        struct.pack_into("<i", self.data, offset, parsed)
        if name in PUBLIC_VALIDATED_FIELDS:
            cursor = PUBLIC_VALIDATED_FIELDS.index(name) * 5
            self.trailing[cursor] = TYPE_INT32
            self.trailing[cursor + 1:cursor + 5] = self.data[offset:offset + 4]

    def document(self) -> dict[str, Any]:
        return {
            "exists": True,
            "fields": {name: self.get(name) for name in PUBLIC_FIELDS},
            "fieldSpecs": [
                {"name": name, "label": label}
                for name, (_offset, label) in PUBLIC_FIELDS.items()
            ],
        }

    def encode(self) -> bytes:
        return encode_profile(
            self.data, self.compressed, self.optional_user_id, bytes(self.trailing)
        )


def find_game_directory(workspace: Path) -> Path | None:
    for root in workspace.iterdir():
        if not root.is_dir() or not root.name.startswith("Call of Duty Online "):
            continue
        for candidate in root.iterdir():
            if candidate.is_dir() and (candidate / TARGET_NAME).is_file():
                return candidate
    return None


def private_profile_path(game_dir: Path, title_id: int, user_id: int) -> Path:
    return (
        game_dir.resolve()
        / "Ayria" / "Assets" / "Alwaysoffline"
        / str(title_id) / f"{user_id:X}" / "Privateprofile"
    )


def public_profile_path(private_path: Path) -> Path:
    return private_path.with_name("Publicprofile")


def inventory_path(private_path: Path) -> Path:
    return private_path.with_name("Inventory.json")


def is_game_running() -> bool:
    if os.name != "nt":
        return False

    class ProcessEntry(ctypes.Structure):
        _fields_ = [
            ("dwSize", ctypes.c_uint32), ("cntUsage", ctypes.c_uint32),
            ("th32ProcessID", ctypes.c_uint32), ("th32DefaultHeapID", ctypes.c_void_p),
            ("th32ModuleID", ctypes.c_uint32), ("cntThreads", ctypes.c_uint32),
            ("th32ParentProcessID", ctypes.c_uint32), ("pcPriClassBase", ctypes.c_long),
            ("dwFlags", ctypes.c_uint32), ("szExeFile", ctypes.c_wchar * 260),
        ]

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateToolhelp32Snapshot.argtypes = (ctypes.c_uint32, ctypes.c_uint32)
    kernel32.CreateToolhelp32Snapshot.restype = ctypes.c_void_p
    kernel32.Process32FirstW.argtypes = (ctypes.c_void_p, ctypes.POINTER(ProcessEntry))
    kernel32.Process32FirstW.restype = ctypes.c_int
    kernel32.Process32NextW.argtypes = (ctypes.c_void_p, ctypes.POINTER(ProcessEntry))
    kernel32.Process32NextW.restype = ctypes.c_int
    kernel32.CloseHandle.argtypes = (ctypes.c_void_p,)
    kernel32.CloseHandle.restype = ctypes.c_int
    snapshot = kernel32.CreateToolhelp32Snapshot(0x00000002, 0)
    if snapshot in (0, ctypes.c_void_p(-1).value):
        return False
    entry = ProcessEntry()
    entry.dwSize = ctypes.sizeof(entry)
    try:
        found = kernel32.Process32FirstW(snapshot, ctypes.byref(entry))
        while found:
            if entry.szExeFile.casefold() == TARGET_NAME.casefold():
                return True
            found = kernel32.Process32NextW(snapshot, ctypes.byref(entry))
        return False
    finally:
        kernel32.CloseHandle(snapshot)


def load_or_create(path: Path, user_id: int) -> tuple[SecureProfile, bool]:
    if path.is_file():
        return SecureProfile.load(path), True
    return SecureProfile.create(user_id), False


def write_encoded(path: Path, encoded: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".writing")
    backup = path.with_name(path.name + ".bak")
    try:
        temporary.write_bytes(encoded)
        if path.is_file():
            shutil.copy2(path, backup)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def write_profile(path: Path, profile: SecureProfile | PublicProfile) -> None:
    write_encoded(path, profile.encode())


def profile_document(path: Path, user_id: int) -> dict[str, Any]:
    profile, exists = load_or_create(path, user_id)
    fields = {field.name: profile.get(field.name) for field in FIELD_SPECS if field.visible}
    return {
        "path": str(path),
        "exists": exists,
        "gameRunning": is_game_running(),
        "ddlVersion": SECURE_DDL_VERSION,
        "ddlChecksum": f"0x{SECURE_DDL_CHECKSUM:08X}",
        "progression": profile.progression(),
        "rankTable": [
            {
                "level": rank.index + 1,
                "code": rank.code,
                "startXp": rank.start_xp,
                "targetXp": rank.target_xp,
            }
            for rank in RANKS
        ],
        "prestigeMultipliers": PRESTIGE_MULTIPLIERS,
        "fields": fields,
        "fieldSpecs": [
            {
                "name": field.name,
                "label": field.label,
                "group": field.group,
                "kind": field.kind,
                "validated": field.validated,
            }
            for field in FIELD_SPECS if field.visible
        ],
    }


def apply_document(path: Path, user_id: int, document: dict[str, Any]) -> dict[str, Any]:
    if is_game_running():
        raise RuntimeError("请先关闭 CODOL，再保存玩家档案。")
    profile, _exists = load_or_create(path, user_id)
    progression = document.get("progression")
    if not isinstance(progression, dict):
        raise ValueError("progression must be an object")
    level = int(progression.get("level"))
    prestige = int(progression.get("prestige"))
    raw_experience = progression.get("experience")
    experience = None if raw_experience is None else int(raw_experience)
    profile.set_progression(level=level, prestige=prestige, experience=experience)

    values = document.get("fields", {})
    if not isinstance(values, dict):
        raise ValueError("fields must be an object")
    for name, value in values.items():
        profile.set(name, value)
    write_profile(path, profile)
    return profile_document(path, user_id)


def public_document(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"exists": False, "fields": {}, "fieldSpecs": []}
    return PublicProfile.load(path).document()


def normalize_inventory(document: Any) -> dict[str, Any]:
    if not isinstance(document, dict) or not isinstance(document.get("items"), list):
        raise ValueError("inventory must contain an items array")
    normalized = json.loads(json.dumps(document))
    seen: set[int] = set()
    for item in normalized["items"]:
        if not isinstance(item, dict):
            raise ValueError("each inventory item must be an object")
        item_id = item.get("id")
        if not isinstance(item_id, int) or not 0 < item_id <= 0xFFFFFFFF:
            raise ValueError("inventory item IDs must be uint32 values")
        if item_id in seen:
            raise ValueError(f"duplicate inventory item ID: {item_id}")
        seen.add(item_id)
        if "quantity" in item:
            quantity = item["quantity"]
            if not isinstance(quantity, int) or not 0 < quantity <= 0xFFFFFFFF:
                raise ValueError(f"invalid quantity for item {item_id}")
        for text_field in ("label", "type"):
            if text_field in item and not isinstance(item[text_field], str):
                raise ValueError(f"{text_field} for item {item_id} must be text")
    return normalized


def editor_document(path: Path, user_id: int) -> dict[str, Any]:
    private = profile_document(path, user_id)
    inventory_file = inventory_path(path)
    return {
        "gameRunning": private["gameRunning"],
        "private": private,
        "public": public_document(public_profile_path(path)),
        "inventory": load_inventory(inventory_file),
        "paths": {
            "private": str(path),
            "public": str(public_profile_path(path)),
            "inventory": str(inventory_file),
        },
    }


def apply_editor_document(path: Path, user_id: int, document: dict[str, Any]) -> dict[str, Any]:
    private_document = document.get("private")
    public_values = document.get("public")
    inventory_document = normalize_inventory(document.get("inventory"))
    if not isinstance(private_document, dict):
        raise ValueError("private must be an object")
    if not isinstance(public_values, dict):
        raise ValueError("public must be an object")

    private, _exists = load_or_create(path, user_id)
    progression = private_document.get("progression")
    if not isinstance(progression, dict):
        raise ValueError("private progression must be an object")
    private.set_progression(
        level=int(progression.get("level")),
        prestige=int(progression.get("prestige")),
        experience=int(progression.get("experience")),
    )
    private_fields = private_document.get("fields", {})
    if not isinstance(private_fields, dict):
        raise ValueError("private fields must be an object")
    for name, value in private_fields.items():
        private.set(name, value)

    public_path = public_profile_path(path)
    public = PublicProfile.load(public_path) if public_path.is_file() else None
    if public is not None:
        for name, value in public_values.items():
            public.set(name, value)
    elif public_values:
        raise ValueError("Publicprofile does not exist; a blank public profile is not safe to create")

    # Everything is validated before the first file replacement.
    write_inventory(inventory_path(path), inventory_document)
    if public is not None:
        write_profile(public_path, public)
    write_profile(path, private)

    sync_steps: list[dict[str, Any]] = []
    if is_game_running():
        targets = ["inventory"]
        if public is not None:
            targets.append("public")
        targets.append("private")
        sync_steps = [result.__dict__ for result in synchronize(targets)]

    result = editor_document(path, user_id)
    result["sync"] = sync_steps
    return result


class EditorServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address: tuple[str, int], handler: type[BaseHTTPRequestHandler], *, path: Path, user_id: int, html: bytes):
        super().__init__(address, handler)
        self.profile_path = path
        self.user_id = user_id
        self.html = html


class EditorHandler(BaseHTTPRequestHandler):
    server: EditorServer

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _json(self, status: int, value: dict[str, Any]) -> None:
        payload = json.dumps(value, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self) -> None:
        route = urlparse(self.path).path
        try:
            if route == "/api/profile":
                self._json(HTTPStatus.OK, editor_document(self.server.profile_path, self.server.user_id))
                return
            if route == "/api/status":
                self._json(HTTPStatus.OK, {"gameRunning": is_game_running()})
                return
            if route in ("/", "/index.html"):
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(self.server.html)))
                self.end_headers()
                self.wfile.write(self.server.html)
                return
            self.send_error(HTTPStatus.NOT_FOUND)
        except (OSError, ValueError, ProfileError) as error:
            self._json(HTTPStatus.BAD_REQUEST, {"error": str(error)})

    def do_PUT(self) -> None:
        if urlparse(self.path).path != "/api/profile":
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 65536:
                raise ValueError("invalid request size")
            document = json.loads(self.rfile.read(length))
            if not isinstance(document, dict):
                raise ValueError("request must be a JSON object")
            result = apply_editor_document(self.server.profile_path, self.server.user_id, document)
            self._json(HTTPStatus.OK, result)
        except (RuntimeError, RuntimeSyncError) as error:
            self._json(HTTPStatus.CONFLICT, {"error": str(error), "gameRunning": True})
        except (OSError, ValueError, ProfileError, json.JSONDecodeError) as error:
            self._json(HTTPStatus.BAD_REQUEST, {"error": str(error)})


def run_editor(path: Path, user_id: int, html_path: Path, port: int, open_browser: bool) -> int:
    html = html_path.read_bytes()
    server = EditorServer(("127.0.0.1", port), EditorHandler, path=path, user_id=user_id, html=html)
    url = f"http://127.0.0.1:{server.server_port}/"
    print(f"CODOL profile editor: {url}")
    print(f"Private profile: {path}")
    if open_browser:
        threading.Timer(0.25, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever(poll_interval=0.25)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


def parse_assignment(value: str) -> tuple[str, str]:
    name, separator, raw = value.partition("=")
    if not separator or not name or not raw:
        raise argparse.ArgumentTypeError("field assignments must use NAME=VALUE")
    return name, raw


def parse_args() -> argparse.Namespace:
    repository = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-dir", type=Path, default=find_game_directory(repository.parent))
    parser.add_argument("--state", type=Path, help="Override the Privateprofile path")
    parser.add_argument("--title-id", type=int, default=DEFAULT_TITLE_ID)
    parser.add_argument("--user-id", type=lambda value: int(value, 0), default=DEFAULT_USER_ID)
    subparsers = parser.add_subparsers(dest="action", required=True)
    subparsers.add_parser("path")
    subparsers.add_parser("show")
    subparsers.add_parser("create")
    edit = subparsers.add_parser("set")
    edit.add_argument("--level", type=int)
    edit.add_argument("--prestige", type=int)
    edit.add_argument("--experience", type=int)
    edit.add_argument("--field", action="append", default=[], type=parse_assignment)
    editor = subparsers.add_parser("editor")
    editor.add_argument("--port", type=int, default=0)
    editor.add_argument("--no-browser", action="store_true")
    parser.set_defaults(repository=repository)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.state is not None:
        path = args.state.resolve()
    elif args.game_dir is not None:
        path = private_profile_path(args.game_dir, args.title_id, args.user_id)
    else:
        print("Could not locate CODOL; pass --game-dir or --state.", file=sys.stderr)
        return 2

    try:
        if args.action == "path":
            print(path)
            return 0
        if args.action == "show":
            print(json.dumps(profile_document(path, args.user_id), indent=2, ensure_ascii=False))
            return 0
        if args.action == "editor":
            return run_editor(
                path,
                args.user_id,
                args.repository / "tools" / "profile" / "CodolProfileEditor.html",
                args.port,
                not args.no_browser,
            )
        if is_game_running():
            raise RuntimeError("请先关闭 CODOL，再修改玩家档案。")
        profile, exists = load_or_create(path, args.user_id)
        if args.action == "create":
            if exists:
                print(f"Privateprofile already exists: {path}")
                return 0
        else:
            current = profile.progression()
            level = args.level if args.level is not None else current["level"]
            prestige = args.prestige if args.prestige is not None else current["prestige"]
            experience = args.experience
            if experience is None and args.level is None and args.prestige is None:
                experience = current["experience"]
            profile.set_progression(level=level, prestige=prestige, experience=experience)
            for name, raw in args.field:
                field = FIELDS.get(name)
                if field is None:
                    raise ValueError(f"unknown field: {name}")
                profile.set(name, float(raw) if field.kind == "float" else int(raw, 0))
        write_profile(path, profile)
        print(f"Saved Privateprofile: {path}")
        print(json.dumps(profile.progression(), ensure_ascii=False))
        return 0
    except (OSError, ValueError, ProfileError, RuntimeError) as error:
        print(f"Profile operation failed: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
