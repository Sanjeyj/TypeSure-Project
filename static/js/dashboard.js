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
    dictionary: "Dictionary & Vocabulary Manager",
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
});

