async function setscore(basedir, id, username, score) {
    res = await fetch(basedir + "/api/ai/" + id + "?format=json");
    json_ai = res.json();

    users = json_ai.users.split(",");
    if (!users.includes(username)) {
        users.push(username);
        users = users.join(",");
        json_ai["users"] = users;
        json_ai["poeple"] = Number(json_ai["poeple"]) + 1;
        json_ai["score"] = Number(json_ai["score"]) + score;

        res = await fetch(
            basedir + "/api/ai/" + id + "/?format=json",
            {
                method: "PUT",
                headers: {
                    'Content-Type': 'application/json'
                },
                body: json_ai
            }
        );
        console.log(json_ai);
    } else {
        console.log("scored");
    }
}


function devinput(basedir, id, username, score) {
    for (s = 1; s <= 5; s++) {
        radioEle = document.getElementById(String(id) + String(s));
        radioEle.checked = false;
    }

    radioEle = document.getElementById(String(id) + String(score));
    radioEle.checked = true;
    setscore(basedir, id, username, score);
}