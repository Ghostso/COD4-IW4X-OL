#include "TCLSCompatibility.h"

#include <sstream>

#include "Launcher.h"

namespace codol {

TCLSCompatibility::~TCLSCompatibility() {
  if (view_) {
    UnmapViewOfFile(view_);
    view_ = nullptr;
  }
  if (mapping_) {
    CloseHandle(mapping_);
    mapping_ = nullptr;
  }
}

void TCLSCompatibility::Disable() {
  enabled_ = false;
  prepared_ = false;
  if (view_) {
    UnmapViewOfFile(view_);
    view_ = nullptr;
  }
  if (mapping_) {
    CloseHandle(mapping_);
    mapping_ = nullptr;
  }
}

bool TCLSCompatibility::Prepare(DWORD gamePid, bool ensurePresent) {
  if (!enabled_) {
    return false;
  }

  std::wostringstream name;
  name << L"TCLS_SHAREDMEMEMORY+" << gamePid;
  mappingName_ = name.str();

  // Try to use an existing mapping created by another process first.
  mapping_ = OpenFileMappingW(FILE_MAP_ALL_ACCESS, FALSE, mappingName_.c_str());
  if (!mapping_ && ensurePresent) {
    mapping_ = CreateFileMappingW(INVALID_HANDLE_VALUE, nullptr,
                                  PAGE_READWRITE, 0,
                                  static_cast<DWORD>(mappingSize_),
                                  mappingName_.c_str());
  }
  if (!mapping_) {
    return false;
  }

  view_ = MapViewOfFile(mapping_, FILE_MAP_ALL_ACCESS, 0, 0, mappingSize_);
  if (!view_) {
    CloseHandle(mapping_);
    mapping_ = nullptr;
    return false;
  }

  // No offset/size/encoding evidence is known beyond the mapping name.
  // Keep the mapped buffer zeroed rather than inventing a protocol.
  memset(view_, 0, mappingSize_);
  prepared_ = true;
  return true;
}

}  // namespace codol
