from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any
from enum import Enum

class LanguageStatus(str, Enum):
    VALIDATED = "VALIDATED"
    ADAPTER_AVAILABLE = "ADAPTER_AVAILABLE"
    PARSER_AVAILABLE = "PARSER_AVAILABLE"
    UNSUPPORTED = "UNSUPPORTED"
    VALIDATION_PENDING = "VALIDATION_PENDING"
    VALIDATION_FAILED = "VALIDATION_FAILED"

@dataclass
class LanguageValidationRecord:
    language: str
    parser_available: bool = False
    adapter_available: bool = False
    real_repository: Optional[Dict[str, str]] = None
    files_discovered: int = 0
    files_parsed: int = 0
    parse_failures: int = 0
    symbols: int = 0
    relationships: int = 0
    evidence_resolution: bool = False
    wiki_generation: bool = False
    diagram_generation: bool = False
    chat_validation: bool = False
    workspace_validation: bool = False
    status: LanguageStatus = LanguageStatus.VALIDATION_PENDING
    failure_stage: Optional[str] = None
    commit_hash: Optional[str] = None
    validation_timestamp: Optional[str] = None

    def to_dict(self):
        d = asdict(self)
        d["status"] = self.status.value if isinstance(self.status, LanguageStatus) else self.status
        return d
