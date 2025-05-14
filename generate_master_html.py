import os
import glob
import logging
from datetime import datetime
from html import escape
from bs4 import BeautifulSoup

__version__ = "1.0.0"
__changelog__ = """
1.0.0:
- Initial implementation to generate master HTML document
- Links to all platform-specific HTML files
- Embeds contents of each HTML file in tables
"""

def setup_logger(debug_dir: str) -> logging.Logger:
    """Set up logger for master HTML generation."""
    os.makedirs(debug_dir, exist_ok=True)
    log_file = os.path.join(debug_dir, "master_html_log.txt")
    logger = logging.getLogger("master_html")
    logger.setLevel(logging.INFO)
    logger.handlers = []
    handler = logging.FileHandler(log_file, encoding='utf-8')
    handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    logger.addHandler(handler)
    return logger

def generate_master_html(output_dir: str, logger: logging.Logger) -> None:
    """Generate master HTML file referencing all platform HTML files."""
    try:
        html_base_dir = os.path.join(output_dir, "html")
        master_html_file = os.path.join(output_dir, "master_output.html")
        
        if not os.path.isdir(html_base_dir):
            logger.error(f"HTML directory {html_base_dir} does not exist")
            print(f"Error: HTML directory {html_base_dir} does not exist")
            return
        
        # Start HTML document
        html_content = [
            "<!DOCTYPE html>",
            "<html>",
            "<head>",
            "<title>Master Audit Output</title>",
            "<style>",
            "body { font-family: Arial, sans-serif; margin: 20px; }",
            "h1 { color: #333; }",
            "h2 { color: #555; }",
            "table { border-collapse: collapse; width: 100%; margin-bottom: 20px; }",
            "th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }",
            "th { background-color: #f2f2f2; }",
            ".platform { margin-top: 40px; }",
            "</style>",
            "</head>",
            "<body>",
            "<h1>Master Audit Output</h1>",
            "<p>Generated on: {}</p>".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            "<h2>Table of Contents</h2>",
            "<ul>"
        ]
        
        # Collect HTML files by platform
        platforms = [d for d in os.listdir(html_base_dir) if os.path.isdir(os.path.join(html_base_dir, d))]
        html_files_by_platform = {}
        
        for platform in sorted(platforms):
            platform_dir = os.path.join(html_base_dir, platform)
            html_files = glob.glob(os.path.join(platform_dir, "*.html"))
            if html_files:
                html_files_by_platform[platform] = sorted(html_files)
                html_content.append(f"<li><a href='#{platform}'>{platform}</a></li>")
        
        html_content.append("</ul>")
        
        # Embed contents of each HTML file
        for platform, html_files in html_files_by_platform.items():
            html_content.append(f"<div class='platform' id='{platform}'")
            html_content.append(f"<h2>{platform}</h2>")
            for html_file in html_files:
                filename = os.path.basename(html_file)
                relative_path = os.path.join("html", platform, filename)
                logger.info(f"Processing {html_file} for master HTML")
                
                try:
                    with open(html_file, 'r', encoding='utf-8') as f:
                        soup = BeautifulSoup(f, 'html.parser')
                        table = soup.find('table')
                        if table:
                            html_content.append(f"<h3><a href='{relative_path}'>{filename}</a></h3>")
                            html_content.append(str(table))
                        else:
                            logger.warning(f"No table found in {html_file}")
                except Exception as e:
                    logger.error(f"Failed to process {html_file}: {str(e)}")
            
            html_content.append("</div>")
        
        html_content.extend(["</body>", "</html>"])
        
        # Write master HTML
        with open(master_html_file, 'w', encoding='utf-8') as f:
            f.write("\n".join(html_content))
        
        logger.info(f"Generated master HTML: {master_html_file}")
        print(f"Master HTML generated: {master_html_file}")
        
    except Exception as e:
        logger.error(f"Failed to generate master HTML: {str(e)}")
        print(f"Error generating master HTML: {str(e)}")
        raise

def main() -> None:
    """Main function to generate master HTML."""
    parser = argparse.ArgumentParser(description="Generate master HTML for audit outputs.")
    parser.add_argument("output_dir", help="Directory containing HTML output files")
    args = parser.parse_args()

    debug_dir = os.path.join(os.getcwd(), "debug")
    logger = setup_logger(debug_dir)
    
    generate_master_html(args.output_dir, logger)

if __name__ == "__main__":
    main()