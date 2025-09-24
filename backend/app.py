# backend/app.py

from flask import Flask, render_template, request, redirect, url_for, jsonify, send_from_directory
from .db import init_db, get_connection
from backend.ocr_service import extract_text
from backend.ocr_utils import extract_text as extract_text_adv
from PIL import Image
from backend.parser import parse_receipt_text
import os
import json

app = Flask(__name__, template_folder=os.path.join(os.path.dirname(__file__), "templates"))
# uploads folder (project root/uploads)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
UPLOAD_FOLDER = os.path.join(PROJECT_ROOT, "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Initialize DB on startup
init_db()




@app.route("/", methods=["GET"])
def index():
    print("[DEBUG] / route called")
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id, voucher_no, voucher_date, supplier_code, created_at FROM vouchers_master ORDER BY created_at DESC")
        rows = cur.fetchall()
        print(f"[DEBUG] vouchers fetched: {len(rows)}")
    except Exception as e:
        print(f"[DEBUG] DB error: {e}")
        rows = []
    conn.close()
    vouchers = []
    for r in rows:
        vouchers.append({
            "id": r[0],
            "voucher_no": r[1],
            "voucher_date": r[2],
            "supplier_code": r[3],
            "created_at": r[4]
        })
    print(f"[DEBUG] vouchers list: {vouchers}")
    print("[DEBUG] Attempting to render template index.html")
    try:
        result = render_template("index.html", vouchers=vouchers)
    except Exception as e:
        print(f"[DEBUG] Template rendering error: {e}")
        return f"Template rendering error: {e}", 500
    print("[DEBUG] Template rendered successfully")
    print("[DEBUG] HTML output:\n" + result[:500])  # print first 500 chars for brevity
    return result


@app.route("/upload", methods=["POST"])
def upload_file():
    """Handle file upload -> OCR -> parse -> persist."""
    if "file" not in request.files:
        return "No file part", 400
    file = request.files["file"]
    if file.filename == "":
        return "No selected file", 400

    # Check for duplicate file in DB
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM vouchers_master WHERE file_name=?", (file.filename,))
    if cur.fetchone():
        # Get current vouchers list for error display
        cur.execute("SELECT id, voucher_no, voucher_date, supplier_code, created_at FROM vouchers_master ORDER BY created_at DESC")
        rows = cur.fetchall()
        vouchers = []
        for r in rows:
            vouchers.append({
                "id": r[0],
                "voucher_no": r[1],
                "voucher_date": r[2],
                "supplier_code": r[3],
                "created_at": r[4]
            })
        conn.close()
        return render_template("index.html", vouchers=vouchers, error="File already uploaded. Please choose a new file.")
    conn.close()
    # Save file
    save_path = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
    file.save(save_path)
    # Only save file, do not persist data yet
    return redirect(url_for("validate", filename=file.filename))


@app.route("/voucher/<int:vid>", methods=["GET"])
def get_voucher(vid):
    """Return full voucher record as JSON (for AJAX or debugging)."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, file_name, voucher_no, voucher_date, supplier_code, raw_ocr, parsed_json, created_at FROM vouchers_master WHERE id = ?", (vid,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return jsonify({"error": "not found"}), 404
    parsed_json = row[6]
    try:
        parsed = json.loads(parsed_json) if parsed_json else {}
    except Exception:
        parsed = {"raw": parsed_json}
    return jsonify({
        "id": row[0],
        "file_name": row[1],
        "voucher_no": row[2],
        "voucher_date": row[3],
        "supplier_code": row[4],
        "raw_ocr": row[5],
        "parsed": parsed,
        "created_at": row[7]
    })




# Serve uploaded files
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


# New route for validation page (GET: show, POST: rerun OCR or save)
@app.route("/validate/<filename>", methods=["GET", "POST"])
def validate(filename):
    image_url = url_for('uploaded_file', filename=filename)
    file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    mode = request.form.get('mode') or request.args.get('mode') or 'default'
    ocr_model = 'tesseract'  # Only use Tesseract now
    crop_x = request.form.get('crop_x', type=int)
    crop_y = request.form.get('crop_y', type=int)
    crop_w = request.form.get('crop_w', type=int)
    crop_h = request.form.get('crop_h', type=int)
    cropped_path = None
    ocr_boxes = []
    if all(v is not None for v in [crop_x, crop_y, crop_w, crop_h]) and crop_w > 0 and crop_h > 0:
        # Crop image and save temporary file
        img = Image.open(file_path)
        crop_box = (crop_x, crop_y, crop_x + crop_w, crop_y + crop_h)
        cropped_img = img.crop(crop_box)
        cropped_path = file_path + ".crop.png"
        cropped_img.save(cropped_path)
        ocr_text = extract_text_adv(cropped_path, mode)
        # Get bounding boxes for words
        import pytesseract
        img_for_boxes = cropped_img
        boxes_data = pytesseract.image_to_data(img_for_boxes, lang='eng', output_type=pytesseract.Output.DICT)
        # Word-level boxes (include all with conf >= 0)
        for i in range(len(boxes_data['text'])):
            if boxes_data['text'][i].strip():
                ocr_boxes.append({
                    'left': boxes_data['left'][i],
                    'top': boxes_data['top'][i],
                    'width': boxes_data['width'][i],
                    'height': boxes_data['height'][i],
                    'text': boxes_data['text'][i]
                })
        # Line-level boxes for broader highlight
        line_boxes = []
        n = len(boxes_data['level'])
        for i in range(n):
            if boxes_data['level'][i] == 5 and boxes_data['text'][i].strip():  # level 5 = line
                line_boxes.append({
                    'left': boxes_data['left'][i],
                    'top': boxes_data['top'][i],
                    'width': boxes_data['width'][i],
                    'height': boxes_data['height'][i],
                    'text': boxes_data['text'][i]
                })
        ocr_boxes += line_boxes
        # Store crop data for ML
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("UPDATE vouchers_master SET crop_data=? WHERE file_name=?", (json.dumps({'x':crop_x,'y':crop_y,'w':crop_w,'h':crop_h}), filename))
        conn.commit()
        conn.close()
    else:
        ocr_text = extract_text_adv(file_path, mode)
        # Get bounding boxes for words
        import pytesseract
        img_for_boxes = Image.open(file_path)
        boxes_data = pytesseract.image_to_data(img_for_boxes, lang='eng', output_type=pytesseract.Output.DICT)
        # Word-level boxes (include all with text)
        for i in range(len(boxes_data['text'])):
            if boxes_data['text'][i].strip():
                ocr_boxes.append({
                    'left': boxes_data['left'][i],
                    'top': boxes_data['top'][i],
                    'width': boxes_data['width'][i],
                    'height': boxes_data['height'][i],
                    'text': boxes_data['text'][i],
                    'level': boxes_data['level'][i]
                })
        # Line-level boxes for broader highlight
        n = len(boxes_data['level'])
        for i in range(n):
            if boxes_data['level'][i] == 5 and boxes_data['text'][i].strip():  # level 5 = line
                ocr_boxes.append({
                    'left': boxes_data['left'][i],
                    'top': boxes_data['top'][i],
                    'width': boxes_data['width'][i],
                    'height': boxes_data['height'][i],
                    'text': boxes_data['text'][i],
                    'level': 5
                })
        # Block-level boxes for maximum coverage
        for i in range(n):
            if boxes_data['level'][i] == 2:  # level 2 = block
                ocr_boxes.append({
                    'left': boxes_data['left'][i],
                    'top': boxes_data['top'][i],
                    'width': boxes_data['width'][i],
                    'height': boxes_data['height'][i],
                    'text': '',
                    'level': 2
                })
    rerun_url = url_for('validate', filename=filename)
    save_url = url_for('save_validated', filename=filename)
    # Only save to DB if /save_validated/<filename> is called
    return render_template("validate.html", image_url=image_url, ocr_text=ocr_text, rerun_url=rerun_url, save_url=save_url, selected_mode=mode, ocr_boxes=ocr_boxes)

# Separate route for saving validated text (for form action)
@app.route("/save_validated/<filename>", methods=["POST"])
def save_validated(filename):
    validated_text = request.form['ocr_text']
    parsed = parse_receipt_text(validated_text)
    conn = get_connection()
    cur = conn.cursor()
    # Check if record exists
    cur.execute("SELECT id FROM vouchers_master WHERE file_name=?", (filename,))
    row = cur.fetchone()
    if row:
        conn.close()
        # Show error on validation page
        return render_template("validate.html", image_url=url_for('uploaded_file', filename=filename), ocr_text=validated_text, rerun_url=url_for('validate', filename=filename), save_url=url_for('save_validated', filename=filename), selected_mode=request.form.get('mode', 'default'), error="This file has already been saved. Please upload a new file.")
    else:
        cur.execute(
            """INSERT INTO vouchers_master (file_name, raw_ocr, parsed_json) VALUES (?, ?, ?)""",
            (filename, validated_text, json.dumps(parsed, ensure_ascii=False))
        )
        conn.commit()
        conn.close()
        return redirect(url_for('index'))


@app.route("/confirm_delete_all", methods=["GET"])
def confirm_delete_all():
    return render_template("confirm_delete_all.html")

@app.route("/delete_all", methods=["POST"])
def delete_all():
    # Delete all records from DB
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM vouchers_master")
    conn.commit()
    conn.close()
    # Delete all files in uploads folder
    for fname in os.listdir(app.config["UPLOAD_FOLDER"]):
        fpath = os.path.join(app.config["UPLOAD_FOLDER"], fname)
        # Remove both image and crop files
        if os.path.isfile(fpath):
            os.remove(fpath)
        crop_path = fpath + ".crop.png"
        if os.path.isfile(crop_path):
            os.remove(crop_path)
    return redirect(url_for("index"))

if __name__ == "__main__":
    # run package-style with: python -m backend.app
    app.run(host="127.0.0.1", port=5000, debug=True)
