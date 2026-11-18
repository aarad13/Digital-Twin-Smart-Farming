# Assisted Village Service Workflow

## Product direction

The farmer is the primary beneficiary, not necessarily the person operating the technology. Farmers can self-register and view a simplified farmer card, but they can also receive the service without owning a smartphone: authorised government extension staff, company/FPO field staff or trained facilitators record farm details during a village visit. Soil laboratories enter test results against traceable sample IDs.

## Login types and access

- **Farmer:** mobile/password sign-in, self-registration, or account activation from a one-time code handed over by a field worker. Farmer record APIs are scoped to the linked farmer ID.
- **Government agriculture / extension officer:** administrator-provisioned account for village registration, field visits, farm mapping and sample creation. Government users have broad pilot visibility in this build; district/state-level scope must be added before multi-jurisdiction deployment.
- **Agriculture company / FPO field officer:** provisioned account. Farmer/farm/sample views are filtered to the exact `organization_name` on that account.
- **Soil laboratory staff:** provisioned account. The lab queue, report retrieval and result submission are restricted to samples whose `assigned_lab_organization` matches the lab account's exact organisation name.
- **Platform administrator:** provisioned account with broad maintenance/demo access.

Passwords are stored as Werkzeug password hashes. The browser session is a signed Flask session with HTTP-only and SameSite=Lax cookie settings. API endpoints require an authenticated account except the sign-in, farmer registration/activation, sign-out and Docker health endpoints. Frontend role visibility is backed by server-side checks.

## Farmer account issued during a field visit

When a field officer registers a farmer and supplies a valid 10-digit Indian mobile number, the service creates a pending farmer login if no account exists for that mobile. The response shows the farmer code and an eight-digit one-time activation code. The code hash is stored in MySQL and expires after seven days. The officer should hand the activation slip directly to the farmer. The farmer selects **I have a field-team code**, enters the mobile number, farmer code and activation code, and chooses their own password.

If no mobile number is supplied, the farm-service record is still created but no online farmer login can be issued by this workflow. A farmer may alternatively self-register. SMS/OTP delivery, SIM ownership verification and password reset are not yet implemented. The one-time code is for a local pilot handover only; do not share it in public groups or on shared devices.

## Field-to-lab workflow

1. Field staff explain the service and record consent before storing farmer/contact/farm data.
2. The officer records the visit and farm location if the farmer agrees. A GPS point is not a cadastral boundary.
3. The officer creates a QR/sample code, records the sample collection information and enters the exact destination laboratory name.
4. A lab account must be provisioned with the same exact organisation name. Its users see samples routed to that lab, not other labs' samples.
5. Lab staff enter measured pH, EC, organic carbon and N/P/K values, attach a report and mark the result verified only after the lab's checking/sign-off.
6. The Farmer Card presents values as verified only when `lab_verified=1`. Missing values stay blank; no nutrient prescription is generated from a missing value.

For example, the demonstration field team routes samples to `Demo Soil Testing Laboratory`; the `lab.demo` account uses that exact organisation name. Real lab accounts and route names must match exactly.

## Create an institutional account

An administrator must first check the staff identity and organisation. Then run inside the container:

```bash
docker compose exec web python scripts/create_user.py \
  --username officer01 \
  --role government_officer \
  --display-name "A. Sharma" \
  --organization "District Agriculture Office, Sehore"
```

Allowed roles are `government_officer`, `company_officer`, `lab_staff`, and `admin`. The script prompts for a password twice and requires at least 12 characters. The account is local to this application's database; the script does not verify a government/company employee identity or send an invitation. For a lab account, choose an organisation name that field staff will enter exactly as the sample destination.

## Presentation demo accounts

Run this after starting the app:

```bash
docker compose exec web python scripts/seed_demo_data.py
```

| Role | Username | Password |
|---|---|---|
| Farmer | `farmer.demo` | `Farmer@123` |
| Government | `govt.demo` | `Govt@123` |
| Company/FPO | `company.demo` | `Company@123` |
| Soil laboratory | `lab.demo` | `Lab@123` |
| Platform administrator | `admin.demo` | `Admin@123` |

The demo company is `Demo Fertiliser Field Partner`; the demo lab is `Demo Soil Testing Laboratory`. Demo samples are routed to that lab. The seeder is idempotent and preserves existing passwords. All demo people, fields, coordinates, test measurements and lab reports are synthetic and must never be used for real agricultural decisions. Change/remove these credentials before any shared deployment.

## Retained Digital Twin features

This release retains the prior Indian regional intelligence and search, weather context, Indian agriculture/crop-season knowledge, virtual farm geometry and plots/assets, soil-report file upload, district crop-statistics CSV import, predictive models, historical experimental data, charts, model comparisons, forecast/advisory history and research documentation. The farmer-facing top bar no longer shows a persistent database connection message. Docker retains `/health` for its internal service-health test.

## Institutional integration boundary

The application does not yet connect to live Soil Health Card APIs, KVK/ICAR systems, government department identity systems, fertiliser-company CRM systems or third-party laboratory information systems. These require formal partner approval, API documentation, credentials, data-sharing agreements, privacy review and end-to-end testing. The local account roles support a pilot workflow; they do not prove partnership or official authorisation.

## Production hardening required

Before real multi-organisation deployment, add HTTPS and a strong random secret key, CSRF protection, login throttling/lockout, verified mobile OTP, password reset and staff account lifecycle, a full audit log for edits and lab verification, district/state jurisdiction controls for government officers, a validated organisation directory (not free-text matching), antivirus/content validation for uploaded files, encrypted backups, retention/deletion process, offline-first field capture and conflict-safe synchronisation. Local language content and voice output need review with target farmers. Do not expose this prototype publicly or enter unnecessary personal identifiers (including Aadhaar) until those safeguards and partner permissions are in place.


### Existing farmer account
If the farmer already has a self-registered account for the same mobile number, the field officer reuses the linked farmer profile and records the visit against it instead of creating a duplicate login. Company officers cannot silently attach a farmer already registered by a different company.
