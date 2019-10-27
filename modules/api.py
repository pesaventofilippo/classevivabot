from json import dumps, loads
from re import sub
from datetime import datetime, timedelta
from json.decoder import JSONDecodeError
from urllib.parse import quote_plus
from urllib.request import Request, urlopen


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
        url = self.baseApiUrl + "/auth/login/"
        headers={"User-Agent":   "zorro/1.0",
                 "Z-Dev-Apikey": "+zorro+",
                 "Content-Type": "application/json"}
        values=dumps({"uid": username,
                      "pass": password})
        data = values.encode('ascii')
        req = Request(url, data, headers)
        result = urlopen(req).read().decode('utf-8')
        result = loads(result)

        if 'authentication failed' in result.get('error', ''):
            raise AuthenticationFailedError()

        self.token = result['token']
        self.id = sub(r"\D", "", result['ident'])
        return {"id": self.id}


    def logout(self):
        self.token = None


    def _request(self, *path, returnFile: bool=False):
        url = "{0}/students/{1}".format(self.baseApiUrl, self.id)
        for x in path:
            url += "/{0}".format(quote_plus(x))

        headers={"User-Agent": "zorro/1.0",
                 "Z-Dev-Apikey": "+zorro+",
                 "Z-Auth-Token": self.token,
                 "Content-Type": "application/json"}
        req = Request(url, headers=headers)
        result = urlopen(req)

        if returnFile:
            return result

        try:
            jsonResult = loads(result.read().decode('utf-8'))
            if jsonResult.get('error'):
                if 'auth token expired' in jsonResult['error']:
                    raise AuthenticationFailedError
                elif 'content temporarily unavailable' in jsonResult['error']:
                    raise ApiServerError
                elif 'invalid date range' in jsonResult['error']:
                    raise InvalidRequestError
            return jsonResult

        except JSONDecodeError:
            return result.read().decode('utf-8')


    def assenze(self):
        now = datetime.now()
        if (now.month < 9) or (now.month == 9 and now.day < 10):
            return self._request('absences', 'details', str(now.year - 1)+"0910", datetime.today().strftime("%Y%m%d"))
        return self._request('absences', 'details', str(now.year)+"0910", datetime.today().strftime("%Y%m%d"))


    def agenda(self, days: int=14):
        return self._request('agenda', 'all', datetime.today().strftime("%Y%m%d"), (datetime.now() + timedelta(days=days)).strftime("%Y%m%d"))


    def didattica(self):
        return self._request('didactics')


    def getFile(self, file_id: str):
        return self._request('didactics', 'item', file_id, returnFile=True)


    def circolari(self):
        return self._request('noticeboard')


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
