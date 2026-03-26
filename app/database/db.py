from app.core.config import settings
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# 1. Get settings (this calls the lru_cache function)
get_settings = settings()

# 2. Create the Synchronous Engine
# Ensure your DATABASE_URL starts with postgresql:// or postgres://
engine = create_engine(
    get_settings.DATABASE_URL,
    pool_size=20,
    max_overflow=40,
    pool_recycle=3600,
    pool_pre_ping=True,
    pool_timeout=30,
    connect_args={"sslmode": "require"}, # Sync psycopg2 handles this perfectly
    echo=False,
    future=True,
)

# 3. Session Factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 4. Base for Models
Base = declarative_base()

# 5. DB Initialization (Sync)
def init_db():
    Base.metadata.create_all(bind=engine)

# 6. Dependency for FastAPI Routes (Sync)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()