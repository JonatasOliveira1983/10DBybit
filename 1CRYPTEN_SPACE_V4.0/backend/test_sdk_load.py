import firebase_admin
from firebase_admin import credentials
import json

# EXACT key list from firebase_service.py
KEY_LINES = [
    "-----BEGIN PRIVATE KEY-----",
    "MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQDDt4bsRJgtdxSe",
    "aptiUqPBewYtZwtScv1vJIMNMw6STSqx460yeifGkM2tMTjp+lvIYIk38seYrtiw",
    "ztrnkF0DbH/6mC9x7woPzmE6ysVjLXrzEx4KvpoYSEmJ2f/2ePqvDfxDMayZhj64",
    "25ErAByLuvnExppRVMI3Hy4gBIWjM1TFzJWc1nAYxiHiVebJzY6ey3sDbFlnyyh6",
    "RDERPLFXKpTs7a2iLXZHu0805Or107RLB2Jize8tmYtTD55ql7/ncOX9hY4MP3LX",
    "vKN7vh25g3OX0jMDcbTpAerT4rIH/mSXu8+VlBagKieJ2DR1ndwC6RTEccV7iXhO",
    "OCtsfbEvAgMBAAECggEAGlplc/3egcy1fYk8R/Z5r0057TYhS6ZJIsSHUukrjp6O",
    "X6qZASF6pp2L3ESy9aps3mPFRj/OCWyNp+0Kg8CoDZR3/Q2t4cj+kVdIN0rjXjHb",
    "CszpsCevBxMAt+ufMBhlJNocvA19wKRXYLvL5b7bmSMBi7H0SHxBtHth0hTZy7oa",
    "1iNIgRvR1Eu0O1EoCfVGINUkCqo6pQM7THX4YuAFYrnYc5jZAnY877og6l826JB8",
    "aXBWujG/TZNd38slO6pG75RGSRDxRBilS2eonQI5j9Xhl/1J5CNCkI6D5N6zDfjA",
    "oEwAO3n+qmobJM9bsFfI7vDLrb0ZUsxZ1t3I39+U7QKBgQDrcQRKQEnImOvjC4Qb",
    "ljwK7V2aYJQsNpdVKl4wEZshDvIx4AYZrFVsoDThIveYeX4Kx3zuOzfvARljNeVc",
    "xVj8klfHhORLkdghJoL2KCXerd/aZ9ImjAzI6sZPgCfuSMgJFLvcc0Z7GqLh3QIy",
    "WIVLmuEi7p6fLwdr91BhYtEtOwKBgQDUzoUeBZUGiIaM56JWXBncDg0Ac4zQTyi0",
    "nSFRz5BhzPp9FrOLkUIwU2/1HLrDjyLhbt0kbw2cDOsLx+dYANgqbJNi3gOFm0KY",
    "bprYk2g/N8ApMpXjuUlQFVoCxBy0f0Pb3Zv63aiX/ChR/gzAHBiKpC1KsTwmZ0PJ",
    "14hlmZ+cnQKBgD0Gl0ETtsw67vFzu7NW1otSiS+Jlv56y/D0QWOePKJt+FL7KTmg",
    "VKgKQoqUgK7R1ty+ZmBtkwrtMwJnJuNL98vHtt7tUCtSSz4UeF+Len1kfiBjRrJd",
    "HLc7O1nB8xetX8QSzrrOWldwSQXYPkiEb1BwfaiLRywliXvvp7MGZQefAoGBAMl2",
    "FcmdKT79IrvkUegF2ylbV+20dnuCZRvPoYqMwLgF0KF5S1J2mr2bT+MxZpHaQQA/",
    "7zUduTmhdSc7AYVrjzlifolbeuQSXxJlq0wbCNbIVa/qxsHGWGRrQkJaHH63+Kr9",
    "+judeo0f15//rVx1fLpLwOD0Nuh4XFGKLQNaUyN1AoGAJVyyiAN3gsrQJOOJwh+",
    "d+nw7aXWPl4ldpFc9mgVCRX8loA17RYKecwsvP03hvpoLmEyC/y0RuVbIbl2utyK",
    "OzXfi9ajpLUPIiS3auKu6sCjsf0Mt8+OhU5omiRiRgqWDSvbHRkl6cEVUfihoXZJ",
    "B1zxvQqx73Sx5Tkbi8nOaow==",
    "-----END PRIVATE KEY-----"
]
PRIVATE_KEY = "\n".join(KEY_LINES)

FIREBASE_CONFIG = {
  "type": "service_account",
  "project_id": "projeto-teste-firestore-3b00e",
  "private_key_id": "f49d6b540c36c425ec9f5ea817e0faa0bf57ba4b",
  "private_key": PRIVATE_KEY,
  "client_email": "firebase-adminsdk-fbsvc@projeto-teste-firestore-3b00e.iam.gserviceaccount.com",
  "client_id": "111433153634667022528",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/firebase-adminsdk-fbsvc%40projeto-teste-firestore-3b00e.iam.gserviceaccount.com",
  "universe_domain": "googleapis.com"
}

try:
    cred = credentials.Certificate(FIREBASE_CONFIG)
    firebase_admin.initialize_app(cred)
    print("SUCCESS: SDK init passed with config dictionary!")
except Exception as e:
    print(f"FAILED: {e}")
