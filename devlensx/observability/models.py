from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any

@dataclass
class ObservabilityContext:
    repository_id: Optional[str] = None
    analysis_run_id: Optional[str] = None
    commit_hash: Optional[str] = None
    request_id: Optional[str] = None

@dataclass
class Metric:
    name: str
    value: float
    unit: str = "ms"
    context: ObservabilityContext = field(default_factory=ObservabilityContext)
    extra: Dict[str, Any] = field(default_factory=dict)
    def to_dict(self):
        d = asdict(self)
        e = d.pop("extra")
        d.update(e)
        ctx = d.pop("context")
        if hasattr(ctx, "__dataclass_fields__"):
            ctx_dict = asdict(ctx)
        elif isinstance(ctx, dict):
            ctx_dict = ctx
        else:
            ctx_dict = {}
        d["context"] = ctx_dict
        return d

@dataclass
class StageMetric:
    stage: str
    wall_clock_ms: float
    cpu_time_ms: float = 0
    success: bool = True
    files_processed: int = 0
    symbols_processed: int = 0
    relationships_processed: int = 0
    context: ObservabilityContext = field(default_factory=ObservabilityContext)
    def to_dict(self):
        d = asdict(self)
        ctx = d.pop("context")
        if hasattr(ctx, "__dataclass_fields__"):
            ctx_dict = asdict(ctx)
        elif isinstance(ctx, dict):
            ctx_dict = ctx
        else:
            ctx_dict = {}
        d.update({f"context_{k}":v for k,v in ctx_dict.items() if v})
        return d

@dataclass
class Event:
    event: str
    timestamp: str
    context: ObservabilityContext = field(default_factory=ObservabilityContext)
    duration_ms: Optional[float] = None
    status: Optional[str] = None
    counts: Optional[Dict[str, int]] = None
    error_code: Optional[str] = None
    request_id: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)
    def to_dict(self):
        d = asdict(self)
        e = d.pop("extra")
        d.update(e)
        ctx = d.pop("context")
        # ctx may be ObservabilityContext dataclass or already dict
        if hasattr(ctx, "__dataclass_fields__"):
            ctx_dict = asdict(ctx)
        elif isinstance(ctx, dict):
            ctx_dict = ctx
        else:
            ctx_dict = {}
        d.update({k:v for k,v in ctx_dict.items() if v})
        return {k:v for k,v in d.items() if v is not None}

@dataclass
class HealthStatus:
    status: str = "ok"
    brain: str = "ready"
    database: str = "ready"
    graph: str = "ready"
    vector_index: str = "ready"
    llm: str = "available"
    uptime: Optional[float] = None
    observability: str = "ready"
    def to_dict(self):
        return asdict(self)
