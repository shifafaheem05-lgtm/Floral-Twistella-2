# Floral Twistella - Daily Facebook + Instagram Auto-Poster

Posts **one photo or Reel every day at 5:00 PM Pakistan time** from a 45-day calendar
(33 photos + 12 Reels). No dates: it starts at **Day 1** and moves forward one day per successful post,
then loops back to Day 1 (switch off in the Settings sheet).

```
content_calendar.xlsx             the calendar (captions, alt text, SEO keywords, notes) - edit here
media/day_01.jpg ... day_45       branded, ready-to-post photos + 1080x1920 Reels (logo already added)
originals/                        your untouched source files, renamed by day number
assets/logo.png                   PLACEHOLDER logo -> replace with your real one
media_config.json                 logo size/position + manual crops
scripts/prepare_media.py          crops, adds logo, formats Reels  (originals -> media)
scripts/make_placeholder_logo.py  regenerates the placeholder logo
post_to_facebook_instagram.py     the poster
posted_state.json                 remembers the last posted day (auto-updated by the workflow)
.github/workflows/dailypost.yml   GitHub Actions schedule (12:00 UTC = 5 PM PKT)
requirements.txt
```

## 1. Put your real logo on everything
1. Save your logo as `assets/logo.png` (PNG, transparent background, ~1200 px wide).
2. Run `pip install -r requirements.txt` (and have `ffmpeg` installed), then `python scripts/prepare_media.py`.
3. Commit the refreshed `media/` folder.
Position/size: edit `media_config.json` (photos: bottom-right, Reels: top-left inside the video area, clear of Instagram's UI).

## 2. One-time GitHub + Meta setup
1. Create a **public** GitHub repo and upload everything (keep the folders).
   Private repo? Set a `MEDIA_BASE_URL` variable pointing to any public host of the `media/` folder.
2. Instagram account = **Business/Creator**, linked to your Facebook Page.
3. In Meta for Developers, create an app and generate a **long-lived Page access token** with:
   `pages_show_list, pages_read_engagement, pages_manage_posts, instagram_basic, instagram_content_publish`.
4. Repo -> Settings -> Secrets and variables -> Actions -> **Secrets**:
   `FB_PAGE_ID`, `FB_PAGE_ACCESS_TOKEN`, `IG_USER_ID`.
5. Repo -> Settings -> Actions -> General -> Workflow permissions -> **Read and write** (needed to save `posted_state.json`).
6. Actions tab -> "Daily Facebook & Instagram Post" -> **Run workflow** with *Dry run* ticked to preview,
   then run once for real to test.

## 3. Everyday use
- Edit captions directly in `content_calendar.xlsx`; the script posts exactly what the cells say.
- Local checks: `python post_to_facebook_instagram.py --check` (validate) / `--dry-run` (preview next post).
- Re-post or test a specific day: `--day 12` (manual runs never change progress).
- Add a day: new row (next Day number) + `originals/day_46.<ext>` + `python scripts/prepare_media.py --days 46`.

## Good to know
- GitHub cron can start 5-30 min late; scheduled workflows pause after 60 days without repo activity (push any small commit).
- If Facebook works but Instagram fails, the day still counts as posted (see `history` in `posted_state.json`); re-post with `--day N --only instagram`.
- Never commit tokens - keep them in GitHub Secrets.

## Check before going live (see the Notes column)
- Some photos/clips show a **"Z&N Creation" sticker**, or **customers' photos and names** - get consent / crop.
- Clips 1-8 carry a **"Meta AI" watermark** (AI-animated): left untouched - turn on the "AI info" label when posting.
- Several crochet photos look AI-styled - make sure they show what you really deliver.
