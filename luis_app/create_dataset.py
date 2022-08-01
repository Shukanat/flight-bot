import json
import pandas as pd
from sklearn.model_selection import train_test_split

INTENT = 'BookFlight'
LABEL_TO_ENTITY = {
    'dst_city': 'To',
    'or_city': 'From',
    'budget' : 'Budget'
}

LUIS_TRAIN_FORMAT = {
    "startPos" : "startCharIndex",
    "endPos" : "endCharIndex",
    "entity" : "entityName",
    "children" : "children"
}

def load_json(path: str) -> dict:
    with open(path, 'rb') as f:
        loaded = json.load(f)
    return loaded

def save_json(path: str, variable) -> None:
    with open(path, 'w') as f:
        json.dump(variable, f)

def turn_to_luis_utterance(turn: dict, intent_name: str, label_to_entity: dict) -> dict:
    """Convert a 'turn' of frames.json to LUIS dataset format."""
    
    text = turn["text"]
    intent = "None"
    entity_labels = []
    for i in turn["labels"]["acts_without_refs"]:
        for l in i["args"]:
            k = l["key"]
            v = l["val"]
            
            if k == "intent":
                # If label is present it's 'book' intent
                # that we map to our intent_name
                intent = intent_name
            elif k and v:
                # Other labels are entities
                if k in label_to_entity.keys():
                    start_char_index = text.lower().find(v.lower())
                    if start_char_index == -1:
                        continue
                    
                    end_char_index = start_char_index + len(v) - 1
                    
                    entity_labels.append({
                        "entity": label_to_entity[k],
                        "startPos": start_char_index,
                        "endPos": end_char_index,
                        "children": []
                    })
    
    res = {
        "text": text,
        "intent": intent,
        "entities": entity_labels,
    }
    return res


def user_turns_to_luis_ds(frames: list, intent_name: str, label_to_entity: dict) -> pd.DataFrame:
    """Convert 'turns' of frames.json to LUIS dataset format."""
    
    res = []
    for frame in frames:
        # To identify each turn in dialogue
        user_turn_id = 0
        
        for turn in frame["turns"]:
            # Only user's turns are considered
            if turn["author"] == "user":
                row = {"user_turn_id": user_turn_id}
                user_turn_id += 1
                row.update(turn_to_luis_utterance(turn, intent_name, label_to_entity))
                res.append(row)
    
    df = pd.DataFrame(res)
    
    df["entity_total_nb"] = df["entities"].apply(len)
    for entity_name in label_to_entity.values():
        df[f"{entity_name}_nb"] = df["entities"].apply(
            lambda x: len(list(
                filter(lambda x1: x1["entity"] == entity_name, x)
            ))
        )
    df["text_word_nb"] = df["text"].apply(lambda x: len(x.split()))
    
    return df

def recode_to_train_format(element):
    return {LUIS_TRAIN_FORMAT[k]:v for k, v in element.items()}

def texts_to_luis_utterances(df: pd.DataFrame, intent_name: str, train: bool = True) -> list:
    """Transform pandas' dataset to Luis train/test format"""
            
    utterances = []
    if train:
        for text, entity in zip(df.text, df.entities):
            utterances.append({
                "text": text,
                "intentName": intent_name,
                "entityLabels": [recode_to_train_format(el) for el in entity]
            })
    else:
        for text, entity in zip(df.text, df.entities):
            utterances.append({
                "text": text,
                "intent": intent_name,
                "entities": entity
            })
        
    return utterances

def create_dataset(path_to_data: str = './'):

    frames = load_json(path_to_data + 'frames.json')
    FlightBooking = load_json(path_to_data + 'FlightBooking.json')
    df = user_turns_to_luis_ds(frames, INTENT, LABEL_TO_ENTITY)
    df_filtered = df.loc[(df.intent == 'BookFlight') & (df.entity_total_nb != 0)]
    train, test = train_test_split(df_filtered, stratify=df_filtered.entity_total_nb, test_size=0.1, random_state=42)
    converted_train = texts_to_luis_utterances(train, INTENT)
    converted_test = texts_to_luis_utterances(test, INTENT, train=False)

    transformed = []
    for utterance in FlightBooking['utterances']:
        transformed.append({
                    "text": utterance['text'],
                    "intentName": utterance['intent'],
                    "entityLabels": [recode_to_train_format(el) for el in utterance['entities']]
                })

    converted_train = transformed + converted_train

    save_json('trainSet.json', converted_train)
    save_json('testSet.json', converted_test)

if __name__ == '__main__':
    create_dataset()
