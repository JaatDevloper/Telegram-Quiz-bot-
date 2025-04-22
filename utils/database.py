import json
import logging
from datetime import datetime
from models import db, Quiz, QuizAttempt

logger = logging.getLogger(__name__)

class QuizDatabase:
    """Class for handling database operations for quizzes"""
    
    @staticmethod
    def get_quiz_by_id(quiz_id):
        """
        Get a quiz by its unique ID (shortcode or parameter)
        
        Args:
            quiz_id (str): The quiz identifier
            
        Returns:
            Quiz: Quiz object or None if not found
        """
        try:
            return Quiz.query.filter_by(quiz_id=quiz_id).first()
        except Exception as e:
            logger.error(f"Error retrieving quiz by ID: {str(e)}")
            return None
    
    @staticmethod
    def save_quiz(quiz_id, quiz_data):
        """
        Save or update a quiz in the database
        
        Args:
            quiz_id (str): The quiz identifier
            quiz_data (dict): Quiz data to save
            
        Returns:
            Quiz: Saved Quiz object or None if save fails
        """
        try:
            # Check if the quiz already exists
            quiz = QuizDatabase.get_quiz_by_id(quiz_id)
            
            if quiz:
                # Update existing quiz
                logger.info(f"Updating existing quiz: {quiz_id}")
                quiz.raw_data = json.dumps(quiz_data)
                quiz.formatted_data = quiz_data.get('formatted_text', '')
                quiz.update_from_data(quiz_data)
                quiz.increment_access()
            else:
                # Create new quiz
                logger.info(f"Creating new quiz: {quiz_id}")
                quiz = Quiz(
                    quiz_id=quiz_id,
                    title=quiz_data.get('title', 'Telegram Quiz'),
                    question_count=len(quiz_data.get('questions', [])),
                    raw_data=json.dumps(quiz_data),
                    formatted_data=quiz_data.get('formatted_text', '')
                )
                db.session.add(quiz)
            
            # Commit the changes
            db.session.commit()
            return quiz
            
        except Exception as e:
            logger.error(f"Error saving quiz: {str(e)}")
            db.session.rollback()
            return None
    
    @staticmethod
    def get_recent_quizzes(limit=10):
        """
        Get a list of recently accessed quizzes
        
        Args:
            limit (int): Maximum number of quizzes to return
            
        Returns:
            list: List of Quiz objects
        """
        try:
            return Quiz.query.order_by(Quiz.last_accessed.desc()).limit(limit).all()
        except Exception as e:
            logger.error(f"Error retrieving recent quizzes: {str(e)}")
            return []
    
    @staticmethod
    def get_popular_quizzes(limit=10):
        """
        Get a list of most popular quizzes by access count
        
        Args:
            limit (int): Maximum number of quizzes to return
            
        Returns:
            list: List of Quiz objects
        """
        try:
            return Quiz.query.order_by(Quiz.access_count.desc()).limit(limit).all()
        except Exception as e:
            logger.error(f"Error retrieving popular quizzes: {str(e)}")
            return []
    
    @staticmethod
    def search_quizzes(query, limit=10):
        """
        Search for quizzes by title or content
        
        Args:
            query (str): Search query
            limit (int): Maximum number of quizzes to return
            
        Returns:
            list: List of Quiz objects matching the search
        """
        try:
            search_pattern = f"%{query}%"
            return Quiz.query.filter(
                db.or_(
                    Quiz.title.ilike(search_pattern),
                    Quiz.raw_data.ilike(search_pattern),
                    Quiz.formatted_data.ilike(search_pattern)
                )
            ).limit(limit).all()
        except Exception as e:
            logger.error(f"Error searching quizzes: {str(e)}")
            return []
    
    @staticmethod
    def delete_quiz(quiz_id):
        """
        Delete a quiz from the database
        
        Args:
            quiz_id (str): The quiz identifier
            
        Returns:
            bool: True if deletion was successful, False otherwise
        """
        try:
            quiz = QuizDatabase.get_quiz_by_id(quiz_id)
            if quiz:
                db.session.delete(quiz)
                db.session.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting quiz: {str(e)}")
            db.session.rollback()
            return False
    
    @staticmethod
    def create_quiz_attempt(quiz_id, user_id=None):
        """
        Create a new quiz attempt
        
        Args:
            quiz_id (str): The quiz identifier
            user_id (str, optional): User identifier
            
        Returns:
            QuizAttempt: Created attempt or None if creation fails
        """
        try:
            # Get the quiz
            quiz = QuizDatabase.get_quiz_by_id(quiz_id)
            if not quiz:
                return None
            
            # Create a new attempt
            attempt = QuizAttempt(
                quiz_id=quiz.id,
                user_id=user_id,
                max_score=quiz.question_count
            )
            
            db.session.add(attempt)
            db.session.commit()
            return attempt
            
        except Exception as e:
            logger.error(f"Error creating quiz attempt: {str(e)}")
            db.session.rollback()
            return None
    
    @staticmethod
    def update_quiz_attempt(attempt_id, score=None, completed=None):
        """
        Update a quiz attempt
        
        Args:
            attempt_id (int): The attempt ID
            score (int, optional): New score
            completed (bool, optional): Completion status
            
        Returns:
            QuizAttempt: Updated attempt or None if update fails
        """
        try:
            attempt = QuizAttempt.query.get(attempt_id)
            if not attempt:
                return None
            
            if score is not None:
                attempt.score = score
            
            if completed is not None:
                attempt.completed = completed
                if completed:
                    attempt.completed_at = datetime.utcnow()
            
            db.session.commit()
            return attempt
            
        except Exception as e:
            logger.error(f"Error updating quiz attempt: {str(e)}")
            db.session.rollback()
            return None