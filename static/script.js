// Global Variables
let uploadedImagePath = '';
let originalImageBase64 = '';
let extractedTextBlocks = [];
let editedImagePath = '';
let serverConnected = false;

// DOM Elements
const uploadBox = document.getElementById('uploadBox');
const imageInput = document.getElementById('imageInput');
const uploadPlaceholder = document.getElementById('uploadPlaceholder');
const previewContainer = document.getElementById('previewContainer');
const previewImage = document.getElementById('previewImage');
const changeImageBtn = document.getElementById('changeImageBtn');
const extractBtn = document.getElementById('extractBtn');
const editorSection = document.getElementById('editorSection');
const textBlocksContainer = document.getElementById('textBlocks');
const blockCount = document.getElementById('blockCount');
const applyChangesBtn = document.getElementById('applyChangesBtn');
const resetBtn = document.getElementById('resetBtn');
const resultSection = document.getElementById('resultSection');
const resultImage = document.getElementById('resultImage');
const originalImage = document.getElementById('originalImage');
const downloadBtn = document.getElementById('downloadBtn');
const newImageBtn = document.getElementById('newImageBtn');
const loader = document.getElementById('loader');
const tesseractStatus = document.getElementById('tesseractStatus');

// Initialize and check server connection
window.addEventListener('load', async () => {
    console.log('%c📷 Image Text Editor', 'font-size: 24px; color: #667eea; font-weight: bold;');
    console.log('Checking server connection...');
    
    await checkServerConnection();
});

async function checkServerConnection() {
    try {
        console.log('Attempting to connect to server...');
        
        const response = await fetch('/health', {
            method: 'GET',
            headers: {
                'Accept': 'application/json'
            }
        });
        
        console.log('Response status:', response.status);
        
        if (!response.ok) {
            throw new Error(`Server returned ${response.status}`);
        }
        
        const data = await response.json();
        console.log('Server response:', data);
        
        serverConnected = true;
        
        if (data.tesseract) {
            tesseractStatus.classList.add('ready');
            tesseractStatus.innerHTML = `<span class="status-dot"></span>OCR Ready (v${data.version})`;
            console.log('✅ Tesseract OCR is ready');
        } else {
            tesseractStatus.innerHTML = `<span class="status-dot"></span>OCR Not Installed`;
            tesseractStatus.style.color = 'var(--error)';
            showToast('Tesseract OCR not installed. Please install it to use this app.', 'error', 8000);
            console.warn('⚠️ Tesseract OCR not found');
        }
        
    } catch (error) {
        console.error('❌ Server connection failed:', error);
        serverConnected = false;
        tesseractStatus.innerHTML = `<span class="status-dot"></span>Server Error`;
        tesseractStatus.style.color = 'var(--error)';
        showToast('Cannot connect to server. Please make sure the Flask server is running.', 'error', 10000);
    }
}

// Upload functionality
uploadBox.addEventListener('click', () => {
    imageInput.click();
});

changeImageBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    imageInput.click();
});

uploadBox.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadBox.classList.add('dragover');
});

uploadBox.addEventListener('dragleave', () => {
    uploadBox.classList.remove('dragover');
});

uploadBox.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadBox.classList.remove('dragover');
    
    const files = e.dataTransfer.files;
    if (files.length > 0 && files[0].type.startsWith('image/')) {
        handleImageUpload(files[0]);
    } else {
        showToast('Please upload a valid image file', 'error');
    }
});

imageInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
        handleImageUpload(e.target.files[0]);
    }
});

function handleImageUpload(file) {
    if (file.size > 16 * 1024 * 1024) {
        showToast('File size should not exceed 16MB', 'error');
        return;
    }

    console.log('Uploading file:', file.name, 'Size:', file.size, 'bytes');

    const reader = new FileReader();
    
    reader.onload = (e) => {
        previewImage.src = e.target.result;
        uploadPlaceholder.style.display = 'none';
        previewContainer.style.display = 'block';
        extractBtn.disabled = false;
        
        editorSection.style.display = 'none';
        resultSection.style.display = 'none';
        
        console.log('✅ Image loaded successfully');
    };
    
    reader.onerror = (e) => {
        console.error('❌ FileReader error:', e);
        showToast('Failed to load image', 'error');
    };
    
    reader.readAsDataURL(file);
}

// Extract text
extractBtn.addEventListener('click', async () => {
    console.log('\n🔍 EXTRACT TEXT BUTTON CLICKED');
    
    if (!serverConnected) {
        showToast('Server not connected. Please refresh the page.', 'error');
        return;
    }
    
    const file = imageInput.files[0];
    if (!file) {
        showToast('Please select an image first', 'error');
        return;
    }
    
    console.log('File to extract:', file.name);
    
    const formData = new FormData();
    formData.append('image', file);
    
    console.log('FormData created, sending request to /extract_text...');
    
    try {
        showLoader(true, 'Extracting text from image...');
        
        const response = await fetch('/extract_text', {
            method: 'POST',
            body: formData
        });
        
        console.log('Response received. Status:', response.status);
        console.log('Response OK:', response.ok);
        console.log('Response headers:', [...response.headers.entries()]);
        
        // Get response text first
        const responseText = await response.text();
        console.log('Response text length:', responseText.length);
        console.log('Response text preview:', responseText.substring(0, 200));
        
        if (!response.ok) {
            let errorMsg = 'Server error';
            try {
                const errorData = JSON.parse(responseText);
                errorMsg = errorData.error || errorMsg;
                console.error('Server error details:', errorData);
            } catch (e) {
                errorMsg = responseText || errorMsg;
                console.error('Could not parse error response:', e);
            }
            throw new Error(errorMsg);
        }
        
        // Parse JSON response
        let data;
        try {
            data = JSON.parse(responseText);
            console.log('✅ JSON parsed successfully');
            console.log('Text blocks found:', data.text_blocks?.length || 0);
        } catch (e) {
            console.error('❌ JSON parse error:', e);
            throw new Error('Invalid response from server');
        }
        
        uploadedImagePath = data.image_path;
        originalImageBase64 = data.image_base64;
        extractedTextBlocks = data.text_blocks || [];
        
        console.log('Stored data:', {
            imagePath: uploadedImagePath,
            blocksCount: extractedTextBlocks.length
        });
        
        if (extractedTextBlocks.length === 0) {
            showToast('No text detected. Try a clearer image.', 'warning', 5000);
            displayTextBlocks([]);
            editorSection.style.display = 'block';
        } else {
            displayTextBlocks(extractedTextBlocks);
            editorSection.style.display = 'block';
            resultSection.style.display = 'none';
            
            setTimeout(() => {
                editorSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }, 100);
            
            showToast(`Found ${extractedTextBlocks.length} text block(s)!`, 'success');
        }
        
        console.log('✅ Extract text completed successfully\n');
        
    } catch (error) {
        console.error('❌ Extract text error:', error);
        console.error('Error stack:', error.stack);
        showToast('Error: ' + error.message, 'error', 6000);
    } finally {
        showLoader(false);
    }
});

function displayTextBlocks(blocks) {
    console.log('Displaying', blocks.length, 'text blocks');
    
    textBlocksContainer.innerHTML = '';
    blockCount.textContent = `${blocks.length} text block(s) found`;
    
    if (blocks.length === 0) {
        textBlocksContainer.innerHTML = `
            <div style="text-align: center; color: var(--gray); padding: 3rem;">
                <p style="font-size: 1.1rem; margin-bottom: 10px;">😕 No text detected</p>
                <p style="font-size: 0.9rem;">Try using a clearer image with better contrast</p>
            </div>
        `;
        return;
    }
    
    blocks.forEach((block, index) => {
        const confidence = Math.round(block.confidence);
        const confidenceColor = confidence > 80 ? 'var(--success)' : confidence > 50 ? 'var(--warning)' : 'var(--error)';
        
        const blockDiv = document.createElement('div');
        blockDiv.className = 'text-block';
        blockDiv.innerHTML = `
            <label>Text Block ${index + 1}</label>
            <input type="text" 
                   id="textBlock${index}" 
                   value="${escapeHtml(block.text)}" 
                   data-index="${index}"
                   placeholder="Enter text...">
            <div class="text-info">
                <span>Position: (${block.x}, ${block.y}) • Size: ${block.width}×${block.height}px</span>
                <span class="confidence" style="color: ${confidenceColor}">
                    ${confidence}%
                </span>
            </div>
        `;
        textBlocksContainer.appendChild(blockDiv);
    });
    
    console.log('✅ Text blocks displayed');
}

// Apply changes
applyChangesBtn.addEventListener('click', async () => {
    console.log('\n✏️ APPLY CHANGES BUTTON CLICKED');
    
    if (!serverConnected) {
        showToast('Server not connected. Please refresh the page.', 'error');
        return;
    }
    
    const updatedBlocks = extractedTextBlocks.map((block, index) => {
        const input = document.getElementById(`textBlock${index}`);
        return {
            ...block,
            text: input ? input.value : block.text
        };
    });
    
    console.log('Updated blocks count:', updatedBlocks.length);
    console.log('Image path:', uploadedImagePath);
    
    try {
        showLoader(true, 'Applying changes...');
        
        const requestBody = {
            image_path: uploadedImagePath,
            text_blocks: updatedBlocks
        };
        
        console.log('Sending request to /update_image...');
        console.log('Request body preview:', JSON.stringify(requestBody).substring(0, 200));
        
        const response = await fetch('/update_image', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestBody)
        });
        
        console.log('Response received. Status:', response.status);
        
        const responseText = await response.text();
        console.log('Response text length:', responseText.length);
        
        if (!response.ok) {
            let errorMsg = 'Update failed';
            try {
                const errorData = JSON.parse(responseText);
                errorMsg = errorData.error || errorMsg;
                console.error('Server error:', errorData);
            } catch (e) {
                errorMsg = responseText || errorMsg;
            }
            throw new Error(errorMsg);
        }
        
        let data;
        try {
            data = JSON.parse(responseText);
            console.log('✅ JSON parsed successfully');
        } catch (e) {
            console.error('❌ JSON parse error:', e);
            throw new Error('Invalid response from server');
        }
        
        if (data.success) {
            resultImage.src = data.edited_image;
            originalImage.src = originalImageBase64;
            editedImagePath = data.filename;
            resultSection.style.display = 'block';
            
            setTimeout(() => {
                resultSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }, 100);
            
            showToast('Image updated successfully!', 'success');
            console.log('✅ Apply changes completed successfully\n');
        }
    } catch (error) {
        console.error('❌ Update image error:', error);
        console.error('Error stack:', error.stack);
        showToast('Error: ' + error.message, 'error', 6000);
    } finally {
        showLoader(false);
    }
});

// Reset
resetBtn.addEventListener('click', () => {
    console.log('Reset button clicked');
    displayTextBlocks(extractedTextBlocks);
    showToast('Reset to original values', 'info');
});

// Download
downloadBtn.addEventListener('click', () => {
    console.log('Download button clicked. Filename:', editedImagePath);
    if (editedImagePath) {
        window.location.href = `/download/${editedImagePath}`;
        showToast('Downloading...', 'success');
    } else {
        showToast('No file to download', 'error');
    }
});

// New Image
newImageBtn.addEventListener('click', () => {
    console.log('New image button clicked - resetting everything');
    imageInput.value = '';
    uploadPlaceholder.style.display = 'block';
    previewContainer.style.display = 'none';
    extractBtn.disabled = false;
    editorSection.style.display = 'none';
    resultSection.style.display = 'none';
    uploadedImagePath = '';
    originalImageBase64 = '';
    extractedTextBlocks = [];
    editedImagePath = '';
    
    window.scrollTo({ top: 0, behavior: 'smooth' });
    showToast('Ready for new image!', 'info');
});

// Comparison tabs
document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        e.target.classList.add('active');
        
        const tab = e.target.dataset.tab;
        console.log('Switching to tab:', tab);
        
        if (tab === 'edited') {
            resultImage.style.display = 'block';
            originalImage.style.display = 'none';
        } else {
            resultImage.style.display = 'none';
            originalImage.style.display = 'block';
        }
    });
});

// Helper functions
function showLoader(show, message = 'Processing...') {
    loader.style.display = show ? 'flex' : 'none';
    const loaderText = loader.querySelector('.loader-text');
    if (loaderText) loaderText.textContent = message;
}

function showToast(message, type = 'info', duration = 3000) {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    
    const icon = {
        success: '✓',
        error: '✕',
        warning: '⚠',
        info: 'ℹ'
    }[type] || 'ℹ';
    
    toast.innerHTML = `<span style="font-size: 1.2rem;">${icon}</span><span>${message}</span>`;
    
    const container = document.getElementById('toastContainer');
    container.appendChild(toast);
    
    setTimeout(() => {
        toast.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => {
            if (container.contains(toast)) {
                container.removeChild(toast);
            }
        }, 300);
    }, duration);
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

console.log('%c✅ JavaScript loaded successfully', 'color: green; font-weight: bold;');