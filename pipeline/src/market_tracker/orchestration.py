from __future__ import annotations

from dataclasses import dataclass, replace


@dataclass(frozen=True, slots=True)
class LoopPolicy:
    max_parallel_agents: int = 3
    max_research_supplements: int = 1
    max_revisions: int = 2


@dataclass(frozen=True, slots=True)
class LoopBudget:
    policy: LoopPolicy = LoopPolicy()
    research_supplements: int = 0
    revisions: int = 0

    def supplement_research(self) -> "LoopBudget":
        if self.research_supplements >= self.policy.max_research_supplements:
            raise LoopLimitExceeded("research supplement limit reached")
        return replace(self, research_supplements=self.research_supplements + 1)

    def revise(self) -> "LoopBudget":
        if self.revisions >= self.policy.max_revisions:
            raise LoopLimitExceeded("revision limit reached")
        return replace(self, revisions=self.revisions + 1)


class LoopLimitExceeded(RuntimeError):
    pass
