from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
import os
import base64
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter
import pytesseract
from io import BytesIO
from werkzeug.utils import secure_filename
import traceback

app = Flask(__name__)
CORS(app)

# Configure folders
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# Configure Tesseract
TESSERACT_PATHS = [
    r'C:\Program Files\Tesseract-OCR\tesseract.exe',
    r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
]

tesseract_configured = False
for path in TESSERACT_PATHS:
    if os.path.exists(path):
        pytesseract.pytesseract.tesseract_cmd = path
        tesseract_configured = True
        print(f"✅ Tesseract found at: {path}")
        break

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint to verify server is running"""
    try:
        version = pytesseract.get_tesseract_version()
        tesseract_ok = True
    except:
        tesseract_ok = False
        version = "Not found"
    
    return jsonify({
        'status': 'ok',
        'tesseract': tesseract_ok,
        'version': str(version)
    })

@app.route('/extract_text', methods=['POST'])
def extract_text():
    print("\n" + "="*60)
    print("📸 EXTRACT TEXT REQUEST RECEIVED")
    print("="*60)
    
    try:
        if not tesseract_configured:
            return jsonify({
                'error': 'Tesseract OCR not found'
            }), 500
        
        if 'image' not in request.files:
            return jsonify({'error': 'No image uploaded'}), 400
        
        file = request.files['image']
        if not file.filename:
            return jsonify({'error': 'No file selected'}), 400
        
        filename = secure_filename(file.filename)
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(image_path)
        
        print(f"📁 Processing: {filename}")
        
        # Open and process image
        image = Image.open(image_path)
        if image.mode not in ('RGB', 'L'):
            image = image.convert('RGB')
        
        # Enhance and convert to grayscale
        enhancer = ImageEnhance.Contrast(image)
        image_enhanced = enhancer.enhance(1.5)
        image_gray = image_enhanced.convert('L')
        
        # Perform OCR
        print("🔍 Running OCR...")
        custom_config = r'--oem 3 --psm 6'
        data = pytesseract.image_to_data(
            image_gray,
            config=custom_config,
            output_type=pytesseract.Output.DICT
        )
        
        # Extract text blocks
        text_blocks = []
        for i in range(len(data['level'])):
            text = data['text'][i]
            if text and str(text).strip():
                block = {
                    'text': str(text).strip(),
                    'x': int(data['left'][i]),
                    'y': int(data['top'][i]),
                    'width': int(data['width'][i]),
                    'height': int(data['height'][i]),
                    'confidence': float(data['conf'][i]),
                    # Default styling
                    'fontSize': 20,
                    'fontFamily': 'Arial',
                    'bold': False,
                    'italic': False,
                    'underline': False,
                    'textColor': '#000000',
                    'backgroundColor': '#FFFFFF',
                    'backgroundTransparent': True
                }
                text_blocks.append(block)
        
        print(f"✅ Found {len(text_blocks)} text blocks")
        
        # Convert to base64
        buffered = BytesIO()
        Image.open(image_path).save(buffered, format="PNG")
        img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
        
        return jsonify({
            'text_blocks': text_blocks,
            'full_text': ' '.join([b['text'] for b in text_blocks]),
            'image_base64': f"data:image/png;base64,{img_base64}",
            'image_path': image_path
        })
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

def hex_to_rgb(hex_color):
    """Convert hex color to RGB tuple"""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

@app.route('/update_image', methods=['POST'])
def update_image():
    print("\n" + "="*60)
    print("✏️  UPDATE IMAGE REQUEST RECEIVED")
    print("="*60)
    
    try:
        data = request.json
        image_path = data.get('image_path')
        text_blocks = data.get('text_blocks')
        
        if not image_path or not text_blocks:
            return jsonify({'error': 'Missing required data'}), 400
        
        if not os.path.exists(image_path):
            return jsonify({'error': 'Original image not found'}), 404
        
        # Open image with alpha channel support
        image = Image.open(image_path)
        if image.mode != 'RGBA':
            image = image.convert('RGBA')
        
        # Create a transparent overlay for drawing
        overlay = Image.new('RGBA', image.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(overlay)
        
        print(f"✏️  Processing {len(text_blocks)} text blocks...")
        
        for idx, block in enumerate(text_blocks):
            try:
                x = int(block['x'])
                y = int(block['y'])
                w = int(block['width'])
                h = int(block['height'])
                text = str(block['text'])
                
                # Get styling options
                font_size = int(block.get('fontSize', 20))
                font_family = block.get('fontFamily', 'Arial')
                bold = block.get('bold', False)
                italic = block.get('italic', False)
                underline = block.get('underline', False)
                text_color = block.get('textColor', '#000000')
                bg_color = block.get('backgroundColor', '#FFFFFF')
                bg_transparent = block.get('backgroundTransparent', True)
                
                # Load font
                font = None
                font_paths = {
                    'Arial': [
                        'C:/Windows/Fonts/arial.ttf',
                        'C:/Windows/Fonts/arialbd.ttf' if bold else 'C:/Windows/Fonts/arial.ttf',
                        'C:/Windows/Fonts/ariali.ttf' if italic else 'C:/Windows/Fonts/arial.ttf'
                    ],
                    'Times New Roman': [
                        'C:/Windows/Fonts/times.ttf',
                        'C:/Windows/Fonts/timesbd.ttf' if bold else 'C:/Windows/Fonts/times.ttf',
                        'C:/Windows/Fonts/timesi.ttf' if italic else 'C:/Windows/Fonts/times.ttf'
                    ],
                    'Courier New': [
                        'C:/Windows/Fonts/cour.ttf',
                        'C:/Windows/Fonts/courbd.ttf' if bold else 'C:/Windows/Fonts/cour.ttf',
                        'C:/Windows/Fonts/couri.ttf' if italic else 'C:/Windows/Fonts/cour.ttf'
                    ],
                    'Comic Sans MS': ['C:/Windows/Fonts/comic.ttf'],
                    'Verdana': ['C:/Windows/Fonts/verdana.ttf'],
                    'Georgia': ['C:/Windows/Fonts/georgia.ttf'],
                }
                
                # Try to load appropriate font
                font_list = font_paths.get(font_family, font_paths['Arial'])
                for font_path in font_list:
                    try:
                        font = ImageFont.truetype(font_path, font_size)
                        break
                    except:
                        continue
                
                if not font:
                    font = ImageFont.load_default()
                
                # Draw background if not transparent
                if not bg_transparent:
                    bg_rgb = hex_to_rgb(bg_color)
                    draw.rectangle(
                        [x-2, y-2, x+w+2, y+h+2],
                        fill=bg_rgb + (255,)  # Opaque background
                    )
                else:
                    # Draw semi-transparent white to cover original text
                    draw.rectangle(
                        [x-2, y-2, x+w+2, y+h+2],
                        fill=(255, 255, 255, 200)  # Semi-transparent white
                    )
                
                # Draw text
                text_rgb = hex_to_rgb(text_color)
                draw.text((x, y), text, fill=text_rgb + (255,), font=font)
                
                # Draw underline if needed
                if underline:
                    text_bbox = draw.textbbox((x, y), text, font=font)
                    underline_y = text_bbox[3] + 1
                    draw.line(
                        [(x, underline_y), (text_bbox[2], underline_y)],
                        fill=text_rgb + (255,),
                        width=2
                    )
                
                print(f"   ✓ Block {idx+1}: '{text[:30]}...' (Font: {font_family}, Size: {font_size})")
                
            except Exception as block_err:
                print(f"   ✗ Block {idx+1} error: {str(block_err)}")
                traceback.print_exc()
        
        # Composite the overlay onto the original image
        image = Image.alpha_composite(image, overlay)
        
        # Convert back to RGB for saving
        image = image.convert('RGB')
        
        # Save
        output_filename = 'edited_' + secure_filename(os.path.basename(image_path))
        output_path = os.path.join(app.config['UPLOAD_FOLDER'], output_filename)
        image.save(output_path, quality=95)
        
        print(f"💾 Saved: {output_filename}")
        
        # Convert to base64
        buffered = BytesIO()
        image.save(buffered, format="PNG")
        img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
        
        print("✅ SUCCESS")
        print("="*60 + "\n")
        
        return jsonify({
            'success': True,
            'edited_image': f"data:image/png;base64,{img_base64}",
            'filename': output_filename
        })
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/download/<path:filename>', methods=['GET'])
def download_file(filename):
    try:
        filename = secure_filename(filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=True, download_name=filename)
        return jsonify({'error': 'File not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🚀 Image Text Editor Server")
    print("="*60)
    
    try:
        version = pytesseract.get_tesseract_version()
        print(f"\n✅ Tesseract OCR v{version} is ready!")
    except:
        print("\n❌ Tesseract OCR not found!")
    
    print(f"\n📁 Upload folder: {os.path.abspath(UPLOAD_FOLDER)}")
    print(f"🌐 Server: http://localhost:5000")
    print("="*60 + "\n")
    
    app.run(debug=True, port=5000, host='127.0.0.1')