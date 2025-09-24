# Usage Examples for tap-wordpress-reviews

## 🚀 Prerequisites

### 1. Activate Virtual Environment

Before running any commands, you need to activate the virtual environment where the tap is installed:

```bash
# Activate the virtual environment
source test_venv/bin/activate

# You'll see (test_venv) in your prompt when activated
# Now all tap-wordpress-reviews commands will work
```

Alternatively, you can use the full path without activating:
```bash
./test_venv/bin/tap-wordpress-reviews --config config.json --discover
```

### 2. Create Configuration File

The tap requires a `config.json` file to specify which WordPress plugins to monitor. Create it like this:

```bash
# Basic config for a single plugin
echo '{"plugins": ["wordpress-seo"]}' > config.json

# Or with more options
cat > config.json << 'EOF'
{
  "plugins": ["wordpress-seo"],
  "number": 30,
  "thread_filter": "all"
}
EOF
```

**Configuration Options:**
- `plugins` (required): Array of WordPress plugin slugs to fetch data from
- `number` (optional, default: 30): Number of items to fetch per page
- `thread_filter` (optional, default: "all"): For support threads - can be "all", "active", or "unresolved"

**Examples of plugin slugs:**
- `"wordpress-seo"` - Yoast SEO
- `"akismet"` - Akismet Anti-Spam
- `"woocommerce"` - WooCommerce
- `"contact-form-7"` - Contact Form 7
- `"jetpack"` - Jetpack

## 🔍 Discovery & Exploration

### See what streams are available (pretty printed)
```bash
tap-wordpress-reviews --config config.json --discover | jq .
```

### Just see stream names and their replication methods
```bash
tap-wordpress-reviews --config config.json --discover | jq '.streams[] | {stream: .tap_stream_id, replication: .replication_method, key: .replication_key}'
```

### Check the schema for reviews
```bash
tap-wordpress-reviews --config config.json --discover | jq '.streams[] | select(.tap_stream_id=="reviews") | .schema.properties | keys'
```

### Check the schema for support threads
```bash
tap-wordpress-reviews --config config.json --discover | jq '.streams[] | select(.tap_stream_id=="support_threads") | .schema.properties | keys'
```

## 🎯 Sync Reviews Only

### Create a catalog with just reviews selected
```bash
tap-wordpress-reviews --config config.json --discover | jq '.streams[0] | .metadata[0].metadata.selected = true | {"streams": [.]}' > reviews_catalog.json
```

### Sync just reviews (see the data flow)
```bash
tap-wordpress-reviews --config config.json --catalog reviews_catalog.json | grep "^RECORD" | head -5 | jq .
```

### Count how many reviews you're getting
```bash
tap-wordpress-reviews --config config.json --catalog reviews_catalog.json | grep -c "^RECORD"
```

## 🆘 Sync Support Threads Only

### Create a catalog with just support threads selected
```bash
tap-wordpress-reviews --config config.json --discover | jq '.streams[1] | .metadata[0].metadata.selected = true | {"streams": [.]}' > support_catalog.json
```

### Sync support threads with different filters
```bash
echo '{"plugins": ["wordpress-seo"], "thread_filter": "unresolved"}' > config_unresolved.json
tap-wordpress-reviews --config config_unresolved.json --catalog support_catalog.json | grep "^RECORD" | head -3 | jq .
```

### Try active threads only
```bash
echo '{"plugins": ["wordpress-seo"], "thread_filter": "active"}' > config_active.json
tap-wordpress-reviews --config config_active.json --catalog support_catalog.json | grep "^RECORD" | head -3 | jq .
```

## 📊 Both Streams Together

### Create a catalog with both streams selected
```bash
tap-wordpress-reviews --config config.json --discover | jq '.streams[] | .metadata[0].metadata.selected = true' | jq -s '{"streams": .}' > both_catalog.json
```

### Run both and see what's happening
```bash
tap-wordpress-reviews --config config.json --catalog both_catalog.json 2>&1 | grep "^INFO"
```

### See records from both streams
```bash
tap-wordpress-reviews --config config.json --catalog both_catalog.json | grep "^RECORD" | jq -r .stream | sort | uniq -c
```

## 🔄 Incremental Sync with State

### First run - saves state
```bash
tap-wordpress-reviews --config config.json --catalog reviews_catalog.json | tee >(grep "^STATE" | tail -1 | jq . > state.json)
```

### See what's in the state
```bash
cat state.json | jq .
```

### Second run - only gets new data since last state
```bash
tap-wordpress-reviews --config config.json --catalog reviews_catalog.json --state state.json | grep "^RECORD" | wc -l
```

### Watch the state evolve during backfill
```bash
tap-wordpress-reviews --config config.json --catalog reviews_catalog.json | grep "^STATE" | jq '.bookmarks.reviews.backfill'
```

## 🎮 Fun Exploration Commands

### See reviews with 1-star ratings only
```bash
tap-wordpress-reviews --config config.json --catalog reviews_catalog.json | grep "^RECORD" | jq 'select(.record.rating == 1) | .record | {author, rating, date, text: .text[:100]}'
```

### Find reviews with the most comments
```bash
tap-wordpress-reviews --config config.json --catalog reviews_catalog.json | grep "^RECORD" | jq '.record | {path, comments: .comments | length}' | jq -s 'sort_by(.comments) | reverse | .[0:5]'
```

### See support threads marked as resolved
```bash
tap-wordpress-reviews --config config.json --catalog support_catalog.json | grep "^RECORD" | jq 'select(.record.status == "resolved") | .record.title'
```

### Find threads where plugin author responded
```bash
tap-wordpress-reviews --config config.json --catalog support_catalog.json | grep "^RECORD" | jq 'select(.record.plugin_author_response == true) | .record | {title, status}'
```

### Watch it work in real-time with less
```bash
tap-wordpress-reviews --config config.json --catalog both_catalog.json 2>&1 | less +F
```

## 📈 Multiple Plugins

### Track multiple plugins
```bash
echo '{"plugins": ["wordpress-seo", "akismet", "woocommerce"], "number": 10}' > multi_config.json
tap-wordpress-reviews --config multi_config.json --discover > multi_catalog.json
```

### See reviews from all plugins
```bash
tap-wordpress-reviews --config multi_config.json --catalog multi_catalog.json | grep "^RECORD" | jq -r '.record.path' | cut -d'/' -f4 | sort | uniq -c
```

## 🐛 Debug & Development

### See all the URLs being fetched (watch the scraping happen)
```bash
tap-wordpress-reviews --config config.json --catalog reviews_catalog.json 2>&1 | grep "Loading"
```

### Time how long it takes
```bash
time tap-wordpress-reviews --config config.json --catalog reviews_catalog.json | wc -l
```

### See just errors if something goes wrong
```bash
tap-wordpress-reviews --config config.json --catalog reviews_catalog.json 2>&1 >/dev/null | grep -E "(ERROR|CRITICAL|WARNING)"
```

### Dry run - see what would be synced without actually doing it
```bash
tap-wordpress-reviews --config config.json --discover | jq '.streams[] | {stream: .tap_stream_id, records: "would sync from wordpress.org"}'
```

## 💾 Save Output for Analysis

### Save all reviews to a file
```bash
tap-wordpress-reviews --config config.json --catalog reviews_catalog.json | grep "^RECORD" | jq .record > all_reviews.json
```

### Create CSV of reviews
```bash
tap-wordpress-reviews --config config.json --catalog reviews_catalog.json | grep "^RECORD" | jq -r '.record | [.date, .author, .rating, .title] | @csv' > reviews.csv
```

### Create a simple report
```bash
echo "=== WordPress Plugin Review Report ===" > report.txt
echo "Generated: $(date)" >> report.txt
echo "" >> report.txt
tap-wordpress-reviews --config config.json --catalog reviews_catalog.json | grep "^RECORD" | jq -r '.record.rating' | sort | uniq -c | awk '{print $2 " stars: " $1 " reviews"}' >> report.txt
```

## 🚀 Quick Start

**Remember:** Always activate the virtual environment first:
```bash
source test_venv/bin/activate
```

Then start with the discovery command to see what you get, and try syncing reviews for a small plugin to see the data structure!