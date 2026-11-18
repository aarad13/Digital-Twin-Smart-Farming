# Accounts, roles and assisted service workflow

## Who can sign in

The sign-in page offers four user-facing access types:

- **Farmer:** self-registers with a mobile number and password, or activates an account created by a field worker. A farmer sees their own farm, sample status and farmer card.
- **Government agriculture / extension officer:** uses an administrator-provisioned account to register farmers, plan visits, map farms and create sample records.
- **Agriculture company / FPO field team:** uses an administrator-provisioned account. Company records are filtered to the exact organisation name stored on the account.
- **Soil laboratory staff:** uses an administrator-provisioned account. The laboratory queue is filtered to samples assigned to the exact lab organisation name on the account.

A **platform administrator** account can be used through the presentation demo account list. Real staff accounts are created only after the responsible administrator checks the user's identity and organisation access. Users cannot choose a government, company or lab role by registering as a farmer.

## Farmer account created during a village visit

1. A government/company field officer records the farmer's consent and details.
2. The farmer may provide a 10-digit Indian mobile number. Phone contact is optional; without it, an online farmer login is not created.
3. If no account already exists for the mobile number, the app creates a pending farmer login and displays an eight-digit one-time activation code on a slip.
4. The officer hands the farmer code and activation code directly to the farmer. The code expires after seven days and is stored as a password hash in the database.
5. The farmer selects **I have a field-team code**, enters their mobile, farmer code and activation code, and chooses their own password.
6. On later visits, the farmer signs in with their mobile number and password.

The activation code is displayed once to the field officer. Do not put it in a public group or leave it on a shared device. SMS/OTP delivery and verified mobile ownership are not yet integrated; the handover is a local pilot process.

Farmers may also create their own accounts from the **New farmer? Create account** form. This currently records a consent checkbox; formal consent wording, withdrawal and retention policy must be approved before a real deployment.

## Field-to-lab workflow

1. Field staff create a farmer and visit record.
2. Field staff create a sample ID/QR and enter the **exact destination laboratory organisation name**.
3. A laboratory login whose `organization_name` matches that destination sees the sample in its queue.
4. The lab records only measured values, attaches the report and marks verification after its internal sign-off.
5. The Farmer Card shows soil values as verified only when `lab_verified=1`.

Use exactly the same lab name when creating the lab account and routing samples. A lab user cannot access or update another lab's assigned samples through the service workflow. Company users are similarly restricted by their provisioned organisation name. Government and platform administrator workspaces are broad pilot roles and should be restricted to an approved district/state jurisdiction model before multi-district deployment.

## Create real organisation accounts

Run inside the web container as an administrator after the organisation and staff member have been checked:

```bash
docker compose exec web python scripts/create_user.py \
  --username officer01 \
  --role government_officer \
  --display-name "A. Sharma" \
  --organization "District Agriculture Office, Sehore"
```

Allowed roles: `government_officer`, `company_officer`, `lab_staff`, `admin`. The script prompts twice for a temporary password of at least 12 characters and stores a one-way password hash. It does not send invitation email/SMS. Deliver credentials through an approved private process and require the user to change them through the organisation's password process; a self-service password reset is not yet implemented.

For a lab account, the `--organization` value must match the exact lab destination text field officers enter on sample creation, for example `District Soil Testing Laboratory, Sehore`.

## Presentation demo accounts

Run:

```bash
docker compose exec web python scripts/seed_demo_data.py
```

The script is idempotent. Demo logins:

| Role | Username | Password |
|---|---|---|
| Farmer | `farmer.demo` | `Farmer@123` |
| Government | `govt.demo` | `Govt@123` |
| Company/FPO | `company.demo` | `Company@123` |
| Soil lab | `lab.demo` | `Lab@123` |
| Platform admin | `admin.demo` | `Admin@123` |

The company demo organisation is `Demo Fertiliser Field Partner`. The lab demo organisation is `Demo Soil Testing Laboratory`; the synthetic soil samples are routed to that exact lab name. Existing demo passwords are not overwritten when the seed script runs again. These credentials are strictly for local demonstration and must be deleted or changed before any shared deployment.

## Existing features retained

The role/login release retains regional location intelligence and weather context, Indian agriculture context, virtual farm boundaries/plots/assets, soil-report upload, historical district crop-statistics import, Plotly charts, model forecasts, model comparisons, forecast/advisory history, and research documentation. The original EcoIrrigate prediction models remain specific to the two experimental Kolkata farm series; they are not treated as general Indian farm sensor data.

The old header-level “MySQL connected” badge has been removed. Database liveness remains available privately to Docker at `/health` for container health checks; it is not displayed as a farmer-facing connection pop-up.

## What this is not yet

This release adds local application accounts and role-aware workflows. It does **not** provide a live connection to the Soil Health Card portal, ICAR/KVK systems, government department identity systems, fertiliser-company CRM systems, or external laboratory information systems. Partner API access requires formal approval, credentials, agreements and testing.

Before production use, add HTTPS and a strong random Flask secret, CSRF protection, login rate limiting/lockout, SMS/OTP verification, password reset and mandatory staff password rotation, an audit trail for edits/verification, file malware scanning, encrypted backups, retention/deletion processes, district/state jurisdiction permissions for government officers, and an offline-first field capture/synchronisation process. The current organisation matching is by exact organisation-name text for a local pilot, not a substitute for a validated organisation directory or production multi-tenant security review.
