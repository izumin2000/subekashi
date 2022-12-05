async function setscore(basedir, id, username, score) {
    res = await fetch(basedir + "/api/ai/" + id + "?format=json");
    json_ai = res.json();

    users = ins_ai.users.split(",");
    if (!users.includes(username)) {
        users.push(username);
        users = users.join(",");
        ins_ai["users"] = users;
        ins_ai["poeple"] = Number(ins_ai["poeple"]) + 1;
        ins_ai["score"] = Number(ins_ai["score"]) + score;

        res = await fetch(
            basedir + "/api/ai/" + id + "/?format=json",
            {
                method: "PUT",
                headers: {
                    'Content-Type': 'application/json'
                },
                body: ins_ai
            }
        );
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