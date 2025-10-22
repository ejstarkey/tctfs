// Forms JavaScript

document.addEventListener('DOMContentLoaded', function() {
    initForms();
});

function initForms() {
    // Logout forms
    document.querySelectorAll('.logout-form').forEach(form => {
        form.addEventListener('submit', handleLogout);
    });
    
    // Subscribe button
    const subscribeBtn = document.getElementById('subscribe-btn');
    if (subscribeBtn) {
        subscribeBtn.addEventListener('click', handleSubscribe);
    }
    
    // Unsubscribe buttons
    document.querySelectorAll('.unsubscribe-btn').forEach(btn => {
        btn.addEventListener('click', handleUnsubscribe);
    });
    
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
}

async function handleLogout(event) {
    event.preventDefault();
    
    try {
        const response = await fetch('/api/auth/logout', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        if (response.ok) {
            window.location.href = '/';
        }
    } catch (error) {
        console.error('Logout error:', error);
    }
}

async function handleSubscribe(event) {
    event.preventDefault();
    
    const btn = event.currentTarget;
    const stormId = btn.dataset.stormId;
    const isSubscribed = btn.dataset.subscribed === 'true';
    
    if (isSubscribed) {
        // Unsubscribe
        // TODO: Get subscription ID and delete
        console.log('Unsubscribe from storm:', stormId);
    } else {
        // Subscribe
        try {
            const response = await fetch('/api/subscriptions', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    storm_id: stormId,
                    mode: 'immediate',
                    alert_on_new_advisory: true,
                    alert_on_zone_change: true
                })
            });
            
            if (response.ok) {
                window.location.reload();
            }
        } catch (error) {
            console.error('Subscribe error:', error);
        }
    }
}

async function handleUnsubscribe(event) {
    event.preventDefault();
    
    const subscriptionId = this.dataset.subscriptionId;
    
    if (!confirm('Are you sure you want to unsubscribe?')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/subscriptions/${subscriptionId}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            window.location.reload();
        }
    } catch (error) {
        console.error('Unsubscribe error:', error);
    }
}
