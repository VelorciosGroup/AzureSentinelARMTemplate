from tkinter import Tk, ttk, messagebox, filedialog
import tkinter as tk
import os
import json
import main
import parametrize



def rendergui():

    params_for_file = {}
    depends_on = {}

    root = Tk()
    root.title("Creador de Master Templates")
    root.geometry("1000x1000")
    root.resizable(False, False)
    
    canvas = tk.Canvas(root, borderwidth=0)
    scrollbar = ttk.Scrollbar(root, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=scrollbar.set)

    scrollbar.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)

    # Frame interior dentro del canvas
    frame_interior = ttk.Frame(canvas)
    canvas.create_window((0,0), window=frame_interior, anchor="nw")

    def actualizar_scroll(event):
        canvas.configure(scrollregion=canvas.bbox("all"))

    frame_interior.bind("<Configure>", actualizar_scroll)

    def _on_mousewheel(event):
        # Windows / Mac
        canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    canvas.bind_all("<MouseWheel>", _on_mousewheel)  # Windows
    canvas.bind_all("<Button-4>", lambda e: canvas.yview_scroll(-1, "units"))  # Linux
    canvas.bind_all("<Button-5>", lambda e: canvas.yview_scroll(1, "units"))   # Linux

    def error(mensaje):
        root = tk.Tk()
        root.withdraw()  # Oculta la ventana principal
        
        # Muestra mensaje de error
        messagebox.showerror("Error", mensaje)
        
        # Cierra toda la aplicación
        root.destroy()
        exit()  # Opcional si quieres asegurarte de salir del script
    



    #________________________________ Estilos con ttk ________________________________

    style = ttk.Style()
    style.theme_use('clam')

    #____________________________________ Frames _____________________________________

    frame_base_templates = ttk.Frame(frame_interior, padding=10)
    frame_base_templates.pack(fill="x")

    frame_rename_templates = ttk.Frame(frame_interior, padding=10)
    frame_rename_templates.pack(fill="x")

    frame_variables = ttk.Frame(frame_interior, padding=10)
    frame_variables.pack(fill="x")

    frame_organize_variables = ttk.Frame(frame_interior, padding=10)
    frame_organize_variables.pack(fill="x")

    #__________________________________ base_templates _________________________________

    ttk.Label(frame_base_templates, text="Selección de las templates que se usarán").grid(row=0, column=0, sticky="w")
    lista_archivos = tk.Listbox(frame_base_templates, width=100, height=8)
    lista_archivos.grid(row=1, column=0, columnspan=2, pady=5)

    archivos = []  # lista interna para almacenar rutas

    def seleccionar_archivos():
        nonlocal params_for_file
        nonlocal depends_on

        nuevos = filedialog.askopenfilenames(
            filetypes=[("JSON files", "*.json")],
            title="Selecciona archivos JSON"
        )
        if nuevos:
            for archivo in nuevos:
                if archivo not in archivos:  # evitar duplicados
                    archivos.append(archivo)
                    lista_archivos.insert(tk.END, archivo)
        
        params_for_file = parametrize.parametrizeFiles(archivos)
        depends_on = parametrize.parametrizeDependsOn(archivos)

        for file in depends_on:
            for dependency in depends_on[file]:
                if dependency not in params_for_file.keys():
                    error(f"Workflow de archivo {file} no encontrado en los otros archivos seleccionados. Revisa si se ha seleccionado o se ha cambiado el nombre")
        
            

        mostrar_variables(frame_variables, params_for_file)


    def eliminar_seleccionados():
        seleccion = lista_archivos.curselection()
        if not seleccion:
            messagebox.showinfo("Info", "Selecciona un archivo para eliminar.")
            return
        
        # eliminar desde el final para no alterar índices
        for i in reversed(seleccion):
            archivos.pop(i)
            lista_archivos.delete(i)

    ttk.Button(frame_base_templates, text="Añadir JSON", command=seleccionar_archivos).grid(row=2, column=0, pady=5, sticky="w")

    ttk.Button(frame_base_templates, text="Eliminar seleccionado", command=eliminar_seleccionados).grid(row=2, column=1, pady=5, sticky="e")


    #__________________________________ renombrar templates _________________________________

    def abrir_renombrador(archivos):
        if not archivos:
            messagebox.showerror("Error", "No hay archivos seleccionados.")
            return
        
        ren_win = tk.Toplevel()
        ren_win.title("Renombrar Playbooks")

        frame = ttk.Frame(ren_win, padding=10)
        frame.pack(fill="both", expand=True)

        # Diccionario para guardar los valores nuevos
        renombres = {}

        # Para cada archivo, creo una fila con:
        # - Label: nombre original
        # - Entry: nuevo nombre
        for i, ruta in enumerate(archivos):
            nombre_original = os.path.basename(ruta)
            ttk.Label(frame, text=nombre_original).grid(row=i, column=0, sticky="w", pady=3)

            entry = ttk.Entry(frame, width=40)
            entry.grid(row=i, column=1, padx=10, pady=3)
            
            # guardo referencia del entry para luego obtener su valor
            renombres[ruta] = entry

        # botón para confirmar y obtener nombres
        def confirmar():
            resultado = {}
            for ruta, entry_widget in renombres.items():
                nuevo_nombre = entry_widget.get().strip()
                original = os.path.basename(ruta)

                # si no pone nada, queda el nombre original
                resultado[ruta] = nuevo_nombre if nuevo_nombre else original

            messagebox.showinfo("OK", "Nombres procesados en consola.")
            ren_win.destroy()

        ttk.Button(frame, text="Confirmar", command=confirmar)\
            .grid(row=len(archivos), column=0, columnspan=2, pady=10)
        
    
    ttk.Button(frame_rename_templates, text="Renombrar Playbooks",
           command=lambda: abrir_renombrador(archivos)).grid(row=3, column=0, pady=10)


    #__________________________________ Iniciar Variables _________________________________
    
    def mostrar_variables(frame_variables, params_for_file):
        # Limpiar frame por si se llama varias veces
        for widget in frame_variables.winfo_children():
            widget.destroy()

        ttk.Label(frame_variables, text="Variables por playbook").grid(row=0, column=0, sticky="w")

        row = 1
        for playbook, variables in params_for_file.items():
            ttk.Label(frame_variables, text=playbook.split("/")[-1]).grid(row=row, column=0, sticky="w", pady=(10,0))
            row += 1

            # Listbox para mostrar variables
            listbox = tk.Listbox(frame_variables, height=5, width=60)
            listbox.grid(row=row, column=0, columnspan=2, pady=5)
            row += 1

            # Llenar la lista
            for var, info in variables.items():
                listbox.insert(tk.END, f"{var} = {info['defaultValue']}")

            # Función para añadir variable
            def añadir_variable(playbook=playbook, lb=listbox):
                def guardar_variable(nombre, valor):
                    # Crear estructura {"defaultValue": valor, "type": "string"}
                    params_for_file[playbook][nombre] = {"defaultValue": valor, "type": "string"}
                    lb.insert(tk.END, f"{nombre} = {valor}")

                abrir_ventana_variable(guardar_variable)

            # Función para eliminar seleccionadas
            def eliminar_variable(playbook=playbook, lb=listbox):
                seleccion = lb.curselection()
                if not seleccion:
                    messagebox.showinfo("Info", "Selecciona una variable para eliminar.")
                    return
                for i in reversed(seleccion):
                    var_text = lb.get(i)
                    nombre = var_text.split(" = ")[0]
                    params_for_file[playbook].pop(nombre, None)
                    lb.delete(i)

            ttk.Button(frame_variables, text="Añadir variable", command=añadir_variable).grid(row=row, column=0, sticky="w")
            ttk.Button(frame_variables, text="Eliminar seleccionada", command=eliminar_variable).grid(row=row, column=1, sticky="e")
            row += 1

    # Ventana emergente para añadir variable
    def abrir_ventana_variable(on_save_callback):
        win = tk.Toplevel()
        win.title("Añadir variable")

        frame = ttk.Frame(win, padding=10)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Nombre de la variable:").grid(row=0, column=0, sticky="w")
        entry_nombre = ttk.Entry(frame, width=30)
        entry_nombre.grid(row=1, column=0, pady=5)

        ttk.Label(frame, text="Valor de la variable:").grid(row=2, column=0, sticky="w")
        entry_valor = ttk.Entry(frame, width=30)
        entry_valor.grid(row=3, column=0, pady=5)

        def guardar():
            nombre = entry_nombre.get().strip()
            valor = entry_valor.get().strip()
            if not nombre:
                messagebox.showerror("Error", "El nombre no puede estar vacío.")
                return
            on_save_callback(nombre, valor)
            win.destroy()

        ttk.Button(frame, text="Guardar", command=guardar).grid(row=4, column=0, pady=10)

    
    def salir():
        root.destroy()
        main.main(params_for_file, depends_on)

    
    ttk.Button(frame_organize_variables, text="Generar", command=salir).grid(row=len(archivos), column=1, pady=10)


    root.mainloop()
