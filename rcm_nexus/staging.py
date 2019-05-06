from lxml import (objectify,etree)
import rcm_nexus.repo as repo

STAGE_START_FORMAT = '/service/local/staging/profiles/{profile_id}/start'
STAGE_FINISH_FORMAT = '/service/local/staging/profiles/{profile_id}/finish'

def _get_staging_description(product, version, is_ga):
    return "%s, ver %s (to %s)" % (product, version, "GA" if is_ga else "Early-Access") 

def start_staging_repo(session, config, product, version, is_ga):
    profile_id = config.get_profile_id( product, is_ga )

    path = STAGE_START_FORMAT.format(profile_id=profile_id)
    request_data = etree.Element('promoteRequest')
    data = etree.SubElement( request_data, 'data')
    etree.SubElement(data, 'description').text=_get_staging_description(product, version, is_ga)

    xml = etree.tostring( request_data, xml_declaration=True, pretty_print=True, encoding='UTF-8')
    (response, text) = session.post(path, xml)

    # TODO: Error handling!

    repo_id = etree.fromstring(text).xpath('/promoteResponse/data/stagedRepositoryId/text()')
    return repo_id[0]

def finish_staging_repo(session, config, repo_id, product, version, is_ga):
    profile_id = config.get_profile_id( product, is_ga )

    path = STAGE_FINISH_FORMAT.format(profile_id=profile_id)
    request_data = etree.Element('promoteRequest')
    data = etree.SubElement( request_data, 'data')
    etree.SubElement(data, 'description').text=_get_staging_description(product, version, is_ga)
    etree.SubElement(data, 'stagedRepositoryId').text=repo_id

    xml = etree.tostring( request_data, xml_declaration=True, pretty_print=True, encoding='UTF-8')
    (response,text) = session.post(path, xml)

    # TODO: Error handling!
    # FIXME: Handle verification failure!

