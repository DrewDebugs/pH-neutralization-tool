// Runs Python (Pyodide) in a background thread (a Web Worker), so the page
// never freezes while the model computes. The page talks to it through
// js/py.js: it sends {id, name, params} and gets back {id, result | error}.
// The Python files are the SAME files tested by pytest (copied into
// py/phsim/ by scripts/build_site.py).

const PYODIDE_VERSION = "0.29.5";   // the ONE place the Pyodide version is set
const PYODIDE_URL = "https://cdn.jsdelivr.net/npm/pyodide@" + PYODIDE_VERSION + "/";
importScripts(PYODIDE_URL + "pyodide.js");

let pythonReady = null;   // one shared promise, so Python loads only once

async function startPython() {
  const started = performance.now();
  self.postMessage({ status: "Loading Python in your browser (first visit downloads ~12 MB)…" });
  const pyodide = await loadPyodide({ indexURL: PYODIDE_URL });

  // Copy our model files into Pyodide's virtual file system.
  // (Paths are relative to this worker file, which lives in js/.)
  const files = await (await fetch("../py/manifest.json")).json();
  pyodide.FS.mkdirTree("/home/pyodide/phsim");
  for (const name of files) {
    const text = await (await fetch("../py/phsim/" + name)).text();
    pyodide.FS.writeFile("/home/pyodide/phsim/" + name, text);
  }
  pyodide.runPython("import sys; sys.path.insert(0, '/home/pyodide'); import phsim.api");
  const seconds = ((performance.now() - started) / 1000).toFixed(1);
  self.postMessage({ status: "Python ready (" + seconds + " s)" });
  return pyodide;
}

// One message = one call to a function in phsim/api.py. Inputs and outputs
// are JSON text, so nothing crosses the JavaScript/Python boundary hidden.
self.onmessage = async (event) => {
  const { id, name, params } = event.data;
  try {
    pythonReady = pythonReady || startPython();
    const pyodide = await pythonReady;
    const api = pyodide.pyimport("phsim.api");
    const result = params === undefined ? api[name]() : api[name](params);
    self.postMessage({ id, result });
  } catch (err) {
    self.postMessage({ id, error: String((err && err.message) || err) });
  }
};
