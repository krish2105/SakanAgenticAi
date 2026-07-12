const PENDING_QUERY_KEY = "sakan_ext_pending_query";
const CONTEXT_MENU_ID = "sakan-check-selection";

chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: CONTEXT_MENU_ID,
    title: 'Check with Sakan AI: "%s"',
    contexts: ["selection"],
  });
});

chrome.contextMenus.onClicked.addListener((info) => {
  if (info.menuItemId !== CONTEXT_MENU_ID || !info.selectionText) return;
  // MV3 service workers can't programmatically open the toolbar popup, so
  // this stashes the selection and popup.js picks it up (and clears it)
  // the next time the user opens the popup themselves.
  chrome.storage.local.set({ [PENDING_QUERY_KEY]: info.selectionText });
  chrome.action.setBadgeText({ text: "1" });
  chrome.action.setBadgeBackgroundColor({ color: "#c9a227" });
});

chrome.runtime.onMessage.addListener((message) => {
  if (message?.type === "open-popup-tab") {
    // content.js's floating button can't open the toolbar popup either
    // (same MV3 restriction), so it opens popup.html as a normal tab
    // instead -- the page works identically either way since it's the
    // same chrome.storage-backed logic in popup.js.
    chrome.tabs.create({ url: chrome.runtime.getURL("popup.html") });
  }
});
