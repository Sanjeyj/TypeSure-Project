/**
 * TypeSure — Authentication Client Scripts
 * auth.js (Login, Registration, Password Recovery, Strength Checker, Theme Toggle)
 */

"use strict";

document.addEventListener("DOMContentLoaded", () => {
  // Update copyright year
  const copyYear = document.getElementById("copy-year");
  if (copyYear) copyYear.textContent = new Date().getFullYear();

  // ═══════════════════════════════════════════════════════════════════════════
  // THEME SWITCHER
  // ═══════════════════════════════════════════════════════════════════════════
  const initAuthTheme = () => {
    const storedTheme = localStorage.getItem("typesure_theme") || "light";
    document.documentElement.setAttribute("data-theme", storedTheme);

    const updateAuthThemeIcon = (theme) => {
      const icon = document.getElementById("theme-icon");
      if (icon) icon.textContent = theme === "dark" ? "☀️" : "🌙";
    };

    updateAuthThemeIcon(storedTheme);

    const themeToggleBtn = document.getElementById("theme-toggle");
    if (themeToggleBtn) {
      themeToggleBtn.addEventListener("click", () => {
        const current = document.documentElement.getAttribute("data-theme") || "light";
        const next = current === "dark" ? "light" : "dark";
        document.documentElement.setAttribute("data-theme", next);
        localStorage.setItem("typesure_theme", next);
        updateAuthThemeIcon(next);
      });
    }
  };

  initAuthTheme();

  // ═══════════════════════════════════════════════════════════════════════════
  // PASSWORD VISIBILITY TOGGLERS
  // ═══════════════════════════════════════════════════════════════════════════
  const setupToggle = (btnId, inputId) => {
    const btn = document.getElementById(btnId);
    const input = document.getElementById(inputId);
    if (!btn || !input) return;

    btn.addEventListener("click", () => {
      if (input.type === "password") {
        input.type = "text";
        btn.textContent = "Hide";
        btn.setAttribute("aria-label", "Hide password");
      } else {
        input.type = "password";
        btn.textContent = "Show";
        btn.setAttribute("aria-label", "Show password");
      }
    });
  };

  setupToggle("toggle-password", "login-password");
  setupToggle("toggle-reg-password", "reg-password");

  // ═══════════════════════════════════════════════════════════════════════════
  // LOGIN FORM
  // ═══════════════════════════════════════════════════════════════════════════
  const loginForm = document.getElementById("login-form");
  if (loginForm) {
    const emailInput = document.getElementById("login-email");
    const passwordInput = document.getElementById("login-password");
    const rememberInput = document.getElementById("login-remember");
    const submitBtn = document.getElementById("btn-login-submit");
    const errorAlert = document.getElementById("login-error-alert");
    const errorMsg = document.getElementById("login-error-msg");

    const showError = (message) => {
      if (errorMsg) errorMsg.textContent = message;
      if (errorAlert) errorAlert.classList.remove("hidden");
    };

    const hideError = () => {
      if (errorAlert) errorAlert.classList.add("hidden");
    };

    loginForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      hideError();

      const email = emailInput ? emailInput.value.trim() : "";
      const password = passwordInput ? passwordInput.value : "";
      const remember = rememberInput ? rememberInput.checked : false;

      if (!email || !password) {
        showError("Please enter both email and password.");
        return;
      }

      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.textContent = "Signing In...";
      }

      try {
        const response = await fetch("/api/auth/login", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            email,
            password,
            remember_me: remember,
          }),
        });

        const data = await response.json();

        if (response.ok && data.success) {
          const params = new URLSearchParams(window.location.search);
          const nextUrl = params.get("next") || "/dashboard";
          window.location.href = nextUrl;
        } else {
          showError(data.error || "Invalid email or password.");
          if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.textContent = "Sign In";
          }
        }
      } catch (err) {
        showError("Network connection error. Please try again.");
        if (submitBtn) {
          submitBtn.disabled = false;
          submitBtn.textContent = "Sign In";
        }
      }
    });
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // REGISTRATION FORM
  // ═══════════════════════════════════════════════════════════════════════════
  const registerForm = document.getElementById("register-form");
  if (registerForm) {
    const nameInput = document.getElementById("reg-name");
    const emailInput = document.getElementById("reg-email");
    const passwordInput = document.getElementById("reg-password");
    const confirmInput = document.getElementById("reg-confirm-password");
    const confirmFeedback = document.getElementById("confirm-feedback");
    const termsInput = document.getElementById("reg-terms");
    const submitBtn = document.getElementById("btn-register-submit");
    const errorAlert = document.getElementById("register-error-alert");
    const errorMsg = document.getElementById("register-error-msg");

    const str1 = document.getElementById("str-1");
    const str2 = document.getElementById("str-2");
    const str3 = document.getElementById("str-3");
    const str4 = document.getElementById("str-4");
    const strengthText = document.getElementById("strength-text");

    const showError = (message) => {
      if (errorMsg) errorMsg.textContent = message;
      if (errorAlert) errorAlert.classList.remove("hidden");
    };

    const hideError = () => {
      if (errorAlert) errorAlert.classList.add("hidden");
    };

    // Evaluate password strength
    const evaluatePassword = (pw) => {
      let score = 0;
      if (pw.length >= 8) score++;
      if (/[a-z]/.test(pw) && /[A-Z]/.test(pw)) score++;
      if (/[0-9]/.test(pw)) score++;
      if (/[^a-zA-Z0-9]/.test(pw) || pw.length >= 12) score++;
      return score;
    };

    const updateStrengthDisplay = (pw) => {
      if (!str1) return;
      const score = pw ? evaluatePassword(pw) : 0;
      const segments = [str1, str2, str3, str4];

      segments.forEach((seg, idx) => {
        seg.className = "strength-segment";
        if (idx < score) {
          if (score === 1) seg.classList.add("weak");
          else if (score === 2) seg.classList.add("medium");
          else if (score >= 3) seg.classList.add("strong");
        }
      });

      if (strengthText) {
        if (!pw) strengthText.textContent = "Password strength: none";
        else if (score === 1) strengthText.textContent = "Password strength: Weak";
        else if (score === 2) strengthText.textContent = "Password strength: Moderate";
        else if (score === 3) strengthText.textContent = "Password strength: Good";
        else strengthText.textContent = "Password strength: Strong";
      }
    };

    if (passwordInput) {
      passwordInput.addEventListener("input", () => {
        updateStrengthDisplay(passwordInput.value);
        checkPasswordMatch();
      });
    }

    const checkPasswordMatch = () => {
      if (!confirmInput || !confirmFeedback) return;
      if (confirmInput.value && passwordInput && passwordInput.value !== confirmInput.value) {
        confirmFeedback.classList.remove("hidden");
      } else {
        confirmFeedback.classList.add("hidden");
      }
    };

    if (confirmInput) {
      confirmInput.addEventListener("input", checkPasswordMatch);
    }

    registerForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      hideError();

      const fullName = nameInput ? nameInput.value.trim() : "";
      const email = emailInput ? emailInput.value.trim() : "";
      const password = passwordInput ? passwordInput.value : "";
      const confirmPassword = confirmInput ? confirmInput.value : "";
      const agree = termsInput ? termsInput.checked : true;

      if (!fullName) {
        showError("Please enter your full name.");
        return;
      }
      if (!email || !email.includes("@")) {
        showError("Please enter a valid email address.");
        return;
      }
      if (password.length < 8) {
        showError("Password must be at least 8 characters long.");
        return;
      }
      if (password !== confirmPassword) {
        showError("Passwords do not match. Please verify.");
        return;
      }
      if (!agree) {
        showError("You must agree to the terms to proceed.");
        return;
      }

      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.textContent = "Creating Account...";
      }

      try {
        const response = await fetch("/api/auth/register", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            full_name: fullName,
            email,
            password,
            confirm_password: confirmPassword,
            agree_terms: agree,
          }),
        });

        const data = await response.json();

        if (response.ok && data.success) {
          window.location.href = "/dashboard";
        } else {
          showError(data.error || "Registration failed. Please try again.");
          if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.textContent = "Create Account";
          }
        }
      } catch (err) {
        showError("Network connection error. Please try again.");
        if (submitBtn) {
          submitBtn.disabled = false;
          submitBtn.textContent = "Create Account";
        }
      }
    });
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // FORGOT PASSWORD FORM
  // ═══════════════════════════════════════════════════════════════════════════
  const forgotForm = document.getElementById("forgot-form");
  if (forgotForm) {
    const emailInput = document.getElementById("reset-email");
    const submitBtn = document.getElementById("btn-reset-submit");
    const successAlert = document.getElementById("reset-success-alert");
    const successMsg = document.getElementById("reset-success-msg");
    const errorAlert = document.getElementById("reset-error-alert");
    const errorMsg = document.getElementById("reset-error-msg");

    forgotForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      if (successAlert) successAlert.classList.add("hidden");
      if (errorAlert) errorAlert.classList.add("hidden");

      const email = emailInput ? emailInput.value.trim() : "";
      if (!email) {
        if (errorMsg) errorMsg.textContent = "Please enter your email address.";
        if (errorAlert) errorAlert.classList.remove("hidden");
        return;
      }

      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.textContent = "Sending Instructions...";
      }

      try {
        const response = await fetch("/api/auth/forgot-password", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ email }),
        });

        const data = await response.json();

        if (successMsg) {
          successMsg.textContent = data.message || "Reset instructions sent if email exists.";
        }
        if (successAlert) successAlert.classList.remove("hidden");
        if (emailInput) emailInput.value = "";
      } catch (err) {
        if (errorMsg) errorMsg.textContent = "Network error. Please try again.";
        if (errorAlert) errorAlert.classList.remove("hidden");
      } finally {
        if (submitBtn) {
          submitBtn.disabled = false;
          submitBtn.textContent = "Send Reset Instructions";
        }
      }
    });
  }
});
