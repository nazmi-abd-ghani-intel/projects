"""HTML Statistics Generator for creating interactive reports"""

from typing import Dict, Any, List
from pathlib import Path
from datetime import datetime


class HTMLStatsGenerator:
    """
    Generates interactive HTML statistics reports.
    """
    
    def __init__(self, output_dir: Path, fusefilename: str):
        """
        Initialize the HTML stats generator.
        
        Args:
            output_dir: Output directory for HTML file
            fusefilename: Base filename for the report
        """
        self.output_dir = output_dir
        self.fusefilename = fusefilename
        self.stats_data = {}
        self.breakdown_data = []
    
    def add_stats_data(self, category: str, data: Dict[str, Any]) -> None:
        """
        Add statistics data for a category.
        
        Args:
            category: Category name (e.g., 'overview', 'matching', 'dff', 'sspec')
            data: Dictionary containing statistics
        """
        self.stats_data[category] = data
    
    def set_breakdown_data(self, breakdown_data: List[Dict[str, Any]]) -> None:
        """
        Set the breakdown data for detailed tables.
        
        Args:
            breakdown_data: List of breakdown records
        """
        self.breakdown_data = breakdown_data
    
    def generate_html_report(self) -> str:
        """
        Generate the interactive HTML statistics report.
        
        Returns:
            Path to the generated HTML file
        """
        html_file = self.output_dir / f"xstats_{self.fusefilename}.html"
        
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FFR Check Statistics - {self.fusefilename}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background-color: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #0078d4;
            border-bottom: 3px solid #0078d4;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #005a9e;
            margin-top: 30px;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }}
        .stat-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        .stat-label {{
            font-size: 14px;
            opacity: 0.9;
        }}
        .stat-value {{
            font-size: 32px;
            font-weight: bold;
            margin-top: 10px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background-color: #0078d4;
            color: white;
            font-weight: bold;
        }}
        tr:hover {{
            background-color: #f5f5f5;
        }}
        .timestamp {{
            color: #666;
            font-size: 14px;
            margin-top: 20px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 FFR Check Statistics Report</h1>
        <p><strong>FusefileName:</strong> {self.fusefilename}</p>
        <p class="timestamp">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        
        <h2>Overview</h2>
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-label">Processing Status</div>
                <div class="stat-value">✅ Complete</div>
            </div>
        </div>
        
        <!-- Additional statistics sections would be added here -->
        
    </div>
</body>
</html>"""
        
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return str(html_file)
