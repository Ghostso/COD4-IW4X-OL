#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <Windows.h>

#include "RuntimeLog.hpp"
#include "ProcessRole.hpp"

#include <algorithm>
#include <array>
#include <chrono>
#include <cctype>
#include <cstdio>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <mutex>
#include <sstream>
#include <string>

namespace
{
    std::mutex LogMutex;
    HANDLE ConsoleOutput = INVALID_HANDLE_VALUE;

    // ONE OPEN HANDLE PER CHANNEL, INSTEAD OF AN open+close PER LINE.
    //
    // What was here before: a named mutex, std::filesystem::create_directories, and an
    // std::ofstream constructed and destroyed for EVERY line -- 132 us of the 135 us a line cost,
    // measured, and 180 lines a second. The average was survivable. The tail was not: reopening a
    // 224 MB file that often, from three processes, is the shape of the 2-to-6 second frame
    // stalls that showed up in think, begin and end indiscriminately, which is to say not in any
    // one of them.
    //
    // The named mutex it replaces was keyed by GetCurrentProcessId(), so each process took its
    // OWN mutex and it never excluded anything -- the client and the dedicated both write this
    // same file. FILE_APPEND_DATA is what actually makes that safe: a handle opened with append
    // access and no FILE_WRITE_DATA gets atomic appends from the filesystem, across processes,
    // with no lock of ours involved. The std::mutex below is only for our own threads.
    //
    // Nothing is buffered in user space, so a line that WriteFile returned from survives a crash
    // of this process -- the old ofstream buffered, which is worse for exactly the case these
    // logs exist to diagnose.
    std::array<HANDLE, 2> ChannelFiles{
        INVALID_HANDLE_VALUE, INVALID_HANDLE_VALUE };

    const char *roleName(const OlMod::ProcessRole role)
    {
        switch (role)
        {
        case OlMod::ProcessRole::Client: return "client";
        case OlMod::ProcessRole::Dedicated: return "dedicated";
        default: return "combined";
        }
    }

    const char *channelName(const OlMod::RuntimeLog::Channel channel)
    {
        return channel == OlMod::RuntimeLog::Channel::Backend
            ? "backend"
            : "game-server";
    }

    std::filesystem::path executableDirectory()
    {
        std::array<wchar_t, 32768> path{};
        const auto size = GetModuleFileNameW(
            nullptr, path.data(), static_cast<DWORD>(path.size()));
        if (!size || size >= path.size())
            return std::filesystem::current_path();
        return std::filesystem::path(path.data()).parent_path();
    }

    std::filesystem::path logPath(const OlMod::RuntimeLog::Channel channel)
    {
        const auto fileName = channel == OlMod::RuntimeLog::Channel::Backend
            ? L"AlwaysofflineRe.Localnet32.log"
            : L"CodolGameServer.log";
        return executableDirectory() / L"Ayria" / L"Logs" / fileName;
    }

    HANDLE ensureChannelFile(const OlMod::RuntimeLog::Channel channel)
    {
        const auto index = channel == OlMod::RuntimeLog::Channel::Backend
            ? std::size_t{ 0 }
            : std::size_t{ 1 };
        if (ChannelFiles[index] != INVALID_HANDLE_VALUE)
            return ChannelFiles[index];
        const auto path = logPath(channel);
        std::error_code error;
        std::filesystem::create_directories(path.parent_path(), error);
        const auto handle = CreateFileW(
            path.c_str(),
            FILE_APPEND_DATA,
            FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,
            nullptr,
            OPEN_ALWAYS,
            FILE_ATTRIBUTE_NORMAL,
            nullptr);
        if (handle != INVALID_HANDLE_VALUE)
            ChannelFiles[index] = handle;
        return ChannelFiles[index];
    }

    std::string formatLine(
        const OlMod::RuntimeLog::Channel channel,
        const std::string_view message)
    {
        // GetLocalTime and a fixed-width stamp, rather than system_clock -> time_t ->
        // localtime_s -> ostringstream -> put_time. Same output, none of the locale machinery,
        // and this runs on the frame thread for every line.
        SYSTEMTIME local{};
        GetLocalTime(&local);
        std::array<char, 24> stamp{};
        std::snprintf(
            stamp.data(), stamp.size(), "[%04u-%02u-%02u %02u:%02u:%02u] ",
            local.wYear, local.wMonth, local.wDay,
            local.wHour, local.wMinute, local.wSecond);

        std::string line;
        line.reserve(message.size() + 64);
        line.append(stamp.data());
        line.push_back('[');
        line.append(roleName(OlMod::processRole()));
        line.push_back('/');
        line.append(channelName(channel));
        line.append("] ");
        line.append(message);
        line.append("\r\n");
        return line;
    }

    void ensureConsole()
    {
        if (ConsoleOutput != INVALID_HANDLE_VALUE)
            return;
        auto consoleWindow = GetConsoleWindow();
        if (consoleWindow && !IsWindowVisible(consoleWindow))
        {
            static_cast<void>(FreeConsole());
            consoleWindow = nullptr;
        }
        if (!consoleWindow)
        {
            static_cast<void>(AllocConsole());
            consoleWindow = GetConsoleWindow();
        }
        if (consoleWindow)
            ShowWindow(consoleWindow, SW_SHOW);

        const auto role = OlMod::processRole();
        SetConsoleTitleW(role == OlMod::ProcessRole::Dedicated
            ? L"CODOL Dedicated Server"
            : role == OlMod::ProcessRole::Client
                ? L"CODOL Client / Backend"
                : L"CODOL Combined Runtime");
        ConsoleOutput = CreateFileW(
            L"CONOUT$", GENERIC_WRITE,
            FILE_SHARE_READ | FILE_SHARE_WRITE, nullptr, OPEN_EXISTING,
            FILE_ATTRIBUTE_NORMAL, nullptr);

        // TURN QUICKEDIT OFF, OR A CLICK IN THIS WINDOW STOPS THE GAME.
        //
        // QuickEdit is on by default. Clicking in the window enters selection mode, and every
        // WriteFile to the console then BLOCKS until the selection is dismissed -- including the
        // ones this function's caller makes from the frame thread. Measured as FRAME THREAD
        // STALLED for seconds at a time, appearing in whichever frame phase happened to log when
        // the click landed, and healing on its own the moment the window was dismissed. A server
        // must not be stoppable by a mouse.
        if (auto *const input = CreateFileW(
                L"CONIN$", GENERIC_READ | GENERIC_WRITE,
                FILE_SHARE_READ | FILE_SHARE_WRITE, nullptr, OPEN_EXISTING,
                FILE_ATTRIBUTE_NORMAL, nullptr);
            input != INVALID_HANDLE_VALUE)
        {
            DWORD mode{};
            if (GetConsoleMode(input, &mode))
            {
                constexpr DWORD QuickEdit = 0x0040;   // ENABLE_QUICK_EDIT_MODE
                constexpr DWORD Extended = 0x0080;    // ENABLE_EXTENDED_FLAGS, required to apply it
                static_cast<void>(SetConsoleMode(
                    input, (mode & ~QuickEdit) | Extended));
            }
            static_cast<void>(CloseHandle(input));
        }
    }
}

namespace OlMod::RuntimeLog
{
    bool consoleEnabled()
    {
        std::array<char, 32> value{};
        const auto size = GetEnvironmentVariableA(
            "OLMOD_CONSOLE_LOG", value.data(), static_cast<DWORD>(value.size()));
        if (!size || size >= value.size())
            return false;
        std::string normalized(value.data(), size);
        std::transform(normalized.begin(), normalized.end(), normalized.begin(),
            [](const unsigned char character) {
                return static_cast<char>(std::tolower(character));
            });
        return normalized == "1" || normalized == "true" ||
            normalized == "yes" || normalized == "on";
    }

    bool verbose()
    {
        static const bool enabled = [] {
            std::array<char, 32> value{};
            const auto size = GetEnvironmentVariableA(
                "OLMOD_VERBOSE_LOG", value.data(),
                static_cast<DWORD>(value.size()));
            if (!size || size >= value.size())
                return false;
            std::string normalized(value.data(), size);
            std::transform(normalized.begin(), normalized.end(),
                normalized.begin(), [](const unsigned char character) {
                    return static_cast<char>(std::tolower(character));
                });
            return normalized == "1" || normalized == "true" ||
                normalized == "yes" || normalized == "on";
        }();
        return enabled;
    }

    void write(const Channel channel, const std::string_view message)
    {
        const auto line = formatLine(channel, message);
        using Clock=std::chrono::steady_clock;
        const auto began=Clock::now();
        std::scoped_lock lock(LogMutex);
        const auto locked=Clock::now();

        const auto file=ensureChannelFile(channel);
        if (file != INVALID_HANDLE_VALUE)
        {
            DWORD written{};
            static_cast<void>(WriteFile(
                file, line.data(), static_cast<DWORD>(line.size()),
                &written, nullptr));
        }
        const auto filed=Clock::now();

        // Only when somebody is listening. With no debugger attached this still takes a global
        // system lock and walks the DBWIN buffer, and it was unconditional.
        if (IsDebuggerPresent())
            OutputDebugStringA(line.c_str());

        // Read the environment ONCE. This was a GetEnvironmentVariableA per line, and the answer
        // cannot change inside a process.
        static const bool console = consoleEnabled();
        if (console)
        {
            ensureConsole();
            if (ConsoleOutput != INVALID_HANDLE_VALUE)
            {
                DWORD written{};
                WriteFile(ConsoleOutput,line.data(),static_cast<DWORD>(line.size()),
                    &written,nullptr);
            }
        }
        const auto done=Clock::now();
        static Clock::time_point lastStall{}; // guarded by LogMutex
        if (done-began>=std::chrono::milliseconds(20) &&
            done-lastStall>=std::chrono::seconds(1) && file!=INVALID_HANDLE_VALUE)
        {
            lastStall=done;
            const auto us=[](auto a,auto b) {
                return std::chrono::duration_cast<std::chrono::microseconds>(b-a).count();
            };
            // File-only and nonrecursive: never diagnose a blocked console by
            // writing the diagnostic back into that same console.
            const auto diagnostic=formatLine(channel,"LOGSTALL lockUs="+
                std::to_string(us(began,locked))+" fileUs="+std::to_string(us(locked,filed))+
                " consoleDebugUs="+std::to_string(us(filed,done))+
                " prefix="+std::string(message.substr(0,96)));
            DWORD written{};
            WriteFile(file,diagnostic.data(),static_cast<DWORD>(diagnostic.size()),&written,nullptr);
        }
    }
}
