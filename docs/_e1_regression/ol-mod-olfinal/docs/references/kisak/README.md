# KisakCOD 与 Kisak Black 开发文章

这里保存 LWSS（SwagSoftware）关于 [KisakCOD](https://github.com/SwagSoftware/KisakCOD) 和 [KisakBlack](https://github.com/SwagSoftware/KisakBlack) 的两篇开发回顾。它们是理解 COD 系列反编译实践、参考资料选择和调试方法的有价值的一手叙述，但不是 CODOL 行为的权威证据。

## 阅读入口

| 文章 | 英文原文 | 中文直译 | 中文总结 |
| --- | --- | --- | --- |
| Duty of Kisak | [`original/2025-06-25-Duty-Of-Kisak.md`](original/2025-06-25-Duty-Of-Kisak.md) | [`translations/duty-of-kisak.zh-CN.md`](translations/duty-of-kisak.zh-CN.md) | [`duty-of-kisak.summary.zh-CN.md`](duty-of-kisak.summary.zh-CN.md) |
| Kisak Black | [`original/2026-05-10-Kisak-Black.md`](original/2026-05-10-Kisak-Black.md) | [`translations/kisak-black.zh-CN.md`](translations/kisak-black.zh-CN.md) | [`kisak-black.summary.zh-CN.md`](kisak-black.summary.zh-CN.md) |

## 来源与归属

- 作者站点：[Duty of Kisak](https://lwss.github.io/Duty-Of-Kisak/)、[Kisak Black](https://lwss.github.io/Kisak-Black/)
- 站点仓库：[LWSS/lwss.github.io](https://github.com/LWSS/lwss.github.io)
- 本地还原基准：站点仓库提交 `47ec14cec78b3b7405c07aab3e3f1e2a6fdb2a2b`
- 获取日期：2026-07-31

`original/` 中的文件直接来自站点仓库 `_posts/`，保留了原始 front matter、正文、链接和资源路径。文章文字、截图和视频的权利仍归原作者及相关权利人所有；本站仓库中的 MIT 文件来自 Jekyll 站点模板，不能据此推定文章内容采用 MIT 授权。中文文件是为研究和阅读制作的非官方翻译，观点与措辞属于原作者，不代表本项目立场。

## 媒体资源

两篇文章共引用 57 张图片和 28 段视频。图片总计约 14.5 MiB，已保存在 `images/`，原文可以直接显示。视频总计约 410.6 MiB，不进入 Git 历史；`media-manifest.json` 保存每个资源的原始 URL、字节数和 SHA-256。

需要完整离线阅读原文时，可按需下载视频：

```powershell
powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File `
  .\docs\references\kisak\Fetch-KisakVideos.ps1
```

下载结果位于 ignored 的 `videos/`。脚本先写入临时文件，校验长度和 SHA-256 后再替换目标文件；已有且校验通过的文件不会重复下载。

## 使用边界

这两篇文章能提供方法论和结构蓝本，例如如何组合 PDB、MAP、近缘源码、反编译和运行调试，以及如何把批量机械工作工具化。涉及 CODOL 的函数 ABI、数据所有权、wire contract 和状态机时，仍必须回到 CODOL xref、反编译、wire bytes 与自然运行证据。
