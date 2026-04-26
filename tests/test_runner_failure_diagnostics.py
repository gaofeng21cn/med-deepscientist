from __future__ import annotations

import pytest

from deepscientist.diagnostics import diagnose_runner_failure


@pytest.mark.parametrize(
    "message",
    [
        "unexpected status 429 Too Many Requests: rate limit exceeded",
        "unexpected status 503 Service Unavailable",
        '{"error":{"message":"502 Bad Gateway from upstream provider","http_code":"502"}}',
    ],
)
def test_codex_upstream_provider_errors_are_retryable_external_blockers(message: str) -> None:
    diagnosis = diagnose_runner_failure(runner_name="codex", output_text=message)

    assert diagnosis is not None
    assert diagnosis.code == "codex_upstream_provider_error"
    assert diagnosis.retriable is True


@pytest.mark.parametrize(
    "message",
    [
        "unexpected status 403 Forbidden: account balance is negative, please recharge first",
        "unexpected status 402 Payment Required: insufficient quota",
        '{"error":{"message":"quota exceeded for this account","http_code":"402"}}',
    ],
)
def test_codex_quota_errors_are_distinct_external_account_blockers(message: str) -> None:
    diagnosis = diagnose_runner_failure(runner_name="codex", output_text=message)

    assert diagnosis is not None
    assert diagnosis.code == "codex_upstream_quota_error"
    assert diagnosis.retriable is False


def test_codex_bad_request_protocol_errors_stay_non_retryable_local_diagnostics() -> None:
    diagnosis = diagnose_runner_failure(
        runner_name="codex",
        stderr_text='{"type":"error","error":{"type":"bad_request_error","message":"invalid params, tool call result does not follow tool call (2013)","http_code":"400"}}',
    )

    assert diagnosis is not None
    assert diagnosis.code == "minimax_tool_result_sequence_error"
    assert diagnosis.retriable is False


def test_local_protocol_error_wins_even_when_payload_mentions_quota_or_rate_limit() -> None:
    diagnosis = diagnose_runner_failure(
        runner_name="codex",
        stderr_text=(
            '{"type":"error","error":{"type":"bad_request_error","message":'
            '"invalid params, tool call result does not follow tool call (2013); '
            'tool payload mentioned quota exceeded and 429 Too Many Requests","http_code":"400"}}'
        ),
    )

    assert diagnosis is not None
    assert diagnosis.code == "minimax_tool_result_sequence_error"
    assert diagnosis.retriable is False


def test_retry_budget_exhaustion_gets_distinct_runner_diagnosis() -> None:
    diagnosis = diagnose_runner_failure(
        runner_name="codex",
        summary=(
            "Runner `codex` exited with code 1 on attempt 5/5. "
            "stderr: temporary transport failure. Retry budget exhausted after 5 attempt(s)."
        ),
    )

    assert diagnosis is not None
    assert diagnosis.code == "runner_retry_budget_exhausted"
    assert diagnosis.retriable is False


@pytest.mark.parametrize(
    ("summary", "expected_code"),
    [
        (
            "Cleared stale active turn state for run `run-stale` after no live worker was found.",
            "daemon_no_live_worker",
        ),
        (
            "Recovered stalled running turn `run-stalled` after 1800 seconds without tool activity while 1 queued user message(s) were waiting.",
            "daemon_stalled_live_turn",
        ),
        (
            "The quest is currently parked and will not auto-spin until a new user message or `/resume`.",
            "runtime_intentionally_parked",
        ),
    ],
)
def test_daemon_runtime_markers_get_distinct_diagnostics(summary: str, expected_code: str) -> None:
    diagnosis = diagnose_runner_failure(runner_name="daemon", summary=summary)

    assert diagnosis is not None
    assert diagnosis.code == expected_code
    assert diagnosis.retriable is False
