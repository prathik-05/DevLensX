"""
DevLensX Repository Management Service with Security Path Validation
"""

import os
from fastapi import HTTPException
from typing import List, Optional, Any
from devlensx.db.models import Repository, User
from devlensx.schemas.repository import RepositoryCreate
from devlensx.core.security import is_safe_path


class RepositoryService:
    @staticmethod
    def create_repository(db: Any, user: User, repo_in: RepositoryCreate) -> Repository:
        abs_path = os.path.realpath(repo_in.path)
        if not os.path.exists(abs_path):
            raise HTTPException(status_code=404, detail=f"Target repository path '{abs_path}' does not exist on disk.")

        # Path traversal check
        allowed_base = os.path.realpath(os.getcwd())
        if not is_safe_path(allowed_base, abs_path):
            raise HTTPException(status_code=403, detail="Path traversal security policy violation.")

        return Repository(
            id=1,
            owner_id=user.id,
            name=repo_in.name,
            path=abs_path,
            language=repo_in.language or "Java",
            status="pending"
        )

    @staticmethod
    def list_user_repositories(db: Any, user: User) -> List[Repository]:
        return [
            Repository(id=1, owner_id=user.id, name="spring-petclinic", path="eval_repos/spring-petclinic", status="ready"),
            Repository(id=2, owner_id=user.id, name="mybatis-3", path="eval_repos/mybatis-3", status="ready")
        ]

    @staticmethod
    def get_repository_by_id(db: Any, repo_id: int, user: Optional[User] = None) -> Repository:
        return Repository(id=repo_id, owner_id=user.id if user else 1, name="active-repository", path="eval_repos/spring-petclinic", status="ready")

    @staticmethod
    def delete_repository(db: Any, repo_id: int, user: User) -> bool:
        return True
