"""Main FFR Processor - coordinates all parsing and processing operations"""

from pathlib import Path
from typing import Set, List, Tuple
from .utils import FileProcessor, CSVSanitizer
from .parsers import XMLParser, JSONParser, UBEParser, SspecParser, ITFParser
from .processors import CSVProcessor, HTMLStatsGenerator, UnitDataSspecProcessor


class FFRProcessor:
    """
    Main processor class that coordinates all FFR check operations.
    """
    
    def __init__(self, input_dir: Path, output_dir: Path, sspec_qdf: str = None,
                 ube_file_path: str = None, mtlolf_file_path: str = None, ituff_dir_path: str = None,
                 visualid_filter: str = None):
        """
        Initialize the FFR processor.
        
        Args:
            input_dir: Input directory containing source files
            output_dir: Output directory for results
            sspec_qdf: QDF specification for sspec processing
            ube_file_path: Path to UBE file
            mtlolf_file_path: Path to MTL_OLF.xml file
            ituff_dir_path: Path to ITF directory
            visualid_filter: Comma-separated visualIDs to filter
        """
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.sspec_qdf = sspec_qdf
        self.ube_file_path = ube_file_path
        self.mtlolf_file_path = mtlolf_file_path
        self.ituff_dir_path = ituff_dir_path
        self.visualid_filter = visualid_filter
        
        # Initialize utilities
        self.file_processor = FileProcessor()
        self.sanitizer = CSVSanitizer()
        
        # Initialize parsers
        self.xml_parser = XMLParser(self.sanitizer)
        self.json_parser = JSONParser(self.sanitizer)
        self.ube_parser = UBEParser(self.sanitizer, self.file_processor)
        self.sspec_parser = SspecParser(self.file_processor)
        self.itf_parser = ITFParser()
        
        # Set visualID filter if provided
        if self.visualid_filter:
            self.itf_parser.set_visualid_filter(self.visualid_filter)
        
        # Initialize processors
        self.csv_processor = CSVProcessor(self.sanitizer, self.file_processor)
        self.unit_data_sspec_processor = UnitDataSspecProcessor()
        
        # Determine fusefilename
        self.fusefilename = self._determine_fusefilename()
        
        # Initialize HTML stats generator
        self.html_stats = HTMLStatsGenerator(self.output_dir, self.fusefilename)
        
        # Parse target QDFs if provided
        self.target_qdf_set = self._parse_target_qdfs(sspec_qdf) if sspec_qdf else set()
        
        # Store lotname and location for ITF file naming
        self.lotname = None
        self.location = None
    
    def _determine_fusefilename(self) -> str:
        """
        Determine the base filename for output files from input directory name.
        
        Returns:
            Base filename string
        """
        fusefilename = self.input_dir.name
        print(f"📝 Extracted FusefileName: '{fusefilename}'")
        return fusefilename
    
    def _parse_target_qdfs(self, sspec_qdf: str) -> Set[str]:
        """
        Parse target QDF specification.
        
        Args:
            sspec_qdf: QDF specification string
            
        Returns:
            Set of QDF identifiers
        """
        if not sspec_qdf or sspec_qdf.strip() == '*':
            return set()  # Wildcard - will be resolved later
        
        return set(qdf.strip() for qdf in sspec_qdf.split(',') if qdf.strip())
    
    def resolve_target_qdfs(self, sspec_file: Path) -> Tuple[Set[str], List[str]]:
        """
        Resolve target QDFs, including wildcard support.
        
        Args:
            sspec_file: Path to sspec.txt file
            
        Returns:
            Tuple of (set of QDFs, list of QDFs)
        """
        if self.sspec_qdf and self.sspec_qdf.strip() == '*':
            # Wildcard - discover all QDFs from sspec.txt
            print("\n🌟 Wildcard QDF specification detected - discovering all QDFs...")
            discovered_qdfs = set()
            
            for line in self.file_processor.read_file_lines(sspec_file):
                if line.startswith('FUSEDATA:'):
                    parts = line.split(':', 4)
                    if len(parts) >= 3:
                        qdf = parts[2].strip()
                        discovered_qdfs.add(qdf)
            
            print(f"✅ Discovered {len(discovered_qdfs)} unique QDFs: {sorted(discovered_qdfs)}")
            return discovered_qdfs, sorted(discovered_qdfs)
        else:
            return self.target_qdf_set, list(self.target_qdf_set)
    
    def parse_xml_optimized(self, xml_file_path: Path):
        """Parse XML file."""
        return self.xml_parser.parse_xml_optimized(xml_file_path)
    
    def parse_json_optimized(self, json_file_path: Path):
        """Parse JSON file."""
        return self.json_parser.parse_json_optimized(json_file_path)
    
    def parse_ube_file_optimized(self, ube_file_path: Path):
        """Parse UBE file."""
        return self.ube_parser.parse_ube_file_optimized(ube_file_path)
    
    def print_ube_statistics(self, ube_data):
        """Print UBE statistics."""
        return self.ube_parser.print_ube_statistics(ube_data)
    
    def parse_sspec_file_optimized(self, sspec_file_path: Path, target_qdf_set: Set[str]):
        """Parse sspec file."""
        return self.sspec_parser.parse_sspec_file_optimized(sspec_file_path, target_qdf_set)
    
    def process_itf_files(self) -> bool:
        """Process ITF files."""
        if not self.ituff_dir_path:
            return False
        return self.itf_parser.process_itf_files(
            Path(self.ituff_dir_path), self.output_dir, self.fusefilename, self.lotname, self.location
        )
    
    def create_matched_csv(self, xml_data, json_data, output_csv_path: Path):
        """Create matched CSV file."""
        return self.csv_processor.create_matched_csv(xml_data, json_data, output_csv_path)
    
    def create_dff_mtl_olf_check_csv(self, xml_data, ube_data, output_csv_path: Path):
        """Create V_Report_DFF_UnitData CSV file."""
        return self.csv_processor.create_dff_mtl_olf_check_csv(xml_data, ube_data, output_csv_path)
    
    def create_sspec_breakdown_csv(self, sspec_data, fusedef_csv_path: Path) -> bool:
        """Create S_SSPEC_Breakdown CSVs."""
        target_qdf_list = list(self.target_qdf_set)
        return self.sspec_parser.create_sspec_breakdown_csv(
            sspec_data, fusedef_csv_path, self.output_dir, self.fusefilename, target_qdf_list
        )
    
    def write_csv_optimized(self, data, csv_file_path: Path, headers):
        """Write CSV file."""
        self.csv_processor.write_csv_optimized(data, csv_file_path, headers)
    
    def generate_html_statistics_report(self) -> str:
        """Generate HTML statistics report."""
        return self.html_stats.generate_html_report()
    
    def extract_lotname_location_from_ube(self, ube_file_path: Path) -> Tuple[str, str]:
        """Extract lot name and location from UBE file."""
        return self.ube_parser.extract_lotname_location_from_ube(ube_file_path)
    
    def create_unit_data_sspec_csv(self, itf_processed: bool) -> bool:
        """Create S_UnitData_by_Fuse CSV files."""
        if not itf_processed or not self.lotname or not self.location:
            return False
        
        # Find ITF fullstring file
        itf_pattern = f"ITF_FullString_{self.fusefilename}_{self.lotname}_{self.location}.csv"
        itf_file = self.output_dir / itf_pattern
        
        if not itf_file.exists():
            print(f"⚠️  ITF fullstring file not found: {itf_pattern}")
            return False
        
        # Find DFF file if it exists
        dff_file = self.output_dir / f"V_Report_DFF_UnitData_{self.fusefilename}.csv"
        if not dff_file.exists():
            dff_file = None
        
        # Process each QDF
        success = False
        for qdf in self.target_qdf_set:
            sspec_file = self.output_dir / f"S_SSPEC_Breakdown_{qdf}_{self.fusefilename}.csv"
            if not sspec_file.exists():
                continue
            
            output_file = self.output_dir / f"S_UnitData_by_Fuse_{qdf}_{self.fusefilename}.csv"
            if self.unit_data_sspec_processor.create_unit_data_sspec_csv(
                sspec_file, itf_file, output_file, qdf, dff_file, self.input_dir
            ):
                success = True
        
        return success
