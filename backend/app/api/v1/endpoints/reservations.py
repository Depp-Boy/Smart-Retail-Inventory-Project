from typing import List
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.core.dependencies import get_current_user, require_roles
from app.database.session import get_db
from app.models.user import User
from app.schemas.reservation import ReservationCreateRequest, ReservationResponse
from app.services.reservation_service import ReservationService

router = APIRouter()


@router.get("/", response_model=List[ReservationResponse], summary="List Active Reservations")
def list_active_reservations(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(require_roles("ADMIN", "WAREHOUSE_MANAGER")),
    db: Session = Depends(get_db),
):
    service = ReservationService(db)
    return service.list_active(skip=skip, limit=limit)


@router.post("/", response_model=ReservationResponse, status_code=status.HTTP_201_CREATED, summary="Create Stock Reservation")
def create_reservation(
    req: ReservationCreateRequest,
    current_user: User = Depends(require_roles("ADMIN", "WAREHOUSE_MANAGER")),
    db: Session = Depends(get_db),
):
    service = ReservationService(db)
    return service.create_reservation(req, actor=current_user)


@router.post("/{reservation_id}/release", response_model=ReservationResponse, summary="Release Reservation")
def release_reservation(
    reservation_id: int,
    current_user: User = Depends(require_roles("ADMIN", "WAREHOUSE_MANAGER")),
    db: Session = Depends(get_db),
):
    service = ReservationService(db)
    return service.release_reservation(reservation_id, actor=current_user)


@router.post("/{reservation_id}/confirm", response_model=ReservationResponse, summary="Confirm Reservation")
def confirm_reservation(
    reservation_id: int,
    current_user: User = Depends(require_roles("ADMIN", "WAREHOUSE_MANAGER")),
    db: Session = Depends(get_db),
):
    service = ReservationService(db)
    return service.confirm_reservation(reservation_id)


@router.get("/allocation/{allocation_id}", response_model=List[ReservationResponse], summary="List Reservations by Allocation")
def list_reservations_by_allocation(
    allocation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = ReservationService(db)
    return service.list_by_allocation(allocation_id)
