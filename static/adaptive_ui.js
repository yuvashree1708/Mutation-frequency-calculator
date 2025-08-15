/**
 * Adaptive UI Manager - Handles user preference learning and UI adaptation
 */
class AdaptiveUIManager {
    constructor(workspace, userSessionId, initialPreferences = {}) {
        this.workspace = workspace;
        this.userSessionId = userSessionId;
        this.preferences = initialPreferences;
        this.activityLog = [];
        this.sessionStartTime = Date.now();
        this.layoutStartTime = Date.now();
        
        this.init();
    }
    
    init() {
        console.log('Adaptive UI Manager initialized for workspace:', this.workspace);
        
        // Apply saved preferences
        this.applyStoredPreferences();
        
        // Set up activity tracking
        this.setupActivityTracking();
        
        // Set up preference saving
        this.setupPreferenceSaving();
        
        // Load recommendations
        this.loadRecommendations();
        
        // Auto-save preferences periodically
        setInterval(() => this.autoSavePreferences(), 30000); // Every 30 seconds
    }
    
    applyStoredPreferences() {
        // Apply table page size preference
        if (this.preferences.table_page_size && window.dashboard && window.dashboard.dataTable) {
            window.dashboard.dataTable.page.len(this.preferences.table_page_size);
        }
        
        // Apply upload panel width
        if (this.preferences.upload_panel_width) {
            this.setUploadPanelWidth(this.preferences.upload_panel_width);
        }
        
        // Apply theme preference
        if (this.preferences.theme_preference && this.preferences.theme_preference !== 'dark') {
            this.applyTheme(this.preferences.theme_preference);
        }
        
        // Apply mutation highlight style
        if (this.preferences.mutation_highlight_style) {
            this.applyMutationHighlightStyle(this.preferences.mutation_highlight_style);
        }
        
        // Restore last viewed file
        if (this.preferences.last_viewed_file) {
            setTimeout(() => this.suggestLastViewedFile(), 2000);
        }
    }
    
    setupActivityTracking() {
        // Track file views
        if (window.dashboard) {
            const originalLoadFile = window.dashboard.loadFileData;
            if (originalLoadFile) {
                window.dashboard.loadFileData = (fileId, workspace) => {
                    this.logActivity('file_view', { file_id: fileId }, fileId);
                    this.savePreference('last_viewed_file', fileId);
                    return originalLoadFile.call(window.dashboard, fileId, workspace);
                };
            }
        }
        
        // Track table interactions
        $(document).on('page.dt', '#dataTable', (e, settings) => {
            this.logActivity('table_page_change', { 
                page: settings._iDisplayStart / settings._iDisplayLength,
                page_size: settings._iDisplayLength 
            });
        });
        
        $(document).on('length.dt', '#dataTable', (e, settings, len) => {
            this.logActivity('table_page_size_change', { new_size: len });
            this.savePreference('table_page_size', len);
        });
        
        $(document).on('order.dt', '#dataTable', (e, settings) => {
            const order = settings.aaSorting[0];
            this.logActivity('table_sort', { 
                column: order[0], 
                direction: order[1] 
            });
            this.savePreference('preferred_sort_column', order[0]);
            this.savePreference('preferred_sort_direction', order[1]);
        });
        
        // Track position jumps
        if (window.dashboard && window.dashboard.highlightTablePosition) {
            const originalHighlight = window.dashboard.highlightTablePosition;
            window.dashboard.highlightTablePosition = (position) => {
                this.logActivity('position_jump', { position: position });
                this.trackFrequentPosition(position);
                return originalHighlight.call(window.dashboard, position);
            };
        }
        
        // Track upload panel resizing
        $('.upload-panel').on('resize', () => {
            const width = $('.upload-panel').width();
            const totalWidth = $('.workspace-container').width();
            const widthPercentage = Math.round((width / totalWidth) * 100);
            this.savePreference('upload_panel_width', widthPercentage);
        });
        
        // Track scroll behavior
        let scrollTimeout;
        $('#dataTable_wrapper .dataTables_scrollBody').on('scroll', () => {
            clearTimeout(scrollTimeout);
            scrollTimeout = setTimeout(() => {
                this.logActivity('table_scroll', {
                    scroll_top: $('#dataTable_wrapper .dataTables_scrollBody').scrollTop()
                });
            }, 500);
        });
    }
    
    setupPreferenceSaving() {
        // Save layout performance on page unload
        $(window).on('beforeunload', () => {
            this.saveLayoutPerformance();
        });
        
        // Detect UI changes and save preferences
        this.detectUIChanges();
    }
    
    detectUIChanges() {
        // Detect theme changes (if theme switcher exists)
        $(document).on('click', '.theme-switcher', (e) => {
            const newTheme = $(e.target).data('theme');
            this.savePreference('theme_preference', newTheme);
            this.applyTheme(newTheme);
        });
        
        // Detect highlight style changes
        $(document).on('change', '.highlight-style-selector', (e) => {
            const newStyle = $(e.target).val();
            this.savePreference('mutation_highlight_style', newStyle);
            this.applyMutationHighlightStyle(newStyle);
        });
    }
    
    logActivity(activityType, activityData = null, fileId = null) {
        const activity = {
            activity_type: activityType,
            activity_data: activityData,
            file_id: fileId,
            timestamp: new Date().toISOString()
        };
        
        this.activityLog.push(activity);
        
        // Send to server asynchronously
        fetch(`/api/${this.workspace}/activity`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(activity)
        }).catch(error => {
            console.warn('Failed to log activity:', error);
        });
    }
    
    savePreference(key, value) {
        this.preferences[key] = value;
        
        // Save to server asynchronously
        fetch(`/api/${this.workspace}/preferences`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ key: key, value: value })
        }).catch(error => {
            console.warn('Failed to save preference:', error);
        });
    }
    
    autoSavePreferences() {
        // Auto-detect and save current UI state
        if (window.dashboard && window.dashboard.dataTable) {
            const currentPageSize = window.dashboard.dataTable.page.len();
            if (currentPageSize !== this.preferences.table_page_size) {
                this.savePreference('table_page_size', currentPageSize);
            }
        }
    }
    
    trackFrequentPosition(position) {
        if (!this.preferences.frequent_positions) {
            this.preferences.frequent_positions = [];
        }
        
        let positions = [...this.preferences.frequent_positions];
        const existingIndex = positions.indexOf(position);
        
        if (existingIndex > -1) {
            // Move to front if already exists
            positions.splice(existingIndex, 1);
        }
        
        positions.unshift(position);
        positions = positions.slice(0, 10); // Keep only top 10
        
        this.savePreference('frequent_positions', positions);
        this.updateQuickAccessPositions(positions);
    }
    
    updateQuickAccessPositions(positions) {
        // Create or update quick access position buttons
        let quickAccessContainer = $('#quick-access-positions');
        if (quickAccessContainer.length === 0) {
            quickAccessContainer = $('<div id="quick-access-positions" class="mb-3"></div>');
            $('#mutatedPositions').parent().prepend(quickAccessContainer);
        }
        
        if (positions.length > 0) {
            const buttonsHtml = positions.slice(0, 5).map(pos => 
                `<button class="btn btn-sm btn-outline-primary me-1 mb-1" 
                         onclick="dashboard.highlightTablePosition(${pos})" 
                         title="Quick access to frequently viewed position ${pos}">
                    ${pos}
                </button>`
            ).join('');
            
            quickAccessContainer.html(`
                <small class="text-muted d-block mb-1">Frequently Accessed:</small>
                ${buttonsHtml}
            `);
        }
    }
    
    loadRecommendations() {
        fetch(`/api/${this.workspace}/recommendations`)
            .then(response => response.json())
            .then(recommendations => {
                this.displayRecommendations(recommendations);
            })
            .catch(error => {
                console.warn('Failed to load recommendations:', error);
            });
    }
    
    displayRecommendations(recommendations) {
        // Display optimization tips
        if (recommendations.optimization_tips && recommendations.optimization_tips.length > 0) {
            this.showOptimizationTip(recommendations.optimization_tips[0]);
        }
        
        // Update quick access with frequent positions
        if (recommendations.frequent_positions && recommendations.frequent_positions.length > 0) {
            this.updateQuickAccessPositions(recommendations.frequent_positions);
        }
        
        // Auto-adjust page size if recommended
        if (recommendations.suggested_page_size && 
            recommendations.suggested_page_size !== this.preferences.table_page_size) {
            setTimeout(() => {
                this.suggestPageSizeOptimization(recommendations.suggested_page_size);
            }, 5000);
        }
    }
    
    showOptimizationTip(tip) {
        // Show subtle optimization tip
        const toast = $(`
            <div class="toast position-fixed top-0 end-0 m-3" role="alert" style="z-index: 9999;">
                <div class="toast-header bg-info text-white">
                    <i class="fas fa-lightbulb me-2"></i>
                    <strong class="me-auto">Tip</strong>
                    <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast"></button>
                </div>
                <div class="toast-body">
                    ${tip}
                </div>
            </div>
        `);
        
        $('body').append(toast);
        const bsToast = new bootstrap.Toast(toast[0], { delay: 8000 });
        bsToast.show();
        
        toast.on('hidden.bs.toast', () => toast.remove());
    }
    
    suggestPageSizeOptimization(suggestedSize) {
        if (confirm(`Based on your usage patterns, would you like to increase the table page size to ${suggestedSize} for better navigation?`)) {
            if (window.dashboard && window.dashboard.dataTable) {
                window.dashboard.dataTable.page.len(suggestedSize).draw();
                this.savePreference('table_page_size', suggestedSize);
            }
        }
    }
    
    suggestLastViewedFile() {
        const lastFileId = this.preferences.last_viewed_file;
        if (lastFileId && window.dashboard) {
            // Check if file exists in current history
            const fileExists = $('.file-card[data-file-id="' + lastFileId + '"]').length > 0;
            if (fileExists) {
                const toast = $(`
                    <div class="toast position-fixed top-0 end-0 m-3" role="alert" style="z-index: 9999;">
                        <div class="toast-header bg-primary text-white">
                            <i class="fas fa-history me-2"></i>
                            <strong class="me-auto">Continue Where You Left Off</strong>
                            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast"></button>
                        </div>
                        <div class="toast-body">
                            Would you like to continue analyzing your last viewed file?
                            <div class="mt-2">
                                <button class="btn btn-primary btn-sm me-2" onclick="dashboard.loadFileData('${lastFileId}', '${this.workspace}'); $(this).closest('.toast').toast('hide');">
                                    Continue
                                </button>
                                <button class="btn btn-outline-secondary btn-sm" data-bs-dismiss="toast">
                                    Dismiss
                                </button>
                            </div>
                        </div>
                    </div>
                `);
                
                $('body').append(toast);
                const bsToast = new bootstrap.Toast(toast[0], { autohide: false });
                bsToast.show();
                
                toast.on('hidden.bs.toast', () => toast.remove());
            }
        }
    }
    
    saveLayoutPerformance() {
        const sessionDuration = Math.round((Date.now() - this.sessionStartTime) / 1000 / 60); // minutes
        const layoutConfig = this.getCurrentLayoutConfig();
        
        fetch(`/api/${this.workspace}/layout-performance`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                layout_config: layoutConfig,
                usage_time: sessionDuration,
                satisfaction: this.calculateSatisfactionScore()
            })
        }).catch(error => {
            console.warn('Failed to save layout performance:', error);
        });
    }
    
    getCurrentLayoutConfig() {
        return {
            upload_panel_width: this.preferences.upload_panel_width || 25,
            table_page_size: this.preferences.table_page_size || 50,
            theme: this.preferences.theme_preference || 'dark',
            highlight_style: this.preferences.mutation_highlight_style || 'standard'
        };
    }
    
    calculateSatisfactionScore() {
        // Simple satisfaction score based on activity patterns
        const totalActivities = this.activityLog.length;
        const errorActivities = this.activityLog.filter(a => a.activity_type.includes('error')).length;
        
        if (totalActivities === 0) return 0.5; // Neutral if no activity
        
        const errorRate = errorActivities / totalActivities;
        return Math.max(0.1, 1.0 - errorRate); // Lower score with more errors
    }
    
    // UI Application Methods
    applyTheme(theme) {
        document.body.className = document.body.className.replace(/theme-\w+/, '');
        document.body.classList.add(`theme-${theme}`);
    }
    
    applyMutationHighlightStyle(style) {
        document.body.className = document.body.className.replace(/highlight-\w+/, '');
        document.body.classList.add(`highlight-${style}`);
    }
    
    setUploadPanelWidth(widthPercentage) {
        const uploadPanel = $('.upload-panel');
        const filesArea = $('.files-area');
        
        if (uploadPanel.length && filesArea.length) {
            uploadPanel.css('width', `${widthPercentage}%`);
            filesArea.css('width', `${100 - widthPercentage}%`);
        }
    }
}

// Global instance
window.adaptiveUI = null;

// Initialize when page loads
$(document).ready(() => {
    // Wait for workspace data to be available
    if (typeof workspaceData !== 'undefined') {
        window.adaptiveUI = new AdaptiveUIManager(
            workspaceData.workspace,
            workspaceData.userSessionId,
            workspaceData.userPreferences || {}
        );
    }
});