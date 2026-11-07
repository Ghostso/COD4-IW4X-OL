#include <windows.h>

#include <iostream>

#include "Launcher.h"

int wmain(int argc, wchar_t** argv) {
  // Look for CODOLLauncher.ini next to the EXE, then in the current directory.
  std::wstring configPath = L"CODOLLauncher.ini";
  wchar_t module[MAX_PATH] = {};
  if (GetModuleFileNameW(nullptr, module, MAX_PATH)) {
    std::wstring exe = module;
    size_t slash = exe.find_last_of(L"\\/");
    std::wstring candidate;
    if (slash != std::wstring::npos) {
      candidate = exe.substr(0, slash + 1) + L"CODOLLauncher.ini";
    } else {
      candidate = L"CODOLLauncher.ini";
    }
    if (GetFileAttributesW(candidate.c_str()) != INVALID_FILE_ATTRIBUTES) {
      configPath = candidate;
    }
  }

  codol::Launcher launcher(configPath);
  return launcher.Run(argc, argv);
}
