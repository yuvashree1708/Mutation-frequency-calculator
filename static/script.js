// JavaScript for mutation analysis dashboard

// Form submission handling
document.addEventListener('DOMContentLoaded', function() {
    const uploadForm = document.getElementById('uploadForm');
    const submitBtn = document.getElementById('submitBtn');
    const processingCard = document.getElementById('processingCard');
    const fileInput = document.getElementById('file');

    if (uploadForm) {
        uploadForm.addEventListener('submit', function(e) {
            // Validate file before submission
            if (!fileInput.files.length) {
                e.preventDefault();
                alert('Please select a file to upload.');
                return;
            }

            const file = fileInput.files[0];
            const maxSize = 16 * 1024 * 1024; // 16MB

            if (file.size > maxSize) {
                e.preventDefault();
                alert('File size exceeds 16MB limit. Please choose a smaller file.');
                return;
            }

            // Show processing state
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Processing...';
            
            if (processingCard) {
                processingCard.classList.remove('d-none');
            }
        });
    }

    // File input validation
    if (fileInput) {
        fileInput.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                const allowedTypes = ['.fasta', '.fa', '.txt', '.csv'];
                const fileName = file.name.toLowerCase();
                const isValidType = allowedTypes.some(type => fileName.endsWith(type));
                
                if (!isValidType) {
                    alert('Invalid file type. Please select a FASTA, TXT, or CSV file.');
                    fileInput.value = '';
                    return;
                }

                const maxSize = 16 * 1024 * 1024; // 16MB
                if (file.size > maxSize) {
                    alert('File size exceeds 16MB limit. Please choose a smaller file.');
                    fileInput.value = '';
                    return;
                }
            }
        });
    }
});

// Results page functionality
function initializeResultsTable() {
    if (typeof $ !== 'undefined' && $('#resultsTable').length) {
        $('#resultsTable').DataTable({
            pageLength: 25,
            lengthMenu: [[10, 25, 50, 100, -1], [10, 25, 50, 100, "All"]],
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
            }
        });
    }
}

function calculateSummaryStats() {
    const rows = document.querySelectorAll('#resultsTable tbody tr');
    let conservedCount = 0;
    let mutatedCount = 0;
    let ambiguousCount = 0;
    
    rows.forEach(row => {
        const color = row.getAttribute('data-color');
        const ambiguity = row.getAttribute('data-ambiguity');
        
        if (color === 'Green') {
            conservedCount++;
        } else if (color === 'Red') {
            mutatedCount++;
        }
        
        if (ambiguity === 'Low-confidence') {
            ambiguousCount++;
        }
    });
    
    const totalPositions = rows.length;
    const mutationRate = totalPositions > 0 ? 
        Math.round((mutatedCount / totalPositions) * 100) : 0;
    
    // Update summary cards
    const conservedEl = document.getElementById('conservedCount');
    const mutatedEl = document.getElementById('mutatedCount');
    const ambiguousEl = document.getElementById('ambiguousCount');
    const mutationRateEl = document.getElementById('mutationRate');
    
    if (conservedEl) conservedEl.textContent = conservedCount;
    if (mutatedEl) mutatedEl.textContent = mutatedCount;
    if (ambiguousEl) ambiguousEl.textContent = ambiguousCount;
    if (mutationRateEl) mutationRateEl.textContent = mutationRate + '%';
}

// Utility functions
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// Auto-dismiss alerts after 5 seconds
document.addEventListener('DOMContentLoaded', function() {
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        if (!alert.querySelector('.btn-close')) return;
        
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });
});

// Export functionality enhancement
function exportToCSV() {
    // This could be enhanced to export filtered results from DataTable
    const table = document.getElementById('resultsTable');
    if (!table) return;
    
    let csv = [];
    const rows = table.querySelectorAll('tr');
    
    for (let i = 0; i < rows.length; i++) {
        const row = [];
        const cols = rows[i].querySelectorAll('td, th');
        
        for (let j = 0; j < cols.length; j++) {
            row.push(cols[j].innerText);
        }
        csv.push(row.join(','));
    }
    
    const csvFile = new Blob([csv.join('\n')], { type: 'text/csv' });
    const downloadLink = document.createElement('a');
    downloadLink.download = 'filtered_results.csv';
    downloadLink.href = window.URL.createObjectURL(csvFile);
    downloadLink.style.display = 'none';
    document.body.appendChild(downloadLink);
    downloadLink.click();
    document.body.removeChild(downloadLink);
}

// Keyboard shortcuts
document.addEventListener('keydown', function(e) {
    // Ctrl+U for upload (on index page)
    if (e.ctrlKey && e.key === 'u' && document.getElementById('file')) {
        e.preventDefault();
        document.getElementById('file').click();
    }
    
    // Ctrl+D for download (on results page)
    if (e.ctrlKey && e.key === 'd' && document.querySelector('a[href*="download"]')) {
        e.preventDefault();
        document.querySelector('a[href*="download"]').click();
    }
});
