#pragma once

#include <cstdint>

// Exact Localnetworking plugin ABI used by the archived 2019 Ayria runtime.
// There is deliberately no virtual destructor: server instances remain owned
// by the Localnet32 plugin for the lifetime of the process.
struct IServer
{
    struct Address
    {
        std::uint32_t ipv4;
        std::uint16_t port;
    };

    struct Endpoints
    {
        Address client;
        Address server;
    };

    virtual void onConnect() {}
    virtual void onDisconnect() {}
    virtual bool onStreamread(void *data, std::uint32_t *size) = 0;
    virtual bool onStreamwrite(const void *data, std::uint32_t size) = 0;
    virtual bool onPacketread(void *data, std::uint32_t *size) = 0;
    virtual bool onPacketwrite(
        const void *data,
        std::uint32_t size,
        const Endpoints *endpoints) = 0;
};

struct IStreamServer : IServer
{
    bool onPacketread(void *, std::uint32_t *) override { return false; }
    bool onPacketwrite(const void *, std::uint32_t, const Endpoints *) override
    {
        return false;
    }
};

struct IDatagramServer : IServer
{
    bool onStreamread(void *, std::uint32_t *) override { return false; }
    bool onStreamwrite(const void *, std::uint32_t) override { return false; }
};

static_assert(sizeof(IServer::Address) == 8);
static_assert(sizeof(IServer::Endpoints) == 16);
