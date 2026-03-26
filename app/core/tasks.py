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
                        Booking.status == BookingStatus.CONFIRMED,
                        Booking.slot <= now
                    )
                )
                .values(status=BookingStatus.AUTO_COMPLETED, updated_at=now)
            )
            session.execute(stmt)
            session.commit()
            print("Daily maintenance: Auto-completed past bookings.")
        except Exception as e:
            session.rollback()
            print(f"Daily maintenance cron failed: {e}")

def run_booking_reminders():
    with SessionLocal() as session:
        try:
            now = datetime.now(timezone.utc)
            in_65_min = now + timedelta(minutes=65)
            stmt = select(Booking).where(
                and_(
                    Booking.status == BookingStatus.CONFIRMED,
                    Booking.slot >= now,
                    Booking.slot <= in_65_min
                )
            )

            upcoming_bookings = session.execute(stmt).scalars().all()

            for booking in upcoming_bookings:
                booking_slot = booking.slot.replace(tzinfo=timezone.utc) if booking.slot.tzinfo is None else booking.slot
                diff = (booking_slot - now).total_seconds()
                if 3000 <= diff <= 4200 and not booking.reminder_60_sent: 
                    booking.reminder_60_sent = True
                    print(f"Sending 60min reminder for booking ID: {booking.id}")
                elif 1200 <= diff <= 2400 and not booking.reminder_30_sent:
                    booking.reminder_30_sent = True
                    print(f"Sending 30min reminder for booking ID: {booking.id}")
            session.commit()
        except Exception as e:
            session.rollback()
            print(f"Booking reminders cron failed: {e}")

def start_tasks():
    scheduler.add_job(run_daily_maintenance, "cron", hour=0, minute=0)
    scheduler.add_job(run_booking_reminders, "interval", minutes=30)
    scheduler.start()
    print("background tasks started successfully")