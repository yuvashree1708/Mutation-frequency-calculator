# Overview

This is an interactive bioinformatics web dashboard for analyzing mutation frequencies in DNA/protein sequence alignments. The application features a sidebar-based interface where users can upload sequence files (FASTA, TXT, CSV formats) and maintain a session-based history of analyzed files. The main content area displays interactive, scrollable tables with mutation analysis results, and highlights specific mutation positions rather than traditional statistical summaries.

# User Preferences

Preferred communication style: Simple, everyday language.
File upload preferences: Maximum file size support (3GB per file) for large genomic datasets.
Workspace storage: Expanded capacity to store up to 25 files per workspace (DENV/CHIKV).

# System Architecture

## Frontend Architecture
- **Template Engine**: Single-page dashboard template (dashboard.html) with Bootstrap 5 dark theme
- **JavaScript**: ES6 class-based MutationDashboard for managing file history, AJAX uploads, and dynamic table rendering
- **UI Layout**: Two-panel design with collapsible sidebar for file history and main content area for interactive tables
- **Data Tables**: DataTables.js with advanced features (search, pagination, scrolling, position jumping)
- **Styling**: Custom responsive CSS with sidebar navigation, mutation position highlighting, and toast notifications

## Backend Architecture
- **Web Framework**: Flask with RESTful API endpoints for AJAX communication and SQLAlchemy ORM
- **Database**: PostgreSQL with Flask-SQLAlchemy for persistent file storage and metadata management
- **File Processing**: AJAX-based file upload with unique file ID generation and temporary storage
- **Data Persistence**: Database models for UploadedFile with comprehensive metadata and analysis results
- **API Endpoints**: /api/file/<id>, /api/history, /api/clear-history for dynamic data management
- **Logging**: Python logging module with detailed debugging for file processing and database operations

## Data Processing Engine
- **Bioinformatics Library**: BioPython for sequence alignment parsing and analysis
- **File Format Support**: FASTA, FA, TXT, and CSV alignment files
- **Analysis Algorithm**: Position-by-position mutation frequency calculation with configurable gap handling
- **Output Generation**: CSV export functionality with detailed mutation statistics

## File Storage Strategy
- **Database-Persistent Storage**: PostgreSQL database stores file metadata and analysis results with unlimited history
- **Shared File Access**: All uploaded files are permanently available to all users across sessions
- **Temporary Processing**: Unique file ID system for secure processing and immediate cleanup of original uploads
- **JSON Results Storage**: Complete analysis results stored as JSON files on disk, referenced by database
- **CSV Export**: Generated CSV files available through download endpoints tied to database records
- **Large Dataset Support**: Enhanced capacity for comprehensive genomic analysis projects with multiple large files

## Security Features
- **File Validation**: Whitelist-based file extension checking and secure filename generation
- **Size Limits**: Maximum file size enforcement to prevent resource exhaustion
- **Input Sanitization**: Werkzeug secure_filename for safe file handling

# External Dependencies

## Core Libraries
- **Flask**: Web application framework with SQLAlchemy ORM integration
- **Flask-SQLAlchemy**: Database ORM for PostgreSQL integration
- **PostgreSQL**: Production database for persistent file storage and metadata
- **BioPython**: Sequence analysis and alignment file parsing
- **Werkzeug**: WSGI utilities and security features

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