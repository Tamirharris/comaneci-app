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
            if (file.type.startsWith('image/')) {
                console.log('Adding file to upload:', file.name, file.type, file.size);
                formData.append('files[]', file);
            } else {
                console.log('Skipping non-image file:', file.name, file.type);
            }
        });

        try {
            console.log('Sending upload request...');
            const response = await fetch('/api/upload', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                throw new Error('Upload failed');
            }

            const data = await response.json();
            console.log('Upload response:', data);
            
            // Clear existing previews
            preview.innerHTML = '';
            uploadedFiles = data.files;
            console.log('Updated uploadedFiles:', uploadedFiles);

            // Create previews for uploaded files
            Array.from(files).forEach((file, index) => {
                if (file.type.startsWith('image/')) {
                    const reader = new FileReader();
                    reader.onload = (e) => {
                        console.log('Creating preview for:', file.name);
                        const div = document.createElement('div');
                        div.className = 'relative';
                        div.innerHTML = `
                            <img src="${e.target.result}" class="w-full h-32 object-cover rounded">
                            <button class="absolute top-0 right-0 bg-red-500 text-white p-1 rounded-full m-1" data-file="${uploadedFiles[index]}">×</button>
                        `;
                        preview.appendChild(div);

                        // Handle remove button
                        div.querySelector('button').addEventListener('click', function() {
                            const fileName = this.dataset.file;
                            console.log('Removing file:', fileName);
                            uploadedFiles = uploadedFiles.filter(f => f !== fileName);
                            div.remove();
                            console.log('Updated uploadedFiles after remove:', uploadedFiles);
                        });
                    };
                    reader.readAsDataURL(file);
                }
            });
        } catch (error) {
            console.error('Upload error:', error);
            alert('Failed to upload files');
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
        const statusCheckInterval = 5000; // Check every 5 seconds
        let checkCount = 0;
        const maxChecks = 360; // Maximum 30 minutes of checking

        const checkStatus = async () => {
            try {
                const response = await fetch(`/api/status/${batchId}`);
                const data = await response.json();

                if (response.ok && data.status === 'found') {
                    updateBatchStatus(data.jobs);
                    
                    // Check if all jobs are complete or failed
                    const allDone = Object.values(data.jobs).every(job => 
                        job.status === 'completed' || job.status === 'failed'
                    );

                    if (allDone) {
                        generateBtn.disabled = false;
                        clearInterval(statusInterval);
                    }
                }

                checkCount++;
                if (checkCount >= maxChecks) {
                    clearInterval(statusInterval);
                    statusDiv.textContent = 'Status checking timed out. Your videos will continue processing in the background.';
                    generateBtn.disabled = false;
                }
            } catch (error) {
                console.error('Error checking status:', error);
            }
        };

        const statusInterval = setInterval(checkStatus, statusCheckInterval);
        checkStatus(); // Check immediately
    }

    function updateBatchStatus(jobs) {
        const results = document.getElementById('videoResults');
        
        // Update status message
        const completed = Object.values(jobs).filter(j => j.status === 'completed').length;
        const total = Object.keys(jobs).length;
        statusDiv.textContent = `Processing: ${completed}/${total} videos complete`;

        // Update results
        results.innerHTML = '';
        Object.entries(jobs).forEach(([jobId, job]) => {
            const resultDiv = document.createElement('div');
            resultDiv.className = 'bg-white p-4 rounded-lg shadow';
            
            let content = `
                <h3 class="font-bold">${job.data?.filename || jobId}</h3>
                <p class="text-sm ${job.status === 'failed' ? 'text-red-500' : 'text-gray-600'}">
                    ${job.data?.message || job.status}
                </p>
            `;

            if (job.status === 'completed' && job.data?.video_url) {
                content += `
                    <div class="mt-2">
                        <video controls class="w-full rounded">
                            <source src="${job.data.video_url}" type="video/mp4">
                            Your browser does not support the video tag.
                        </video>
                        <a href="${job.data.video_url}" target="_blank" class="inline-block mt-2 bg-green-500 text-white px-4 py-2 rounded hover:bg-green-600">
                            Download Video
                        </a>
                    </div>
                `;
            }

            resultDiv.innerHTML = content;
            results.appendChild(resultDiv);
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
