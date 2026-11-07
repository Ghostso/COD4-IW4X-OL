import io
import os
import re


ROOT = r"D:\BaiduNetdiskDownload\使命召唤OL"
REPORT = os.path.join(
    ROOT, "CODOLServer", "_static_reports",
    "02_RUNTIME_DLL_EXE_DEPENDENCY_GRAPH.txt")


def block_for(text, name, base_only=False):
    blocks = re.split(r"(?=COMPONENT \d+: )", text)
    for block in blocks:
        m = re.match(r"COMPONENT \d+: (.+?)\n", block)
        if not m:
            continue
        if m.group(1) == name:
            return block
    return ""


def field(block, key, default="-"):
    m = re.search(r"^\s*%s=(.*)$" % re.escape(key), block, re.M)
    return m.group(1).strip() if m else default


def export_names(block):
    out = []
    for line in block.splitlines():
        m = re.match(r"\s+(\d+)\s+0x[0-9A-Fa-f]+\s+(.+?)\s*$", line)
        if m:
            out.append(m.group(2).strip())
    return out


def sha_of(block):
    m = re.search(r"SHA-256=([0-9A-F]{64})", block)
    return m.group(1) if m else "-"


def size_of(block):
    m = re.search(r"bytes=(\d+)", block)
    return m.group(1) if m else "-"


def import_modules(block):
    out = []
    for line in block.splitlines():
        m = re.match(r"\s+(\S+\.dll)\s+APIs=(\d+)", line)
        if m:
            out.append("%s(%s)" % (m.group(1), m.group(2)))
    return out


def urls(block):
    out = []
    lines = block.splitlines()
    in_strings = False
    collecting = False
    for line in lines:
        if line.strip() == "[\u53ef\u7591/\u7f51\u7edc/\u52a0\u5bc6\u5b57\u7b26\u4e32]":
            in_strings = True
            continue
        if in_strings and line.startswith("["):
            in_strings = False
        if not in_strings:
            continue
        if re.match(r"\s+(url|domain|ip|port) \(", line):
            collecting = True
            continue
        if re.match(r"\s+(crypto|module|suspicious|cert_url) \(", line):
            collecting = False
            continue
        if collecting and line.startswith("    "):
            out.append(line.strip())
    seen = []
    for u in out:
        if ("qq.com" in u or "iips" in u.lower()
                or u.startswith(("udp://", "tcp://", "http://", "https://"))) \
                and "symantec" not in u and "verisign" not in u \
                and "thawte" not in u and "digicert" not in u:
            if u not in seen:
                seen.append(u)
    return seen


def main():
    text = io.open(REPORT, encoding="utf-8").read()

    key = [
        ("iips.dll", "72DDB9D15626B5A0A001347DA141FB944A9F862DB713E01C06A964EC8DC35348"),
        ("IFS.dll", "5B0324E0B2BA3545A6C02626287D4FBC6A3116594744F4647333982D85508421"),
        ("IIPSHost.dll", "F44F2B1C481BA6F91C1095A950F6531B19DD2FE1AC702BB0A7B7B3226E41BE9E"),
        ("IIPSHostApp.exe", "B507B47A80CAF135EE95006AE1A3AD62777CB3DF8AA339EA835117A1B508F0C8"),
        ("TenProxy.dll", "A5EE7EDE762C473F58A87B214213097F6DDA8950AC537B0A959389AEF31348CB"),
        ("TenRpcs.dll", "0CCD33E7CF7C3A909C2986D65AD4B891527FF207636D09AE1623A23DF3BE7FAE"),
        ("GameRpcs.dll", "277A43306B940E77A20B26529F087B7BDEA71E1C0F55CA0C1F4820F7D528CC38"),
        ("GDPLoader.dll", "4A6E09B86869F03D27203A9AFDE9BAF97EB460E9E14ECA05085CFA2BDF824241"),
        ("GameDataPlatformServer.dll",
         "BBB5808B070DC50E93092100B659E7E2B2B83402C10F0C2F0196F98121B35CC9"),
        ("ace-ats32.dll",
         "3CA1238267E0299E136D5153ABAB52124331AC9E78EABE749E5E84A32392EF45"),
        ("ACE-DRV32.dll",
         "700E77786256C91BB089C9B1158664511212D802344C9B89494B043903D12466"),
        ("BugTrace.dll",
         "1FDB07E47C0BAD6024309D6DCDDA0EED3B1A87BCAC61B57DC0EF750CB2225646"),
        ("TCLSClient.dll",
         "5C5D6BCE0AE7A98FD8180798BD6173E647AC5714A8F86DBB22E5678FBDE11632"),
        ("TPSvc.exe",
         "13A0C6F0C0C7F484C601AC189CDEE15B578C30FDEBED7E0F1A03CA3074A65ADE"),
        ("codoMP_client_shipRetailBase.dll",
         "EF75220DE1D6973F34C7069F5BF211B11BD61520C6C0DE1882F7359FA5BC6A20"),
    ]

    lines = []
    add = lines.append
    add("")
    add("=" * 112)
    add("核心结论（替代边界，静态证据）")
    add("=" * 112)
    add("")
    add("C-01 客户端入口是 codoMP_client_shipRetail.exe，它只声明导入")
    add("      codoMP_client_shipRetailBase.dll!ordinal_1，全部引擎代码在 Base.dll 中。")
    blk = block_for(text, "codoMP_client_shipRetail.exe")
    add("      EXE shim: bytes=%s sha256=%s" % (size_of(blk), sha_of(blk)))
    blk = block_for(text, "codoMP_client_shipRetailBase.dll")
    add("      Base  DLL: bytes=%s sha256=%s bits=32" % (
        size_of(blk), sha_of(blk)))
    add("      含义：替换/绕过单机化不能改 EXE 的调用约定，必须保持")
    add("      Base.dll 的 ordinal_1 boundary（或整体替换 Base.dll）。")
    add("")
    add("C-02 IIPS 平台由 4 个可替换单元组成，且导出面极小：")
    for name in ("iips.dll", "IFS.dll", "IIPSHost.dll", "IIPSHostApp.exe"):
        blk = block_for(text, name)
        exps = export_names(blk)
        add("      %-18s size=%-9s exports=%d %s" % (
            name, size_of(blk), len(exps), exps))
    add("      IIPSHostApp.exe 无导出，只做 Host 进程启动壳。")
    add("")
    add("C-03 IIPSHost.dll 是唯一持有策略/下载服务器地址的单元：")
    blk = block_for(text, "IIPSHost.dll")
    add("      imports: %s" % ", ".join(import_modules(blk)))
    for u in urls(blk):
        add("      endpoint string: %s" % u)
    add("      含义：要替代服务器，至少要让 Host 的 ctrl/speed 端点指向本地")
    add("      实现，或直接替换 IIPSHost.dll 的 2 个导出 + Download.dll 依赖。")
    add("")
    add("C-04 iips.dll 不直接持有所需下载域名，只经共享内存/管道连 Host：")
    blk = block_for(text, "iips.dll", )
    add("      imports: %s" % ", ".join(import_modules(blk)))
    add("      shared-memory/lock names: Global\\SharedSpaceName_, "
        "Local\\IIPSHostSharedInfo, Global\\IIPSShareState_MMF_, "
        "Global\\IIPSShareState_Mutex_")
    for u in urls(blk):
        add("      endpoint string: %s" % u)
    add("      含义：iips.dll 是客户端侧 API 面（4 导出），服务器替代主要在")
    add("      Host 侧；iips.dll 本身多半只需保持 ABI 与共享内存契约。")
    add("")
    add("C-05 工具目录存在 iips.dll 的第二份不同二进制（380928 字节，")
    add("      SHA-256 2ED4782491592EC837DF12E8A48D8F763DE417A18E466E68DE5B171E59FCB4C2），")
    add("      与主副本 347704 字节/72DDB9D1... 不同：导出同为 4 个，")
    add("      sections 由 5 变为 6，且无 Authenticode 签名。")
    add("      这是既有实验/存根产物，未进入当前沙箱主链路，替代时需明确取舍。")
    add("")
    add("C-06 TenProxy.dll / TNProxy.dll 与 TCLS 代理层：")
    for name in ("TenProxy.dll", "TNProxy.dll"):
        blk = block_for(text, name)
        add("      %-14s sha=%s size=%s exports=%s" % (
            name, sha_of(blk), size_of(blk), export_names(blk)))
    add("      含义：TCLS/TenProxy 是否参与登录由沙箱是否启动 TenProxy 决定；")
    add("      静态上它们是独立可替换层，不与 IIPS 导出面耦合。")
    add("")
    add("C-07 反作弊/保护层（ACE、TerSafe、tvsd、PolicyProbe、TCJ、TenSLX）")
    add("      在沙箱主链路中为独立 DLL/EXE，导出面 3-21 个，且带驱动/服务特征")
    add("      字符串。它们是可移除/存根化的候选，不承载游戏资源协议。")
    add("")
    add("C-08 未发现任何 IIPS/TCLS 组件直接声明游戏内战斗服端口或协议常量；")
    add("      域名/端口集中在 IIPSHost.dll（ctrl.iips.qq.com:8000、")
    add("      iips.speed.qq.com、stat.iips.qq.com）。游戏服端口需由外部")
    add("      配置/运行时证据补齐，静态字符串不足以证明。")
    add("")
    add("未解项")
    add("  U-01 IIPSHost.dll 的 2 个导出名与其 ABI 需与 IIPSHostApp.exe 的")
    add("       调用点逐一对应；本报告给出导出与调用方，不展开函数体语义。")
    add("  U-02 Download.dll 的 35 个导入 API 在 Host 侧的构造/回调关系尚未")
    add("       静态反编译确证。")
    add("  U-03 沙箱 CODOL 子树的 TCLS/TenProtect 与 TGuard 是否在运行时实际")
    add("       加载，需要既有动态证据交叉确认（本报告只做静态覆盖）。")
    add("  U-04 工具目录 iips.dll 380928 字节副本的生成来源需查实验记录。")
    add("")
    add("可复查命令")
    add("  python \"%s\"" % os.path.join(
        ROOT, "CODOLServer", "_static_reports", "02_runtime_pe_scan.py"))
    add("  python \"%s\" iips.dll IFS2.dll IIPSHost.dll" % os.path.join(
        ROOT, "CODOLServer", "_static_reports", "_02_extract_core.py"))
    add("  Get-Item -LiteralPath '<path>' | Select-Object Length,LastWriteTime")
    add("  Get-FileHash -LiteralPath '<path>' -Algorithm SHA256")
    add("  python -c \"import pefile;p=pefile.PE(r'<path>');"
        "print(p.FILE_HEADER.Machine,p.OPTIONAL_HEADER.Magic)\"")
    add("")
    add("=" * 112)
    add("END OF CORE CONCLUSIONS")
    add("=" * 112)

    with io.open(REPORT, "a", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    print("APPENDED", REPORT, "lines", len(lines))


if __name__ == "__main__":
    main()
