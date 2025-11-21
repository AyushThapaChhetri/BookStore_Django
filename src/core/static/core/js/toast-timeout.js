document.addEventListener("DOMContentLoaded", () => {
    const toasts = document.querySelectorAll("#toast-success, #toast-danger,#toast-warning");
    toasts.forEach((toast) => {

        // Get the message text inside the toast
        // const message = toast.querySelector(".text-sm.font-normal")?.textContent.trim();
        // console.log("Active toast found:", {
        //     type: toast.id, // toast-success, toast-danger, or toast-warning
        //     message: message
        // });


        setTimeout(() => {
            toast.remove();
        }, 3000);
    });
});