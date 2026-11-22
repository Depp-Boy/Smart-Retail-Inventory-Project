from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.location import Location
from app.repositories.location_repository import LocationRepository
from app.schemas.location import LocationCreate, LocationUpdate

VALID_LOCATION_TYPES = {"MAIN_WAREHOUSE", "SUB_WAREHOUSE", "SHOP"}


class LocationService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = LocationRepository(db)

    def create(self, req: LocationCreate) -> Location:
        loc_type = req.location_type.upper()
        if loc_type not in VALID_LOCATION_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid location_type '{req.location_type}'. Supported: {', '.join(sorted(VALID_LOCATION_TYPES))}",
            )

        if req.parent_location_id:
            parent = self.repo.get_by_id(req.parent_location_id)
            if not parent:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Parent location ID {req.parent_location_id} does not exist.",
                )

        loc = Location(
            location_name=req.location_name.strip(),
            location_type=loc_type,
            address=req.address.strip(),
            parent_location_id=req.parent_location_id,
        )
        return self.repo.create(loc)

    def get_by_id(self, location_id: int) -> Location:
        loc = self.repo.get_by_id(location_id)
        if not loc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Location with ID {location_id} not found.",
            )
        return loc

    def list(self, location_type: Optional[str] = None, search: Optional[str] = None, skip: int = 0, limit: int = 50) -> List[Location]:
        return self.repo.list(location_type=location_type, search=search, skip=skip, limit=limit)

    def update(self, location_id: int, req: LocationUpdate) -> Location:
        loc = self.get_by_id(location_id)
        if req.location_type:
            loc_type = req.location_type.upper()
            if loc_type not in VALID_LOCATION_TYPES:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid location_type '{req.location_type}'.",
                )
            loc.location_type = loc_type
        if req.location_name is not None:
            loc.location_name = req.location_name.strip()
        if req.address is not None:
            loc.address = req.address.strip()
        if req.parent_location_id is not None:
            if req.parent_location_id == location_id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Location cannot be its own parent.")
            parent = self.repo.get_by_id(req.parent_location_id)
            if not parent:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Parent location not found.")
            loc.parent_location_id = req.parent_location_id
        return self.repo.update(loc)
