import time

from azure.cognitiveservices.language.luis.authoring import LUISAuthoringClient
from azure.cognitiveservices.language.luis.authoring.models import \
    ApplicationCreateObject
from azure.cognitiveservices.language.luis.runtime import LUISRuntimeClient
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from loguru import logger
from msrest.authentication import CognitiveServicesCredentials

from create_dataset import load_json

credential = DefaultAzureCredential()
secret_client = SecretClient(vault_url="https://chatbot-vault.vault.azure.net/", credential=credential)

predictionKey = secret_client.get_secret('LuisAPIKey').value
autoringKey = secret_client.get_secret('LuisAutoringAPIKey').value 
autoringPredictionEndpoint = 'https://' + secret_client.get_secret('LuisAPIHostName').value

def chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

TrainSet = load_json('./trainSet.json')
versionId = '0.1'

def main():

    ### CONFIG ###
    appName = "BookFlight"
    versionId = "0.1"
    culture = "en-us"
    appDefinition = ApplicationCreateObject(name=appName, initial_version_id=versionId, culture=culture)
    client = LUISAuthoringClient(autoringPredictionEndpoint, CognitiveServicesCredentials(autoringKey))

    ### CREATE APP ###
    appId = client.apps.add(appDefinition)
    logger.info(f'Application created with id: {appId}')

    ### CREATE INTENTS ###
    intents = ["BookFlight", "GetWeather", "Cancel"]
    for intent in intents:
        client.model.add_intent(appId, versionId, intent)
    logger.info(f"Created LUIS intents: {intents}")

    ### ADD PREBUILD ENTITY ###
    prebuilt_entities = ["geographyV2", "datetimeV2", "money"]
    client.model.add_prebuilt(appId, versionId, prebuilt_extractor_names=prebuilt_entities)
    logger.info(f"Added prebuilt entities: {prebuilt_entities}")
    
    ### ADD MACHINE LEARNING ENTITIES ###
    ml_entities = ['From', 'To', 'Budget']
    ml_entities_ids = {}
    for entity in ml_entities:
        id = client.model.add_entity(appId, versionId, name=entity)
        ml_entities_ids[entity] = id
    logger.info(f'Added ml entities: {ml_entities}')    

    ### ADD MODELS AS ENTITY'S FEATURE
    geography_feature = {
        "model_name": "geographyV2",
        "is_required": False,
    }
    client.features.add_entity_feature(appId, versionId, ml_entities_ids['From'], geography_feature)
    client.features.add_entity_feature(appId, versionId, ml_entities_ids['To'], geography_feature)

    money = {
        "model_name": "money",
        "is_required": False,
    }
    client.features.add_entity_feature(appId, versionId, ml_entities_ids['Budget'], money)

    ### ADD DATA AND TRAIN ###
    for chunk in chunks(TrainSet, 100):
        client.examples.batch(appId, versionId, chunk)

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
