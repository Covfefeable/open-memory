# Agent Memory System Design

## 1. Core Memory Table (Refined)

For a robust agent memory system, especially one distinguishing between *preferences* and *facts*, we should consider adding fields for **provenance (source)**, **context**, and **relevance/embedding** (if you plan to use vector search later).

Here is a recommended schema design:

| Field Name | Type | Description | Rationale |
| :--- | :--- | :--- | :--- |
| `id` | UUID | Primary Key | Standard unique identifier. |
| `user_id` | VARCHAR(256) | Foreign Key / Index | To retrieve memories for a specific user. |
| `type` | ENUM | `preference`, `fact`, `skill` (optional) | Categorizes memory for different processing logic. |
| `content` | TEXT | The actual memory | The core information. |
| `source` | VARCHAR(256) | Metadata (optional) | Where did this come from? (e.g., "user_input", "system_inference", "file_analysis"). Important for trust/verification. |
| `context` | JSONB | Metadata (optional) | Stores related context like `conversation_id`, `file_path`, or specific tags. |
| `embedding` | VECTOR(1536) | Vector (pgvector) | **Crucial for Agent Memory**: Allows semantic search to find relevant memories based on meaning, not just keywords. |
| `last_accessed_at`| TIMESTAMP | Metadata | For "forgetting" mechanisms or LRU caching. |
| `created_at` | TIMESTAMP | Audit | When the memory was formed. |
| `updated_at` | TIMESTAMP | Audit | When the memory was last modified. |

## 2. Explanation of Additions

1.  **`source` (来源)**:
    *   **Why**: Agent memories can come from direct user instruction ("Call me John") or deduction ("User seems to like Python"). Distinguishing these helps in conflict resolution (User instruction > Deduction).
2.  **`context` (上下文 - JSONB)**:
    *   **Why**: Memories often depend on context. Storing `{"conversation_id": "123"}` or `{"related_file": "config.py"}` helps the agent understand *when* this memory applies.
3.  **`embedding` (向量)**:
    *   **Why**: If you want the agent to *recall* this memory when relevant, you need vector search. SQL `LIKE` queries are insufficient for semantic understanding. (Requires `pgvector` extension).
4.  **`last_accessed_at` (最后访问时间)**:
    *   **Why**: Helps implement "Long-term vs Short-term" memory. Old, unused memories can be archived or summarized.

## 3. Revised Model Definition (SQLAlchemy)

```python
from ..extensions import db
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy import func
import uuid

class MemoryType(enum.Enum):
    PREFERENCE = "preference"
    FACT = "fact"

class Memory(db.Model):
    __tablename__ = 'memories'

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = db.Column(db.String(256), nullable=False, index=True)
    type = db.Column(db.Enum(MemoryType), nullable=False)
    content = db.Column(db.Text, nullable=False)
    
    # Context & Meta
    source = db.Column(db.String(50), default='user_input') # user, system, observation
    context = db.Column(JSONB, default={}) # Flexible metadata
    
    # Timestamps
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
    updated_at = db.Column(db.DateTime(timezone=True), onupdate=func.now())
    last_accessed_at = db.Column(db.DateTime(timezone=True))

    # Optional: Embedding if using pgvector
    # embedding = db.Column(Vector(1536)) 
```
