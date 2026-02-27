import sys
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEnginePage

class LoggingPage(QWebEnginePage):
    def javaScriptConsoleMessage(self, level, message, lineNumber, sourceID):
        print(f"JS: {message} ({sourceID}:{lineNumber})")

def test():
    app = QApplication(sys.argv)
    
    # Enable all necessary WebEngine features to prevent JWPlayer/Sandbox errors
    webview = QWebEngineView()
    settings = webview.settings()
    settings.setAttribute(settings.WebAttribute.JavascriptEnabled, True)
    settings.setAttribute(settings.WebAttribute.PluginsEnabled, True)
    
    # Allow all cookies (essential for embedded JWPlayers)
    profile = webview.page().profile()
    from PySide6.QtWebEngineCore import QWebEngineProfile
    profile.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.AllowPersistentCookies)
    
    # Disable generic Tracking Prevention if it exists (Qt 6.7+)
    if hasattr(profile, "setTrackingPreventionEnabled"):
        profile.setTrackingPreventionEnabled(False)
        
    logging_page = LoggingPage(webview)
    webview.setPage(logging_page)
    
    url = "https://vidbasic.top/embed/evvbf4vav"
    referer = "https://ww16.dramacool.bg/"
    
    html_content = f'''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="referrer" content="unsafe-url">
        <title>Loading Player...</title>
    </head>
    <body style="margin:0;padding:0;">
        <h2>Loading streaming host...</h2>
        <script>
            setTimeout(function() {{
                window.location.replace("{url}");
            }}, 100);
        </script>
    </body>
    </html>
    '''
    
    print("Testing setHtml with baseUrl spoofing...")
    view = webview
    view.setHtml(html_content, baseUrl=QUrl(referer))
    
    win = QMainWindow()
    win.setCentralWidget(view)
    win.show()
    
    # Run for 8 seconds to collect logs
    from PySide6.QtCore import QTimer
    QTimer.singleShot(8000, app.quit)
    app.exec()

if __name__ == "__main__":
    test()
