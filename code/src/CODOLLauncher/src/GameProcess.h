#pragma once

#include <windows.h>

#include <string>

#include "Launcher.h"

namespace codol {

class GameProcess {
 public:
  GameProcess(const std::wstring& path, const std::wstring& cwd,
              const std::wstring& args, DWORD creationFlags);
  ~GameProcess();

  bool Create();
  bool Resume();
  DWORD Pid() const { return pid_; }
  DWORD ThreadId() const { return threadId_; }
  HANDLE ProcessHandle() const { return process_; }
  HANDLE ThreadHandle() const { return thread_; }
  DWORD LastError() const { return lastError_; }

 private:
  std::wstring path_;
  std::wstring cwd_;
  std::wstring args_;
  DWORD creationFlags_ = 0;
  HANDLE process_ = nullptr;
  HANDLE thread_ = nullptr;
  DWORD pid_ = 0;
  DWORD threadId_ = 0;
  DWORD lastError_ = 0;
};

}  // namespace codol
