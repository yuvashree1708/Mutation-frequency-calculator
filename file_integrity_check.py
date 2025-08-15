#!/usr/bin/env python3
"""
File integrity checker for mutation analysis application.
Ensures all uploaded files and results are properly stored and accessible.
"""

import os
import json
import logging
from models import db, UploadedFile

def check_file_integrity():
    """Check integrity of all uploaded files and their results."""
    logging.basicConfig(level=logging.INFO)
    
    with app.app_context():
        files = UploadedFile.query.all()
        
        missing_files = []
        missing_results = []
        fixed_files = []
        
        for file_record in files:
            # Check original file
            if file_record.uploaded_file_path:
                file_path = os.path.join('uploads', file_record.uploaded_file_path)
                if not os.path.exists(file_path):
                    missing_files.append(file_record)
                    logging.error(f"Missing original file: {file_path}")
            
            # Check results file
            if file_record.results_file:
                results_path = os.path.join('uploads', file_record.results_file)
                backup_path = results_path.replace('.json', '_backup.json')
                
                if not os.path.exists(results_path):
                    if os.path.exists(backup_path):
                        # Restore from backup
                        logging.info(f"Restoring results from backup: {backup_path}")
                        with open(backup_path, 'r') as f:
                            results = json.load(f)
                        with open(results_path, 'w') as f:
                            json.dump(results, f, indent=2)
                        fixed_files.append(file_record)
                    else:
                        missing_results.append(file_record)
                        logging.error(f"Missing results file: {results_path}")
        
        print(f"\nIntegrity Check Results:")
        print(f"Total files: {len(files)}")
        print(f"Missing original files: {len(missing_files)}")
        print(f"Missing results files: {len(missing_results)}")
        print(f"Fixed from backup: {len(fixed_files)}")
        
        return {
            'total': len(files),
            'missing_files': missing_files,
            'missing_results': missing_results,
            'fixed': fixed_files
        }

if __name__ == '__main__':
    from app import app
    check_file_integrity()