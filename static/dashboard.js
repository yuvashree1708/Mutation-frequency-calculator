// Workspace JavaScript for Interactive Mutation Analysis

class MutationWorkspace {
    constructor() {
        this.currentFileId = null;
        this.dataTable = null;
        this.workspace = window.WORKSPACE;
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.loadHistory();
    }

    setupEventListeners() {
        // File upload handling
        document.getElementById('fileInput').addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                this.uploadFile(e.target.files[0]);
            }
        });

        // History item clicks
        document.addEventListener('click', (e) => {
            const historyItem = e.target.closest('.history-item');
            if (historyItem) {
                const fileId = historyItem.getAttribute('data-file-id');
                this.loadFileData(fileId);
                this.setActiveHistoryItem(historyItem);
            }
        });

        // Clear history button
        document.getElementById('clearHistoryBtn').addEventListener('click', () => {
            this.clearHistory();
        });

        // Download button
        document.getElementById('downloadBtn').addEventListener('click', () => {
            this.downloadCurrentFile();
        });

        // Position badge clicks (scroll to position in table)
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('position-badge')) {
                const position = parseInt(e.target.textContent);
                this.scrollToPosition(position);
            }
        });
    }

    uploadFile(file) {
        const formData = new FormData();
        formData.append('file', file);

        // Show upload progress
        this.showUploadProgress();
        this.updateUploadStatus('Uploading and processing file...');

        fetch('/upload', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            this.hideUploadProgress();
            
            if (data.success) {
                this.showToast('Success', data.message, 'success');
                this.updateUploadStatus('');
                this.loadHistory(); // Refresh history
                this.loadFileData(data.file_id); // Load the new file
                
                // Clear file input
                document.getElementById('fileInput').value = '';
            } else {
                this.showToast('Error', data.error, 'danger');
                this.updateUploadStatus('Upload failed');
            }
        })
        .catch(error => {
            this.hideUploadProgress();
            this.showToast('Error', 'Upload failed: ' + error.message, 'danger');
            this.updateUploadStatus('Upload failed');
        });
    }

    loadHistory() {
        fetch('/api/history')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                this.renderHistory(data.history);
            }
        })
        .catch(error => {
            console.error('Error loading history:', error);
        });
    }

    renderHistory(history) {
        const historyList = document.getElementById('historyList');
        
        // Clear existing content safely
        historyList.textContent = '';
        
        if (history.length === 0) {
            const emptyDiv = document.createElement('div');
            emptyDiv.id = 'emptyHistory';
            emptyDiv.className = 'text-center text-muted py-4';
            
            const icon = document.createElement('i');
            icon.className = 'fas fa-history fa-2x mb-2 opacity-50';
            emptyDiv.appendChild(icon);
            
            const text = document.createElement('p');
            text.className = 'small';
            text.textContent = 'No files uploaded yet';
            emptyDiv.appendChild(text);
            
            historyList.appendChild(emptyDiv);
            return;
        }

        history.forEach(file => {
            const historyItem = document.createElement('div');
            historyItem.className = 'history-item';
            historyItem.setAttribute('data-file-id', file.id);
            
            const fileName = document.createElement('div');
            fileName.className = 'file-name';
            fileName.textContent = file.original_filename;
            historyItem.appendChild(fileName);
            
            const fileMeta = document.createElement('div');
            fileMeta.className = 'file-meta';
            const metaSmall = document.createElement('small');
            metaSmall.className = 'text-muted';
            metaSmall.textContent = file.upload_time;
            fileMeta.appendChild(metaSmall);
            historyItem.appendChild(fileMeta);
            
            const fileStats = document.createElement('div');
            fileStats.className = 'file-stats';
            const statsSmall = document.createElement('small');
            const badge = document.createElement('span');
            badge.className = 'badge bg-danger';
            badge.textContent = file.mutation_count;
            statsSmall.appendChild(badge);
            statsSmall.appendChild(document.createTextNode(' mutations'));
            fileStats.appendChild(statsSmall);
            historyItem.appendChild(fileStats);
            
            historyList.appendChild(historyItem);
        });
    }

    loadFileData(fileId) {
        if (fileId === this.currentFileId) return; // Already loaded
        
        this.showLoadingSpinner();
        
        fetch(`/api/file/${fileId}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                this.currentFileId = fileId;
                this.renderFileData(data.file_data);
                this.hideLoadingSpinner();
            } else {
                this.showToast('Error', data.error, 'danger');
                this.hideLoadingSpinner();
            }
        })
        .catch(error => {
            this.showToast('Error', 'Failed to load file data', 'danger');
            this.hideLoadingSpinner();
        });
    }

    renderFileData(fileData) {
        // Update header
        document.getElementById('currentFileName').textContent = fileData.original_filename;
        document.getElementById('fileInfo').textContent = 
            `${fileData.total_positions} positions • ${fileData.mutation_count} mutations • Uploaded ${fileData.upload_time}`;

        // Show download button
        document.getElementById('downloadBtn').classList.remove('d-none');
        document.getElementById('downloadBtn').setAttribute('data-filename', fileData.output_file);

        // Render mutation positions
        this.renderPositions(fileData.mutated_positions, fileData.low_conf_positions);

        // Render data table
        this.renderDataTable(fileData.results);

        // Hide welcome message and show table
        document.getElementById('welcomeMessage').classList.add('d-none');
        document.getElementById('tableContainer').classList.remove('d-none');
        document.getElementById('positionsPanel').style.display = 'block';
    }

    renderPositions(mutatedPositions, lowConfPositions) {
        const mutatedContainer = document.getElementById('mutatedPositions');
        const lowConfContainer = document.getElementById('lowConfPositions');

        // Clear existing content safely
        mutatedContainer.textContent = '';
        lowConfContainer.textContent = '';

        // Render mutated positions
        if (mutatedPositions.length > 0) {
            mutatedPositions.forEach(pos => {
                const badge = document.createElement('span');
                badge.className = 'position-badge';
                badge.title = `Jump to position ${pos}`;
                badge.textContent = pos;
                mutatedContainer.appendChild(badge);
            });
        } else {
            const noMutations = document.createElement('span');
            noMutations.className = 'text-muted small';
            noMutations.textContent = 'No mutations found';
            mutatedContainer.appendChild(noMutations);
        }

        // Render low confidence positions
        if (lowConfPositions.length > 0) {
            lowConfPositions.forEach(pos => {
                const badge = document.createElement('span');
                badge.className = 'position-badge low-conf';
                badge.title = `Jump to position ${pos}`;
                badge.textContent = pos;
                lowConfContainer.appendChild(badge);
            });
        } else {
            const allHighConf = document.createElement('span');
            allHighConf.className = 'text-muted small';
            allHighConf.textContent = 'All positions high confidence';
            lowConfContainer.appendChild(allHighConf);
        }
    }

    renderDataTable(results) {
        // Destroy existing DataTable if exists
        if (this.dataTable) {
            this.dataTable.destroy();
            this.dataTable = null;
        }

        const tableBody = document.querySelector('#dataTable tbody');
        
        // Clear existing content safely
        tableBody.textContent = '';
        
        // Create table rows using safe DOM methods
        results.forEach(result => {
            const row = document.createElement('tr');
            row.setAttribute('data-color', result.Color);
            row.setAttribute('data-ambiguity', result.Ambiguity);
            row.setAttribute('data-position', result.Position);
            
            // Position column
            const posCell = document.createElement('td');
            posCell.textContent = result.Position;
            row.appendChild(posCell);
            
            // Reference column (with code styling)
            const refCell = document.createElement('td');
            const codeEl = document.createElement('code');
            codeEl.textContent = result.Reference;
            refCell.appendChild(codeEl);
            row.appendChild(refCell);
            
            // Color/Status column
            const colorCell = document.createElement('td');
            const statusBadge = document.createElement('span');
            const statusIcon = document.createElement('i');
            statusIcon.className = result.Color === 'Green' ? 'fas fa-check me-1' : 'fas fa-exclamation me-1';
            statusBadge.className = result.Color === 'Green' ? 'badge bg-success' : 'badge bg-danger';
            statusBadge.appendChild(statusIcon);
            statusBadge.appendChild(document.createTextNode(result.Color === 'Green' ? 'Conserved' : 'Mutated'));
            colorCell.appendChild(statusBadge);
            row.appendChild(colorCell);
            
            // Mutation representation column
            const mutCell = document.createElement('td');
            const mutSpan = document.createElement('span');
            mutSpan.className = 'mutation-repr';
            mutSpan.textContent = result['Mutation Representation'];
            mutCell.appendChild(mutSpan);
            row.appendChild(mutCell);
            
            // Ambiguity column
            const ambCell = document.createElement('td');
            const ambBadge = document.createElement('span');
            ambBadge.className = result.Ambiguity === 'High-confidence' ? 'badge bg-info' : 'badge bg-warning';
            ambBadge.textContent = result.Ambiguity === 'High-confidence' ? 'High' : 'Low';
            ambCell.appendChild(ambBadge);
            row.appendChild(ambCell);
            
            // Counts column
            const countsCell = document.createElement('td');
            const countsSmall = document.createElement('small');
            countsSmall.className = 'text-muted';
            countsSmall.textContent = result.Counts;
            countsCell.appendChild(countsSmall);
            row.appendChild(countsCell);
            
            // Frequencies column
            const freqCell = document.createElement('td');
            const freqSmall = document.createElement('small');
            freqSmall.className = 'text-muted';
            freqSmall.textContent = result['Frequencies (%)'];
            freqCell.appendChild(freqSmall);
            row.appendChild(freqCell);
            
            tableBody.appendChild(row);
        });

        // Initialize DataTable
        this.dataTable = $('#dataTable').DataTable({
            pageLength: 50,
            lengthMenu: [[50, 25, 100, -1], [50, 25, 100, "All"]],
            order: [[0, 'asc']], // Sort by position
            columnDefs: [
                {
                    targets: [5, 6], // Raw counts and frequencies columns
                    orderable: false
                }
            ],
            language: {
                search: "Search positions:",
                lengthMenu: "Show _MENU_ positions per page",
                info: "Showing _START_ to _END_ of _TOTAL_ positions",
                infoEmpty: "No positions found",
                infoFiltered: "(filtered from _MAX_ total positions)"
            },
            dom: '<"row"<"col-sm-12 col-md-6"l><"col-sm-12 col-md-6"f>><"row"<"col-sm-12"t>><"row"<"col-sm-12 col-md-5"i><"col-sm-12 col-md-7"p>>',
            scrollY: 'calc(100vh - 400px)',
            scrollCollapse: true
        });
    }

    scrollToPosition(position) {
        if (!this.dataTable) return;

        // Search for the position in DataTable
        this.dataTable.search('').draw(); // Clear any existing search
        
        // Find the row with the specific position
        const targetRow = document.querySelector(`#dataTable tbody tr[data-position="${position}"]`);
        if (targetRow) {
            // Scroll to the row
            targetRow.scrollIntoView({ 
                behavior: 'smooth', 
                block: 'center' 
            });
            
            // Highlight the row temporarily
            targetRow.style.backgroundColor = 'var(--bs-warning-bg-subtle)';
            setTimeout(() => {
                targetRow.style.backgroundColor = '';
            }, 2000);
        }
    }

    setActiveHistoryItem(activeItem) {
        // Remove active class from all items
        document.querySelectorAll('.history-item').forEach(item => {
            item.classList.remove('active');
        });
        
        // Add active class to selected item
        activeItem.classList.add('active');
    }

    clearHistory() {
        if (!confirm('Are you sure you want to clear the file history?')) {
            return;
        }

        fetch('/api/clear-history', {
            method: 'POST'
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                this.showToast('Success', 'History cleared', 'success');
                this.loadHistory();
                this.resetView();
            }
        })
        .catch(error => {
            this.showToast('Error', 'Failed to clear history', 'danger');
        });
    }

    downloadCurrentFile() {
        if (!this.currentFileId) return;
        
        const filename = document.getElementById('downloadBtn').getAttribute('data-filename');
        if (filename) {
            window.location.href = `/download/${filename}`;
        }
    }

    resetView() {
        this.currentFileId = null;
        document.getElementById('currentFileName').textContent = 'Select a file to view analysis results';
        document.getElementById('fileInfo').textContent = '';
        document.getElementById('downloadBtn').classList.add('d-none');
        document.getElementById('positionsPanel').style.display = 'none';
        document.getElementById('welcomeMessage').classList.remove('d-none');
        document.getElementById('tableContainer').classList.add('d-none');
        
        if (this.dataTable) {
            this.dataTable.destroy();
            this.dataTable = null;
        }
    }

    showUploadProgress() {
        const progress = document.getElementById('uploadProgress');
        progress.classList.remove('d-none');
        progress.querySelector('.progress-bar').style.width = '100%';
    }

    hideUploadProgress() {
        const progress = document.getElementById('uploadProgress');
        progress.classList.add('d-none');
        progress.querySelector('.progress-bar').style.width = '0%';
    }

    updateUploadStatus(message) {
        document.getElementById('uploadStatus').textContent = message;
    }

    showLoadingSpinner() {
        document.getElementById('loadingSpinner').classList.remove('d-none');
        document.getElementById('tableContainer').classList.add('d-none');
        document.getElementById('welcomeMessage').classList.add('d-none');
    }

    hideLoadingSpinner() {
        document.getElementById('loadingSpinner').classList.add('d-none');
    }

    showToast(title, message, type = 'info') {
        const toast = document.getElementById('toastNotification');
        const toastHeader = toast.querySelector('.toast-header');
        const toastBody = toast.querySelector('.toast-body');
        
        // Update icon and colors based on type
        let icon = 'fas fa-info-circle';
        let colorClass = 'text-primary';
        
        if (type === 'success') {
            icon = 'fas fa-check-circle';
            colorClass = 'text-success';
        } else if (type === 'danger') {
            icon = 'fas fa-exclamation-triangle';
            colorClass = 'text-danger';
        }
        
        toastHeader.innerHTML = `
            <i class="${icon} ${colorClass} me-2"></i>
            <strong class="me-auto">${title}</strong>
            <button type="button" class="btn-close" data-bs-dismiss="toast"></button>
        `;
        
        toastBody.textContent = message;
        
        // Show toast
        const bsToast = new bootstrap.Toast(toast);
        bsToast.show();
    }
}

// Initialize dashboard when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    window.dashboard = new MutationDashboard();
});

// Utility functions for file validation
function validateFile(file) {
    const allowedTypes = ['fasta', 'fa', 'txt', 'csv'];
    const maxSize = 16 * 1024 * 1024; // 16MB
    
    const extension = file.name.split('.').pop().toLowerCase();
    
    if (!allowedTypes.includes(extension)) {
        return { valid: false, error: 'Invalid file type. Please select a FASTA, TXT, or CSV file.' };
    }
    
    if (file.size > maxSize) {
        return { valid: false, error: 'File size exceeds 16MB limit. Please choose a smaller file.' };
    }
    
    return { valid: true };
}

// Keyboard shortcuts
document.addEventListener('keydown', function(e) {
    // Ctrl/Cmd + U for upload
    if ((e.ctrlKey || e.metaKey) && e.key === 'u') {
        e.preventDefault();
        document.getElementById('fileInput').click();
    }
    
    // Ctrl/Cmd + D for download (if file is selected)
    if ((e.ctrlKey || e.metaKey) && e.key === 'd') {
        e.preventDefault();
        const downloadBtn = document.getElementById('downloadBtn');
        if (!downloadBtn.classList.contains('d-none')) {
            downloadBtn.click();
        }
    }
    
    // Escape key to clear selection
    if (e.key === 'Escape') {
        document.querySelectorAll('.history-item.active').forEach(item => {
            item.classList.remove('active');
        });
    }
});