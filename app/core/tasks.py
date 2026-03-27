from datetime import datetime, timedelta, timezone
from sqlalchemy import select, update, and_
from apscheduler.schedulers.background import BackgroundScheduler
from app.models.schema import Booking, BookingStatus
from app.database.db import SessionLocal

scheduler = BackgroundScheduler()

def run_daily_maintenance():
    with SessionLocal() as session:
        try:
            now = datetime.now(timezone.utc)
            stmt = (
                update(Booking)
                .where(
                    and_(
                        Booking.status == BookingStatus.confirmed,
                        Booking.slot <= now
                    )
                )
                .values(status=BookingStatus.auto_completed, updated_at=now)
            )
            session.execute(stmt)
            session.commit()
            print("daily maintenance: auto-completed past bookings")
        except Exception as e:
            session.rollback()
            print(f"daily maintenance cron failed: {e}")

def run_booking_reminders():
    with SessionLocal() as session:
        try:
            now = datetime.now(timezone.utc)
            in_75_min = now + timedelta(minutes=75)
            
            stmt = select(Booking).where(
                and_(
                    Booking.status == BookingStatus.confirmed,
                    Booking.slot >= now,
                    Booking.slot <= in_75_min,
                    Booking.reminder_60_sent == False
                )
            )

            upcoming_bookings = session.execute(stmt).scalars().all()

            for booking in upcoming_bookings:
                booking_slot = booking.slot.replace(tzinfo=timezone.utc) if booking.slot.tzinfo is None else booking.slot
                diff = (booking_slot - now).total_seconds()
                
                if 3300 <= diff <= 4500: 
                    booking.reminder_60_sent = True
                    print(f"sending 60min reminder for booking ID: {booking.id}")
                    
            session.commit()
        except Exception as e:
            session.rollback()
            print(f"booking reminders cron failed: {e}")

def start_tasks():
    scheduler.add_job(run_daily_maintenance, "cron", hour=0, minute=0)
    scheduler.add_job(run_booking_reminders, "interval", minutes=15)
    scheduler.start()
    print("background tasks started successfully")