import uuid
from typing import Dict, Any
from pydantic import BaseModel
from app.database.db import get_db
from sqlalchemy.orm import Session
from fastapi.responses import JSONResponse
from geoalchemy2.elements import WKTElement
from fastapi import APIRouter, Depends, Body, BackgroundTasks
from app.models.schema import Customer, Barber, Seat
from app.utils.mail import send_forgot_password_mail
from app.core.security import get_password_hash, verify_password, create_access_token,get_current_user

class ResetPasswordRequest(BaseModel):
    token: str
    newPassword: str

router = APIRouter()

@router.post("/signup")
def signup(body: Dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    role = body.get("role")
    email = body.get("email")
    password = body.get("password")
    hashed_password = get_password_hash(password)
    
    try:
        if role == "customer":
            new_user = Customer(
                id=str(uuid.uuid4()),
                name=body.get("name"),
                email=email,
                password=hashed_password,
                phone_number=body.get("phone_number")
            )
            db.add(new_user)
            db.commit()
            return {
                "success": True,
                "data": {"customer": {"id": new_user.id, "name": new_user.name}},
                "message": "Signup successful"
            }
        
        else:
            loc = body.get("location", {"x": 0, "y": 0})
            point = f"POINT({loc.get('x', 0)} {loc.get('y', 0)})"
            
            new_barber = Barber(
                id=str(uuid.uuid4()),
                name=body.get("name"),
                email=email,
                password=hashed_password,
                phone_number=body.get("phone_number"),
                shop_name=body.get("shop_name", ""),
                address=body.get("address", ""),
                location=WKTElement(point, srid=4326),
                timings=body.get("timings", {"open": "09:00", "close": "21:00"}),
                services=body.get("services", []),
                total_seats=int(body.get("total_seats", 1))
            )
            db.add(new_barber)
            db.flush()

            for i in range(new_barber.total_seats):
                seat = Seat(
                    id=str(uuid.uuid4()),
                    barber_id=new_barber.id,
                    seat_number=i + 1,
                    is_occupied=False
                )
                db.add(seat)
            
            db.commit()
            return {
                "success": True,
                "data": {"barber": {"id": new_barber.id, "shopName": new_barber.shop_name}},
                "message": "Signup successful"
            }

    except Exception as e:
        db.rollback()
        error_msg = str(e)
        status_code = 400 if "unique constraint" in error_msg.lower() else 500
        display_error = "Email already registered" if status_code == 400 else f"Server Error: {error_msg}"
        
        return JSONResponse(
            status_code=status_code,
            content={
                "success": False,
                "data": None,
                "error": display_error
            }
        )

@router.post("/signin")
def signin(body: Dict[str, str] = Body(...), db: Session = Depends(get_db)):
    email = body.get("email")
    password = body.get("password")

    try:
        account = db.query(Customer).filter(Customer.email == email).first()
        role = "customer"

        if not account:
            account = db.query(Barber).filter(Barber.email == email).first()
            role = "barber"

        if not account or not verify_password(password, account.password):
            return JSONResponse(
                status_code=401,
                content={
                    "success": False,
                    "data": None,
                    "error": "Invalid email or password"
                }
            )

        token = create_access_token(account.id, role)
        
        if role == "customer":
            account.access_token = token
            db.commit()

        return {
            "success": True,
            "data": {
                "token": token,
                "account": {
                    "role": role,
                    "id": str(account.id),
                    "name": account.name,
                    "email": account.email
                }
            },
            "message": "Login successful"
        }

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "data": None,
                "error": f"Internal Server Error: {str(e)}"
            }
        )

@router.get("/profile")
def get_profile(user: Any = Depends(get_current_user), db: Session = Depends(get_db)):
    if not user or "sub" not in user:
        return JSONResponse(status_code=401, content={"success": False, "error": "Unauthorized"})
    try:
        user_id = user.get("sub")
        role = user.get("role")

        if role == "customer":
            customer = db.query(Customer).filter(Customer.id == user_id).first()
            if not customer:
                return JSONResponse(status_code=404, content={"success": False, "error": "Customer not found"})
            
            return {
                "success": True,
                "data": {
                    "id": customer.id,
                    "name": customer.name,
                    "email": customer.email,
                    "phoneNumber": customer.phone_number,
                    "profilePic": getattr(customer, 'profile_pic', None),
                    "penalty": getattr(customer, 'penalty', 0),
                    "role": "customer"
                }
            }
        else:
            barber = db.query(Barber).filter(Barber.id == user_id).first()
            if not barber:
                return JSONResponse(status_code=404, content={"success": False, "error": "Barber not found"})
            
            return {
                "success": True,
                "data": {
                    "id": barber.id,
                    "name": barber.name,
                    "email": barber.email,
                    "phoneNumber": barber.phone_number,
                    "shopName": barber.shop_name,
                    "address": barber.address,
                    "shop_images": barber.shop_images,
                    "profilePic": getattr(barber, 'profile_pic', None),
                    "role": "barber"
                }
            }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": f"Internal Server Error: {str(e)}"}
        )

@router.patch("/update")
def update_profile(
    id: str, 
    body: Dict[str, Any] = Body(...), 
    db: Session = Depends(get_db),
):
    role = body.get("role")
    
    if role == "customer":
        user = db.query(Customer).filter(Customer.id == id).first()
    else:
        user = db.query(Barber).filter(Barber.id == id).first()

    if not user:
        return JSONResponse(status_code=404, content={"success": False, "error": "User not found"})

    if "name" in body: user.name = body["name"]
    if "phoneNumber" in body: user.phone_number = body["phoneNumber"]
    if "profilePic" in body: user.profile_pic = body["profilePic"]
    
    if role == "barber" and "shop_images" in body:
        user.shop_images = body["shop_images"]

    try:
        db.commit()
        db.refresh(user)
        
        return {
            "success": True,
            "data": {
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "phoneNumber": user.phone_number,
                "profilePic": getattr(user, 'profile_pic', None),
                "role": role,
                "shop_images": getattr(user, 'shop_images', []) if role == "barber" else None,
                "penalty": getattr(user, 'penalty', 0) if role == "customer" else None
            }
        }
    except Exception as e:
        db.rollback()
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})

@router.post("/forgot-password")
def forgot_password(
    background_tasks: BackgroundTasks,
    body: Dict[str, Any] = Body(...), 
    db: Session = Depends(get_db)
):
    email = body.get("email")
    if not email:
        return JSONResponse(status_code=400, content={"success": False, "error": "Email is required"})

    user = db.query(Customer).filter(Customer.email == email).first()
    role = "customer"
    
    if not user:
        user = db.query(Barber).filter(Barber.email == email).first()
        role = "barber"
        
    if not user:
        return JSONResponse(status_code=404, content={"success": False, "error": "User with this email does not exist"})

    token = create_access_token(user.id, role)

    user.reset_token = token
    db.commit()

    background_tasks.add_task(send_forgot_password_mail, user.id, token, next(get_db()))
    
    return {
        "success": True,
        "message": "Password reset instructions have been sent to your email."
    }

@router.post("/verify-reset-token")
def verify_reset_token(
    body: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db)
):
    token = body.get("token")
    if not token:
        return JSONResponse(status_code=400, content={"success": False, "error": "Token is required"})

    user = db.query(Customer).filter(Customer.reset_token == token).first()
    
    if not user:
        user = db.query(Barber).filter(Barber.reset_token == token).first()

    if not user:
        return JSONResponse(status_code=401, content={"success": False, "error": "Invalid reset token"})

    return {
        "success": True,
        "message": "Reset token is valid"
    }

@router.post("/reset-password")
def reset_password(
    data: ResetPasswordRequest,
    db: Session = Depends(get_db)
):
    user = db.query(Customer).filter(Customer.reset_token == data.token).first()
    
    if not user:
        user = db.query(Barber).filter(Barber.reset_token == data.token).first()

    if not user:
        return JSONResponse(
            status_code=404, 
            content={"success": False, "error": "Invalid or expired reset token"}
        )

    user.password = get_password_hash(data.newPassword)
    user.reset_token = None
    db.commit()

    return {
        "success": True,
        "message": "Password has been reset successfully"
    }