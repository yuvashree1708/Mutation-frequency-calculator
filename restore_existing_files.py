#!/usr/bin/env python3
"""
Create database entries for existing files in uploads directory
"""

import os
import json
import uuid
import logging
from datetime import datetime
from app import app
from models import db, UploadedFile

def restore_existing_files():
    """Create database entries for files that exist but aren't in database."""
    logging.basicConfig(level=logging.INFO)
    
    with app.app_context():
        # Map files to their results
        file_mappings = [
            {
                'original_file': '6418ffd0-0cc2-470f-958f-42db14785abf_NSP1Conserved_set2022.fasta',
                'results_file': None,  # No matching results
                'file_id': '6418ffd0-0cc2-470f-958f-42db14785abf',
                'display_name': 'NSP1 Conserved set 2022.fasta'
            },
            {
                'original_file': '6deb15ad-e60f-4ddd-a3d1-3718b78a0ae9_NSP2AConserved_set2022.fasta',
                'results_file': None,  # No matching results
                'file_id': '6deb15ad-e60f-4ddd-a3d1-3718b78a0ae9',
                'display_name': 'NSP2A Conserved set 2022.fasta'
            },
            {
                'original_file': '878eca02-c4f0-45cc-9bbf-e1fa05223cee_NSP2Bconserved_set2022.fasta',
                'results_file': 'results_878eca02-c4f0-45cc-9bbf-e1fa05223cee.json',
                'file_id': '878eca02-c4f0-45cc-9bbf-e1fa05223cee',
                'display_name': 'NSP2B conserved set 2022.fasta'
            },
            {
                'original_file': 'ded99e3b-ed32-4116-a1f3-79cc6f61c79c_NSP1Conserved_set2022.fasta',
                'results_file': 'results_ded99e3b-ed32-4116-a1f3-79cc6f61c79c.json',
                'file_id': 'ded99e3b-ed32-4116-a1f3-79cc6f61c79c',
                'display_name': 'NSP1 Conserved set 2022.fasta'
            }
        ]
        
        created_count = 0
        for mapping in file_mappings:
            original_path = os.path.join('uploads', mapping['original_file'])
            
            if os.path.exists(original_path):
                print(f"Creating entry for: {mapping['display_name']}")
                
                # Create database entry
                new_file = UploadedFile()
                new_file.id = mapping['file_id']
                new_file.filename = mapping['original_file'].split('_', 1)[1]  # Remove UUID prefix
                new_file.original_filename = mapping['display_name']
                new_file.workspace = 'denv'
                new_file.keyword = 'DENV'
                new_file.upload_time = datetime.utcnow()
                new_file.uploaded_file_path = mapping['original_file']
                
                # Check if results file exists and load data
                if mapping['results_file']:
                    results_path = os.path.join('uploads', mapping['results_file'])
                    if os.path.exists(results_path):
                        new_file.results_file = mapping['results_file']
                        
                        # Load results to get statistics
                        try:
                            with open(results_path, 'r') as f:
                                results = json.load(f)
                            
                            new_file.total_positions = len(results)
                            mutated_positions = [r['Position'] for r in results if r.get('Color') == 'Red']
                            new_file.mutation_count = len(mutated_positions)
                            new_file.conserved_count = new_file.total_positions - new_file.mutation_count
                            new_file.mutated_positions = json.dumps(mutated_positions)
                            
                            low_conf_positions = [r['Position'] for r in results if r.get('Ambiguity') == 'Low-confidence']
                            new_file.low_conf_positions = json.dumps(low_conf_positions)
                            
                            print(f"  ✓ Results loaded: {new_file.total_positions} positions, {new_file.mutation_count} mutations")
                        except Exception as e:
                            print(f"  ✗ Error reading results: {str(e)}")
                            # Set default values
                            new_file.results_file = mapping['results_file']
                            new_file.total_positions = 0
                            new_file.mutation_count = 0
                            new_file.conserved_count = 0
                            new_file.mutated_positions = '[]'
                            new_file.low_conf_positions = '[]'
                    else:
                        print(f"  ! Results file missing: {results_path}")
                        continue
                else:
                    print(f"  ! No results file - will need to analyze")
                    # We'll skip files without results for now
                    continue
                
                # Add to database
                db.session.add(new_file)
                created_count += 1
            else:
                print(f"✗ Original file missing: {original_path}")
        
        # Commit all changes
        db.session.commit()
        print(f"\n✓ Created {created_count} database entries")

if __name__ == '__main__':
    restore_existing_files()