#pragma once

#include <windows.h>

#include <map>
#include <string>

namespace codol {

// Records the launch context that is actually confirmed by evidence.
// Fields without confirmed offsets/encodings are intentionally not filled.
struct LauncherContext {
  DWORD launcherPid = 0;
  DWORD gamePid = 0;
  std::wstring gamePath;
  std::wstring workingDirectory;
  std::wstring commandLine;
  std::map<std::wstring, std::wstring> environment;
  HANDLE sharedMemory = nullptr;
  HANDLE mutex = nullptr;
  HANDLE event = nullptr;
  std::wstring mappingName;
  bool tclsMappingCreated = false;

  void ClearHandles();
};

}  // namespace codol
