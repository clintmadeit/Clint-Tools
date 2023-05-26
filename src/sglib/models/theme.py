try:
    from sg_py_vendor.pymarshal.json import *
except ImportError:
    from pymarshal.json import *

from sglib.constants import HOME, MAJOR_VERSION
from sglib.lib.util import (
    get_file_setting,
    IS_WINDOWS,
    pi_path,
    set_file_setting,
    SHARE_DIR,
    THEMES_DIR,
    write_file_text,
    read_file_yaml,
    read_file_json,
    sg_open,
)
from sglib.log import LOG
from sglib.math import clip_value

import json
import os
import re
import shutil

import jinja2
import yaml


ASSETS_DIR = None
ICON_PATH = None
THEME_FILE = None
_THEMES_DIR_SUB = '{{ SYSTEM_THEME_DIR }}'
VARIABLES = None

HEX_MATCHER = re.compile(r'^#(?:[0-9a-fA-F]{1,2}){3,4}$')

def hex_color_assert(color):
    pm_assert(
        HEX_MATCHER.match(color),
        ValueError,
        (HEX_MATCHER, color),
        "Invalid hex color",
    )

class GradientStop:
    def __init__(
        self,
        pos: float,
        color: str,
    ):
        hex_color_assert(color)
        self.pos = type_assert(
            pos,
            float,
        )
        self.color = type_assert(
            color,
            str,
        )

class Gradient:
    def __init__(
        self,
        stops: list,
    ):
        self.stops = type_assert_iter(
            stops,
            GradientStop,
        )

class UIScaler:
    """ UI scaling helper class, available to sgui code and Jinja templates
        Mostly useful for HiDpi scaling across many screen sizes
    """
    def __init__(
        self,
        x_size: float,
        y_size: float,
        x_res: float,
        y_res: float,
    ):
        self.x_size = x_size
        self.y_size = y_size
        self.x_res = x_res
        self.y_res = y_res

    def _mm_to_px(
        self,
        mm: int,
        orientation: str='h',
    ):
        if orientation == 'w':
            res = self.x_res
            size = self.x_size
        elif orientation == 'h':
            res = self.y_res
            size = self.y_size
        else:
            raise ValueError(f"orientation {orientation} not in ('w', 'h')")
        px = (float(mm) / size) * res
        return px, size

    def mm_to_px_pct(
        self,
        mm: int,
        _min: float=3.,
        _max: float=15.,
        orientation: str='h',
    ) -> int:
        """ Convert millimeters to screen pixels, clip to a percentage of
            screen size.

            @mm:      The size in millimeters
            @_min: 0.0-100.0
                The minimum percentage of screen size the element should
                consume.
            @_max: 1.0-100.0
                The maximum percentage of screen size the element should
                consume
            @return: The size in pixels (QSS px)
        """
        px, size = self._mm_to_px(mm, orientation)
        max_px = _max * size * 0.01
        min_px = _min * size * 0.01
        px = clip_value(
            px,
            min_px,
            max_px,
        )
        return int(px)

    def mm_to_px(
        self,
        mm: int,
        _min: int=1,
        _max: int=15,
        orientation: str='h',
    ) -> int:
        """ Convert millimeters to screen pixels
            @mm:      The size in millimeters
            @_min: 1-N
                The minimum number of pixels
            @_max:  1-N
                The maximum number of pixels
            @return: The size in pixels (QSS px)
        """
        px, _ = self._mm_to_px(mm, orientation)
        px = clip_value(
            px,
            _min,
            _max,
        )
        return int(px)

    def pct_to_px(
        self,
        pct: float,
        orientation: str='h',
    ) -> int:
        """ Convert percentage of screen size to pixels
            @pct: 0.0-100.0
        """
        if orientation == 'w':
            px = self.x_res * pct
        elif orientation == 'h':
            px = self.y_res * pct
        else:
            raise ValueError(f"orientation {orientation} not in ('w', 'h')")
        px = round(px * 0.01)
        return int(px)

class DawColors:
    def __init__(
        self,
        seq_antialiasing=False,
        seq_atm_item='#ffffff',
        seq_atm_item_selected='#000000',
        seq_atm_line='#ffffff',
        seq_item_note="#a5a5a5",
        seq_item_audio="#969696",
        seq_item_text="#ffffff",
        seq_item_text_selected="#000000",
        seq_bar_line="#787878",
        seq_beat_line="#d2d2d2",
        seq_16th_line="#090909",
        seq_track_line="#181818",
        seq_background="#424242",
        seq_item_background="#424242",
        seq_item_background_use_track_color=False,
        seq_selected_item="#eeeeee",
        seq_header="#1d1e22",
        seq_header_text="#ffffff",
        seq_header_region="#7878ff",
        seq_header_event_pos="#7878ff",
        seq_item_handle="#ffffff",
        seq_item_handle_selected="#ffffff",
        seq_tempo_marker="#ffffff",
        track_default_colors=[
            "#b00fb8",
            "#0f1cb8",
            "#62b80f",
            "#b3b80f",
            "#b80f0f",
        ],
        item_audio_handle="#ffffff",
        item_audio_handle_selected="#181818",
        item_audio_vol_line="#ff0000",
        item_audio_label="#ffffff",
        item_audio_label_selected="#1e1e1e",
        item_audio_waveform="#1e1e1e",
        item_atm_point="#f00e0e",
        item_atm_point_selected="#f0f0f0",
        item_atm_point_pen="#d00e0e",
        note_beat_line="#000000",
        note_black_background="#1e1e1e",
        note_root_background="#5f1e1e",
        note_snap_line="#000000",
        note_white_background="#5f5f61",
        note_vel_max_color="#f89e19",
        note_vel_min_color="#199ef8",
        note_selected_color="#cccccc",
        playback_cursor="#ff0000",
        drag_drop_silhouette="#7878ff",
    ):
        self.seq_antialiasing = type_assert(
            seq_antialiasing,
            bool,
        )
        self.seq_atm_item = type_assert(
            seq_atm_item,
            str,
        )
        self.seq_atm_item_selected = type_assert(
            seq_atm_item_selected,
            str,
        )
        self.seq_atm_line = type_assert(
            seq_atm_line,
            str,
        )
        self.seq_item_note = type_assert(
            seq_item_note,
            str,
        )
        self.seq_item_audio = type_assert(
            seq_item_audio,
            str,
        )
        self.seq_item_text = type_assert(
            seq_item_text,
            str,
        )
        self.seq_item_text_selected = type_assert(
            seq_item_text_selected,
            str,
        )
        self.seq_bar_line = type_assert(
            seq_bar_line,
            str,
        )
        self.seq_beat_line = type_assert(
            seq_beat_line,
            str,
        )
        self.seq_16th_line = type_assert(
            seq_16th_line,
            str,
        )
        self.seq_track_line = type_assert(
            seq_track_line,
            str,
        )
        self.seq_background = type_assert(
            seq_background,
            str,
        )
        self.seq_item_background = type_assert(
            seq_item_background,
            str,
        )
        self.seq_item_background_use_track_color = type_assert(
            seq_item_background_use_track_color,
            bool,
        )
        self.seq_selected_item = type_assert(
            seq_selected_item,
            str,
        )
        self.seq_header = type_assert(
            seq_header,
            str,
        )
        self.seq_header_text = type_assert(
            seq_header_text,
            str,
        )
        self.seq_header_region = type_assert(
            seq_header_region,
            str,
        )
        self.seq_header_event_pos = type_assert(
            seq_header_event_pos,
            str,
        )
        self.seq_item_handle = type_assert(
            seq_item_handle,
            str,
        )
        self.seq_item_handle_selected = type_assert(
            seq_item_handle_selected,
            str,
        )
        self.seq_tempo_marker = type_assert(
            seq_tempo_marker,
            str,
        )
        self.track_default_colors = type_assert_iter(
            track_default_colors,
            str,
        )
        self.item_audio_handle = type_assert(
            item_audio_handle,
            str,
        )
        self.item_audio_handle_selected = type_assert(
            item_audio_handle_selected,
            str,
        )
        self.item_audio_vol_line = type_assert(
            item_audio_vol_line,
            str,
        )
        self.item_audio_label = type_assert(
            item_audio_label,
            str,
        )
        self.item_audio_label_selected = type_assert(
            item_audio_label_selected,
            str,
        )
        self.item_audio_waveform = type_assert(
            item_audio_waveform,
            str,
        )
        self.item_atm_point = type_assert(
            item_atm_point,
            str,
        )
        self.item_atm_point_selected = type_assert(
            item_atm_point_selected,
            str,
        )
        self.item_atm_point_pen = type_assert(
            item_atm_point_pen,
            str,
        )
        self.note_root_background = type_assert(
            note_root_background,
            str,
        )
        self.note_white_background = type_assert(
            note_white_background,
            str,
        )
        self.note_black_background = type_assert(
            note_black_background,
            str,
        )
        self.note_beat_line = type_assert(
            note_beat_line,
            str,
        )
        self.note_snap_line = type_assert(
            note_snap_line,
            str,
        )
        self.note_vel_max_color = type_assert(
            note_vel_max_color,
            str,
        )
        self.note_vel_min_color = type_assert(
            note_vel_min_color,
            str,
        )
        self.note_selected_color = type_assert(
            note_selected_color,
            str,
        )
        self.playback_cursor = type_assert(
            playback_cursor,
            str,
        )
        self.drag_drop_silhouette = type_assert(
            drag_drop_silhouette,
            str,
        )

class WidgetColors:
    def __init__(
        self,
        audio_item_viewer_color="#8212f2",
        default_scene_background="#424242",
        knob_arc_pen="#ffffff",
        knob_arc_background_pen="#5a5a5a",
        knob_bg_image="knob-bg.png",
        knob_fg_image="knob-fg.png",
        peak_meter={
            'stops': [
                {'pos': 0.0, 'color': "#cc2222"},
                {'pos': 0.0333, 'color': "#cc2222"},
                {'pos': 0.05, 'color': "#aacc22"},
                {'pos': 0.2, 'color': "#aacc22"},
                {'pos': 0.4, 'color': "#22cc22"},
                {'pos': 0.7, 'color': "#22cc22"},
                {'pos': 1.0, 'color': "#22aa99"},
            ],
        },
        playback_cursor="#aa0000",
        rout_graph_node="#e7e700",
        rout_graph_node_text="#e7e7e7",
        rout_graph_to="#e7a0a0",
        rout_graph_from="#a0a0e7",
        rout_graph_lines="#696969",
        rout_graph_wire_audio="#cccccc",
        rout_graph_wire_midi="#6666cc",
        rout_graph_wire_sc="#cc6666",
        splash_screen="splash.svg",
        splash_screen_text="#ffffff",
    ):
        self.audio_item_viewer_color = type_assert(
            audio_item_viewer_color,
            str,
        )
        self.default_scene_background = type_assert(
            default_scene_background,
            str,
        )
        self.knob_arc_pen = type_assert(
            knob_arc_pen,
            str,
        )
        self.knob_arc_background_pen = type_assert(
            knob_arc_background_pen,
            str,
        )
        self.knob_bg_image = type_assert(
            knob_bg_image,
            str,
        )
        self.knob_fg_image = type_assert(
            knob_fg_image,
            str,
        )
        self.peak_meter = type_assert(
            peak_meter,
            Gradient,
        )
        self.playback_cursor = type_assert(
            playback_cursor,
            str,
        )
        self.rout_graph_node = type_assert(
            rout_graph_node,
            str,
        )
        self.rout_graph_node_text = type_assert(
            rout_graph_node_text,
            str,
        )
        self.rout_graph_to = type_assert(
            rout_graph_to,
            str,
        )
        self.rout_graph_from = type_assert(
            rout_graph_from,
            str,
        )
        self.rout_graph_lines = type_assert(
            rout_graph_lines,
            str,
        )
        self.rout_graph_wire_audio = type_assert(
            rout_graph_wire_audio,
            str,
        )
        self.rout_graph_wire_midi = type_assert(
            rout_graph_wire_midi,
            str,
        )
        self.rout_graph_wire_sc = type_assert(
            rout_graph_wire_sc,
            str,
        )
        self.splash_screen = type_assert(
            splash_screen,
            str,
        )
        self.splash_screen_text = type_assert(
            splash_screen_text,
            str,
        )


class SystemColors:
    def __init__(
        self,
        daw,
        widgets
    ):
        self.daw = type_assert(daw, DawColors)
        self.widgets = type_assert(widgets, WidgetColors)

class VarsFile:
    def __init__(
        self,
        path,
        overrides,
    ):
        self.path = type_assert(path, str)
        self.overrides = type_assert(
            overrides,
            dict,
        )

class SystemOverrides:
    def __init__(
        self,
        daw,
        widgets,
    ):
        self.daw = type_assert(
            daw,
            dict,
        )
        self.widgets = type_assert_dict(
            widgets,
            dict,
        )

class SystemFile:
    def __init__(
        self,
        path,
        overrides,
    ):
        self.path = type_assert(path, str)
        self.overrides = type_assert(overrides, SystemOverrides)

class Theme:
    def __init__(
        self,
        template,
        palette,
        variables,
        system=None,
    ):
        self.template = type_assert(
            template,
            str,
            desc=(
                "The path to a QSS Jinja template file relative to the "
                "theme directory"
            ),
        )
        self.palette = type_assert(
            palette,
            str,
        )
        self.variables = type_assert(
            variables,
            VarsFile,
            desc=(
                "The path to a YAML file of variables to pass to the QSS "
                "Jinja template, and any overrides"
            ),
        )
        self.system = type_assert(
            system,
            SystemFile,
            allow_none=True,
            desc=(
                "The path to a YAML file containing a system colors "
                "definition, and any overrides"
            ),
        )

    def render(
        self,
        path,
        scaler,
        font_size,
        font_unit,
    ):
        rendered_dir = os.path.join(HOME, 'rendered_theme')
        if not os.path.isdir(rendered_dir):
            os.makedirs(rendered_dir)
        dirname = os.path.dirname(path)
        var_dir = os.path.join(dirname, 'vars')
        var_path = os.path.join(var_dir, self.variables.path)
        palette_path = os.path.join(dirname, 'palettes', self.palette)
        palette = read_file_yaml(palette_path)
        with sg_open(var_path) as f:
            template = jinja2.Environment(
                loader=jinja2.FileSystemLoader(var_dir),
            ).from_string(f.read())
            y = template.render(palette=palette)
            variables = yaml.safe_load(y)
        LOG.info(f"Overriding {variables}")
        LOG.info(f"with {self.variables.overrides}")
        variables.update(self.variables.overrides)
        LOG.info(f"Result: {variables}")
        with sg_open(
            os.path.join(rendered_dir, 'variables.yaml'),
            'w',
        ) as f:
            json.dump(variables, f, indent=2)

        system_path = os.path.join(dirname, 'system', self.system.path)
        with sg_open(system_path) as f:
            template = jinja2.Template(f.read())
            y = template.render(palette=palette, **variables)
            y = yaml.safe_load(y)
        y['daw'].update(self.system.overrides.daw)
        y['widgets'].update(self.system.overrides.widgets)
        system_colors = unmarshal_json(y, SystemColors)
        with sg_open(
            os.path.join(rendered_dir, 'system.yaml'),
            'w'
        ) as f:
            json.dump(
                marshal_json(system_colors),
                f,
                indent=4,
            )

        template_path = os.path.join(dirname, 'templates', self.template)
        with sg_open(template_path) as f:
            template = jinja2.Template(f.read())
            qss = template.render(
                ASSETS_DIR=ASSETS_DIR,
                FONT_SIZE=font_size,
                FONT_UNIT=font_unit,
                palette=palette,
                SYSTEM_COLORS=system_colors,
                SCALER=scaler,
                **variables
            )
        qss_path = os.path.join(rendered_dir, 'theme.qss')
        write_file_text(qss_path, qss)

        return qss, system_colors, variables


def setup_globals():
    global \
        ASSETS_DIR, \
        ICON_PATH, \
        THEME_FILE

    ICON_PATH = os.path.join(
        os.path.dirname(__file__),
        '..',
        '..',
        'files',
        "share",
        "pixmaps",
        "{}.ico".format(
            MAJOR_VERSION
        ),
    )
    if not os.path.exists(ICON_PATH):
        ICON_PATH = os.path.join(
            SHARE_DIR,
            "pixmaps",
            "{}.ico".format(
                MAJOR_VERSION
            ),
        )
    ICON_PATH = os.path.abspath(ICON_PATH)

    DEFAULT_THEME_FILE = os.path.join(
        THEMES_DIR,
        "default",
        "default.sgtheme",
    )

    if not os.path.exists(DEFAULT_THEME_FILE):
        DEFAULT_THEME_FILE = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__),
                '..',
                '..',
                'files',
                'themes',
                'default',
                'default.sgtheme',
            )
        )

    THEME_FILE = get_file_setting("default-style", str, None)
    if THEME_FILE:
        # The Windows install prefix changes everytime Stargate is launched,
        # so substitute it every time the file is saved or loaded
        THEME_FILE = THEME_FILE.replace(
            _THEMES_DIR_SUB,
            pi_path(THEMES_DIR),
        )

    if (
        not THEME_FILE
        or
        not os.path.isfile(THEME_FILE)
    ):
        LOG.warning(
            f"Theme file: '{THEME_FILE}', does not exist, using default"
        )
        THEME_FILE = DEFAULT_THEME_FILE


    LOG.info(f"Using theme file {THEME_FILE}")
    STYLESHEET_DIR = os.path.dirname(THEME_FILE)
    if IS_WINDOWS:
        STYLESHEET_DIR = STYLESHEET_DIR.replace("\\", "/")

    # In QSS, backslashes are not valid
    ASSETS_DIR = "/".join([
        STYLESHEET_DIR,
        'assets',
    ])


def open_theme(
    theme_file: str,
    scaler: UIScaler,
    font_size: int,
    font_unit: str,
):
    y = read_file_yaml(theme_file)
    theme = unmarshal_json(y, Theme)
    return theme.render(
        theme_file,
        scaler,
        font_size,
        font_unit,
    )

def load_theme(
    scaler: UIScaler,
    font_size: int,
    font_unit: str,
):
    """ Load the QSS theme and system colors.  Do this before creating any
        widgets.
    """
    global \
        QSS, \
        SYSTEM_COLORS, \
        VARIABLES

    setup_globals()
    QSS, SYSTEM_COLORS, VARIABLES = open_theme(
        THEME_FILE,
        scaler,
        font_size,
        font_unit,
    )


def copy_theme(dest):
    theme_dir = os.path.dirname(THEME_FILE)
    shutil.copytree(theme_dir, dest)

def set_theme(
    path: str,
    scaler,
    font_size: int,
    font_unit: str,
):
    path = pi_path(path)
    # Test that the theme parses before accepting it.
    # Will raise an exception if malformed data, you must use try/except
    open_theme(path, scaler, font_size, font_unit)
    # The Windows install prefix changes everytime Stargate is launched,
    # so substitute it every time the file is saved or loaded
    path = path.replace(
        pi_path(THEMES_DIR),
        _THEMES_DIR_SUB,
    )
    LOG.info(f"Setting theme file {path}")
    set_file_setting("default-style", path)

def get_asset_path(asset: str):
    path = os.path.join(
        ASSETS_DIR,
        VARIABLES['assets_subdir'],
        asset,
    )
    if not os.path.exists(path):
        path = os.path.join(
            ASSETS_DIR,
            asset,
        )
    pm_assert(
        os.path.exists(path),
        FileNotFoundError,
        path,
        f'{path} does not exist',
    )
    return path

