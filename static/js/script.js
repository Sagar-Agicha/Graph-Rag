let selectedFiles = new Map();

function handleFileSelect() {
    const fileInput = document.getElementById('pdf-file');
    const files = fileInput.files;
    
    if (files.length === 0) {
        alert('Please select files first');
        return;
    }

    const previewContainer = document.getElementById('preview-container');
    if (!previewContainer.querySelector('h3')) {
        previewContainer.innerHTML = '<h3>Selected Files:</h3>';
    }
    
    let fileList = previewContainer.querySelector('.selected-files-list');
    if (!fileList) {
        fileList = document.createElement('div');
        fileList.className = 'selected-files-list';
        previewContainer.appendChild(fileList);
    }

    Array.from(files).forEach(file => {
        if (!selectedFiles.has(file.name)) {
            selectedFiles.set(file.name, file);
            const fileItem = document.createElement('div');
            fileItem.className = 'selected-file-item';
            fileItem.innerHTML = `
                <span class="file-name">${file.name}</span>
                <span class="file-size">(${formatFileSize(file.size)})</span>
                <button class="delete-btn" onclick="removeFile('${file.name}')">Delete</button>
            `;
            fileList.appendChild(fileItem);
        }
    });

    let buttonContainer = previewContainer.querySelector('.button-container');
    if (!buttonContainer) {
        buttonContainer = document.createElement('div');
        buttonContainer.className = 'button-container';
        previewContainer.appendChild(buttonContainer);
    }
    
    buttonContainer.innerHTML = `
        <button class="upload-all-btn" onclick="uploadFiles()">Upload ${selectedFiles.size} Files</button>
    `;

    fileInput.value = '';
}

function removeFile(filename) {
    selectedFiles.delete(filename);
    const fileList = document.querySelector('.selected-files-list');
    const fileItems = fileList.querySelectorAll('.selected-file-item');
    
    fileItems.forEach(item => {
        if (item.querySelector('.file-name').textContent === filename) {
            item.remove();
        }
    });

    const uploadBtn = document.querySelector('.upload-all-btn');
    if (uploadBtn) {
        uploadBtn.innerHTML = `Upload ${selectedFiles.size} Files`;
    }
}

function uploadFiles() {
    if (selectedFiles.size === 0) {
        alert('Please select files first');
        return;
    }

    const uploadBtn = document.querySelector('.upload-all-btn');
    uploadBtn.innerHTML = 'Uploading...';
    uploadBtn.disabled = true;

    const formData = new FormData();
    selectedFiles.forEach((file) => {
        formData.append('files', file);
    });

    fetch('/upload', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            alert('Upload failed: ' + data.error);
        } else {
            console.log('Upload successful');
            selectedFiles.clear();
            document.querySelector('.selected-files-list').innerHTML = '';
            displayUploadedFiles();
            
            const buttonContainer = document.querySelector('.button-container');
            if (buttonContainer) {
                buttonContainer.remove();
            }
        }
    })
    .catch(error => {
        console.error('Upload error:', error);
        alert('Upload failed');
        uploadBtn.innerHTML = 'Upload Failed';
        uploadBtn.disabled = false;
    });
}

function displayUploadedFiles() {
    fetch('/files')
        .then(response => {
            if (response.status === 401) {
                throw new Error('Not logged in');
            }
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            const uploadedContainer = document.getElementById('uploaded-files');
            if (!uploadedContainer) {
                console.error('Container not found: #uploaded-files');
                return;
            }

            // Clear existing content
            uploadedContainer.innerHTML = '<h3>Your Uploaded Files:</h3>';

            // Create file list container
            const fileList = document.createElement('div');
            fileList.id = 'file-list';
            
            if (data.files && data.files.length > 0) {
                data.files.forEach(file => {
                    const fileItem = document.createElement('div');
                    fileItem.className = 'file-stack-item';
                    fileItem.innerHTML = `
                        <div class="file-info">
                            <span class="file-name">${file.name}</span>
                            <span class="file-size">${formatFileSize(file.size)}</span>
                        </div>
                        <button class="delete-btn" onclick="deleteUploadedFile('${file.name}')">Delete</button>
                    `;
                    fileList.appendChild(fileItem);
                });

                uploadedContainer.appendChild(fileList);

                if (data.files.length > 0) {
                    // Add process button if there are files
                    const processButton = document.createElement('button');
                    processButton.className = 'process-btn';
                    processButton.innerHTML = 'Start Processing';
                    processButton.onclick = startProcessing;
                    uploadedContainer.appendChild(processButton);
                }
            } else {
                fileList.innerHTML = '<p>No files uploaded yet</p>';
                uploadedContainer.appendChild(fileList);
            }

            // Show queue position if available
            if (data.queue_position !== undefined) {
                const queueInfo = document.createElement('div');
                queueInfo.className = 'queue-info';
                if (data.queue_position === 0) {
                    queueInfo.textContent = 'Processing your files...';
                } else if (data.queue_position > 0) {
                    queueInfo.textContent = `Queue position: ${data.queue_position}`;
                }
                uploadedContainer.appendChild(queueInfo);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            if (error.message === 'Not logged in') {
                window.location.href = '/';
            }
        });
}

function deleteUploadedFile(filename) {
    fetch('/delete', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ filename: filename })
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            alert('Error deleting file: ' + data.error);
        } else {
            displayUploadedFiles(); // Refresh the list
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Error deleting file');
    });
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function startProcessing() {
    // Show processing started popup immediately
    showCustomPopup('Processing Started', 
        'Processing has begun!<br>' +
        'We will notify you once completed.<br>' +
        'You can upload more documents if you like.<br>' +
        'Check the Status tab for updates.'
    );

    // Make the API call
    fetch('/process', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            showCustomPopup('Error', 'Processing failed: ' + data.error);
        }
    })
    .catch(error => {
        console.error('Processing error:', error);
        showCustomPopup('Error', 'Processing failed');
    });
}

function showCustomPopup(title, message) {
    // Remove any existing popups
    const existingPopup = document.querySelector('.custom-popup');
    if (existingPopup) {
        existingPopup.remove();
    }

    // Create and add the new popup
    const popup = document.createElement('div');
    popup.className = 'custom-popup';
    popup.innerHTML = `
        <h3>${title}</h3>
        <p>${message}</p>
        <button onclick="this.parentElement.remove()">OK</button>
    `;
    document.body.appendChild(popup);

    // Automatically remove the popup after 5 seconds
    setTimeout(() => {
        if (popup.parentElement) {
            popup.remove();
        }
    }, 5000);
}

const style = document.createElement('style');
style.textContent += `
    #file-list {
        border: 1px solid #ddd;
        border-radius: 4px;
        margin-bottom: 20px;
        max-height: 300px;
        overflow-y: auto;
    }

    .process-btn {
        margin-top: 10px;
        padding: 10px 20px;
        background-color: #4CAF50;
        color: white;
        border: none;
        border-radius: 4px;
        cursor: pointer;
        font-size: 16px;
        width: 100%;
    }

    .process-btn:hover {
        background-color: #45a049;
    }

    .process-btn:disabled {
        background-color: #cccccc;
        cursor: not-allowed;
    }

    .custom-popup {
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        background: linear-gradient(145deg, #1f0404, #0f0000);
        padding: 25px;
        border-radius: 12px;
        border: 2px solid #ff2233;
        box-shadow: 0 0 30px rgba(255, 34, 51, 0.3),
                    inset 0 0 15px rgba(255, 0, 0, 0.2);
        z-index: 1000;
        text-align: center;
        min-width: 350px;
        color: #fff1f1;
        animation: popupAppear 0.3s ease-out;
        backdrop-filter: blur(5px);
    }

    @keyframes popupAppear {
        from {
            transform: translate(-50%, -60%);
            opacity: 0;
        }
        to {
            transform: translate(-50%, -50%);
            opacity: 1;
        }
    }

    .custom-popup::before {
        content: '';
        position: absolute;
        top: -1px;
        left: -1px;
        right: -1px;
        bottom: -1px;
        border-radius: 12px;
        background: linear-gradient(45deg, #ff0000, transparent, #ff2233);
        z-index: -1;
        animation: borderGlow 2s linear infinite;
    }

    @keyframes borderGlow {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.5; }
    }

    .custom-popup h3 {
        margin-top: 0;
        color: #ff1a1a;
        margin-bottom: 20px;
        font-family: 'Orbitron', sans-serif;
        text-transform: uppercase;
        letter-spacing: 2px;
        position: relative;
        display: inline-block;
        text-shadow: 0 0 10px rgba(255, 26, 26, 0.5);
    }

    .custom-popup h3::after {
        content: '';
        position: absolute;
        bottom: -8px;
        left: 0;
        width: 100%;
        height: 2px;
        background: linear-gradient(90deg, transparent, #ff1a1a, transparent);
    }

    .custom-popup p {
        margin: 15px 0;
        line-height: 1.6;
        color: #fff1f1;
        font-size: 1.1em;
        position: relative;
        padding: 10px;
        background: rgba(255, 0, 0, 0.1);
        border-radius: 8px;
    }

    .custom-popup button {
        background: linear-gradient(135deg, #f6e447, #e6cf05);
        color: white;
        border: none;
        padding: 12px 30px;
        border-radius: 8px;
        cursor: pointer;
        margin-top: 20px;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 1px;
        position: relative;
        overflow: hidden;
        transition: all 0.3s ease;
        font-family: 'Orbitron', sans-serif;
        box-shadow: 0 0 15px rgba(246, 228, 71, 0.3);
    }

    .custom-popup button::before {
        content: '';
        position: absolute;
        top: -50%;
        left: -50%;
        width: 200%;
        height: 200%;
        background: linear-gradient(
            transparent,
            rgba(255, 255, 255, 0.2),
            transparent
        );
        transform: rotate(45deg);
        transition: 0.5s;
    }

    .custom-popup button:hover::before {
        left: 100%;
    }

    .custom-popup button:hover {
        transform: translateY(-2px);
        box-shadow: 0 0 30px rgba(246, 228, 71, 0.5);
        background: linear-gradient(135deg, #f6e447, #e6cf05);
    }
`;
document.head.appendChild(style);

document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded, calling displayUploadedFiles');
    displayUploadedFiles();
    startFileListUpdater(); // Start the automatic updates
});

// Chat functionality
function sendMessage() {
    const input = document.getElementById('user-input');
    const message = input.value.trim();
    
    if (!message) {
        return;
    }

    // Add user message to chat
    addMessageToChat('user', message);
    
    // Clear input
    input.value = '';

    // Send message to server
    fetch('/chat', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ message: message })
    })
    .then(response => response.json())
    .then(data => {
        // Add bot response to chat
        addMessageToChat('bot', data.response);
    })
    .catch(error => {
        console.error('Error:', error);
        addMessageToChat('bot', 'Sorry, there was an error processing your message.');
    });
}

function addMessageToChat(sender, message) {
    const chatContainer = document.getElementById('chat-container');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}-message`;
    messageDiv.textContent = message;
    chatContainer.appendChild(messageDiv);
    
    // Scroll to bottom of chat
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

// Add event listener for Enter key in chat input
document.addEventListener('DOMContentLoaded', function() {
    const userInput = document.getElementById('user-input');
    if (userInput) {
        userInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                sendMessage();
            }
        });
    }
});

// Add this function to automatically refresh the file list

function startFileListUpdater() {
    // Update every 2 seconds
    setInterval(() => {
        displayUploadedFiles();
    }, 2000);
}

// Start the automatic updates when the page loads
document.addEventListener('DOMContentLoaded', function() {
    displayUploadedFiles();
    startFileListUpdater();
});

// Add this function to show notifications
function showDuplicateNotification(count) {
    const notification = document.createElement('div');
    notification.className = 'duplicate-notification';
    notification.innerHTML = `
        <div class="notification-content">
            <span class="notification-icon">⚠️</span>
            <span class="notification-text">
                ${count} duplicate${count > 1 ? 's' : ''} found! 
                <a href="/duplicates">Check duplicates tab</a>
            </span>
            <button class="notification-close" onclick="this.parentElement.parentElement.remove()">×</button>
        </div>
    `;
    document.body.appendChild(notification);

    // Auto-hide after 10 seconds
    setTimeout(() => {
        if (notification.parentElement) {
            notification.remove();
        }
    }, 10000);
}

function showStatusModal() {
    const modal = document.getElementById('statusModal');
    modal.style.display = 'block';
    updateStatusTable();
}

function closeStatusModal() {
    const modal = document.getElementById('statusModal');
    modal.style.display = 'none';
}

function updateStatusTable() {
    fetch('/processing-status')
        .then(response => response.json())
        .then(data => {
            const tableBody = document.getElementById('statusTableBody');
            tableBody.innerHTML = '';

            if (data.status_data && data.status_data.length > 0) {
                data.status_data.forEach(item => {
                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td>${item.filename}</td>
                        <td>
                            <span class="status-badge ${item.status.toLowerCase()}">
                                ${item.status}
                            </span>
                        </td>
                        <td>
                            <button class="view-btn" onclick="window.open('${item.file_link}', '_blank')">
                                View
                            </button>
                        </td>
                    `;
                    tableBody.appendChild(row);
                });
            } else {
                tableBody.innerHTML = `
                    <tr>
                        <td colspan="3" style="text-align: center;">No files processed yet</td>
                    </tr>
                `;
            }
        })
        .catch(error => console.error('Error:', error));
}

// Close modal when clicking outside
window.onclick = function(event) {
    const modal = document.getElementById('statusModal');
    if (event.target === modal) {
        closeStatusModal();
    }
}

// Add event listener for close button
document.addEventListener('DOMContentLoaded', function() {
    const closeBtn = document.querySelector('.close-modal');
    if (closeBtn) {
        closeBtn.onclick = closeStatusModal;
    }
});

// Update the event listener for navigation links
document.addEventListener('DOMContentLoaded', function() {
    // Add status button click handler
    const statusBtn = document.querySelector('.status-btn');
    if (statusBtn) {
        statusBtn.addEventListener('click', function(e) {
            e.preventDefault();
            showStatusModal();
        });
    }

    // Navigation transitions for other links
    document.querySelectorAll('a:not(.status-btn)').forEach(link => {
        link.addEventListener('click', (e) => {
            if (link.hasAttribute('target')) {
                return;
            }
            
            e.preventDefault();
            const transition = document.querySelector('.page-transition');
            const lines = document.querySelectorAll('.transition-line');
            
            transition.classList.add('active');
            lines.forEach(line => line.classList.add('active'));
            
            setTimeout(() => {
                window.location.href = link.href;
            }, 1000);
        });
    });
});