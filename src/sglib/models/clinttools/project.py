from .audio_pool import (
    AudioPool,
    AudioPoolEntry,
)
from .sample_graph import (
    clear_sample_graph_cache,
    remove_item_from_sg_cache,
    SampleGraph,
)
from sglib import constants
from sglib.lib import *
from sglib.lib.util import *
from sglib.constants import MAJOR_VERSION
from sglib.models.project.abstract import AbstractProject
from sglib.log import LOG
import collections
import datetime
import glob
import json
import os
import shutil
import tarfile
import tempfile


folder_audio_root = 'audio'
folder_audio = os.path.join("audio", "files")
folder_audio_rec = os.path.join("audio", "rec")
folder_samplegraph = os.path.join("audio", "samplegraph")
folder_samples = os.path.join("audio", "samples")
folder_timestretch = os.path.join("audio", "timestretch")
folder_glued = os.path.join("audio", "glued")
folder_user = "user"
folder_backups = "backups"
folder_projects = "projects"
folder_plugins = os.path.join("projects", "plugins")
file_plugin_uid = os.path.join("projects", "plugin_uid.txt")
FILE_AUDIO_POOL = os.path.join("audio", "audio_pool")
file_pystretch = os.path.join("audio", "stretch.txt")
file_pystretch_map = os.path.join("audio", "stretch_map.txt")
file_backups = "backups.json"


class SgProject(AbstractProject):
    def __init__(self):
        self.cached_audio_files = []
        self.glued_name_index = 0

    def set_project_folders(self, a_project_file):
        #folders
        self.project_folder = os.path.dirname(a_project_file)
        self.project_file = os.path.splitext(
            os.path.basename(a_project_file))[0]

        self.audio_root_folder = pi_path(
            os.path.join(
                self.project_folder,
                folder_audio_root,
            ),
        )
        self.audio_folder = os.path.join(
            self.project_folder,
            folder_audio,
        )
        self.audio_rec_folder = os.path.join(
            self.project_folder, folder_audio_rec)
        self.audio_tmp_folder = os.path.join(
            self.project_folder, folder_audio, "tmp")
        self.samplegraph_folder = os.path.join(
            self.project_folder, folder_samplegraph)
        self.timestretch_folder = os.path.join(
            self.project_folder, folder_timestretch)
        self.glued_folder = os.path.join(
            self.project_folder, folder_glued)
        self.user_folder = os.path.join(
            self.project_folder, folder_user)
        self.backups_folder = os.path.join(
            self.project_folder, folder_backups)
        self.samples_folder = os.path.join(
            self.project_folder, folder_samples)
        self.backups_file = os.path.join(
            self.project_folder, file_backups)
        self.plugin_pool_folder = os.path.join(
            self.project_folder, folder_plugins)
        self.projects_folder = os.path.join(
            self.project_folder, folder_projects)
        self.plugin_uid_file = os.path.join(
            self.project_folder, file_plugin_uid)
        self.audio_pool_file = os.path.join(
            self.project_folder, FILE_AUDIO_POOL)
        self.pystretch_file = os.path.join(
            self.project_folder, file_pystretch)
        self.pystretch_map_file = os.path.join(
            self.project_folder, file_pystretch_map)

        self.project_folders = [
            self.audio_root_folder,
            self.audio_folder,
            self.audio_rec_folder,
            self.audio_tmp_folder,
            self.backups_folder,
            self.glued_folder,
            self.plugin_pool_folder,
            self.projects_folder,
            self.samplegraph_folder,
            self.samples_folder,
            self.timestretch_folder,
            self.user_folder,
        ]

        clear_sample_graph_cache()

    def open_project(self, a_project_file, a_notify_osc=True):
        self.set_project_folders(a_project_file)
        if not os.path.exists(a_project_file):
            LOG.info(
                f"project file {a_project_file} does not exist, creating as "
                "new project"
            )
            self.new_project(a_project_file)
        else:
            self.open_stretch_dicts()
        self.quirks(a_project_file)

    def quirks(self, project_file):
        """ Make modifications to the project folder format as needed, to
            bring old projects up to date on format changes
        """
        # TODO Stargate v2: Remove all existing quirks
        self._quirk_windows_audio_pool_corruption(project_file)

    def _quirk_windows_audio_pool_corruption(self, project_file):
        """ Github issue #39
            On Windows, dragging files from the project audio folder corrupts
            the audio pool
        """
        changed = False
        project_dir = os.path.dirname(project_file)
        def full_path(path):
            _path = os.path.join(
                project_dir,
                'audio',
                'samples',
                path,
            )
            return _path
        pool = self.get_audio_pool()
        for entry in pool.pool:
            if entry.path.startswith('/:'):
                _full = full_path(entry.path[1:])
                if os.path.exists(_full):
                    continue
                new_path = entry.path[0] + entry.path[2:]
                _full = full_path(new_path[1:])
                if os.path.exists(_full):
                    LOG.info(
                        'Fixing corrupt audio pool entry: '
                        f'{entry.path} -> {new_path}'
                    )
                    entry.path = new_path
                    changed = True
                else:
                    LOG.warning(
                        f'Corrupt audio pool, {new_path} does not exist'
                    )
        if changed:
            LOG.info('Saving repaired audio pool')
            self.save_audio_pool(pool)


    def new_project(self, a_project_file, a_notify_osc=True):
        self.set_project_folders(a_project_file)

        for project_dir in self.project_folders:
            LOG.info(project_dir)
            if not os.path.isdir(project_dir):
                os.makedirs(project_dir)

        minor_version = META_DOT_JSON['version']['minor']
        self.create_file(
            "",
            os.path.basename(a_project_file),
            minor_version,
        )
        self.create_file("", FILE_AUDIO_POOL, terminating_char)
        self.create_file("", file_pystretch_map, terminating_char)
        self.create_file("", file_pystretch, terminating_char)

        self.open_stretch_dicts()
        #self.commit("Created project")

    def get_next_plugin_uid(self):
        if os.path.isfile(self.plugin_uid_file):
            content = read_file_text(self.plugin_uid_file)
            f_result = int(content)
            f_result += 1
            write_file_text(self.plugin_uid_file, f_result)
            assert(f_result < 100000)
            return f_result
        else:
            write_file_text(self.plugin_uid_file, str(0))
            return 0

    def clear_audio_tmp_folder(self):
        pattern = os.path.join(self.audio_tmp_folder, '*')
        for path in glob.glob(pattern):
            os.remove(path)

    def create_backup(self, a_name=None):
        name = datetime.datetime.now().strftime(
            f"%Y-%m-%d_%H-%M-%S-{a_name}.tar.bz2"
        )
        path = os.path.join(self.backups_folder, name)
        if os.path.exists(path):
            LOG.error(f"create_backup: '{path}' exists, not creating")
            return False
        with tarfile.open(path, "w:bz2") as f_tar:
            f_tar.add(
                self.projects_folder,
                arcname=os.path.basename(self.projects_folder),
            )
        LOG.info(f'Created backup at {path}')
        return True

    def get_next_glued_file_name(self):
        while True:
            self.glued_name_index += 1
            f_path = os.path.join(
                self.glued_folder,
                "glued-{}.wav".format(self.glued_name_index))
            if not os.path.isfile(f_path):
                break
        return f_path

    def open_stretch_dicts(self):
        self.timestretch_cache = {}
        self.timestretch_reverse_lookup = {}

        f_cache_text = read_file_text(self.pystretch_file)
        for f_line in f_cache_text.split("\n"):
            if f_line == terminating_char:
                break
            f_line_arr = f_line.split("|", 5)
            f_file_path_and_uid = f_line_arr[5].split("|||")
            self.timestretch_cache[
                (int(f_line_arr[0]), float(f_line_arr[1]),
                float(f_line_arr[2]), float(f_line_arr[3]),
                float(f_line_arr[4]),
                f_file_path_and_uid[0])] = int(f_file_path_and_uid[1])

        f_map_text = read_file_text(self.pystretch_map_file)
        for f_line in f_map_text.split("\n"):
            if f_line == terminating_char:
                break
            f_line_arr = f_line.split("|||")
            src = util.pi_path(f_line_arr[0])
            dst = util.pi_path(f_line_arr[1])
            self.timestretch_reverse_lookup[src] = dst

    def save_stretch_dicts(self):
        f_stretch_text = ""
        for k, v in list(self.timestretch_cache.items()):
            for f_tuple_val in k:
                f_stretch_text += "{}|".format(f_tuple_val)
            f_stretch_text += "||{}\n".format(v)
        f_stretch_text += terminating_char
        self.save_file("", file_pystretch, f_stretch_text)

        f_map_text = ""
        for k, v in list(self.timestretch_reverse_lookup.items()):
            f_map_text += "{}|||{}\n".format(k, v)
        f_map_text += terminating_char
        self.save_file("", file_pystretch_map, f_map_text)

    def get_audio_pool(self):
        if not os.path.exists(self.audio_pool_file):
            return AudioPool.new()
        content = read_file_text(self.audio_pool_file)
        return AudioPool.from_str(content)

    def save_audio_pool(self, a_uid_dict):
        write_file_text(self.audio_pool_file, a_uid_dict)

    def timestretch_lookup_orig_path(self, a_path):
        if a_path in self.timestretch_reverse_lookup:
            return self.timestretch_reverse_lookup[a_path]
        else:
            return a_path

    def timestretch_audio_item(self, a_audio_item):
        """ Return path, uid for a time-stretched
            audio item and update all project files,
            or None if the UID already exists in the cache
        """
        a_audio_item.timestretch_amt = round(
            a_audio_item.timestretch_amt, 6)
        a_audio_item.pitch_shift = round(a_audio_item.pitch_shift, 6)
        a_audio_item.timestretch_amt_end = round(
            a_audio_item.timestretch_amt_end, 6)
        a_audio_item.pitch_shift_end = round(a_audio_item.pitch_shift_end, 6)

        f_src_path = self.get_wav_name_by_uid(a_audio_item.uid)

        if f_src_path in self.timestretch_reverse_lookup:
            LOG.info(
                f'Replacing {f_src_path} with '
                f'{self.timestretch_reverse_lookup[f_src_path]}'
            )
            f_src_path = self.timestretch_reverse_lookup[f_src_path]
        else:
            if (
                a_audio_item.timestretch_amt == 1.0
                and
                a_audio_item.pitch_shift == 0.0
                and
                a_audio_item.timestretch_amt_end == 1.0
                and
                a_audio_item.pitch_shift_end == 0.0
            ) or (
                a_audio_item.time_stretch_mode == 1
                and
                a_audio_item.pitch_shift == a_audio_item.pitch_shift_end
            ) or (
                a_audio_item.time_stretch_mode == 2
                and
                a_audio_item.timestretch_amt ==
                    a_audio_item.timestretch_amt_end
            ):
                #Don't process if the file is not being stretched/shifted yet
                return
        f_key = (
            a_audio_item.time_stretch_mode,
            a_audio_item.timestretch_amt,
            a_audio_item.pitch_shift,
            a_audio_item.timestretch_amt_end,
            a_audio_item.pitch_shift_end,
            a_audio_item.crispness,
            f_src_path,
        )
        if f_key in self.timestretch_cache:
            a_audio_item.uid = self.timestretch_cache[f_key]
            return
        else:
            f_wavs_dict = self.get_audio_pool()
            f_uid = f_wavs_dict.next_uid()
            f_dest_path = os.path.join(
                self.timestretch_folder,
                f"{f_uid}.wav",
            )
            f_dest_path = util.pi_path(f_dest_path)

            f_cmd = None
            if a_audio_item.time_stretch_mode == 1:
                constants.IPC.pitch_env(
                    f_src_path,
                    f_dest_path,
                    a_audio_item.pitch_shift,
                    a_audio_item.pitch_shift_end,
                )
                f_wavs_dict.add_entry(f_dest_path, uid=f_uid)
                self.save_audio_pool(f_wavs_dict)
            elif a_audio_item.time_stretch_mode == 2:
                constants.IPC.rate_env(
                    f_src_path,
                    f_dest_path,
                    a_audio_item.timestretch_amt,
                    a_audio_item.timestretch_amt_end,
                )
                f_wavs_dict.add_entry(f_dest_path, uid=f_uid)
                self.save_audio_pool(f_wavs_dict)
            elif a_audio_item.time_stretch_mode == 3:
                f_cmd = [
                    RUBBERBAND_PATH,
                    "-c", str(a_audio_item.crispness),
                    "-t", str(a_audio_item.timestretch_amt),
                    "-p", str(a_audio_item.pitch_shift),
                    "-R",
                    "--pitch-hq",
                    f_src_path,
                    f_dest_path,
                ]
            elif a_audio_item.time_stretch_mode == 4:
                f_cmd = [
                    RUBBERBAND_PATH,
                    "-F",
                    "-c", str(a_audio_item.crispness),
                    "-t", str(a_audio_item.timestretch_amt),
                    "-p", str(a_audio_item.pitch_shift),
                    "-R",
                    "--pitch-hq",
                    f_src_path,
                    f_dest_path,
                ]
            elif a_audio_item.time_stretch_mode == 5:
                f_cmd = [
                    SBSMS,
                    f_src_path,
                    f_dest_path,
                    str(1.0 / a_audio_item.timestretch_amt),
                    str(1.0 / a_audio_item.timestretch_amt_end),
                    str(a_audio_item.pitch_shift),
                    str(a_audio_item.pitch_shift_end)
                ]
            elif a_audio_item.time_stretch_mode == 6:
                f_cmd = [
                    PAULSTRETCH_PATH,
                    'paulstretch',
                    "-s", str(a_audio_item.timestretch_amt),
                    f_src_path,
                    f_dest_path,
                ]
                if IS_WINDOWS and IS_LOCAL_DEVEL:
                    f_cmd.insert(1, sys.argv[0])
            elif a_audio_item.time_stretch_mode in (7, 8):
                ext = os.path.splitext(f_src_path)[1].lower()
                if ext not in ('.wav', '.wave'):
                    with tempfile.NamedTemporaryFile() as t:
                        tmp = t.name + '.wav'
                    convert_to_wav(f_src_path, tmp)
                    f_src_path = tmp
                _rate = ((1. / a_audio_item.timestretch_amt) - 1.0) * 100.
                f_cmd = [
                    SOUNDSTRETCH,
                    f_src_path,
                    f_dest_path,
                    f'-pitch={a_audio_item.pitch_shift}',
                    f'-rate={_rate}',
                ]
                if a_audio_item.time_stretch_mode == 8:
                    f_cmd.append('-speech')

            self.timestretch_cache[f_key] = f_uid
            self.timestretch_reverse_lookup[f_dest_path] = f_src_path

            if f_cmd is not None:
                LOG.info("Running {}".format(" ".join(f_cmd)))
                if IS_WINDOWS:
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    env = os.environ.copy()
                    env['PATH'] = ENGINE_DIR + ';' + env['PATH']
                    env['PYTHONPATH'] = INSTALL_PREFIX
                    #LOG.info(env)
                    f_proc = subprocess.Popen(
                        f_cmd,
                        encoding='UTF-8',
                        env=env,
                        startupinfo=startupinfo,
                    )
                else:
                    f_proc = subprocess.Popen(
                        f_cmd,
                        encoding='UTF-8',
                    )
                stdout, stderr = f_proc.communicate()
                if not (
                    f_proc.returncode == 0
                    and
                    os.path.exists(f_dest_path)
                ):
                    LOG.error(f"{f_cmd} failed with {f_proc.returncode}")
                    LOG.error(stdout)
                    LOG.error(stderr)
                    raise FileNotFoundError(
                        f"Could not time stretch file, {f_cmd} returned "
                        f"{f_proc.returncode}"
                    )
                a_audio_item.uid = self.timestretch_cache[f_key]
                self.get_wav_uid_by_name(
                    f_dest_path,
                    a_uid=f_uid,
                )

    def timestretch_get_orig_file_uid(self, a_uid):
        """ Return the UID of the original file """
        f_new_path = self.get_wav_path_by_uid(a_uid)
        if f_new_path in self.timestretch_reverse_lookup:
            f_old_path = self.timestretch_reverse_lookup[f_new_path]
            return self.get_wav_uid_by_name(f_old_path)
        else:
            LOG.warning(
                f"timestretch_get_orig_file_uid could not find uid {a_uid}"
            )
            return a_uid

    def get_sample_graph_by_name(self, a_path, a_uid_dict=None, a_cp=True):
        f_uid = self.get_wav_uid_by_name(a_path, a_cp=a_cp)
        return self.get_sample_graph_by_uid(f_uid)

    def get_sample_graph_by_uid(self, a_uid):
        f_pygraph_file = os.path.join(
            *(str(x) for x in (self.samplegraph_folder, a_uid))
        )
        f_result = SampleGraph.create(
            f_pygraph_file,
            self.samples_folder,
        )
        if not f_result.is_valid(): # or not f_result.check_mtime():
            LOG.info(
                "\n\nNot valid, or else mtime is newer than graph time, "
                "deleting sample graph...\n"
            )
            remove_item_from_sg_cache(f_pygraph_file)
            self.create_sample_graph(self.get_wav_path_by_uid(a_uid), a_uid)
            return SampleGraph.create(
                f_pygraph_file, self.samples_folder)
        else:
            return f_result

    def delete_sample_graph_by_name(self, a_path):
        f_uid = self.get_wav_uid_by_name(a_path, a_cp=False)
        self.delete_sample_graph_by_uid(f_uid)

    def delete_sample_graph_by_uid(self, a_uid):
        f_pygraph_file = os.path.join(
            *(str(x) for x in (self.samplegraph_folder, a_uid))
        )
        remove_item_from_sg_cache(f_pygraph_file)

    def get_wav_uid_by_name(
        self,
        a_path,
        a_uid_dict=None,
        a_uid=None,
        a_cp=True,
    ):
        """ Return the UID from the wav pool, or add to the
            pool if it does not exist
        """
        if a_uid_dict is None:
            audio_pool = self.get_audio_pool()
        else:
            audio_pool = a_uid_dict
        f_path = util.pi_path(a_path)
        if a_cp:
            self.cp_audio_file_to_cache(f_path)
        by_path = audio_pool.by_path()
        if f_path in by_path:
            return by_path[f_path].uid
        else:
            entry = audio_pool.add_entry(f_path, uid=a_uid)
            self.create_sample_graph(f_path, entry.uid)
            self.save_audio_pool(audio_pool)
            return entry.uid


    def to_long_audio_file_path(self, path: str) -> str:
        """ Check if an audio file path begins with an escape character
            and convert to the real path

            @path: THe path to an audio file
        """
        if path[0] == '!':
            return pi_path(
                path.replace('!', self.audio_root_folder, 1),
            )
        return pi_path(path)

    def to_short_audio_file_path(self, path: str) -> str:
        """ Check if the user is trying to load a file already
            in the projects audio file cache

            @path: THe path to an audio file
        """
        audio_dir = pi_path(self.audio_root_folder)
        samples_dir = pi_path(self.samples_folder)
        path = pi_path(path)
        if path.startswith(samples_dir):
            result = path.replace(samples_dir, "", 1)
            return result
        elif path.startswith(audio_dir):
            # Specifically, any folder under project/audio except for the
            # samples/ folder that caches everything else
            return path.replace(audio_dir, '!', 1)
        return path

    def reload_audio_file(self, path):
        """ Reload a audio file that (may have) changed into the audio pool
        """
        LOG.info(f'Attempting to reload {path}')
        path = util.pi_path(path)
        audio_pool = self.get_audio_pool()
        by_path = audio_pool.by_path()
        if path not in by_path:
            LOG.info(f'{path} is not in {by_path}, not reloading')
            return
        uid = by_path[path].uid

        cache_path, cache_dir = self.audio_file_cache_path(path)
        # Only copy files that were previously copied to project cache
        if os.path.isfile(cache_path):
            shutil.copy(path, cache_path)

        self.delete_sample_graph_by_name(path)
        constants.IPC.reload_audio_pool_item(uid)

    def audio_file_cache_path(self, path):
        """ Return the full file path and it's parent directory for an audio
            file in the project cache folder

            @path:
                The path to the file as it already exists on the user's
                hard drive
        """
        if path[0] != "/" and path[1] == ":":  # Windows path
            path = path.replace(":", "", 1)
            cache_path = os.path.join(self.samples_folder, path)
        else:  # UNIX path
            # Work around some baffling Python behaviour where
            # os.path.join('/lala/la', '/ha/haha') returns '/ha/haha'
            if path[0] == '/':
                cache_path = "".join([self.samples_folder, path])
            else:
                cache_path = os.path.join(self.samples_folder, path)
        cache_path = pi_path(cache_path)
        cache_dir = os.path.dirname(cache_path)
        return (cache_path, cache_dir)

    def cp_audio_file_to_cache(self, a_file):
        if (
            a_file in self.cached_audio_files
            or
            a_file.startswith(self.audio_root_folder)
        ):
            return
        f_cp_path, f_cp_dir = self.audio_file_cache_path(a_file)
        if not os.path.isdir(f_cp_dir):
            os.makedirs(f_cp_dir)
        if not os.path.isfile(f_cp_path):
            shutil.copy(a_file, f_cp_path)
        self.cached_audio_files.append(a_file)

    def get_wav_name_by_uid(self, a_uid, a_uid_dict=None):
        """ Return the UID from the wav pool, or add to the
            pool if it does not exist
        """
        if a_uid_dict is None:
            audio_pool = self.get_audio_pool()
        else:
            audio_pool = a_uid_dict
        by_uid = audio_pool.by_uid()
        assert a_uid in by_uid, (a_uid, by_uid)
        return util.pi_path(by_uid[a_uid].path)

    def get_wav_path_by_uid(self, a_uid):
        audio_pool = self.get_audio_pool()
        by_uid = audio_pool.by_uid()
        return by_uid[a_uid].path

    def create_sample_graph(self, a_path, a_uid):
        f_uid = int(a_uid)
        a_path = util.pi_path(a_path)
        f_sample_dir_path = "{}{}".format(self.samples_folder, a_path)
        if os.path.isfile(a_path):
            f_path = a_path
        elif os.path.isfile(f_sample_dir_path):
            f_path = f_sample_dir_path
        else:
            raise Exception("Cannot create sample graph, the "
                "following do not exist:\n{}\n{}\n".format(
                a_path, f_sample_dir_path))
        constants.IPC.add_to_audio_pool(f_path, f_uid)


    def copy_plugin(self, a_old, a_new):
        f_old_path = os.path.join(
            *(str(x) for x in (self.plugin_pool_folder, a_old)))
        if os.path.exists(f_old_path):
            content = read_file_text(f_old_path)
            self.save_file(folder_plugins, a_new, content)
            #self.commit("Copy plugin UID {} to {}".format(a_old, a_new))
        else:
            LOG.info("{} does not exist, not copying".format(f_old_path))


