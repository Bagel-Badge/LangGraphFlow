import urllib.request
import json
try:
    req = urllib.request.Request("http://127.0.0.1:8001/api/active_sessions")
    response = urllib.request.urlopen(req)
    print(response.read().decode())
except Exception as e:
    print(e)
