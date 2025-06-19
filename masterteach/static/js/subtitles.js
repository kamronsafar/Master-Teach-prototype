let subtitles = [];
let lang = "ru";

document.addEventListener("DOMContentLoaded", () => {
  const video = document.getElementById("video-player");
  const originalEl = document.getElementById("subtitle-original");
  const translatedEl = document.getElementById("subtitle-translated");
  const languageSelect = document.getElementById("language-select");

  languageSelect.addEventListener("change", () => {
    lang = languageSelect.value;
    fetchSubtitles();
  });

  function fetchSubtitles() {
    fetch("/films/api/translate/dual/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCookie("csrftoken")
      },
      body: JSON.stringify({
        film_id: {{ film.id }},
        target_language: lang
      })
    })
    .then(res => res.json())
    .then(data => {
      subtitles = data.subtitles;
    });
  }

  function getCookie(name) {
    const value = `; ${document.cookie}`;
    return value.split(`; ${name}=`).pop().split(";").shift();
  }

  video.addEventListener("timeupdate", () => {
    const currentTime = video.currentTime;
    const current = subtitles.find(s => currentTime >= s.start && currentTime <= s.end);
    if (current) {
      originalEl.innerText = current.original;
      translatedEl.innerText = current.translated;
    } else {
      originalEl.innerText = "";
      translatedEl.innerText = "";
    }
  });

  fetchSubtitles();
});
