import Foundation
import EventKit

// MARK: - RemindCTL: Swift CLI for macOS Reminders via EventKit

class RemindersManager {
    let store = EKEventStore()

    func requestAccess(completion: @escaping (Bool) -> Void) {
        let status = EKEventStore.authorizationStatus(for: .reminder)
        if status == .authorized || status.rawValue == 4 /* fullAccess */ {
            completion(true)
            return
        }

        if #available(macOS 14.0, *) {
            store.requestFullAccessToReminders { granted, error in
                completion(granted)
            }
        } else {
            store.requestAccess(to: .reminder) { granted, error in
                completion(granted)
            }
        }
    }

    func getCalendar(named name: String?) -> EKCalendar? {
        let calendars = store.calendars(for: .reminder)
        if let name = name {
            return calendars.first { $0.title.lowercased() == name.lowercased() }
        }
        return store.defaultCalendarForNewReminders() ?? calendars.first
    }

    func listReminders(listName: String?, includeCompleted: Bool, completion: @escaping () -> Void) {
        let calendars: [EKCalendar]
        if let listName = listName {
            guard let cal = getCalendar(named: listName) else {
                print("❌ Error: List '\(listName)' not found.")
                completion()
                return
            }
            calendars = [cal]
        } else {
            calendars = store.calendars(for: .reminder)
        }

        let predicate: NSPredicate
        if includeCompleted {
            predicate = store.predicateForReminders(in: calendars)
        } else {
            predicate = store.predicateForIncompleteReminders(withDueDateStarting: nil, ending: nil, calendars: calendars)
        }

        store.fetchReminders(matching: predicate) { reminders in
            guard let reminders = reminders, !reminders.isEmpty else {
                print("ℹ️ No reminders found.")
                completion()
                return
            }

            var grouped = [String: [EKReminder]]()
            for r in reminders {
                grouped[r.calendar.title, default: []].append(r)
            }

            let df = DateFormatter()
            df.dateStyle = .medium
            df.timeStyle = .short

            for (calTitle, list) in grouped.sorted(by: { $0.key < $1.key }) {
                print("\n📋 List: \(calTitle)")
                for r in list {
                    let status = r.isCompleted ? "[x]" : "[ ]"
                    var line = "  \(status) \(r.title ?? "Untitled")"
                    if let due = r.dueDateComponents, let date = Calendar.current.date(from: due) {
                        line += " (Due: \(df.string(from: date)))"
                    }
                    if let rules = r.recurrenceRules, !rules.isEmpty {
                        let recStr = rules.map { rule -> String in
                            let freq: String
                            switch rule.frequency {
                            case .daily: freq = "Daily"
                            case .weekly: freq = "Weekly"
                            case .monthly: freq = "Monthly"
                            case .yearly: freq = "Yearly"
                            @unknown default: freq = "Custom"
                            }
                            return rule.interval > 1 ? "Every \(rule.interval) \(freq.lowercased())" : freq
                        }.joined(separator: ", ")
                        line += " 🔁 [\(recStr)]"
                    }
                    if let notes = r.notes, !notes.isEmpty {
                        line += "\n      Note: \(notes.replacingOccurrences(of: "\n", with: " "))"
                    }
                    print(line)
                }
            }
            completion()
        }
    }

    func addReminder(title: String, listName: String?, notes: String?, dueDate: Date?, recurrence: String?, interval: Int, completion: @escaping () -> Void) {
        guard let calendar = getCalendar(named: listName) else {
            print("❌ Error: List '\(listName ?? "Default")' not found.")
            completion()
            return
        }

        let reminder = EKReminder(eventStore: store)
        reminder.title = title
        reminder.notes = notes
        reminder.calendar = calendar

        if let dueDate = dueDate {
            let components = Calendar.current.dateComponents([.year, .month, .day, .hour, .minute, .timeZone], from: dueDate)
            reminder.dueDateComponents = components
            reminder.addAlarm(EKAlarm(absoluteDate: dueDate))
        }

        if let recurrence = recurrence?.lowercased() {
            let freq: EKRecurrenceFrequency
            switch recurrence {
            case "daily", "day": freq = .daily
            case "weekly", "week": freq = .weekly
            case "monthly", "month": freq = .monthly
            case "yearly", "year": freq = .yearly
            default:
                print("⚠️ Unknown recurrence frequency '\(recurrence)', skipping recurrence.")
                freq = .weekly
            }
            let rule = EKRecurrenceRule(recurrenceWith: freq, interval: max(1, interval), end: nil)
            reminder.addRecurrenceRule(rule)
        }

        do {
            try store.save(reminder, commit: true)
            print("✅ Successfully created reminder: '\(title)' in list '\(calendar.title)'")
        } catch {
            print("❌ Failed to create reminder: \(error.localizedDescription)")
        }
        completion()
    }

    func setRecurrence(title: String, listName: String?, recurrence: String, interval: Int, completion: @escaping () -> Void) {
        let calendars: [EKCalendar]
        if let listName = listName {
            guard let cal = getCalendar(named: listName) else {
                print("❌ Error: List '\(listName)' not found.")
                completion()
                return
            }
            calendars = [cal]
        } else {
            calendars = store.calendars(for: .reminder)
        }

        let predicate = store.predicateForIncompleteReminders(withDueDateStarting: nil, ending: nil, calendars: calendars)
        store.fetchReminders(matching: predicate) { reminders in
            guard let matched = reminders?.filter({ $0.title?.lowercased() == title.lowercased() }), !matched.isEmpty else {
                print("❌ No matching incomplete reminder found with title '\(title)'.")
                completion()
                return
            }

            let freq: EKRecurrenceFrequency
            switch recurrence.lowercased() {
            case "daily", "day": freq = .daily
            case "weekly", "week": freq = .weekly
            case "monthly", "month": freq = .monthly
            case "yearly", "year": freq = .yearly
            default:
                print("❌ Invalid recurrence type: '\(recurrence)'. Use daily, weekly, monthly, or yearly.")
                completion()
                return
            }

            for r in matched {
                if let existing = r.recurrenceRules {
                    for rule in existing { r.removeRecurrenceRule(rule) }
                }
                let rule = EKRecurrenceRule(recurrenceWith: freq, interval: max(1, interval), end: nil)
                r.addRecurrenceRule(rule)
                do {
                    try self.store.save(r, commit: true)
                    print("✅ Updated recurrence for '\(r.title ?? title)' to \(recurrence) (interval: \(interval))")
                } catch {
                    print("❌ Error updating '\(r.title ?? title)': \(error.localizedDescription)")
                }
            }
            completion()
        }
    }

    func completeReminder(title: String, listName: String?, completion: @escaping () -> Void) {
        let calendars = listName != nil ? [getCalendar(named: listName)!] : store.calendars(for: .reminder)
        let predicate = store.predicateForIncompleteReminders(withDueDateStarting: nil, ending: nil, calendars: calendars)
        store.fetchReminders(matching: predicate) { reminders in
            guard let matched = reminders?.filter({ $0.title?.lowercased() == title.lowercased() }), !matched.isEmpty else {
                print("❌ No matching incomplete reminder found with title '\(title)'.")
                completion()
                return
            }

            for r in matched {
                r.isCompleted = true
                do {
                    try self.store.save(r, commit: true)
                    print("✅ Completed reminder: '\(r.title ?? title)'")
                } catch {
                    print("❌ Error completing '\(r.title ?? title)': \(error.localizedDescription)")
                }
            }
            completion()
        }
    }
}

// MARK: - CLI Argument Parsing

let args = CommandLine.arguments
let semaphore = DispatchSemaphore(value: 0)
let manager = RemindersManager()

func printUsage() {
    print("""
    Usage: remindctl <command> [options]

    Commands:
      list                       List reminders
        --list <name>            Filter by list name
        --all                    Include completed reminders

      add                        Add a new reminder
        --title <text>           Reminder title (required)
        --list <name>            Target list name (default: default list)
        --notes <text>           Optional notes
        --due <YYYY-MM-DD HH:mm> Due date and time (e.g. "2026-08-31 18:00")
        --recurrence <freq>      daily | weekly | monthly | yearly
        --interval <n>           Recurrence interval (default: 1)

      recurrence                 Update recurrence rule on an existing reminder
        --title <text>           Reminder title (required)
        --recurrence <freq>      daily | weekly | monthly | yearly (required)
        --interval <n>           Recurrence interval (default: 1)
        --list <name>            Optional list name filter

      complete                   Mark a reminder as completed
        --title <text>           Reminder title (required)
        --list <name>            Optional list name filter
    """)
}

func getArgValue(_ flag: String) -> String? {
    if let idx = args.firstIndex(of: flag), idx + 1 < args.count {
        return args[idx + 1]
    }
    return nil
}

guard args.count > 1 else {
    printUsage()
    exit(0)
}

let command = args[1].lowercased()

manager.requestAccess { granted in
    guard granted else {
        print("❌ Error: Access to Reminders not granted. Check System Settings -> Privacy & Security -> Reminders.")
        semaphore.signal()
        return
    }

    switch command {
    case "list":
        let list = getArgValue("--list")
        let includeAll = args.contains("--all")
        manager.listReminders(listName: list, includeCompleted: includeAll) {
            semaphore.signal()
        }

    case "add":
        guard let title = getArgValue("--title") else {
            print("❌ Missing --title")
            semaphore.signal()
            return
        }
        let list = getArgValue("--list")
        let notes = getArgValue("--notes")
        let recurrence = getArgValue("--recurrence")
        let interval = Int(getArgValue("--interval") ?? "1") ?? 1

        var dueDate: Date? = nil
        if let dueStr = getArgValue("--due") {
            let df = DateFormatter()
            df.dateFormat = "yyyy-MM-dd HH:mm"
            df.locale = Locale(identifier: "en_US_POSIX")
            dueDate = df.date(from: dueStr)
            if dueDate == nil {
                df.dateFormat = "yyyy-MM-dd"
                dueDate = df.date(from: dueStr)
            }
        }

        manager.addReminder(title: title, listName: list, notes: notes, dueDate: dueDate, recurrence: recurrence, interval: interval) {
            semaphore.signal()
        }

    case "recurrence":
        guard let title = getArgValue("--title"), let recurrence = getArgValue("--recurrence") else {
            print("❌ Missing --title or --recurrence")
            semaphore.signal()
            return
        }
        let list = getArgValue("--list")
        let interval = Int(getArgValue("--interval") ?? "1") ?? 1
        manager.setRecurrence(title: title, listName: list, recurrence: recurrence, interval: interval) {
            semaphore.signal()
        }

    case "complete":
        guard let title = getArgValue("--title") else {
            print("❌ Missing --title")
            semaphore.signal()
            return
        }
        let list = getArgValue("--list")
        manager.completeReminder(title: title, listName: list) {
            semaphore.signal()
        }

    default:
        printUsage()
        semaphore.signal()
    }
}

_ = semaphore.wait(timeout: .now() + 15)
