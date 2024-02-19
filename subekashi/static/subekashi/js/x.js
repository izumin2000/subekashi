(function(window, document) {
    function main1() {
        var ad = document.createElement('script');
        ad.type = 'text/javascript';
        ad.async = true;
        ad.src = 'https://platform.twitter.com/widgets.js';
        var sc = document.getElementsByTagName('script')[0];
        sc.parentNode.insertBefore(ad, sc);
    }

    var lazyLoad = false;

    function onLazyLoad() {
        if (lazyLoad === false) {
            lazyLoad = true;
            window.removeEventListener('scroll', onLazyLoad);
            window.removeEventListener('mousemove', onLazyLoad);
            window.removeEventListener('mousedown', onLazyLoad);
            window.removeEventListener('touchstart', onLazyLoad);
            window.removeEventListener('keydown', onLazyLoad);
            main1();
        }
    }

    window.addEventListener('scroll', onLazyLoad);
    window.addEventListener('mousemove', onLazyLoad);
    window.addEventListener('mousedown', onLazyLoad);
    window.addEventListener('touchstart', onLazyLoad);
    window.addEventListener('keydown', onLazyLoad);

    window.addEventListener('load', function() {
        if (window.scrollY) {
            onLazyLoad();
        }
    });
})(window, document);
