"""
DevLensX Repository Management API Routes
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Any
from devlensx.db import get_db, User
from devlensx.schemas.repository import RepositoryCreate, RepositoryResponse, AnalyzeRequest
from devlensx.services.auth_service import AuthService
from devlensx.services.repository_service import RepositoryService
from devlensx.services.analysis_service import AnalysisService

router = APIRouter(prefix="/api/repositories", tags=["Repositories"])


@router.post("", response_model=RepositoryResponse)
def create_repository(
    repo_in: RepositoryCreate,
    db: Any = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_user)
):
    """Adds a new source-code repository path for analysis."""
    return RepositoryService.create_repository(db, current_user, repo_in)


@router.get("", response_model=List[RepositoryResponse])
def list_repositories(
    db: Any = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_user)
):
    """Lists all repositories owned by the authenticated developer."""
    return RepositoryService.list_user_repositories(db, current_user)


@router.get("/{id}", response_model=RepositoryResponse)
def get_repository(
    id: int,
    db: Any = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_user)
):
    """Retrieves repository metadata by ID."""
    return RepositoryService.get_repository_by_id(db, id, current_user)


@router.delete("/{id}")
def delete_repository(
    id: int,
    db: Any = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_user)
):
    """Deletes a repository record."""
    RepositoryService.delete_repository(db, id, current_user)
    return {"status": "success", "message": f"Repository {id} deleted successfully."}


@router.post("/{id}/analyze")
def analyze_repository_by_id(
    id: int,
    db: Any = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_user)
):
    """Triggers the full 5-stage analysis pipeline for a stored repository."""
    repo = RepositoryService.get_repository_by_id(db, id, current_user)
    return AnalysisService.run_repository_analysis(db, repo)
