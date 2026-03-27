from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from sqlalchemy.orm import Session
from app.database.db import SessionLocal
from app.models.schema import Booking, BookingStatus
from app.utils.mail import send_booking_reminder_mail

IST = ZoneInfo("Asia/Kolkata")

def check_and_send_reminders():
    db: Session = SessionLocal()
    try:
        now = datetime.now(IST)

        remind_60_time = now + timedelta(minutes=60)
        bookings_60 = db.query(Booking).filter(
            Booking.status == BookingStatus.confirmed,
            Booking.reminder_60_sent == False,
            Booking.slot <= remind_60_time,
            Booking.slot > now
        ).all()

        for b in bookings_60:
            try:
                send_booking_reminder_mail(b.id, 60, db)
                b.reminder_60_sent = True
                db.commit()
            except Exception as e:
                db.rollback()
                print(f"Error sending 60m reminder for {b.id}: {e}")

    except Exception as e:
        print(f"Reminder Task Error: {e}")
    finally:
        db.close()