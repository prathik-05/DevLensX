from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional
import time
import psutil
import os

@dataclass
class BenchmarkMetrics:
    wall_clock_ms: float = 0
    cpu_time_ms: float = 0
    files_processed: int = 0
    symbols_processed: int = 0
    relationships_processed: int = 0
    bytes_processed: int = 0
    memory_peak_mb: float = 0
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self):
        d = asdict(self)
        e = d.pop("extra")
        d.update(e)
        return d

class Timer:
    def __init__(self):
        self.start_wall = time.perf_counter()
        self.start_cpu = time.process_time()
        self.proc = psutil.Process(os.getpid()) if psutil else None
        self.mem_start = self.proc.memory_info().rss if self.proc else 0

    def stop(self, **extra) -> BenchmarkMetrics:
        wall = (time.perf_counter() - self.start_wall) * 1000
        cpu = (time.process_time() - self.start_cpu) * 1000
        mem_peak = 0
        if self.proc:
            try:
                mem_peak = self.proc.memory_info().rss / (1024*1024)
            except: pass
        m = BenchmarkMetrics(wall_clock_ms=round(wall,2), cpu_time_ms=round(cpu,2), memory_peak_mb=round(mem_peak,2))
        for k,v in extra.items():
            m.extra[k] = v
        return m
