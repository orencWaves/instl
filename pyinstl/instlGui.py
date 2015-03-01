#!/usr/bin/env python2.7

from __future__ import print_function

import stat
import shlex
from pyinstl.utils import *
from aYaml import augmentedYaml

from instlInstanceBase import InstlInstanceBase
from configVarStack import var_stack

from Tkinter import *
from ttk import *

def bool_int_to_str(in_bool_int):
    if in_bool_int == 0:
        retVal = "no"
    else:
        retVal = "yes"
    return retVal

def str_to_bool_int(the_str):
    if the_str.lower() in ("yes", "true", "y", 't'):
        retVal = 1
    elif the_str.lower() in ("no", "false", "n", "f"):
        retVal = 0
    else:
        raise ValueError("Cannot translate", the_str, "to bool-int")
    return retVal

class InstlGui(InstlInstanceBase):
    def __init__(self, initial_vars):
        super(InstlGui, self).__init__(initial_vars)
        self.master = Tk()
        self.master.createcommand('exit', self.quit_app) # exit from quit menu or Command-Q
        self.master.protocol('WM_DELETE_WINDOW', self.quit_app) # exit from closing the window
        self.commands_that_accept_limit_option = ("stage2svn", "svn2stage")

        self.client_command_name_var = StringVar()
        self.client_input_path_var = StringVar()
        self.client_input_combobox = None
        self.client_output_path_var = StringVar()
        self.run_client_batch_file_var = IntVar()

        self.admin_command_name_var = StringVar()
        self.admin_config_path_var = StringVar()
        self.admin_output_path_var = StringVar()
        self.admin_stage_index_var = StringVar()
        self.admin_sync_url_var = StringVar()
        self.admin_svn_repo_var = StringVar()
        self.admin_config_file_dirty = True
        self.run_admin_batch_file_var = IntVar()
        self.admin_limit_var = StringVar()
        self.limit_path_entry_widget = None
        self.client_credentials_var = StringVar()
        self.client_credentials_on_var = IntVar()

    def quit_app(self):
        self.write_history()
        exit()

    def set_default_variables(self):
        client_command_list = var_stack.resolve_var_to_list("__CLIENT_GUI_CMD_LIST__")
        var_stack.set_var("CLIENT_GUI_CMD").append(client_command_list[0])
        admin_command_list = var_stack.resolve_var_to_list("__ADMIN_GUI_CMD_LIST__")
        var_stack.set_var("ADMIN_GUI_CMD").append(admin_command_list[0])

    def do_command(self):
        self.set_default_variables()
        self.read_history()
        self.create_gui()

    def read_history(self):
        try:
            self.read_yaml_file(var_stack.resolve_var("INSTL_GUI_CONFIG_FILE_NAME"))
        except:
            pass


    def write_history(self):
        selected_tab = self.notebook.tab(self.notebook.select(), option='text')
        var_stack.set_var("SELECTED_TAB").append(selected_tab)

        the_list_yaml_ready= var_stack.repr_for_yaml(which_vars=var_stack.resolve_var_to_list("__GUI_CONFIG_FILE_VARS__"), include_comments=False, resolve=False, ignore_unknown_vars=True)
        the_doc_yaml_ready = augmentedYaml.YamlDumpDocWrap(the_list_yaml_ready, '!define', "Definitions", explicit_start=True, sort_mappings=True)
        with open(var_stack.resolve_var("INSTL_GUI_CONFIG_FILE_NAME"), "w") as wfd:
            make_open_file_read_write_for_all(wfd)
            augmentedYaml.writeAsYaml(the_doc_yaml_ready, wfd)

    def get_client_input_file(self):
        import tkFileDialog
        retVal = tkFileDialog.askopenfilename()
        if retVal:
            self.client_input_path_var.set(retVal)
            self.update_client_state()

    def get_client_output_file(self):
        import tkFileDialog
        retVal = tkFileDialog.asksaveasfilename()
        if retVal:
            self.client_output_path_var.set(retVal)
            self.update_client_state()

    def get_admin_config_file(self):
        import tkFileDialog
        retVal = tkFileDialog.askopenfilename()
        if retVal:
            self.admin_config_path_var.set(retVal)
            self.update_admin_state()

    def get_admin_output_file(self):
        import tkFileDialog
        retVal = tkFileDialog.asksaveasfilename()
        if retVal:
            self.admin_output_path_var.set(retVal)
            self.update_admin_state()

    def open_file_for_edit(self, path_to_file):
        path_to_file = os.path.relpath(path_to_file)
        try:
            os.startfile(path_to_file, 'edit')
        except AttributeError:
            subprocess.call(['open', path_to_file])

    def create_client_command_line(self):
        retVal = [var_stack.resolve_var("__INSTL_EXE_PATH__"), var_stack.resolve_var("CLIENT_GUI_CMD"),
                        "--in", var_stack.resolve_var("CLIENT_GUI_IN_FILE"),
                        "--out", var_stack.resolve_var("CLIENT_GUI_OUT_FILE")]

        if self.client_credentials_on_var.get():
            credentials = self.client_credentials_var.get()
            if credentials != "":
                retVal.append("--credentials")
                retVal.append(credentials)

        if self.run_client_batch_file_var.get() == 1:
            retVal.append("--run")

        if 'Win' in var_stack.resolve_to_list("$(__CURRENT_OS_NAMES__)"):
            if not getattr(sys, 'frozen', False):
                retVal.insert(0, sys.executable)

        return retVal

    def create_admin_command_line(self):
        retVal = [var_stack.resolve_var("__INSTL_EXE_PATH__"), var_stack.resolve_var("ADMIN_GUI_CMD"),
                        "--config-file", var_stack.resolve_var("ADMIN_GUI_CONFIG_FILE"),
                        "--out", var_stack.resolve_var("ADMIN_GUI_OUT_FILE")]

        if self.admin_command_name_var.get() in self.commands_that_accept_limit_option:
            limit_path = self.admin_limit_var.get()
            if limit_path != "":
                retVal.append("--limit")
                limit_paths = shlex.split(limit_path) # there might be space separated paths
                retVal.extend(limit_paths)

        if self.run_admin_batch_file_var.get() == 1:
            retVal.append("--run")

        if 'Win' in var_stack.resolve_to_list("$(__CURRENT_OS_NAMES__)"):
            if not getattr(sys, 'frozen', False):
                retVal.insert(0, sys.executable)

        return retVal

    def update_client_input_file_combo(self, *args):
        prev_input_file = var_stack.resolve_var("CLIENT_GUI_IN_FILE")
        new_input_file = self.client_input_path_var.get()
        if os.path.isfile(new_input_file):
            new_input_file_dir, new_input_file_name = os.path.split(new_input_file)
            items_in_dir = os.listdir(new_input_file_dir)
            dir_items = [os.path.join(new_input_file_dir, item) for item in items_in_dir if os.path.isfile(os.path.join(new_input_file_dir, item))]
            self.client_input_combobox.configure(values = dir_items)
        var_stack.set_var("CLIENT_GUI_IN_FILE").append(self.client_input_path_var.get())

    def update_client_state(self, *args):
        var_stack.set_var("CLIENT_GUI_CMD").append(self.client_command_name_var.get())
        self.update_client_input_file_combo()

        _, input_file_base_name = os.path.split(var_stack.unresolved_var("CLIENT_GUI_IN_FILE"))
        var_stack.set_var("CLIENT_GUI_IN_FILE_NAME").append(input_file_base_name)

        var_stack.set_var("CLIENT_GUI_OUT_FILE").append(self.client_output_path_var.get())
        var_stack.set_var("CLIENT_GUI_RUN_BATCH").append(bool_int_to_str(self.run_client_batch_file_var.get()))
        var_stack.set_var("CLIENT_GUI_CREDENTIALS").append(self.client_credentials_var.get())
        var_stack.set_var("CLIENT_GUI_CREDENTIALS_ON").append(self.client_credentials_on_var.get())

        command_line = " ".join(self.create_client_command_line())

        self.client_command_line_var.set(var_stack.resolve(command_line))

    def read_admin_config_file(self):
        config_path = var_stack.resolve_var("ADMIN_GUI_CONFIG_FILE", default="")
        if os.path.isfile(config_path):
            var_stack.get_configVar_obj("__SEARCH_PATHS__").clear_values() # so __include__ file will not be found on old paths
            self.read_yaml_file(config_path)
            self.admin_config_file_dirty = False
        else:
            print("File not found:", config_path)


    def update_admin_state(self, *args):
        var_stack.set_var("ADMIN_GUI_CMD").append(self.admin_command_name_var.get())

        current_config_path = var_stack.resolve_var("ADMIN_GUI_CONFIG_FILE", default="")
        new_config_path = self.admin_config_path_var.get()
        if current_config_path != new_config_path:
            self.admin_config_file_dirty = True
        var_stack.set_var("ADMIN_GUI_CONFIG_FILE").append(new_config_path)
        if self.admin_config_file_dirty:
             self.read_admin_config_file()

        _, input_file_base_name = os.path.split(var_stack.unresolved_var("ADMIN_GUI_CONFIG_FILE"))
        var_stack.set_var("ADMIN_GUI_CONFIG_FILE_NAME").append(input_file_base_name)

        var_stack.set_var("ADMIN_GUI_OUT_FILE").append(self.admin_output_path_var.get())

        var_stack.set_var("ADMIN_GUI_RUN_BATCH").append(bool_int_to_str(self.run_admin_batch_file_var.get()))
        var_stack.set_var("ADMIN_GUI_LIMIT").append(self.admin_limit_var.get())

        self.admin_stage_index_var.set(var_stack.resolve("$(STAGING_FOLDER)/instl/index.yaml"))
        self.admin_svn_repo_var.set(var_stack.resolve("$(SVN_REPO_URL), REPO_REV: $(REPO_REV)"))

        sync_url = var_stack.resolve("$(SYNC_BASE_URL)")
        self.admin_sync_url_var.set(sync_url)

        if self.admin_command_name_var.get() in self.commands_that_accept_limit_option:
            self.limit_path_entry_widget.configure(state='normal')
        else:
            self.limit_path_entry_widget.configure(state='disabled')

        command_line = " ".join(self.create_admin_command_line())

        self.admin_command_line_var.set(var_stack.resolve(command_line))

    def run_client(self):
        self.update_client_state()
        command_line = self.create_client_command_line()

        from subprocess import Popen
        if getattr(os, "setsid", None):
            proc = subprocess.Popen(command_line, executable=command_line[0], shell=False, preexec_fn=os.setsid) # Unix
        else:
            proc = subprocess.Popen(command_line, executable=command_line[0], shell=False) # Windows
        unused_stdout, unused_stderr = proc.communicate()
        retcode = proc.returncode
        if retcode != 0:
            print(" ".join(command_line) + " returned exit code " + str(retcode))

    def run_admin(self):
        self.update_admin_state()
        command_line = self.create_admin_command_line()

        from subprocess import Popen
        if getattr(os, "setsid", None):
            proc = subprocess.Popen(command_line, executable=command_line[0], shell=False, preexec_fn=os.setsid) # Unix
        else:
            proc = subprocess.Popen(command_line, executable=command_line[0], shell=False) # Windows
        unused_stdout, unused_stderr = proc.communicate()
        retcode = proc.returncode
        if retcode != 0:
            print(" ".join(command_line) + " returned exit code " + str(retcode))

    def create_admin_frame(self, master):

        admin_frame = Frame(master)
        admin_frame.grid(row=0, column=1)

        curr_row = 0
        Label(admin_frame, text="Command:").grid(row=curr_row, column=0, sticky=E)

        # instl command selection
        self.admin_command_name_var.set(var_stack.unresolved_var("ADMIN_GUI_CMD"))
        admin_command_list = var_stack.resolve_var_to_list("__ADMIN_GUI_CMD_LIST__")
        OptionMenu(admin_frame, self.admin_command_name_var, self.admin_command_name_var.get(), *admin_command_list, command=self.update_admin_state).grid(row=curr_row, column=1, sticky=W)

        self.run_admin_batch_file_var.set(str_to_bool_int(var_stack.unresolved_var("ADMIN_GUI_RUN_BATCH")))
        Checkbutton(admin_frame, text="Run batch file", variable=self.run_admin_batch_file_var, command=self.update_admin_state).grid(row=curr_row, column=2, columnspan=2, sticky=E)

        # path to config file
        curr_row += 1
        Label(admin_frame, text="Config file:").grid(row=curr_row, column=0, sticky=E)
        self.admin_config_path_var.set(var_stack.unresolved_var("ADMIN_GUI_CONFIG_FILE"))
        Entry(admin_frame, textvariable=self.admin_config_path_var).grid(row=curr_row, column=1, columnspan=2, sticky=W+E)
        self.admin_config_path_var.trace('w', self.update_admin_state)
        Button(admin_frame, width=2, text="...", command=self.get_admin_config_file).grid(row=curr_row, column=3, sticky=W)
        Button(admin_frame, width=4, text="Edit", command=lambda: self.open_file_for_edit(var_stack.resolve_var("ADMIN_GUI_CONFIG_FILE"))).grid(row=curr_row, column=4, sticky=W)

        # path to stage index file
        curr_row += 1
        Label(admin_frame, text="Stage index:").grid(row=curr_row, column=0, sticky=E)
        Label(admin_frame, text="---", textvariable=self.admin_stage_index_var).grid(row=curr_row, column=1, columnspan=2, sticky=W)
        Button(admin_frame, width=4, text="Edit", command=lambda: self.open_file_for_edit(var_stack.resolve("$(STAGING_FOLDER)/instl/index.yaml", raise_on_fail=True))).grid(row=curr_row, column=4, sticky=W)

        # path to svn repository
        curr_row += 1
        Label(admin_frame, text="Svn repo:").grid(row=curr_row, column=0, sticky=E)
        Label(admin_frame, text="---", textvariable=self.admin_svn_repo_var).grid(row=curr_row, column=1, columnspan=2, sticky=W)

        # sync URL
        curr_row += 1
        Label(admin_frame, text="Sync URL:").grid(row=curr_row, column=0, sticky=E)
        Label(admin_frame, text="---", textvariable=self.admin_sync_url_var).grid(row=curr_row, column=1, columnspan=2, sticky=W)

        # path to output file
        curr_row += 1
        Label(admin_frame, text="Batch file:").grid(row=curr_row, column=0, sticky=E)
        self.admin_output_path_var.set(var_stack.unresolved_var("ADMIN_GUI_OUT_FILE"))
        Entry(admin_frame, textvariable=self.admin_output_path_var).grid(row=curr_row, column=1, columnspan=2, sticky=W+E)
        self.admin_output_path_var.trace('w', self.update_admin_state)
        Button(admin_frame, width=2, text="...", command=self.get_admin_output_file).grid(row=curr_row, column=3, sticky=W)
        Button(admin_frame, width=4, text="Edit", command=lambda: self.open_file_for_edit(var_stack.resolve_var("ADMIN_GUI_OUT_FILE"))).grid(row=curr_row, column=4, sticky=W)

        # relative path to limit folder
        curr_row += 1
        Label(admin_frame, text="Limit to:").grid(row=curr_row, column=0, sticky=E)
        self.admin_limit_var.set(var_stack.unresolved_var("ADMIN_GUI_LIMIT"))
        self.limit_path_entry_widget = Entry(admin_frame, textvariable=self.admin_limit_var)
        self.limit_path_entry_widget.grid(row=curr_row, column=1, columnspan=2, sticky=W+E)
        self.admin_limit_var.trace('w', self.update_admin_state)

        # the combined command line text
        curr_row += 1
        Button(admin_frame, width=6, text="run:", command=self.run_admin).grid(row=curr_row, column=0, sticky=W)
        self.admin_command_line_var = StringVar()
        Label(admin_frame, textvariable=self.admin_command_line_var, wraplength=400, anchor=W).grid(row=curr_row, column=1, columnspan=2, sticky=W)

        return admin_frame

    def create_client_frame(self, master):

        client_frame = Frame(master)
        client_frame.grid(row=0, column=0)


        curr_row = 0
        command_label = Label(client_frame, text="Command:")
        command_label.grid(row=curr_row, column=0, sticky=W)

        # instl command selection
        client_command_list = var_stack.resolve_var_to_list("__CLIENT_GUI_CMD_LIST__")
        self.client_command_name_var.set(var_stack.unresolved_var("CLIENT_GUI_CMD"))
        OptionMenu(client_frame, self.client_command_name_var, self.client_command_name_var.get(), *client_command_list, command=self.update_client_state).grid(row=curr_row, column=1, sticky=W)

        self.run_client_batch_file_var.set(str_to_bool_int(var_stack.unresolved_var("CLIENT_GUI_RUN_BATCH")))
        Checkbutton(client_frame, text="Run batch file", variable=self.run_client_batch_file_var, command=self.update_client_state).grid(row=curr_row, column=2, sticky=E)

        # path to input file
        curr_row += 1
        Label(client_frame, text="Input file:").grid(row=curr_row, column=0)
        self.client_input_path_var.set(var_stack.unresolved_var("CLIENT_GUI_IN_FILE"))
        self.client_input_combobox = Combobox(client_frame, textvariable=self.client_input_path_var)
        self.client_input_combobox.grid(row=curr_row, column=1, columnspan=2, sticky=W+E)
        self.client_input_path_var.trace('w', self.update_client_state)
        Button(client_frame, width=2, text="...", command=self.get_client_input_file).grid(row=curr_row, column=3, sticky=W)
        Button(client_frame, width=4, text="Edit", command=lambda: self.open_file_for_edit(var_stack.resolve_var("CLIENT_GUI_IN_FILE"))).grid(row=curr_row, column=4, sticky=W)

        # path to output file
        curr_row += 1
        Label(client_frame, text="Batch file:").grid(row=curr_row, column=0)
        self.client_output_path_var.set(var_stack.unresolved_var("CLIENT_GUI_OUT_FILE"))
        Entry(client_frame, textvariable=self.client_output_path_var).grid(row=curr_row, column=1, columnspan=2, sticky=W+E)
        self.client_output_path_var.trace('w', self.update_client_state)
        Button(client_frame, width=2, text="...", command=self.get_client_output_file).grid(row=curr_row, column=3, sticky=W)
        Button(client_frame, width=4, text="Edit", command=lambda: self.open_file_for_edit(var_stack.resolve_var("CLIENT_GUI_OUT_FILE"))).grid(row=curr_row, column=4, sticky=W)

        # s3 user credentials
        curr_row += 1
        Label(client_frame, text="Credentials:").grid(row=curr_row, column=0, sticky=E)
        self.client_credentials_var.set(var_stack.unresolved_var("CLIENT_GUI_CREDENTIALS"))
        Entry(client_frame, textvariable=self.client_credentials_var).grid(row=curr_row, column=1, columnspan=2, sticky=W+E)
        self.client_credentials_var.trace('w', self.update_client_state)

        self.client_credentials_on_var.set(var_stack.unresolved_var("CLIENT_GUI_CREDENTIALS_ON"))
        Checkbutton(client_frame, text="", variable=self.client_credentials_on_var).grid(row=curr_row, column=3, sticky=W)
        self.client_credentials_on_var.trace('w', self.update_client_state)

        # the combined command line text
        curr_row += 1
        Button(client_frame, width=6, text="run:", command=self.run_client).grid(row=curr_row, column=0, sticky=W)
        self.client_command_line_var = StringVar()
        Label(client_frame, textvariable=self.client_command_line_var, wraplength=400, anchor=W).grid(row=curr_row, column=1, columnspan=4, sticky=W)

        client_frame.grid_columnconfigure(0, minsize=80)
        client_frame.grid_columnconfigure(1, minsize=300)
        client_frame.grid_columnconfigure(2, minsize=80)

        return client_frame

    def tabChangedEvent(self, *args):
        tab_id = self.notebook.select()
        tab_name = self.notebook.tab(tab_id, option='text')
        if tab_name == "Admin":
            self.update_admin_state()
        elif tab_name == "Client":
            self.update_client_state()
        else:
            print("Unknown tab", tab_name)

    def create_gui(self):

        self.master.title(self.get_version_str())

        self.notebook = Notebook(self.master)
        self.notebook.grid(row=0, column=0)
        self.notebook.bind_all("<<NotebookTabChanged>>", self.tabChangedEvent)

        client_frame = self.create_client_frame(self.notebook)
        admin_frame = self.create_admin_frame(self.notebook)

        self.notebook.add(client_frame, text='Client')
        self.notebook.add(admin_frame, text='Admin')

        to_be_selected_tab_name = var_stack.resolve_var("SELECTED_TAB")
        for tab_id in self.notebook.tabs():
            tab_name = self.notebook.tab(tab_id, option='text')
            if tab_name == to_be_selected_tab_name:
                self.notebook.select(tab_id)
                break

        self.master.resizable(0, 0)

        # bring window to front, be default it stays behind the Terminal window
        if var_stack.resolve_var("__CURRENT_OS__") == "Mac":
            os.system('''/usr/bin/osascript -e 'tell app "Finder" to set frontmost of process "Python" to true' ''')

        self.master.mainloop()
        self.quit_app()
        #self.master.destroy() # optional; see description below