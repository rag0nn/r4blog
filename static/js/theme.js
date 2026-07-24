(() => {
  const root = document.documentElement;
  const slider = document.querySelector(".bg-slider");
  const steps = { white: 0, reading: 1, colorful: 2 };
  const stored = localStorage.getItem("r4blog-theme");
  const initial = Object.hasOwn(steps, stored) ? stored : "white";

  function selectTheme(theme) {
    if (!Object.hasOwn(steps, theme)) return;
    root.dataset.theme = theme;
    if (slider) slider.style.transform = `translateX(-${steps[theme] * 100}vw)`;
    localStorage.setItem("r4blog-theme", theme);
    document.querySelectorAll("[data-theme-choice]").forEach((button) => {
      button.setAttribute("aria-pressed", button.dataset.themeChoice === theme ? "true" : "false");
    });
  }

  selectTheme(initial);
  document.querySelectorAll("[data-theme-choice]").forEach((button) => {
    button.addEventListener("click", () => selectTheme(button.dataset.themeChoice));
  });

  const menuButton = document.querySelector(".mobile-menu");
  const menu = document.querySelector(".header-content");
  if (menuButton && menu) {
    menuButton.addEventListener("click", () => {
      const open = menu.classList.toggle("is-open");
      menuButton.setAttribute("aria-expanded", open ? "true" : "false");
    });
  }
})();

