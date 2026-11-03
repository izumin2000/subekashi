// MIDIキーボードで遊ぶロールピアノ（#1258）。util.jsがグローバルにcanvasやctxを宣言しているため、IIFEで囲んで名前の衝突を避ける
(() => {
    const MIDI_URL = `${baseURL()}/static/subekashi/special/5472.mid`;
    const CSS_URL = `${baseURL()}/static/subekashi/special/5472.css`;
    const AUDIO_URL = `${baseURL()}/static/subekashi/special/5472.mp3`;
    const SCORE_URL = `${baseURL()}/static/subekashi/special/5472.pdf`;

    // mp3の音は、MIDIのノートの開始より遅れて立ち上がる。ノートごとに、開始の近くで音量が最も増える位置を探すと、中央値は曲の始めで0.062秒、終わりで0.082秒だった。
    // その平均の分だけ音を早く始めて、ノートが鍵盤に届く瞬間に音が聞こえるようにする
    const AUDIO_OFFSET_SEC = 0.07;
    const LEAD_IN_SEC = 2;
    const TAIL_SEC = 1;
    const HIT_WINDOW_SEC = 0.15;
    const MAX_POINTS = 100;
    const MIN_POINTS = 50;
    const PX_PER_SEC = 160;
    const ROLL_HEIGHT = 400;
    const MIN_WHITE_KEY_WIDTH = 18;
    const MAX_WHITE_KEY_WIDTH = 24;
    const NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];
    const BLACK_PITCH_CLASSES = [1, 3, 6, 8, 10];
    const NOTE_COLORS = { pending: "#09F", hit: "#3c3", missed: "#733" };
    const PLAY_BUTTONS = {
        loading: ["fa-spinner fa-spin", "読み込み中"],
        idle: ["fa-play", "再生"],
        playing: ["fa-pause", "一時停止"],
        paused: ["fa-play", "再開"],
        finished: ["fa-redo", "もう一度"],
    };

    let notes = [];
    let notesByPitch = new Map();
    let endTime = 0;
    let layout = null;
    let state = "idle";
    let songTime = -LEAD_IN_SEC;
    let lastPerf = 0;
    let rafId = 0;
    let score = 0;
    let hits = 0;
    let wrong = 0;
    let missCursor = 0;
    let audioContext = null;
    let audioBuffer = null;
    let audioSource = null;
    const pressedNotes = new Set();
    const keyElements = new Map();
    let els = {};
    let ctx = null;

    const isBlackKey = (note) => BLACK_PITCH_CLASSES.includes(note % 12);
    const noteName = (note) => NOTE_NAMES[note % 12] + (Math.floor(note / 12) - 1);

    function formatTime(sec) {
        const total = Math.max(0, Math.floor(sec));
        return `${Math.floor(total / 60)}:${String(total % 60).padStart(2, "0")}`;
    }

    // SMF（format 0/1）の読み込み。テンポ変化を反映して、ノートの開始・終了を秒で返す
    function parseMidi(buffer) {
        const data = new Uint8Array(buffer);
        const view = new DataView(buffer);
        const readText = (pos) => String.fromCharCode(...data.slice(pos, pos + 4));
        if (readText(0) !== "MThd") throw new Error("MIDIファイルではありません");
        const trackCount = view.getUint16(10);
        const division = view.getUint16(12);
        if (division & 0x8000) throw new Error("SMPTE形式のMIDIには対応していません");

        const tempos = [{ tick: 0, usPerBeat: 500000 }];
        const rawNotes = [];
        let pos = 8 + view.getUint32(4);
        for (let track = 0; track < trackCount; track++) {
            const trackEnd = pos + 8 + view.getUint32(pos + 4);
            const isTrack = readText(pos) === "MTrk";
            let i = pos + 8;
            pos = trackEnd;
            if (!isTrack) continue;

            const readVlq = () => {
                let value = 0;
                let byte;
                do {
                    byte = data[i++];
                    value = (value << 7) | (byte & 0x7f);
                } while (byte & 0x80);
                return value;
            };

            const openNotes = new Map();
            let tick = 0;
            let status = 0;
            while (i < trackEnd) {
                tick += readVlq();
                const first = data[i];
                if (first === 0xff) {
                    const type = data[i + 1];
                    i += 2;
                    const length = readVlq();
                    if (type === 0x51 && length === 3) {
                        tempos.push({ tick, usPerBeat: (data[i] << 16) | (data[i + 1] << 8) | data[i + 2] });
                    }
                    i += length;
                    continue;
                }
                if (first === 0xf0 || first === 0xf7) {
                    i++;
                    i += readVlq();
                    continue;
                }
                if (first & 0x80) {
                    status = first;
                    i++;
                }
                const type = status & 0xf0;
                if (type === 0xc0 || type === 0xd0) {
                    i += 1;
                    continue;
                }
                const note = data[i];
                const velocity = data[i + 1];
                i += 2;
                const key = `${status & 0x0f}:${note}`;
                if (type === 0x90 && velocity > 0) {
                    if (!openNotes.has(key)) openNotes.set(key, []);
                    openNotes.get(key).push(tick);
                } else if (type === 0x80 || type === 0x90) {
                    const starts = openNotes.get(key);
                    if (starts && starts.length > 0) {
                        rawNotes.push({ note, startTick: starts.shift(), endTick: tick });
                    }
                }
            }
            // 終了が書かれていないノートはトラックの最後で止める
            for (const [key, starts] of openNotes) {
                for (const startTick of starts) {
                    rawNotes.push({ note: Number(key.split(":")[1]), startTick, endTick: tick });
                }
            }
        }

        // 同じtickのテンポ変化は後に書かれたものを使う（sortは安定）
        tempos.sort((a, b) => a.tick - b.tick);
        const segments = [];
        let sec = 0;
        let prevTick = 0;
        let usPerBeat = tempos[0].usPerBeat;
        for (const tempo of tempos) {
            sec += ((tempo.tick - prevTick) * usPerBeat) / 1e6 / division;
            prevTick = tempo.tick;
            usPerBeat = tempo.usPerBeat;
            segments.push({ tick: tempo.tick, sec, usPerBeat });
        }
        const tickToSec = (tick) => {
            let segment = segments[0];
            for (const candidate of segments) {
                if (candidate.tick <= tick) segment = candidate;
            }
            return segment.sec + ((tick - segment.tick) * segment.usPerBeat) / 1e6 / division;
        };

        const parsed = rawNotes
            .map((raw) => ({
                note: raw.note,
                start: tickToSec(raw.startTick),
                end: tickToSec(raw.endTick),
                state: "pending",
            }))
            .sort((a, b) => a.start - b.start || a.note - b.note);
        if (parsed.length === 0) throw new Error("MIDIファイルにノートがありません");
        return parsed;
    }

    // 白鍵の幅から各音の鍵盤上の位置を決める。ロールも鍵盤もこの位置を使うので、ノートが対応する鍵の真上に落ちてくる
    function buildLayout(low, high, whiteWidth) {
        const blackWidth = Math.round((whiteWidth * 2) / 3);
        const keys = new Map();
        let whiteCount = 0;
        for (let note = low; note <= high; note++) {
            if (isBlackKey(note)) {
                keys.set(note, { x: whiteCount * whiteWidth - blackWidth / 2, width: blackWidth, black: true });
            } else {
                keys.set(note, { x: whiteCount * whiteWidth, width: whiteWidth, black: false });
                whiteCount++;
            }
        }
        return { keys, whiteWidth, blackWidth, width: whiteCount * whiteWidth, whiteCount };
    }

    function pitchRange() {
        let low = Math.min(...notes.map((n) => n.note));
        let high = Math.max(...notes.map((n) => n.note));
        while (isBlackKey(low)) low--;
        while (isBlackKey(high)) high++;
        return [low, high];
    }

    function renderBoard() {
        const [low, high] = pitchRange();
        const whiteCount = buildLayout(low, high, 1).whiteCount;
        const available = els.scroll.clientWidth;
        const whiteWidth = Math.max(MIN_WHITE_KEY_WIDTH, Math.min(MAX_WHITE_KEY_WIDTH, Math.floor(available / whiteCount)));
        if (layout && layout.whiteWidth === whiteWidth) return;
        layout = buildLayout(low, high, whiteWidth);

        els.board.style.width = `${layout.width}px`;
        els.board.style.setProperty("--white-key-width", `${layout.whiteWidth}px`);
        els.board.style.setProperty("--black-key-width", `${layout.blackWidth}px`);

        const dpr = window.devicePixelRatio || 1;
        els.roll.width = Math.round(layout.width * dpr);
        els.roll.height = Math.round(ROLL_HEIGHT * dpr);
        els.roll.style.width = `${layout.width}px`;
        els.roll.style.height = `${ROLL_HEIGHT}px`;
        ctx = els.roll.getContext("2d");
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

        els.keyboard.replaceChildren();
        keyElements.clear();
        const blackKeys = [];
        for (const [note, key] of layout.keys) {
            const element = document.createElement("div");
            element.dataset.note = note;
            keyElements.set(note, element);
            if (key.black) {
                element.className = "piano-black-key";
                element.style.left = `${key.x}px`;
                blackKeys.push(element);
            } else {
                element.className = "piano-white-key";
                if (note % 12 === 0) {
                    const label = document.createElement("span");
                    label.className = "piano-key-label";
                    label.textContent = noteName(note);
                    element.appendChild(label);
                }
                els.keyboard.appendChild(element);
            }
            element.classList.toggle("is-pressed", pressedNotes.has(note));
        }
        blackKeys.forEach((element) => els.keyboard.appendChild(element));
        draw(songTime);
    }

    function draw(time) {
        if (!ctx || !layout) return;
        ctx.clearRect(0, 0, layout.width, ROLL_HEIGHT);

        ctx.fillStyle = "rgba(255, 255, 255, 0.06)";
        for (const key of layout.keys.values()) {
            if (!key.black) ctx.fillRect(key.x + key.width - 1, 0, 1, ROLL_HEIGHT);
        }
        ctx.fillStyle = "rgba(255, 255, 255, 0.5)";
        ctx.fillRect(0, ROLL_HEIGHT - 2, layout.width, 2);

        ctx.font = '600 10px "Noto Sans JP", sans-serif';
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        for (const note of notes) {
            const bottom = ROLL_HEIGHT - (note.start - time) * PX_PER_SEC;
            const top = ROLL_HEIGHT - (note.end - time) * PX_PER_SEC;
            if (bottom < 0 || top > ROLL_HEIGHT) continue;
            const key = layout.keys.get(note.note);
            if (!key) continue;

            const x = key.x + 1;
            const width = key.width - 2;
            ctx.fillStyle = NOTE_COLORS[note.state];
            ctx.fillRect(x, top, width, bottom - top);
            ctx.strokeStyle = "rgba(0, 0, 0, 0.4)";
            ctx.strokeRect(x + 0.5, top + 0.5, width - 1, bottom - top - 1);

            // 幅に収まるときだけ音名を書く。収まらないときはオクターブ番号を省く
            const name = noteName(note.note);
            const label = [name, NOTE_NAMES[note.note % 12]].find((text) => ctx.measureText(text).width <= width - 2);
            if (label) {
                ctx.fillStyle = note.state === "hit" ? "#111" : "#fff";
                ctx.fillText(label, x + width / 2, bottom - 9);
            }
        }

        if (state === "playing" && time < 0) {
            ctx.font = 'bold 56px "Noto Sans JP", sans-serif';
            ctx.fillStyle = "rgba(255, 255, 255, 0.8)";
            ctx.fillText(String(Math.ceil(-time)), layout.width / 2, ROLL_HEIGHT / 2);
        }
    }

    function currentTime(perfNow) {
        return state === "playing" ? songTime + (perfNow - lastPerf) / 1000 : songTime;
    }

    // <audio>の再生位置の変更（シーク）は、サーバーがRangeリクエストに対応していないと先頭に戻るため、音声はメモリにデコードしてWeb Audioで鳴らす
    async function loadAudio() {
        if (!audioContext) throw new Error("Web Audioに対応していません");
        const response = await fetch(AUDIO_URL);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return audioContext.decodeAudioData(await response.arrayBuffer());
    }

    // 再生・再開のたびに、曲の時間に合う位置から新しく鳴らす。音の始まりより前（カウントダウン中）は、そこまで待ってから鳴らす
    function startAudio() {
        if (!audioBuffer) return;
        const position = songTime + AUDIO_OFFSET_SEC;
        const source = audioContext.createBufferSource();
        source.buffer = audioBuffer;
        source.connect(audioContext.destination);
        audioContext.resume();
        source.start(audioContext.currentTime + Math.max(0, -position), Math.max(0, position));
        audioSource = source;
    }

    function stopAudio() {
        audioSource?.stop();
        audioSource = null;
    }

    function setStatus(text) {
        els.status.textContent = text;
    }

    function updateHud() {
        els.score.textContent = score.toLocaleString("ja-JP");
        els.hits.textContent = `${hits} / ${notes.length}`;
        els.time.textContent = `${formatTime(Math.max(0, songTime))} / ${formatTime(endTime)}`;
    }

    function updateControls() {
        const [icon, text] = PLAY_BUTTONS[state];
        els.playButton.innerHTML = `<i class="fas ${icon}"></i><span class="icon-p-big">${text}</span>`;
    }

    // 開始時刻から判定窓を過ぎても弾かれていないノートをミスにする
    function settleMisses(untilStart) {
        while (missCursor < notes.length && notes[missCursor].start < untilStart) {
            if (notes[missCursor].state === "pending") notes[missCursor].state = "missed";
            missCursor++;
        }
    }

    // 判定窓の中にある同じ音高のノートのうち、いちばん近いものを命中にする
    function judge(pitch, time) {
        let best = null;
        let bestDiff = Infinity;
        for (const note of notesByPitch.get(pitch) ?? []) {
            if (note.state !== "pending") continue;
            const diff = Math.abs(note.start - time);
            if (diff <= HIT_WINDOW_SEC && diff < bestDiff) {
                best = note;
                bestDiff = diff;
            }
        }
        if (!best) {
            wrong++;
            return;
        }
        best.state = "hit";
        hits++;
        score += Math.round(MAX_POINTS - ((MAX_POINTS - MIN_POINTS) * bestDiff) / HIT_WINDOW_SEC);
    }

    function frame() {
        if (state !== "playing") return;
        const now = performance.now();
        songTime = currentTime(now);
        lastPerf = now;
        settleMisses(songTime - HIT_WINDOW_SEC);
        draw(songTime);
        updateHud();
        if (songTime >= endTime) {
            finish();
            return;
        }
        rafId = requestAnimationFrame(frame);
    }

    function play() {
        if (!layout) return;
        if (state === "finished") reset();
        state = "playing";
        lastPerf = performance.now();
        startAudio();
        rafId = requestAnimationFrame(frame);
        updateControls();
    }

    function pause() {
        if (state !== "playing") return;
        songTime = currentTime(performance.now());
        state = "paused";
        cancelAnimationFrame(rafId);
        stopAudio();
        updateControls();
        draw(songTime);
        updateHud();
    }

    function reset() {
        cancelAnimationFrame(rafId);
        stopAudio();
        state = "idle";
        songTime = -LEAD_IN_SEC;
        score = 0;
        hits = 0;
        wrong = 0;
        missCursor = 0;
        notes.forEach((note) => (note.state = "pending"));
        els.result.classList.remove("is-visible");
        updateControls();
        updateHud();
        draw(songTime);
    }

    function finish() {
        state = "finished";
        stopAudio();
        songTime = endTime;
        settleMisses(Infinity);
        const missed = notes.length - hits;
        // 弾き損ねた音と、どの音にも当たらなかった余計な打鍵の分だけ下がる
        const accuracy = (100 * hits) / (notes.length + wrong);
        els.resultAccuracy.textContent = `${accuracy.toFixed(1)}%`;
        els.resultDetail.textContent = `スコア ${score.toLocaleString("ja-JP")} ／ 命中 ${hits} ／ ミス ${missed} ／ 余計な打鍵 ${wrong}`;
        els.result.classList.add("is-visible");
        updateControls();
        updateHud();
        draw(songTime);
    }

    function setKeyPressed(note, pressed) {
        keyElements.get(note)?.classList.toggle("is-pressed", pressed);
    }

    function onMidiMessage(event) {
        const [status, note, velocity] = event.data;
        const type = status & 0xf0;
        if (type === 0x90 && velocity > 0) {
            pressedNotes.add(note);
            setKeyPressed(note, true);
            if (state === "playing") {
                judge(note, currentTime(performance.now()));
                updateHud();
            }
        } else if (type === 0x80 || type === 0x90) {
            pressedNotes.delete(note);
            setKeyPressed(note, false);
        }
    }

    async function setupMidi() {
        if (!navigator.requestMIDIAccess) {
            setStatus("このブラウザはWeb MIDIに対応していません。ChromeかEdgeで開いてください。");
            return;
        }
        try {
            const access = await navigator.requestMIDIAccess();
            const refresh = () => {
                const names = [];
                for (const input of access.inputs.values()) {
                    input.onmidimessage = onMidiMessage;
                    if (input.state === "connected") names.push(input.name);
                }
                setStatus(names.length ? `接続中のMIDIキーボード: ${names.join("、")}` : "MIDIキーボードが見つかりません。接続してください。");
            };
            access.onstatechange = refresh;
            refresh();
        } catch (e) {
            setStatus("MIDIの使用が許可されませんでした。ブラウザの設定でこのサイトのMIDIを許可してください。");
        }
    }

    function buildStage() {
        const stage = document.createElement("div");
        stage.id = "piano-stage";
        stage.innerHTML = `
            <div class="action-buttons">
                <button type="button" id="piano-play" class="action-button" disabled></button>
                <button type="button" id="piano-reset" class="action-button" disabled><i class="fas fa-undo"></i><span class="icon-p-big">リセット</span></button>
            </div>
            <p id="piano-status">MIDIキーボードを探しています…</p>
            <p id="piano-help">音が鍵盤に届くタイミング（前後${HIT_WINDOW_SEC}秒）で、同じ音高の鍵を弾いてください。</p>
            <div id="piano-hud">
                <span>スコア <b id="piano-score">0</b></span>
                <span>命中 <b id="piano-hits">0 / 0</b></span>
                <span>時間 <b id="piano-time">0:00 / 0:00</b></span>
            </div>
            <div id="piano-scroll">
                <div id="piano-board">
                    <div id="piano-roll-wrap">
                        <canvas id="piano-roll" role="img" aria-label="ロールピアノ"></canvas>
                        <div id="piano-result">
                            <p>正確率</p>
                            <p id="piano-result-accuracy"></p>
                            <p id="piano-result-detail"></p>
                        </div>
                    </div>
                    <div id="piano-keyboard"></div>
                </div>
            </div>
            <div id="piano-downloads" class="action-buttons">
                <a href="${SCORE_URL}" download="朝.pdf" class="action-button"><i class="fas fa-file-pdf"></i><span class="icon-p-big">楽譜（PDF）</span></a>
                <a href="${AUDIO_URL}" download="朝.mp3" class="action-button"><i class="fas fa-music"></i><span class="icon-p-big">mp3</span></a>
                <a href="${MIDI_URL}" download="朝.mid" class="action-button"><i class="fas fa-file-audio"></i><span class="icon-p-big">MIDI</span></a>
            </div>
        `;
        document.querySelector("#mainarticle section").prepend(stage);
        els = {
            playButton: stage.querySelector("#piano-play"),
            resetButton: stage.querySelector("#piano-reset"),
            status: stage.querySelector("#piano-status"),
            score: stage.querySelector("#piano-score"),
            hits: stage.querySelector("#piano-hits"),
            time: stage.querySelector("#piano-time"),
            scroll: stage.querySelector("#piano-scroll"),
            board: stage.querySelector("#piano-board"),
            roll: stage.querySelector("#piano-roll"),
            keyboard: stage.querySelector("#piano-keyboard"),
            result: stage.querySelector("#piano-result"),
            resultAccuracy: stage.querySelector("#piano-result-accuracy"),
            resultDetail: stage.querySelector("#piano-result-detail"),
        };
        state = "loading";
        updateControls();
        els.playButton.addEventListener("click", () => (state === "playing" ? pause() : play()));
        els.resetButton.addEventListener("click", reset);
    }

    async function special() {
        document.querySelector(".action-buttons")?.remove();
        // ユーザーの操作（このボタンのクリック）の中で作らないと、ブラウザが音の再生を止める
        audioContext = window.AudioContext ? new AudioContext() : null;
        buildStage();
        setupMidi();
        const audioLoading = loadAudio().catch((e) => {
            console.error("音声の読み込みに失敗しました:", e);
            return null;
        });

        try {
            const response = await fetch(MIDI_URL);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            notes = parseMidi(await response.arrayBuffer());
        } catch (e) {
            console.error("MIDIファイルの読み込みに失敗しました:", e);
            showToast("error", "MIDIファイルの読み込みに失敗しました。");
            els.scroll.textContent = "MIDIファイルの読み込みに失敗しました。ページを読み込み直してください。";
            return;
        }
        notesByPitch = new Map();
        for (const note of notes) {
            if (!notesByPitch.has(note.note)) notesByPitch.set(note.note, []);
            notesByPitch.get(note.note).push(note);
        }
        audioBuffer = await audioLoading;
        if (!audioBuffer) showToast("warning", "音声の読み込みに失敗しました。音なしで遊べます。");
        // 最後のノートの余韻が途切れないよう、音声の終わりまでを曲の時間にする
        const audioEnd = audioBuffer ? audioBuffer.duration - AUDIO_OFFSET_SEC : 0;
        endTime = Math.max(Math.max(...notes.map((note) => note.end)) + TAIL_SEC, audioEnd);

        renderBoard();
        window.addEventListener("resize", renderBoard);
        document.addEventListener("visibilitychange", () => {
            if (document.hidden) pause();
        });
        state = "idle";
        updateControls();
        els.playButton.disabled = false;
        els.resetButton.disabled = false;
        updateHud();
    }

    window.special = special;

    document.addEventListener("DOMContentLoaded", () => {
        const link = document.createElement("link");
        link.rel = "stylesheet";
        link.href = CSS_URL;
        document.head.appendChild(link);
        add_special_button();
    });
})();
