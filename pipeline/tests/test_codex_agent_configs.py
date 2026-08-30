from __future__ import annotations

import tomllib
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
AGENTS_DIRECTORY = REPOSITORY_ROOT / ".codex" / "agents"
EXPECTED_AGENTS = {
    "gainer_researcher",
    "loser_researcher",
    "market_theme_researcher",
    "fact_checker",
    "blog_quality_reviewer",
    "humanify_reviewer",
}


def load_toml(path: Path) -> dict[str, object]:
    with path.open("rb") as file:
        return tomllib.load(file)


def test_project_agent_files_are_complete_and_shareable() -> None:
    agent_files = sorted(AGENTS_DIRECTORY.glob("*.toml"))
    assert {path.stem for path in agent_files} == EXPECTED_AGENTS

    loaded_agents = [load_toml(path) for path in agent_files]
    assert {agent["name"] for agent in loaded_agents} == EXPECTED_AGENTS

    for path, agent in zip(agent_files, loaded_agents, strict=True):
        assert agent["name"] == path.stem
        assert isinstance(agent.get("description"), str) and agent["description"].strip()
        assert isinstance(agent.get("developer_instructions"), str)
        assert agent["developer_instructions"].strip()
        assert agent.get("sandbox_mode") == "read-only"
        assert agent.get("approval_policy") == "never"
        assert "model" not in agent
        assert "model_reasoning_effort" not in agent


def test_project_agent_concurrency_is_limited_to_three() -> None:
    config = load_toml(REPOSITORY_ROOT / ".codex" / "config.toml")
    agents = config["agents"]

    assert isinstance(agents, dict)
    assert agents.get("enabled") is True
    assert agents.get("max_concurrent_threads_per_session") == 3
    assert "default_subagent_model" not in agents
    assert "default_subagent_reasoning_effort" not in agents
