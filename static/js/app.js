/* ═══════════════════════════════════════════════════════════════
   LearnBridge — App JavaScript
   Theme switching, toast notifications, unread badge, utilities
   ═══════════════════════════════════════════════════════════════ */

// ── Theme Management ──────────────────────────────────────────────

function loadTheme() {
    const saved = localStorage.getItem('lb-theme') || 'dark';
    document.documentElement.setAttribute('data-theme', saved);
    updateThemeIcon(saved);
}

function setTheme(theme) {
    localStorage.setItem('lb-theme', theme);
    document.documentElement.setAttribute('data-theme', theme);
    updateThemeIcon(theme);
    // Close dropdown
    const menu = document.getElementById('theme-menu');
    if (menu) menu.classList.add('hidden');
}

function updateThemeIcon(theme) {
    const icon = document.getElementById('theme-icon');
    if (!icon) return;
    const icons = {
        dark:  '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"/>',
        light: '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"/>',
        aqua:  '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 6C14 6 13 2 12 2S10 6 10 6 6 8 6 10c0 3.314 2.686 6 6 6s6-2.686 6-6c0-2-4-4-4-4zM8 18h8"/>',
    };
    icon.innerHTML = icons[theme] || icons.dark;
}

function toggleThemeDropdown() {
    const menu = document.getElementById('theme-menu');
    if (menu) menu.classList.toggle('hidden');
}

// Close dropdown on outside click
document.addEventListener('click', (e) => {
    const dropdown = document.getElementById('theme-dropdown');
    const menu = document.getElementById('theme-menu');
    if (dropdown && menu && !dropdown.contains(e.target)) {
        menu.classList.add('hidden');
    }
});

// Apply theme immediately
loadTheme();


// ── Toast Notifications ───────────────────────────────────────────

function showToast(message, type = 'info', duration = 4000) {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const icons = {
        success: '✅',
        error: '❌',
        info: 'ℹ️',
    };

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `<span>${icons[type] || 'ℹ️'}</span><span>${message}</span>`;
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100px)';
        toast.style.transition = 'all 0.3s';
        setTimeout(() => toast.remove(), 300);
    }, duration);
}


// ── YouTube URL Helper ────────────────────────────────────────────

function extractYouTubeId(url) {
    if (!url) return null;
    const patterns = [
        /(?:youtube\.com\/watch\?v=|youtu\.be\/)([a-zA-Z0-9_-]{11})/,
        /youtube\.com\/embed\/([a-zA-Z0-9_-]{11})/,
    ];
    for (const p of patterns) {
        const m = url.match(p);
        if (m) return m[1];
    }
    return null;
}


// ── Unread Message Badge ──────────────────────────────────────────

async function updateUnreadBadge() {
    try {
        const r = await fetch('/chat/api/unread');
        if (!r.ok) return;
        const data = await r.json();
        const badge = document.getElementById('nav-unread-badge');
        if (!badge) return;
        if (data.unread > 0) {
            badge.textContent = data.unread > 9 ? '9+' : data.unread;
            badge.classList.remove('hidden');
            badge.classList.add('flex');
        } else {
            badge.classList.add('hidden');
            badge.classList.remove('flex');
        }
    } catch (e) {}
}

// Poll every 15s
if (document.getElementById('nav-unread-badge')) {
    updateUnreadBadge();
    setInterval(updateUnreadBadge, 15000);
}
