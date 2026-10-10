import asyncio
import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import Response, StreamingResponse

from schemas.run import CreateRunRequest, RunResponse
from services.project_service import ProjectNotFoundError, ProjectService
from services.run_service import (
    RunNotFoundError,
    RunService,
    TestPatchUnavailableError,
    get_run_service,
)

router = APIRouter(prefix="/runs", tags=["runs"])


def get_project_service() -> ProjectService:
    return ProjectService()


@router.post("", response_model=RunResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_run(
    payload: CreateRunRequest,
    projects: ProjectService = Depends(get_project_service),
    runs: RunService = Depends(get_run_service),
) -> RunResponse:
    try:
        if payload.repository_url:
            project = projects.get_github_project(payload.repository_url)
        else:
            project = projects.get_project(payload.project_id or "")
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return await runs.create_run(project, payload)


@router.get("/{run_id}", response_model=RunResponse)
async def get_run(
    run_id: str,
    runs: RunService = Depends(get_run_service),
) -> RunResponse:
    try:
        return runs.get_run(run_id)
    except RunNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Run not found") from exc


@router.post("/{run_id}/cancel", response_model=RunResponse)
async def cancel_run(
    run_id: str,
    runs: RunService = Depends(get_run_service),
) -> RunResponse:
    try:
        return runs.cancel_run(run_id)
    except RunNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Run not found") from exc


@router.get("/{run_id}/diff")
async def get_run_diff(
    run_id: str,
    runs: RunService = Depends(get_run_service),
    projects: ProjectService = Depends(get_project_service),
) -> dict[str, str]:
    try:
        run = runs.get_run(run_id)
        project = None
        if run.repository_url is None and run.candidate_tests:
            try:
                project = projects.get_project(run.project_id)
            except ProjectNotFoundError:
                project = None
        diff = runs.get_test_patch(run_id, project)
    except RunNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Run or project not found") from exc
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Run or project not found") from exc
    except TestPatchUnavailableError as exc:
        raise HTTPException(status_code=409, detail="No generated test diff is available") from exc
    return {"run_id": run_id, "diff": diff}


@router.get("/{run_id}/patch")
async def download_run_patch(
    run_id: str,
    runs: RunService = Depends(get_run_service),
    projects: ProjectService = Depends(get_project_service),
) -> Response:
    try:
        run = runs.get_run(run_id)
        project = None
        if run.repository_url is None and run.candidate_tests:
            try:
                project = projects.get_project(run.project_id)
            except ProjectNotFoundError:
                project = None
        patch = runs.get_test_patch(run_id, project)
    except RunNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Run or project not found") from exc
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Run or project not found") from exc
    except TestPatchUnavailableError as exc:
        raise HTTPException(status_code=409, detail="No generated test patch is available") from exc
    return Response(
        content=patch,
        media_type="text/x-diff",
        headers={"Content-Disposition": f'attachment; filename="{run_id}.patch"'},
    )


@router.get("/{run_id}/events")
async def stream_run_events(
    run_id: str,
    request: Request,
    after: int = 0,
    runs: RunService = Depends(get_run_service),
) -> StreamingResponse:
    try:
        runs.get_run(run_id)
    except RunNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Run not found") from exc

    async def events() -> AsyncIterator[str]:
        cursor = after
        while not await request.is_disconnected():
            new_events = runs.get_events(run_id, after_event_id=cursor)
            for event in new_events:
                cursor = event.event_id
                body = json.dumps(event.model_dump(mode="json"))
                yield f"id: {event.event_id}\nevent: {event.type}\ndata: {body}\n\n"

            run = runs.get_run(run_id)
            if run.status in {"completed", "completed_with_warnings", "failed", "cancelled"}:
                break
            if not new_events:
                yield ": keep-alive\n\n"
            await asyncio.sleep(0.5)

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
