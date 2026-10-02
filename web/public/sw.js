// Service worker for reminder notifications (Web Push). The API encrypts each message
// for this browser; it carries a title, a body and the page to open on a click.
self.addEventListener("push", (event) => {
  let message = {};
  try {
    message = event.data ? event.data.json() : {};
  } catch {
    message = { body: event.data ? event.data.text() : "" };
  }
  event.waitUntil(
    self.registration.showNotification(message.title || "Jyotish", {
      body: message.body || "",
      data: { url: message.url || "/my" },
    }),
  );
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  let target = new URL(event.notification.data?.url || "/my", self.location.origin);
  if (target.origin !== self.location.origin) target = new URL("/my", self.location.origin);
  event.waitUntil(
    self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((windows) => {
      const open = windows.find((client) => client.url === target.href);
      return open ? open.focus() : self.clients.openWindow(target.href);
    }),
  );
});
