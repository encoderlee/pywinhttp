import pywinhttp
from pywinhttp import HttpProxy

def main():
    client = pywinhttp.Session()
    client.proxy = HttpProxy("127.0.0.1", 8443, "user", "password")
    # set timeout 30 seconds
    client.timeout = 30 * 1000

    url = "https://httpbin.org/get"

    resp = client.get(url)
    print(resp.text)



if __name__ == '__main__':
    main()