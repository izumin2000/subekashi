async function good(basedir, id) {
    goodEle = document.getElementById(id + "good");
    if (goodEle.className == "fas fa-thumbs-up") {
        isgood = false;
        goodEle.className = "far fa-thumbs-up";
    } else {
        isgood = true;
        goodEle.className = "fas fa-thumbs-up";
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