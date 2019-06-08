from json import dumps
from re import sub
from requests import get, post
from datetime import datetime, timedelta
from json.decoder import JSONDecodeError
from urllib.parse import quote_plus


class AuthenticationFailedError(Exception):
    def __init__(self):
        self.message = "Invalid username or password"


class ApiServerError(Exception):
    def __init__(self):
        self.message = "ClasseViva APIs are not available"


class InvalidRequestError(Exception):
    def __init__(self):
        self.message = "Request made is not valid"


class ClasseVivaAPI:
    baseApiUrl = "https://web.spaggiari.eu/rest/v1"

    def __init__(self):
        self.id = None
        self.token = None


    def login(self, username: str, password: str):
        r = post(
            url=self.baseApiUrl + "/auth/login/",
            headers={"User-Agent": "zorro/1.0",
                     "Z-Dev-Apikey": "+zorro+",
                     "Content-Type": "application/json"
            },
            data=dumps({"uid": username,
                        "pass": password
            })
        )
        result = r.json()

        if 'authentication failed' in result.get('error', ''):
            raise AuthenticationFailedError()

        self.token = result['token']
        self.id = sub(r"\D", "", result['ident'])
        return {"id": self.id}


    def logout(self):
        self.token = None


    def _request(self, *path):
        url = "{0}/students/{1}".format(self.baseApiUrl, self.id)
        for x in path:
            url += "/{0}".format(quote_plus(x))

        req = get(url=url, headers={"User-Agent": "zorro/1.0",
                                    "Z-Dev-Apikey": "+zorro+",
                                    "Z-Auth-Token": self.token,
                                    "Content-Type": "application/json"})
        try:
            jsonReq = req.json()
            if jsonReq.get('error'):
                if 'auth token expired' in jsonReq['error']:
                    raise AuthenticationFailedError
                elif 'content temporarily unavailable' in jsonReq['error']:
                    raise ApiServerError
                elif 'invalid date range' in jsonReq['error']:
                    raise InvalidRequestError
            return jsonReq

        except JSONDecodeError:
            return req.text


    def assenze(self):
        try:
            result = self._request('absences', 'details', str(datetime.now().year)+"0910", datetime.today().strftime("%Y%m%d"))
        except InvalidRequestError:
            result = self._request('absences', 'details', str(datetime.now().year - 1)+"0910", datetime.today().strftime("%Y%m%d"))
        return result


    def agenda(self, days: int=14):
        return self._request('agenda', 'all', datetime.today().strftime("%Y%m%d"), (datetime.now() + timedelta(days=days)).strftime("%Y%m%d"))


    def didattica(self):
        return self._request('didactics')


    def getFile(self, file_id: str):
        return self._request('didactics', 'item', file_id)


    def comunicazioni(self):
        return self._request('noticeboard')


    def getMessage(self, file_id: str):
        return self._request('noticeboard', 'attach', 'CF', file_id)


    def info(self):
        return self._request('cards')


    def voti(self):
        return self._request('grades')


    def note(self):
        return self._request('notes', 'all')


    def materie(self):
        return self._request('subjects')


    def lezioni(self, days: int=0):
        return self._request('lessons', (datetime.now() + timedelta(days=days)).strftime("%Y%m%d"))
