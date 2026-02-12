import bcrypt


def create_password(password:str):
    # bytes olmalı
    psw_bytes = password.encode("utf-8")

    HASHED_PSW = bcrypt.hashpw(psw_bytes, bcrypt.gensalt())

    print("Hashed Password: ", HASHED_PSW)