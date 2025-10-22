// Time Controls - Track animation and time slider

let timeControls = {
    currentIndex: 0,
    maxIndex: 0,
    isPlaying: false,
    playbackSpeed: 1000, // ms per step
    timePoints: [],
    playInterval: null
};

// Initialize time controls
function initTimeControls(advisories, forecastPoints) {
    // Combine advisories and forecast points with timestamps
    timeControls.timePoints = [
        ...advisories.map(a => ({
            timestamp: new Date(a.issued_at_utc),
            type: 'advisory',
            data: a
        })),
        ...forecastPoints.map(f => ({
            timestamp: new Date(f.valid_at),
            type: 'forecast',
            data: f
        }))
    ].sort((a, b) => a.timestamp - b.timestamp);
    
    timeControls.maxIndex = timeControls.timePoints.length - 1;
    timeControls.currentIndex = advisories.length - 1; // Start at latest advisory
    
    setupTimeSlider();
    setupTimeButtons();
    updateTimeDisplay();
}

// Setup time slider
function setupTimeSlider() {
    const slider = document.getElementById('time-slider');
    if (!slider) return;
    
    slider.min = 0;
    slider.max = timeControls.maxIndex;
    slider.value = timeControls.currentIndex;
    
    slider.addEventListener('input', function(e) {
        timeControls.currentIndex = parseInt(e.target.value);
        updateTimeDisplay();
        updateMapForTime();
        
        // Pause playback when slider is moved manually
        if (timeControls.isPlaying) {
            pausePlayback();
        }
    });
}

// Setup time control buttons
function setupTimeButtons() {
    const playBtn = document.getElementById('play-btn');
    const pauseBtn = document.getElementById('pause-btn');
    const prevBtn = document.getElementById('prev-btn');
    const nextBtn = document.getElementById('next-btn');
    const resetBtn = document.getElementById('reset-btn');
    
    if (playBtn) {
        playBtn.addEventListener('click', startPlayback);
    }
    
    if (pauseBtn) {
        pauseBtn.addEventListener('click', pausePlayback);
    }
    
    if (prevBtn) {
        prevBtn.addEventListener('click', previousTimeStep);
    }
    
    if (nextBtn) {
        nextBtn.addEventListener('click', nextTimeStep);
    }
    
    if (resetBtn) {
        resetBtn.addEventListener('click', resetToStart);
    }
}

// Playback controls
function startPlayback() {
    if (timeControls.isPlaying) return;
    
    timeControls.isPlaying = true;
    updatePlaybackButtons();
    
    timeControls.playInterval = setInterval(() => {
        if (timeControls.currentIndex < timeControls.maxIndex) {
            timeControls.currentIndex++;
            updateTimeDisplay();
            updateTimeSlider();
            updateMapForTime();
        } else {
            // Loop back to start
            pausePlayback();
        }
    }, timeControls.playbackSpeed);
}

function pausePlayback() {
    if (!timeControls.isPlaying) return;
    
    timeControls.isPlaying = false;
    updatePlaybackButtons();
    
    if (timeControls.playInterval) {
        clearInterval(timeControls.playInterval);
        timeControls.playInterval = null;
    }
}

function previousTimeStep() {
    if (timeControls.currentIndex > 0) {
        timeControls.currentIndex--;
        updateTimeDisplay();
        updateTimeSlider();
        updateMapForTime();
    }
}

function nextTimeStep() {
    if (timeControls.currentIndex < timeControls.maxIndex) {
        timeControls.currentIndex++;
        updateTimeDisplay();
        updateTimeSlider();
        updateMapForTime();
    }
}

function resetToStart() {
    timeControls.currentIndex = 0;
    updateTimeDisplay();
    updateTimeSlider();
    updateMapForTime();
    
    if (timeControls.isPlaying) {
        pausePlayback();
    }
}

// Jump to specific time
function jumpToTime(index) {
    if (index >= 0 && index <= timeControls.maxIndex) {
        timeControls.currentIndex = index;
        updateTimeDisplay();
        updateTimeSlider();
        updateMapForTime();
    }
}

// Update UI
function updateTimeDisplay() {
    const display = document.getElementById('time-display');
    if (!display || timeControls.timePoints.length === 0) return;
    
    const current = timeControls.timePoints[timeControls.currentIndex];
    const dateStr = current.timestamp.toUTCString();
    const typeStr = current.type === 'advisory' ? 'Advisory' : 'Forecast';
    
    display.innerHTML = `
        <div style="font-size: 0.875rem; color: #6b7280;">${typeStr}</div>
        <div style="font-size: 0.9375rem; font-weight: 600;">${dateStr}</div>
        <div style="font-size: 0.75rem; color: #9ca3af; margin-top: 0.25rem;">
            ${timeControls.currentIndex + 1} / ${timeControls.maxIndex + 1}
        </div>
    `;
}

function updateTimeSlider() {
    const slider = document.getElementById('time-slider');
    if (slider) {
        slider.value = timeControls.currentIndex;
    }
}

function updatePlaybackButtons() {
    const playBtn = document.getElementById('play-btn');
    const pauseBtn = document.getElementById('pause-btn');
    
    if (playBtn) {
        playBtn.style.display = timeControls.isPlaying ? 'none' : 'block';
    }
    
    if (pauseBtn) {
        pauseBtn.style.display = timeControls.isPlaying ? 'block' : 'none';
    }
}

// Update map for current time
function updateMapForTime() {
    if (typeof map === 'undefined' || !map) return;
    
    const current = timeControls.timePoints[timeControls.currentIndex];
    
    // Filter track points up to current time
    const visibleAdvisories = timeControls.timePoints
        .filter((p, i) => i <= timeControls.currentIndex && p.type === 'advisory')
        .map(p => p.data);
    
    const visibleForecast = timeControls.timePoints
        .filter((p, i) => i <= timeControls.currentIndex && p.type === 'forecast')
        .map(p => p.data);
    
    // Update map sources
    updateTrackLayer(map, visibleAdvisories, visibleForecast);
    
    // Center map on current position
    if (current.data.latitude && current.data.longitude) {
        map.easeTo({
            center: [current.data.longitude, current.data.latitude],
            duration: 500
        });
    }
}

function updateTrackLayer(map, advisories, forecast) {
    // Update past track
    if (map.getSource('past-track')) {
        const pastFeatures = advisories.map(a => ({
            type: 'Feature',
            geometry: {
                type: 'Point',
                coordinates: [a.longitude, a.latitude]
            },
            properties: {
                time: a.issued_at_utc,
                vmax_kt: a.vmax_kt,
                category: a.intensity_category
            }
        }));
        
        map.getSource('past-track').setData({
            type: 'FeatureCollection',
            features: pastFeatures
        });
    }
    
    // Update forecast track
    if (map.getSource('forecast-track')) {
        const forecastFeatures = forecast.map(f => ({
            type: 'Feature',
            geometry: {
                type: 'Point',
                coordinates: [f.longitude, f.latitude]
            },
            properties: {
                valid_at: f.valid_at,
                vmax_kt: f.vmax_kt,
                category: f.intensity_category
            }
        }));
        
        map.getSource('forecast-track').setData({
            type: 'FeatureCollection',
            features: forecastFeatures
        });
    }
}

// Speed controls
function setPlaybackSpeed(speed) {
    // speed in range 0.5x to 4x
    timeControls.playbackSpeed = 1000 / speed;
    
    // Restart playback if currently playing
    if (timeControls.isPlaying) {
        pausePlayback();
        startPlayback();
    }
}

// Export time controls
window.timeControls = {
    init: initTimeControls,
    play: startPlayback,
    pause: pausePlayback,
    next: nextTimeStep,
    prev: previousTimeStep,
    reset: resetToStart,
    jumpTo: jumpToTime,
    setSpeed: setPlaybackSpeed,
    getCurrentTime: () => timeControls.timePoints[timeControls.currentIndex],
    getCurrentIndex: () => timeControls.currentIndex,
    isPlaying: () => timeControls.isPlaying
};
