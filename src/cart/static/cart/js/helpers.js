async function updateCartCount() {
    try {
        let response = await axios.get('/carts/count/');

        let data = await response.data.count;
        const cartCount = document.querySelector("#cart-count");
        if (cartCount) {
            cartCount.innerHTML = data.count;
        }

    } catch (e) {
        console.log(e);
        alert(`error occured`);
    }
}

