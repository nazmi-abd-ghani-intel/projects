"""Main entry point for FFR Check application"""

import sys
import argparse
from pathlib import Path
from .ffr_processor import FFRProcessor
from .utils import ConsoleLogger, get_config


def main():
    """Main function to run FFR Check."""
    # Load configuration for defaults
    config = get_config()
    
    parser = argparse.ArgumentParser(
        description='FFR Check - Enhanced version with ITF parsing integration, memory optimization, and flexible file paths',
        epilog='Note: Default values can be configured in config.json under "default_arguments" section'
    )
    
    # Get defaults from config
    default_output = config.get('default_arguments.output_dir', 'output')
    default_sspec = config.get('default_arguments.sspec')
    default_ube = config.get('default_arguments.ube')
    default_mtlolf = config.get('default_arguments.mtlolf')
    default_ituff = config.get('default_arguments.ituff')
    default_log = config.get('default_arguments.log', False)
    default_html_stats = config.get('default_arguments.html_stats', True)
    
    parser.add_argument('input_dir', nargs='?', default=config.get('default_arguments.input_dir'),
                       help='Input directory containing fuseDef.json and optionally sspec.txt')
    parser.add_argument('output_dir', nargs='?', default=default_output,
                       help=f'Output directory for generated CSV files (default: {default_output})')
    parser.add_argument('-sspec', '--sspec', default=default_sspec,
                       help='QDF specification(s) (e.g., L0V8 or L0V8,L0VS,L15E) or "*" for all QDFs in sspec.txt' + 
                       (f' (default: {default_sspec})' if default_sspec else ''))
    parser.add_argument('-ube', '--ube', default=default_ube,
                       help='UBE file path to parse' + (f' (default: {default_ube})' if default_ube else ''))
    parser.add_argument('-mtlolf', '--mtlolf', default=default_mtlolf,
                       help='MTL_OLF.xml file path (if not in input directory)' + 
                       (f' (default: {default_mtlolf})' if default_mtlolf else ''))
    parser.add_argument('-ituff', '--ituff', default=default_ituff,
                       help='Directory path containing ITF files to parse' + 
                       (f' (default: {default_ituff})' if default_ituff else ''))
    parser.add_argument('-log', '--log', action='store_true', default=default_log,
                       help=f'Enable console logging to file (default: {default_log})')
    parser.add_argument('--html-stats', action='store_true', default=default_html_stats,
                       help=f'Generate interactive HTML statistics report (default: {default_html_stats})')
    
    args = parser.parse_args()
    
    # Validate required input_dir
    if not args.input_dir:
        parser.error("input_dir is required (either via command line or config.json)")
    
    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    
    if not input_dir.exists() or not input_dir.is_dir():
        print(f"❌ Error: Invalid input directory '{input_dir}'")
        sys.exit(1)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    processor = FFRProcessor(input_dir, output_dir, args.sspec, args.ube, args.mtlolf, args.ituff)
    
    console_log_file = None
    if args.log:
        console_log_file = output_dir / f"xconsole_{processor.fusefilename}.txt"
    
    with ConsoleLogger(str(console_log_file) if console_log_file else None) as logger:
        # Determine XML file path
        if args.mtlolf:
            xml_file = Path(args.mtlolf)
            if not xml_file.exists():
                print(f"❌ Error: Specified MTL_OLF.xml file '{args.mtlolf}' does not exist")
                sys.exit(1)
        else:
            xml_file = input_dir / "MTL_OLF.xml"
        
        json_file = input_dir / "fuseDef.json"
        sspec_file = input_dir / "sspec.txt"
        
        xml_output_csv = output_dir / f"I_Report_MTL_OLF_{processor.fusefilename}.csv"
        json_output_csv = output_dir / f"I_Report_FuseDef_{processor.fusefilename}.csv"
        combined_output_csv = output_dir / f"V_Report_FuseDef_vs_MTL_OLF_{processor.fusefilename}.csv"
        
        print(f"📁 Input directory: {input_dir}")
        print(f"📁 Output directory: {output_dir}")
        print(f"📝 FusefileName: {processor.fusefilename}")
        if console_log_file:
            print(f"📄 Console log: {console_log_file}")
        if args.sspec:
            if args.sspec.strip() == '*':
                print(f"🌟 QDF specification: * (wildcard - will discover all QDFs from sspec.txt)")
            else:
                print(f"🎯 Target QDFs: {list(processor.target_qdf_set)}")
        if args.ube:
            print(f"📄 UBE file: {args.ube}")
        if args.mtlolf:
            print(f"📄 MTL_OLF file: {args.mtlolf}")
        else:
            print(f"📄 MTL_OLF file: {xml_file} (default location)")
        if args.ituff:
            print(f"📄 ITF directory: {args.ituff}")
        print("=" * 80)
        
        xml_data = []
        json_data = []
        ube_data = []
        
        # UBE processing
        if args.ube:
            ube_path = Path(args.ube)
            if ube_path.exists():
                print("🔄 Processing UBE file with memory optimization...")
                ube_data = processor.parse_ube_file_optimized(ube_path)
                if ube_data:
                    lotname, location = processor.extract_lotname_location_from_ube(ube_path)
                    processor.lotname = lotname
                    processor.location = location
                    ube_output_csv = output_dir / f"I_Report_UBE_{lotname}_{location}.csv"
                    headers = ['visualID', 'ULT', 'ref_level', 'first_socket_upload', 'token_name', 'tokenValue', 'MDPOSITION']
                    processor.write_csv_optimized(ube_data, ube_output_csv, headers)
                    processor.print_ube_statistics(ube_data)
            else:
                print(f"❌ Error: UBE file '{args.ube}' does not exist")
        
        # XML processing
        if xml_file.exists():
            print(f"🔄 Processing XML file: {xml_file}")
            xml_data = processor.parse_xml_optimized(xml_file)
            if xml_data:
                headers = [
                    'dff_token_id_MTL', 'token_name_MTL', 'first_socket_upload_MTL', 'upload_process_step_MTL',
                    'ssid_MTL', 'ref_level_MTL', 'module_MTL', 'field_name_MTL', 'field_name_seq_MTL',
                    'fuse_name_ori_MTL', 'fuse_name_MTL', 'fuse_register_ori_MTL', 'fuse_register_MTL'
                ]
                suffixed_data = [{f"{k}_MTL": v for k, v in row.items()} for row in xml_data]
                processor.write_csv_optimized(suffixed_data, xml_output_csv, headers)
        else:
            print(f"⚠️  MTL_OLF.xml not found at '{xml_file}'")
        
        # JSON processing
        if json_file.exists():
            print("🔄 Processing JSON file...")
            json_data = processor.parse_json_optimized(json_file)
            if json_data:
                headers = ['RegisterName_fuseDef', 'FuseGroup_Name_fuseDef', 'Fuse_Name_fuseDef', 'StartAddress_fuseDef', 'EndAddress_fuseDef']
                suffixed_data = [{f"{k}_fuseDef": v for k, v in row.items()} for row in json_data]
                processor.write_csv_optimized(suffixed_data, json_output_csv, headers)
        else:
            print(f"⚠️  fuseDef.json not found in input directory '{input_dir}'")
        
        # Create combined CSV
        if xml_data and json_data:
            print("🔄 Creating combined matched CSV with memory optimization...")
            combined_data = processor.create_matched_csv(xml_data, json_data, combined_output_csv)
        else:
            print("⚠️  Cannot create combined CSV - need both XML and JSON data")
        
        # Create xfuse-dff-unitData-check CSV
        if xml_data and ube_data:
            print("🔄 Creating xfuse-dff-unitData-check CSV...")
            dff_check_csv = output_dir / f"V_Report_DFF_UnitData_{processor.fusefilename}.csv"
            processor.create_dff_mtl_olf_check_csv(xml_data, ube_data, dff_check_csv)
        
        # Process ITF files
        itf_processed = False
        if args.ituff:
            itf_processed = processor.process_itf_files()
        
        # Process sspec.txt
        if args.sspec:
            if sspec_file.exists():
                print(f"📄 Processing sspec.txt for QDFs '{args.sspec}' with memory optimization...")
                
                target_qdf_set, target_qdf_list = processor.resolve_target_qdfs(sspec_file)
                
                if target_qdf_set:
                    sspec_data, resolved_qdf_list = processor.parse_sspec_file_optimized(sspec_file, target_qdf_set)
                    
                    if sspec_data and json_output_csv.exists():
                        print(f"✅ sspec data parsed successfully")
                        processor.create_sspec_breakdown_csv(sspec_data, json_output_csv)
                        
                        # Create unit data SSPEC CSV if ITF was processed
                        if itf_processed:
                            processor.create_unit_data_sspec_csv(itf_processed)
                    else:
                        print("⚠️  Cannot create sspec breakdown - need sspec data and FUSEDEF CSV")
                else:
                    print("⚠️  No QDFs resolved for processing")
            else:
                print(f"⚠️  sspec.txt not found in input directory '{input_dir}'")
        
        # Generate HTML statistics report
        if args.html_stats:
            html_report = processor.generate_html_statistics_report()
            print(f"\n📊 Interactive HTML statistics report generated: {html_report}")
            print(f"\n🌐 Open the following file in your browser to view interactive statistics:")
            print(f"   {html_report}")
        
        # Summary
        print("=" * 80)
        print("📋 PROCESSING SUMMARY:")
        
        if xml_data:
            print(f"✅ XML processing completed! Results: {xml_output_csv}")
        else:
            print("❌ XML processing failed or no data found")
        
        if json_data:
            print(f"✅ JSON processing completed! Results: {json_output_csv}")
        else:
            print("❌ JSON processing failed or no data found")
        
        if xml_data and json_data:
            print(f"✅ Combined matching completed! Results: {combined_output_csv}")
        else:
            print("❌ Combined matching failed or insufficient data")
        
        # Check for UBE+XML matching
        if not (xml_data and ube_data):
            print("❌ xfuse-dff-unitData-check processing failed or insufficient data")
        
        if not xml_data and not json_data and not ube_data and not itf_processed:
            print("❌ No files were processed successfully!")
            sys.exit(1)
        
        print(f"\n📁 All output files saved to: {output_dir}")
        print(f"🏷️  All files tagged with FusefileName: {processor.fusefilename}")
        if console_log_file:
            print(f"📄 Complete console log saved to: {console_log_file}")


if __name__ == "__main__":
    main()
