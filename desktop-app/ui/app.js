// ==========================================================================
// KRONOS 4K - Desktop Application Controller
// ==========================================================================

document.addEventListener('DOMContentLoaded', () => {
    // Topbar Controls
    const folderPickerBtn = document.getElementById('folder-picker-btn');
    const currentFolderLabel = document.getElementById('current-folder-label');
    const statusbarDestText = document.getElementById('statusbar-dest-text');
    const cookiesBtn = document.getElementById('cookies-btn');
    const cookieStatusText = document.getElementById('cookie-status-text');

    // Main Input Elements
    const urlInput = document.getElementById('video-url-input');
    const pasteBtn = document.getElementById('paste-btn');
    const clearBtn = document.getElementById('clear-btn');
    const fetchBtn = document.getElementById('fetch-btn');
    const errorBanner = document.getElementById('error-banner');
    const errorMessage = document.getElementById('error-message');
    const errorCookieBtn = document.getElementById('error-cookie-btn');
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

    // Tabs
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');

    // Download Modal Elements
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
    const openFileFolderBtn = document.getElementById('open-file-folder-btn');
    const modalDoneBtn = document.getElementById('modal-done-btn');

    // Download Controls (Pause / Resume / Stop)
    const downloadControls = document.getElementById('download-controls');
    const pauseResumeBtn = document.getElementById('pause-resume-btn');
    const pauseIcon = document.getElementById('pause-icon');
    const resumeIcon = document.getElementById('resume-icon');
    const pauseResumeText = document.getElementById('pause-resume-text');
    const stopDownloadBtn = document.getElementById('stop-download-btn');

    // Engine Update Elements
    const engineUpdateBtn = document.getElementById('engine-update-btn');
    const engineVersionLabel = document.getElementById('engine-version-label');
    const engineUpdateBadge = document.getElementById('engine-update-badge');
    const engineUpdateModal = document.getElementById('engine-update-modal');
    const engineModalCloseBtn = document.getElementById('engine-modal-close-btn');
    const engineCurrentVersion = document.getElementById('engine-current-version');
    const engineLatestVersion = document.getElementById('engine-latest-version');
    const engineStatusTag = document.getElementById('engine-status-tag');
    const engineUpdateProgressCard = document.getElementById('engine-update-progress-card');
    const engineUpdateMsg = document.getElementById('engine-update-msg');
    const checkEngineBtn = document.getElementById('check-engine-btn');
    const installEngineBtn = document.getElementById('install-engine-btn');

    // State
    let currentVideoData = null;
    let activePollInterval = null;
    let currentCompletedFilePath = null;
    let currentActiveTaskId = null;
    let isDownloadPaused = false;
    let currentSaveDirectory = localStorage.getItem('kronos_save_dir') || null;

    // Helper for pywebview API calls with promise wrapper
    async function callApi(fnName, ...args) {
        if (window.pywebview && window.pywebview.api && typeof window.pywebview.api[fnName] === 'function') {
            return await window.pywebview.api[fnName](...args);
        }
        return null;
    }

    // Initialize Window State once pywebview is ready
    window.addEventListener('pywebviewready', async () => {
        if (!currentSaveDirectory) {
            currentSaveDirectory = await callApi('get_default_downloads_dir');
            if (currentSaveDirectory) {
                updateFolderDisplay(currentSaveDirectory);
            }
        } else {
            updateFolderDisplay(currentSaveDirectory);
        }
        checkCookiesStatus();
        checkEngineStatus(true);
    });

    // Developer GitHub Link Handler
    const devGithubLink = document.getElementById('dev-github-link');
    if (devGithubLink) {
        devGithubLink.addEventListener('click', (e) => {
            e.preventDefault();
            callApi('open_external_url', 'https://github.com/Bl4ke100');
        });
    }

    // Engine Update Handlers
    async function checkEngineStatus(silent = false) {
        try {
            const data = await callApi('check_engine_update');
            if (data && data.success) {
                if (engineVersionLabel) {
                    engineVersionLabel.textContent = `v${data.current_version}`;
                }
                if (engineCurrentVersion) engineCurrentVersion.textContent = `v${data.current_version}`;
                if (engineLatestVersion) engineLatestVersion.textContent = `v${data.latest_version}`;

                if (data.update_available) {
                    if (engineUpdateBadge) engineUpdateBadge.classList.remove('hidden');
                    if (engineStatusTag) {
                        engineStatusTag.className = 'engine-status-badge update-ready';
                        engineStatusTag.textContent = 'Update Available';
                    }
                    if (installEngineBtn) installEngineBtn.classList.remove('hidden');
                } else {
                    if (engineUpdateBadge) engineUpdateBadge.classList.add('hidden');
                    if (engineStatusTag) {
                        engineStatusTag.className = 'engine-status-badge up-to-date';
                        engineStatusTag.textContent = 'Up to Date';
                    }
                    if (installEngineBtn) installEngineBtn.classList.add('hidden');
                }
            }
        } catch (e) {
            console.warn('Engine check error:', e);
        }
    }

    if (engineUpdateBtn) {
        engineUpdateBtn.addEventListener('click', () => {
            if (engineUpdateModal) engineUpdateModal.classList.remove('hidden');
            checkEngineStatus();
        });
    }

    if (engineModalCloseBtn) {
        engineModalCloseBtn.addEventListener('click', () => {
            if (engineUpdateModal) engineUpdateModal.classList.add('hidden');
        });
    }

    if (checkEngineBtn) {
        checkEngineBtn.addEventListener('click', async () => {
            checkEngineBtn.textContent = 'Checking...';
            await checkEngineStatus();
            checkEngineBtn.textContent = 'Check for Updates';
        });
    }

    if (installEngineBtn) {
        installEngineBtn.addEventListener('click', async () => {
            if (engineUpdateProgressCard) engineUpdateProgressCard.classList.remove('hidden');
            installEngineBtn.disabled = true;
            if (engineUpdateMsg) engineUpdateMsg.textContent = 'Downloading and extracting latest yt-dlp release...';

            try {
                const data = await callApi('install_engine_update');
                if (data && data.success) {
                    if (engineUpdateMsg) engineUpdateMsg.textContent = data.message || 'Engine updated successfully!';
                    await checkEngineStatus();
                    setTimeout(() => {
                        if (engineUpdateProgressCard) engineUpdateProgressCard.classList.add('hidden');
                        installEngineBtn.disabled = false;
                    }, 2000);
                } else {
                    if (engineUpdateMsg) engineUpdateMsg.textContent = `Update failed: ${data?.error || 'Unknown error'}`;
                    installEngineBtn.disabled = false;
                }
            } catch (err) {
                if (engineUpdateMsg) engineUpdateMsg.textContent = `Update error: ${err.message}`;
                installEngineBtn.disabled = false;
            }
        });
    }

    function updateFolderDisplay(folderPath) {
        if (!folderPath) return;
        const folderName = folderPath.split(/[\\/]/).pop() || folderPath;
        currentFolderLabel.textContent = folderName;
        currentFolderLabel.title = folderPath;
        statusbarDestText.textContent = `Saving to: ${folderPath}`;
    }

    // Folder Picker
    folderPickerBtn.addEventListener('click', async () => {
        const pickedDir = await callApi('select_download_folder');
        if (pickedDir) {
            currentSaveDirectory = pickedDir;
            localStorage.setItem('kronos_save_dir', pickedDir);
            updateFolderDisplay(pickedDir);
        }
    });

    // Cookie Modal Elements
    const cookieSettingsModal = document.getElementById('cookie-settings-modal');
    const cookieModalCloseBtn = document.getElementById('cookie-modal-close-btn');
    const authSignedInCard = document.getElementById('auth-signed-in-card');
    const authSignedOutCard = document.getElementById('auth-signed-out-card');
    const inAppLoginBtn = document.getElementById('in-app-login-btn');
    const reauthBtn = document.getElementById('reauth-btn');
    const signoutBtn = document.getElementById('signout-btn');
    const browserCookieSelect = document.getElementById('browser-cookie-select');
    const importBrowserBtn = document.getElementById('import-browser-btn');
    const importBtnText = document.getElementById('import-btn-text');
    const importSpinner = document.getElementById('import-spinner');
    const browserImportStatus = document.getElementById('browser-import-status');
    const cookieFileInput = document.getElementById('cookie-file-input');
    const uploadCookieFileBtn = document.getElementById('upload-cookie-file-btn');
    const cookiesTextarea = document.getElementById('cookies-textarea');
    const saveCookiesBtn = document.getElementById('save-cookies-btn');
    const clearCookiesBtn = document.getElementById('clear-cookies-btn');

    cookiesBtn.addEventListener('click', () => {
        cookieSettingsModal.classList.remove('hidden');
        checkCookiesStatus();
    });
    cookieModalCloseBtn.addEventListener('click', () => cookieSettingsModal.classList.add('hidden'));
    errorCookieBtn.addEventListener('click', () => {
        cookieSettingsModal.classList.remove('hidden');
        checkCookiesStatus();
    });

    async function triggerInAppLogin(btn) {
        btn.disabled = true;
        const originalHtml = btn.innerHTML;
        btn.innerHTML = `
            <div class="spinner" style="display: inline-block; width: 14px; height: 14px; margin-right: 6px;"></div>
            <span>Signing in... (Finish in Google window)</span>
        `;
        
        await callApi('launch_youtube_login');
        
        let attempts = 0;
        const checkInterval = setInterval(async () => {
            attempts++;
            const statusRes = await callApi('check_cookies');
            if (statusRes && statusRes.has_cookies) {
                clearInterval(checkInterval);
                btn.innerHTML = `<span>✓ Linked!</span>`;
                btn.style.background = '#10b981';
                btn.style.color = '#ffffff';
                
                await checkCookiesStatus();
                
                setTimeout(() => {
                    cookieSettingsModal.classList.add('hidden');
                    btn.disabled = false;
                    btn.style.background = '';
                    btn.style.color = '';
                    btn.innerHTML = originalHtml;
                }, 1000);
            } else if (attempts > 90) {
                clearInterval(checkInterval);
                btn.disabled = false;
                btn.innerHTML = originalHtml;
            }
        }, 1500);
    }

    if (inAppLoginBtn) {
        inAppLoginBtn.addEventListener('click', () => triggerInAppLogin(inAppLoginBtn));
    }
    if (reauthBtn) {
        reauthBtn.addEventListener('click', () => triggerInAppLogin(reauthBtn));
    }

    if (importBrowserBtn) {
        importBrowserBtn.addEventListener('click', async () => {
            const browserName = browserCookieSelect ? browserCookieSelect.value : 'chrome';
            importBrowserBtn.disabled = true;
            if (importBtnText) importBtnText.textContent = 'Importing...';
            if (importSpinner) importSpinner.classList.remove('hidden');
            if (browserImportStatus) {
                browserImportStatus.textContent = `Reading cookies from ${browserName.toUpperCase()}...`;
                browserImportStatus.style.color = 'var(--text-secondary)';
            }

            try {
                const res = await callApi('import_browser_cookies', browserName);
                if (res && res.success) {
                    if (browserImportStatus) {
                        browserImportStatus.textContent = `✓ ${res.message || 'Cookies imported successfully!'}`;
                        browserImportStatus.style.color = '#10b981';
                    }
                    if (importBtnText) importBtnText.textContent = '✓ Imported!';
                    await checkCookiesStatus();
                    setTimeout(() => {
                        cookieSettingsModal.classList.add('hidden');
                        if (importBtnText) importBtnText.textContent = 'Import Cookies';
                    }, 1200);
                } else {
                    const err = (res && res.error) || 'Failed to import cookies.';
                    if (browserImportStatus) {
                        browserImportStatus.textContent = `⚠ ${err}`;
                        browserImportStatus.style.color = '#f87171';
                    }
                    if (importBtnText) importBtnText.textContent = 'Import Cookies';
                }
            } catch (err) {
                if (browserImportStatus) {
                    browserImportStatus.textContent = `⚠ ${err.message || 'Import error'}`;
                    browserImportStatus.style.color = '#f87171';
                }
                if (importBtnText) importBtnText.textContent = 'Import Cookies';
            } finally {
                importBrowserBtn.disabled = false;
                if (importSpinner) importSpinner.classList.add('hidden');
            }
        });
    }

    if (signoutBtn) {
        signoutBtn.addEventListener('click', async () => {
            await callApi('clear_cookies');
            cookiesTextarea.value = '';
            await checkCookiesStatus();
        });
    }

    uploadCookieFileBtn.addEventListener('click', () => cookieFileInput.click());
    cookieFileInput.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = (event) => {
                cookiesTextarea.value = event.target.result;
            };
            reader.readAsText(file);
        }
    });

    saveCookiesBtn.addEventListener('click', async () => {
        const cookieText = cookiesTextarea.value.trim();
        if (cookieText) {
            await callApi('save_cookies', cookieText);
        }

        cookieSettingsModal.classList.add('hidden');
        checkCookiesStatus();
    });

    clearCookiesBtn.addEventListener('click', async () => {
        cookiesTextarea.value = '';
        await callApi('clear_cookies');
        cookieSettingsModal.classList.add('hidden');
        checkCookiesStatus();
    });

    async function checkCookiesStatus() {
        const res = await callApi('check_cookies');
        const hasFile = res && res.has_cookies;

        if (hasFile) {
            cookiesBtn.classList.add('active');
            cookieStatusText.textContent = 'Auth: Signed In';
            if (authSignedInCard) authSignedInCard.classList.remove('hidden');
            if (authSignedOutCard) authSignedOutCard.classList.add('hidden');
        } else {
            cookiesBtn.classList.remove('active');
            cookieStatusText.textContent = 'Cookies';
            if (authSignedInCard) authSignedInCard.classList.add('hidden');
            if (authSignedOutCard) authSignedOutCard.classList.remove('hidden');
        }
    }

    // Input handlers
    pasteBtn.addEventListener('click', async () => {
        try {
            const text = await navigator.clipboard.readText();
            if (text) {
                urlInput.value = text.trim();
                urlInput.dispatchEvent(new Event('input'));
                fetchVideoDetails();
            }
        } catch (e) {
            urlInput.focus();
        }
    });

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

    modalDoneBtn.addEventListener('click', () => {
        downloadModal.classList.add('hidden');
    });

    // Reveal in File Explorer
    openFileFolderBtn.addEventListener('click', () => {
        if (currentCompletedFilePath) {
            callApi('reveal_in_explorer', currentCompletedFilePath);
        } else if (currentSaveDirectory) {
            callApi('reveal_in_explorer', currentSaveDirectory);
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
            const res = await callApi('fetch_video_info', url);

            if (!res || !res.success) {
                throw new Error(res?.error || 'Failed to extract video details.');
            }

            currentVideoData = res.data;
            renderVideoPreview(res.data);
        } catch (err) {
            const msg = err.message || 'Unable to load video.';
            const isAgeOrCookie = msg.toLowerCase().includes('age') || msg.toLowerCase().includes('sign in') || msg.toLowerCase().includes('cookie');
            showError(msg, isAgeOrCookie);
        } finally {
            skeletonLoader.classList.add('hidden');
            setLoading(false);
        }
    }

    // Render Preview
    function renderVideoPreview(data) {
        videoThumbnail.src = data.thumbnail || '';
        videoDuration.textContent = data.duration_formatted || '0:00';
        videoTitle.textContent = data.title || 'Untitled';
        videoChannel.textContent = data.channel || 'YouTube';
        videoViews.textContent = data.views_formatted || '0 views';

        const highestVideo = data.video_options && data.video_options.length > 0 ? data.video_options[0] : null;
        if (highestVideo) {
            metaResolutionTag.textContent = highestVideo.badge || 'HD';
        }

        // Render Video Formats
        videoOptionsList.innerHTML = '';
        if (data.video_options && data.video_options.length > 0) {
            data.video_options.forEach(opt => {
                const is4K = opt.height >= 2160;
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
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                            <polyline points="7 10 12 15 17 10"></polyline>
                            <line x1="12" y1="15" x2="12" y2="3"></line>
                        </svg>
                    </div>
                `;

                card.addEventListener('click', () => initiateDownload(opt, 'video'));
                videoOptionsList.appendChild(card);
            });
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
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
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

    // Download Controls Click Handlers
    function setPauseState(paused) {
        isDownloadPaused = paused;
        if (!pauseResumeBtn) return;
        if (paused) {
            pauseResumeBtn.classList.add('is-paused');
            if (pauseIcon) pauseIcon.classList.add('hidden');
            if (resumeIcon) resumeIcon.classList.remove('hidden');
            if (pauseResumeText) pauseResumeText.textContent = 'Resume';
            progressBarFill.classList.add('paused');
        } else {
            pauseResumeBtn.classList.remove('is-paused');
            if (pauseIcon) pauseIcon.classList.remove('hidden');
            if (resumeIcon) resumeIcon.classList.add('hidden');
            if (pauseResumeText) pauseResumeText.textContent = 'Pause';
            progressBarFill.classList.remove('paused');
        }
    }

    if (pauseResumeBtn) {
        pauseResumeBtn.addEventListener('click', async () => {
            if (!currentActiveTaskId) return;
            if (!isDownloadPaused) {
                await callApi('pause_download', currentActiveTaskId);
                setPauseState(true);
                progressSpeed.textContent = '0 KB/s (Paused)';
                progressStepMsg.textContent = 'Download paused by user';
            } else {
                await callApi('resume_download', currentActiveTaskId);
                setPauseState(false);
                progressStepMsg.textContent = 'Resuming download...';
            }
        });
    }

    if (stopDownloadBtn) {
        stopDownloadBtn.addEventListener('click', async () => {
            if (!currentActiveTaskId) return;
            await callApi('stop_download', currentActiveTaskId);
            handleDownloadStopped();
        });
    }

    function handleDownloadStopped() {
        if (activePollInterval) {
            clearInterval(activePollInterval);
            activePollInterval = null;
        }
        if (downloadControls) downloadControls.classList.add('hidden');
        setPauseState(false);
        progressBarFill.style.width = '0%';
        progressPercent.textContent = '0%';
        progressSpeed.textContent = 'Stopped';
        progressEta.textContent = '--';
        progressStepMsg.textContent = 'Download stopped and temporary files cleaned.';

        modalStatusIcon.className = 'modal-icon-badge error';
        modalStatusIcon.innerHTML = `
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10"></circle>
                <line x1="15" y1="9" x2="9" y2="15"></line>
                <line x1="9" y1="9" x2="15" y2="15"></line>
            </svg>
        `;
        modalHeading.textContent = 'Download Stopped';
        modalSubtext.textContent = 'The download task was cancelled.';
    }

    // Trigger Download Task
    async function initiateDownload(option, type) {
        if (!currentVideoData) return;

        downloadModal.classList.remove('hidden');
        modalActions.classList.add('hidden');
        if (downloadControls) downloadControls.classList.remove('hidden');
        setPauseState(false);

        modalStatusIcon.className = 'modal-icon-badge';
        modalStatusIcon.innerHTML = `
            <svg class="spin-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 12a9 9 0 1 1-6.219-8.56"></path>
            </svg>
        `;
        modalHeading.textContent = 'Downloading Media...';
        modalSubtext.textContent = 'Fetching high-speed streams from YouTube';
        modalTargetBadge.textContent = option.badge || (type === 'video' ? 'Video' : 'Audio');
        modalTargetTitle.textContent = currentVideoData.title || '';
        progressBarFill.style.width = '0%';
        progressPercent.textContent = '0%';
        progressSpeed.textContent = 'Connecting...';
        progressSize.textContent = '-- / --';
        progressEta.textContent = 'ETA: --';
        progressStepMsg.textContent = 'Initializing background worker...';
        currentCompletedFilePath = null;

        try {
            const res = await callApi(
                'start_download_task',
                currentVideoData.url,
                option.id,
                type,
                currentSaveDirectory
            );

            if (!res || !res.success) {
                throw new Error(res?.error || 'Could not start download.');
            }

            currentActiveTaskId = res.task_id;
            startPollingProgress(res.task_id);
        } catch (err) {
            handleDownloadError(err.message || 'Failed to start download');
        }
    }

    // Polling Loop
    function startPollingProgress(taskId) {
        if (activePollInterval) clearInterval(activePollInterval);

        activePollInterval = setInterval(async () => {
            try {
                const task = await callApi('get_download_progress', taskId);
                if (!task) return;

                if (task.status === 'paused') {
                    setPauseState(true);
                    progressSpeed.textContent = task.speed || '0 KB/s (Paused)';
                    progressStepMsg.textContent = task.step_message || 'Download paused by user';
                } else if (task.status === 'downloading' || task.status === 'starting') {
                    setPauseState(false);
                    const percent = Math.min(task.progress || 0, 99);
                    progressBarFill.style.width = `${percent}%`;
                    progressPercent.textContent = `${Math.round(percent)}%`;
                    progressSpeed.textContent = task.speed || 'Downloading...';
                    progressSize.textContent = `${task.downloaded_formatted || '0 MB'} / ${task.total_formatted || '...'}`;
                    progressEta.textContent = task.eta ? `ETA: ${task.eta}` : 'Calculating...';
                    progressStepMsg.textContent = task.step_message || 'Downloading media stream...';
                } else if (task.status === 'processing') {
                    setPauseState(false);
                    progressBarFill.style.width = '99%';
                    progressPercent.textContent = '99%';
                    progressSpeed.textContent = 'Processing';
                    progressEta.textContent = 'Merging';
                    progressStepMsg.textContent = 'Merging video & audio streams with FFmpeg...';
                    modalHeading.textContent = 'Finalizing Media...';
                    modalSubtext.textContent = 'Encoding & saving directly to folder';
                } else if (task.status === 'stopped') {
                    clearInterval(activePollInterval);
                    activePollInterval = null;
                    handleDownloadStopped();
                } else if (task.status === 'completed') {
                    clearInterval(activePollInterval);
                    activePollInterval = null;
                    if (downloadControls) downloadControls.classList.add('hidden');
                    handleDownloadCompleted(task);
                } else if (task.status === 'error') {
                    clearInterval(activePollInterval);
                    activePollInterval = null;
                    if (downloadControls) downloadControls.classList.add('hidden');
                    handleDownloadError(task.error || 'Download failed during processing.');
                }
            } catch (e) {
                console.warn('Poll error:', e);
            }
        }, 400);
    }

    function handleDownloadCompleted(task) {
        progressBarFill.style.width = '100%';
        progressPercent.textContent = '100%';
        progressSpeed.textContent = 'Done';
        progressSize.textContent = task.filesize_formatted || '';
        progressEta.textContent = 'Saved';
        progressStepMsg.textContent = 'File successfully saved to your downloads folder!';

        modalStatusIcon.className = 'modal-icon-badge success';
        modalStatusIcon.innerHTML = `
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                <polyline points="20 6 9 17 4 12"></polyline>
            </svg>
        `;
        modalHeading.textContent = 'Download Complete!';
        modalSubtext.textContent = `Saved: ${task.filename || 'media file'}`;

        currentCompletedFilePath = task.filepath;
        modalActions.classList.remove('hidden');
    }

    function handleDownloadError(msg) {
        modalStatusIcon.className = 'modal-icon-badge error';
        modalStatusIcon.innerHTML = `
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
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

    function showError(msg, showCookieHint = false) {
        errorMessage.textContent = msg;
        if (showCookieHint) {
            errorCookieBtn.classList.remove('hidden');
        } else {
            errorCookieBtn.classList.add('hidden');
        }
        errorBanner.classList.remove('hidden');
    }

    function hideError() {
        errorBanner.classList.add('hidden');
    }
});
