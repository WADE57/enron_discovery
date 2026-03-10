import os
import email
import pandas as pd

MAILDIR_PATH = "../maildir"

def parse_email(file_path):

    with open(file_path, "r", encoding="latin-1") as f:
        msg = email.message_from_file(f)

    email_data = {
        "from": msg.get("From"),
        "to": msg.get("To"),
        "date": msg.get("Date"),
        "subject": msg.get("Subject"),
        "message_id": msg.get("Message-ID"),
        "in_reply_to": msg.get("In-Reply-To"),
        "body": msg.get_payload()
    }

    return email_data

emails = []

for root, dirs, files in os.walk(MAILDIR_PATH):

    for file in files:

        file_path = os.path.join(root, file)

        try:
            email_data = parse_email(file_path)
            emails.append(email_data)

        except Exception as e:
            print("Error:", file_path)


df = pd.DataFrame(emails)

print(df.head())
print("Total emails:", len(df))

df.to_csv("../data/emails.csv", index=False)