(() => {
  "use strict";
  const filterLinks = [...document.querySelectorAll("[data-filter]")];
  const seasons = [...document.querySelectorAll("[data-season]")];
  const reducedMotion = matchMedia("(prefers-reduced-motion: reduce)");
  const reveals = new Set();
  function cancelReveals() {
    reveals.forEach(animation => animation.cancel());
    reveals.clear();
  }
  function revealCards() {
    if (reducedMotion.matches) return;
    const cards = seasons.filter(section => !section.hidden)
      .flatMap(section => [...section.querySelectorAll(".project-card-link")]);
    if (!cards.length || typeof cards[0].animate !== "function") return;
    try {
      cards.forEach((card, index) => {
        const animation = card.animate([
          { clipPath: "inset(0 0 100% 0)", opacity: 0, transform: "translateY(-6px)" },
          { clipPath: "inset(0 0 0% 0)", opacity: 1, transform: "translateY(0)" }
        ], {
          duration: 540,
          delay: Math.min(index * 28, 100),
          easing: "cubic-bezier(.22, .61, .36, 1)",
          fill: "backwards"
        });
        reveals.add(animation);
        animation.onfinish = animation.oncancel = () => reveals.delete(animation);
      });
    } catch {
      cancelReveals();
    }
  }
  const motionChanged = () => { if (reducedMotion.matches) cancelReveals(); };
  if (typeof reducedMotion.addEventListener === "function") {
    reducedMotion.addEventListener("change", motionChanged);
  } else if (typeof reducedMotion.addListener === "function") {
    reducedMotion.addListener(motionChanged);
  }
  function filterArchive(id, announce = true, animate = true) {
    cancelReveals();
    if (!filterLinks.some(link => link.dataset.filter === id)) id = "all";
    seasons.forEach(section => { section.hidden = id !== "all" && section.dataset.season !== id; });
    filterLinks.forEach(link => {
      if (link.dataset.filter === id) link.setAttribute("aria-current", "true");
      else link.removeAttribute("aria-current");
    });
    const status = document.querySelector(".filter-status");
    if (status && announce) {
      const count = seasons.filter(s => !s.hidden).reduce((n,s) => n+s.querySelectorAll(".project-card").length,0);
      status.textContent = `${count} projects shown.`;
    }
    if (animate) revealCards();
  }
  filterLinks.forEach(link => link.addEventListener("click", event => {
    event.preventDefault();
    const id = link.dataset.filter;
    filterArchive(id);
    history.replaceState(null, "", `#${id}`);
  }));
  if (filterLinks.length) {
    filterArchive(location.hash.slice(1), false, false);
    addEventListener("hashchange", () => filterArchive(location.hash.slice(1)));
  }

  const index = document.querySelector(".project-index");
  if (index && matchMedia("(max-width:700px)").matches) index.open = false;

  const dialog = document.querySelector(".lightbox");
  const images = [...document.querySelectorAll("[data-gallery-image]")];
  if (!dialog || !images.length || typeof dialog.showModal !== "function") return;
  const picture = dialog.querySelector(".lightbox-image");
  const label = dialog.querySelector(".lightbox-label");
  const position = dialog.querySelector(".lightbox-position");
  const previous = dialog.querySelector("[data-lightbox-prev]");
  const next = dialog.querySelector("[data-lightbox-next]");
  let selected = 0;
  function display(i) {
    selected = Math.max(0, Math.min(images.length - 1, i));
    const source = images[selected].querySelector("img");
    picture.src = images[selected].href;
    picture.alt = source.alt;
    label.textContent = source.alt;
    position.textContent = `${selected + 1} / ${images.length}`;
    previous.disabled = selected === 0;
    next.disabled = selected === images.length - 1;
  }
  images.forEach((link, i) => link.addEventListener("click", event => {
    if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    display(i);
    dialog.showModal();
    document.body.classList.add("lightbox-open");
  }));
  previous.addEventListener("click", () => display(selected - 1));
  next.addEventListener("click", () => display(selected + 1));
  dialog.querySelector(".lightbox-close").addEventListener("click", () => dialog.close());
  dialog.addEventListener("close", () => { document.body.classList.remove("lightbox-open"); });
  dialog.addEventListener("keydown", event => {
    if (event.key === "ArrowLeft") { event.preventDefault(); display(selected - 1); }
    if (event.key === "ArrowRight") { event.preventDefault(); display(selected + 1); }
  });
})();
