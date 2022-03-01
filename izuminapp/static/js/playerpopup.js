function playerpopup(uuid, name, online, info) {
    document.getElementById("popup_skin").setAttribute("src", "https://crafatar.com/renders/body/" + uuid);
    document.getElementById("popup_name").innerHTML = name;
    document.getElementById("popup_name").removeAttribute("class");
    if (online == "True") {
        document.getElementById("popup_name").setAttribute("class", "isonline");
    } else {
        document.getElementById("popup_name").setAttribute("class", "isoffline");
    }
    if (info == "") {
        document.getElementById("popup_hr").hidden = true;
        document.getElementById("popup_info").hidden = true;
    } else {
        document.getElementById("popup_hr").hidden = false;
        document.getElementById("popup_info").hidden = false;
        document.getElementById("popup_info").innerHTML = info;
    }
}