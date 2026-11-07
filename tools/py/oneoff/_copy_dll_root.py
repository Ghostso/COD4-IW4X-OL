import shutil, os

src = r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\sandbox_datafix_20260929\Ayria\Plugins\CodolGameServer.Localnet32"
dst = r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\sandbox_datafix_20260929\CodolGameServer.dll"

shutil.copy2(src, dst)
print(f"Copied {src} to {dst}")
print("File size:", os.path.getsize(dst))
