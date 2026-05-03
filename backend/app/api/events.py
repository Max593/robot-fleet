from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.event import RobotEventListResponse
from app.services.events import list_robot_event_page

router = APIRouter(tags=["events"])


@router.get("/robots/{robot_id}/events", response_model=RobotEventListResponse)
def get_robot_events(
    robot_id: str,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
    db: Session = Depends(get_db),
) -> RobotEventListResponse:
    events = list_robot_event_page(db, robot_id, page=page, page_size=page_size)
    if events is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Robot not found")
    return events
