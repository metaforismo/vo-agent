"""Verifier primitives for evidence-gated claims."""

from __future__ import annotations

import inspect
import os
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Protocol

from vo.exceptions import VerificationError
from vo.models import Claim, Evidence, VerificationResult


@dataclass(slots=True)
class VerificationContext:
    """Runtime context shared by verifiers."""

    cwd: str | Path | None = None
    env: dict[str, str] = field(default_factory=dict)
    timeout: float | None = None

    def merged_env(self) -> dict[str, str]:
        return {**os.environ, **self.env}


class Verifier(Protocol):
    name: str

    def verify(self, claim: Claim, context: VerificationContext) -> Evidence:
        """Run verification and return evidence."""


class CommandVerifier:
    """Verifier that records the result of a local shell command."""

    def __init__(
        self,
        command: str,
        *,
        name: str | None = None,
        timeout: float | None = None,
    ) -> None:
        if not command.strip():
            raise ValueError("command must not be empty")
        self.command = command
        self.name = name or command
        self.timeout = timeout

    def verify(self, claim: Claim, context: VerificationContext) -> Evidence:
        del claim
        started = time.monotonic()
        timeout = self.timeout if self.timeout is not None else context.timeout
        completed = subprocess.run(
            self.command,
            shell=True,
            cwd=Path(context.cwd) if context.cwd is not None else None,
            env=context.merged_env(),
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        duration_s = time.monotonic() - started
        passed = completed.returncode == 0
        summary = (
            f"command exited 0: {self.command}"
            if passed
            else f"command exited {completed.returncode}: {self.command}"
        )
        return Evidence(
            name=self.name,
            kind="command",
            passed=passed,
            summary=summary,
            data={
                "command": self.command,
                "cwd": str(Path(context.cwd)) if context.cwd is not None else None,
                "duration_s": round(duration_s, 6),
                "exit_code": completed.returncode,
                "stdout": completed.stdout,
                "stderr": completed.stderr,
            },
        )


class CallableVerifier:
    """Verifier adapter for small Python checks."""

    def __init__(
        self,
        fn: Callable[..., bool | Evidence],
        *,
        name: str | None = None,
    ) -> None:
        self.fn = fn
        self.name = name or getattr(fn, "__name__", "callable")

    def verify(self, claim: Claim, context: VerificationContext) -> Evidence:
        del claim
        signature = inspect.signature(self.fn)
        result = self.fn() if len(signature.parameters) == 0 else self.fn(context)
        if isinstance(result, Evidence):
            return result
        if isinstance(result, bool):
            return Evidence(
                name=self.name,
                kind="callable",
                passed=result,
                summary="callable returned true" if result else "callable returned false",
            )
        raise VerificationError(
            f"callable verifier {self.name!r} must return bool or Evidence"
        )


class VerifierChain:
    """Runs verifiers in order and gates a claim on their evidence."""

    def __init__(self, verifiers: list[Verifier]) -> None:
        if not verifiers:
            raise ValueError("verifier chain must contain at least one verifier")
        self.verifiers = list(verifiers)

    def verify(
        self,
        claim: Claim,
        context: VerificationContext | None = None,
    ) -> VerificationResult:
        context = context or VerificationContext()
        collected: list[Evidence] = []
        failed: Evidence | None = None

        for verifier in self.verifiers:
            try:
                evidence = verifier.verify(claim, context)
            except Exception as exc:
                evidence = Evidence(
                    name=getattr(verifier, "name", type(verifier).__name__),
                    kind="exception",
                    passed=False,
                    summary=f"{type(exc).__name__}: {exc}",
                    data={"error_type": type(exc).__name__, "error": str(exc)},
                )
            claim.add_evidence(evidence)
            collected.append(evidence)
            if not evidence.passed:
                failed = evidence
                claim.reject()
                break

        if failed is None:
            claim.accept()
        return VerificationResult(
            passed=failed is None,
            evidence=collected,
            failed_evidence=failed,
        )
