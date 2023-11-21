function autoScroll(element, speed, direction) {
    let scrollTop = 0;
    const interval = 5;
    const scrollDirection = direction === 'up' ? -1 : 1;
  
    function scroll() {
        scrollTop += scrollDirection;
        element.scrollTop = scrollTop;
    }

    const scrollInterval = setInterval(scroll, speed * interval);
}

document.addEventListener('DOMContentLoaded', function() {
    const scrollingContainer = document.getElementsByTagName("html")[0];
    autoScroll(scrollingContainer, 2, 'down');
});