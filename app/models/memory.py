from ..extensions import db
from ..config import Config
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy import func
from pgvector.sqlalchemy import Vector
import uuid
import enum

class MemoryType(enum.Enum):
    POSITION = "position"
    WORK_CONTENT = "work_content"
    WRITING_PREFERENCE = "writing_preference"
    HISTORICAL_CONTEXT = "historical_context"

class Memory(db.Model):
    __tablename__ = 'memories'

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = db.Column(db.String(256), nullable=False, index=True)
    type = db.Column(db.Enum(MemoryType), nullable=False)
    content = db.Column(db.Text, nullable=False)
    locked = db.Column(db.Boolean, default=False, nullable=False)
    
    # Vector embedding (configured in environment variables)
    embedding = db.Column(Vector(Config.EMBEDDING_DIMENSION))
    
    # Timestamps
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
    updated_at = db.Column(db.DateTime(timezone=True), onupdate=func.now())
    last_accessed_at = db.Column(db.DateTime(timezone=True))

    def to_dict(self):
        return {
            'id': str(self.id),
            'user_id': self.user_id,
            'type': self.type.value,
            'content': self.content,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'last_accessed_at': self.last_accessed_at.isoformat() if self.last_accessed_at else None
        }
