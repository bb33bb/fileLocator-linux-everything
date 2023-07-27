#!/usr/bin/python3
import os
import time
import threading
import tkinter as tk
import tkinter.messagebox
import tkinter.simpledialog
import tkinter.font as tkFont
from tkinter import ttk, Menu
from subprocess import Popen, PIPE
import subprocess

def pixels_to_chars(pixels):
    # This is an estimate of the width of a single character.
    # You may need to adjust this value for your specific font and size.
    average_char_width = 10
    return pixels // average_char_width

class Application(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("FileLocator")
        self.sort_directions = {"filename": False, "path": False, "time": False}
        # Global variable to track if the menu is shown
        self.menu_shown = False
        # Add a boolean to track if a search is ongoing
        self.searching = False
        # Create widgets
        self.entry = tk.Entry(self)
        self.entry.bind("<FocusIn>", self.focus_in)  # Bind FocusIn event to focus_in function
        
        # Define a font
        self.font = tkFont.Font(family="Helvetica", size=10)
        # Measure the width of the button text and convert it to characters
        search_button_width = pixels_to_chars(self.font.measure("Search"))
        update_index_button_width = pixels_to_chars(self.font.measure("Update Index"))
        # Create the buttons with the measured width
        print(search_button_width)
        self.button = tk.Button(self, text="Search", command=self.search, width=search_button_width)
        print(update_index_button_width)
        self.update_button = tk.Button(self, text="Update Index", command=self.update_index, width=update_index_button_width)
        self.tree = ttk.Treeview(self, columns=("filename", "path", "time"), show="headings", selectmode='extended')
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)

        # Configure treeview
        self.tree.heading("filename", text="Filename", command=lambda: self.sort_by("filename", False))
        self.tree.heading("path", text="Full Path", command=lambda: self.sort_by("path", False))
        self.tree.heading("time", text="Time Modified", command=lambda: self.sort_by("time", False))
        self.tree.column("filename", stretch=tk.YES, width=200)
        self.tree.column("path", stretch=tk.YES, width=300)
        self.tree.column("time", stretch=tk.NO, width=190)
        self.tree.configure(yscrollcommand=self.scrollbar.set)

        # Create right click context menu
        self.menu = Menu(self, tearoff=0)
        self.menu.bind("<FocusOut>", lambda _: self.menu.unpost())
        self.menu.add_command(label="Open Directory", command=self.open_directory)
        self.menu.add_command(label="Open File", command=self.open_file)
        self.menu.add_command(label="Delete", command=self.delete_selected)
        self.tree.bind("<Button-3>", self.show_menu)

        # Bind Return key to search function
        self.entry.bind("<Return>", self.search)

        # Layout
        self.entry.grid(row=0, column=0, sticky='ew', ipadx=4, padx=(0, 2))
        self.button.grid(row=0, column=1, sticky='ew', ipadx=4, padx=(2, 2))
        self.update_button.grid(row=0, column=2, sticky='ew', ipadx=4, padx=(2, 0))
        self.tree.grid(row=1, column=0, columnspan=3, sticky='nsew', padx=0, pady=0)
        self.scrollbar.grid(row=1, column=4, sticky='ns', padx=0)

        # Configure column weights for resizing
        self.grid_columnconfigure(0, weight=1)  # Give the Entry widget's column a weight
        self.grid_columnconfigure(1, weight=0)  # Set the button's column weight to 0
        self.grid_columnconfigure(2, weight=0)  # Set the update_button's column weight to 0
        self.grid_columnconfigure(4, weight=0)  # Set the scrollbar's column weight to 0
        self.grid_rowconfigure(1, weight=1)  # Give the Treeview widget's row a weight



        # Create progress bar
        self.progress = ttk.Progressbar(self, mode='indeterminate')

        # Set focus to the entry widget
        self.entry.focus_set()

    def search(self, event=None):
        # Release the input focus
        if self.menu_shown:
            self.menu.unpost()
            self.menu_shown = False
        # Disable the button and set the searching boolean to True
        self.button.config(state='disabled')
        self.searching = True
        # Start a new thread to search
        threading.Thread(target=self.do_search, daemon=True).start()

    def do_search(self):
        # Clear old results
        for i in self.tree.get_children():
            self.tree.delete(i)
        # Get the filename from the entry
        filename = self.entry.get()
        # Split the filename into keywords
        keywords = filename.split()
        # Call locate command for the first keyword
        process = Popen(['locate', '-b', keywords[0]], stdout=PIPE, stderr=PIPE)
        stdout, stderr = process.communicate()
        # Filter the results with the rest keywords
        for line in stdout.decode().split("\n"):
            if line and os.path.exists(line) and all(keyword in line for keyword in keywords[1:]):
                timestamp = os.path.getmtime(line)
                readable_time = time.ctime(timestamp)
                self.tree.insert("", "end", values=(line.split("/")[-1], line, readable_time))
        # When the search is done, re-enable the button and set the searching boolean to False
        self.after(0, lambda: self.button.config(state='normal'))
        self.searching = False

    def update_index(self):
        password = tkinter.simpledialog.askstring("Password", "Enter password:", show='*')
        command = ['sudo', '-S', 'updatedb']
        # Start the progress bar
        self.progress.start()
        self.progress.grid(row=3, column=0, columnspan=2, sticky='ew')
        # Disable the buttons
        self.button.config(state='disabled')
        self.update_button.config(state='disabled')
        # Start a new thread to run updatedb
        threading.Thread(target=self.run_updatedb, args=(command, password), daemon=True).start()

    def run_updatedb(self, command, password):
        proc = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        proc.stdin.write(password.encode())
        stdout, stderr = proc.communicate()
        if proc.returncode != 0:
            tkinter.messagebox.showerror("Error", "Failed to update index. Error: " + stderr.decode())
        else:
            tkinter.messagebox.showinfo("Success", "Index updated successfully.")
        # Stop the progress bar
        self.progress.stop()
        self.progress.grid_forget()
        # Re-enable the buttons
        self.after(0, lambda: self.button.config(state='normal'))
        self.after(0, lambda: self.update_button.config(state='normal'))

    def sort_by(self, col, descending):
        # Remove the arrow from all columns
        for col_name in self.sort_directions.keys():
            col_heading = self.tree.heading(col_name, option="text")
            self.tree.heading(col_name, text=col_heading.replace(" ↑", "").replace(" ↓", ""))
            
        # Sort the treeview by the given column
        data = [(self.tree.set(child, col), child) for child in self.tree.get_children('')]
        data.sort(reverse=descending)
        for indx, item in enumerate(data):
            self.tree.move(item[1], '', indx)
        # Switch the heading so that it will sort in the opposite direction
        self.tree.heading(col, command=lambda col=col: self.sort_by(col, int(not descending)))
        # Add the arrow to the sorted column
        col_heading = self.tree.heading(col, option="text")
        if descending:
            self.tree.heading(col, text=col_heading + " ↓")
        else:
            self.tree.heading(col, text=col_heading + " ↑")
        self.sort_directions[col] = descending

    def show_menu(self, event):
        # Select row under mouse
        item = self.tree.identify_row(event.y)
        if item not in self.tree.selection():
            self.tree.selection_set(item)
        # Show right click context menu
        self.menu.post(event.x_root, event.y_root)
        # Set the focus to the menu
        self.menu.focus_set()
        # Set the global variable to True
        self.menu_shown = True

    def open_directory(self):
        # Get selected item
        selected_items = self.tree.selection()
        if len(selected_items) > 0:
            item = selected_items[0]
            # Get file path
            path = self.tree.item(item)['values'][1]
            # Check if the path is a directory
            if os.path.isdir(path):
                # Open the directory
                subprocess.run(['nautilus', path])
            else:
                # Open the directory containing the file and select the file
                subprocess.run(['nautilus', '--select', path])
        else:
            tkinter.messagebox.showinfo("No selection", "Please select an item first.")

    def open_file(self):
        # Get selected item
        selected_items = self.tree.selection()
        if len(selected_items) > 0:
            item = selected_items[0]
            # Get file path
            path = self.tree.item(item)['values'][1]
            # Open the file
            subprocess.run(['xdg-open', path])
        else:
            tkinter.messagebox.showinfo("No selection", "Please select an item first.")

    def delete_selected(self):
        # Get selected items
        selected_items = self.tree.selection()
        if len(selected_items) > 0:
            # Show a confirmation dialog
            if not tkinter.messagebox.askyesno("Confirm deletion", "Are you sure you want to delete the selected files?"):
                return
            for item in selected_items:
                # Get file path
                path = self.tree.item(item)['values'][1]
                # Delete the file
                try:
                    if os.path.isfile(path):
                        os.remove(path)
                    elif os.path.isdir(path):
                        os.rmdir(path)  # This will only remove empty directories
                    # Remove the item from the treeview
                    self.tree.delete(item)
                except OSError as e:
                    tkinter.messagebox.showerror("Error", "Failed to delete file: " + str(e))
        else:
            tkinter.messagebox.showinfo("No selection", "Please select an item first.")

    def focus_in(self, event):
        # Check the global variable
        if self.menu_shown:
            # Unpost the menu
            self.menu.unpost()
            # Set the global variable to False
            self.menu_shown = False

if __name__ == "__main__":
    app = Application()
    app.mainloop()
