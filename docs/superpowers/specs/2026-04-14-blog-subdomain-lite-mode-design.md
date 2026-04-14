# Secondary Blog Site — Lite Mode

**Date:** 2026-04-14  
**Status:** Approved

---

## Problem

Secondary blog sites — whether a subdomain (`blog.glasgowthaimassage.co.uk`) or a fully separate domain (`clientblog.co.uk`) — currently receive the full `seomachine.php` plugin including all 5 CPT registrations (`seo_service`, `seo_location`, `seo_pillar`, `seo_comp_alt`, `seo_problem`). These CPTs should never be used on a secondary blog site — content of those types lives exclusively on the main site and surfaces on the blog via the `[seo_hub]` shortcode cross-site fetch. Having the CPTs registered on the blog site creates risk: a future admin could accidentally publish service/location pages there, diluting main-site authority and creating duplicate content.

This applies equally to subdomains and separate domains. The plugin has no way to distinguish a subdomain from an unrelated URL — nor should it need to.

## Goal

When the plugin detects it is running on a secondary blog site, suppress all CPT registration while keeping the shortcode, SEO meta output, and admin metabox fully functional.

---

## Architecture

### Detection mechanism — `seo_hub_source` auto-detect

The plugin checks the `seo_hub_source` WordPress option at init time. If the option is non-empty, the site is a content consumer (blog subdomain) and enters lite mode. This piggybacks on the existing option that is already set during GTB onboarding — no extra setup step required.

```php
function seo_machine_is_secondary_blog(): bool {
    return !empty(get_option('seo_hub_source', ''));
}
```

**Edge case accepted:** if a future main site ever needed cross-site hub aggregation from another source, this would incorrectly activate lite mode. That scenario is hypothetical and can be addressed when it arises.

### What lite mode suppresses

- Registration of all 5 CPTs: `seo_service`, `seo_location`, `seo_pillar`, `seo_comp_alt`, `seo_problem`
- The "SEO Content" wp-admin menu group (contains only those CPTs)
- `seo_blog` CPT (already unused — blog posts use standard `post` type; suppressed for consistency)

### What lite mode keeps

| Feature | Kept | Reason |
|---------|------|--------|
| `[seo_hub]` shortcode | ✓ | Core display mechanism for main-site CPT content |
| SEO Machine metabox | ✓ | Meta title, meta description, focus keyword on standard `post` type |
| `<meta name="description">` output | ✓ | SEO function, applies to blog posts |
| Open Graph + Twitter Card tags | ✓ | SEO function, applies to blog posts |
| JSON-LD schema output | ✓ | SEO function, applies to blog posts |
| `seo_meta` REST field | ✓ | Still needed for `post` type meta read/write |

---

## Implementation

### 1. `wordpress/seomachine.php` — conditional CPT registration

Add `seo_machine_is_secondary_blog()` helper. Wrap the entire CPT registration block (currently the `init` action that registers all CPTs + the "SEO Content" menu group) in a conditional:

```php
add_action('init', function() {
    if (seo_machine_is_secondary_blog()) {
        return; // lite mode — skip all CPT registration
    }
    // ... existing CPT registration code
});
```

The shortcode registration, meta output hooks, and metabox registration are all separate action hooks — they remain unconditional.

### 2. `seomachine.php` — Settings UI label

Add a read-only notice in the Settings → General section (where `seo_hub_source` is set) indicating that lite mode is active when the field is populated. This makes the behaviour discoverable.

### 3. `/new-client` command — onboarding question

Add a question to the `/new-client` onboarding flow (after the WordPress credentials questions):

> **Q: Is this a secondary blog site that should pull service/location pages from a main site?**  
> *(This applies whether the blog is on a subdomain or a completely separate domain.)*  
> If yes, ask for the main site URL and run:  
> `wp option update seo_hub_source "https://main-site-url.com"`  
> This activates lite mode automatically — no CPTs registered, cross-site hub enabled.

The command should also note: secondary blog sites do not need `elementor-template.json` for service/location types (those page types don't exist on the blog site).

### 4. `clients/README.md` — document the pattern

Add a "Secondary blog sites" section explaining:
- Plugin is installed but CPTs are suppressed
- `seo_hub_source` is the activation mechanism — works for subdomains and separate domains equally
- Content types available: `blog` only (standard `post` type)
- Hub shortcode fetches service/location/etc from main site automatically

---

## Onboarding flow change (summary)

```
/new-client
  ...existing questions...
  Q: Is this a secondary blog site that pulls service/location pages from a main site? (yes/no)
    yes →
      Q: Main site URL? (subdomain or separate domain — doesn't matter)
      → wp option update seo_hub_source "<url>"
      → Note: lite mode active, no CPTs registered
      → Note: only "blog" content type available in batch runner
    no →
      → Standard full setup
```

---

## Verification

1. Set `seo_hub_source` on a test WordPress install → confirm CPTs absent from wp-admin menu
2. Clear `seo_hub_source` → confirm CPTs reappear (no plugin change, just option toggle)
3. Confirm `[seo_hub type="location"]` still renders on the secondary blog site
4. Confirm SEO Machine metabox still appears on standard `post` edit screen
5. Confirm `<meta name="description">` still outputs on blog post front end
6. Deploy updated plugin to GTB via GitHub Actions → verify GTB wp-admin shows no CPTs
7. Run `/new-client` for a secondary blog site and confirm the question appears at the right step
8. Verify the same setup works for a hypothetical non-subdomain URL in `seo_hub_source`
