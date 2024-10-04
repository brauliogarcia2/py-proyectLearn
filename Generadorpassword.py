""" Generador de contraseñas"""


import secrets
import string

def crear_password(longitud):
    todo_caracteres = string.ascii_letters + string.digits + string.punctuation
    password = ""
    for _ in range(longitud):
        password += secrets.choice(todo_caracteres)
        return password
    
    nuevo_pass = crear_password(10)
    print(nuevo_pass)
