# importação das bibliotecas
import tkinter as tk
from tkinter import messagebox
import subprocess

# função de captura dos dígitos
def on_button_click(number):
    current = entry.get()
    entry.delete(0, tk.END)
    entry.insert(0, current + str(number))

# função de limpeza dos dígitos
def clear_entry():
    entry.delete(0, tk.END)

# função de cancelamento
def cancel_shutdown():
    subprocess.run(["shutdown", "/a"])

# função de desligamento
def shutdown(minutes):
    try:
        minutes = int(minutes)
        seconds = minutes * 60
        subprocess.run(["shutdown", "/s", "/t", str(seconds)])
    except ValueError:
        messagebox.showerror("Erro", "Digite um valor válido de minutos.")

# função de acionamento do desligamento
def on_shutdown_click():
    minutes = entry.get()
    shutdown(minutes)

# configuração da janela
root = tk.Tk()
root.title("Calculadora de Desligamento")

# aumentar o tamanho da janela
root.geometry("400x550")

# campo de entrada
entry = tk.Entry(root, width=20, font=("Helvetica", 24), borderwidth=5)
entry.grid(row=0, column=0, columnspan=4, padx=10, pady=10)

# botões numéricos
for i in range(1, 10):
    row = (i - 1) // 3 + 1
    col = (i - 1) % 3
    button = tk.Button(root, text=str(i), padx=20, pady=20, font=("Helvetica", 18), command=lambda i=i: on_button_click(i))
    button.grid(row=row, column=col, padx=5, pady=5)

# configuração dos botões adicionais
zero_button = tk.Button(root, text="0", padx=20, pady=20, font=("Helvetica", 18), command=lambda: on_button_click(0))
shutdown_button = tk.Button(root, text="Desligar", padx=15, pady=20, font=("Helvetica", 18), command=on_shutdown_click)
clear_button = tk.Button(root, text="Limpar", padx=15, pady=20, font=("Helvetica", 18), command=clear_entry)
cancel_button = tk.Button(root, text="Cancelar", padx=120, pady=20, font=("Helvetica", 18), command=cancel_shutdown)

# disposição dos botões adicionais
zero_button.grid(row=4, column=1, padx=5, pady=5)
shutdown_button.grid(row=4, column=2, padx=5, pady=5)
clear_button.grid(row=4, column=0, padx=5, pady=5)
cancel_button.grid(row=5, column=0, columnspan=3, padx=5, pady=5)

# execução do programa
root.mainloop()
