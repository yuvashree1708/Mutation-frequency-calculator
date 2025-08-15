#!/usr/bin/env python3
"""
Database Integrity Manager - Ensures database consistency and proper data management
"""

import os
import json
import logging
from datetime import datetime
from app import app
from models import db, UploadedFile

class DatabaseIntegrityManager:
    def __init__(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger('DatabaseIntegrityManager')

    def verify_database_consistency(self):
        """Verify that all database records have corresponding files."""
        with app.app_context():
            try:
                files = UploadedFile.query.all()
                inconsistencies = []
                
                for file_record in files:
                    issues = []
                    
                    # Check original file
                    if file_record.uploaded_file_path:
                        original_path = os.path.join('uploads', file_record.uploaded_file_path)
                        if not os.path.exists(original_path):
                            issues.append(f"Missing original file: {original_path}")
                    
                    # Check results file
                    if file_record.results_file:
                        results_path = os.path.join('uploads', file_record.results_file)
                        if not os.path.exists(results_path):
                            issues.append(f"Missing results file: {results_path}")
                    
                    # Check output file
                    if file_record.output_file:
                        output_path = os.path.join('uploads', file_record.output_file)
                        if not os.path.exists(output_path):
                            issues.append(f"Missing output file: {output_path}")
                    
                    if issues:
                        inconsistencies.append({
                            'id': file_record.id,
                            'filename': file_record.original_filename,
                            'workspace': file_record.workspace,
                            'issues': issues
                        })
                
                self.logger.info(f"Database consistency check complete. Found {len(inconsistencies)} inconsistencies")
                return inconsistencies
                
            except Exception as e:
                self.logger.error(f"Error during database consistency check: {str(e)}")
                return None

    def clean_orphaned_database_entries(self):
        """Remove database entries that have no corresponding files."""
        with app.app_context():
            try:
                db.session.begin()
                
                files = UploadedFile.query.all()
                orphaned_count = 0
                
                for file_record in files:
                    has_files = False
                    
                    # Check if any associated files exist
                    if file_record.uploaded_file_path:
                        original_path = os.path.join('uploads', file_record.uploaded_file_path)
                        if os.path.exists(original_path):
                            has_files = True
                    
                    if file_record.results_file and not has_files:
                        results_path = os.path.join('uploads', file_record.results_file)
                        if os.path.exists(results_path):
                            has_files = True
                    
                    if not has_files:
                        self.logger.info(f"Removing orphaned database entry: {file_record.id} - {file_record.original_filename}")
                        db.session.delete(file_record)
                        orphaned_count += 1
                
                db.session.commit()
                self.logger.info(f"Cleaned up {orphaned_count} orphaned database entries")
                return orphaned_count
                
            except Exception as e:
                db.session.rollback()
                self.logger.error(f"Error cleaning orphaned entries: {str(e)}")
                return None

    def clean_orphaned_files(self):
        """Remove files that have no corresponding database entries."""
        with app.app_context():
            try:
                # Get all file IDs from database
                db_file_ids = set()
                files = UploadedFile.query.all()
                
                for file_record in files:
                    db_file_ids.add(file_record.id)
                
                # Check uploads directory
                orphaned_files = []
                upload_dir = 'uploads'
                
                for filename in os.listdir(upload_dir):
                    filepath = os.path.join(upload_dir, filename)
                    
                    # Skip directories and non-relevant files
                    if not os.path.isfile(filepath):
                        continue
                    
                    # Extract file ID from filename
                    file_id = None
                    if filename.startswith('results_'):
                        # Results file: results_{file_id}.json or results_{file_id}_backup.json
                        parts = filename.replace('results_', '').replace('_backup.json', '').replace('.json', '')
                        file_id = parts
                    elif '_' in filename and len(filename.split('_')[0]) == 36:
                        # Original file: {file_id}_{original_name}
                        file_id = filename.split('_')[0]
                    
                    # Check if file ID exists in database
                    if file_id and file_id not in db_file_ids:
                        orphaned_files.append(filepath)
                
                # Delete orphaned files
                deleted_count = 0
                for filepath in orphaned_files:
                    try:
                        os.remove(filepath)
                        deleted_count += 1
                        self.logger.info(f"Deleted orphaned file: {filepath}")
                    except Exception as e:
                        self.logger.error(f"Failed to delete orphaned file {filepath}: {str(e)}")
                
                self.logger.info(f"Cleaned up {deleted_count} orphaned files")
                return deleted_count
                
            except Exception as e:
                self.logger.error(f"Error cleaning orphaned files: {str(e)}")
                return None

    def safe_delete_file(self, file_id, workspace):
        """Safely delete a file with full cleanup and transaction integrity."""
        with app.app_context():
            try:
                db.session.begin()
                
                # Find the file record
                file_record = UploadedFile.query.filter_by(
                    id=file_id, 
                    workspace=workspace.lower()
                ).first()
                
                if not file_record:
                    return {'success': False, 'error': 'File not found in database'}
                
                # Collect all associated files
                files_to_delete = []
                
                if file_record.uploaded_file_path:
                    files_to_delete.extend([
                        os.path.join('uploads', file_record.uploaded_file_path),
                        os.path.join('backups', file_record.uploaded_file_path)
                    ])
                
                if file_record.results_file:
                    results_base = file_record.results_file.replace('.json', '')
                    files_to_delete.extend([
                        os.path.join('uploads', file_record.results_file),
                        os.path.join('uploads', f"{results_base}_backup.json"),
                        os.path.join('backups', f"{results_base}_backup.json")
                    ])
                
                if file_record.output_file:
                    files_to_delete.append(os.path.join('uploads', file_record.output_file))
                
                # Delete database record first
                db.session.delete(file_record)
                db.session.commit()
                
                # Clean up files
                deleted_files = 0
                for file_path in files_to_delete:
                    if os.path.exists(file_path):
                        try:
                            os.remove(file_path)
                            deleted_files += 1
                        except Exception as e:
                            self.logger.error(f"Failed to delete file {file_path}: {str(e)}")
                
                self.logger.info(f"Successfully deleted file {file_id} with {deleted_files} associated files")
                return {
                    'success': True,
                    'message': 'File deleted successfully',
                    'files_cleaned': deleted_files
                }
                
            except Exception as e:
                db.session.rollback()
                self.logger.error(f"Error in safe_delete_file: {str(e)}")
                return {'success': False, 'error': str(e)}

    def get_database_statistics(self):
        """Get comprehensive database statistics."""
        with app.app_context():
            try:
                total_files = UploadedFile.query.count()
                
                # Files by workspace
                denv_files = UploadedFile.query.filter_by(workspace='denv').count()
                chikv_files = UploadedFile.query.filter_by(workspace='chikv').count()
                
                # Recent uploads
                from datetime import datetime, timedelta
                recent_cutoff = datetime.utcnow() - timedelta(days=7)
                recent_files = UploadedFile.query.filter(
                    UploadedFile.upload_time >= recent_cutoff
                ).count()
                
                # Mutation statistics
                total_positions = db.session.query(
                    db.func.sum(UploadedFile.total_positions)
                ).scalar() or 0
                
                total_mutations = db.session.query(
                    db.func.sum(UploadedFile.mutation_count)
                ).scalar() or 0
                
                return {
                    'total_files': total_files,
                    'denv_files': denv_files,
                    'chikv_files': chikv_files,
                    'recent_files': recent_files,
                    'total_positions': total_positions,
                    'total_mutations': total_mutations,
                    'timestamp': datetime.utcnow().isoformat()
                }
                
            except Exception as e:
                self.logger.error(f"Error getting database statistics: {str(e)}")
                return None

if __name__ == '__main__':
    manager = DatabaseIntegrityManager()
    
    print("=== Database Integrity Check ===")
    inconsistencies = manager.verify_database_consistency()
    if inconsistencies:
        print(f"Found {len(inconsistencies)} inconsistencies")
        for issue in inconsistencies:
            print(f"  - {issue['filename']} ({issue['workspace']}): {', '.join(issue['issues'])}")
    else:
        print("Database is consistent")
    
    print("\n=== Cleanup Operations ===")
    orphaned_entries = manager.clean_orphaned_database_entries()
    orphaned_files = manager.clean_orphaned_files()
    
    print(f"Removed {orphaned_entries or 0} orphaned database entries")
    print(f"Removed {orphaned_files or 0} orphaned files")
    
    print("\n=== Database Statistics ===")
    stats = manager.get_database_statistics()
    if stats:
        print(f"Total files: {stats['total_files']}")
        print(f"DENV files: {stats['denv_files']}")
        print(f"CHIKV files: {stats['chikv_files']}")
        print(f"Recent files (7 days): {stats['recent_files']}")
        print(f"Total positions analyzed: {stats['total_positions']:,}")
        print(f"Total mutations found: {stats['total_mutations']:,}")