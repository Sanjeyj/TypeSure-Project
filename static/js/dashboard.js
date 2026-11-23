/**
 * TypeSure — Dashboard Interactive Controller
 * dashboard.js
 *
 * Handles:
 *  - Sidebar navigation & tab switching (Overview, Checker, Dictionary, History, Analytics, Settings)
 *  - Jump to checker shortcuts
 *  - User profile update form via /api/auth/profile
 *  - Theme switching within settings
 *  - Dynamic breadcrumb update
 */

"use strict";

document.addEventListener("DOMContentLoaded", () => {
  const sidebarLinks = document.querySelectorAll(".sidebar-link[data-tab]");
  const tabPanes = document.querySelectorAll(".tab-pane");
  const tabTitle = document.getElementById("current-tab-title");

  const tabTitles = {
    overview: "Dashboard Overview",
    checker: "Tamil Spell Checker Workspace",
    dictionary: "Master Tamil Lexicon (12,500+ Words)",
    personal: "Personal Custom Dictionary",
    history: "Check History & Activity Logs",
    analytics: "Accuracy & Coverage Analytics",
    settings: "Profile & System Preferences",
  };

  /**
   * Switch active tab
   * @param {string} tabId
   */
  function switchTab(tabId) {
    if (!tabId) return;

    // Update active tab buttons
    sidebarLinks.forEach((link) => {
      const match = link.getAttribute("data-tab") === tabId;
      link.classList.toggle("active", match);
      link.setAttribute("aria-selected", String(match));
    });

    // Update active tab panels
    tabPanes.forEach((pane) => {
      const match = pane.id === `tab-${tabId}`;
      pane.classList.toggle("active", match);
    });

    // Update breadcrumb
    if (tabTitle && tabTitles[tabId]) {
      tabTitle.textContent = tabTitles[tabId];
    }

    // Update URL hash without jumping
    history.replaceState(null, "", `#${tabId}`);
  }

  // Bind sidebar link clicks
  sidebarLinks.forEach((link) => {
    link.addEventListener("click", (e) => {
      e.preventDefault();
      const tabId = link.getAttribute("data-tab");
      switchTab(tabId);
    });
  });

  // Jump to checker button (on overview banner)
  const jumpBtn = document.getElementById("btn-jump-checker");
  if (jumpBtn) {
    jumpBtn.addEventListener("click", () => switchTab("checker"));
  }

  // Any other data-tab-switch buttons
  document.querySelectorAll("[data-tab-switch]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const target = btn.getAttribute("data-tab-switch");
      if (target) switchTab(target);
    });
  });

  // Initial tab from hash (if present)
  if (window.location.hash) {
    const hash = window.location.hash.replace("#", "");
    if (tabTitles[hash]) {
      switchTab(hash);
    }
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // PROFILE UPDATE FORM
  // ═══════════════════════════════════════════════════════════════════════════
  const profileForm = document.getElementById("profile-update-form");
  if (profileForm) {
    profileForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const saveBtn = document.getElementById("btn-save-profile");
      const nameInput = document.getElementById("prof-name");
      const fullName = nameInput ? nameInput.value.trim() : "";

      if (!fullName) {
        if (window.showToast) window.showToast("Please enter a valid name.", "error");
        else alert("Please enter a valid name.");
        return;
      }

      if (saveBtn) {
        saveBtn.disabled = true;
        saveBtn.textContent = "Saving...";
      }

      try {
        const response = await fetch("/api/auth/profile", {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ full_name: fullName }),
        });

        const data = await response.json();

        if (response.ok && data.success) {
          if (window.showToast) window.showToast("Profile updated successfully!", "success");
          else alert("Profile updated successfully!");

          // Update header / sidebar display
          document.querySelectorAll(".user-badge-name").forEach((el) => {
            el.textContent = fullName;
          });
          document.querySelectorAll(".user-avatar-circle").forEach((el) => {
            el.textContent = fullName.charAt(0).toUpperCase();
          });
        } else {
          if (window.showToast) window.showToast(data.error || "Update failed.", "error");
          else alert(data.error || "Update failed.");
        }
      } catch (err) {
        if (window.showToast) window.showToast("Network error. Please try again.", "error");
        else alert("Network error. Please try again.");
      } finally {
        if (saveBtn) {
          saveBtn.disabled = false;
          saveBtn.textContent = "Save Profile";
        }
      }
    });
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // SETTINGS THEME TOGGLE
  // ═══════════════════════════════════════════════════════════════════════════
  const settingsThemeBtn = document.getElementById("btn-theme-toggle-settings");
  if (settingsThemeBtn) {
    settingsThemeBtn.addEventListener("click", () => {
      const current = document.documentElement.getAttribute("data-theme") || "light";
      const target = current === "dark" ? "light" : "dark";
      document.documentElement.setAttribute("data-theme", target);
      localStorage.setItem("typesure_theme", target);

      // Also trigger any icon updates
      document.querySelectorAll(".theme-toggle, .btn-theme-toggle").forEach((btn) => {
        btn.innerHTML = target === "dark" ? "☀️" : "🌙";
      });
      if (window.showToast) {
        window.showToast(`Switched to ${target === "dark" ? "Dark" : "Light"} mode`, "info");
      }
    });
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // PERSONAL DICTIONARY MANAGEMENT
  // ═══════════════════════════════════════════════════════════════════════════
  let personalCurrentPage = 1;
  let personalSearchQuery = "";
  const personalPageLimit = 50;

  const personalLoading = document.getElementById("personal-loading");
  const personalTableWrap = document.getElementById("personal-words-table-wrap");
  const personalTbody = document.getElementById("personal-words-tbody");
  const personalEmpty = document.getElementById("personal-empty-state");
  const personalPagination = document.getElementById("personal-pagination");
  const personalPageInfo = document.getElementById("personal-page-info");
  const personalPrevBtn = document.getElementById("btn-personal-prev");
  const personalNextBtn = document.getElementById("btn-personal-next");
  const personalSearchInput = document.getElementById("personal-search-input");
  const personalClearSearchBtn = document.getElementById("btn-clear-personal-search");

  // Add Word Modal elements
  const addPersonalModal = document.getElementById("add-personal-modal");
  const openAddPersonalBtn = document.getElementById("btn-open-add-personal-modal");
  const closeAddPersonalBtn = document.getElementById("add-personal-close");
  const cancelAddPersonalBtn = document.getElementById("btn-add-personal-cancel");
  const addPersonalForm = document.getElementById("add-personal-form");
  const personalWordInput = document.getElementById("personal-word-input");
  const personalNotesInput = document.getElementById("personal-notes-input");

  // Export buttons
  const exportPersonalTxtBtn = document.getElementById("btn-export-personal-txt");
  const exportPersonalCsvBtn = document.getElementById("btn-export-personal-csv");

  async function loadPersonalWords(query = "", page = 1) {
    if (!personalTbody) return;
    if (personalLoading) personalLoading.classList.remove("hidden");
    if (personalTableWrap) personalTableWrap.classList.add("hidden");
    if (personalEmpty) personalEmpty.classList.add("hidden");
    if (personalPagination) personalPagination.classList.add("hidden");

    try {
      const url = `/api/personal-dictionary?q=${encodeURIComponent(query)}&page=${page}&limit=${personalPageLimit}`;
      const res = await fetch(url);
      const data = await res.json();

      if (personalLoading) personalLoading.classList.add("hidden");

      if (!res.ok || !data.success) {
        if (personalEmpty) {
          personalEmpty.classList.remove("hidden");
          const p = personalEmpty.querySelector(".empty-title");
          if (p) p.textContent = data.error || "Failed to load personal words.";
        }
        return;
      }

      const words = data.words || [];
      const total = data.total || 0;
      const totalPages = data.total_pages || 1;

      // Update overview badge if exists
      const dashPersonalVal = document.getElementById("dash-total-personal");
      if (dashPersonalVal && !query) {
        dashPersonalVal.textContent = total;
      }

      if (words.length === 0) {
        if (personalEmpty) personalEmpty.classList.remove("hidden");
        return;
      }

      personalTbody.innerHTML = "";
      words.forEach((item) => {
        const tr = document.createElement("tr");
        tr.style.borderBottom = "1px solid var(--color-border-light)";

        const tdWord = document.createElement("td");
        tdWord.style.padding = "10px 14px";
        tdWord.style.fontWeight = "600";
        tdWord.style.fontFamily = "'Noto Sans Tamil', sans-serif";
        tdWord.textContent = item.word;

        const tdNotes = document.createElement("td");
        tdNotes.style.padding = "10px 14px";
        tdNotes.style.fontSize = "0.85rem";
        tdNotes.style.color = "var(--color-text-secondary)";
        tdNotes.textContent = item.notes || "—";

        const tdDate = document.createElement("td");
        tdDate.style.padding = "10px 14px";
        tdDate.style.fontSize = "0.82rem";
        tdDate.style.color = "var(--color-text-muted)";
        tdDate.textContent = item.created_at ? item.created_at.split("T")[0] : "—";

        const tdAction = document.createElement("td");
        tdAction.style.padding = "10px 14px";
        tdAction.style.textAlign = "right";

        const delBtn = document.createElement("button");
        delBtn.className = "btn btn-ghost btn-sm";
        delBtn.style.color = "var(--color-danger)";
        delBtn.textContent = "Delete";
        delBtn.title = `Delete '${item.word}'`;
        delBtn.addEventListener("click", async () => {
          if (!confirm(`Remove '${item.word}' from your personal dictionary?`)) return;
          try {
            const delRes = await fetch(`/api/personal-dictionary/${item.id}`, { method: "DELETE" });
            const delData = await delRes.json();
            if (delRes.ok && delData.success) {
              if (window.showToast) window.showToast(`'${item.word}' removed.`, "info");
              loadPersonalWords(personalSearchQuery, personalCurrentPage);
            } else {
              alert(delData.error || "Could not delete word.");
            }
          } catch (e) {
            alert("Network error.");
          }
        });

        tdAction.appendChild(delBtn);
        tr.append(tdWord, tdNotes, tdDate, tdAction);
        personalTbody.appendChild(tr);
      });

      if (personalTableWrap) personalTableWrap.classList.remove("hidden");

      if (total > personalPageLimit) {
        if (personalPagination) personalPagination.classList.remove("hidden");
        if (personalPageInfo) personalPageInfo.textContent = `Page ${page} of ${totalPages} (${total} total)`;
        if (personalPrevBtn) personalPrevBtn.disabled = page <= 1;
        if (personalNextBtn) personalNextBtn.disabled = page >= totalPages;
      }
    } catch (err) {
      if (personalLoading) personalLoading.classList.add("hidden");
      if (personalEmpty) personalEmpty.classList.remove("hidden");
    }
  }

  // Load personal words when switching to personal tab
  sidebarLinks.forEach((link) => {
    if (link.getAttribute("data-tab") === "personal") {
      link.addEventListener("click", () => {
        loadPersonalWords(personalSearchQuery, personalCurrentPage);
      });
    }
  });

  if (window.location.hash === "#personal") {
    loadPersonalWords("", 1);
  }

  // Search input with debounce
  let searchTimeout = null;
  if (personalSearchInput) {
    personalSearchInput.addEventListener("input", (e) => {
      clearTimeout(searchTimeout);
      searchTimeout = setTimeout(() => {
        personalSearchQuery = e.target.value.trim();
        personalCurrentPage = 1;
        loadPersonalWords(personalSearchQuery, 1);
      }, 300);
    });
  }

  if (personalClearSearchBtn) {
    personalClearSearchBtn.addEventListener("click", () => {
      if (personalSearchInput) personalSearchInput.value = "";
      personalSearchQuery = "";
      personalCurrentPage = 1;
      loadPersonalWords("", 1);
    });
  }

  // Pagination navigation
  if (personalPrevBtn) {
    personalPrevBtn.addEventListener("click", () => {
      if (personalCurrentPage > 1) {
        personalCurrentPage--;
        loadPersonalWords(personalSearchQuery, personalCurrentPage);
      }
    });
  }
  if (personalNextBtn) {
    personalNextBtn.addEventListener("click", () => {
      personalCurrentPage++;
      loadPersonalWords(personalSearchQuery, personalCurrentPage);
    });
  }

  // Add word modal open / close
  if (openAddPersonalBtn && addPersonalModal) {
    openAddPersonalBtn.addEventListener("click", () => {
      addPersonalModal.classList.remove("hidden");
      if (personalWordInput) {
        personalWordInput.value = "";
        personalWordInput.focus();
      }
      if (personalNotesInput) personalNotesInput.value = "";
    });
  }

  function closeAddPersonalModal() {
    if (addPersonalModal) addPersonalModal.classList.add("hidden");
  }
  if (closeAddPersonalBtn) closeAddPersonalBtn.addEventListener("click", closeAddPersonalModal);
  if (cancelAddPersonalBtn) cancelAddPersonalBtn.addEventListener("click", closeAddPersonalModal);

  // Add word form submit
  if (addPersonalForm) {
    addPersonalForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const word = personalWordInput ? personalWordInput.value.trim() : "";
      const notes = personalNotesInput ? personalNotesInput.value.trim() : "";
      if (!word) return;

      const submitBtn = document.getElementById("btn-add-personal-submit");
      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.textContent = "Saving...";
      }

      try {
        const resp = await fetch("/api/personal-dictionary", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ word, notes }),
        });
        const result = await resp.json();

        if (resp.ok && result.success) {
          if (window.showToast) window.showToast(`'${word}' added to personal dictionary!`, "success");
          closeAddPersonalModal();
          loadPersonalWords(personalSearchQuery, 1);
        } else {
          alert(result.error || "Failed to add word.");
        }
      } catch (err) {
        alert("Network error.");
      } finally {
        if (submitBtn) {
          submitBtn.disabled = false;
          submitBtn.textContent = "Save Word";
        }
      }
    });
  }

  // Export buttons
  if (exportPersonalTxtBtn) {
    exportPersonalTxtBtn.addEventListener("click", () => {
      window.location.href = "/api/personal-dictionary/export?format=txt";
    });
  }
  if (exportPersonalCsvBtn) {
    exportPersonalCsvBtn.addEventListener("click", () => {
      window.location.href = "/api/personal-dictionary/export?format=csv";
    });
  }
});

