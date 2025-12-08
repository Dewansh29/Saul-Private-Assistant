import zipfile

def inspect_zip_structure(path):
    try:
        with zipfile.ZipFile(path, 'r') as z:
            print("--- Zip Contents ---")
            for name in z.namelist():
                print(name)
            
            if 'word/document.xml' in z.namelist():
                print("\n--- word/document.xml (First 500 chars) ---")
                xml_content = z.read('word/document.xml')
                print(xml_content[:500])
            else:
                print("\nERROR: word/document.xml not found!")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    inspect_zip_structure("backend/template.docx")
