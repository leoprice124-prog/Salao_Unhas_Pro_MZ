import os, subprocess, time, urllib.request, http.server, socketserver

PORT = int(os.environ.get("PORT", 10000))
ST_PORT = 8501

ADS_TXT = b"google.com, pub-6467621234967556, DIRECT, f08c47fec0942fa0"
ADS_HEAD = (
    '<meta name="google-adsense-account" content="ca-pub-6467621234967556">'
    '<script async src="https://googlesyndication.com" crossorigin="anonymous"></script>'
)

# Iniciar Streamlit em segundo plano
subprocess.Popen([
    "streamlit", "run", "salao_pro.py",
    "--server.port", str(ST_PORT),
    "--server.address", "127.0.0.1",
    "--server.headless", "true"
])

class FastAdSenseHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path.split("?").pop(0)
        if path == "/ads.txt":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(ADS_TXT)
            return

        # Entregar pagina inicial leve com o codigo AdSense + iframe do Salao Pro MZ
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        html = f"""<!DOCTYPE html>
<html lang="pt">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
{ADS_HEAD}
<title>Studio & Salão Pro MZ — Agendamento, Galeria & Gestão</title>
<style>
  body, html {{ margin:0; padding:0; height:100%; background:#0e1117; color:#fff; font-family:sans-serif; }}
  iframe {{ width:100%; height:100vh; border:none; display:block; }}
</style>
</head>
<body>
  <iframe src="https://onrender.com" id="appFrame"></iframe>
  <noscript>
    <h1>Studio & Salão Pro MZ — Agendamento & Beleza</h1>
    <p>Plataforma de agendamento online para salões de beleza, estúdios de unhas, cabeleireiros e barbearias em Moçambique.</p>
  </noscript>
</body>
</html>"""
        self.wfile.write(html.encode("utf-8"))

socketserver.TCPServer.allow_reuse_address = True
with socketserver.TCPServer(("0.0.0.0", PORT), FastAdSenseHandler) as httpd:
    httpd.serve_forever()
