---
name: macos-reminders
description: >-
  Automate and manage Apple Reminders on macOS using EventKit and AppleScript.
  Use when the user asks to list, create, edit, delete, complete, or schedule
  recurring reminders and alerts synced across macOS and iOS via iCloud.
---

# macOS Reminders Automation Skill

This skill provides fast and reliable CLI tools and scripts to interact directly with Apple's **Reminders** database on macOS via **EventKit** (and AppleScript fallback). Any changes made sync seamlessly across all iOS/iPadOS/macOS devices via iCloud.

## Helper Tool: `remindctl`

A pre-compiled Swift CLI tool is located at:
`~/.gemini/skills/macos-reminders/scripts/remindctl` (Source: `remindctl.swift`)

### Common Commands

#### 1. List Reminders
```bash
# List all active (incomplete) reminders across all lists
swift ~/.gemini/skills/macos-reminders/scripts/remindctl.swift list

# List active reminders in a specific list
swift ~/.gemini/skills/macos-reminders/scripts/remindctl.swift list --list "Business"

# List including completed reminders
swift ~/.gemini/skills/macos-reminders/scripts/remindctl.swift list --list "Business" --all
```

#### 2. Add a Reminder (with Due Date and Recurrence)
```bash
# Basic reminder
swift ~/.gemini/skills/macos-reminders/scripts/remindctl.swift add --title "Buy milk" --list "Przypomnienia"

# Recurring reminder with due date/alert
swift ~/.gemini/skills/macos-reminders/scripts/remindctl.swift add \
  --title "Zwolnij parking (wtorek)" \
  --list "Business" \
  --due "2026-08-31 18:00" \
  --recurrence "weekly" \
  --notes "Zwolnij miejsce parkingowe na wtorek (jeśli niepotrzebne)"
```
Supported recurrence frequencies: `daily`, `weekly`, `monthly`, `yearly`. Use `--interval <n>` for custom intervals (e.g. every 2 weeks).

#### 3. Update Recurrence on Existing Reminder
```bash
swift ~/.gemini/skills/macos-reminders/scripts/remindctl.swift recurrence \
  --title "Zwolnij parking (wtorek)" \
  --recurrence "weekly" \
  --list "Business"
```

#### 4. Complete a Reminder
```bash
swift ~/.gemini/skills/macos-reminders/scripts/remindctl.swift complete \
  --title "Buy milk" \
  --list "Przypomnienia"
```

---

## Zero-Dependency AppleScript Fallback

For quick lightweight queries without EventKit:

```bash
# Get all list names
osascript -e 'tell application "Reminders" to get name of lists'

# Add basic reminder via AppleScript
osascript -e '
tell application "Reminders"
    set targetList to list "Business"
    make new reminder at end of reminders of targetList with properties {name:"Task Name", body:"Notes"}
end tell'
```
