from dataclasses import dataclass
from typing import List, Dict, Any
import yaml
from pathlib import Path

@dataclass
class Action:
    type: str
    target: str
    params: Dict[str, Any]

@dataclass
class Phase:
    name: str
    duration_sec: int
    actions: List[Action]

@dataclass
class Scenario:
    name: str
    description: str
    phases: List[Phase]

def load_scenario(path: str) -> Scenario:
    path_obj = Path(path)
    if not path_obj.exists():
        raise FileNotFoundError(f"Scenario file not found: {path}")

    with open(path_obj, "r") as f:
        data = yaml.safe_load(f)

    phases = []
    for p in data.get("phases", []):
        actions = []
        for a in p.get("actions", []):
            a_type = a.get("type")
            a_target = a.get("target")
            # everything else goes into params
            params = {k: v for k, v in a.items() if k not in ("type", "target")}
            actions.append(Action(type=a_type, target=a_target, params=params))
        phases.append(
            Phase(
                name=p.get("name"),
                duration_sec=p.get("duration_sec", 0),
                actions=actions,
            )
        )

    return Scenario(
        name=data.get("name", path_obj.stem),
        description=data.get("description", ""),
        phases=phases,
    )
