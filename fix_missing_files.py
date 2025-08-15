#!/usr/bin/env python3
"""
Fix missing results files by regenerating them from available original files
"""

import os
import json
import logging
from app import app
from models import db, UploadedFile
from mutation_analyzer import analyze_mutations

def fix_missing_files():
    """Fix missing results files for existing database entries."""
    logging.basicConfig(level=logging.INFO)
    
    with app.app_context():
        # Get all files that might have missing results
        files = UploadedFile.query.all()
        fixed_count = 0
        missing_count = 0
        
        for file_record in files:
            print(f"\nChecking file: {file_record.original_filename} (ID: {file_record.id})")
            
            # Check if results file exists
            results_path = os.path.join('uploads', file_record.results_file)
            
            if not os.path.exists(results_path):
                print(f"  Missing results file: {results_path}")
                
                # Try to find the original file
                possible_paths = []
                if file_record.uploaded_file_path:
                    possible_paths.append(os.path.join('uploads', file_record.uploaded_file_path))
                
                # Also check for files in uploads directory that might match
                for filename in os.listdir('uploads'):
                    if (filename.endswith('.fasta') or filename.endswith('.fa') or 
                        filename.endswith('.txt') or filename.endswith('.csv')):
                        if (file_record.id in filename or 
                            file_record.filename in filename or 
                            file_record.original_filename.replace(' ', '').replace('(', '').replace(')', '') in filename.replace('(', '').replace(')', '')):
                            possible_paths.append(os.path.join('uploads', filename))
                
                # Try to regenerate from any matching file
                original_file_found = None
                for path in possible_paths:
                    if os.path.exists(path):
                        original_file_found = path
                        break
                
                if original_file_found:
                    print(f"  Found original file: {original_file_found}")
                    try:
                        # Regenerate results
                        results, output_file = analyze_mutations(original_file_found)
                        
                        # Save primary results
                        with open(results_path, 'w') as f:
                            json.dump(results, f, indent=2)
                        
                        # Save backup
                        backup_path = results_path.replace('.json', '_backup.json')
                        with open(backup_path, 'w') as f:
                            json.dump(results, f, indent=2)
                        
                        # Update database record if needed
                        file_record.uploaded_file_path = os.path.basename(original_file_found)
                        file_record.output_file = output_file
                        
                        # Recalculate statistics
                        file_record.total_positions = len(results)
                        mutated_positions = [r['Position'] for r in results if r['Color'] == 'Red']
                        file_record.mutation_count = len(mutated_positions)
                        file_record.conserved_count = file_record.total_positions - file_record.mutation_count
                        file_record.mutated_positions = json.dumps(mutated_positions)
                        
                        low_conf_positions = [r['Position'] for r in results if r.get('Ambiguity') == 'Low-confidence']
                        file_record.low_conf_positions = json.dumps(low_conf_positions)
                        
                        db.session.commit()
                        
                        print(f"  ✓ Regenerated results successfully")
                        fixed_count += 1
                    except Exception as e:
                        print(f"  ✗ Failed to regenerate: {str(e)}")
                        missing_count += 1
                else:
                    print(f"  ✗ No original file found")
                    missing_count += 1
            else:
                print(f"  ✓ Results file exists")
        
        print(f"\n=== Summary ===")
        print(f"Total files checked: {len(files)}")
        print(f"Files fixed: {fixed_count}")
        print(f"Files still missing: {missing_count}")

if __name__ == '__main__':
    fix_missing_files()