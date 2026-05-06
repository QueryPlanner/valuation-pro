import sys
import json
from pathlib import Path

# Add the packages directory to sys.path so we can import the module directly
# without needing to install it globally for this script
sys.path.insert(0, str(Path(__file__).parent / "packages" / "xbrl-downloader" / "src"))

from xbrl_downloader.parser import XBRLParser

def main():
    if len(sys.argv) < 2:
        print("Usage: python inspect_xbrl.py <path_to_xml_file>")
        print("Example: python inspect_xbrl.py valuation_data/BPCL/BPCL_Annual_2025-03-31.xml")
        sys.exit(1)
        
    file_path = sys.argv[1]
    if not Path(file_path).exists():
        print(f"Error: File '{file_path}' does not exist.")
        sys.exit(1)
        
    print(f"Parsing: {file_path}...\n")
    parser = XBRLParser(file_path)
    data = parser.parse()
    
    # Print the output beautifully formatted as JSON
    print(json.dumps(data, indent=2))
    
    print(f"\n--- Summary ---")
    for period, metrics in data.items():
        print(f"Period: {period} -> {len(metrics)} tags extracted")

if __name__ == "__main__":
    main()
