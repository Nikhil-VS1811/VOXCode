let recognition;

const startBtn = document.querySelector("#startBtn");
const stopBtn = document.querySelector("#stopBtn");
const status = document.querySelector("#status");
const textOut = document.querySelector("#textOut");
const respOut = document.querySelector("#respOut");
const filesList = document.querySelector("#filesList");

if (window.SpeechRecognition || window.webkitSpeechRecognition) {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  recognition = new SR();
  recognition.lang = "en-IN";
  recognition.interimResults = false;

  recognition.onstart = () => {
    status.textContent = "Status: listening…";
    startBtn.disabled = true;
    stopBtn.disabled = false;
  };

  recognition.onresult = (e) => {
    const text = e.results[0][0].transcript;
    textOut.textContent = text;
    status.textContent = "Sending to server…";

    fetch("/command", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    })
      .then((r) => r.json().then((j) => ({ ok: r.ok, j })))
      .then(({ ok, j }) => {
        respOut.textContent = JSON.stringify(j, null, 2);

        if (ok && j.action === "generate_program") {
          const li = document.createElement("li");
          li.innerHTML = `<a href="/generated/${j.filename}">${j.filename}</a>`;
          filesList.prepend(li);
        }

        status.textContent = "Status: idle";
      });
  };

  recognition.onend = () => {
    startBtn.disabled = false;
    stopBtn.disabled = true;
    status.textContent = "Status: idle";
  };
}

startBtn.addEventListener("click", () => recognition.start());
stopBtn.addEventListener("click", () => recognition.stop());
