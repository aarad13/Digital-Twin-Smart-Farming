from pathlib import Path
from html.parser import HTMLParser

ROOT = Path(__file__).resolve().parents[1]


class AuthMarkup(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []
        self.role_buttons = []
        self.role_views = {}

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get("id"):
            self.ids.append(attrs["id"])
        if attrs.get("data-auth-role"):
            self.role_buttons.append(attrs["data-auth-role"])
        if attrs.get("data-app-view"):
            self.role_views[attrs["data-app-view"]] = attrs.get("data-roles", "")


def test_login_portal_supports_farmer_government_company_and_lab_roles():
    html = (ROOT / "app/templates/index.html").read_text(encoding="utf-8")
    parser = AuthMarkup()
    parser.feed(html)
    assert set(parser.role_buttons) == {"farmer", "government_officer", "company_officer", "lab_staff"}
    assert 'id="auth-login-form"' in html
    assert 'id="auth-register-form"' in html
    assert 'id="logout-button"' in html


def test_no_database_connected_badge_is_displayed_to_users():
    html = (ROOT / "app/templates/index.html").read_text(encoding="utf-8")
    dashboard = (ROOT / "app/static/js/dashboard.js").read_text(encoding="utf-8")
    assert "connection-label" not in html
    assert "MySQL connected" not in dashboard


def test_authentication_uses_password_hashes_and_server_side_role_checks():
    app = (ROOT / "app/app.py").read_text(encoding="utf-8")
    assert "generate_password_hash" in app
    assert "check_password_hash" in app
    assert "require_authenticated_api_and_role" in app
    assert '"service_save_sample_results": {"lab_staff", "admin"}' in app
    assert '"service_create_farmer": {"government_officer", "company_officer", "admin"}' in app


def test_organisation_accounts_are_not_publicly_self_assigned():
    html = (ROOT / "app/templates/index.html").read_text(encoding="utf-8")
    seed = (ROOT / "scripts/seed_demo_data.py").read_text(encoding="utf-8")
    assert "Organisation accounts are created only after your identity and organisation access are checked" in html
    assert "DEMO-ONLY SIGN-IN ACCOUNTS" in seed
    assert "existing password retained" in seed


def test_migration_and_account_provisioning_are_in_entrypoint():
    entrypoint = (ROOT / "scripts/docker_entrypoint.sh").read_text(encoding="utf-8")
    migration = (ROOT / "scripts/migrate_app_access.py").read_text(encoding="utf-8")
    provision = (ROOT / "scripts/create_user.py").read_text(encoding="utf-8")
    assert "migrate_app_access.py" in entrypoint
    assert "CREATE TABLE IF NOT EXISTS app_users" in migration
    assert "getpass" in provision


def test_farmer_dashboard_and_staff_views_are_role_aware():
    html = (ROOT / "app/templates/index.html").read_text(encoding="utf-8")
    assert 'data-roles="farmer"' in html
    assert 'data-roles="government_officer,company_officer,admin"' in html
    assert 'data-roles="lab_staff,admin"' in html
    auth_js = (ROOT / "app/static/js/auth-ui.js").read_text(encoding="utf-8")
    assert "applyRoleVisibility" in auth_js
    assert "window.appAuthReady" in auth_js


def test_field_team_can_issue_a_one_time_farmer_activation_code():
    app = (ROOT / "app/app.py").read_text(encoding="utf-8")
    html = (ROOT / "app/templates/index.html").read_text(encoding="utf-8")
    js = (ROOT / "app/static/js/auth-ui.js").read_text(encoding="utf-8")
    field_js = (ROOT / "app/static/js/service-desk.js").read_text(encoding="utf-8")
    assert '@app.post("/api/auth/activate-farmer")' in app
    assert '"auth_activate_farmer"' in app
    assert "activation_code_hash" in app and "must_change_password" in app
    assert 'id="auth-activate-form"' in html
    assert 'id="auth-show-activate"' in html
    assert '/api/auth/activate-farmer' in js
    assert "data.activation_code" in field_js


def test_soil_samples_are_routed_to_the_named_laboratory():
    sql = (ROOT / "sql/schema.sql").read_text(encoding="utf-8")
    migration = (ROOT / "scripts/migrate_app_access.py").read_text(encoding="utf-8")
    app = (ROOT / "app/app.py").read_text(encoding="utf-8")
    html = (ROOT / "app/templates/index.html").read_text(encoding="utf-8")
    assert "assigned_lab_organization VARCHAR(180) NULL" in sql
    assert '"assigned_lab_organization": "VARCHAR(180) NULL"' in migration
    assert 'conditions.append("s.assigned_lab_organization=%s")' in app
    assert 'sample_id=%s AND assigned_lab_organization=%s' in app
    assert 'id="ss-lab-destination"' in html


def test_migration_and_demo_scripts_add_project_root_before_importing_app():
    for relative in ("scripts/migrate_app_access.py", "scripts/seed_demo_data.py", "scripts/create_user.py"):
        source = (ROOT / relative).read_text(encoding="utf-8")
        assert "sys.path.insert(0, str(ROOT))" in source
        assert source.index("sys.path.insert(0, str(ROOT))") < source.index("from app")


def test_login_ui_offers_farmer_self_signup_and_field_team_activation():
    html = (ROOT / "app/templates/index.html").read_text(encoding="utf-8")
    js = (ROOT / "app/static/js/auth-ui.js").read_text(encoding="utf-8")
    assert 'id="auth-register-form"' in html
    assert 'id="auth-activate-form"' in html
    assert 'id="auth-show-activate"' in html
    assert 'function showActivationMode()' in js
    assert 'window.location.reload()' in js


def test_field_officers_reuse_existing_farmer_login_instead_of_creating_duplicate_profiles():
    app = (ROOT / "app/app.py").read_text(encoding="utf-8")
    assert "SELECT user_id, role, farmer_id FROM app_users WHERE username=%s LIMIT 1 FOR UPDATE" in app
    assert "existing farmer login is not linked to a farmer record" in app
    assert "This farmer is already registered under another organisation" in app
    assert "account_exists = True" in app


def test_sensitive_workflows_are_restricted_to_relevant_roles():
    app = (ROOT / "app/app.py").read_text(encoding="utf-8")
    assert '"virtual_farm_create": {"farmer", "government_officer", "company_officer", "admin"}' in app
    assert '"virtual_farm_add_plot": {"farmer", "government_officer", "company_officer", "admin"}' in app
    assert '"upload_soil_report": {"farmer", "government_officer", "company_officer", "admin"}' in app
    assert '"update_farm_settings": {"government_officer", "company_officer", "admin"}' in app
