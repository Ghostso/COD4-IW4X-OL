#pragma once

#include <windows.h>

#include <string>

namespace codol {

class TCLSCompatibility {
 public:
  TCLSCompatibility() = default;
  ~TCLSCompatibility();

  void Disable();

  // Creates a mapping named TCLS_SHAREDMEMEMORY+<gamePid> and maps a
  // zero-filled buffer before the game is resumed. This matches the only
  // launcher-provided IPC name confirmed by historical TenproxyLog files.
  bool Prepare(DWORD gamePid, bool ensurePresent = true);

  bool Enabled() const { return enabled_; }
  void SetEnabled(bool enabled) { enabled_ = enabled; }
  const std::wstring& MappingName() const { return mappingName_; }
  SIZE_T MappingSize() const { return mappingSize_; }
  HANDLE MappingHandle() const { return mapping_; }
  void* View() const { return view_; }

 private:
  bool enabled_ = false;
  bool prepared_ = false;
  HANDLE mapping_ = nullptr;
  void* view_ = nullptr;
  std::wstring mappingName_;
  SIZE_T mappingSize_ = 0x10000;
};

}  // namespace codol
