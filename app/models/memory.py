from ..extensions import db
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy import func
from pgvector.sqlalchemy import Vector
import uuid
import enum

class MemoryType(enum.Enum):
    PREFERENCE = "preference"
    FACT = "fact"

class Memory(db.Model):
    __tablename__ = 'memories'

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = db.Column(db.String(256), nullable=False, index=True)
    type = db.Column(db.Enum(MemoryType), nullable=False)
    content = db.Column(db.Text, nullable=False)
    
    # Vector embedding (1536 is standard for OpenAI ada-002, adjust if using other models)
    embedding = db.Column(Vector(1536))
    
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
