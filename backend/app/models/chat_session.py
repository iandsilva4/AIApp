from datetime import datetime, timezone
import json
from app.__init__ import db

class ChatSession(db.Model):
    __tablename__ = "chat_sessionv1"
    id = db.Column(db.Integer, primary_key=True)
    user_email = db.Column(db.String(120), nullable=False)
    title = db.Column(db.String(255), nullable=False, default="Untitled Chat")
    assistant_id = db.Column(db.Integer, db.ForeignKey('assistants.id'), nullable=True, default=1)
    messages = db.Column(db.Text, nullable=False, default="[]")
    summary = db.Column(db.Text, nullable=True)
    embedding = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    is_deleted = db.Column(db.Boolean, nullable=False, default=False)
    is_archived = db.Column(db.Boolean, nullable=False, default=False)
    is_ended = db.Column(db.Boolean, nullable=False, default=False)

    def to_dict(self):
        # Get assistant name if available
        assistant_name = None
        assistant_avatar = None
        if self.assistant_id:
            from app.models.assistant import Assistant
            assistant = Assistant.query.get(self.assistant_id)
            if assistant:
                assistant_name = assistant.name
                assistant_avatar = assistant.avatar_url
            else:
                print(f"No assistant found with ID: {self.assistant_id}")

        result = {
            "id": self.id,
            "user_email": self.user_email,
            "title": self.title,
            "assistant_id": self.assistant_id,
            "assistant_name": assistant_name,
            "assistant_avatar": assistant_avatar,
            "messages": json.loads(self.messages),
            "summary": self.summary,
            "embedding": self.embedding,
            "timestamp": self.timestamp.isoformat(),
            "is_deleted": self.is_deleted,
            "is_archived": self.is_archived,
            "is_ended": self.is_ended
        }
        return result 