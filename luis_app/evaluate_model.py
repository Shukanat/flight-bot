import json
import time

import pandas as pd
from loguru import logger
import requests

from ..config import DefaultConfig
from create_dataset import load_json

CONFIG = DefaultConfig()

def check_response_ok_or_raise_for_status(response):
    if not response.ok:
        logger.info(response.content)
        response.raise_for_status()

def evaluate(env, is_staging, utterances, check_status_period=5):
    """Batch evaluation of luis model"""
    
    if is_staging:
        slots = "staging"
    else:
        slots = "production"
    
    # Evaluate
    response = requests.post(
        url=f"{env.LUIS_API_HOST_NAME}luis/v3.0-preview/apps/{env.LUIS_APP_ID}/slots/{slots}/evaluations",
        headers={
            "Ocp-Apim-Subscription-Key": env.LUIS_API_KEY,
        },
        json=utterances
    )
    
    # Check response
    check_response_ok_or_raise_for_status(response)
    
    operation_id = response.json()["operationId"]
    
    waiting = True
    while waiting:
        response = requests.get(
            url=f"{env.LUIS_API_HOST_NAME}luis/v3.0-preview/apps/{env.LUIS_APP_ID}/slots/{slots}/evaluations/{operation_id}/status",
            headers={
                "Ocp-Apim-Subscription-Key": env.LUIS_API_KEY,
            }
        )
        
        if response.json()["status"] == "failed":
            raise ValueError(response.content)
        
        waiting = response.json()["status"] in ["notstarted", "running"]
        
        if waiting:
            time.sleep(check_status_period)
        
    # Get results
    response = requests.get(
        url=f"{env.LUIS_API_HOST_NAME}luis/v3.0-preview/apps/{env.LUIS_APP_ID}/slots/{slots}/evaluations/{operation_id}/result",
        headers={
            "Ocp-Apim-Subscription-Key": env.LUIS_API_KEY,
        }
    )
    
    check_response_ok_or_raise_for_status(response)
    
    resultat = response.json()
    
    #we interested only in first intent stats
    resultat = pd.DataFrame([resultat["intentModelsStats"][0]] + resultat["entityModelsStats"])
    resultat.iloc[:, -3:] = resultat.iloc[:, -3:].astype(float)
    resultat.columns = [
        "model_name",
        "model_type",
        f"precision",
        f"recall",
        f"f_score",
    ]
    
    return resultat

def launch_eval(path_to_data: str = './', is_staging: bool = False):
    testSet = load_json(path_to_data + 'testSet.json')
    test_utterancies = {"LabeledTestSetUtterances": testSet}
    r = evaluate(CONFIG, is_staging, test_utterancies)
    print(r)

if __name__ == '__main__':
    launch_eval()