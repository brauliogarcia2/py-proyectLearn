"Reloj Que se actualiza Cada Segundo En Consola"""

import tkinter as tk
import time

def actualizar_reloj():
    # Obtén la hora actual en formato HH:MM:SS
    tiempo_actual = time.strftime("%H:%M:%S")
    # Actualiza el texto del label con la hora actual
    label_reloj.config(text=tiempo_actual)
    # Llama a esta función nuevamente después de 1000 ms (1 segundo)
    root.after(1000, actualizar_reloj)

# Crea una ventana principal
root = tk.Tk()
root.title("Reloj en Python")

# Crea un widget Label para mostrar la hora
label_reloj = tk.Label(root, font=("calibri", 40, "bold"), background="black",foreground="white")
label_reloj.pack(anchor="center")

# Llama a la función para actualizar el reloj
actualizar_reloj()

# Inicia el bucle principal de la interfaz gráfica
root.mainloop()
