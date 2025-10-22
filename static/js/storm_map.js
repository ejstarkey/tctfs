// Storm Map - COMPLETE with category-colored tracks and proper tc-eye logic
let map, stormData, eyeMarker = null, currentBasin = null;

const BASIN_SCALES = {
    'SH': {
        name: 'Australian Tropical Cyclone Scale',
        thresholds: [34, 48, 64, 87, 108],
        categories: [
            { name: 'Tropical Low', range: '< 63 km/h', color: '#5ebaff' },
            { name: 'Category 1', range: '63-88 km/h', color: '#00faf4' },
            { name: 'Category 2', range: '89-117 km/h', color: '#ffffcc' },
            { name: 'Category 3', range: '118-159 km/h', color: '#ffe775' },
            { name: 'Category 4', range: '160-199 km/h', color: '#ffc140' },
            { name: 'Category 5', range: '≥ 200 km/h', color: '#ff8f20' }
        ],
        textColors: ['#000', '#000', '#000', '#ff8c00', '#ff6600', '#ff0000']
    },
    'IO': {
        name: 'Australian Tropical Cyclone Scale',
        thresholds: [34, 48, 64, 87, 108],
        categories: [
            { name: 'Tropical Low', range: '< 63 km/h', color: '#5ebaff' },
            { name: 'Category 1', range: '63-88 km/h', color: '#00faf4' },
            { name: 'Category 2', range: '89-117 km/h', color: '#ffffcc' },
            { name: 'Category 3', range: '118-159 km/h', color: '#ffe775' },
            { name: 'Category 4', range: '160-199 km/h', color: '#ffc140' },
            { name: 'Category 5', range: '≥ 200 km/h', color: '#ff8f20' }
        ],
        textColors: ['#000', '#000', '#000', '#ff8c00', '#ff6600', '#ff0000']
    },
    'AL': {
        name: 'Saffir-Simpson Hurricane Scale',
        thresholds: [34, 64, 83, 96, 113, 137],
        categories: [
            { name: 'TD/TS', range: '< 64 kt', color: '#5ebaff' },
            { name: 'Category 1', range: '64-82 kt', color: '#00faf4' },
            { name: 'Category 2', range: '83-95 kt', color: '#ffffcc' },
            { name: 'Category 3', range: '96-112 kt', color: '#ffe775' },
            { name: 'Category 4', range: '113-136 kt', color: '#ffc140' },
            { name: 'Category 5', range: '≥ 137 kt', color: '#ff8f20' }
        ],
        textColors: ['#000', '#000', '#000', '#ff8c00', '#ff6600', '#ff0000']
    }
};

BASIN_SCALES.EP = BASIN_SCALES.AL;
BASIN_SCALES.CP = BASIN_SCALES.AL;
BASIN_SCALES.WP = BASIN_SCALES.AL;

function initStormMap(stormId) {
    const mapContainer = document.querySelector('[data-storm-id]');
    currentBasin = mapContainer?.dataset.basin || 'WP';
    
    map = new maplibregl.Map({
        container: 'storm-map',
        style: 'https://basemaps.cartocdn.com/gl/positron-gl-style/style.json',
        center: [0, 0],
        zoom: 2
    });

    map.addControl(new maplibregl.NavigationControl(), 'top-right');
    map.addControl(new maplibregl.ScaleControl({ unit: 'nautical' }), 'bottom-left');
    map.addControl(new maplibregl.FullscreenControl(), 'top-right');

    map.on('load', () => {
        addLegend();
        loadStormData(stormId);
    });
}

function addLegend() {
    const scale = BASIN_SCALES[currentBasin];
    const legendDiv = document.createElement('div');
    legendDiv.style.cssText = 'position: absolute; top: 20px; left: 20px; background: white; padding: 1rem; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.15); z-index: 1000; font-family: system-ui; max-width: 280px;';
    
    let html = `<div style="font-weight: bold; margin-bottom: 0.75rem; font-size: 0.9rem;">${scale.name.toUpperCase()}</div>`;
    scale.categories.forEach(cat => {
        html += `<div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem;"><div style="width: 20px; height: 20px; background: ${cat.color}; border-radius: 50%; border: 2px solid white;"></div><span style="font-size: 0.85rem;">${cat.name} ${cat.range}</span></div>`;
    });
    html += `<div style="border-top: 1px solid #e5e7eb; padding-top: 0.75rem; margin-top: 0.75rem;"><div style="font-weight: 600; margin-bottom: 0.5rem; font-size: 0.85rem;">TRACK</div><div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.25rem;"><div style="width: 30px; height: 3px; background: linear-gradient(90deg, #5ebaff, #ff8f20);"></div><span style="font-size: 0.8rem;">Observed Track (Category Colored)</span></div><div style="display: flex; align-items: center; gap: 0.5rem;"><div style="width: 30px; height: 3px; background: #3b82f6; opacity: 0.5;"></div><span style="font-size: 0.8rem;">Forecast Track (50% opacity)</span></div></div>`;
    legendDiv.innerHTML = html;
    map.getContainer().appendChild(legendDiv);
}

async function loadStormData(stormId) {
    try {
        const response = await fetch(`/api/storms/${stormId}/track`);
        const data = await response.json();
        if (!data.track || data.track.length === 0) return;
        stormData = data;
        
        const latest = data.track[data.track.length - 1];
        document.getElementById('current-vmax').textContent = `${latest.vmax_kt || '--'} kt`;
        document.getElementById('current-mslp').textContent = `${latest.mslp_hpa || '--'} mb`;
        document.getElementById('current-position').textContent = `${latest.latitude.toFixed(2)}°, ${latest.longitude.toFixed(2)}°`;
        document.getElementById('current-category').textContent = getCategoryName(latest.vmax_kt);
        
        plotTrack(data.track);
        addWindRadiiToggle();
        fitMapToTrack(data.track);
    } catch (error) {
        console.error('Error:', error);
    }
}

function addWindRadiiToggle() {
    const toggleBtn = document.createElement('button');
    toggleBtn.id = 'wind-radii-toggle';
    toggleBtn.style.cssText = 'position: absolute; top: 20px; left: 400px; background: white; border: 2px solid #3b82f6; border-radius: 12px; padding: 18px 32px; box-shadow: 0 4px 16px rgba(0,0,0,0.25); cursor: pointer; font-weight: 700; font-size: 18px; z-index: 1000; transition: all 0.2s;';
    toggleBtn.innerHTML = '🌬️ Wind Radii: ON';
    toggleBtn.onmouseover = () => {
        toggleBtn.style.transform = 'scale(1.05)';
        toggleBtn.style.boxShadow = '0 6px 20px rgba(0,0,0,0.3)';
    };
    toggleBtn.onmouseout = () => {
        toggleBtn.style.transform = 'scale(1)';
        toggleBtn.style.boxShadow = '0 4px 16px rgba(0,0,0,0.25)';
    };
    toggleBtn.onclick = toggleWindRadii;
    map.getContainer().appendChild(toggleBtn);
}

let windRadiiVisible = true;

function toggleWindRadii() {
    windRadiiVisible = !windRadiiVisible;
    const btn = document.getElementById('wind-radii-toggle');
    btn.innerHTML = `🌬️ Wind Radii: ${windRadiiVisible ? 'ON' : 'OFF'}`;
    
    const layers = ['wind-radii-34', 'wind-radii-50', 'wind-radii-64'];
    layers.forEach(layer => {
        if (map.getLayer(layer)) {
            map.setLayoutProperty(layer, 'visibility', windRadiiVisible ? 'visible' : 'none');
        }
    });
}

function renderWindRadii(track) {
    console.log('🌬️ Rendering wind radii for', track.length, 'points');
    
    // Remove existing radii layers
    ['wind-radii-34', 'wind-radii-50', 'wind-radii-64'].forEach(id => {
        if (map.getLayer(id)) map.removeLayer(id);
        if (map.getSource(id)) map.removeSource(id);
    });
    
    const keyPoints = selectKeyPoints(track);
    console.log('🔑 Key points:', keyPoints.length);
    
    // Create quadrant wedges for each key point
    const radii34Features = [];
    const radii50Features = [];
    const radii64Features = [];
    
    keyPoints.forEach((point, idx) => {
        console.log(`Point ${idx}:`, {
            lat: point.latitude,
            lon: point.longitude,
            vmax: point.vmax_kt,
            hasRadii: !!point.radii,
            radii: point.radii
        });
        
        if (!point.radii) {
            console.log(`⚠️ No radii data for point ${idx}`);
            return;
        }
        
        const isLatest = point.isLatest;
        const baseOpacity = isLatest ? 1.0 : 0.05;
        
        // Each quadrant is a wedge (pie slice)
        const quadrants = {
            'NE': { start: 0, end: 90 },
            'SE': { start: 90, end: 180 },
            'SW': { start: 180, end: 270 },
            'NW': { start: 270, end: 360 }
        };
        
        Object.entries(quadrants).forEach(([quad, angles]) => {
            const quadRadii = point.radii[quad];
            if (!quadRadii) {
                console.log(`⚠️ No radii for quadrant ${quad}`);
                return;
            }
            
            console.log(`✓ ${quad} radii:`, quadRadii);
            
            if (quadRadii.r34_nm && quadRadii.r34_nm > 0) {
                const wedge = createWedge(
                    point.longitude, point.latitude,
                    quadRadii.r34_nm, angles.start, angles.end,
                    baseOpacity * 0.1
                );
                radii34Features.push(wedge);
                console.log(`  + Added R34 wedge (${quadRadii.r34_nm}nm)`);
            }
            
            if (quadRadii.r50_nm && quadRadii.r50_nm > 0) {
                const wedge = createWedge(
                    point.longitude, point.latitude,
                    quadRadii.r50_nm, angles.start, angles.end,
                    baseOpacity * 0.3
                );
                radii50Features.push(wedge);
                console.log(`  + Added R50 wedge (${quadRadii.r50_nm}nm)`);
            }
            
            if (quadRadii.r64_nm && quadRadii.r64_nm > 0) {
                const wedge = createWedge(
                    point.longitude, point.latitude,
                    quadRadii.r64_nm, angles.start, angles.end,
                    baseOpacity * 0.8
                );
                radii64Features.push(wedge);
                console.log(`  + Added R64 wedge (${quadRadii.r64_nm}nm)`);
            }
        });
    });
    
    console.log('📊 Total features:', {
        r34: radii34Features.length,
        r50: radii50Features.length,
        r64: radii64Features.length
    });
    
    // Add R34 layer (lightest, below others)
    if (radii34Features.length > 0) {
        map.addSource('wind-radii-34', {
            type: 'geojson',
            data: { type: 'FeatureCollection', features: radii34Features }
        });
        map.addLayer({
            id: 'wind-radii-34',
            type: 'fill',
            source: 'wind-radii-34',
            paint: {
                'fill-color': '#DC143C',
                'fill-opacity': ['get', 'opacity']
            }
        }, 'storm-track-glow'); // Insert below track
        console.log('✅ Added R34 layer');
    }
    
    // Add R50 layer
    if (radii50Features.length > 0) {
        map.addSource('wind-radii-50', {
            type: 'geojson',
            data: { type: 'FeatureCollection', features: radii50Features }
        });
        map.addLayer({
            id: 'wind-radii-50',
            type: 'fill',
            source: 'wind-radii-50',
            paint: {
                'fill-color': '#DC143C',
                'fill-opacity': ['get', 'opacity']
            }
        }, 'storm-track-glow');
        console.log('✅ Added R50 layer');
    }
    
    // Add R64 layer (darkest, on top)
    if (radii64Features.length > 0) {
        map.addSource('wind-radii-64', {
            type: 'geojson',
            data: { type: 'FeatureCollection', features: radii64Features }
        });
        map.addLayer({
            id: 'wind-radii-64',
            type: 'fill',
            source: 'wind-radii-64',
            paint: {
                'fill-color': '#DC143C',
                'fill-opacity': ['get', 'opacity']
            }
        }, 'storm-track-glow');
        console.log('✅ Added R64 layer');
    }
    
    if (radii34Features.length === 0 && radii50Features.length === 0 && radii64Features.length === 0) {
        console.error('❌ NO WIND RADII RENDERED - Check if API is returning radii data');
    }
}

function createWedge(lon, lat, radiusNm, startAngle, endAngle, opacity) {
    // Convert nautical miles to degrees (rough approximation)
    const radiusDeg = radiusNm * 0.0167;
    
    const coordinates = [[lon, lat]];
    
    // Create arc
    for (let angle = startAngle; angle <= endAngle; angle += 5) {
        const rad = (angle * Math.PI) / 180;
        const x = lon + radiusDeg * Math.cos(rad);
        const y = lat + radiusDeg * Math.sin(rad);
        coordinates.push([x, y]);
    }
    
    // Close the wedge
    coordinates.push([lon, lat]);
    
    return {
        type: 'Feature',
        geometry: {
            type: 'Polygon',
            coordinates: [coordinates]
        },
        properties: { opacity }
    };
}

function getCategory(vmax) {
    const scale = BASIN_SCALES[currentBasin];
    const thresholds = scale.thresholds;
    
    // thresholds for SH/IO: [34, 48, 64, 87, 108]
    // categories: [0=Low, 1=Cat1, 2=Cat2, 3=Cat3, 4=Cat4, 5=Cat5]
    
    if (vmax < thresholds[1]) return 0;  // < 48kt = Tropical Low/TS (Category 0)
    if (vmax < thresholds[2]) return 1;  // 48-63kt = Category 1
    if (vmax < thresholds[3]) return 2;  // 64-86kt = Category 2
    if (vmax < thresholds[4]) return 3;  // 87-107kt = Category 3
    if (vmax < 140) return 4;  // 108-139kt = Category 4
    return 5;  // 140+ = Category 5
}

function getCategoryText(vmax) {
    const cat = getCategory(vmax);
    if (cat === 0) return 'LOW';
    return cat.toString();
}

function getCategoryName(vmax) {
    const cat = getCategory(vmax);
    return BASIN_SCALES[currentBasin].categories[cat].name;
}

function getCategoryColor(cat) {
    return BASIN_SCALES[currentBasin].categories[cat].color;
}

function catmullRomSpline(points, numSegments = 15) {
    if (points.length < 3) return points;
    const smoothed = [points[0]];
    for (let i = 0; i < points.length - 1; i++) {
        const p0 = points[Math.max(0, i - 1)];
        const p1 = points[i];
        const p2 = points[i + 1];
        const p3 = points[Math.min(points.length - 1, i + 2)];
        for (let t = 0; t < numSegments; t++) {
            const t1 = t / numSegments, t2 = t1 * t1, t3 = t2 * t1;
            smoothed.push([
                0.5 * ((2 * p1[0]) + (-p0[0] + p2[0]) * t1 + (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2 + (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3),
                0.5 * ((2 * p1[1]) + (-p0[1] + p2[1]) * t1 + (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2 + (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3)
            ]);
        }
    }
    smoothed.push(points[points.length - 1]);
    return smoothed;
}

function selectKeyPoints(track) {
    const keyPoints = [];
    let lastCat = null, lastTime = null;
    track.forEach((p, i) => {
        const cat = getCategory(p.vmax_kt || 0);
        const time = new Date(p.time);
        if (i === 0 || i === track.length - 1 || cat !== lastCat || (lastTime && (time - lastTime) / 3600000 >= 6)) {
            keyPoints.push({...p, isLatest: i === track.length - 1});
            lastCat = cat;
            lastTime = time;
        }
    });
    return keyPoints;
}

function plotTrack(track) {
    const scale = BASIN_SCALES[currentBasin];
    
    // Create line segments colored by category
    const trackSegments = [];
    for (let i = 0; i < track.length - 1; i++) {
        const cat = getCategory(track[i].vmax_kt || 0);
        const color = scale.categories[cat].color;
        
        trackSegments.push({
            type: 'Feature',
            geometry: {
                type: 'LineString',
                coordinates: [
                    [track[i].longitude, track[i].latitude],
                    [track[i + 1].longitude, track[i + 1].latitude]
                ]
            },
            properties: {
                category: cat,
                color: color,
                vmax: track[i].vmax_kt || 0
            }
        });
    }
    
    map.addSource('storm-track-segments', {
        type: 'geojson',
        data: {
            type: 'FeatureCollection',
            features: trackSegments
        }
    });
    
    map.addLayer({
        id: 'storm-track-glow',
        type: 'line',
        source: 'storm-track-segments',
        paint: {
            'line-color': ['get', 'color'],
            'line-width': 8,
            'line-blur': 4,
            'line-opacity': 0.4
        }
    });
    
    map.addLayer({
        id: 'storm-track-line',
        type: 'line',
        source: 'storm-track-segments',
        paint: {
            'line-color': ['get', 'color'],
            'line-width': 3
        }
    });
    
    const keyPoints = selectKeyPoints(track);
    
    // Add small circles for non-latest key points
    const nonLatestPoints = keyPoints.filter(p => !p.isLatest);
    map.addSource('storm-points', { 
        type: 'geojson', 
        data: { 
            type: 'FeatureCollection', 
            features: nonLatestPoints.map(p => ({ 
                type: 'Feature', 
                geometry: { type: 'Point', coordinates: [p.longitude, p.latitude]}, 
                properties: { 
                    category: getCategory(p.vmax_kt || 0),
                    time: p.time,
                    vmax: p.vmax_kt || 0,
                    mslp: p.mslp_hpa || 0
                }
            }))
        }
    });
    
    map.addLayer({ 
        id: 'storm-points-layer', 
        type: 'circle', 
        source: 'storm-points', 
        paint: { 
            'circle-radius': 6, 
            'circle-color': ['match', ['get', 'category'], 0, scale.categories[0].color, 1, scale.categories[1].color, 2, scale.categories[2].color, 3, scale.categories[3].color, 4, scale.categories[4].color, 5, scale.categories[5].color, '#5ebaff'], 
            'circle-stroke-width': 2, 
            'circle-stroke-color': '#fff'
        }
    });
    
    map.on('click', 'storm-points-layer', (e) => {
        const props = e.features[0].properties;
        const date = new Date(props.time);
        
        new maplibregl.Popup()
            .setLngLat(e.features[0].geometry.coordinates)
            .setHTML(`
                <div style="padding: 0.75rem; min-width: 220px; font-family: system-ui;">
                    <strong style="font-size: 1.1rem; color: #1e40af;">${date.toUTCString()}</strong><br><br>
                    <div style="display: grid; grid-template-columns: auto 1fr; gap: 0.5rem 1rem;">
                        <strong>Winds:</strong> <span>${props.vmax} kt</span>
                        <strong>Pressure:</strong> <span>${props.mslp} mb</span>
                        <strong>Category:</strong> <span>${getCategoryName(props.vmax)}</span>
                    </div>
                </div>
            `)
            .addTo(map);
    });
    
    map.on('mouseenter', 'storm-points-layer', () => {
        map.getCanvas().style.cursor = 'pointer';
    });
    
    map.on('mouseleave', 'storm-points-layer', () => {
        map.getCanvas().style.cursor = '';
    });
    
    // Add markers ONLY at key points (already filtered by selectKeyPoints)
    keyPoints.forEach(point => {
        const vmax = point.vmax_kt || 0;
        const isCycloneStrength = vmax >= scale.thresholds[1];
        
        if (!isCycloneStrength) {
            addLowMarker(point);
        } else {
            addCycloneEye(point, point.isLatest);
        }
    });
    
    // Render wind radii AFTER track but BEFORE tc-eye markers
    renderWindRadii(track);
}

function addCycloneEye(point, isLatest) {
    const vmax = point.vmax_kt || 0;
    const cat = getCategory(vmax);
    const scale = BASIN_SCALES[currentBasin];
    const isCycloneStrength = vmax >= scale.thresholds[1];
    
    if (!isCycloneStrength) {
        return;
    }
    
    const text = getCategoryText(vmax);
    const color = scale.textColors[cat];
    const el = document.createElement('div');
    el.style.cssText = 'width: 80px; height: 80px; cursor: pointer;';
    
    // Determine rotation direction based on hemisphere
    const isNorthernHemisphere = point.latitude >= 0;
    const rotationDirection = isNorthernHemisphere ? 'counter-clockwise' : 'clockwise';
    
    // Rotating animation ONLY for latest position
    let rotationStyle = '';
    if (isLatest) {
        const animationName = isNorthernHemisphere ? 'rotate-ccw' : 'rotate-cw';
        rotationStyle = `animation: ${animationName} 6s linear infinite;`;
    }
    
    el.innerHTML = `
        <div style="position: relative; width: 80px; height: 80px;">
            <img src="/static/img/tc-eye.png" style="width: 80px; height: 80px; ${rotationStyle}">
            <div style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); font-weight: bold; font-size: 18px; color: ${color}; text-shadow: 0 0 3px white, 0 0 3px white;">
                ${text}
            </div>
        </div>
    `;
    
    if (!document.getElementById('cyclone-eye-animation')) {
        const style = document.createElement('style');
        style.id = 'cyclone-eye-animation';
        style.innerHTML = `
            @keyframes rotate-cw { 
                from { transform: rotate(0deg); } 
                to { transform: rotate(360deg); } 
            }
            @keyframes rotate-ccw { 
                from { transform: rotate(0deg); } 
                to { transform: rotate(-360deg); } 
            }
        `;
        document.head.appendChild(style);
    }
    
    el.addEventListener('click', () => {
        const date = new Date(point.time);
        new maplibregl.Popup()
            .setLngLat([point.longitude, point.latitude])
            .setHTML(`
                <div style="padding: 1rem; min-width: 240px; font-family: system-ui;">
                    <strong style="font-size: 1.2rem; color: #1e40af;">${isLatest ? 'CURRENT POSITION' : 'HISTORICAL POSITION'}</strong><br>
                    <em style="color: #64748b;">${date.toUTCString()}</em><br><br>
                    <div style="display: grid; grid-template-columns: auto 1fr; gap: 0.5rem 1rem;">
                        <strong>Winds:</strong> <span>${point.vmax_kt} kt</span>
                        <strong>Pressure:</strong> <span>${point.mslp_hpa} mb</span>
                        <strong>Category:</strong> <span>${getCategoryName(point.vmax_kt)}</span>
                        <strong>Position:</strong> <span>${point.latitude.toFixed(2)}°, ${point.longitude.toFixed(2)}°</span>
                    </div>
                </div>
            `)
            .addTo(map);
    });
    
    new maplibregl.Marker({element: el, anchor: 'center'}).setLngLat([point.longitude, point.latitude]).addTo(map);
}

function addLowMarker(point) {
    const el = document.createElement('div');
    el.style.cssText = 'width: 60px; height: 60px; cursor: pointer;';
    
    el.innerHTML = `
        <div style="position: relative; width: 60px; height: 60px; background: rgba(94, 186, 255, 0.3); border: 2px solid #5ebaff; border-radius: 50%; display: flex; align-items: center; justify-content: center;">
            <div style="font-weight: bold; font-size: 14px; color: #000; text-shadow: 0 0 3px white, 0 0 3px white;">
                LOW
            </div>
        </div>
    `;
    
    el.addEventListener('click', () => {
        const date = new Date(point.time);
        new maplibregl.Popup()
            .setLngLat([point.longitude, point.latitude])
            .setHTML(`
                <div style="padding: 1rem; min-width: 240px; font-family: system-ui;">
                    <strong style="font-size: 1.2rem; color: #1e40af;">SUB-CYCLONE STRENGTH</strong><br>
                    <em style="color: #64748b;">${date.toUTCString()}</em><br><br>
                    <div style="display: grid; grid-template-columns: auto 1fr; gap: 0.5rem 1rem;">
                        <strong>Winds:</strong> <span>${point.vmax_kt || 0} kt</span>
                        <strong>Pressure:</strong> <span>${point.mslp_hpa || 0} mb</span>
                        <strong>Status:</strong> <span>Tropical Low</span>
                        <strong>Position:</strong> <span>${point.latitude.toFixed(2)}°, ${point.longitude.toFixed(2)}°</span>
                    </div>
                </div>
            `)
            .addTo(map);
    });
    
    new maplibregl.Marker({element: el, anchor: 'center'}).setLngLat([point.longitude, point.latitude]).addTo(map);
}

function fitMapToTrack(track) {
    if (!track || track.length === 0) return;
    
    // Get the latest position (current location)
    const latest = track[track.length - 1];
    
    // Center on current position with zoom level 6
    map.flyTo({
        center: [latest.longitude, latest.latitude],
        zoom: 6,
        duration: 1500,
        essential: true
    });
}

document.addEventListener('DOMContentLoaded', () => {
    const id = document.querySelector('[data-storm-id]')?.dataset.stormId;
    if (id) initStormMap(id);
});