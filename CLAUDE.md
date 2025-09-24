# CRITICAL: tap-wordpress-reviews Setup & Testing

## 🚨 FUNDAMENTAL UNDERSTANDING

### How This Tap Works
1. **Writes state** to `unified_state.json` at the end of each sync
2. **Tracks per-plugin data**: `newest_seen`, `oldest_seen`, and `count`
3. **Always fetches all pages** up to the configured limit
4. **Not truly incremental**: Doesn't stop when it hits known data
5. **Simple approach**: Re-fetches everything each time

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

## 📁 State File: unified_state.json

### What Gets Stored
```json
{
  "type": "STATE",
  "value": {
    "plugin_states": {
      "woocommerce": {
        "reviews": {                    // Separate state per stream type
          "count": 742,
          "newest_seen": "2025-09-15T10:30:00",
          "oldest_seen": "2025-06-01T14:22:00"
        },
        "support_threads": {            // Only if support threads were synced
          "count": 1523,
          "newest_seen": "2025-09-24T08:00:00",
          "oldest_seen": "2025-01-01T12:00:00"
        }
      },
      "mailpoet": { ... }              // Each plugin tracked separately
    }
  }
}
```

### For Initial/Full Syncs
- **DELETE unified_state.json** to start fresh
- The tap will fetch ALL history up to your configured limit
- State file will be created at the end of the sync

### For Subsequent Syncs
- Keep the unified_state.json from previous run (though it's not used for stopping)
- Tap will fetch all data again up to the configured limit
- State is updated with new `newest_seen` dates

## 🔥 KNOWN ISSUES & GOTCHAS

### DO NOT TRUST MY TESTING
- **ALWAYS verify the catalog** before saying "yes you can run it"
- **ALWAYS check which tap version** is being used (venv vs source)
- **ALWAYS run a small test** before full production runs
- **DELETE unified_state.json for full initial syncs**

### Discovery Configuration
- **Behavior**: Respects `support_threads` setting in config
- `support_threads: false` → Only generates reviews stream
- `support_threads: true` → Only generates support_threads stream
- **Location**: `tap_wordpress_reviews/discover.py`
- **Note**: If using venv installation, must reinstall after code changes

### httpx Configuration
- **Version**: 0.28.1
- **Redirect parameter**: Uses `follow_redirects=True`
- **Location**: `tap_wordpress_reviews/wordpress_review.py`

## 📋 MANDATORY CHECKLIST BEFORE SAYING "YES YOU CAN RUN IT"

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