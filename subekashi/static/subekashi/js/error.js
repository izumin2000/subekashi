function autoScroll(element, speed, direction) {
    let scrollTop = element.scrollTop;
    const interval = 4;
    const scrollDirection = direction === 'up' ? -1 : 1;

    const timer = setInterval(() => {
        scrollTop += scrollDirection;
        element.scrollTop = scrollTop;

        // 上方向：scrollTopが0以下で停止
        if (scrollDirection === -1 && element.scrollTop <= 0) {
            clearInterval(timer);
        }
        // 下方向：スクロールが末尾に到達したら停止
        if (scrollDirection === 1 && element.scrollTop + element.clientHeight >= element.scrollHeight) {
            clearInterval(timer);
        }
    }, speed * interval);
}

document.addEventListener('DOMContentLoaded', function() {
    const scrollingContainer = document.getElementsByTagName("html")[0];
    autoScroll(scrollingContainer, 2, 'down');
});