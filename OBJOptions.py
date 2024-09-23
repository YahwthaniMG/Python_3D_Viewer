import tkinter as tk

"""
    Esta clase se encarga de mostrar que opciones de procesamiento de la malla quiere el usuario
    aplicar a su modelo.
"""

class MeshObjOptions:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Opciones del OBJ")
        self.root.geometry('260x150') 
        
        self.label_title = tk.Label(self.root, text="Elige ", anchor="w")
        self.label_space = tk.Label(self.root, text=" ", anchor="w")
        
        self.button1 = tk.Button(self.root, text="Option 1", command=self.print_text1)
        self.label_space1 = tk.Label(self.root, text=" ", anchor="w")
        self.button2 = tk.Button(self.root, text="Option 2", command=self.print_text2)
        self.label_space2 = tk.Label(self.root, text=" ", anchor="w")
        
        self.label_title.pack(fill='x')  
        self.label_space.pack(fill='x')
        
        self.button1.pack(fill='x')
        self.label_space1.pack(fill='x')
        self.button2.pack(fill='x')
        self.label_space2.pack(fill='x')
        
        self.opt = None  # Inicializar opt como None al principio
        
    def display_data(self, opt1, opt2):
        self.opt1 = opt1
        self.opt2 = opt2
        self.label_title.config(text="Elige una opción.")
        self.label_space.config(text=" ")
        self.button1.config(text=self.opt1)
        self.label_space1.config(text=" ")
        self.button2.config(text=self.opt2)
        self.label_space2.config(text=" ")
        self.root.mainloop()
        
    def print_text1(self):
        self.opt = 1
        self.root.quit()  # Salir del loop principal de tkinter después de seleccionar la opción
        
    def print_text2(self):
        self.opt = 2
        self.root.quit()  # Salir del loop principal de tkinter después de seleccionar la opción
    
    def get_selected_option(self):
        self.root.mainloop()  # Esperar hasta que se haya seleccionado una opción
        return self.opt