import zipfile
import re

def inspect_docx_xml(path):
    try:
        with zipfile.ZipFile(path, 'r') as z:
            xml_content = z.read('word/document.xml').decode('utf-8')
            # Remove xml tags to just see text (rough approximation)
            text = re.sub('<[^>]+>', '', xml_content)
            print("--- Raw Text Content ---")
            print(text[:2000]) # Print first 2000 chars
            
            print("\n--- Potential Placeholders ---")
            # Look for patterns like {{...}} or similar
            placeholders = re.findall(r'\{\{[^}]+\}\}', xml_content)
            print(placeholders)
            
            # Also look for ALL CAPS words that might be placeholders
            # caps = re.findall(r'\b[A-Z_]{3,}\b', text)
            # print(caps)

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    inspect_docx_xml("backend/template.docx")
