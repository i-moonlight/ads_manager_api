from linkedin_api.clients.restli.client import RestliClient

restli_client = RestliClient()

def update_linkedin_campaign(access_token, api_id, new_campaign):
    counter = 0

    while True:
        response = restli_client.partial_update(
            resource_path='/adCampaignGroupsV2/{id}',
            path_keys={'id': api_id},
            patch_set_object=new_campaign,
            access_token=access_token
        )

        if response.status_code != 204:
            if counter == 5:
                return {
                    'message': str(response.entity['message'])
                }

            counter += 1
        else:
            return {
                'message': ''
            }

def update_linkedin_adset(access_token, api_id, new_adset):
    counter = 0

    while True:
        response = restli_client.partial_update(
            resource_path="/adCampaignsV2/{id}",
            path_keys={"id": api_id},
            patch_set_object=new_adset,
            access_token=access_token,
        )

        if response.status_code != 204:
            if counter == 5:
                return {
                    'message': str(response.entity['message'])
                }

            counter += 1
        else:
            return {
                'message': ''
            }

def update_linkedin_ad(access_token, api_id, new_ad):
    reference = restli_client.get(
        resource_path='/adCreativesV2/{id}',
        path_keys={'id': api_id},
        access_token=access_token
    ).entity['reference']

    counter = 0

    while True:
        response = restli_client.partial_update(
            resource_path='/adDirectSponsoredContents/{id}',
            path_keys={'id': reference},
            patch_set_object=new_ad,
            access_token=access_token
        )

        if response.status_code != 204:
            if counter == 5:
                return {
                    'message': str(response.entity['message'])
                }

            counter += 1
        else:
            return {
                'message': ''
            }

def update_linkedin_location(access_token, api_id, location_names):
    entities = []

    for l in location_names:
        response = restli_client.finder(
            resource_path='/geoTypeahead',
            finder_name='search',
            query_params={
                'query': l
            },
            access_token=access_token,
            version_string='202308'
        )

        if response.elements:
            entities.append(response.elements[0]['entity'])

    counter = 0

    while True:
        response = restli_client.partial_update(
            resource_path="/adCampaignsV2/{id}",
            path_keys={"id": api_id},
            patch_set_object={
                "targetingCriteria": {
                    "include": {
                        "and": [
                            {
                                "or": {
                                    "urn:li:adTargetingFacet:locations": entities
                                }
                            }
                        ]
                    }
                }
            },
            access_token=access_token,
        )

        if response.status_code != 204:
            if counter == 5:
                return {
                    'message': str(response.entity['message'])
                }

            counter += 1
        else:
            return {
                'message': ''
            }
