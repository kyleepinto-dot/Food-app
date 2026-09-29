# Turning on real invite emails (Gmail)

By default the app records Circle invites but does not email them. To make it send
a real email when you invite someone by email address, do this one-time setup.

You need a Gmail account and an **App Password** (a special 16-character password
just for this app — not your normal Gmail password). App passwords require that
2-Step Verification is turned on for the Google account.

## 1. Turn on 2-Step Verification (if it isn't already)
- Go to https://myaccount.google.com/security
- Under "How you sign in to Google," turn on **2-Step Verification**.

## 2. Create an App Password
- Go to https://myaccount.google.com/apppasswords
- Type a name like **SharedPantry** and click **Create**.
- Google shows a 16-character password like `abcd efgh ijkl mnop`. Copy it.

## 3. Put it in a local config file (never committed to GitHub)
- In the project folder, copy `email_config.example.py` and rename the copy to
  **`email_config.py`**.
- Open `email_config.py` and fill in:
  ```python
  GMAIL_USER = "youraddress@gmail.com"
  GMAIL_APP_PASSWORD = "abcd efgh ijkl mnop"
  ```
- Save it. (`email_config.py` is git-ignored, so your password stays on your
  machine and never goes to GitHub.)

*(Alternative to the file: set the environment variables
`SHAREDPANTRY_GMAIL_USER` and `SHAREDPANTRY_GMAIL_APP_PASSWORD` instead.)*

## 4. Test it
- Run the app, go to **Me → My Circle**, type a **real email address** you can
  check, and click **Send invite**.
- The app shows "Sending invite to ..." then "Invite email sent." Check that
  inbox (look in Spam the first time — mark it "Not spam" so future ones land in
  the inbox).

## Notes
- If setup is skipped or wrong, the app still works — it just records the invite
  and tells you email isn't set up. It never crashes.
- Inviting a **phone number** (instead of an email) never sends an email.
- This sends a friendly invite with a code. Actually joining someone to your
  Circle across their own device would need a shared online server, which is
  beyond this app (see the project notes).
