import markdown
import re
import os

def markdown_to_html(md_file, output_file):
    with open(md_file, 'r', encoding='utf-8') as f:
        md_content = f.read()
    
    # Remove XML tags like <w:p>...
    md_content = re.sub(r'```\{=openxml\}.*?```', '', md_content, flags=re.DOTALL)
    
    html_content = markdown.markdown(md_content, extensions=['tables', 'fenced_code'])
    
    # Add support for newlines (Markdown single newlines usually don't map to <br>, but we want them to)
    md_content = md_content.replace('  \n', '\n').replace('\n', '  \n')
    
    html_content = markdown.markdown(md_content, extensions=['tables', 'fenced_code', 'nl2br'])
    
    # Clean up double linebreaks after headers that might be caused by double space newlines
    html_content = re.sub(r'(</h[1-6]>)\s*<br\s*/?>', r'\1', html_content)
    # Don't clean up <br> after </p> because it ruins paragraph spacing
    # html_content = re.sub(r'(</p>)\s*<br\s*/?>', r'\1', html_content)
    # html_content = re.sub(r'<br\s*/?>\s*(<p>)', r'\1', html_content)
    
    # Ensure double newlines inside markdown translate to properly separated HTML blocks or brs
    # by letting the markdown nl2br extension do its job
    
    # Process custom image and icon placeholders
    # Syntax: [[IMG-FULL:filename.jpg]]
    html_content = re.sub(r'\[\[IMG-FULL:(.*?)\]\]', r'<div style="clear: both; margin-top: 2em; display: block; overflow: hidden; height: 1px;">&nbsp;</div>\n<img src="images/\1" class="full-image" alt="\1">', html_content)
    
    # Syntax: [[IMG:filename.jpg]]
    html_content = re.sub(r'\[\[IMG:(.*?)\]\]', r'<div style="clear: both; margin-top: 2em; display: block; overflow: hidden; height: 1px;">&nbsp;</div>\n<img src="images/\1" class="left-image" alt="\1">', html_content)
    
    # Syntax: [[ICON:fa-solid fa-monument]]
    html_content = re.sub(r'\[\[ICON:(.*?)\]\]', r'<i class="\1" style="color:#7f8c8d; margin-right:8px;"></i>', html_content)
    
    # Optional header format for nested deep dive
    header_icons = {
        'Introduction & History': '<i class="fa-solid fa-book-open"></i> ',
        'Map': '<i class="fa-solid fa-map"></i> ',
        'Essential Things to Know': '<i class="fa-solid fa-circle-info"></i> ',
        'Historical & Cultural Context': '<i class="fa-solid fa-landmark"></i> ',
        'Schedule': '<i class="fa-regular fa-clock"></i> ',
        'Daily Overview': '<i class="fa-solid fa-compass"></i> ',
        'Detailed Context': '<i class="fa-solid fa-map-location-dot"></i> ',
        'DAY 1': '<i class="fa-regular fa-calendar-days"></i> ',
        'DAY 2': '<i class="fa-regular fa-calendar-days"></i> ',
        'Deep Dive: Historical Context': '<i class="fa-solid fa-landmark"></i> '
    }
    
    # Restore markdown headers that might be messed up by our double line break handling earlier
    html_content = re.sub(r'(<br\s*/?>\s*)+(<h[1-6]>)', r'\n\2', html_content)
    
    # Process tips and warnings based on keywords
    lines = html_content.split('\n')
    processed_lines = []
    in_list = False
    
    # Simple regex for warning/tip keywords
    warning_pattern = re.compile(r'<(p|li)>(.*?(?:Warning|Attention|Nightmare|Scam|Never|Problem).*?)<\/\1>', re.IGNORECASE)
    tip_pattern = re.compile(r'<(p|li)>(.*?(?:Tip|Advice|Essential|Golden rule|Note|Solution|Card).*?)<\/\1>', re.IGNORECASE)
    
    for line in lines:
        if warning_pattern.search(line):
            line = warning_pattern.sub(r'<div class="warning-box"><i class="fa-solid fa-triangle-exclamation warning-icon"></i> <strong>Attenzione:</strong> \2</div>', line)
        elif tip_pattern.search(line):
            line = tip_pattern.sub(r'<div class="tip-box"><i class="fa-solid fa-lightbulb tip-icon"></i> <strong>Tip:</strong> \2</div>', line)
            
        processed_lines.append(line)
        
    html_content = '\n'.join(processed_lines)
    
    
    css = """
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Merriweather:ital,wght@0,300;0,400;0,700;1,400&family=Open+Sans:wght@400;600;700&display=swap');
        
        body {
            font-family: 'Open Sans', sans-serif;
            color: #2c3e50;
            background-color: #fff;
            line-height: 1.7;
            margin: 0;
            padding: 20px;
            max-width: 850px;
            margin: 0 auto;
        }
        h1, h2, h3 {
            font-family: 'Merriweather', serif;
            color: #1a252f;
        }
        h1, h2, h3, h4, h5, h6 {
            color: #222;
            margin-top: 1.5em;
            margin-bottom: 0.5em;
            clear: both;
        }
        h1 {
            border-bottom: 3px solid #e74c3c;
            padding-bottom: 15px;
            margin-top: 2em;
            font-size: 2.5em;
            page-break-before: always;
            text-align: center;
        }
        h2 {
            color: #2980b9;
            border-bottom: 1px solid #bdc3c7;
            padding-bottom: 5px;
            margin-top: 1.8em;
        }
        h3 {
            color: #e67e22;
            margin-top: 1.5em;
            clear: both;
        }
        h1:first-child {
            page-break-before: auto;
        }
        .left-image {
            float: left;
            margin: 15px 20px 10px 0;
            max-width: 250px;
            border-radius: 4px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        .full-image {
            display: block;
            margin: 20px auto;
            max-width: 100%;
            height: auto;
            border-radius: 8px;
            box-shadow: 0 4px 10px rgba(0,0,0,0.15);
        }
        p {
            margin-bottom: 1.2em;
            text-align: justify;
        }
        
        /* Warning and Tips blocks */
        .warning-box, .tip-box {
            padding: 15px 20px;
            margin: 20px 0;
            border-radius: 8px;
            background-color: #fdfae6;
            border-left: 5px solid #f1c40f;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        }
        .warning-box {
            background-color: #fdedec;
            border-left: 5px solid #e74c3c;
        }
        .warning-box p:first-child, .tip-box p:first-child {
            margin-top: 0;
        }
        .warning-box p:last-child, .tip-box p:last-child {
            margin-bottom: 0;
        }
        .warning-icon {
            color: #e74c3c;
            margin-right: 10px;
        }
        .tip-icon {
            color: #f39c12;
            margin-right: 10px;
        }
        
        ul, ol {
            margin-bottom: 1em;
            padding-left: 20px;
        }
        
        ul ul {
            list-style-type: none;
            padding-left: 25px;
            margin-top: 5px;
            margin-bottom: 10px;
            border-left: 2px solid #eaeaea;
        }
        ul ul li {
            position: relative;
            margin-bottom: 8px;
            padding-left: 5px;
        }
        ul ul li::before {
            content: "•";
            color: #2980b9; /* Change to preferred color for bullets or use FontAwesome below */
            display: inline-block;
            width: 1em;
            margin-left: -1em;
            font-weight: bold;
        }
        
        /* Make sure the icons we explicitly add don't clash with the pseudo-element bullet */
        ul ul li:has(i) {
            padding-left: 0;
        }
        ul ul li:has(i)::before {
            content: none;
        }
        hr {
            border: 0;
            border-top: 1px solid #eaeaea;
            margin: 2em 0;
            clear: both;
        }
        strong {
            color: #000;
        }
        @media print {
            body {
                background-color: transparent;
                padding: 0;
                max-width: none;
                font-size: 10pt;
            }
            .warning-box, .tip-box {
                break-inside: avoid;
                border: 1px solid #e0e0e0;
                border-left: 5px solid #e74c3c; /* fallback for print */
            }
            .tip-box {
                border-left: 5px solid #f1c40f;
            }
            .left-image {
                max-width: 200px;
                break-inside: avoid;
            }
            .full-image {
                max-width: 100%;
                break-inside: avoid;
            }
            h1, h2, h3 {
                break-after: avoid;
            }
            p, li {
                break-inside: avoid;
            }
            @page {
                margin: 2cm;
            }
        }
        .clearfix::after {
            content: "";
            clear: both;
            display: table;
        }
    </style>
    """
    
    full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Istanbul Itinerary</title>
    {css}
</head>
<body>
    <div class="clearfix">
        {html_content}
    </div>
</body>
</html>
"""
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(full_html)
        
if __name__ == "__main__":
    markdown_to_html('itinerary/_istanbul_itinerary_combined.md', 'itinerary/index.html')
