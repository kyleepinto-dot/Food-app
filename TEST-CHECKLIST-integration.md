# Integration Test Checklist — one single app

Yaashvi's screens (login, My Circle, Share, Donate, Impact) are now wired into the
single app, on one multi-user database. This branch is **`integrate-single-app`** —
the working app on `yaashvi-dev` is untouched until this is tested and merged.

> ⚠️ This was integrated with AI help and **could not be run end-to-end** on the
> machine it was built on (that machine has no camera libraries). So please test
> everything below on a full setup before we merge. Note anything that looks
> broken or disconnected.

## Setup
1. Get the branch:
   ```
   git fetch origin
   git checkout integrate-single-app
   ```
2. Install requirements (Flet 0.85 + camera libs):
   ```
   pip install -r requirements.txt
   ```
3. Run the app:
   ```
      flet run main.py
   ```

## What changed (so you know what to look at)
- The app now **opens to a Welcome / login screen**. You must create an account
  or sign in to get in.
- The **"Me"** tab now shows the **Impact** screen (stats + profile + Log out +
  a **My Circle** button). The old plain "Me" settings page is no longer shown
  (its file `me_page.py` is still in the repo, nothing was deleted).
- The pantry item **Options** screen's **Share** and **Donate** buttons now open
  the real Share and Donate screens (they used to just show a message).
- All pantry data is now **per-user** (each account has its own pantry).

## Tests — tick each one
**Login**
- [ ] App opens to Welcome. "Create account" makes a new account and goes in.
- [ ] Log out (Me tab → Log out) returns to Welcome.
- [ ] Sign in with the same email/password works; wrong password shows an error.
- [ ] Close & reopen the app — it remembers you're logged in (session).

**Pantry (regression + multi-user)**
- [ ] Add an item (Pantry → Add manually) — it appears in your pantry.
- [ ] Make a SECOND account — its pantry is empty (you only see your own items).
- [ ] Scanner still works and can add a scanned item to the pantry (Kylee).

**Share**
- [ ] Pantry item → Options → Share opens the Share form, locked to that item's
      food type, and posting shows a confirmation.

**Donate**
- [ ] A **sealed, in-date** item → Options → Donate → pick a bank → Confirm →
      a drop-off pass appears.
- [ ] A **homemade/opened** item → Options → Donate shows a "can't be donated"
      reason (not eligible).
- [ ] The pass's "View dashboard" link opens the food-bank dashboard, and
      "Check in" marks a donation checked in.

**My Circle**
- [ ] Me → My Circle shows your circle; sending an invite adds a "pending" row.

**Impact**
- [ ] Me tab shows stats (meals shared, items donated, lb saved, CO₂), recent
      activity, and badges that reflect what you've actually done.

**Existing data**
- [ ] Any items that were already in the app before are still there after the
      upgrade (they become owned by the first account).

## If something's wrong
Note the screen and what happened. Because this is on its own branch, nothing is
at risk — we fix on the branch and only merge into `yaashvi-dev` once it all works.
When merging, the old separate `yaashvi/` folder gets deleted so there's truly one app.
