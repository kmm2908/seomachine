<?php
/**
 * Plugin Name: SEO Machine
 * Description: Registers SEO content post types and exposes SEO meta fields via REST API. No Yoast dependency.
 * Version: 2.2
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

// ── Elementor support for custom post types ──────────────────────────────────

add_filter('elementor/utils/get_public_post_types', function($types) {
    foreach (SEO_MACHINE_POST_TYPES as $slug => [$plural]) {
        $obj = get_post_type_object($slug);
        if ($obj) {
            $types[$slug] = $plural;
        }
    }
    return $types;
});
