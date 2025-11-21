document.addEventListener('DOMContentLoaded', () => {
    // console.log("prevent-multi-form-submit.js loaded");
    document.querySelectorAll('form').forEach(form => {
        const submitBtn = form.querySelector('button[type="submit"], input[type="submit"]');
        // console.log("Button found:", submitBtn)
        if (!submitBtn) return;

        form.addEventListener('submit', () => {
            submitBtn.disabled = true;
            submitBtn.innerText = 'Submitting...';
        });
    });
});