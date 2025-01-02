# import built-in
import tkinter as tk
import TKinterModernThemes as TKMT
from TKinterModernThemes.WidgetFrame import noneDict
from tkinter import ttk
from PIL import ImageTk, Image
import csv
import os
import time
import threading
from datetime import datetime

# Library
import pyautogui
import pygetwindow as gw
import cv2
import numpy as np
import keyboard
from PIL import ImageGrab


class ShopItem:
    def __init__(self, path="", image=None, price=0, count=0):
        self.path = path
        self.image = image
        self.price = price
        self.count = count

    def __repr__(self):
        return f"ShopItem(path={self.path}, image={self.image}, price={self.price}, count={self.count})"


class RefreshStatistic:
    def __init__(self):
        self.refresh_count = 0
        self.items = {}

    def addShopItem(self, path: str, name="", price=0, count=0):
        image = cv2.imread(os.path.join("assets", path))
        image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        newItem = ShopItem(path, image, price, count)
        self.items[name] = newItem

    def getInventory(self):
        return self.items

    def getName(self):
        return list(self.items.keys())

    def getPath(self):
        res = []
        for value in self.items.values():
            res.append(value.path)
        return res

    def getItemCount(self):
        res = []
        for value in self.items.values():
            res.append(value.count)
        return res

    def getTotalCost(self):
        total = 0
        for value in self.items.values():
            total += value.price * value.count
        return total

    def incrementRefreshCount(self):
        self.refresh_count += 1

    def writeToCSV(self):
        res_folder = "ShopRefreshHistory"
        if not os.path.exists(res_folder):
            os.makedirs(res_folder)

        gen_path = "refreshAttempt"
        for name in self.getName():
            gen_path += name[:4]
        gen_path += ".csv"

        path = os.path.join(res_folder, gen_path)

        if not os.path.isfile(path):
            with open(path, "w", newline="") as file:
                writer = csv.writer(file)
                column_name = ["Time", "Refresh count", "Skystone spent", "Gold spent"]
                column_name.extend(self.getName())
                writer.writerow(column_name)
        with open(path, "a", newline="") as file:
            writer = csv.writer(file)
            data = [
                datetime.now(),
                self.refresh_count,
                self.refresh_count * 3,
                self.getTotalCost(),
            ]
            data.extend(self.getItemCount())
            writer.writerow(data)


class SecretShopRefresh:
    def __init__(
        self,
        title_name: str,
        callback=None,
        tk_instance: tk = None,
        budget: int = None,
        allow_move: bool = False,
        debug: bool = False,
    ):
        # init state
        self.debug = debug
        self.loop_active = False
        self.loop_finish = True
        self.mouse_sleep = 0.2
        self.screenshot_sleep = 0.3
        self.callback = callback if callback else self.refreshFinishCallback
        self.budget = budget
        self.allow_move = allow_move

        self.loading_asset = cv2.imread(os.path.join("assets", "loading.jpg"))
        self.loading_asset = cv2.cvtColor(self.loading_asset, cv2.COLOR_BGR2GRAY)

        # find window
        self.title_name = title_name
        windows = gw.getWindowsWithTitle(self.title_name)
        self.window = next((w for w in windows if w.title == self.title_name), None)

        self.tk_instance = tk_instance
        self.rs_instance = RefreshStatistic()

    # Start shop refresh macro
    def start(self):
        if self.loop_active or not self.loop_finish:
            return

        self.loop_active = True
        self.loop_finish = False
        keyboard_thread = threading.Thread(target=self.checkKeyPress)
        refresh_thread = threading.Thread(target=self.shopRefreshLoop)
        keyboard_thread.daemon = True
        refresh_thread.daemon = True
        keyboard_thread.start()
        refresh_thread.start()

    # Threads
    def checkKeyPress(self):
        while self.loop_active and not self.loop_finish:
            self.loop_active = not keyboard.is_pressed("esc")
        self.loop_active = False
        print("Terminating shop refresh ...")

    def refreshFinishCallback(self):
        print("Terminated!")

    def shopRefreshLoop(self):

        try:
            if self.window.isMaximized or self.window.isMinimized:
                self.window.restore()
            if not self.allow_move:
                self.window.moveTo(0, 0)
            self.window.resizeTo(906, 539)
        except Exception as e:
            print(e)
            self.loop_active = False
            self.loop_finish = True
            self.callback()
            return

        # show mini display
        # generating mini image
        mini_images = []
        hint, mini_labels = None, None
        if self.tk_instance:
            selected_path = self.rs_instance.getPath()
            for path in selected_path:
                img = Image.open(os.path.join("assets", path))
                img = img.resize((45, 45))
                img = ImageTk.PhotoImage(img)
                mini_images.append(img)
            hint, mini_labels = self.showMiniDisplays(mini_images)

        # update state on minidisplay
        def updateMiniDisplay():
            for label, count in zip(mini_labels, self.rs_instance.getItemCount()):
                label.config(text=count)

        time.sleep(self.mouse_sleep)

        if not self.loop_active:
            if hint:
                hint.destroy()
            self.loop_finish = True
            self.callback()
            return

        try:
            # replace with window activate in python
            # window.minimize()
            # window.maximize()
            # window.restore()
            self.window.activate()

            self.clickShop()
            time.sleep(1)

            # item sliding const
            sliding_time = (1 - self.mouse_sleep) if self.mouse_sleep <= 1 else 0

            # Loop for how the
            while self.loop_active:

                self.window.resizeTo(906, 539)

                # array for determining if an item has been purchsed in this loop
                brought = set()
                if not self.loop_active:
                    break

                # take screenshot, check for items, buy all items that appear
                time.sleep(
                    sliding_time
                )  # This is a constant sleep to account for the item sliding in frame

                ###start of bundle refresh
                screenshot = self.takeScreenshot()
                process_screenshot = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)

                # show image if in debug
                if self.debug:
                    cv2.imshow("Press any key to continue ...", process_screenshot)
                    cv2.waitKey(0)
                    cv2.destroyAllWindows()

                # checks if loading screen is blocking
                check_screen, reset = self.checkLoading(process_screenshot)
                if check_screen is None:
                    break
                else:
                    process_screenshot = check_screen

                if reset:
                    # x = self.window.left + self.window.width * 0.04
                    # y = self.window.top + self.window.height * 0.10
                    # pyautogui.moveTo(x, y)
                    # pyautogui.click()
                    # time.sleep(1)
                    # self.clickShop()
                    self.scrollUp()
                    time.sleep(0.5)
                    continue

                # loop through all the assets to find item to buy
                for key, value in self.rs_instance.getInventory().items():
                    pos = self.findItemPosition(process_screenshot, value.image)
                    if pos is not None:
                        self.clickBuy(pos)
                        value.count += 1
                        brought.add(key)

                # real time count UI update
                if hint:
                    updateMiniDisplay()
                if not self.loop_active:
                    break

                # scroll shop
                self.scrollShop()
                time.sleep(self.mouse_sleep)
                if not self.loop_active:
                    break

                ###start of bundle refresh
                screenshot = self.takeScreenshot()
                process_screenshot = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)

                # show image if in debug
                if self.debug:
                    cv2.imshow("Press any key to continue ...", process_screenshot)
                    cv2.waitKey(0)
                    cv2.destroyAllWindows()

                # checks if loading screen is blocking
                check_screen, reset = self.checkLoading(process_screenshot)
                if check_screen is None:
                    break
                else:
                    process_screenshot = check_screen

                if reset:
                    for key in brought:
                        value = self.rs_instance.items.get(key)
                        if value:
                            value.count -= 1

                    # x = self.window.left + self.window.width * 0.04
                    # y = self.window.top + self.window.height * 0.10
                    # pyautogui.moveTo(x, y)
                    # pyautogui.click()
                    # time.sleep(1)
                    # self.clickShop()
                    self.scrollUp()
                    time.sleep(0.5)
                    continue

                # loop through all the assets to find item to buy
                for key, value in self.rs_instance.getInventory().items():
                    pos = self.findItemPosition(process_screenshot, value.image)
                    if pos is not None and key not in brought:
                        self.clickBuy(pos)
                        value.count += 1

                if hint:
                    updateMiniDisplay()
                if not self.loop_active:
                    break

                # check budget
                if self.budget:
                    if self.rs_instance.refresh_count >= self.budget // 3:
                        break

                # refresh shop
                self.clickRefresh()
                self.rs_instance.incrementRefreshCount()
                time.sleep(self.mouse_sleep)
                if self.window.title != self.title_name:
                    break

        except Exception as e:
            print(e)
            if hint:
                hint.destroy()
            self.rs_instance.writeToCSV()
            self.loop_active = False
            self.loop_finish = True
            self.callback()
            return

        if hint:
            hint.destroy()
        self.rs_instance.writeToCSV()
        self.loop_active = False
        self.loop_finish = True
        self.callback()

    # show mini display
    def showMiniDisplays(self, mini_images):
        bg_color = "#171717"
        fg_color = "#dddddd"

        if self.tk_instance is None:
            return None, None
        # Display exit key
        hint = tk.Toplevel(self.tk_instance)
        hint.geometry(
            r"200x200+%d+%d" % (self.window.left, self.window.top + self.window.height)
        )
        hint.title("Hint")
        hint.iconbitmap(os.path.join("assets", "icon.ico"))
        tk.Label(
            master=hint, text="Press ESC to stop refreshing!", bg=bg_color, fg=fg_color
        ).pack()
        hint.config(bg=bg_color)

        # Display stat
        mini_stats = tk.Frame(master=hint, bg=bg_color)
        mini_labels = []

        # packing mini image
        for img in mini_images:
            frame = tk.Frame(mini_stats, bg=bg_color)
            tk.Label(master=frame, image=img, bg=bg_color).pack(side=tk.LEFT)
            count = tk.Label(master=frame, text="0", bg=bg_color, fg="#FFBF00")
            count.pack(side=tk.RIGHT)
            mini_labels.append(count)
            frame.pack()
        mini_stats.pack()
        return hint, mini_labels

    # add item to list
    def addShopItem(self, path: str, name="", price=0, count=0):
        self.rs_instance.addShopItem(path, name, price, count)

    # take screenshot of entire window
    def takeScreenshot(self):
        try:
            # replace with window activate in python
            # window.minimize()
            # window.maximize()
            # window.restore()
            self.window.activate()

            # fix pyautogui's multiscreen bug
            # screenshot = pyautogui.screenshot(region=(self.window.left, self.window.top, self.window.width, self.window.height))
            region = [
                self.window.left,
                self.window.top,
                self.window.width,
                self.window.height,
            ]
            screenshot = ImageGrab.grab(
                bbox=(
                    region[0],
                    region[1],
                    region[2] + region[0],
                    region[3] + region[1],
                ),
                all_screens=True,
            )
            screenshot = np.array(screenshot)
            return screenshot

        except Exception as e:
            print(e)
            return None

    def checkLoading(self, process_screenshot):
        result = cv2.matchTemplate(
            process_screenshot, self.loading_asset, cv2.TM_CCOEFF_NORMED
        )
        loc = np.where(result >= 0.75)
        if loc[0].size <= 0:
            return process_screenshot, False

        for _ in range(14):
            time.sleep(1)
            screenshot = self.takeScreenshot()
            process_screenshot = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)
            result = cv2.matchTemplate(
                process_screenshot, self.loading_asset, cv2.TM_CCOEFF_NORMED
            )
            loc = np.where(result >= 0.75)
            if loc[0].size <= 0:
                time.sleep(1.5)
                screenshot = self.takeScreenshot()
                process_screenshot = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)
                return process_screenshot, True

        return None, False

    # return item position
    def findItemPosition(self, process_screenshot, process_item):

        result = cv2.matchTemplate(
            process_screenshot, process_item, cv2.TM_CCOEFF_NORMED
        )
        loc = np.where(result >= 0.75)
        x, y = 1, 1

        # debug mode!
        if self.debug and loc[0].size > 0:
            debug_screenshot = process_screenshot.copy()
            for pt in zip(*loc[::-1]):
                cv2.rectangle(
                    debug_screenshot,
                    pt,
                    (pt[0] + process_item.shape[1], pt[1] + process_item.shape[0]),
                    (255, 255, 0),
                    2,
                )
            cv2.imshow("Press any key to continue ...", debug_screenshot)
            # cv2.imwrite('Debug.png', debug_screenshot)
            cv2.waitKey(0)
            cv2.destroyAllWindows()

        if loc[0].size > 0:
            x = self.window.left + self.window.width * 0.90
            y = self.window.top + loc[0][0] + process_item.shape[0] * 3 // 4
            pos = (x, y)
            return pos
        return None

    # BUY MACRO
    def clickBuy(self, pos):
        if pos is None:
            return False
        x, y = pos
        pyautogui.moveTo(x, y)
        pyautogui.click(clicks=2, interval=self.mouse_sleep)
        time.sleep(self.mouse_sleep)
        self.clickConfirmBuy()
        return True

    def clickConfirmBuy(self):
        x = self.window.left + self.window.width * 0.55
        y = self.window.top + self.window.height * 0.70
        pyautogui.moveTo(x, y)
        pyautogui.click(clicks=2, interval=self.mouse_sleep)
        time.sleep(self.mouse_sleep)
        time.sleep(self.screenshot_sleep)  # Account for Loading

        # checks if loading screen is blocking
        screenshot = self.takeScreenshot()
        process_screenshot = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)
        self.checkLoading(process_screenshot)

    # REFRESH MACRO
    def clickRefresh(self):
        x = self.window.left + self.window.width * 0.20
        y = self.window.top + self.window.height * 0.90
        pyautogui.moveTo(x, y)
        pyautogui.click(clicks=2, interval=self.mouse_sleep)
        time.sleep(self.mouse_sleep)
        self.clickConfirmRefresh()

    def clickConfirmRefresh(self):
        x = self.window.left + self.window.width * 0.58
        y = self.window.top + self.window.height * 0.62
        pyautogui.moveTo(x, y)
        pyautogui.click(clicks=2, interval=self.mouse_sleep)
        time.sleep(self.screenshot_sleep)  # Account for Loading

    # SHOP MACRO
    def clickShop(self):
        # wake window
        x = self.window.left + self.window.width * 0.05
        y = self.window.top + self.window.height * 0.32
        pyautogui.moveTo(x, y)
        pyautogui.click()

        time.sleep(self.mouse_sleep)

        # old lobby
        x = self.window.left + self.window.width * 0.44
        y = self.window.top + self.window.height * 0.26
        pyautogui.moveTo(x, y)
        pyautogui.click()

        time.sleep(self.mouse_sleep)

        # new lobby
        x = self.window.left + self.window.width * 0.05
        y = self.window.top + self.window.height * 0.32
        pyautogui.moveTo(x, y)
        pyautogui.click()

    def scrollShop(self):
        x = self.window.left + self.window.width * 0.58
        y = self.window.top + self.window.height * 0.62
        pyautogui.moveTo(x, y)
        pyautogui.mouseDown(button="left")
        pyautogui.moveTo(x, y - self.window.height * 0.28)
        pyautogui.mouseUp(button="left")

    def scrollUp(self):
        x = self.window.left + self.window.width * 0.58
        y = self.window.top + self.window.height * 0.62
        pyautogui.moveTo(x, y - self.window.height * 0.28)
        pyautogui.mouseDown(button="left")
        pyautogui.moveTo(x, y)
        pyautogui.mouseUp(button="left")


class AppConfig:
    def __init__(self):
        # here is where you can config setting
        # general setting
        self.RECOGNIZE_TITLES = {
            "Epic Seven",
            "BlueStacks App Player",
            "LDPlayer",
            "MuMu Player 12",
        }  # if detected title show up in the select bar so that you don't need to manual enter
        self.ALL_PATH = ["cov.jpg", "mys.jpg", "fb.jpg"]  # Path to all the image
        self.ALL_NAME = [
            "Covenant bookmark",
            "Mystic medal",
            "Friendship bookmark",
        ]  # Name to all the image
        self.ALL_PRICE = [184000, 280000, 18000]  # Price to the image
        self.MANDATORY_PATH = {
            "cov.jpg",
            "mys.jpg",
        }  # make item unable to be unselected
        self.DEBUG = False


def text_with_img(
    frame,
    data: list,
    row: int = None,
    col: int = None,
    padx=10,
    pady=10,
    sticky="nsw",
    rowspan: int = 1,
    colspan: int = 1,
    widgetkwargs: dict = None,
    gridkwargs: dict = None,
):
    widgetkwargs, gridkwargs = noneDict(widgetkwargs, gridkwargs)

    # Calculate the maximum width based on text and image sizes
    max_text_length = max((len(item_content) for item_type, item_content in data if item_type == "text"), default=0)
    image_width = int(14 * 1.5)  # Width of the images
    width = max(max_text_length, image_width) + 10  # Add padding

    span = tk.Text(
        frame.master,
        wrap="word",
        borderwidth=0,
        highlightthickness=0,
        width=width,
        height=1,  # Keep height as 1 for a single line
        **widgetkwargs,
    )
    row, col = frame.getRow(row, col, rowspan, colspan)
    span.grid(
        row=row,
        column=col,
        padx=padx,
        pady=pady,
        sticky=sticky,
        rowspan=rowspan,
        columnspan=colspan,
        **gridkwargs,
    )
    for item_type, item_content in data:
        if item_type == "text":
            span.insert("end", item_content)
        elif item_type == "img":
            image_path = os.path.join(os.getcwd(), item_content)
            if not os.path.exists(image_path):
                print(f"Error: Image file not found at {image_path}")
                continue
            try:
                pil_image = Image.open(image_path).resize((int(14 * 1.5), int(14 * 1.5)))
                emoji = ImageTk.PhotoImage(
                    pil_image
                )
                span.image_create("end", image=emoji)
            except (IOError, ValueError) as e:  # Handle specific image loading errors
                print(f"Error loading image: {e}")
                continue  # Skip this image if there's an error
    span.config(state="disabled")
    return span

class AutoRefreshGUI(TKMT.ThemedTKinterFrame):
    def __init__(self):
        super().__init__("SHOP AUTO REFRESH", "sun-valley", "dark")
        self.app_config = AppConfig()

        # gui
        # color
        self.unite_bg_color = "#171717"
        self.unite_text_color = "#dddddd"

        self.root.config(bg=self.unite_bg_color)
        self.root.attributes("-alpha", 0.95)

        icon_path = os.path.join("assets", "gui_icon.ico")
        self.root.iconbitmap(icon_path)
        self.mouse_speed = tk.DoubleVar(value=0.2)
        self.screenshot_speed = tk.DoubleVar(value=0.3)
        self.ignore_path = (
            set(self.app_config.ALL_PATH) - self.app_config.MANDATORY_PATH
        )
        self.keep_image_open = []
        self.lock_start_button = False
        self.budget = tk.DoubleVar(value=0)

        # app title and image        #apply ui change here
        self.Label("Epic Seven shop refresh", weight="bold")

        # special setting
        special_frame = tk.Frame(self.root, bg=self.unite_bg_color)
        self.hint_cbv = tk.IntVar()
        self.move_zerozero_cbv = tk.IntVar()

        def setupSpecialSetting(label, value):
            frame = tk.Frame(special_frame, bg=self.unite_bg_color)
            special_label = tk.Label(
                master=frame,
                text=label,
                bg=self.unite_bg_color,
                fg=self.unite_text_color,
                font=("Helvetica", 12),
            )
            special_cb = tk.Checkbutton(
                master=frame,
                font=("Helvetica", 14),
                variable=value,
                bg=self.unite_bg_color,
            )
            special_cb.select()
            special_label.pack(side=tk.LEFT)
            special_cb.pack(side=tk.RIGHT)
            frame.pack()

        setupSpecialSetting("Hint:", self.hint_cbv)
        setupSpecialSetting(
            "Auto move emulator window to top left:", self.move_zerozero_cbv
        )

        # Step 1 Select the emulator
        self.emulator = self.addLabelFrame("Select emulator or type emulator's window title")
        
        # Sort titles initially
        self.titles = self._get_titles()
        self.title_name = tk.StringVar(value=self.titles[0])
        
        # Create initial option menu
        self.window_list = self.emulator.OptionMenu(self.titles, self.title_name, self._select_window, row=1, col=1)
        # Update the button to use an icon
        refresh_icon = ImageTk.PhotoImage(Image.open(os.path.join("assets", "ui", "cm_hud_top_btn_auto.png")).resize((24,24)))
        self.refresh_icon = self.emulator.Button("Refresh", widgetkwargs={"image":refresh_icon}, command=self._refresh_window, row=1, col=2)

        # Step 2 Select item
        self.items = self.addLabelFrame("Select item that you are looking for")

        def updateIgnore(cbv):
            if cbv.get() == 1:
                self.ignore_path.discard(path)
            else:
                self.ignore_path.add(path)

        for index, path in enumerate(self.app_config.ALL_PATH):
            self.keep_image_open.append(
                ImageTk.PhotoImage(Image.open(os.path.join("assets", path)))
            )
            image_label = tk.Label(
                text="Image and Text",
                image=self.keep_image_open[index],
                bg="#FFBF00",
                compound=tk.TOP,
            )
            self.items.SlideSwitch(image_label, updateIgnore, col=index)

        self.tool_settings = self.addLabelFrame("Refresh settings")
        # Step 3 Select setting
        # check if input is valid
        self.tool_settings.Text("Mouse speed (s):", col=1, row=1)
        self.tool_settings.NumericalSpinbox(
            0.2, 100000000, 0.1, self.mouse_speed, col=2, row=1
        )

        self.tool_settings.Text("Screenshot speed (s):", row=2, col=1)
        self.tool_settings.NumericalSpinbox(
            0.3, 100000000, 0.1, self.screenshot_speed, col=2, row=2
        )

        text_with_img(
            self.tool_settings,
            row=3,
            col=1,
            data=(
                ("text", "How many "),
                ("img", os.path.join("assets", "ui", "token_crystal.png")),
                ("text", "skystone do you want to spend? :")
            ),
        )
        # self.tool_settings.Text(skystone, row=3, col=1)
        self.tool_settings.NumericalSpinbox(3, 100000000, 3, self.budget, col=2, row=3)

        # Step 3.5 special setting and setting

        # Step 4 profit
        self.start_button = self.AccentButton(
            "Start refresh",
            command=self.startShopRefresh,
            pady=25,
            widgetkwargs={
                "state": (
                    tk.NORMAL if self.title_name in gw.getAllTitles() else tk.DISABLED
                )
            },
        )

        self.root.mainloop()

    def _get_titles(self):
        _titles = [t for t in self.app_config.RECOGNIZE_TITLES if t in gw.getAllTitles()]
        _titles.sort()  # Sort the list in place
        if not _titles:
            return ["No valid window detected."]
        return _titles 

    def _select_window(self, title):
        if title not in gw.getAllTitles():
            self.start_button.config(state=tk.DISABLED)
        elif not self.lock_start_button:
            self.start_button.config(state=tk.NORMAL)

    def _refresh_window(self):
        "Get list of windows and recreate option menu"
        # Get new list of titles
        new_titles = self._get_titles()
        # if new_titles == self.titles: return
        
        # Destroy old option menu and create new one
        if self.window_list:
            for wg in self.emulator.widgets.widgetlist:
                if str(wg.name).startswith("OptionMenu"):
                    self.emulator.widgets.widgetlist.remove(wg)
            self.window_list.destroy()
        self.window_list = self.emulator.OptionMenu(new_titles, self.title_name, self._select_window, row=1, col=1)
        self.titles = new_titles
        
        # Update title if current one is not valid
        if self.title_name.get() not in new_titles:
            self.title_name.set(new_titles[0])
            self._select_window(new_titles[0])


    def refreshComplete(self):
        print("Terminated!")
        self.root.title("SHOP AUTO REFRESH")
        self.start_button.config(state=tk.NORMAL)
        self.lock_start_button = False

    # start refresh loop
    def startShopRefresh(self):
        self.root.title("Press ESC to stop!")
        self.lock_start_button = True
        self.start_button.config(state=tk.DISABLED)

        if self.hint_cbv.get() == 1:
            self.ssr = SecretShopRefresh(
                title_name=self.title_name,
                callback=self.refreshComplete,
                tk_instance=self.root,
                debug=self.app_config.DEBUG,
            )
        else:
            self.ssr = SecretShopRefresh(
                title_name=self.title_name,
                callback=self.refreshComplete,
                debug=self.app_config.DEBUG,
            )

        if self.move_zerozero_cbv.get() != 1:
            self.ssr.allow_move = True

        # setting item to refresh for
        rs_instance = RefreshStatistic()
        all_data = zip(
            self.app_config.ALL_PATH,
            self.app_config.ALL_NAME,
            self.app_config.ALL_PRICE,
        )
        for path, name, price in all_data:
            if path not in self.ignore_path:
                rs_instance.addShopItem(path, name, price)
        self.ssr.rs_instance = rs_instance

        # setting mouse speed
        self.ssr.mouse_sleep = (
            float(self.mouse_speed_entry.get())
            if self.mouse_speed_entry.get() != ""
            else self.mouse_speed
        )
        self.ssr.screenshot_sleep = (
            float(self.screenshot_speed_entry.get())
            if self.screenshot_speed_entry.get() != ""
            else self.screenshot_speed
        )

        # setting up skystone budget
        if self.limit_spend_entry.get() != "":
            self.ssr.budget = int(self.limit_spend_entry.get())

        print("refresh shop start!")
        print("Budget:", self.ssr.budget)
        print("Mouse speed:", self.ssr.mouse_sleep)
        print("Screenshot speed", self.ssr.screenshot_sleep)
        if self.ssr.budget and self.ssr.budget >= 1000:
            ev_cost = 1691.04536 * int(self.ssr.budget) * 2
            ev_cov = 0.006602509 * int(self.ssr.budget) * 2
            ev_mys = 0.001700646 * int(self.ssr.budget) * 2
            print("Approximation based on budget:")
            print(f"Cost: {int(ev_cost):,}")
            print(f"Cov: {ev_cov}")
            print(f"mys: {ev_mys}")
        print()

        self.ssr.start()


if __name__ == "__main__":
    # Secret shop with GUI
    gui = AutoRefreshGUI()

    # # Uncomment below code start secret shop without gui, remember to comment everything above
    # # Here are some parameter that you can pass in to secret shop calss
    # # title_name: str      name of your emulator window
    # # call_back: func      callback function when the macro terminates
    # # budget: int          the ammont of skystone that you want to spend
    # # debug: boolean       this will help you debug problem with the program

    # print('Here are the active windows\n')
    # for title in gw.getAllTitles():
    #     if title != '':
    #         print(title)

    # win = input('Emulator: ')
    # if win != '':

    #     ssr = SecretShopRefresh(win, budget=None)       #init macro instance with the application title being epic seven
    #     ssr.addShopItem('cov.jpg', 'Covenant bookmark', 184000)     #adding items to refresh, cov.jpg needs to be in: assets/cov.jpg
    #     ssr.addShopItem('mys.jpg', 'Mystic medal', 280000)
    #     #ssr.addShopItem('fb.jpg', 'Friendship bookmark', 18000)     #comment out this, if you don't need to test
    #     input('press any key to start')
    #     ssr.start()     #Start macro instance, use ESC to terminate macro
    # # Eric baby piles approved
