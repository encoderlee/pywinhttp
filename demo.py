import pywinhttp

def main():
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


if __name__ == '__main__':
    main()