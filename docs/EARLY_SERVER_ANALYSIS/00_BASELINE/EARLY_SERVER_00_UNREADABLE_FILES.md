# EARLY_SERVER_00 — 不可读 / 疑似损坏 / 格式不明文件

> 阶段 0 交付物。范围：样本根 `D:\BaiduNetdiskDownload\CODOL-AlphaBuild_By_Antia(20261006)\CODOL-AlphaBuild By Antia\CODOL_Server`（15,754 文件）。

## 1. 结论（CONFIRMED）

**不可读文件：0。** **疑似损坏文件：0。**

- 全量遍历 15,754 个文件，全部成功打开并读取完整内容以计算 SHA-256；无权限错误、无 I/O 错误、无长度截断。
- 证据：`00_BASELINE\_summary.json` → `"unreadable_count": 0`，`"unreadable": []`。
- 证据：`00_BASELINE\EARLY_SERVER_00_FILE_MANIFEST.csv` 中 `read_error` 列全为空值（无任何一行标记读取失败）。

## 2. 判定方法

1. `_tools\manifest.py` 对每个文件：以二进制只读方式打开 → 分块计算 SHA-256 → 记录实际读取字节数 → 与实际 `stat` 大小比对。
2. 任何打开失败、读取异常或长度不一致者，会被写入 `_summary.json` 的 `unreadable` 数组，并在清单 `read_error` 列标注原因。
3. 本轮结果为空数组 / 空列，因此不存在不可读项。

## 3. 关于"格式不明"文件

阶段 0 不对文件"格式是否正确"下结论——只判定**可读性**。样本中存在大量：

- 无扩展名文件（`no-extension` 类别 1,647 个）；
- 二进制数据文件（`binary-data` 11 个）；
- 专有游戏归档（`game-archive` 1 个，即 `dedicated\bin\home\main\sh1x_svr_scripts.iwd`，4,277,656 B）。

这些文件**全部可读**，其格式归属与可解析性在阶段 1/3 由签名与内容分析处理，不在此处归类为"格式不明"。任何在本轮无法进一步解析的专有格式，在后续阶段以 `UNKNOWN`/`CANDIDATE` 明确标注，而非在此处武断排除。

## 4. 排除策略说明

- 未按扩展名预先排除任何文件：全量 15,754 个文件均纳入清单与哈希。
- 未因文件"看起来无关"（如 `build\pyenv`、`build\pyinstaller` 内的 Python 运行库）而从基线中剔除——它们在阶段 1 的**资产地图**中按业务相关性分类，但在阶段 0 的**完整性基线**中必须全部纳入，以保证样本可复算。
- 无任何文件被跳过、跳过原因无一项成立。

## 5. 交付物

| 文件 | 内容 |
|---|---|
| `00_BASELINE\EARLY_SERVER_00_UNREADABLE_FILES.md` | 本报告 |
| `00_BASELINE\_summary.json` | 机器可读汇总（含 `unreadable_count`/`unreadable`） |
| `00_BASELINE\EARLY_SERVER_00_FILE_MANIFEST.csv` | 全量清单（含 `read_error` 列） |
