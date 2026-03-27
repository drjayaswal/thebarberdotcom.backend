from sqlalchemy.orm import Session
from app.database.db import get_db
from typing import Dict, Any, Optional
from fastapi.responses import JSONResponse
from geoalchemy2 import Geometry, Geography
from sqlalchemy import Numeric, cast, func
from app.models.schema import Barber, Seat
from app.api.v1.auth import get_current_user
from sqlalchemy import func, or_, and_, cast, Numeric
from fastapi import APIRouter, Depends, Query, Path, Body
from sqlalchemy import or_, and_, cast, Numeric, func, select, column

router = APIRouter()
@router.get("")
async def get_barbers(
    lat: Optional[float] = Query(None),
    long: Optional[float] = Query(None),
    radius: float = Query(10),
    searchQuery: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    radius_in_meters = radius * 1000
    try:
        has_coords = lat is not None and long is not None
        
        if has_coords:
            user_point = func.ST_SetSRID(func.ST_Point(long, lat), 4326)
            distance_col = func.round(
                cast(
                    func.ST_Distance(
                        cast(Barber.location, Geography),
                        cast(user_point, Geography)
                    ),
                    Numeric
                ), 0
            ).label("distance")
        else:
            distance_col = func.lit(0).label("distance")

        query = db.query(
            Barber,
            func.ST_Y(cast(Barber.location, Geometry)).label("lat"),
            func.ST_X(cast(Barber.location, Geometry)).label("long"),
            distance_col
        )

        conditions = []
        
        if has_coords:
            user_point = func.ST_SetSRID(func.ST_Point(long, lat), 4326)
            conditions.append(
                func.ST_DWithin(
                    cast(Barber.location, Geography),
                    cast(user_point, Geography),
                    radius_in_meters
                )
            )
        if searchQuery and searchQuery.strip():
            pattern = f"%{searchQuery}%"
            service_alias = func.jsonb_array_elements(Barber.services).alias("service_item")
            json_search = select(1).select_from(service_alias).where(
                column("service_item").op("->>")("name").ilike(pattern)
            ).correlate(Barber).exists()

            conditions.append(
                or_(
                    Barber.shop_name.ilike(pattern),
                    Barber.name.ilike(pattern),
                    Barber.address.ilike(pattern),
                    json_search
                )
            )

        if conditions:
            query = query.filter(and_(*conditions))
        if has_coords:
            query = query.order_by("distance")
        else:
            query = query.order_by(Barber.shop_name)

        results = query.all()
        
        if not results:
            return {"success": True, "data": []}

        barber_ids = [r.Barber.id for r in results]
        all_seats = db.query(Seat).filter(Seat.barber_id.in_(barber_ids)).all()

        data_with_seats = []
        for r in results:
            barber_data = {
                "id": r.Barber.id,
                "name": r.Barber.name,
                "shopName": r.Barber.shop_name,
                "address": r.Barber.address,
                "phoneNumber": r.Barber.phone_number,
                "rating": r.Barber.rating,
                "profilePic": r.Barber.profile_pic,
                "services": r.Barber.services,
                "shop_images": r.Barber.shop_images,
                "totalSeats": r.Barber.total_seats,
                "lat": r.lat,
                "long": r.long,
                "distance": float(r.distance),
                "seats": [
                    {
                        "id": s.id,
                        "seatNumber": s.seat_number,
                        "isOccupied": s.is_occupied,
                        "bookingId": s.current_booking_id
                    } for s in all_seats if s.barber_id == r.Barber.id
                ]
            }
            data_with_seats.append(barber_data)

        return {"success": True, "data": data_with_seats}

    except Exception as e:
        print(f"Error in get_barbers: {e}")
        return JSONResponse(
            status_code=500, 
            content={"success": False, "error": "Internal Server Error"}
        )

@router.get("/{id}")
def get_barber_by_id(id: str = Path(...), db: Session = Depends(get_db)):
    try:
        barber_seats = db.query(Seat).filter(Seat.barber_id == id).all()
        
        result = db.query(
            Barber,
            func.ST_Y(cast(Barber.location, Geometry)).label("lat"),
            func.ST_X(cast(Barber.location, Geometry)).label("long")
        ).filter(Barber.id == id).first()

        if not result:
            return JSONResponse(status_code=404, content={"success": False, "error": "Barber not found"})

        barber = result.Barber
        return {
            "success": True,
            "data": {
                "id": barber.id,
                "name": barber.name,
                "shopName": barber.shop_name,
                "address": barber.address,
                "rating": barber.rating,
                "profilePic": barber.profile_pic,
                "phoneNumber": barber.phone_number,
                "services": barber.services,
                "timings": barber.timings,
                "totalSeats": barber.total_seats,
                "lat": result.lat,
                "long": result.long,
                "seats": [
                    {
                        "id": s.id,
                        "seatNumber": s.seat_number,
                        "isOccupied": s.is_occupied,
                        "bookingId": s.current_booking_id
                    } for s in barber_seats
                ]
            }
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})

@router.patch("/{id}")
def update_barber(
    id: str = Path(...),
    body: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    user: Any = Depends(get_current_user)
):
    try:
        barber = db.query(Barber).filter(Barber.id == id).first()
        if not barber:
            return JSONResponse(status_code=404, content={"success": False, "error": "Barber not found"})

        if body.get("name"): barber.name = body["name"]
        if body.get("shopName"): barber.shop_name = body["shopName"]
        if body.get("address"): barber.address = body["address"]
        if body.get("profilePic"): barber.profile_pic = body["profilePic"]
        if body.get("phoneNumber"): barber.phone_number = body["phoneNumber"]
        if body.get("services"): barber.services = body["services"]
        if body.get("timings"): barber.timings = body["timings"]

        if body.get("lat") is not None and body.get("long") is not None:
            point = f"POINT({body['long']} {body['lat']})"
            barber.location = func.ST_SetSRID(func.ST_GeomFromText(point), 4326)

        db.commit()
        db.refresh(barber)

        return {"success": True, "data": {"id": barber.id, "name": barber.name}}
    except Exception as e:
        db.rollback()
        return JSONResponse(status_code=500, content={"success": False, "error": "System fault during update"})

@router.delete("/{id}")
def delete_barber(
    id: str = Path(...),
    db: Session = Depends(get_db),
    user: Any = Depends(get_current_user)
):
    try:
        barber = db.query(Barber).filter(Barber.id == id).first()
        if not barber:
            return JSONResponse(status_code=404, content={"success": False, "error": "Barber not found"})

        db.delete(barber)
        db.commit()
        return {"success": True, "data": {"message": "Account deleted"}}
    except Exception as e:
        db.rollback()
        return JSONResponse(status_code=500, content={"success": False, "error": "Deletion failed"})