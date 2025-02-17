from app.__init__ import db
from datetime import datetime, timezone

class Assistant(db.Model):
    __tablename__ = "assistants"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    system_prompt = db.Column(db.Text, nullable=False)
    avatar_url = db.Column(db.String(255), nullable=True)
    created_by = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)) 