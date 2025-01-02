import tkinter as tk
import TKinterModernThemes as TKMT
from PIL import Image, ImageTk
import os

class AutoRefreshGUI(TKMT.ThemedTKinterFrame):
    def __init__(self):
        super().__init__("SHOP AUTO REFRESH", "sun-valley", "dark")

        # Initialize the reference list to prevent image garbage collection
        self.keep_image_open = []
        self.e7_settings = self.addLabelFrame("Game settings", rowspan=2)


        # Create a Text widget inside the new Frame
        skystone = tk.Text(self.e7_settings.master, wrap="word", font=("Arial", 14), height=5)
        skystone.pack()

        # Insert text into the Text widget
        skystone.insert("end", "How many ")

        # Load the image
        image_path = os.path.join(os.getcwd(), "assets", "ui", "token_crystal.png")
        if not os.path.exists(image_path):
            print(f"Error: Image file not found at {image_path}")
            return

        try:
            # Open and resize the image
            pil_image = Image.open(image_path)
            emoji = ImageTk.PhotoImage(pil_image.resize((32, 32)))  # Adjust size
            self.keep_image_open.append(emoji)  # Store reference
        except Exception as e:
            print(f"Error loading image: {e}")
            return

        # Insert the image into the Text widget
        skystone.image_create("end", image=emoji)

        # Insert more text after the image
        skystone.insert("end", " skystone do you want to spend? :")

        # Make the Text widget read-only
        skystone.config(state="disabled")
        self.root.mainloop()

# Main application
if __name__ == "__main__":

    # Instantiate the application
    AutoRefreshGUI()

