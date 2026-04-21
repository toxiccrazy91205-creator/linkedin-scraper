/* ==========================================================================
   LinkedIn Scraper — Frontend Application
   ========================================================================== */

(function () {
    'use strict';

    // -----------------------------------------------------------------------
    // State
    // -----------------------------------------------------------------------
    const state = {
        sessionActive: false,
        loading: {},          // { tabName: bool }
        lastResults: {},      // { tabName: data }
    };

    // -----------------------------------------------------------------------
    // DOM References
    // -----------------------------------------------------------------------
    const $ = (sel) => document.querySelector(sel);
    const $$ = (sel) => document.querySelectorAll(sel);

    // -----------------------------------------------------------------------
    // Theme Management
    // -----------------------------------------------------------------------
    function initTheme() {
        const saved = localStorage.getItem('linkedin-scraper-theme');
        const theme = saved || 'dark';
        document.documentElement.setAttribute('data-theme', theme);

        $('#theme-toggle').addEventListener('click', () => {
            const current = document.documentElement.getAttribute('data-theme');
            const next = current === 'dark' ? 'light' : 'dark';
            document.documentElement.setAttribute('data-theme', next);
            localStorage.setItem('linkedin-scraper-theme', next);
        });
    }

    // -----------------------------------------------------------------------
    // Tab Navigation
    // -----------------------------------------------------------------------
    function initTabs() {
        const tabs = $$('.tab');
        tabs.forEach(tab => {
            tab.addEventListener('click', () => {
                const target = tab.dataset.tab;
                switchTab(target);
            });
        });

        // Handle "go to tab" links
        document.addEventListener('click', (e) => {
            const link = e.target.closest('[data-goto-tab]');
            if (link) {
                e.preventDefault();
                switchTab(link.dataset.gotoTab);
            }
        });
    }

    function switchTab(tabName) {
        $$('.tab').forEach(t => {
            t.classList.toggle('active', t.dataset.tab === tabName);
            t.setAttribute('aria-selected', t.dataset.tab === tabName);
        });
        $$('.panel').forEach(p => {
            p.classList.toggle('active', p.id === `panel-${tabName}`);
        });
    }

    // -----------------------------------------------------------------------
    // Disclaimer
    // -----------------------------------------------------------------------
    function initDisclaimer() {
        const dismissed = localStorage.getItem('linkedin-scraper-disclaimer');
        if (dismissed) {
            $('#disclaimer').classList.add('hidden');
        }
        $('#disclaimer-close').addEventListener('click', () => {
            $('#disclaimer').classList.add('hidden');
            localStorage.setItem('linkedin-scraper-disclaimer', 'true');
        });
    }

    // -----------------------------------------------------------------------
    // Toast Notifications
    // -----------------------------------------------------------------------
    function showToast(message, type = 'info', duration = 5000) {
        const container = $('#toast-container');
        const icons = {
            success: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>',
            error: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>',
            warning: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>',
            info: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>',
        };

        const toast = document.createElement('div');
        toast.className = `toast toast--${type}`;
        toast.innerHTML = `
            <span class="toast__icon">${icons[type] || icons.info}</span>
            <span class="toast__body">${escapeHtml(message)}</span>
            <button class="toast__close" aria-label="Dismiss">&times;</button>
        `;

        toast.querySelector('.toast__close').addEventListener('click', () => {
            toast.style.animation = 'slideIn 0.2s ease reverse';
            setTimeout(() => toast.remove(), 200);
        });

        container.appendChild(toast);

        if (duration > 0) {
            setTimeout(() => {
                if (toast.parentNode) {
                    toast.style.animation = 'slideIn 0.2s ease reverse';
                    setTimeout(() => toast.remove(), 200);
                }
            }, duration);
        }
    }

    // -----------------------------------------------------------------------
    // API Calls
    // -----------------------------------------------------------------------
    async function apiCall(endpoint, data = null) {
        const options = {
            method: data ? 'POST' : 'GET',
            headers: { 'Content-Type': 'application/json' },
        };
        if (data) options.body = JSON.stringify(data);

        const response = await fetch(endpoint, options);
        const json = await response.json();

        if (!response.ok) {
            throw new Error(json.error || json.message || `Request failed (${response.status})`);
        }

        return json;
    }

    // -----------------------------------------------------------------------
    // Session Status
    // -----------------------------------------------------------------------
    async function checkSession() {
        try {
            const data = await apiCall('/api/status');
            state.sessionActive = data.session_active;
            updateSessionUI();
        } catch (e) {
            console.error('Status check failed:', e);
            state.sessionActive = false;
            updateSessionUI();
        }
    }

    function updateSessionUI() {
        const dot = $('#session-dot');
        const label = $('#session-label');
        const cardTitle = $('#session-card-title');
        const cardDesc = $('#session-card-desc');
        const cardIcon = $('.session-card__icon');
        const loginBtn = $('#btn-login');
        const notice = $('#people-login-notice');

        if (state.sessionActive) {
            dot.className = 'session-dot active';
            label.textContent = 'Logged In';
            cardTitle.textContent = 'Session Active';
            cardDesc.textContent = 'Your LinkedIn session is active. All features are available.';
            cardIcon.classList.add('active');
            loginBtn.textContent = 'Refresh Session';
            notice.style.display = 'none';
        } else {
            dot.className = 'session-dot inactive';
            label.textContent = 'Not Logged In';
            cardTitle.textContent = 'Not Logged In';
            cardDesc.textContent = 'Log in to LinkedIn to unlock people search and full profile data.';
            cardIcon.classList.remove('active');
            loginBtn.innerHTML = `
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"/><polyline points="10 17 15 12 10 7"/><line x1="15" y1="12" x2="3" y2="12"/></svg>
                Launch LinkedIn Login
            `;
            notice.style.display = 'flex';
        }
    }

    // -----------------------------------------------------------------------
    // Loading States
    // -----------------------------------------------------------------------
    function showLoading(containerId, count = 3) {
        const container = $(`#${containerId}`);
        let html = '';
        for (let i = 0; i < count; i++) {
            html += `
                <div class="skeleton">
                    <div class="skeleton__line skeleton__line--title"></div>
                    <div class="skeleton__line skeleton__line--sub"></div>
                    <div class="skeleton__line skeleton__line--meta"></div>
                    <div class="skeleton__line skeleton__line--short"></div>
                </div>
            `;
        }
        container.innerHTML = html;
    }

    function setButtonLoading(btnId, loading) {
        const btn = $(`#${btnId}`);
        if (loading) {
            btn.dataset.originalHtml = btn.innerHTML;
            btn.innerHTML = '<span class="spinner"></span> Searching…';
            btn.disabled = true;
        } else {
            btn.innerHTML = btn.dataset.originalHtml || btn.innerHTML;
            btn.disabled = false;
        }
    }

    // -----------------------------------------------------------------------
    // Job Search
    // -----------------------------------------------------------------------
    function initJobSearch() {
        $('#form-jobs').addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = getFormData('form-jobs');

            if (!formData.query) {
                showToast('Please enter search keywords', 'warning');
                return;
            }

            setButtonLoading('btn-search-jobs', true);
            showLoading('results-jobs');

            try {
                const data = await apiCall('/api/search/jobs', formData);
                state.lastResults.jobs = data;
                renderJobResults(data);
                showToast(`Found ${data.count || 0} job${data.count !== 1 ? 's' : ''}`, 'success');
            } catch (err) {
                renderError('results-jobs', err.message);
                showToast(err.message, 'error');
            } finally {
                setButtonLoading('btn-search-jobs', false);
            }
        });
    }

    function renderJobResults(data) {
        const container = $('#results-jobs');
        const results = data.results || [];

        if (results.length === 0) {
            container.innerHTML = renderEmptyState('No jobs found', 'Try different keywords or broaden your filters.');
            return;
        }

        let html = `
            <div class="results-header">
                <div class="results-header__info">
                    Found <strong>${data.count || results.length}</strong> job${results.length !== 1 ? 's' : ''} for "${escapeHtml(data.query || '')}"
                    ${data.total_count ? ` · ${escapeHtml(data.total_count)} total` : ''}
                </div>
                <div class="results-header__actions">
                    <button class="btn btn--secondary btn--sm" onclick="App.exportResults('jobs', 'json')">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                        JSON
                    </button>
                    <button class="btn btn--secondary btn--sm" onclick="App.exportResults('jobs', 'csv')">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                        CSV
                    </button>
                </div>
            </div>
        `;

        results.forEach((job) => {
            const titleLink = job.job_url
                ? `<a href="${escapeHtml(job.job_url)}" target="_blank" rel="noopener">${escapeHtml(job.title)}</a>`
                : escapeHtml(job.title);

            html += `
                <div class="job-card">
                    <div class="job-card__title">${titleLink}</div>
                    ${job.company ? `<div class="job-card__company">${escapeHtml(job.company)}</div>` : ''}
                    <div class="job-card__meta">
                        ${job.location ? `
                            <span class="job-card__meta-item">
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>
                                ${escapeHtml(job.location)}
                            </span>
                        ` : ''}
                        ${job.posted_date ? `
                            <span class="job-card__meta-item">
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
                                ${escapeHtml(job.posted_date)}
                            </span>
                        ` : ''}
                        ${job.employment_type ? `
                            <span class="job-card__meta-item">
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="7" width="20" height="14" rx="2" ry="2"/><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/></svg>
                                ${escapeHtml(job.employment_type)}
                            </span>
                        ` : ''}
                        ${job.salary ? `
                            <span class="job-card__meta-item">
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>
                                ${escapeHtml(job.salary)}
                            </span>
                        ` : ''}
                    </div>
                </div>
            `;
        });

        container.innerHTML = html;
    }

    // -----------------------------------------------------------------------
    // Profile Lookup
    // -----------------------------------------------------------------------
    function initProfileLookup() {
        $('#form-profile').addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = getFormData('form-profile');

            if (!formData.profile_url && !formData.username) {
                showToast('Please enter a profile URL or username', 'warning');
                return;
            }

            setButtonLoading('btn-get-profile', true);
            showLoading('results-profile', 1);

            try {
                const data = await apiCall('/api/profile', formData);
                state.lastResults.profile = data;
                renderProfileCard(data);
                showToast(`Profile loaded: ${data.name || 'Unknown'}`, 'success');
            } catch (err) {
                renderError('results-profile', err.message);
                showToast(err.message, 'error');
            } finally {
                setButtonLoading('btn-get-profile', false);
            }
        });
    }

    function renderProfileCard(profile) {
        const container = $('#results-profile');
        const initials = getInitials(profile.name || '?');

        let skillsHtml = '';
        if (profile.skills && profile.skills.length > 0) {
            skillsHtml = `
                <div class="profile-card__section">
                    <div class="profile-card__section-title">Skills</div>
                    <div class="skills-list">
                        ${profile.skills.map(s => `<span class="skill-tag">${escapeHtml(s)}</span>`).join('')}
                    </div>
                </div>
            `;
        }

        const exportBtns = `
            <div class="results-header" style="margin-top:1rem;">
                <div></div>
                <div class="results-header__actions">
                    <button class="btn btn--secondary btn--sm" onclick="App.exportResults('profile', 'json')">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                        Export JSON
                    </button>
                </div>
            </div>
        `;

        container.innerHTML = `
            <div class="profile-card">
                <div class="profile-card__banner">
                    <div class="profile-card__avatar">${initials}</div>
                </div>
                <div class="profile-card__body">
                    <div class="profile-card__name">${escapeHtml(profile.name || 'Unknown')}</div>
                    ${profile.headline ? `<div class="profile-card__headline">${escapeHtml(profile.headline)}</div>` : ''}
                    <div class="profile-card__detail">
                        ${profile.location ? `
                            <span class="profile-card__detail-item">
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>
                                ${escapeHtml(profile.location)}
                            </span>
                        ` : ''}
                        ${profile.current_company ? `
                            <span class="profile-card__detail-item">
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="7" width="20" height="14" rx="2" ry="2"/><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/></svg>
                                ${escapeHtml(profile.current_company)}
                            </span>
                        ` : ''}
                        ${profile.current_title ? `
                            <span class="profile-card__detail-item">
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
                                ${escapeHtml(profile.current_title)}
                            </span>
                        ` : ''}
                        ${profile.connections ? `
                            <span class="profile-card__detail-item">
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
                                ${escapeHtml(profile.connections)}
                            </span>
                        ` : ''}
                    </div>
                    ${profile.about ? `<div class="profile-card__about">${escapeHtml(profile.about)}</div>` : ''}
                    ${skillsHtml}
                    ${profile.profile_url ? `
                        <a href="${escapeHtml(profile.profile_url)}" target="_blank" rel="noopener" class="btn btn--secondary btn--sm" style="margin-top:0.5rem;">
                            View on LinkedIn →
                        </a>
                    ` : ''}
                </div>
            </div>
            ${exportBtns}
        `;
    }

    // -----------------------------------------------------------------------
    // People Search
    // -----------------------------------------------------------------------
    function initPeopleSearch() {
        $('#form-people').addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = getFormData('form-people');

            if (!formData.query) {
                showToast('Please enter search keywords', 'warning');
                return;
            }

            setButtonLoading('btn-search-people', true);
            showLoading('results-people');

            try {
                const data = await apiCall('/api/search/people', formData);
                state.lastResults.people = data;
                renderPeopleResults(data);
                showToast(`Found ${data.count || 0} people`, 'success');
            } catch (err) {
                renderError('results-people', err.message);
                showToast(err.message, 'error');
            } finally {
                setButtonLoading('btn-search-people', false);
            }
        });
    }

    function renderPeopleResults(data) {
        const container = $('#results-people');
        const results = data.results || [];

        if (results.length === 0) {
            container.innerHTML = renderEmptyState('No people found', 'Try different keywords or filters.');
            return;
        }

        let html = `
            <div class="results-header">
                <div class="results-header__info">
                    Found <strong>${data.count || results.length}</strong> people for "${escapeHtml(data.query || '')}"
                    ${data.total_count ? ` · ${escapeHtml(data.total_count)} total` : ''}
                </div>
                <div class="results-header__actions">
                    <button class="btn btn--secondary btn--sm" onclick="App.exportResults('people', 'json')">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                        JSON
                    </button>
                    <button class="btn btn--secondary btn--sm" onclick="App.exportResults('people', 'csv')">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                        CSV
                    </button>
                </div>
            </div>
            <div class="people-grid">
        `;

        results.forEach((person) => {
            const initials = getInitials(person.name || '?');
            const nameLink = person.profile_url
                ? `<a href="${escapeHtml(person.profile_url)}" target="_blank" rel="noopener">${escapeHtml(person.name)}</a>`
                : escapeHtml(person.name || 'Unknown');

            html += `
                <div class="person-card">
                    <div class="person-card__header">
                        <div class="person-card__avatar">${initials}</div>
                        <div>
                            <div class="person-card__name">${nameLink}</div>
                            ${person.headline ? `<div class="person-card__headline">${escapeHtml(person.headline)}</div>` : ''}
                        </div>
                    </div>
                    ${person.location ? `
                        <div class="person-card__location">
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>
                            ${escapeHtml(person.location)}
                        </div>
                    ` : ''}
                </div>
            `;
        });

        html += '</div>';
        container.innerHTML = html;
    }

    // -----------------------------------------------------------------------
    // Company Lookup
    // -----------------------------------------------------------------------
    function initCompanyLookup() {
        $('#form-company').addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = getFormData('form-company');

            console.log('Company form data:', formData);

            if (!formData.company_url && !formData.company_slug) {
                showToast('Please enter a company URL or slug', 'warning');
                return;
            }

            setButtonLoading('btn-get-company', true);
            showLoading('results-company', 1);

            try {
                const data = await apiCall('/api/company', formData);
                console.log('Company API response:', data);
                state.lastResults.company = data;
                renderCompanyCard(data);
                showToast(`Company loaded: ${data.name || 'Unknown'}`, 'success');
            } catch (err) {
                console.error('Company API error:', err);
                renderError('results-company', err.message);
                showToast(err.message, 'error');
            } finally {
                setButtonLoading('btn-get-company', false);
            }
        });
    }

    function renderCompanyCard(company) {
        const container = $('#results-company');
        const initial = (company.name || '?')[0].toUpperCase();

        // Debug: log the raw company data
        console.log('Company data received:', company);

        const details = [];
        if (company.industry) details.push({ label: 'Industry', value: company.industry });
        if (company.company_size) details.push({ label: 'Company Size', value: company.company_size });
        if (company.headquarters) details.push({ label: 'Headquarters', value: company.headquarters });
        if (company.website) details.push({ label: 'Website', value: company.website });
        if (company.founded) details.push({ label: 'Founded', value: company.founded });
        if (company.employee_count) details.push({ label: 'Employees', value: company.employee_count });

        let specialtiesHtml = '';
        if (company.specialties && company.specialties.length > 0) {
            specialtiesHtml = `
                <div class="profile-card__section">
                    <div class="profile-card__section-title">Specialties</div>
                    <div class="skills-list">
                        ${company.specialties.map(s => `<span class="skill-tag">${escapeHtml(s)}</span>`).join('')}
                    </div>
                </div>
            `;
        }

        const exportBtns = `
            <div class="results-header" style="margin-top:1rem;">
                <div></div>
                <div class="results-header__actions">
                    <button class="btn btn--secondary btn--sm" onclick="App.exportResults('company', 'json')">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                        Export JSON
                    </button>
                </div>
            </div>
        `;

        container.innerHTML = `
            <div class="company-card">
                <div class="company-card__banner">
                    <div class="company-card__banner-icon">${initial}</div>
                </div>
                <div class="company-card__body">
                    <div class="company-card__name">${escapeHtml(company.name || 'Unknown')}</div>
                    ${company.tagline ? `<div class="company-card__tagline">${escapeHtml(company.tagline)}</div>` : ''}
                    ${details.length > 0 ? `
                        <div class="company-card__details">
                            ${details.map(d => `
                                <div class="detail-item">
                                    <span class="detail-item__label">${escapeHtml(d.label)}</span>
                                    <span class="detail-item__value">${escapeHtml(d.value)}</span>
                                </div>
                            `).join('')}
                        </div>
                    ` : ''}
                    ${company.about ? `<div class="company-card__about">${escapeHtml(company.about)}</div>` : ''}
                    ${specialtiesHtml}
                    ${company.company_url ? `
                        <a href="${escapeHtml(company.company_url)}" target="_blank" rel="noopener" class="btn btn--secondary btn--sm" style="margin-top:0.5rem;">
                            View on LinkedIn →
                        </a>
                    ` : ''}
                </div>
            </div>
            ${exportBtns}
        `;
    }

    // -----------------------------------------------------------------------
    // Session / Login
    // -----------------------------------------------------------------------
    function initLogin() {
        $('#btn-login').addEventListener('click', async () => {
            const btn = $('#btn-login');
            btn.innerHTML = '<span class="spinner"></span> Waiting for login…';
            btn.disabled = true;

            showToast('A browser window will open. Please log in to LinkedIn manually.', 'info', 10000);

            try {
                const data = await apiCall('/api/login', {});
                showToast(data.message || 'Login successful!', 'success');
                await checkSession();
            } catch (err) {
                showToast(err.message || 'Login failed', 'error');
            } finally {
                btn.disabled = false;
                btn.innerHTML = `
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"/><polyline points="10 17 15 12 10 7"/><line x1="15" y1="12" x2="3" y2="12"/></svg>
                    Launch LinkedIn Login
                `;
            }
        });
    }

    // -----------------------------------------------------------------------
    // Export
    // -----------------------------------------------------------------------
    function exportResults(tabName, format) {
        const data = state.lastResults[tabName];
        if (!data) {
            showToast('No data to export', 'warning');
            return;
        }

        const exportData = data.results || (Array.isArray(data) ? data : [data]);
        const filename = `linkedin_${tabName}_${new Date().toISOString().slice(0, 10)}`;

        if (format === 'csv') {
            downloadCSV(exportData, filename);
        } else {
            downloadJSON(exportData, filename);
        }
    }

    function downloadJSON(data, filename) {
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        triggerDownload(blob, `${filename}.json`);
        showToast('JSON file downloaded', 'success', 3000);
    }

    function downloadCSV(data, filename) {
        if (!Array.isArray(data) || data.length === 0) {
            showToast('No data to export', 'warning');
            return;
        }

        // Collect all keys
        const keys = [];
        data.forEach(row => {
            if (typeof row === 'object' && row !== null) {
                Object.keys(row).forEach(k => {
                    if (!keys.includes(k)) keys.push(k);
                });
            }
        });

        const rows = [keys.join(',')];
        data.forEach(row => {
            const vals = keys.map(k => {
                let v = row[k];
                if (Array.isArray(v)) v = v.join('; ');
                if (v === null || v === undefined) v = '';
                v = String(v).replace(/"/g, '""');
                return `"${v}"`;
            });
            rows.push(vals.join(','));
        });

        const blob = new Blob([rows.join('\n')], { type: 'text/csv' });
        triggerDownload(blob, `${filename}.csv`);
        showToast('CSV file downloaded', 'success', 3000);
    }

    function triggerDownload(blob, filename) {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    // -----------------------------------------------------------------------
    // Utilities
    // -----------------------------------------------------------------------
    function getFormData(formId) {
        const form = $(`#${formId}`);
        const formData = new FormData(form);
        const data = {};
        for (const [key, value] of formData.entries()) {
            if (value) data[key] = value;
        }
        return data;
    }

    function escapeHtml(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    function getInitials(name) {
        return name
            .split(' ')
            .filter(Boolean)
            .slice(0, 2)
            .map(w => w[0].toUpperCase())
            .join('');
    }

    function renderEmptyState(title, desc) {
        return `
            <div class="empty-state">
                <div class="empty-state__icon">
                    <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
                </div>
                <div class="empty-state__title">${title}</div>
                <div class="empty-state__desc">${desc}</div>
            </div>
        `;
    }

    function renderError(containerId, message) {
        const container = $(`#${containerId}`);
        container.innerHTML = `
            <div class="error-state">
                <div class="error-state__icon">
                    <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>
                </div>
                <div class="error-state__message">${escapeHtml(message)}</div>
            </div>
        `;
    }

    // -----------------------------------------------------------------------
    // Initialize
    // -----------------------------------------------------------------------
    function init() {
        initTheme();
        initTabs();
        initDisclaimer();
        initJobSearch();
        initProfileLookup();
        initPeopleSearch();
        initCompanyLookup();
        initLogin();
        checkSession();

        // Expose export function globally for onclick handlers
        window.App = { exportResults };
    }

    // Run when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
