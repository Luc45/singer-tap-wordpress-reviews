# CRITICAL: tap-wordpress-reviews Setup & Testing

## ⚠️ BEFORE RUNNING ANY SYNC

### 1. CHECK THE CATALOG
```bash
# ALWAYS verify what streams are in the catalog and which are selected
cat [catalog_file] | jq '.streams[] | {stream: .tap_stream_id, selected: .schema.selected}'
```

### 2. VERIFY TAP INSTALLATION
```bash
# Check if running from venv or system
which tap-wordpress-reviews
# If venv exists, it may have OLD CODE without fixes!
ls -la tap_env/
```

### 3. REGENERATE CATALOG AFTER ANY CODE CHANGES
```bash
# The catalog MUST be regenerated after fixing discovery!
tap-wordpress-reviews --config [config_file] --discover > [new_catalog_file]
```

## 🔥 KNOWN ISSUES

### Discovery Bug (FIXED in source, NOT in venv)
- **Problem**: Discovery didn't respect `support_threads: false` in config
- **Fix**: Modified `discover()` function to accept and respect config
- **Location**: `tap_wordpress_reviews/discover.py`
- **CRITICAL**: If using venv installation, reinstall after fixes!

### httpx Compatibility
- **Version**: 0.28.1 uses `follow_redirects=True` (not `allow_redirects`)
- **Location**: `tap_wordpress_reviews/wordpress_review.py`

## 📋 TEST CHECKLIST BEFORE PRODUCTION

- [ ] Verify config has correct settings
- [ ] Regenerate catalog with fixed discovery
- [ ] Check catalog only has desired streams
- [ ] Verify selected streams match config intent
- [ ] Run small test (2-3 plugins, low number limit)
- [ ] Check output data has correct fields
- [ ] For reviews: should have `rating`, `title`, `text`
- [ ] For support: should have `filter_type`, `last_activity`

## 🚨 EMERGENCY: Wrong Data Being Fetched

If fetching wrong stream type (e.g., support instead of reviews):

1. **STOP THE SYNC IMMEDIATELY**
2. Check the catalog - probably has wrong streams selected
3. Check the logs for URLs:
   - Reviews: `/support/plugin/[name]/reviews/`
   - Support: `/support/plugin/[name]/` (no /reviews/)
4. Regenerate catalog with correct config
5. Ensure only desired stream is selected

## 🛠️ Reinstall After Code Changes

```bash
# If using venv
tap_env/bin/pip uninstall tap-wordpress-reviews
tap_env/bin/pip install -e .

# Or recreate venv entirely
rm -rf tap_env
python -m venv tap_env
tap_env/bin/pip install -e .
```

## ⚡ Quick Commands

```bash
# Generate catalog for reviews only
tap-wordpress-reviews --config woo_ecosystem_reviews_only.json --discover > woo_reviews_catalog_CORRECT.json

# Verify catalog streams
cat woo_reviews_catalog_CORRECT.json | jq '.streams[].tap_stream_id'

# Run sync with correct catalog
tap-wordpress-reviews \
    --config woo_ecosystem_reviews_only.json \
    --catalog woo_reviews_catalog_CORRECT.json \
    > output.jsonl 2> sync.log
```

## 📊 Expected Data Structure

### Reviews Stream Fields
- `author`, `date`, `path`, `plugin`
- `rating` (1-5 stars)
- `title` (review title)
- `text` (review content)
- `comments` (array of responses)

### Support Threads Fields
- `author`, `date`, `path`, `plugin`
- `filter_type` (resolved/unresolved)
- `last_activity` (timestamp)
- `plugin_author_response` (boolean)
- `status` (open/closed)

## 🔍 Debugging Commands

```bash
# Check what's actually being fetched
tail -f sync.log | grep "Loading"

# Count records by plugin
cat output.jsonl | jq -r '.record.plugin' | sort | uniq -c

# Verify stream type in output
cat output.jsonl | jq -c 'select(.type == "RECORD") | {stream: .stream, has_rating: (.record.rating != null), has_filter: (.record.filter_type != null)}' | head -5
```

---

**NEVER RUN A SYNC WITHOUT VERIFYING THE CATALOG FIRST!**