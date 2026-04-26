from __future__ import annotations

import pytest

from deepscientist.diagnostics import diagnose_runner_failure


@pytest.mark.parametrize(
    "message",
    [
        "unexpected status 403 Forbidden: account balance is negative, please recharge first",
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


def test_codex_bad_request_protocol_errors_stay_non_retryable_local_diagnostics() -> None:
    diagnosis = diagnose_runner_failure(
        runner_name="codex",
        stderr_text='{"type":"error","error":{"type":"bad_request_error","message":"invalid params, tool call result does not follow tool call (2013)","http_code":"400"}}',
    )

    assert diagnosis is not None
    assert diagnosis.code == "minimax_tool_result_sequence_error"
    assert diagnosis.retriable is False
