#pragma once

#include <windows.h>

#include <map>
#include <string>
#include <vector>

namespace codol {

enum class BootDepth {
  ProcessNotCreated = 0,
  ExeEntry = 1,
  BaseOrdinal1 = 2,
  BaseVmBoundary = 3,
  NewBaseExeBootstrap = 4,
  TenProxyProjectDll = 5,
  FilesystemAssetInit = 6,
  Engine = 7,
  GameInit = 8,
  Running = 9
};

struct ModuleSnapshot {
  std::wstring path;
  uintptr_t base = 0;
  uintptr_t size = 0;
};

struct LaunchResult {
  DWORD launcherPid = 0;
  DWORD gamePid = 0;
  DWORD mainThreadId = 0;
  HANDLE process = nullptr;
  HANDLE thread = nullptr;
  BootDepth depth = BootDepth::ProcessNotCreated;
  std::vector<ModuleSnapshot> modules;
  DWORD exitCode = 0;
  std::wstring lastKnownModule;
  uintptr_t lastKnownRva = 0;
  DWORD lastError = 0;
};

class Launcher {
 public:
  explicit Launcher(const std::wstring& configPath);

  int Run(int argc, wchar_t** argv);

 private:
  std::wstring configPath_;
  bool diagnostic_ = false;
  bool verbose_ = false;
  bool wait_ = false;
  bool monitor_ = true;
  bool tclsEnabled_ = false;
  std::wstring gamePath_;
  std::wstring workingDirectory_;
  std::wstring arguments_;

  bool LoadConfig();
  std::wstring ExpandPath(const std::wstring& value) const;
  void PrintDiagnostic(const LaunchResult& result) const;
  void LogResult(const LaunchResult& result) const;
  int PrintUsage() const;
};

std::wstring Widen(const std::string& value);
std::string Narrow(const std::wstring& value);
std::wstring NowIso();
std::wstring Utf8PathFromArg(const wchar_t* value);
std::wstring GetLastErrorText(DWORD code);
std::wstring ModuleName(const std::wstring& path);
bool FileExists(const std::wstring& path);

}  // namespace codol
