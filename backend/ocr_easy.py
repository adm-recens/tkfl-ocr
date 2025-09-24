import easyocr
from PIL import Image
import numpy as np

def extract_text_easyocr(image_path):
    reader = easyocr.Reader(['en'])
    img = Image.open(image_path)
    img_np = np.array(img)
    result = reader.readtext(img_np, detail=0)
    return '\n'.join(result)
