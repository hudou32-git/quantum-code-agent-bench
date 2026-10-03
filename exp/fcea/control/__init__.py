"""DEU-RC (Dynamic Evidence Utility Guided Repair Control).

Research hypothesis (rq4_deurc_design.md): dynamic utility signals control
repair behavior more effectively when converted into explicit repair control
states that RESTRICT the LLM decision space — control state -> decision-space
reduction — than when merely selecting actions (DEU-v3-ACT) or emitting soft
guidance (DEU-v2/v3).

Pipeline: state manager (frozen DEU-v2) -> dynamic utility (frozen EMA) ->
Repair Control Index -> Repair Mode Selector -> evidence gate + context gate
-> LLM execution. Deterministic everywhere; no LLM in the controller.
"""
from exp.fcea.control.control_index import DEFAULT_CONSTANTS as RCI_CONSTANTS
from exp.fcea.control.controller import RepairController

__all__ = ["RCI_CONSTANTS", "RepairController"]
