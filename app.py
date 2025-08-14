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
ALLOWED_EXTENSIONS = {'fasta', 'fa', 'txt', 'csv'}
MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB

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
    """Main dashboard with sidebar and interactive table."""
    # Initialize session history if not exists
    if 'file_history' not in session:
        session['file_history'] = []
    
    return render_template('dashboard.html', history=session.get('file_history', []))

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload and process mutation analysis via AJAX."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file selected'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file format. Please upload FASTA, TXT, or CSV files only.'}), 400
    
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
        
        # Create file entry for history
        file_entry = {
            'id': file_id,
            'filename': filename,
            'original_filename': file.filename,
            'timestamp': datetime.now().isoformat(),
            'upload_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'results': results,
            'output_file': output_file,
            'total_positions': total_positions,
            'mutated_positions': mutated_positions,
            'low_conf_positions': low_conf_positions,
            'mutation_count': len(mutated_positions),
            'conserved_count': total_positions - len(mutated_positions)
        }
        
        # Initialize session history if not exists
        if 'file_history' not in session:
            session['file_history'] = []
        
        # Add to history (newest first)
        session['file_history'].insert(0, file_entry)
        
        # Keep only last 10 files
        session['file_history'] = session['file_history'][:10]
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
        if 'filepath' in locals() and os.path.exists(filepath):
            os.remove(filepath)
        return jsonify({'error': f'Error processing file: {str(e)}'}), 500

@app.route('/download/<filename>')
def download_file(filename):
    """Download the generated CSV file."""
    try:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if os.path.exists(filepath):
            return send_file(filepath, as_attachment=True, download_name=filename)
        else:
            flash('File not found', 'error')
            return redirect(url_for('index'))
    except Exception as e:
        logging.error(f"Error downloading file: {str(e)}")
        flash('Error downloading file', 'error')
        return redirect(url_for('index'))

@app.route('/api/file/<file_id>')
def get_file_data(file_id):
    """Get file data for display in the main table."""
    if 'file_history' not in session:
        return jsonify({'error': 'No files in history'}), 404
    
    # Find file in history
    file_data = None
    for entry in session['file_history']:
        if entry['id'] == file_id:
            file_data = entry
            break
    
    if not file_data:
        return jsonify({'error': 'File not found'}), 404
    
    return jsonify({
        'success': True,
        'file_data': file_data
    })

@app.route('/api/history')
def get_history():
    """Get current file history."""
    return jsonify({
        'success': True,
        'history': session.get('file_history', [])
    })

@app.route('/api/clear-history', methods=['POST'])
def clear_history():
    """Clear file history."""
    session['file_history'] = []
    session.modified = True
    return jsonify({'success': True, 'message': 'History cleared'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
