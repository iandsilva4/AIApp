from app.__init__ import db
from datetime import datetime, timezone
import json

class UserSummary(db.Model):
    __tablename__ = 'user_summaries'

    id = db.Column(db.Integer, primary_key=True)
    user_email = db.Column(db.String(255), unique=True, nullable=False)
    summary = db.Column(db.Text, nullable=False)  # Overall user summary
    session_summaries = db.Column(db.Text, nullable=True)  # JSON of past session summaries
    session_embeddings = db.Column(db.Text, nullable=True)  # JSON of vector embeddings
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            'id': self.id,
            'user_email': self.user_email,
            'summary': self.summary,
            'session_summaries': json.loads(self.session_summaries) if self.session_summaries else [],
            'session_embeddings': json.loads(self.session_embeddings) if self.session_embeddings else [],
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

    def add_session_summary(self, session_id, title, timestamp, summary, embedding):
        """
        Add a new session summary and its embedding.
        """
        session_summaries = json.loads(self.session_summaries) if self.session_summaries else []
        session_embeddings = json.loads(self.session_embeddings) if self.session_embeddings else {}

        session_summaries.append({
            'session_id': session_id,
            'title': title,
            'timestamp': timestamp.isoformat(),
            'summary': summary
        })

        session_embeddings[str(session_id)] = embedding  # Store embedding by session ID

        self.session_summaries = json.dumps(session_summaries)
        self.session_embeddings = json.dumps(session_embeddings)
        self.updated_at = datetime.now(timezone.utc)
