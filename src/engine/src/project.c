#include <time.h>

#include "clinttools.h"
#include "daw.h"
#include "files.h"
#include "wave_edit.h"


void v_open_project(const SGPATHSTR* a_project_folder, int a_first_load){
#if SG_OS == _OS_LINUX
    struct timespec f_start, f_finish;
    clock_gettime(CLOCK_REALTIME, &f_start);
#endif

    SGPATHSTR clinttools_dot_project[1024];
    sg_path_snprintf(
        clinttools_dot_project,
        1024,
#if SG_OS == _OS_WINDOWS
        L"%ls/clinttools.project",
#else
        "%s/clinttools.project",
#endif
        a_project_folder
    );
    if(!i_file_exists(clinttools_dot_project)){
#if SG_OS == _OS_WINDOWS
        log_error(
            "Project folder %ls does not contain a clinttools.project file, "
            "it is not a Clinttools DAW project, exiting.",
            a_project_folder
        );
#else
        log_error(
            "Project folder %s does not contain a clinttools.project file, "
            "it is not a Clinttools DAW project, exiting.",
            a_project_folder
        );
#endif
        exit(321);
    }
    log_info("Setting files and folders");
    sg_path_snprintf(
        CLINTTOOLS->project_folder,
        1024,
#if SG_OS == _OS_WINDOWS
        L"%ls",
#else
        "%s",
#endif
        a_project_folder
    );
    sg_path_snprintf(
        CLINTTOOLS->plugins_folder,
        1024,
#if SG_OS == _OS_WINDOWS
        L"%ls/projects/plugins/",
#else
        "%s/projects/plugins/",
#endif
        CLINTTOOLS->project_folder
    );
    sg_path_snprintf(
        CLINTTOOLS->samples_folder,
        1024,
#if SG_OS == _OS_WINDOWS
        L"%ls/audio/samples",
#else
        "%s/audio/samples",
#endif
        CLINTTOOLS->project_folder
    );  //No trailing slash
    sg_path_snprintf(
        CLINTTOOLS->samplegraph_folder,
        1024,
#if SG_OS == _OS_WINDOWS
        L"%ls/audio/samplegraph",
#else
        "%s/audio/samplegraph",
#endif
        CLINTTOOLS->project_folder
    );  //No trailing slash

    sg_path_snprintf(
        CLINTTOOLS->audio_pool->samples_folder,
        1024,
#if SG_OS == _OS_WINDOWS
        L"%ls",
#else
        "%s",
#endif
        CLINTTOOLS->samples_folder
    );

    sg_path_snprintf(
        CLINTTOOLS->audio_pool_file,
        1024,
#if SG_OS == _OS_WINDOWS
        L"%ls/audio/audio_pool",
#else
        "%s/audio/audio_pool",
#endif
        CLINTTOOLS->project_folder
    );
    sg_path_snprintf(
        CLINTTOOLS->audio_folder,
        1024,
#if SG_OS == _OS_WINDOWS
        L"%ls/audio",
#else
        "%s/audio",
#endif
        CLINTTOOLS->project_folder
    );
    sg_path_snprintf(
        CLINTTOOLS->audio_tmp_folder,
        1024,
#if SG_OS == _OS_WINDOWS
        L"%ls/audio/files/tmp/",
#else
        "%s/audio/files/tmp/",
#endif
        CLINTTOOLS->project_folder
    );

    if(a_first_load && i_file_exists(CLINTTOOLS->audio_pool_file)){
        log_info("Loading wave pool");
        v_audio_pool_add_items(
            CLINTTOOLS->audio_pool,
            CLINTTOOLS->audio_pool_file,
            CLINTTOOLS->audio_folder
        );
    }

    log_info("Opening wave editor project");
    v_we_open_project();
    log_info("Opening DAW project");
    v_daw_open_project(a_first_load);
    log_info("Finished opening projects");

#if SG_OS == _OS_LINUX
    clock_gettime(CLOCK_REALTIME, &f_finish);
    v_print_benchmark("v_open_project", f_start, f_finish);
#endif
}


