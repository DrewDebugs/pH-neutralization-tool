// Theory page: each equation (rendered by KaTeX) next to the exact Python
// function that implements it. The code is read from the running model
// with inspect.getsource(), so it cannot be out of date.

function escapeHtml(text) {
  return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

async function showTheory() {
  const statusText = document.getElementById("status-text");
  document.getElementById("status").classList.add("busy");
  const entries = await callPy("theory", undefined, (t) => (statusText.textContent = t));
  const container = document.getElementById("equations");
  const toc = document.getElementById("toc");
  container.innerHTML = "";
  entries.forEach((e, i) => {
    const anchor = "eq-" + i;
    const card = document.createElement("article");
    card.className = "card eq-card";
    card.id = anchor;
    card.innerHTML = `
      <h3><span class="tag">${e.id}</span>${e.title}</h3>
      <div class="math"></div>
      <p class="src">phsim.${e.function}</p>
      <pre class="code"><code class="language-python">${escapeHtml(e.code)}</code></pre>`;
    katex.render(e.latex, card.querySelector(".math"), { displayMode: true, throwOnError: false });
    if (window.hljs) hljs.highlightElement(card.querySelector("code"));
    container.appendChild(card);
    toc.insertAdjacentHTML("beforeend",
      `<a href="#${anchor}"><span class="tid">${e.id}</span>${e.title}</a>`);
  });
  document.getElementById("status").remove();
}

showTheory().catch((err) => {
  document.getElementById("status-text").textContent = "Could not load Python: " + err.message;
});
