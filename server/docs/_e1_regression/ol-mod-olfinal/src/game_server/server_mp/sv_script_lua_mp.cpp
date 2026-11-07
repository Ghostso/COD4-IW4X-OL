#include "sv_script_lua_mp.hpp"

#include <lua.hpp>

#include <algorithm>
#include <array>
#include <cstddef>
#include <cstdlib>
#include <limits>
#include <map>
#include <optional>
#include <string>
#include <type_traits>
#include <utility>

namespace CodolGameServer
{
    namespace
    {
        constexpr std::string_view ObjectMetatable = "codol.object";
        constexpr std::size_t MaxLogEntries = 256;
        constexpr std::size_t MaxLogMessageLength = 4096;
        constexpr std::size_t MaxTracebackLength = 16384;
        constexpr std::size_t MaxCallbacksPerEvent = 64;
        constexpr std::uint32_t MaxWaitMilliseconds = 24u * 60u * 60u * 1000u;

        struct LuaObjectRef
        {
            std::uint64_t generation{};
            SvScriptObjectKind kind{};
            std::uint32_t id{};
            std::uint32_t entityGeneration{};
            bool hasEntityGeneration{};
        };

        std::string boundedString(
            const std::string_view value,
            const std::size_t maximumLength)
        {
            return std::string(value.substr(0, maximumLength));
        }

        int buildTraceback(lua_State *state)
        {
            const auto *message = lua_tostring(state, 1);
            luaL_traceback(state, state, message, 1);
            return 1;
        }

        std::pair<std::string, std::string> splitTraceback(
            const std::string_view value)
        {
            constexpr std::string_view Marker = "\nstack traceback:";
            const auto marker = value.find(Marker);
            if (marker == std::string_view::npos)
                return { std::string(value), std::string(value) };
            return {
                std::string(value.substr(0, marker)),
                std::string(value),
            };
        }
    }

    struct SvLuaRuntime::Impl
    {
        struct AllocatorState
        {
            std::size_t usedBytes{};
            std::size_t maximumBytes{};
        };

        struct RuntimeBridge
        {
            Impl *runtime{};
            std::uint64_t generation{};
        };

        struct ScheduledThread
        {
            lua_State *thread{};
            int registryReference{ LUA_NOREF };
            std::uint32_t wakeServerTime{};
        };

        explicit Impl(
            const SvScriptBuiltinRegistry &registry,
            SvLuaRuntimeLimits configuredLimits)
            : builtins(registry),
              limits{
                  .maximumMemoryBytes = std::max<std::size_t>(
                      configuredLimits.maximumMemoryBytes, 1),
                  .maximumInstructionsPerRun = std::max<std::uint64_t>(
                      configuredLimits.maximumInstructionsPerRun, 1),
                  .instructionHookInterval = std::max<std::uint32_t>(
                      configuredLimits.instructionHookInterval, 1),
                  .maximumSourceBytes = std::max<std::size_t>(
                      configuredLimits.maximumSourceBytes, 1),
                  .maximumScheduledThreads = std::max<std::size_t>(
                      configuredLimits.maximumScheduledThreads, 1),
                  .maximumThreadResumesPerFrame = std::max<std::size_t>(
                      configuredLimits.maximumThreadResumesPerFrame, 1),
              },
              allocator{ .maximumBytes = limits.maximumMemoryBytes }
        {
        }

        ~Impl()
        {
            closeState();
        }

        void closeState()
        {
            if (state)
                lua_close(state);
            state = nullptr;
            allocator.usedBytes = 0;
            remainingInstructions = 0;
            loaded = false;
            eventCallbacks.clear();
            scheduledThreads.clear();
            currentServerTime = 0;
        }

        static void *allocate(
            void *userData,
            void *pointer,
            const std::size_t oldSize,
            const std::size_t newSize)
        {
            auto &allocator = *static_cast<AllocatorState *>(userData);
            const auto accountedOldSize = pointer ? oldSize : 0;
            if (!newSize)
            {
                std::free(pointer);
                allocator.usedBytes -= std::min(
                    allocator.usedBytes, accountedOldSize);
                return nullptr;
            }

            if (newSize > accountedOldSize &&
                newSize - accountedOldSize >
                    allocator.maximumBytes -
                        std::min(allocator.maximumBytes, allocator.usedBytes))
            {
                return nullptr;
            }
            auto *resized = std::realloc(pointer, newSize);
            if (!resized)
                return nullptr;
            allocator.usedBytes = allocator.usedBytes -
                std::min(allocator.usedBytes, accountedOldSize) + newSize;
            return resized;
        }

        static void instructionHook(lua_State *luaState, lua_Debug *)
        {
            const auto runtime = *static_cast<Impl **>(lua_getextraspace(luaState));
            if (!runtime)
            {
                static_cast<void>(luaL_error(
                    luaState, "Lua runtime instruction hook lost its owner"));
                return;
            }
            const auto interval = runtime->limits.instructionHookInterval;
            if (runtime->remainingInstructions <= interval)
            {
                runtime->remainingInstructions = 0;
                static_cast<void>(luaL_error(
                    luaState, "Lua instruction budget exceeded"));
                return;
            }
            runtime->remainingInstructions -= interval;
        }

        void appendLog(
            const SvLuaLogLevel level,
            const SvLuaLogKind kind,
            const std::string_view message,
            const std::string_view traceback = {})
        {
            if (logs.size() == MaxLogEntries)
                logs.erase(logs.begin());
            logs.push_back({
                .level = level,
                .kind = kind,
                .generation = generation,
                .sourceName = sourceName,
                .message = boundedString(message, MaxLogMessageLength),
                .traceback = boundedString(traceback, MaxTracebackLength),
            });
        }

        static Impl *runtimeFromUpvalue(lua_State *luaState)
        {
            const auto *bridge = static_cast<const RuntimeBridge *>(
                lua_touserdata(luaState, lua_upvalueindex(1)));
            const auto *stateRuntime =
                *static_cast<Impl **>(lua_getextraspace(luaState));
            if (!bridge || !bridge->runtime || stateRuntime != bridge->runtime ||
                bridge->generation != bridge->runtime->generation ||
                !bridge->runtime->state)
            {
                return nullptr;
            }
            return bridge->runtime;
        }

        void pushBridgeClosure(lua_CFunction callback)
        {
            auto *bridge = static_cast<RuntimeBridge *>(
                lua_newuserdatauv(state, sizeof(RuntimeBridge), 0));
            *bridge = {
                .runtime = this,
                .generation = generation,
            };
            lua_pushcclosure(state, callback, 1);
        }

        static int pushFailure(lua_State *luaState, const std::string_view message)
        {
            lua_pushnil(luaState);
            lua_pushlstring(luaState, message.data(), message.size());
            return 2;
        }

        static std::optional<SvScriptObjectRef> readObject(
            lua_State *luaState,
            const int index,
            const std::uint64_t generation)
        {
            const auto *object = static_cast<const LuaObjectRef *>(
                luaL_testudata(luaState, index, ObjectMetatable.data()));
            if (!object || object->generation != generation)
                return std::nullopt;
            return SvScriptObjectRef{
                .kind = object->kind,
                .id = object->id,
                .entityGeneration = object->hasEntityGeneration
                    ? std::optional{ object->entityGeneration }
                    : std::nullopt,
            };
        }

        static std::optional<SvScriptValue> readValue(
            lua_State *luaState,
            const int index,
            const std::uint64_t generation)
        {
            switch (lua_type(luaState, index))
            {
            case LUA_TNIL:
                return std::monostate{};
            case LUA_TBOOLEAN:
                return lua_toboolean(luaState, index) != 0;
            case LUA_TNUMBER:
                if (lua_isinteger(luaState, index))
                    return static_cast<std::int64_t>(lua_tointeger(luaState, index));
                return static_cast<double>(lua_tonumber(luaState, index));
            case LUA_TSTRING:
            {
                std::size_t length{};
                const auto *value = lua_tolstring(luaState, index, &length);
                return std::string(value, length);
            }
            case LUA_TUSERDATA:
                if (const auto object = readObject(luaState, index, generation))
                    return *object;
                return std::nullopt;
            case LUA_TTABLE:
            {
                SvScriptVector vector{};
                if (lua_rawlen(luaState, index) != vector.size())
                    return std::nullopt;
                for (std::size_t component = 0; component < vector.size(); ++component)
                {
                    lua_rawgeti(
                        luaState,
                        index,
                        static_cast<lua_Integer>(component + 1));
                    if (lua_type(luaState, -1) != LUA_TNUMBER)
                    {
                        lua_pop(luaState, 1);
                        return std::nullopt;
                    }
                    vector[component] = static_cast<float>(
                        lua_tonumber(luaState, -1));
                    lua_pop(luaState, 1);
                }
                return vector;
            }
            default:
                return std::nullopt;
            }
        }

        static int pushObject(
            lua_State *luaState,
            const std::uint64_t generation,
            const SvScriptObjectRef object)
        {
            auto *value = static_cast<LuaObjectRef *>(
                lua_newuserdatauv(luaState, sizeof(LuaObjectRef), 0));
            *value = {
                .generation = generation,
                .kind = object.kind,
                .id = object.id,
                .entityGeneration = object.entityGeneration.value_or(0),
                .hasEntityGeneration = object.entityGeneration.has_value(),
            };
            luaL_setmetatable(luaState, ObjectMetatable.data());
            return 1;
        }

        static int pushValue(
            lua_State *luaState,
            const std::uint64_t generation,
            const SvScriptValue &value)
        {
            return std::visit([luaState, generation](const auto &result) -> int {
                using Result = std::decay_t<decltype(result)>;
                if constexpr (std::is_same_v<Result, std::monostate>)
                {
                    lua_pushnil(luaState);
                }
                else if constexpr (std::is_same_v<Result, bool>)
                {
                    lua_pushboolean(luaState, result ? 1 : 0);
                }
                else if constexpr (std::is_same_v<Result, std::int64_t>)
                {
                    lua_pushinteger(luaState, static_cast<lua_Integer>(result));
                }
                else if constexpr (std::is_same_v<Result, double>)
                {
                    lua_pushnumber(luaState, static_cast<lua_Number>(result));
                }
                else if constexpr (std::is_same_v<Result, std::string>)
                {
                    lua_pushlstring(luaState, result.data(), result.size());
                }
                else if constexpr (std::is_same_v<Result, SvScriptVector>)
                {
                    lua_createtable(luaState, 3, 0);
                    for (std::size_t index = 0; index < result.size(); ++index)
                    {
                        lua_pushnumber(luaState, result[index]);
                        lua_rawseti(luaState, -2, static_cast<lua_Integer>(index + 1));
                    }
                }
                else if constexpr (std::is_same_v<Result, SvScriptObjectRef>)
                {
                    return pushObject(luaState, generation, result);
                }
                else if constexpr (std::is_same_v<Result, SvScriptObjectArray>)
                {
                    lua_createtable(
                        luaState, static_cast<int>(result.size()), 0);
                    for (std::size_t index = 0; index < result.size(); ++index)
                    {
                        pushObject(luaState, generation, result[index]);
                        lua_rawseti(
                            luaState, -2,
                            static_cast<lua_Integer>(index + 1));
                    }
                }
                return 1;
            }, value);
        }

        static int createObject(lua_State *luaState, const SvScriptObjectKind kind)
        {
            const auto *runtime = runtimeFromUpvalue(luaState);
            if (!runtime)
                return pushFailure(luaState, "script runtime generation is stale");
            if (!lua_isinteger(luaState, 1))
                return pushFailure(luaState, "object id must be an integer");
            const auto id = lua_tointeger(luaState, 1);
            if (id < 0 || static_cast<lua_Unsigned>(id) >
                std::numeric_limits<std::uint32_t>::max())
            {
                return pushFailure(luaState, "object id is outside uint32 range");
            }
            return pushObject(luaState, runtime->generation, {
                .kind = kind,
                .id = static_cast<std::uint32_t>(id),
            });
        }

        static int createPlayer(lua_State *luaState)
        {
            return createObject(luaState, SvScriptObjectKind::Player);
        }

        static int createEntity(lua_State *luaState)
        {
            return createObject(luaState, SvScriptObjectKind::Entity);
        }

        static int objectToString(lua_State *luaState)
        {
            lua_pushliteral(luaState, "codol object");
            return 1;
        }

        static int callBuiltin(lua_State *luaState)
        {
            const auto *runtime = runtimeFromUpvalue(luaState);
            if (!runtime)
                return pushFailure(luaState, "script runtime generation is stale");
            if (lua_type(luaState, 1) != LUA_TSTRING)
                return pushFailure(luaState, "builtin key must be a string");
            std::size_t keyLength{};
            const auto *keyData = lua_tolstring(luaState, 1, &keyLength);
            const std::string_view key(keyData, keyLength);
            const auto separator = key.find(':');
            if (separator == std::string_view::npos || separator == 0 ||
                separator + 1 == key.size() || key.find(':', separator + 1) !=
                    std::string_view::npos)
            {
                return pushFailure(luaState, "builtin key must use kind:name syntax");
            }

            SvScriptBuiltinKind kind{};
            const auto kindName = key.substr(0, separator);
            if (kindName == "function")
                kind = SvScriptBuiltinKind::Function;
            else if (kindName == "method")
                kind = SvScriptBuiltinKind::Method;
            else
                return pushFailure(luaState, "builtin kind must be function or method");

            std::optional<SvScriptObjectRef> self;
            int firstArgument = 2;
            if (kind == SvScriptBuiltinKind::Method)
            {
                self = readObject(luaState, 2, runtime->generation);
                if (!self)
                    return pushFailure(luaState, "method receiver must be a current object");
                firstArgument = 3;
            }

            std::vector<SvScriptValue> arguments;
            const auto argumentCount = lua_gettop(luaState) - firstArgument + 1;
            if (argumentCount > 0)
                arguments.reserve(static_cast<std::size_t>(argumentCount));
            for (auto index = firstArgument; index <= lua_gettop(luaState); ++index)
            {
                auto value = readValue(luaState, index, runtime->generation);
                if (!value)
                    return pushFailure(luaState, "builtin argument has an unsupported type");
                arguments.push_back(std::move(*value));
            }

            const auto result = runtime->builtins.invoke(
                kind, key.substr(separator + 1), self, arguments);
            if (!result.succeeded())
            {
                lua_pushnil(luaState);
                lua_pushlstring(
                    luaState, result.error.message.data(), result.error.message.size());
                lua_pushinteger(
                    luaState, static_cast<lua_Integer>(result.error.code));
                return 3;
            }
            return pushValue(luaState, runtime->generation, result.value);
        }

        static std::optional<SvWorldEventType> parseEventType(
            const std::string_view name)
        {
            if (name == "client_spawned")
                return SvWorldEventType::ClientSpawned;
            if (name == "client_disconnected")
                return SvWorldEventType::ClientDisconnected;
            if (name == "weapon_switch_started")
                return SvWorldEventType::WeaponSwitchStarted;
            if (name == "weapon_change")
                return SvWorldEventType::WeaponChanged;
            if (name == "player_damage")
                return SvWorldEventType::PlayerDamage;
            if (name == "entity_touch")
                return SvWorldEventType::EntityTouch;
            if (name == "player_killed")
                return SvWorldEventType::PlayerKilled;
            if (name == "entity_damage")
                return SvWorldEventType::EntityDamage;
            if (name == "entity_killed")
                return SvWorldEventType::EntityKilled;
            if (name == "sd_bomb_picked_up")
                return SvWorldEventType::SdBombPickedUp;
            if (name == "sd_bomb_dropped")
                return SvWorldEventType::SdBombDropped;
            if (name == "sd_plant_started")
                return SvWorldEventType::SdPlantStarted;
            if (name == "sd_plant_cancelled")
                return SvWorldEventType::SdPlantCancelled;
            if (name == "sd_bomb_planted")
                return SvWorldEventType::SdBombPlanted;
            if (name == "sd_defuse_started")
                return SvWorldEventType::SdDefuseStarted;
            if (name == "sd_defuse_cancelled")
                return SvWorldEventType::SdDefuseCancelled;
            if (name == "sd_bomb_defused")
                return SvWorldEventType::SdBombDefused;
            if (name == "sd_bomb_exploded")
                return SvWorldEventType::SdBombExploded;
            if (name == "sd_round_ended")
                return SvWorldEventType::SdRoundEnded;
            if (name == "zm_round_tick")
                return SvWorldEventType::ZmRoundTick;
            return std::nullopt;
        }

        static int registerEventCallback(lua_State *luaState)
        {
            auto *runtime = runtimeFromUpvalue(luaState);
            if (!runtime)
                return pushFailure(luaState, "script runtime generation is stale");
            if (lua_type(luaState, 1) != LUA_TSTRING ||
                !lua_isfunction(luaState, 2))
            {
                return pushFailure(
                    luaState, "codol.on expects an event name and function");
            }
            std::size_t nameLength{};
            const auto *nameData = lua_tolstring(luaState, 1, &nameLength);
            const auto eventType = parseEventType(
                std::string_view(nameData, nameLength));
            if (!eventType)
                return pushFailure(luaState, "unsupported CODOL world event");
            auto &callbacks = runtime->eventCallbacks[*eventType];
            if (callbacks.size() >= MaxCallbacksPerEvent)
                return pushFailure(luaState, "world event callback limit exceeded");
            lua_pushvalue(luaState, 2);
            callbacks.push_back(luaL_ref(luaState, LUA_REGISTRYINDEX));
            lua_pushboolean(luaState, 1);
            return 1;
        }

        static int print(lua_State *luaState)
        {
            auto *runtime = runtimeFromUpvalue(luaState);
            if (!runtime)
                return 0;
            const auto top = lua_gettop(luaState);
            std::string message;
            for (int index = 1; index <= top; ++index)
            {
                if (index != 1)
                    message.push_back('\t');
                switch (lua_type(luaState, index))
                {
                case LUA_TNIL:
                    message.append("nil");
                    break;
                case LUA_TBOOLEAN:
                    message.append(lua_toboolean(luaState, index) ? "true" : "false");
                    break;
                case LUA_TNUMBER:
                case LUA_TSTRING:
                {
                    std::size_t length{};
                    const auto *value = lua_tolstring(luaState, index, &length);
                    message.append(value, length);
                    break;
                }
                default:
                    message.append(lua_typename(luaState, lua_type(luaState, index)));
                    break;
                }
            }
            runtime->appendLog(SvLuaLogLevel::Info, SvLuaLogKind::Print, message);
            return 0;
        }

        static int wait(lua_State *luaState)
        {
            auto *runtime = runtimeFromUpvalue(luaState);
            if (!runtime)
                return luaL_error(luaState, "script runtime generation is stale");
            if (!lua_isyieldable(luaState))
                return luaL_error(luaState, "codol.wait requires a managed script thread");
            if (lua_gettop(luaState) != 1 || !lua_isinteger(luaState, 1))
                return luaL_error(luaState, "codol.wait expects integer milliseconds");
            const auto milliseconds = lua_tointeger(luaState, 1);
            if (milliseconds < 0 ||
                static_cast<lua_Unsigned>(milliseconds) > MaxWaitMilliseconds)
            {
                return luaL_error(
                    luaState, "codol.wait milliseconds are outside 0..86400000");
            }
            lua_pushinteger(luaState, milliseconds);
            return lua_yield(luaState, 1);
        }

        void configureManagedThread(lua_State *thread)
        {
            *static_cast<Impl **>(lua_getextraspace(thread)) = this;
            lua_sethook(
                thread,
                instructionHook,
                LUA_MASKCOUNT,
                static_cast<int>(std::min<std::uint32_t>(
                    limits.instructionHookInterval,
                    static_cast<std::uint32_t>(
                        std::numeric_limits<int>::max()))));
        }

        void appendThreadError(lua_State *thread, const std::string_view fallback)
        {
            const auto *error = lua_tostring(thread, -1);
            const auto message = std::string(error ? std::string_view(error) : fallback);
            luaL_traceback(state, thread, message.c_str(), 1);
            const auto *trace = lua_tostring(state, -1);
            const auto [summary, traceback] = splitTraceback(
                trace ? std::string_view(trace) : std::string_view(message));
            appendLog(
                SvLuaLogLevel::Error,
                SvLuaLogKind::RuntimeError,
                summary,
                traceback);
            lua_pop(state, 1);
        }

        bool resumeManagedThread(
            lua_State *thread,
            const int registryReference,
            const int argumentCount,
            lua_State *resumer)
        {
            const auto callerInstructionBudget = remainingInstructions;
            remainingInstructions = limits.maximumInstructionsPerRun;
            int resultCount{};
            const auto result = lua_resume(
                thread, resumer, argumentCount, &resultCount);
            remainingInstructions = callerInstructionBudget;
            if (result == LUA_OK)
            {
                lua_settop(thread, 0);
                luaL_unref(state, LUA_REGISTRYINDEX, registryReference);
                return true;
            }
            if (result != LUA_YIELD)
            {
                appendThreadError(thread, "unknown Lua thread error");
                lua_settop(thread, 0);
                luaL_unref(state, LUA_REGISTRYINDEX, registryReference);
                return false;
            }
            if (resultCount != 1 || !lua_isinteger(thread, -1))
            {
                appendLog(
                    SvLuaLogLevel::Error,
                    SvLuaLogKind::RuntimeError,
                    "managed Lua thread yielded without codol.wait");
                lua_settop(thread, 0);
                luaL_unref(state, LUA_REGISTRYINDEX, registryReference);
                return false;
            }
            const auto delay = lua_tointeger(thread, -1);
            if (delay < 0 || static_cast<lua_Unsigned>(delay) >
                    MaxWaitMilliseconds ||
                scheduledThreads.size() >= limits.maximumScheduledThreads)
            {
                appendLog(
                    SvLuaLogLevel::Error,
                    SvLuaLogKind::RuntimeError,
                    scheduledThreads.size() >= limits.maximumScheduledThreads
                        ? "managed Lua thread limit exceeded"
                        : "managed Lua thread yielded an invalid wait");
                lua_settop(thread, 0);
                luaL_unref(state, LUA_REGISTRYINDEX, registryReference);
                return false;
            }
            lua_settop(thread, 0);
            scheduledThreads.push_back({
                .thread = thread,
                .registryReference = registryReference,
                .wakeServerTime = currentServerTime +
                    static_cast<std::uint32_t>(delay),
            });
            return true;
        }

        bool startManagedThread(
            const int argumentCount,
            lua_State *resumer)
        {
            auto *thread = lua_newthread(state);
            const auto registryReference =
                luaL_ref(state, LUA_REGISTRYINDEX);
            configureManagedThread(thread);
            lua_xmove(state, thread, argumentCount + 1);
            return resumeManagedThread(
                thread, registryReference, argumentCount, resumer);
        }

        static int spawnThread(lua_State *luaState)
        {
            auto *runtime = runtimeFromUpvalue(luaState);
            if (!runtime)
                return pushFailure(luaState, "script runtime generation is stale");
            if (lua_gettop(luaState) != 1 || !lua_isfunction(luaState, 1))
                return pushFailure(luaState, "codol.thread expects one function");
            lua_pushvalue(luaState, 1);
            if (luaState != runtime->state)
                lua_xmove(luaState, runtime->state, 1);
            if (!runtime->startManagedThread(0, luaState))
                return pushFailure(luaState, "managed script thread failed");
            lua_pushboolean(luaState, 1);
            return 1;
        }

        bool advance(const std::uint32_t serverTime)
        {
            currentServerTime = serverTime;
            if (!state || !loaded || scheduledThreads.empty())
                return true;
            std::vector<ScheduledThread> due;
            std::vector<ScheduledThread> remaining;
            due.reserve(std::min(
                scheduledThreads.size(), limits.maximumThreadResumesPerFrame));
            remaining.reserve(scheduledThreads.size());
            for (const auto &thread : scheduledThreads)
            {
                const auto reached = static_cast<std::int32_t>(
                    serverTime - thread.wakeServerTime) >= 0;
                if (reached && due.size() < limits.maximumThreadResumesPerFrame)
                    due.push_back(thread);
                else
                    remaining.push_back(thread);
            }
            scheduledThreads = std::move(remaining);
            bool succeeded = true;
            for (const auto &thread : due)
            {
                if (!resumeManagedThread(
                        thread.thread, thread.registryReference, 0, state))
                {
                    succeeded = false;
                }
            }
            lua_settop(state, 0);
            return succeeded;
        }

        void removeGlobal(const char *name)
        {
            lua_pushnil(state);
            lua_setglobal(state, name);
        }

        void removeLibraryField(const char *library, const char *field)
        {
            lua_getglobal(state, library);
            if (lua_istable(state, -1))
            {
                lua_pushnil(state);
                lua_setfield(state, -2, field);
            }
            lua_pop(state, 1);
        }

        void openRestrictedLibraries()
        {
            const std::array libraries{
                std::pair{ "_G", luaopen_base },
                std::pair{ LUA_TABLIBNAME, luaopen_table },
                std::pair{ LUA_STRLIBNAME, luaopen_string },
                std::pair{ LUA_MATHLIBNAME, luaopen_math },
                std::pair{ LUA_UTF8LIBNAME, luaopen_utf8 },
            };
            for (const auto &[name, open] : libraries)
            {
                luaL_requiref(state, name, open, 1);
                lua_pop(state, 1);
            }

            removeGlobal("dofile");
            removeGlobal("load");
            removeGlobal("loadfile");
            removeGlobal("collectgarbage");
            removeGlobal("warn");
            removeLibraryField(LUA_STRLIBNAME, "dump");
            removeLibraryField(LUA_MATHLIBNAME, "random");
            removeLibraryField(LUA_MATHLIBNAME, "randomseed");
        }

        void registerApi()
        {
            if (luaL_newmetatable(state, ObjectMetatable.data()))
            {
                lua_pushliteral(state, "codol object");
                lua_setfield(state, -2, "__metatable");
                lua_pushcfunction(state, objectToString);
                lua_setfield(state, -2, "__tostring");
            }
            lua_pop(state, 1);

            pushBridgeClosure(print);
            lua_setglobal(state, "print");

            lua_createtable(state, 0, 6);
            pushBridgeClosure(createPlayer);
            lua_setfield(state, -2, "player");
            pushBridgeClosure(createEntity);
            lua_setfield(state, -2, "entity");
            pushBridgeClosure(callBuiltin);
            lua_setfield(state, -2, "call");
            pushBridgeClosure(registerEventCallback);
            lua_setfield(state, -2, "on");
            pushBridgeClosure(wait);
            lua_setfield(state, -2, "wait");
            pushBridgeClosure(spawnThread);
            lua_setfield(state, -2, "thread");
            lua_setglobal(state, "codol");
        }

        bool dispatchWorldEvents(const std::span<const SvWorldEvent> events)
        {
            if (!state || !loaded || events.empty())
                return true;
            // OLMOD(lua-world-event-validation): native Scr_Notify carries a
            // typed VM stack owned by the engine. The temporary Lua bridge must
            // validate every source variant before constructing an equivalent
            // table so a mismatched optional payload cannot cross the host ABI.
            bool succeeded = true;
            for (const auto &event : events)
            {
                currentServerTime = event.serverTime;
                if (event.type == SvWorldEventType::EntityTouch)
                {
                    appendLog(
                        SvLuaLogLevel::Error,
                        SvLuaLogKind::HostError,
                        "entity touch requires the dedicated notification ABI");
                    succeeded = false;
                    continue;
                }
                if (event.type == SvWorldEventType::PlayerDamage &&
                    (!event.playerDamage ||
                        event.playerDamage->targetClientNum != event.clientNum ||
                        event.playerDamage->weaponAssetIndex !=
                            event.weaponAssetIndex))
                {
                    appendLog(
                        SvLuaLogLevel::Error,
                        SvLuaLogKind::HostError,
                        "invalid PlayerDamage world event payload");
                    succeeded = false;
                    continue;
                }
                if (event.type == SvWorldEventType::PlayerKilled &&
                    (!event.playerKilled ||
                        event.playerKilled->damage.targetClientNum !=
                            event.clientNum ||
                        event.playerKilled->damage.weaponAssetIndex !=
                            event.weaponAssetIndex))
                {
                    appendLog(
                        SvLuaLogLevel::Error,
                        SvLuaLogKind::HostError,
                        "invalid PlayerKilled world event payload");
                    succeeded = false;
                    continue;
                }
                const auto entityDamageEvent =
                    event.type == SvWorldEventType::EntityDamage ||
                    event.type == SvWorldEventType::EntityKilled;
                if (entityDamageEvent &&
                    (!event.entityDamage ||
                        event.entityDamage->damage.targetEntityNum !=
                            event.clientNum ||
                        event.entityDamage->damage.weaponAssetIndex !=
                            event.weaponAssetIndex ||
                        (event.type == SvWorldEventType::EntityDamage &&
                            event.entityDamage->remainingHealth <= 0) ||
                        (event.type == SvWorldEventType::EntityKilled &&
                            event.entityDamage->remainingHealth > 0)))
                {
                    appendLog(
                        SvLuaLogLevel::Error,
                        SvLuaLogKind::HostError,
                        "invalid EntityDamage world event payload");
                    succeeded = false;
                    continue;
                }
                const auto found = eventCallbacks.find(event.type);
                if (event.type == SvWorldEventType::ZmRoundTick &&
                    event.serverTime <= 1000u)
                {
                    appendLog(
                        SvLuaLogLevel::Info,
                        SvLuaLogKind::Print,
                        "ZMTICK Lua callbacks=" + std::to_string(
                            found == eventCallbacks.end()
                                ? 0u
                                : found->second.size()));
                }
                if (found == eventCallbacks.end())
                    continue;
                // CODDIFF(g_damage): BO1/Ghosts enter CodeCallback_PlayerDamage
                // synchronously and let script call finishPlayerDamage on the
                // same native stack. ol-mod preserves that call order in
                // ServerCore but adapts the arguments through this typed Lua
                // table until the COD script VM/notify owner is restored.
                const auto callbacks = found->second;
                for (const auto callback : callbacks)
                {
                    lua_settop(state, 0);
                    lua_rawgeti(state, LUA_REGISTRYINDEX, callback);
                    if (event.sd && !event.sd->actorClientNum)
                        lua_pushnil(state);
                    else
                        pushObject(state, generation, {
                            .kind = entityDamageEvent
                                ? SvScriptObjectKind::Entity
                                : SvScriptObjectKind::Player,
                            .id = event.clientNum,
                            .entityGeneration = entityDamageEvent
                                ? std::optional{
                                      event.entityDamage->damage.targetGeneration }
                                : std::nullopt,
                        });
                    const auto *damage = event.playerDamage
                        ? &*event.playerDamage
                        : event.playerKilled
                            ? &event.playerKilled->damage
                            : nullptr;
                    const auto *entityDamage = event.entityDamage
                        ? &event.entityDamage->damage
                        : nullptr;
                    lua_createtable(
                        state, 0, damage
                            ? (event.playerKilled ? 20 : 19)
                            : entityDamage ? 20 : 7);
                    lua_pushinteger(state, event.sequence);
                    lua_setfield(state, -2, "sequence");
                    lua_pushinteger(state, event.serverTime);
                    lua_setfield(state, -2, "server_time");
                    lua_pushinteger(state, event.clientNum);
                    lua_setfield(state, -2, "client_num");
                    lua_pushinteger(state, event.spawnSequence);
                    lua_setfield(state, -2, "spawn_sequence");
                    lua_pushinteger(state, event.spawnGeneration);
                    lua_setfield(state, -2, "spawn_generation");
                    lua_pushinteger(state, event.weaponAssetIndex);
                    lua_setfield(state, -2, "weapon_asset_index");
                    lua_pushlstring(
                        state, event.weaponName.data(), event.weaponName.size());
                    lua_setfield(state, -2, "weapon_name");
                    if (event.sd)
                    {
                        const auto &sd = *event.sd;
                        if (sd.actorClientNum)
                            lua_pushinteger(state, *sd.actorClientNum);
                        else
                            lua_pushnil(state);
                        lua_setfield(state, -2, "actor_client_num");
                        if (sd.objectId)
                            lua_pushinteger(state, *sd.objectId);
                        else
                            lua_pushnil(state);
                        lua_setfield(state, -2, "object_id");
                        if (sd.siteLabel)
                            lua_pushlstring(state, sd.siteLabel->data(), sd.siteLabel->size());
                        else
                            lua_pushnil(state);
                        lua_setfield(state, -2, "site_label");
                        if (sd.origin)
                        {
                            lua_createtable(state, 3, 0);
                            for (std::size_t index{}; index < sd.origin->size(); ++index)
                            {
                                lua_pushnumber(state, (*sd.origin)[index]);
                                lua_rawseti(state, -2, static_cast<lua_Integer>(index + 1));
                            }
                        }
                        else
                            lua_pushnil(state);
                        lua_setfield(state, -2, "origin");
                        if (sd.winner)
                            lua_pushinteger(state, static_cast<lua_Integer>(*sd.winner));
                        else
                            lua_pushnil(state);
                        lua_setfield(state, -2, "winner");
                        lua_pushinteger(state, sd.reason);
                        lua_setfield(state, -2, "reason");
                        lua_pushinteger(state, sd.elapsedMilliseconds);
                        lua_setfield(state, -2, "elapsed_milliseconds");
                    }
                    if (damage)
                    {
                        const auto pushEntityReference = [this](
                                                             const char *name,
                                                             const std::optional<std::uint32_t> value) {
                            if (value)
                                lua_pushinteger(state, *value);
                            else
                                lua_pushnil(state);
                            lua_setfield(state, -2, name);
                        };
                        const auto pushOptionalVector = [this](
                                                          const char *name,
                                                          const std::optional<std::array<float, 3>> &value) {
                            if (!value)
                            {
                                lua_pushnil(state);
                                lua_setfield(state, -2, name);
                                return;
                            }
                            lua_createtable(state, 3, 0);
                            for (std::size_t index = 0; index < value->size(); ++index)
                            {
                                lua_pushnumber(state, (*value)[index]);
                                lua_rawseti(state, -2, static_cast<lua_Integer>(index + 1));
                            }
                            lua_setfield(state, -2, name);
                        };
                        lua_pushinteger(state, damage->targetClientNum);
                        lua_setfield(state, -2, "target_client_num");
                        pushEntityReference(
                            "inflictor_entity_num", damage->inflictorEntityNum);
                        pushEntityReference(
                            "attacker_entity_num", damage->attackerEntityNum);
                        lua_pushinteger(state, damage->damage);
                        lua_setfield(state, -2, "damage");
                        lua_pushinteger(state, damage->damageFlags);
                        lua_setfield(state, -2, "damage_flags");
                        lua_pushinteger(state, damage->methodOfDeath);
                        lua_setfield(state, -2, "method_of_death");
                        lua_pushinteger(state, damage->hitLocation);
                        lua_setfield(state, -2, "hit_location");
                        lua_pushinteger(state, damage->timeOffset);
                        lua_setfield(state, -2, "time_offset");
                        lua_pushinteger(state, damage->boneIndex);
                        lua_setfield(state, -2, "bone_index");
                        pushOptionalVector("point", damage->point);
                        pushOptionalVector("direction", damage->direction);
                        if (event.playerKilled)
                        {
                            lua_pushinteger(
                                state,
                                event.playerKilled->deathAnimationDuration);
                            lua_setfield(
                                state, -2, "death_animation_duration");
                        }
                    }
                    if (entityDamage)
                    {
                        const auto pushOptionalEntity = [this](
                                                            const char *name,
                                                            const std::optional<std::uint32_t> value) {
                            if (value)
                                lua_pushinteger(state, *value);
                            else
                                lua_pushnil(state);
                            lua_setfield(state, -2, name);
                        };
                        const auto pushOptionalVector = [this](
                                                          const char *name,
                                                          const std::optional<std::array<float, 3>> &value) {
                            if (!value)
                            {
                                lua_pushnil(state);
                                lua_setfield(state, -2, name);
                                return;
                            }
                            lua_createtable(state, 3, 0);
                            for (std::size_t index = 0; index < value->size(); ++index)
                            {
                                lua_pushnumber(state, (*value)[index]);
                                lua_rawseti(state, -2, static_cast<lua_Integer>(index + 1));
                            }
                            lua_setfield(state, -2, name);
                        };
                        lua_pushinteger(state, entityDamage->targetEntityNum);
                        lua_setfield(state, -2, "target_entity_num");
                        lua_pushinteger(state, entityDamage->targetGeneration);
                        lua_setfield(state, -2, "target_generation");
                        pushOptionalEntity(
                            "inflictor_entity_num", entityDamage->inflictorEntityNum);
                        pushOptionalEntity(
                            "attacker_entity_num", entityDamage->attackerEntityNum);
                        lua_pushinteger(state, entityDamage->damage);
                        lua_setfield(state, -2, "damage");
                        lua_pushinteger(state, entityDamage->damageFlags);
                        lua_setfield(state, -2, "damage_flags");
                        lua_pushinteger(state, entityDamage->methodOfDeath);
                        lua_setfield(state, -2, "method_of_death");
                        lua_pushinteger(state, entityDamage->hitLocation);
                        lua_setfield(state, -2, "hit_location");
                        lua_pushinteger(state, entityDamage->timeOffset);
                        lua_setfield(state, -2, "time_offset");
                        lua_pushinteger(state, entityDamage->boneIndex);
                        lua_setfield(state, -2, "bone_index");
                        lua_pushinteger(state, event.entityDamage->remainingHealth);
                        lua_setfield(state, -2, "remaining_health");
                        pushOptionalVector("point", entityDamage->point);
                        pushOptionalVector("direction", entityDamage->direction);
                    }
                    // OLMOD(lua-callback-error-boundary): callbacks are
                    // exactly-once notifications. A failed callback is logged
                    // and later callbacks continue; replay would duplicate any
                    // builtin mutation completed before the Lua error.
                    if (!startManagedThread(2, state))
                        succeeded = false;
                }
            }
            lua_settop(state, 0);
            return succeeded;
        }

        bool dispatchTouchNotifications(
            const SvClientImpactScriptNotificationBatch &notifications)
        {
            if (!state || !loaded || !notifications.notificationCount)
                return true;
            if (notifications.notificationCount >
                    notifications.notifications.size() ||
                notifications.notificationCount % 2 != 0)
            {
                appendLog(
                    SvLuaLogLevel::Error,
                    SvLuaLogKind::HostError,
                    "invalid entity-touch notification batch");
                return false;
            }
            for (std::uint32_t index = 0;
                 index < notifications.notificationCount;
                 index += 2)
            {
                const auto &source = notifications.notifications[index];
                const auto &target = notifications.notifications[index + 1];
                if (source.receiverEntityNum > MaximumServerCollisionEntityNum ||
                    source.otherEntityNum > MaximumServerCollisionEntityNum ||
                    source.receiverEntityNum == source.otherEntityNum ||
                    target.receiverEntityNum != source.otherEntityNum ||
                    target.otherEntityNum != source.receiverEntityNum)
                {
                    appendLog(
                        SvLuaLogLevel::Error,
                        SvLuaLogKind::HostError,
                        "invalid entity-touch notification batch");
                    return false;
                }
            }
            const auto found = eventCallbacks.find(SvWorldEventType::EntityTouch);
            if (found == eventCallbacks.end())
                return true;
            bool succeeded = true;
            const auto callbacks = found->second;
            for (std::uint32_t index = 0;
                 index < notifications.notificationCount;
                 ++index)
            {
                const auto &notification = notifications.notifications[index];
                const auto objectKind = [](const std::uint32_t entityNum) {
                    return entityNum < MaximumGameClients
                        ? SvScriptObjectKind::Player
                        : SvScriptObjectKind::Entity;
                };
                for (const auto callback : callbacks)
                {
                    lua_settop(state, 0);
                    lua_rawgeti(state, LUA_REGISTRYINDEX, callback);
                    pushObject(state, generation, {
                        .kind = objectKind(notification.receiverEntityNum),
                        .id = notification.receiverEntityNum,
                    });
                    pushObject(state, generation, {
                        .kind = objectKind(notification.otherEntityNum),
                        .id = notification.otherEntityNum,
                    });
                    lua_createtable(state, 0, 2);
                    lua_pushinteger(state, notification.receiverEntityNum);
                    lua_setfield(state, -2, "receiver_entity_num");
                    lua_pushinteger(state, notification.otherEntityNum);
                    lua_setfield(state, -2, "other_entity_num");
                    if (!startManagedThread(3, state))
                        succeeded = false;
                }
            }
            lua_settop(state, 0);
            return succeeded;
        }

        bool reload(const std::string_view newSourceName, const std::string_view source)
        {
            closeState();
            ++generation;
            sourceName = boundedString(newSourceName, 1024);
            if (sourceName.empty())
            {
                appendLog(
                    SvLuaLogLevel::Error,
                    SvLuaLogKind::HostError,
                    "script source name must not be empty");
                return false;
            }
            if (source.size() > limits.maximumSourceBytes)
            {
                appendLog(
                    SvLuaLogLevel::Error,
                    SvLuaLogKind::HostError,
                    "script source exceeds the configured byte limit");
                return false;
            }

            state = lua_newstate(allocate, &allocator);
            if (!state)
            {
                appendLog(
                    SvLuaLogLevel::Error,
                    SvLuaLogKind::HostError,
                    "failed to create Lua state");
                return false;
            }
            *static_cast<Impl **>(lua_getextraspace(state)) = this;
            remainingInstructions = limits.maximumInstructionsPerRun;
            lua_sethook(
                state,
                instructionHook,
                LUA_MASKCOUNT,
                static_cast<int>(std::min<std::uint32_t>(
                    limits.instructionHookInterval,
                    static_cast<std::uint32_t>(
                        std::numeric_limits<int>::max()))));
            openRestrictedLibraries();
            registerApi();

            const auto chunkName = "@" + sourceName;
            lua_pushcfunction(state, buildTraceback);
            const auto errorHandler = lua_gettop(state);
            const auto compileStatus = luaL_loadbufferx(
                state,
                source.data(),
                source.size(),
                chunkName.c_str(),
                "t");
            if (compileStatus != LUA_OK)
            {
                const auto *message = lua_tostring(state, -1);
                appendLog(
                    SvLuaLogLevel::Error,
                    SvLuaLogKind::CompileError,
                    message ? message : "unknown Lua compile error");
                closeState();
                return false;
            }

            const auto runtimeStatus = lua_pcall(state, 0, 0, errorHandler);
            if (runtimeStatus != LUA_OK)
            {
                const auto *trace = lua_tostring(state, -1);
                const auto [message, traceback] = splitTraceback(
                    trace ? std::string_view(trace) :
                        std::string_view("unknown Lua runtime error"));
                appendLog(
                    SvLuaLogLevel::Error,
                    SvLuaLogKind::RuntimeError,
                    message,
                    traceback);
                closeState();
                return false;
            }

            lua_settop(state, 0);
            loaded = true;
            return true;
        }

        void reset()
        {
            if (!state && !loaded)
                return;
            closeState();
            ++generation;
            sourceName.clear();
        }

        const SvScriptBuiltinRegistry &builtins;
        SvLuaRuntimeLimits limits;
        AllocatorState allocator;
        lua_State *state{};
        std::uint64_t generation{};
        std::uint64_t remainingInstructions{};
        bool loaded{};
        std::string sourceName;
        std::vector<SvLuaLogEntry> logs;
        std::map<SvWorldEventType, std::vector<int>> eventCallbacks;
        std::vector<ScheduledThread> scheduledThreads;
        std::uint32_t currentServerTime{};
    };

    SvLuaRuntime::SvLuaRuntime(
        const SvScriptBuiltinRegistry &builtins,
        const SvLuaRuntimeLimits limits)
        : impl_(std::make_unique<Impl>(builtins, limits))
    {
    }

    SvLuaRuntime::~SvLuaRuntime() = default;

    bool SvLuaRuntime::reload(
        const std::string_view sourceName,
        const std::string_view source)
    {
        return impl_->reload(sourceName, source);
    }

    bool SvLuaRuntime::dispatchWorldEvents(
        const std::span<const SvWorldEvent> events)
    {
        return impl_->dispatchWorldEvents(events);
    }

    bool SvLuaRuntime::dispatchTouchNotifications(
        const SvClientImpactScriptNotificationBatch &notifications)
    {
        return impl_->dispatchTouchNotifications(notifications);
    }

    bool SvLuaRuntime::advance(const std::uint32_t serverTime)
    {
        return impl_->advance(serverTime);
    }

    void SvLuaRuntime::reset()
    {
        impl_->reset();
    }

    SvLuaRuntimeStatus SvLuaRuntime::status() const
    {
        return {
            .generation = impl_->generation,
            .loaded = impl_->loaded,
            .sourceName = impl_->sourceName,
            .scheduledThreadCount = impl_->scheduledThreads.size(),
        };
    }

    std::vector<SvLuaLogEntry> SvLuaRuntime::takeLogs()
    {
        auto logs = std::move(impl_->logs);
        impl_->logs.clear();
        return logs;
    }
}
