from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.models.schema import Seat, Booking, Customer

router = APIRouter()

@router.get("/barber/{barber_id}")
def get_barber_seats(barber_id: str, db: Session = Depends(get_db)):
    try:
        barber_seats = (
            db.query(Seat)
            .filter(Seat.barber_id == barber_id)
            .order_by(Seat.is_occupied.desc(), Seat.seat_number.asc())
            .all()
        )

        if not barber_seats:
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "data": None,
                    "error": "No seats found for this barber"
                }
            )

        data = [
            {
                "id": seat.id,
                "bookingId": getattr(seat, 'current_booking_id', None),
                "seatNumber": seat.seat_number,
                "isOccupied": seat.is_occupied
            }
            for seat in barber_seats
        ]

        return {
            "success": True,
            "data": data,
            "message": "Seats retrieved successfully"
        }

    except Exception as e:
        print(f"GET_BARBER_SEATS ERROR: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "data": None,
                "error": "Internal server error"
            }
        )