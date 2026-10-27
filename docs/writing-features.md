# Writing features

The shared step vocabulary and the checklist for a new feature file.

## Step patterns (essentials)

- Public (CSV-driven): `the channel is the primary channel`, `the response count should be at
  least the CSV product count`, `the CSV attributes should be non-empty`.
- ContentDB: `I GET the ContentDB published endpoint "{path}"` (+ `with channel` / `with routes`).
- ContentDB admin v1 (JWT, `/api-admin/` prefix — not the v2 `/api/` shape):
  `I GET/DELETE the ContentDB admin endpoint "{path}" [without auth]`.
- Admin v2 (JWT): `Given I am authenticated as an admin/regular user`;
  `When I GET/POST/PATCH/DELETE the v2 admin endpoint "{path}" [with body|with params|without auth]`.
- Assertions: `the response field "{field}" should equal/be true/be null/be a dict…`,
  `the results should contain an item with "{key}" equal to "{value}"`,
  `I save the response field "{field}" as "{alias}"`.
- Mail sandbox (`features/steps/mail.py`): `the sandbox mailbox is empty` (purges), `the sandbox mailbox
  contains {n} messages`, `I inject the fixture mail "{name}" into INBOX [replying to "{saved.alias}"]`,
  `I send the fixture mail "{name}" over SMTP to the sandbox`, `the last sandbox message has header "{h}"
  equal to "{v}"` (resolves `{saved.alias}`), `the last sandbox message subject starts with "{prefix}"`,
  `the value "{value}" is saved as "{alias}"`. Fixture mails use a `{message_id}` placeholder (single braces)
  in `In-Reply-To`/`References`/`Original-Message-ID`; `duplicate.eml` shares `Message-ID` with `reply_plain.eml`.
- Access (`features/steps/access_steps.py`, shared with the security matrix): `I am authenticated as the
  {viewer|editor|manager} staff user`, `the gate refuses with issue "{ACCESS_DENIED|STAFF_ONLY|UNMAPPED_ROUTE}"`,
  `the refusal names "{text}"`, `the response is not a gate refusal`, `the permission "{area}" should be
  "{level}"|absent` (on `access/me/`), audit lookups after `I save the newest audit entry id as "{alias}"`,
  `an application "{alias}" for this run` + `a token "{alias}" of application … with scope "{scope}" [pinned to the
  first|second seed channel]`, `I submit a contact form with the token "{alias}" on the first|second seed channel`.
  Raw token values stay in `context.raw_tokens` — never printed, never in `context.saved` or an assertion message.
  `the admin sends {METHOD} to "{path}" when the scenario ends` registers a cleanup that runs even when the
  scenario fails (resolved at the end; an alias never saved means nothing to clean).
- Access security (`@access-security`, same file): `the caller is {anonymous|customer|bad-bearer|token-only|norole|
  viewer|editor|manager|accessadmin|admin}` (a requests session with exactly those headers; token-only = fresh
  publishable + secret tokens, no JWT), `the caller has a Django admin session as {who}`, `the caller presents the
  {-|checkout fixture|contact-forms fixture|<scope>} key`, `the caller sends {METHOD} to "{path}"` (POST = `{}`;
  `with JSON <cell>` / `with body` docstring; `{days_ahead:N}` → an ISO instant), `the answer is {status} with
  "{gate issue|-|n/a|login redirect}"` (`-` = no gate issue, `n/a` = HEAD). Token abuse: `the tokens "a, b" are sent in
  "{header}" with {METHOD} to "{path}"` → `every answer is the same {status}`, `no answer carries a token secret`.
  Tokens of these steps live in the shared, never-deactivated application `bdd-access-security` (revoked per
  scenario, 30-day expiry); a `raw` in any answer moves to `context.raw_tokens` and its token is revoked at the end.
  Audit: `the audit log counts {n} "gate.bypass" after "{mark}" for {METHOD} "{route}" [with status {s}]`.
  A generated staff `password` in an answer is kept aside like a `raw` (`I save the answered password as "{alias}"`);
  `a generated password is saved as "{alias}"`, `the caller signs in as "{username}" through customer tokens with the
  password "{alias}"` (the CMS login, primary channel), `no staff account has the {username|email} "{value}"`,
  `the answer field "{dotted.path}" is {json}`, `the answer names the field "{field}"`. Pinned erase: `the channel is
  the {first|second} seed channel`, `the caller presents the token "{alias}" in "{header}"`, `the customer account of
  user "{alias}" belongs to the {position} seed channel` (Django admin form — the signup is not available on zeno).
  Legacy keys are chosen by channel: `… legacy "{scope}" token pinned to the {first|second} seed channel …`.
- Admin tokens (`@access-admin-tokens`, same file): `a token "{alias}" of application "{app}" with scopes "{a, b}"`,
  `I issue a token of application "{app}" with scopes "{a, b}"` (an expected refusal; a token created anyway is
  revoked at the end), `I exchange the token "{alias}"` (the JWT stays in `context.exchanged`, never in
  `context.saved`), `the exchange answer is a Bearer JWT valid for {n} seconds`, `I send {METHOD} to "{path}" with the
  exchanged JWT of "{alias}"`, `the service account of application "{app}" signs in with the password "{p}"`,
  `the service account of application "{app}" is not in the staff list`.
- Clock (`features/steps/clock.py`, needs the channel + admin auth): `the channel clock is {weekday} {time}`,
  `the beat send task has run`, `the IMAP poll task has run`.
- Scenarios needing an empty mailbox purge in their own `Background` — never rely on order (`seed.sh` purges
  GreenMail once, `docs/harness.md`).

## Writing a new feature

1. Create `features/{module}/` + `{module}.feature` with appropriate tags.
2. Add module-specific steps in `features/steps/{module}_steps.py` (shared verbs already exist).
3. Add a CSV loader function in `src/entirius_tests/csv_loader.py` if needed.
4. Run `behave features/{module}/`; never hardcode channels, counts, or SKUs.
