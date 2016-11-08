# wp_clone
Word Press clone tool. Clones one WP site to a new site with different table_prefix so they can coexist on the same server.

Assuming you have a site in `./public_html/site1`, running `./public_html/wp_clone.py site1 site2 --db --copy --private` will create `./public_html/site2` with an exact copy of site1 but with `$table_prefix = site2`. All links in the content will be changed to point to `site2`. The database from site1 will be replacated with the new table prefix. le
