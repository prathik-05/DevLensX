"""Thin FastAPI router wrapper for CodeRabbit engine (Code Turtle-compatible)."""
from devlensx.codereview import create_review_router

router = create_review_router()
