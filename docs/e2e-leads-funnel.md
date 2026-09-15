# Leads funnel e2e

Mode B of the leads funnel (entirius-docs `guides/leads-end-to-end-testing.md`): Playwright clicks the funnel through
the admin CMS, on a phone and on a desktop. Mode A is the BDD feature `features/leads/leads_funnel.feature`
(`@funnel`); mode C is an AI-tester session driven by zeno.

## Files

| Path | Holds |
|---|---|
| `e2e/cms/test_leads_funnel.py` | the tests; `pytestmark = require_module("leads")` skips the file when munin does not list leads |
| `e2e/cms/conftest.py` | `admin_page` — a CMS page with the admin logged in |
| `e2e/conftest.py` | `E2E_DEVICE` device emulation; `desktop_only` tests are skipped under a device |
| `src/entirius_tests/cms_e2e.py` | `CMS_BASE_URL` (`:8180`), `API_BASE_URL` (`:8100`), admin login, `module_installed` |
| `src/entirius_tests/cms_pages/` | page objects, one per screen; every user action counts a tap (`self.taps`) |
| `src/entirius_tests/mail.py`, `clock.py` | GreenMail REST/IMAP and the communicator test endpoints (channel clock, beat send, IMAP poll) |

Page objects:

| Class | Screen |
|---|---|
| `LeadsImportPage` | CSV import dialog |
| `BoardPage` | leads board: search, card per stage |
| `CompanyPage` | company card and its tabs (`intel`), create-customer action |
| `InboxPage` | Inbox and Review: open a draft, send, scheduled state, horizontal scroll check |
| `ThreadPage` | company thread: outbound status, reply, opt-out confirm |
| `NotificationBar` | unread badge, rows by title and severity, open a row |
| `SettingsPage` | communicator settings: scheduled mails table, Send now |
| `StagesPage` | stage list, delete with inline error |

## Tests

| Test | Runs on | Proves |
|---|---|---|
| `test_funnel_steps_1_to_7` | desktop | CSV upload in the CMS lands on the board in `new`; Intel tab shows the desktop score; then steps 3–7 |
| `test_funnel_steps_3_to_7` | phone, desktop | accept a draft in ≤ 3 taps, sent status in the thread, reply shown, tapping the notification jumps to the company thread and drops the badge by one |
| `test_C07_accept_from_inbox_schedules` | phone, desktop | an accepted draft is `approved` with a future `scheduled_at`; the Inbox shows the next slot |
| `test_C31_send_now_moves_scheduled_at` | desktop | Send now in settings moves `scheduled_at` only and sends nothing; the beat sends it |
| `test_C23_optout_confirm_from_thread` | phone, desktop | a suspected opt-out reply is confirmed from the thread |
| `test_N01_high_notification_in_bar` | phone, desktop | a reply raises a `high` notification that opens the company thread |
| `test_L15_create_customer_action_only_with_accounts` | desktop | the create-customer action appears in a `won` stage only when accounts is installed |
| `test_L18_stage_delete_refused_inline` | desktop | deleting a stage that holds a company shows an inline error and keeps the stage |

## State and determinism

The file runs twice on the same seed, so every test builds its own state through the admin API:

- **Own thread per run.** Drafts come from `communicator/…/test/communicate/` with a unique recipient
  (`e2e-<ns>@<seeded domain>`) on a seeded company (`example-shop-4/5/6.test`). The CSV-to-draft path belongs to
  `@funnel`, which consumes it on a seed.
- **Own Inbox.** Every other `review_required` draft is skipped first, so the Inbox holds only the test's draft.
- **Own CSV.** Step 1 uploads the first row of `package/leads--default-europe.csv` under a unique domain. The CMS
  `POST imports/` is routed to `test/import-now/` (same multipart body), so the import completes in the request.
- **Open send policy.** An autouse fixture opens the policy to the whole day (no business-days rule, cap 1000)
  and restores the original after the test. Drafts are due now: no channel clock in the future, replies land
  after the sent mail, and the beat sends nothing the tests leave behind later.
- **Sending.** `_send` sets the channel clock to the message's slot, runs one beat send and clears the clock.
- **C07 and C-31 close the window.** They replace the window with one hour twelve hours from now, so the accepted
  message waits for a future slot and the beat cannot send it mid-test. C-31 reopens the window before its own
  beat run; the fixture restores the policy either way.
- **Replies.** `_reply` renders a `fixtures/mail/` file with `In-Reply-To` of the sent mail, a `Date` one minute
  after `sent_at`, `From` the thread recipient and a fresh `Message-ID`, appends it over IMAP and runs the poll.
- **Mailbox checks are scoped.** C-31 counts sandbox mails by `X-Original-To` of its own recipient, never the
  whole mailbox.

## One-shot tags

The e2e file carries no tags and can re-run on one seed. The BDD side cannot:

- `@funnel` (with `@leads @leads-oneshot`) consumes the import, audit, draft and reply of `example-shop-1.test`.
- `@leads-oneshot` and `@communicator-oneshot` scenarios elsewhere in the suite mutate pre-seeded rows once.

A second BDD run on the same database fails on purpose. Re-seed first.

## Run it (zeno)

Prerequisites: toolbox up (`make toolbox-check` green) before the seed, a fresh `make seed`, `make mail`,
`make cms-dev`.

```bash
make seed && make bdd TAGS=@funnel   # mode A first, on the fresh seed
make e2e-funnel                      # mode B: E2E_DEVICE="iPhone 14", then desktop
make runner-init                     # once: registers the ux-tester role
make e2e-accept                      # mode C: ux-tester session, report in .runner/accept/<ts>/
```

`make e2e-accept` exits 1 when a runner guard trips, `report.md` is missing or its `## Blockers` section lists
anything. First `make e2e` on a host needs `uv run --extra e2e playwright install chromium` here.

A single test outside zeno:

```bash
CMS_BASE_URL=http://localhost:8180 API_BASE_URL=http://localhost:8100 \
  make e2e E2E_ARGS="e2e/cms/test_leads_funnel.py -k C07" E2E_DEVICE="iPhone 14"
```
