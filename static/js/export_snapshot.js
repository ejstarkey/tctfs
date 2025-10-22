// Export map snapshot as PNG

function exportMapSnapshot() {
    if (!map) {
        console.error('Map not initialized');
        return;
    }
    
    // Get map canvas
    const canvas = map.getCanvas();
    
    // Create a new canvas with legend
    const exportCanvas = document.createElement('canvas');
    exportCanvas.width = canvas.width;
    exportCanvas.height = canvas.height;
    
    const ctx = exportCanvas.getContext('2d');
    
    // Draw map
    ctx.drawImage(canvas, 0, 0);
    
    // Add timestamp watermark
    ctx.font = '14px Arial';
    ctx.fillStyle = 'rgba(255, 255, 255, 0.8)';
    ctx.fillRect(10, canvas.height - 30, 200, 20);
    ctx.fillStyle = '#000';
    ctx.fillText(new Date().toISOString(), 15, canvas.height - 15);
    
    // Convert to blob and download
    exportCanvas.toBlob(function(blob) {
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.download = `storm-${stormId}-${Date.now()}.png`;
        link.href = url;
        link.click();
        URL.revokeObjectURL(url);
    });
}

// Add export button if not exists
document.addEventListener('DOMContentLoaded', function() {
    const mapContainer = document.getElementById('storm-map');
    if (mapContainer) {
        const exportBtn = document.createElement('button');
        exportBtn.textContent = 'Export PNG';
        exportBtn.className = 'export-btn';
        exportBtn.onclick = exportMapSnapshot;
        
        // TODO: Position button properly
    }
});
