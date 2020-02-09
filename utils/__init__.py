from .files import *
from .misc_utils import *
from .str_utils import *
from .searchPaths import SearchPaths
from .parallel_run import run_processes_in_parallel, run_process
from .multi_file import MultiFileReader
from .extract_info import extract_binary_info, check_binaries_versions_in_folder, check_binaries_versions_filter_with_ignore_regexes, get_info_from_plugin
from .ls import disk_item_listing, single_disk_item_listing
from .log_utils import *
import platform
current_os = platform.system()
if current_os == 'Darwin':
    from .dockutil import dock_util
from .redisClient import RedisClient
from .email_utils import send_email, send_email_from_template_file
