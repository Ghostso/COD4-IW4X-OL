#include "GameProcess.h"

#include <shellapi.h>

#include "Launcher.h"

namespace codol {

GameProcess::GameProcess(const std::wstring& path, const std::wstring& cwd,
                         const std::wstring& args, DWORD creationFlags)
    : path_(path), cwd_(cwd), args_(args), creationFlags_(creationFlags) {}

GameProcess::~GameProcess() {
  if (thread_) {
    CloseHandle(thread_);
    thread_ = nullptr;
  }
  if (process_) {
    CloseHandle(process_);
    process_ = nullptr;
  }
}

bool GameProcess::Create() {
  std::wstring commandLine;
  if (!path_.empty() && path_[0] != L'"') {
    commandLine = L"\"";
    commandLine += path_;
    commandLine += L"\"";
  } else {
    commandLine = path_;
  }
  if (!args_.empty()) {
    commandLine += L" ";
    commandLine += args_;
  }

  // The original client is a 32-bit x86 game. Keep CREATE_SUSPENDED so the
  // launcher can create verified IPC before Base bootstrap makes any
  // OpenFileMappingW call.
  STARTUPINFOW si = {};
  si.cb = sizeof(si);
  PROCESS_INFORMATION pi = {};
  if (!CreateProcessW(path_.c_str(), &commandLine[0], nullptr, nullptr, FALSE,
                      creationFlags_, nullptr,
                      cwd_.empty() ? nullptr : cwd_.c_str(), &si, &pi)) {
    lastError_ = GetLastError();
    return false;
  }

  process_ = pi.hProcess;
  thread_ = pi.hThread;
  pid_ = pi.dwProcessId;
  threadId_ = pi.dwThreadId;
  return true;
}

bool GameProcess::Resume() {
  if (!thread_) {
    lastError_ = ERROR_INVALID_HANDLE;
    return false;
  }
  if (ResumeThread(thread_) == static_cast<DWORD>(-1)) {
    lastError_ = GetLastError();
    return false;
  }
  return true;
}

}  // namespace codol
