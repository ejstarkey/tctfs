// Main app JS
document.addEventListener('DOMContentLoaded', function() {
    // User menu dropdown
    const userMenuBtn = document.getElementById('user-menu-button');
    const userMenuDropdown = document.getElementById('user-menu-dropdown');
    
    if (userMenuBtn && userMenuDropdown) {
        userMenuBtn.addEventListener('click', function(e) {
            e.stopPropagation();
            userMenuDropdown.classList.toggle('hidden');
        });
        
        document.addEventListener('click', function() {
            userMenuDropdown.classList.add('hidden');
        });
    }
});
