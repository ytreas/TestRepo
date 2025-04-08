document.addEventListener('DOMContentLoaded', () => {
    const shareBtn = document.getElementById('share_btn');
    const popoverItem = document.getElementById('popover_item');

    shareBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        popoverItem.classList.toggle('visible');
    });

    document.addEventListener('click', (e) => {
        if (!popoverItem.contains(e.target) && e.target !== shareBtn) {
            popoverItem.classList.remove('visible');
        }
    });

});