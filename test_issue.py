import urllib.request
import urllib.error
import re

try:
    urllib.request.urlopen("http://127.0.0.1:8000/faculty/dashboard/attendance/")
    print("SUCCESS")
except urllib.error.HTTPError as e:
    content = e.read().decode('utf-8')
    m = re.search(r'<pre class="exception_value">(.*?)</pre>', content, re.IGNORECASE | re.DOTALL)
    if m:
        print("EXCEPTION: " + m.group(1).strip())
    else:
        m2 = re.search(r'<title>(.*?)</title>', content, re.IGNORECASE)
        print("HTTP ERROR:", e.code, m2.group(1).strip() if m2 else content[:100])
except Exception as e:
    print("ERROR:", e)
