from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.schemas.consignments import (
    Consignment,
    ConsignmentCreate,
    ConsignmentUpdate,
)
from backend.app.services.consignment_service import consignment_service

router = APIRouter()


@router.get(
    "/",
    response_model=List[Consignment],
    summary="List all tracked consignments",
)
def list_consignments(
    status: Optional[str] = Query(None, description="Filter by lifecycle status"),
    commodity: Optional[str] = Query(None, description="Filter by commodity type"),
    vehicle_id: Optional[str] = Query(None, description="Filter by assigned vehicle"),
    session: Session = Depends(get_db),
):
    return consignment_service.list(
        session, status=status, commodity=commodity, vehicle_id=vehicle_id
    )


@router.post(
    "/",
    response_model=Consignment,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new commodity shipment consignment",
)
def create_consignment(
    payload: ConsignmentCreate,
    session: Session = Depends(get_db),
):
    return consignment_service.create(session, payload)


@router.get(
    "/{shipment_id}",
    response_model=Consignment,
    summary="Get consignment details by shipment ID",
)
def get_consignment(
    shipment_id: str,
    session: Session = Depends(get_db),
):
    consignment = consignment_service.get(session, shipment_id)
    if not consignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Consignment '{shipment_id}' not found",
        )
    return consignment


@router.patch(
    "/{shipment_id}",
    response_model=Consignment,
    summary="Update consignment lifecycle status or assignment",
)
def update_consignment(
    shipment_id: str,
    payload: ConsignmentUpdate,
    session: Session = Depends(get_db),
):
    consignment = consignment_service.update(session, shipment_id, payload)
    if not consignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Consignment '{shipment_id}' not found",
        )
    return consignment
