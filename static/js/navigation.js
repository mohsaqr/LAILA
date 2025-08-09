// =============================================================================
// UNIFIED NAVIGATION SYSTEM - LAILA Platform
// =============================================================================
// Include this in all pages for consistent navigation

// Create unified navigation header
async function createNavigationHeader() {
    const nav = document.createElement('div');
    nav.className = 'unified-nav';
    nav.innerHTML = `
        <div class="nav-left">
            <button class="nav-button back-home" onclick="goToMainMenu()">
                <i class="fas fa-home"></i> Main Menu
            </button>
        </div>
        <div class="nav-center">
            <span class="app-title">LAILA</span>
        </div>
        <div class="nav-right">
            <button class="nav-button admin-btn" id="adminBtn" onclick="goToAdmin()" style="display: none;">
                <i class="fas fa-crown"></i> Admin Panel
            </button>
             
            <button class="nav-button settings-btn" id="userInfo" onclick="goToUserSettings()" style="display: none;">
                <i class="fas fa-user"></i> <span id="userName">Loading...</span>
            </button>
            <button class="nav-button logout-btn" onclick="logout()">
                <i class="fas fa-sign-out-alt"></i> Logout
            </button>
        </div>
    `;
    
    // Insert at the beginning of body
    document.body.insertBefore(nav, document.body.firstChild);
    // Load user info
    await loadUserInfo();
}

// Load user information
async function loadUserInfo() {
    try {
        const response = await fetch('/api/user-info');
        if (response.ok) {
            const data = await response.json();
            if (data.authenticated) {
                document.getElementById('userName').textContent = data.user.fullname || data.user.email;
                
                // Show admin button if user is admin
                if (data.user.is_admin) {
                    const adminBtn = document.getElementById('adminBtn');
                    if (adminBtn) {
                        adminBtn.style.display = 'inline-block';
                    }
                }
            }
        }
    } catch (error) {
        console.error('Error loading user info:', error);
    }
}

// Navigation functions
function goToMainMenu() {
    window.location.href = '/main-menu';
}

function logout() {
    if (confirm('Are you sure you want to logout?')) {
        window.location.href = '/logout';
    }
}

function goToUserSettings() {
    window.location.href = '/user-settings';
}

function goToAdmin() {
    window.location.href = '/admin';
}

// Log interaction helper
function logInteraction(action, page, elementId = null, elementType = null, elementValue = null) {
    fetch('/api/log-interaction', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            action: action,
            page: page,
            element_id: elementId,
            element_type: elementType,
            element_value: elementValue,
            interaction_type: 'user_click',
            timestamp: new Date().toISOString()
        })
    }).catch(error => console.error('Error logging interaction:', error));
}

// Initialize navigation when DOM is loaded
document.addEventListener('DOMContentLoaded', async function() {
    // Add navigation to all pages except login page
    const path = window.location.pathname;
    const isLoginPage = path.includes('login') || path === '/' || path.endsWith('/');
    
    if (!isLoginPage) {
       await createNavigationHeader();
    }
    
    // Log page view
    const page = window.location.pathname.split('/').pop() || 'index';
    logInteraction('page_view', page);
});

// Unified CSS for navigation (inject into head)
const navCSS = `
<style>
    .unified-nav {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 10px 20px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        z-index: 1000;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        font-family: 'Arial', sans-serif;
    }
    
    .nav-left, .nav-right {
        display: flex;
        align-items: center;
        gap: 15px;
    }
    
    .nav-center {
        flex: 1;
        text-align: center;
    }
    
    .app-title {
        font-size: 1.5em;
        font-weight: bold;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
    }
    
    .nav-button {
        background: rgba(255,255,255,0.2);
        color: white;
        border: none;
        padding: 8px 16px;
        border-radius: 20px;
        cursor: pointer;
        font-size: 0.9em;
        backdrop-filter: blur(10px);
        transition: all 0.3s ease;
        display: flex;
        align-items: center;
        gap: 5px;
    }
    
    .nav-button:hover {
        background: rgba(255,255,255,0.3);
        transform: translateY(-2px);
    }
    
    .logout-btn {
        background: rgba(220, 53, 69, 0.8);
    }
    
    .logout-btn:hover {
        background: rgba(220, 53, 69, 1);
    }
    
    .settings-btn {
        background: rgba(40, 167, 69, 0.8);
    }
    
    .admin-btn {
        background: linear-gradient(135deg, #e74c3c, #c0392b);
        border: 2px solid rgba(255,255,255,0.3);
        font-weight: bold;
        box-shadow: 0 2px 10px rgba(231, 76, 60, 0.3);
    }
    
    .admin-btn:hover {
        background: linear-gradient(135deg, #c0392b, #a93226);
        box-shadow: 0 4px 15px rgba(231, 76, 60, 0.5);
        border-color: rgba(255,255,255,0.6);
    }
    
    .settings-btn:hover {
        background: rgba(40, 167, 69, 1);
    }
    
    .user-info {
        background: rgba(255,255,255,0.15);
        padding: 4px 16px;
        border-radius: 20px;
        backdrop-filter: blur(10px);
        font-size: 0.9em;
        display: flex;
        align-items: center;
        gap: 5px;
    }
    
    /* Adjust body padding to account for fixed nav */
    body {
        padding-top: 60px !important;
    }
    
    /* Responsive design */
    @media (max-width: 768px) {
        .unified-nav {
            padding: 8px 15px;
            flex-wrap: wrap;
        }
        
        .nav-center {
            order: -1;
            width: 100%;
            margin-bottom: 10px;
        }
        
        .app-title {
            font-size: 1.2em;
        }
        
        .nav-button, .user-info {
            font-size: 0.8em;
            padding: 4px 12px;
        }
    }
</style>
`;

// Inject CSS into head
document.head.insertAdjacentHTML('beforeend', navCSS); 