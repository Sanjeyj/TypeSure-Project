/**
 * TypeSure — Frontend Application
 * app.js  (v1.1 — post-audit fix)
 *
 * Responsibilities:
 *  - Capture Tamil text input and send to /api/check
 *  - Render spell-check results with interactive suggestion buttons
 *  - Support correction, undo, recheck, and copy actions
 *  - Load and display check history from /api/history
 *  - Handle dictionary import via /api/dictionary/import
 *  - Export report via /api/report
 *
 * Security note:
 *  - User-submitted text is NEVER inserted via innerHTML.
 *  - Only suggestion words (returned from the server, themselves sourced
 *    from the dictionary) are inserted as textContent.
 *  - No eval() or Function() usage.
 *
 * Fix v1.1: All index-page-specific event listeners and DOM access are now
 *  wrapped inside isEditorPage guard to prevent null-access errors on other
 *  pages (e.g., /about).
 */

"use strict";

/* ═══════════════════════════════════════════════════════════════════════════
   SAMPLE TEXTS
═══════════════════════════════════════════════════════════════════════════ */
const SAMPLES = {
  "1": `வணக்கம். நான் தமிழ் படிக்கிறேன். என் பெயர் மாணவன். நான் கல்லூரியில் படிக்கிறேன். தமிழ் மொழி மிகவும் அழகான மொழி.`,
  "2": `வணககம். நான் தமழ் படிகிறேன். என் அம்மா மருத்துவமனையில் வேலை செய்கிறார். நான் சாபிடு வீட்டில் இருக்கிறேன்.`,
  "3": `Good morning. வணக்கம். I am studying at கல்லூரி. நான் computer science படிக்கிறேன். என் நண்பன் மிகவும் புத்திசாலி.`,
};

/* ═══════════════════════════════════════════════════════════════════════════
   STATE
═══════════════════════════════════════════════════════════════════════════ */
const state = {
  lastResult: null,
  originalText: "",
  currentSpans: [],
  corrections: {},
  correctionsCount: 0,
  selectedFile: null,
};

/* ═══════════════════════════════════════════════════════════════════════════
   DOM REFERENCES (safe — null if element not present on page)
═══════════════════════════════════════════════════════════════════════════ */
const $ = (id) => document.getElementById(id);

const el = {
  input:            $("tamil-input"),
  charCount:        $("char-count"),
  wordCount:        $("word-count"),
  btnCheck:         $("btn-check"),
  btnClear:         $("btn-clear"),
  btnUndo:          $("btn-undo"),
  btnRecheck:       $("btn-recheck"),
  btnExport:        $("btn-export"),
  btnCopyCorrected: $("btn-copy-corrected"),
  storeTextToggle:  $("store-text-toggle"),
  loadingOverlay:   $("loading-overlay"),
  errorBanner:      $("error-banner"),
  errorMessage:     $("error-message"),
  statsSection:     $("stats-section"),
  statTotalVal:     $("stat-total-val"),
  statIssuesVal:    $("stat-issues-val"),
  statRecognizedVal:$("stat-recognized-val"),
  statCoverageVal:  $("stat-coverage-val"),
  resultsSection:   $("results-section"),
  noIssuesMsg:      $("no-issues-msg"),
  issuesList:       $("issues-list"),
  previewSection:   $("preview-section"),
  correctedPreview: $("corrected-preview"),
  correctionsCount: $("corrections-count"),
  historyList:      $("history-list"),
  // Import modal
  importModal:      $("import-modal"),
  btnImportOpen:    $("btn-import-open"),
  btnImportCancel:  $("btn-import-cancel"),
  btnImportConfirm: $("btn-import-confirm"),
  importModalClose: $("import-modal-close"),
  fileDropZone:     $("file-drop-zone"),
  dictFileInput:    $("dict-file-input"),
  importResult:     $("import-result"),
  // Clear history modal
  clearHistoryModal:      $("clear-history-modal"),
  btnClearHistory:        $("btn-clear-history"),
  btnClearHistoryCancel:  $("btn-clear-history-cancel"),
  btnClearHistoryConfirm: $("btn-clear-history-confirm"),
  clearHistoryModalClose: $("clear-history-modal-close"),
  // Nav
  hamburger: $("hamburger"),
  siteNav:   document.querySelector(".site-nav"),
  closePrivacyNotice: $("close-privacy-notice"),
};

/* ═══════════════════════════════════════════════════════════════════════════
   PAGE DETECTION
   isEditorPage = true only when the textarea is present (index.html)
═══════════════════════════════════════════════════════════════════════════ */
const isEditorPage = Boolean(el.input);

/* ═══════════════════════════════════════════════════════════════════════════
   UTILITY HELPERS
═══════════════════════════════════════════════════════════════════════════ */

function showError(msg) {
  if (!el.errorMessage || !el.errorBanner) return;
  el.errorMessage.textContent = msg;
  el.errorBanner.classList.remove("hidden");
  setTimeout(() => el.errorBanner.classList.add("hidden"), 8000);
}
function hideError() {
  if (el.errorBanner) el.errorBanner.classList.add("hidden");
}

function setLoading(on) {
  if (!el.loadingOverlay || !el.btnCheck) return;
  if (on) {
    el.loadingOverlay.classList.add("visible");
    el.btnCheck.disabled = true;
  } else {
    el.loadingOverlay.classList.remove("visible");
    el.btnCheck.disabled = false;
  }
}

function formatTimestamp(iso) {
  try {
    return new Date(iso).toLocaleString("en-IN", {
      dateStyle: "short", timeStyle: "short",
    });
  } catch { return iso; }
}

/* ═══════════════════════════════════════════════════════════════════════════
   EDITOR PAGE — all code below only runs when the editor is present
═══════════════════════════════════════════════════════════════════════════ */

if (isEditorPage) {

  /* ─── Live character / word count ──────────────────────────────────────── */

  function updateCounts() {
    const text = el.input.value;
    const chars = text.length;
    const tamilWords = (text.match(/[\u0B80-\u0BFF]+/g) || []).length;
    const englishWords = (text.match(/[A-Za-z]+/g) || []).length;
    const total = tamilWords + englishWords;
    el.charCount.textContent = `${chars.toLocaleString()} character${chars !== 1 ? "s" : ""}`;
    el.wordCount.textContent = `${total.toLocaleString()} word${total !== 1 ? "s" : ""}`;
  }

  el.input.addEventListener("input", updateCounts);

  /* ─── Sample texts ──────────────────────────────────────────────────────── */

  document.querySelectorAll("[data-sample]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const key = btn.dataset.sample;
      el.input.value = SAMPLES[key] || "";
      updateCounts();
      el.input.focus();
    });
  });

  /* ─── Clear button ──────────────────────────────────────────────────────── */

  el.btnClear.addEventListener("click", () => {
    el.input.value = "";
    updateCounts();
    resetResults();
    el.input.focus();
  });

  function resetResults() {
    el.statsSection.classList.add("hidden");
    el.resultsSection.classList.add("hidden");
    el.previewSection.classList.add("hidden");
    el.issuesList.innerHTML = "";
    el.noIssuesMsg.classList.add("hidden");
    state.lastResult = null;
    state.originalText = "";
    state.currentSpans = [];
    state.corrections = {};
    state.correctionsCount = 0;
    if (el.btnUndo) el.btnUndo.disabled = true;
    hideError();
  }

  /* ─── Spell Check ───────────────────────────────────────────────────────── */

  el.btnCheck.addEventListener("click", runCheck);
  if (el.btnRecheck) el.btnRecheck.addEventListener("click", runCheck);

  async function runCheck() {
    const text = el.input.value.trim();
    if (!text) {
      showError("Please enter some Tamil text before checking.");
      return;
    }
    if (text.length > 20000) {
      showError("Text is too long (maximum 20,000 characters).");
      return;
    }

    resetResults();
    hideError();
    setLoading(true);

    try {
      const resp = await fetch("/api/check", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text,
          store_text: el.storeTextToggle ? el.storeTextToggle.checked : false,
          corrections: state.correctionsCount,
        }),
      });

      const data = await resp.json();

      if (!resp.ok) {
        showError(data.error || "Server returned an error.");
        return;
      }

      state.lastResult = data;
      state.originalText = text;
      state.currentSpans = JSON.parse(JSON.stringify(data.spans));
      state.corrections = {};
      state.correctionsCount = 0;

      renderStats(data.stats);
      renderIssues(data.issues);
      renderPreview();
      loadHistory();

    } catch (err) {
      showError("Could not reach the server. Is Flask running?");
      console.error(err);
    } finally {
      setLoading(false);
    }
  }

  /* ─── Render stats ──────────────────────────────────────────────────────── */

  function renderStats(stats) {
    el.statTotalVal.textContent      = stats.total_words_scanned.toLocaleString();
    el.statIssuesVal.textContent     = stats.issues_found.toLocaleString();
    el.statRecognizedVal.textContent = stats.recognized.toLocaleString();
    el.statCoverageVal.textContent   = stats.dictionary_coverage_pct + "%";
    el.statsSection.classList.remove("hidden");
  }

  /* ─── Render issues ─────────────────────────────────────────────────────── */

  function renderIssues(issues) {
    el.resultsSection.classList.remove("hidden");
    el.issuesList.innerHTML = "";

    if (issues.length === 0) {
      el.noIssuesMsg.classList.remove("hidden");
      return;
    }

    issues.forEach((issue) => {
      const item = document.createElement("div");
      item.className = "issue-item";
      item.dataset.word = issue.word;

      const top = document.createElement("div");
      top.className = "issue-top";

      const badge = document.createElement("span");
      badge.className = "issue-badge";
      badge.textContent = "⚠ Possible Issue";

      const wordEl = document.createElement("span");
      wordEl.className = "issue-word";
      wordEl.textContent = issue.word;

      const occEl = document.createElement("span");
      occEl.className = "issue-occ";
      occEl.textContent = `(${issue.occurrences} occurrence${issue.occurrences > 1 ? "s" : ""})`;

      top.append(badge, wordEl, occEl);

      const sugRow = document.createElement("div");
      sugRow.className = "suggestions-row";

      if (issue.suggestions.length === 0) {
        const noSug = document.createElement("span");
        noSug.className = "no-suggestions";
        noSug.textContent = "No close suggestions found in the current dictionary.";
        sugRow.appendChild(noSug);
      } else {
        const label = document.createElement("span");
        label.className = "suggestions-label";
        label.textContent = "Suggestions:";
        sugRow.appendChild(label);

        issue.suggestions.forEach((sug) => {
          const btn = document.createElement("button");
          btn.className = "suggestion-btn";
          btn.type = "button";
          btn.title = `Replace "${issue.word}" with "${sug.word}" (edit distance: ${sug.distance})`;

          const wordSpan = document.createElement("span");
          wordSpan.textContent = sug.word;

          const distBadge = document.createElement("span");
          distBadge.className = "dist-badge";
          distBadge.textContent = `d=${sug.distance}`;

          btn.append(wordSpan, distBadge);
          btn.addEventListener("click", () => applyCorrection(issue.word, sug.word));
          sugRow.appendChild(btn);
        });
      }

      item.append(top, sugRow);
      el.issuesList.appendChild(item);
    });
  }

  /* ─── Apply correction ──────────────────────────────────────────────────── */

  function applyCorrection(wrongWord, correctWord) {
    if (!state.currentSpans.length) return;

    let changed = 0;
    state.currentSpans.forEach((span) => {
      if (span.is_tamil && span.text === wrongWord) {
        span.text = correctWord;
        span.status = "corrected";
        changed++;
      }
    });

    if (changed === 0) return;

    state.corrections[wrongWord] = correctWord;
    state.correctionsCount += changed;
    if (el.btnUndo) el.btnUndo.disabled = false;

    const issueRow = el.issuesList.querySelector(`[data-word="${CSS.escape(wrongWord)}"]`);
    if (issueRow) {
      issueRow.style.opacity = "0";
      issueRow.style.transition = "opacity 0.3s";
      setTimeout(() => issueRow.remove(), 300);
    }

    const remaining = el.issuesList.querySelectorAll(".issue-item");
    if (remaining.length <= 1) {
      setTimeout(() => {
        if (el.issuesList.querySelectorAll(".issue-item").length === 0) {
          el.noIssuesMsg.classList.remove("hidden");
        }
      }, 400);
    }

    renderPreview();
    updateCorrectionsCounter();
  }

  /* ─── Undo all ──────────────────────────────────────────────────────────── */

  if (el.btnUndo) {
    el.btnUndo.addEventListener("click", () => {
      if (!state.lastResult) return;
      state.currentSpans = JSON.parse(JSON.stringify(state.lastResult.spans));
      state.corrections = {};
      state.correctionsCount = 0;
      el.btnUndo.disabled = true;
      renderIssues(state.lastResult.issues);
      renderPreview();
      updateCorrectionsCounter();
    });
  }

  /* ─── Render preview ────────────────────────────────────────────────────── */

  function renderPreview() {
    el.previewSection.classList.remove("hidden");
    const container = el.correctedPreview;
    container.innerHTML = "";

    state.currentSpans.forEach((span) => {
      const node = document.createElement("span");
      node.textContent = span.text;

      if (span.is_tamil) {
        node.classList.add("tamil-text");
        if (span.status === "corrected") {
          node.classList.add("corrected-word-changed");
        } else if (span.status === "unknown") {
          node.classList.add("corrected-word-unknown");
        } else {
          node.classList.add("corrected-word-ok");
        }
      }
      container.appendChild(node);
    });

    updateCorrectionsCounter();
  }

  function updateCorrectionsCounter() {
    if (!el.correctionsCount) return;
    const n = state.correctionsCount;
    el.correctionsCount.textContent = `${n} correction${n !== 1 ? "s" : ""} applied this session`;
  }

  /* ─── Copy corrected text ───────────────────────────────────────────────── */

  if (el.btnCopyCorrected) {
    el.btnCopyCorrected.addEventListener("click", async () => {
      const text = state.currentSpans.map((s) => s.text).join("");
      try {
        await navigator.clipboard.writeText(text);
        el.btnCopyCorrected.textContent = "✅ Copied!";
        setTimeout(() => { el.btnCopyCorrected.textContent = "📋 Copy"; }, 2000);
      } catch {
        showError("Could not copy to clipboard. Please copy manually.");
      }
    });
  }

  /* ─── Export report ─────────────────────────────────────────────────────── */

  if (el.btnExport) {
    el.btnExport.addEventListener("click", () => {
      window.location.href = "/api/report?format=csv";
    });
  }

  /* ─── History ───────────────────────────────────────────────────────────── */

  async function loadHistory() {
    if (!el.historyList) return;
    try {
      const resp = await fetch("/api/history?limit=20");
      if (!resp.ok) return;
      const data = await resp.json();
      renderHistory(data.history || []);
    } catch { /* silent */ }
  }

  function renderHistory(records) {
    if (!el.historyList) return;
    el.historyList.innerHTML = "";

    if (!records.length) {
      el.historyList.innerHTML = `
        <div class="empty-state">
          <div class="empty-icon">📭</div>
          <p class="empty-title">No history yet</p>
          <p class="empty-sub">Your check results will appear here.</p>
        </div>`;
      return;
    }

    records.forEach((r, i) => {
      const item = document.createElement("div");
      item.className = "history-item";

      const num = document.createElement("div");
      num.className = "history-num";
      num.textContent = i + 1;

      const meta = document.createElement("div");
      meta.className = "history-meta";

      const time = document.createElement("div");
      time.className = "history-time";
      time.textContent = formatTimestamp(r.created_at);

      const stats = document.createElement("div");
      stats.className = "history-stats";
      stats.appendChild(document.createTextNode(`${r.word_count} words · `));
      const strong = document.createElement("strong");
      strong.textContent = `${r.issue_count} issues`;
      stats.appendChild(strong);
      if (r.corrections > 0) {
        stats.appendChild(document.createTextNode(` · ${r.corrections} corrected`));
      }

      meta.append(time, stats);
      item.append(num, meta);
      el.historyList.appendChild(item);
    });
  }

  /* ─── Clear history modal ───────────────────────────────────────────────── */

  function openClearHistoryModal()  {
    if (el.clearHistoryModal) el.clearHistoryModal.classList.remove("hidden");
  }
  function closeClearHistoryModal() {
    if (el.clearHistoryModal) el.clearHistoryModal.classList.add("hidden");
  }

  if (el.btnClearHistory) el.btnClearHistory.addEventListener("click", openClearHistoryModal);
  if (el.btnClearHistoryCancel) el.btnClearHistoryCancel.addEventListener("click", closeClearHistoryModal);
  if (el.clearHistoryModalClose) el.clearHistoryModalClose.addEventListener("click", closeClearHistoryModal);

  if (el.btnClearHistoryConfirm) {
    el.btnClearHistoryConfirm.addEventListener("click", async () => {
      try {
        const resp = await fetch("/api/history", { method: "DELETE" });
        if (resp.ok) renderHistory([]);
      } catch { showError("Failed to clear history."); }
      closeClearHistoryModal();
    });
  }

  /* ─── Dictionary import modal ───────────────────────────────────────────── */

  function openImportModal() {
    if (!el.importModal) return;
    el.importModal.classList.remove("hidden");
    el.importResult.classList.add("hidden");
    el.importResult.textContent = "";
    el.btnImportConfirm.disabled = true;
    state.selectedFile = null;
    el.dictFileInput.value = "";
  }
  function closeImportModal() {
    if (el.importModal) el.importModal.classList.add("hidden");
  }

  if (el.btnImportOpen) el.btnImportOpen.addEventListener("click", openImportModal);
  if (el.btnImportCancel) el.btnImportCancel.addEventListener("click", closeImportModal);
  if (el.importModalClose) el.importModalClose.addEventListener("click", closeImportModal);

  if (el.fileDropZone) {
    el.fileDropZone.addEventListener("click", () => el.dictFileInput && el.dictFileInput.click());
    el.fileDropZone.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") el.dictFileInput && el.dictFileInput.click();
    });
    el.fileDropZone.addEventListener("dragover", (e) => {
      e.preventDefault();
      el.fileDropZone.classList.add("drag-over");
    });
    el.fileDropZone.addEventListener("dragleave", () => {
      el.fileDropZone.classList.remove("drag-over");
    });
    el.fileDropZone.addEventListener("drop", (e) => {
      e.preventDefault();
      el.fileDropZone.classList.remove("drag-over");
      const file = e.dataTransfer.files[0];
      if (file) handleFileSelection(file);
    });
  }

  if (el.dictFileInput) {
    el.dictFileInput.addEventListener("change", () => {
      const file = el.dictFileInput.files[0];
      if (file) handleFileSelection(file);
    });
  }

  function handleFileSelection(file) {
    if (!file.name.toLowerCase().endsWith(".txt")) {
      el.importResult.textContent = "Only .txt files are accepted.";
      el.importResult.className = "import-result error";
      el.importResult.classList.remove("hidden");
      el.btnImportConfirm.disabled = true;
      return;
    }
    state.selectedFile = file;
    const p = el.fileDropZone && el.fileDropZone.querySelector("p");
    if (p) p.textContent = `Selected: ${file.name}`;
    el.btnImportConfirm.disabled = false;
    el.importResult.classList.add("hidden");
  }

  if (el.btnImportConfirm) {
    el.btnImportConfirm.addEventListener("click", async () => {
      if (!state.selectedFile) return;
      el.btnImportConfirm.disabled = true;
      el.btnImportConfirm.textContent = "Importing…";

      const formData = new FormData();
      formData.append("file", state.selectedFile);

      try {
        const resp = await fetch("/api/dictionary/import", {
          method: "POST",
          body: formData,
        });
        const data = await resp.json();

        if (!resp.ok) {
          el.importResult.textContent = data.error || "Import failed.";
          el.importResult.className = "import-result error";
        } else {
          let msg = `✅ Import complete: ${data.added} new words added.`;
          if (data.duplicates > 0) msg += ` ${data.duplicates} duplicates skipped.`;
          if (data.invalid > 0) msg += ` ${data.invalid} invalid lines skipped.`;
          if (data.errors && data.errors.length > 0) {
            msg += "\n\nWarnings:\n" + data.errors.join("\n");
          }
          el.importResult.textContent = msg;
          el.importResult.className = "import-result success";
        }
        el.importResult.classList.remove("hidden");
      } catch {
        el.importResult.textContent = "Network error during import.";
        el.importResult.className = "import-result error";
        el.importResult.classList.remove("hidden");
      }

      el.btnImportConfirm.textContent = "Import";
      el.btnImportConfirm.disabled = false;
    });
  }

  /* ─── Close modals on overlay click ────────────────────────────────────── */

  [el.importModal, el.clearHistoryModal].forEach((modal) => {
    if (modal) {
      modal.addEventListener("click", (e) => {
        if (e.target === modal) modal.classList.add("hidden");
      });
    }
  });

  /* ─── INIT (editor page) ────────────────────────────────────────────────── */
  updateCounts();
  loadHistory();

} // end isEditorPage

/* ═══════════════════════════════════════════════════════════════════════════
   SHARED ACROSS ALL PAGES
═══════════════════════════════════════════════════════════════════════════ */

/* ─── Hamburger menu (mobile) ───────────────────────────────────────────── */

if (el.hamburger && el.siteNav) {
  el.hamburger.addEventListener("click", () => {
    const open = el.siteNav.classList.toggle("open");
    el.hamburger.setAttribute("aria-expanded", String(open));
  });

  // Close menu when a nav link is clicked (mobile)
  el.siteNav.querySelectorAll(".nav-link").forEach((link) => {
    link.addEventListener("click", () => {
      el.siteNav.classList.remove("open");
      el.hamburger.setAttribute("aria-expanded", "false");
    });
  });
}

/* ─── Privacy notice dismiss ────────────────────────────────────────────── */

if (el.closePrivacyNotice) {
  el.closePrivacyNotice.addEventListener("click", () => {
    const notice = $("privacy-notice");
    if (notice) notice.style.display = "none";
  });
}

/* ─── Update footer copyright year dynamically ──────────────────────────── */
const copyrightYearEl = $("copyright-year");
if (copyrightYearEl) {
  copyrightYearEl.textContent = new Date().getFullYear();
}
