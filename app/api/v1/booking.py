import uuid
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
from sqlalchemy import desc, and_, func
from fastapi.responses import JSONResponse
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from fastapi import APIRouter, Depends, Query, Path, Body, BackgroundTasks

from app.database.db import get_db
from app.models.schema import Booking, Barber, Customer, Seat, BookingStatus
from app.utils.mail import (
    send_booking_confirmation_mail,
    send_booking_cancellation_mail,
    send_booking_cancellation_with_penalty_mail
)

router = APIRouter()
IST = ZoneInfo("Asia/Kolkata")

@router.get("")
def get_bookings(
    customerId: Optional[str] = Query(None),
    barberId: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    try:
        if not customerId and not barberId:
            return JSONResponse(status_code=400, content={"success": False, "error": "Missing identity filter"})

        query = db.query(
            Booking.id,
            Booking.slot,
            Booking.service,
            Booking.price,
            Booking.status,
            Booking.note,
            Booking.is_penalized,
            Booking.created_at,
            Booking.seat_number,
            Barber.id.label("barber_id"),
            Barber.name.label("barber_name"),
            Barber.shop_name.label("barber_shopName"),
            Barber.address.label("barber_address"),
            Barber.profile_pic.label("barber_profilePic"),
            Customer.id.label("customer_id"),
            Customer.name.label("customer_name"),
            Customer.phone_number.label("customer_phoneNumber"),
            Customer.profile_pic.label("customer_profilePic")
        ).join(Barber, Booking.barber_id == Barber.id)\
         .join(Customer, Booking.customer_id == Customer.id)

        if customerId:
            query = query.filter(Booking.customer_id == customerId)
        else:
            query = query.filter(Booking.barber_id == barberId)

        results = query.order_by(desc(Booking.slot)).all()

        formatted_data = []
        for r in results:
            formatted_data.append({
                "id": r.id,
                "slot": r.slot,
                "service": r.service,
                "price": r.price,
                "status": r.status,
                "note": r.note,
                "isPenalized": r.is_penalized,
                "createdAt": r.created_at,
                "seatNumber": r.seat_number,
                "barber": {
                    "id": r.barber_id,
                    "name": r.barber_name,
                    "shopName": r.barber_shopName,
                    "address": r.barber_address,
                    "profilePic": r.barber_profilePic
                },
                "customer": {
                    "id": r.customer_id,
                    "name": r.customer_name,
                    "phoneNumber": r.customer_phoneNumber,
                    "profilePic": r.customer_profilePic
                }
            })

        return {"success": True, "data": formatted_data}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})

@router.post("")
def create_booking(
    background_tasks: BackgroundTasks,
    body: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db)
):
    try:
        barber_id = body.get("barberId")
        seat_number = body.get("seatNumber")
        
        with db.begin_nested():
            seat = db.query(Seat).filter(
                and_(Seat.barber_id == barber_id, Seat.seat_number == seat_number)
            ).with_for_update().first()

            if not seat:
                return JSONResponse(status_code=404, content={"success": False, "error": "Seat does not exist"})
            
            if seat.is_occupied:
                return JSONResponse(status_code=409, content={"success": False, "error": "Seat is already occupied"})

            booking_id = str(uuid.uuid4())
            
            slot_str = body.get("slot")
            if "Z" in slot_str:
                utc_dt = datetime.fromisoformat(slot_str.replace("Z", "+00:00"))
                dt_obj = utc_dt.astimezone(IST).replace(tzinfo=None)
            else:
                if "T" in slot_str:
                    dt_obj = datetime.strptime(slot_str.split(".")[0], "%Y-%m-%dT%H:%M:%S")
                else:
                    dt_obj = datetime.strptime(slot_str, "%Y-%m-%d %H:%M:%S")

            new_booking = Booking(
                id=booking_id,
                customer_id=body.get("customerId"),
                barber_id=barber_id,
                service=body.get("service"),
                price="{:.2f}".format(float(body.get("price"))),
                slot=dt_obj,
                note=body.get("note", ""),
                status=BookingStatus.confirmed, 
                seat_number=seat_number,
                is_penalized=False,
                created_at=datetime.now(IST).replace(tzinfo=None),
                updated_at=datetime.now(IST).replace(tzinfo=None)
            )

            db.add(new_booking)
            
            seat.is_occupied = True
            seat.current_booking_id = booking_id

        db.commit()
        print("1")        
        background_tasks.add_task(send_booking_confirmation_mail, booking_id, db)
        print("8")        

        return {"success": True, "data": {"id": booking_id, "status": BookingStatus.confirmed}}
    except Exception as e:
        db.rollback()
        return JSONResponse(status_code=400, content={"success": False, "error": str(e)})

@router.patch("/{id}")
def update_booking(
    background_tasks: BackgroundTasks,
    id: str = Path(...),
    body: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db)
):
    try:
        booking = db.query(Booking).filter(Booking.id == id).first()
        if not booking:
            return JSONResponse(status_code=404, content={"success": False, "error": "Booking record not found"})

        raw_status = body.get("status")
        new_status = BookingStatus(raw_status) if raw_status else None
        
        is_cancelling = new_status == BookingStatus.canceled and booking.status != BookingStatus.canceled
        is_finishing = new_status in [BookingStatus.completed, BookingStatus.auto_completed] and \
                      booking.status not in [BookingStatus.completed, BookingStatus.auto_completed]

        if is_cancelling:
            now = datetime.now(IST).replace(tzinfo=None)
            slot_time = booking.slot
            time_diff = slot_time - now
            
            if timedelta(hours=0) < time_diff < timedelta(hours=2):
                booking.is_penalized = True
                fine = float(booking.price) * 0.20
                db.query(Customer).filter(Customer.id == booking.customer_id).update({
                    "penalty": Customer.penalty + fine
                })
                background_tasks.add_task(send_booking_cancellation_with_penalty_mail, id, db)
            else:
                background_tasks.add_task(send_booking_cancellation_mail, id, db)

        if body.get("note") is not None: booking.note = body["note"]
        if new_status: booking.status = new_status
        if body.get("slot"): 
            slot_str = body["slot"]
            if "Z" in slot_str:
                utc_dt = datetime.fromisoformat(slot_str.replace("Z", "+00:00"))
                booking.slot = utc_dt.astimezone(IST).replace(tzinfo=None)
            else:
                if "T" in slot_str:
                    booking.slot = datetime.strptime(slot_str.split(".")[0], "%Y-%m-%dT%H:%M:%S")
                else:
                    booking.slot = datetime.strptime(slot_str, "%Y-%m-%d %H:%M:%S")
        
        if is_finishing: booking.completed_at = datetime.now(IST).replace(tzinfo=None)
        
        booking.updated_at = datetime.now(IST).replace(tzinfo=None)

        if is_cancelling or is_finishing:
            db.query(Seat).filter(Seat.current_booking_id == id).update({
                "is_occupied": False,
                "current_booking_id": None
            })

        db.commit()
        return {"success": True, "data": {"id": id, "status": booking.status}}
    except Exception as e:
        db.rollback()
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})

@router.delete("/{id}")
def delete_booking(id: str = Path(...), db: Session = Depends(get_db)):
    try:
        booking = db.query(Booking).filter(Booking.id == id).first()
        if not booking:
            return JSONResponse(status_code=404, content={"success": False, "error": "Booking not found"})

        if booking.status == BookingStatus.confirmed:
            db.query(Seat).filter(Seat.current_booking_id == id).update({
                "is_occupied": False,
                "current_booking_id": None
            })

        db.delete(booking)
        db.commit()
        return {"success": True, "data": {"id": id, "message": "Booking deleted"}}
    except Exception:
        db.rollback()
        return JSONResponse(status_code=500, content={"success": False, "error": "Internal Server Error"})