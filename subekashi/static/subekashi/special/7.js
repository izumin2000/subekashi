function special() { 
    document.getElementsByClassName("dummybuttons")[0].remove();
    kyouiku();
}

document.addEventListener("DOMContentLoaded", () => {
    add_special_button();
});