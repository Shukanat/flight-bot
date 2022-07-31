import json
import time

from azure.cognitiveservices.language.luis.authoring import LUISAuthoringClient
from azure.cognitiveservices.language.luis.runtime import LUISRuntimeClient
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from loguru import logger
from msrest.authentication import CognitiveServicesCredentials

credential = DefaultAzureCredential()
secret_client = SecretClient(vault_url="https://chatbot-vault.vault.azure.net/", credential=credential)

predictionKey = secret_client.get_secret('LuisAPIKey').value
autoringKey = secret_client.get_secret('LuisAutoringAPIKey').value 
autoringPredictionEndpoint = 'https://' + secret_client.get_secret('LuisAPIHostName').value

def load_json(path: str) -> dict:
    with open(path, 'rb') as f:
        loaded = json.load(f)
    return loaded

FlightBooking = load_json('./models/FlightBooking.json')
TrainSet = load_json('./models/TrainSet.json')
versionId = '0.1'

def main():

    ### IMPORT OF THE APP ###
    client = LUISAuthoringClient(autoringPredictionEndpoint, CognitiveServicesCredentials(autoringKey))
    appId = client.apps.import_v2_app(FlightBooking)

    ### ADD NEW ENTITIES ###
    client.model.add_prebuilt(appId, versionId, prebuilt_extractor_names=["number"])

    mlEntityDefinition = [{"name": "Amount"}]
    modelId = client.model.add_entity(appId, versionId, name="Budget", children=mlEntityDefinition)

    modelObject = client.model.get_entity(appId, versionId, modelId)
    childrenId = modelObject.as_dict()['children'][0]['id']

    prebuiltFeatureRequiredDefinition = {"model_name": "number", "is_required": True}
    client.features.add_entity_feature(appId, versionId, childrenId, prebuiltFeatureRequiredDefinition)

    ### ADD NEW EXEMPLES AND TRAIN ###
    client.examples.batch(appId, versionId, TrainSet)

    client.train.train_version(appId, versionId)
    logger.info('Start to train the model')
    waiting = True
    while waiting:
        info = client.train.get_status(appId, versionId)
        waiting = any(map(lambda x: 'Queued' == x.details.status or 'InProgress' == x.details.status, info))
        if waiting:
            logger.info("Waiting 5 more seconds for training to complete...")
            time.sleep(5)
        else: 
            logger.info("Done")
            waiting = False

    ### PUBLISH TO PROD ###
    client.apps.update_settings(appId, is_public=True)
    responseEndpointInfo = client.apps.publish(appId, versionId, is_staging=False)
    logger.info(f"Model is published: {responseEndpointInfo.as_dict()['endpoint_url']}")

    ### TEST ###
    runtimeCredentials = CognitiveServicesCredentials(predictionKey)
    clientRuntime = LUISRuntimeClient(endpoint=autoringPredictionEndpoint, credentials=runtimeCredentials)

    predictionRequest = { "query" : "Hi. I need to book a vacation to Long Beach between August 25 and September 3. Departure is from Paris" }
    predictionResponse = clientRuntime.prediction.get_slot_prediction(appId, "Production", predictionRequest)
    assert predictionResponse.prediction.top_intent == 'BookFlight'
    logger.info('Test passed')

if __name__ == '__main__':
    main()