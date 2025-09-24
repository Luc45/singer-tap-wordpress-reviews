# tap-wordpress-reviews

This is a [Singer](https://singer.io) tap that produces JSON-formatted data
following the [Singer
spec](https://github.com/singer-io/getting-started/blob/master/SPEC.md).

This tap:

- Pulls raw data from [WordPress Reviews](https://wordpress.org/plugins/wordpress-seo/#reviews)
- Extracts the following resources:
  - Reviews
- Outputs the schema for each resource
- Incrementally pulls data based on the input state


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
  "thread_filter": "all"
}
```

**Configuration parameters:**
- `plugins` (required): Array of WordPress plugin slugs to fetch data from
- `number` (optional, default: 30): Number of items to fetch per page
- `thread_filter` (optional, default: "all"): For support threads - can be "all", "active", or "unresolved"

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