WordPress export spec (WPages)

Purpose
- Define the export formats, field order, and SQL for data extraction that feeds WPages.
- Provide ready-to-run single-line SELECT statements suitable for `mysql -e` usage.

General conventions
- Output is expected as MySQL tab-delimited (mysql -e default).
- Each export is a standalone file; do not mix row types in a single file unless explicitly stated.
- Field order is fixed and consistent across exports when possible.
- Empty/unavailable fields are emitted as empty strings.

Base post field order (shared)
1) ID
2) post_title
3) post_content
4) post_status
5) post_date
6) post_type
7) post_name
8) post_parent
9) menu_order
10) guid
11) post_modified
12) post_author
13) post_mime_type

Recommended exports

1) Pages + posts (content)
- Purpose: primary content extraction for pages and posts.
- Rows: wp_posts where post_type in ('page','post') and status in active states.
- Output format: tab-delimited rows with the base post field order.

SELECT (single line):
SELECT ID, post_title, post_content, post_status, post_date, post_type, IFNULL(post_name,''), IFNULL(post_parent,''), IFNULL(menu_order,''), IFNULL(guid,''), IFNULL(post_modified,''), IFNULL(post_author,''), IFNULL(post_mime_type,'') FROM wp_posts WHERE post_type IN ('page','post') AND post_status IN ('publish','draft','private','pending','future') ORDER BY post_type, ID;

2) Menu / navigation items
- Purpose: reconstruct menu structure and item targets.
- Rows: wp_posts with post_type='nav_menu_item', joined to nav_menu terms and menu item meta.
- Output format: base post fields first (same order), then menu fields.

Menu fields (append after base post fields)
- menu_name
- menu_slug
- parent_item_id
- item_type
- item_object
- item_object_id
- item_url

SELECT (single line):
SELECT p.ID, p.post_title, p.post_content, p.post_status, p.post_date, p.post_type, IFNULL(p.post_name,''), IFNULL(p.post_parent,''), IFNULL(p.menu_order,''), IFNULL(p.guid,''), IFNULL(p.post_modified,''), IFNULL(p.post_author,''), IFNULL(p.post_mime_type,''), IFNULL(t.name,'' ) AS menu_name, IFNULL(t.slug,'' ) AS menu_slug, IFNULL(MAX(CASE WHEN pm.meta_key='_menu_item_menu_item_parent' THEN pm.meta_value END),'' ) AS parent_item_id, IFNULL(MAX(CASE WHEN pm.meta_key='_menu_item_type' THEN pm.meta_value END),'' ) AS item_type, IFNULL(MAX(CASE WHEN pm.meta_key='_menu_item_object' THEN pm.meta_value END),'' ) AS item_object, IFNULL(MAX(CASE WHEN pm.meta_key='_menu_item_object_id' THEN pm.meta_value END),'' ) AS item_object_id, IFNULL(MAX(CASE WHEN pm.meta_key='_menu_item_url' THEN pm.meta_value END),'' ) AS item_url FROM wp_posts p JOIN wp_term_relationships tr ON tr.object_id=p.ID JOIN wp_term_taxonomy tt ON tt.term_taxonomy_id=tr.term_taxonomy_id JOIN wp_terms t ON t.term_id=tt.term_id LEFT JOIN wp_postmeta pm ON pm.post_id=p.ID WHERE p.post_type='nav_menu_item' AND tt.taxonomy='nav_menu' GROUP BY p.ID, p.post_title, p.post_content, p.post_status, p.post_date, p.post_type, p.post_name, p.post_parent, p.menu_order, p.guid, p.post_modified, p.post_author, p.post_mime_type, t.name, t.slug ORDER BY t.name, p.menu_order, p.ID;

3) Attachments / media
- Purpose: media inventory for image/PDF mapping and library reconstruction.
- Rows: wp_posts where post_type='attachment'.
- Output format: base post field order.

SELECT (single line):
SELECT ID, post_title, post_content, post_status, post_date, post_type, IFNULL(post_name,''), IFNULL(post_parent,''), IFNULL(menu_order,''), IFNULL(guid,''), IFNULL(post_modified,''), IFNULL(post_author,''), IFNULL(post_mime_type,'') FROM wp_posts WHERE post_type='attachment' AND post_status IN ('inherit','publish') ORDER BY ID;

4) Attachment meta (optional, separate export)
- Purpose: capture file paths, sizes, and alt text for attachments.
- Rows: wp_postmeta for specific keys.
- Output format: attachment_id, meta_key, meta_value.

SELECT (single line):
SELECT post_id, meta_key, meta_value FROM wp_postmeta WHERE meta_key IN ('_wp_attached_file','_wp_attachment_metadata','_wp_attachment_image_alt') ORDER BY post_id, meta_key;

Command-line usage (mysql -e)
- Replace wp_ with your actual table prefix.
- Example (pages/posts):
  mysql -p -e "SELECT ID, post_title, post_content, post_status, post_date, post_type, IFNULL(post_name,''), IFNULL(post_parent,''), IFNULL(menu_order,''), IFNULL(guid,''), IFNULL(post_modified,''), IFNULL(post_author,''), IFNULL(post_mime_type,'') FROM wp_posts WHERE post_type IN ('page','post') AND post_status IN ('publish','draft','private','pending','future') ORDER BY post_type, ID;" > pages_posts.out

Notes
- The base post field order is designed to be consistent across exports.
- The menu export appends menu-specific fields after the base post fields.
- Avoid mixing row types in one file unless you also add a row-type discriminator and accept many empty fields.
