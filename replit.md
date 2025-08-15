# Overview

This is an interactive bioinformatics web dashboard for analyzing mutation frequencies in DNA/protein sequence alignments. The application features a sidebar-based interface where users can upload sequence files (FASTA, TXT, CSV formats) and maintain a session-based history of analyzed files. The main content area displays interactive, scrollable tables with mutation analysis results, and highlights specific mutation positions rather than traditional statistical summaries.

# User Preferences

Preferred communication style: Simple, everyday language.
File upload preferences: Maximum file size support (3GB per file) for large genomic datasets with optimized upload progress tracking and chunked processing.
Workspace storage: Keyword-based shared file access system for team collaboration.
Access control: Limited to "DENV" and "CHIKV" keywords only for workspace access.
File viewing: Each file requires "View Mutation Freq Table" button for viewing detailed mutation data.
Device accessibility: Fully responsive design for mobile phones, tablets, laptops, and desktops.
Adaptive UI: Personalized interface that learns user preferences and adapts layouts, table settings, and workflows based on usage patterns.
User preference memory: System remembers individual choices like table page sizes, sort preferences, frequently accessed positions, and UI layouts across sessions.

# System Architecture

## Adaptive UI & Personalization
- **User Preference Tracking**: Database-backed system that learns from user interactions and saves preferences persistently
- **Activity Learning**: Tracks user patterns like frequently accessed positions, preferred table settings, and file usage
- **Layout Optimization**: Automatically suggests and applies optimal UI configurations based on user behavior
- **Session Continuity**: Remembers last viewed files, table states, and workspace configurations across sessions
- **Smart Recommendations**: Provides personalized tips and shortcuts based on usage patterns

## Frontend Architecture
- **Template Engine**: Single-page dashboard template (workspace.html) with Bootstrap 5 dark theme
- **JavaScript**: ES6 class-based MutationDashboard for managing file history, AJAX uploads, and dynamic table rendering
- **UI Layout**: Center-focused grid layout for file display with analysis view switching
- **Data Tables**: DataTables.js with advanced features (search, pagination, scrolling, position jumping)
- **Styling**: Fully responsive CSS with mobile-first design, touch-friendly interfaces, and cross-device compatibility
- **File Actions**: Each file displays as a card with "View Mutation Freq Table" button for direct access to mutation data
- **Mobile Optimization**: Responsive grid layouts, touch-friendly buttons (44px+ touch targets), and optimized typography for all screen sizes

## Backend Architecture
- **Web Framework**: Flask with RESTful API endpoints for AJAX communication and SQLAlchemy ORM
- **Database**: PostgreSQL with Flask-SQLAlchemy for persistent file storage and metadata management
- **File Processing**: Optimized XMLHttpRequest upload with real-time progress tracking, 3GB file support, and 5-minute timeout for large files
- **Data Persistence**: Database models for UploadedFile with comprehensive metadata and analysis results
- **API Endpoints**: /api/file/<id>, /api/history, /api/clear-history for dynamic data management
- **Logging**: Python logging module with detailed debugging for file processing and database operations

## Data Processing Engine
- **Bioinformatics Library**: BioPython for sequence alignment parsing and analysis
- **File Format Support**: FASTA, FA, TXT, and CSV alignment files
- **Analysis Algorithm**: Position-by-position mutation frequency calculation with configurable gap handling and chunked processing for large datasets (1000 positions per chunk)
- **Output Generation**: CSV export functionality with detailed mutation statistics

## File Storage Strategy
- **Database-Persistent Storage**: PostgreSQL database stores file metadata and analysis results with keyword-based access control
- **Keyword-Based Sharing**: Files uploaded by users with the same keyword are shared within that group
- **Session Isolation**: Different keywords create separate file spaces for team collaboration
- **Temporary Processing**: Unique file ID system for secure processing and immediate cleanup of original uploads
- **JSON Results Storage**: Complete analysis results stored as JSON files on disk, referenced by database
- **CSV Export**: Generated CSV files available through download endpoints tied to database records
- **Large Dataset Support**: Enhanced capacity for comprehensive genomic analysis projects with multiple large files

## Security Features
- **File Validation**: Whitelist-based file extension checking and secure filename generation
- **Size Limits**: Maximum file size enforcement to prevent resource exhaustion
- **Input Sanitization**: Werkzeug secure_filename for safe file handling

## File Integrity & Reliability Systems
- **Atomic File Operations**: All file writes use atomic operations to prevent corruption
- **Multi-Level Backup System**: Primary, backup, and permanent backup copies for all files
- **Startup Integrity Checks**: Automatic verification and recovery on application start
- **Continuous Monitoring**: Scheduled integrity checks with auto-recovery capabilities
- **Orphaned Entry Cleanup**: Automatic detection and removal of database entries without files
- **Backup Recovery**: Automatic restoration from backups when primary files are missing
- **File Regeneration**: Ability to recreate results from original files when needed

# External Dependencies

## Core Libraries
- **Flask**: Web application framework with SQLAlchemy ORM integration
- **Flask-SQLAlchemy**: Database ORM for PostgreSQL integration with enhanced connection pooling
- **PostgreSQL**: Production database with connection pooling and retry mechanisms for deployment stability
- **BioPython**: Sequence analysis and alignment file parsing
- **Werkzeug**: WSGI utilities and security features
- **Gunicorn**: Production WSGI server with optimized worker configuration for large file handling

## Frontend Dependencies
- **Bootstrap 5**: UI framework with dark theme variant and toast notification system
- **Font Awesome 6**: Icon library for navigation, status indicators, and interactive elements
- **DataTables.js**: Advanced table functionality with scrolling, search, and position navigation
- **jQuery**: Required for DataTables and DOM manipulation

## Python Standard Library
- **logging**: Application monitoring and debugging
- **tempfile**: Secure temporary file operations
- **collections.Counter**: Efficient frequency counting for mutations
- **csv**: Results file generation
- **os**: File system operations and environment variable access