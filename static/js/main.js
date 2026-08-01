/**
 * Helpdesk IT Rumah Sakit - Main JavaScript
 */

// Toast notification system
function showToast(message, type = 'success') {
    const toastEl = document.getElementById('toast-notification');
    const titleEl = document.getElementById('toast-title');
    const messageEl = document.getElementById('toast-message');

    // Set color based on type
    const bgColors = {
        'success': '#198754',
        'error': '#dc3545',
        'warning': '#ffc107',
        'info': '#0dcaf0',
    };

    const titles = {
        'success': 'Berhasil',
        'error': 'Gagal',
        'warning': 'Peringatan',
        'info': 'Informasi',
    };

    titleEl.textContent = titles[type] || 'Informasi';
    messageEl.textContent = message;

    // Reset toast classes
    toastEl.classList.remove('text-bg-success', 'text-bg-danger', 'text-bg-warning', 'text-bg-info');

    if (type === 'error') {
        toastEl.classList.add('text-bg-danger');
    } else if (type === 'warning') {
        toastEl.classList.add('text-bg-warning');
    } else if (type === 'info') {
        toastEl.classList.add('text-bg-info');
    } else {
        toastEl.classList.add('text-bg-success');
    }

    const toast = new bootstrap.Toast(toastEl, {
        autohide: true,
        delay: 3000,
    });
    toast.show();
}

// Format date helper
function formatDate(dateStr) {
    const date = new Date(dateStr);
    return date.toLocaleDateString('id-ID', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
    });
}

// Format phone number for display
function formatPhone(phone) {
    if (!phone) return '-';
    if (phone.startsWith('62')) {
        return '0' + phone.slice(2);
    }
    return phone;
}

// Confirm dialog
async function confirmAction(message) {
    return new Promise((resolve) => {
        const result = window.confirm(message);
        resolve(result);
    });
}

// ===== Real-Time Updates via SSE =====
let eventSource = null;

function connectSSE() {
    if (eventSource) {
        eventSource.close();
    }
    eventSource = new EventSource('/api/events');

    eventSource.onopen = function() {
        console.log('SSE connected');
    };

    eventSource.onmessage = function(event) {
        try {
            const msg = JSON.parse(event.data);
            handleSSEEvent(msg.event, msg.data);
        } catch (e) {
            // Ignore keepalive or non-JSON messages
        }
    };

    eventSource.onerror = function() {
        console.warn('SSE connection error, reconnecting in 5s...');
        eventSource.close();
        setTimeout(connectSSE, 5000);
    };
}

function handleSSEEvent(event, data) {
    switch (event) {
        case 'tiket_baru':
        case 'status_update':
            // Refresh stats on dashboard
            if (typeof loadStats === 'function' && window.location.pathname === '/') {
                loadStats();
                loadTickets(currentPage || 1);
            }
            // Refresh tiket list on daftar tiket page
            if (typeof loadTickets === 'function' && window.location.pathname === '/tiket') {
                loadTickets(currentPage || 1);
            }
            // Show toast notification
            if (event === 'tiket_baru' && data.nomor_tiket) {
                showToast(`Tiket baru: ${data.nomor_tiket}`, 'info');
            }
            if (event === 'status_update' && data.nomor_tiket) {
                showToast(`${data.nomor_tiket}: ${data.status_lama} → ${data.status_baru}`, 'info');
            }
            break;
    }
}

// Auto refresh dashboard — replaced by SSE
// if (window.location.pathname === '/') {
//     setTimeout(() => {
//         window.location.reload();
//     }, 30000);
// }

// ===== Authentication Functions =====

// Decode payload JWT tanpa verifikasi tanda tangan — cukup untuk membaca klaim exp
function decodeJwtPayload(token) {
    try {
        const base64Url = token.split('.')[1];
        if (!base64Url) return null;
        const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
        const jsonPayload = decodeURIComponent(atob(base64).split('').map(function(c) {
            return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
        }).join(''));
        return JSON.parse(jsonPayload);
    } catch (e) {
        return null;
    }
}

// Periksa apakah token JWT sudah kedaluwarsa berdasarkan klaim exp
function isTokenExpired(token) {
    const payload = decodeJwtPayload(token);
    if (!payload || !payload.exp) return true;
    return payload.exp * 1000 <= Date.now();
}

// Check if user is authenticated and update navbar
function checkAuth() {
    let token = localStorage.getItem('auth_token');
    let username = localStorage.getItem('auth_username');
    const loginBtn = document.getElementById('btn-login');
    const logoutBtn = document.getElementById('btn-logout');
    const authUserEl = document.getElementById('auth-username');
    const navArsip = document.getElementById('nav-arsip');
    const navMaster = document.getElementById('nav-master');

    // Token ada tapi sudah kedaluwarsa/tidak valid -> anggap logout, bersihkan storage
    if (token && (!username || isTokenExpired(token))) {
        localStorage.removeItem('auth_token');
        localStorage.removeItem('auth_username');
        localStorage.removeItem('auth_role');
        token = null;
        username = null;
    }

    if (token && username) {
        // User is logged in
        if (loginBtn) loginBtn.style.display = 'none';
        if (logoutBtn) logoutBtn.style.display = 'inline-block';
        if (authUserEl) {
            authUserEl.style.display = 'inline';
            authUserEl.innerHTML = '<i class="bi bi-person-circle"></i> ' + username;
        }
        if (navArsip) navArsip.style.display = '';
        if (navMaster) navMaster.style.display = '';
    } else {
        // User is not logged in
        if (loginBtn) loginBtn.style.display = 'inline-block';
        if (logoutBtn) logoutBtn.style.display = 'none';
        if (authUserEl) authUserEl.style.display = 'none';
        if (navArsip) navArsip.style.display = 'none';
        if (navMaster) navMaster.style.display = 'none';
    }
}

// Logout function
async function logout() {
    if (!confirm('Yakin ingin logout?')) return;

    try {
        // Hapus cookie HTTP-only via backend
        await fetch('/api/auth/logout', { method: 'POST' });
    } catch (err) {
        console.warn('Gagal menghubungi server, logout lokal tetap dijalankan');
    }

    // Hapus localStorage
    localStorage.removeItem('auth_token');
    localStorage.removeItem('auth_username');
    localStorage.removeItem('auth_role');

    // Redirect to home if on protected page
    const protectedPaths = ['/tiket/arsip', '/master'];
    if (protectedPaths.includes(window.location.pathname)) {
        window.location.href = '/';
    } else {
        checkAuth();
        showToast('Berhasil logout', 'info');
    }
}

// Check auth on page load
document.addEventListener('DOMContentLoaded', function() {
    checkAuth();
    connectSSE();
});

// Re-check auth saat tab kembali aktif — token bisa saja kedaluwarsa selama tidak dipakai
window.addEventListener('focus', checkAuth);
document.addEventListener('visibilitychange', function() {
    if (!document.hidden) checkAuth();
});

// Close SSE connection before navigating away to free server resources
window.addEventListener('beforeunload', function() {
    if (eventSource) {
        eventSource.close();
        eventSource = null;
    }
});

// Dark Mode Toggle
function toggleDarkMode() {
    const html = document.documentElement;
    const icon = document.getElementById('darkmode-icon');
    const currentTheme = html.getAttribute('data-bs-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    
    html.setAttribute('data-bs-theme', newTheme);
    localStorage.setItem('theme', newTheme);
    
    if (icon) {
        icon.className = newTheme === 'dark' ? 'bi bi-sun-fill' : 'bi bi-moon-fill';
    }
}

// Apply saved theme on page load
(function applyTheme() {
    const savedTheme = localStorage.getItem('theme') || 'light';
    const html = document.documentElement;
    html.setAttribute('data-bs-theme', savedTheme);
    
    const icon = document.getElementById('darkmode-icon');
    if (icon) {
        icon.className = savedTheme === 'dark' ? 'bi bi-sun-fill' : 'bi bi-moon-fill';
    }
})();

