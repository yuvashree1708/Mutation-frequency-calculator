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
        # Test connection
        db.session.execute("SELECT 1")
        db.session.commit()
        logging.info("Database connection established successfully")
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
        # Generate unique file ID and save uploaded file permanently
        file_id = str(uuid.uuid4())
        filename = secure_filename(file.filename or 'uploaded_file')
        # Store with unique ID prefix for permanent access
        permanent_filename = f"{file_id}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], permanent_filename)
        file.save(filepath)
        
        logging.info(f"File saved permanently: {permanent_filename}")
        
        # Process the file
        results, output_file = analyze_mutations(filepath)
        
        # Calculate summary statistics and mutation positions
        total_positions = len(results)
        mutated_positions = [r['Position'] for r in results if r['Color'] == 'Red']
        low_conf_positions = [r['Position'] for r in results if r['Ambiguity'] == 'Low-confidence']
        
        # Store results in a temporary file to avoid large sessions
        import json
        results_file = f"results_{file_id}.json"
        results_path = os.path.join(app.config['UPLOAD_FOLDER'], results_file)
        
        with open(results_path, 'w') as f:
            json.dump(results, f)
        
        # Save file information to database for persistent storage
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
        
        # Don't commit yet - add file path first
        db.session.add(new_file)
        
        logging.debug(f"File processed: {filename}, mutations at positions: {mutated_positions[:10]}...")
        
        # Store the uploaded file path in database
        new_file.uploaded_file_path = permanent_filename
        
        # Update the database with file path before committing
        try:
            db.session.commit()
            logging.info(f"File permanently stored and database updated: {permanent_filename}")
        except Exception as db_error:
            logging.error(f"Error updating database with file path: {str(db_error)}")
            db.session.rollback()
            raise Exception(f"Failed to update file path in database: {str(db_error)}")
        
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
        db.session.execute("SELECT 1")
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
            logging.error(f"Results file missing: {results_path}")
            # Try to regenerate results from original file if it exists
            # Check multiple possible locations for the original file
            possible_paths = []
            if uploaded_file.uploaded_file_path:
                possible_paths.append(os.path.join(app.config['UPLOAD_FOLDER'], uploaded_file.uploaded_file_path))
            
            # Also try the filename
            possible_paths.append(os.path.join(app.config['UPLOAD_FOLDER'], uploaded_file.filename))
            
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
                    results, _ = analyze_mutations(original_file_path)
                    
                    # Save regenerated results
                    with open(results_path, 'w') as f:
                        json.dump(results, f)
                    logging.info(f"Results regenerated successfully: {results_path}")
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
    """Clear workspace file history for the current keyword."""
    if workspace_name not in ['denv', 'chikv']:
        return jsonify({'error': 'Invalid workspace'}), 400
    
    # Get keyword from session
    keyword = session.get(f'{workspace_name}_keyword')
    if not keyword:
        return jsonify({'error': 'No keyword found. Please refresh the page.'}), 400
    
    try:
        # Get all files for the workspace and keyword
        files_to_delete = UploadedFile.get_keyword_files(workspace_name, keyword, limit=1000)
        
        # Clean up files from disk
        for uploaded_file in files_to_delete:
            try:
                # Remove results file
                results_path = os.path.join(app.config['UPLOAD_FOLDER'], uploaded_file.results_file)
                if os.path.exists(results_path):
                    os.remove(results_path)
                
                # Remove output file if exists
                if uploaded_file.output_file:
                    output_path = os.path.join(app.config['UPLOAD_FOLDER'], uploaded_file.output_file)
                    if os.path.exists(output_path):
                        os.remove(output_path)
                        
            except Exception as e:
                logging.error(f"Error cleaning up files for {uploaded_file.id}: {str(e)}")
        
        # Delete from database (only files with this keyword)
        UploadedFile.query.filter_by(workspace=workspace_name, keyword=keyword).delete()
        db.session.commit()
        
        return jsonify({'success': True, 'message': f'History cleared for {workspace_name} workspace with keyword "{keyword}"'})
        
    except Exception as e:
        logging.error(f"Error clearing history: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Failed to clear history'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
