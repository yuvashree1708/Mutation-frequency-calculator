#!/usr/bin/env python3
"""
Clean up orphaned database entries and restore working files
"""

import os
import json
import logging
from app import app
from models import db, UploadedFile

def cleanup_and_restore():
    """Remove orphaned entries and match existing files to database."""
    logging.basicConfig(level=logging.INFO)
    
    with app.app_context():
        # Get all files in uploads directory
        uploaded_files = []
        results_files = []
        
        for filename in os.listdir('uploads'):
            filepath = os.path.join('uploads', filename)
            if filename.endswith(('.fasta', '.fa', '.txt', '.csv')):
                uploaded_files.append((filename, filepath))
            elif filename.startswith('results_') and filename.endswith('.json'):
                results_files.append((filename, filepath))
        
        print(f"Found {len(uploaded_files)} data files and {len(results_files)} results files")
        
        # Get all database entries
        db_entries = UploadedFile.query.all()
        print(f"Found {len(db_entries)} database entries")
        
        # Check which database entries have corresponding files
        valid_entries = []
        orphaned_entries = []
        
        for entry in db_entries:
            has_original = False
            has_results = False
            
            # Check for original file
            if entry.uploaded_file_path:
                original_path = os.path.join('uploads', entry.uploaded_file_path)
                if os.path.exists(original_path):
                    has_original = True
            
            # Check for results file
            if entry.results_file:
                results_path = os.path.join('uploads', entry.results_file)
                if os.path.exists(results_path):
                    has_results = True
            
            if has_original and has_results:
                valid_entries.append(entry)
                print(f"✓ Valid: {entry.original_filename}")
            else:
                orphaned_entries.append(entry)
                print(f"✗ Orphaned: {entry.original_filename} (original: {has_original}, results: {has_results})")
        
        # Remove orphaned entries
        print(f"\nRemoving {len(orphaned_entries)} orphaned entries...")
        for entry in orphaned_entries:
            db.session.delete(entry)
        
        db.session.commit()
        print(f"Cleanup complete. {len(valid_entries)} valid entries remain.")
        
        # Show remaining valid files
        print("\nRemaining files:")
        for entry in valid_entries:
            print(f"  - {entry.original_filename} (ID: {entry.id})")

if __name__ == '__main__':
    cleanup_and_restore()