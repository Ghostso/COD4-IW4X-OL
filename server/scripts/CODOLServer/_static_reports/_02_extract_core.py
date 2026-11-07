import io
import re
import sys


PATH = (
    r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_static_reports"
    r"\02_RUNTIME_DLL_EXE_DEPENDENCY_GRAPH.txt")

TARGETS = [
    "iips.dll", "IFS.dll", "IFS2.dll", "IIPSHost.dll", "IIPSHostApp.exe",
    "IIPSVFS.dll", "IIPSStats.dll", "IIPSRepair.dll", "IIPSLaunchRestore.dll",
    "IIPSCheck.dll", "iips_policymsg.dll", "Download.dll", "TenProxy.dll",
    "TNProxy.dll", "TenRpcs.dll", "GameRpcs.dll", "GDPLoader.dll",
    "GDPImpl.dll", "GDPCODOTrail.dll", "GameDataPlatformServer.dll",
    "TCLSClient.dll", "TCLS.dll", "TPSvc.exe", "tpsvcBase.dll", "Client.exe",
    "ClientBase.dll", "TenioDL.dll", "TenioTPF.dll",
]


def main():
    targets = set(sys.argv[1:]) or set(TARGETS)
    text = io.open(PATH, encoding="utf-8").read()
    blocks = re.split(r"(?=COMPONENT \d+: )", text)
    for block in blocks:
        m = re.match(r"COMPONENT \d+: (.+?)\n", block)
        if not m or m.group(1) not in targets:
            continue
        print("=" * 100)
        lines = block.splitlines()
        section = ""
        for line in lines:
            if line.startswith("["):
                section = line.strip()
            if section in ("[权威路径]", "[其他副本]", "[PE 基本信息]",
                           "[字节/SHA-256]", "[版本资源]"):
                print(line)
            elif section == "[导入边]":
                if line.startswith("  ") and " APIs=" in line:
                    m_imp = re.match(r"  (\S+)\s+APIs=(\d+)", line)
                    if m_imp:
                        print("  IMPORT %s APIs=%s" % (
                            m_imp.group(1), m_imp.group(2)))
            elif section == "[导出边]":
                if re.match(r"  \d+\s+0x", line):
                    print(line)
            elif section == "[依赖边]":
                print(line)
            elif section == "[可疑/网络/加密字符串]":
                if re.match(
                        r"  (?:url|domain|ip|port|crypto|suspicious) \(",
                        line):
                    print(line)
                elif line.startswith("    "):
                    print(line[:360])
            elif section == "[调用边界]":
                print(line)


if __name__ == "__main__":
    main()
