# Overview

This is a bioinformatics web application for analyzing mutation frequencies in DNA/protein sequence alignments. The application allows researchers to upload sequence alignment files (FASTA, TXT, CSV formats) and generates detailed mutation analysis reports with visual dashboards. It identifies conserved positions versus positions with mutations, calculates frequency percentages for each variant, and provides downloadable CSV results.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Frontend Architecture
- **Template Engine**: Jinja2 templates with Bootstrap 5 dark theme for responsive UI
- **JavaScript**: Vanilla JavaScript for form validation, file upload handling, and interactive features
- **Data Tables**: DataTables.js for sortable, searchable results display
- **Styling**: Custom CSS with Bootstrap components, Font Awesome icons, and mutation-specific color coding

## Backend Architecture
- **Web Framework**: Flask with Werkzeug utilities for file handling and proxy support
- **File Processing**: Secure file upload with extension validation and size limits (16MB max)
- **Session Management**: Flask sessions with configurable secret key
- **Logging**: Python logging module for debugging and monitoring

## Data Processing Engine
- **Bioinformatics Library**: BioPython for sequence alignment parsing and analysis
- **File Format Support**: FASTA, FA, TXT, and CSV alignment files
- **Analysis Algorithm**: Position-by-position mutation frequency calculation with configurable gap handling
- **Output Generation**: CSV export functionality with detailed mutation statistics

## File Storage Strategy
- **Upload Directory**: Local filesystem storage in 'uploads' folder
- **Temporary Processing**: Python tempfile module for secure temporary file handling
- **Result Files**: Generated CSV files stored temporarily for download

## Security Features
- **File Validation**: Whitelist-based file extension checking and secure filename generation
- **Size Limits**: Maximum file size enforcement to prevent resource exhaustion
- **Input Sanitization**: Werkzeug secure_filename for safe file handling

# External Dependencies

## Core Libraries
- **Flask**: Web application framework
- **BioPython**: Sequence analysis and alignment file parsing
- **Werkzeug**: WSGI utilities and security features

## Frontend Dependencies
- **Bootstrap 5**: UI framework with dark theme variant
- **Font Awesome 6**: Icon library for visual enhancements
- **DataTables.js**: Advanced table functionality for results display

## Python Standard Library
- **logging**: Application monitoring and debugging
- **tempfile**: Secure temporary file operations
- **collections.Counter**: Efficient frequency counting for mutations
- **csv**: Results file generation
- **os**: File system operations and environment variable access