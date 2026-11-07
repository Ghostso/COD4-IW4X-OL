#pragma once

namespace CodolGameServer
{
    // Names whoever calls CL_Disconnect in the CLIENT process. See the .cpp for why a
    // hook and not more static reading. Off unless OLMOD_DISCONNECT_WITNESS=1.
    enum class DisconnectWitnessResult
    {
        NotRequested,
        Installed,
        AlreadyInstalled,
        UnexpectedBytes,
        UnsupportedHost,
    };

    DisconnectWitnessResult installDisconnectWitness();
    const char *disconnectWitnessResultName(DisconnectWitnessResult result);
}
