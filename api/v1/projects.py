from fastapi import APIRouter, Depends

from schemas.project import ProjectListResponse
from services.project_service import ProjectService

router = APIRouter(prefix="/projects", tags=["projects"])


def get_project_service() -> ProjectService:
    return ProjectService()


@router.get("", response_model=ProjectListResponse)
async def list_projects(
    service: ProjectService = Depends(get_project_service),
) -> ProjectListResponse:
    return service.list_projects()
