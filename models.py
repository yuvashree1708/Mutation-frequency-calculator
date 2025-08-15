from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from datetime import datetime
import json
import logging

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
    keyword = db.Column(db.String(100), nullable=False)  # keyword for shared access
    upload_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    results_file = db.Column(db.String(255), nullable=False)  # path to JSON results file
    output_file = db.Column(db.String(255), nullable=True)   # path to CSV output file
    uploaded_file_path = db.Column(db.String(255), nullable=True)  # path to original uploaded file
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
            'uploaded_file_path': self.uploaded_file_path,
            'total_positions': self.total_positions,
            'mutation_count': self.mutation_count,
            'conserved_count': self.conserved_count,
            'mutated_positions': json.loads(self.mutated_positions) if self.mutated_positions else [],
            'low_conf_positions': json.loads(self.low_conf_positions) if self.low_conf_positions else []
        }
    
    @classmethod
    def get_workspace_files(cls, workspace, keyword=None, limit=25):
        """Get files for a specific workspace and keyword, ordered by most recent first."""
        query = cls.query.filter_by(workspace=workspace)
        if keyword:
            query = query.filter_by(keyword=keyword)
        return query.order_by(cls.upload_time.desc()).limit(limit).all()
    
    @classmethod
    def get_file_by_id(cls, file_id, keyword=None):
        """Get a file by its ID, optionally filtered by keyword with enhanced reliability."""
        import os
        import json
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                query = cls.query.filter_by(id=file_id)
                if keyword:
                    query = query.filter_by(keyword=keyword)
                
                file_obj = query.first()
                if file_obj:
                    logging.info(f"Found file: {file_obj.filename}, results_file: {file_obj.results_file}")
                    
                    # Verify file integrity if found
                    if file_obj.results_file:
                        results_path = os.path.join('uploads', file_obj.results_file)
                        backup_path = results_path.replace('.json', '_backup.json')
                        
                        # Check if results file exists, if not try backup
                        if not os.path.exists(results_path) and os.path.exists(backup_path):
                            # Restore from backup
                            with open(backup_path, 'r') as f:
                                backup_data = json.load(f)
                            with open(results_path, 'w') as f:
                                json.dump(backup_data, f, indent=2)
                            logging.info(f"Restored results file from backup: {results_path}")
                else:
                    logging.error(f"File not found: {file_id} with keyword: {keyword}")
                
                return file_obj
            except Exception as e:
                logging.error(f"Database query attempt {attempt + 1} failed: {str(e)}")
                if attempt < max_retries - 1:
                    db.session.rollback()
                    db.engine.dispose()  # Force reconnection
                    import time
                    time.sleep(0.5)  # Brief delay before retry
                else:
                    raise e
    
    @classmethod
    def get_keyword_files(cls, workspace, keyword, limit=25):
        """Get files for a specific workspace and keyword combination."""
        return cls.query.filter_by(workspace=workspace, keyword=keyword)\
                       .order_by(cls.upload_time.desc())\
                       .limit(limit).all()