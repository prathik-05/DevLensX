"""
DevLensX Core Configuration Module
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.parent.resolve()

# Database & Runtime Paths
DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{BASE_DIR}/devlensx.db")
KUZU_DB_DIR = os.environ.get("KUZU_DATABASE_PATH", os.path.join(BASE_DIR, "devlensx_graph_db"))
FAISS_INDEX_PATH = os.environ.get("FAISS_INDEX_PATH", os.path.join(BASE_DIR, ".devlensx-runtime", "faiss_index.bin"))

# Resource & Upload Security Thresholds
MAX_ZIP_SIZE_BYTES = 50 * 1024 * 1024       # 50 MB
MAX_EXTRACTED_FILES = 2000                   # 2,000 files limit
MAX_SINGLE_FILE_BYTES = 10 * 1024 * 1024    # 10 MB limit per file

# Authentication & Security
JWT_SECRET = os.environ.get("JWT_SECRET", "devlensx_secret_key_change_in_production_987654321")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 Days

# LLM & Vector Store Parameters
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
VECTOR_DIMENSION = 384

# Locked Score Formula Weights (30 / 25 / 20 / 15 / 10)
SCORE_WEIGHTS = {
    "architecture": 0.30,
    "security": 0.25,
    "maintainability": 0.20,
    "coupling": 0.15,
    "evidence_coverage": 0.10
}

# Blast Radius & Maintainability Thresholds
RISK_THRESHOLDS = {
    "HIGH": 15,
    "MEDIUM": 5,
    "LOW": 0
}
GOD_CLASS_METHOD_LIMIT = 15

# P1-B review diff grounding bounds (defense-in-depth behind API diff caps).
# The hunk parser enforces these and reports truncation instead of failing.
MAX_REVIEW_FILES = 50             # files parsed per diff
MAX_REVIEW_HUNKS_PER_FILE = 100   # hunks parsed per file
MAX_REVIEW_TOTAL_HUNKS = 500      # hunks parsed per diff
MAX_REVIEW_SYMBOLS = 100          # resolved symbols returned per diff
MAX_AFFECTED_PER_SYMBOL = 25      # affected entities recorded per changed symbol
MAX_AFFECTED_TOTAL = 100          # affected entities recorded per review
MAX_IMPACT_HOPS = 3               # graph/model traversal depth for affected set
MAX_MERMAID_NODES = 25            # nodes rendered in deterministic change diagram
MAX_REVIEW_FINDINGS = 50          # findings returned per review (deterministic first)
