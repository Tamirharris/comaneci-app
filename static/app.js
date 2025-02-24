document.addEventListener('DOMContentLoaded', () => {
    // Get DOM elements
    const dropZone = document.getElementById('drop-zone');
    const fileInput = dropZone.querySelector('input[type="file"]');
    const chooseFilesBtn = dropZone.querySelector('button');
    const preview = document.getElementById('preview');
    const generateBtn = document.getElementById('generateBtn');
    const statusDiv = document.getElementById('status');
    const resultsDiv = document.getElementById('results');
    const videoResults = document.getElementById('videoResults');
    const outputFolderSelect = document.getElementById('outputFolder');
    const newFolderBtn = document.getElementById('newFolderBtn');

    // Store uploaded files
    let uploadedFiles = [];

    // Store active event sources
    const activeEventSources = new Map();

    // Handle drag and drop
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('border-blue-500');
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('border-blue-500');
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('border-blue-500');
        handleFiles(e.dataTransfer.files);
    });

    // Handle file input change
    fileInput.addEventListener('change', (e) => {
        handleFiles(e.target.files);
    });

    // Handle choose files button
    chooseFilesBtn.addEventListener('click', () => {
        fileInput.click();
    });

    // Handle files
    async function handleFiles(files) {
        console.log('Handling files:', files);
        
        const formData = new FormData();
        Array.from(files).forEach(file => {
            formData.append('images[]', file);
        });
        
        try {
            // Upload files to temporary storage and get URLs
            const response = await fetch('/api/upload', {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
                throw new Error('Failed to upload files');
            }
            
            const data = await response.json();
            console.log('Upload response:', data);
            
            // Store file data for later use
            uploadedFiles = data.files.map(file => ({
                name: file.originalName,
                url: file.url
            }));
            
            // Show preview
            preview.innerHTML = uploadedFiles.map(file => `
                <div class="preview-item">
                    <img src="${file.url}" alt="${file.name}" class="w-32 h-32 object-cover rounded">
                    <p class="text-sm mt-1">${file.name}</p>
                </div>
            `).join('');
            
            // Enable generate button
            generateBtn.disabled = false;
            
        } catch (error) {
            console.error('Error:', error);
            statusDiv.textContent = `Error: ${error.message}`;
        }
    }

    async function generateVideos() {
        if (uploadedFiles.length === 0) {
            statusDiv.textContent = 'Please upload some images first.';
            return;
        }

        const prompt = document.getElementById('prompt').value;
        const negative_prompt = document.getElementById('negative_prompt').value;
        const aspectRatio = document.getElementById('aspectRatio').value;
        const duration = parseInt(document.getElementById('duration').value);
        const email = document.getElementById('notification_email').value;

        generateBtn.disabled = true;
        statusDiv.textContent = 'Starting video generation...';

        try {
            const response = await fetch('/api/generate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    images: uploadedFiles,
                    prompt,
                    negative_prompt,
                    aspectRatio,
                    duration,
                    cfg_scale: 0.5,
                    email
                })
            });

            const data = await response.json();
            console.log('Generate response:', data);
            
            if (response.ok) {
                statusDiv.textContent = `Videos queued for processing. Batch ID: ${data.batch_id}`;
                startStatusChecking(data.batch_id);
            } else {
                throw new Error(data.error || 'Failed to start processing');
            }
        } catch (error) {
            console.error('Error:', error);
            statusDiv.textContent = `Error: ${error.message}`;
            generateBtn.disabled = false;
        }
    }

    function startStatusChecking(batchId) {
        // Create a unique event source for this batch
        const eventSource = new EventSource(`/api/status/${batchId}`);
        activeEventSources.set(batchId, eventSource);
        
        eventSource.onmessage = (event) => {
            const data = JSON.parse(event.data);
            console.log('Status update:', data);
            
            if (data.jobs) {
                updateBatchStatus(data.jobs);
            }
            
            // Close connection if all jobs are complete or failed
            if (data.status === 'completed' || data.status === 'failed') {
                eventSource.close();
                activeEventSources.delete(batchId);
                generateBtn.disabled = false;
            }
        };
        
        eventSource.onerror = (error) => {
            console.error('EventSource error:', error);
            eventSource.close();
            activeEventSources.delete(batchId);
            generateBtn.disabled = false;
            statusDiv.textContent = 'Lost connection to server. Please refresh the page.';
        };
    }

    function updateBatchStatus(jobs) {
        // Clear previous results
        videoResults.innerHTML = '';
        
        // Add new results
        jobs.forEach(job => {
            const resultDiv = document.createElement('div');
            resultDiv.className = 'mb-4 p-4 border rounded';
            
            if (job.status === 'completed' && job.data && job.data.video_url) {
                resultDiv.innerHTML = `
                    <h3 class="text-lg font-semibold">${job.filename}</h3>
                    <p class="text-green-600">✅ Complete</p>
                    <video controls class="mt-2 w-full max-w-md">
                        <source src="${job.data.video_url}" type="video/mp4">
                        Your browser does not support the video tag.
                    </video>
                    <a href="${job.data.video_url}" class="mt-2 inline-block text-blue-600 hover:underline" download>Download Video</a>
                `;
            } else if (job.status === 'failed') {
                resultDiv.innerHTML = `
                    <h3 class="text-lg font-semibold">${job.filename}</h3>
                    <p class="text-red-600">❌ Failed: ${job.data?.error || 'Unknown error'}</p>
                `;
            } else {
                resultDiv.innerHTML = `
                    <h3 class="text-lg font-semibold">${job.filename}</h3>
                    <p class="text-blue-600">⏳ Processing...</p>
                `;
            }
            
            videoResults.appendChild(resultDiv);
        });
    }

    // Handle generate button click
    generateBtn.addEventListener('click', generateVideos);

    // Load folders on page load
    async function loadFolders() {
        try {
            const response = await fetch('/api/folders');
            const data = await response.json();

            outputFolderSelect.innerHTML = '<option value="default">Default</option>';
            data.folders.forEach(folder => {
                if (folder !== 'default') {
                    const option = document.createElement('option');
                    option.value = folder;
                    option.textContent = folder;
                    outputFolderSelect.appendChild(option);
                }
            });
        } catch (error) {
            console.error('Error loading folders:', error);
        }
    }

    // Handle new folder button
    newFolderBtn.addEventListener('click', async () => {
        const folderName = prompt('Enter folder name:');
        if (folderName) {
            try {
                const response = await fetch('/api/folders', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ name: folderName })
                });

                if (response.ok) {
                    loadFolders();
                } else {
                    throw new Error('Failed to create folder');
                }
            } catch (error) {
                console.error('Error creating folder:', error);
                alert('Failed to create folder');
            }
        }
    });

    loadFolders();
});
