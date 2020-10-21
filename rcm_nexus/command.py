from __future__ import print_function

from rcm_nexus.session import Session
import rcm_nexus.config as config
import rcm_nexus.repo as repos
import rcm_nexus.archive as archive
import rcm_nexus.staging as staging
import os.path
import sys
import click
import requests
import shutil
import tempfile
import npm
import subprocess

from .product import create_product, modify_permissions
from . import checker


@click.command()
def init():
    """Create a starter configuration for rcm-nexus.

    More information: https://mojo.redhat.com/docs/DOC-1199638
    """
    conf_path = config.init_config()
    print("""Wrote starter config to:

    %s

    Next steps:

    - Fine tune each environment's configuration (username, ssl-verify, etc.).
    - Setup passwords (`pass` is a nice tool for this) to match the configured password keys.

    For more information on using rcm-nexus (nexus-push etc.), see:

    https://mojo.redhat.com/docs/DOC-1199638
    """ % conf_path)


@click.command()
def list_of_commands():
    """Commands available:

     - nexus - this command - list of available actions

     - nexus-add-npm-product - adds a new npm product

     - nexus-add-product - adds a new Maven product (and staging profile)

     - nexus-check - checks Nexus deployment

     - nexus-init - create a configuration file with default values

     - nexus-list-products - lists configured products

     - nexus-push - pushes new releases to Nexus

     - nexus-rollback - revokes a Maven release"""
    print(subprocess.check_output(["nexus", "--help"]))


@click.command()
@click.argument('repo', type=click.Path(exists=True))
@click.option(
    "--environment",
    "-e",
    help="The target Nexus environment (from config file)",
    default="prod",
)
@click.option('--product', '-p', help='The product key, used to lookup profileId from the configuration', nargs=1,
              required=True)
@click.option('--version', '-v', help='The product version, used in repository definition metadata', multiple=False)
@click.option('--ga', '-g', is_flag=True, default=False, multiple=False,
              help='Push content to the GA group (as opposed to earlyaccess)')
@click.option('--debug', '-D', is_flag=True, default=False)
def push(repo, environment, product, version, ga=False, debug=False):
    """Push Apache Maven repository content to a Nexus staging repository, 
    then add the staging repository to appropriate content groups.

    More information: https://mojo.redhat.com/docs/DOC-1199638
    """

    nexus_config = config.load(environment)
    npm_archive_type = npm.detect_npm_archive(repo)
    if npm_archive_type != npm.NpmArchiveType.NOT_NPM:
        npm.push(nexus_config, repo, npm_archive_type, product, debug=debug)
    else:
        if nexus_config.get_profile_type(product) != config.ProfileType.JAVA:
            print(product + " is not a java product!", file=sys.stderr)
            exit(1)

        session = Session(nexus_config, debug=debug)
        print("Pushing: %s content to: %s" % (repo.decode("utf-8"), environment))

        zips_dir = None
        try:
            # produce a set of clean repository zips for PUT upload.
            zips_dir = tempfile.mkdtemp()
            print("Creating ZIP archives in: %s" % zips_dir)
            if os.path.isdir(repo):
                print("Processing repository directory: %s" % repo)

                # Walk the directory tree, and create a zip.
                zip_paths = archive.create_partitioned_zips_from_dir(repo, zips_dir)
            else:
                print("Processing repository zip archive: %s" % repo)

                # Open the zip, walk the entries and normalize the structure to
                # clean zip
                zip_paths = archive.create_partitioned_zips_from_zip(
                    repo, zips_dir, debug=debug
                )

            # Open new staging repository with description
            staging_repo_id = staging.start_staging_repo(session, nexus_config, product, version, ga)

            # HTTP PUT clean repository zips to Nexus.
            delete_first = True
            for idx, zipfile in enumerate(zip_paths, start=1):
                print("Uploading zip %s out of %s" % (idx, len(zip_paths)))
                repos.push_zip(session, staging_repo_id, zipfile, delete_first)
                delete_first = False

            # Close staging repository
            staging.finish_staging_repo(session, nexus_config, staging_repo_id, product, version, ga)

            if staging.verify_action(session, staging_repo_id, "close"):
                sys.exit(1)

            print("Promoting repo")
            profiles = nexus_config.get_promote_profile_ids(product, ga)
            promote_entity = None
            for promote_profile in profiles:
                if not promote_entity:
                    # First iteration, promote staging repo directly.
                    promote_entity = staging_repo_id
                else:
                    # On every other iteration promote the group created by
                    # previous promotion.
                    promote_entity = staging.get_next_promote_entity(
                        session, promote_entity
                    )
                staging.promote(
                    session, promote_profile, promote_entity, product, version, ga
                )

                if staging.verify_action(session, promote_entity, "promote"):
                    sys.exit(1)
        except RuntimeError as exc:
            if debug:
                raise
            print("Error: %s" % exc, file=sys.stderr)
            sys.exit(1)
        except requests.exceptions.HTTPError as exc:
            if debug:
                raise
            print("Network error: %s" % exc, file=sys.stderr)
            sys.exit(1)
        finally:
            if session is not None:
                session.close()
            if zips_dir:
                shutil.rmtree(zips_dir)
        print("Deployment successfully finished.")


@click.command()
@click.argument('staging_repo_name')
@click.option('--environment', '-e', help='The target Nexus environment (from config file)')
@click.option('--debug', '-D', is_flag=True, default=False)
def rollback(staging_repo_name, environment, debug=False):
    """Drop given staging repository.

    More information: https://mojo.redhat.com/docs/DOC-1199638
    """
    nexus_config = config.load(environment)

    session = Session(nexus_config, debug=debug)

    try:
        print("Dropping repository %s" % staging_repo_name)
        if not staging.drop_staging_repo(session, staging_repo_name):
            sys.exit(1)
    except requests.exceptions.HTTPError as exc:
        if debug:
            raise
        print("Network error: %s" % exc, file=sys.stderr)
        sys.exit(1)
    finally:
        if session is not None:
            session.close()


@click.command()
@click.option(
    "--environment",
    "-e",
    help="The target Nexus environment (from config file)",
    default="prod",
)
@click.option("--npm", help="Display only npm products", is_flag=True, default=False)
@click.option("--java", "--mvn", "---maven", help="Display only java products", is_flag=True, default=False)
def list_products(environment, npm, java):
    """ Lists all configured products. It is possible to filter the results to npm/java products using the switches. """
    nexus_config = config.load(environment)
    fmt = None
    if sys.stdout.isatty():
        if npm == java:
            # print all by default
            fmt = "%-4s %-20s%-30s%-20s%-20s%-20s"
            print("\033[1m" + (fmt % ("Type", "Key", "Product Name", "EA", "GA", "NPM Repository")) + "\033[0m")
        elif java:
            fmt = "%-20s%-30s%-20s%-20s"
            print("\033[1m" + (fmt % ("Key", "Product Name", "EA", "GA")) + "\033[0m")
        else:
            fmt = "%-20s%-30s%-20s"
            print("\033[1m" + (fmt % ("Key", "Product Name", "NPM Repository")) + "\033[0m")

    for product in sorted(nexus_config.profile_map.keys()):
        product_type,  product_name, ga_id, ea_id, npm_repository = nexus_config.get_profile_data(product)
        if npm == java and product_type:
            # print everything but UNKNOWN product type
            print(fmt % (
                config.ProfileType(product_type).name,
                product,
                product_name,
                ga_id,
                ea_id,
                npm_repository)
                  )
        elif java and product_type == config.ProfileType.JAVA:
            print(fmt % (
                product,
                product_name,
                ga_id,
                ea_id)
                  )
        elif npm and product_type == config.ProfileType.NPM:
            print(fmt % (
                product,
                product_name,
                npm_repository)
                  )


@click.command()
@click.argument("product_name")
@click.argument("product_key")
@click.argument("repository_name")
@click.option(
    "--environment",
    "-e",
    help="The target Nexus environment (from config file)",
    default="prod",
)
@click.option("--debug", "-D", is_flag=True, default=False, help="if flagged, more information will be logged")
def add_npm_product(product_name, product_key, environment, repository_name, debug):
    """Creates a new NPM product in the shared configuration file. More information: https://mojo.redhat.com/docs/DOC-1199638

    PRODUCT_NAME is the name of the product to be stored in the configuration file for easier reading

    PRODUCT_KEY is the key under which it will be created

    ENVIRONMENT -  working environment (prod by default)

    REPOSITORY_NAME - name of the repository in Nexus
    """
    nexus_config = config.load(environment)
    try:
        with config.cloned_repo(nexus_config) as cloned_repo:
            print("Creating npm product in Nexus...")
            try:
                config.add_npm_product(cloned_repo, product_key, product_name, repository_name)
            except Exception as exc:
                print("Failed to update configuration npm repo: %s" % exc, file=sys.stderr)
                sys.exit(1)

    except RuntimeError as exc:
        if debug:
            raise
        print(str(exc), file=sys.stderr)
        sys.exit(1)


@click.command()
@click.argument("product_name")
@click.argument("product_key")
@click.option(
    "--environment",
    "-e",
    help="The target Nexus environment (from config file)",
    default="prod",
)
@click.option(
    "--target-group",
    help=(
            "Which target groups should contain artifacts from this product "
            "before promotion"
    ),
)
@click.option(
    "--promote-ruleset",
    help=(
            "Identifier of the rule sets that will validate when attempting to promote "
            "the release to MRRC"
    )

)
@click.option(
    "--promotion-target",
    help=(
            "The repository where the artifacts will be cleaned up after it is safe "
            "to move them from the temporary status"
    ),
)
@click.option("--debug", "-D", is_flag=True, default=False)
def add_product(
        product_name,
        product_key,
        environment,
        target_group,
        promote_ruleset,
        promotion_target,
        debug,
):
    """Creates a new product in Nexus and updates configuration so it can be used.

    PRODUCT_NAME is the name used by the Nexus service

    PRODUCT_KEY is the shorthand used to reference the product by rcm-nexus tools

    More information: https://mojo.redhat.com/docs/DOC-1199638
    """
    ids = {}
    nexus_config = config.load(environment)
    session = Session(nexus_config, debug=debug)

    try:
        with config.cloned_repo(nexus_config) as cloned_repo:

            print("Creating product in Nexus...")
            try:
                ids = {
                    config.IS_GA: create_product(
                        session,
                        product_name,
                        target_group or nexus_config.target_groups[config.IS_GA],
                        promote_ruleset or nexus_config.promote_ruleset[config.IS_GA],
                        promotion_target or nexus_config.promote_target[config.IS_GA],
                    ),
                    config.IS_EA: create_product(
                        session,
                        product_name + " Early Access",
                        target_group or nexus_config.target_groups[config.IS_EA],
                        promote_ruleset or nexus_config.promote_ruleset[config.IS_EA],
                        promotion_target or nexus_config.promote_target[config.IS_EA],
                    ),
                }
            except requests.exceptions.HTTPError:
                if debug:
                    raise
                sys.exit(1)

            print("Updating permissions")
            for product_id in ids.values():
                modify_permissions(session, product_id, nexus_config.deployer_role)

            try:
                config.add_product(cloned_repo, product_key, product_name, ids)
            except Exception as exc:
                print("Failed to update configuration repo: %s" % exc, file=sys.stderr)
                print("Add the following manually:", file=sys.stderr)
                print(
                    "\n[%s]\nga = %s\nea = %s\n"
                    % (product_key, ids[config.IS_GA], ids[config.IS_EA])
                )
                sys.exit(1)
    except RuntimeError as exc:
        if debug:
            raise
        print(str(exc), file=sys.stderr)
        sys.exit(1)


@click.command()
@click.argument('repo', type=click.Path(exists=True))
@click.option(
    "--environment",
    "-e",
    help="The target Nexus environment (from config file)",
    default="prod",
)
@click.option('--debug', '-D', is_flag=True, default=False)
def check(repo, environment, debug=False):
    nexus_config = config.load(environment)
    if not nexus_config.web_url:
        print("Missing option %s in config file" % config.WEB_URL, file=sys.stderr)
        sys.exit(1)
    session = Session(nexus_config, debug=debug)
    if debug:
        print("Checking file", repo)
    try:
        if not checker.check_zip_file(session, nexus_config.web_url, repo):
            sys.exit(1)
    except requests.exceptions.HTTPError as exc:
        if debug:
            raise
        print("Network error: %s" % exc, file=sys.stderr)
        sys.exit(1)
