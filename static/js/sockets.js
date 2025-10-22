// WebSocket Live Updates - TCTFS

let socket = null;
let reconnectAttempts = 0;
let maxReconnectAttempts = 5;
let reconnectDelay = 1000;

// Initialize WebSocket connection
function initWebSocket() {
    if (typeof io === 'undefined') {
        console.warn('Socket.IO not loaded');
        return;
    }
    
    socket = io('/ws/live', {
        transports: ['websocket', 'polling'],
        reconnection: true,
        reconnectionAttempts: maxReconnectAttempts,
        reconnectionDelay: reconnectDelay
    });
    
    setupSocketHandlers();
}

// Setup all socket event handlers
function setupSocketHandlers() {
    // Connection events
    socket.on('connect', handleConnect);
    socket.on('disconnect', handleDisconnect);
    socket.on('reconnect', handleReconnect);
    socket.on('reconnect_error', handleReconnectError);
    socket.on('error', handleError);
    
    // Application events
    socket.on('connected', handleConnected);
    socket.on('advisory_updated', handleAdvisoryUpdate);
    socket.on('forecast_updated', handleForecastUpdate);
    socket.on('zones_updated', handleZonesUpdate);
    
    // Subscription events
    socket.on('subscribed', handleSubscribed);
    socket.on('unsubscribed', handleUnsubscribed);
}

// Connection handlers
function handleConnect() {
    console.log('WebSocket connected');
    reconnectAttempts = 0;
    updateConnectionStatus('connected');
    
    // Subscribe to current storm if on storm detail page
    if (typeof stormId !== 'undefined') {
        subscribeToStorm(stormId);
    }
}

function handleDisconnect(reason) {
    console.log('WebSocket disconnected:', reason);
    updateConnectionStatus('disconnected');
}

function handleReconnect(attemptNumber) {
    console.log('WebSocket reconnected after', attemptNumber, 'attempts');
    reconnectAttempts = 0;
    updateConnectionStatus('connected');
}

function handleReconnectError(error) {
    reconnectAttempts++;
    console.error('Reconnection error:', error);
    
    if (reconnectAttempts >= maxReconnectAttempts) {
        updateConnectionStatus('failed');
        showNotification('Connection lost. Please refresh the page.', 'error');
    }
}

function handleError(error) {
    console.error('WebSocket error:', error);
}

function handleConnected(data) {
    console.log('Connected to TCTFS:', data.message);
}

// Application event handlers
function handleAdvisoryUpdate(data) {
    console.log('Advisory updated for storm:', data.storm_id);
    
    showNotification(`New advisory for ${data.storm_id}`, 'info');
    
    // Refresh data if on storm detail page
    if (typeof stormId !== 'undefined' && data.storm_id === stormId) {
        refreshStormData();
    }
    
    // Update dashboard if present
    if (typeof updateStormInList === 'function') {
        updateStormInList(data.storm_id);
    }
}

function handleForecastUpdate(data) {
    console.log('Forecast updated for storm:', data.storm_id);
    
    showNotification(`Forecast updated for ${data.storm_id}`, 'info');
    
    // Refresh data if on storm detail page
    if (typeof stormId !== 'undefined' && data.storm_id === stormId) {
        refreshForecastData();
    }
}

function handleZonesUpdate(data) {
    console.log('Zones updated for storm:', data.storm_id);
    
    showNotification(`Watch/Warning zones updated for ${data.storm_id}`, 'warning');
    
    // Refresh data if on storm detail page
    if (typeof stormId !== 'undefined' && data.storm_id === stormId) {
        refreshZonesData();
    }
}

// Subscription handlers
function handleSubscribed(data) {
    console.log('Subscribed to storm:', data.storm_id);
}

function handleUnsubscribed(data) {
    console.log('Unsubscribed from storm:', data.storm_id);
}

// Subscription functions
function subscribeToStorm(stormId) {
    if (!socket || !socket.connected) {
        console.warn('Socket not connected, cannot subscribe');
        return;
    }
    
    socket.emit('subscribe_storm', { storm_id: stormId });
}

function unsubscribeFromStorm(stormId) {
    if (!socket || !socket.connected) {
        return;
    }
    
    socket.emit('unsubscribe_storm', { storm_id: stormId });
}

// Data refresh functions
async function refreshStormData() {
    if (typeof loadStormData === 'function') {
        await loadStormData();
    }
}

async function refreshForecastData() {
    if (typeof stormId !== 'undefined' && typeof map !== 'undefined') {
        // Reload forecast
        const response = await fetch(`/api/storms/${stormId}/forecast`);
        const data = await response.json();
        
        // Update map if function available
        if (typeof updateMap === 'function') {
            forecast = data.forecast_points || [];
            updateMap();
        }
    }
}

async function refreshZonesData() {
    if (typeof stormId !== 'undefined' && typeof map !== 'undefined') {
        // Reload zones
        if (typeof loadZones === 'function') {
            await loadZones(stormId, map);
        }
    }
}

// Connection status UI update
function updateConnectionStatus(status) {
    const indicator = document.getElementById('connection-status');
    if (!indicator) return;
    
    indicator.className = `connection-status connection-${status}`;
    
    const statusText = {
        'connected': 'Live',
        'disconnected': 'Connecting...',
        'failed': 'Offline'
    };
    
    indicator.textContent = statusText[status] || status;
}

// Notification system
function showNotification(message, type = 'info') {
    // Check if toast/notification system available
    if (typeof createToast === 'function') {
        createToast(message, type);
        return;
    }
    
    // Fallback: simple console log
    console.log(`[${type.toUpperCase()}] ${message}`);
    
    // Could also create a simple notification div
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    notification.style.cssText = `
        position: fixed;
        top: 1rem;
        right: 1rem;
        padding: 1rem 1.5rem;
        background: white;
        border-radius: 0.5rem;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        z-index: 9999;
        animation: slideIn 0.3s ease-out;
    `;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease-in';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// Ping/pong for connection health
function startHeartbeat() {
    if (!socket) return;
    
    setInterval(() => {
        if (socket.connected) {
            socket.emit('ping');
        }
    }, 30000); // Every 30 seconds
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    initWebSocket();
    startHeartbeat();
});

// Cleanup on page unload
window.addEventListener('beforeunload', function() {
    if (socket) {
        socket.disconnect();
    }
});

// Export for use in other modules
window.socketManager = {
    subscribe: subscribeToStorm,
    unsubscribe: unsubscribeFromStorm,
    isConnected: () => socket && socket.connected
};
