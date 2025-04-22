import os
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Quiz(db.Model):
    """Model for storing quiz data"""
    id = db.Column(db.Integer, primary_key=True)

    # Quiz identifier (short code or full parameter)
    quiz_id = db.Column(db.String(255), unique=True, nullable=False, index=True)

    # Quiz metadata
    title = db.Column(db.String(255), nullable=True)
    author = db.Column(db.String(255), nullable=True)
    description = db.Column(db.Text, nullable=True)
    question_count = db.Column(db.Integer, default=0)

    # Content storage
    raw_data = db.Column(db.Text, nullable=True)  # Original JSON/data
    formatted_data = db.Column(db.Text, nullable=True)  # Formatted text version

    # Tracking
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_accessed = db.Column(db.DateTime, default=datetime.utcnow)
    access_count = db.Column(db.Integer, default=0)

    def __repr__(self):
        return f"<Quiz {self.quiz_id} ({self.title})>"

    def increment_access(self):
        """Update the access count and last accessed timestamp"""
        self.access_count += 1
        self.last_accessed = datetime.utcnow()

    def update_from_data(self, quiz_data):
        """Update quiz information from quiz data dictionary"""
        if not quiz_data:
            return False

        if 'title' in quiz_data:
            self.title = quiz_data.get('title')

        if 'author' in quiz_data:
            self.author = quiz_data.get('author')

        if 'description' in quiz_data:
            self.description = quiz_data.get('description')

        questions = quiz_data.get('questions', [])
        self.question_count = len(questions)

        return True

class QuizAttempt(db.Model):
    """Model for storing quiz attempts"""
    id = db.Column(db.Integer, primary_key=True)

    # Foreign key to Quiz model
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'), nullable=False)
    quiz = db.relationship('Quiz', backref=db.backref('attempts', lazy=True))

    # Attempt information
    user_id = db.Column(db.String(255), nullable=True)  # User identifier (if available)
    score = db.Column(db.Integer, default=0)
    max_score = db.Column(db.Integer, default=0)
    completed = db.Column(db.Boolean, default=False)

    # Timestamps
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)

    def __repr__(self):
        return f"<QuizAttempt {self.id} for Quiz {self.quiz_id}>"
