// Small progressive enhancements. Every page works without this file.

// Home: the visitor asks the question; the agent "types" and answers.
// Without JS the whole exchange is simply shown.
(function () {
  var ask = document.querySelector("[data-ask]");
  if (!ask) return;
  var chat = ask.closest(".chat");
  var question = chat.querySelector("[data-question]");
  var reply = chat.querySelector("[data-reply]");
  var answer = reply.querySelector(".answer");
  var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  question.hidden = true;
  reply.hidden = true;
  ask.hidden = false;
  ask.addEventListener("click", function () {
    ask.hidden = true;
    question.hidden = false;
    question.classList.add("enter");
    setTimeout(function () {
      reply.hidden = false;
      reply.classList.add("enter");
      chat.classList.add("typing-now");
      setTimeout(function () {
        chat.classList.remove("typing-now");
        answer.focus({ preventScroll: true });
      }, reduce ? 0 : 1100);
    }, reduce ? 0 : 350);
  });
})();

// Publications: filter by type.
(function () {
  var buttons = document.querySelectorAll("[data-filter]");
  if (!buttons.length) return;
  buttons.forEach(function (btn) {
    btn.addEventListener("click", function () {
      var cat = btn.dataset.filter;
      buttons.forEach(function (b) { b.setAttribute("aria-pressed", String(b === btn)); });
      document.querySelectorAll(".year-group").forEach(function (group) {
        var visible = 0;
        group.querySelectorAll(".pub").forEach(function (p) {
          var show = cat === "all" || p.dataset.cat === cat;
          p.hidden = !show;
          if (show) visible++;
        });
        group.hidden = visible === 0;
      });
    });
  });
})();

// BibTeX: toggle the entry and copy it to the clipboard.
document.addEventListener("click", function (ev) {
  var btn = ev.target.closest("[data-bibtex]");
  if (!btn) return;
  var pre = document.getElementById(btn.dataset.bibtex);
  var open = pre.hidden;
  pre.hidden = !open;
  btn.setAttribute("aria-expanded", String(open));
  if (open && navigator.clipboard) {
    navigator.clipboard.writeText(pre.textContent).then(function () {
      var label = btn.textContent;
      btn.textContent = "BibTeX copied";
      setTimeout(function () { btn.textContent = label; }, 1600);
    }, function () {});
  }
});

// Projects: load the YouTube player only when asked.
document.addEventListener("click", function (ev) {
  var btn = ev.target.closest("[data-video]");
  if (!btn) return;
  var frame = document.createElement("iframe");
  frame.src = "https://www.youtube-nocookie.com/embed/" + btn.dataset.video + "?autoplay=1";
  frame.title = "Project video";
  frame.allow = "autoplay; encrypted-media; picture-in-picture";
  frame.allowFullscreen = true;
  var box = document.createElement("div");
  box.className = "video";
  box.appendChild(frame);
  btn.replaceWith(box);
  frame.focus();
});

// Theme toggle: remembers an explicit choice; otherwise follows the system setting.
(function () {
  var btn = document.querySelector(".theme-toggle");
  if (!btn) return;
  var root = document.documentElement;
  var media = window.matchMedia("(prefers-color-scheme: dark)");
  function current() { return root.dataset.theme || (media.matches ? "dark" : "light"); }
  function label() {
    var next = current() === "dark" ? "light" : "dark";
    btn.setAttribute("aria-label", "Switch to " + next + " mode");
    btn.title = "Switch to " + next + " mode";
  }
  btn.addEventListener("click", function () {
    var next = current() === "dark" ? "light" : "dark";
    root.dataset.theme = next;
    try { localStorage.setItem("theme", next); } catch (e) {}
    label();
  });
  media.addEventListener("change", label);
  label();
})();

// Projects: filter by topic and sort.
(function () {
  var list = document.querySelector("[data-project-list]");
  if (!list) return;
  var chips = document.querySelectorAll("[data-tag-filter]");
  var select = document.querySelector("[data-project-sort]");
  var items = Array.prototype.slice.call(list.querySelectorAll(".project"));
  var num = function (el, k) { return Number(el.dataset[k]); };
  var sorters = {
    featured: function (a, b) { return num(a, "order") - num(b, "order"); },
    newest: function (a, b) { return num(b, "end") - num(a, "end") || num(b, "start") - num(a, "start"); },
    oldest: function (a, b) { return num(a, "start") - num(b, "start") || num(a, "end") - num(b, "end"); }
  };
  select.addEventListener("change", function () {
    items.slice().sort(sorters[select.value]).forEach(function (el) { list.appendChild(el); });
  });
  chips.forEach(function (chip) {
    chip.addEventListener("click", function () {
      var tag = chip.dataset.tagFilter;
      chips.forEach(function (c) { c.setAttribute("aria-pressed", String(c === chip)); });
      items.forEach(function (el) {
        el.hidden = tag !== "all" && el.dataset.tags.split("|").indexOf(tag) === -1;
      });
    });
  });
})();
