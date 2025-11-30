// console.log("Reusable stock table JS loaded");

function setupStockTable({formId, tableId, paginationId}) {
    const form = document.getElementById(formId);
    const tableContainer = document.getElementById(tableId);
    const paginationContainer = document.getElementById(paginationId);

    if (!form || !tableContainer || !paginationContainer) {
        console.error("Form or table or pagination container missing");
        return;
    }

    function buildQueryFromForm(form, includeDates = true) {
        const params = new URLSearchParams();
        new FormData(form).forEach((value, key) => {
            if (!value) return;
            if (!includeDates && (key.endsWith("_from") || key.endsWith("_to"))) return;
            params.append(key, value);
        });
        console.log("Built query:", params.toString());
        return params.toString();
    }

    function updateUrl(query) {
        const url = `${window.location.pathname}?${query}`;
        console.log("Updating URL to:", url);
        window.history.replaceState(null, "", url);
    }

    async function fetchTableData({url, attachPagination}) {
        console.log("Fetching URL:", url);


        const errorSpans = form.querySelectorAll("span.text-red-500");
        errorSpans.forEach(span => span.innerText = "");

        try {

            const response = await axios.get(`${url}&ajax=1`);
            const data = response.data;

            tableContainer.innerHTML = data.table_html;
            paginationContainer.innerHTML = data.pagination_html;

            if (typeof attachPagination === "function") attachPagination();
        } catch (err) {
            console.error("AJAX Error:", err);

            if (err.response && err.response.data.errors) {

                const errors = err.response.data.errors;
                Object.keys(errors).forEach(field => {

                    const errorSpan = form.querySelector(`#${field}_error`);
                    if (errorSpan) errorSpan.innerText = errors[field];
                });
            }


        }
    }

    function debounce(func, wait = 700) {
        let timeout;
        return function (...args) {
            clearTimeout(timeout);
            timeout = setTimeout(() => func.apply(this, args), wait);
        };
    }

    function attachPaginationEvents(fetchFunction) {
        const paginationLinks = paginationContainer.querySelectorAll(".ajax-page");
        paginationLinks.forEach(link => {
            link.addEventListener("click", function (e) {
                e.preventDefault();


                const url = new URL(this.href, window.location.origin);
                const page = url.searchParams.get("page");


                const queryParams = new URLSearchParams(new FormData(form));
                if (page) queryParams.set("page", page);

                const fullUrl = `${window.location.pathname}?${queryParams.toString()}`;
                updateUrl(queryParams.toString());
                fetchFunction(fullUrl);
            });
        });
    }

    const fetchData = (includeDates = false) => {
        const query = buildQueryFromForm(form, includeDates);


        updateUrl(query);
        const url = `${window.location.pathname}?${query}`;
        return fetchTableData({
            url,
            attachPagination: () => attachPaginationEvents(fetchDataWithUrl)
        });
    };

    const fetchDataWithUrl = (url) => fetchTableData({
        url,
        attachPagination: () => attachPaginationEvents(fetchDataWithUrl)
    });


    const textInputs = form.querySelectorAll('input[type="text"]');
    textInputs.forEach(input => input.addEventListener("input", debounce(() => fetchData(false))));


    const selectInputs = form.querySelectorAll('select');
    selectInputs.forEach(select => select.addEventListener("change", () => fetchData(false)));


    form.addEventListener("submit", function (e) {
        e.preventDefault();
        console.log("filter form")
        fetchData(true);
    });

    attachPaginationEvents(fetchDataWithUrl);
}


document.addEventListener("DOMContentLoaded", function () {
    const form = document.getElementById("stock-filter-form");
    if (form) setupStockTable({
        formId: "stock-filter-form",
        tableId: "table-container",
        paginationId: "pagination-container"
    });
});
