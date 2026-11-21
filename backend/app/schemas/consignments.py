from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import Literal, Optional


CommodityType = Literal[
    "Food Supplies",
    "Medicine",
    "Fuel",
    "Emergency Kits",
    "General Cargo",
]

LifecycleStatus = Literal[
    "Dispatched",
    "In Transit",
    "Delayed due to Risk",
    "Delivered",
]


class ConsignmentBase(BaseModel):
    commodity_type: str = Field(..., description="Type of essential commodity (Food Supplies, Medicine, Fuel, Emergency Kits)")
    quantity: str = Field(..., description="Quantity with units, e.g. '500 Bags', '1000 Liters'")
    origin: str = Field(..., description="Dispatch location name or facility")
    destination: str = Field(..., description="Drop-off point or relief camp")
    assigned_vehicle_id: Optional[str] = Field(None, description="Assigned vehicle identifier (e.g. V001)")
    route_id: Optional[str] = Field(None, description="Assigned route identifier")
    lifecycle_status: LifecycleStatus = Field(default="Dispatched", description="Lifecycle progress")
    current_lat: Optional[float] = None
    current_lng: Optional[float] = None
    risk_score: Optional[int] = Field(None, ge=0, le=100)
    eta_minutes: Optional[float] = None
    notes: Optional[str] = None


class ConsignmentCreate(ConsignmentBase):
    shipment_id: Optional[str] = Field(None, description="Custom shipment ID, generated if omitted")


class ConsignmentUpdate(BaseModel):
    lifecycle_status: Optional[LifecycleStatus] = None
    assigned_vehicle_id: Optional[str] = None
    route_id: Optional[str] = None
    current_lat: Optional[float] = None
    current_lng: Optional[float] = None
    risk_score: Optional[int] = None
    eta_minutes: Optional[float] = None
    notes: Optional[str] = None


class Consignment(ConsignmentBase):
    model_config = ConfigDict(from_attributes=True)

    shipment_id: str
    created_at: datetime
    updated_at: datetime
