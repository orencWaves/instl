import os
import stat
import random
import string
import shutil
import pathlib
import re
from typing import List, Any

import utils
from .baseClasses import *


def touch(file_path):
    with open(file_path, 'a'):
        os.utime(file_path, None)


# regex to find some characters that should be escaped in dos, but are not
dos_escape_regex = re.compile("""(?<!\^)([<|&>])""", re.MULTILINE)


def escape_me_dos_callback(match_obj):
    replacement = "^"+match_obj.group(1)
    return replacement


def dos_escape(some_string):
    # 1. remove ^><|'s from end of string - they cause CMD to ask for 'More?' or 'The syntax of the command is incorrect.'
    retVal = some_string.rstrip("^><|")
    # 2. replace some chars with ?
    retVal = re.sub("""[\r\n]""", "?", retVal)
    # 3. escape some chars, but only of they are not already escaped
    retVal = dos_escape_regex.sub(escape_me_dos_callback, retVal)
    return retVal

# === classes with tests ===
class MakeRandomDirs(PythonBatchCommandBase):
    """ MakeRandomDirs is intended for use during tests - not for production
        Will create in current working directory a hierarchy of folders and files with random names so we can test copying
    """

    def __init__(self, num_levels: int, num_dirs_per_level: int, num_files_per_dir: int, file_size: int) -> None:
        super().__init__()
        self.num_levels = num_levels
        self.num_dirs_per_level = num_dirs_per_level
        self.num_files_per_dir = num_files_per_dir
        self.file_size = file_size

    def __repr__(self):
        the_repr = f"""{self.__class__.__name__}(num_levels={self.num_levels}, num_dirs_per_level={self.num_dirs_per_level}, num_files_per_dir={self.num_files_per_dir}, file_size={self.file_size})"""
        return the_repr

    def repr_batch_win(self):
        return "echo MakeRandomDirs is not implemented for batch win"

    def repr_batch_mac(self):
        return "echo MakeRandomDirs is not implemented for batch mac"

    def progress_msg_self(self):
        the_progress_msg = f"create random directories and files under current dir {os.getcwd()}"
        return the_progress_msg

    def make_random_dirs_recursive(self, num_levels: int):
        for i_file in range(self.num_files_per_dir):
            random_file_name = ''.join(random.choice(string.ascii_lowercase) for i in range(8))
            if self.file_size == 0:
                touch(random_file_name)
            else:
                with open(random_file_name, "w") as wfd:
                    wfd.write(''.join(random.choice(string.ascii_lowercase+string.ascii_uppercase) for i in range(self.file_size)))
        if num_levels > 0:
            for i_dir in range(self.num_dirs_per_level):
                random_dir_name = ''.join(random.choice(string.ascii_uppercase) for i in range(8))
                os.makedirs(random_dir_name, mode=0o777, exist_ok=False)
                save_cwd = os.getcwd()
                os.chdir(random_dir_name)
                self.make_random_dirs_recursive(num_levels-1)
                os.chdir(save_cwd)

    def __call__(self, *args, **kwargs):
        self.make_random_dirs_recursive(self.num_levels)


class MakeDirs(PythonBatchCommandBase):
    """ Create one or more dirs
        when remove_obstacles==True if one of the paths is a file it will be removed
        when remove_obstacles==False if one of the paths is a file 'FileExistsError: [Errno 17] File exists' will raise
        it it always OK for a dir to already exists
        Tests: TestPythonBatch.test_MakeDirs_*
    """
    def __init__(self, *paths_to_make, remove_obstacles: bool=True) -> None:
        super().__init__()
        self.paths_to_make = paths_to_make
        self.remove_obstacles = remove_obstacles
        self.cur_path = None

    def __repr__(self):
        paths_csl = ", ".join(utils.raw_string(utils.quoteme_double(os.fspath(path))) for path in self.paths_to_make)
        the_repr = f"""{self.__class__.__name__}({paths_csl}, remove_obstacles={self.remove_obstacles})"""
        return the_repr

    def repr_batch_win(self):
        retVal = list()
        for directory in self.paths_to_make:
            norm_directory = os.path.normpath(directory)
            quoted_norm_directory = utils.quoteme_double(norm_directory)
            quoted_norm_directory_slash = utils.quoteme_double(norm_directory+"\\")
            mk_command = " ".join(("if not exist", quoted_norm_directory, "mkdir", quoted_norm_directory))
            check_mk_command = " ".join(("if not exist", quoted_norm_directory_slash, "(", "echo Error: failed to create ", quoted_norm_directory, "1>&2",
                                        "&", "GOTO", "EXIT_ON_ERROR", ")"))
            retVal.append(mk_command)
            retVal.append(check_mk_command)
        return retVal

    def repr_batch_mac(self):
        retVal = list()
        for directory in self.paths_to_make:
            mk_command = " ".join(("mkdir", "-p", "-m a+rwx", utils.quoteme_double(directory) ))
            retVal.append(mk_command)
        return retVal

    def progress_msg_self(self):
        the_progress_msg = f"mkdir {self.paths_to_make}"
        return the_progress_msg

    def __call__(self, *args, **kwargs):
        retVal = 0
        for self.cur_path in self.paths_to_make:
            if self.remove_obstacles:
                if os.path.isfile(self.cur_path):
                    os.unlink(self.cur_path)
            os.makedirs(self.cur_path, mode=0o777, exist_ok=True)
            retVal += 1
        return retVal

    def error_msg_self(self):
        return f"creating {self.cur_path}"


class Touch(PythonBatchCommandBase):
    def __init__(self, path: os.PathLike) -> None:
        super().__init__()
        self.path = path

    def __repr__(self):
        the_repr = f"""{self.__class__.__name__}(path=r"{os.fspath(self.path)}")"""
        return the_repr

    def repr_batch_win(self):
        retVal = list()
        touch_command = " ".join(("type", "NUL", ">", utils.quoteme_double(self.path)))
        retVal.append(touch_command)
        return retVal

    def repr_batch_mac(self):
        retVal = list()
        touch_command = " ".join(("touch", utils.quoteme_double(self.path)))
        retVal.append(touch_command)
        return retVal

    def progress_msg_self(self):
        the_progress_msg = f"Touch {self.path}"
        return the_progress_msg

    def __call__(self, *args, **kwargs):
        with open(self.path, 'a'):
            os.utime(self.path, None)


class Cd(PythonBatchCommandBase):
    def __init__(self, path: os.PathLike) -> None:
        super().__init__()
        self.new_path: os.PathLike = path
        self.old_path: os.PathLike = None

    def __repr__(self):
        the_repr = f"""{self.__class__.__name__}(path=r"{os.fspath(self.new_path)}")"""
        return the_repr

    def repr_batch_win(self):
        retVal = list()
        norm_directory = utils.quoteme_double(os.path.normpath(self.new_path))
        is_exists_command = " ".join(("if not exist", norm_directory,
                                    "(", "echo directory does not exists", norm_directory, "1>&2",
                                    "&", "GOTO", "EXIT_ON_ERROR", ")"))
        cd_command = " ".join(("cd", '/d', norm_directory))
        check_cd_command = " ".join(("if /I not", norm_directory, "==", utils.quoteme_double("%CD%"),
                                    "(", "echo Error: failed to cd to", norm_directory, "1>&2",
                                    "&", "GOTO", "EXIT_ON_ERROR", ")"))
        retVal.extend((is_exists_command, cd_command, check_cd_command))
        return retVal

    def repr_batch_mac(self):
        retVal = list()
        retVal.append(" ".join(("cd", utils.quoteme_double(self.new_path))))
        return retVal

    def progress_msg_self(self):
        the_progress_msg = f"cd to {self.new_path}"
        return the_progress_msg

    def __call__(self, *args, **kwargs):
        self.old_path = os.getcwd()
        os.chdir(self.new_path)
        return None

    def exit_self(self, exit_return):
        os.chdir(self.old_path)


class ChFlags(RunProcessBase):
    """ Mac specific to change system flags on files or dirs.
        These flags are different from permissions.
        For changing permissions use chmod.
    """
    def __init__(self, path, flag: str, recursive=False, ignore_errors=True) -> None:
        super().__init__(ignore_all_errors=ignore_errors)
        self.flags_dict = {'darwin': {'hidden': 'hidden', 'nohidden': 'nohidden', 'locked': 'uchg', 'unlocked': 'nouchg'},
                           'win32': {'hidden': '+H', 'nohidden': '-H', 'locked': '+R', 'unlocked': '-R'}}
        self.path = path
        self.flag = flag
        self.recursive = recursive
        self.ignore_errors = ignore_errors

    def __repr__(self):
        the_repr = f"""{self.__class__.__name__}(path=r"{os.fspath(self.path)}", flag="{self.flag}", recursive={self.recursive}, ignore_errors={self.ignore_errors})"""
        return the_repr

    def repr_batch_win(self):
        retVal = list()
        return retVal

    def repr_batch_mac(self):
        retVal = list()
        chflags_parts = list()
        chflags_parts.append("chflags")
        if self.ignore_errors:
            chflags_parts.append("-f")
        if self.recursive:
            chflags_parts.append("-R")
        chflags_parts.append(self.flag)
        chflags_parts.append(utils.quoteme_double(self.path))
        retVal.append(" ".join(chflags_parts))
        return retVal

    def progress_msg_self(self):
        the_progress_msg = f"change flag {self.flag} on file {self.path}"
        return the_progress_msg

    def create_run_args(self):
        flag = self.flags_dict[sys.platform][self.flag]
        if sys.platform == 'darwin':
            return self._create_run_args_mac(flag)
        elif sys.platform == 'win32':
            return self._create_run_args_win(flag)

    def _create_run_args_win(self, flag):
        run_args = list()
        run_args.append("attrib")
        if self.recursive:
            run_args.extend(('/S', '/D'))
        run_args.append(flag)
        run_args.append(self.path)
        return run_args

    def _create_run_args_mac(self, flag):
        run_args = list()
        run_args.append("chflags")
        if self.ignore_errors:
            run_args.append("-f")
        if self.recursive:
            run_args.append("-R")
        run_args.append(flag)
        run_args.append(self.path)
        return run_args


class Unlock(ChFlags):
    """
        Remove the system's read-only flag, this is different from permissions.
        For changing permissions use chmod.
    """
    def __init__(self, path, recursive=False, ignore_errors=True):
        super().__init__(path, "unlocked", recursive=recursive, ignore_errors=ignore_errors)

    def __repr__(self):
        the_repr = f"""{self.__class__.__name__}(path=r"{os.fspath(self.path)}", recursive={self.recursive}, ignore_errors={self.ignore_errors})"""
        return the_repr

    def repr_batch_win(self):
        retVal = list()
        recurse_flag = ""
        if self.recursive:
            recurse_flag = "/S /D"
        writable_command = " ".join(("$(ATTRIB_PATH)", "-R", recurse_flag, utils.quoteme_double(self.path)))
        retVal.append(writable_command)
        return retVal

    def repr_batch_mac(self):
        retVal = list()
        ignore_errors_flag = recurse_flag = ""
        if self.ignore_errors:
            ignore_errors_flag = "-f"
        if self.recursive:
            recurse_flag = "-R"
        nouchg_command = " ".join(("chflags", ignore_errors_flag, recurse_flag, "nouchg", utils.quoteme_double(self.path)))
        if self.ignore_errors: # -f is not enough in case the file does not exist, chflags will still exit with 1
            nouchg_command = " ".join((nouchg_command, "2>", "/dev/null", "||", "true"))
        retVal.append(nouchg_command)
        return retVal

    def progress_msg_self(self):
        the_progress_msg = f"unlocking file {self.path}"
        return the_progress_msg


class CopyBase(RunProcessBase):
    def __init__(self, src: os.PathLike, trg: os.PathLike, link_dest=False, ignore=None, preserve_dest_files=False, copy_file=False, copy_dir=False) -> None:
        super().__init__()
        self.src: os.PathLike = src
        self.trg: os.PathLike = trg
        self.link_dest = link_dest
        self.ignore = ignore
        self.preserve_dest_files = preserve_dest_files
        self.copy_file = copy_file
        self.copy_dir = copy_dir

    def __repr__(self):
        the_repr = f"""{self.__class__.__name__}(src=r"{self.src}", trg=r"{self.trg}", link_dest={self.link_dest}, ignore={self.ignore}, preserve_dest_files={self.preserve_dest_files})"""
        return the_repr

    def progress_msg_self(self):
        the_progress_msg = f"{self}"
        return the_progress_msg

    @abc.abstractmethod
    def create_run_args(self):
        raise NotImplemented()

    @abc.abstractmethod
    def create_ignore_spec(self, ignore: bool):
        raise NotImplemented()


class RsyncCopyBase(CopyBase):
    def __init__(self, src: os.PathLike, trg: os.PathLike, *args, **kwargs) -> None:
        if not os.fspath(trg).endswith("/"):
            trg = os.fspath(trg) + "/"
        super().__init__(src, trg, *args, **kwargs)

    def create_run_args(self):
        run_args = list()
        ignore_spec = self.create_ignore_spec(self.ignore)
        if not self.preserve_dest_files:
            delete_spec = "--delete"
        else:
            delete_spec = ""

        run_args.extend(["rsync", "--owner", "--group", "-l", "-r", "-E", "--hard-links", delete_spec, *ignore_spec])
        if self.link_dest:
            src_base, src_leaf = os.path.split(self.src)
            target_relative_to_source = os.path.relpath(src_base, self.trg)  # rsync expect --link-dest to be relative to target
            the_link_dest_arg = f'''--link-dest="{target_relative_to_source}"'''
            run_args.append(the_link_dest_arg)
        run_args.extend([self.src, self.trg])
        return run_args

    def create_ignore_spec(self, ignore: bool) -> None:
        retVal = []
        if self.ignore:
            if isinstance(self.ignore, str):
                self.ignore = (self.ignore,)
            retVal.extend(["--exclude=" + utils.quoteme_single(ignoree) for ignoree in self.ignore])
        return retVal


class RoboCopyBase(CopyBase):
    RETURN_CODES = {0:  '''
                            No errors occurred, and no copying was done.
                            The source and destination directory trees are completely synchronized.''',
                    1: '''One or more files were copied successfully (that is, new files have arrived).''',
                    2: '''
                            Some Extra files or directories were detected. No files were copied
                            Examine the output log for details.''',
                    # (2 + 1)
                    3: '''Some files were copied.Additional files were present.No failure was encountered.''',
                    4: '''
                            Some Mismatched files or directories were detected.
                            Examine the output log. Housekeeping might be required.''',
                    # (4 + 1)
                    5: '''Some files were copied. Some files were mismatched. No failure was encountered.''',
                    # (4 + 2)
                    6: '''
                            Additional files and mismatched files exist. No files were copied and no failures were encountered.
                            This means that the files already exist in the destination directory''',
                    # (4 + 1 + 2)
                    7: '''Files were copied, a file mismatch was present, and additional files were present.''',

                    # Any value greater than 7 indicates that there was at least one failure during the copy operation.
                    8: '''
                            Some files or directories could not be copied
                            (copy errors occurred and the retry limit was exceeded).
                            Check these errors further.''',
                    16: '''
                            Serious error. Robocopy did not copy any files.
                            Either a usage error or an error due to insufficient access privileges
                            on the source or destination directories.'''}

    def __call__(self, *args, **kwargs):
        try:
            super().__call__(*args, **kwargs)
        except subprocess.CalledProcessError as e:
            if e.returncode > 7:
                raise e
            #     pass  # One or more files were copied successfully (that is, new files have arrived).
            # else:
            #     raise subprocess.SubprocessError(f'{self.RETURN_CODES[e.returncode]}') from e

    def create_run_args(self):
        run_args = ['robocopy', '/E', '/R:9', '/W:1', '/NS', '/NC', '/NFL', '/NDL', '/NP', '/NJS']
        if not self.preserve_dest_files:
            run_args.append('/purge')
        if self.copy_file:
            run_args.extend((os.path.dirname(self.src), self.trg, os.path.basename(self.src)))
        elif self.copy_dir:
            run_args.extend((self.src, os.path.join(self.trg, os.path.basename(self.src))))
        else:
            run_args.extend((self.src, self.trg))
        run_args.extend(self.create_ignore_spec(self.ignore))
        return run_args

    def create_ignore_spec(self, ignore: bool):
        try:
            ignore = [os.path.abspath(os.path.join(self.src, path)) for path in ignore]
        except TypeError:
            retVal = []
        else:
            retVal = ['/XF'] + ignore + ['/XD'] + ignore
        return retVal


if sys.platform == 'darwin':
    CopyClass = RsyncCopyBase
elif sys.platform == 'win32':
    CopyClass = RoboCopyBase


class CopyDirToDir(CopyClass):
    def __init__(self, src: os.PathLike, trg: os.PathLike, link_dest=False, ignore=None, preserve_dest_files=False) -> None:
        src = os.fspath(src).rstrip("/")
        super().__init__(src=src, trg=trg, link_dest=link_dest, ignore=ignore, preserve_dest_files=preserve_dest_files, copy_dir=True)

    def repr_batch_win(self):
        retVal = list()
        _, dir_to_copy = os.path.split(self.src)
        self.trg = "/".join((self.trg, dir_to_copy))
        ignore_spec = self._create_ignore_spec_batch_win(self.ignore)
        norm_src_dir = os.path.normpath(self.src)
        norm_trg_dir = os.path.normpath(self.trg)
        if not self.preserve_dest_files:
            delete_spec = "/PURGE"
        else:
            delete_spec = ""
        copy_command = f""""$(ROBOCOPY_PATH)" "{norm_src_dir}" "{norm_trg_dir}" {ignore_spec} /E /R:9 /W:1 /NS /NC /NFL /NDL /NP /NJS {delete_spec}"""
        retVal.append(copy_command)
        retVal.append(self.platform_helper.exit_if_error(self.robocopy_error_threshold))
        return retVal

    def repr_batch_mac(self):
        if self.src.endswith("/"):
            self.src.rstrip("/")
        ignore_spec = self.create_ignore_spec(self.ignore)
        if not self.preserve_dest_files:
            delete_spec = "--delete"
        else:
            delete_spec = ""
        if self.link_dest:
            the_link_dest = os.path.join(self.src, "..")
            sync_command = f"""rsync --owner --group -l -r -E {delete_spec} {ignore_spec} --link-dest="{the_link_dest}" "{self.src}" "{self.trg}" """
        else:
            sync_command = f"""rsync --owner --group -l -r -E {delete_spec} {ignore_spec} "{self.src}" "{self.trg}" """

        return sync_command


class CopyDirContentsToDir(CopyClass):
    def __init__(self, src: os.PathLike, trg: os.PathLike, link_dest=False, ignore=None, preserve_dest_files=False) -> None:
        if not os.fspath(src).endswith("/"):
            src = os.fspath(src)+"/"
        super().__init__(src=src, trg=trg, link_dest=link_dest, ignore=ignore, preserve_dest_files=preserve_dest_files)

    def repr_batch_win(self):
        retVal = list()
        ignore_spec = self.create_ignore_spec(self.ignore)
        delete_spec = ""
        if not self.preserve_dest_files:
            delete_spec = "/PURGE"
        else:
            delete_spec = ""
        norm_src_dir = os.path.normpath(self.src)
        norm_trg_dir = os.path.normpath(self.trg)
        copy_command = f""""$(ROBOCOPY_PATH)" "{norm_src_dir}" "{norm_trg_dir}" /E {delete_spec} {ignore_spec} /R:9 /W:1 /NS /NC /NFL /NDL /NP /NJS"""
        retVal.append(copy_command)
        retVal.append(self.platform_helper.exit_if_error(self.robocopy_error_threshold))
        return retVal

    def repr_batch_mac(self):
        if not self.src.endswith("/"):
            self.src += "/"
        ignore_spec = self.create_ignore_spec(self.ignore)
        delete_spec = ""
        if not self.preserve_dest_files:
            delete_spec = "--delete"
        else:
            delete_spec = ""
        if self.link_dest:
            relative_link_dest = os.path.relpath(self.src, self.trg)
            sync_command = f"""rsync --owner --group -l -r -E {delete_spec} {ignore_spec} --link-dest="{relative_link_dest}" "{self.src}" "{self.trg}" """
        else:
            sync_command = f"""rsync --owner --group -l -r -E {delete_spec} {ignore_spec} "{self.src}" "{self.trg}" """

        return sync_command


class CopyFileToDir(CopyClass):
    def __init__(self, src: os.PathLike, trg: os.PathLike, link_dest=False, ignore=None, preserve_dest_files=False) -> None:
        src = os.fspath(src).rstrip("/")
        if not os.fspath(trg).endswith("/"):
            trg = os.fspath(trg)+"/"
        super().__init__(src=src, trg=trg, link_dest=link_dest, ignore=ignore, preserve_dest_files=preserve_dest_files, copy_file=True)

    def repr_batch_win(self):
        retVal = list()
        norm_src_dir, norm_src_file = os.path.split(os.path.normpath(self.src))
        norm_trg_dir = os.path.normpath(self.trg)
        copy_command = f""""$(ROBOCOPY_PATH)" "{norm_src_dir}" "{norm_trg_dir}" "{norm_src_file}" /R:9 /W:1 /NS /NC /NFL /NDL /NP /NJS"""
        retVal.append(copy_command)
        retVal.append(self.platform_helper.exit_if_error(self.robocopy_error_threshold))
        return retVal

    def repr_batch_mac(self):
        assert not self.src.endswith("/")
        if not self.trg.endswith("/"):
            self.trg += "/"
        ignore_spec = self.create_ignore_spec(self.ignore)
        permissions_spec = str(config_vars.get("RSYNC_PERM_OPTIONS", ""))
        if self.link_dest:
            the_link_dest, src_file_name = os.path.split(self.src)
            relative_link_dest = os.path.relpath(the_link_dest, self.trg)
            sync_command = f"""rsync --owner --group -l -r -E {ignore_spec} --link-dest="{relative_link_dest}" "{self.src}" "{self.trg}" """
        else:
            sync_command = f"""rsync --owner --group -l -r -E {ignore_spec} "{self.src}" "{self.trg}" """

        return sync_command


class CopyFileToFile(CopyClass):
    def __init__(self, src: os.PathLike, trg: os.PathLike, link_dest=False, ignore=None, preserve_dest_files=False) -> None:
        src = os.fspath(src).rstrip("/")
        trg = os.fspath(trg).rstrip("/")
        super().__init__(src=src, trg=trg, link_dest=link_dest, ignore=ignore, preserve_dest_files=preserve_dest_files, copy_file=True)

    def repr_batch_win(self):
        retVal = list()
        norm_src_file = os.path.normpath(self.src)
        norm_trg_file = os.path.normpath(self.trg)
        copy_command = f"""copy "{norm_src_file}" "{norm_trg_file}" """
        retVal.append(copy_command)
        retVal.append(self.platform_helper.exit_if_error())
        return retVal

    def repr_batch_mac(self):
        assert not self.src.endswith("/")
        ignore_spec = self.create_ignore_spec(self.ignore)
        if self.link_dest:
            src_folder_name, src_file_name = os.path.split(self.src)
            trg_folder_name, trg_file_name = os.path.split(self.trg)
            relative_link_dest = os.path.relpath(src_folder_name, trg_folder_name)
            sync_command = f"""rsync --owner --group -l -r -E {ignore_spec} --link-dest="{relative_link_dest}" "{self.src}" "{self.trg}" """
        else:
            sync_command = f"""rsync --owner --group -l -r -E {ignore_spec} "{self.src}" "{self.trg}" """

        return sync_command


class RmFile(PythonBatchCommandBase):
    def __init__(self, path: os.PathLike) -> None:
        """ remove a file
            - It's OK is the file does not exist
            - but exception will be raised if path is a folder
        """
        super().__init__()
        self.path: os.PathLike = path
        self.exceptions_to_ignore.append(FileNotFoundError)

    def __repr__(self):
        the_repr = f"""{self.__class__.__name__}(path=r"{os.fspath(self.path)}")"""
        return the_repr

    def repr_batch_win(self):
        retVal = list()
        rmfile_command_parts = list()
        norm_file = utils.quoteme(os.path.normpath(self.path), "'")
        rmfile_command_parts.extend(("if", "exist", norm_file))
        rmfile_command_parts.extend(("del", "/F", "/Q", norm_file))
        rmfile_command = " ".join(rmfile_command_parts)
        retVal.append(rmfile_command)
        return retVal

    def repr_batch_mac(self):
        retVal = list()
        rmfile_command_parts = list()
        norm_file = utils.quoteme(self.path, '"')
        rmfile_command_parts.extend(("[", "!", "-f", norm_file, "]", "||"))
        rmfile_command_parts.extend(("rm", "-f", norm_file))
        rmfile_command = " ".join(rmfile_command_parts)
        retVal.append(rmfile_command)
        return retVal

    def progress_msg_self(self):
        the_progress_msg = f"remove file {self.path}"
        return the_progress_msg

    def error_msg_self(self):
        if os.path.isdir(self.path):
            retVal = "cannot remove file that is actually a folder"
        else:
            retVal = ""
        return retVal

    def __call__(self, *args, **kwargs):
        os.remove(self.path)
        return None


class RmDir(PythonBatchCommandBase):
    def __init__(self, path: os.PathLike) -> None:
        """ remove a directory.
            - it's OK if the directory does not exist.
            - all files and directory under path will be removed recursively
            - exception will be raised if the path if a folder
        """
        super().__init__()
        self.path: os.PathLike = path
        self.exceptions_to_ignore.append(FileNotFoundError)

    def __repr__(self):
        the_repr = f"""{self.__class__.__name__}(path=r"{os.fspath(self.path)}")"""
        return the_repr

    def repr_batch_win(self):
        retVal = list()
        rmdir_command_parts = list()
        norm_directory = utils.quoteme_double(os.path.normpath(self.path))
        rmdir_command_parts.extend(("if", "exist", norm_directory))
        rmdir_command_parts.append("rmdir")
        rmdir_command_parts.extend(("/S", "/Q"))
        rmdir_command_parts.append(norm_directory)
        rmdir_command = " ".join(rmdir_command_parts)
        retVal.append(rmdir_command)
        return retVal

    def repr_batch_mac(self):
        retVal = list()
        rmdir_command_parts = list()
        norm_directory = utils.quoteme_double(self.path)
        rmdir_command_parts.extend(("[", "!", "-d", norm_directory, "]", "||"))
        rmdir_command_parts.extend(("rm", "-fr", norm_directory))
        rmdir_command = " ".join(rmdir_command_parts)
        retVal.append(rmdir_command)
        return retVal

    def progress_msg_self(self):
        the_progress_msg = f"remove file {self.path}"
        return the_progress_msg

    def __call__(self, *args, **kwargs):
        shutil.rmtree(self.path)
        return None


class RmFileOrDir(PythonBatchCommandBase):
    def __init__(self, path: os.PathLike):
        """ remove a file or directory.
            - it's OK if the path does not exist.
            - all files and directory under path will be removed recursively
        """
        super().__init__()
        self.path: os.PathLike = path
        self.exceptions_to_ignore.append(FileNotFoundError)

    def __repr__(self):
        the_repr = f"""{self.__class__.__name__}(path=r"{os.fspath(self.path)}")"""
        return the_repr

    def repr_batch_win(self):
        retVal = list()
        norm_path = utils.quoteme_double(os.path.normpath(self.path))
        rmdir_command = " ".join(("rmdir", '/S', '/Q', norm_path, '>nul', '2>&1'))
        rmfile_command = " ".join(("del", '/F', '/Q', norm_path, '>nul', '2>&1'))
        retVal.append(rmfile_command)
        retVal.append(rmfile_command)
        return retVal

    def repr_batch_mac(self):
        retVal = list()
        rmdir_command_parts = list()
        norm_directory = utils.quoteme_double(self.path)
        rmdir_command_parts.extend(("[", "!", "-d", norm_directory, "]", "||"))
        rmdir_command_parts.extend(("rm", "-fr", norm_directory))
        rmdir_command = " ".join(rmdir_command_parts)
        retVal.append(rmdir_command)
        return retVal

    def progress_msg_self(self):
        the_progress_msg = f"remove file {self.path}"
        return the_progress_msg

    def __call__(self, *args, **kwargs):
        if os.path.isfile(self.path):
            os.remove(self.path)
        elif os.path.isdir(self.path):
            shutil.rmtree(self.path)
        return None


class AppendFileToFile(PythonBatchCommandBase):
    def __init__(self, source_file, target_file):
        super().__init__()
        self.source_file = source_file
        self.target_file = target_file

    def __repr__(self):
        the_repr = f"""{self.__class__.__name__}(source_file="{os.fspath(self.source_file)}", target_file="{os.fspath(self.target_file)}")"""
        return the_repr

    def repr_batch_win(self):
        retVal = list()
        append_command = " ".join(("type", utils.quoteme_double(self.source_file), ">>", utils.quoteme_double(self.target_file)))
        retVal.append(append_command)
        return retVal

    def repr_batch_mac(self):
        retVal = list()
        append_command = " ".join(("cat", utils.quoteme_double(self.source_file), ">>", utils.quoteme_double(self.target_file)))
        retVal.append(append_command)
        return retVal

    def progress_msg_self(self):
        the_progress_msg = f"appending {self.source_file} to {self.target_file}"
        return the_progress_msg

    def __call__(self, *args, **kwargs):
        with open(self.target_file, "a") as wfd:
            with open(self.source_file, "r") as rfd:
                wfd.write(rfd.read())
        return None


# === classes without tests (yet) ===
class Section(PythonBatchCommandBase):
    def __init__(self, name):
        super().__init__()
        self.name = name

    def __repr__(self):
        the_repr = f"""{self.__class__.__name__}(name="{self.name}")"""
        return the_repr

    def repr_batch_win(self):
        retVal = list()
        retVal.append(f"""echo section: {self.name}""")
        return retVal

    def repr_batch_mac(self):
        retVal = list()
        retVal.append(f"""echo section: {self.name}""")
        return retVal

    def progress_msg_self(self):
        the_progress_msg = f"{self.name} ..."
        return the_progress_msg

    def __call__(self, *args, **kwargs):
        pass


class Chown(RunProcessBase):
    def __init__(self, user_id: int, group_id: int, path: os.PathLike, recursive: bool=False):
        super().__init__()
        self.user_id = user_id
        self.group_id = group_id
        self.path = path
        self.recursive = recursive
        self.exceptions_to_ignore.append(FileNotFoundError)

    def __repr__(self):
        the_repr = f"""{self.__class__.__name__}(user_id={self.user_id}, group_id={self.group_id}, path="{os.fspath(self.path)}", recursive={self.recursive})"""
        return the_repr

    def repr_batch_win(self):
        retVal = list()
        retVal.append(f"""chown not implemented yet for Windows, {self.path}""")
        return retVal

    def repr_batch_mac(self):
        retVal = list()
        chown_command_parts = list()
        chown_command_parts.append("chown")
        chown_command_parts.append("-f")
        if self.recursive:
            chown_command_parts.append("-R")
        chown_command_parts.append("".join((self.user_id, ":", self.group_id)))
        chown_command_parts.append(utils.quoteme_double(self.path))
        chown_command = " ".join(chown_command_parts)
        retVal.append(chown_command)
        return retVal

    def create_run_args(self):
        run_args = list()
        run_args.append("chown")
        run_args.append("-f")
        if self.recursive:
            run_args.append("-R")
        run_args.append("".join((self.user_id, ":", self.group_id)))
        run_args.append(utils.quoteme_double(self.path))
        return run_args

    def progress_msg_self(self):
        the_progress_msg = f"Change owner {self.path}"
        return the_progress_msg

    def __call__(self, *args, **kwargs):
        # os.chown is not recursive so call the system's chown
        if self.recursive:
            return super().__call__(args, kwargs)
        else:
            os.chown(self.path, uid=self.user_id, gid=self.group_id)
            return None


class Dummy(PythonBatchCommandBase):
    def __init__(self, name):
        super().__init__()
        self.name = name

    def __repr__(self):
        the_repr = f"""{self.__class__.__name__}(name="{self.name}")"""
        return the_repr

    def repr_batch_win(self):
        retVal = list()
        retVal.append(f"""Just a dummy called {self.name} for win""")
        return retVal

    def repr_batch_mac(self):
        retVal = list()
        retVal.append(f"""Just a dummy called {self.name} for mac""")
        return retVal

    def progress_msg_self(self):
        the_progress_msg = f"Dummy {self.name} ..."
        return the_progress_msg

    def enter_self(self):
        print(f"Dummy __enter__ {self.name}")

    def exit_self(self, exit_return):
        print(f"Dummy __exit__ {self.name}")

    def __call__(self, *args, **kwargs):
        print(f"Dummy __call__ {self.name}")


class Chmod(RunProcessBase):
    all_read = stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH
    all_exec = stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
    all_read_write = all_read | stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH
    all_read_write_exec = all_read_write | all_exec
    user_read_write_exec = stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR
    all_read_exec = all_read | all_exec
    who_2_perm = {'u': {'r': stat.S_IRUSR, 'w': stat.S_IWUSR, 'x': stat.S_IXUSR},
                  'g': {'r': stat.S_IRGRP, 'w': stat.S_IWGRP, 'x': stat.S_IXGRP},
                  'o': {'r': stat.S_IROTH, 'w': stat.S_IWOTH, 'x': stat.S_IXOTH}}

    def __init__(self, path, mode, recursive: bool=False, **kwargs):
        super().__init__(**kwargs)
        self.path = path
        self.mode = mode
        self.recursive = recursive

    def __repr__(self):
        the_mode = self.mode
        if isinstance(the_mode, str):
            the_mode = utils.quoteme_double(the_mode)
        the_repr = f"""{self.__class__.__name__}(path=r"{os.fspath(self.path)}", mode={the_mode}, recursive={self.recursive}"""
        if self.ignore_all_errors:
            the_repr += f"ignore_all_errors={self.ignore_all_errors})"
        else:
            the_repr += ")"
        return the_repr

    def repr_batch_win(self):
        retVal = list()
        chmod_parts = list()
        chmod_parts.append('attrib')
        if self.recursive:
            chmod_parts.append('/s')
        chmod_parts.append(utils.quoteme_double(self.path))
        retVal.append(" ".join(chmod_parts))
        return retVal

    def repr_batch_mac(self):
        retVal = list()
        chmod_parts = list()
        chmod_parts.append("chmod")
        if self.ignore_all_errors:
            chmod_parts.append("-f")
        if self.recursive:
            chmod_parts.append("-R")
        chmod_parts.append(self.mode)
        chmod_parts.append(utils.quoteme_double(self.path))
        retVal.append(" ".join(chmod_parts))
        return retVal

    def progress_msg_self(self):
        the_progress_msg = f"Change mode {self.path}"
        return the_progress_msg

    def parse_symbolic_mode(self, symbolic_mode_str):
        """ parse chmod symbolic mode string e.g. uo+xw
            return the mode as a number (e.g 766) and the operation (e.g. =|+|-)
        """
        flags = 0
        symbolic_mode_re = re.compile("""^(?P<who>[augo]+)(?P<op>\+|-|=)(?P<perm>[rwx]+)$""")
        match = symbolic_mode_re.match(symbolic_mode_str)
        if not match:
            raise ValueError(f"invalid symbolic mode for chmod: {symbolic_mode_str}")
        who = match.group('who')
        if 'a' in who:
            who = 'ugo'
        perm = match.group('perm')
        for w in who:
            for p in perm:
                flags |= Chmod.who_2_perm[w][p]
        return flags, match.group('op')

    def create_run_args(self):
        run_args = list()
        if sys.platform == 'darwin':
            run_args.append("chmod")
            if self.ignore_all_errors:
                run_args.append("-f")
            if self.recursive:
                run_args.append("-R")
            run_args.append(self.mode)
        elif sys.platform == 'win32':
            run_args.append('attrib')
            if self.recursive:
                run_args.append('/s')
        run_args.append(self.path)
        return run_args

    def __call__(self, *args, **kwargs):
        # os.chmod is not recursive so call the system's chmod
        if self.recursive:
            return super().__call__(args, kwargs)
        else:
            flags, op = self.parse_symbolic_mode(self.mode)
            mode_to_set = flags
            if op == '+':
                current_mode = stat.S_IMODE(os.stat(self.path)[stat.ST_MODE])
                mode_to_set |= current_mode
            elif op == '-':
                current_mode = stat.S_IMODE(os.stat(self.path)[stat.ST_MODE])
                mode_to_set = current_mode & ~flags

            os.chmod(self.path, mode_to_set)
        return None


class ShellCommands(RunProcessBase):
    def __init__(self, dir, shell_commands_var_name, shell_commands_list=None, **kwargs):
        kwargs["shell"] = True
        super().__init__(**kwargs)
        self.dir = dir
        self.var_name = shell_commands_var_name
        self.shell_commands_list = shell_commands_list

    def __repr__(self):
        the_repr = f"""{self.__class__.__name__}(dir="{self.dir}", shell_commands_var_name="{self.var_name}", shell_commands_list={self.var_name})"""
        return the_repr

    def repr_batch_win(self):
        return self.shell_commands_list

    def repr_batch_mac(self):
        return self.shell_commands_list

    def progress_msg_self(self):
        prog_mess = ""
        return prog_mess

    def create_run_args(self):
        the_lines = self.shell_commands_list
        if isinstance(the_lines, str):
            the_lines = [the_lines]
        if sys.platform == 'darwin':
            the_lines.insert(0,  "#!/usr/bin/env bash")
            batch_extension = ".command"
        elif sys.platform == "win32":
            batch_extension = ".bat"
        commands_text = "\n".join(the_lines)
        batch_file_path = pathlib.Path(self.dir, self.var_name + batch_extension)
        with open(batch_file_path, "w") as batch_file:
            batch_file.write(commands_text)
        os.chmod(batch_file.name, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)

        run_args = list()
        run_args.append(batch_file.name)
        return run_args


class VarAssign(PythonBatchCommandBase):
    def __init__(self, var_name: str, var_value: Any):
        super().__init__(is_context_manager=False)
        self.var_name = var_name
        self.var_value = var_value

    def __repr__(self):
        the_repr = f'{self.var_name} = {repr(self.var_value)}\n'
        return the_repr

    def repr_batch_mac(self):
        quoter = '"'
        if '"' in self.var_value:
            quoter = "'"
            if "'" in self.var_value:
                print(self.var_value, """has both ' and " quote chars;""", "identifier:", self.var_name)
                return ()

        retVal = "".join((self.var_name, '=', quoter, self.var_value, quoter))
        return retVal

    def repr_batch_win(self):
        retVal = "SET " + self.var_name + '=' + dos_escape(self.var_value)
        return retVal

    def progress_msg_self(self):
        return ""

    def __call__(self, *args, **kwargs):
        pass

# todo:
# override PythonBatchCommandBase for all commands
# windows!
# check and map errors: for each command find which errors can be returned, which exception they raise, which can be ignored. Map all errors to a number and message.
# check and map errors: for RunProcess special handling of exception subprocess.CalledProcessError
# capture subprocess.run output
# intro code
# configVars?
# comments ?
# echos - most will automatically produced by the commands
# total progress calculation
# accumulator transactions
# handle completed_process
# tests: for each test add a test to verify failure is handled correctly
# time measurements
# InstlAdmin