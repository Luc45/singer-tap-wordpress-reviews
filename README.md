# tap-wordpress-reviews

This is a [Singer](https://singer.io) tap that produces JSON-formatted data
following the [Singer
spec](https://github.com/singer-io/getting-started/blob/master/SPEC.md).

This tap:

- Pulls raw data from WordPress.org plugin pages
- Extracts the following resources:
  - **Reviews**: User ratings and feedback for plugins
  - **Support Threads**: Support forum discussions including full conversation threads
- Outputs the schema for each resource
- Incrementally pulls data based on the input state

## Data Collection

### Reviews
Each review includes:
- Title and text content
- Author username
- Rating (1-5 stars)
- Date posted
- Plugin identifier

### Support Threads
Each support thread includes:
- Title and initial post content
- Author username
- Thread status (resolved/unresolved)
- Thread type (bug/question/feature_request/how_to)
- Reply count and participant count
- Plugin author response indicator
- Full comment thread with all replies
- Tags and metadata


### Step 1: Configure

Create a file called `config.json` in your working directory. You can copy from `config.json.example`:

```bash
cp config.json.example config.json
```

Or create it manually:

```json
{
  "plugins": ["wordpress-seo"],
  "number": 30,
  "support_threads": false,
  "thread_filter": "all"
}
```

**Configuration parameters:**
- `plugins` (required): Array of WordPress plugin slugs to fetch data from
- `number` (optional, default: 30): Number of items to fetch per plugin
- `support_threads` (optional, default: false): Set to `true` to also fetch support threads
- `thread_filter` (optional, default: "all"): For support threads - can be "all", "active", or "unresolved"

**Examples:**

Reviews only (default):
```json
{
  "plugins": ["woocommerce", "wordpress-seo"],
  "number": 100
}
```

Reviews and support threads:
```json
{
  "plugins": ["woocommerce", "wordpress-seo"],
  "number": 100,
  "support_threads": true,
  "thread_filter": "all"
}
```

Support threads only (unresolved):
```json
{
  "plugins": ["woocommerce"],
  "number": 50,
  "support_threads": true,
  "thread_filter": "unresolved"
}
```

### Step 2: Install and Run

Create a virtual Python environment for this tap. This tap requires Python 3.10 or later.
```
python -m venv singer-wp-reviews
singer-wp-reviews/bin/python -m pip install --upgrade pip
singer-wp-reviews/bin/pip install git+https://github.com/Yoast/singer-tap-wordpress-reviews.git
```

This tap can be tested by piping the data to a local JSON target. For example:

Create a virtual Python environment with `singer-json`
```
python -m venv singer-json
singer-json/bin/python -m pip install --upgrade pip
singer-json/bin/pip install target-json
```

Test the tap:

```bash
# Run discovery
singer-wp-reviews/bin/tap-wordpress-reviews --config config.json --discover

# Run sync to JSON target
singer-wp-reviews/bin/tap-wordpress-reviews --config config.json | singer-json/bin/target-json
```

Copyright &copy; 2021 Yoast