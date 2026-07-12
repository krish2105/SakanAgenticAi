async function init() {
  const input = document.getElementById("backend-url");
  input.value = await SakanAPI.getBackendUrl();

  document.getElementById("settings-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    await SakanAPI.setBackendUrl(input.value.trim());
    const note = document.getElementById("saved-note");
    note.hidden = false;
    setTimeout(() => (note.hidden = true), 1500);
  });
}

document.addEventListener("DOMContentLoaded", init);
