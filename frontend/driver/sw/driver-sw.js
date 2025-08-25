self.addEventListener('push', (event) => {
  let data = {};
  try {
    data = event.data ? event.data.json() : {};
  } catch (e) {
    // ignore
  }
  const title = data.title || 'New Assignment';
  const options = {
    body: data.body || '',
    data: { assignmentId: data.assignmentId },
  };
  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const id = event.notification?.data?.assignmentId;
  event.waitUntil(
    self.clients.matchAll({ type: 'window' }).then((clients) => {
      for (const client of clients) {
        if ('focus' in client) {
          client.focus();
          if (id) client.navigate(`/driver/assignment/${id}`);
          return;
        }
      }
      if (self.clients.openWindow) {
        if (id) return self.clients.openWindow(`/driver/assignment/${id}`);
        return self.clients.openWindow('/driver');
      }
    })
  );
});
