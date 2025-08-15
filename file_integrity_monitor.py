#!/usr/bin/env python3
"""
Continuous file integrity monitoring and auto-recovery system
Prevents and automatically fixes file corruption issues
"""

import os
import json
import logging
import schedule
import time
from datetime import datetime, timedelta
from app import app
from models import db, UploadedFile

class FileIntegrityMonitor:
    def __init__(self):
        self.upload_dir = 'uploads'
        self.backup_dir = 'backups'
        self.last_check = None
        
        # Ensure backup directory exists
        os.makedirs(self.backup_dir, exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('file_integrity.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('FileIntegrityMonitor')

    def check_file_integrity(self):
        """Comprehensive file integrity check with auto-recovery"""
        with app.app_context():
            self.logger.info("Starting file integrity check...")
            
            files = UploadedFile.query.all()
            issues_found = 0
            issues_fixed = 0
            
            for file_record in files:
                try:
                    # Check original file
                    if file_record.uploaded_file_path:
                        original_path = os.path.join(self.upload_dir, file_record.uploaded_file_path)
                        if not os.path.exists(original_path):
                            self.logger.warning(f"Missing original file: {original_path}")
                            issues_found += 1
                            # Try to restore from backup
                            if self._restore_from_backup(file_record.uploaded_file_path):
                                issues_fixed += 1
                    
                    # Check results file
                    if file_record.results_file:
                        results_path = os.path.join(self.upload_dir, file_record.results_file)
                        backup_path = results_path.replace('.json', '_backup.json')
                        
                        if not os.path.exists(results_path):
                            self.logger.warning(f"Missing results file: {results_path}")
                            issues_found += 1
                            
                            # Try backup first
                            if os.path.exists(backup_path):
                                self._restore_results_from_backup(results_path, backup_path)
                                issues_fixed += 1
                            else:
                                # Try to regenerate
                                if self._regenerate_results(file_record):
                                    issues_fixed += 1
                        
                        # Ensure backup exists
                        if os.path.exists(results_path) and not os.path.exists(backup_path):
                            self._create_backup(results_path, backup_path)
                
                except Exception as e:
                    self.logger.error(f"Error checking file {file_record.id}: {str(e)}")
            
            self.last_check = datetime.now()
            self.logger.info(f"Integrity check complete. Issues found: {issues_found}, Issues fixed: {issues_fixed}")
            
            return {'issues_found': issues_found, 'issues_fixed': issues_fixed}

    def _restore_from_backup(self, filename):
        """Restore original file from backup"""
        backup_path = os.path.join(self.backup_dir, filename)
        original_path = os.path.join(self.upload_dir, filename)
        
        if os.path.exists(backup_path):
            try:
                with open(backup_path, 'rb') as src, open(original_path, 'wb') as dst:
                    dst.write(src.read())
                self.logger.info(f"Restored {filename} from backup")
                return True
            except Exception as e:
                self.logger.error(f"Failed to restore {filename}: {str(e)}")
        return False

    def _restore_results_from_backup(self, results_path, backup_path):
        """Restore results file from backup"""
        try:
            with open(backup_path, 'r') as src, open(results_path, 'w') as dst:
                data = json.load(src)
                json.dump(data, dst, indent=2)
            self.logger.info(f"Restored results file from backup: {results_path}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to restore results from backup: {str(e)}")
            return False

    def _regenerate_results(self, file_record):
        """Regenerate results from original file"""
        if not file_record.uploaded_file_path:
            return False
            
        original_path = os.path.join(self.upload_dir, file_record.uploaded_file_path)
        if not os.path.exists(original_path):
            return False
        
        try:
            from mutation_analyzer import analyze_mutations
            results, output_file = analyze_mutations(original_path)
            
            # Save results
            results_path = os.path.join(self.upload_dir, file_record.results_file)
            with open(results_path, 'w') as f:
                json.dump(results, f, indent=2)
            
            # Create backup
            backup_path = results_path.replace('.json', '_backup.json')
            with open(backup_path, 'w') as f:
                json.dump(results, f, indent=2)
            
            self.logger.info(f"Regenerated results for {file_record.original_filename}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to regenerate results: {str(e)}")
            return False

    def _create_backup(self, source_path, backup_path):
        """Create backup copy of file"""
        try:
            if source_path.endswith('.json'):
                with open(source_path, 'r') as src, open(backup_path, 'w') as dst:
                    data = json.load(src)
                    json.dump(data, dst, indent=2)
            else:
                with open(source_path, 'rb') as src, open(backup_path, 'wb') as dst:
                    dst.write(src.read())
            self.logger.info(f"Created backup: {backup_path}")
        except Exception as e:
            self.logger.error(f"Failed to create backup: {str(e)}")

    def backup_all_files(self):
        """Create backups of all current files"""
        with app.app_context():
            files = UploadedFile.query.all()
            backup_count = 0
            
            for file_record in files:
                # Backup original file
                if file_record.uploaded_file_path:
                    original_path = os.path.join(self.upload_dir, file_record.uploaded_file_path)
                    backup_path = os.path.join(self.backup_dir, file_record.uploaded_file_path)
                    
                    if os.path.exists(original_path):
                        self._create_backup(original_path, backup_path)
                        backup_count += 1
                
                # Backup results file
                if file_record.results_file:
                    results_path = os.path.join(self.upload_dir, file_record.results_file)
                    if os.path.exists(results_path):
                        backup_path = results_path.replace('.json', '_backup.json')
                        if not os.path.exists(backup_path):
                            self._create_backup(results_path, backup_path)
                            backup_count += 1
            
            self.logger.info(f"Created {backup_count} backup files")

    def start_monitoring(self):
        """Start continuous monitoring"""
        self.logger.info("Starting file integrity monitoring...")
        
        # Initial backup
        self.backup_all_files()
        
        # Schedule regular checks
        schedule.every(30).minutes.do(self.check_file_integrity)
        schedule.every(6).hours.do(self.backup_all_files)
        
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute

if __name__ == '__main__':
    monitor = FileIntegrityMonitor()
    monitor.start_monitoring()