"""Loads the scenario suite from evals/scenarios/ (design doc §10.1)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

EVALS_ROOT = Path(__file__).resolve().parent.parent
SCENARIOS_ROOT = EVALS_ROOT / "scenarios"


@dataclass(frozen=True)
class Scenario:
    id: str
    title: str
    mode: str
    language: str
    probes: list[str]
    task: str
    starter_files: dict[str, str]  # relative path -> file content
    output_file: str
    measure_diff_size: bool


def load_scenario(scenario_dir: Path) -> Scenario:
    meta = json.loads((scenario_dir / "meta.json").read_text(encoding="utf-8"))
    task = (scenario_dir / "task.md").read_text(encoding="utf-8")
    starter_files = {
        relative_path: (scenario_dir / relative_path).read_text(encoding="utf-8")
        for relative_path in meta["starter_files"]
    }
    return Scenario(
        id=meta["id"],
        title=meta["title"],
        mode=meta["mode"],
        language=meta["language"],
        probes=meta["probes"],
        task=task,
        starter_files=starter_files,
        output_file=meta["output_file"],
        measure_diff_size=meta["measure_diff_size"],
    )


def load_all_scenarios() -> list[Scenario]:
    scenario_dirs = sorted(p for p in SCENARIOS_ROOT.iterdir() if p.is_dir())
    return [load_scenario(d) for d in scenario_dirs]


def build_user_prompt(scenario: Scenario) -> str:
    """The task plus any starter files, laid out the way a human would paste
    them into a chat box with no file access -- this is the harness's
    equivalent of "local context" for a no-tools model."""
    sections = [scenario.task.strip()]
    for relative_path, content in scenario.starter_files.items():
        sections.append(f"```{scenario.language}\n# {relative_path}\n{content}\n```")
    return "\n\n".join(sections)
