"""Access rule by firm, role and portfolio (NUC-02, P-09).

Pure functions: the caller loads the session membership and the client through
its own repository and asks the rule. No database, no HTTP, no user messages.
"""

from collections.abc import Iterable

from lastro.core.contracts import AccessDecision, Action, ClientScope, Membership, Role


def decide_access(
    membership: Membership, action: Action, client: ClientScope | None
) -> AccessDecision:
    """Decide whether a member may perform an action on a client.

    Checks run in the order of P-09: invalid membership, then missing client or
    client of another firm (both `NOT_FOUND`, so nobody learns that a client of
    another firm exists), then the rule of the action.

    Args:
        membership: Active membership of the session.
        action: What the member wants to do.
        client: The client, or `None` when the id does not exist.

    Returns:
        The decision; any refusal says why.
    """
    if (
        not _is_valid(membership)
        or client is None
        or client.firm_id != membership.firm_id
    ):
        return AccessDecision.NOT_FOUND

    is_manager = membership.role is Role.MANAGER
    is_responsible = client.responsible_member_id == membership.member_id

    if action is Action.MANAGE_ASSIGNMENT:
        return AccessDecision.ALLOWED if is_manager else AccessDecision.FORBIDDEN_ROLE
    if is_responsible or (action is Action.LIST and is_manager):
        return AccessDecision.ALLOWED
    if action is Action.ACCESS and is_manager:
        return AccessDecision.NOT_ASSIGNED
    return AccessDecision.NOT_FOUND


def filter_visible_clients(
    membership: Membership, clients: Iterable[ClientScope]
) -> list[ClientScope]:
    """Keep only the clients the member may see in the list, in input order.

    Args:
        membership: Active membership of the session.
        clients: Clients to filter.

    Returns:
        The clients for which `Action.LIST` is allowed.
    """
    return [
        client
        for client in clients
        if decide_access(membership, Action.LIST, client) is AccessDecision.ALLOWED
    ]


def _is_valid(membership: Membership) -> bool:
    """Tell whether the membership is active and has a firm and a known role."""
    return (
        membership.is_active
        and membership.firm_id is not None
        and isinstance(membership.role, Role)
    )
