# Technical Troubleshooting

If the app fails to log in, first confirm the customer is using the correct
email and that Caps Lock is off. A "500 error" on login usually clears up
by asking the customer to clear their browser cache or try a private
window; if it persists more than once, file a bug ticket with the
timestamp and browser/OS version.

Sync issues between devices are almost always resolved by signing out and
back in on the affected device. Data does not get lost during a sign-out.

Mobile app crashes on launch are most often caused by an outdated app
version. Ask the customer to update from the app store; if already on the
latest version, escalate to engineering with device model and OS version.

Two-factor authentication (2FA) codes expire after 5 minutes. If a customer
is locked out because they lost their 2FA device, they must be routed to
identity verification before 2FA can be reset - this cannot be done by a
support agent directly.
