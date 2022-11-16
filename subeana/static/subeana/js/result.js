async function good(basedir, id) {
    res = await fetch(
        basedir + "/subeana/api/ai/" + id + "/?format=json",
        {
            method: "PUT",
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(
                {
                    "isgood": true
                }
            )
        }
    );
}

async function badd(basedir, id) {
    res = await fetch(
        basedir + "/subeana/api/ai/" + id + "?format=json",
        {
            method: "POST",
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(
                {
                    "isbad": true
                }
            )
        }
    );
}