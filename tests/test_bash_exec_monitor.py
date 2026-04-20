from __future__ import annotations

from deepscientist.bash_exec.monitor import _drain_buffer, _render_terminal_log_line


def test_drain_buffer_flushes_oversized_unterminated_exec_lines() -> None:
    oversized = "x" * 200_000
    emitted: list[tuple[str, str]] = []

    def append_line(line: str, *, stream: str = "stdout") -> None:
        emitted.append((stream, line))

    remainder = _drain_buffer(oversized, append_line, flush_partial=False)

    partial_chunks = [line for stream, line in emitted if stream == "partial"]
    assert partial_chunks
    assert "".join(partial_chunks) + remainder == oversized
    assert max(len(chunk) for chunk in partial_chunks) <= 128_000
    assert len(remainder) <= 128_000


def test_render_terminal_log_line_truncates_huge_single_line_output() -> None:
    line = "prefix:" + ("x" * 100_000) + ":suffix"

    rendered = _render_terminal_log_line(line)

    assert rendered.startswith("prefix:")
    assert rendered.endswith(":suffix")
    assert "full content remains in log.jsonl" in rendered
    assert len(rendered) < len(line)
