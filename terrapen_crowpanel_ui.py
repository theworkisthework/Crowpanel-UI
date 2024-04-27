import lvgl as lv
import time
import json
from espidf import VSPI_HOST
from ili9XXX import ili9341
from xpt2046 import xpt2046
from machine import UART

# lv.include_in_defs(lv.obj.HEADER_SYMBOL)

# uart0 = UART(1, 115200)  # Default USB-C
uart1 = UART(2, 115200)  # Uart 1

WIDTH = 240
HEIGHT = 320

#print(f"{uart0}, {uart1}")

disp = ili9341(miso=12, mosi=13, clk=14, cs=15, dc=2, rst=-1, power=0, backlight=27, backlight_on=-1, power_on=1, rot=0x80,
        spihost=VSPI_HOST, mhz=60, factor=16, hybrid=True, width=WIDTH, height=HEIGHT,
        invert=False, double_buffer=True, half_duplex=False, initialize=True)

touch = xpt2046(cs=33, spihost=VSPI_HOST, mosi=-1, miso=-1, clk=-1, cal_y0 = 423, cal_y1=3948)

ui_scr = lv.obj()

ui_file_list = lv.list(ui_scr)
ui_file_list.set_size(240, 240)
# ui_dialog = lv.message(ui_scr)

class CommandParser():
    def __init__(self):
        self.gcode_files = []
        self.data = []
    
    # def show_gcode_files():
    #     text_area.add_text(self.gcode_files)
        
    def parse_square_brackets(self, data):
        if ("JSON:" in data):
            _leader, raw_data = data.split("JSON:",1)
            items = raw_data.split("\\r\\n")
            for item in items:
                json_data = json.loads(item)
            if (hasattr(json_data, "files")):
                print(f"json_data: {json_data}")

            # We now have a list of the files on the SD card stored in this class
            # This can be done here or could be a call back to the UI element (hardcode for now)
            text_area.add_text(self.gcode_files)


    def fetch_data(self):
        # Fetch data from the serial port until we read an 'ok'
        # print("Fetch data")
        # clear previously fetch data
        self.data = []
        fetch = True
        while fetch:
            while uart1.any():
                data = uart1.readline()
                if "ok" in data:
                    fetch = False
                else:
                    self.data.append(data)
        self.parse_input(self.data)
        
    def get_file_data(self):
        # Return stored file data
        return self.gcode_files["files"]

    def parse_input(self, data):
        # for each bit of data in input data, parse it and store for each type of command
        # do we have data? If so, identify the type of command we have - that requires some research
        # <> is likey default grbl report (position etc)
        # [] is other data?
        
        # For now, lets just get file list working with the json data

        # print(f"parse_input data: {data}")
        joined_data = "".join([item.decode('utf-8') for item in data])
        print(f"parse_input joined: {joined_data}")
        json_data = json.loads(joined_data)
        self.gcode_files = json_data
        # print(f"Json data: {json_data["files"]}) 


class Button():
    def __init__(self, scr, label, x, y, callback):
        self.label = label
        self.callback = callback
        btn = lv.btn(scr)  
        btn.set_size(120, 50) 
        # btn.set_pos(x,y) # Why doesn't this set the buttons position?
        btn.align(lv.ALIGN.CENTER,x,y)  # Why does this set the buttons position but also messes with the buttons clickable area or location?
        btn.add_event_cb(self.btn_event_cb, lv.EVENT.ALL, None)  
        label = lv.label(btn) 
        label.set_text(self.label)
        label.center() 

    def btn_event_cb(self, evt):
        code = evt.get_code()  
        if code == lv.EVENT.CLICKED:
            self.callback()

def write_command(command):
    print(f"Write Command: {command}")
    uart1.write(command)

def fetch_files(path=None):
    # $sd/listjson=/sd/gcode
    if path:
        write_command(f"$SD/ListJSON={path}\r\n")
    else:
        write_command("$SD/ListJSON\r\n")

def run_file(file):
    write_command(f"$SD/Run=/{file}\r\n")

def delete_file(file):
    write_command(f"$SD/Delete=/{file}\r\n")

def play():
    write_command("~")

def pause():
    write_command("!")

def file_browser_callback():
    fetch_files()
    list_files()

def list_files():
    command_parser.fetch_data()  # If we know that this command returns json, why not call parse json for this?
    # print(f"List files has: {command_parser.get_file_data()}")
    
    # clean the ui file list
    ui_file_list = lv.list(ui_scr)
    ui_file_list.set_size(240, 240)
    
    if command_parser.gcode_files["path"] is not "":
        # include a nagivate "up" button
        list_item_button = ui_file_list.add_btn(lv.SYMBOL.NEW_LINE, "Back")
        
    for item in command_parser.get_file_data():

        def handle_button_click(event):
            # Access the item data stored in the button's user data
            clicked_btn = event.get_target()
            print(f"clicked_btn: {clicked_btn}")

            def handle_dialog_button_click(dialog_event):
                print(f"Dialog button pressed with event {dialog_event}")
                # if (dialog_event == lv.EVENT.VALUE_CHANGED):
                button_target = dialog_event.get_target()
                print(f"button_target: {button_target}")
                if button_target is lv.btnmatrix:
                    button_id = button_target.get_selected_btn()
                    button_text = lv.btnmatrix.get_btn_text(button_target, button_id)
                    print(f"dialog event target {button_text}")
                    if button_text == "Run":
                        run_file(clicked_btn["name"])
                    elif button_text == "Delete":
                        delete_file(clicked_btn["name"])    

            # If this is a file, display a dialog to execute the gcode, maybe delete as well?
            if int(clicked_btn["size"]) > 0:
                # Open dialog to run or cancel job
                print("File clicked - display dialog to run or cancel job")
                job_dialog = lv.msgbox(None, "Job", clicked_btn["name"], ["Run", "Delete"], True)
                job_dialog.align(lv.ALIGN.CENTER,0,0)
                job_dialog.add_event_cb(handle_dialog_button_click, lv.EVENT.CLICKED, None)
            
            # If this is a directory, get new file list but also display a link back (dir up icon ..)
            elif int(clicked_btn["size"]) == -1:
                print(f"Directory entry clicked: '{clicked_btn["name"]}' - relist files for selected directory")
                print(f"command_parser.gcode: {command_parser.gcode_files}")
                if (command_parser.gcode_files["path"] is not ""):
                    print(f"We have a path already? {command_parser.gcode_files["path"]}")
                    fetch_files(f"{command_parser.gcode_files["path"]}/{clicked_btn["name"]}")
                else:
                    fetch_files(f"/SD/{clicked_btn["name"]}")
                list_files()

            else:
                print("No idea what this is... we shouldn't be here")

        if item["size"] == "-1":
            # print("Directory")
            list_item_button = ui_file_list.add_btn(lv.SYMBOL.DIRECTORY, item["name"])
        else:
            # print("File")
            list_item_button = ui_file_list.add_btn(lv.SYMBOL.FILE, item["name"])
        
        # Set the user data of the button to the current item data
        list_item_button.set_user_data(item)

        # Add a click event handler to the button
        list_item_button.add_event_cb(handle_button_click, lv.EVENT.CLICKED, None)


#play_button = CounterBtn(scr,"Play",-50,0, play)
#pause_button = CounterBtn(scr,"Pause",50,0, pause)

# List files button, run callback 'list_files' (that issues the file list command, parses the data and puts that into the ui list component)
list_files_button = Button(ui_scr,"List Files",0,115, file_browser_callback)
lv.scr_load(ui_scr)

command_parser = CommandParser()
# uart1.irq(command_parser.fetch_data())

try:
    # from machine import WDT
    # wdt = WDT(timeout=2000)  # enable it with a timeout of 2s
    print("Hint: Press Ctrl+C to end the program")
    while True:
        # wdt.feed()
        time.sleep(0.1)
except KeyboardInterrupt as ret:
    print("The program stopped running, ESP32 has restarted...")
    disp.deinit()

