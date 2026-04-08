import ctypes
import json
from ctypes import wintypes
from urllib.parse import urlparse


class WinhttpException(Exception):
    def __init__(self, msg: str, last_error: int = 0, status_code: int = None):
        self.msg = msg
        self.last_error = last_error
        self.status_code = status_code

    def __str__(self):
        return json.dumps({"msg": self.msg, "last_error": self.last_error, "status_code": self.status_code})


class Response:
    def __init__(self, status_code: int, headers: dict, content: bytes, url: str):
        self.status_code = status_code
        self.headers = headers
        self.content = content
        self.url = url
        self.encoding = "utf-8"

    @property
    def text(self) -> str:
        return self.content.decode(self.encoding, errors="replace")

    def json(self):
        return json.loads(self.text)

    def raise_for_status(self):
        if 400 <= self.status_code:
            raise WinhttpException(f"HTTP {self.status_code} for {self.url}", status_code = self.status_code)


class HttpProxy:
    def __init__(self, host: str, port: int | str, username: str = None, password: str = None):
        self.host = host
        self.port = port
        self.username = username
        self.password = password


class Session:
    WINHTTP_ACCESS_TYPE_DEFAULT_PROXY = 0
    WINHTTP_ACCESS_TYPE_NO_PROXY = 1
    WINHTTP_ACCESS_TYPE_NAMED_PROXY = 3
    WINHTTP_FLAG_SECURE = 0x00800000
    WINHTTP_OPTION_PROXY = 38
    WINHTTP_NO_PROXY_BYPASS = None

    WINHTTP_AUTH_TARGET_PROXY = 1
    WINHTTP_AUTH_SCHEME_BASIC = 0x00000001

    INTERNET_DEFAULT_HTTP_PORT = 80
    INTERNET_DEFAULT_HTTPS_PORT = 443

    WINHTTP_QUERY_STATUS_CODE = 19
    WINHTTP_QUERY_RAW_HEADERS_CRLF = 22
    WINHTTP_QUERY_FLAG_NUMBER = 0x20000000

    class WINHTTP_PROXY_INFO(ctypes.Structure):
        _fields_ = [
            ("dwAccessType", wintypes.DWORD),
            ("lpszProxy", wintypes.LPCWSTR),
            ("lpszProxyBypass", wintypes.LPCWSTR),
        ]

    def __init__(self, user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36 Edg/146.0.0.0", proxy: HttpProxy = None):
        self.user_agent = user_agent
        self.default_headers = {}
        self.proxy: HttpProxy = proxy if proxy else None
        self.timeout: int | None = None
        self.winhttp = ctypes.WinDLL("winhttp.dll", use_last_error=True)
        self._init_prototypes()

    def _init_prototypes(self):
        w = self.winhttp
        w.WinHttpOpen.argtypes = [
            wintypes.LPCWSTR, wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD
        ]
        w.WinHttpOpen.restype = wintypes.HANDLE
        w.WinHttpConnect.argtypes = [wintypes.HANDLE, wintypes.LPCWSTR, wintypes.WORD, wintypes.DWORD]
        w.WinHttpConnect.restype = wintypes.HANDLE
        w.WinHttpOpenRequest.argtypes = [
            wintypes.HANDLE, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.LPCWSTR,
            wintypes.LPCWSTR, ctypes.POINTER(wintypes.LPCWSTR), wintypes.DWORD
        ]
        w.WinHttpOpenRequest.restype = wintypes.HANDLE
        w.WinHttpSendRequest.argtypes = [
            wintypes.HANDLE, wintypes.LPCWSTR, wintypes.DWORD,
            wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, ctypes.c_size_t
        ]
        w.WinHttpSendRequest.restype = wintypes.BOOL
        w.WinHttpReceiveResponse.argtypes = [wintypes.HANDLE, wintypes.LPVOID]
        w.WinHttpReceiveResponse.restype = wintypes.BOOL
        w.WinHttpQueryDataAvailable.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
        w.WinHttpQueryDataAvailable.restype = wintypes.BOOL
        w.WinHttpReadData.argtypes = [wintypes.HANDLE, wintypes.LPVOID, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
        w.WinHttpReadData.restype = wintypes.BOOL
        w.WinHttpQueryHeaders.argtypes = [
            wintypes.HANDLE, wintypes.DWORD, wintypes.LPCWSTR,
            wintypes.LPVOID, ctypes.POINTER(wintypes.DWORD), ctypes.POINTER(wintypes.DWORD)
        ]
        w.WinHttpQueryHeaders.restype = wintypes.BOOL
        w.WinHttpCloseHandle.argtypes = [wintypes.HANDLE]
        w.WinHttpCloseHandle.restype = wintypes.BOOL
        w.WinHttpSetOption.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPVOID, wintypes.DWORD]
        w.WinHttpSetOption.restype = wintypes.BOOL
        w.WinHttpSetCredentials.argtypes = [
            wintypes.HANDLE,
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.LPCWSTR,
            wintypes.LPCWSTR,
            wintypes.LPVOID,
        ]
        w.WinHttpSetCredentials.restype = wintypes.BOOL
        w.WinHttpSetTimeouts.argtypes = [
            wintypes.HANDLE,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
        ]
        w.WinHttpSetTimeouts.restype = wintypes.BOOL

    def _raise_last_error(self, msg: str):
        raise WinhttpException(msg, ctypes.get_last_error())

    def _query_status_code(self, h_request) -> int:
        size = wintypes.DWORD(ctypes.sizeof(wintypes.DWORD))
        status_code = wintypes.DWORD(0)
        ok = self.winhttp.WinHttpQueryHeaders(
            h_request,
            self.WINHTTP_QUERY_STATUS_CODE | self.WINHTTP_QUERY_FLAG_NUMBER,
            None,
            ctypes.byref(status_code),
            ctypes.byref(size),
            None,
        )
        if not ok:
            self._raise_last_error("WinHttpQueryHeaders(status code) failed")
        return int(status_code.value)

    def _query_raw_headers(self, h_request) -> str:
        size = wintypes.DWORD(0)
        self.winhttp.WinHttpQueryHeaders(
            h_request,
            self.WINHTTP_QUERY_RAW_HEADERS_CRLF,
            None,
            None,
            ctypes.byref(size),
            None,
        )
        if size.value == 0:
            return ""
        wchar_count = size.value // ctypes.sizeof(ctypes.c_wchar)
        buf = (ctypes.c_wchar * wchar_count)()
        ok = self.winhttp.WinHttpQueryHeaders(
            h_request,
            self.WINHTTP_QUERY_RAW_HEADERS_CRLF,
            None,
            ctypes.byref(buf),
            ctypes.byref(size),
            None,
        )
        if not ok:
            self._raise_last_error("WinHttpQueryHeaders(raw headers) failed")
        return ctypes.wstring_at(buf)

    @staticmethod
    def _parse_headers(raw_headers: str) -> dict:
        result = {}
        for line in raw_headers.split("\r\n"):
            if ": " in line:
                key, value = line.split(": ", 1)
                result[key] = value
        return result

    def _set_proxy_option(self, h_session):
        if self.proxy is None:
            return
        proxy_server = f"{self.proxy.host}:{self.proxy.port}"
        proxy_list = f"http={proxy_server};https={proxy_server}"
        proxy_info = self.WINHTTP_PROXY_INFO(
            self.WINHTTP_ACCESS_TYPE_NAMED_PROXY,
            proxy_list,
            self.WINHTTP_NO_PROXY_BYPASS,
        )
        ok = self.winhttp.WinHttpSetOption(
            h_session,
            self.WINHTTP_OPTION_PROXY,
            ctypes.byref(proxy_info),
            ctypes.sizeof(proxy_info),
        )
        if not ok:
            self._raise_last_error("WinHttpSetOption(proxy) failed")

    def _set_proxy_credentials(self, h_request):
        if self.proxy is None:
            return
        if not self.proxy.username:
            return
        ok = self.winhttp.WinHttpSetCredentials(
            h_request,
            self.WINHTTP_AUTH_TARGET_PROXY,
            self.WINHTTP_AUTH_SCHEME_BASIC,
            self.proxy.username,
            self.proxy.password or "",
            None,
        )
        if not ok:
            self._raise_last_error("WinHttpSetCredentials(proxy) failed")

    def _set_timeouts(self, h_session, timeout: int | None):
        if timeout is None:
            return
        timeout_ms = int(timeout)
        if timeout_ms < 0:
            raise ValueError("timeout must be >= 0")
        ok = self.winhttp.WinHttpSetTimeouts(
            h_session,
            timeout_ms,
            timeout_ms,
            timeout_ms,
            timeout_ms,
        )
        if not ok:
            self._raise_last_error("WinHttpSetTimeouts failed")

    def request(self, method: str, url: str, params: dict | None = None, data=None, json_data=None, headers: dict | None = None, timeout: int | None = None) -> Response:
        parsed = urlparse(url)
        if parsed.scheme.lower() not in ("http", "https"):
            raise ValueError("URL must start with http:// or https://")

        query_path = parsed.path or "/"
        query_string = parsed.query
        if params:
            extra = "&".join([f"{k}={v}" for k, v in params.items()])
            query_string = f"{query_string}&{extra}" if query_string else extra
        if query_string:
            query_path = f"{query_path}?{query_string}"

        all_headers = dict(self.default_headers)
        if headers:
            all_headers.update(headers)

        body = b""
        if json_data is not None:
            body = json.dumps(json_data).encode("utf-8")
            all_headers.setdefault("Content-Type", "application/json")
        elif data is not None:
            if isinstance(data, bytes):
                body = data
            else:
                body = str(data).encode("utf-8")

        header_text = "".join([f"{k}: {v}\r\n" for k, v in all_headers.items()])
        is_https = parsed.scheme.lower() == "https"
        port = parsed.port or (self.INTERNET_DEFAULT_HTTPS_PORT if is_https else self.INTERNET_DEFAULT_HTTP_PORT)
        flags = self.WINHTTP_FLAG_SECURE if is_https else 0

        h_session = h_connect = h_request = None
        try:
            h_session = self.winhttp.WinHttpOpen(
                self.user_agent, self.WINHTTP_ACCESS_TYPE_DEFAULT_PROXY, None, None, 0
            )
            if not h_session:
                self._raise_last_error("WinHttpOpen failed")
            effective_timeout = self.timeout if timeout is None else timeout
            self._set_timeouts(h_session, effective_timeout)
            self._set_proxy_option(h_session)

            h_connect = self.winhttp.WinHttpConnect(h_session, parsed.hostname, port, 0)
            if not h_connect:
                self._raise_last_error("WinHttpConnect failed")

            h_request = self.winhttp.WinHttpOpenRequest(
                h_connect, method.upper(), query_path, None, None, None, flags
            )
            if not h_request:
                self._raise_last_error("WinHttpOpenRequest failed")
            self._set_proxy_credentials(h_request)

            body_buf = ctypes.create_string_buffer(body) if body else None
            body_ptr = ctypes.cast(body_buf, wintypes.LPVOID) if body_buf else None
            hdr_ptr = header_text if header_text else None
            hdr_len = -1 if hdr_ptr else 0
            body_len = len(body)

            ok = self.winhttp.WinHttpSendRequest(
                h_request, hdr_ptr, hdr_len, body_ptr, body_len, body_len, 0
            )
            if not ok:
                self._raise_last_error("WinHttpSendRequest failed")

            ok = self.winhttp.WinHttpReceiveResponse(h_request, None)
            if not ok:
                self._raise_last_error("WinHttpReceiveResponse failed")

            status_code = self._query_status_code(h_request)
            if status_code == 407:
                raise WinhttpException("Proxy authentication failed (HTTP 407)", ctypes.get_last_error(), status_code)
            raw_headers = self._query_raw_headers(h_request)
            response_headers = self._parse_headers(raw_headers)

            chunks = []
            while True:
                available = wintypes.DWORD(0)
                ok = self.winhttp.WinHttpQueryDataAvailable(h_request, ctypes.byref(available))
                if not ok:
                    self._raise_last_error("WinHttpQueryDataAvailable failed")
                if available.value == 0:
                    break
                buf = ctypes.create_string_buffer(available.value)
                read = wintypes.DWORD(0)
                ok = self.winhttp.WinHttpReadData(h_request, buf, available.value, ctypes.byref(read))
                if not ok:
                    self._raise_last_error("WinHttpReadData failed")
                chunks.append(buf.raw[:read.value])

            return Response(status_code, response_headers, b"".join(chunks), url)
        finally:
            if h_request:
                self.winhttp.WinHttpCloseHandle(h_request)
            if h_connect:
                self.winhttp.WinHttpCloseHandle(h_connect)
            if h_session:
                self.winhttp.WinHttpCloseHandle(h_session)

    def get(self, url: str, params: dict | None = None, headers: dict | None = None, timeout: int | None = None) -> Response:
        return self.request("GET", url, params=params, headers=headers, timeout=timeout)

    def post(self, url: str, data=None, json=None, headers: dict | None = None, timeout: int | None = None) -> Response:
        return self.request("POST", url, data=data, json_data=json, headers=headers, timeout=timeout)


def request(method: str, url: str, **kwargs) -> Response:
    return Session().request(method, url, **kwargs)


def get(url: str, params: dict | None = None, headers: dict | None = None, timeout: int | None = None) -> Response:
    return Session().get(url, params=params, headers=headers, timeout=timeout)


def post(url: str, data=None, json=None, headers: dict | None = None, timeout: int | None = None) -> Response:
    return Session().post(url, data=data, json=json, headers=headers, timeout=timeout)
