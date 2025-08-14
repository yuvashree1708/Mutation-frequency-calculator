import os
import logging
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, send_file, jsonify, session
from werkzeug.utils import secure_filename
from werkzeug.middleware.proxy_fix import ProxyFix
from mutation_analyzer import analyze_mutations
import tempfile
import shutil
import uuid

# Configure logging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'fasta', 'fa', 'txt', 'csv', 'fas', 'aln', 'seq', 'msa', 'phylip', 'phy', 'nex', 'nexus'}  # Support extensive alignment formats
MAX_FILE_SIZE = 3 * 1024 * 1024 * 1024  # 3GB for very large genomic datasets

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

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
    
    # Initialize workspace-specific session history
    session_key = f'{workspace_name}_history'
    if session_key not in session:
        session[session_key] = []
    
    return render_template('workspace.html', 
                         workspace=workspace_name, 
                         history=session.get(session_key, []))

@app.route('/upload/<workspace_name>', methods=['POST'])
def upload_file(workspace_name):
    """Handle file upload and process mutation analysis via AJAX."""
    if workspace_name not in ['denv', 'chikv']:
        return jsonify({'error': 'Invalid workspace'}), 400
        
    if 'file' not in request.files:
        return jsonify({'error': 'No file selected'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file format. Supported formats: FASTA, FA, TXT, CSV, FAS, ALN, SEQ, MSA, PHYLIP, PHY, NEX, NEXUS'}), 400
    
    filepath = None
    try:
        # Generate unique file ID and save uploaded file
        file_id = str(uuid.uuid4())
        filename = secure_filename(file.filename or 'uploaded_file')
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], f"{file_id}_{filename}")
        file.save(filepath)
        
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
        
        # Create file entry for workspace history (without storing full results in session)
        file_entry = {
            'id': file_id,
            'filename': filename,
            'original_filename': file.filename,
            'workspace': workspace_name,
            'timestamp': datetime.now().isoformat(),
            'upload_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'results_file': results_file,  # Store file path instead of data
            'output_file': output_file,
            'total_positions': total_positions,
            'mutated_positions': mutated_positions,
            'low_conf_positions': low_conf_positions,
            'mutation_count': len(mutated_positions),
            'conserved_count': total_positions - len(mutated_positions)
        }
        
        # Initialize workspace-specific session history
        session_key = f'{workspace_name}_history'
        if session_key not in session:
            session[session_key] = []
        
        # Add to workspace history (newest first)
        session[session_key].insert(0, file_entry)
        
        # Keep only last 25 files per workspace (expanded for 3GB storage capacity)
        session[session_key] = session[session_key][:25]
        session.modified = True
        
        logging.debug(f"File processed: {filename}, mutations at positions: {mutated_positions[:10]}...")
        
        # Clean up uploaded file
        os.remove(filepath)
        
        return jsonify({
            'success': True,
            'file_id': file_id,
            'filename': filename,
            'message': f'File processed successfully. Found {len(mutated_positions)} mutations in {total_positions} positions.'
        })
        
    except Exception as e:
        logging.error(f"Error processing file: {str(e)}")
        # Clean up on error
        try:
            if 'filepath' in locals() and filepath and os.path.exists(filepath):
                os.remove(filepath)
        except Exception:
            pass  # Ignore cleanup errors
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
    """Get file data for display in the main table."""
    if workspace_name not in ['denv', 'chikv']:
        return jsonify({'error': 'Invalid workspace'}), 400
        
    session_key = f'{workspace_name}_history'
    if session_key not in session:
        return jsonify({'error': 'No files in history'}), 404
    
    # Find file in workspace history
    file_data = None
    for entry in session[session_key]:
        if entry['id'] == file_id:
            file_data = entry.copy()
            break
    
    if not file_data:
        return jsonify({'error': 'File not found in session'}), 404
    
    # Load results from file (supports both legacy pickle and new JSON formats)
    try:
        import json
        import pickle
        results_path = os.path.join(app.config['UPLOAD_FOLDER'], file_data['results_file'])
        
        if not os.path.exists(results_path):
            return jsonify({'error': 'Results file not found on disk'}), 404
        
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
            
            # Update session to reference JSON file
            session_key = f'{workspace_name}_history'
            for entry in session[session_key]:
                if entry['id'] == file_id:
                    entry['results_file'] = file_data['results_file']
                    break
            session.modified = True
            
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
        
    session_key = f'{workspace_name}_history'
    return jsonify({
        'success': True,
        'history': session.get(session_key, [])
    })

@app.route('/api/<workspace_name>/clear-history', methods=['POST'])
def clear_history(workspace_name):
    """Clear workspace file history."""
    if workspace_name not in ['denv', 'chikv']:
        return jsonify({'error': 'Invalid workspace'}), 400
    
    session_key = f'{workspace_name}_history'
    
    # Clean up results files before clearing session
    if session_key in session:
        for entry in session[session_key]:
            try:
                results_path = os.path.join(app.config['UPLOAD_FOLDER'], entry.get('results_file', ''))
                if os.path.exists(results_path):
                    os.remove(results_path)
            except Exception as e:
                logging.error(f"Error cleaning up results file: {str(e)}")
    
    session[session_key] = []
    session.modified = True
    return jsonify({'success': True, 'message': 'History cleared'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
