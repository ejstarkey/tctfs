/**
 * Archive Page JavaScript
 * Handles search, filtering, and display of archived storms
 */

class ArchiveManager {
    constructor() {
        this.currentPage = 0;
        this.limit = 50;
        this.currentFilters = {};
        this.viewMode = 'grid';
        
        this.init();
    }
    
    init() {
        // Event listeners
        document.getElementById('archiveSearchForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.performSearch();
        });
        
        document.getElementById('archiveSearchForm').addEventListener('reset', () => {
            setTimeout(() => this.performSearch(), 100);
        });
        
        // View toggle
        document.querySelectorAll('.view-toggle').forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.toggleView(e.target.dataset.view);
            });
        });
        
        // Pagination
        document.getElementById('prevPage').addEventListener('click', () => this.previousPage());
        document.getElementById('nextPage').addEventListener('click', () => this.nextPage());
        
        // Quick links
        document.querySelectorAll('.quick-link-card').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                this.handleQuickLink(e.currentTarget.getAttribute('href'));
            });
        });
        
        // Initial load - show recent archives
        this.loadRecentArchives();
        this.loadStatistics();
    }
    
    performSearch() {
        const formData = new FormData(document.getElementById('archiveSearchForm'));
        const filters = {};
        
        for (let [key, value] of formData.entries()) {
            if (value) filters[key] = value;
        }
        
        this.currentFilters = filters;
        this.currentPage = 0;
        this.loadArchives();
    }
    
    async loadArchives() {
        const loadingEl = document.getElementById('loadingSpinner');
        const gridEl = document.getElementById('stormGrid');
        const emptyEl = document.getElementById('emptyState');
        
        // Show loading
        loadingEl.style.display = 'block';
        gridEl.innerHTML = '';
        emptyEl.style.display = 'none';
        
        try {
            // Build query string
            const params = new URLSearchParams({
                ...this.currentFilters,
                limit: this.limit,
                offset: this.currentPage * this.limit
            });
            
            const response = await fetch(`/api/archive/storms?${params}`);
            const data = await response.json();
            
            // Hide loading
            loadingEl.style.display = 'none';
            
            if (data.storms.length === 0) {
                emptyEl.style.display = 'block';
                document.getElementById('pagination').style.display = 'none';
                document.getElementById('resultCount').textContent = '(0)';
            } else {
                this.renderStorms(data.storms);
                this.updatePagination(data);
                document.getElementById('resultCount').textContent = `(${data.total})`;
            }
            
        } catch (error) {
            console.error('Failed to load archives:', error);
            loadingEl.style.display = 'none';
            this.showError('Failed to load archived storms. Please try again.');
        }
    }
    
    renderStorms(storms) {
        const gridEl = document.getElementById('stormGrid');
        gridEl.innerHTML = '';
        
        if (this.viewMode === 'grid') {
            storms.forEach(storm => {
                gridEl.appendChild(this.createStormCard(storm));
            });
        } else {
            storms.forEach(storm => {
                gridEl.appendChild(this.createStormListItem(storm));
            });
        }
    }
    
    createStormCard(storm) {
        const card = document.createElement('div');
        card.className = 'storm-card';
        
        const intensityClass = this.getIntensityClass(storm.peak_intensity_kt);
        const archivedDate = new Date(storm.archived_at).toLocaleDateString();
        
        card.innerHTML = `
            <div class="storm-card-thumb">
                <img src="${storm.thumbnail_url || '/static/img/placeholder-storm.png'}" 
                     alt="${storm.name} track" 
                     loading="lazy">
                <span class="intensity-badge ${intensityClass}">
                    ${storm.peak_intensity_kt || '?'}kt
                </span>
            </div>
            <div class="storm-card-content">
                <h3 class="storm-name">${storm.name || 'Unknown'}</h3>
                <p class="storm-id">${storm.storm_id} - ${storm.basin}</p>
                <div class="storm-stats">
                    <span>Peak: ${storm.peak_intensity_kt || '?'}kt</span>
                    ${storm.min_pressure_hpa ? `<span>${storm.min_pressure_hpa}hPa</span>` : ''}
                    <span>ACE: ${storm.ace || '0.0'}</span>
                </div>
                <p class="storm-date">${this.formatDateRange(storm)}</p>
                <p class="archived-info">Archived: ${archivedDate}</p>
                <div class="storm-actions">
                    <a href="/archive/storms/${storm.id}" class="btn btn-sm btn-primary">
                        View Storm
                    </a>
                    <button class="btn btn-sm btn-secondary" 
                            onclick="archiveManager.downloadExport(${storm.id}, 'geojson')">
                        <svg class="icon">
                            <use href="/static/img/icons/download.svg#icon"></use>
                        </svg>
                        Export
                    </button>
                </div>
            </div>
        `;
        
        return card;
    }
    
    createStormListItem(storm) {
        const item = document.createElement('div');
        item.className = 'storm-list-item';
        
        const intensityClass = this.getIntensityClass(storm.peak_intensity_kt);
        
        item.innerHTML = `
            <div class="list-thumb">
                <img src="${storm.thumbnail_url || '/static/img/placeholder-storm.png'}" 
                     alt="${storm.name}">
            </div>
            <div class="list-content">
                <div class="list-header">
                    <h3>${storm.name || 'Unknown'} <span class="storm-id-small">(${storm.storm_id})</span></h3>
                    <span class="intensity-badge ${intensityClass}">${storm.peak_intensity_kt || '?'}kt</span>
                </div>
                <div class="list-details">
                    <span class="basin">${storm.basin}</span>
                    <span class="date">${this.formatDateRange(storm)}</span>
                    <span class="ace">ACE: ${storm.ace || '0.0'}</span>
                    <span class="advisories">${storm.advisories_count || 0} advisories</span>
                </div>
            </div>
            <div class="list-actions">
                <a href="/archive/storms/${storm.id}" class="btn btn-sm btn-primary">View</a>
                <button class="btn btn-sm btn-secondary" 
                        onclick="archiveManager.downloadExport(${storm.id}, 'geojson')">
                    Export
                </button>
            </div>
        `;
        
        return item;
    }
    
    getIntensityClass(kt) {
        if (!kt) return 'intensity-unknown';
        if (kt >= 130) return 'intensity-super';
        if (kt >= 100) return 'intensity-major';
        if (kt >= 64) return 'intensity-typhoon';
        if (kt >= 34) return 'intensity-ts';
        return 'intensity-td';
    }
    
    formatDateRange(storm) {
        if (!storm.first_seen) return 'Unknown';
        
        const start = new Date(storm.first_seen);
        const end = storm.last_seen ? new Date(storm.last_seen) : start;
        
        const startStr = start.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
        const endStr = end.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
        
        if (start.toDateString() === end.toDateString()) {
            return end.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
        }
        
        return `${startStr} - ${endStr}`;
    }
    
    updatePagination(data) {
        const paginationEl = document.getElementById('pagination');
        const totalPages = Math.ceil(data.total / this.limit);
        
        if (totalPages <= 1) {
            paginationEl.style.display = 'none';
            return;
        }
        
        paginationEl.style.display = 'flex';
        
        document.getElementById('prevPage').disabled = this.currentPage === 0;
        document.getElementById('nextPage').disabled = this.currentPage >= totalPages - 1;
        document.getElementById('pageInfo').textContent = 
            `Page ${this.currentPage + 1} of ${totalPages}`;
    }
    
    previousPage() {
        if (this.currentPage > 0) {
            this.currentPage--;
            this.loadArchives();
            window.scrollTo({ top: 0, behavior: 'smooth' });
        }
    }
    
    nextPage() {
        this.currentPage++;
        this.loadArchives();
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }
    
    toggleView(mode) {
        this.viewMode = mode;
        
        // Update active button
        document.querySelectorAll('.view-toggle').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.view === mode);
        });
        
        // Update grid class
        const gridEl = document.getElementById('stormGrid');
        gridEl.className = mode === 'grid' ? 'storm-grid' : 'storm-list';
        
        // Re-render current results
        this.loadArchives();
    }
    
    async loadRecentArchives() {
        // Load last 30 days of archived storms
        const thirtyDaysAgo = new Date();
        thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);
        
        this.currentFilters = {};
        this.currentPage = 0;
        this.loadArchives();
    }
    
    async loadStatistics() {
        try {
            const response = await fetch('/api/archive/statistics');
            const data = await response.json();
            
            document.getElementById('totalStorms').textContent = data.total_systems || '-';
            document.getElementById('namedStorms').textContent = data.named_storms || '-';
            document.getElementById('majorStorms').textContent = data.major_typhoons || '-';
            document.getElementById('totalACE').textContent = 
                data.ace_total ? data.ace_total.toFixed(1) : '-';
        } catch (error) {
            console.error('Failed to load statistics:', error);
        }
    }
    
    handleQuickLink(href) {
        const target = href.replace('#', '');
        
        switch(target) {
            case 'recent':
                this.loadRecentArchives();
                break;
            case 'season':
                document.getElementById('season').value = new Date().getFullYear();
                this.performSearch();
                break;
            case 'major':
                document.getElementById('minIntensity').value = '100';
                this.performSearch();
                break;
            case 'notable':
                // Scroll to notable section
                document.querySelector('.notable-storms').scrollIntoView({ behavior: 'smooth' });
                break;
        }
    }
    
    async downloadExport(stormId, format = 'geojson') {
        try {
            const response = await fetch(`/api/archive/storms/${stormId}/export?format=${format}`);
            
            if (!response.ok) {
                throw new Error('Export failed');
            }
            
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `storm-${stormId}.${format}`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
            
            this.showToast('Export downloaded successfully', 'success');
        } catch (error) {
            console.error('Export failed:', error);
            this.showToast('Failed to download export', 'error');
        }
    }
    
    showError(message) {
        const emptyEl = document.getElementById('emptyState');
        emptyEl.innerHTML = `<p class="error">${message}</p>`;
        emptyEl.style.display = 'block';
    }
    
    showToast(message, type = 'info') {
        // Assumes you have a toast notification system
        if (window.showToast) {
            window.showToast(message, type);
        } else {
            alert(message);
        }
    }
}

// Initialize on page load
let archiveManager;
document.addEventListener('DOMContentLoaded', () => {
    archiveManager = new ArchiveManager();
});
