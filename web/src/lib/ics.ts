/** A minimal iCalendar file of all-day events (RFC 5545), for reminders in any calendar app. */

export interface CalendarEvent {
  /** YYYY-MM-DD */
  date: string;
  summary: string;
}

const escape = (text: string) => text.replace(/\\/g, "\\\\").replace(/([,;])/g, "\\$1").replace(/\n/g, "\\n");

export function icsCalendar(events: CalendarEvent[], stamp: string): string {
  const compact = (d: string) => d.slice(0, 10).replace(/-/g, "");
  const lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Jyotish Platform//Reminders//EN", "CALSCALE:GREGORIAN"];
  events.forEach((event, i) => {
    lines.push(
      "BEGIN:VEVENT",
      `UID:${compact(event.date)}-${i}@jyotish-platform`,
      `DTSTAMP:${stamp}`,
      `DTSTART;VALUE=DATE:${compact(event.date)}`,
      `SUMMARY:${escape(event.summary)}`,
      "END:VEVENT",
    );
  });
  lines.push("END:VCALENDAR");
  return `${lines.join("\r\n")}\r\n`;
}
