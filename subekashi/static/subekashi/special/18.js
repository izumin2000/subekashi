
var defaultDummybuttonsEle = document.getElementsByClassName("dummybuttons")[0];

function special() {
    defaultDummybuttonsEle.remove();
    dot_lyrics();
    initRain();
}

document.addEventListener("DOMContentLoaded", () => {
    add_special_button();
});