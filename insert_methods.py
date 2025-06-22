#!/usr/bin/env python3

import re

# Read the fixed methods
with open('fixed_methods.py', 'r') as f:
    methods = f.read()

# Read the main file
with open('main.py', 'r') as f:
    content = f.read()

# Define the pattern to find the check_ytdlp_installed method
pattern = r'def check_ytdlp_installed\(self\):.*?self\.install_ytdlp_btn\.setText\("安装 yt-dlp"\)\n'
match = re.search(pattern, content, re.DOTALL)

if match:
    # Get the matched text
    matched_text = match.group(0)
    
    # Insert the methods after the check_ytdlp_installed method
    replacement = matched_text + "\n    " + methods.replace("\n", "\n    ") + "\n\n"
    new_content = content.replace(matched_text, replacement)
    
    # Write the new content back to the file
    with open('main.py', 'w') as f:
        f.write(new_content)
    
    print("Methods inserted successfully!")
else:
    print("Could not find the check_ytdlp_installed method in the file.") 