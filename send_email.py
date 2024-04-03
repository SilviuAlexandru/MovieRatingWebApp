import smtplib

MY_EMAIL = "my-email"
APP_PASSWORD = "my-password"


class SendEmail:
    def __init__(self, email_to_send, password_to_generate):
        self.email = email_to_send
        self.password = password_to_generate

    def send_email(self):
        with smtplib.SMTP("smtp.gmail.com", port=587) as connection:
            connection.starttls()
            connection.login(user=MY_EMAIL, password=APP_PASSWORD)
            connection.sendmail(
                from_addr=MY_EMAIL,
                to_addrs=self.email,
                msg=f"Subject:Change password\n\nYour new password is: {self.password}"
            )
        connection.close()
