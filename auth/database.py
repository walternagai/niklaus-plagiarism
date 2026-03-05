"""
Database setup and session management for Niklaus.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from contextlib import contextmanager
from typing import Generator, Optional
import os
from pathlib import Path

Base = declarative_base()


class DatabaseManager:
    """Gerenciador do banco de dados."""
    
    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or os.getenv(
            'DATABASE_URL', 
            'sqlite:///./niklaus.db'
        )
        
        self.engine = create_engine(
            self.database_url,
            connect_args={"check_same_thread": False} if 'sqlite' in self.database_url else {},
            echo=False
        )
        
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )
        
        if 'sqlite' in self.database_url:
            db_path = self.database_url.replace('sqlite:///', '')
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    
    def create_tables(self) -> None:
        from auth.models import Base
        Base.metadata.create_all(bind=self.engine)
        print("✅ Database tables created successfully")
    
    def drop_tables(self) -> None:
        from auth.models import Base
        Base.metadata.drop_all(bind=self.engine)
        print("⚠️ Database tables dropped")
    
    def get_session(self) -> Session:
        return self.SessionLocal()
    
    @contextmanager
    def session_scope(self) -> Generator[Session, None, None]:
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()


_db_manager: Optional[DatabaseManager] = None


def get_db_manager() -> DatabaseManager:
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager


def get_session() -> Session:
    """Get a database session (convenience function)."""
    return get_db_manager().get_session()


def get_db() -> Generator[Session, None, None]:
    db_manager = get_db_manager()
    db = db_manager.get_session()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """Provide a transactional scope around a series of operations."""
    db_manager = get_db_manager()
    with db_manager.session_scope() as session:
        yield session


def init_db() -> None:
    db_manager = get_db_manager()
    db_manager.create_tables()
    print("✅ Database initialized")
