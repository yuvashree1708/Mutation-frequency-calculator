import os
import logging
from datetime import datetime
import json
from flask import Flask, render_template, request, redirect, url_for, flash, send_file, jsonify, session
from werkzeug.utils import secure_filename
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_sqlalchemy import SQLAlchemy
from mutation_analyzer import analyze_mutations
import tempfile
import shutil
import uuid

# Configure logging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Database configuration
database_url = os.environ.get("DATABASE_URL")
if not database_url:
    # Fallback for local development
    database_url = "sqlite:///mutations.db"

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
    "pool_timeout": 20,
    "max_overflow": 0,
    "connect_args": {"connect_timeout": 60}
}
# Increase max content length for large file uploads (3GB)
app.config['MAX_CONTENT_LENGTH'] = 3 * 1024 * 1024 * 1024  # 3GB
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Import database models after app configuration
from models import db, UploadedFile

# Initialize the database with the app
db.init_app(app)

# Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'fasta', 'fa', 'txt', 'csv', 'fas', 'aln', 'seq', 'msa', 'phylip', 'phy', 'nex', 'nexus'}  # Support extensive alignment formats
MAX_FILE_SIZE = 3 * 1024 * 1024 * 1024  # 3GB for very large genomic datasets

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Create database tables and add connection health check
with app.app_context():
    try:
        db.create_all()
        # Test connection with proper SQLAlchemy syntax
        from sqlalchemy import text
        db.session.execute(text("SELECT 1"))
        db.session.commit()
        logging.info("Database connection established successfully")
        
        # Run startup integrity check
        try:
            from startup_integrity_check import startup_integrity_check
            startup_integrity_check()
        except Exception as integrity_error:
            logging.error(f"Startup integrity check failed: {str(integrity_error)}")
            
    except Exception as db_error:
        logging.error(f"Database initialization failed: {str(db_error)}")
        # Continue anyway for debugging purposes

def allowed_file(filename):
    """Check if file extension is allowed."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    """Main landing page with workspace selection."""
    return render_template('index.html')

@app.route('/workspace/<workspace_name>')
def workspace(workspace_name):
    """Workspace dashboard for DENV or CHIKV analysis."""
    if workspace_name not in ['denv', 'chikv']:
        return redirect(url_for('index'))
    
    # Get keyword from URL parameter or session
    keyword = request.args.get('keyword') or session.get(f'{workspace_name}_keyword')
    
    # For DENV and CHIKV workspaces, enforce the exact keywords
    if workspace_name == 'denv' and keyword != 'DENV':
        keyword = 'DENV'
    elif workspace_name == 'chikv' and keyword != 'CHIKV':
        keyword = 'CHIKV'
    
    # Store keyword in session for this workspace
    session[f'{workspace_name}_keyword'] = keyword
    session.permanent = True
    logging.info(f"Keyword stored in session: {keyword} for workspace: {workspace_name}")
    
    # Load files from database for this keyword
    try:
        uploaded_files = UploadedFile.get_keyword_files(workspace_name, keyword, limit=50)
        history = [file.to_dict() for file in uploaded_files]
        access_mode = 'keyword-shared'
    except Exception as e:
        logging.error(f"Error loading files from database: {str(e)}")
        history = []
        access_mode = 'keyword-shared'
    
    return render_template('workspace.html', 
                         workspace=workspace_name, 
                         history=history,
                         access_mode=access_mode,
                         keyword=keyword)

@app.route('/upload/<workspace_name>', methods=['POST'])
def upload_file(workspace_name):
    """Handle file upload and process mutation analysis via AJAX."""
    logging.info(f"Upload request received for workspace: {workspace_name}")
    
    if workspace_name not in ['denv', 'chikv']:
        logging.error(f"Invalid workspace: {workspace_name}")
        return jsonify({'error': 'Invalid workspace'}), 400
    
    # Get keyword from session or set default for workspace
    keyword = session.get(f'{workspace_name}_keyword')
    logging.info(f"Session keyword for {workspace_name}: {keyword}")
    
    # If no keyword in session, use default based on workspace
    if not keyword:
        if workspace_name == 'denv':
            keyword = 'DENV'
        elif workspace_name == 'chikv':
            keyword = 'CHIKV'
        
        # Store the keyword in session
        session[f'{workspace_name}_keyword'] = keyword
        session.permanent = True
        logging.info(f"Set default keyword for {workspace_name}: {keyword}")
        
    if 'file' not in request.files:
        logging.error("No file in request")
        return jsonify({'error': 'No file selected'}), 400
    
    file = request.files['file']
    if file.filename == '':
        logging.error("Empty filename")
        return jsonify({'error': 'No file selected'}), 400
    
    logging.info(f"Processing file: {file.filename}, size: {len(file.read())} bytes")
    file.seek(0)  # Reset file pointer after reading size
    
    if not allowed_file(file.filename):
        logging.error(f"Invalid file format: {file.filename}")
        return jsonify({'error': 'Invalid file format. Supported formats: FASTA, FA, TXT, CSV, FAS, ALN, SEQ, MSA, PHYLIP, PHY, NEX, NEXUS'}), 400
    
    filepath = None
    try:
        # Generate unique file ID and save uploaded file permanently with atomic write
        file_id = str(uuid.uuid4())
        filename = secure_filename(file.filename or 'uploaded_file')
        # Store with unique ID prefix for permanent access
        permanent_filename = f"{file_id}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], permanent_filename)
        
        # Atomic file save - write to temp file then rename
        temp_filepath = filepath + '.tmp'
        file.save(temp_filepath)
        os.rename(temp_filepath, filepath)  # Atomic operation
        
        # Create immediate backup of uploaded file
        backup_dir = os.path.join(app.config['UPLOAD_FOLDER'], '..', 'backups')
        os.makedirs(backup_dir, exist_ok=True)
        backup_filepath = os.path.join(backup_dir, permanent_filename)
        with open(filepath, 'rb') as src, open(backup_filepath, 'wb') as dst:
            dst.write(src.read())
        
        logging.info(f"File saved permanently: {permanent_filename}")
        
        # Process the file
        results, output_file = analyze_mutations(filepath)
        
        # Calculate summary statistics and mutation positions
        total_positions = len(results)
        mutated_positions = [r['Position'] for r in results if r['Color'] == 'Red']
        low_conf_positions = [r['Position'] for r in results if r['Ambiguity'] == 'Low-confidence']
        
        # Store results permanently with backup for reliability
        import json
        results_file = f"results_{file_id}.json"
        results_path = os.path.join(app.config['UPLOAD_FOLDER'], results_file)
        
        # Save primary results file with atomic write
        temp_results_path = results_path + '.tmp'
        with open(temp_results_path, 'w') as f:
            json.dump(results, f, indent=2)
        os.rename(temp_results_path, results_path)  # Atomic operation
        
        # Create backup copy for redundancy
        backup_file = f"results_{file_id}_backup.json"
        backup_path = os.path.join(app.config['UPLOAD_FOLDER'], backup_file)
        temp_backup_path = backup_path + '.tmp'
        with open(temp_backup_path, 'w') as f:
            json.dump(results, f, indent=2)
        os.rename(temp_backup_path, backup_path)  # Atomic operation
        
        # Create permanent backup in separate directory
        backup_dir = os.path.join(app.config['UPLOAD_FOLDER'], '..', 'backups')
        os.makedirs(backup_dir, exist_ok=True)
        permanent_backup = os.path.join(backup_dir, backup_file)
        with open(permanent_backup, 'w') as f:
            json.dump(results, f, indent=2)
        
        logging.info(f"Results saved with multiple backups: {results_file}, {backup_file}, and permanent backup")
        
        # Save file information to database with full transactional integrity
        db_transaction_successful = False
        
        try:
            # Begin explicit database transaction
            db.session.begin()
            
            new_file = UploadedFile()
            new_file.id = file_id
            new_file.filename = filename
            new_file.original_filename = file.filename
            new_file.workspace = workspace_name
            new_file.keyword = keyword
            new_file.upload_time = datetime.utcnow()
            new_file.results_file = results_file
            new_file.output_file = output_file
            new_file.total_positions = total_positions
            new_file.mutation_count = len(mutated_positions)
            new_file.conserved_count = total_positions - len(mutated_positions)
            new_file.mutated_positions = json.dumps(mutated_positions)
            new_file.low_conf_positions = json.dumps(low_conf_positions)
            new_file.uploaded_file_path = permanent_filename
            
            # Add to session
            db.session.add(new_file)
            
            # Commit the transaction
            db.session.commit()
            db_transaction_successful = True
            
            logging.info(f"Database transaction completed successfully: {file_id}")
            logging.debug(f"File processed: {filename}, mutations at positions: {mutated_positions[:10]}...")
            
        except Exception as db_error:
            db.session.rollback()
            logging.error(f"Database transaction failed, rolling back: {str(db_error)}")
            
            # Complete cleanup of all created files if database transaction fails
            cleanup_files = [
                filepath,  # Original uploaded file
                backup_filepath,  # Backup of uploaded file
                results_path,  # Results file
                backup_path,  # Backup results file
                permanent_backup  # Permanent backup
            ]
            
            for cleanup_file in cleanup_files:
                if os.path.exists(cleanup_file):
                    try:
                        os.remove(cleanup_file)
                        logging.info(f"Cleaned up file after DB failure: {cleanup_file}")
                    except Exception as cleanup_error:
                        logging.error(f"Failed to cleanup file {cleanup_file}: {str(cleanup_error)}")
            
            raise Exception(f"Database transaction failed - all files cleaned up: {str(db_error)}")
        
        if not db_transaction_successful:
            raise Exception("Database transaction was not completed successfully")
        
        return jsonify({
            'success': True,
            'file_id': file_id,
            'filename': filename,
            'message': f'File processed successfully. Found {len(mutated_positions)} mutations in {total_positions} positions.'
        })
        
    except Exception as e:
        logging.error(f"Error processing file: {str(e)}")
        # Don't clean up uploaded files on error - keep them for debugging and potential recovery
        logging.error(f"File processing failed but uploaded file preserved: {filepath if 'filepath' in locals() else 'unknown'}")
        return jsonify({'error': f'Error processing file: {str(e)}'}), 500

@app.route('/download/<filename>')
def download_file(filename):
    """Download the generated CSV file."""
    try:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        logging.debug(f"Attempting to download file: {filepath}")
        
        if os.path.exists(filepath):
            return send_file(filepath, as_attachment=True, download_name=filename)
        else:
            logging.error(f"File not found for download: {filepath}")
            return jsonify({'error': 'File not found'}), 404
    except Exception as e:
        logging.error(f"Error downloading file: {str(e)}")
        return jsonify({'error': 'Error downloading file'}), 500

@app.route('/api/<workspace_name>/file/<file_id>')
def get_file_data(workspace_name, file_id):
    """Get file data for display in the main table with enhanced error handling."""
    logging.info(f"Request for file data: workspace={workspace_name}, file_id={file_id}")
    
    if workspace_name not in ['denv', 'chikv']:
        logging.error(f"Invalid workspace requested: {workspace_name}")
        return jsonify({'error': 'Invalid workspace'}), 400
    
    # Get keyword from session or set default
    keyword = session.get(f'{workspace_name}_keyword')
    if not keyword:
        keyword = 'DENV' if workspace_name == 'denv' else 'CHIKV'
        session[f'{workspace_name}_keyword'] = keyword
        session.permanent = True
        logging.info(f"Set default keyword for {workspace_name}: {keyword}")
    
    # Test database connectivity first
    try:
        from sqlalchemy import text
        db.session.execute(text("SELECT 1"))
        db.session.commit()
    except Exception as db_test_error:
        logging.error(f"Database connectivity test failed: {str(db_test_error)}")
        try:
            db.session.rollback()
            db.engine.dispose()  # Force reconnection
        except:
            pass
    
    # Load file from database with keyword check
    try:
        uploaded_file = UploadedFile.get_file_by_id(file_id, keyword=keyword)
        if not uploaded_file:
            logging.error(f"File not found in database: file_id={file_id}, keyword={keyword}")
            return jsonify({'error': 'File not found'}), 404
            
        if uploaded_file.workspace != workspace_name:
            logging.error(f"Workspace mismatch: expected={workspace_name}, found={uploaded_file.workspace}")
            return jsonify({'error': 'Access denied - workspace mismatch'}), 403
        
        file_data = uploaded_file.to_dict()
        logging.info(f"File data loaded successfully: {file_data['original_filename']}")
    except Exception as e:
        logging.error(f"Database error loading file: {str(e)}")
        # Try to reconnect and retry once
        try:
            db.session.rollback()
            db.engine.dispose()
            uploaded_file = UploadedFile.get_file_by_id(file_id, keyword=keyword)
            if uploaded_file and uploaded_file.workspace == workspace_name:
                file_data = uploaded_file.to_dict()
                logging.info(f"File data loaded on retry: {file_data['original_filename']}")
            else:
                return jsonify({'error': 'File not found after retry'}), 404
        except Exception as retry_error:
            logging.error(f"Database retry failed: {str(retry_error)}")
            return jsonify({'error': f'Database connection failed: {str(e)}'}), 500
    
    # Load results from file (supports both legacy pickle and new JSON formats)
    try:
        import json
        import pickle
        results_path = os.path.join(app.config['UPLOAD_FOLDER'], file_data['results_file'])
        
        if not os.path.exists(results_path):
            logging.error(f"Primary results file missing: {results_path}")
            
            # Try backup file first
            backup_file = file_data['results_file'].replace('.json', '_backup.json')
            backup_path = os.path.join(app.config['UPLOAD_FOLDER'], backup_file)
            
            if os.path.exists(backup_path):
                logging.info(f"Using backup results file: {backup_path}")
                results_path = backup_path
            else:
                logging.error(f"Backup file also missing: {backup_path}")
                # Try to regenerate results from original file if it exists
                # Check multiple possible locations for the original file
                possible_paths = []
                if uploaded_file.uploaded_file_path:
                    possible_paths.append(os.path.join(app.config['UPLOAD_FOLDER'], uploaded_file.uploaded_file_path))
                
                # Also try the filename and variations
                possible_paths.append(os.path.join(app.config['UPLOAD_FOLDER'], uploaded_file.filename))
                possible_paths.append(os.path.join(app.config['UPLOAD_FOLDER'], f"{file_id}_{uploaded_file.filename}"))
                
                # Try to find any matching file
                original_file_path = None
                for path in possible_paths:
                    if os.path.exists(path):
                        original_file_path = path
                        break
            
            if original_file_path:
                logging.info(f"Regenerating results from original file: {original_file_path}")
                try:
                    from mutation_analyzer import analyze_mutations
                    results, output_file = analyze_mutations(original_file_path)
                    
                    # Save regenerated results with backup
                    with open(results_path, 'w') as f:
                        json.dump(results, f)
                    
                    # Create backup copy for reliability
                    backup_path = results_path.replace('.json', '_backup.json')
                    with open(backup_path, 'w') as f:
                        json.dump(results, f)
                    
                    logging.info(f"Results regenerated successfully with backup: {results_path}")
                except Exception as regen_error:
                    logging.error(f"Failed to regenerate results: {str(regen_error)}")
                    return jsonify({'error': 'Results file not found and cannot be regenerated'}), 404
            else:
                logging.error(f"Original file also missing: {original_file_path}")
                return jsonify({'error': 'Both results and original files are missing'}), 404
        
        # Check if it's a legacy pickle file or new JSON file
        if file_data['results_file'].endswith('.pkl'):
            # Legacy pickle file - load and convert to JSON
            with open(results_path, 'rb') as f:
                results = pickle.load(f)
            
            # Convert to JSON format for future use
            json_path = results_path.replace('.pkl', '.json')
            with open(json_path, 'w') as f:
                json.dump(results, f)
            
            # Update file_data to point to new JSON file
            file_data['results_file'] = file_data['results_file'].replace('.pkl', '.json')
            
            # Update database to reference JSON file
            try:
                uploaded_file.results_file = file_data['results_file']
                db.session.commit()
            except Exception as db_error:
                logging.error(f"Error updating database: {str(db_error)}")
                db.session.rollback()
            
            # Clean up old pickle file
            try:
                os.remove(results_path)
            except:
                pass
        else:
            # New JSON file
            with open(results_path, 'r') as f:
                results = json.load(f)
            
        file_data['results'] = results
        
        return jsonify({
            'success': True,
            'file_data': file_data
        })
        
    except Exception as e:
        logging.error(f"Error loading results file: {str(e)}")
        return jsonify({'error': 'Failed to load results data'}), 500

@app.route('/api/<workspace_name>/delete-file/<file_id>', methods=['DELETE'])
def delete_file(workspace_name, file_id):
    """Delete a specific file from workspace with complete cleanup."""
    keyword = session.get('keyword')
    if not keyword or workspace_name.lower() not in ['denv', 'chikv']:
        return jsonify({'error': 'Invalid workspace or session expired'}), 400
    
    try:
        # Begin database transaction
        db.session.begin()
        
        # Find the file record
        file_record = UploadedFile.query.filter_by(
            id=file_id, 
            workspace=workspace_name.lower()
        ).first()
        
        if not file_record:
            return jsonify({'error': 'File not found'}), 404
        
        # Collect all associated files for cleanup
        files_to_delete = []
        
        if file_record.uploaded_file_path:
            files_to_delete.extend([
                os.path.join(app.config['UPLOAD_FOLDER'], file_record.uploaded_file_path),
                os.path.join('backups', file_record.uploaded_file_path)
            ])
        
        if file_record.results_file:
            results_base = file_record.results_file.replace('.json', '')
            files_to_delete.extend([
                os.path.join(app.config['UPLOAD_FOLDER'], file_record.results_file),
                os.path.join(app.config['UPLOAD_FOLDER'], f"{results_base}_backup.json"),
                os.path.join('backups', f"{results_base}_backup.json")
            ])
        
        if file_record.output_file:
            files_to_delete.append(os.path.join(app.config['UPLOAD_FOLDER'], file_record.output_file))
        
        # Delete database record first
        db.session.delete(file_record)
        db.session.commit()
        
        # Clean up associated files
        deleted_files = 0
        for file_path in files_to_delete:
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    deleted_files += 1
                    logging.info(f"Deleted file: {file_path}")
                except Exception as file_error:
                    logging.error(f"Failed to delete file {file_path}: {str(file_error)}")
        
        logging.info(f"Successfully deleted file {file_id} and {deleted_files} associated files")
        return jsonify({
            'success': True,
            'message': f'File deleted successfully',
            'files_cleaned': deleted_files
        })
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error deleting file {file_id}: {str(e)}")
        return jsonify({'error': f'Failed to delete file: {str(e)}'}), 500

@app.route('/api/<workspace_name>/history')
def get_history(workspace_name):
    """Get current workspace file history."""
    if workspace_name not in ['denv', 'chikv']:
        return jsonify({'error': 'Invalid workspace'}), 400
    
    # Get keyword from session
    keyword = session.get(f'{workspace_name}_keyword')
    if not keyword:
        return jsonify({'error': 'No keyword found. Please refresh the page.'}), 400
    
    # Load files from database for this keyword
    try:
        uploaded_files = UploadedFile.get_keyword_files(workspace_name, keyword, limit=50)
        history = [file.to_dict() for file in uploaded_files]
        return jsonify({
            'success': True,
            'history': history
        })
    except Exception as e:
        logging.error(f"Error loading history from database: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Database error',
            'history': []
        })

@app.route('/api/<workspace_name>/clear-history', methods=['POST'])
def clear_history(workspace_name):
    """Clear workspace file history with complete transactional integrity."""
    if workspace_name not in ['denv', 'chikv']:
        return jsonify({'error': 'Invalid workspace'}), 400
    
    # Get keyword from session
    keyword = session.get(f'{workspace_name}_keyword')
    if not keyword:
        return jsonify({'error': 'No keyword found. Please refresh the page.'}), 400
    
    try:
        # Begin database transaction
        db.session.begin()
        
        # Get all files for the workspace and keyword
        files_to_delete = UploadedFile.get_keyword_files(workspace_name, keyword, limit=1000)
        files_count = len(files_to_delete)
        
        if files_count == 0:
            return jsonify({
                'success': True,
                'message': f'{workspace_name.upper()} workspace is already empty',
                'files_deleted': 0,
                'files_cleaned': 0
            })
        
        # Collect all files for cleanup
        all_files_to_delete = []
        
        for uploaded_file in files_to_delete:
            # Original uploaded file
            if uploaded_file.uploaded_file_path:
                all_files_to_delete.extend([
                    os.path.join(app.config['UPLOAD_FOLDER'], uploaded_file.uploaded_file_path),
                    os.path.join('backups', uploaded_file.uploaded_file_path)
                ])
            
            # Results files
            if uploaded_file.results_file:
                results_base = uploaded_file.results_file.replace('.json', '')
                all_files_to_delete.extend([
                    os.path.join(app.config['UPLOAD_FOLDER'], uploaded_file.results_file),
                    os.path.join(app.config['UPLOAD_FOLDER'], f"{results_base}_backup.json"),
                    os.path.join('backups', f"{results_base}_backup.json")
                ])
            
            # Output files
            if uploaded_file.output_file:
                all_files_to_delete.append(os.path.join(app.config['UPLOAD_FOLDER'], uploaded_file.output_file))
        
        # Delete from database first (transactional)
        UploadedFile.query.filter_by(workspace=workspace_name, keyword=keyword).delete()
        db.session.commit()
        
        # Clean up all associated files
        deleted_files = 0
        for file_path in all_files_to_delete:
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    deleted_files += 1
                    logging.info(f"Deleted file: {file_path}")
                except Exception as file_error:
                    logging.error(f"Failed to delete file {file_path}: {str(file_error)}")
        
        logging.info(f"Cleared {files_count} database records and {deleted_files} files from {workspace_name} workspace")
        return jsonify({
            'success': True, 
            'message': f'History cleared for {workspace_name.upper()} workspace', 
            'files_deleted': files_count,
            'files_cleaned': deleted_files
        })
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error clearing workspace history: {str(e)}")
        return jsonify({'error': f'Failed to clear workspace history: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
