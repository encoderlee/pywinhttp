# pywinhttp
![version](https://img.shields.io/badge/version-1.0.1-blue)
![license](https://img.shields.io/badge/license-MIT-brightgreen)
![python_version](https://img.shields.io/badge/python-%3E%3D%203.6-brightgreen)
![coverage](https://img.shields.io/badge/coverage-100%25-brightgreen)
[![](https://img.shields.io/badge/blog-@encoderlee-red)](https://encoderlee.blog.csdn.net)

a python http client implemented based on the winhttp library.

Using it to create web crawlers can avoid Cloudflare's TLS fingerprinting.

because the winhttp library is the underlying implementation of the Edge browser.

its TLS fingerprint is consistent with the Edge browser.

it can only run on the Windows platform.

this project uses python's built-in ctypes to call winhttp.dll directly, with no dependencies on third-party packages.

# Install
```$ pip install pywinhttp```

# Using
```python
import pywinhttp

user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36 Edg/146.0.0.0"
client = pywinhttp.Session(user_agent)

url = "https://public-wax-on.wax.io/wam/sign"

resp = client.get(url)
print(resp.text)

post_data = {
    "serializedTransaction": "xxxxxxxxxxxxxxxxxxxxxxx",
    "description": "jwt is insecure",
    "freeBandwidth": False,
    "website": "play.alienworlds.io",
}
headers = {"x-access-token": "xxxxxxxxxxxxxxxxxxxxxxx"}
resp = client.post(url, json = post_data, headers = headers)
print(resp.text)
```