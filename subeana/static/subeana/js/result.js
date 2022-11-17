async function good(basedir, id) {
    goodEle = document.getElementById(id + "good");
    if (goodEle.className == "fas fa-thumbs-up checkgood") {
        isgood = false;
        goodEle.className = "far fa-thumbs-up checkgood";
    } else {
        isgood = true;
        goodEle.className = "fas fa-thumbs-up checkgood";
    }

    res = await fetch(
        basedir + "/subeana/api/ai/" + id + "/?format=json",
        {
            method: "PUT",
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(
                {
                    "isgood": isgood
                }
            )
        }
    );
}

async function bad(basedir, id) {
    badEle = document.getElementById(id + "bad");
    if (badEle.className == "fas fa-flag") {
        isbad = false;
        badEle.className = "far fa-flag";
    } else {
        isbad = true;
        badEle.className = "fas fa-flag";
    }

    res = await fetch(
        basedir + "/subeana/api/ai/" + id + "/?format=json",
        {
            method: "PUT",
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(
                {
                    "isbad": isbad
                }
            )
        }
    );
}

function copygood() {
    toastr.options = {
        "closeButton": false,
        "debug": false,
        "newestOnTop": false,
        "progressBar": true,
        "positionClass": "toast-bottom-right",
        "preventDuplicates": false,
        "onclick": null,
        "timeOut": "3000",
        "extendedTimeOut": "0",
        "showEasing": "swing",
        "hideEasing": "linear",
    }

    checkgoodEles = document.getElementsByClassName("checkgood");
    copytext = ""
    for (checkgoodEle of checkgoodEles) {
        if (checkgoodEle.className == "fas fa-thumbs-up checkgood") {
            copytext += checkgoodEle.parentElement.innerText + "\n";
        }
    }

    if (Boolean(navigator.clipboard)) {
        navigator.clipboard.writeText(copytext);
        toastr.success(copytext + " をコピーしました！")
    } else {
        toastr.warning("この機能はセキュリティの関係上、HTTPS環境上でしか動作しません。")
    }
}