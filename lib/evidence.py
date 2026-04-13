"""Capture and serialize test execution evidence."""

import json
from dataclasses import dataclass


@dataclass
class TestCaseResult:
    test_case_id: int
    category: str
    description: str
    status: str  # "PASS" or "FAIL"
    duration_ms: int
    request: dict
    response: dict
    failure_reason: str | None = None

    def to_dict(self) -> dict:
        return {
            "id": self.test_case_id,
            "category": self.category,
            "description": self.description,
            "status": self.status,
            "duration_ms": self.duration_ms,
            "request": self.request,
            "response": self.response,
            "failure_reason": self.failure_reason,
        }


class EvidenceCapture:
    """Collects test results and produces structured output."""

    def __init__(self, ticket: str, run_id: str):
        self.ticket = ticket
        self.run_id = run_id
        self.results: list[TestCaseResult] = []

    def add_result(self, result: TestCaseResult):
        self.results.append(result)

    def summary(self) -> dict:
        passed = sum(1 for r in self.results if r.status == "PASS")
        failed = sum(1 for r in self.results if r.status == "FAIL")
        return {
            "total": len(self.results),
            "passed": passed,
            "failed": failed,
            "skipped": len(self.results) - passed - failed,
        }

    def failed_cases(self) -> list[TestCaseResult]:
        return [r for r in self.results if r.status == "FAIL"]

    def to_json(self) -> str:
        return json.dumps(
            {
                "ticket": self.ticket,
                "run_id": self.run_id,
                "summary": self.summary(),
                "test_cases": [r.to_dict() for r in self.results],
            },
            indent=2,
        )
