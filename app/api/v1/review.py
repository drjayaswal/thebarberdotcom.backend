import uuid
from typing import Dict, Any
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Body, Query, Path
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.database.db import get_db
from app.models.schema import Review, Barber, Booking, Customer
from app.api.v1.auth import get_current_user

router = APIRouter()

def recalc_barber_rating(barber_id: str, db: Session):
    stats = db.query(
        func.avg(Review.rating).label("average"),
        func.count(Review.id).label("total")
    ).filter(Review.barber_id == barber_id).first()

    avg_rating = "0.00"
    if stats and stats.average is not None:
        avg_rating = "{:.2f}".format(float(stats.average))

    db.query(Barber).filter(Barber.id == barber_id).update({
        "rating": avg_rating,
        "total_reviews": stats.total if stats else 0
    })
    db.commit()

@router.post("")
def create_review(
    body: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    user: Any = Depends(get_current_user)
):
    try:
        booking_id = body.get("bookingId")
        rating = body.get("rating")
        comment = body.get("comment")
        customer_id = body.get("customerId")

        if not user or user.get("sub") != customer_id:
            return JSONResponse(status_code=403, content={"success": False, "error": "Unauthorized"})

        booking = db.query(Booking).filter(Booking.id == booking_id).first()
        if not booking:
            return JSONResponse(status_code=404, content={"success": False, "error": "Booking not found"})

        if booking.customer_id != customer_id:
            return JSONResponse(status_code=403, content={"success": False, "error": "Unauthorized"})

        if booking.status not in ["completed", "auto"]:
            return JSONResponse(status_code=400, content={"success": False, "error": "Can only review completed bookings"})

        existing = db.query(Review).filter(Review.booking_id == booking_id).first()
        if existing:
            return JSONResponse(status_code=409, content={"success": False, "error": "Review already submitted"})

        new_review = Review(
            id=str(uuid.uuid4()),
            customer_id=customer_id,
            barber_id=booking.barber_id,
            booking_id=booking_id,
            rating=int(rating),
            comment=comment,
            created_at=datetime.now(timezone.utc)
        )
        
        db.add(new_review)
        db.commit()
        db.refresh(new_review)

        recalc_barber_rating(booking.barber_id, db)

        return {"success": True, "data": {"id": new_review.id, "rating": new_review.rating}}

    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})

@router.get("/barber/{barberId}")
def get_barber_reviews(
    barberId: str = Path(...),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1),
    db: Session = Depends(get_db)
):
    try:
        offset = (page - 1) * limit
        
        results = db.query(
            Review.id,
            Review.rating,
            Review.comment,
            Review.created_at,
            Customer.name.label("customerName")
        ).join(Customer, Review.customer_id == Customer.id)\
         .filter(Review.barber_id == barberId)\
         .order_by(desc(Review.created_at))\
         .offset(offset).limit(limit).all()

        stats = db.query(
            func.avg(Review.rating).label("avg"),
            func.count(Review.id).label("total")
        ).filter(Review.barber_id == barberId).first()

        return {
            "success": True,
            "data": {
                "reviews": [dict(r._asdict()) for r in results],
                "stats": {
                    "average": round(float(stats.avg), 2) if stats.avg else 0,
                    "total": stats.total or 0
                }
            }
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})

@router.get("/booking/{bookingId}")
def get_booking_review(bookingId: str = Path(...), db: Session = Depends(get_db)):
    try:
        review = db.query(Review).filter(Review.booking_id == bookingId).first()
        return {"success": True, "data": review}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})

@router.patch("/{id}")
def update_review(
    id: str = Path(...),
    body: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    user: Any = Depends(get_current_user)
):
    try:
        review = db.query(Review).filter(Review.id == id).first()
        if not review:
            return JSONResponse(status_code=404, content={"success": False, "error": "Review not found"})

        if not user or user.get("sub") != review.customer_id:
            return JSONResponse(status_code=403, content={"success": False, "error": "Unauthorized"})

        if "rating" in body:
            review.rating = body["rating"]
        if "comment" in body:
            review.comment = body["comment"]
        
        review.updated_at = datetime.now(timezone.utc)
        db.commit()

        recalc_barber_rating(review.barber_id, db)
        return {"success": True, "data": {"id": review.id}}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})

@router.delete("/{id}")
def delete_review(
    id: str = Path(...),
    db: Session = Depends(get_db),
    user: Any = Depends(get_current_user)
):
    try:
        review = db.query(Review).filter(Review.id == id).first()
        if not review:
            return JSONResponse(status_code=404, content={"success": False, "error": "Review not found"})

        if not user or user.get("sub") != review.customer_id:
            return JSONResponse(status_code=403, content={"success": False, "error": "Unauthorized"})

        barber_id = review.barber_id
        db.delete(review)
        db.commit()

        recalc_barber_rating(barber_id, db)
        return {"success": True, "data": {"message": "Review deleted"}}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})