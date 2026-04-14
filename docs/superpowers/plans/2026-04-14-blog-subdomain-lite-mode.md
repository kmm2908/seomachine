# Secondary Blog Site Lite Mode — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** When `seomachine.php` detects it is running on a secondary blog site (detected via `seo_hub_source` option being set), suppress all CPT registration and the "SEO Content" wp-admin menu while keeping the shortcode, SEO meta output, and admin metabox fully functional.

**Architecture:** A single `seo_machine_is_secondary_blog()` helper function reads `seo_hub_source` at runtime. All CPT-related init hooks check this flag and return early if set. The `/new-client` onboarding command gains a new question that runs `wp option update seo_hub_source` when the site is a secondary blog.

**Tech Stack:** PHP 8.1 (WordPress MU plugin), Markdown (command + docs)

---

## Files

| File | Action | What changes |
|------|--------|--------------|
| `wordpress/seomachine.php` | Modify | Add helper function; wrap CPT registration, taxonomy, and admin menu in conditional; add lite mode notice to Settings UI; bump version to 3.2.0 |
| `.claude/commands/new-client.md` | Modify | Add Q16 (secondary blog?); add `seo_hub_source` WP-CLI step; update config.json template |
| `clients/README.md` | Modify | Add "Secondary blog sites" section documenting the pattern |

---

## Task 1: Add `seo_machine_is_secondary_blog()` and wrap CPT registration

**Files:**
- Modify: `wordpress/seomachine.php`

The function must be defined before any hook that calls it. Add it immediately after the `ABSPATH` guard (line 16), before the `SEO_MACHINE_POST_TYPES` constant.

- [ ] **Step 1: Add the helper function**

Open `wordpress/seomachine.php`. After line 15 (`exit;`) and before line 17 (`define('SEO_MACHINE_POST_TYPES'`), insert:

```php
/**
 * Returns true if this WordPress install is a secondary blog site
 * (subdomain or separate domain) that pulls CPT content from a main site.
 * Detection: seo_hub_source option is non-empty.
 * In lite mode: CPTs are suppressed; shortcode, meta output, and metabox remain active.
 */
function seo_machine_is_secondary_blog(): bool {
    return !empty(get_option('seo_hub_source', ''));
}
```

- [ ] **Step 2: Wrap the CPT registration block**

Find this block (lines 52–65):

```php
// ── Custom Post Types ────────────────────────────────────────────────────────
// Register on init if it hasn't fired yet, otherwise register immediately.

if (did_action('init')) {
    seo_machine_register_post_types();
} else {
    add_action('init', 'seo_machine_register_post_types', 1);
}

// Flush rewrite rules on activation so CPT permalinks work immediately.
register_activation_hook(__FILE__, function () {
    seo_machine_register_post_types();
    flush_rewrite_rules();
});
```

Replace with:

```php
// ── Custom Post Types ────────────────────────────────────────────────────────
// Register on init if it hasn't fired yet, otherwise register immediately.
// Skipped entirely on secondary blog sites (seo_hub_source is set).

if (!seo_machine_is_secondary_blog()) {
    if (did_action('init')) {
        seo_machine_register_post_types();
    } else {
        add_action('init', 'seo_machine_register_post_types', 1);
    }

    register_activation_hook(__FILE__, function () {
        seo_machine_register_post_types();
        flush_rewrite_rules();
    });
}
```

- [ ] **Step 3: Wrap the seo_blog taxonomy registration**

Find this block (lines 67–71):

```php
// Register built-in category taxonomy for seo_blog so blog posts can be
// assigned to WordPress categories (Thai Massage, Stay Healthy, etc.)
add_action('init', function() {
    register_taxonomy_for_object_type('category', 'seo_blog');
}, 5);
```

Replace with:

```php
// Register built-in category taxonomy for seo_blog so blog posts can be
// assigned to WordPress categories (Thai Massage, Stay Healthy, etc.)
// Not needed on secondary blog sites — seo_blog CPT is suppressed there.
if (!seo_machine_is_secondary_blog()) {
    add_action('init', function() {
        register_taxonomy_for_object_type('category', 'seo_blog');
    }, 5);
}
```

- [ ] **Step 4: Wrap the "SEO Content" admin menu**

Find this block (lines 74–85):

```php
// Parent admin menu — redirects to Services list
add_action('admin_menu', function() {
    add_menu_page(
        'SEO Content',
        'SEO Content',
        'edit_posts',
        'seo-content',
        fn() => wp_redirect(admin_url('edit.php?post_type=seo_service')),
        'dashicons-text-page',
        20
    );
});
```

Replace with:

```php
// Parent admin menu — redirects to Services list.
// Hidden on secondary blog sites where no CPTs are registered.
if (!seo_machine_is_secondary_blog()) {
    add_action('admin_menu', function() {
        add_menu_page(
            'SEO Content',
            'SEO Content',
            'edit_posts',
            'seo-content',
            fn() => wp_redirect(admin_url('edit.php?post_type=seo_service')),
            'dashicons-text-page',
            20
        );
    });
}
```

- [ ] **Step 5: Bump the plugin version**

Find line 6:
```php
 * Version: 3.1.5
```

Replace with:
```php
 * Version: 3.2.0
```

- [ ] **Step 6: Commit**

```bash
cd "/Volumes/Ext Data/VSC Projects/CC Dev/seomachine"
git add wordpress/seomachine.php
git commit -m "feat(plugin): lite mode for secondary blog sites — suppress CPTs when seo_hub_source is set (v3.2.0)"
```

---

## Task 2: Add lite mode notice to Settings → General UI

**Files:**
- Modify: `wordpress/seomachine.php`

The existing `seo_hub_source` settings field (lines 526–541) describes the field but doesn't tell an admin that setting it has the additional effect of suppressing CPTs. Add a conditional notice below the existing description.

- [ ] **Step 1: Update the settings field callback**

Find this block inside the `add_settings_field` callback:

```php
        function() {
            $value = get_option('seo_hub_source', '');
            echo '<input type="url" name="seo_hub_source" id="seo_hub_source" '
               . 'value="' . esc_attr($value) . '" class="regular-text" '
               . 'placeholder="https://main-site.com" />';
            echo '<p class="description">For blog subdomains: enter the main site URL so the '
               . '<code>[seo_hub]</code> shortcode can pull location/service links from it. '
               . 'Leave blank on main sites.</p>';
        },
```

Replace with:

```php
        function() {
            $value = get_option('seo_hub_source', '');
            echo '<input type="url" name="seo_hub_source" id="seo_hub_source" '
               . 'value="' . esc_attr($value) . '" class="regular-text" '
               . 'placeholder="https://main-site.com" />';
            echo '<p class="description">For secondary blog sites: enter the main site URL so the '
               . '<code>[seo_hub]</code> shortcode can pull location/service links from it. '
               . 'Leave blank on main sites. Works for subdomains and separate domains.</p>';
            if (!empty($value)) {
                echo '<p class="description" style="color:#2271b1;font-weight:600;">'
                   . '&#9432; SEO Machine lite mode is active — service, location, and other CPTs '
                   . 'are suppressed on this site. Blog posts and SEO meta functions remain available.</p>';
            }
        },
```

- [ ] **Step 2: Commit**

```bash
cd "/Volumes/Ext Data/VSC Projects/CC Dev/seomachine"
git add wordpress/seomachine.php
git commit -m "feat(plugin): show lite mode notice in Settings → General when seo_hub_source is set"
```

---

## Task 3: Update `/new-client` command with secondary blog question

**Files:**
- Modify: `.claude/commands/new-client.md`

Add Q16 after the existing Q15 (WordPress app password). When answered yes, the command runs `wp option update seo_hub_source` and notes the lite mode implications. Also update the config.json template to include a `site_type` field.

- [ ] **Step 1: Add Q16 to the questions list**

Find the end of the questions list (after Q15):

```
15. **WordPress application password** — (e.g. "Wtg0 jK0T 3bak 7XRg Mg1P o7io") — enter "skip" if skipping WordPress
```

Add after it:

```
16. **Secondary blog site?** — Is this a secondary blog site that should pull service/location pages from a main site? This applies whether the blog is on a subdomain (e.g. `blog.example.com`) or a completely separate domain (e.g. `exampleblog.com`). Answer yes/no.
    - If **yes**: ask "What is the main site URL?" then note it — `seo_hub_source` will be set in Step 3.
    - If **no**: standard full setup, all CPTs registered.
```

- [ ] **Step 2: Update the config.json template in Step 3**

Find the `wordpress` block in the config.json template:

```json
  "wordpress": {
    "url": "[answer to Q13, or null]",
    "username": "[answer to Q14, or null]",
    "app_password": "[answer to Q15, or null]",
    "default_post_type": "post",
    "default_status": "draft"
  }
```

Replace with:

```json
  "wordpress": {
    "url": "[answer to Q13, or null]",
    "username": "[answer to Q14, or null]",
    "app_password": "[answer to Q15, or null]",
    "default_post_type": "post",
    "default_status": "draft"
  },
  "site_type": "[\"secondary_blog\" if Q16=yes, else \"main\"]",
  "seo_hub_source": "[main site URL if Q16=yes, else omit this key]"
```

Note: `site_type` and `seo_hub_source` are documentation fields in config.json for human reference. The actual runtime detection happens via the WordPress option set by WP-CLI in the next step — the batch runner does not read these fields.

- [ ] **Step 3: Add WP-CLI setup step after Step 3 (Create Folder and Config)**

Find "### Step 4: Create Stub Context Files" and insert a new step before it:

```markdown
### Step 3b: Configure secondary blog site (if Q16 = yes)

If the client answered yes to Q16, run:

```bash
wp option update seo_hub_source "https://[main-site-url]" --url=[client-wp-url] --ssh=[ssh-host]
```

Or if WordPress credentials are available locally via WP-CLI, run without SSH.

This activates lite mode automatically — no CPTs will be registered on this WordPress install. Verify by checking Settings → General in wp-admin for the lite mode notice.

**What this means for this client:**
- Only the `blog` content type is available in the batch runner
- No `elementor-template.json` needed for service/location types (those page types don't exist here)
- The `[seo_hub]` shortcode fetches location/service links from the main site automatically
```

- [ ] **Step 4: Update the completion summary to note secondary blog status**

Find the "Next steps" block in Step 6:

```
Next steps:
  1. Fill in the TODO sections in the remaining context files
  2. Add [ABBREVIATION] rows to the Google Sheet to start generating content
  3. Run /research [topic] to start building keyword strategy
  4. Run python3 src/geo_batch_runner.py to generate content when ready
```

Add a conditional note after step 4:

```
  [If secondary blog] Note: only "blog" content type is available. Service/location pages
  are served from [main site URL] via [seo_hub] shortcode — do not publish them here.
```

- [ ] **Step 5: Commit**

```bash
cd "/Volumes/Ext Data/VSC Projects/CC Dev/seomachine"
git add .claude/commands/new-client.md
git commit -m "feat(onboarding): add secondary blog site question to /new-client flow"
```

---

## Task 4: Document secondary blog pattern in clients/README.md

**Files:**
- Modify: `clients/README.md`

- [ ] **Step 1: Read the current README to find the right insertion point**

```bash
grep -n "## " "clients/README.md" | head -20
```

Find a logical place — after the existing client structure section and before the schema docs, or at the end of the setup section.

- [ ] **Step 2: Add the secondary blog sites section**

Insert the following section at the appropriate location:

```markdown
## Secondary Blog Sites

Some clients have a secondary blog site alongside their main site — either as a subdomain (`blog.example.com`) or a completely separate domain (`exampleblog.com`). The SEO Machine plugin handles these differently to prevent accidental content duplication.

### How it works

Setting the `seo_hub_source` WordPress option on the secondary blog site activates **lite mode**:

```bash
wp option update seo_hub_source "https://main-site-url.com"
```

In lite mode, the plugin:
- **Suppresses** all CPT registration (`seo_service`, `seo_location`, `seo_pillar`, `seo_comp_alt`, `seo_problem`, `seo_blog`) — these post types will not appear in wp-admin
- **Keeps** the `[seo_hub]` shortcode, SEO meta output, Open Graph tags, JSON-LD schema, and the SEO Machine metabox on standard `post` type

### Available content types

Secondary blog sites support `blog` content type only (standard WordPress `post` type). The batch runner and scheduled publisher will generate and publish blog posts as normal.

Service, location, pillar, comp-alt, and problem pages are **not published to the secondary blog site**. They live on the main site and surface on the blog via the `[seo_hub]` shortcode.

### Hub shortcode

Place `[seo_hub type="location"]` in an Elementor Shortcode widget to display a live list of location pages from the main site. Works for all types: `location`, `service`, `pillar`, `topical`, `comp_alt`, `problem`. Results are cached for 12 hours.

Cache bust if needed:
```bash
wp transient delete seo_hub_cache_location
```

### Existing secondary blog clients

| Client | Abbr | Main site | seo_hub_source set? |
|--------|------|-----------|---------------------|
| Glasgow Thai Massage Blog | GTB | glasgowthaimassage.co.uk | ✓ (set in session 14) |
| Thai Massage Greenock Blog | TMB | thaimassagegreenock.co.uk | pending onboarding |
```

- [ ] **Step 3: Commit**

```bash
cd "/Volumes/Ext Data/VSC Projects/CC Dev/seomachine"
git add clients/README.md
git commit -m "docs: document secondary blog site lite mode pattern in clients/README.md"
```

---

## Task 5: Deploy and verify on GTB

**Files:** None — deployment via GitHub Actions on push to main.

GTB (`blog.glasgowthaimassage.co.uk`) already has `seo_hub_source` set. After the plugin update is deployed, CPTs should disappear from its wp-admin automatically.

- [ ] **Step 1: Push to main to trigger auto-deploy**

The GitHub Actions workflow (`deploy-plugin.yml`) deploys `wordpress/seomachine.php` to all 5 sites on every push to main that touches the file. The commits from Tasks 1 and 2 already touch the file — just confirm they've been pushed:

```bash
git log --oneline origin/main..HEAD
```

If there are unpushed commits, push:

```bash
git push origin main
```

- [ ] **Step 2: Confirm deployment completed**

Check GitHub Actions at the repo's Actions tab. Wait for all three deploy jobs (GTM/GTB, SDY/staging2, TMG/TMB) to show green.

- [ ] **Step 3: Verify GTB wp-admin — CPTs absent**

Log in to `blog.glasgowthaimassage.co.uk/wp-admin`. Confirm:
- No "SEO Content" menu item in the left sidebar
- No `seo_service`, `seo_location`, `seo_pillar`, `seo_comp_alt`, `seo_problem` post types visible anywhere

- [ ] **Step 4: Verify lite mode notice in Settings → General**

Navigate to Settings → General on GTB wp-admin. Confirm:
- "SEO Hub Source URL" field shows `https://glasgowthaimassage.co.uk`
- Blue notice reads "SEO Machine lite mode is active — service, location, and other CPTs are suppressed on this site."

- [ ] **Step 5: Verify shortcode still works on GTB**

Open a page on GTB that uses `[seo_hub type="location"]`. Confirm the location links from GTM still render correctly.

- [ ] **Step 6: Verify SEO Machine metabox still present on GTB blog posts**

Edit any standard blog post on GTB wp-admin. Confirm the SEO Machine metabox (meta title, meta description, focus keyword) is still visible in the sidebar.

- [ ] **Step 7: Verify GTM is unaffected**

Log in to `glasgowthaimassage.co.uk/wp-admin`. Confirm:
- "SEO Content" menu is still present
- All CPTs are still registered and accessible

- [ ] **Step 8: Update STATUS.md**

Add to the "What's Built and Working" section:

```markdown
### Secondary blog site lite mode (session 45)
- [x] `seo_machine_is_secondary_blog()` — detects secondary blog via `seo_hub_source` option
- [x] All 6 CPTs + "SEO Content" menu suppressed in lite mode — no accidental content creation on blog sites
- [x] seo_blog taxonomy registration also suppressed (seo_blog CPT doesn't exist in lite mode)
- [x] Lite mode notice in Settings → General — visible when seo_hub_source is set
- [x] `/new-client` Q16 — asks if secondary blog; runs `wp option update seo_hub_source` if yes
- [x] `clients/README.md` — secondary blog sites section added with setup instructions
- [x] Deployed to GTB — CPTs confirmed absent from wp-admin
```

- [ ] **Step 9: Commit STATUS.md**

```bash
cd "/Volumes/Ext Data/VSC Projects/CC Dev/seomachine"
git add STATUS.md
git commit -m "docs(status): secondary blog lite mode complete and verified on GTB"
```
