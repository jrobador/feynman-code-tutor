/* Feynman dossier runtime.
   Owns: language switching, word gates, jargon detection, sequential unlocking,
   break-glass accounting, progress, and the honesty report.
   Storage is best-effort: it upgrades the experience when available and is never required. */

(function () {
  "use strict";

  var KEY = "feynman:" + (CFG.systemName || "system");

  var mem = {};
  var store = {
    get: function () {
      try {
        var raw = window.localStorage.getItem(KEY);
        return raw ? JSON.parse(raw) : null;
      } catch (e) { return mem.data || null; }
    },
    set: function (obj) {
      mem.data = obj;
      try { window.localStorage.setItem(KEY, JSON.stringify(obj)); } catch (e) { /* in-memory only */ }
    }
  };

  var S = store.get() || {};
  S.lang = S.lang || CFG.defaultLang;
  S.text = S.text || {};
  S.submitted = S.submitted || {};
  S.revealed = S.revealed || {};
  S.ms = S.ms || {};
  S.glass = S.glass || {};
  S.marks = S.marks || {};    // per-concept self-marks, ticked before the reveal
  S.marked = S.marked || {};   // concepts whose marks are locked in
  S.theme = S.theme || "auto";

  function save() { store.set(S); }
  function words(s) { return (s || "").trim() ? (s || "").trim().split(/\s+/).length : 0; }
  function $(sel, root) { return (root || document).querySelector(sel); }
  function $$(sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); }
  function t(key) { return (CFG.ui[key] && CFG.ui[key][S.lang]) || (CFG.ui[key] && CFG.ui[key].en) || key; }

  /* ---------------- language + theme ---------------- */

  function setLang(lg) {
    S.lang = lg;
    document.body.setAttribute("data-lang", lg);
    document.documentElement.setAttribute("lang", lg);
    $$(".langbtn").forEach(function (b) {
      b.classList.toggle("on", b.getAttribute("data-setlang") === lg);
    });
    $$(".ta").forEach(function (ta) {
      var p = ta.getAttribute("data-ph-" + lg);
      if (p) ta.setAttribute("placeholder", p);
    });
    save();
    refresh();
  }

  function setTheme(mode) {
    S.theme = mode;
    if (mode === "auto") document.documentElement.removeAttribute("data-theme");
    else document.documentElement.setAttribute("data-theme", mode);
    save();
  }

  /* ---------------- gates ---------------- */

  function bannedHits(text, terms) {
    var low = (text || "").toLowerCase();
    var hits = [];
    (terms || []).forEach(function (term) {
      var tl = String(term).toLowerCase();
      if (tl && low.indexOf(tl) !== -1 && hits.indexOf(term) === -1) hits.push(term);
    });
    return hits;
  }

  function taState(ta) {
    var key = ta.getAttribute("data-key");
    var min = parseInt(ta.getAttribute("data-min") || "0", 10);
    var val = S.text[key] || "";
    var w = words(val);
    var hits = [];
    if (ta.hasAttribute("data-banned-check")) {
      var host = ta.closest("[data-banned]");
      if (host) {
        try { hits = bannedHits(val, JSON.parse(host.getAttribute("data-banned"))); } catch (e) { hits = []; }
      }
    }
    return { key: key, min: min, wordCount: w, hits: hits, ok: w >= min && hits.length === 0 };
  }

  function blankDone() { return words(S.text["blank"]) >= 60 || !!S.glass["sec:concepts"]; }

  function rubricN(cid) { return (CFG.rubricCounts && CFG.rubricCounts[cid]) || 0; }

  function ticked(cid) {
    var m = S.marks[cid] || {};
    return Object.keys(m).filter(function (k) { return m[k]; }).length;
  }

  /* A rubric turns the explanation into something gradeable, so the reference
     stays shut until the marks are in. Without a rubric this is the old
     behaviour: submitting reveals. */
  function refShown(cid) {
    if (S.glass[cid]) return true;
    if (!S.submitted[cid + ".exp"]) return false;
    return rubricN(cid) ? !!S.marked[cid] : true;
  }

  function expDone(cid) { return refShown(cid) || !!S.glass[cid]; }

  function gapsDone(cid) {
    var n = CFG.gapCounts[cid] || 0;
    for (var i = 0; i < n; i++) {
      if (words(S.text[cid + ".gap" + i]) < 8 && !S.glass[cid]) return false;
    }
    return true;
  }

  function conceptDone(cid) { return expDone(cid) && gapsDone(cid); }

  function allConceptsDone() {
    return CFG.conceptIds.every(conceptDone) || !!S.glass["sec:rebuild"];
  }

  function msAllChecked() {
    for (var i = 0; i < CFG.msCount; i++) if (!S.ms[i]) return false;
    return true;
  }

  function sourceUnlocked() {
    return (!!S.submitted["rebuild.notes"] && msAllChecked() && words(S.text["rebuild.notes"]) >= 80)
      || !!S.glass["rebuild"];
  }

  function seniorOpen() { return sourceUnlocked() || !!S.glass["sec:senior"]; }

  /* ---------------- status per section ---------------- */
  // "v" verified by real work, "u" opened with break-glass, "n" not started

  function statusOf(sec) {
    switch (sec) {
      case "blank":
        if (words(S.text["blank"]) >= 60) return "v";
        // Skipping the blank page via break-glass on concepts is a real bypass; record it.
        return S.glass["sec:concepts"] ? "u" : "n";
      case "concepts": {
        if (S.glass["sec:concepts"] && !CFG.conceptIds.some(function (c) { return S.submitted[c + ".exp"]; })) return "u";
        var anyGlass = CFG.conceptIds.some(function (c) { return S.glass[c]; });
        var all = CFG.conceptIds.every(function (c) { return S.submitted[c + ".exp"] && gapsDone(c); });
        if (all && !anyGlass) return "v";
        if (anyGlass || CFG.conceptIds.some(function (c) { return S.submitted[c + ".exp"]; })) return "u";
        return "n";
      }
      case "rebuild":
        if (S.glass["rebuild"] || S.glass["sec:rebuild"]) return "u";
        return sourceUnlocked() ? "v" : "n";
      case "senior":
        if (S.glass["sec:senior"]) return "u";
        return seniorOpen() ? "v" : "n";
      default:
        return "n";
    }
  }

  function conceptStatus(cid) {
    if (S.glass[cid]) return "u";
    if (!conceptDone(cid)) return "n";
    // You said yourself the explanation was missing something. Recording that
    // as VERIFIED would make the report agree with you instead of with the work.
    var n = rubricN(cid);
    if (n && ticked(cid) < n) return "u";
    return "v";
  }

  /* ---------------- progress ---------------- */

  function progress() {
    var total = 1, done = 0;
    if (words(S.text["blank"]) >= 60) done++;
    CFG.conceptIds.forEach(function (cid) {
      var n = CFG.gapCounts[cid] || 0;
      total += 2 + n;                                   // explanation + analogy + gaps
      if (S.submitted[cid + ".exp"]) done++;
      if (words(S.text[cid + ".ana"]) >= 15) done++;
      for (var i = 0; i < n; i++) if (words(S.text[cid + ".gap" + i]) >= 8) done++;
    });
    total += CFG.msCount + 1;
    for (var i = 0; i < CFG.msCount; i++) if (S.ms[i]) done++;
    if (S.submitted["rebuild.notes"]) done++;
    return total ? Math.round((done / total) * 100) : 0;
  }

  /* ---------------- rendering ---------------- */

  function refresh() {
    // textareas: counters, jargon, submit buttons
    $$(".ta").forEach(function (ta) {
      var st = taState(ta);
      if (ta.value !== (S.text[st.key] || "")) ta.value = S.text[st.key] || "";
      var wc = $('.wc[data-for="' + CSS.escape(st.key) + '"]');
      if (wc) wc.textContent = st.wordCount;
      var short = $('.short[data-for="' + CSS.escape(st.key) + '"]');
      if (short) short.textContent = st.wordCount < st.min ? ("+" + (st.min - st.wordCount)) : "";

      var jar = $('.jargon[data-for="' + CSS.escape(st.key) + '"]');
      if (jar) {
        if (st.hits.length) {
          jar.classList.add("on");
          jar.innerHTML = '<div class="jtitle">' + t("banned_hit") + "</div>"
            + st.hits.map(function (h) { return '<span class="chip">' + h + "</span>"; }).join("")
            + '<div class="jhelp">' + (S.lang === "es"
              ? "Estas palabras no están prohibidas para molestarte. Cada una es una caja que no abriste. Decí qué pasa realmente en su lugar."
              : "These words are not banned to annoy you. Each one is a box you have not opened. Say what physically happens instead.")
            + "</div>";
          ta.classList.add("bad");
        } else {
          jar.classList.remove("on");
          jar.innerHTML = "";
          ta.classList.remove("bad");
        }
      }

      var sub = $('[data-submit="' + CSS.escape(st.key) + '"]');
      if (sub) sub.disabled = !st.ok;
      var rev = $('[data-reveal="' + CSS.escape(st.key) + '"]');
      if (rev) rev.disabled = !st.ok;
    });

    // rebuild unlock button also needs all milestones ticked
    var rbBtn = $('[data-submit="rebuild.notes"]');
    if (rbBtn && !rbBtn.disabled) rbBtn.disabled = !msAllChecked();

    // reveal boxes
    Object.keys(S.revealed).forEach(function (k) {
      var el = document.getElementById("rev-" + k.replace(/\./g, "-"));
      if (el && S.revealed[k]) el.classList.add("shown");
    });

    // the mark-yourself stage sits between submitting and the reference
    CFG.conceptIds.forEach(function (cid) {
      var n = rubricN(cid);
      if (!n) return;
      var box = document.getElementById("rub-" + cid);
      if (box) {
        box.classList.toggle("shown", !!S.submitted[cid + ".exp"] && !S.glass[cid]);
        box.classList.toggle("locked", !!S.marked[cid]);
      }
      $$('[data-mark="' + CSS.escape(cid) + '"]').forEach(function (cb) {
        cb.checked = !!(S.marks[cid] || {})[cb.getAttribute("data-box")];
        cb.disabled = !!S.marked[cid];
      });
      var btn = $('[data-revealref="' + CSS.escape(cid) + '"]');
      if (btn) btn.style.display = S.marked[cid] ? "none" : "";
      var sc = $('.score[data-score="' + CSS.escape(cid) + '"]');
      if (sc) {
        sc.textContent = S.marked[cid] ? (ticked(cid) + "/" + n + " " + t("score")) : "";
        sc.classList.toggle("short", S.marked[cid] && ticked(cid) < n);
      }
      // the reference only opens once the marks are locked
      var ref = document.getElementById("rev-" + cid + "-exp");
      if (ref && !refShown(cid)) ref.classList.remove("shown");
    });

    // section locks
    var open = {
      orientation: true, blank: true, report: true,
      concepts: blankDone(),
      rebuild: allConceptsDone(),
      senior: seniorOpen()
    };
    $$(".sec").forEach(function (sec) {
      sec.classList.toggle("open", !!open[sec.getAttribute("data-sec")]);
    });
    document.body.classList.toggle("senior-open", seniorOpen());

    // per-concept badges
    CFG.conceptIds.forEach(function (cid) {
      var b = $('[data-badge="' + cid + '"]');
      if (!b) return;
      var st = conceptStatus(cid);
      b.className = "badge" + (st === "v" ? " done" : st === "u" ? " unver" : "");
      b.textContent = st === "v" ? t("verified") : st === "u" ? t("unverified") : "";
    });

    // milestones
    $$("[data-ms]").forEach(function (cb) { cb.checked = !!S.ms[cb.getAttribute("data-ms")]; });

    // nav dots
    $$(".sidenav a").forEach(function (a) {
      var sec = a.getAttribute("data-nav");
      var st = statusOf(sec);
      a.classList.toggle("done", st === "v");
      a.classList.toggle("unver", st === "u");
    });

    var p = progress();
    $("#pbar").style.width = p + "%";
    $("#ppct").textContent = p + "%";

    renderReport();
  }

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  function renderReport() {
    var rows = [];
    function label(st) { return st === "v" ? t("verified") : st === "u" ? t("unverified") : t("incomplete"); }
    // Each row carries a stable id as well as its display name. The name is
    // bilingual and will drift; anything reading this report back -- a study
    // system, a script -- needs a key that does not move.
    function row(id, name, st) {
      rows.push('<div class="rrow" data-id="' + esc(id) + '"><span>' + esc(name)
        + '</span><span class="rstat ' + st + '">' + label(st) + "</span></div>");
    }
    row("blank", S.lang === "es" ? "La hoja en blanco" : "The blank page", statusOf("blank"));
    CFG.conceptIds.forEach(function (cid) {
      var nm = CFG.names[cid] || {};
      row(cid, nm[S.lang] || nm.en || cid, conceptStatus(cid));
    });
    row("rebuild", S.lang === "es" ? "Reconstrucción" : "Rebuild", statusOf("rebuild"));
    row("senior", S.lang === "es" ? "Registro senior" : "Senior register", statusOf("senior"));
    var el = $("#reportbody");
    if (el) el.innerHTML = rows.join("");
  }

  function reportText() {
    var out = ["Feynman dossier — " + (CFG.systemName || ""), ""];
    $$("#reportbody .rrow").forEach(function (r) {
      out.push("- [" + (r.getAttribute("data-id") || "") + "] "
        + r.children[0].textContent + ": " + r.children[1].textContent);
    });
    out.push("", "Progress: " + progress() + "%");
    return out.join("\n");
  }

  /* ---------------- events ---------------- */

  document.addEventListener("input", function (e) {
    var ta = e.target.closest(".ta");
    if (!ta) return;
    S.text[ta.getAttribute("data-key")] = ta.value;
    save();
    refresh();
  });

  document.addEventListener("change", function (e) {
    var cb = e.target.closest("[data-ms]");
    if (cb) {
      S.ms[cb.getAttribute("data-ms")] = cb.checked;
      save(); refresh();
      return;
    }
    var mk = e.target.closest("[data-mark]");
    if (mk) {
      var cid = mk.getAttribute("data-mark");
      if (S.marked[cid]) { mk.checked = !mk.checked; return; }   // locked
      S.marks[cid] = S.marks[cid] || {};
      S.marks[cid][mk.getAttribute("data-box")] = mk.checked;
      save(); refresh();
    }
  });

  document.addEventListener("click", function (e) {
    var el;

    if ((el = e.target.closest("[data-setlang]"))) { setLang(el.getAttribute("data-setlang")); return; }

    if (e.target.closest("#themebtn")) {
      setTheme(S.theme === "auto" ? "light" : S.theme === "light" ? "dark" : "auto");
      return;
    }

    if ((el = e.target.closest("[data-submit]"))) {
      var k = el.getAttribute("data-submit");
      S.submitted[k] = true;
      var cid = k.indexOf(".exp") > 0 ? k.slice(0, k.indexOf(".exp")) : null;
      // With a rubric, submitting opens the marking stage, not the answer.
      var toRubric = cid && rubricN(cid) && !S.marked[cid];
      if (!toRubric) S.revealed[k] = true;
      save(); refresh();
      var box = document.getElementById(
        toRubric ? "rub-" + cid : "rev-" + k.replace(/\./g, "-"));
      if (box) box.scrollIntoView({ behavior: "smooth", block: "nearest" });
      return;
    }

    if ((el = e.target.closest("[data-revealref]"))) {
      var rc = el.getAttribute("data-revealref");
      S.marked[rc] = true;              // locks the marks; they cannot be edited after
      S.revealed[rc + ".exp"] = true;
      save(); refresh();
      var rb = document.getElementById("rev-" + rc + "-exp");
      if (rb) rb.scrollIntoView({ behavior: "smooth", block: "nearest" });
      return;
    }

    if ((el = e.target.closest("[data-reveal]"))) {
      S.revealed[el.getAttribute("data-reveal")] = true;
      save(); refresh();
      return;
    }

    if ((el = e.target.closest("[data-glass]"))) {
      var g = el.getAttribute("data-glass");
      var msg = S.lang === "es"
        ? "Esto abre la sección ahora y la deja marcada SIN VERIFICAR para siempre en el informe. Es un registro honesto, no un castigo. ¿Seguir?"
        : "This opens the section now and permanently marks it UNVERIFIED in your report. It is an honest record, not a punishment. Continue?";
      if (!window.confirm(msg)) return;
      S.glass[g] = true;
      if (g === "rebuild") S.revealed["rebuild.notes"] = true;
      if (CFG.conceptIds.indexOf(g) !== -1) { S.revealed[g + ".exp"] = true; S.marked[g] = true; }
      save(); refresh();
      return;
    }

    if ((el = e.target.closest(".flashcard"))) { el.classList.toggle("flip"); return; }

    if (e.target.closest("#copyreport")) {
      var txt = reportText();
      if (navigator.clipboard) navigator.clipboard.writeText(txt).catch(function () { window.prompt("", txt); });
      else window.prompt("", txt);
      return;
    }
  });

  // scroll spy
  var secs = $$(".sec");
  window.addEventListener("scroll", function () {
    var best = null, bestTop = Infinity;
    secs.forEach(function (s) {
      var top = Math.abs(s.getBoundingClientRect().top - 100);
      if (top < bestTop) { bestTop = top; best = s.getAttribute("data-sec"); }
    });
    $$(".sidenav a").forEach(function (a) {
      a.classList.toggle("active", a.getAttribute("data-nav") === best);
    });
  }, { passive: true });

  // CSS.escape fallback for older engines
  if (!window.CSS || !window.CSS.escape) {
    window.CSS = window.CSS || {};
    window.CSS.escape = function (s) { return String(s).replace(/([^\w-])/g, "\\$1"); };
  }

  setLang(S.lang);
  setTheme(S.theme);
  refresh();
})();
