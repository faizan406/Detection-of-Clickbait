document.addEventListener('DOMContentLoaded', () => {
  
  // =========================================================================
  // 1. Navigation Tabs & Breadcrumb Sync
  // =========================================================================
  const tabBtns = document.querySelectorAll('.tab-btn[data-tab]');
  const tabContents = document.querySelectorAll('.tab-content');
  const breadcrumbCategory = document.getElementById('bc-category');
  const breadcrumbPage = document.getElementById('bc-page');

  const breadcrumbMap = {
    detector: { cat: 'Analyzer', page: 'Real-time Detector' },
    wordcloud: { cat: 'Analytics', page: 'Word Cloud Insights' },
    studio: { cat: 'Model Management', page: 'ML Studio' },
    history: { cat: 'Database', page: 'Detection History Log' }
  };

  tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const targetTab = btn.getAttribute('data-tab');
      if (!targetTab) return;
      
      tabBtns.forEach(b => b.classList.remove('active'));
      tabContents.forEach(c => c.classList.remove('active'));

      btn.classList.add('active');
      const targetContent = document.getElementById(`tab-${targetTab}`);
      if (targetContent) targetContent.classList.add('active');

      // Update Topbar Breadcrumb
      if (breadcrumbMap[targetTab]) {
        if (breadcrumbCategory) breadcrumbCategory.textContent = breadcrumbMap[targetTab].cat;
        if (breadcrumbPage) breadcrumbPage.textContent = breadcrumbMap[targetTab].page;
      }

      // Load specific tab data on activation
      if (targetTab === 'studio') {
        loadMetrics();
      } else if (targetTab === 'history') {
        loadHistory();
      } else if (targetTab === 'wordcloud') {
        loadWordCloud();
      }
    });
  });

  // Sidebar Brand / Logo Click -> Return to Home (Detector Tab)
  const brandHomeBtn = document.getElementById('brand-home-btn');
  brandHomeBtn?.addEventListener('click', (e) => {
    e.preventDefault();
    const detectorBtn = document.querySelector('.tab-btn[data-tab="detector"]');
    if (detectorBtn) detectorBtn.click();
    window.scrollTo({ top: 0, behavior: 'smooth' });
  });

  // =========================================================================
  // 2. Mode Switcher (Headline / Text vs Live URL Analysis)
  // =========================================================================
  const modeTextBtn = document.getElementById('mode-text-btn');
  const modeUrlBtn = document.getElementById('mode-url-btn');
  const textInputBox = document.getElementById('text-input-box');
  const urlInputBox = document.getElementById('url-input-box');
  const quickLinkBtn = document.getElementById('quick-link-btn');

  function activateTextMode() {
    modeTextBtn.classList.add('active');
    modeUrlBtn.classList.remove('active');
    textInputBox.style.display = 'block';
    urlInputBox.style.display = 'none';
  }

  function activateUrlMode() {
    modeUrlBtn.classList.add('active');
    modeTextBtn.classList.remove('active');
    urlInputBox.style.display = 'block';
    textInputBox.style.display = 'none';
  }

  modeTextBtn?.addEventListener('click', activateTextMode);
  modeUrlBtn?.addEventListener('click', activateUrlMode);
  quickLinkBtn?.addEventListener('click', activateUrlMode);

  // Quick Paste Button (Reads text from user clipboard)
  const quickPasteBtn = document.getElementById('quick-paste-btn');
  quickPasteBtn?.addEventListener('click', async () => {
    try {
      activateTextMode();
      const clipText = await navigator.clipboard.readText();
      if (clipText) {
        headlineInput.value = clipText;
        updateCharCount(clipText.length);
      }
    } catch (err) {
      headlineInput.focus();
    }
  });

  // Character Counter (Formatted as: 0 / 1,000)
  const headlineInput = document.getElementById('headline-input');
  const charCount = document.getElementById('char-count');

  function updateCharCount(len) {
    if (charCount) {
      charCount.textContent = `${len.toLocaleString()} / 1,000`;
    }
  }

  headlineInput?.addEventListener('input', () => {
    updateCharCount(headlineInput.value.length);
  });

  // Example Prompt Chips
  const sampleChips = document.querySelectorAll('.sample-chip');
  sampleChips.forEach(chip => {
    chip.addEventListener('click', () => {
      activateTextMode();
      headlineInput.value = chip.textContent.trim();
      updateCharCount(headlineInput.value.length);
      headlineInput.focus();
    });
  });

  // Sample URL Chips
  const urlInput = document.getElementById('url-input');
  const sampleUrlChips = document.querySelectorAll('.sample-url-chip');
  sampleUrlChips.forEach(chip => {
    chip.addEventListener('click', () => {
      urlInput.value = chip.getAttribute('data-url');
      urlInput.focus();
    });
  });

  // =========================================================================
  // 3. User Authentication & Profile Widget
  // =========================================================================
  const userNav = document.getElementById('user-nav');
  const authModal = document.getElementById('auth-modal');
  const authCloseBtn = document.getElementById('auth-close-btn');
  const tabAuthLogin = document.getElementById('tab-auth-login');
  const tabAuthRegister = document.getElementById('tab-auth-register');
  const loginForm = document.getElementById('login-form');
  const registerForm = document.getElementById('register-form');
  const authAlert = document.getElementById('auth-alert');

  checkCurrentUser();

  async function checkCurrentUser() {
    try {
      const res = await fetch('/api/auth/me');
      const data = await res.json();
      const appLayout = document.getElementById('app-layout');
      if (data.authenticated && data.user) {
        window._isAuthenticated = true;
        if (appLayout) appLayout.style.display = 'flex';
        if (authModal) authModal.style.display = 'none';
        renderLoggedInUser(data.user);
      } else {
        window._isAuthenticated = false;
        if (appLayout) appLayout.style.display = 'none';
        renderDefaultUser();
        openAuthModal();
      }
    } catch (e) {
      window._isAuthenticated = false;
      const appLayout = document.getElementById('app-layout');
      if (appLayout) appLayout.style.display = 'none';
      renderDefaultUser();
      openAuthModal();
    }
  }

  function renderDefaultUser() {
    renderGuestUser();
  }

  function renderGuestUser() {
    if (!userNav) return;
    userNav.innerHTML = `
      <button class="user-profile-trigger" id="user-profile-trigger" title="Sign in to your account">
        <div class="user-avatar-initial" style="background: linear-gradient(135deg, #6366f1, #4f46e5);"><i class="fa-solid fa-user" style="font-size:13px;"></i></div>
        <span class="user-profile-name" style="color:#475569; font-weight:500;">Sign In</span>
      </button>
    `;
    document.getElementById('user-profile-trigger')?.addEventListener('click', openAuthModal);
  }

  function renderLoggedInUser(user) {
    const displayName = user.name || 'User';
    const displayEmail = user.email || '';
    const initial = displayName.charAt(0).toUpperCase();

    const avatarHtml = user.avatar_url
      ? `<img src="${user.avatar_url}" alt="${displayName}" class="user-avatar-circle">`
      : `<div class="user-avatar-initial">${initial}</div>`;

    const largeAvatarHtml = user.avatar_url
      ? `<img src="${user.avatar_url}" alt="${displayName}">`
      : `<div class="user-avatar-initial" style="width:100%; height:100%; font-size: 26px;">${initial}</div>`;

    userNav.innerHTML = `
      <div style="position: relative;">
        <button class="user-profile-trigger" id="user-profile-trigger" title="Account (${displayName})">
          ${avatarHtml}
          <span class="user-profile-name">${displayName}</span>
          <i class="fa-solid fa-chevron-down" style="font-size: 11px; color: #94a3b8; margin-left: 2px;"></i>
        </button>

        <div class="profile-dropdown-card" id="profile-dropdown-card">
          <div class="profile-avatar-large">
            ${largeAvatarHtml}
            <label class="avatar-upload-overlay" for="avatar-file-input" title="Upload / Change Photo">
              <i class="fa-solid fa-camera"></i> Change
            </label>
            <input type="file" id="avatar-file-input" accept="image/*" style="display: none;">
          </div>
          
          <div style="font-weight: 700; font-size: 15px; color: #0f172a; margin-bottom: 2px;">${displayName}</div>
          <div style="font-size: 12px; color: #64748b; margin-bottom: 12px;">${displayEmail}</div>
          
          <div style="font-size: 11px; color: #059669; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 14px; background: #ecfdf5; padding: 4px 8px; border-radius: 4px; display: inline-block;">
            <i class="fa-solid fa-circle-check"></i> System Active Analyst
          </div>

          <div style="display: flex; flex-direction: column; gap: 8px;">
            <button class="btn-clean-outline" id="switch-account-btn" style="width: 100%; justify-content: center; font-size: 12.5px; padding: 7px;">
              <i class="fa-solid fa-user-plus"></i> Switch Account / Sign In
            </button>
            <button class="btn-clean-danger" id="logout-btn" style="width: 100%; justify-content: center; font-size: 12.5px; padding: 7px;">
              <i class="fa-solid fa-right-from-bracket"></i> Sign Out
            </button>
          </div>
        </div>
      </div>
    `;

    const profileTrigger = document.getElementById('user-profile-trigger');
    const dropdownCard = document.getElementById('profile-dropdown-card');
    const avatarInput = document.getElementById('avatar-file-input');

    profileTrigger?.addEventListener('click', (e) => {
      e.stopPropagation();
      dropdownCard?.classList.toggle('active');
    });

    document.addEventListener('click', (e) => {
      if (!dropdownCard?.contains(e.target) && !profileTrigger?.contains(e.target)) {
        dropdownCard?.classList.remove('active');
      }
    });

    avatarInput?.addEventListener('change', async (e) => {
      const file = e.target.files[0];
      if (!file) return;

      const formData = new FormData();
      formData.append('avatar', file);

      try {
        const res = await fetch('/api/auth/avatar', {
          method: 'POST',
          body: formData
        });
        const data = await res.json();
        if (data.success && data.avatar_url) {
          user.avatar_url = data.avatar_url;
          renderLoggedInUser(user);
        } else {
          alert(data.message || 'Failed to update photo.');
        }
      } catch (err) {
        alert('Error uploading profile picture.');
      }
    });

    document.getElementById('logout-btn')?.addEventListener('click', handleLogout);
    document.getElementById('switch-account-btn')?.addEventListener('click', () => {
      dropdownCard?.classList.remove('active');
      openAuthModal();
    });
  }

  function openAuthModal() {
    const appLayout = document.getElementById('app-layout');
    if (appLayout) appLayout.style.display = 'none';
    if (authModal) authModal.style.display = 'flex';
  }

  // closeAuthModal only works when user is authenticated
  function closeAuthModal() {
    if (!window._isAuthenticated) return;
    if (authModal) authModal.style.display = 'none';
    const appLayout = document.getElementById('app-layout');
    if (appLayout) appLayout.style.display = 'flex';
  }

  // Switch links inside the auth modal (no close — just tab switch)
  document.getElementById('switch-to-register-link')?.addEventListener('click', (e) => {
    e.preventDefault();
    tabAuthRegister?.click();
  });
  document.getElementById('switch-to-login-link')?.addEventListener('click', (e) => {
    e.preventDefault();
    tabAuthLogin?.click();
  });

  // Prevent closing auth modal by clicking backdrop when not authenticated
  authModal?.addEventListener('click', (e) => {
    if (e.target === authModal && window._isAuthenticated) closeAuthModal();
  });

  // Prevent ESC key from closing auth modal when not authenticated
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && authModal && authModal.style.display !== 'none' && !window._isAuthenticated) {
      e.stopImmediatePropagation();
    }
  }, true);

  async function handleLogout() {
    window._isAuthenticated = false;
    await fetch('/api/auth/logout', { method: 'POST' });
    renderGuestUser();
    openAuthModal();
  }

  // Auth Tabs inside Modal
  tabAuthLogin?.addEventListener('click', () => {
    tabAuthLogin.classList.add('active');
    tabAuthRegister.classList.remove('active');
    loginForm.style.display = 'block';
    registerForm.style.display = 'none';
    hideAuthAlert();
  });

  tabAuthRegister?.addEventListener('click', () => {
    tabAuthRegister.classList.add('active');
    tabAuthLogin.classList.remove('active');
    registerForm.style.display = 'block';
    loginForm.style.display = 'none';
    hideAuthAlert();
  });

  function showAuthAlert(msg, isError = true) {
    if (!authAlert) return;
    authAlert.textContent = msg;
    authAlert.className = `alert-message ${isError ? 'error' : 'success'}`;
  }

  function hideAuthAlert() {
    if (!authAlert) return;
    authAlert.className = 'alert-message';
    authAlert.textContent = '';
  }

  // Password Visibility Toggles
  document.querySelectorAll('.toggle-password-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const targetId = btn.getAttribute('data-target');
      const input = document.getElementById(targetId);
      const icon = btn.querySelector('i');
      if (!input || !icon) return;

      if (input.type === 'password') {
        input.type = 'text';
        icon.className = 'fa-solid fa-eye';
      } else {
        input.type = 'password';
        icon.className = 'fa-solid fa-eye-slash';
      }
    });
  });

  loginForm?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const email = document.getElementById('login-email').value;
    const password = document.getElementById('login-password').value;

    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      });
      const data = await res.json();
      if (data.success) {
        showAuthAlert('Login successful!', false);
        window._isAuthenticated = true;
        setTimeout(() => {
          hideAuthAlert();
          if (authModal) authModal.style.display = 'none';
          const appLayout = document.getElementById('app-layout');
          if (appLayout) appLayout.style.display = 'flex';
          renderLoggedInUser(data.user);
        }, 350);
      } else {
        showAuthAlert(data.message, true);
      }
    } catch (err) {
      showAuthAlert('Network error. Please try again.', true);
    }
  });

  registerForm?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const name = document.getElementById('reg-name').value.trim();
    const email = document.getElementById('reg-email').value.trim();
    const password = document.getElementById('reg-password').value;
    const confirm_password = document.getElementById('reg-confirm-password').value;

    if (!/^[A-Za-z\s]+$/.test(name)) {
      showAuthAlert("Name can only contain alphabetic letters and spaces.", true);
      return;
    }

    if (!/^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/.test(email)) {
      showAuthAlert("Please enter a valid email address.", true);
      return;
    }

    if (password.length < 6 || !/[A-Za-z]/.test(password) || !/[0-9!@#$%^&*]/.test(password)) {
      showAuthAlert("Password must be at least 6 characters and contain letters and numbers/symbols.", true);
      return;
    }

    if (password !== confirm_password) {
      showAuthAlert("Passwords do not match.", true);
      return;
    }

    try {
      const res = await fetch('/api/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, email, password, confirm_password })
      });
      const data = await res.json();
      if (data.success) {
        showAuthAlert('Account created successfully!', false);
        window._isAuthenticated = true;
        setTimeout(() => {
          hideAuthAlert();
          if (authModal) authModal.style.display = 'none';
          const appLayout = document.getElementById('app-layout');
          if (appLayout) appLayout.style.display = 'flex';
          renderLoggedInUser(data.user);
        }, 350);
      } else {
        showAuthAlert(data.message, true);
      }
    } catch (err) {
      showAuthAlert('Network error. Please try again.', true);
    }
  });

  // =========================================================================
  // 4. Notifications & System Settings
  // =========================================================================
  const notifBellBtn = document.getElementById('notif-bell-btn');
  const notifPopover = document.getElementById('notif-popover');
  notifBellBtn?.addEventListener('click', (e) => {
    e.stopPropagation();
    notifPopover?.classList.toggle('active');
  });

  document.addEventListener('click', (e) => {
    if (!notifPopover?.contains(e.target) && !notifBellBtn?.contains(e.target)) {
      notifPopover?.classList.remove('active');
    }
  });

  const sidebarSettingsBtn = document.getElementById('sidebar-settings-btn');
  const settingsModal = document.getElementById('settings-modal');
  const settingsCloseBtn = document.getElementById('settings-close-btn');

  sidebarSettingsBtn?.addEventListener('click', () => {
    if (settingsModal) settingsModal.style.display = 'flex';
  });
  settingsCloseBtn?.addEventListener('click', () => {
    if (settingsModal) settingsModal.style.display = 'none';
  });
  settingsModal?.addEventListener('click', (e) => {
    if (e.target === settingsModal) settingsModal.style.display = 'none';
  });

  document.getElementById('modal-switch-account-btn')?.addEventListener('click', () => {
    if (settingsModal) settingsModal.style.display = 'none';
    openAuthModal();
  });
  document.getElementById('modal-logout-btn')?.addEventListener('click', () => {
    if (settingsModal) settingsModal.style.display = 'none';
    handleLogout();
  });

  // =========================================================================
  // Theme Switcher (SaaS Light Grid <-> Dark Blueprint)
  // =========================================================================
  const themeToggleBtn = document.getElementById('theme-toggle-btn');
  const topbarThemeToggleBtn = document.getElementById('topbar-theme-toggle-btn');
  const themeBtnIcon = document.getElementById('theme-btn-icon');
  const topbarThemeIcon = document.getElementById('topbar-theme-icon');

  function applyTheme(theme) {
    if (theme === 'dark') {
      document.documentElement.setAttribute('data-theme', 'dark');
      localStorage.setItem('clickbait_theme', 'dark');
      if (themeBtnIcon) themeBtnIcon.className = 'fa-solid fa-sun';
      if (topbarThemeIcon) topbarThemeIcon.className = 'fa-solid fa-sun';
      if (themeToggleBtn) themeToggleBtn.title = 'Switch to SaaS Light Grid';
      if (topbarThemeToggleBtn) topbarThemeToggleBtn.title = 'Switch to SaaS Light Grid';
    } else {
      document.documentElement.removeAttribute('data-theme');
      localStorage.setItem('clickbait_theme', 'light');
      if (themeBtnIcon) themeBtnIcon.className = 'fa-solid fa-moon';
      if (topbarThemeIcon) topbarThemeIcon.className = 'fa-solid fa-moon';
      if (themeToggleBtn) themeToggleBtn.title = 'Switch to Dark Blueprint';
      if (topbarThemeToggleBtn) topbarThemeToggleBtn.title = 'Switch to Dark Blueprint';
    }
  }

  function toggleTheme() {
    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    applyTheme(isDark ? 'light' : 'dark');
  }

  themeToggleBtn?.addEventListener('click', toggleTheme);
  topbarThemeToggleBtn?.addEventListener('click', toggleTheme);

  // Synchronize active theme from storage or default
  const savedTheme = localStorage.getItem('clickbait_theme') || 'light';
  applyTheme(savedTheme);

  // Global Search Input (Switches to History and filters)
  const topbarSearchInput = document.getElementById('topbar-search-input');
  topbarSearchInput?.addEventListener('input', () => {
    const query = topbarSearchInput.value.trim();
    if (query) {
      const historyTabBtn = document.querySelector('.tab-btn[data-tab="history"]');
      if (historyTabBtn && !historyTabBtn.classList.contains('active')) {
        historyTabBtn.click();
      }
      const historySearch = document.getElementById('history-search');
      if (historySearch) {
        historySearch.value = query;
        loadHistory();
      }
    }
  });

  // =========================================================================
  // 4b. Sidebar Collapse / Expand Toggle
  // =========================================================================
  const sidebarToggleBtn = document.getElementById('sidebar-toggle-btn');
  const appSidebar = document.getElementById('app-sidebar');

  sidebarToggleBtn?.addEventListener('click', () => {
    if (!appSidebar) return;
    appSidebar.classList.toggle('sidebar-collapsed');
    const isCollapsed = appSidebar.classList.contains('sidebar-collapsed');
    localStorage.setItem('clickbait_sidebar_collapsed', isCollapsed ? '1' : '0');
  });

  // Restore sidebar state from localStorage
  (function () {
    const collapsed = localStorage.getItem('clickbait_sidebar_collapsed');
    if (collapsed === '1' && appSidebar) {
      appSidebar.classList.add('sidebar-collapsed');
    }
  })();

  // =========================================================================
  // 5. Prediction Execution (Headline Analysis & Live URL Analysis)
  // =========================================================================
  const analyzeBtn = document.getElementById('analyze-btn');
  const analyzeUrlBtn = document.getElementById('analyze-url-btn');
  const resultContainer = document.getElementById('result-container');
  const resultPlaceholder = document.getElementById('result-placeholder');
  const resetResultBtn = document.getElementById('reset-result-btn');
  const topbarResetBtn = document.getElementById('topbar-reset-btn');

  function doResetResult() {
    if (resultContainer) resultContainer.style.display = 'none';
    if (topbarResetBtn) topbarResetBtn.style.display = 'none';
    if (resultPlaceholder) {
      resultPlaceholder.style.display = 'block';
      resultPlaceholder.classList.remove('is-collapsed');
      const badge = document.getElementById('badge-collapsed-engine');
      if (badge) badge.style.display = 'none';
      const engBtn = document.getElementById('collapse-engine-btn');
      if (engBtn) {
        engBtn.setAttribute('aria-expanded', 'true');
        engBtn.title = 'Collapse panel';
      }
    }
    if (headlineInput) {
      headlineInput.value = '';
      updateCharCount(0);
    }
    if (urlInput) urlInput.value = '';
  }

  resetResultBtn?.addEventListener('click', doResetResult);
  topbarResetBtn?.addEventListener('click', doResetResult);

  analyzeBtn?.addEventListener('click', async () => {
    const text = headlineInput.value.trim();

    if (!text) {
      alert('Please enter headline text before analyzing.');
      return;
    }

    if (/^(http:\/\/|https:\/\/|www\.)/i.test(text)) {
      alert('Headline/Text mode only accepts text input. For webpage links, please switch to "Live URL Analysis" mode.');
      activateUrlMode();
      urlInput.value = text;
      return;
    }

    analyzeBtn.disabled = true;
    analyzeBtn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> <span>Analyzing Headline...</span>`;

    try {
      const res = await fetch('/api/predict', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ headline: text })
      });
      const data = await res.json();
      if (data.success) {
        renderPredictionResult(data.result, null);
      } else {
        alert(data.message);
      }
    } catch (err) {
      alert('Failed to process prediction. Please try again.');
    } finally {
      analyzeBtn.disabled = false;
      analyzeBtn.innerHTML = `<i class="fa-solid fa-magnifying-glass"></i> <span>Analyze Headline</span>`;
    }
  });

  analyzeUrlBtn?.addEventListener('click', async () => {
    const urlVal = urlInput.value.trim();

    if (!urlVal) {
      alert('Please enter a webpage URL before analyzing.');
      return;
    }

    if (!/^(http:\/\/|https:\/\/)/i.test(urlVal)) {
      alert('URL Analysis mode only accepts valid web URLs starting with http:// or https:// (e.g. https://www.bbc.com/news/...).');
      return;
    }

    analyzeUrlBtn.disabled = true;
    analyzeUrlBtn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> <span>Fetching & Analyzing Webpage...</span>`;

    try {
      const res = await fetch('/api/analyze-url', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: urlVal })
      });
      const data = await res.json();
      if (data.success) {
        renderPredictionResult(data.result, data.source_url, data.body_preview, data.word_count, data.full_body_text);
      } else {
        alert(data.message);
      }
    } catch (err) {
      alert('Unable to analyze this URL. Check the web connection and URL format.');
    } finally {
      analyzeUrlBtn.disabled = false;
      analyzeUrlBtn.innerHTML = `<i class="fa-solid fa-globe"></i> <span>Analyze Webpage</span>`;
    }
  });

  function renderPredictionResult(res, sourceUrl, bodyPreview = null, wordCount = 0, fullBodyText = null) {
    if (resultPlaceholder) resultPlaceholder.style.display = 'none';
    if (topbarResetBtn) topbarResetBtn.style.display = 'inline-flex';
    if (resultContainer) {
      resultContainer.style.display = 'block';
      resultContainer.classList.remove('is-collapsed');
      const badge = document.getElementById('badge-collapsed-result');
      if (badge) badge.style.display = 'none';
      const resBtn = document.getElementById('collapse-result-btn');
      if (resBtn) {
        resBtn.setAttribute('aria-expanded', 'true');
        resBtn.title = 'Collapse panel';
      }
    }

    const resUrlBanner = document.getElementById('res-url-banner');
    const resUrlLink = document.getElementById('res-url-link');
    const resTypeLabel = document.getElementById('res-type-label');
    const resBodyContainer = document.getElementById('res-body-container');
    const resBodyText = document.getElementById('res-body-text');
    const resWordCount = document.getElementById('res-word-count');

    if (sourceUrl) {
      if (resUrlBanner) resUrlBanner.style.display = 'flex';
      if (resUrlLink) {
        resUrlLink.href = sourceUrl;
        resUrlLink.textContent = sourceUrl;
      }
      if (resTypeLabel) resTypeLabel.textContent = 'Extracted Webpage Article & Headline Analysis';

      const displayText = fullBodyText || bodyPreview;
      if (displayText && resBodyContainer && resBodyText) {
        resBodyContainer.style.display = 'block';
        if (resWordCount) resWordCount.textContent = wordCount || '0';

        const toggleBtn = document.getElementById('toggle-body-btn');
        if (displayText.length > 200) {
          const truncated = displayText.slice(0, 200) + '...';
          resBodyText.textContent = truncated;
          if (toggleBtn) {
            toggleBtn.style.display = 'inline-block';
            toggleBtn.innerHTML = `<i class="fa-solid fa-book-open"></i> Read More`;
            let isExpanded = false;
            toggleBtn.onclick = () => {
              isExpanded = !isExpanded;
              if (isExpanded) {
                resBodyText.textContent = displayText;
                toggleBtn.innerHTML = `<i class="fa-solid fa-angle-up"></i> Show Less`;
              } else {
                resBodyText.textContent = truncated;
                toggleBtn.innerHTML = `<i class="fa-solid fa-book-open"></i> Read More`;
              }
            };
          }
        } else {
          resBodyText.textContent = displayText;
          if (toggleBtn) toggleBtn.style.display = 'none';
        }
      } else if (resBodyContainer) {
        resBodyContainer.style.display = 'none';
      }
    } else {
      if (resUrlBanner) resUrlBanner.style.display = 'none';
      if (resBodyContainer) resBodyContainer.style.display = 'none';
      if (resTypeLabel) resTypeLabel.textContent = 'Headline Outcome';
    }

    const isClickbait = res.prediction === 'Clickbait';

    // Headline Preview & Expansion
    const headlinePreview = document.getElementById('res-headline-preview');
    const toggleHeadlineBtn = document.getElementById('toggle-headline-btn');
    const fullHeadline = res.headline || '';

    if (headlinePreview) {
      if (fullHeadline.length > 120) {
        const truncatedHeadline = fullHeadline.slice(0, 120) + '...';
        headlinePreview.textContent = `"${truncatedHeadline}"`;
        if (toggleHeadlineBtn) {
          toggleHeadlineBtn.style.display = 'inline-block';
          toggleHeadlineBtn.innerHTML = `<i class="fa-solid fa-book-open"></i> Read More`;
          let isHeadlineExpanded = false;
          toggleHeadlineBtn.onclick = () => {
            isHeadlineExpanded = !isHeadlineExpanded;
            if (isHeadlineExpanded) {
              headlinePreview.textContent = `"${fullHeadline}"`;
              toggleHeadlineBtn.innerHTML = `<i class="fa-solid fa-angle-up"></i> Show Less`;
            } else {
              headlinePreview.textContent = `"${truncatedHeadline}"`;
              toggleHeadlineBtn.innerHTML = `<i class="fa-solid fa-book-open"></i> Read More`;
            }
          };
        }
      } else {
        headlinePreview.textContent = `"${fullHeadline}"`;
        if (toggleHeadlineBtn) toggleHeadlineBtn.style.display = 'none';
      }
    }

    // Outcome Badge
    const badge = document.getElementById('res-badge');
    if (badge) {
      badge.className = `result-badge ${isClickbait ? 'clickbait' : 'non-clickbait'}`;
      badge.innerHTML = isClickbait
        ? `<i class="fa-solid fa-triangle-exclamation"></i> Clickbait Style`
        : `<i class="fa-solid fa-circle-check"></i> Objective Style`;
    }

    // Engine 2: Real-time Factual Authenticity Rendering
    const auth = res.authenticity || {};
    const authBadge = document.getElementById('res-auth-badge');
    const authStatus = auth.status || 'UNVERIFIED';
    let authBadgeClass = 'auth-unverified';
    let authIcon = 'fa-triangle-exclamation';

    if (authStatus.includes('VERIFIED')) {
      authBadgeClass = 'auth-verified';
      authIcon = 'fa-circle-check';
    } else if (authStatus.includes('DEBUNKED')) {
      authBadgeClass = 'auth-debunked';
      authIcon = 'fa-circle-xmark';
    } else if (authStatus.includes('DEVELOPING') || authStatus.includes('CORROBORATED')) {
      authBadgeClass = 'auth-developing';
      authIcon = 'fa-clock';
    } else if (authStatus.includes('SATIRE')) {
      authBadgeClass = 'auth-satire';
      authIcon = 'fa-masks-theater';
    } else if (authStatus.includes('OPINION')) {
      authBadgeClass = 'auth-opinion';
      authIcon = 'fa-comment-dots';
    }

    if (authBadge) {
      authBadge.className = `result-badge ${authBadgeClass}`;
      authBadge.innerHTML = `<i class="fa-solid ${authIcon}"></i> ${authStatus}`;
    }

    const authClaimType = document.getElementById('res-auth-claim-type');
    if (authClaimType) {
      authClaimType.textContent = auth.claim_type || 'Factual News Assessment';
    }

    const authConsensus = document.getElementById('res-auth-consensus');
    if (authConsensus) {
      authConsensus.innerHTML = `<i class="fa-solid fa-newspaper"></i> ${auth.consensus_label || 'Consensus Evaluated'}`;
    }

    const authExplanation = document.getElementById('res-auth-explanation');
    if (authExplanation) {
      authExplanation.textContent = auth.explanation || 'Authenticity evaluation completed.';
    }

    const sourcesListEl = document.getElementById('res-auth-sources-list');
    const evidenceBox = document.getElementById('res-auth-evidence-container');
    if (sourcesListEl) {
      sourcesListEl.innerHTML = '';
      const sources = auth.evidence_sources || [];
      if (sources.length > 0) {
        if (evidenceBox) evidenceBox.style.display = 'block';
        sources.forEach(s => {
          const a = document.createElement('a');
          a.className = 'evidence-item-link';
          a.href = s.url || '#';
          a.target = '_blank';
          a.rel = 'noopener noreferrer';
          a.title = `View report from ${s.source}`;
          a.innerHTML = `
            <span class="evidence-item-title">${s.title}</span>
            <span class="evidence-item-source"><i class="fa-solid fa-arrow-up-right-from-square"></i> ${s.source}</span>
          `;
          sourcesListEl.appendChild(a);
        });
      } else {
        if (evidenceBox) evidenceBox.style.display = 'none';
      }
    }

    // Likelihood Dual Progress Bars
    let rawCb = res.prob_clickbait !== undefined ? res.prob_clickbait : (isClickbait ? res.confidence : (100 - res.confidence));
    if (rawCb <= 1.0 && rawCb >= 0) {
      rawCb = rawCb * 100;
    }
    const cbVal = Math.min(100, Math.max(0, parseFloat(rawCb) || 0));
    const nonCbVal = Math.min(100, Math.max(0, 100 - cbVal));

    const probCb = cbVal.toFixed(1);
    const probNonCb = nonCbVal.toFixed(1);

    const cbText = document.getElementById('res-prob-cb-text');
    const nonCbText = document.getElementById('res-prob-non-cb-text');
    if (cbText) cbText.textContent = `${probCb}%`;
    if (nonCbText) nonCbText.textContent = `${probNonCb}%`;

    const probCbBar = document.getElementById('res-prob-cb-bar');
    const probNonCbBar = document.getElementById('res-prob-non-cb-bar');
    setTimeout(() => {
      if (probCbBar) probCbBar.style.width = `${probCb}%`;
      if (probNonCbBar) probNonCbBar.style.width = `${probNonCb}%`;
    }, 50);

    // Classification Factors List
    const reasonsContainer = document.getElementById('res-reasons-container');
    const reasonsList = document.getElementById('res-reasons-list');
    if (reasonsList) reasonsList.innerHTML = '';

    const genericFallbacks = [
      'evaluated using vector tf-idf',
      'statistical feature weighting matches',
      'text structure adheres to standard journal'
    ];

    const specificReasons = (res.reasons || []).filter(r => {
      const lower = r.toLowerCase();
      return !genericFallbacks.some(fb => lower.includes(fb));
    });

    if (specificReasons.length > 0 && reasonsContainer && reasonsList) {
      reasonsContainer.style.display = 'block';
      specificReasons.forEach(r => {
        const li = document.createElement('li');
        li.textContent = r;
        reasonsList.appendChild(li);
      });
    } else if (reasonsContainer) {
      reasonsContainer.style.display = 'none';
    }

    // Influential XAI Keywords
    currentXaiWords = res.top_words || [];
    const limitSelect = document.getElementById('xai-limit-select');
    const selectedLimit = limitSelect ? parseInt(limitSelect.value) : 6;
    renderXaiWords(selectedLimit);

    // Linguistic Signals
    const lingBox = document.getElementById('linguistic-box');
    const lf = res.linguistic_features || {};
    if (lingBox) {
      lingBox.innerHTML = `
        <div style="font-size: 11.5px; font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px; width: 100%;">
          Linguistic Signals & Structure:
        </div>
        <div style="display: flex; gap: 6px; flex-wrap: wrap;">
          ${lf.sensational_words?.length ? `<span class="ling-tag" style="color: #d97706; background: #fef3c7;"><i class="fa-solid fa-bolt"></i> Sensational Terms: ${lf.sensational_words.join(', ')}</span>` : ''}
          ${lf.hyperbolic_expressions?.length ? `<span class="ling-tag" style="color: #dc2626; background: #fee2e2;"><i class="fa-solid fa-fire"></i> Hyperbolic Expression</span>` : ''}
          ${lf.has_ai_signal ? `<span class="ling-tag" style="color: #7c3aed; background: #ede9fe;"><i class="fa-solid fa-robot"></i> Synthetic Writing Pattern</span>` : ''}
          ${lf.has_exclamation ? `<span class="ling-tag" style="color: #0284c7; background: #e0f2fe;"><i class="fa-solid fa-exclamation"></i> Exclamation Signal</span>` : ''}
          ${!lf.sensational_words?.length && !lf.hyperbolic_expressions?.length && !lf.has_ai_signal && !lf.has_exclamation ? `<span class="ling-tag"><i class="fa-solid fa-check"></i> Standard objective news syntax</span>` : ''}
        </div>
      `;
    }
  }

  let currentXaiWords = [];
  const xaiLimitSelect = document.getElementById('xai-limit-select');
  xaiLimitSelect?.addEventListener('change', (e) => {
    const limit = parseInt(e.target.value) || 6;
    renderXaiWords(limit);
  });

  function renderXaiWords(limit) {
    const xaiBox = document.getElementById('res-xai-words');
    if (!xaiBox) return;
    xaiBox.innerHTML = '';

    const wordsToDisplay = currentXaiWords.slice(0, limit);

    if (wordsToDisplay && wordsToDisplay.length > 0) {
      wordsToDisplay.forEach(w => {
        const span = document.createElement('span');
        const isCb = w.impact === 'Clickbait';
        span.className = `xai-chip ${isCb ? 'clickbait-word' : 'nonclickbait-word'}`;
        span.innerHTML = `${w.word} <span class="xai-weight">(${isCb ? '+' : '-'}${w.weight})</span>`;
        xaiBox.appendChild(span);
      });
    } else {
      xaiBox.innerHTML = `<span style="font-size: 13px; color: #94a3b8;">No distinct high-weight words found.</span>`;
    }
  }

  // =========================================================================
  // 6. ML Studio & Adaptive Retraining
  // =========================================================================
  async function loadMetrics() {
    try {
      const res = await fetch('/api/model/metrics');
      const data = await res.json();
      if (data.success && data.metrics) {
        const m = data.metrics;
        document.getElementById('metric-accuracy').textContent = `${(m.accuracy * 100).toFixed(1)}%`;
        document.getElementById('metric-precision').textContent = `${(m.precision * 100).toFixed(1)}%`;
        document.getElementById('metric-recall').textContent = `${(m.recall * 100).toFixed(1)}%`;
        document.getElementById('metric-f1').textContent = `${(m.f1_score * 100).toFixed(1)}%`;
      }
    } catch (e) {
      console.error(e);
    }
  }

  const dropZone = document.getElementById('drop-zone');
  const datasetFile = document.getElementById('dataset-file');
  const uploadForm = document.getElementById('upload-form');
  const fileInfo = document.getElementById('file-info');
  const fileNameText = document.getElementById('file-name-text');
  const retrainBtn = document.getElementById('retrain-btn');
  const trainStatus = document.getElementById('train-status');
  let selectedUploadedFile = null;

  dropZone?.addEventListener('click', () => datasetFile.click());

  datasetFile?.addEventListener('change', () => {
    if (datasetFile.files.length > 0) {
      fileInfo.style.display = 'flex';
      fileNameText.textContent = datasetFile.files[0].name;
    }
  });

  uploadForm?.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (!datasetFile.files.length) {
      alert('Please select a CSV file to upload.');
      return;
    }

    const formData = new FormData();
    formData.append('file', datasetFile.files[0]);

    try {
      const res = await fetch('/api/dataset/upload', {
        method: 'POST',
        body: formData
      });
      const data = await res.json();
      if (data.success) {
        alert(data.message);
        selectedUploadedFile = data.filename;
        document.getElementById('active-dataset-text').textContent = `${data.filename} (${data.row_count.toLocaleString()} rows)`;
      } else {
        alert(data.message);
      }
    } catch (err) {
      alert('Upload failed.');
    }
  });

  retrainBtn?.addEventListener('click', async () => {
    retrainBtn.disabled = true;
    retrainBtn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Retraining Model...`;
    trainStatus.style.display = 'block';
    trainStatus.className = 'train-status-msg';
    trainStatus.textContent = 'Processing dataset and vectorizing features...';

    try {
      const res = await fetch('/api/model/train', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filename: selectedUploadedFile })
      });
      const data = await res.json();
      if (data.success) {
        trainStatus.className = 'train-status-msg success';
        trainStatus.textContent = 'Model retrained successfully!';
        loadMetrics();
      } else {
        trainStatus.className = 'train-status-msg error';
        trainStatus.textContent = `Error: ${data.message}`;
      }
    } catch (err) {
      trainStatus.className = 'train-status-msg error';
      trainStatus.textContent = 'Retraining failed.';
    } finally {
      retrainBtn.disabled = false;
      retrainBtn.innerHTML = `<i class="fa-solid fa-arrows-rotate"></i> Retrain Model Now`;
    }
  });

  // =========================================================================
  // 7. Detection History Log
  // =========================================================================
  const historySearch = document.getElementById('history-search');
  const thFilterSource = document.getElementById('th-filter-source');
  const thFilterStyle = document.getElementById('th-filter-style');
  const thFilterAuth = document.getElementById('th-filter-auth');
  const historyTbody = document.getElementById('history-tbody');
  const clearHistoryBtn = document.getElementById('clear-history-btn');

  function updateFilterActiveState(el) {
    if (!el) return;
    if (el.value && el.value !== 'All') {
      el.classList.add('is-active');
    } else {
      el.classList.remove('is-active');
    }
  }

  historySearch?.addEventListener('input', debounce(loadHistory, 300));
  thFilterSource?.addEventListener('change', () => {
    updateFilterActiveState(thFilterSource);
    loadHistory();
  });
  thFilterStyle?.addEventListener('change', () => {
    updateFilterActiveState(thFilterStyle);
    loadHistory();
  });
  thFilterAuth?.addEventListener('change', () => {
    updateFilterActiveState(thFilterAuth);
    loadHistory();
  });

  async function loadHistory() {
    const search = historySearch ? historySearch.value : '';
    const filter = thFilterStyle ? thFilterStyle.value : 'All';
    const sourceType = thFilterSource ? thFilterSource.value : 'All';
    const authFilter = thFilterAuth ? thFilterAuth.value : 'All';

    try {
      const res = await fetch(`/api/history?search=${encodeURIComponent(search)}&filter=${encodeURIComponent(filter)}&source_type=${encodeURIComponent(sourceType)}&auth_filter=${encodeURIComponent(authFilter)}`);
      const data = await res.json();
      if (data.success) {
        renderHistoryTable(data.history);
      }
    } catch (e) {
      console.error(e);
    }
  }

  clearHistoryBtn?.addEventListener('click', async () => {
    if (!confirm('Are you sure you want to delete all history records?')) return;
    try {
      const res = await fetch('/api/history/clear', { method: 'POST' });
      const data = await res.json();
      if (data.success) {
        loadHistory();
      } else {
        alert(data.message);
      }
    } catch (e) {
      alert('Failed to clear history records.');
    }
  });

  function initColResize() {
    const table = document.querySelector('#tab-history .data-table');
    if (!table) return;
    const ths = table.querySelectorAll('thead th');
    ths.forEach((th) => {
      // Avoid double-init
      if (th.querySelector('.col-resizer')) return;
      th.style.position = 'relative';
      const resizer = document.createElement('div');
      resizer.className = 'col-resizer';
      resizer.style.cssText = 'position:absolute;right:0;top:0;bottom:0;width:5px;cursor:col-resize;user-select:none;z-index:2;background:transparent;';
      th.appendChild(resizer);

      let startX, startW;
      resizer.addEventListener('mousedown', (e) => {
        startX = e.clientX;
        startW = th.offsetWidth;
        document.body.style.cursor = 'col-resize';
        document.body.style.userSelect = 'none';
        const onMove = (ev) => {
          const w = Math.max(50, startW + ev.clientX - startX);
          th.style.width = w + 'px';
          th.style.minWidth = w + 'px';
        };
        const onUp = () => {
          document.body.style.cursor = '';
          document.body.style.userSelect = '';
          document.removeEventListener('mousemove', onMove);
          document.removeEventListener('mouseup', onUp);
        };
        document.addEventListener('mousemove', onMove);
        document.addEventListener('mouseup', onUp);
        e.preventDefault();
      });

      resizer.addEventListener('mouseenter', () => { resizer.style.background = '#c7d2fe'; });
      resizer.addEventListener('mouseleave', () => { if (document.body.style.cursor !== 'col-resize') resizer.style.background = 'transparent'; });
    });
  }

  function renderHistoryTable(records) {
    if (!historyTbody) return;
    historyTbody.innerHTML = '';

    if (!records || records.length === 0) {
      historyTbody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: #94a3b8; padding: 2.5rem; font-size: 13px;"><i class="fa-solid fa-inbox" style="margin-right:6px;"></i>${window._isAuthenticated ? 'No detection records found.' : 'Sign in to view your history.'}</td></tr>`;
      return;
    }

    records.forEach(r => {
      const tr = document.createElement('tr');
      const isCb = r.prediction === 'Clickbait';
      const isUrl = r.source_type === 'url';

      // Top 3 XAI words — compact chips
      const xaiChips = (r.top_words || []).slice(0, 3).map(w =>
        `<span class="hist-xai-chip ${w.impact === 'Clickbait' ? 'cb' : 'ncb'}">${w.word}</span>`
      ).join('');

      const typeBadge = isUrl
        ? `<span class="hist-type-badge url"><i class="fa-solid fa-globe"></i> URL</span>`
        : `<span class="hist-type-badge text"><i class="fa-solid fa-align-left"></i> Text</span>`;

      // Headline cell - truncate long URLs cleanly
      const shortUrl = isUrl && r.source_url ? (r.source_url.length > 45 ? r.source_url.slice(0,45)+'…' : r.source_url) : '';
      const headlineCell = `
        <div class="hist-headline-cell">
          <div class="hist-headline-text">${r.headline || ''}</div>
          ${isUrl && r.source_url ? `<a href="${r.source_url}" target="_blank" class="hist-url-link">${shortUrl}</a>` : ''}
        </div>`;

      const authStatus = r.authenticity_status || 'Unverified';
      let authClass = 'auth-unverified';
      if (authStatus.includes('VERIFIED')) authClass = 'auth-verified';
      else if (authStatus.includes('DEBUNKED')) authClass = 'auth-debunked';
      else if (authStatus.includes('DEVELOPING') || authStatus.includes('CORROBORATED')) authClass = 'auth-developing';
      else if (authStatus.includes('SATIRE')) authClass = 'auth-satire';
      else if (authStatus.includes('OPINION')) authClass = 'auth-opinion';

      const authBadge = `<span class="result-badge ${authClass} hist-auth-badge">${authStatus}</span>`;
      const styleBadge = `<span class="result-badge ${isCb ? 'clickbait' : 'non-clickbait'} hist-style-badge">${r.prediction} <span class="hist-conf">${r.confidence}%</span></span>`;

      tr.innerHTML = `
        <td class="hist-td-date">${r.created_at || 'Just now'}</td>
        <td class="hist-td-source">${typeBadge}</td>
        <td class="hist-td-headline">${headlineCell}</td>
        <td class="hist-td-style">${styleBadge}</td>
        <td class="hist-td-auth">${authBadge}</td>
        <td class="hist-td-xai">${xaiChips || '<span class="hist-empty">—</span>'}</td>
        <td class="hist-td-action">
          <button type="button" class="delete-row-btn" data-id="${r.id}" title="Delete record">
            <i class="fa-solid fa-trash-can"></i>
          </button>
        </td>
      `;
      historyTbody.appendChild(tr);
    });

    document.querySelectorAll('.delete-row-btn').forEach(btn => {
      btn.addEventListener('click', async () => {
        const rowId = btn.getAttribute('data-id');
        if (!rowId) return;
        try {
          const res = await fetch(`/api/history/delete/${rowId}`, { method: 'POST' });
          const data = await res.json();
          if (data.success) {
            loadHistory();
          } else {
            alert(data.message);
          }
        } catch (err) {
          alert('Failed to delete history record.');
        }
      });
    });

    // Init column resizers after each render
    initColResize();
  }

  // =========================================================================
  // 8. Word Cloud Generator
  // =========================================================================
  const generateWordCloudBtn = document.getElementById('generate-wordcloud-btn');
  const wordcloudLimitSelect = document.getElementById('wordcloud-limit');
  const cbCloudBox = document.getElementById('clickbait-wordcloud');
  const nonCbCloudBox = document.getElementById('nonclickbait-wordcloud');

  generateWordCloudBtn?.addEventListener('click', loadWordCloud);
  wordcloudLimitSelect?.addEventListener('change', loadWordCloud);

  async function loadWordCloud() {
    const limit = wordcloudLimitSelect?.value || 50;

    if (generateWordCloudBtn) {
      generateWordCloudBtn.disabled = true;
      generateWordCloudBtn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Generating...`;
    }

    try {
      const res = await fetch(`/api/wordcloud?limit=${limit}`);
      const result = await res.json();

      if (result.success && result.data) {
        const d = result.data;
        const cbCount = document.getElementById('cb-sample-count');
        const nonCbCount = document.getElementById('noncb-sample-count');
        if (cbCount) cbCount.textContent = `${d.total_clickbait_samples.toLocaleString()} Clickbait Headlines`;
        if (nonCbCount) nonCbCount.textContent = `${d.total_non_clickbait_samples.toLocaleString()} Non-Clickbait Headlines`;

        renderCloudTags(cbCloudBox, d.clickbait_words, 'clickbait-tag');
        renderCloudTags(nonCbCloudBox, d.non_clickbait_words, 'nonclickbait-tag');
      } else {
        alert(result.message || 'Failed to generate word clouds.');
      }
    } catch (err) {
      console.error(err);
      alert('Error fetching word cloud data.');
    } finally {
      if (generateWordCloudBtn) {
        generateWordCloudBtn.disabled = false;
        generateWordCloudBtn.innerHTML = `<i class="fa-solid fa-arrows-rotate"></i> Generate Word Clouds`;
      }
    }
  }

  function renderCloudTags(container, words, tagClass) {
    if (!container) return;
    container.innerHTML = '';

    if (!words || words.length === 0) {
      container.innerHTML = `<span style="color: #94a3b8; font-size: 14px;">No word data available.</span>`;
      return;
    }

    words.forEach(w => {
      const tag = document.createElement('span');
      const fontSize = (0.85 + w.weight * 1.3).toFixed(2);
      const opacity = (0.65 + w.weight * 0.35).toFixed(2);

      tag.className = `example-chip ${tagClass}`;
      tag.style.fontSize = `${fontSize}rem`;
      tag.style.opacity = opacity;
      tag.style.fontWeight = '600';
      tag.title = `Word: "${w.word}" | Frequency: ${w.count} occurrences`;
      tag.innerHTML = `${w.word} <small style="font-size: 0.65em; opacity: 0.75;">(${w.count})</small>`;

      container.appendChild(tag);
    });
  }

  function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
      const later = () => {
        clearTimeout(timeout);
        func(...args);
      };
      clearTimeout(timeout);
      timeout = setTimeout(later, wait);
    };
  }

  // =========================================================================
  // 9. Vertical Card Layout — Collapsible Panel Handlers
  // =========================================================================
  function setupCollapsibleCard(cardId, headerId, btnId, badgeId) {
    const card = document.getElementById(cardId);
    const header = document.getElementById(headerId);
    const btn = document.getElementById(btnId);
    const badge = document.getElementById(badgeId);

    function toggleCard(e) {
      if (!card) return;
      // Do not toggle if user clicked on form inputs, textareas, selects, or links
      if (e && e.target && e.target.closest('input, textarea, select, a, .seg-btn, .gradient-action-btn') && !e.target.closest('.card-collapse-toggle-btn')) {
        return;
      }
      const isCollapsed = card.classList.toggle('is-collapsed');
      if (badge) badge.style.display = isCollapsed ? 'inline-flex' : 'none';
      if (btn) {
        btn.setAttribute('aria-expanded', !isCollapsed);
        btn.title = isCollapsed ? 'Expand panel' : 'Collapse panel';
      }
    }

    btn?.addEventListener('click', (e) => {
      e.stopPropagation();
      toggleCard(e);
    });

    header?.addEventListener('click', toggleCard);
  }

  // Setup Card 1 (Input Card)
  setupCollapsibleCard('panel-input', 'header-input-card', 'collapse-input-btn', 'badge-collapsed-input');

  // Setup Card 2 State A (Engine Placeholder)
  setupCollapsibleCard('result-placeholder', 'header-engine-card', 'collapse-engine-btn', 'badge-collapsed-engine');

  // Setup Card 2 State B (Prediction Result)
  setupCollapsibleCard('result-container', 'header-result-card', 'collapse-result-btn', 'badge-collapsed-result');

});
