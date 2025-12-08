from docx import Document

def list_styles(path):
    try:
        doc = Document(path)
        print(f"--- Styles in {path} ---")
        styles = [s.name for s in doc.styles if s.type.name == 'PARAGRAPH']
        for s in styles:
            print(s)
            
        print(f"\nHas 'List Bullet'? {'List Bullet' in styles}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    list_styles("backend/template.docx")
