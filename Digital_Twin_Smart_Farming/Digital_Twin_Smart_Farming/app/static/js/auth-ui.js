(() => {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const roleLabels = {
    farmer: "Farmer",
    government_officer: "Government agriculture / extension officer",
    company_officer: "Agriculture company / FPO field team",
    lab_staff: "Soil laboratory staff",
    admin: "Platform administrator"
  };
  let selectedRole = "farmer";

  function setStatus(id, message, error = false) {
    const node = $(id);
    if (!node) return;
    node.textContent = message;
    node.classList.toggle("is-error", !!error);
    node.classList.toggle("is-success", !!message && !error);
  }

  function chooseRole(role) {
    if (!roleLabels[role]) return;
    selectedRole = role;
    document.querySelectorAll("[data-auth-role]").forEach((button) => {
      const active = button.dataset.authRole === role;
      button.classList.toggle("is-selected", active);
      button.setAttribute("aria-pressed", String(active));
    });
    const farmer = role === "farmer";
    const registerButton = $("auth-show-register");
    const activateButton = $("auth-show-activate");
    registerButton.disabled = !farmer;
    activateButton.disabled = !farmer;
    registerButton.title = farmer ? "Create a farmer account" : "Only farmers can self-register";
    activateButton.title = farmer ? "Activate an account created by a field worker" : "Only farmer accounts use activation codes";
    if (!farmer && ((!$("auth-register-form").hidden) || (!$("auth-activate-form").hidden))) showLoginMode();
    $("auth-form-title").textContent = farmer ? "Sign in to your farm service" : `Sign in · ${roleLabels[role]}`;
    $("auth-form-subtitle").textContent = farmer
      ? "Use your registered mobile number and password. You can also create a farmer account."
      : "Use the account issued by your organisation or platform administrator.";
    $("auth-login-help").textContent = farmer
      ? "Your mobile number is your sign-in ID. You can ask a family member or field worker to help you."
      : "Government, company and laboratory accounts are activated only after organisation access is checked.";
  }

  function showLoginMode() {
    $("auth-login-form").hidden = false;
    $("auth-register-form").hidden = true;
    $("auth-activate-form").hidden = true;
    $("auth-show-login").classList.add("is-active");
    $("auth-show-register").classList.remove("is-active");
    $("auth-show-activate").classList.remove("is-active");
  }

  function showRegisterMode() {
    if (selectedRole !== "farmer") return;
    $("auth-login-form").hidden = true;
    $("auth-register-form").hidden = false;
    $("auth-activate-form").hidden = true;
    $("auth-show-login").classList.remove("is-active");
    $("auth-show-register").classList.add("is-active");
    $("auth-show-activate").classList.remove("is-active");
  }

  function showActivationMode() {
    if (selectedRole !== "farmer") return;
    $("auth-login-form").hidden = true;
    $("auth-register-form").hidden = true;
    $("auth-activate-form").hidden = false;
    $("auth-show-login").classList.remove("is-active");
    $("auth-show-register").classList.remove("is-active");
    $("auth-show-activate").classList.add("is-active");
  }

  function applyRoleVisibility(user) {
    const role = user.role;
    document.querySelectorAll("[data-roles]").forEach((element) => {
      const allowed = element.dataset.roles.split(",").map((value) => value.trim());
      element.hidden = !allowed.includes(role);
    });
    const staffCard = document.querySelector(".service-role-card.role-field");
    const labCard = document.querySelector(".service-role-card.role-lab");
    if (staffCard) staffCard.hidden = !["government_officer", "company_officer", "admin"].includes(role);
    if (labCard) labCard.hidden = !["lab_staff", "admin"].includes(role);
    if (role === "farmer") {
      const picker = document.querySelector(".farmer-card-select");
      const refresh = $("farmer-card-refresh");
      if (picker) picker.hidden = true;
      if (refresh) refresh.hidden = true;
      if ($("farmer-home-name")) $("farmer-home-name").textContent = user.display_name || "Farmer";
    }
    if (role === "lab_staff") {
      const fieldSection = $("field-team-view");
      if (fieldSection) fieldSection.hidden = true;
    }
  }

  function showApplication(user) {
    window.APP_CURRENT_USER = user;
    $("auth-screen").hidden = true;
    $("app-shell").hidden = false;
    $("main-navigation").hidden = false;
    $("account-tools").hidden = false;
    $("account-display-name").textContent = user.display_name || user.username;
    $("account-role-pill").textContent = roleLabels[user.role] || "Account";
    applyRoleVisibility(user);
    const officer = $("sf-officer");
    const collector = $("ss-collector");
    const technician = $("sl-technician");
    const labName = $("sl-lab");
    [officer, collector, technician].forEach((field) => {
      if (field && !field.value) field.value = user.display_name || "";
    });
    if (labName && user.role === "lab_staff" && !labName.value) labName.value = user.organization_name || "";
    const organisation = user.organization_name ? ` · ${user.organization_name}` : "";
    document.title = `Smart Farming · ${roleLabels[user.role] || "Farm service"}`;
    const home = document.querySelector('.app-view[data-app-view="home"]');
    if (home) home.dataset.activeRole = user.role;
    if (user.role === "farmer" && window.setFarmerView) window.setFarmerView("home", { keepScroll: true });
    // Organisation name is available on the account chip title, not as a claim of official integration.
    $("account-role-pill").title = `${roleLabels[user.role] || "Account"}${organisation}`;
  }

  async function postJSON(url, payload) {
    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "same-origin",
      body: JSON.stringify(payload)
    });
    const data = await response.json();
    if (!response.ok || data.ok === false) throw new Error(data.error || `Request failed (${response.status})`);
    return data;
  }

  document.querySelectorAll("[data-auth-role]").forEach((button) => {
    button.addEventListener("click", () => chooseRole(button.dataset.authRole));
  });
  $("auth-show-login").addEventListener("click", showLoginMode);
  $("auth-show-register").addEventListener("click", showRegisterMode);
  $("auth-show-activate").addEventListener("click", showActivationMode);

  document.querySelectorAll("[data-demo-user]").forEach((button) => {
    button.addEventListener("click", () => {
      chooseRole(button.dataset.demoRole);
      showLoginMode();
      $("auth-username").value = button.dataset.demoUser;
      $("auth-password").value = button.dataset.demoPassword;
      setStatus("auth-login-status", "Demo credentials filled. Select Sign in to continue.");
      $("auth-password").focus();
    });
  });

  $("auth-login-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = event.submitter;
    button.disabled = true;
    setStatus("auth-login-status", "Checking your account…");
    try {
      await postJSON("/api/auth/login", {
        username: $("auth-username").value.trim(),
        password: $("auth-password").value,
        role: selectedRole
      });
      window.location.reload();
    } catch (error) {
      setStatus("auth-login-status", error.message, true);
    } finally {
      button.disabled = false;
    }
  });

  $("auth-register-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = event.submitter;
    button.disabled = true;
    setStatus("auth-register-status", "Creating your farmer account…");
    try {
      await postJSON("/api/auth/register-farmer", {
        farmer_name: $("auth-register-name").value.trim(),
        mobile: $("auth-register-mobile").value.trim(),
        preferred_language: $("auth-register-language").value,
        state: $("auth-register-state").value.trim(),
        district: $("auth-register-district").value.trim(),
        village: $("auth-register-village").value.trim(),
        password: $("auth-register-password").value,
        consent_recorded: $("auth-register-consent").checked
      });
      window.location.reload();
    } catch (error) {
      setStatus("auth-register-status", error.message, true);
    } finally {
      button.disabled = false;
    }
  });


  $("auth-activate-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = event.submitter;
    button.disabled = true;
    setStatus("auth-activate-status", "Activating your farmer account…");
    try {
      await postJSON("/api/auth/activate-farmer", {
        mobile: $("auth-activate-mobile").value.trim(),
        farmer_code: $("auth-activate-farmer-code").value.trim(),
        activation_code: $("auth-activate-code").value.trim(),
        password: $("auth-activate-password").value
      });
      window.location.reload();
    } catch (error) {
      setStatus("auth-activate-status", error.message, true);
    } finally {
      button.disabled = false;
    }
  });

  $("logout-button").addEventListener("click", async () => {
    try { await postJSON("/api/auth/logout", {}); } catch (_) { /* clear the browser view regardless */ }
    window.location.reload();
  });

  window.appAuthReady = (async () => {
    try {
      const response = await fetch("/api/auth/me", { credentials: "same-origin" });
      const data = await response.json();
      if (!response.ok || data.ok === false) throw new Error(data.error || "Could not check sign-in status.");
      if (!data.authenticated || !data.user) {
        $("auth-screen").hidden = false;
        $("app-shell").hidden = true;
        $("main-navigation").hidden = true;
        $("account-tools").hidden = true;
        return null;
      }
      showApplication(data.user);
      return data.user;
    } catch (error) {
      $("auth-screen").hidden = false;
      $("app-shell").hidden = true;
      $("main-navigation").hidden = true;
      $("account-tools").hidden = true;
      setStatus("auth-login-status", `${error.message} Please check the connection and try again.`, true);
      return null;
    }
  })();

  chooseRole("farmer");
})();
