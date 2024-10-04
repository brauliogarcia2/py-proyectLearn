"cronometro"

import tkinter as tk

class Cronometro:
    def __init__(self, root):
        self.root = root
        self.root.title("Cronómetro")

        # Tiempo en segundos
        self.tiempo = 0
        self.cronometro_corriendo = False

        # Etiqueta para mostrar el tiempo
        self.label_tiempo = tk.Label(root, text='00:00:00', font=('calibri', 40, 'bold'))
        self.label_tiempo.pack(pady=20)

        # Botones
        self.boton_iniciar = tk.Button(root, text='Iniciar', command=self.iniciar)
        self.boton_iniciar.pack(side='left', padx=10)

        self.boton_detener = tk.Button(root, text='Detener', command=self.detener)
        self.boton_detener.pack(side='left', padx=10)

        self.boton_reiniciar = tk.Button(root, text='Reiniciar', command=self.reiniciar)
        self.boton_reiniciar.pack(side='left', padx=10)

    def actualizar(self):
        if self.cronometro_corriendo:
            self.tiempo += 1
            minutos, segundos = divmod(self.tiempo, 60)
            horas, minutos = divmod(minutos, 60)
            tiempo_formateado = f'{horas:02}:{minutos:02}:{segundos:02}'
            self.label_tiempo.config(text=tiempo_formateado)
            self.root.after(1000, self.actualizar)

    def iniciar(self):
        if not self.cronometro_corriendo:
            self.cronometro_corriendo = True
            self.actualizar()

    def detener(self):
        self.cronometro_corriendo = False

    def reiniciar(self):
        self.cronometro_corriendo = False
        self.tiempo = 0
        self.label_tiempo.config(text='00:00:00')

# Configuración de la ventana principal
root = tk.Tk()
app = Cronometro(root)
root.mainloop()
