// Loads Python (Pyodide) in the browser and gives the pages one function:
//     await callPy("simulation", params)  ->  result object
// The Python files are the SAME files tested by pytest (copied into
// py/phsim/ by scripts/build_site.py). No server: everything runs here.

const PYODIDE_VERSION = "0.29.5";   // pinned: change only on purpose
const PYODIDE_URL = "https://cdn.jsdelivr.net/npm/pyodide@" + PYODIDE_VERSION + "/";

let pythonReady = null;   // one shared promise, so Python loads only once

function loadPython(onStatus) {
  if (pythonReady) return pythonReady;
  pythonReady = (async () => {
    const started = performance.now();
    onStatus("Loading Python in your browser (first visit downloads ~12 MB)…");
    const pyodide = await loadPyodide({ indexURL: PYODIDE_URL });

    // Copy our model files into Pyodide's virtual file system.
    const files = await (await fetch("py/manifest.json")).json();
    pyodide.FS.mkdirTree("/home/pyodide/phsim");
    for (const name of files) {
      const text = await (await fetch("py/phsim/" + name)).text();
      pyodide.FS.writeFile("/home/pyodide/phsim/" + name, text);
    }
    pyodide.runPython("import sys; sys.path.insert(0, '/home/pyodide'); import phsim.api");
    const seconds = ((performance.now() - started) / 1000).toFixed(1);
    onStatus("Python ready (" + seconds + " s).");
    return pyodide;
  })();
  return pythonReady;
}

// Call a function in phsim/api.py. Inputs and outputs cross the
// JavaScript/Python boundary as JSON text, so nothing is hidden.
async function callPy(name, params, onStatus = () => {}) {
  const pyodide = await loadPython(onStatus);
  const api = pyodide.pyimport("phsim.api");
  const text = params === undefined ? api[name]() : api[name](JSON.stringify(params));
  return JSON.parse(text);
}
