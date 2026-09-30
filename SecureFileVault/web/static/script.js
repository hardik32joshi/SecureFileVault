/* ==========================================================================
   Secure File Vault — frontend logic
   Talks to the Flask API in server.py. No frameworks — plain fetch().
   ========================================================================== */

// ---- State ----
let currentMode = "encrypt";   // "encrypt" | "decrypt"
let selectedFile = null;

// ---- Element references ----
const modeButtons     = document.querySelectorAll(".mode-btn");
const dropzone         = document.getElementById("dropzone");
const dropzoneTitle    = document.getElementById("dropzoneTitle");
const dropzoneSub      = document.getElementById("dropzoneSub");
const fileInput        = document.getElementById("fileInput");
const fileChip         = document.getElementById("fileChip");
const fileChipName     = document.getElementById("fileChipName");
const fileChipSize     = document.getElementById("fileChipSize");
const fileChipRemove   = document.getElementById("fileChipRemove");
const dropzoneInner     = document.querySelector(".dropzone-inner");

const passwordInput    = document.getElementById("passwordInput");
const passwordLabel    = document.getElementById("passwordLabel");
const togglePassword   = document.getElementById("togglePassword");
const generateBtn      = document.getElementById("generatePassword");

const strengthBlock    = document.getElementById("strengthBlock");
const strengthLabel    = document.getElementById("strengthLabel");
const strengthHint     = document.getElementById("strengthHint");
const dialTicks        = document.querySelectorAll(".dial-tick");

const submitBtn        = document.getElementById("submitBtn");
const submitBtnText     = document.getElementById("submitBtnText");

const receiptSlot       = document.getElementById("receiptSlot");
const ledgerLog          = document.getElementById("ledgerLog");
const statusDot          = document.getElementById("status-dot") || document.querySelector(".status-dot");
const serverStatus        = document.getElementById("serverStatus");

// ==========================================================================
// SERVER CONNECTIVITY CHECK
// ==========================================================================
async function checkServer() {
  try {
    const res = await fetch("/api/logs");
    if (res.ok) {
      statusDot.classList.add("online");
      serverStatus.textContent = "vault online";
    }
  } catch (e) {
    serverStatus.textContent = "offline";
  }
}
checkServer();

// ==========================================================================
// MODE SWITCHING (Lock / Unlock)
// ==========================================================================
modeButtons.forEach((btn) => {
  btn.addEventListener("click", () => {
    modeButtons.forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    currentMode = btn.dataset.mode;
    updateModeUI();
  });
});

function updateModeUI() {
  const isEncrypt = currentMode === "encrypt";

  dropzoneTitle.textContent = isEncrypt ? "Drop a file to lock" : "Drop an encrypted (.enc) file to unlock";
  dropzoneSub.textContent = isEncrypt
    ? "or click to browse — any file type, any size up to 200MB"
    : "or click to browse — must be a file produced by this vault";

  passwordLabel.textContent = isEncrypt ? "Combination" : "Enter the combination";
  passwordInput.placeholder = isEncrypt ? "Choose a password" : "Enter the original password";

  strengthBlock.style.display = isEncrypt ? "flex" : "none";

  submitBtnText.textContent = isEncrypt ? "Lock file" : "Unlock file";
  submitBtn.classList.toggle("mode-decrypt", !isEncrypt);

  validateForm();
}

// ==========================================================================
// FILE SELECTION (click + drag/drop)
// ==========================================================================
dropzone.addEventListener("click", () => {
  if (!selectedFile) fileInput.click();
});

fileInput.addEventListener("change", () => {
  if (fileInput.files.length > 0) setSelectedFile(fileInput.files[0]);
});

["dragenter", "dragover"].forEach((evt) => {
  dropzone.addEventListener(evt, (e) => {
    e.preventDefault();
    dropzone.classList.add("dragover");
  });
});
["dragleave", "drop"].forEach((evt) => {
  dropzone.addEventListener(evt, (e) => {
    e.preventDefault();
    dropzone.classList.remove("dragover");
  });
});
dropzone.addEventListener("drop", (e) => {
  if (e.dataTransfer.files.length > 0) setSelectedFile(e.dataTransfer.files[0]);
});

function setSelectedFile(file) {
  selectedFile = file;
  fileChipName.textContent = file.name;
  fileChipSize.textContent = formatBytes(file.size);
  fileChip.hidden = false;
  dropzoneInner.hidden = true;
  validateForm();
}

fileChipRemove.addEventListener("click", (e) => {
  e.stopPropagation();
  selectedFile = null;
  fileInput.value = "";
  fileChip.hidden = true;
  dropzoneInner.hidden = false;
  validateForm();
});

function formatBytes(bytes) {
  const units = ["B", "KB", "MB", "GB"];
  let size = bytes, i = 0;
  while (size >= 1024 && i < units.length - 1) { size /= 1024; i++; }
  return `${size.toFixed(2)} ${units[i]}`;
}

// ==========================================================================
// PASSWORD: show/hide, strength check, generator
// ==========================================================================
togglePassword.addEventListener("click", () => {
  const isHidden = passwordInput.type === "password";
  passwordInput.type = isHidden ? "text" : "password";
  togglePassword.textContent = isHidden ? "◎" : "◉";
});

let strengthDebounce = null;
passwordInput.addEventListener("input", () => {
  validateForm();
  if (currentMode !== "encrypt") return;

  clearTimeout(strengthDebounce);
  strengthDebounce = setTimeout(checkStrength, 150); // light debounce
});

async function checkStrength() {
  const password = passwordInput.value;
  if (!password) {
    updateDial(0, "—", "");
    return;
  }
  try {
    const res = await fetch("/api/password-strength", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password }),
    });
    const data = await res.json();
    updateDial(data.score, data.label, data.suggestions[0] || "");
  } catch (e) {
    // Fail silently — strength check is advisory, not blocking.
  }
}

function updateDial(score, label, hint) {
  dialTicks.forEach((tick, i) => {
    tick.classList.toggle("lit", i < score);
    tick.style.background = i < score ? tickColor(score) : "";
  });
  strengthLabel.textContent = label;
  strengthHint.textContent = hint;
}

function tickColor(score) {
  if (score <= 1) return "var(--rust)";
  if (score <= 3) return "var(--brass)";
  return "var(--good)";
}

generateBtn.addEventListener("click", async () => {
  try {
    const res = await fetch("/api/generate-password?length=16");
    const data = await res.json();
    passwordInput.value = data.password;
    passwordInput.type = "text";
    togglePassword.textContent = "◎";
    validateForm();
    if (currentMode === "encrypt") checkStrength();
  } catch (e) {
    alert("Could not reach the vault server to generate a password.");
  }
});

// ==========================================================================
// FORM VALIDATION
// ==========================================================================
function validateForm() {
  submitBtn.disabled = !(selectedFile && passwordInput.value.length > 0);
}

// ==========================================================================
// SUBMIT: encrypt or decrypt
// ==========================================================================
submitBtn.addEventListener("click", async () => {
  if (!selectedFile || !passwordInput.value) return;

  submitBtn.disabled = true;
  submitBtn.classList.add("loading");

  const formData = new FormData();
  formData.append("file", selectedFile);
  formData.append("password", passwordInput.value);

  const endpoint = currentMode === "encrypt" ? "/api/encrypt" : "/api/decrypt";

  try {
    const res = await fetch(endpoint, { method: "POST", body: formData });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ error: "Unknown error." }));
      renderReceipt(false, { message: err.error || "Request failed." });
      return;
    }

    // Successful response is a file blob; hash is in a custom header.
    const blob = await res.blob();
    const disposition = res.headers.get("Content-Disposition") || "";
    const filenameMatch = disposition.match(/filename="?([^"]+)"?/);
    const downloadName = filenameMatch ? filenameMatch[1] : "output_file";

    const hashHeader = currentMode === "encrypt"
      ? res.headers.get("X-Original-SHA256")
      : res.headers.get("X-Decrypted-SHA256");

    const downloadUrl = URL.createObjectURL(blob);

    renderReceipt(true, {
      mode: currentMode,
      originalName: selectedFile.name,
      outputName: downloadName,
      hash: hashHeader,
      downloadUrl,
    });

    refreshLog();

  } catch (e) {
    renderReceipt(false, { message: "Could not reach the vault server." });
  } finally {
    submitBtn.disabled = false;
    submitBtn.classList.remove("loading");
    validateForm();
  }
});

// ==========================================================================
// RECEIPT RENDERING
// ==========================================================================
function renderReceipt(success, info) {
  if (!success) {
    receiptSlot.innerHTML = `
      <div class="receipt">
        <div class="receipt-status err">✕ &nbsp;Transaction failed</div>
        <div class="receipt-row"><span class="k">Reason</span><span class="v">${escapeHtml(info.message)}</span></div>
      </div>`;
    return;
  }

  const verb = info.mode === "encrypt" ? "Locked" : "Unlocked";
  const hashLabel = info.mode === "encrypt" ? "Original file SHA-256" : "Recovered file SHA-256";

  receiptSlot.innerHTML = `
    <div class="receipt">
      <div class="receipt-status ok">✓ &nbsp;${verb} successfully</div>
      <div class="receipt-row"><span class="k">Source</span><span class="v">${escapeHtml(info.originalName)}</span></div>
      <div class="receipt-row"><span class="k">Output</span><span class="v">${escapeHtml(info.outputName)}</span></div>
      <div class="receipt-row"><span class="k">${hashLabel}</span><span class="v">${escapeHtml(info.hash || "n/a")}</span></div>
      <a class="receipt-download" href="${info.downloadUrl}" download="${info.outputName}">⇩ Download ${escapeHtml(info.outputName)}</a>
    </div>`;
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

// ==========================================================================
// ACTIVITY LOG (ledger)
// ==========================================================================
async function refreshLog() {
  try {
    const res = await fetch("/api/logs");
    const data = await res.json();
    ledgerLog.innerHTML = data.logs
      .map((line) => `<div class="ledger-log-line">${escapeHtml(line.trim())}</div>`)
      .join("");
  } catch (e) {
    // Non-critical — ledger is a nice-to-have view.
  }
}
refreshLog();

// ---- Init ----
updateModeUI();
