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

@router.get("/{seat_id}")
def get_seat_details(seat_id: str, db: Session = Depends(get_db)):
    try:
        result = (
            db.query(Seat)
            .filter(Seat.id == seat_id)
            .outerjoin(Booking, Seat.current_booking_id == Booking.id)
            .outerjoin(Customer, Booking.customer_id == Customer.id)
            .first()
        )

        if not result:
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "data": None,
                    "error": "Seat not found"
                }
            )

        booking_data = None
        customer_data = None

        if hasattr(result, 'booking') and result.booking:
            booking_data = {
                "id": result.booking.id,
                "service": result.booking.service,
                "price": result.booking.price,
                "slot": result.booking.slot,
                "status": result.booking.status,
                "note": result.booking.note,
            }
            if hasattr(result.booking, 'customer') and result.booking.customer:
                customer_data = {
                    "id": result.booking.customer.id,
                    "name": result.booking.customer.name,
                    "email": result.booking.customer.email,
                    "phoneNumber": result.booking.customer.phone_number,
                }

        response_data = {
            "seat": {
                "id": result.id,
                "seatNumber": result.seat_number,
                "isOccupied": result.is_occupied,
                "barberId": result.barber_id,
            },
            "booking": booking_data,
            "customer": customer_data
        }

        return {
            "success": True,
            "data": response_data
        }

    except Exception as e:
        print(f"GET_SEAT_DETAILS ERROR: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "data": None,
                "error": "Internal server error"
            }
        )