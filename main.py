import yfinance as yf
import pandas as pd
import schedule
import smtplib
from email.mime.text import MIMEText
from datetime import datetime
import pytz
import time
from datetime import timedelta
import smtplib
from email.mime.text import MIMEText
import os


# === Configuration ===
SYMBOL = "QQQ"
# EMAIL = "nguyenhminhp@gmail.com"
# APP_PASSWORD = "babt easm gylr wbvy"
# TO_NUMBER = "4252464470@tmomail.net"
EMAIL = os.environ["EMAIL"]
APP_PASSWORD = os.environ["APP_PASSWORD"]
# import yfinance as yf
# import pandas as pd
# import smtplib
# from email.mime.text import MIMEText
# from datetime import datetime, timedelta
# import pytz
# import os

# # === Configuration ===
# SYMBOL = "NQ=F"
# EMAIL = os.environ["EMAIL"]
# APP_PASSWORD = os.environ["APP_PASSWORD"]
# TO_NUMBER = os.environ["TO_NUMBER"]

def is_now_pst_time(hour, minute):
    now = datetime.now(pytz.timezone("US/Pacific"))
    return now.hour == hour and now.minute == minute
    
def fetch_and_resample():
    ticker = yf.Ticker(SYMBOL)
    
    # end_date = datetime.now().date()
    # start_date = end_date - timedelta(days=2)

    # df = ticker.history(interval="15m", start=start_date.strftime("%Y-%m-%d"), end=end_date.strftime("%Y-%m-%d"), prepost=True)
    df = ticker.history(interval="15m", period="2d", prepost=True)
    df = df.reset_index()
    df["timestamp"] = pd.to_datetime(df["Datetime"]).dt.tz_convert("US/Pacific")
    df = df.set_index("timestamp")

    # Align resampling to end at 7:15 AM PST by shifting index
    # anchor_minutes = (df.index[0].hour * 60 + df.index[0].minute) % 195
    df.index = df.index - pd.Timedelta(minutes=195)
    df_195 = df.resample("195T", label='right', closed='right').agg({
        "Open": "first",
        "High": "max",
        "Low": "min",
        "Close": "last",
        "Volume": "sum"
    }).dropna()
    df_195.index = df_195.index + pd.Timedelta(minutes=195)  # shift index back
    print(df_195.tail(5))
    return df_195, df

def detect_latest_3_bar_at_0715(df_195):
    # Filter only bars ending at 07:15
    matches = df_195[df_195.index.time == datetime.strptime("07:15", "%H:%M").time()]
    
    if len(matches) == 0:
        print("❌ No bars ending at 07:15 PST found.")
        return False, None

    # Get the latest bar ending at 07:15
    latest_idx = df_195.index.get_loc(matches.index[-1])

    if latest_idx < 2:
        print("❌ Not enough bars before the latest 07:15 bar to form a 3-bar pattern.")
        return False, None

    bar1 = df_195.iloc[latest_idx - 2]
    bar2 = df_195.iloc[latest_idx - 1]
    bar3 = df_195.iloc[latest_idx]

    is_outside = bar3["High"] > bar2["High"] and bar3["Low"] < bar2["Low"]
    if is_outside:
        return True, bar3
    return False, None

def detect_3_2_combos(df):
    combos = []
    for i in range(2, len(df)):
        bar1 = df.iloc[i - 2]
        bar2 = df.iloc[i - 1]
        bar3 = df.iloc[i]

        # Check if bar2 is a 3-bar
        is_3_bar = bar2["High"] > bar1["High"] and bar2["Low"] < bar1["Low"]

        # Check if bar3 is a 2-bar (breaks high or low, but not both)
        breaks_high = bar3["High"] > bar2["High"]
        breaks_low = bar3["Low"] < bar2["Low"]
        is_2_bar = breaks_high ^ breaks_low  # one or the other

        if is_3_bar and is_2_bar:
            combos.append((df.index[i - 1], df.index[i]))  # (3-bar time, 2-bar time)
    return combos

def send_email_alert(subject, message):
    sender_email = "nguyenhminhp@gmail.com"
    recipient_email = "nguyenhminhp@gmail.com"  # or send to someone else
    app_password = APP_PASSWORD

    msg = MIMEText(message)
    msg["Subject"] = subject
    msg["From"] = sender_email
    msg["To"] = recipient_email

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, app_password)
            server.sendmail(sender_email, recipient_email, msg.as_string())
        print("✅ Email sent!")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")

def run_check():
    
    df_195, df = fetch_and_resample()
    if is_now_pst_time(7, 14):
        print("🔍 Checking latest 07:15 PST bar for 3-bar pattern...")
        detected, bar = detect_latest_3_bar_at_0715(df_195)
        if detected:
            time_str = bar.name.strftime("%Y-%m-%d %H:%M")
            message = f"✅ 3-bar (outside bar) detected for {SYMBOL} ending at {time_str} PST"
            send_email_alert("195 min 3-bar Pattern Detected", message)
        else:
            print("❌ No 3-bar pattern detected on latest 07:15 PST bar.")
    
    window_df = df.between_time("05:30", "08:00")
    combos = detect_3_2_combos(window_df)

    if combos:
        message = "3-2 combos detected for {}:\n".format(SYMBOL)
        for bar3, bar2 in combos:
            message += f" - 3-bar at {bar3}, 2-bar at {bar2}\n"
        send_email_alert("Strat 3-2 Combo Alert", message)
    else:
        print("❌ No 3-2 combos detected.")
def is_market_hours():
    now = datetime.now(pytz.timezone("US/Pacific"))
    return now.time() >= datetime.strptime("05:30", "%H:%M").time() and now.time() <= datetime.strptime("13:00", "%H:%M").time()

def schedule_runner():
    schedule.every(14).minutes.do(lambda: run_check() if is_market_hours() else None)
    print("⏰ Scheduler started. Running every 14 minutes...")

    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    schedule_runner()
