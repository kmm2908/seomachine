<?php
/**
 * Plugin Name: SEO Machine
 * Description: Registers SEO content post types and exposes SEO meta fields via REST API. No Yoast dependency.
 * Version: 2.4
 * Author: SEO Machine
 *
 * Installation:
 * 1. Upload this file to: wp-content/mu-plugins/seo-machine-yoast-rest.php
 * 2. That's it - mu-plugins are automatically activated
 */

if (!defined('ABSPATH')) {
    exit;
}

define('SEO_MACHINE_POST_TYPES', [
    'seo_service'  => ['Services',          'Service'],
    'seo_location' => ['Locations',         'Location'],
    'seo_pillar'   => ['Pillar Pages',      'Pillar Page'],
    'seo_topical'  => ['Topical Articles',  'Topical Article'],
    'seo_blog'     => ['Blog Posts',        'Blog Post'],
]);

// ── Custom Post Types ────────────────────────────────────────────────────────

add_action('init', function() {
    foreach (SEO_MACHINE_POST_TYPES as $slug => [$plural, $singular]) {
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
            'show_in_menu'       => 'seo-content',
            'show_in_nav_menus'  => true,
            'supports'           => ['title', 'editor', 'thumbnail', 'excerpt', 'custom-fields'],
            'rewrite'            => ['slug' => str_replace('seo_', '', $slug)],
            'has_archive'        => false,
        ]);
    }
});

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

// ── SEO Meta Fields (no Yoast dependency) ───────────────────────────────────

add_action('init', function() {
    $all_types = array_merge(['post', 'page'], array_keys(SEO_MACHINE_POST_TYPES));
    $meta_keys = [
        '_yoast_wpseo_focuskw'  => 'SEO Focus Keyphrase',
        '_yoast_wpseo_title'    => 'SEO Title',
        '_yoast_wpseo_metadesc' => 'SEO Meta Description',
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

// ── Hub page shortcode ───────────────────────────────────────────────────────
//
// Usage: [seo_hub type="location"]  (or service, pillar, topical, blog)
// Place in an Elementor HTML widget. Renders a <ul> of all published posts of
// that type, sorted A–Z. Automatically reflects publish/unpublish changes.

add_shortcode('seo_hub', function($atts) {
    $atts = shortcode_atts(['type' => 'location'], $atts, 'seo_hub');

    $type_map = [
        'location' => 'seo_location',
        'service'  => 'seo_service',
        'pillar'   => 'seo_pillar',
        'topical'  => 'seo_topical',
        'blog'     => 'seo_blog',
    ];

    $post_type = $type_map[$atts['type']] ?? 'seo_location';

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

    $items = array_map(fn($p) =>
        '<li><h3><a href="' . esc_url(get_permalink($p)) . '">'
        . esc_html($p->post_excerpt ?: $p->post_title) . '</a></h3></li>',
        $posts
    );

    return '<ul class="seo-hub-links">' . implode('', $items) . '</ul>';
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
        'seo_location' => 'Location Page',
        'seo_service'  => 'Service Page',
        'seo_pillar'   => 'Pillar Page',
        'seo_topical'  => 'Topical Article',
        'seo_blog'     => 'Blog Post',
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
        'seo_location' => 'Location Page',
        'seo_service'  => 'Service Page',
        'seo_pillar'   => 'Pillar Page',
        'seo_topical'  => 'Topical Article',
        'seo_blog'     => 'Blog Post',
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
        'seo_location' => 'Location Page',
        'seo_service'  => 'Service Page',
        'seo_pillar'   => 'Pillar Page',
        'seo_topical'  => 'Topical Article',
        'seo_blog'     => 'Blog Post',
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
