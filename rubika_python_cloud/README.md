# Rubika Python Cloud v0.1

Text-only Rubika bot prototype. Each Python request runs on a fresh GitHub-hosted Actions runner.

## Included
- Rubika Bot API polling from a scheduled Actions workflow.
- Text commands only; no glass buttons.
- Separate worker workflow for each Python request.
- Worker has no repository secrets and read-only repository permissions.
- Execution limits: 10-second process timeout, Linux resource limits, 12 KiB source limit, 2-minute job timeout.
- A separate notifier workflow sends the result to Rubika; user code never receives the bot token.

## Limitations
- Polling runs on a 5-minute schedule and checks for updates for about 3 minutes. Replies are not instant.
- Only IDs in RUBIKA_ALLOWED_USERS may execute code.
- Every request gets a fresh runner. Files and installed packages do not persist.
- This version does not yet provide a persistent filesystem, interactive terminal, package persistence, or admin quota controls.
- GitHub Actions does not guarantee per-user 50 MB RAM / 185 MB disk allocations.
- Hosted runners have outbound network access. These limits are not a complete security sandbox. Keep the allowlist restricted to trusted testers; do not expose this prototype to arbitrary public users.

## Required repository secrets
Add these in Settings → Secrets and variables → Actions:
- RUBIKA_BOT_TOKEN: the token issued by Rubika BotFather.
- RUBIKA_ALLOWED_USERS: comma-separated Rubika sender IDs allowed to execute code.

Do not put tokens or passwords in source files.

## Enable
1. Add both secrets.
2. Ensure GitHub Actions are enabled in Settings → Actions → General.
3. Run Actions → Rubika Poller → Run workflow once.
4. Send /start to the bot, then send:

    پایتون:
    print("Hello from GitHub Actions")

The first response can take several minutes.

## Commands
- /start or /help: show help.
- پایتون: followed by Python source: dispatch an isolated worker.

## Flow
Rubika → scheduled poller → workflow_dispatch → fresh Python worker → result artifact → separate notifier → Rubika.

This is a prototype. Persistent user files, package management, faster message delivery, and broader user access need a separate security design.
