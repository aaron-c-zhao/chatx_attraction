# This files contains your custom actions which can be used to run
# custom Python code.
#
# See this guide on how to implement these action:
# https://rasa.com/docs/rasa/custom-actions


# This is a simple example for a custom action which utters "Hello World!"

from typing import Any, Text, Dict, List

from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import AllSlotsReset, FollowupAction

import requests
import json
import config
import difflib


json_file= open('attractions_filter.json')
filterv2 = json.load(json_file)
json_file.close()
attractionType = {}
for option in filterv2['filter_sections'][3]['filter_groups'][0]['options']:
    attractionType[option['label'].lower()] = option['value']


class ActionConfirmFoodPreference(Action):

    def name(self) -> Text:
        return "action_confirm_attraction_preference"

    def run(self, dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
    
        dispatcher.utter_message(
            json_message={
                "text": " Looking for a {attraction} at {loc}?" \
                    .format(loc=tracker.slots['location'], attraction=tracker.slots['attraction']),
                "type": "confirm"
            }
        )
        return []

class ActionSendQuery(Action): 
    def __init__(self):
        self.loc_dic = {}

    def name(self) -> Text:
        return "action_send_query"
        
    def __findCuisineId(self, tracker):
        targetCuisine = tracker.slots['attraction'].lower()
        res = difflib.get_close_matches(targetCuisine, attractionType)
        if not len(res):
            return 'undefined'
        else:
            return res[0]
        

    def run(self, dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        loc = tracker.slots['location']
        loc_id = 188626

        headers = {
            'x-rapidapi-key': config.config['rapidAPIKey'],
            'x-rapidapi-host': "travel-advisor.p.rapidapi.com"
        }

        if loc in self.loc_dic:
            loc_id = self.loc_dic[loc]
        else:
            url = "https://travel-advisor.p.rapidapi.com/locations/search"
            querystring = {"query":"{location}".format(location=tracker.slots['location']),"limit":"30","offset":"0",\
                "units":"km","location_id":"1","currency":"USD","sort":"relevance","lang":"en_US"}

            response = requests.request("GET", url, headers=headers, params=querystring)

            dict_response = response.json()        
            loc_id = dict_response['data'][0]['result_object']['location_id']
            self.loc_dic[loc] = loc_id

        url = "https://travel-advisor.p.rapidapi.com/attractions/list"
        querystring = {"location_id":"{location}".format(location=loc_id), 
                       "currency": "EUR",
                       "lang": "en_US",
                       "lunit": "km",
                       "sort": "recommended",
                       "subcategory": self.__findCuisineId(tracker),
        }

        response = requests.request("GET", url, headers=headers, params=querystring)
        res_json = response.json()

        result = {
            "text": [],
            "type": "result"
        } 
        for rest in res_json['data']:
            if  'name' in rest:
                result['text'].append({
                    "name": rest['name'],
                    "image": rest['photo']['images']['thumbnail'] if 'photo' in rest else "",
                    "rating": rest['rating'],
                    "price_level": rest['price_level'] if 'price_level' in rest else "",
                    "website": rest['website'] if "website" in rest else "",
                    "address": rest['address'],
                    "type": rest['subcategory'] if "subcategory" in rest else ""
                })

        dispatcher.utter_message(
            json_message= result
        )

        return [AllSlotsReset()]


class ActionMonitorGroupChat(Action):
    def name(self) -> Text:
        return "action_monitor_groupchat"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
            
            if not tracker.slots['attraction'] and not tracker.slots['location']:
                return [FollowupAction(name= 'utter_ignore')] 
            else:
                return []

class ActionResetPreferences(Action):
    def name(self) -> Text:
        return "action_reset_preferences"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

            return [AllSlotsReset()]

