
const defaultActionButtonsEle = document.getElementsByClassName("action-buttons")[0];

function special() {
    defaultActionButtonsEle.remove();
    dot_lyrics();
}

document.addEventListener("DOMContentLoaded", () => {
    add_special_button();
});