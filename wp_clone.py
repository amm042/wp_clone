#!/usr/bin/env python3
"""clone a wordpress site, changing prefix and fixing up all
   necessary tables.

   assumes python3.

   rougly based on
   http://tdot-blog.com/wordpress/6-simple-steps-to-change-your-table-prefix-in-wordpress

   Alan Marchiori 2016

   Note, you can clone sites that use SqlLite by leaving off the DB option,
   however you might have to fixup the wp-config file by hand. (change the
   table prefix back to the old value and check siteurl and homeurl)

"""
import os
import os.path
import sys
import re
#import mysql.connector as sql
import MySQLdb as sql
from pprint import pprint
import urllib.parse
import shutil
import tempfile

def read_wp_config(cfile):
    'parses the wp config into a dict'
    defs = re.compile("'(.*?)',\s*'(.*?)'")
    vars = re.compile("\$(\w+)\s*=\s*'(\w+)")
    config = {}
    with open (cfile, 'r') as fp:
        for line in fp:
            for match in defs.finditer(line):
                config[match.group(1)] = match.group(2)
            for match in vars.finditer(line):
                config[match.group(1)] = match.group(2)
    return config

def connect(host, user, passwd, database):
    return sql.connect(user=user, password= passwd,
    host=host, database=database)

def getoptions(cursor, wp_prefix, options):
    r = []
    for opt in options:
        cursor.execute(
            "SELECT option_value FROM {}options WHERE option_name = '{}'".format(
            wp_prefix, opt))
        res = cursor.fetchone()[0]
        r.append(res)
    return tuple(r)

def prompt_continue():
    x = None
    while x == None or (len(x)> 0 and x.lower()[0] not in ['y', 'n']):
        x = input("Continue [y/N]: ")
    if (x == "" or x.lower()[0] == 'n'):
        print("Abort", file=sys.stderr)
        exit(-5)
def select_url(prompt, old_url, dst_prefix):
    o = urllib.parse.urlparse(old_url)
    paths = []
    parts = o.path.split('/')
    x = None
    #o = list(o)
    #o.remove("")
    #parts.remove("")
    print("dst_prefix ", dst_prefix)
    print (old_url)
    print (o)
    print (parts)
    opts = [urllib.parse.urlunparse( (o[0], o[1], "/".join(parts[:-i] + [dst_prefix])) + o[3:])
        for i in range(len(parts))]

    while x == None or int(x) not in range(len(parts)):
        for i,op in enumerate(opts):
            print("[{}]: {}".format(i, op))
        x = input(prompt)
        try:
            y = int(x)
        except:
            print("enter a number!")
            x = None
    return opts[int(x)]

def clone(wp_src_path, wp_dst_path, wp_dst_prefix,
    db=False, copy=False, private=True, **kwargs):

    config = read_wp_config(os.path.join(args.src, 'wp-config.php'))

    wp_dst_path = wp_dst_path[2:]
    print("dst_prefix ",wp_dst_prefix)
    print("dst_path", wp_dst_path)


    if (db):

        print("--Processing database.")
        dbx = connect(
                config['DB_HOST'], config['DB_USER'],
                config['DB_PASSWORD'], config['DB_NAME'])
        cursor = dbx.cursor()

        siteurl, home = getoptions(
            cursor, config['table_prefix'], ['siteurl', 'home'])

    else:
        dbx = None
        cursor = None

        if 'WP_SITEURL' not in config or 'WP_HOME' not in config:
            print("Must run with DB if WP_HOME and WP_SITEURL are NOT defined in your wp-config.php file.")
            exit(-4)

        siteurl = config['WP_SITEURL']
        home = config['WP_HOME']

    try:


        print("Source siteurl: {}".format(siteurl))
        print("Source home: {}".format(home))

        if siteurl.endswith(config['table_prefix'][:-1]):
            new_siteurl = siteurl.replace(
                config['table_prefix'][:-1],
                wp_dst_prefix)
        else:
            new_siteurl = select_url("Choose the new site url: ",
                siteurl, os.path.join(wp_dst_path, wp_dst_prefix))

        if home.endswith(config['table_prefix'][:-1]):
            new_home = home.replace(
                config['table_prefix'][:-1],
                wp_dst_prefix)
        else:
            new_home = select_url("Choose the new home: ",
                home, os.path.join(wp_dst_path, wp_dst_prefix))

        print("New siteurl: {}".format(new_siteurl))
        print("New home: {}".format(new_home))

        prompt_continue()

        if copy == False:
            print("WARN: not copying source files (set --copy to enable)")
        else:
            # copy filesystem and .httaccess
            print("Copy filesystem {} -> {}".format(
                wp_src_path,
                os.path.join(wp_dst_path, wp_dst_prefix)
            ))
            shutil.copytree(wp_src_path, os.path.join(wp_dst_path, wp_dst_prefix))

        # modify .httaccess [RewriteRule, update table_prefix]
        new_htaccess = os.path.join(
            wp_dst_path, wp_dst_prefix, '.htaccess')
        if os.path.exists(new_htaccess):
            with tempfile.NamedTemporaryFile(mode='w', delete=False) as new_hf:

                with open(new_htaccess, 'r') as old_hf:
                    print("Modify {}.".format(old_hf.name))
                    xfrom = config['table_prefix'].strip("_")
                    xto = wp_dst_prefix
                    for line in old_hf:
                        new_hf.write(line.replace(xfrom, xto))
            shutil.move(new_hf.name, old_hf.name)
            # have to set permissions to 0644 because tempfile is 0600
            os.chmod(old_hf.name, 0o644)
        else:
            print("WARN: no .htaccess file at {}."
                .format(new_htaccess))

        # modify wp-config.php [$table_prefix = new_table_prefix;]
        new_config_filename = os.path.join(
            wp_dst_path, wp_dst_prefix, 'wp-config.php')
        if os.path.exists(new_config_filename):
            with tempfile.NamedTemporaryFile(mode='w', delete=False) as new_config:
                with open(new_config_filename, 'r') as old_config:
                    print("Modify {}.".format(old_config.name))
                    for line in old_config:
                        if line.startswith("$table_prefix"):
                            new_config.write("$table_prefix = '{}_';\n".format(wp_dst_prefix))
                        else:
                            new_config.write(line)
            shutil.move(new_config.name, old_config.name)
        else:
            print("The destination wp-config file cannot be found, it should be at {}"
                .format(new_config_filename), file=sys.stderr)
            exit(-6)

        # copy database
        if db == False:
            print("WARN: not cloning database (set --db to enable).")
        else:
            cursor.execute('SHOW TABLES')
            tables = cursor.fetchall()
            for (table_name,) in tables:
                if table_name.startswith(config['table_prefix']):
                    new_table = table_name.replace(
                        config['table_prefix'], wp_dst_prefix+'_')
                    print("Cloning {} --> {}".format(table_name, new_table), end="")

                    cursor.execute("SHOW CREATE TABLE {}".format(table_name))
                    tname, ccmd = cursor.fetchone()
                    ccmd = ccmd.replace(
                        '`{}`'.format(table_name),
                        "`{}`".format(new_table))
                    cursor.execute("DROP TABLE IF EXISTS `{}`".format(new_table))
                    cursor.execute(ccmd)

                    cursor.execute("INSERT INTO {} SELECT * FROM {}".format(
                        new_table,
                        table_name))

                    print(", copied {} records.".format(cursor.rowcount))
                    dbx.commit()

            # fixup the new tables
            cursor.execute('SHOW TABLES')
            tables = cursor.fetchall()
            for (table_name,) in tables:
                if table_name.startswith(wp_dst_prefix):
                    print("fixup {}".format(table_name))

                    if table_name == "{}_options".format(wp_dst_prefix):
                        cursor.execute("UPDATE {} SET option_value = '{}' WHERE option_name = 'siteurl'"\
                            .format(table_name, new_siteurl))
                        cursor.execute("UPDATE {} SET option_value = '{}' WHERE option_name = 'home'"\
                            .format(table_name, new_home))
                        cursor.execute("SELECT option_id, option_name FROM {} WHERE option_name like '%{}%'"
                            .format(table_name, config['table_prefix']))
                        rows = cursor.fetchall()
                        for (optid, optname) in rows:
                            new_optname = optname.replace(config['table_prefix'], wp_dst_prefix+'_')
                            print("change {}.{} -> {}.{}".format(optid, optname, optid, new_optname), end="")
                            cursor.execute("UPDATE {} SET option_name = '{}' WHERE option_id = {}"
                                .format(table_name, new_optname, optid))
                            print (", changed {} records.".format(cursor.rowcount))
                        dbx.commit()
                    elif table_name == "{}_usermeta".format(wp_dst_prefix):
                        cursor.execute("SELECT umeta_id, user_id, meta_key FROM {} WHERE meta_key like '%{}%'"
                            .format(table_name, config['table_prefix']))
                        rows = cursor.fetchall()
                        for (umeta_id, user_id, meta_key) in rows:
                            new_key = meta_key.replace(config['table_prefix'], wp_dst_prefix+'_')

                            print("change {}.{}.{} -> {}.{}.{}".format(
                                umeta_id, user_id, meta_key,
                                umeta_id, user_id, new_key), end="")
                            cursor.execute("UPDATE {} SET meta_key = '{}' WHERE umeta_id = {} and user_id = {}"
                                .format(table_name, new_key, umeta_id, user_id))
                            print (", changed {} records.".format(cursor.rowcount))
                        dbx.commit()
                    elif table_name == "{}_posts".format(wp_dst_prefix):

                        cursor.execute("SELECT ID, guid FROM {} WHERE guid like '{}%'"
                            .format(table_name, siteurl))
                        rows = cursor.fetchall()
                        changes = []
                        for (pid, guid) in rows:
                            new_guid = guid.replace(siteurl, new_siteurl)
                            print("change guid {}.{} -> {}.{}".format(pid,guid,pid,new_guid))
                            changes.append((new_guid, pid))

                        print ("Updating {} guids (wait for db)".format(len(changes)), flush = True, end = "")
                        cursor.executemany(
                            "UPDATE {} SET guid = %s WHERE ID = %s".format(table_name),
                            changes)
                        print (", updated {} guids.".format(cursor.rowcount))
                        dbx.commit()
                        del changes

                        cursor.execute("SELECT ID, post_content FROM {}"
                            .format(table_name))
                        rows = cursor.fetchall()
                        changes = []
                        for (pid, content) in rows:
                            if siteurl in content:
                                new_content = content.replace(siteurl, new_siteurl)
                                print("update urls in post ID {}".format(pid))
                                changes.append((new_content, pid))

                        print ("Updating {} posts (wait for db)".format(len(changes)), flush = True, end = "")
                        cursor.executemany(
                            "UPDATE {} SET post_content = %s WHERE ID = %s".format(table_name),
                            changes
                        )
                        print (", updated {} posts.".format(cursor.rowcount))
                        dbx.commit()
                        del changes

        if db and private == True:
            print("Marking posts pending/private", end="")
            cursor.execute("UPDATE {}_posts SET post_status = 'pending' WHERE post_status = 'publish' and post_type='post'"
                .format(wp_dst_prefix))
            print(", modified {} posts.".format(cursor.rowcount))
            dbx.commit()


    finally:
        dbx.close()


if __name__=="__main__":
    import argparse

    p = argparse.ArgumentParser(description="Clone a wordpress site to a new prefix on the same server.")
    p.add_argument('src', help='root path of the source wordpress install.')
    p.add_argument(
        'dst_prefix',
        help='database prefix to use for clone, the new site will be put in dst_path/dst_prefix.')
    p.add_argument(
        '--dst_path',
        help='path to locate new clone on the filesystem.',
        default = './')
    p.add_argument(
        '--exists',
        help='proceed even if the destination exists [default=False].',
        action = 'store_true',
        default = False)
    p.add_argument(
        '--db',
        help='clone the database (set this unless you copy the db manually).',
        action = 'store_true',
        default = False
    )
    p.add_argument(
        '--copy',
        help='copy files to the destination path (set this unless you copy the files manually).',
        action = 'store_true',
        default = False
    )
    p.add_argument(
        '--private',
        help='sets all *posts* to pending (not pages!) [default=False].',
        action = 'store_true',
        default = False
    )
    args = p.parse_args()

    dst_site = os.path.join(args.dst_path, args.dst_prefix)
    print("Cloning site at {} to {}".format(
        args.src, dst_site
    ))

    if args.exists == False and os.path.exists (dst_site):
        print("The destination site already exists!, remove {} and try again."
            .format(dst_site), file=sys.stderr)
        exit(-1)

    if args.dst_prefix.endswith("_"):
        print("An underscore is automatically appended in the dst prefix.")
        exit(-2)

    clone(args.src, args.dst_path, args.dst_prefix, **vars(args))
