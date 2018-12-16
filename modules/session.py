import json
import re
import requests
from datetime import datetime, timedelta
from json.decoder import JSONDecodeError
from urllib.parse import quote_plus


class AuthenticationFailedError(Exception):
    def __init__(self):
        self.message = "Invalid username or password"


class ClasseVivaAPI:
    rest_api_url = "https://web.spaggiari.eu/rest/v1"

    def __init__(self):
        self.id = None
        self.username = None
        self.password = None
        self.token = None


    def login(self, username: str=None, password: str=None):
        r = requests.post(
            url=self.rest_api_url + "/auth/login/",
            headers={"User-Agent": "zorro/1.0",
                     "Z-Dev-Apikey": "+zorro+",
                     "Content-Type": "application/json"
            },
            data=json.dumps({"uid": username if username else self.username,
                             "pass": password if username else self.password
            })
        )
        result = r.json()

        if 'authentication failed' in result.get('error', ''):
            raise AuthenticationFailedError()

        self.token = result['token']
        self.id = re.sub(r"\D", "", result['ident'])
        return {"id": self.id}


    def logout(self):
        self.token = None
        return True


    def _request(self, *path):
        url = "{0}/students/{1}".format(self.rest_api_url, self.id)
        for x in path:
            url += "/{0}".format(quote_plus(x))

        r = requests.get(url=url, headers={"User-Agent": "zorro/1.0", "Z-Dev-Apikey": "+zorro+",
                                           "Z-Auth-Token": self.token, "Content-Type": "application/json"})
        try:
            rj = r.json()
            if rj.get('error'):
                if 'auth token expired' in rj['error']:
                    self.login()
                    r = requests.get(url=url, headers={"User-Agent": "zorro/1.0", "Z-Dev-Apikey": "+zorro+",
                                                       "Z-Auth-Token": self.token, "Content-Type": "application/json"})
                    try:
                        rj = r.json()
                    except JSONDecodeError:
                        return r.text
            return rj

        except JSONDecodeError:
            return r.text


    def assenze(self):
        return self._request('absences', 'details', str(datetime.now().year)+"0910", datetime.today().strftime("%Y%m%d"))


    def agenda(self, days):
        return self._request('agenda', 'all', datetime.today().strftime("%Y%m%d"), (datetime.now() + timedelta(days=days)).strftime("%Y%m%d"))


    def didattica(self):
        return self._request('didactics')


    def info(self):
        return self._request('cards')


    def voti(self):
        return self._request('grades')


    def note(self):
        return self._request('notes', 'all')


    def materie(self):
        return self._request('subjects')


    def lezioni(self, days=0):
        return self._request('lessons', (datetime.now() + timedelta(days=days)).strftime("%Y%m%d"))