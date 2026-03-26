import enum
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlmodel import SQLModel, Field, Column, JSON, Numeric
from geoalchemy2 import Geometry

# 1. Enums
class BookingStatus(str, enum.Enum):
    confirmed = "confirmed"
    canceled = "canceled"
    completed = "completed"
    auto_completed = "auto-completed"


# 2. Saved Barbers (Many-to-Many Link Table)
class SavedBarber(SQLModel, table=True):
    __tablename__ = "saved_barbers"
    customer_id: str = Field(foreign_key="customers.id", primary_key=True)
    barber_id: str = Field(foreign_key="barbers.id", primary_key=True)

# 3. Customer Model
class Customer(SQLModel, table=True):
    __tablename__ = "customers"
    id: str = Field(primary_key=True)
    name: str
    email: str = Field(unique=True, index=True)
    password: str
    profile_pic: Optional[str] = None
    phone_number: Optional[str] = None
    refresh_token: Optional[str] = None
    access_token: Optional[str] = None
    fcm_token: Optional[str] = None
    penalty: float = Field(default=0.00, sa_column=Column(Numeric(10, 2)))
    created_at: datetime = Field(default_factory=datetime.utcnow)

# 4. Barber Model
class Barber(SQLModel, table=True):
    __tablename__ = "barbers"
    id: str = Field(primary_key=True)
    name: str
    email: str = Field(unique=True, index=True)
    password: str
    phone_number: Optional[str] = None
    profile_pic: Optional[str] = None
    shop_name: str
    address: str
    
    # JSONB columns
    services: List[Dict[str, Any]] = Field(default=[], sa_column=Column(JSON))
    timings: Dict[str, Any] = Field(sa_column=Column(JSON))
    
    # PostGIS Geometry (Point, SRID 4326)
    location: Any = Field(sa_column=Column(Geometry(geometry_type='POINT', srid=4326)))
    
    rating: float = Field(default=0.00, sa_column=Column(Numeric(3, 2)))
    total_seats: int = Field(default=1)
    total_reviews: int = Field(default=0)

# 5. Booking Model
class Booking(SQLModel, table=True):
    __tablename__ = "bookings"
    id: str = Field(primary_key=True)
    customer_id: str = Field(foreign_key="customers.id")
    barber_id: str = Field(foreign_key="barbers.id")
    service: str
    price: float = Field(sa_column=Column(Numeric(10, 2)))
    slot: datetime
    status: BookingStatus = Field(default=BookingStatus.confirmed)
    note: Optional[str] = None
    is_penalized: bool = Field(default=False)
    completed_at: Optional[datetime] = None
    reminder_60_sent: bool = Field(default=False)
    reminder_30_sent: bool = Field(default=False)
    seat_number: int
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

# 6. Seat Model
class Seat(SQLModel, table=True):
    __tablename__ = "seats"
    id: str = Field(primary_key=True)
    barber_id: str = Field(foreign_key="barbers.id", ondelete="CASCADE")
    seat_number: int
    is_occupied: bool = Field(default=False)
    current_booking_id: Optional[str] = Field(default=None, foreign_key="bookings.id")

# 7. Review Model
class Review(SQLModel, table=True):
    __tablename__ = "reviews"
    id: str = Field(primary_key=True)
    customer_id: str = Field(foreign_key="customers.id", ondelete="CASCADE")
    barber_id: str = Field(foreign_key="barbers.id", ondelete="CASCADE")
    booking_id: str = Field(foreign_key="bookings.id", ondelete="CASCADE", unique=True)
    rating: int
    comment: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)