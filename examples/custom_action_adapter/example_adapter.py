"""Minimal explicit action adapter example."""

from __future__ import annotations

from worldbench import NormalizedActions, PluginCapabilities
from worldbench.schemas import ActionRecord


class DirectionActionAdapter:
    name = "direction_action_adapter"
    version = "0.1.0"
    supported_schema = "example.direction_actions.v1"
    capabilities = PluginCapabilities(
        inputs=("example.direction_actions.v1",),
        outputs=("worldbench.actions.v1",),
        limitations=("Only documented direction labels are supported.",),
    )

    def normalize(self, actions: object) -> NormalizedActions:
        if not isinstance(actions, list):
            raise ValueError("Expected a list of documented direction action labels.")
        records = []
        for index, raw in enumerate(actions):
            if raw not in {"move_left", "move_right", "move_up", "move_down", "hold"}:
                raise ValueError(
                    f"Unsupported direction action at index {index}: {raw}"
                )
            records.append(ActionRecord(t=index, action=str(raw)))
        return NormalizedActions(
            schema="worldbench.actions.v1",
            actions=tuple(records),
            adapter_name=self.name,
            adapter_version=self.version,
        )
