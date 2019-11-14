from bs4 import BeautifulSoup
import json
import re
import requests
from functools import reduce
import boto3

class Download:
    def __init__(self, list_match_id):
        self.__list_match_id = list_match_id
        self.__path_staging_in = "blno/STAGING_IN/"
        self.__s3_resource = boto3.resource('s3')
        self.__bucket_name = 'hubie'
        
        for match_id in self.__list_match_id:
            self.__parse_html_to_json(match_id=match_id)
        
    def __convert_to_nor_char(self, d):
        """
        Converts special characters to norwegian letters
        """
        rep = {"&#248;": "ø",
               "\u00f8": "ø",
               "&#229;": "å",
               "Ã¸": 'ø',
               "Ã˜": "Ø",
               "Ã¥": "å",
               "Ã¦": "æ",
               "Ã©": "é"}
        replaced_dict = reduce(lambda a, kv: a.replace(*kv), rep.items(), str(d))

        return eval(replaced_dict)
    
    
    def __parse_html_to_json(self, match_id):
        match_id = str(match_id)

        url = "https://wp.nif.no/MatchDetails?id=" + str(match_id)
        response = requests.get(url, allow_redirects=True) # download the website
        response.encoding = response.apparent_encoding
        if response.ok:
            html = response.content
            soup = BeautifulSoup(html, 'html.parser')
            search_dict = ['MatchSummaryViewModel', 'MatchEventsViewModel']
            for search in search_dict:
                JSON = re.compile('Nif.Basket.' + search + '(\({.*?}\));', re.DOTALL)
                matches = JSON.search(soup.get_text())
                data_json = json.loads(matches.group(1)[1:-1]) #takes away the ()
                nor_char_data_json = json.dumps(self.__convert_to_nor_char(data_json)) # replace the chars with norwegian chars

                file_name = match_id + "_" + search + '.json'

                s3object = self.__s3_resource.Object(self.__bucket_name, self.__path_staging_in + file_name)

                s3object.put(
                    Body=(nor_char_data_json)
                )
                print("File {} saved to {}".format(file_name, self.__path_staging_in))