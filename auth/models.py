"""
SQLAlchemy Models for Niklaus Authentication System.
"""

from sqlalchemy import Column, Integer, String, Float, Boolean, JSON, DateTime, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
from typing import Optional, Dict, Any

Base = declarative_base()


class User(Base):
    """Usuário do sistema."""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    role = Column(String(50), default='user')
    
    oauth_provider = Column(String(50))
    oauth_id = Column(String(255))
    oauth_access_token = Column(Text)
    oauth_refresh_token = Column(Text)
    oauth_token_expires_at = Column(DateTime)
    
    avatar_url = Column(String(500))
    locale = Column(String(10), default='pt_BR')
    timezone = Column(String(50), default='America/Sao_Paulo')
    
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    
    settings = Column(JSON, default=dict)
    
    submissions_count = Column(Integer, default=0)
    total_analyses = Column(Integer, default=0)
    total_suspicious_pairs = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_at = Column(DateTime)
    last_submission_at = Column(DateTime)
    
    submissions = relationship("Submission", back_populates="user", cascade="all, delete-orphan")
    cache_entries = relationship("AnalysisCache", back_populates="user")
    
    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}', role='{self.role}')>"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'email': self.email,
            'name': self.name,
            'role': self.role,
            'avatar_url': self.avatar_url,
            'is_active': self.is_active,
            'submissions_count': self.submissions_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login_at': self.last_login_at.isoformat() if self.last_login_at else None,
        }
    
    @property
    def is_admin(self) -> bool:
        return self.role == 'admin'
    
    def update_settings(self, key: str, value: Any) -> None:
        settings = self.settings or {}
        settings[key] = value
        self.settings = settings


class Submission(Base):
    """Submissão de análise de plágio."""
    __tablename__ = 'submissions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    
    filename = Column(String(255), nullable=False)
    file_size_bytes = Column(Integer)
    file_hash = Column(String(64))
    
    language = Column(String(50), nullable=False)
    threshold = Column(Float, default=0.7)
    max_workers = Column(Integer, default=4)
    enable_ai = Column(Boolean, default=True)
    use_cache = Column(Boolean, default=True)
    
    files_count = Column(Integer)
    suspicious_pairs_count = Column(Integer, default=0)
    average_similarity = Column(Float)
    max_similarity = Column(Float)
    analysis_time_seconds = Column(Float)
    
    status = Column(String(50), default='pending')
    error_message = Column(Text)
    
    analysis_data = Column(JSON)
    
    processed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    user = relationship("User", back_populates="submissions")
    
    def __repr__(self):
        return f"<Submission(id={self.id}, user_id={self.user_id}, filename='{self.filename}')>"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'user_id': self.user_id,
            'filename': self.filename,
            'language': self.language,
            'threshold': self.threshold,
            'files_count': self.files_count,
            'suspicious_pairs_count': self.suspicious_pairs_count,
            'analysis_time_seconds': self.analysis_time_seconds,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
    
    def has_analysis_data(self) -> bool:
        return self.analysis_data is not None and self.status == 'completed'


class AnalysisCache(Base):
    """Cache de análises para evitar reprocessamento."""
    __tablename__ = 'analysis_cache'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'))
    
    cache_key = Column(String(128), unique=True, nullable=False, index=True)
    file_hashes = Column(Text, nullable=False)
    language = Column(String(50), nullable=False)
    threshold = Column(Float, nullable=False)
    
    cache_data = Column(JSON, nullable=False)
    size_bytes = Column(Integer)
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    expires_at = Column(DateTime, nullable=False)
    accessed_at = Column(DateTime, default=datetime.utcnow)
    access_count = Column(Integer, default=0)
    
    user = relationship("User", back_populates="cache_entries")
    
    def __repr__(self):
        return f"<AnalysisCache(id={self.id}, cache_key='{self.cache_key[:16]}...')>"
    
    def is_expired(self) -> bool:
        return datetime.utcnow() > self.expires_at
    
    def touch(self) -> None:
        self.accessed_at = datetime.utcnow()
        self.access_count += 1


class AuditLog(Base):
    """Log de ações para auditoria."""
    __tablename__ = 'audit_log'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'))
    
    action = Column(String(100), nullable=False)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(Integer)
    
    details = Column(JSON, default=dict)
    ip_address = Column(String(45))
    user_agent = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    def __repr__(self):
        return f"<AuditLog(id={self.id}, action='{self.action}')>"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'user_id': self.user_id,
            'action': self.action,
            'entity_type': self.entity_type,
            'entity_id': self.entity_id,
            'details': self.details,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
