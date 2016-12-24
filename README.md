# wp_clone
Word Press clone tool. Clones one WP site to a new site with different table_prefix so they can coexist on the same server.

Assuming you have a site in `./public_html/site1`, running `./public_html/wp_clone.py site1 site2 --db --copy --private` will create `./public_html/site2` with an exact copy of site1 but with `$table_prefix = site2`. All links in the content will be changed to point to `site2`. The database from site1 will be copied with the new table prefix. All **posts** in site2 will be marked *pending*. The old site will be unchanged and work properly. The new site will be an exact clone but backed by the new database tables.


Once case this doesn't handle is if WP is installed directly in the root of  ~/public_html. To use this, you'll have to first manually move that install into a subfolder and reconfigure WP to work. Once WP is working, you can then clone it. [See this link for more information](https://codex.wordpress.org/Moving_WordPress#Moving_Directories_On_Your_Existing_Server).

