function special() {
    document.querySelector('#lyrics').style.lineHeight = '64px';
    document.getElementsByClassName("dummybuttons")[0].remove();

        /**
     * sky-gradient-scroll.js
     *
     * ページのスクロール位置に応じて背景色が変化します。
     * 一番上 = 0時（深夜）、一番下 = 24時（翌深夜）
     *
     * 使い方:
     *     <script src="sky-gradient-scroll.js"></script>
     *     読み込むだけで動作します。コンテンツは通常通りスクロールできます。
     *
     * オプション:
     *     SkyGradientScroll.init({ target: document.querySelector('#wrap') });
     */

    (function (global) {
        "use strict";

        const COLOR_STOPS = [
            ["#000000", "#000000"],
            ["#000201", "#020403"],
            ["#010302", "#06080a"],
            ["#020405", "#090d13"],
            ["#05070b", "#0e151c"],
            ["#08090d", "#111922"],
            ["#0a1017", "#272c3c"],
            ["#0b151e", "#665263"],
            ["#0a1b28", "#7f6669"],
            ["#0b1c2c", "#917a6e"],
            ["#152839", "#988b7f"],
            ["#364e74", "#96a0a0"],
            ["#5979a2", "#85b0ba"],
            ["#70abcb", "#9bd8eb"],
            ["#89a1be", "#b4d2e5"],
            ["#7295b8", "#b0cee3"],
            ["#5b87b1", "#bedaeb"],
            ["#5986b2", "#a0aec2"],
            ["#527dac", "#998a96"],
            ["#3d557b", "#94605f"],
            ["#3a4c6c", "#a25849"],
            ["#373952", "#ae4f31"],
            ["#30283b", "#98452b"],
            ["#282230", "#7a3a26"],
            ["#1e1d2a", "#5d3123"],
            ["#111622", "#2c1c19"],
            ["#060e17", "#0e1016"],
            ["#040d16", "#030c12"],
            ["#000000", "#000000"],
        ];

        function hexToRgb(hex) {
            return [
                parseInt(hex.slice(1, 3), 16),
                parseInt(hex.slice(3, 5), 16),
                parseInt(hex.slice(5, 7), 16),
            ];
        }

        function lerpColor(a, b, t) {
            return a.map(function (v, i) {
                return Math.round(v + (b[i] - v) * t);
            });
        }

        function rgbToHex(rgb) {
            return "#" + rgb.map(function (v) {
                return v.toString(16).padStart(2, "0");
            }).join("");
        }

        function getScrollProgress() {
            var scrollTop = window.scrollY || window.pageYOffset;
            var maxScroll = document.documentElement.scrollHeight - window.innerHeight;
            if (maxScroll <= 0) return 0;
            return Math.max(0, Math.min(1, scrollTop / maxScroll));
        }

        function render(el, progress) {
            var n = COLOR_STOPS.length - 1;
            var idx = progress * n;
            var lo = Math.floor(idx);
            var hi = Math.min(lo + 1, n);
            var t = idx - lo;

            var topColor = rgbToHex(
                lerpColor(hexToRgb(COLOR_STOPS[lo][0]), hexToRgb(COLOR_STOPS[hi][0]), t)
            );
            var botColor = rgbToHex(
                lerpColor(hexToRgb(COLOR_STOPS[lo][1]), hexToRgb(COLOR_STOPS[hi][1]), t)
            );

            el.style.background =
                "linear-gradient(to bottom, " + topColor + ", " + botColor + ")";
            el.style.backgroundAttachment = "fixed";
        }

        function init(options) {
            var opts = Object.assign({ target: document.body }, options || {});
            var el = opts.target;

            render(el, getScrollProgress());

            var ticking = false;
            window.addEventListener(
                "scroll",
                function () {
                    if (!ticking) {
                        requestAnimationFrame(function () {
                            render(el, getScrollProgress());
                            ticking = false;
                        });
                        ticking = true;
                    }
                },
                { passive: true }
            );

            return {
                update: function () {
                    render(el, getScrollProgress());
                },
            };
        }

        global.SkyGradientScroll = { init: init };

        if (document.readyState === "loading") {
            document.addEventListener("DOMContentLoaded", function () { init(); });
        } else {
            init();
        }

    })(typeof window !== "undefined" ? window : this);
}


document.addEventListener("DOMContentLoaded", () => {
    add_special_button();
});