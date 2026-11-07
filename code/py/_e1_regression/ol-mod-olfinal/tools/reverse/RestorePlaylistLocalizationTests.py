#!/usr/bin/env python3

from RestorePlaylistLocalization import restore_document


def main() -> int:
    damaged = (
        'name chinese "Map: Nuketown"\n'
        'name english "-ºËµ¯Ð¡Õò"\n'
        'description chinese "Charge TDM on Nuketown only."\n'
        'description english "ÈËÊý9V9¡£"\n'
    ).encode("utf-8")
    restored, stats = restore_document(damaged)
    text = restored.decode("gbk")
    assert 'name chinese "-核弹小镇"' in text
    assert 'name english "Map: Nuketown"' in text
    assert 'description chinese "人数9V9。"' in text
    assert 'description english "Charge TDM on Nuketown only."' in text
    assert stats.localized_pairs == 2
    assert stats.chinese_characters == 6
    utf8, _ = restore_document(damaged, "utf-8")
    assert utf8.decode("utf-8") == text
    print("RestorePlaylistLocalization tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
