// ==========================================================================
// KRONOS 4K - Client Logic & Realtime Downloader
// ==========================================================================

document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const urlInput = document.getElementById('video-url-input');
    const pasteBtn = document.getElementById('paste-btn');
    const clearBtn = document.getElementById('clear-btn');
    const fetchBtn = document.getElementById('fetch-btn');
    const errorBanner = document.getElementById('error-banner');
    const errorMessage = document.getElementById('error-message');
    const skeletonLoader = document.getElementById('skeleton-loader');
    const previewSection = document.getElementById('preview-section');

    // Preview Meta Elements
    const videoThumbnail = document.getElementById('video-thumbnail');
    const videoDuration = document.getElementById('video-duration');
    const metaResolutionTag = document.getElementById('meta-resolution-tag');
    const videoViews = document.getElementById('video-views');
    const videoTitle = document.getElementById('video-title');
    const videoChannel = document.getElementById('video-channel');
    const videoOptionsList = document.getElementById('video-options-list');
    const audioOptionsList = document.getElementById('audio-options-list');

    // Tab buttons
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');

    // Modal Elements
    const downloadModal = document.getElementById('download-modal');
    const modalCloseBtn = document.getElementById('modal-close-btn');
    const modalStatusIcon = document.getElementById('modal-status-icon');
    const modalHeading = document.getElementById('modal-heading');
    const modalSubtext = document.getElementById('modal-subtext');
    const modalTargetBadge = document.getElementById('modal-target-badge');
    const modalTargetTitle = document.getElementById('modal-target-title');
    const progressBarFill = document.getElementById('progress-bar-fill');
    const progressPercent = document.getElementById('progress-percent');
    const progressSpeed = document.getElementById('progress-speed');
    const progressSize = document.getElementById('progress-size');
    const progressEta = document.getElementById('progress-eta');
    const progressStepMsg = document.getElementById('progress-step-message');
    const modalActions = document.getElementById('modal-actions');
    const saveFileBtn = document.getElementById('save-file-btn');
    const openFolderBtn = document.getElementById('open-folder-btn');

    // Current State
    let currentVideoData = null;
    let activePollInterval = null;
    let currentTaskId = null;

    // Clipboard Paste Handler
    pasteBtn.addEventListener('click', async () => {
        try {
            const text = await navigator.clipboard.readText();
            if (text) {
                urlInput.value = text.trim();
                urlInput.dispatchEvent(new Event('input'));
                fetchVideoDetails();
            }
        } catch (err) {
            urlInput.focus();
        }
    });

    // Clear Input Handler
    clearBtn.addEventListener('click', () => {
        urlInput.value = '';
        clearBtn.classList.add('hidden');
        urlInput.focus();
    });

    urlInput.addEventListener('input', () => {
        if (urlInput.value.trim().length > 0) {
            clearBtn.classList.remove('hidden');
        } else {
            clearBtn.classList.add('hidden');
        }
    });

    // Enter Key Trigger
    urlInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            fetchVideoDetails();
        }
    });

    fetchBtn.addEventListener('click', fetchVideoDetails);

    // Tab Navigation
    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            tabBtns.forEach(b => b.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));

            btn.classList.add('active');
            const targetTab = document.getElementById(btn.dataset.tab);
            if (targetTab) targetTab.classList.add('active');
        });
    });

    // Modal Close
    modalCloseBtn.addEventListener('click', () => {
        downloadModal.classList.add('hidden');
        if (activePollInterval) {
            clearInterval(activePollInterval);
            activePollInterval = null;
        }
    });

    // Reveal in Folder
    openFolderBtn.addEventListener('click', async () => {
        if (!currentTaskId) return;
        try {
            const res = await fetch(`/api/open-folder/${currentTaskId}`, { method: 'POST' });
            const data = await res.json();
            if (data.success) {
                openFolderBtn.innerHTML = `
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="2">
                        <polyline points="20 6 9 17 4 12"></polyline>
                    </svg>
                    <span>Folder Opened</span>
                `;
            }
        } catch (e) {
            console.error(e);
        }
    });

    // Main Fetch Function
    async function fetchVideoDetails() {
        const url = urlInput.value.trim();
        if (!url) {
            showError('Please paste a YouTube link first.');
            urlInput.focus();
            return;
        }

        hideError();
        previewSection.classList.add('hidden');
        skeletonLoader.classList.remove('hidden');
        setLoading(true);

        try {
            const res = await fetch('/api/info', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url })
            });

            const data = await res.json();

            if (!res.ok) {
                throw new Error(data.detail || 'Failed to extract video details.');
            }

            currentVideoData = data;
            renderVideoPreview(data);
        } catch (err) {
            showError(err.message || 'Unable to load video. Please check your internet or URL.');
        } finally {
            skeletonLoader.classList.add('hidden');
            setLoading(false);
        }
    }

    // Render Preview and Quality Options
    function renderVideoPreview(data) {
        videoThumbnail.src = data.thumbnail || '';
        videoDuration.textContent = data.duration_formatted || '0:00';
        videoTitle.textContent = data.title || 'Untitled';
        videoChannel.textContent = data.channel || 'YouTube';
        videoViews.textContent = data.views_formatted || '0 views';

        // Set top badge resolution (e.g. 4K if available)
        const highestVideo = data.video_options && data.video_options.length > 0 ? data.video_options[0] : null;
        if (highestVideo) {
            metaResolutionTag.textContent = highestVideo.badge || 'HD';
        }

        // Render Video Formats
        videoOptionsList.innerHTML = '';
        if (data.video_options && data.video_options.length > 0) {
            data.video_options.forEach(opt => {
                const is4K = opt.height >= 2160;
                const is2K = opt.height === 1440;
                const card = document.createElement('div');
                card.className = `option-card ${is4K ? 'option-4k' : ''}`;
                card.innerHTML = `
                    <div class="option-info">
                        <div class="option-header-row">
                            <span class="option-quality">${opt.label}</span>
                            <span class="option-badge ${is4K ? 'badge-4k' : ''}">${opt.badge}</span>
                            ${opt.fps ? `<span class="option-badge">${opt.fps}</span>` : ''}
                        </div>
                        <div class="option-subtext">
                            <span>${opt.ext.toUpperCase()}</span>
                            <span>•</span>
                            <span>${opt.size_formatted}</span>
                        </div>
                    </div>
                    <div class="option-download-btn" title="Download ${opt.label}">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                            <polyline points="7 10 12 15 17 10"></polyline>
                            <line x1="12" y1="15" x2="12" y2="3"></line>
                        </svg>
                    </div>
                `;

                card.addEventListener('click', () => initiateDownload(opt, 'video'));
                videoOptionsList.appendChild(card);
            });
        } else {
            videoOptionsList.innerHTML = '<p style="color: var(--text-muted); padding: 10px;">No specific video streams detected.</p>';
        }

        // Render Audio Formats
        audioOptionsList.innerHTML = '';
        if (data.audio_options && data.audio_options.length > 0) {
            data.audio_options.forEach(opt => {
                const card = document.createElement('div');
                card.className = 'option-card';
                card.innerHTML = `
                    <div class="option-info">
                        <div class="option-header-row">
                            <span class="option-quality">${opt.label}</span>
                            <span class="option-badge">${opt.badge}</span>
                        </div>
                        <div class="option-subtext">
                            <span>${opt.ext.toUpperCase()}</span>
                            <span>•</span>
                            <span>${opt.size_formatted}</span>
                        </div>
                    </div>
                    <div class="option-download-btn" title="Download ${opt.label}">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                            <polyline points="7 10 12 15 17 10"></polyline>
                            <line x1="12" y1="15" x2="12" y2="3"></line>
                        </svg>
                    </div>
                `;

                card.addEventListener('click', () => initiateDownload(opt, 'audio'));
                audioOptionsList.appendChild(card);
            });
        }

        previewSection.classList.remove('hidden');
        previewSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

    // Trigger Download Task
    async function initiateDownload(option, type) {
        if (!currentVideoData) return;

        // Reset and prepare Modal
        downloadModal.classList.remove('hidden');
        modalActions.classList.add('hidden');
        modalStatusIcon.className = 'modal-icon-badge';
        modalStatusIcon.innerHTML = `
            <svg class="spin-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 12a9 9 0 1 1-6.219-8.56"></path>
            </svg>
        `;
        modalHeading.textContent = 'Processing Download...';
        modalSubtext.textContent = 'Fetching high-speed streams from YouTube';
        modalTargetBadge.textContent = option.badge || (type === 'video' ? 'Video' : 'Audio');
        modalTargetTitle.textContent = currentVideoData.title || '';
        progressBarFill.style.width = '0%';
        progressPercent.textContent = '0%';
        progressSpeed.textContent = 'Connecting...';
        progressSize.textContent = '-- / --';
        progressEta.textContent = 'ETA: --';
        progressStepMsg.textContent = 'Initializing background worker...';

        openFolderBtn.innerHTML = `
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>
            </svg>
            <span>Open Folder</span>
        `;

        try {
            const res = await fetch('/api/download', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    url: currentVideoData.url,
                    option_id: option.id,
                    option_type: type
                })
            });

            const data = await res.json();
            if (!res.ok) {
                throw new Error(data.detail || 'Could not start download task.');
            }

            currentTaskId = data.task_id;
            startPollingProgress(data.task_id);
        } catch (err) {
            handleDownloadError(err.message || 'Failed to start download');
        }
    }

    // Poll Progress Endpoint
    function startPollingProgress(taskId) {
        if (activePollInterval) clearInterval(activePollInterval);

        activePollInterval = setInterval(async () => {
            try {
                const res = await fetch(`/api/progress/${taskId}`);
                if (!res.ok) return;

                const task = await res.json();

                if (task.status === 'downloading' || task.status === 'starting') {
                    const percent = Math.min(task.progress || 0, 99);
                    progressBarFill.style.width = `${percent}%`;
                    progressPercent.textContent = `${Math.round(percent)}%`;
                    progressSpeed.textContent = task.speed || 'Downloading...';
                    progressSize.textContent = `${task.downloaded_formatted || '0 MB'} / ${task.total_formatted || '...'}`;
                    progressEta.textContent = task.eta ? `ETA: ${task.eta}` : 'Calculating...';
                    progressStepMsg.textContent = task.step_message || 'Downloading media stream...';
                } else if (task.status === 'processing') {
                    progressBarFill.style.width = '99%';
                    progressPercent.textContent = '99%';
                    progressSpeed.textContent = 'Processing';
                    progressEta.textContent = 'Merging';
                    progressStepMsg.textContent = 'Merging video & audio with FFmpeg 8.1...';
                    modalHeading.textContent = 'Finalizing Media...';
                    modalSubtext.textContent = 'Encoding & adding ID3 metadata tags';
                } else if (task.status === 'completed') {
                    clearInterval(activePollInterval);
                    activePollInterval = null;
                    handleDownloadCompleted(task, taskId);
                } else if (task.status === 'error') {
                    clearInterval(activePollInterval);
                    activePollInterval = null;
                    handleDownloadError(task.error || 'Download failed during processing.');
                }
            } catch (e) {
                console.warn('Poll error:', e);
            }
        }, 500);
    }

    // Download Finished Handler
    function handleDownloadCompleted(task, taskId) {
        progressBarFill.style.width = '100%';
        progressPercent.textContent = '100%';
        progressSpeed.textContent = 'Done';
        progressSize.textContent = task.filesize_formatted || '';
        progressEta.textContent = 'Complete';
        progressStepMsg.textContent = task.step_message || 'Download ready!';

        modalStatusIcon.className = 'modal-icon-badge success';
        modalStatusIcon.innerHTML = `
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                <polyline points="20 6 9 17 4 12"></polyline>
            </svg>
        `;
        modalHeading.textContent = 'Download Complete!';
        modalSubtext.textContent = `Ready: ${task.filename || 'media file'}`;

        const fileDownloadUrl = `/api/file/${taskId}`;
        saveFileBtn.href = fileDownloadUrl;
        saveFileBtn.setAttribute('download', task.filename || 'video.mp4');

        modalActions.classList.remove('hidden');

        // Automatically trigger browser download popup
        triggerBrowserDownload(fileDownloadUrl, task.filename);
    }

    function triggerBrowserDownload(url, filename) {
        const link = document.createElement('a');
        link.href = url;
        link.download = filename || 'download';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }

    // Download Error Handler
    function handleDownloadError(msg) {
        modalStatusIcon.className = 'modal-icon-badge error';
        modalStatusIcon.innerHTML = `
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10"></circle>
                <line x1="15" y1="9" x2="9" y2="15"></line>
                <line x1="9" y1="9" x2="15" y2="15"></line>
            </svg>
        `;
        modalHeading.textContent = 'Download Failed';
        modalSubtext.textContent = 'An error occurred while downloading';
        progressStepMsg.textContent = msg;
        progressBarFill.style.background = '#ef4444';
    }

    // Loading State on Fetch Button
    function setLoading(isLoading) {
        const btnText = fetchBtn.querySelector('.btn-text');
        const btnArrow = fetchBtn.querySelector('.btn-arrow');
        const spinner = fetchBtn.querySelector('.spinner');

        if (isLoading) {
            fetchBtn.disabled = true;
            btnText.textContent = 'Analyzing...';
            btnArrow.classList.add('hidden');
            spinner.classList.remove('hidden');
        } else {
            fetchBtn.disabled = false;
            btnText.textContent = 'Fetch Video';
            btnArrow.classList.remove('hidden');
            spinner.classList.add('hidden');
        }
    }

    function showError(msg) {
        errorMessage.textContent = msg;
        errorBanner.classList.remove('hidden');
    }

    function hideError() {
        errorBanner.classList.add('hidden');
    }
});
