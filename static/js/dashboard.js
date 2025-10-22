// Dashboard JavaScript - TCTFS

let storms = [];
let filteredStorms = [];
let favorites = new Set(JSON.parse(localStorage.getItem('favorites') || '[]'));

// Initialize dashboard
document.addEventListener('DOMContentLoaded', function() {
    initDashboard();
    initFilters();
    initFavorites();
    setupWebSocket();
    
    // Auto-refresh every 5 minutes
    setInterval(loadStorms, 5 * 60 * 1000);
});

async function initDashboard() {
    showLoading();
    await loadStorms();
    renderStorms();
}

async function loadStorms() {
    try {
        const response = await fetch('/api/storms?status=active');
        if (!response.ok) throw new Error('Failed to load storms');
        
        const data = await response.json();
        storms = data.storms || [];
        filteredStorms = storms;
        
        console.log(`Loaded ${storms.length} storms`);
    } catch (error) {
        console.error('Error loading storms:', error);
        showError('Failed to load storms');
    }
}

function renderStorms() {
    const grid = document.getElementById('storm-grid');
    if (!grid) return;
    
    // Clear loading/error states
    hideLoading();
    
    if (filteredStorms.length === 0) {
        grid.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">🌀</div>
                <h3 class="empty-state-title">No active storms</h3>
                <p class="empty-state-text">There are currently no active tropical cyclones</p>
            </div>
        `;
        return;
    }
    
    grid.innerHTML = filteredStorms.map(storm => createStormCard(storm)).join('');
    
    // Add event listeners
    document.querySelectorAll('.storm-card').forEach(card => {
        card.addEventListener('click', function(e) {
            if (!e.target.closest('.favorite-btn')) {
                const stormId = this.dataset.stormId;
                window.location.href = `/storm/${stormId}`;
            }
        });
    });
    
    document.querySelectorAll('.favorite-btn').forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.stopPropagation();
            toggleFavorite(this.dataset.stormId);
        });
    });
}

function createStormCard(storm) {
    const isFavorite = favorites.has(storm.id.toString());
    const category = storm.intensity_category || 'TD';
    const categoryClass = `intensity-${category.toLowerCase()}`;
    
    return `
        <div class="storm-card" data-storm-id="${storm.id}">
            ${storm.last_thumb_url ? 
                `<img src="${storm.last_thumb_url}" alt="${storm.name || storm.storm_id}" class="storm-card-thumbnail">` :
                '<div class="storm-card-thumbnail"></div>'
            }
            
            <button class="favorite-btn ${isFavorite ? 'is-favorite' : ''}" data-storm-id="${storm.id}">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
                </svg>
            </button>
            
            <div class="storm-card-body">
                <div class="storm-card-header">
                    <div>
                        <h3 class="storm-name">${storm.name || 'UNNAMED'}</h3>
                        <p class="storm-id">${storm.storm_id} • ${storm.basin}</p>
                    </div>
                    <span class="status-badge status-${storm.status}">${storm.status}</span>
                </div>
                
                <div class="storm-stats">
                    <div class="storm-stat">
                        <span class="storm-stat-label">Intensity</span>
                        <span class="storm-stat-value ${categoryClass}">
                            ${storm.last_intensity_kt ? `${storm.last_intensity_kt} kt` : 'N/A'}
                        </span>
                    </div>
                    
                    <div class="storm-stat">
                        <span class="storm-stat-label">Category</span>
                        <span class="storm-stat-value ${categoryClass}">${category}</span>
                    </div>
                    
                    <div class="storm-stat">
                        <span class="storm-stat-label">Pressure</span>
                        <span class="storm-stat-value">
                            ${storm.last_mslp_hpa ? `${storm.last_mslp_hpa} hPa` : 'N/A'}
                        </span>
                    </div>
                    
                    <div class="storm-stat">
                        <span class="storm-stat-label">Position</span>
                        <span class="storm-stat-value">
                            ${storm.last_position ? 
                                `${storm.last_position.lat.toFixed(1)}°, ${storm.last_position.lon.toFixed(1)}°` : 
                                'N/A'}
                        </span>
                    </div>
                </div>
                
                ${storm.time_since_update ? 
                    `<div class="last-update">Updated ${formatTimeAgo(storm.time_since_update)}</div>` : 
                    ''}
            </div>
        </div>
    `;
}

// Filters
function initFilters() {
    const basinFilter = document.getElementById('basin-filter');
    const statusFilter = document.getElementById('status-filter');
    const searchInput = document.getElementById('search-input');
    
    if (basinFilter) {
        basinFilter.addEventListener('change', applyFilters);
    }
    
    if (statusFilter) {
        statusFilter.addEventListener('change', applyFilters);
    }
    
    if (searchInput) {
        searchInput.addEventListener('input', debounce(applyFilters, 300));
    }
}

function applyFilters() {
    const basin = document.getElementById('basin-filter')?.value || 'all';
    const status = document.getElementById('status-filter')?.value || 'all';
    const search = document.getElementById('search-input')?.value.toLowerCase() || '';
    
    filteredStorms = storms.filter(storm => {
        // Basin filter
        if (basin !== 'all' && storm.basin !== basin) return false;
        
        // Status filter
        if (status !== 'all' && storm.status !== status) return false;
        
        // Search filter
        if (search) {
            const searchText = `${storm.name} ${storm.storm_id} ${storm.basin}`.toLowerCase();
            if (!searchText.includes(search)) return false;
        }
        
        return true;
    });
    
    renderStorms();
}

// Favorites
function initFavorites() {
    // Load favorites from localStorage
    favorites = new Set(JSON.parse(localStorage.getItem('favorites') || '[]'));
}

function toggleFavorite(stormId) {
    const id = stormId.toString();
    
    if (favorites.has(id)) {
        favorites.delete(id);
    } else {
        favorites.add(id);
    }
    
    localStorage.setItem('favorites', JSON.stringify([...favorites]));
    renderStorms();
}

// WebSocket
function setupWebSocket() {
    if (typeof io === 'undefined') return;
    
    const socket = io('/ws/live');
    
    socket.on('connect', function() {
        console.log('WebSocket connected');
    });
    
    socket.on('advisory_updated', function(data) {
        console.log('Advisory updated:', data.storm_id);
        updateStormInList(data.storm_id);
    });
    
    socket.on('forecast_updated', function(data) {
        console.log('Forecast updated:', data.storm_id);
        updateStormInList(data.storm_id);
    });
}

async function updateStormInList(stormId) {
    try {
        const response = await fetch(`/api/storms/${stormId}`);
        if (!response.ok) return;
        
        const storm = await response.json();
        
        // Update in storms array
        const index = storms.findIndex(s => s.id === stormId);
        if (index !== -1) {
            storms[index] = storm;
            applyFilters(); // Re-render with filters
        }
    } catch (error) {
        console.error('Error updating storm:', error);
    }
}

// Utilities
function formatTimeAgo(seconds) {
    if (seconds < 60) return 'just now';
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
    return `${Math.floor(seconds / 86400)}d ago`;
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

function showLoading() {
    const grid = document.getElementById('storm-grid');
    if (grid) {
        grid.innerHTML = `
            <div class="loading-spinner">
                <div class="spinner"></div>
            </div>
        `;
    }
}

function hideLoading() {
    // Loading will be replaced by content
}

function showError(message) {
    const grid = document.getElementById('storm-grid');
    if (grid) {
        grid.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">⚠️</div>
                <h3 class="empty-state-title">Error</h3>
                <p class="empty-state-text">${message}</p>
            </div>
        `;
    }
}
