#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <Windows.h>

#include "ClientNoclipHotkey.hpp"
#include "ClientBatteryLookup.hpp"

#include "../shared/DedicatedControl.hpp"
#include "../shared/RuntimeLog.hpp"

#include <atomic>
#include <charconv>
#include <chrono>
#include <cstdlib>
#include <string>
#include <optional>
#include <thread>

namespace CodolGameServer
{
    namespace
    {
        // CONFIRMED PLAYED 2026-08-25: hold to fly, release and stand up with your
        // weapons. The player's own choice of key. VK_LMENU is LEFT ALT specifically -- VK_MENU
        // would also fire on right alt, and AltGr on a non-US layout sends right
        // alt together with control, which is a keystroke nobody meant as "fly".
        constexpr int DefaultKey = VK_LMENU;
        // 30 Hz. A human keypress is hundreds of milliseconds; this resolves the
        // edge to ~33 ms, which is under one server frame at 50 ms.
        constexpr auto PollInterval = std::chrono::milliseconds(33);
        // While the key is held, say so twice a second. The dedicated expires a
        // hold it has not heard about, so this is what makes a LOST key-up
        // recover on its own instead of stranding somebody in the air.
        constexpr auto RepeatInterval = std::chrono::milliseconds(500);
        // Deliberately larger than two repeats and far smaller than a life.
        constexpr std::uint32_t HoldMilliseconds = 1500;
        // Short. This runs on its own thread, but a dedicated that is gone
        // should cost the poller 150 ms, not half a second, per attempt.
        constexpr std::uint32_t SubmitTimeoutMilliseconds = 150;

        std::string environmentValue(const char *const name)
        {
            char *value{};
            std::size_t size{};
            if (_dupenv_s(&value, &size, name) != 0 || !value)
                return {};
            std::string result(value);
            std::free(value);
            return result;
        }

        bool environmentDisables(const char *const name)
        {
            const auto value = environmentValue(name);
            if (value.empty())
                return false;
            const auto first = value[0];
            return first == '0' || first == 'n' || first == 'N' ||
                first == 'f' || first == 'F';
        }

        std::uint64_t parseNumber(
            const std::string &text,
            const int base,
            const std::uint64_t fallback)
        {
            if (text.empty())
                return fallback;
            const auto *begin = text.data();
            const auto *const end = text.data() + text.size();
            if (base == 16 && text.size() > 2 && text[0] == '0' &&
                (text[1] == 'x' || text[1] == 'X'))
            {
                begin += 2;
            }
            std::uint64_t parsed{};
            const auto result = std::from_chars(begin, end, parsed, base);
            if (result.ec != std::errc{} || result.ptr != end)
                return fallback;
            return parsed;
        }

        std::string hexText(const std::uint64_t value)
        {
            char buffer[24]{};
            const auto end = std::to_chars(
                buffer, buffer + sizeof(buffer), value, 16);
            return std::string(buffer, end.ptr);
        }

        // ONLY WHEN THIS PROCESS OWNS THE FOREGROUND WINDOW. GetAsyncKeyState is
        // global, so without this an alt-tabbed client would fly whenever the
        // player pressed alt in another window -- and ALT IS THE ALT-TAB KEY, so
        // that is not a corner case, it is the common one. Losing focus also
        // releases, which is the behaviour a player expects anyway.
        bool foreground()
        {
            const auto window = GetForegroundWindow();
            if (!window)
                return false;
            DWORD processId{};
            GetWindowThreadProcessId(window, &processId);
            return processId == GetCurrentProcessId();
        }

        void send(const std::uint64_t userId, const bool enabled)
        {
            const auto payload =
                OlMod::DedicatedControl::encodeNoclipRequest({
                    .userId = userId,
                    .enabled = enabled,
                    .holdMilliseconds = HoldMilliseconds,
                });
            const auto result = OlMod::DedicatedControl::submit(
                OlMod::DedicatedControl::configuredHostAddress(),
                OlMod::DedicatedControl::configuredPort(),
                {
                    .type = OlMod::DedicatedControl::MessageType::SetNoclip,
                    .payload = payload,
                },
                SubmitTimeoutMilliseconds);
            // SILENT WHEN HEALTHY, and an edge that fails is not healthy. The
            // repeats are not reported at all; only a state CHANGE that did not
            // land, which is the only case a player would notice and ask about.
            if (result.delivered &&
                result.status ==
                    OlMod::DedicatedControl::ResponseStatus::Accepted)
            {
                return;
            }
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer,
                std::string("noclip ") + (enabled ? "on" : "off") +
                    " NOT APPLIED delivered=" +
                    std::to_string(result.delivered ? 1 : 0) + " status=" +
                    std::to_string(static_cast<int>(result.status)) +
                    " socketError=" + std::to_string(result.socketError));
        }

        void pump(const int key, const std::uint64_t userId)
        {
            auto held = false;
            auto nextRepeat = std::chrono::steady_clock::now();
            for (;;)
            {
                std::this_thread::sleep_for(PollInterval);
                const auto down = foreground() &&
                    (GetAsyncKeyState(key) & 0x8000) != 0;
                const auto now = std::chrono::steady_clock::now();
                if (down != held)
                {
                    held = down;
                    nextRepeat = now + RepeatInterval;
                    send(userId, held);
                    continue;
                }
                // EDGE PLUS KEEP-ALIVE, NEVER LEVEL: nothing is sent while the
                // key is up, and twice a second while it is down.
                if (held && now >= nextRepeat)
                {
                    nextRepeat = now + RepeatInterval;
                    send(userId, true);
                }
            }
        }
    }

    // CODREF(client-cg): 613A40 resolves cg; native ps+158 is clientNum.
    // Read only on a debug key edge, not a per-frame hook. Failed reads refuse
    // the grant instead of guessing which of two loopback players owns it.
    static std::optional<std::uint32_t> batteryClientNum()
    {
        const auto base=reinterpret_cast<std::uintptr_t>(GetModuleHandleW(nullptr));
        const auto read=[](std::uintptr_t address,std::uint32_t &out) {
            SIZE_T got{};
            return ReadProcessMemory(GetCurrentProcess(),reinterpret_cast<void*>(address),
                &out,sizeof(out),&got) && got==sizeof(out);
        };
        return resolveBatteryClientNum(base,read);
    }

    void startClientBatteryHotkey()
    {
        // OLMOD(debug_battery): no game hook, one existing-style key poller.
        if(environmentValue("OLMOD_ZM_DEBUG_BATTERY")!="1" ||
            OlMod::DedicatedControl::configuredHostAddress()!="127.0.0.1")return;
        static std::atomic_flag started;
        if(started.test_and_set())return;
        const auto configuredKey=parseNumber(environmentValue("OLMOD_ZM_DEBUG_BATTERY_KEY"),16,VK_F6);
        const auto key=static_cast<int>(configuredKey>=1 && configuredKey<=255 ? configuredKey : VK_F6);
        OlMod::RuntimeLog::write(OlMod::RuntimeLog::Channel::GameServer,
            "DEBUG BATTERY armed key=0x"+hexText(key)+
            " (default F6); apostrophe/Numpad+ aliases; +1 focused Factory battery");
        std::thread([key] {
            const auto downNow=[key] {
                // VK_OEM_7 is the apostrophe key on the testing US layout.
                return ((GetAsyncKeyState(key)|GetAsyncKeyState(VK_ADD)|GetAsyncKeyState(VK_OEM_7))&0x8000)!=0;
            };
            bool held=downNow();
            auto next=std::chrono::steady_clock::now();
            for(;;) {
                std::this_thread::sleep_for(PollInterval);
                const bool down=downNow();
                const bool pressed=down&&!held;held=down;
                const auto now=std::chrono::steady_clock::now();
                // Track physical key-up even while unfocused. Returning to the
                // game with the key already held cannot synthesize another grant.
                if(!pressed || !foreground() || now<next)continue;
                next=now+std::chrono::milliseconds(500);
                const auto client=batteryClientNum();
                if(!client) {
                    OlMod::RuntimeLog::write(OlMod::RuntimeLog::Channel::GameServer,
                        "DEBUG BATTERY local lookup refused: requires a readable living player state");
                    continue;
                }
                const auto result=OlMod::DedicatedControl::submit("127.0.0.1",
                    OlMod::DedicatedControl::configuredPort(),
                    {.type=OlMod::DedicatedControl::MessageType::DebugGrantBattery,
                     .payload=std::to_string(*client)},
                    SubmitTimeoutMilliseconds);
                OlMod::RuntimeLog::write(OlMod::RuntimeLog::Channel::GameServer,
                    result.delivered && result.status==OlMod::DedicatedControl::ResponseStatus::Accepted
                    ? "DEBUG BATTERY grant accepted" : "DEBUG BATTERY grant refused (requires active local Factory player)");
            }
        }).detach();
    }

    void startClientNoclipHotkey()
    {
        static std::atomic_flag started;
        if (started.test_and_set())
            return;
        if (environmentDisables("OLMOD_NOCLIP"))
        {
            OlMod::RuntimeLog::write(
                OlMod::RuntimeLog::Channel::GameServer,
                "noclip hotkey disabled (OLMOD_NOCLIP)");
            return;
        }
        // CODOL MAY ALREADY WANT LEFT ALT. If it fights something, move the key
        // here rather than in code -- OLMOD_NOCLIP_KEY takes a virtual-key code
        // in hex (A4 left alt, 12 either alt, 11 control).
        const auto key = static_cast<int>(parseNumber(
            environmentValue("OLMOD_NOCLIP_KEY"), 16, DefaultKey));
        // ZERO, DELIBERATELY: "resolve me by the address I am sending from".
        // A client CANNOT name itself here. It knows OLMOD_PLATFORM_USER_ID
        // (0x01100001DEADC0DE) and the server knows the xuid out.exe put in its
        // connect string, which is the C# AuthServer's sequentially issued
        // account -- a live match ran with 69420 and 69422 against platform ids
        // ...C0DE and ...C0DF. Sending the platform id would name no slot at
        // all. Only the tool path sends a real xuid.
        constexpr std::uint64_t ResolveBySenderAddress = 0;
        OlMod::RuntimeLog::write(
            OlMod::RuntimeLog::Channel::GameServer,
            "noclip hotkey armed key=0x" +
                hexText(static_cast<std::uint64_t>(key)) + " host=" +
                OlMod::DedicatedControl::configuredHostAddress() + ':' +
                std::to_string(OlMod::DedicatedControl::configuredPort()));
        std::thread(pump, key, ResolveBySenderAddress).detach();
    }
}
