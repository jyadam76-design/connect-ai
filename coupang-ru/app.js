(() => {
  const $ = (id) => document.getElementById(id);
  const DICT = window.DICT || {};

  // ---------- Перевод ----------
  async function withTimeout(promise, ms) {
    let t;
    const timeout = new Promise((_, rej) => { t = setTimeout(() => rej(new Error("timeout")), ms); });
    try { return await Promise.race([promise, timeout]); } finally { clearTimeout(t); }
  }

  async function googleTranslate(text, sl, tl) {
    const url = "https://translate.googleapis.com/translate_a/single?client=gtx&dt=t" +
      `&sl=${sl}&tl=${tl}&q=${encodeURIComponent(text)}`;
    const res = await withTimeout(fetch(url), 6000);
    if (!res.ok) throw new Error("google " + res.status);
    const data = await res.json();
    const out = (data[0] || []).map((p) => p[0]).join("").trim();
    if (!out) throw new Error("google empty");
    return out;
  }

  async function myMemoryTranslate(text, sl, tl) {
    const url = `https://api.mymemory.translated.net/get?langpair=${sl}|${tl}&q=${encodeURIComponent(text)}`;
    const res = await withTimeout(fetch(url), 6000);
    if (!res.ok) throw new Error("mymemory " + res.status);
    const data = await res.json();
    const out = data?.responseData?.translatedText?.trim();
    if (!out || data.responseStatus !== 200) throw new Error("mymemory empty");
    return out;
  }

  const norm = (s) => s.toLowerCase().replace(/ё/g, "е").replace(/[^\p{L}\p{N}\s-]/gu, " ").replace(/\s+/g, " ").trim();
  const NDICT = {};
  for (const [k, v] of Object.entries(DICT)) NDICT[norm(k)] = v;

  // Офлайн-перевод по словарю: сначала самые длинные фразы, затем слова.
  // Падежные окончания учитываются грубо: слова совпадают, если совпадает основа.
  const KEYS = Object.keys(NDICT).map((k) => k.split(" ")).sort((a, b) => b.length - a.length);
  const wordMatch = (w, k) => w === k ||
    (k.length >= 4 && w.length >= 4 && w.slice(0, Math.max(4, k.length - 2)) === k.slice(0, Math.max(4, k.length - 2)));

  function dictTranslate(text) {
    const words = norm(text).split(" ").filter(Boolean);
    if (!words.length) return null;
    const out = [];
    let hits = 0;
    for (let i = 0; i < words.length;) {
      const key = KEYS.find((k) => k.length <= words.length - i && k.every((kw, j) => wordMatch(words[i + j], kw)));
      if (key) {
        const ko = NDICT[key.join(" ")];
        if (ko) out.push(ko);
        hits++; i += key.length;
      } else { out.push(words[i]); i++; }
    }
    return hits ? out.join(" ").trim() : null;
  }

  // Онлайн-переводчики иногда добавляют лишнее — для поиска убираем знаки препинания.
  const cleanQuery = (s) => s.replace(/[.。!?,"«»]/g, " ").replace(/\s+/g, " ").trim();

  async function translate(text, sl, tl) {
    if (sl === "ru") {
      const exact = NDICT[norm(text)];
      if (exact) return { text: exact, source: "словарь покупок" };
    }
    for (const [fn, name] of [[googleTranslate, "Google"], [myMemoryTranslate, "MyMemory"]]) {
      try { return { text: await fn(text, sl, tl), source: name }; } catch (e) { /* пробуем следующий */ }
    }
    if (sl === "ru") {
      const d = dictTranslate(text);
      if (d) return { text: d, source: "словарь (без интернета)" };
    }
    throw new Error("Не удалось перевести. Проверьте интернет.");
  }

  // ---------- Coupang ----------
  const isMobile = /Android|iPhone|iPad|iPod/i.test(navigator.userAgent);
  const coupangUrl = (q) => isMobile
    ? `https://m.coupang.com/nm/search?q=${encodeURIComponent(q)}`
    : `https://www.coupang.com/np/search?q=${encodeURIComponent(q)}`;

  function toast(msg) {
    const t = $("toast"); t.textContent = msg; t.classList.add("show");
    clearTimeout(toast._t); toast._t = setTimeout(() => t.classList.remove("show"), 2200);
  }

  async function copy(text) {
    try { await navigator.clipboard.writeText(text); return true; }
    catch {
      const ta = document.createElement("textarea"); ta.value = text; document.body.appendChild(ta);
      ta.select(); const ok = document.execCommand("copy"); ta.remove(); return ok;
    }
  }

  // ---------- История ----------
  const HKEY = "coupang-ru-history";
  const loadHistory = () => { try { return JSON.parse(localStorage.getItem(HKEY)) || []; } catch { return []; } };
  const saveHistory = (h) => { try { localStorage.setItem(HKEY, JSON.stringify(h.slice(0, 30))); } catch {} };

  function addHistory(ru, ko) {
    const h = loadHistory().filter((x) => x.ko !== ko);
    h.unshift({ ru, ko }); saveHistory(h); renderHistory();
  }

  function renderHistory() {
    const h = loadHistory(); const ul = $("history"); ul.innerHTML = "";
    $("clearHistory").hidden = !h.length;
    if (!h.length) { ul.innerHTML = '<li class="empty">Пока пусто</li>'; return; }
    for (const item of h) {
      const li = document.createElement("li");
      const b = document.createElement("button"); b.textContent = item.ru;
      b.onclick = () => { $("ru").value = item.ru; showResult(item.ru, item.ko, "история"); };
      const v = document.createElement("span"); v.className = "v"; v.textContent = item.ko;
      li.append(b, v); ul.append(li);
    }
  }

  // ---------- Поиск ----------
  async function showResult(ru, ko, source) {
    $("ko").value = ko;
    $("src").textContent = "Перевод: " + source;
    $("back").textContent = "";
    $("result").hidden = false;
    $("result").scrollIntoView({ behavior: "smooth", block: "nearest" });
    // Обратная проверка: что означает корейский запрос по-русски.
    try {
      const back = await translate(ko, "ko", "ru");
      if ($("ko").value === ko) $("back").textContent = "Проверка (обратно на русский): " + back.text;
    } catch {}
  }

  async function doTranslate() {
    const ru = $("ru").value.trim();
    if (!ru) { $("ru").focus(); return; }
    const btn = $("translate"); btn.disabled = true; btn.textContent = "Переводим…";
    try {
      const r = await translate(ru, "ru", "ko");
      const ko = cleanQuery(r.text);
      addHistory(ru, ko);
      showResult(ru, ko, r.source);
    } catch (e) { toast(e.message); }
    finally { btn.disabled = false; btn.textContent = "Перевести на корейский"; }
  }

  $("translate").onclick = doTranslate;
  $("ru").addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); doTranslate(); } });
  $("open").onclick = () => { const q = $("ko").value.trim(); if (q) window.open(coupangUrl(q), "_blank", "noopener"); };
  $("copy").onclick = async () => { if (await copy($("ko").value.trim())) toast("Скопировано: " + $("ko").value.trim()); };
  $("openApp").onclick = async () => {
    const q = $("ko").value.trim(); if (!q) return;
    await copy(q);
    toast("Скопировано — вставьте в поиск Coupang");
    // На телефоне ссылка m.coupang.com обычно открывает установленное приложение Coupang.
    setTimeout(() => { location.href = coupangUrl(q); }, 700);
  };
  $("clearHistory").onclick = () => { saveHistory([]); renderHistory(); };

  // Быстрые категории
  for (const [label, ko] of window.CHIPS || []) {
    const b = document.createElement("button"); b.className = "chip"; b.textContent = label;
    b.onclick = () => { const ru = label.replace(/^\S+\s/, ""); $("ru").value = ru; addHistory(ru, ko); showResult(ru, ko, "словарь покупок"); };
    $("chips").append(b);
  }

  // Голосовой ввод
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) { $("mic").hidden = true; }
  else {
    let rec = null;
    $("mic").onclick = () => {
      if (rec) { rec.stop(); return; }
      rec = new SR(); rec.lang = "ru-RU"; rec.interimResults = true; rec.maxAlternatives = 1;
      $("mic").classList.add("listening");
      rec.onresult = (e) => {
        $("ru").value = Array.from(e.results).map((r) => r[0].transcript).join("");
        if (e.results[e.results.length - 1].isFinal) doTranslate();
      };
      rec.onerror = (e) => { if (e.error === "not-allowed") toast("Разрешите доступ к микрофону"); };
      rec.onend = () => { $("mic").classList.remove("listening"); rec = null; };
      rec.start();
    };
  }

  // ---------- Корейский → русский ----------
  $("toRu").onclick = async () => {
    const ko = $("koIn").value.trim(); if (!ko) return;
    const btn = $("toRu"); btn.disabled = true; btn.textContent = "Переводим…";
    try {
      const r = await translate(ko, "ko", "ru");
      $("ruOut").textContent = r.text; $("ruSrc").textContent = "Перевод: " + r.source;
      $("ruOutWrap").hidden = false;
    } catch (e) { toast(e.message); }
    finally { btn.disabled = false; btn.textContent = "Перевести на русский"; }
  };

  // ---------- Словарик ----------
  for (const [k, v] of window.GLOSSARY || []) {
    const li = document.createElement("li");
    li.innerHTML = `<span class="k"></span><span class="v"></span>`;
    li.querySelector(".k").textContent = k; li.querySelector(".v").textContent = v;
    $("glossary").append(li);
  }

  // ---------- Вкладки ----------
  document.querySelectorAll(".tab").forEach((t) => t.onclick = () => {
    document.querySelectorAll(".tab").forEach((x) => x.setAttribute("aria-selected", x === t));
    for (const name of ["search", "reverse", "help"]) $("tab-" + name).hidden = name !== t.dataset.tab;
  });

  renderHistory();

  // Поддержка ?q=... (например, из ярлыка или ссылки)
  const q = new URLSearchParams(location.search).get("q");
  if (q) { $("ru").value = q; doTranslate(); }

  if ("serviceWorker" in navigator && location.protocol === "https:") {
    navigator.serviceWorker.register("sw.js").catch(() => {});
  }

  // Для тестов
  window.__dictTranslate = dictTranslate;
})();
