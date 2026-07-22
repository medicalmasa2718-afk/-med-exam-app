import os
import re
import fitz # PyMuPDF

pdf_path = "downloads/tp260424-01a_02.pdf"
doc = fitz.open(pdf_path)

IMAGE_DIR = "images"
os.makedirs(IMAGE_DIR, exist_ok=True)

mapped_images = {} # { "A16": "images/A16_p5.png", ... }

pattern = re.compile(r"\(([A-FＡ-Ｆ])\s*問題\s*(\d{1,3})\s*\)")

for i in range(len(doc)):
    page = doc[i]
    text = page.get_text()
    matches = pattern.findall(text)
    
    if matches:
        # Render high quality page image
        pix = page.get_pixmap(dpi=150)
        
        for block_raw, q_num in matches:
            block = block_raw.upper()
            if block in ['Ａ', 'Ｂ', 'Ｃ', 'Ｄ', 'Ｅ', 'Ｆ']:
                block = chr(ord(block) - ord('Ａ') + ord('A'))
                
            img_filename = f"block_{block}_q_{q_num}_p{i+1}.png"
            img_filepath = os.path.join(IMAGE_DIR, img_filename)
            pix.save(img_filepath)
            
            key = f"{block}{q_num}"
            mapped_images[key] = f"images/{img_filename}"
            print(f"Mapped Page {i+1} -> Block {block} Question {q_num} ({img_filename})")

print(f"Total mapped image pages: {len(mapped_images)}")
