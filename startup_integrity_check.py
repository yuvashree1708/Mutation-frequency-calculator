#!/usr/bin/env python3
"""
Startup integrity check - runs when application starts
Ensures all files are intact before serving requests
"""

import os
import json
import logging
from app import app
from models import db, UploadedFile

def startup_integrity_check():
    """Perform integrity check on application startup"""
    logging.info("=== STARTUP INTEGRITY CHECK ===")
    
    with app.app_context():
        try:
            # Test database connection
            db.session.execute("SELECT 1")
            db.session.commit()
            logging.info("✓ Database connection verified")
            
            # Check all files
            files = UploadedFile.query.all()
            logging.info(f"Checking {len(files)} files in database...")
            
            issues = []
            fixed = []
            
            for file_record in files:
                file_id = file_record.id
                
                # Check original file
                if file_record.uploaded_file_path:
                    original_path = os.path.join('uploads', file_record.uploaded_file_path)
                    if not os.path.exists(original_path):
                        issues.append(f"Missing original: {file_record.uploaded_file_path}")
                        
                        # Try backup restore
                        backup_path = os.path.join('backups', file_record.uploaded_file_path)
                        if os.path.exists(backup_path):
                            try:
                                with open(backup_path, 'rb') as src, open(original_path, 'wb') as dst:
                                    dst.write(src.read())
                                fixed.append(f"Restored: {file_record.uploaded_file_path}")
                                logging.info(f"✓ Restored {file_record.uploaded_file_path} from backup")
                            except Exception as e:
                                logging.error(f"✗ Failed to restore {file_record.uploaded_file_path}: {str(e)}")
                
                # Check results file
                if file_record.results_file:
                    results_path = os.path.join('uploads', file_record.results_file)
                    backup_path = results_path.replace('.json', '_backup.json')
                    
                    if not os.path.exists(results_path):
                        issues.append(f"Missing results: {file_record.results_file}")
                        
                        # Try backup restore
                        if os.path.exists(backup_path):
                            try:
                                with open(backup_path, 'r') as src, open(results_path, 'w') as dst:
                                    data = json.load(src)
                                    json.dump(data, dst, indent=2)
                                fixed.append(f"Restored: {file_record.results_file}")
                                logging.info(f"✓ Restored {file_record.results_file} from backup")
                            except Exception as e:
                                logging.error(f"✗ Failed to restore {file_record.results_file}: {str(e)}")
                    
                    # Ensure backup exists
                    elif not os.path.exists(backup_path):
                        try:
                            with open(results_path, 'r') as src, open(backup_path, 'w') as dst:
                                data = json.load(src)
                                json.dump(data, dst, indent=2)
                            logging.info(f"✓ Created missing backup: {backup_path}")
                        except Exception as e:
                            logging.error(f"✗ Failed to create backup {backup_path}: {str(e)}")
            
            # Summary
            logging.info(f"=== INTEGRITY CHECK COMPLETE ===")
            logging.info(f"Files checked: {len(files)}")
            logging.info(f"Issues found: {len(issues)}")
            logging.info(f"Issues fixed: {len(fixed)}")
            
            if issues:
                logging.warning("Issues detected:")
                for issue in issues:
                    logging.warning(f"  - {issue}")
            
            if fixed:
                logging.info("Issues fixed:")
                for fix in fixed:
                    logging.info(f"  + {fix}")
            
            if not issues:
                logging.info("✓ All files verified - system healthy")
            
            return len(issues) == 0
            
        except Exception as e:
            logging.error(f"✗ Startup integrity check failed: {str(e)}")
            return False

if __name__ == '__main__':
    startup_integrity_check()