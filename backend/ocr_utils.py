from PIL import Image, ImageOps, ImageFilter
import pytesseract

def preprocess_image(path, mode='default'):
    img = Image.open(path)
    if mode == 'contrast':
        img = ImageOps.grayscale(img)
        img = ImageOps.autocontrast(img)
    elif mode == 'threshold':
        img = ImageOps.grayscale(img)
        img = img.point(lambda x: 0 if x < 128 else 255, '1')
    elif mode == 'resize':
        img = img.resize((img.width * 2, img.height * 2))
    else:
        img = ImageOps.grayscale(img)
        img = img.filter(ImageFilter.MedianFilter(size=3))
    return img

def extract_text(path, mode='default'):
    try:
        img = preprocess_image(path, mode)
        text = pytesseract.image_to_string(img, lang='eng')
        return text or ''
    except Exception as e:
        return f'[OCR ERROR] {e}'
