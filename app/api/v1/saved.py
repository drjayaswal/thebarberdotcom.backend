from sqlalchemy import and_
from app.database.db import get_db
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, status
from app.models.schema import SavedBarber, Barber

router = APIRouter()

@router.post("", status_code=status.HTTP_200_OK)
async def toggle_save_barber(data: SavedBarber, session: Session = Depends(get_db)):
    existing = session.query(SavedBarber).filter(
        and_(
            SavedBarber.customer_id == data.customer_id,
            SavedBarber.barber_id == data.barber_id
        )
    ).first()
    
    if existing:
        session.delete(existing)
        session.commit()
        return {"success": True, "message": "Barber Removed!"}
    
    new_save = SavedBarber(
        customer_id=data.customer_id,
        barber_id=data.barber_id
    )
    session.add(new_save)
    session.commit()
    return {"success": True, "message": "Barber Saved!"}

@router.get("/{customer_id}")
async def get_saved_barbers(customer_id: str, db: Session = Depends(get_db)):
    results = db.query(Barber).join(
        SavedBarber, Barber.id == SavedBarber.barber_id
    ).filter(
        SavedBarber.customer_id == customer_id
    ).all()
    
    return {"success": True, "data": results}