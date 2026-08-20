// ShopSphere - main client-side interactions

// Product image gallery swap
function swapImg(src) {
    const main = document.getElementById('mainImage');
    if (main && src) main.src = src;
}

// Quantity stepper
document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('.qty-control').forEach(function (group) {
        const input = group.querySelector('input[type="number"]');
        const minus = group.querySelector('.qty-minus');
        const plus = group.querySelector('.qty-plus');
        if (!input) return;
        if (minus) minus.addEventListener('click', function () {
            const v = parseInt(input.value, 10) || 1;
            if (v > 1) input.value = v - 1;
        });
        if (plus) plus.addEventListener('click', function () {
            const v = parseInt(input.value, 10) || 1;
            input.value = v + 1;
        });
    });

    // Auto-dismiss flash messages
    setTimeout(function () {
        document.querySelectorAll('.alert.auto-dismiss').forEach(function (el) {
            el.style.transition = 'opacity .5s';
            el.style.opacity = '0';
            setTimeout(function () { el.remove(); }, 500);
        });
    }, 4000);

    // Confirm delete buttons with data-confirm attribute
    document.querySelectorAll('[data-confirm]').forEach(function (btn) {
        btn.addEventListener('click', function (e) {
            if (!confirm(btn.getAttribute('data-confirm'))) e.preventDefault();
        });
    });

    // Mobile admin sidebar toggle
    const toggle = document.querySelector('.admin-toggle');
    if (toggle) {
        toggle.addEventListener('click', function () {
            document.querySelector('.admin-sidebar').classList.toggle('open');
        });
    }
});
