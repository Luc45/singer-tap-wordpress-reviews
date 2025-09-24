# Usage Examples for tap-wordpress-reviews

This tap can fetch both **reviews** and **support threads** from WordPress.org plugin pages.

## 🚀 Prerequisites

### 1. Activate Virtual Environment

Before running any commands, you need to activate the virtual environment where the tap is installed:

```bash
# Activate the virtual environment
source test_venv/bin/activate

# You'll see (test_venv) in your prompt when activated
```

### 2. Create Configuration File

The tap requires a `config.json` file to specify which WordPress plugins to monitor:

```bash
# Single plugin
echo '{"plugins": ["wordpress-seo"]}' > config.json

# Multiple plugins with options
cat > config.json << 'EOF'
{
  "plugins": ["wordpress-seo", "akismet"],
  "number": 10,
  "support_threads": false,
  "thread_filter": "all"
}
EOF
```

**Configuration Options:**
- `plugins` (required): Array of WordPress plugin slugs to fetch data from
- `number` (optional, default: 30): Number of items to fetch per plugin
- `support_threads` (optional, default: false): Set to `true` to also fetch support threads
- `thread_filter` (optional, default: "all"): For support threads - "all", "active", or "unresolved"

**Popular plugin slugs:**
- `"wordpress-seo"` - Yoast SEO
- `"akismet"` - Akismet Anti-Spam
- `"woocommerce"` - WooCommerce
- `"contact-form-7"` - Contact Form 7
- `"jetpack"` - Jetpack

### 3. Prepare Catalog (Required for Sync)

Before syncing, you need a catalog. Discovery creates it but doesn't fetch any data:

```bash
# Create catalog (NO HTTP requests - just returns schema)
tap-wordpress-reviews --config config.json --discover > catalog.json
```

## 🔥 Actually Syncing Data (Makes HTTP Requests!)

### Quick Start - Sync Everything

```bash
# This ACTUALLY fetches data from WordPress.org!
tap-wordpress-reviews --config config.json --catalog catalog.json

# Watch it work (see the HTTP requests)
tap-wordpress-reviews --config config.json --catalog catalog.json 2>&1 | grep "Loading"

# See first 5 reviews
tap-wordpress-reviews --config config.json --catalog catalog.json | grep "^RECORD" | head -5 | jq .
```

## 🎯 Sync Reviews Only (Default)

### Fetch reviews for a single plugin

```bash
# Config for one plugin (reviews only by default)
echo '{"plugins": ["wordpress-seo"], "number": 10}' > config.json

# Create catalog and select only reviews stream
tap-wordpress-reviews --config config.json --discover | \
  jq '.streams[0] | .metadata[0].metadata.selected = true | {"streams": [.]}' > reviews_catalog.json

# SYNC - This fetches real reviews from WordPress.org!
tap-wordpress-reviews --config config.json --catalog reviews_catalog.json | \
  grep "^RECORD" | head -5 | jq '.record | {author, rating, date}'
```

### See 1-star reviews (while syncing)

```bash
# Fetch and filter for 1-star reviews in real-time
tap-wordpress-reviews --config config.json --catalog reviews_catalog.json | \
  grep "^RECORD" | jq 'select(.record.rating == 1) | .record | {author, rating, text: .text[:100]}'
```

## 🆘 Sync Support Threads

### Fetch support threads only

```bash
# Config for support threads (must explicitly enable)
cat > config_threads.json << 'EOF'
{
  "plugins": ["wordpress-seo"],
  "number": 10,
  "support_threads": true,
  "thread_filter": "all"
}
EOF

# For unresolved threads only
cat > config_unresolved.json << 'EOF'
{
  "plugins": ["wordpress-seo"],
  "number": 10,
  "support_threads": true,
  "thread_filter": "unresolved"
}
EOF

# Create catalog for support threads
tap-wordpress-reviews --config config_unresolved.json --discover | \
  jq '.streams[1] | .metadata[0].metadata.selected = true | {"streams": [.]}' > support_catalog.json

# SYNC - Fetches real support threads!
tap-wordpress-reviews --config config_unresolved.json --catalog support_catalog.json | \
  grep "^RECORD" | head -3 | jq '.record | {title, status, author}'
```

### Find threads where plugin author responded

```bash
# While syncing, filter for author responses
tap-wordpress-reviews --config config.json --catalog support_catalog.json | \
  grep "^RECORD" | jq 'select(.record.plugin_author_response == true) | .record.title'
```

## 📊 Sync Both Reviews and Support Threads

```bash
# Config for BOTH reviews and support threads
cat > both_config.json << 'EOF'
{
  "plugins": ["wordpress-seo", "woocommerce"],
  "number": 50,
  "support_threads": true,
  "thread_filter": "all"
}
EOF

# Create catalog with both streams
tap-wordpress-reviews --config both_config.json --discover > both_catalog.json

# SYNC both reviews and support threads
tap-wordpress-reviews --config both_config.json --catalog both_catalog.json | \
  grep "^RECORD" | jq -r '.stream' | sort | uniq -c
# Output: count of reviews vs support_threads
```

## 📊 Sync Multiple Plugins

```bash
# Config for multiple plugins (reviews only by default)
echo '{"plugins": ["wordpress-seo", "akismet", "woocommerce"], "number": 5}' > multi_config.json

# Create catalog
tap-wordpress-reviews --config multi_config.json --discover > multi_catalog.json

# SYNC all plugins - watch it fetch from each!
tap-wordpress-reviews --config multi_config.json --catalog multi_catalog.json 2>&1 | \
  grep "Loading.*page"

# Count reviews per plugin while syncing
tap-wordpress-reviews --config multi_config.json --catalog multi_catalog.json | \
  grep "^RECORD" | jq -r '.record.path' | cut -d'/' -f4 | sort | uniq -c
```

## 🔄 Incremental Sync (Stateful)

### First sync - saves state

```bash
# Initial sync - fetches ALL historical data
tap-wordpress-reviews --config config.json --catalog catalog.json | \
  tee >(grep "^STATE" | tail -1 > state.json)

# Check what's in state (bookmark of newest record)
cat state.json | jq '.bookmarks.reviews.replication_key_value'
```

### Second sync - only new data

```bash
# This only fetches reviews NEWER than the state!
tap-wordpress-reviews --config config.json --catalog catalog.json --state state.json | \
  grep "^RECORD" | wc -l

# If no new reviews, this returns 0
```

## 🔍 Monitor Sync Progress

### Watch the tap work in real-time

```bash
# See all HTTP requests as they happen
tap-wordpress-reviews --config config.json --catalog catalog.json 2>&1 | \
  grep -E "(Loading|Processing|Syncing)"

# Monitor state during backfill
tap-wordpress-reviews --config config.json --catalog catalog.json | \
  grep "^STATE" | jq '.bookmarks.reviews.backfill | {oldest: .oldest_seen, fetched: .total_fetched}'

# Time the full sync
time tap-wordpress-reviews --config config.json --catalog catalog.json | wc -l
```

## 💾 Export Synced Data

### Save reviews to JSON file

```bash
# Sync and save all review records
tap-wordpress-reviews --config config.json --catalog reviews_catalog.json | \
  grep "^RECORD" | jq .record > reviews_backup.json

# Create CSV of reviews
tap-wordpress-reviews --config config.json --catalog reviews_catalog.json | \
  grep "^RECORD" | jq -r '.record | [.date, .author, .rating, .title] | @csv' > reviews.csv
```

### Generate a quick report

```bash
# Sync and create rating distribution
tap-wordpress-reviews --config config.json --catalog reviews_catalog.json | \
  grep "^RECORD" | jq -r '.record.rating' | \
  sort | uniq -c | awk '{print $2 " stars: " $1 " reviews"}'
```

## 🐛 Debugging

### See errors during sync

```bash
# Run sync and only see errors
tap-wordpress-reviews --config config.json --catalog catalog.json 2>&1 >/dev/null | \
  grep -E "(ERROR|CRITICAL|WARNING|failed)"

# Verbose mode - see everything
tap-wordpress-reviews --config config.json --catalog catalog.json 2>&1 | less
```

## 📝 Key Points to Remember

1. **Discovery** (`--discover`) = NO HTTP requests, just returns schema
2. **Sync** (`--catalog catalog.json`) = MAKES HTTP requests, fetches real data
3. Always create a catalog before syncing
4. Use `--state state.json` for incremental syncs
5. The tap outputs Singer format: SCHEMA, RECORD, STATE messages
6. Use `grep "^RECORD"` to filter just the data records
7. Use `2>&1` to see log messages along with data

## 🚀 Quick Test

```bash
# Test 1: Reviews only (default)
echo '{"plugins": ["akismet"], "number": 5}' > test.json
tap-wordpress-reviews --config test.json --discover > test_catalog.json
tap-wordpress-reviews --config test.json --catalog test_catalog.json | \
  grep "^RECORD" | jq '.record | {author, rating}'

# Test 2: Both reviews and support threads
echo '{"plugins": ["akismet"], "number": 5, "support_threads": true}' > test_both.json
tap-wordpress-reviews --config test.json --discover > test_catalog.json
tap-wordpress-reviews --config test.json --catalog test_catalog.json | \
  grep "^RECORD" | jq '.record | {author, rating}'
```

This will actually fetch real reviews from WordPress.org!