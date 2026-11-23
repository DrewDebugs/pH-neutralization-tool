// Theory page: each equation (rendered by KaTeX) next to the exact Python
// function that implements it. The code is read from the running model
// with inspect.getsource(), so it cannot be out of date.

function escapeHtml(text) {
  return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

async function showTheory() {
  const status = document.getElementById("status");
  const entries = await callPy("theory", undefined, (t) => (status.textContent = t));
  const container = document.getElementById("equations");
  container.innerHTML = "";
  for (const e of entries) {
    const card = document.createElement("div");
    card.className = "card";
    card.innerHTML = `
      <h3><span class="tag">${e.id}</span>${e.title}</h3>
      <div class="eq-row">
        <div class="math"></div>
        <pre class="code"><code>${escapeHtml(e.code)}</code></pre>
      </div>`;
    katex.render(e.latex, card.querySelector(".math"), { displayMode: true, throwOnError: false });
    container.appendChild(card);
  }
  status.textContent = "";
}

showTheory().catch((err) => {
  document.getElementById("status").textContent = "Could not load Python: " + err.message;
});
