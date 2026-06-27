"""Agent execution adapters."""

from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol, Sequence

from vo.models import Evidence, jsonable, utc_now
from vo.verifiers import VerificationContext


def _coerce_output_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode(errors="replace")
    return str(value)


@dataclass(slots=True)
class AgentRun:
    """Captured result of one agent task execution."""

    agent_name: str
    task: str
    command: list[str]
    exit_code: int
    stdout: str
    stderr: str
    duration_s: float
    started_at: str
    finished_at: str
    metadata: dict[str, object] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return self.exit_code == 0

    def to_dict(self) -> dict[str, object]:
        return {
            "agent_name": self.agent_name,
            "task": self.task,
            "command": list(self.command),
            "exit_code": self.exit_code,
            "passed": self.passed,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "duration_s": self.duration_s,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "metadata": jsonable(self.metadata),
        }

    def to_evidence(self) -> Evidence:
        return Evidence(
            name=f"agent:{self.agent_name}",
            kind="agent_run",
            passed=self.passed,
            summary=(
                f"agent {self.agent_name} exited 0"
                if self.passed
                else f"agent {self.agent_name} exited {self.exit_code}"
            ),
            data=self.to_dict(),
        )

    @classmethod
    def from_exception(
        cls,
        *,
        agent_name: str,
        task: str,
        command: Sequence[str],
        exc: BaseException,
        started_at: str,
        started: float,
        exit_code: int = -1,
        stdout: str = "",
        stderr: str | None = None,
        metadata: dict[str, object] | None = None,
    ) -> "AgentRun":
        error_metadata = {
            **(metadata or {}),
            "error_type": type(exc).__name__,
        }
        return cls(
            agent_name=agent_name,
            task=task,
            command=[str(part) for part in command],
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr if stderr is not None else str(exc),
            duration_s=round(time.monotonic() - started, 6),
            started_at=started_at,
            finished_at=utc_now(),
            metadata=error_metadata,
        )


class AgentAdapter(Protocol):
    """Narrow interface for executing one agent task."""

    name: str

    def run(
        self,
        task: str,
        context: VerificationContext | None = None,
    ) -> AgentRun:
        """Execute a task and return its captured transcript."""


class LocalCommandAgent:
    """Agent adapter backed by a local subprocess command.

    The task is sent to stdin. stdout, stderr, exit status, and duration are
    captured for replayable workflow bundles.
    """

    def __init__(
        self,
        command: Sequence[str],
        *,
        name: str,
        timeout: float | None = None,
        metadata: dict[str, object] | None = None,
    ) -> None:
        if not name.strip():
            raise ValueError("agent name must not be empty")
        if not command:
            raise ValueError("command must contain at least one argument")
        self.command = [str(part) for part in command]
        self.name = name
        self.timeout = timeout
        self.metadata = dict(metadata or {})

    def run(
        self,
        task: str,
        context: VerificationContext | None = None,
    ) -> AgentRun:
        context = context or VerificationContext()
        started_at = utc_now()
        started = time.monotonic()
        timeout = self.timeout if self.timeout is not None else context.timeout
        try:
            completed = subprocess.run(
                self.command,
                input=task,
                text=True,
                capture_output=True,
                cwd=Path(context.cwd) if context.cwd is not None else None,
                env=context.merged_env(),
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            return AgentRun.from_exception(
                agent_name=self.name,
                task=task,
                command=self.command,
                exc=exc,
                started_at=started_at,
                started=started,
                exit_code=124,
                stdout=_coerce_output_text(exc.output),
                stderr=f"command timed out after {exc.timeout} seconds",
                metadata={
                    **self.metadata,
                    "timed_out": True,
                    "timeout_s": exc.timeout,
                },
            )
        except OSError as exc:
            return AgentRun.from_exception(
                agent_name=self.name,
                task=task,
                command=self.command,
                exc=exc,
                started_at=started_at,
                started=started,
                exit_code=127,
                metadata=dict(self.metadata),
            )
        finished_at = utc_now()
        return AgentRun(
            agent_name=self.name,
            task=task,
            command=list(self.command),
            exit_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            duration_s=round(time.monotonic() - started, 6),
            started_at=started_at,
            finished_at=finished_at,
            metadata=dict(self.metadata),
        )
