"""P1-G review telemetry: correlation identity, lifecycle, timings, outcomes.

Observes the existing review architecture through D10 primitives
(emit_event / record_metric with automatic sanitization). Introduces no new
event bus, persistence, graph, or truth mechanism.

Invariants:
- Payloads carry counts, ids, enums, and timings ONLY. Never source code,
  prompts, raw diffs, API keys, secret values, or full LLM responses.
- Counts/timings are operational measurements, never correctness scores.
- Every event is bound to repository_id + analysis_run_id + commit_hash
  (snapshot isolation is structural, not conventional).
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Provider failure taxonomy (normalized categories, raw exceptions sanitized)
# ---------------------------------------------------------------------------
FAIL_AUTHENTICATION = "AUTHENTICATION"
FAIL_AUTHORIZATION = "AUTHORIZATION"
FAIL_RATE_LIMIT = "RATE_LIMIT"
FAIL_TIMEOUT = "TIMEOUT"
FAIL_CONNECTION = "CONNECTION"
FAIL_MALFORMED = "MALFORMED_RESPONSE"
FAIL_STREAM = "STREAM_INTERRUPTED"
FAIL_OUTPUT_LIMIT = "OUTPUT_LIMIT"
FAIL_UNKNOWN = "UNKNOWN"


def classify_provider_failure(exc: BaseException, status: Optional[int] = None) -> Dict[str, Any]:
    """Normalize a provider transport failure. Never includes raw text."""
    name = type(exc).__name__
    if "EMPTY_PROVIDER_RESPONSE" in str(exc):
        return {"category": FAIL_UNKNOWN, "error_type": name, "detail": "empty_response"}
    code = status
    if code is None:
        code = getattr(exc, "code", None) or getattr(getattr(exc, "response", None), "status_code", None)
    try:
        code = int(code) if code is not None else None
    except Exception:
        code = None
    if code == 401:
        category = FAIL_AUTHENTICATION
    elif code == 403:
        category = FAIL_AUTHORIZATION
    elif code == 429:
        category = FAIL_RATE_LIMIT
    elif name in ("TimeoutError",) or "timeout" in name.lower() or "timed out" in str(exc).lower():
        category = FAIL_TIMEOUT
    elif name in ("ConnectionError", "ConnectionRefusedError", "ConnectionResetError") or "connection" in name.lower():
        category = FAIL_CONNECTION
    elif name in ("JSONDecodeError", "ValueError", "UnicodeDecodeError"):
        category = FAIL_MALFORMED
    elif "interrupted" in str(exc).lower() or "disconnect" in str(exc).lower():
        category = FAIL_STREAM
    else:
        category = FAIL_UNKNOWN
    out: Dict[str, Any] = {"category": category, "error_type": name}
    if code is not None:
        out["http_status"] = code
    return out


# ---------------------------------------------------------------------------
# Review trace: per-operation correlation + phase timings + counters
# ---------------------------------------------------------------------------
@dataclass
class ReviewTrace:
    review_id: str = ""
    repository_id: Optional[str] = None
    analysis_run_id: Optional[str] = None
    commit_hash: Optional[str] = None
    provider: str = "offline"
    model: str = ""
    mode: str = "diff"  # diff | repo | stream | offline
    t0: float = 0.0
    marks: Dict[str, float] = field(default_factory=dict)
    counts: Dict[str, int] = field(default_factory=dict)
    flags: Dict[str, Any] = field(default_factory=dict)

    def mark(self, phase: str) -> float:
        now = time.perf_counter()
        if not self.t0:
            self.t0 = now
        self.marks[phase] = now
        return now

    def count(self, key: str, n: int = 1) -> None:
        self.counts[key] = self.counts.get(key, 0) + n

    def set_flag(self, key: str, value: Any) -> None:
        self.flags[key] = value

    def _ctx(self):
        from devlensx.observability.models import ObservabilityContext
        return ObservabilityContext(
            repository_id=self.repository_id,
            analysis_run_id=self.analysis_run_id,
            commit_hash=self.commit_hash,
            request_id=self.review_id or None,
        )

    def _base_extra(self) -> Dict[str, Any]:
        return {"review_id": self.review_id, "provider": self.provider,
                "model": self.model, "mode": self.mode}

    def event(
        self,
        event_type: str,
        status: Optional[str] = None,
        counts: Optional[Dict[str, int]] = None,
        error_code: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
        duration_ms: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Emit a sanitized D10 event bound to this trace's snapshot identity."""
        from devlensx.observability.events import emit_event
        payload = dict(self._base_extra())
        if extra:
            payload.update(extra)
        return emit_event(event_type, context=self._ctx(), duration_ms=duration_ms,
                          status=status, counts=counts, error_code=error_code, extra=payload)

    def metric(self, name: str, value: float, unit: str = "ms",
               extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        from devlensx.observability.metrics import record_metric
        payload = dict(self._base_extra())
        if extra:
            payload.update(extra)
        return record_metric(name, value, unit=unit, context=self._ctx(), extra=payload)

    def _elapsed(self, start_key: str, end_key: Optional[str] = None) -> Optional[float]:
        if start_key not in self.marks:
            return None
        end = self.marks.get(end_key, time.perf_counter()) if end_key else time.perf_counter()
        return round((end - self.marks[start_key]) * 1000.0, 2)

    def summary(self) -> Dict[str, Any]:
        """Operational truth: timings + counts + identity. No content, ever."""
        return {
            "review_id": self.review_id,
            "repository_id": self.repository_id,
            "analysis_run_id": self.analysis_run_id,
            "commit_hash": self.commit_hash,
            "provider": self.provider,
            "model": self.model,
            "mode": self.mode,
            "total_duration_ms": self._elapsed("start"),
            "provider_duration_ms": self._elapsed("provider_start", "provider_end"),
            "time_to_first_token_ms": self._elapsed("provider_start", "provider_first_token"),
            "verification_duration_ms": self._elapsed("verification_start", "verification_end"),
            "finalization_duration_ms": self._elapsed("finalization_start", "finalization_end"),
            "counts": dict(self.counts),
            "flags": dict(self.flags),
        }


def new_trace(
    repository_id: Optional[str] = None,
    analysis_run_id: Optional[str] = None,
    commit_hash: Optional[str] = None,
    provider: str = "offline",
    model: str = "",
    mode: str = "diff",
) -> ReviewTrace:
    trace = ReviewTrace(
        review_id=f"rev-{uuid.uuid4().hex[:12]}",
        repository_id=repository_id,
        analysis_run_id=analysis_run_id,
        commit_hash=commit_hash,
        provider=provider,
        model=model,
        mode=mode,
    )
    trace.mark("start")
    return trace
