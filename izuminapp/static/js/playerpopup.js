function playerpopup(uuid, name, ableapi, online, info) {
    document.getElementById("popup_skin").removeAttribute("src");
    document.getElementById("popup_name").innerHTML = name;
    document.getElementById("popup_name").removeAttribute("class");
    if (ableapi == "True") {
        if (online == "True") {
            document.getElementById("popup_name").setAttribute("class", "isonline");
        } else {
            document.getElementById("popup_name").setAttribute("class", "isoffline");
        }
    }
    if (info == "") {
        document.getElementById("popup_hr").hidden = true;
        document.getElementById("popup_info").hidden = true;
    } else {
        document.getElementById("popup_hr").hidden = false;
        document.getElementById("popup_info").hidden = false;
        document.getElementById("popup_info").innerHTML = info;
    }
    document.getElementById("popup_skin").setAttribute("src", "https://crafatar.com/renders/body/" + uuid);
}