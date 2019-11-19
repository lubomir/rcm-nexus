import json

CREATE_PRODUCT_PATH = "/service/local/staging/profiles"
ROLES_PATH = "/service/local/roles/{role}"


HEADERS = {"Accept": "application/json", "Content-Type": "application/json"}


def create_product(session, name, target_group, ruleset, promotion_target):
    data = {
        "data": {
            "name": name,
            "repositoryTemplateId": "default_hosted_release",
            "repositoryType": "maven2",
            "repositoryTargetId": "1",
            "targetGroups": [target_group],
            "promoteRuleSets": [ruleset],
            "promotionTargetRepository": promotion_target,
            "dropNotifyCreator": True,
            "finishNotifyCreator": True,
            "promotionNotifyCreator": True,
            "autoStagingDisabled": True,
            "repositoriesSearchable": True,
            "mode": "DEPLOY",
            "finishNotifyRoles": [],
            "promotionNotifyRoles": [],
            "dropNotifyRoles": [],
            "closeRuleSets": [],
            "properties": {}
        }
    }
    response, _ = session.post(CREATE_PRODUCT_PATH, json.dumps(data), headers=HEADERS)
    return response.json()["data"]["id"]


def modify_permissions(session, product_id, deployer_role):
    path = ROLES_PATH.format(role=deployer_role)
    response, _ = session.get(path, headers={"Accept": "application/json"})
    data = response.json()
    for prefix in ("staging-deployer-", "staging-promoter-"):
        data["data"]["roles"].append(prefix + product_id)

    session.put(path, json.dumps(data), headers=HEADERS)
