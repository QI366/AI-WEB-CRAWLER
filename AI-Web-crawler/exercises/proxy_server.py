# coding=utf-8
"""一个同时支持 HTTP 与 HTTPS 的最小正向代理。

原版只写了 do_GET / do_POST：客户端抓 https 站点时先发 CONNECT 建隧道，
BaseHTTPRequestHandler 找不到 do_CONNECT 就回 501，requests 那头便报
ProxyError: Tunnel connection failed。补上 do_CONNECT 即可。

启动：python proxy_server.py [端口]        默认 8080
客户端：proxies = {'http': 'http://<本机IP>:8080', 'https': 'http://<本机IP>:8080'}
"""

import select
import socket
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import requests

# 逐跳首部：只对单条连接有意义，不能原样转发给下一跳
HOP_BY_HOP = {
    'connection', 'keep-alive', 'proxy-authenticate', 'proxy-authorization',
    'proxy-connection', 'te', 'trailer', 'transfer-encoding', 'upgrade',
}

BUFSIZE = 65536


class ProxyHandler(BaseHTTPRequestHandler):
    # 一个请求一条连接，省掉 keep-alive 下的长度协商
    protocol_version = 'HTTP/1.0'

    # ---------- HTTPS：CONNECT 隧道 ----------

    def do_CONNECT(self):
        """self.path 形如 spiderbuf.cn:443。代理不解密，只做字节水管。"""
        host, _, port = self.path.rpartition(':')
        if not host:                      # 没写端口
            host, port = self.path, '443'

        try:
            upstream = socket.create_connection((host, int(port)), timeout=10)
        except OSError as e:
            self.send_error(502, f'无法连接目标 {self.path}: {e}')
            return

        # 回 200 之后这条连接就不再是 HTTP 了，双方直接跑 TLS
        self.send_response_only(200, 'Connection Established')
        self.end_headers()
        self.wfile.flush()

        try:
            self._relay(self.connection, upstream)
        finally:
            upstream.close()
            self.close_connection = True

    @staticmethod
    def _relay(client, upstream):
        """在两个 socket 之间双向搬运，任一端关闭就结束。"""
        socks = [client, upstream]
        try:
            while True:
                readable, _, errored = select.select(socks, [], socks, 60)
                if errored or not readable:   # 出错或 60 秒无数据
                    return
                for src in readable:
                    data = src.recv(BUFSIZE)
                    if not data:
                        return
                    (upstream if src is client else client).sendall(data)
        except OSError:
            return

    # ---------- 明文 HTTP：解析后用 requests 转发 ----------

    def forward_request(self):
        # 走代理时客户端发来的是绝对 URL（http://host/path），不是 /path
        if not self.path.lower().startswith(('http://', 'https://')):
            self.send_error(400, '代理只接受绝对 URL')
            return

        headers = {k: v for k, v in self.headers.items()
                   if k.lower() not in HOP_BY_HOP}
        length = int(self.headers.get('Content-Length') or 0)
        body = self.rfile.read(length) if length else None

        try:
            resp = requests.request(
                method=self.command,
                url=self.path,
                headers=headers,
                data=body,
                timeout=30,
                allow_redirects=False,   # 重定向该由客户端自己决定跟不跟
                stream=True,
            )
            # decode_content=False：原样透传压缩后的字节。
            # 若让 requests 自动解 gzip，body 解了而 Content-Encoding 头还写着 gzip，
            # 客户端会再解一次然后报错。
            payload = resp.raw.read(decode_content=False)
        except Exception as e:
            self.send_error(502, f'代理转发错误: {e}')
            return

        self.log_request(resp.status_code, len(payload))
        self.send_response_only(resp.status_code)
        for key, value in resp.headers.items():
            if key.lower() not in HOP_BY_HOP and key.lower() != 'content-length':
                self.send_header(key, value)
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        if self.command != 'HEAD':
            self.wfile.write(payload)

    do_GET = forward_request
    do_POST = forward_request
    do_HEAD = forward_request
    do_PUT = forward_request
    do_DELETE = forward_request
    do_PATCH = forward_request
    do_OPTIONS = forward_request


if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    # ThreadingHTTPServer：一个连接一个线程。原来的 TCPServer 是单线程，
    # CONNECT 隧道会一直占着它，后面的请求全被堵死。
    with ThreadingHTTPServer(('', port), ProxyHandler) as httpd:
        print(f'代理监听 0.0.0.0:{port}，Ctrl+C 退出')
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print('\n已停止')
