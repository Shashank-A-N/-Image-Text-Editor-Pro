from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
import os
import shutil
import base64
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
import pytesseract
from io import BytesIO
from werkzeug.utils import secure_filename
import traceback
import subprocess
import sys

app = Flask(__name__)
CORS(app)

# Configure folders
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# ==================== TESSERACT CONFIGURATION ====================

def setup_tesseract():
    """
    Configure Tesseract OCR for different environments
    Priority: ENV variable > Auto-detect > Common paths
    """
    
    # Method 1: Environment variable (highest priority)
    env_path = os.environ.get('TESSERACT_PATH')
    if env_path and os.path.exists(env_path):
        pytesseract.pytesseract.tesseract_cmd = env_path
        print(f"✅ Tesseract from ENV: {env_path}")
        return True
    
    # Method 2: Auto-detect using which/shutil (works in Docker/Linux)
    detected = shutil.which('tesseract')
    if detected:
        pytesseract.pytesseract.tesseract_cmd = detected
        print(f"✅ Tesseract auto-detected: {detected}")
        return True
    
    # Method 3: Common Linux paths (for Docker/production)
    linux_paths = [
        '/usr/bin/tesseract',
        '/usr/local/bin/tesseract',
        '/app/.apt/usr/bin/tesseract',
    ]
    
    for path in linux_paths:
        if os.path.exists(path):
            pytesseract.pytesseract.tesseract_cmd = path
            print(f"✅ Tesseract found: {path}")
            return True
    
    # Method 4: Windows paths (for local development)
    windows_paths = [
        r'C:\Program Files\Tesseract-OCR\tesseract.exe',
        r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
    ]
    
    for path in windows_paths:
        if os.path.exists(path):
            pytesseract.pytesseract.tesseract_cmd = path
            print(f"✅ Tesseract found: {path}")
            return True
    
    print("❌ Tesseract not found in any expected location!")
    return False

# Initialize Tesseract
tesseract_available = setup_tesseract()

# ==================== HELPER FUNCTIONS ====================

def hex_to_rgb(hex_color):
    """Convert hex color to RGB tuple"""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def get_font(font_family, font_size, bold=False, italic=False):
    """
    Load font with fallbacks for both Linux (Docker) and Windows
    """
    
    # Linux font paths (for Docker/production)
    linux_fonts = {
        'Arial': [
            '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',
            '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf' if bold else None,
            '/usr/share/fonts/truetype/liberation/LiberationSans-Italic.ttf' if italic else None,
        ],
        'Times New Roman': [
            '/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf',
            '/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf' if bold else None,
        ],
        'Courier New': [
            '/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf',
            '/usr/share/fonts/truetype/liberation/LiberationMono-Bold.ttf' if bold else None,
        ],
    }
    
    # Windows font paths (for local development)
    windows_fonts = {
        'Arial': [
            'C:/Windows/Fonts/arial.ttf',
            'C:/Windows/Fonts/arialbd.ttf' if bold else None,
            'C:/Windows/Fonts/ariali.ttf' if italic else None,
        ],
        'Times New Roman': [
            'C:/Windows/Fonts/times.ttf',
            'C:/Windows/Fonts/timesbd.ttf' if bold else None,
            'C:/Windows/Fonts/timesi.ttf' if italic else None,
        ],
        'Courier New': [
            'C:/Windows/Fonts/cour.ttf',
            'C:/Windows/Fonts/courbd.ttf' if bold else None,
        ],
        'Comic Sans MS': ['C:/Windows/Fonts/comic.ttf'],
        'Verdana': ['C:/Windows/Fonts/verdana.ttf'],
        'Georgia': ['C:/Windows/Fonts/georgia.ttf'],
    }
    
    # Try Linux fonts first (Docker environment)
    font_paths = linux_fonts.get(font_family, linux_fonts.get('Arial', []))
    for path in font_paths:
        if path and os.path.exists(path):
            try:
                return ImageFont.truetype(path, font_size)
            except:
                continue
    
    # Try Windows fonts (local development)
    font_paths = windows_fonts.get(font_family, windows_fonts.get('Arial', []))
    for path in font_paths:
        if path and os.path.exists(path):
            try:
                return ImageFont.truetype(path, font_size)
            except:
                continue
    
    # Final fallback to default font
    print(f"⚠️  Could not load {font_family}, using default font")
    return ImageFont.load_default()

# ==================== ROUTES ====================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint to verify server is running"""
    try:
        version = pytesseract.get_tesseract_version()
        tesseract_ok = True
    except Exception as e:
        tesseract_ok = False
        version = f"Error: {str(e)}"
    
    return jsonify({
        'status': 'ok',
        'tesseract': tesseract_ok,
        'version': str(version),
        'tesseract_path': pytesseract.pytesseract.tesseract_cmd
    })

@app.route('/debug', methods=['GET'])
def debug_info():
    """Debug endpoint to check system configuration"""
    debug_data = {
        'python_version': sys.version,
        'tesseract_cmd': pytesseract.pytesseract.tesseract_cmd,
        'tesseract_configured': tesseract_available,
        'cwd': os.getcwd(),
        'upload_folder': os.path.abspath(UPLOAD_FOLDER),
    }
    
    # Try to find tesseract
    try:
        result = subprocess.run(['which', 'tesseract'], capture_output=True, text=True, timeout=5)
        debug_data['which_tesseract'] = result.stdout.strip()
    except:
        debug_data['which_tesseract'] = 'Command not available'
    
    # Try to run tesseract version
    try:
        version = pytesseract.get_tesseract_version()
        debug_data['tesseract_version'] = str(version)
    except Exception as e:
        debug_data['tesseract_version'] = f"Error: {str(e)}"
    
    # Check common paths
    common_paths = [
        '/usr/bin/tesseract',
        '/usr/local/bin/tesseract',
        r'C:\Program Files\Tesseract-OCR\tesseract.exe',
    ]
    
    debug_data['path_checks'] = {
        path: os.path.exists(path) for path in common_paths
    }
    
    # Check environment variables
    debug_data['env_vars'] = {
        'PORT': os.environ.get('PORT'),
        'RENDER': os.environ.get('RENDER'),
        'TESSERACT_PATH': os.environ.get('TESSERACT_PATH'),
    }
    
    return jsonify(debug_data)

@app.route('/extract_text', methods=['POST'])
def extract_text():
    print("\n" + "="*60)
    print("📸 EXTRACT TEXT REQUEST")
    print("="*60)
    
    try:
        # Check Tesseract availability
        if not tesseract_available:
            return jsonify({
                'error': 'Tesseract OCR is not configured properly',
                'help': 'Please check /debug endpoint for details'
            }), 500
        
        # Validate request
        if 'image' not in request.files:
            return jsonify({'error': 'No image uploaded'}), 400
        
        file = request.files['image']
        if not file.filename:
            return jsonify({'error': 'No file selected'}), 400
        
        # Save file
        filename = secure_filename(file.filename)
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(image_path)
        print(f"📁 File saved: {filename}")
        
        # Process image
        image = Image.open(image_path)
        if image.mode not in ('RGB', 'L'):
            image = image.convert('RGB')
        
        # Enhance for better OCR
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
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@app.route('/update_image', methods=['POST'])
def update_image():
    print("\n" + "="*60)
    print("✏️  UPDATE IMAGE REQUEST")
    print("="*60)
    
    try:
        data = request.json
        image_path = data.get('image_path')
        text_blocks = data.get('text_blocks')
        
        # Validate input
        if not image_path or not text_blocks:
            return jsonify({'error': 'Missing required data'}), 400
        
        if not os.path.exists(image_path):
            return jsonify({'error': 'Original image not found'}), 404
        
        # Open image
        image = Image.open(image_path)
        if image.mode != 'RGBA':
            image = image.convert('RGBA')
        
        # Create transparent overlay
        overlay = Image.new('RGBA', image.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(overlay)
        
        print(f"✏️  Processing {len(text_blocks)} text blocks...")
        
        # Process each text block
        for idx, block in enumerate(text_blocks):
            try:
                x = int(block['x'])
                y = int(block['y'])
                w = int(block['width'])
                h = int(block['height'])
                text = str(block['text'])
                
                # Get styling
                font_size = int(block.get('fontSize', 20))
                font_family = block.get('fontFamily', 'Arial')
                bold = block.get('bold', False)
                italic = block.get('italic', False)
                underline = block.get('underline', False)
                text_color = block.get('textColor', '#000000')
                bg_color = block.get('backgroundColor', '#FFFFFF')
                bg_transparent = block.get('backgroundTransparent', True)
                
                # Load font
                font = get_font(font_family, font_size, bold, italic)
                
                # Draw background
                if not bg_transparent:
                    bg_rgb = hex_to_rgb(bg_color)
                    draw.rectangle(
                        [x-2, y-2, x+w+2, y+h+2],
                        fill=bg_rgb + (255,)
                    )
                else:
                    # Semi-transparent white to cover original
                    draw.rectangle(
                        [x-2, y-2, x+w+2, y+h+2],
                        fill=(255, 255, 255, 200)
                    )
                
                # Draw text
                text_rgb = hex_to_rgb(text_color)
                draw.text((x, y), text, fill=text_rgb + (255,), font=font)
                
                # Draw underline
                if underline:
                    try:
                        text_bbox = draw.textbbox((x, y), text, font=font)
                        underline_y = text_bbox[3] + 1
                        draw.line(
                            [(x, underline_y), (text_bbox[2], underline_y)],
                            fill=text_rgb + (255,),
                            width=2
                        )
                    except:
                        pass  # textbbox might not be available in older Pillow
                
                print(f"   ✓ Block {idx+1}: '{text[:30]}...'")
                
            except Exception as block_err:
                print(f"   ✗ Block {idx+1} error: {str(block_err)}")
        
        # Composite and convert
        image = Image.alpha_composite(image, overlay)
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
        return jsonify({
            'success': True,
            'edited_image': f"data:image/png;base64,{img_base64}",
            'filename': output_filename
        })
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        traceback.print_exc()
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

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

# ==================== MAIN ====================

if __name__ == '__main__':
    # Get port from environment (for Docker/Render)
    port = int(os.environ.get('PORT', 5000))
    
    # Determine if running in production
    is_production = os.environ.get('RENDER') or os.environ.get('PORT')
    
    print("\n" + "="*60)
    print("🚀 Image Text Editor Server")
    print("="*60)
    print(f"\nEnvironment: {'Production (Docker)' if is_production else 'Development'}")
    
    # Display Tesseract status
    try:
        version = pytesseract.get_tesseract_version()
        print(f"\n✅ Tesseract OCR v{version}")
        print(f"📍 Location: {pytesseract.pytesseract.tesseract_cmd}")
    except Exception as e:
        print(f"\n❌ Tesseract Error: {str(e)}")
        print("Check /debug endpoint for details")
    
    print(f"\n📁 Upload folder: {os.path.abspath(UPLOAD_FOLDER)}")
    print(f"🌐 Server: http://{'0.0.0.0' if is_production else '127.0.0.1'}:{port}")
    print(f"🔍 Debug endpoint: /debug")
    print(f"❤️  Health check: /health")
    print("="*60 + "\n")
    
    # Run app
    app.run(
        debug=not is_production,
        host='0.0.0.0' if is_production else '127.0.0.1',
        port=port
    )
