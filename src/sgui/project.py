import os

from sgui import util
from sglib.constants import (
    DEFAULT_PROJECT_DIR,
    IS_PORTABLE_INSTALL,
    MAJOR_VERSION,
)
from sglib.lib import portable
from sglib.lib.translate import _
from sglib.lib.util import (
    pi_path,
    META_DOT_JSON,
    PROJECT_FILE_TYPE,
    get_file_setting,
    set_file_setting,
    read_file_text,
    write_file_text,
)
from sglib.log import LOG
from sgui.sgqt import *
import shutil

__all__ = [
    'new_project',
    'open_project',
    'set_project',
    'get_history',
]

PROJECT_DIR = None

def new_project_dialog(parent, last_dir):
    f_file, _filter = QFileDialog.getSaveFileName(
        parent,
        _('Create a new project'),
        last_dir,
        options=(
            QFileDialog.Option.ShowDirsOnly
            |
            QFileDialog.Option.DontUseNativeDialog
        ),
    )
    return f_file, _filter

def new_project(a_parent=None):
    try:
        f_last_dir = DEFAULT_PROJECT_DIR
        while True:
            f_file, _filter = new_project_dialog(a_parent, f_last_dir)
            if f_file and str(f_file):
                f_file = str(f_file)
                f_last_dir = f_file
                if os.path.exists(f_file):
                    QMessageBox.warning(
                        a_parent,
                        "Error",
                        f"{f_file} already exists"
                    )
                    continue
                os.makedirs(f_file)
                f_file = os.path.join(
                    f_file,
                    f"{MAJOR_VERSION}.project",
                )
                set_project(f_file)
                return f_file
            else:
                return None
    except Exception as ex:
        LOG.exception(ex)
        QMessageBox.warning(a_parent, "Error", str(ex))
        return None

def clone_project(parent):
    try:
        clone, _ = open_project_dialog(parent)
    except StargateProjectVersionError:
        return False
    if not clone:
        return False
    new, _ = new_project_dialog(parent, DEFAULT_PROJECT_DIR)
    if not new:
        return False
    clone_dir = os.path.dirname(clone)
    shutil.copytree(clone_dir, new)
    set_project(
        os.path.join(new, f"{MAJOR_VERSION}.project"),
    )
    return True

def open_project_dialog(parent):
    f_file, f_filter = QFileDialog.getOpenFileName(
        parent=parent,
        caption='Open Project',
        directory=DEFAULT_PROJECT_DIR,
        filter=PROJECT_FILE_TYPE,
        options=QFileDialog.Option.DontUseNativeDialog,
    )
    if f_file:
        check_project_version(parent, f_file)
    return f_file, f_filter

def open_project(a_parent=None):
    try:
        f_file, f_filter = open_project_dialog(a_parent)
        if f_file is None:
            return False
        f_file_str = str(f_file)
        if not f_file_str:
            return False
        if not util.check_for_rw_perms(f_file):
            return False
        #global_open_project(f_file_str)
        set_project(f_file_str)
        return True
    except StargateProjectVersionError:
        return False
    except Exception as ex:
        LOG.exception(ex)
        QMessageBox.warning(a_parent, "Error", str(ex))
        return False

def set_project(project):
    global PROJECT_DIR
    project = pi_path(project)
    PROJECT_DIR = project
    set_file_setting("last-project", str(project))
    history = [pi_path(x) for x in get_history() if pi_path(x) != project]
    if IS_PORTABLE_INSTALL:
        project = portable.escape_path(project)
        history = [
            portable.escape_path(x)
            for x in history
        ]
    history.insert(0, project)
    util.set_file_setting(
        "project-history",
        "\n".join(history[:20]),
    )

def get_history():
    history = get_file_setting("project-history", str, "")
    if IS_PORTABLE_INSTALL:
        history = [
            portable.unescape_path(x)
            for x in history.split("\n")
            if x.strip()
        ]
        history = [
            x for x in history
            if os.path.exists(x)
        ]
    else:
        history = [
            x for x in history.split("\n")
            if (
                x.strip()
                and
                os.path.exists(x)
            )
        ]
    return history

class StargateProjectVersionError(Exception):
    """ Raised when the project has been opened in a newer version
        of Stargate than the version being run
    """

def check_project_version(parent, project_file):
    minor_version = META_DOT_JSON['version']['minor']
    project_version = read_file_text(project_file).strip()
    if (
        "placeholder" in project_version
        or
        minor_version > project_version
    ):
        write_file_text(project_file, minor_version)
    elif minor_version == project_version:
        pass
    else:
        msg = _(
            "Please update to the latest version of Stargate.  "
            "This project {} was last edited with version '{}', however, "
            "you are using version '{}'"
        ).format(
            project_file,
            project_version,
            minor_version,
        )
        LOG.error(msg)
        QMessageBox.warning(
            parent,
            _("Error"),
            msg,
        )
        raise StargateProjectVersionError

