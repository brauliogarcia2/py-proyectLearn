"""Reloj Digital, Ciclos de Enfoque (Pomodoro), Tareas y Calendario de Rutinas Diarias.

Interfaz moderna en Tkinter con sonido armónico, mini-calendario mensual y control de hábitos.
"""

import calendar
import json
import os
import threading
import tkinter as tk
from tkinter import messagebox
from datetime import datetime, date

# Módulo de sonido nativo en Windows
try:
    import winsound
except ImportError:
    winsound = None

ARCHIVO_TAREAS = "tareas.json"
ARCHIVO_RUTINAS = "rutinas.json"


def reproducir_sonido_alarma():
    """Reproduce una melodía de alarma agradable en un hilo separado para no congelar la UI."""
    def _tocar():
        if winsound:
            try:
                # Secuencia de tonos armónicos ascendentes (Do - Mi - Sol - Do agudo)
                melodia = [(523, 160), (659, 160), (784, 160), (1046, 350)]
                for frec, dur in melodia:
                    winsound.Beep(frec, dur)
            except Exception:
                try:
                    winsound.MessageBeep(winsound.MB_ICONASTERISK)
                except Exception:
                    pass

    threading.Thread(target=_tocar, daemon=True).start()


class RelojProductivo:
    def __init__(self, root):
        self.root = root
        self.root.title("Reloj & Productividad Personal")
        self.root.geometry("480x700")
        self.root.configure(bg="#121214")
        self.root.resizable(False, False)

        # Variables de estado del reloj y ciclos
        self.formato_24h = True
        self.tiempo_restante = 25 * 60  # 25 minutos
        self.pomodoro_corriendo = False
        self.temporizador_id = None
        self.modo_ciclo = "Enfoque"
        self.ciclos_completados = 0
        self.tarea_activa = "Sin tarea asignada"

        # Variables de calendario
        hoy = date.today()
        self.cal_anio = hoy.year
        self.cal_mes = hoy.month
        self.fecha_seleccionada = hoy.strftime("%Y-%m-%d")

        # Cargar datos persistentes
        self.tareas = self.cargar_tareas()
        self.datos_rutinas = self.cargar_rutinas()

        # Construir Interfaz
        self._construir_encabezado_reloj()
        self._construir_pestanas()
        self._construir_panel_ciclos()
        self._construir_panel_pendientes()
        self._construir_panel_calendario()

        # Iniciar en la pestaña de Ciclos
        self.mostrar_pestana("ciclos")

        # Iniciar actualización del reloj
        self.actualizar_reloj()

    # -------------------------------------------------------------
    # 1. ENCABEZADO: RELOJ Y FECHA
    # -------------------------------------------------------------
    def _construir_encabezado_reloj(self):
        frame_reloj = tk.Frame(self.root, bg="#18181b", bd=0)
        frame_reloj.pack(fill="x", padx=16, pady=(12, 6))

        # Hora
        self.label_hora = tk.Label(
            frame_reloj,
            font=("Segoe UI", 34, "bold"),
            bg="#18181b",
            fg="#00E5FF",
            cursor="hand2"
        )
        self.label_hora.pack(pady=(6, 0))
        self.label_hora.bind("<Button-1>", self.alternar_formato)

        # Fecha
        self.label_fecha = tk.Label(
            frame_reloj,
            font=("Segoe UI", 10),
            bg="#18181b",
            fg="#a1a1aa"
        )
        self.label_fecha.pack(pady=(0, 2))

        # Tip
        label_tip = tk.Label(
            frame_reloj,
            text="(Haz clic en la hora para alternar 12h / 24h)",
            font=("Segoe UI", 8),
            bg="#18181b",
            fg="#52525b"
        )
        label_tip.pack(pady=(0, 6))

    # -------------------------------------------------------------
    # 2. PESTAÑAS MODERNAS DE NAVEGACIÓN
    # -------------------------------------------------------------
    def _construir_pestanas(self):
        frame_nav = tk.Frame(self.root, bg="#121214")
        frame_nav.pack(fill="x", padx=16, pady=(4, 6))

        self.btn_tab_ciclos = tk.Button(
            frame_nav,
            text="⏱️ Ciclos",
            font=("Segoe UI", 9, "bold"),
            bg="#27272a",
            fg="#ffffff",
            bd=0,
            pady=6,
            cursor="hand2",
            command=lambda: self.mostrar_pestana("ciclos")
        )
        self.btn_tab_ciclos.pack(side="left", expand=True, fill="x", padx=(0, 2))

        self.btn_tab_pendientes = tk.Button(
            frame_nav,
            text=f"📋 Tareas ({len(self.tareas)})",
            font=("Segoe UI", 9, "bold"),
            bg="#18181b",
            fg="#71717a",
            bd=0,
            pady=6,
            cursor="hand2",
            command=lambda: self.mostrar_pestana("pendientes")
        )
        self.btn_tab_pendientes.pack(side="left", expand=True, fill="x", padx=2)

        self.btn_tab_calendario = tk.Button(
            frame_nav,
            text="📅 Calendario & Rutinas",
            font=("Segoe UI", 9, "bold"),
            bg="#18181b",
            fg="#71717a",
            bd=0,
            pady=6,
            cursor="hand2",
            command=lambda: self.mostrar_pestana("calendario")
        )
        self.btn_tab_calendario.pack(side="left", expand=True, fill="x", padx=(2, 0))

    def mostrar_pestana(self, pestana):
        self.frame_ciclos.pack_forget()
        self.frame_pendientes.pack_forget()
        self.frame_calendario.pack_forget()

        # Restaurar estilos de botones
        tabs = [
            ("ciclos", self.btn_tab_ciclos, self.frame_ciclos),
            ("pendientes", self.btn_tab_pendientes, self.frame_pendientes),
            ("calendario", self.btn_tab_calendario, self.frame_calendario)
        ]

        for nombre, btn, frame in tabs:
            if nombre == pestana:
                frame.pack(fill="both", expand=True, padx=16, pady=4)
                btn.config(bg="#27272a", fg="#ffffff")
            else:
                btn.config(bg="#18181b", fg="#71717a")

        if pestana == "pendientes":
            self.actualizar_vista_tareas()
        elif pestana == "calendario":
            self.actualizar_vista_calendario()

    # -------------------------------------------------------------
    # 3. PESTAÑA: CICLOS DE ENFOQUE (POMODORO) CON SONIDO
    # -------------------------------------------------------------
    def _construir_panel_ciclos(self):
        self.frame_ciclos = tk.Frame(self.root, bg="#18181b")

        # Tarea de foco
        frame_tarea_foco = tk.Frame(self.frame_ciclos, bg="#27272a", bd=0)
        frame_tarea_foco.pack(fill="x", padx=12, pady=(10, 8))

        lbl_foco_title = tk.Label(
            frame_tarea_foco,
            text="🎯 ENFOCÁNDOSE EN:",
            font=("Segoe UI", 8, "bold"),
            bg="#27272a",
            fg="#a1a1aa"
        )
        lbl_foco_title.pack(anchor="w", padx=10, pady=(6, 0))

        self.lbl_tarea_activa = tk.Label(
            frame_tarea_foco,
            text=self.tarea_activa,
            font=("Segoe UI", 10, "bold"),
            bg="#27272a",
            fg="#38bdf8",
            wraplength=400,
            justify="left"
        )
        self.lbl_tarea_activa.pack(anchor="w", padx=10, pady=(2, 6))

        # Modos
        frame_modos = tk.Frame(self.frame_ciclos, bg="#18181b")
        frame_modos.pack(pady=8)

        self.btn_modo_foco = tk.Button(
            frame_modos,
            text="🎯 Enfoque (25m)",
            font=("Segoe UI", 9, "bold"),
            bg="#0284c7",
            fg="white",
            bd=0,
            padx=8,
            pady=4,
            cursor="hand2",
            command=lambda: self.seleccionar_modo("Enfoque", 25 * 60)
        )
        self.btn_modo_foco.pack(side="left", padx=3)

        self.btn_modo_corto = tk.Button(
            frame_modos,
            text="☕ Descanso (5m)",
            font=("Segoe UI", 9),
            bg="#27272a",
            fg="#d4d4d8",
            bd=0,
            padx=8,
            pady=4,
            cursor="hand2",
            command=lambda: self.seleccionar_modo("Descanso Corto", 5 * 60)
        )
        self.btn_modo_corto.pack(side="left", padx=3)

        self.btn_modo_largo = tk.Button(
            frame_modos,
            text="🌴 Descanso (15m)",
            font=("Segoe UI", 9),
            bg="#27272a",
            fg="#d4d4d8",
            bd=0,
            padx=8,
            pady=4,
            cursor="hand2",
            command=lambda: self.seleccionar_modo("Descanso Largo", 15 * 60)
        )
        self.btn_modo_largo.pack(side="left", padx=3)

        # Contador
        self.lbl_tiempo_ciclo = tk.Label(
            self.frame_ciclos,
            text="25:00",
            font=("Segoe UI", 48, "bold"),
            bg="#18181b",
            fg="#f4f4f5"
        )
        self.lbl_tiempo_ciclo.pack(pady=(4, 2))

        self.lbl_estado_ciclo = tk.Label(
            self.frame_ciclos,
            text="Ciclo de Enfoque listo",
            font=("Segoe UI", 10),
            bg="#18181b",
            fg="#a1a1aa"
        )
        self.lbl_estado_ciclo.pack(pady=(0, 10))

        # Botones
        frame_controles = tk.Frame(self.frame_ciclos, bg="#18181b")
        frame_controles.pack(pady=4)

        self.btn_iniciar_ciclo = tk.Button(
            frame_controles,
            text="▶ Iniciar",
            font=("Segoe UI", 11, "bold"),
            bg="#10b981",
            fg="white",
            bd=0,
            width=12,
            pady=6,
            cursor="hand2",
            command=self.alternar_ciclo
        )
        self.btn_iniciar_ciclo.pack(side="left", padx=6)

        self.btn_reset_ciclo = tk.Button(
            frame_controles,
            text="↺ Reiniciar",
            font=("Segoe UI", 11),
            bg="#3f3f46",
            fg="white",
            bd=0,
            width=10,
            pady=6,
            cursor="hand2",
            command=self.reiniciar_ciclo
        )
        self.btn_reset_ciclo.pack(side="left", padx=6)

        # Contador de rachas
        self.lbl_contador_ciclos = tk.Label(
            self.frame_ciclos,
            text="🔥 Ciclos de enfoque completados: 0",
            font=("Segoe UI", 9),
            bg="#18181b",
            fg="#eab308"
        )
        self.lbl_contador_ciclos.pack(pady=(14, 8))

    def seleccionar_modo(self, modo, segundos):
        if self.pomodoro_corriendo:
            if not messagebox.askyesno("Cambiar Modo", "¿Deseas interrumpir el ciclo actual?"):
                return
            self.pausar_ciclo()

        self.modo_ciclo = modo
        self.tiempo_restante = segundos

        btn_dict = {
            "Enfoque": self.btn_modo_foco,
            "Descanso Corto": self.btn_modo_corto,
            "Descanso Largo": self.btn_modo_largo
        }
        for nombre, btn in btn_dict.items():
            if nombre == modo:
                btn.config(bg="#0284c7", fg="white", font=("Segoe UI", 9, "bold"))
            else:
                btn.config(bg="#27272a", fg="#d4d4d8", font=("Segoe UI", 9))

        self.lbl_estado_ciclo.config(text=f"{modo} listo")
        self._actualizar_pantalla_ciclo()

    def alternar_ciclo(self):
        if not self.pomodoro_corriendo:
            self.pomodoro_corriendo = True
            self.btn_iniciar_ciclo.config(text="⏸ Pausar", bg="#f59e0b")
            self.lbl_estado_ciclo.config(text=f"En progreso: {self.modo_ciclo}...")
            self.ejecutar_cuenta_regresiva()
        else:
            self.pausar_ciclo()

    def pausar_ciclo(self):
        self.pomodoro_corriendo = False
        if self.temporizador_id:
            self.root.after_cancel(self.temporizador_id)
            self.temporizador_id = None
        self.btn_iniciar_ciclo.config(text="▶ Reanudar", bg="#10b981")
        self.lbl_estado_ciclo.config(text=f"Pausado: {self.modo_ciclo}")

    def reiniciar_ciclo(self):
        if self.temporizador_id:
            self.root.after_cancel(self.temporizador_id)
            self.temporizador_id = None
        self.pomodoro_corriendo = False
        self.btn_iniciar_ciclo.config(text="▶ Iniciar", bg="#10b981")

        duraciones = {
            "Enfoque": 25 * 60,
            "Descanso Corto": 5 * 60,
            "Descanso Largo": 15 * 60
        }
        self.tiempo_restante = duraciones.get(self.modo_ciclo, 25 * 60)
        self.lbl_estado_ciclo.config(text=f"{self.modo_ciclo} reiniciado")
        self._actualizar_pantalla_ciclo()

    def ejecutar_cuenta_regresiva(self):
        if self.pomodoro_corriendo and self.tiempo_restante > 0:
            self.tiempo_restante -= 1
            self._actualizar_pantalla_ciclo()
            self.temporizador_id = self.root.after(1000, self.ejecutar_cuenta_regresiva)
        elif self.pomodoro_corriendo and self.tiempo_restante <= 0:
            self.pomodoro_corriendo = False
            self.btn_iniciar_ciclo.config(text="▶ Iniciar", bg="#10b981")

            # REPRODUCIR SONIDO DE ALARMA
            reproducir_sonido_alarma()

            if self.modo_ciclo == "Enfoque":
                self.ciclos_completados += 1
                self.lbl_contador_ciclos.config(
                    text=f"🔥 Ciclos de enfoque completados: {self.ciclos_completados}"
                )
                messagebox.showinfo(
                    "🔔 ¡Tiempo Terminado!",
                    "¡Excelente trabajo! Has completado tu ciclo de enfoque.\nTómate un merecido descanso."
                )
                self.seleccionar_modo("Descanso Corto", 5 * 60)
            else:
                messagebox.showinfo(
                    "🔔 ¡Descanso Finalizado!",
                    "Tu descanso ha terminado. ¿Listo para el próximo ciclo de enfoque?"
                )
                self.seleccionar_modo("Enfoque", 25 * 60)

    def _actualizar_pantalla_ciclo(self):
        minutos = self.tiempo_restante // 60
        segundos = self.tiempo_restante % 60
        self.lbl_tiempo_ciclo.config(text=f"{minutos:02d}:{segundos:02d}")

    # -------------------------------------------------------------
    # 4. PESTAÑA: TAREAS PENDIENTES (TO-DO LIST)
    # -------------------------------------------------------------
    def _construir_panel_pendientes(self):
        self.frame_pendientes = tk.Frame(self.root, bg="#18181b")

        frame_input = tk.Frame(self.frame_pendientes, bg="#18181b")
        frame_input.pack(fill="x", padx=10, pady=(8, 6))

        self.entry_nueva_tarea = tk.Entry(
            frame_input,
            font=("Segoe UI", 11),
            bg="#27272a",
            fg="#ffffff",
            insertbackground="#ffffff",
            bd=0
        )
        self.entry_nueva_tarea.pack(side="left", fill="x", expand=True, ipady=6, padx=(0, 6))
        self.entry_nueva_tarea.bind("<Return>", lambda e: self.agregar_tarea())

        btn_agregar = tk.Button(
            frame_input,
            text="+ Añadir",
            font=("Segoe UI", 10, "bold"),
            bg="#0284c7",
            fg="white",
            bd=0,
            padx=10,
            pady=4,
            cursor="hand2",
            command=self.agregar_tarea
        )
        btn_agregar.pack(side="right")

        frame_lista_scroll = tk.Frame(self.frame_pendientes, bg="#18181b")
        frame_lista_scroll.pack(fill="both", expand=True, padx=10, pady=4)

        self.canvas_tareas = tk.Canvas(frame_lista_scroll, bg="#18181b", bd=0, highlightthickness=0)
        scrollbar = tk.Scrollbar(frame_lista_scroll, orient="vertical", command=self.canvas_tareas.yview)
        self.frame_lista_interior = tk.Frame(self.canvas_tareas, bg="#18181b")

        self.frame_lista_interior.bind(
            "<Configure>",
            lambda e: self.canvas_tareas.configure(scrollregion=self.canvas_tareas.bbox("all"))
        )

        self.canvas_tareas.create_window((0, 0), window=self.frame_lista_interior, anchor="nw", width=420)
        self.canvas_tareas.configure(yscrollcommand=scrollbar.set)

        self.canvas_tareas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def cargar_tareas(self):
        if os.path.exists(ARCHIVO_TAREAS):
            try:
                with open(ARCHIVO_TAREAS, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return []
        return [
            {"texto": "Definir objetivos principales", "completada": False},
            {"texto": "Bloque de estudio / trabajo 25m", "completada": False}
        ]

    def guardar_tareas(self):
        try:
            with open(ARCHIVO_TAREAS, "w", encoding="utf-8") as f:
                json.dump(self.tareas, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print("Error al guardar tareas:", e)

    def agregar_tarea(self):
        texto = self.entry_nueva_tarea.get().strip()
        if texto:
            self.tareas.append({"texto": texto, "completada": False})
            self.entry_nueva_tarea.delete(0, tk.END)
            self.guardar_tareas()
            self.actualizar_vista_tareas()
            self.btn_tab_pendientes.config(text=f"📋 Tareas ({len(self.tareas)})")

    def alternar_completada(self, indice):
        if 0 <= indice < len(self.tareas):
            self.tareas[indice]["completada"] = not self.tareas[indice]["completada"]
            self.guardar_tareas()
            self.actualizar_vista_tareas()

    def eliminar_tarea(self, indice):
        if 0 <= indice < len(self.tareas):
            if self.tarea_activa == self.tareas[indice]["texto"]:
                self.asignar_tarea_activa("Sin tarea asignada")
            self.tareas.pop(indice)
            self.guardar_tareas()
            self.actualizar_vista_tareas()
            self.btn_tab_pendientes.config(text=f"📋 Tareas ({len(self.tareas)})")

    def asignar_tarea_activa(self, texto):
        self.tarea_activa = texto
        self.lbl_tarea_activa.config(text=self.tarea_activa)
        self.mostrar_pestana("ciclos")

    def actualizar_vista_tareas(self):
        for widget in self.frame_lista_interior.winfo_children():
            widget.destroy()

        if not self.tareas:
            lbl_vacio = tk.Label(
                self.frame_lista_interior,
                text="No tienes tareas pendientes 🎉",
                font=("Segoe UI", 11, "italic"),
                bg="#18181b",
                fg="#71717a"
            )
            lbl_vacio.pack(pady=20)
            return

        for i, item in enumerate(self.tareas):
            item_frame = tk.Frame(self.frame_lista_interior, bg="#27272a", bd=0)
            item_frame.pack(fill="x", pady=3, ipady=3)

            check_char = "✔" if item["completada"] else "○"
            check_fg = "#10b981" if item["completada"] else "#71717a"
            btn_check = tk.Button(
                item_frame,
                text=check_char,
                font=("Segoe UI", 10, "bold"),
                bg="#27272a",
                fg=check_fg,
                bd=0,
                cursor="hand2",
                command=lambda idx=i: self.alternar_completada(idx)
            )
            btn_check.pack(side="left", padx=6)

            color_texto = "#71717a" if item["completada"] else "#f4f4f5"
            lbl_txt = tk.Label(
                item_frame,
                text=item["texto"],
                font=("Segoe UI", 10, "overstrike" if item["completada"] else "normal"),
                bg="#27272a",
                fg=color_texto,
                anchor="w",
                wraplength=250,
                justify="left"
            )
            lbl_txt.pack(side="left", fill="x", expand=True, padx=2)

            if not item["completada"]:
                btn_foco = tk.Button(
                    item_frame,
                    text="🎯 Foco",
                    font=("Segoe UI", 8),
                    bg="#0369a1",
                    fg="#ffffff",
                    bd=0,
                    cursor="hand2",
                    padx=4,
                    command=lambda t=item["texto"]: self.asignar_tarea_activa(t)
                )
                btn_foco.pack(side="right", padx=4)

            btn_del = tk.Button(
                item_frame,
                text="✕",
                font=("Segoe UI", 9),
                bg="#27272a",
                fg="#ef4444",
                bd=0,
                cursor="hand2",
                command=lambda idx=i: self.eliminar_tarea(idx)
            )
            btn_del.pack(side="right", padx=6)

    # -------------------------------------------------------------
    # 5. PESTAÑA: CALENDARIO & RUTINAS DIARIAS
    # -------------------------------------------------------------
    def _construir_panel_calendario(self):
        self.frame_calendario = tk.Frame(self.root, bg="#18181b")

        # Cabecera del mes con botones < >
        frame_mes_nav = tk.Frame(self.frame_calendario, bg="#18181b")
        frame_mes_nav.pack(fill="x", padx=10, pady=(8, 4))

        btn_prev = tk.Button(
            frame_mes_nav,
            text="◀",
            font=("Segoe UI", 9),
            bg="#27272a",
            fg="white",
            bd=0,
            padx=8,
            cursor="hand2",
            command=self.mes_anterior
        )
        btn_prev.pack(side="left")

        self.lbl_mes_titulo = tk.Label(
            frame_mes_nav,
            text="",
            font=("Segoe UI", 11, "bold"),
            bg="#18181b",
            fg="#f4f4f5"
        )
        self.lbl_mes_titulo.pack(side="left", expand=True)

        btn_next = tk.Button(
            frame_mes_nav,
            text="▶",
            font=("Segoe UI", 9),
            bg="#27272a",
            fg="white",
            bd=0,
            padx=8,
            cursor="hand2",
            command=self.mes_siguiente
        )
        btn_next.pack(side="right")

        # Cuadrícula del Calendario
        self.frame_grid_dias = tk.Frame(self.frame_calendario, bg="#18181b")
        self.frame_grid_dias.pack(padx=10, pady=2)

        # Separador / Barra de Rutinas
        frame_rutinas_header = tk.Frame(self.frame_calendario, bg="#27272a", bd=0)
        frame_rutinas_header.pack(fill="x", padx=10, pady=(8, 4), ipady=3)

        self.lbl_rutina_fecha = tk.Label(
            frame_rutinas_header,
            text="",
            font=("Segoe UI", 9, "bold"),
            bg="#27272a",
            fg="#00E5FF"
        )
        self.lbl_rutina_fecha.pack(side="left", padx=8)

        self.lbl_rutina_progreso = tk.Label(
            frame_rutinas_header,
            text="Progreso: 0%",
            font=("Segoe UI", 9),
            bg="#27272a",
            fg="#a1a1aa"
        )
        self.lbl_rutina_progreso.pack(side="right", padx=8)

        # Input para nueva rutina habitual
        frame_input_rutina = tk.Frame(self.frame_calendario, bg="#18181b")
        frame_input_rutina.pack(fill="x", padx=10, pady=(4, 4))

        self.entry_nueva_rutina = tk.Entry(
            frame_input_rutina,
            font=("Segoe UI", 10),
            bg="#27272a",
            fg="#ffffff",
            insertbackground="#ffffff",
            bd=0
        )
        self.entry_nueva_rutina.pack(side="left", fill="x", expand=True, ipady=5, padx=(0, 6))
        self.entry_nueva_rutina.bind("<Return>", lambda e: self.agregar_rutina())

        btn_add_rutina = tk.Button(
            frame_input_rutina,
            text="+ Rutina",
            font=("Segoe UI", 9, "bold"),
            bg="#0284c7",
            fg="white",
            bd=0,
            padx=8,
            pady=3,
            cursor="hand2",
            command=self.agregar_rutina
        )
        btn_add_rutina.pack(side="right")

        # Lista de rutinas con scroll
        frame_scroll_rutinas = tk.Frame(self.frame_calendario, bg="#18181b")
        frame_scroll_rutinas.pack(fill="both", expand=True, padx=10, pady=(2, 6))

        self.canvas_rutinas = tk.Canvas(frame_scroll_rutinas, bg="#18181b", bd=0, highlightthickness=0)
        scrollbar_rutinas = tk.Scrollbar(frame_scroll_rutinas, orient="vertical", command=self.canvas_rutinas.yview)
        self.frame_rutinas_interior = tk.Frame(self.canvas_rutinas, bg="#18181b")

        self.frame_rutinas_interior.bind(
            "<Configure>",
            lambda e: self.canvas_rutinas.configure(scrollregion=self.canvas_rutinas.bbox("all"))
        )

        self.canvas_rutinas.create_window((0, 0), window=self.frame_rutinas_interior, anchor="nw", width=420)
        self.canvas_rutinas.configure(yscrollcommand=scrollbar_rutinas.set)

        self.canvas_rutinas.pack(side="left", fill="both", expand=True)
        scrollbar_rutinas.pack(side="right", fill="y")

    def cargar_rutinas(self):
        if os.path.exists(ARCHIVO_RUTINAS):
            try:
                with open(ARCHIVO_RUTINAS, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "rutinas_base": [
                "💧 Beber 2L de agua",
                "🏃 Ejercicio / Estiramiento 15m",
                "📖 Lectura o Estudio 20m",
                "🎯 Planificar tareas del día"
            ],
            "registro": {}
        }

    def guardar_rutinas(self):
        try:
            with open(ARCHIVO_RUTINAS, "w", encoding="utf-8") as f:
                json.dump(self.datos_rutinas, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print("Error al guardar rutinas:", e)

    def mes_anterior(self):
        if self.cal_mes == 1:
            self.cal_mes = 12
            self.cal_anio -= 1
        else:
            self.cal_mes -= 1
        self.actualizar_vista_calendario()

    def mes_siguiente(self):
        if self.cal_mes == 12:
            self.cal_mes = 1
            self.cal_anio += 1
        else:
            self.cal_mes += 1
        self.actualizar_vista_calendario()

    def seleccionar_dia(self, dia_num):
        fecha_str = f"{self.cal_anio:04d}-{self.cal_mes:02d}-{dia_num:02d}"
        self.fecha_seleccionada = fecha_str
        self.actualizar_vista_calendario()

    def actualizar_vista_calendario(self):
        # Nombres de meses en español
        meses = [
            "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
            "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
        ]
        self.lbl_mes_titulo.config(text=f"{meses[self.cal_mes - 1]} {self.cal_anio}")

        # Limpiar cuadrícula
        for w in self.frame_grid_dias.winfo_children():
            w.destroy()

        # Días de la semana
        dias_abrev = ["Lu", "Ma", "Mi", "Ju", "Vi", "Sa", "Do"]
        for col, dia_txt in enumerate(dias_abrev):
            lbl_c = tk.Label(
                self.frame_grid_dias,
                text=dia_txt,
                font=("Segoe UI", 9, "bold"),
                bg="#18181b",
                fg="#a1a1aa",
                width=5
            )
            lbl_c.grid(row=0, column=col, padx=1, pady=2)

        # Matriz de días del mes
        cal_matriz = calendar.monthcalendar(self.cal_anio, self.cal_mes)
        hoy_str = date.today().strftime("%Y-%m-%d")

        for fila, semana in enumerate(cal_matriz, start=1):
            for col, dia in enumerate(semana):
                if dia == 0:
                    lbl_v = tk.Label(self.frame_grid_dias, text="", bg="#18181b", width=5)
                    lbl_v.grid(row=fila, column=col)
                else:
                    fecha_boton = f"{self.cal_anio:04d}-{self.cal_mes:02d}-{dia:02d}"
                    es_hoy = (fecha_boton == hoy_str)
                    es_seleccionado = (fecha_boton == self.fecha_seleccionada)

                    bg_color = "#27272a"
                    fg_color = "#f4f4f5"

                    if es_seleccionado:
                        bg_color = "#0284c7"  # Azul selección
                        fg_color = "#ffffff"
                    elif es_hoy:
                        bg_color = "#0e7490"  # Cian oscuro para hoy
                        fg_color = "#ffffff"

                    btn_dia = tk.Button(
                        self.frame_grid_dias,
                        text=str(dia),
                        font=("Segoe UI", 8, "bold" if (es_hoy or es_seleccionado) else "normal"),
                        bg=bg_color,
                        fg=fg_color,
                        bd=0,
                        width=5,
                        pady=2,
                        cursor="hand2",
                        command=lambda d=dia: self.seleccionar_dia(d)
                    )
                    btn_dia.grid(row=fila, column=col, padx=1, pady=1)

        # Actualizar lista de rutinas para la fecha seleccionada
        self.actualizar_vista_rutinas()

    def agregar_rutina(self):
        texto = self.entry_nueva_rutina.get().strip()
        if texto:
            if texto not in self.datos_rutinas["rutinas_base"]:
                self.datos_rutinas["rutinas_base"].append(texto)
                self.guardar_rutinas()
            self.entry_nueva_rutina.delete(0, tk.END)
            self.actualizar_vista_rutinas()

    def alternar_rutina(self, nombre_rutina):
        reg = self.datos_rutinas.setdefault("registro", {})
        completadas_dia = reg.setdefault(self.fecha_seleccionada, [])

        if nombre_rutina in completadas_dia:
            completadas_dia.remove(nombre_rutina)
        else:
            completadas_dia.append(nombre_rutina)

        self.guardar_rutinas()
        self.actualizar_vista_rutinas()

    def eliminar_rutina_base(self, nombre_rutina):
        if nombre_rutina in self.datos_rutinas["rutinas_base"]:
            self.datos_rutinas["rutinas_base"].remove(nombre_rutina)
            # Limpiar del registro
            for dia in self.datos_rutinas.get("registro", {}):
                if nombre_rutina in self.datos_rutinas["registro"][dia]:
                    self.datos_rutinas["registro"][dia].remove(nombre_rutina)
            self.guardar_rutinas()
            self.actualizar_vista_rutinas()

    def actualizar_vista_rutinas(self):
        for w in self.frame_rutinas_interior.winfo_children():
            w.destroy()

        self.lbl_rutina_fecha.config(text=f"Rutinas: {self.fecha_seleccionada}")

        rutinas = self.datos_rutinas.get("rutinas_base", [])
        completadas = self.datos_rutinas.get("registro", {}).get(self.fecha_seleccionada, [])

        total = len(rutinas)
        hechas = len([r for r in rutinas if r in completadas])
        porcentaje = int((hechas / total) * 100) if total > 0 else 0
        self.lbl_rutina_progreso.config(text=f"Progreso: {hechas}/{total} ({porcentaje}%)")

        if not rutinas:
            lbl_v = tk.Label(
                self.frame_rutinas_interior,
                text="Agrega tus hábitos diarios arriba 👆",
                font=("Segoe UI", 10, "italic"),
                bg="#18181b",
                fg="#71717a"
            )
            lbl_v.pack(pady=10)
            return

        for r in rutinas:
            cumplida = (r in completadas)
            item_frame = tk.Frame(self.frame_rutinas_interior, bg="#27272a", bd=0)
            item_frame.pack(fill="x", pady=2, ipady=2)

            check_char = "✔" if cumplida else "○"
            check_fg = "#10b981" if cumplida else "#71717a"
            btn_check = tk.Button(
                item_frame,
                text=check_char,
                font=("Segoe UI", 10, "bold"),
                bg="#27272a",
                fg=check_fg,
                bd=0,
                cursor="hand2",
                command=lambda nom=r: self.alternar_rutina(nom)
            )
            btn_check.pack(side="left", padx=6)

            lbl_txt = tk.Label(
                item_frame,
                text=r,
                font=("Segoe UI", 9, "overstrike" if cumplida else "normal"),
                bg="#27272a",
                fg="#71717a" if cumplida else "#f4f4f5",
                anchor="w",
                wraplength=280,
                justify="left"
            )
            lbl_txt.pack(side="left", fill="x", expand=True, padx=2)

            btn_del = tk.Button(
                item_frame,
                text="✕",
                font=("Segoe UI", 8),
                bg="#27272a",
                fg="#ef4444",
                bd=0,
                cursor="hand2",
                command=lambda nom=r: self.eliminar_rutina_base(nom)
            )
            btn_del.pack(side="right", padx=6)

    # -------------------------------------------------------------
    # 6. RELOJ EN TIEMPO REAL
    # -------------------------------------------------------------
    def alternar_formato(self, event=None):
        self.formato_24h = not self.formato_24h
        self.actualizar_reloj()

    def actualizar_reloj(self):
        ahora = datetime.now()

        fmt_hora = "%H:%M:%S" if self.formato_24h else "%I:%M:%S %p"
        self.label_hora.config(text=ahora.strftime(fmt_hora))

        dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
        meses = [
            "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
            "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
        ]
        dia_semana = dias[ahora.weekday()]
        mes_nombre = meses[ahora.month - 1]
        self.label_fecha.config(
            text=f"{dia_semana}, {ahora.day} de {mes_nombre} de {ahora.year}"
        )

        milisegundos_restantes = max(1, 1000 - (ahora.microsecond // 1000))
        self.root.after(milisegundos_restantes, self.actualizar_reloj)


if __name__ == "__main__":
    ventana = tk.Tk()
    app = RelojProductivo(ventana)
    ventana.mainloop()