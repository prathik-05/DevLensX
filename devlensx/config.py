"""
DevLensX System Configurations & Default Parameters
"""

import os
from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).parent.parent.resolve()
KUZU_DB_DIR = os.path.join(BASE_DIR, "devlensx_graph_db")

# Vector Store Model
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
VECTOR_DIMENSION = 384

# Locked 5-Weighted Score Formula Weights
SCORE_WEIGHTS = {
    "architecture": 0.30,
    "security": 0.25,
    "maintainability": 0.20,
    "coupling": 0.15,
    "evidence_coverage": 0.10
}

# Blast Radius Risk Thresholds (Incoming Dependents Count)
RISK_THRESHOLDS = {
    "HIGH": 15,
    "MEDIUM": 5,
    "LOW": 0
}

# Maintainability God Class Threshold
GOD_CLASS_METHOD_LIMIT = 15
