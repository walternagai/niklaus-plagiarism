"""
Repository pattern for database operations.
"""

from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import datetime, timedelta, UTC
import json

from auth.models import User, Submission, AnalysisCache, AuditLog
from utils.logger import get_logger
from utils.db_cache import get_submission_cache
from utils.performance import track_performance

logger = get_logger(__name__)


def utcnow() -> datetime:
    """Return current UTC datetime without tzinfo for DB writes/queries."""
    return datetime.now(UTC).replace(tzinfo=None)


class UserRepository:
    """Repository for User operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, email: str, name: str, **kwargs) -> User:
        user = User(email=email, name=name, **kwargs)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user
    
    def find_by_id(self, user_id: int) -> Optional[User]:
        return self.db.query(User).filter(User.id == user_id).first()
    
    def find_by_email(self, email: str) -> Optional[User]:
        return self.db.query(User).filter(User.email == email.lower()).first()
    
    def find_by_oauth(self, provider: str, oauth_id: str) -> Optional[User]:
        return self.db.query(User).filter(
            User.oauth_provider == provider,
            User.oauth_id == oauth_id
        ).first()
    
    def get_all_active(self, limit: int = 100) -> List[User]:
        return self.db.query(User).filter(User.is_active == True).limit(limit).all()
    
    def update_last_login(self, user_id: int) -> None:
        user = self.find_by_id(user_id)
        if user:
            user.last_login_at = utcnow()
            self.db.commit()
    
    def update_settings(self, user_id: int, settings: dict) -> None:
        user = self.find_by_id(user_id)
        if user:
            user.settings = {**(user.settings or {}), **settings}
            self.db.commit()
    
    def set_role(self, user_id: int, role: str) -> None:
        user = self.find_by_id(user_id)
        if user:
            user.role = role
            self.db.commit()
    
    def deactivate(self, user_id: int) -> None:
        user = self.find_by_id(user_id)
        if user:
            user.is_active = False
            self.db.commit()


class SubmissionRepository:
    """Repository for Submission operations."""
    
    def __init__(self, db: Session):
        self.db = db
        self._cache = get_submission_cache()
    
    @track_performance('submission.create')
    def create(self, user_id: int, filename: str, language: str, **kwargs) -> Submission:
        submission = Submission(
            user_id=user_id,
            filename=filename,
            language=language,
            **kwargs
        )
        self.db.add(submission)

        # Increment denormalized counters on User
        user = self.db.query(User).filter(User.id == user_id).first()
        if user is not None:
            suspicious = int(kwargs.get('suspicious_pairs_count', 0) or 0)
            user.submissions_count = (user.submissions_count or 0) + 1
            user.total_analyses = (user.total_analyses or 0) + 1
            user.total_suspicious_pairs = (user.total_suspicious_pairs or 0) + suspicious
            user.last_submission_at = utcnow()

        self.db.commit()
        self.db.refresh(submission)
        self._cache.invalidate_user(user_id)
        return submission
    
    @track_performance('submission.find_by_id')
    def find_by_id(self, submission_id: int) -> Optional[Submission]:
        cached = self._cache.get_submission_by_id(submission_id)
        if cached:
            return cached
        
        result = self.db.query(Submission).filter(Submission.id == submission_id).first()
        if result:
            self._cache.set_submission(result)
        return result
    
    @track_performance('submission.find_by_user')
    def find_by_user(self, user_id: int, limit: int = 50, offset: int = 0, status: str = None, use_cache: bool = True) -> List[Submission]:
        filters = {'status': status} if status else None
        
        if use_cache:
            cached = self._cache.get_user_submissions(user_id, offset, limit, filters)
            if cached:
                return cached
        
        query = self.db.query(Submission).filter(Submission.user_id == user_id)
        if status:
            query = query.filter(Submission.status == status)
        results = query.order_by(desc(Submission.created_at)).offset(offset).limit(limit).all()
        
        if use_cache and results:
            self._cache.set_user_submissions(user_id, results, offset, limit, filters, ttl=30)
        
        return results
    
    def update_status(self, submission_id: int, status: str, error_message: str = None) -> None:
        submission = self.find_by_id(submission_id)
        if submission:
            submission.status = status
            submission.error_message = error_message
            if status == 'completed':
                submission.processed_at = utcnow()
            self.db.commit()
    
    def save_analysis_data(self, submission_id: int, analysis_data: dict) -> None:
        submission = self.find_by_id(submission_id)
        if submission:
            submission.analysis_data = analysis_data
            submission.files_count = analysis_data.get('files_count', len(analysis_data.get('files', [])))
            submission.suspicious_pairs_count = len(analysis_data.get('suspicious_pairs', []))
            submission.average_similarity = analysis_data.get('average_similarity')
            submission.max_similarity = analysis_data.get('max_similarity')
            submission.analysis_time_seconds = analysis_data.get('analysis_time', 0)
            submission.status = 'completed'
            submission.processed_at = utcnow()
            self.db.commit()
    
    def delete(self, submission_id: int) -> bool:
        submission = self.find_by_id(submission_id)
        if submission:
            self.db.delete(submission)
            self.db.commit()
            return True
        return False
    
    def count_by_user(self, user_id: int) -> int:
        return self.db.query(Submission).filter(Submission.user_id == user_id).count()
    
    def count_by_status(self, status: str) -> int:
        return self.db.query(Submission).filter(Submission.status == status).count()


class CacheRepository:
    """Repository for Cache operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get(self, cache_key: str) -> Optional[AnalysisCache]:
        cache = self.db.query(AnalysisCache).filter(
            AnalysisCache.cache_key == cache_key,
            AnalysisCache.expires_at > utcnow()
        ).first()
        
        if cache:
            cache.accessed_at = utcnow()
            cache.access_count += 1
            self.db.commit()
        
        return cache
    
    def set(self, cache_key: str, cache_data: dict, file_hashes: list,
            language: str, threshold: float, user_id: int = None,
            expires_hours: int = 24) -> AnalysisCache:
        self.db.query(AnalysisCache).filter(
            AnalysisCache.cache_key == cache_key
        ).delete()
        
        cache = AnalysisCache(
            user_id=user_id,
            cache_key=cache_key,
            file_hashes=json.dumps(file_hashes),
            language=language,
            threshold=threshold,
            cache_data=cache_data,
            size_bytes=len(json.dumps(cache_data)),
            expires_at=utcnow() + timedelta(hours=expires_hours)
        )
        
        self.db.add(cache)
        self.db.commit()
        self.db.refresh(cache)
        
        return cache
    
    def delete_expired(self) -> int:
        count = self.db.query(AnalysisCache).filter(
            AnalysisCache.expires_at < utcnow()
        ).delete()
        self.db.commit()
        return count
    
    def clear_user_cache(self, user_id: int) -> int:
        count = self.db.query(AnalysisCache).filter(
            AnalysisCache.user_id == user_id
        ).delete()
        self.db.commit()
        return count


class AuditRepository:
    """Repository for Audit Log operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def log(self, action: str, entity_type: str, entity_id: int = None,
            user_id: int = None, details: dict = None,
            ip_address: str = None, user_agent: str = None) -> AuditLog:
        log = AuditLog(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent
        )
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        return log
    
    def get_user_logs(self, user_id: int, limit: int = 100) -> List[AuditLog]:
        return self.db.query(AuditLog).filter(
            AuditLog.user_id == user_id
        ).order_by(desc(AuditLog.created_at)).limit(limit).all()
    
    def get_recent_logs(self, limit: int = 100) -> List[AuditLog]:
        return self.db.query(AuditLog).order_by(
            desc(AuditLog.created_at)
        ).limit(limit).all()
