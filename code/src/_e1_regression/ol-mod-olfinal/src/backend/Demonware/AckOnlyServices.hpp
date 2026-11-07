#pragma once

#include "ServiceRegistry.hpp"

namespace AlwaysofflineRe::Demonware
{
    /// The bdSDK tasks the client sends during menu bring-up that need only an empty,
    /// error-free reply, and are known to need only that.
    ///
    /// WHAT REGISTERING THEM BUYS, now that ServiceRegistry::acknowledgeUnhandled answers every
    /// task: exactly one thing, and it is worth having. An unregistered task is logged
    /// LSG_UNHANDLED, which is the coverage work list; a registered one is logged by name.
    /// Without this split, a task nobody has ever looked at is indistinguishable from one that
    /// was looked at and found to want nothing -- and it was the first kind hiding among the
    /// second that cost the last two sessions.
    ///
    /// PROVENANCE, and a correction. An earlier version of this file said these were "handled
    /// by the C# OLfinal LobbyServer". They are not, in the sense that mattered: Messaging2.cs,
    /// RichPresence.cs and Mail.cs exist in that server but have no arm in Client.cs's service
    /// switch, so they never run. What actually answered these was the same universal fallback
    /// this backend has now -- `if (!handled) SendTaskReply(taskId)`. The bytes on the wire were
    /// always the empty reply; only the route was wrong in the comment. The claim that survives
    /// is the one that was always the real evidence: an OLfinal client received an empty reply
    /// for each of these and went on to draw the menu.
    ///
    /// SEVERAL OF THESE ALSO APPEAR IN CodolStartupTasks' recovered-capture table, and that
    /// overlap is deliberate. Registration is insert_or_assign and this service registers LAST
    /// (Servers.cpp), so these entries win -- which changes nothing on the wire (both send the
    /// empty reply) and everything in the log, where `RecoveredEmpty::0x03/0x2E` becomes
    /// `Teams::task46`. The startup table's provenance is a 3.3.3.3-era startup capture; these
    /// are from an OLfinal client at the menu. Both are real, and the more specific name wins.
    ///
    /// Task ids are MEASURED, from lobby_tasks.log of an OLfinal client reaching the menu on
    /// 2026-08-17, with the request count from that session beside each entry. Anything not
    /// seen on the wire is deliberately absent rather than guessed.
    class AckOnlyServices
    {
    public:
        void registerTasks(ServiceRegistry &registry) const;

    private:
        [[nodiscard]] static ServiceResponse acknowledge(const ServiceRequest &request);
    };
}
