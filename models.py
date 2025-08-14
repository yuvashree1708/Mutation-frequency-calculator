from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from datetime import datetime
import json

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

class UploadedFile(db.Model):
    """Model for storing uploaded file metadata and analysis results."""
    __tablename__ = 'uploaded_files'
    
    id = db.Column(db.String(36), primary_key=True)  # UUID
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    workspace = db.Column(db.String(10), nullable=False)  # 'denv' or 'chikv'
    upload_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    results_file = db.Column(db.String(255), nullable=False)  # path to JSON results file
    output_file = db.Column(db.String(255), nullable=True)   # path to CSV output file
    total_positions = db.Column(db.Integer, nullable=False)
    mutation_count = db.Column(db.Integer, nullable=False)
    conserved_count = db.Column(db.Integer, nullable=False)
    mutated_positions = db.Column(db.Text, nullable=True)  # JSON string of positions
    low_conf_positions = db.Column(db.Text, nullable=True)  # JSON string of positions
    
    def __repr__(self):
        return f'<UploadedFile {self.filename} in {self.workspace}>'
    
    def to_dict(self):
        """Convert model to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'filename': self.filename,
            'original_filename': self.original_filename,
            'workspace': self.workspace,
            'timestamp': self.upload_time.isoformat(),
            'upload_time': self.upload_time.strftime('%Y-%m-%d %H:%M:%S'),
            'results_file': self.results_file,
            'output_file': self.output_file,
            'total_positions': self.total_positions,
            'mutation_count': self.mutation_count,
            'conserved_count': self.conserved_count,
            'mutated_positions': json.loads(self.mutated_positions) if self.mutated_positions else [],
            'low_conf_positions': json.loads(self.low_conf_positions) if self.low_conf_positions else []
        }
    
    @classmethod
    def get_workspace_files(cls, workspace, limit=25):
        """Get files for a specific workspace, ordered by most recent first."""
        return cls.query.filter_by(workspace=workspace)\
                       .order_by(cls.upload_time.desc())\
                       .limit(limit).all()
    
    @classmethod
    def get_file_by_id(cls, file_id):
        """Get a file by its ID."""
        return cls.query.filter_by(id=file_id).first()