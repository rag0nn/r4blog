(() => {
  const root = document.documentElement;
  const allowed = new Set(["en", "tr"]);
  const stored = localStorage.getItem("r4blog-language");

  function applyLanguage(language) {
    if (!allowed.has(language)) return;
    root.lang = language;
    root.dataset.language = language;
    localStorage.setItem("r4blog-language", language);

    document.querySelectorAll("[data-i18n-en][data-i18n-tr]").forEach((element) => {
      element.textContent = language === "tr" ? element.dataset.i18nTr : element.dataset.i18nEn;
    });
    document.querySelectorAll("[data-placeholder-en][data-placeholder-tr]").forEach((element) => {
      element.placeholder = language === "tr" ? element.dataset.placeholderTr : element.dataset.placeholderEn;
    });
    document.querySelectorAll("[data-aria-en][data-aria-tr]").forEach((element) => {
      element.setAttribute("aria-label", language === "tr" ? element.dataset.ariaTr : element.dataset.ariaEn);
    });
    document.querySelectorAll("[data-language-content]").forEach((element) => {
      element.hidden = element.dataset.languageContent !== language;
    });
    document.querySelectorAll("[data-language-choice]").forEach((button) => {
      button.setAttribute("aria-pressed", button.dataset.languageChoice === language ? "true" : "false");
    });

    const manualEditor = document.getElementById("id_manual_content");
    if (manualEditor) {
      manualEditor.placeholder = language === "tr"
        ? "# Zorunlu başlık\n\nMarkdown içeriğini buraya yaz..."
        : "# Required title\n\nWrite your Markdown here...";
    }
    const visibility = document.getElementById("id_visibility");
    if (visibility) {
      const publicOption = visibility.querySelector('option[value="public"]');
      const privateOption = visibility.querySelector('option[value="private"]');
      if (publicOption) publicOption.textContent = language === "tr" ? "Herkese Açık" : "Public";
      if (privateOption) privateOption.textContent = language === "tr" ? "Özel" : "Private";
    }
  }

  applyLanguage(allowed.has(stored) ? stored : "en");
  document.querySelectorAll("[data-language-choice]").forEach((button) => {
    button.addEventListener("click", () => applyLanguage(button.dataset.languageChoice));
  });
})();
