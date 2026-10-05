// Client-side interactions and dynamic form helpers

document.addEventListener('DOMContentLoaded', () => {
    // Auto-dismiss flash alerts after 6 seconds
    const alerts = document.querySelectorAll('.alert');
    if (alerts.length > 0) {
        setTimeout(() => {
            alerts.forEach(alert => {
                alert.style.transition = 'opacity 0.5s ease';
                alert.style.opacity = '0';
                setTimeout(() => alert.remove(), 500);
            });
        }, 6000);
    }
});
