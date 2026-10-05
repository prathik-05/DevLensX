import time, os
from devlensx.observability.models import HealthStatus
_start = time.time()

def get_health():
    has_llm = bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("OPENAI_API_KEY") or os.environ.get("OPENROUTER_API_KEY"))
    uptime = time.time() - _start
    return HealthStatus(
        status="ok",
        brain="ready",
        database="ready",
        graph="ready",
        vector_index="ready",
        llm="available" if has_llm else "unavailable (deterministic features active)",
        uptime=round(uptime,2),
        observability="ready"
    ).to_dict()
