"""Compile parsed approval instructions into a validated workflow graph."""

from .errors import InvalidProcessError, WorkflowCycleError


def _state_name(role):
    return "pending_" + role.replace("-", "_")


def _detect_graph_cycle(transitions, line=None, sentence=None):
    graph = {}
    for transition in transitions:
        graph.setdefault(transition["from"], []).append(transition["to"])
    visiting = set()
    visited = set()

    def visit(state):
        if state in visiting:
            raise WorkflowCycleError(
                f"Approval workflow contains a cycle through state '{state}'.",
                line=line,
                sentence=sentence,
            )
        if state in visited:
            return
        visiting.add(state)
        for target in graph.get(state, []):
            visit(target)
        visiting.remove(state)
        visited.add(state)

    for state in graph:
        visit(state)


def compile_workflow(parse_tree):
    approvals = parse_tree["approvals"]
    states = ["draft", "submitted", "approved", "rejected"]
    transitions = [{"from": "draft", "to": "submitted", "on": "submit"}]
    approver_roles = []

    chains = [item for item in approvals if item["kind"] == "chain"]
    thresholds = [item for item in approvals if item["kind"] == "threshold"]
    if chains and thresholds:
        raise InvalidProcessError("A process cannot mix a linear approval chain with threshold routes.")
    if len(chains) > 1:
        raise InvalidProcessError("Only one approval chain is supported.")

    if chains:
        chain = chains[0]
        roles = chain["roles"]
        approver_roles = roles
        pending_states = []
        for role in roles:
            pending = _state_name(role)
            if pending not in states:
                states.append(pending)
            pending_states.append(pending)
        transitions.append({"from": "submitted", "to": pending_states[0], "on": "submit"})
        for index, role in enumerate(roles):
            pending = pending_states[index]
            transitions.append({"from": pending, "to": "rejected", "on": "reject", "approver_role": role})
            destination = pending_states[index + 1] if index + 1 < len(roles) else "approved"
            transitions.append({"from": pending, "to": destination, "on": "approve", "approver_role": role})
    elif thresholds:
        for item in thresholds:
            role = item["role"]
            if role != "requester" and role not in approver_roles:
                approver_roles.append(role)
            target = "approved" if item["mode"] == "automatic" else _state_name(role)
            if target not in states:
                states.append(target)
            condition = {"field": item["field"], "operator": item["operator"]}
            if item["operator"] == "between":
                condition.update({"minimum": item["minimum"], "maximum": item["maximum"]})
            else:
                condition["value"] = item["value"]
            transitions.append({
                "from": "submitted",
                "to": target,
                "on": "route",
                "approver_role": role,
                "mode": item["mode"],
                "condition": condition,
            })
            if item["mode"] == "manual":
                transitions.append({"from": target, "to": "approved", "on": "approve", "approver_role": role})
                transitions.append({"from": target, "to": "rejected", "on": "reject", "approver_role": role})
    else:
        transitions.append({"from": "submitted", "to": "approved", "on": "submit", "mode": "automatic"})

    chain_context = chains[0] if chains else {}
    _detect_graph_cycle(transitions, chain_context.get("line"), chain_context.get("sentence"))

    return {
        "states": states,
        "transitions": transitions,
        "approver_roles": approver_roles,
        "threshold_conditions": [t["condition"] for t in transitions if "condition" in t],
        "escalation_rules": [a for a in parse_tree["actions"] if a["kind"] == "escalate"],
    }
