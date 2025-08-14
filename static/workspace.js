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
        this.setupMobileMenu();
    }

    setupEventListeners() {
        // File upload handling with validation
        document.getElementById('fileInput').addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                const file = e.target.files[0];
                const validation = this.validateFile(file);
                
                if (validation.valid) {
                    this.uploadFile(file);
                } else {
                    this.showToast('Error', validation.error, 'danger');
                    e.target.value = '';
                }
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

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => this.handleKeyboard(e));
    }

    setupMobileMenu() {
        // Add mobile menu toggle for responsive design
        if (window.innerWidth <= 768) {
            const contentHeader = document.querySelector('.content-header');
            const toggleBtn = document.createElement('button');
            toggleBtn.className = 'mobile-menu-toggle btn btn-primary';
            toggleBtn.innerHTML = '<i class="fas fa-bars"></i>';
            toggleBtn.addEventListener('click', this.toggleMobileSidebar);
            contentHeader.appendChild(toggleBtn);
        }
    }

    toggleMobileSidebar() {
        const sidebar = document.querySelector('.sidebar');
        sidebar.classList.toggle('show');
    }

    validateFile(file) {
        const allowedTypes = ['fasta', 'fa'];
        const maxSize = 16 * 1024 * 1024; // 16MB
        
        const extension = file.name.split('.').pop().toLowerCase();
        
        if (!allowedTypes.includes(extension)) {
            return { 
                valid: false, 
                error: 'Invalid file type. Please select a FASTA file (.fasta or .fa).' 
            };
        }
        
        if (file.size > maxSize) {
            return { 
                valid: false, 
                error: 'File size exceeds 16MB limit. Please choose a smaller file.' 
            };
        }
        
        return { valid: true };
    }

    uploadFile(file) {
        const formData = new FormData();
        formData.append('file', file);

        // Show upload progress
        this.showUploadProgress();
        this.updateUploadStatus('Uploading and processing file...');

        fetch(`/upload/${this.workspace}`, {
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
        fetch(`/api/${this.workspace}/history`)
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
        
        if (history.length === 0) {
            historyList.innerHTML = `
                <div id="emptyHistory" class="text-center text-muted py-4">
                    <i class="fas fa-history fa-2x mb-2 opacity-50"></i>
                    <p class="small">No files uploaded yet</p>
                </div>
            `;
            return;
        }

        const historyHtml = history.map(file => `
            <div class="history-item fade-in" data-file-id="${file.id}">
                <div class="file-name">${file.original_filename}</div>
                <div class="file-meta">
                    <small class="text-muted">${file.upload_time}</small>
                </div>
                <div class="file-stats">
                    <span class="badge bg-danger">${file.mutation_count}</span>
                    <span class="badge bg-secondary">${file.total_positions}</span>
                </div>
                <div class="file-actions mt-2">
                    <button class="btn btn-primary btn-sm view-table-btn" data-file-id="${file.id}">
                        <i class="fas fa-table me-1"></i>View Mutation Freq Table
                    </button>
                </div>
            </div>
        `).join('');
        
        historyList.innerHTML = historyHtml;
        
        // Add event listeners for view table buttons
        historyList.querySelectorAll('.view-table-btn').forEach(button => {
            button.addEventListener('click', (e) => {
                e.stopPropagation();
                const fileId = button.getAttribute('data-file-id');
                this.loadFileData(fileId);
                
                // Set the parent history item as active
                const historyItem = button.closest('.history-item');
                this.setActiveHistoryItem(historyItem);
            });
        });
    }

    loadFileData(fileId) {
        if (fileId === this.currentFileId) return; // Already loaded
        
        this.showLoadingSpinner();
        
        fetch(`/api/${this.workspace}/file/${fileId}`)
        .then(response => {
            if (response.ok) {
                return response.json();
            } else {
                return response.json().then(err => Promise.reject(err));
            }
        })
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
            const errorMessage = error.error || error.message || 'Failed to load file data';
            this.showToast('File Error', errorMessage, 'danger');
            this.hideLoadingSpinner();
            console.error('Load file error:', error);
        });
    }

    renderFileData(fileData) {
        // Update header
        document.getElementById('currentFileName').textContent = fileData.original_filename;
        document.getElementById('fileInfo').innerHTML = `
            <i class="fas fa-chart-bar me-1"></i>${fileData.total_positions} positions analyzed • 
            <i class="fas fa-exclamation-triangle text-danger me-1"></i>${fileData.mutation_count} mutations found • 
            <i class="fas fa-clock me-1"></i>Uploaded ${fileData.upload_time}
        `;

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

        // Render mutated positions
        if (mutatedPositions.length > 0) {
            const mutatedHtml = mutatedPositions.map(pos => 
                `<button class="position-badge" title="Jump to position ${pos}" data-position="${pos}">${pos}</button>`
            ).join('');
            mutatedContainer.innerHTML = mutatedHtml;
        } else {
            mutatedContainer.innerHTML = '<span class="text-muted small">No mutations detected</span>';
        }

        // Render low confidence positions
        if (lowConfPositions.length > 0) {
            const lowConfHtml = lowConfPositions.map(pos => 
                `<button class="position-badge low-conf" title="Jump to position ${pos}" data-position="${pos}">${pos}</button>`
            ).join('');
            lowConfContainer.innerHTML = lowConfHtml;
        } else {
            lowConfContainer.innerHTML = '<span class="text-muted small">All positions high confidence</span>';
        }
    }

    renderDataTable(results) {
        // Destroy existing DataTable if exists
        if (this.dataTable) {
            this.dataTable.destroy();
            this.dataTable = null;
        }

        const tableBody = document.querySelector('#dataTable tbody');
        
        // Generate table rows with enhanced styling
        const rowsHtml = results.map(result => `
            <tr data-color="${result.Color}" data-ambiguity="${result.Ambiguity}" data-position="${result.Position}" class="slide-up">
                <td class="text-center fw-bold">${result.Position}</td>
                <td class="text-center"><code>${result.Reference}</code></td>
                <td class="text-center">
                    ${result.Color === 'Green' ? 
                        '<span class="badge bg-success"><i class="fas fa-check me-1"></i>Conserved</span>' :
                        '<span class="badge bg-danger"><i class="fas fa-exclamation me-1"></i>Mutated</span>'
                    }
                </td>
                <td>
                    <span class="mutation-repr">${result['Mutation Representation']}</span>
                </td>
                <td class="text-center">
                    ${result.Ambiguity === 'High-confidence' ?
                        '<span class="badge bg-info">High</span>' :
                        '<span class="badge bg-warning text-dark">Low</span>'
                    }
                </td>
                <td><small class="text-muted font-monospace">${result.Counts}</small></td>
                <td><small class="text-muted font-monospace">${result['Frequencies (%)']}</small></td>
            </tr>
        `).join('');
        
        tableBody.innerHTML = rowsHtml;

        // Initialize DataTable with single scroll view and enhanced readability
        this.dataTable = $('#dataTable').DataTable({
            pageLength: -1, // Show all rows (no pagination)
            lengthMenu: [[-1], ["All"]], // Only "All" option
            paging: false, // Disable pagination completely
            scrollY: '70vh', // Increased vertical scrolling height
            scrollX: true, // Horizontal scrolling if needed
            scrollCollapse: true,
            order: [[0, 'asc']], // Sort by position
            dom: '<"row"<"col-sm-12"f>>rt', // Only show search and table (no pagination controls)
            columnDefs: [
                {
                    targets: [5, 6], // Raw counts and frequencies columns
                    orderable: false
                },
                {
                    targets: [0], // Position column
                    className: 'text-center fw-bold'
                },
                {
                    targets: [1, 2, 4], // Reference, Status, Confidence columns
                    className: 'text-center'
                }
            ],
            language: {
                search: "Search positions and mutations:",
                info: "", // Remove info display
                infoEmpty: "",
                infoFiltered: ""
            },
            responsive: false,
            autoWidth: false,
            processing: false
        });

        // Add custom styling for DataTables elements
        this.styleDataTable();
    }

    styleDataTable() {
        // Add custom classes to DataTables controls
        $('.dataTables_filter input').addClass('form-control-sm');
        $('.dataTables_length select').addClass('form-select-sm');
        
        // Add icons to pagination buttons
        $('.paginate_button.previous').html('<i class="fas fa-chevron-left me-1"></i>Previous');
        $('.paginate_button.next').html('Next<i class="fas fa-chevron-right ms-1"></i>');
    }

    scrollToPosition(position) {
        if (!this.dataTable) return;

        // Clear any existing search and show all rows
        this.dataTable.search('').draw();
        
        // Find the row with the specific position
        const targetRow = document.querySelector(`#dataTable tbody tr[data-position="${position}"]`);
        if (targetRow) {
            // Scroll to the row smoothly
            targetRow.scrollIntoView({ 
                behavior: 'smooth', 
                block: 'center' 
            });
            
            // Highlight the row temporarily
            targetRow.style.backgroundColor = 'var(--bs-warning-bg-subtle)';
            targetRow.style.transform = 'scale(1.02)';
            
            setTimeout(() => {
                targetRow.style.backgroundColor = '';
                targetRow.style.transform = '';
            }, 2000);

            // Show success toast
            this.showToast('Position Found', `Scrolled to position ${position}`, 'success');
        } else {
            this.showToast('Position Not Found', `Position ${position} is not visible in current view`, 'warning');
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
        if (!confirm(`Are you sure you want to clear the ${this.workspace.toUpperCase()} workspace history?`)) {
            return;
        }

        fetch(`/api/${this.workspace}/clear-history`, {
            method: 'POST'
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                this.showToast('Success', 'History cleared successfully', 'success');
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
            // Check if file exists before attempting download
            fetch(`/download/${filename}`, { method: 'HEAD' })
            .then(response => {
                if (response.ok) {
                    // File exists, proceed with download
                    const link = document.createElement('a');
                    link.href = `/download/${filename}`;
                    link.download = filename;
                    link.style.display = 'none';
                    document.body.appendChild(link);
                    link.click();
                    document.body.removeChild(link);
                    
                    this.showToast('Download', 'CSV file download started', 'success');
                } else {
                    this.showToast('Download Error', 'File not found on server', 'danger');
                }
            })
            .catch(error => {
                this.showToast('Download Error', 'Failed to access file', 'danger');
            });
        }
    }

    resetView() {
        this.currentFileId = null;
        document.getElementById('currentFileName').textContent = 'Select a FASTA file to view mutation analysis';
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
        } else if (type === 'warning') {
            icon = 'fas fa-exclamation-circle';
            colorClass = 'text-warning';
        }
        
        toastHeader.innerHTML = `
            <i class="${icon} ${colorClass} me-2"></i>
            <strong class="me-auto">${title}</strong>
            <button type="button" class="btn-close" data-bs-dismiss="toast"></button>
        `;
        
        toastBody.textContent = message;
        
        // Show toast
        const bsToast = new bootstrap.Toast(toast, { delay: 4000 });
        bsToast.show();
    }

    handleKeyboard(e) {
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
            
            // Hide mobile sidebar if open
            const sidebar = document.querySelector('.sidebar');
            sidebar.classList.remove('show');
        }
    }
}

// Initialize workspace when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    window.mutationWorkspace = new MutationWorkspace();
});

// Handle window resize
window.addEventListener('resize', function() {
    if (window.innerWidth > 768) {
        const sidebar = document.querySelector('.sidebar');
        sidebar.classList.remove('show');
    }
});

// Add smooth scrolling for better UX
document.documentElement.style.scrollBehavior = 'smooth';