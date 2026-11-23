// The pages' only doorway to Python:
//     const result = await callPy("simulation", params, onStatus)
// The work happens in js/py-worker.js (a background thread running Pyodide),
// so the page stays responsive while the model runs.

const pyWorker = new Worker("js/py-worker.js");
const pendingCalls = new Map();   // call id -> {resolve, reject}
let nextCallId = 0;
let statusListener = () => {};

pyWorker.onmessage = (event) => {
  const msg = event.data;
  if (msg.status !== undefined) {           // progress text while Python loads
    statusListener(msg.status);
    return;
  }
  const call = pendingCalls.get(msg.id);
  pendingCalls.delete(msg.id);
  if (msg.error !== undefined) call.reject(new Error(msg.error));
  else call.resolve(JSON.parse(msg.result));
};

function callPy(name, params, onStatus) {
  if (onStatus) statusListener = onStatus;
  return new Promise((resolve, reject) => {
    const id = ++nextCallId;
    pendingCalls.set(id, { resolve, reject });
    pyWorker.postMessage({ id, name, params: params === undefined ? undefined : JSON.stringify(params) });
  });
}
