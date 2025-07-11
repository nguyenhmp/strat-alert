import smtplib
from email.mime.text import MIMEText
EMAIL = "nguyenhminhp@gmail.com"
APP_PASSWORD = "babt easm gylr wbvy"
TO_NUMBER = "+14252464470@tmomail.net"
msg = MIMEText("Test message from your script")
msg["Subject"] = "Test"
msg["From"] = "nguyenhminhp@gmail.com"
msg["To"] = "+14252464470@tmomail.net"

server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
server.login(EMAIL, APP_PASSWORD)
server.sendmail(msg["From"], [msg["To"]], msg.as_string())
server.quit()
print("✅ Test sent")
