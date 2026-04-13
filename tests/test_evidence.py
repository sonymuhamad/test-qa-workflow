import pytest
import json
from lib.evidence import EvidenceCapture, TestCaseResult


class TestTestCaseResult:
    def test_create_pass_result(self):
        result = TestCaseResult(
            test_case_id=1, category="Happy Path", description="Basic GET",
            status="PASS", duration_ms=150,
            request={"method": "GET", "url": "http://localhost/admin/test", "headers": {}, "body": None},
            response={"status_code": 200, "body": {"data": []}, "duration_ms": 120},
        )
        assert result.status == "PASS"
        assert result.test_case_id == 1
        assert result.response["status_code"] == 200

    def test_create_fail_result(self):
        result = TestCaseResult(
            test_case_id=2, category="Auth", description="No auth",
            status="FAIL", duration_ms=50,
            request={"method": "GET", "url": "http://localhost/admin/test", "headers": {}, "body": None},
            response={"status_code": 200, "body": {}},
            failure_reason="Expected status 401, got 200",
        )
        assert result.status == "FAIL"
        assert result.failure_reason == "Expected status 401, got 200"

    def test_to_dict(self):
        result = TestCaseResult(
            test_case_id=1, category="Happy Path", description="Test",
            status="PASS", duration_ms=100,
            request={"method": "GET", "url": "http://localhost/test", "headers": {}, "body": None},
            response={"status_code": 200, "body": {}, "duration_ms": 80},
        )
        d = result.to_dict()
        assert d["id"] == 1
        assert d["status"] == "PASS"
        assert "request" in d
        assert "response" in d


class TestEvidenceCapture:
    def test_add_result(self):
        capture = EvidenceCapture(ticket="SD-0000", run_id="run-123")
        capture.add_result(TestCaseResult(
            test_case_id=1, category="Happy Path", description="Test",
            status="PASS", duration_ms=100,
            request={"method": "GET", "url": "http://localhost/test", "headers": {}, "body": None},
            response={"status_code": 200, "body": {}, "duration_ms": 80},
        ))
        assert len(capture.results) == 1

    def test_summary(self):
        capture = EvidenceCapture(ticket="SD-0000", run_id="run-123")
        capture.add_result(TestCaseResult(
            test_case_id=1, category="Happy Path", description="Pass test",
            status="PASS", duration_ms=100,
            request={"method": "GET", "url": "http://localhost/test", "headers": {}, "body": None},
            response={"status_code": 200, "body": {}, "duration_ms": 80},
        ))
        capture.add_result(TestCaseResult(
            test_case_id=2, category="Auth", description="Fail test",
            status="FAIL", duration_ms=50,
            request={"method": "GET", "url": "http://localhost/test", "headers": {}, "body": None},
            response={"status_code": 200, "body": {}},
            failure_reason="Expected 401, got 200",
        ))
        summary = capture.summary()
        assert summary["total"] == 2
        assert summary["passed"] == 1
        assert summary["failed"] == 1

    def test_to_json(self):
        capture = EvidenceCapture(ticket="SD-0000", run_id="run-123")
        capture.add_result(TestCaseResult(
            test_case_id=1, category="Happy Path", description="Test",
            status="PASS", duration_ms=100,
            request={"method": "GET", "url": "http://localhost/test", "headers": {}, "body": None},
            response={"status_code": 200, "body": {}, "duration_ms": 80},
        ))
        json_str = capture.to_json()
        data = json.loads(json_str)
        assert data["ticket"] == "SD-0000"
        assert data["run_id"] == "run-123"
        assert len(data["test_cases"]) == 1
        assert "summary" in data

    def test_failed_cases(self):
        capture = EvidenceCapture(ticket="SD-0000", run_id="run-123")
        capture.add_result(TestCaseResult(
            test_case_id=1, category="Happy Path", description="Pass",
            status="PASS", duration_ms=100,
            request={"method": "GET", "url": "http://localhost/test", "headers": {}, "body": None},
            response={"status_code": 200, "body": {}, "duration_ms": 80},
        ))
        capture.add_result(TestCaseResult(
            test_case_id=2, category="Auth", description="Fail",
            status="FAIL", duration_ms=50,
            request={"method": "GET", "url": "http://localhost/test", "headers": {}, "body": None},
            response={"status_code": 200, "body": {}},
            failure_reason="Wrong status",
        ))
        failed = capture.failed_cases()
        assert len(failed) == 1
        assert failed[0].test_case_id == 2
