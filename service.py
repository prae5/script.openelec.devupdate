import os
import sys
import urllib2

import xbmc, xbmcgui, xbmcaddon, xbmcvfs

from lib import constants
from lib import utils
from lib.progress import restart_countdown

__addon__ = xbmcaddon.Addon(constants.__scriptid__)
__icon__ = __addon__.getAddonInfo('icon')
__dir__ = xbmc.translatePath(__addon__.getAddonInfo('profile'))

init = not sys.argv[0]

if init:
    rpi_config_backup_file = os.path.join(__dir__, constants.RPI_CONFIG_FILE)
    if os.path.exists(rpi_config_backup_file):
        utils.log("Re-enabling overclocking")
        utils.mount_readwrite()
        xbmcvfs.copy(rpi_config_backup_file, constants.RPI_CONFIG_PATH)
        utils.mount_readonly()
        xbmcvfs.delete(rpi_config_backup_file)
        if restart_countdown("Ready to reboot to re-enable overclocking."):
            utils.log("Restarting")
            xbmc.restart()
            sys.exit()
        else:
            utils.log("Restart cancelled")

    update_extlinux_file = os.path.join(__dir__, constants.UPDATE_EXTLINUX)
    if os.path.exists(update_extlinux_file):
        utils.log("Updating extlinux")
        utils.mount_readwrite()
        utils.update_extlinux()
        utils.mount_readonly()
        os.remove(update_extlinux_file)

try:
    from lib import builds
except urllib2.URLError:
    sys.exit(1)

check_enabled = __addon__.getSetting('check') == 'true'
check_onbootonly = __addon__.getSetting('check_onbootonly') == 'true'
check_prompt = int(__addon__.getSetting('check_prompt'))

if init:
    notify_file = os.path.join(__dir__, constants.NOTIFY_FILE)
    try:
        with open(notify_file) as f:
            build = f.read()
    except IOError:
        utils.log("No installation notification")
    else:
        utils.log("Notifying that build {} was installed".format(build))
        if build == str(builds.INSTALLED_BUILD):
            xbmc.executebuiltin("Notification(OpenELEC Dev Update, Build {} was installed successfully."
                                ", 12000, {})".format(build, __icon__))
        utils.log("Removing notification file")
        try:
            os.remove(notify_file)
        except OSError:
            pass # in case file was already deleted


    if not check_onbootonly:
        # Start a timer to check for a new build every hour.
        utils.log("Starting build check timer")
        xbmc.executebuiltin("AlarmClock(openelecdevupdate,RunScript({}),03:00:00,silent,loop)".format(__file__))


if check_enabled:
    source = __addon__.getSetting('source')
    if isinstance(builds.INSTALLED_BUILD, builds.Release) and source == "Official Releases":
        # Don't do the job of the official auto-update system.
        utils.log("Skipping build check - official release")
    else:
        try:
            subdir = __addon__.getSetting('subdir')
            if source == "Other":
                url = __addon__.getSetting('custom_url')
                build_url = builds.BuildsURL(url, subdir)
            else:
                build_url = builds.URLS[source]
                url = build_url.url
    
            utils.log("Checking {}".format(url))
            with build_url.extractor() as parser:
                latest = sorted(parser.get_links(), reverse=True)[0]
                if latest > builds.INSTALLED_BUILD:
                    if (check_prompt == 1 and xbmc.Player().isPlayingVideo()) or check_prompt == 0:
                        utils.log("Notifying that new build {} is available".format(latest))
                        xbmc.executebuiltin("Notification(OpenELEC Dev Update, Build {} "
                                            "is available., 7500, {})".format(latest, __icon__))
                    else:
                        utils.log("New build {} is available, prompting to show build list".format(latest))
                        if xbmcgui.Dialog().yesno("OpenELEC Dev Update",
                                                  "A more recent build is available:   {}".format(latest),
                                                  "Current build:   {}".format(builds.INSTALLED_BUILD),
                                                  "Show builds available to install?"):
                            xbmc.executebuiltin("RunAddon({})".format(constants.__scriptid__))
        except:
            pass
