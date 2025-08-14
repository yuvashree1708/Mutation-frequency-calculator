from Bio import AlignIO
from collections import Counter
import csv
import os
import tempfile
import logging

def analyze_mutations(filepath, include_gaps=False):
    """
    Analyze mutations in a sequence alignment file.
    
    Args:
        filepath (str): Path to the input alignment file
        include_gaps (bool): Whether to include gaps in calculations
        
    Returns:
        tuple: (results_list, output_filepath)
    """
    try:
        # Determine file format based on extension
        file_ext = filepath.split('.')[-1].lower()
        
        # Map file extensions to BioPython format names
        format_map = {
            'fasta': 'fasta',
            'fa': 'fasta',
            'txt': 'fasta',  # Assume text files are FASTA format
            'csv': 'fasta'   # Handle CSV as FASTA for now
        }
        
        file_format = format_map.get(file_ext, 'fasta')
        
        # Read alignment
        logging.debug(f"Reading alignment from {filepath} with format {file_format}")
        alignment = AlignIO.read(filepath, file_format)
        num_positions = alignment.get_alignment_length()
        
        if len(alignment) == 0:
            raise ValueError("No sequences found in the alignment file")
        
        # Pick reference sequence (first sequence in alignment)
        reference_seq = alignment[0].seq
        
        logging.info(f"Processing {len(alignment)} sequences with {num_positions} positions")
        file_size_mb = os.path.getsize(filepath) / (1024 * 1024)
        logging.info(f"File size: {file_size_mb:.1f}MB")
        
        results = []
        
        # Process in chunks for large files to optimize memory usage
        chunk_size = min(1000, num_positions) if file_size_mb > 10 else num_positions
        if chunk_size < num_positions:
            logging.info(f"Processing large file in chunks of {chunk_size} positions")
        
        for i in range(num_positions):
            if i % chunk_size == 0:
                logging.debug(f"Processing position {i + 1}/{num_positions} ({((i + 1) / num_positions * 100):.1f}%)")
            
            column = alignment[:, i]  # Residues at position i across all sequences
            counts = Counter(column)
            
            # Remove gaps if not counting them
            if not include_gaps:
                counts.pop("-", None)
            
            # Check for ambiguity
            has_ambiguity = "X" in counts
            
            # Sequences to consider for % calculation (exclude ambiguities)
            total_non_ambig = sum(v for k, v in counts.items() if k != "X")
            
            # Calculate percentages
            if total_non_ambig > 0:
                freq_percent = {res: round((count / total_non_ambig) * 100, 2)
                               for res, count in counts.items() if res != "X"}
            else:
                freq_percent = {}
            
            ref_res = str(reference_seq[i])
            position_number = i + 1  # 1-based position
            
            # Enhanced mutation representation & color coding with clear formatting
            mutation_freqs = {res: pct for res, pct in freq_percent.items() if res != ref_res}
            
            if not mutation_freqs:
                mutation_status = "Green"
                # Show reference residue with its frequency
                ref_freq = freq_percent.get(ref_res, 100)
                representation = f"{ref_res} ({ref_freq}%)"
            else:
                mutation_status = "Red"
                # Enhanced format: show reference frequency + all mutations clearly separated
                ref_freq = freq_percent.get(ref_res, 0)
                representation_parts = []
                
                # Add reference residue frequency if present
                if ref_freq > 0:
                    representation_parts.append(f"{ref_res} ({ref_freq}%)")
                
                # Add each mutation clearly formatted: RefPos+Mutated (frequency)
                mutation_parts = []
                for res, pct in sorted(mutation_freqs.items()):
                    mutation_parts.append(f"{ref_res}{position_number}{res} ({pct}%)")
                
                # Join multiple mutations with comma separation for clarity
                if len(mutation_parts) > 1:
                    mutation_display = ", ".join(mutation_parts)
                else:
                    mutation_display = mutation_parts[0] if mutation_parts else ""
                
                # Final representation: Reference frequency | All mutations
                if ref_freq > 0:
                    representation = f"{ref_res} ({ref_freq}%) | {mutation_display}"
                else:
                    representation = mutation_display
                logging.debug(f"Position {position_number}: Enhanced representation = {representation}")
            
            results.append({
                "Position": i + 1,
                "Reference": ref_res,
                "Counts": str(dict(counts)),  # Convert to string for CSV
                "Frequencies (%)": str(freq_percent),  # Convert to string for CSV
                "Ambiguity": "Low-confidence" if has_ambiguity else "High-confidence",
                "Mutation Representation": representation,
                "Color": mutation_status
            })
        
        # Save to CSV
        output_filename = f"mutation_analysis_results.csv"
        output_filepath = os.path.join("uploads", output_filename)
        
        with open(output_filepath, "w", newline="") as csvfile:
            fieldnames = ["Position", "Reference", "Counts", "Frequencies (%)", 
                         "Ambiguity", "Mutation Representation", "Color"]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for row in results:
                writer.writerow(row)
        
        logging.debug(f"Analysis complete. Results saved to {output_filepath}")
        return results, output_filename
        
    except Exception as e:
        logging.error(f"Error in mutation analysis: {str(e)}")
        raise Exception(f"Failed to analyze mutations: {str(e)}")
