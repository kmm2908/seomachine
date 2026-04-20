<?php
/**
 * Plugin Name: SEO Machine
 * Description: Registers SEO content post types and exposes SEO meta fields via REST API. No Yoast dependency.
 * Version: 3.4.5
 * Author: SEO Machine
 *
 * Installation:
 * 1. Upload this file to: wp-content/mu-plugins/seo-machine-yoast-rest.php
 * 2. That's it - mu-plugins are automatically activated
 */

if (!defined('ABSPATH')) {
    exit;
}

/**
 * Returns true if this WordPress install is a secondary blog site
 * (subdomain or separate domain) that pulls CPT content from a main site.
 * Detection: seo_hub_source option is non-empty.
 * In lite mode: CPTs are suppressed; shortcode, meta output, and metabox remain active.
 */
function seo_machine_is_secondary_blog(): bool {
    return !empty(get_option('seo_hub_source', ''));
}

define('SEO_MACHINE_POST_TYPES', [
    'seo_service'   => ['Services',                 'Service',               'seo_service'],
    'seo_location'  => ['Locations',                'Location',              'seo_location'],
    'seo_pillar'    => ['Pillar Pages',             'Pillar Page',           'seo_pillar'],
    'seo_topical'   => ['Topical Articles',         'Topical Article',       'seo_topical'],
    'seo_blog'      => ['Blog Posts',               'Blog Post',             'seo_blog'],
    'seo_comp_alt'  => ['Competitor Alternatives',  'Competitor Alternative','seo_comp_alt'],
    'seo_problem'   => ['Problem Pages',            'Problem Page',          'seo_problem'],
]);

// ── CPT registration helper ───────────────────────────────────────────────────

function seo_machine_register_post_types() {
    foreach (SEO_MACHINE_POST_TYPES as $slug => [$plural, $singular, $rest_base]) {
        register_post_type($slug, [
            'labels'       => [
                'name'          => $plural,
                'singular_name' => $singular,
                'add_new_item'  => "Add New $singular",
                'edit_item'     => "Edit $singular",
                'view_item'     => "View $singular",
                'search_items'  => "Search $plural",
            ],
            'public'             => true,
            'show_in_rest'       => true,
            'rest_base'          => $rest_base,
            'show_in_menu'       => 'seo-content',
            'show_in_nav_menus'  => true,
            'supports'           => ['title', 'editor', 'thumbnail', 'excerpt', 'custom-fields'],
            'rewrite'            => ['slug' => str_replace('_', '-', str_replace('seo_', '', $slug))],
            'has_archive'        => false,
        ]);
    }
}

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

// Register built-in category taxonomy for seo_blog so blog posts can be
// assigned to WordPress categories (Thai Massage, Stay Healthy, etc.)
// Not needed on secondary blog sites — seo_blog CPT is suppressed there.
if (!seo_machine_is_secondary_blog()) {
    add_action('init', function() {
        register_taxonomy_for_object_type('category', 'seo_blog');
    }, 5);
}


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

// ── SEO Meta Fields (no Yoast dependency) ───────────────────────────────────

add_action('init', function() {
    $all_types = array_merge(['post', 'page'], array_keys(SEO_MACHINE_POST_TYPES));
    $meta_keys = [
        '_yoast_wpseo_focuskw'       => 'SEO Focus Keyphrase',
        '_yoast_wpseo_title'         => 'SEO Title',
        '_yoast_wpseo_metadesc'      => 'SEO Meta Description',
        '_seo_machine_focus_keyword' => 'SEO Machine Focus Keyword',
    ];

    foreach ($all_types as $type) {
        foreach ($meta_keys as $key => $description) {
            register_post_meta($type, $key, [
                'show_in_rest'  => true,
                'single'        => true,
                'type'          => 'string',
                'description'   => $description,
                'auth_callback' => fn() => current_user_can('edit_posts'),
            ]);
        }
    }
});

// ── seo_meta REST field (Yoast-compatible keys, no Yoast requirement) ────────

add_action('rest_api_init', function() {
    $all_types = array_merge(['post', 'page'], array_keys(SEO_MACHINE_POST_TYPES));

    foreach ($all_types as $type) {
        register_rest_field($type, 'seo_meta', [
            'get_callback' => function($post) {
                return [
                    'focus_keyphrase'  => get_post_meta($post['id'], '_yoast_wpseo_focuskw', true),
                    'seo_title'        => get_post_meta($post['id'], '_yoast_wpseo_title', true),
                    'meta_description' => get_post_meta($post['id'], '_yoast_wpseo_metadesc', true),
                ];
            },
            'update_callback' => function($value, $post) {
                if (!current_user_can('edit_post', $post->ID)) {
                    return new WP_Error('rest_forbidden', 'Permission denied.', ['status' => 403]);
                }
                if (isset($value['focus_keyphrase'])) {
                    update_post_meta($post->ID, '_yoast_wpseo_focuskw', sanitize_text_field($value['focus_keyphrase']));
                }
                if (isset($value['seo_title'])) {
                    update_post_meta($post->ID, '_yoast_wpseo_title', sanitize_text_field($value['seo_title']));
                }
                if (isset($value['meta_description'])) {
                    update_post_meta($post->ID, '_yoast_wpseo_metadesc', sanitize_text_field($value['meta_description']));
                }
                return true;
            },
            'schema' => [
                'type'       => 'object',
                'properties' => [
                    'focus_keyphrase'  => ['type' => 'string'],
                    'seo_title'        => ['type' => 'string'],
                    'meta_description' => ['type' => 'string'],
                ],
            ],
        ]);
    }
});

// ── Audit API endpoint ────────────────────────────────────────────────────────
// GET /wp-json/seomachine/v1/audit — requires authentication (app password).
// Returns post counts for all SEO Machine types in a single call, bypassing
// any per-route bot-protection that may block rapid sequential requests.

add_action('rest_api_init', function() {
    register_rest_route('seomachine/v1', '/audit', [
        'methods'             => 'GET',
        'callback'            => function(WP_REST_Request $request) {
            $types = array_merge(['post', 'page'], array_keys(SEO_MACHINE_POST_TYPES));
            $counts = [];
            foreach ($types as $type) {
                $q = new WP_Query([
                    'post_type'      => $type,
                    'post_status'    => 'publish',
                    'posts_per_page' => 1,
                    'fields'         => 'ids',
                    'no_found_rows'  => false,
                ]);
                $counts[$type] = (int) $q->found_posts;
            }
            return rest_ensure_response([
                'post_counts'    => $counts,
                'plugin_version' => '3.0.0',
                'site_url'       => get_site_url(),
            ]);
        },
        'permission_callback' => function() {
            return current_user_can('edit_posts');
        },
    ]);
});

// ── Hub cache-bust REST endpoint ─────────────────────────────────────────────
//
// Consumer sites (e.g. GTB) expose this endpoint so source sites (e.g. GTM)
// can clear the seo_hub transient cache immediately after a CPT post changes.
// Caller must supply source_url matching this site's seo_hub_source option.

add_action('rest_api_init', function() {
    register_rest_route('seomachine/v1', '/bust-hub-cache', [
        'methods'             => 'POST',
        'permission_callback' => '__return_true',
        'callback'            => function(WP_REST_Request $request) {
            $source   = get_option('seo_hub_source', '');
            $provided = $request->get_param('source_url') ?? '';
            if (empty($source) || untrailingslashit($provided) !== untrailingslashit($source)) {
                return new WP_Error('forbidden', 'Forbidden', ['status' => 403]);
            }
            $type = sanitize_text_field($request->get_param('type') ?? '');
            $all  = ['location', 'service', 'pillar', 'topical', 'comp-alt', 'problem'];
            foreach ($type ? [$type] : $all as $t) {
                delete_transient('seo_hub_cache_' . $t);
            }
            return ['busted' => true, 'type' => $type ?: 'all'];
        },
    ]);
});

// ── Notify hub consumers on CPT post status change ───────────────────────────
//
// Source sites (e.g. GTM) ping each URL listed in seo_hub_consumers whenever
// a CPT post is published, unpublished, trashed, or restored. Non-blocking.

add_action('transition_post_status', function($new_status, $old_status, WP_Post $post) {
    if ($new_status === $old_status) return;
    $cpt_map = [
        'seo_location' => 'location', 'seo_service'  => 'service',
        'seo_pillar'   => 'pillar',   'seo_topical'  => 'topical',
        'seo_comp_alt' => 'comp-alt', 'seo_problem'  => 'problem',
    ];
    if (!isset($cpt_map[$post->post_type])) return;
    $raw       = get_option('seo_hub_consumers', '');
    $consumers = array_filter(array_map('trim', explode("\n", $raw)));
    if (empty($consumers)) return;
    $type = $cpt_map[$post->post_type];
    foreach ($consumers as $url) {
        wp_remote_post(trailingslashit($url) . 'wp-json/seomachine/v1/bust-hub-cache', [
            'body'     => ['type' => $type, 'source_url' => home_url()],
            'blocking' => false,
            'timeout'  => 5,
        ]);
    }
}, 10, 3);

// ── SEO Machine Admin Panel ──────────────────────────────────────────────────
// TODO: add brand styling before public/commercial release (plain WP metabox for now)

add_action('add_meta_boxes', function() {
    $types = array_merge(['post', 'page'], array_keys(SEO_MACHINE_POST_TYPES));
    foreach ($types as $type) {
        add_meta_box(
            'seo_machine_panel',
            'SEO Machine',
            'seo_machine_panel_render',
            $type,
            'side',
            'high'
        );
    }
});

function seo_machine_panel_render(WP_Post $post): void {
    wp_nonce_field('seo_machine_panel_save', 'seo_machine_panel_nonce');
    $keyword  = get_post_meta($post->ID, '_seo_machine_focus_keyword', true);
    $title    = get_post_meta($post->ID, '_yoast_wpseo_title', true);
    $metadesc = get_post_meta($post->ID, '_yoast_wpseo_metadesc', true);
    ?>
    <p>
        <label for="seo_machine_focus_keyword"><strong>Target Keyword</strong></label><br>
        <input
            type="text"
            id="seo_machine_focus_keyword"
            name="seo_machine_focus_keyword"
            value="<?php echo esc_attr($keyword); ?>"
            style="width:100%;margin-top:4px;"
        >
    </p>
    <p>
        <label for="seo_machine_meta_title"><strong>SEO Title</strong></label><br>
        <input
            type="text"
            id="seo_machine_meta_title"
            name="seo_machine_meta_title"
            value="<?php echo esc_attr($title); ?>"
            style="width:100%;margin-top:4px;"
            placeholder="Leave blank to use post title"
        >
    </p>
    <p>
        <label for="seo_machine_metadesc"><strong>Meta Description</strong></label><br>
        <textarea
            id="seo_machine_metadesc"
            name="seo_machine_metadesc"
            rows="3"
            style="width:100%;margin-top:4px;resize:vertical;"
            placeholder="120–160 characters"
        ><?php echo esc_textarea($metadesc); ?></textarea>
        <span id="seo_machine_metadesc_count" style="font-size:11px;color:#646970;">
            <?php echo strlen($metadesc); ?> chars
        </span>
    </p>
    <script>
    (function() {
        var ta = document.getElementById('seo_machine_metadesc');
        var ct = document.getElementById('seo_machine_metadesc_count');
        if (ta && ct) {
            ta.addEventListener('input', function() {
                var n = ta.value.length;
                ct.textContent = n + ' chars';
                ct.style.color = (n >= 120 && n <= 160) ? '#00a32a' : (n > 160 ? '#d63638' : '#646970');
            });
        }
    })();
    </script>
    <?php
}

add_action('save_post', function(int $post_id): void {
    if (
        !isset($_POST['seo_machine_panel_nonce']) ||
        !wp_verify_nonce($_POST['seo_machine_panel_nonce'], 'seo_machine_panel_save') ||
        defined('DOING_AUTOSAVE') && DOING_AUTOSAVE ||
        !current_user_can('edit_post', $post_id)
    ) {
        return;
    }

    if (isset($_POST['seo_machine_focus_keyword'])) {
        update_post_meta(
            $post_id,
            '_seo_machine_focus_keyword',
            sanitize_text_field($_POST['seo_machine_focus_keyword'])
        );
    }
    if (isset($_POST['seo_machine_meta_title'])) {
        update_post_meta(
            $post_id,
            '_yoast_wpseo_title',
            sanitize_text_field($_POST['seo_machine_meta_title'])
        );
    }
    if (isset($_POST['seo_machine_metadesc'])) {
        update_post_meta(
            $post_id,
            '_yoast_wpseo_metadesc',
            sanitize_textarea_field($_POST['seo_machine_metadesc'])
        );
    }
});

// ── SEO head output ──────────────────────────────────────────────────────────
// Outputs canonical, meta description, robots, Open Graph, and Twitter Card
// tags from SEO Machine meta fields on all singular pages (CPTs, pages, posts).
// Also overrides <title> when a custom SEO title is set.

// Allow Google to display large images from our pages in search results.
add_filter('wp_robots', 'wp_robots_max_image_preview_large');

add_action('wp_head', function(): void {
    if (!is_singular()) {
        return;
    }

    // We own canonical and description output — remove WordPress core and Hello Elementor fallbacks.
    remove_action('wp_head', 'rel_canonical', 10);
    remove_action('wp_head', 'hello_elementor_add_description_meta_tag', 10);

    $post_id    = get_queried_object_id();
    $meta_desc  = get_post_meta($post_id, '_yoast_wpseo_metadesc', true);
    $meta_title = get_post_meta($post_id, '_yoast_wpseo_title', true);
    $thumb_url  = get_the_post_thumbnail_url($post_id, 'large') ?: '';
    $post_url   = get_permalink($post_id);
    $site_name  = get_bloginfo('name');
    $post_type  = get_post_type($post_id);
    $title_tag  = $meta_title ?: get_the_title($post_id);

    echo '<link rel="canonical" href="' . esc_url($post_url) . '">' . "\n";

    if ($meta_desc) {
        add_filter('wpseo_metadesc', '__return_empty_string', 99);
        echo '<meta name="description" content="' . esc_attr($meta_desc) . '">' . "\n";
    }

    $og_type = in_array($post_type, ['post', 'seo_blog', 'seo_topical'], true) ? 'article' : 'website';
    echo '<meta property="og:type" content="' . esc_attr($og_type) . '">' . "\n";
    echo '<meta property="og:title" content="' . esc_attr($title_tag) . '">' . "\n";
    echo '<meta property="og:url" content="' . esc_url($post_url) . '">' . "\n";
    echo '<meta property="og:site_name" content="' . esc_attr($site_name) . '">' . "\n";
    if ($meta_desc) {
        echo '<meta property="og:description" content="' . esc_attr($meta_desc) . '">' . "\n";
    }
    if ($thumb_url) {
        echo '<meta property="og:image" content="' . esc_url($thumb_url) . '">' . "\n";
    }

    $card = $thumb_url ? 'summary_large_image' : 'summary';
    echo '<meta name="twitter:card" content="' . esc_attr($card) . '">' . "\n";
    echo '<meta name="twitter:title" content="' . esc_attr($title_tag) . '">' . "\n";
    if ($meta_desc) {
        echo '<meta name="twitter:description" content="' . esc_attr($meta_desc) . '">' . "\n";
    }
    if ($thumb_url) {
        echo '<meta name="twitter:image" content="' . esc_url($thumb_url) . '">' . "\n";
    }
}, 1);

// ── Sitewide LocalBusiness JSON-LD ───────────────────────────────────────────
// Outputs a LocalBusiness schema block on the front page and all singular pages.
// Populated from WP options set per-site via WP-CLI (see below).
// Only outputs if seo_machine_biz_name is set — opt-in per install.
//
// Set options via WP-CLI:
//   wp option update seo_machine_biz_name      "Business Name"
//   wp option update seo_machine_biz_phone     "0141 000 0000"
//   wp option update seo_machine_biz_street    "Floor 1, 93 Hope Street"
//   wp option update seo_machine_biz_locality  "Glasgow"
//   wp option update seo_machine_biz_postcode  "G2 6LD"
//   wp option update seo_machine_biz_country   "GB"
//   wp option update seo_machine_biz_schema_type "MassageTherapist"
//   wp option update seo_machine_opening_hours '[{"@type":"OpeningHoursSpecification","dayOfWeek":["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"],"opens":"10:00","closes":"20:00"}]'

add_action('wp_head', function(): void {
    if (!is_front_page() && !is_singular()) {
        return;
    }

    $name = get_option('seo_machine_biz_name', '');
    if (!$name) {
        return;
    }

    $schema = [
        '@context' => 'https://schema.org',
        '@type'    => get_option('seo_machine_biz_schema_type', 'LocalBusiness'),
        'name'     => $name,
        'url'      => home_url('/'),
    ];

    $phone = get_option('seo_machine_biz_phone', '');
    if ($phone) {
        $schema['telephone'] = $phone;
    }

    $street   = get_option('seo_machine_biz_street', '');
    $locality = get_option('seo_machine_biz_locality', '');
    $postcode = get_option('seo_machine_biz_postcode', '');
    $country  = get_option('seo_machine_biz_country', 'GB');
    if ($street || $locality || $postcode) {
        $schema['address'] = array_filter([
            '@type'           => 'PostalAddress',
            'streetAddress'   => $street,
            'addressLocality' => $locality,
            'postalCode'      => $postcode,
            'addressCountry'  => $country,
        ]);
    }

    $hours_json = get_option('seo_machine_opening_hours', '');
    if ($hours_json) {
        $hours = json_decode($hours_json, true);
        if (is_array($hours)) {
            $schema['openingHoursSpecification'] = $hours;
        }
    }

    echo '<script type="application/ld+json">' . "\n"
        . wp_json_encode($schema, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT)
        . "\n</script>\n";
}, 5);

// Override <title> when a custom SEO title is stored.
add_filter('document_title_parts', function(array $title): array {
    if (!is_singular()) {
        return $title;
    }
    $custom = get_post_meta(get_queried_object_id(), '_yoast_wpseo_title', true);
    if ($custom) {
        $title['title'] = $custom;
        unset($title['site'], $title['tagline']);
    }
    return $title;
});

// ── Hub page shortcode ───────────────────────────────────────────────────────
//
// Usage: [seo_hub type="location"]
//        [seo_hub type="service" source="https://example.com"]
//
// Place in an Elementor Shortcode widget. Renders a <ul> of all published posts
// of that type, sorted A–Z.
//
// On blog subdomains: set wp_option 'seo_hub_source' to the main site URL.
// The shortcode will fetch posts from the main site via REST API (no auth needed)
// and cache results for 12 hours. The 'blog' type always queries locally.
//
// Cache bust: wp transient delete seo_hub_cache_location

add_shortcode('seo_hub', function($atts) {
    $atts = shortcode_atts(['type' => 'location', 'source' => ''], $atts, 'seo_hub');

    $type_map = [
        'location' => 'seo_location',
        'service'  => 'seo_service',
        'pillar'   => 'seo_pillar',
        'topical'  => 'seo_topical',
        'blog'     => 'post',
        'comp-alt' => 'seo_comp_alt',
        'problem'  => 'seo_problem',
    ];

    $type      = $atts['type'];
    $post_type = $type_map[$type] ?? 'seo_location';
    $source    = $atts['source'] ?: get_option('seo_hub_source', '');

    // Remote fetch: source is set and type is not 'blog' (blogs live locally)
    if ($source && $type !== 'blog') {
        return seo_hub_remote_fetch($source, $type, $post_type);
    }

    // Local query (default behaviour)
    $posts = get_posts([
        'post_type'      => $post_type,
        'post_status'    => 'publish',
        'posts_per_page' => -1,
        'orderby'        => 'title',
        'order'          => 'ASC',
    ]);

    if (empty($posts)) {
        return '';
    }

    $items = array_map(function($p) {
        $text = wp_trim_words($p->post_title, 7, '');
        return '<li><a href="' . esc_url(get_permalink($p)) . '">' . esc_html($text) . '</a></li>';
    }, $posts);

    if ($type === 'problem') {
        return seo_hub_problem_grid($items);
    }

    // Wrap items in h3 for standard hub types
    $items = array_map(fn($li) => str_replace(['<li>', '</li>'], ['<li><h3>', '</h3></li>'], $li), $items);
    return '<ul class="seo-hub-links">' . implode('', $items) . '</ul>';
});

/**
 * Fetch hub links from a remote WordPress site via REST API.
 * Results are cached in a transient for 12 hours.
 */
function seo_hub_remote_fetch(string $source, string $type, string $rest_base): string {
    $cache_key = 'seo_hub_cache_' . $type;
    $cached    = get_transient($cache_key);

    if ($cached !== false) {
        return $cached;
    }

    $source = untrailingslashit($source);
    $all_posts = [];
    $page = 1;

    do {
        $url = add_query_arg([
            'per_page' => 100,
            'page'     => $page,
            'orderby'  => 'title',
            'order'    => 'asc',
            '_fields'  => 'id,title,excerpt,link',
            'status'   => 'publish',
        ], "{$source}/wp-json/wp/v2/{$rest_base}");

        $response = wp_remote_get($url, ['timeout' => 15]);

        if (is_wp_error($response) || wp_remote_retrieve_response_code($response) !== 200) {
            break;
        }

        $body = json_decode(wp_remote_retrieve_body($response), true);
        if (!is_array($body) || empty($body)) {
            break;
        }

        $all_posts   = array_merge($all_posts, $body);
        $total_pages = (int) wp_remote_retrieve_header($response, 'x-wp-totalpages');
        $page++;
    } while ($page <= $total_pages);

    if (empty($all_posts)) {
        set_transient($cache_key, '', 12 * HOUR_IN_SECONDS);
        return '';
    }

    $items = array_map(function($item) {
        $link  = esc_url($item['link'] ?? '');
        $title = wp_strip_all_tags($item['title']['rendered'] ?? '');
        $text  = esc_html(wp_trim_words($title, 7, ''));
        return "<li><a href=\"{$link}\">{$text}</a></li>";
    }, $all_posts);

    if ($type === 'problem') {
        $html = seo_hub_problem_grid($items);
    } else {
        $items = array_map(fn($li) => str_replace(['<li>', '</li>'], ['<li><h3>', '</h3></li>'], $li), $items);
        $html = '<ul class="seo-hub-links">' . implode('', $items) . '</ul>';
    }
    set_transient($cache_key, $html, 12 * HOUR_IN_SECONDS);

    return $html;
}

// ── Problem hub grid ────────────────────────────────────────────────────────
//
// Renders problem-type hub links as a 3-column grid with bordered cards.
// Used by [seo_hub type="problem"].

function seo_hub_problem_grid(array $items): string {
    // Wrap each item's link in h3
    $items = array_map(fn($li) => str_replace(['<li>', '</li>'], ['<li><h3>', '</h3></li>'], $li), $items);

    return '<div class="seo-hub-problem-grid"><ul>' . implode('', $items) . '</ul></div>';
}

// ── Hub Source setting (Settings → General) ──────────────────────────────────
//
// Adds a single field to Settings → General where you paste the main site URL.
// Only needed on blog subdomains. Leave blank on main sites.

add_action('admin_init', function() {
    register_setting('general', 'seo_hub_source', [
        'type'              => 'string',
        'sanitize_callback' => function($val) {
            return $val ? untrailingslashit(esc_url_raw($val)) : '';
        },
        'default'           => '',
    ]);

    add_settings_field(
        'seo_hub_source',
        'SEO Hub Source URL',
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
        'general',
        'default',
        ['label_for' => 'seo_hub_source']
    );

    register_setting('general', 'seo_hub_consumers', [
        'type'    => 'string',
        'default' => '',
    ]);

    // Only show on source/main sites (where seo_hub_source is blank)
    if (empty(get_option('seo_hub_source', ''))) {
        add_settings_field(
            'seo_hub_consumers',
            'SEO Hub Consumers',
            function() {
                $value = get_option('seo_hub_consumers', '');
                echo '<textarea name="seo_hub_consumers" id="seo_hub_consumers" '
                   . 'class="large-text" rows="3" placeholder="https://blog.example.com">'
                   . esc_textarea($value) . '</textarea>';
                echo '<p class="description">One URL per line. When a CPT post is published or changed, '
                   . 'these sites will have their hub cache cleared automatically. '
                   . 'Leave blank if no blog subdomains consume from this site.</p>';
            },
            'general',
            'default',
            ['label_for' => 'seo_hub_consumers']
        );
    }
});

// ── Convert Post Type metabox ────────────────────────────────────────────────
//
// Adds a "SEO Content Type" sidebar panel to Pages (and Posts).
// Lets editors convert a standard page to any SEO Machine CPT.
// After conversion the post_type changes in the DB and the editor
// is redirected to the correct admin URL.

add_action('add_meta_boxes', function() {
    $screen_types = array_merge(['page', 'post'], array_keys(SEO_MACHINE_POST_TYPES));
    add_meta_box(
        'seo_machine_convert',
        'SEO Content Type',
        'seo_machine_convert_metabox_html',
        $screen_types,
        'side',
        'default'
    );
});

function seo_machine_convert_metabox_html(WP_Post $post): void {
    $current = $post->post_type;
    $labels  = [
        'seo_location'  => 'Location Page',
        'seo_service'   => 'Service Page',
        'seo_pillar'    => 'Pillar Page',
        'seo_topical'   => 'Topical Article',
        'seo_blog'      => 'Blog Post',
        'seo_comp_alt'  => 'Competitor Alternative',
    ];

    wp_nonce_field('seo_machine_convert', 'seo_machine_convert_nonce');
    ?>
    <p style="margin:0 0 8px;color:#646970;font-size:12px;">
        <?php if (array_key_exists($current, $labels)): ?>
            Currently: <strong><?= esc_html($labels[$current]) ?></strong>
        <?php else: ?>
            Convert this <?= esc_html($current) ?> to an SEO content type.
        <?php endif; ?>
    </p>
    <select name="seo_machine_target_type" style="width:100%;margin-bottom:6px;">
        <option value="">— No change —</option>
        <?php foreach ($labels as $slug => $label): ?>
            <option value="<?= esc_attr($slug) ?>" <?= selected($current, $slug, false) ?>>
                <?= esc_html($label) ?>
            </option>
        <?php endforeach; ?>
    </select>
    <?php if (array_key_exists($current, $labels)): ?>
        <p style="margin:4px 0 0;color:#646970;font-size:11px;">
            To unconvert, use Quick Edit or WP-CLI.
        </p>
    <?php endif; ?>
    <?php
}

add_action('save_post', function(int $post_id, WP_Post $post) {
    // Bail on autosave, revisions, or missing nonce
    if (
        defined('DOING_AUTOSAVE') && DOING_AUTOSAVE ||
        wp_is_post_revision($post_id) ||
        !isset($_POST['seo_machine_convert_nonce']) ||
        !wp_verify_nonce($_POST['seo_machine_convert_nonce'], 'seo_machine_convert') ||
        !current_user_can('edit_post', $post_id)
    ) {
        return;
    }

    $target = sanitize_key($_POST['seo_machine_target_type'] ?? '');

    if (empty($target) || !array_key_exists($target, SEO_MACHINE_POST_TYPES)) {
        return;
    }

    if ($post->post_type === $target) {
        return;
    }

    // Update post_type directly — wp_update_post() would recurse into save_post
    global $wpdb;
    $wpdb->update(
        $wpdb->posts,
        ['post_type' => $target],
        ['ID' => $post_id],
        ['%s'],
        ['%d']
    );

    // Flush rewrite rules so the new permalink structure resolves immediately
    flush_rewrite_rules();

    // Quick Edit saves via AJAX — let WordPress handle the response normally
    if (wp_doing_ajax()) {
        return;
    }

    // Full page save — redirect back to the Pages list
    wp_redirect(admin_url('edit.php?post_type=page&seo_converted=1&converted_label=' . urlencode(SEO_MACHINE_POST_TYPES[$target][1])));
    exit;
}, 10, 2);

// Show an admin notice after a successful conversion
add_action('admin_notices', function() {
    if (!isset($_GET['seo_converted'])) {
        return;
    }
    $label = sanitize_text_field($_GET['converted_label'] ?? 'SEO content type');
    echo '<div class="notice notice-success is-dismissible"><p>'
        . sprintf('Page converted to <strong>%s</strong> successfully.', esc_html($label))
        . '</p></div>';
});

// ── Quick Edit support on Pages list ────────────────────────────────────────

// 1. Add "SEO Type" column to the Pages list
add_filter('manage_pages_columns', function(array $cols): array {
    $cols['seo_type'] = 'SEO Type';
    return $cols;
});

add_action('manage_pages_custom_column', function(string $col, int $post_id): void {
    if ($col !== 'seo_type') {
        return;
    }
    $labels = [
        'seo_location'  => 'Location Page',
        'seo_service'   => 'Service Page',
        'seo_pillar'    => 'Pillar Page',
        'seo_topical'   => 'Topical Article',
        'seo_blog'      => 'Blog Post',
        'seo_comp_alt'  => 'Competitor Alternative',
    ];
    $type    = get_post_type($post_id);
    $display = $labels[$type] ?? '—';

    // Hidden input carries the current value so JS can read it
    echo esc_html($display);
    echo '<input type="hidden" class="seo-type-value" value="' . esc_attr($type) . '">';
}, 10, 2);

// 2. Add our dropdown inside the Quick Edit form
add_action('quick_edit_custom_box', function(string $col, string $post_type): void {
    if ($col !== 'seo_type' || $post_type !== 'page') {
        return;
    }
    $labels = [
        'seo_location'  => 'Location Page',
        'seo_service'   => 'Service Page',
        'seo_pillar'    => 'Pillar Page',
        'seo_topical'   => 'Topical Article',
        'seo_blog'      => 'Blog Post',
        'seo_comp_alt'  => 'Competitor Alternative',
    ];
    wp_nonce_field('seo_machine_convert', 'seo_machine_convert_nonce');
    ?>
    <fieldset class="inline-edit-col-left" style="clear:both;padding-top:8px;">
        <div class="inline-edit-col">
            <label>
                <span class="title">SEO Type</span>
                <select name="seo_machine_target_type" id="seo_machine_target_type">
                    <option value="">— No change —</option>
                    <?php foreach ($labels as $slug => $label): ?>
                        <option value="<?= esc_attr($slug) ?>"><?= esc_html($label) ?></option>
                    <?php endforeach; ?>
                </select>
            </label>
        </div>
    </fieldset>
    <?php
}, 10, 2);

// 3. JS: pre-populate the select when Quick Edit opens
add_action('admin_footer-edit.php', function(): void {
    $screen = get_current_screen();
    if (!$screen || $screen->id !== 'edit-page') {
        return;
    }
    ?>
    <script>
    (function($) {
        var _edit = inlineEditPost.edit;
        inlineEditPost.edit = function(id) {
            _edit.apply(this, arguments);
            var postId  = typeof id === 'object' ? parseInt(this.getId(id), 10) : id;
            var current = $('#post-' + postId).find('.seo-type-value').val() || '';
            $('#seo_machine_target_type').val(current);
        };
    }(jQuery));
    </script>
    <?php
});

// ── hdr-* class specificity fix ──────────────────────────────────────────────
// Elementor's heading widget generates per-post, per-element CSS with 4-class
// specificity (0,4,0) that overrides our hdr-* utility classes (0,2,0). The
// compiled global-frontend-desktop.css loads after per-post CSS but loses on
// specificity. Fix: output inline CSS after all Elementor styles at priority 999
// with !important on font-size only — the one property Elementor always sets per widget.

$_seo_machine_hdr_css = '
    .elementor .hdr-xl { font-size: clamp(2rem,   1rem  + 5vw,   2.5rem) !important; }
    .elementor .hdr-l  { font-size: clamp(1.6rem, 0.75rem + 4vw, 2rem)   !important; }
    .elementor .hdr-m  { font-size: clamp(1.3rem, 0.5rem + 3vw,  1.6rem) !important; }
    .elementor .hdr-s  { font-size: clamp(1.1rem, 0.4rem + 2vw,  1.3rem) !important; }
    .elementor .hdr-xs { font-size: clamp(1rem,   0.25rem + 1.5vw, 1.1rem) !important; }
';

// Hub shortcode stylesheet (problem grid etc.)
add_action('wp_enqueue_scripts', function(): void {
    wp_enqueue_style(
        'seo-machine-hub',
        content_url('mu-plugins/seomachine-hub-v2.css'),
        [],
        '3.4.1'
    );
});

// Frontend
add_action('wp_enqueue_scripts', function() use ($_seo_machine_hdr_css): void {
    if (!wp_style_is('elementor-frontend', 'enqueued')) {
        return;
    }
    wp_add_inline_style('elementor-frontend', $_seo_machine_hdr_css);
}, 999);

// Elementor editor preview iframe
add_action('elementor/preview/enqueue_styles', function() use ($_seo_machine_hdr_css): void {
    wp_register_style('seo-machine-hdr', false);
    wp_enqueue_style('seo-machine-hdr');
    wp_add_inline_style('seo-machine-hdr', $_seo_machine_hdr_css);
});

// Elementor editor panel (for live-preview in the panel itself)
add_action('elementor/editor/after_enqueue_styles', function() use ($_seo_machine_hdr_css): void {
    wp_register_style('seo-machine-hdr-editor', false);
    wp_enqueue_style('seo-machine-hdr-editor');
    wp_add_inline_style('seo-machine-hdr-editor', $_seo_machine_hdr_css);
});

// ── Elementor h1 heading class injection ─────────────────────────────────────
// Elementor's heading widget always renders <h1 class="elementor-heading-title ...">
// with its own fixed classes. The widget's css_classes setting goes on the outer
// wrapper <div>, not the <h1> itself. This filter adds hdr-xl directly to the
// inner <h1> tag so it picks up the same typography styles as our injected content.

add_filter('elementor/widget/render_content', function(string $content, $widget): string {
    if ($widget->get_name() !== 'heading') {
        return $content;
    }
    $settings = $widget->get_settings_for_display();
    if (($settings['header_size'] ?? '') !== 'h1') {
        return $content;
    }
    // Add hdr-xl to the inner <h1> rendered by Elementor's heading widget
    return preg_replace(
        '/<h1\s+class="(elementor-heading-title[^"]*)"/',
        '<h1 class="$1 hdr-xl"',
        $content,
        1
    );
}, 10, 2);

// ── Elementor support for custom post types ──────────────────────────────────
//
// Two approaches combined for compatibility across Elementor versions:
// 1. Filter the public post types list (shows CPTs in Elementor → Settings)
// 2. Filter the stored option (auto-enables CPTs without manual checkbox step)

add_filter('elementor/utils/get_public_post_types', function($types) {
    foreach (SEO_MACHINE_POST_TYPES as $slug => [$plural]) {
        $obj = get_post_type_object($slug);
        if ($obj) {
            $types[$slug] = $plural;
        }
    }
    return $types;
});

// Auto-enable our CPTs in Elementor without requiring manual settings checkbox
add_filter('option_elementor_cpt_support', function($value) {
    $cpts = array_keys(SEO_MACHINE_POST_TYPES);
    if (!is_array($value)) {
        $value = [];
    }
    foreach ($cpts as $cpt) {
        if (!in_array($cpt, $value, true)) {
            $value[] = $cpt;
        }
    }
    return $value;
});

add_filter('default_option_elementor_cpt_support', function() {
    return array_keys(SEO_MACHINE_POST_TYPES);
});

// ── Sitemap ───────────────────────────────────────────────────────────────────
// WordPress core (5.5+) generates /wp-sitemap.xml including all public CPTs.
// Redirect legacy /sitemap.xml requests there so Google and audit tools see
// the full site index, not whatever 8-URL stub a theme/plugin left behind.
// Also declare the correct sitemap URL in robots.txt.

add_action('template_redirect', function() {
    if (!is_admin() && isset($_SERVER['REQUEST_URI'])
        && preg_match('#^/sitemap\.xml#', $_SERVER['REQUEST_URI'])) {
        wp_redirect(home_url('/wp-sitemap.xml'), 301);
        exit;
    }
});

add_action('template_redirect', function() {
    $map = json_decode(get_option('seo_machine_redirects', '[]'), true);
    if (!is_array($map) || empty($map)) return;
    $uri = rtrim(strtok($_SERVER['REQUEST_URI'], '?'), '/');
    foreach ($map as $rule) {
        if (isset($rule['from'], $rule['to']) && rtrim($rule['from'], '/') === $uri) {
            wp_redirect($rule['to'], 301);
            exit;
        }
    }
});

add_filter('robots_txt', function(string $output): string {
    if (strpos($output, 'wp-sitemap.xml') === false) {
        $output .= "\nSitemap: " . home_url('/wp-sitemap.xml') . "\n";
    }
    return $output;
});

