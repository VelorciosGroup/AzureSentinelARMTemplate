from tkinter import Tk, ttk, messagebox, filedialog
import tkinter as tk
from . import parametrize
from . import functions
from . import generate
import os

def rendergui():
    """
    Renderiza la interfaz gráfica para crear Master Templates a partir de archivos JSON.

    Funcionalidades principales:
    - Selección de archivos JSON que contienen playbooks.
    - Visualización de archivos seleccionados.
    - Eliminación de archivos seleccionados de la lista.
    - Validación de dependencias entre workflows.
    - Generación del Master Template llamando a la función `generate_master`.

    :return: Devuelve la ruta del directorio de salida de los archivos procesados.
    """
    params_for_file = {}
    depends_on = {}
    archivos = []
    dirin = ""

    # ========================= CONFIGURACIÓN DE LA VENTANA PRINCIPAL =========================
    print("Renderizando root")
    root = Tk()
    root.title("Creador de Master Templates")
    root.geometry("650x380")
    root.resizable(False, False)
    root.configure(bg="#f5f5f5")  # Fondo blanco grisáceo

    # Canvas para scroll o contenedores dinámicos (si se necesitara)
    canvas = tk.Canvas(root, borderwidth=0, bg="#f5f5f5", highlightthickness=0)
    canvas.pack(side="left", fill="both", expand=True)

    frame_interior = ttk.Frame(canvas)
    canvas.create_window((0,0), window=frame_interior, anchor="nw")

    # ------------------------ Función de manejo de errores ------------------------
    def error(mensaje):
        """
        Muestra un mensaje de error y termina la ejecución del programa.

        :param mensaje: Texto del mensaje de error.
        """
        root_err = tk.Tk()
        root_err.withdraw()
        messagebox.showerror("Error", mensaje)
        root_err.destroy()
        exit()

    # ========================= ESTILOS MODERNOS =========================
    style = ttk.Style()
    style.theme_use('clam')  # Tema limpio y moderno

    # Frame redondeado y fondo blanco
    style.configure("Rounded.TFrame",
                    background="white",
                    borderwidth=1,
                    relief="ridge")
    
    # Configuración general de etiquetas
    style.configure("TLabel",
                    background="white",
                    font=("Arial", 11))
    
    # Botones normales
    style.configure("TButton",
                    font=("Arial", 11),
                    padding=6,
                    borderwidth=0,
                    relief="flat",
                    foreground="white",
                    background="#4C7AAF")  # Azul moderno
    style.map("TButton",
              background=[("active", "#204E99")])

    # Botón grande estilo "Generar"
    style.configure("Big.TButton",
                    font=("Arial", 12, "bold"),
                    padding=10,
                    borderwidth=0,
                    relief="flat",
                    foreground="white",
                    background="#4C7AAF")
    style.map("Big.TButton",
              background=[("active", "#204E99")])

    # ========================= FRAMES =========================
    print("Renderizando frames dentro de root")
    frame_base_templates = ttk.Frame(frame_interior, padding=15, style="Rounded.TFrame")
    frame_base_templates.pack(fill="x", pady=10, padx=10)

    # ========================= CONTENIDO DEL FRAME =========================
    ttk.Label(frame_base_templates, text="Selección de las templates que se usarán").grid(row=0, column=0, columnspan=2, sticky="w", pady=(0,5))

    lista_archivos = tk.Listbox(
        frame_base_templates,
        width=100,
        height=8,
        bg="#f9f9f9",
        relief="flat",
        highlightthickness=1,
        highlightbackground="#ddd"
    )
    lista_archivos.grid(row=1, column=0, columnspan=2, pady=5)

    ttk.Label(frame_base_templates, text="Directorio de salida").grid(row=2, column=0, columnspan=2, sticky="w", pady=(10, 0))

    # ========================= FUNCIONES INTERNAS =========================
    def seleccionar_archivos():
        """
        Permite seleccionar archivos JSON mediante un diálogo de archivos.
        Evita duplicados y normaliza nombres.
        Actualiza los parámetros y dependencias de los archivos seleccionados.
        """
        nonlocal params_for_file
        nonlocal depends_on

        nuevos = list(filedialog.askopenfilenames(
            filetypes=[("JSON files", "*.json")],
            title="Selecciona archivos JSON"
        ))
        if nuevos:
            for index, archivo in enumerate(nuevos):
                print(f"Seleccionado archivo {archivo}")
                nuevos[index] = functions.normalizeFileNames(archivo)

            for archivo in nuevos:
                if archivo not in archivos:  # evitar duplicados
                    functions.deleteprefix(archivo)
                    archivos.append(archivo)
                    lista_archivos.insert(tk.END, archivo)
                    print(f"archivo {archivo} añadido con éxito")
        
        # Parametrizar y buscar dependencias
        params_for_file = parametrize.parametrizeFiles(archivos)
        depends_on = parametrize.parametrizeDependsOn(archivos)

        # Validación de dependencias
        print("Eliminando dependencias repetidas")
        for file in depends_on:
            for dependency in depends_on[file]:
                if dependency not in params_for_file.keys():
                    error(f"Workflow {dependency} de archivo {file} no encontrado en los otros archivos seleccionados. Revisa si se ha seleccionado o se ha cambiado el nombre")

    def eliminar_seleccionados():
        """
        Elimina los archivos seleccionados en la lista de archivos y actualiza la lista interna.
        """
        print("Eliminando el archivo seleccionado")
        seleccion = lista_archivos.curselection()
        if not seleccion:
            messagebox.showinfo("Info", "Selecciona un archivo para eliminar.")
            return
        
        for i in reversed(seleccion):
            archivos.pop(i)
            lista_archivos.delete(i)

    # ========================= BOTONES =========================
    print("Renderizando botones de añadir / eliminar JSON")
    ttk.Button(frame_base_templates, text="Añadir JSON", command=seleccionar_archivos).grid(row=4, column=0, pady=10, sticky="w")
    ttk.Button(frame_base_templates, text="Eliminar seleccionado", command=eliminar_seleccionados).grid(row=4, column=1, pady=10, sticky="e")

    def salir():
        """
        Finaliza la GUI y llama a la función `generate_master` para crear el Master Template.
        """
        nonlocal dirin
        if archivos:
            dirin = os.path.dirname(archivos[0])

        print("saliendo de la GUI")
        root.destroy()
        generate.generate_master(params_for_file, depends_on, dirin)

    print("Renderizando botón generar")
    ttk.Button(frame_base_templates, text="Generar", command=salir, style="Big.TButton").grid(row=5, column=0, pady=15, sticky="w")

    root.mainloop()
    return dirin
