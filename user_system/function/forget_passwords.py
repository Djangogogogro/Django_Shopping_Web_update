import smtplib
import os
from email.message import EmailMessage
from dotenv import load_dotenv
import random

def send_email(user_email):
    load_dotenv()

    gmail_user = os.getenv('GMAIL_USER')
    gmail_password = os.getenv('GMAIL_APP_PASSWORD')

    random_number = random.randint(0, 9999)
    verification_code = str(random_number).zfill(4)

    msg = EmailMessage()
    msg['Subject'] = '🐜BUYIT | Forget Passwords'
    msg['From'] = f'BUYIT <{gmail_user}>'
    msg['To'] = user_email
    msg.set_content(f'This is your verification code\n{verification_code}\nPlease enter it on the Forget Passwords page.')

    with smtplib.SMTP('smtp.gmail.com', 587) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.login(gmail_user, gmail_password)
        smtp.send_message(msg)
        print("郵件傳送成功!")

    return verification_code
