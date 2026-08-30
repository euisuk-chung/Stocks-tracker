import pytest

from market_tracker.orchestration import LoopBudget, LoopLimitExceeded


def test_research_and_revision_loops_are_bounded() -> None:
    budget = LoopBudget().supplement_research()
    with pytest.raises(LoopLimitExceeded):
        budget.supplement_research()

    budget = budget.revise().revise()
    with pytest.raises(LoopLimitExceeded):
        budget.revise()

    budget = budget.revise_knowledge()
    with pytest.raises(LoopLimitExceeded):
        budget.revise_knowledge()
