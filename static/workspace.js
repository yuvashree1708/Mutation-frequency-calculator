// Workspace JavaScript for Interactive Mutation Analysis

// Global workspace instance for onclick handlers
let dashboard = null;

class MutationWorkspace {
    constructor() {
        this.currentFileId = null;
        this.dataTable = null;
        this.workspace = window.WORKSPACE;
        this.fileCache = new FileCache();
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.loadHistory();
        this.setupMobileMenu();
        
        // Initialize caching system for offline reliability
        if (this.fileCache.isSupported()) {
            const stats = this.fileCache.getCacheStats();
            console.log('File cache initialized:', stats);
        } else {
            console.warn('Browser storage not available - reduced offline capability');
        }
    }

    setupEventListeners() {
        // File upload handling with validation for all upload inputs
        const fileInputs = ['fileInput', 'fileInputSidebar', 'fileInputMain'];
        fileInputs.forEach(inputId => {
            const input = document.getElementById(inputId);
            if (input) {
                input.addEventListener('change', (e) => {
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

        // Back to files button
        const backToFilesBtn = document.getElementById('backToFilesBtn');
        if (backToFilesBtn) {
            backToFilesBtn.addEventListener('click', () => {
                this.resetView();
            });
        }

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
        const allowedTypes = ['fasta', 'fa', 'txt', 'csv', 'fas', 'aln', 'seq', 'msa', 'phylip', 'phy', 'nex', 'nexus'];
        const maxSize = 3 * 1024 * 1024 * 1024; // 3GB
        
        const extension = file.name.split('.').pop().toLowerCase();
        
        if (!allowedTypes.includes(extension)) {
            return { 
                valid: false, 
                error: 'Invalid file type. Please select a genomic alignment file (FASTA, TXT, CSV, etc.).' 
            };
        }
        
        if (file.size > maxSize) {
            return { 
                valid: false, 
                error: 'File too large. Maximum size is 3GB.' 
            };
        }
        
        return { valid: true };
    }

    uploadFile(file) {
        const formData = new FormData();
        formData.append('file', file);

        // Show upload progress with file size info
        this.showUploadProgress();
        const fileSizeMB = (file.size / (1024 * 1024)).toFixed(1);
        this.updateUploadStatus(`Uploading ${fileSizeMB}MB file...`);

        // Create XMLHttpRequest for better progress tracking
        const xhr = new XMLHttpRequest();
        
        // Track upload progress
        xhr.upload.addEventListener('progress', (e) => {
            if (e.lengthComputable) {
                const percentComplete = (e.loaded / e.total) * 100;
                this.updateUploadProgress(percentComplete);
                this.updateUploadStatus(`Uploading... ${percentComplete.toFixed(1)}%`);
            }
        });
        
        // Handle upload start
        xhr.addEventListener('loadstart', () => {
            this.updateUploadStatus('Starting upload...');
        });

        xhr.onload = () => {
            if (xhr.status === 200) {
                const data = JSON.parse(xhr.responseText);
                
                if (data.success) {
                    this.hideUploadProgress();
                    this.showToast('Success', data.message, 'success');
                    this.updateUploadStatus('');
                    this.loadHistory(); // Refresh history
                    this.loadFileData(data.file_id); // Load the new file
                    
                    // Clear file input
                    document.getElementById('fileInput').value = '';
                } else {
                    this.hideUploadProgress();
                    this.showToast('Error', data.error, 'danger');
                    this.updateUploadStatus('Upload failed');
                }
            } else {
                this.hideUploadProgress();
                this.showToast('Error', 'Upload failed: Server error', 'danger');
                this.updateUploadStatus('Upload failed');
            }
        };

        xhr.onerror = () => {
            this.hideUploadProgress();
            this.showToast('Error', 'Upload failed: Network error', 'danger');
            this.updateUploadStatus('Upload failed');
        };

        xhr.timeout = 300000; // 5 minutes timeout for large files
        xhr.ontimeout = () => {
            this.hideUploadProgress();
            this.showToast('Error', 'Upload timed out. File may be too large.', 'danger');
            this.updateUploadStatus('Upload timed out');
        };

        // Use window.WORKSPACE to ensure correct workspace
        const currentWorkspace = window.WORKSPACE || window.location.pathname.split('/')[2] || this.workspace;
        console.log('Uploading to workspace:', currentWorkspace);
        
        xhr.open('POST', `/upload/${currentWorkspace}`);
        xhr.send(formData);
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
        const filesGrid = document.getElementById('filesGrid');
        const emptyFiles = document.getElementById('emptyFiles');
        
        if (history.length === 0) {
            filesGrid.innerHTML = '';
            emptyFiles.style.display = 'block';
            return;
        }

        emptyFiles.style.display = 'none';
        
        const filesHtml = history.map(file => `
            <div class="file-card" data-file-id="${file.id}">
                <div class="file-card-header">
                    <div class="file-icon">
                        <i class="fas fa-dna"></i>
                    </div>
                    <div class="file-stats-badges">
                        <span class="badge bg-danger">${file.mutation_count}</span>
                        <span class="badge bg-secondary">${file.total_positions}</span>
                    </div>
                </div>
                <div class="file-card-body">
                    <h6 class="file-title">${file.original_filename}</h6>
                    <div class="file-meta">
                        <small class="text-muted">
                            <i class="fas fa-clock me-1"></i>${file.upload_time}
                        </small>
                    </div>
                    <div class="file-stats-text">
                        <small class="text-muted">
                            ${file.mutation_count} mutations • ${file.total_positions} positions
                        </small>
                    </div>
                </div>
                <div class="file-card-footer">
                    <button class="btn btn-primary w-100 view-table-btn" data-file-id="${file.id}">
                        <i class="fas fa-table me-1"></i>View Mutation Freq Table
                    </button>
                </div>
            </div>
        `).join('');
        
        filesGrid.innerHTML = filesHtml;
        
        // Add event listeners for view table buttons
        filesGrid.querySelectorAll('.view-table-btn').forEach(button => {
            button.addEventListener('click', (e) => {
                e.stopPropagation();
                const fileId = button.getAttribute('data-file-id');
                this.loadFileData(fileId);
            });
        });
    }

    loadFileData(fileId) {
        if (fileId === this.currentFileId) return; // Already loaded
        
        this.showLoadingSpinner();
        
        // Use window.WORKSPACE to ensure correct workspace
        const workspace = window.WORKSPACE || this.workspace;
        console.log('Loading file data for:', fileId, 'workspace:', workspace);
        
        // Try cached data first for offline reliability
        if (this.fileCache.isSupported()) {
            const cachedData = this.fileCache.getCachedFileData(fileId);
            if (cachedData) {
                console.log('Using cached data for offline access');
                this.currentFileId = fileId;
                this.renderFileData(cachedData);
                this.hideLoadingSpinner();
                this.showToast('Offline Mode', 'Displaying cached file data - limited connectivity detected', 'info');
                return;
            }
        }

        // Enhanced error handling with retry mechanism and offline support
        const loadWithRetry = (attempt = 1) => {
            fetch(`/api/${workspace}/file/${fileId}`, {
                method: 'GET',
                headers: {
                    'Cache-Control': 'no-cache',
                    'Pragma': 'no-cache',
                    'Connection': 'keep-alive'
                },
                timeout: 30000  // 30 second timeout
            })
            .then(response => {
                if (!response.ok) {
                    if (response.status >= 500) {
                        throw new Error(`Server Error ${response.status}: ${response.statusText}`);
                    }
                    return response.json().then(err => Promise.reject(err));
                }
                return response.json();
            })
            .then(data => {
                if (data.success && data.file_data) {
                    this.currentFileId = fileId;
                    
                    // Cache the data for offline access
                    if (this.fileCache.isSupported()) {
                        this.fileCache.cacheFileData(fileId, data.file_data);
                    }
                    
                    this.renderFileData(data.file_data);
                    this.hideLoadingSpinner();
                } else {
                    const errorMsg = data.error || 'Failed to load file data';
                    this.showToast('Error', errorMsg, 'danger');
                    this.hideLoadingSpinner();
                }
            })
            .catch(error => {
                console.error(`Load file attempt ${attempt} failed:`, error);
                
                // Retry on server errors, network issues, or timeouts
                const shouldRetry = (
                    error.message.includes('Server Error') || 
                    error.message.includes('Failed to fetch') ||
                    error.message.includes('timeout') ||
                    error.message.includes('NetworkError') ||
                    error.name === 'TypeError'
                );
                
                if (attempt < 5 && shouldRetry) {
                    const delay = Math.min(1000 * Math.pow(2, attempt - 1), 10000); // Exponential backoff max 10s
                    setTimeout(() => {
                        console.log(`Retrying file load, attempt ${attempt + 1} after ${delay}ms`);
                        loadWithRetry(attempt + 1);
                    }, delay);
                } else {
                    const errorMessage = error.error || error.message || 'Failed to load file data';
                    
                    if (attempt > 1) {
                        this.showToast('Connection Issue', 
                            `File data could not be loaded after ${attempt} attempts. The file is safely stored and will be available when connection is restored.`, 
                            'warning');
                    } else {
                        this.showToast('File Error', errorMessage, 'danger');
                    }
                    
                    this.hideLoadingSpinner();
                    console.error('Final load error after', attempt, 'attempts:', error);
                }
            });
        };
        
        loadWithRetry();
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

        // Show analysis section and hide files section
        document.getElementById('filesSection').style.display = 'none';
        document.getElementById('analysisSection').style.display = 'block';
    }

    renderPositions(mutatedPositions, lowConfPositions) {
        const mutatedContainer = document.getElementById('mutatedPositions');
        const lowConfContainer = document.getElementById('lowConfPositions');

        // Render mutated positions with click handlers
        if (mutatedPositions.length > 0) {
            const mutatedHtml = mutatedPositions.map(pos => 
                `<button class="position-badge" title="Click to highlight position ${pos}" data-position="${pos}" onclick="dashboard.highlightTablePosition(${pos})">${pos}</button>`
            ).join('');
            mutatedContainer.innerHTML = mutatedHtml;
        } else {
            mutatedContainer.innerHTML = '<span class="text-muted small">No mutations detected</span>';
        }

        // Render low confidence positions with click handlers
        if (lowConfPositions.length > 0) {
            const lowConfHtml = lowConfPositions.map(pos => 
                `<button class="position-badge low-conf" title="Click to highlight position ${pos}" data-position="${pos}" onclick="dashboard.highlightTablePosition(${pos})">${pos}</button>`
            ).join('');
            lowConfContainer.innerHTML = lowConfHtml;
        } else {
            lowConfContainer.innerHTML = '<span class="text-muted small">All positions high confidence</span>';
        }
    }

    renderDataTable(results) {
        // Properly destroy existing DataTable if it exists
        if (this.dataTable) {
            try {
                this.dataTable.destroy();
                this.dataTable = null;
                // Remove any DataTables specific classes
                $('#dataTable').removeClass('dataTable');
            } catch (e) {
                console.warn('Error destroying DataTable:', e);
            }
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
                <td class="mutation-cell">
                    <div class="mutation-repr-enhanced">${this.formatMutationRepresentation(result['Mutation Representation'], result.Color)}</div>
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

        // Initialize DataTable with enhanced visibility for positions up to 50
        try {
            this.dataTable = $('#dataTable').DataTable({
                destroy: true, // Allow DataTable to be destroyed and recreated
                pageLength: 50, // Show first 50 positions clearly
                lengthMenu: [[25, 50, 100, -1], [25, 50, 100, "All"]], // Multiple page size options
                paging: true, // Enable pagination for better position viewing
                scrollY: '65vh', // Vertical scrolling height
                scrollX: true, // Horizontal scrolling if needed
                scrollCollapse: true,
                order: [[0, 'asc']], // Sort by position
                dom: '<"row"<"col-sm-6"l><"col-sm-6"f>>' +
                     '<"row"<"col-sm-12"tr>>' +
                     '<"row"<"col-sm-5"i><"col-sm-7"p>>', // Show all controls including pagination
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
                    info: "Showing _START_ to _END_ of _TOTAL_ positions",
                    infoEmpty: "No positions found",
                    infoFiltered: "(filtered from _MAX_ total positions)",
                    lengthMenu: "Show _MENU_ positions per page"
                },
                responsive: false,
                autoWidth: false,
                processing: false
            });
        } catch (e) {
            console.error('Error initializing DataTable:', e);
            // Fallback: show table without DataTable features
            console.log('Table displayed without DataTable enhancements');
        }

        // Add custom styling for DataTables elements
        this.styleDataTable();
        
        // Add event listeners for position badge clicks and table row highlighting
        this.addTableInteractions();
    }
    
    formatMutationRepresentation(representation, color) {
        if (color === 'Green') {
            return `<span class="conserved-residue">${representation}</span>`;
        } else {
            // Enhanced formatting for mutations with clear separation
            const parts = representation.split(' | ');
            const formattedParts = [];
            
            parts.forEach(part => {
                if (part.includes('(') && !part.match(/^[A-Z]\d+[A-Z]/)) {
                    // Reference residue part (e.g., "A (20%)")
                    formattedParts.push(`<span class="reference-freq">${part}</span>`);
                } else {
                    // Multiple mutations part - split by comma and format each
                    const mutations = part.split(', ');
                    const formattedMutations = mutations.map(mutation => 
                        `<span class="mutation-change">${mutation.trim()}</span>`
                    ).join('<span class="mutation-separator">, </span>');
                    formattedParts.push(formattedMutations);
                }
            });
            
            return formattedParts.join('<span class="separator"> | </span>');
        }
    }
    
    addTableInteractions() {
        // Table row click highlighting
        $(document).on('click', '#dataTable tbody tr', (e) => {
            const $row = $(e.currentTarget);
            const position = $row.data('position');
            
            // Remove previous highlights
            $('#dataTable tbody tr').removeClass('highlighted-row');
            
            // Add highlight to clicked row
            $row.addClass('highlighted-row');
            
            // Show position info toast
            this.showToast('Position Selected', `Position ${position} highlighted`, 'info');
            
            // Auto-remove highlight after 5 seconds
            setTimeout(() => {
                $row.removeClass('highlighted-row');
            }, 5000);
        });
    }
    
    highlightTablePosition(position) {
        if (!this.dataTable) {
            this.showToast('Error', 'Table not loaded yet', 'warning');
            return;
        }

        // Clear any existing search to show all rows
        this.dataTable.search('').draw();
        
        // Find the correct page for this position
        const pageSize = this.dataTable.page.len();
        const targetPage = Math.floor((position - 1) / pageSize);
        
        // Go to the correct page
        this.dataTable.page(targetPage).draw(false);
        
        // Small delay to ensure page is rendered
        setTimeout(() => {
            // Find and highlight the target row
            const targetRow = document.querySelector(`#dataTable tbody tr[data-position="${position}"]`);
            if (targetRow) {
                // Remove previous highlights
                document.querySelectorAll('#dataTable tbody tr').forEach(row => {
                    row.classList.remove('highlighted-row');
                });
                
                // Add highlight to target row
                targetRow.classList.add('highlighted-row');
                
                // Scroll to the row smoothly
                targetRow.scrollIntoView({ 
                    behavior: 'smooth', 
                    block: 'center' 
                });
                
                // Show success toast
                this.showToast('Position Highlighted', `Position ${position} is now highlighted in the table`, 'success');
                
                // Auto-remove highlight after 8 seconds
                setTimeout(() => {
                    targetRow.classList.remove('highlighted-row');
                }, 8000);
            } else {
                this.showToast('Position Not Found', `Position ${position} could not be found in the table`, 'warning');
            }
        }, 100);
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
        document.getElementById('currentFileName').textContent = 'Mutation Analysis Results';
        document.getElementById('fileInfo').innerHTML = '';
        document.getElementById('downloadBtn').classList.add('d-none');
        document.getElementById('filesSection').style.display = 'block';
        document.getElementById('analysisSection').style.display = 'none';
        
        // Properly destroy DataTable with enhanced cleanup
        if (this.dataTable) {
            try {
                this.dataTable.destroy();
                this.dataTable = null;
                // Remove DataTables specific classes
                $('#dataTable').removeClass('dataTable');
                // Clear any DataTables wrapper elements
                $('#dataTable_wrapper').remove();
            } catch (e) {
                console.warn('Error destroying DataTable in resetView:', e);
                this.dataTable = null;
            }
        }
    }



    updateUploadStatus(message) {
        const status = document.getElementById('uploadStatus');
        if (status) status.textContent = message;
    }

    showUploadProgress() {
        const progressContainer = document.getElementById('upload-progress');
        if (progressContainer) {
            progressContainer.style.display = 'block';
            this.updateUploadProgress(0);
        }
    }

    hideUploadProgress() {
        const progressContainer = document.getElementById('upload-progress');
        if (progressContainer) {
            progressContainer.style.display = 'none';
        }
    }

    updateUploadProgress(percentage) {
        const progressContainer = document.getElementById('upload-progress');
        if (progressContainer) {
            const progressBar = progressContainer.querySelector('.progress-bar');
            if (progressBar) {
                progressBar.style.width = `${percentage}%`;
                progressBar.setAttribute('aria-valuenow', percentage);
            }
        }
    }

    showLoadingSpinner() {
        const spinner = document.getElementById('loadingSpinner');
        const table = document.getElementById('tableContainer');
        const welcome = document.getElementById('welcomeMessage');
        
        if (spinner) spinner.classList.remove('d-none');
        if (table) table.classList.add('d-none');
        if (welcome) welcome.classList.add('d-none');
    }

    hideLoadingSpinner() {
        const spinner = document.getElementById('loadingSpinner');
        if (spinner) spinner.classList.add('d-none');
    }

    showToast(title, message, type = 'info') {
        const toast = document.getElementById('toastNotification');
        if (!toast) return;
        
        const toastHeader = toast.querySelector('.toast-header');
        const toastBody = toast.querySelector('.toast-body');
        
        if (!toastHeader || !toastBody) return;
        
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