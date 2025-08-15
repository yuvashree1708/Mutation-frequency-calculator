from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json

db = SQLAlchemy()

class UploadedFile(db.Model):
    __tablename__ = 'uploaded_files'
    
    id = db.Column(db.String(36), primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    workspace = db.Column(db.String(50), nullable=False)
    keyword = db.Column(db.String(50), nullable=False)
    upload_time = db.Column(db.DateTime, default=datetime.utcnow)
    results_file = db.Column(db.String(255))
    output_file = db.Column(db.String(255))
    uploaded_file_path = db.Column(db.String(255))
    
    # Analysis results metadata
    total_positions = db.Column(db.Integer, default=0)
    mutation_count = db.Column(db.Integer, default=0)
    conserved_count = db.Column(db.Integer, default=0)
    mutated_positions = db.Column(db.Text)  # JSON string
    low_conf_positions = db.Column(db.Text)  # JSON string
    
    @classmethod
    def get_keyword_files(cls, workspace, keyword, limit=None):
        """Get all files for a specific workspace and keyword."""
        query = cls.query.filter_by(workspace=workspace, keyword=keyword).order_by(cls.upload_time.desc())
        if limit:
            query = query.limit(limit)
        return query.all()
    
    @classmethod
    def get_file_by_id(cls, file_id, keyword=None):
        """Get a file by ID, optionally filtered by keyword."""
        query = cls.query.filter_by(id=file_id)
        if keyword:
            query = query.filter_by(keyword=keyword)
        return query.first()
    
    def to_dict(self):
        """Convert file record to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'filename': self.filename,
            'original_filename': self.original_filename,
            'workspace': self.workspace,
            'keyword': self.keyword,
            'upload_time': self.upload_time.isoformat() if self.upload_time else None,
            'results_file': self.results_file,
            'output_file': self.output_file,
            'uploaded_file_path': self.uploaded_file_path,
            'total_positions': self.total_positions or 0,
            'mutation_count': self.mutation_count or 0,
            'conserved_count': self.conserved_count or 0,
            'mutated_positions': json.loads(self.mutated_positions) if self.mutated_positions else [],
            'low_conf_positions': json.loads(self.low_conf_positions) if self.low_conf_positions else []
        }

class UserPreference(db.Model):
    __tablename__ = 'user_preferences'
    
    id = db.Column(db.Integer, primary_key=True)
    user_session_id = db.Column(db.String(255), nullable=False)  # Browser session or user identifier
    workspace = db.Column(db.String(50), nullable=False)
    preference_key = db.Column(db.String(100), nullable=False)
    preference_value = db.Column(db.Text, nullable=False)  # JSON string
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    usage_count = db.Column(db.Integer, default=1)
    
    __table_args__ = (
        db.UniqueConstraint('user_session_id', 'workspace', 'preference_key', name='unique_user_workspace_preference'),
    )
    
    @classmethod
    def get_preference(cls, session_id, workspace, key, default=None):
        """Get user preference value."""
        pref = cls.query.filter_by(
            user_session_id=session_id,
            workspace=workspace,
            preference_key=key
        ).first()
        
        if pref:
            try:
                return json.loads(pref.preference_value)
            except:
                return default
        return default
    
    @classmethod
    def set_preference(cls, session_id, workspace, key, value):
        """Set or update user preference."""
        pref = cls.query.filter_by(
            user_session_id=session_id,
            workspace=workspace,
            preference_key=key
        ).first()
        
        if pref:
            pref.preference_value = json.dumps(value)
            pref.usage_count += 1
            pref.last_updated = datetime.utcnow()
        else:
            pref = cls(
                user_session_id=session_id,
                workspace=workspace,
                preference_key=key,
                preference_value=json.dumps(value)
            )
            db.session.add(pref)
        
        db.session.commit()
        return pref

class UserActivity(db.Model):
    __tablename__ = 'user_activities'
    
    id = db.Column(db.Integer, primary_key=True)
    user_session_id = db.Column(db.String(255), nullable=False)
    workspace = db.Column(db.String(50), nullable=False)
    activity_type = db.Column(db.String(100), nullable=False)  # 'file_view', 'table_sort', 'position_jump', etc.
    activity_data = db.Column(db.Text)  # JSON string with activity details
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    file_id = db.Column(db.String(36))  # Optional reference to file
    
    @classmethod
    def log_activity(cls, session_id, workspace, activity_type, data=None, file_id=None):
        """Log user activity for adaptive learning."""
        activity = cls(
            user_session_id=session_id,
            workspace=workspace,
            activity_type=activity_type,
            activity_data=json.dumps(data) if data else None,
            file_id=file_id
        )
        db.session.add(activity)
        db.session.commit()
        return activity
    
    @classmethod
    def get_user_patterns(cls, session_id, workspace, activity_type=None, days=30):
        """Get user activity patterns for adaptive UI."""
        from datetime import datetime, timedelta
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        query = cls.query.filter(
            cls.user_session_id == session_id,
            cls.workspace == workspace,
            cls.timestamp >= cutoff
        )
        
        if activity_type:
            query = query.filter_by(activity_type=activity_type)
        
        return query.order_by(cls.timestamp.desc()).all()

class AdaptiveLayout(db.Model):
    __tablename__ = 'adaptive_layouts'
    
    id = db.Column(db.Integer, primary_key=True)
    user_session_id = db.Column(db.String(255), nullable=False)
    workspace = db.Column(db.String(50), nullable=False)
    layout_config = db.Column(db.Text, nullable=False)  # JSON string with layout settings
    performance_score = db.Column(db.Float, default=0.0)  # How well this layout performs for user
    usage_duration = db.Column(db.Integer, default=0)  # Total minutes used
    last_used = db.Column(db.DateTime, default=datetime.utcnow)
    
    @classmethod
    def get_best_layout(cls, session_id, workspace):
        """Get the best performing layout for user."""
        return cls.query.filter_by(
            user_session_id=session_id,
            workspace=workspace
        ).order_by(cls.performance_score.desc()).first()
    
    @classmethod
    def update_layout_performance(cls, session_id, workspace, layout_config, usage_time, user_satisfaction=None):
        """Update layout performance based on usage."""
        layout = cls.query.filter_by(
            user_session_id=session_id,
            workspace=workspace
        ).first()
        
        if not layout:
            layout = cls(
                user_session_id=session_id,
                workspace=workspace,
                layout_config=json.dumps(layout_config)
            )
            db.session.add(layout)
        
        # Update performance metrics
        layout.usage_duration += usage_time
        layout.last_used = datetime.utcnow()
        
        # Calculate performance score based on usage patterns
        base_score = min(usage_time / 60.0, 10.0)  # Up to 10 points for 60+ minutes
        if user_satisfaction:
            base_score *= user_satisfaction  # Multiply by satisfaction rating (0-1)
        
        layout.performance_score = (layout.performance_score + base_score) / 2  # Running average
        
        db.session.commit()
        return layout