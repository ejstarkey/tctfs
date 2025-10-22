// Zones Layer - Watch/Warning polygon rendering and legend sync

let zonesLayer = {
    visible: true,
    zones: [],
    colors: {
        watch: {
            fill: 'rgba(251, 191, 36, 0.3)',
            stroke: '#f59e0b'
        },
        warning: {
            fill: 'rgba(239, 68, 68, 0.4)',
            stroke: '#dc2626'
        }
    }
};

// Initialize zones layer
function initZonesLayer(map) {
    if (!map) return;
    
    // Add zones source if not exists
    if (!map.getSource('zones')) {
        map.addSource('zones', {
            type: 'geojson',
            data: {
                type: 'FeatureCollection',
                features: []
            }
        });
    }
    
    // Add fill layer
    if (!map.getLayer('zones-fill')) {
        map.addLayer({
            id: 'zones-fill',
            type: 'fill',
            source: 'zones',
            paint: {
                'fill-color': [
                    'match',
                    ['get', 'zone_type'],
                    'warning', zonesLayer.colors.warning.fill,
                    'watch', zonesLayer.colors.watch.fill,
                    'rgba(107, 114, 128, 0.2)'
                ],
                'fill-opacity': 1
            }
        });
    }
    
    // Add outline layer
    if (!map.getLayer('zones-outline')) {
        map.addLayer({
            id: 'zones-outline',
            type: 'line',
            source: 'zones',
            paint: {
                'line-color': [
                    'match',
                    ['get', 'zone_type'],
                    'warning', zonesLayer.colors.warning.stroke,
                    'watch', zonesLayer.colors.watch.stroke,
                    '#6b7280'
                ],
                'line-width': 2
            }
        });
    }
    
    // Add hover effects
    map.on('mouseenter', 'zones-fill', function() {
        map.getCanvas().style.cursor = 'pointer';
    });
    
    map.on('mouseleave', 'zones-fill', function() {
        map.getCanvas().style.cursor = '';
    });
    
    // Add click handler for zone details
    map.on('click', 'zones-fill', function(e) {
        const zone = e.features[0];
        showZonePopup(e.lngLat, zone.properties);
    });
    
    // Initialize legend
    updateZonesLegend();
}

// Load zones data
async function loadZones(stormId, map) {
    try {
        const response = await fetch(`/api/storms/${stormId}/zones`);
        if (!response.ok) {
            console.error('Failed to load zones');
            return;
        }
        
        const data = await response.json();
        zonesLayer.zones = data.features || [];
        
        updateZonesLayer(map);
        updateZonesLegend();
        
    } catch (error) {
        console.error('Error loading zones:', error);
    }
}

// Update zones layer with new data
function updateZonesLayer(map) {
    if (!map || !map.getSource('zones')) return;
    
    map.getSource('zones').setData({
        type: 'FeatureCollection',
        features: zonesLayer.zones
    });
}

// Toggle zones layer visibility
function toggleZonesLayer(map) {
    zonesLayer.visible = !zonesLayer.visible;
    
    const visibility = zonesLayer.visible ? 'visible' : 'none';
    
    if (map.getLayer('zones-fill')) {
        map.setLayoutProperty('zones-fill', 'visibility', visibility);
    }
    
    if (map.getLayer('zones-outline')) {
        map.setLayoutProperty('zones-outline', 'visibility', visibility);
    }
    
    updateZonesLegend();
}

// Show zone popup with details
function showZonePopup(lngLat, properties) {
    const zoneType = properties.zone_type;
    const validFrom = new Date(properties.valid_from_utc);
    const validTo = new Date(properties.valid_to_utc);
    
    const html = `
        <div style="padding: 0.75rem; min-width: 200px;">
            <div style="font-weight: 700; font-size: 1rem; margin-bottom: 0.5rem; text-transform: uppercase;">
                ${zoneType === 'warning' ? 'Cyclone Warning' : 'Cyclone Watch'}
            </div>
            <div style="font-size: 0.875rem; color: #4b5563;">
                <strong>Valid From:</strong><br>
                ${validFrom.toUTCString()}<br><br>
                <strong>Valid To:</strong><br>
                ${validTo.toUTCString()}
            </div>
            ${properties.metadata ? `
                <div style="margin-top: 0.5rem; padding-top: 0.5rem; border-top: 1px solid #e5e7eb; font-size: 0.8125rem; color: #6b7280;">
                    ${properties.metadata.description || ''}
                </div>
            ` : ''}
        </div>
    `;
    
    new maplibregl.Popup()
        .setLngLat(lngLat)
        .setHTML(html)
        .addTo(map);
}

// Update zones legend
function updateZonesLegend() {
    const legend = document.getElementById('zones-legend');
    if (!legend) return;
    
    const watchCount = zonesLayer.zones.filter(z => z.properties.zone_type === 'watch').length;
    const warningCount = zonesLayer.zones.filter(z => z.properties.zone_type === 'warning').length;
    
    legend.innerHTML = `
        <div class="legend-title">Zones</div>
        <div class="legend-items">
            ${warningCount > 0 ? `
                <div class="legend-item">
                    <div class="legend-color zone-warning"></div>
                    <span class="legend-label">Cyclone Warning (${warningCount})</span>
                </div>
            ` : ''}
            ${watchCount > 0 ? `
                <div class="legend-item">
                    <div class="legend-color zone-watch"></div>
                    <span class="legend-label">Cyclone Watch (${watchCount})</span>
                </div>
            ` : ''}
            ${watchCount === 0 && warningCount === 0 ? `
                <div class="legend-item">
                    <span class="legend-label" style="color: #9ca3af;">No active zones</span>
                </div>
            ` : ''}
        </div>
    `;
}

// Get zone statistics
function getZoneStats() {
    const stats = {
        total: zonesLayer.zones.length,
        watch: 0,
        warning: 0,
        areaKm2: 0
    };
    
    zonesLayer.zones.forEach(zone => {
        if (zone.properties.zone_type === 'watch') {
            stats.watch++;
        } else if (zone.properties.zone_type === 'warning') {
            stats.warning++;
        }
        
        // Calculate area if geometry present
        if (zone.geometry) {
            // Use turf.js or similar for accurate area calculation
            // stats.areaKm2 += turf.area(zone.geometry) / 1e6;
        }
    });
    
    return stats;
}

// Highlight zones by type
function highlightZoneType(map, zoneType) {
    if (!map || !map.getLayer('zones-fill')) return;
    
    map.setFilter('zones-fill', zoneType ? ['==', ['get', 'zone_type'], zoneType] : null);
    map.setFilter('zones-outline', zoneType ? ['==', ['get', 'zone_type'], zoneType] : null);
}

// Clear zone highlights
function clearZoneHighlight(map) {
    highlightZoneType(map, null);
}

// Export zones as GeoJSON
function exportZonesGeoJSON() {
    const geojson = {
        type: 'FeatureCollection',
        features: zonesLayer.zones
    };
    
    const dataStr = JSON.stringify(geojson, null, 2);
    const dataUri = 'data:application/json;charset=utf-8,' + encodeURIComponent(dataStr);
    
    const exportName = `zones_${stormId}_${Date.now()}.geojson`;
    
    const linkElement = document.createElement('a');
    linkElement.setAttribute('href', dataUri);
    linkElement.setAttribute('download', exportName);
    linkElement.click();
}

// Listen for zone updates via WebSocket
function setupZonesWebSocket(stormId, map) {
    if (typeof io === 'undefined') return;
    
    const socket = io('/ws/live');
    
    socket.on('connect', function() {
        socket.emit('subscribe_storm', { storm_id: stormId });
    });
    
    socket.on('zones_updated', function(data) {
        if (data.storm_id === stormId) {
            console.log('Zones updated via WebSocket');
            loadZones(stormId, map);
        }
    });
}

// Initialize on page load if storm map present
if (typeof map !== 'undefined' && typeof stormId !== 'undefined') {
    initZonesLayer(map);
    loadZones(stormId, map);
    setupZonesWebSocket(stormId, map);
}
