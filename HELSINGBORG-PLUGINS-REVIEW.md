# Helsingborg: the WordPress plugins set aside - for a decision

> Prepared 2026-09-29 from the 2026-09-28 run. **Nothing here has been changed**: `filters.py` still sets all 103 aside as `wordpress-plugin` (they declare `wordpress-plugin` / `wordpress-muplugin` in `composer.json`). This is the review CONTINUE.md asked for, done the way the iMio rules were reviewed. Two iMio rules were removed after catching real products, so the question is whether this rule catches real software too.

## What is actually at stake: 73, not 103

**30 of the 103 have no description**, so the `no-description` rule would set them aside anyway (measured: `classify()` with the plugin rule removed puts exactly those 30 under `no-description` and the other 73 in). That includes **6 of the 8 `api-*-manager` repos** CONTINUE.md named as the likeliest false positives (alarm, event, exhibition, project, schools, sponsor). They are WordPress-based API backends, but with no description they stay out either way - the fix for those is upstream (the city writing a description), not here.

The 73 with a description fall into three groups.

## A. Municipal tools that happen to be WordPress plugins (13) - the case for reinstating

Each does a government job a reader could adopt: volunteer management, citizen feedback and ideas, a support desk, plain-language (LIX) scoring, an easy-to-read text alternative. The rule's premise - a plugin is plumbing, not adoptable software - fits these least.

| repo | description | last push |
|---|---|---|
| [api-volunteer-manager](https://github.com/helsingborg-stad/api-volunteer-manager) | Managing data for volunteers and their assignments | 2026-02-23 |
| [api-alarm-integration](https://github.com/helsingborg-stad/api-alarm-integration) | Alarm service for the City of Helsingborg. | 2026-09-28 |
| [Customer-feedback](https://github.com/helsingborg-stad/Customer-feedback) | Plugin for collecting feedback on pages and managing chat tools. | 2026-09-09 |
| [idea-manager](https://github.com/helsingborg-stad/idea-manager) | Submit and manage innovative idéas from users | 2019-10-08 |
| [student-council-protocols](https://github.com/helsingborg-stad/student-council-protocols) | Archive of student council protocols with comment functionality | 2023-01-05 |
| [todo](https://github.com/helsingborg-stad/todo) | A simple support ticket system based on ACF fields. | 2018-05-11 |
| [lix-calculator](https://github.com/helsingborg-stad/lix-calculator) | Calculates the LIX readability score of the text in the main area of a post. | 2025-11-20 |
| [easy-to-read-alternative](https://github.com/helsingborg-stad/easy-to-read-alternative) | Provides field with an legible text alternative | 2026-05-05 |
| [municipio-faq-nlp-classification](https://github.com/helsingborg-stad/municipio-faq-nlp-classification) | Classification of articles and faq | 2022-06-16 |
| [open-hours](https://github.com/helsingborg-stad/open-hours) | Creates simple shortcodes for when an operation linked to the page is open. | 2016-11-09 |
| [location-explorer](https://github.com/helsingborg-stad/location-explorer) | Explore nice places to live | 2018-01-04 |
| [wp-listings](https://github.com/helsingborg-stad/wp-listings) | Minimalistic listing plugin for stuff like apartments, selling ads and jobs. | 2019-04-25 |
| [notification-center](https://github.com/helsingborg-stad/notification-center) | Plugin to give logged in users notifications when others react comments etc. | 2018-10-19 |

## B. Modularity / Municipio modules (16) - the ecosystem of a theme the catalogue already keeps

Municipio (the WordPress theme Swedish municipalities run) is kept on purpose - `CLAUDE.md`: "Themes stay - Municipio IS one." These are its content modules. Reinstating them would list one product as ~16 entries; keeping them out leaves Municipio's entry as the single door. A middle path: keep them set aside and name them on Municipio's entry (the `variants` mechanism links, never merges - see CLAUDE.md), which is a code change, not a filter change.

| repo | description | last push |
|---|---|---|
| [Modularity](https://github.com/helsingborg-stad/Modularity) | [Deprecated] Widget plugin for WordPress based on post-type's | 2026-02-07 |
| [modularity-contact-banner](https://github.com/helsingborg-stad/modularity-contact-banner) | Stores and presents general contact information to the organization | 2026-09-09 |
| [modularity-dictionary](https://github.com/helsingborg-stad/modularity-dictionary) | Explenation of words on pages/posts - modularity module | 2017-05-12 |
| [modularity-dynamic-guides](https://github.com/helsingborg-stad/modularity-dynamic-guides) | Module for displaying interactive guides | 2026-09-14 |
| [modularity-entryscape](https://github.com/helsingborg-stad/modularity-entryscape) | Enables modules to display entryscape | 2026-09-28 |
| [modularity-form-builder](https://github.com/helsingborg-stad/modularity-form-builder) | Simple form builder that uses acf for forms. | 2026-09-28 |
| [modularity-guides](https://github.com/helsingborg-stad/modularity-guides) | Manages guides for buisness WordPress (helsingborg.se/foretagare) | 2026-09-09 |
| [modularity-json-render](https://github.com/helsingborg-stad/modularity-json-render) | Renders a single level api-response (json) as a list. | 2026-09-11 |
| [modularity-like](https://github.com/helsingborg-stad/modularity-like) | Adds the ability to like posts and manage likes with a module. | 2026-09-28 |
| [modularity-onepage](https://github.com/helsingborg-stad/modularity-onepage) | One page module for Modularity | 2016-12-19 |
| [modularity-products](https://github.com/helsingborg-stad/modularity-products) | Display products & offers matrix | 2026-09-28 |
| [modularity-recommend](https://github.com/helsingborg-stad/modularity-recommend) | Modularity recommend. Display static or AI generated recommendation links. | 2026-09-28 |
| [modularity-sections](https://github.com/helsingborg-stad/modularity-sections) | Provides graphical sections intended for full-width usage | 2026-09-10 |
| [modularity-testimonials](https://github.com/helsingborg-stad/modularity-testimonials) | Modularity plugin to display testemonials | 2026-09-10 |
| [modularity-timeline](https://github.com/helsingborg-stad/modularity-timeline) | A module to display a timeline | 2026-09-28 |
| [municipio-clone](https://github.com/helsingborg-stad/municipio-clone) | WordPress plugin that enables WP-CLI command for cloning remote WordPress sites. | 2026-09-28 |

## C. WordPress plumbing - the rule is right (44)

Multisite fixes, SSO and cache glue, redirects, editor tweaks, boilerplates, a test plugin, a fork, and repos marked deprecated. Generic to any WordPress install, not government software.

| repo | description | last push |
|---|---|---|
| [ACF-UX-collapse-explore](https://github.com/helsingborg-stad/ACF-UX-collapse-explore) | Exploration clone of ACF-UX-collapse for better deployment | 2026-04-07 |
| [active-directory-api-wp-integration](https://github.com/helsingborg-stad/active-directory-api-wp-integration) | Simple plugin for verification of existing WordPress users with api. | 2026-09-10 |
| [api-event-manager-integration](https://github.com/helsingborg-stad/api-event-manager-integration) | DEPRECATED: Intragration with event-api for WordPress | 2026-09-18 |
| [better-post-UI](https://github.com/helsingborg-stad/better-post-UI) | Enhances WordPress admin UI on posts and pages. | 2026-09-10 |
| [broken-link-detector](https://github.com/helsingborg-stad/broken-link-detector) | Detects and fixes broken links (internally) | 2026-09-09 |
| [custom-short-links](https://github.com/helsingborg-stad/custom-short-links) | Create shorter versions of url:s | 2026-09-14 |
| [depricated-xcap-import](https://github.com/helsingborg-stad/depricated-xcap-import) | NOTE: NOT SUPPORTED ANYMORE! | 2017-05-16 |
| [elasticpress-synonyms](https://github.com/helsingborg-stad/elasticpress-synonyms) | Adds the ability to create synonyms for popular searchwords in elastic search | 2017-11-01 |
| [force-ssl](https://github.com/helsingborg-stad/force-ssl) | Simple plugin forcing the user to use ssl | 2026-01-23 |
| [google-analythics](https://github.com/helsingborg-stad/google-analythics) | Adds a set of google analythics related functions | 2022-12-07 |
| [import-rss-feed](https://github.com/helsingborg-stad/import-rss-feed) | Probably the last Wordpress RSS importer. Import items from RSS feed to any post type. | 2018-11-21 |
| [larrum-custom-api](https://github.com/helsingborg-stad/larrum-custom-api) | Custom API endpoint for Lärrum. | 2022-07-04 |
| [media-usage](https://github.com/helsingborg-stad/media-usage) | Track the use of attachments across posts, meta and options | 2025-11-20 |
| [miniorange-saml-20-single-sign-on](https://github.com/helsingborg-stad/miniorange-saml-20-single-sign-on) | Fork of miniorange-saml-20-single-sign-on with added filters. | 2026-05-31 |
| [modularity-boilerplate](https://github.com/helsingborg-stad/modularity-boilerplate) | Boilerplate repo for addon modules | 2024-10-01 |
| [multisite-role-propagation](https://github.com/helsingborg-stad/multisite-role-propagation) | Plugin to quickly set a role for a multisite user on multiple blogs in a network | 2025-11-20 |
| [polylang-fallback](https://github.com/helsingborg-stad/polylang-fallback) | Automatic fallback to selected language(s) if a translation dosen't exist on current language. Without doing a redirect  | 2023-01-25 |
| [post-comment-likes](https://github.com/helsingborg-stad/post-comment-likes) | Adds functionality to like posts and comments | 2022-12-10 |
| [post-type-export](https://github.com/helsingborg-stad/post-type-export) | Exports selected post type & meta to CSV | 2018-03-29 |
| [readspeaker-helper](https://github.com/helsingborg-stad/readspeaker-helper) | Helper plugin for readspeaker | 2020-11-13 |
| [release-workflow-test-plugin](https://github.com/helsingborg-stad/release-workflow-test-plugin) | This is a no-op plugin used to test the release workflow. | 2025-10-10 |
| [s3-local-index](https://github.com/helsingborg-stad/s3-local-index) | Stores a local index to make common file operations faster | 2026-09-25 |
| [Search-notices](https://github.com/helsingborg-stad/Search-notices) | Add notices on keywords in WordPress search. | 2026-02-23 |
| [search-statistics](https://github.com/helsingborg-stad/search-statistics) | Adds awesome but simple search statistics to WordPress Admin. | 2026-09-10 |
| [webhooks-manager](https://github.com/helsingborg-stad/webhooks-manager) | Create and manage webhooks from WordPress action hooks | 2026-09-24 |
| [Wordpress-Plugin-Boilerplate](https://github.com/helsingborg-stad/Wordpress-Plugin-Boilerplate) | A simple class based WordPress plugin structure to start off any plugin with. | 2026-03-26 |
| [wp-api-get-sites](https://github.com/helsingborg-stad/wp-api-get-sites) | Add endpoint listing all sites in a multisite installation. | 2017-05-10 |
| [wp-content-translator](https://github.com/helsingborg-stad/wp-content-translator) | DEPRICATED! This plugin lacks attention. | 2017-09-13 |
| [wp-mu-plugins-url-everywhere](https://github.com/helsingborg-stad/wp-mu-plugins-url-everywhere) | Allow Plugins URL function to create urls towards any directory | 2026-01-23 |
| [wp-page-for-posttype](https://github.com/helsingborg-stad/wp-page-for-posttype) | Adds the ability to place a page on an archive page and/or place a posttype archive on a page. | 2026-09-10 |
| [wpmu-accordion-expand-plus](https://github.com/helsingborg-stad/wpmu-accordion-expand-plus) | Replaces accordion expand arrow to a plus-circle | 2022-05-17 |
| [wpmu-acf-fatal-error-when-used-too-early](https://github.com/helsingborg-stad/wpmu-acf-fatal-error-when-used-too-early) | Throws a descriptive exception when an ACF field is accessed before WordPress has initialized. | 2026-09-18 |
| [wpmu-acf-google-maps-key](https://github.com/helsingborg-stad/wpmu-acf-google-maps-key) | Adds a field to enter a google maps api key for ACF | 2026-01-23 |
| [wpmu-allow-cors](https://github.com/helsingborg-stad/wpmu-allow-cors) | Allows cors with * | 2026-02-23 |
| [wpmu-correct-file-paths](https://github.com/helsingborg-stad/wpmu-correct-file-paths) | esolves incorrect file paths, when migrating databases between different environments. | 2026-01-23 |
| [wpmu-fatal-error-when-equeue-too-early](https://github.com/helsingborg-stad/wpmu-fatal-error-when-equeue-too-early) | Throws a descriptive exception when an enqueue or register of a asset is made before WordPress has initialized. | 2026-09-18 |
| [wpmu-fatal-error-when-translation-too-early](https://github.com/helsingborg-stad/wpmu-fatal-error-when-translation-too-early) | Throws a descriptive exception when an translation is loaded before WordPress has initialized. | 2026-09-18 |
| [wpmu-filter-email](https://github.com/helsingborg-stad/wpmu-filter-email) | Multisite plugin to filter outgoing email adresses. | 2022-02-04 |
| [wpmu-invalidate-login-pagecache](https://github.com/helsingborg-stad/wpmu-invalidate-login-pagecache) | Invalidates pagecache on submit of the login form. | 2026-01-23 |
| [wpmu-litespeed-common-settings](https://github.com/helsingborg-stad/wpmu-litespeed-common-settings) | Use blog 1 as the master for all settings in litespeed configuration | 2026-01-23 |
| [wpmu-network-admin-url](https://github.com/helsingborg-stad/wpmu-network-admin-url) | Fixes network ur's when running WordPress as multisite aquired by composer | 2026-01-23 |
| [wpmu-propagate-miniorange-saml-sso-settings](https://github.com/helsingborg-stad/wpmu-propagate-miniorange-saml-sso-settings) | Adds a wp-cli command to send a miniorange saml sso default setting to all blogs in a network. | 2025-02-12 |
| [wpmu-remove-user-endpoint](https://github.com/helsingborg-stad/wpmu-remove-user-endpoint) | Removes the user endpoint when not logged in | 2026-04-24 |
| [wpmu-security](https://github.com/helsingborg-stad/wpmu-security) | Adds basic security features to WordPress | 2026-09-28 |

## Options

1. **Keep the rule as is.** All 103 stay set aside; group A is the cost.
2. **Reinstate group A only**, by an explicit allow-list of repo URLs in `filters.py` (never by name pattern - `CLAUDE.md`: names are not evidence). Pin the list in `test_filters.py`. 13 entries return.
3. **Option 2, plus link group B to Municipio** as its modules instead of listing them - a `variants.json`-style curated link, so the page names them under Municipio without adding 16 entries.

Either reinstatement puts the returned repos in **Recently added** on the next run: `first_seen.py` records only active rows, and none of these has ever been active (checked: `api-volunteer-manager`, `lix-calculator` are absent from `cache/_first_seen.json`). That is arguably correct - they would be new to the catalogue - but it would fill the strip with Helsingborg for a week. Stamping them `null` (baseline) in the same commit avoids that, if preferred.

