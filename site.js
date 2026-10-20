(() => {
  "use strict";
  const filterLinks = [...document.querySelectorAll("[data-filter]")];
  const seasons = [...document.querySelectorAll("[data-season]")];
  function filterArchive(id, announce = true) {
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
  }
  filterLinks.forEach(link => link.addEventListener("click", event => {
    event.preventDefault();
    const id = link.dataset.filter;
    filterArchive(id);
    history.replaceState(null, "", `#${id}`);
  }));
  if (filterLinks.length) {
    filterArchive(location.hash.slice(1), false);
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
