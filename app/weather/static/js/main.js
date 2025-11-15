/* WeatherCraft front-end helpers (Alpine used inline in templates)
 * This file holds route transition helpers and small utilities.
 */
(function () {
    // Fade between content swaps
    function fadeNavigate(url) {
        const root = document.getElementById('route-content');
        if (!root) { window.location.href = url; return; }
        root.classList.add('opacity-0');
        setTimeout(() => { window.location.href = url; }, 150);
    }
    window.wc = { fadeNavigate };
})();
