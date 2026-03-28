import logging
from datetime import datetime
from sqlalchemy import update, and_
from app.models.schema import Booking, BookingStatus
from app.database.db import SessionLocal

logger = logging.getLogger("app.tasks")

def run_daily_maintenance():
    with SessionLocal() as session:
        try:
            now = datetime.now()
            stmt = (
                update(Booking)
                .where(
                    and_(
                        Booking.status == BookingStatus.confirmed,
                        Booking.slot <= now
                    )
                )
                .values(status=BookingStatus.auto, updated_at=now)
            )
            session.execute(stmt)
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"ERROR: Maintenance cron failed: {e}")

def register_tasks(scheduler):
    if not scheduler.get_job("maintenance_job"):
        scheduler.add_job(
            run_daily_maintenance, 
            "cron", 
            hour=4,
            minute=0,
            id="maintenance_job",
            replace_existing=True
        )