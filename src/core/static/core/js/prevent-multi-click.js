document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('button.prevent-multi-click').forEach(button => {
        button.addEventListener('click', () => {
            if (button.disabled) return; // Prevent double binding

            // Save original text in case you want to restore later
            const originalText = button.innerText;

            button.disabled = true;
            button.innerText = 'Processing...';

            // Submit the form
            const form = button.closest('form');
            if (form) {
                form.submit();
            }

            // Optional: auto-enable after 3 seconds
            setTimeout(() => {
                button.disabled = false;
                button.innerText = originalText;
            }, 5000);
        });
    });
});
