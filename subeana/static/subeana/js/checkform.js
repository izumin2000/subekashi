var isfirst = true;

async function checksong(basedir) {
    if (isfirst) {
        const res = await fetch(basedir + "/subeana/api/song/?format=json");
        const users = await res.json();
        isfirst = false;
    }
};