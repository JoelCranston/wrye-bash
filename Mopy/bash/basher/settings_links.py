# -*- coding: utf-8 -*-
#
# GPL License and Copyright Notice ============================================
#  This file is part of Wrye Bash.
#
#  Wrye Bash is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  Wrye Bash is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with Wrye Bash; if not, write to the Free Software Foundation,
#  Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2014 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
import locale
import wx # FIXME(ut): wx
from ..balt import _Link, vSizer, hSizer, spacer, button, AppendableLink, \
    RadioLink, CheckLink, MenuLink, TransLink, EnabledLink, SeparatorLink, \
    BoolLink, staticText, tooltip
from .. import barb, bosh, bush, balt, bass, bolt
from .constants import tabInfo
from ..bolt import StateError, deprint, GPath
from . import askYes, BashFrame, ColorDialog, bashFrameSetTitle, getStatusBar, \
    BashStatusBar, App_Button
# TODO(ut): settings links do not seem to use Link.data attribute - it's None..
# FIXME(ut): globals everywhere !
#------------------------------------------------------------------------------
# Settings Links --------------------------------------------------------------
#------------------------------------------------------------------------------
class Settings_BackupSettings(_Link): # TODO(ut): was checklink - why ?
    """Saves Bash's settings and user data.."""
    text =_(u'Backup Settings...')
    help = _(u"Backup all of Wrye Bash's settings/data to an archive file.")

    def Execute(self,event):
        def OnClickAll(event):
            dialog.EndModal(2)
        def OnClickNone(event):
            dialog.EndModal(1)
        def PromptConfirm(msg=None):
            msg = msg or _(u'Do you want to backup your Bash settings now?')
            return askYes(msg,_(u'Backup Bash Settings?'))
        from . import bashFrame # FIXME(ut): globals
        BashFrame.SaveSettings(bashFrame)
        #backup = barb.BackupSettings(bashFrame)
        try:
            if PromptConfirm():
                dialog = wx.Dialog(bashFrame,wx.ID_ANY,_(u'Backup Images?'),size=(400,200),style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)
                icon = wx.StaticBitmap(dialog,wx.ID_ANY,wx.ArtProvider_GetBitmap(wx.ART_WARNING,wx.ART_MESSAGE_BOX, (32,32)))
                sizer = vSizer(
                    (hSizer(
                        (icon,0,wx.ALL,6),
                        (staticText(dialog,_(u'Do you want to backup any images?'),style=wx.ST_NO_AUTORESIZE),1,wx.EXPAND|wx.LEFT,6),
                        ),1,wx.EXPAND|wx.ALL,6),
                    (hSizer(
                        spacer,
                        button(dialog,label=_(u'Backup All Images'),onClick=OnClickAll),
                        (button(dialog,label=_(u'Backup Changed Images'),onClick=OnClickNone),0,wx.LEFT,4),
                        (button(dialog,id=wx.ID_CANCEL,label=_(u'None')),0,wx.LEFT,4),
                        ),0,wx.EXPAND|wx.LEFT|wx.RIGHT|wx.BOTTOM,6),
                    )
                dialog.SetSizer(sizer)
                backup = barb.BackupSettings(bashFrame,backup_images=dialog.ShowModal())
                backup.Apply()
        except StateError:
            backup.WarnFailed()
        except barb.BackupCancelled:
            pass
        #end try
        backup = None

#------------------------------------------------------------------------------
class Settings_RestoreSettings(_Link): # TODO(ut): was checklink - why ?
    """Saves Bash's settings and user data.."""
    text = _(u'Restore Settings...')
    help = _(u"Restore all of Wrye Bash's settings/data from a backup archive "
             u"file.")

    def Execute(self,event):
        try:
            from . import bashFrame # FIXME(ut): globals
            backup = barb.RestoreSettings(bashFrame)
            if backup.PromptConfirm():
                backup.restore_images = askYes(
                    _(u'Do you want to restore saved images as well as settings?'),
                    _(u'Restore Settings'))
                backup.Apply()
        except barb.BackupCancelled: #cancelled
            pass
        #end try
        backup = None

#------------------------------------------------------------------------------
class Settings_SaveSettings(_Link): # TODO(ut): was checklink - why ?
    """Saves Bash's settings and user data."""
    text = _(u'Save Settings')
    help = _(u"Save all of Wrye Bash's settings/data now.")

    def Execute(self,event):
        from . import bashFrame # FIXME(ut): globals
        BashFrame.SaveSettings(bashFrame)

#------------------------------------------------------------------------------
class Settings_ExportDllInfo(AppendableLink):
    """Exports list of good and bad dll's."""
    text = _(
        u"Export list of allowed/disallowed %s plugin dlls") % bush.game.se_sd
    help = _(u"Export list of allowed/disallowed plugin dlls to a txt file"
        u" (for BAIN).")

    def _append(self, window): return bush.game.se_sd

    def Execute(self,event):
        textDir = bosh.dirs['patches']
        textDir.makedirs()
        #--File dialog
        textPath = balt.askSave(self.window,
            _(u'Export list of allowed/disallowed %s plugin dlls to:') % bush.game.se_sd,
            textDir, bush.game.se.shortName+u' '+_(u'dll permissions')+u'.txt',
            u'*.txt')
        if not textPath: return
        with textPath.open('w',encoding='utf-8-sig') as out:
            out.write(u'goodDlls '+_(u'(those dlls that you have chosen to allow to be installed)')+u'\r\n')
            if bosh.settings['bash.installers.goodDlls']:
                for dll in bosh.settings['bash.installers.goodDlls']:
                    out.write(u'dll:'+dll+u':\r\n')
                    for index, version in enumerate(bosh.settings['bash.installers.goodDlls'][dll]):
                        out.write(u'version %02d: %s\r\n' % (index, version))
            else: out.write(u'None\r\n')
            out.write(u'badDlls '+_(u'(those dlls that you have chosen to NOT allow to be installed)')+u'\r\n')
            if bosh.settings['bash.installers.badDlls']:
                for dll in bosh.settings['bash.installers.badDlls']:
                    out.write(u'dll:'+dll+u':\r\n')
                    for index, version in enumerate(bosh.settings['bash.installers.badDlls'][dll]):
                        out.write(u'version %02d: %s\r\n' % (index, version))
            else: out.write(u'None\r\n')

#------------------------------------------------------------------------------
class Settings_ImportDllInfo(AppendableLink):
    """Imports list of good and bad dll's."""
    text = _(
        u"Import list of allowed/disallowed %s plugin dlls") % bush.game.se_sd
    help = _(u"Import list of allowed/disallowed plugin dlls from a txt file"
        u" (for BAIN).")

    def _append(self, window): return bush.game.se_sd

    def Execute(self,event):
        textDir = bosh.dirs['patches']
        textDir.makedirs()
        #--File dialog
        textPath = balt.askOpen(self.window,
            _(u'Import list of allowed/disallowed %s plugin dlls from:') % bush.game.se_sd,
            textDir, bush.game.se.shortName+u' '+_(u'dll permissions')+u'.txt',
            u'*.txt',mustExist=True)
        if not textPath: return
        message = (_(u'Merge permissions from file with current dll permissions?')
                   + u'\n' +
                   _(u"('No' Replaces current permissions instead.)")
                   )
        if not balt.askYes(self.window,message,_(u'Merge permissions?')): replace = True
        else: replace = False
        try:
            with textPath.open('r',encoding='utf-8-sig') as ins:
                Dlls = {'goodDlls':{},'badDlls':{}}
                for line in ins:
                    line = line.strip()
                    if line.startswith(u'goodDlls'):
                        current = Dlls['goodDlls']
                    if line.startswith(u'badDlls'):
                        current = Dlls['badDlls']
                    elif line.startswith(u'dll:'):
                        dll = line.split(u':',1)[1].strip()
                        current.setdefault(dll,[])
                    elif line.startswith(u'version'):
                        ver = line.split(u':',1)[1]
                        ver = eval(ver)
                        current[dll].append(ver)
                        print dll,':',ver
            if not replace:
                bosh.settings['bash.installers.goodDlls'].update(Dlls['goodDlls'])
                bosh.settings['bash.installers.badDlls'].update(Dlls['badDlls'])
            else:
                bosh.settings['bash.installers.goodDlls'], bosh.settings['bash.installers.badDlls'] = Dlls['goodDlls'], Dlls['badDlls']
        except UnicodeError:
            balt.showError(self.window,_(u'Wrye Bash could not load %s, because it is not saved in UTF-8 format.  Please resave it in UTF-8 format and try again.') % textPath.s)
        except Exception as e:
            deprint(u'Error reading', textPath.s, traceback=True)
            balt.showError(self.window,_(u'Wrye Bash could not load %s, because there was an error in the format of the file.') % textPath.s)

#------------------------------------------------------------------------------
class Settings_Colors(_Link):
    """Shows the color configuration dialog."""
    text = _(u'Colors...')
    help = _(u"Configure the custom colors used in the UI.")

    def Execute(self,event):
        from . import bashFrame # FIXME(ut): globals
        dialog = ColorDialog(bashFrame)
        dialog.ShowModal()
        dialog.Destroy()

#------------------------------------------------------------------------------
class Settings_Tab(AppendableLink, CheckLink, EnabledLink):
    """Handle hiding/unhiding tabs."""
    def __init__(self,tabKey,canDisable=True):
        super(Settings_Tab, self).__init__()
        self.tabKey = tabKey
        self.enabled = canDisable
        className, self.text, item = tabInfo.get(self.tabKey,[None,None,None])
        self.help = _(u"Show/Hide the %(tabtitle)s Tab.") % (
            {'tabtitle': self.text})

    def _append(self, window): return self.text is not None

    def _enable(self): return self.enabled

    def _check(self): return bosh.settings['bash.tabs'][self.tabKey]

    def Execute(self,event):
        from . import bashFrame # FIXME(ut): globals
        if bosh.settings['bash.tabs'][self.tabKey]:
            # It was enabled, disable it.
            iMods = None
            iInstallers = None
            iDelete = None
            for i in range(bashFrame.notebook.GetPageCount()):
                pageTitle = bashFrame.notebook.GetPageText(i)
                if pageTitle == tabInfo['Mods'][1]:
                    iMods = i
                elif pageTitle == tabInfo['Installers'][1]:
                    iInstallers = i
                if pageTitle == tabInfo[self.tabKey][1]:
                    iDelete = i
            if iDelete == bashFrame.notebook.GetSelection():
                # We're deleting the current page...
                if ((iDelete == 0 and iInstallers == 1) or
                        (iDelete - 1 == iInstallers)):
                    # The auto-page change will change to
                    # the 'Installers' tab.  Change to the
                    # 'Mods' tab instead.
                    bashFrame.notebook.SetSelection(iMods)
            page = bashFrame.notebook.GetPage(iDelete)
            bashFrame.notebook.RemovePage(iDelete)
            page.Show(False)
        else:
            # It was disabled, enable it
            insertAt = 0
            for i,key in enumerate(bosh.settings['bash.tabs.order']):
                if key == self.tabKey: break
                if bosh.settings['bash.tabs'][key]:
                    insertAt = i+1
            className,title,panel = tabInfo[self.tabKey]
            if not panel:
                panel = globals()[className](bashFrame.notebook)
                tabInfo[self.tabKey][2] = panel
            if insertAt > bashFrame.notebook.GetPageCount():
                bashFrame.notebook.AddPage(panel,title)
            else:
                bashFrame.notebook.InsertPage(insertAt,panel,title)
        bosh.settings['bash.tabs'][self.tabKey] ^= True
        bosh.settings.setChanged('bash.tabs')

#------------------------------------------------------------------------------
class Settings_IconSize(RadioLink):
    def __init__(self, size):
        super(Settings_IconSize, self).__init__()
        self.size = size
        self.text = unicode(size)
        self.help = _(u"Sets the status bar icons to %(size)s pixels") % (
            {'size': unicode(size)})

    def _check(self): return self.size == bosh.settings['bash.statusbar.iconSize']

    def Execute(self,event):
        bosh.settings['bash.statusbar.iconSize'] = self.size
        getStatusBar().UpdateIconSizes()

#------------------------------------------------------------------------------
class Settings_StatusBar_ShowVersions(CheckLink):
    """Show/Hide version numbers for buttons on the statusbar."""
    text = _(u'Show App Version')
    help = _(u"Show/hide version numbers for buttons on the status bar.")

    def _check(self): return bosh.settings['bash.statusbar.showversion']

    def Execute(self,event):
        bosh.settings['bash.statusbar.showversion'] ^= True
        for button in BashStatusBar.buttons:
            if isinstance(button, App_Button):
                if button.gButton:
                    button.gButton.SetToolTip(tooltip(button.tip))
        if bosh.settings['bash.obse.on']:
            for button in App_Button.obseButtons:
                button.gButton.SetToolTip(tooltip(getattr(button,'obseTip',u'')))

#------------------------------------------------------------------------------
class Settings_Languages(TransLink):
    """Menu for available Languages."""
    # TODO(ut): test
    def _decide(self, window, data):
        languages = []
        for file in bosh.dirs['l10n'].list():
            if file.cext == u'.txt' and file.csbody[-3:] != u'new':
                languages.append(file.body)
        if languages:
            subMenu = MenuLink(_(u'Language'))
            for language in languages:
                subMenu.links.append(Settings_Language(language.s))
            if GPath('english') not in languages:
                subMenu.links.append(Settings_Language('English'))
            return subMenu
        else:
            class _NoLang(EnabledLink):
                text = _(u'Language')
                help = _(u"Wrye Bash was unable to detect any translation"
                         u" files.")
                def _enable(self): return False
            return _NoLang()

#------------------------------------------------------------------------------
class Settings_Language(RadioLink):
    """Specific language for Wrye Bash."""
    languageMap = {
        u'chinese (simplified)': _(u'Chinese (Simplified)') + u' (简体中文)',
        u'chinese (traditional)': _(u'Chinese (Traditional)') + u' (繁体中文)',
        u'de': _(u'German') + u' (Deutsch)',
        u'pt_opt': _(u'Portuguese') + u' (português)',
        u'italian': _(u'Italian') + u' (italiano)',
        u'russian': _(u'Russian') + u' (ру́сский язы́к)',
        u'english': _(u'English') + u' (English)',
        }

    def __init__(self,language):
        super(Settings_Language, self).__init__()
        self.language = language
        self.text = self.__class__.languageMap.get(self.language.lower(),
                                                    self.language)

    def _initData(self, window, data):
        bassLang = bass.language if bass.language else locale.getlocale()[0].split('_',1)[0]
        if self.language == bassLang:
            self.help = _(
                "Currently using %(languagename)s as the active language.") % (
                            {'languagename': self.text})
            self.check = True
        else:
            self.help = _(
                "Restart Wrye Bash and use %(languagename)s as the active "
                "language.") % ({'languagename': self.text})
            self.check = False

    def _check(self): return self.check

    def Execute(self,event):
        bassLang = bass.language if bass.language else locale.getlocale()[0].split('_',1)[0]
        if self.language == bassLang: return
        if askYes(_(u'Wrye Bash needs to restart to change languages.  Do you '
                    u'want to restart?'), _(u'Restart Wrye Bash')):
            from . import bashFrame # FIXME(ut): globals
            bashFrame.Restart(('--Language',self.language))

#------------------------------------------------------------------------------
class Settings_PluginEncodings(MenuLink):
    encodings = {
        'gbk': _(u'Chinese (Simplified)'),
        'big5': _(u'Chinese (Traditional)'),
        'cp1251': _(u'Russian'),
        'cp932': _(u'Japanese'),
        'cp1252': _(u'Western European (English, French, German, etc)'),
        }
    def __init__(self):
        super(Settings_PluginEncodings, self).__init__(_(u'Plugin Encoding'))
        bolt.pluginEncoding = bosh.settings['bash.pluginEncoding'] # TODO(ut): why is this init here ??
        self.links.append(Settings_PluginEncoding(_(u'Automatic'),None))
        # self.links.append(SeparatorLink())
        enc_name = sorted(Settings_PluginEncodings.encodings.items(),key=lambda x: x[1])
        for encoding,name in enc_name:
            self.links.append(Settings_PluginEncoding(name,encoding))

#------------------------------------------------------------------------------
class Settings_PluginEncoding(RadioLink):
    def __init__(self,name,encoding):
        super(Settings_PluginEncoding, self).__init__()
        self.text = name
        self.encoding = encoding
        self.help = _("Select %(encodingname)s encoding for Wrye Bash to use."
            ) % ({'encodingname': self.text})

    def _check(self): return self.encoding == bosh.settings[
        'bash.pluginEncoding']

    def Execute(self,event):
        bosh.settings['bash.pluginEncoding'] = self.encoding
        bolt.pluginEncoding = self.encoding

#------------------------------------------------------------------------------
class Settings_Games(MenuLink):

    def __init__(self):
        super(Settings_Games, self).__init__(_(u'Game'))
        foundGames,allGames,name = bush.detectGames() # TODO(ut): is this cached ?
        for game in foundGames:
            game = game[0].upper()+game[1:]
            self.links.append(Settings_Game(game))

class Settings_Game(RadioLink):
    def __init__(self,game):
        super(Settings_Game, self).__init__()
        self.game = self.text = game
        self.help = _("Restart Wrye Bash to manage %(game)s.") % (
            {'game': game})

    def _check(self): return self.game.lower() == bush.game.fsName.lower()

    def Execute(self,event):
        if self.game.lower() == bush.game.fsName.lower(): return
        from . import bashFrame # FIXME(ut): globals
        bashFrame.Restart(('--game',self.game))

#------------------------------------------------------------------------------
class Settings_UnHideButtons(TransLink):
    """Menu to unhide a StatusBar button."""
    # TODO(ut): test
    def _decide(self, window, data):
        hide = bosh.settings['bash.statusbar.hide']
        hidden = []
        for link in BashStatusBar.buttons:
            if link.uid in hide:
                hidden.append(link)
        if hidden:
            subMenu = MenuLink(_(u'Unhide Buttons'))
            for link in hidden:
                subMenu.links.append(Settings_UnHideButton(link))
            return subMenu
        else:
            class _NoButtons(EnabledLink):
                text = _(u'Unhide Buttons')
                help = _(u"No hidden buttons available to unhide.")
                def _enable(self): return False
            return _NoButtons()

#------------------------------------------------------------------------------
class Settings_UnHideButton(_Link):
    """Unhide a specific StatusBar button."""
    def __init__(self,link):
        super(Settings_UnHideButton, self).__init__()
        self.link = link
        button = self.link.gButton
        # Get a title for the hidden button
        if button:
            # If the wx.Button object exists (it was hidden this session),
            # Use the tooltip from it
            tip = button.GetToolTip().GetTip()
        else:
            # If the link is an App_Button, it will have a 'tip' attribute
            tip = getattr(self.link,'tip',None)
        if tip is None:
            # No good, use its uid as a last resort
            tip = self.link.uid
        self.text = tip
        self.help = _(u"Unhide the '%s' status bar button.") % tip

    def Execute(self,event):
        getStatusBar().UnhideButton(self.link)

#------------------------------------------------------------------------------
class Settings_UseAltName(BoolLink):
    text, key, help = _(u'Use Alternate Wrye Bash Name'), 'bash.useAltName', \
        _(u'Use an alternate display name for Wrye Bash based on the game it'
          u' is managing.')

    def Execute(self,event):
        super(Settings_UseAltName, self).Execute(event)
        bashFrameSetTitle()

#------------------------------------------------------------------------------
class Settings_UAC(AppendableLink):
    text = _(u'Administrator Mode')
    help = _(u'Restart Wrye Bash with administrator privileges.')

    def _append(self, window):
        from . import isUAC # FIXME(ut): globals
        return isUAC

    def Execute(self,event):
        if askYes(_(u'Restart Wrye Bash with administrator privileges?'),
                  _(u'Administrator Mode'), ):
            from . import bashFrame # FIXME(ut): globals
            bashFrame.Restart(True,True)
