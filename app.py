import os
import logging
from flask import Flask, render_template, request, redirect, url_for, flash, send_file, jsonify
from werkzeug.utils import secure_filename
from werkzeug.middleware.proxy_fix import ProxyFix
from mutation_analyzer import analyze_mutations
import tempfile
import shutil

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
    """Main upload page."""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload and process mutation analysis."""
    if 'file' not in request.files:
        flash('No file selected', 'error')
        return redirect(url_for('index'))
    
    file = request.files['file']
    if file.filename == '':
        flash('No file selected', 'error')
        return redirect(url_for('index'))
    
    if not allowed_file(file.filename):
        flash('Invalid file format. Please upload FASTA, TXT, or CSV files only.', 'error')
        return redirect(url_for('index'))
    
    try:
        # Save uploaded file
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Process the file
        results, output_file = analyze_mutations(filepath)
        
        # Calculate summary statistics
        total_positions = len(results)
        conserved_count = sum(1 for r in results if r['Color'] == 'Green')
        mutated_count = sum(1 for r in results if r['Color'] == 'Red') 
        low_conf_count = sum(1 for r in results if r['Ambiguity'] == 'Low-confidence')
        mutation_rate = round((mutated_count / total_positions) * 100) if total_positions > 0 else 0
        
        stats = {
            'total_positions': total_positions,
            'conserved_count': conserved_count,
            'mutated_count': mutated_count,
            'low_conf_count': low_conf_count,
            'mutation_rate': mutation_rate
        }
        
        logging.debug(f"Summary stats: {stats}")
        
        # Clean up uploaded file
        os.remove(filepath)
        
        return render_template('results.html', 
                             results=results, 
                             output_file=output_file,
                             original_filename=filename,
                             stats=stats)
        
    except Exception as e:
        logging.error(f"Error processing file: {str(e)}")
        flash(f'Error processing file: {str(e)}', 'error')
        # Clean up on error
        if 'filepath' in locals() and os.path.exists(filepath):
            os.remove(filepath)
        return redirect(url_for('index'))

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

@app.route('/api/progress')
def get_progress():
    """API endpoint for progress updates (for future enhancement)."""
    # This could be enhanced with real-time progress tracking
    return jsonify({'status': 'processing'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
