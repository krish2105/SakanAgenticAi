/**
 * Deliberately does NOT scrape listing price/details off the page. This
 * repo has no access to bayut.com's or propertyfinder.ae's real DOM
 * structure to build and verify a scraper against, and a guessed selector
 * breaks the moment the site's markup changes -- silently returning wrong
 * numbers is worse than not extracting anything. This just adds a visible
 * entry point into the extension while the user is already looking at a
 * listing; matching CRM/portal-specific field extraction is real future
 * work, not faked here.
 */
(function () {
  if (document.getElementById("sakan-ai-fab")) return;

  const button = document.createElement("button");
  button.id = "sakan-ai-fab";
  button.type = "button";
  button.title = "Check this listing with Sakan AI";
  button.textContent = "Sakan AI";

  button.addEventListener("click", () => {
    chrome.runtime.sendMessage({ type: "open-popup-tab" });
  });

  document.documentElement.appendChild(button);
})();
