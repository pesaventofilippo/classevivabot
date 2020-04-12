from json import dumps
from re import sub
from datetime import datetime, timedelta
from http.client import RemoteDisconnected
import requests
from requests.exceptions import HTTPError, InvalidURL



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
        url = self.baseApiUrl + "/auth/login"
        headers = {
            "User-Agent":   "zorro/1.0",
            "Z-Dev-Apikey": "+zorro+",
            "Content-Type": "application/json"
        }
        values = dumps({
            "uid": username,
            "pass": password
        })
        data = values.encode('ascii')

        try:
            req = requests.post(url, data, headers=headers)
            result = req.json()
        except (ValueError, HTTPError, InvalidURL, RemoteDisconnected):
            raise ApiServerError

        if 'authentication failed' in result.get('error', ''):
            raise AuthenticationFailedError
        if 'token' not in result:
            raise ApiServerError

        self.token = result['token']
        self.id = sub(r"\D", "", result['ident'])
        return {"id": self.id}


    def logout(self):
        self.token = None


    def _request(self, relUrl, method="GET", returnFile=False):
        url = "{0}/students/{1}/{2}".format(self.baseApiUrl, self.id, relUrl)

        headers={
            "User-Agent": "zorro/1.0",
            "Z-Dev-Apikey": "+zorro+",
            "Z-Auth-Token": self.token,
            "Content-Type": "application/json"
        }
        try:
            if method == "POST":
                req = requests.post(url, headers=headers)
            else:
                req = requests.get(url, headers=headers)
        except (HTTPError, InvalidURL, RemoteDisconnected):
            raise ApiServerError

        if returnFile:
            from io import BytesIO
            return BytesIO(req.content)

        try:
            jsonResult = req.json()
            if jsonResult.get('error'):
                if 'auth token expired' in jsonResult['error']:
                    raise AuthenticationFailedError
                elif 'content temporarily unavailable' in jsonResult['error']:
                    raise ApiServerError
                elif 'invalid date range' in jsonResult['error']:
                    raise InvalidRequestError
            return jsonResult

        except ValueError:
            return req.text if req.text != "" else {}


    def assenze(self):
        now = datetime.now()
        if (now.month < 9) or (now.month == 9 and now.day < 10):
            return self._request("absences/details/{0}0910".format(now.year - 1))
        return self._request("absences/details/{0}0910".format(now.year))


    def agenda(self, days: int=14):
        return self._request("agenda/all/{0}/{1}".format(datetime.today().strftime("%Y%m%d"), (datetime.now() + timedelta(days=days)).strftime("%Y%m%d")))


    def didattica(self):
        return self._request("didactics")


    def circolari(self):
        return self._request("noticeboard")


    def info(self):
        return self._request("cards")


    def voti(self):
        return self._request("grades")


    def note(self):
        return self._request("notes/all")


    def materie(self):
        return self._request("subjects")


    def lezioni(self, days: int=0):
        return self._request("lessons/{0}".format((datetime.now() + timedelta(days=days)).strftime("%Y%m%d")))


    def getFile(self, fileId: int):
        return self._request("didactics/item/{0}".format(fileId), returnFile=True)


    def getCirc(self, eventCode: int, pubId: int):
        self._request("noticeboard/read/{0}/{1}/101".format(eventCode, pubId), method="POST")
        return self._request("noticeboard/attach/{0}/{1}/101".format(eventCode, pubId), returnFile=True)
