from tkinter import Tk, ttk, messagebox, filedialog
import tkinter as tk
from . import parametrize
from . import functions
from . import generate
import os

def render_gui():
    """
    Renders the graphical interface to create Master Templates from JSON files.

    Main functionalities:
    - Selection of JSON files containing playbooks.
    - Display of selected files.
    - Removal of selected files from the list.
    - Validation of dependencies between workflows.
    - Generation of the Master Template by calling the `generate_master` function.

    :return: Returns the output directory path of the processed files.
    """
    params_for_file = {}
    dependencies = {}
    file_list = []
    input_dir = ""

    # ========================= MAIN WINDOW CONFIGURATION =========================
    print("Rendering main window")
    root = Tk()
    root.title("Master Template Creator")
    root.geometry("650x380")
    root.resizable(False, False)
    root.configure(bg="#f5f5f5")  # Light gray background

    # Canvas for scrolling or dynamic containers if needed
    canvas = tk.Canvas(root, borderwidth=0, bg="#f5f5f5", highlightthickness=0)
    canvas.pack(side="left", fill="both", expand=True)

    inner_frame = ttk.Frame(canvas)
    canvas.create_window((0,0), window=inner_frame, anchor="nw")

    # ------------------------ Error handling function ------------------------
    def show_error(message):
        """
        Shows an error message and exits the program.

        :param message: Text of the error message.
        """
        error_root = tk.Tk()
        error_root.withdraw()
        messagebox.showerror("Error", message)
        error_root.destroy()
        exit()

    # ========================= MODERN STYLES =========================
    style = ttk.Style()
    style.theme_use('clam')  # Clean, modern theme

    # Rounded frame with white background
    style.configure("Rounded.TFrame",
                    background="white",
                    borderwidth=1,
                    relief="ridge")
    
    # General label style
    style.configure("TLabel",
                    background="white",
                    font=("Arial", 11))
    
    # Normal buttons
    style.configure("TButton",
                    font=("Arial", 11),
                    padding=6,
                    borderwidth=0,
                    relief="flat",
                    foreground="white",
                    background="#4C7AAF")  # Modern blue
    style.map("TButton",
              background=[("active", "#204E99")])

    # Large "Generate" button style
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
    print("Rendering frames inside main window")
    base_frame = ttk.Frame(inner_frame, padding=15, style="Rounded.TFrame")
    base_frame.pack(fill="x", pady=10, padx=10)

    # ========================= FRAME CONTENT =========================
    ttk.Label(base_frame, text="Select the templates to use").grid(row=0, column=0, columnspan=2, sticky="w", pady=(0,5))

    listbox_files = tk.Listbox(
        base_frame,
        width=100,
        height=8,
        bg="#f9f9f9",
        relief="flat",
        highlightthickness=1,
        highlightbackground="#ddd"
    )
    listbox_files.grid(row=1, column=0, columnspan=2, pady=5)

    ttk.Label(base_frame, text="Output directory").grid(row=2, column=0, columnspan=2, sticky="w", pady=(10, 0))

    # ========================= INTERNAL FUNCTIONS =========================
    def select_files():
        """
        Allows selecting JSON files via a file dialog.
        Prevents duplicates and normalizes filenames.
        Updates parameters and dependencies of selected files.
        """
        nonlocal params_for_file
        nonlocal dependencies

        new_files = list(filedialog.askopenfilenames(
            filetypes=[("JSON files", "*.json")],
            title="Select JSON files"
        ))
        if new_files:
            for index, file in enumerate(new_files):
                print(f"Selected file {file}")
                new_files[index] = functions.normalize_file_names(file)

            for file in new_files:
                if file not in file_list:  # Avoid duplicates
                    functions.remove_prefixes(file)
                    file_list.append(file)
                    listbox_files.insert(tk.END, file)
                    print(f"File {file} successfully added")
        
        # Parametrize and search for dependencies
        params_for_file = parametrize.parametrize_files(file_list)
        dependencies = parametrize.parametrize_dependencies(file_list)

        # Dependency validation
        print("Removing repeated dependencies")
        for file_name in dependencies:
            for dependency in dependencies[file_name]:
                if dependency not in params_for_file.keys():
                    show_error(f"Workflow {dependency} in file {file_name} not found in other selected files. Check if it was selected or renamed.")

    def remove_selected():
        """
        Removes the selected files from the list and updates the internal list.
        """
        print("Removing selected file")
        selection = listbox_files.curselection()
        if not selection:
            messagebox.showinfo("Info", "Select a file to remove.")
            return
        
        for i in reversed(selection):
            file_list.pop(i)
            listbox_files.delete(i)

    # ========================= BUTTONS =========================
    print("Rendering buttons to add / remove JSON files")
    ttk.Button(base_frame, text="Add JSON", command=select_files).grid(row=4, column=0, pady=10, sticky="w")
    ttk.Button(base_frame, text="Remove selected", command=remove_selected).grid(row=4, column=1, pady=10, sticky="e")

    def exit_gui():
        """
        Closes the GUI and calls `generate_master` to create the Master Template.
        """
        nonlocal input_dir
        if file_list:
            input_dir = os.path.dirname(file_list[0])

        print("Exiting GUI")
        root.destroy()
        generate.generate_master(params_for_file, dependencies, input_dir)

    print("Rendering generate button")
    ttk.Button(base_frame, text="Generate", command=exit_gui, style="Big.TButton").grid(row=5, column=0, pady=15, sticky="w")

    root.mainloop()
    return input_dir
