#include "RuntimePaths.hpp"

#include <algorithm>
#include <cwctype>

namespace OlMod::Localnetworking
{
    RuntimePaths runtimePathsFromModule(const std::filesystem::path &modulePath)
    {
        const auto plugins = modulePath.parent_path().lexically_normal();
        const auto root = plugins.parent_path().lexically_normal();
        return RuntimePaths{
            root,
            plugins,
            root / L"Logs",
            root / L"Assets",
        };
    }

    bool isLocalnetPluginFilename(const std::wstring_view filename)
    {
        constexpr std::wstring_view suffix = L".localnet32";
        if (filename.size() < suffix.size())
            return false;
        const auto tail = filename.substr(filename.size() - suffix.size());
        return std::equal(
            tail.begin(),
            tail.end(),
            suffix.begin(),
            [](const wchar_t left, const wchar_t right) {
                return std::towlower(left) == right;
            });
    }
}
