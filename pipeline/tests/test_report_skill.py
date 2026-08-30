from __future__ import annotations

from pathlib import Path

import yaml


SKILL_DIR = Path(__file__).parents[2] / ".agents" / "skills" / "market-report-composer"


def test_report_composer_skill_is_shareable_and_complete() -> None:
    skill_text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    frontmatter = yaml.safe_load(skill_text.split("---", 2)[1])
    ui = yaml.safe_load((SKILL_DIR / "agents" / "openai.yaml").read_text(encoding="utf-8"))

    assert frontmatter["name"] == "market-report-composer"
    assert "references/report-contract.md" in skill_text
    assert "references/editorial-sequence.md" in skill_text
    assert (SKILL_DIR / "references" / "report-contract.md").is_file()
    assert (SKILL_DIR / "references" / "editorial-sequence.md").is_file()
    assert "$market-report-composer" in ui["interface"]["default_prompt"]
    assert ui["policy"]["allow_implicit_invocation"] is True
