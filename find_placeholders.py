import zipfile
import re

def find_placeholders(path):
    try:
        with zipfile.ZipFile(path, 'r') as z:
            xml_content = z.read('word/document.xml').decode('utf-8')
            # Find all occurrences of {{...}}
            # XML tags might be inside the braces like {{<w:t>Key</w:t>}} so we need to be careful.
            # A better approach for docx xml is to remove tags first, then look for {{...}}
            
            # Simple tag stripper
            text = re.sub('<[^>]+>', '', xml_content)
            
            matches = re.findall(r'\{\{.*?\}\}', text)
            print("--- Found Placeholders ---")
            for m in set(matches):
                print(m)
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    find_placeholders("backend/template.docx")
