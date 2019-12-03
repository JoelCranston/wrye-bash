# -*- coding: utf-8 -*-
#
######## BEGIN LICENSE BLOCK ######
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
#
# The contents of this file are subject to the Mozilla Public License Version
# 1.1 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS IS" basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
# for the specific language governing rights and limitations under the
# License.
#
# The Original Code is CBash code.
#
# The Initial Developer of the Original Code is
# Waruddar.
# Portions created by the Initial Developer are Copyright (C) 2010
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#  Wrye Bash Team
#
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
#
####### END LICENSE BLOCK ######

from __future__ import division, print_function
from ctypes import byref, cast, c_bool, c_byte, c_char, c_char_p, c_float, \
    CFUNCTYPE, c_long, c_short, c_ubyte, c_uint32, c_ushort, c_ulong, CDLL, \
    POINTER, string_at, Structure, c_int, c_void_p
import math
import os
from functools import reduce
from os.path import exists, join
try:
    #See if cint is being used by Wrye Bash
    from .bolt import CBash as CBashEnabled
    from .bolt import GPath, deprint, Path
    from .bolt import encode as _enc
    from .bolt import decode as _uni
    from . import bolt
    def _encode(text,*args,**kwdargs):
        if len(args) > 1:
            args = list(args)
            args[1] = bolt.pluginEncoding
        else:
            kwdargs[u'firstEncoding'] = bolt.pluginEncoding
        if isinstance(text,Path): text = text.s
        return _enc(text,*args,**kwdargs)
    def _unicode(text,*args,**kwdargs):
        if args:
            args = list(args)
            args[1] = bolt.pluginEncoding
        else:
            kwdargs[u'encoding'] = bolt.pluginEncoding
        return _uni(text,*args,**kwdargs)
except:
    #It isn't, so replace the imported items with bare definitions
    CBashEnabled = u'.'
    class Path(object):
        pass
    def GPath(obj):
        return obj
    def deprint(obj):
        print(obj)
    def _(obj):
        return obj

    # Unicode ---------------------------------------------------------------------
    #--decode unicode strings
    #  This is only useful when reading fields from mods, as the encoding is not
    #  known.  For normal filesystem interaction, these functions are not needed
    encodingOrder = (
        u'ascii',    # Plain old ASCII (0-127)
        u'gbk',      # GBK (simplified Chinese + some)
        u'cp932',    # Japanese
        u'cp949',    # Korean
        u'cp1252',   # English (extended ASCII)
        u'utf8',
        u'cp500',
        u'UTF-16LE',
        u'mbcs',
    )

    def _unicode(text,encoding=None,avoidEncodings=()):
        if isinstance(text,unicode) or text is None: return text
        # Try the user specified encoding first
        if encoding:
            try: return unicode(text,encoding)
            except UnicodeDecodeError: pass
        # If that fails, fall back to the old method, trial and error
        for encoding in encodingOrder:
            try: return unicode(text,encoding)
            except UnicodeDecodeError: pass
        raise UnicodeDecodeError(u'Text could not be decoded using any method')
    _uni = _unicode

    def _encode(text,encodings=encodingOrder,firstEncoding=None,returnEncoding=False):
        if isinstance(text,str) or text is None:
            if returnEncoding: return (text,None)
            else: return text
        # Try user specified encoding
        if firstEncoding:
            try:
                text = text.encode(firstEncoding)
                if returnEncoding: return (text,firstEncoding)
                else: return text
            except UnicodeEncodeError:
                pass
        # Try the list of encodings in order
        for encoding in encodings:
            try:
                if returnEncoding: return (text.encode(encoding),encoding)
                else: return text.encode(encoding)
            except UnicodeEncodeError:
                pass
        raise UnicodeEncodeError(u'Text could not be encoded using any of the following encodings: %s' % encodings)
    _enc = _encode

class CBashError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

def ZeroIsErrorCheck(result, function, cArguments, *args):
    if result == 0: raise CBashError(u'Function returned error code 0.')
    return result

def NegativeIsErrorCheck(result, function, cArguments, *args):
    if result < 0:
        raise CBashError(u'Function returned error code %i.' % result)
    return result

def PositiveIsErrorCheck(result, function, cArguments, *args):
    if result > 0:
        raise CBashError(u'Function returned error code %i' % result)
    return result

_CBash = None
# Have to hardcode this relative to the cwd, because passing any non-unicode
# characters to CDLL tries to encode them as ASCII and crashes
# PY3: fixed in py3, remove this on upgrade
cb_path = join(u'bash', u'compiled', u'CBash.dll')
if CBashEnabled != 1 and exists(cb_path):
    try:
        from .env import get_file_version
        if get_file_version(cb_path) < (0, 7):
            raise ImportError(u'Bundled CBash version is too old for this '
                              u'Wrye Bash version. Only 0.7.0+ is '
                              u'supported.')
        _CBash = CDLL(cb_path)
    except (AttributeError, ImportError, OSError):
        _CBash = None
        deprint(u'Failed to import CBash.', traceback=True)
    except:
        _CBash = None
        raise

if _CBash:
    def LoggingCB(logString):
        print(logString, end=u' ')
        return 0

    def RaiseCB(raisedString):
        #Raising is mostly worthless in a callback
        #CTypes prints the error, but the traceback is useless
        #and it doesn't propagate properly

        #Apparently...
        #"The standard way of doing something meaningful with the exception is
        #to catch it in the callback, set a global flag, somehow encourage the
        #C code to unwind back to the original Python call and there check the
        #flag and re-raise the exception."

        #But this would lead to a large performance hit if it were checked after
        #every CBash call. An alternative might be to start a separate thread
        #that then raises the error in the main thread after control returns from
        #CBash. Dunno.

        #This particular callback may disappear, or be morphed into something else
        print(u'CBash encountered an error', raisedString, u'Check the log.')
##        raise CBashError("Check the log.")
        return

    # https://stackoverflow.com/a/5030940
    class _CCollection(Structure): pass
    class _CMod(Structure): pass
    class _CRecord(Structure): pass

    c_collection_p = POINTER(_CCollection)
    c_mod_p = POINTER(_CMod)
    c_record_p = POINTER(_CRecord)

    _CGetVersionMajor = _CBash.cb_GetVersionMajor
    _CGetVersionMinor = _CBash.cb_GetVersionMinor
    _CGetVersionRevision = _CBash.cb_GetVersionRevision
    _CCreateCollection = _CBash.cb_CreateCollection
    _CDeleteCollection = _CBash.cb_DeleteCollection
    _CLoadCollection = _CBash.cb_LoadCollection
    _CUnloadCollection = _CBash.cb_UnloadCollection
    _CGetCollectionType = _CBash.cb_GetCollectionType
    _CUnloadAllCollections = _CBash.cb_UnloadAllCollections
    _CDeleteAllCollections = _CBash.cb_DeleteAllCollections
    _CAddMod = _CBash.cb_AddMod
    _CLoadMod = _CBash.cb_LoadMod
    _CUnloadMod = _CBash.cb_UnloadMod
    _CCleanModMasters = _CBash.cb_CleanModMasters
    _CSaveMod = _CBash.cb_SaveMod
    _CGetAllNumMods = _CBash.cb_GetAllNumMods
    _CGetAllModIDs = _CBash.cb_GetAllModIDs
    _CGetLoadOrderNumMods = _CBash.cb_GetLoadOrderNumMods
    _CGetLoadOrderModIDs = _CBash.cb_GetLoadOrderModIDs
    _CGetFileNameByID = _CBash.cb_GetFileNameByID
    _CGetFileNameByLoadOrder = _CBash.cb_GetFileNameByLoadOrder
    _CGetModNameByID = _CBash.cb_GetModNameByID
    _CGetModNameByLoadOrder = _CBash.cb_GetModNameByLoadOrder
    _CGetModIDByName = _CBash.cb_GetModIDByName
    _CGetModIDByLoadOrder = _CBash.cb_GetModIDByLoadOrder
    _CGetModLoadOrderByName = _CBash.cb_GetModLoadOrderByName
    _CGetModLoadOrderByID = _CBash.cb_GetModLoadOrderByID
    _CGetModIDByRecordID = _CBash.cb_GetModIDByRecordID
    _CGetCollectionIDByRecordID = _CBash.cb_GetCollectionIDByRecordID
    _CGetCollectionIDByModID = _CBash.cb_GetCollectionIDByModID
    _CIsModEmpty = _CBash.cb_IsModEmpty
    _CGetModNumTypes = _CBash.cb_GetModNumTypes
    _CGetModTypes = _CBash.cb_GetModTypes
    _CGetModNumEmptyGRUPs = _CBash.cb_GetModNumEmptyGRUPs
    _CGetModNumOrphans = _CBash.cb_GetModNumOrphans
    _CGetModOrphansFormIDs = _CBash.cb_GetModOrphansFormIDs
    _CGetLongIDName = _CBash.cb_GetLongIDName
    _CMakeShortFormID = _CBash.cb_MakeShortFormID
    _CCreateRecord = _CBash.cb_CreateRecord
    _CCopyRecord = _CBash.cb_CopyRecord
    _CUnloadRecord = _CBash.cb_UnloadRecord
    _CResetRecord = _CBash.cb_ResetRecord
    _CDeleteRecord = _CBash.cb_DeleteRecord
    _CGetRecordID = _CBash.cb_GetRecordID
    _CGetNumRecords = _CBash.cb_GetNumRecords
    _CGetRecordIDs = _CBash.cb_GetRecordIDs
    _CIsRecordWinning = _CBash.cb_IsRecordWinning
    _CGetNumRecordConflicts = _CBash.cb_GetNumRecordConflicts
    _CGetRecordConflicts = _CBash.cb_GetRecordConflicts
    _CGetRecordHistory = _CBash.cb_GetRecordHistory
    _CGetNumIdenticalToMasterRecords = _CBash.cb_GetNumIdenticalToMasterRecords
    _CGetIdenticalToMasterRecords = _CBash.cb_GetIdenticalToMasterRecords
    _CIsRecordFormIDsInvalid = _CBash.cb_IsRecordFormIDsInvalid
    _CUpdateReferences = _CBash.cb_UpdateReferences
    _CGetRecordUpdatedReferences = _CBash.cb_GetRecordUpdatedReferences
    _CSetIDFields = _CBash.cb_SetIDFields
    _CSetField = _CBash.cb_SetField
    _CDeleteField = _CBash.cb_DeleteField
    _CGetFieldAttribute = _CBash.cb_GetFieldAttribute
    _CGetField = _CBash.cb_GetField

    _CGetVersionMajor.argtypes = []
    _CGetVersionMinor.argtypes = []
    _CGetVersionRevision.argtypes = []
    _CCreateCollection.argtypes = [c_char_p, c_int]
    _CDeleteCollection.argtypes = [c_collection_p]
    _CLoadCollection.argtypes = [c_collection_p, CFUNCTYPE(c_bool, c_ulong, c_ulong, c_char_p)]
    _CUnloadCollection.argtypes = [c_collection_p]
    _CGetCollectionType.argtypes = [c_collection_p]
    _CUnloadAllCollections.argtypes = []
    _CDeleteAllCollections.argtypes = []
    _CAddMod.argtypes = [c_collection_p, c_char_p, c_int]
    _CLoadMod.argtypes = [c_mod_p]
    _CUnloadMod.argtypes = [c_mod_p]
    _CCleanModMasters.argtypes = [c_mod_p]
    _CSaveMod.argtypes = [c_mod_p, c_int, c_char_p]
    _CGetAllNumMods.argtypes = [c_collection_p]
    _CGetAllModIDs.argtypes = [c_collection_p, POINTER(c_mod_p)]
    _CGetLoadOrderNumMods.argtypes = [c_collection_p]
    _CGetLoadOrderModIDs.argtypes = [c_collection_p, POINTER(c_mod_p)]
    _CGetFileNameByID.argtypes = [c_mod_p]
    _CGetFileNameByLoadOrder.argtypes = [c_collection_p, c_ulong]
    _CGetModNameByID.argtypes = [c_mod_p]
    _CGetModNameByLoadOrder.argtypes = [c_collection_p, c_ulong]
    _CGetModIDByName.argtypes = [c_collection_p, c_char_p]
    _CGetModIDByLoadOrder.argtypes = [c_collection_p, c_ulong]
    _CGetModLoadOrderByName.argtypes = [c_collection_p, c_char_p]
    _CGetModLoadOrderByID.argtypes = [c_mod_p]
    _CGetModIDByRecordID.argtypes = [c_record_p]
    _CGetCollectionIDByRecordID.argtypes = [c_record_p]
    _CGetCollectionIDByModID.argtypes = [c_mod_p]
    _CIsModEmpty.argtypes = [c_mod_p]
    _CGetModNumTypes.argtypes = [c_mod_p]
    _CGetModTypes.argtypes = [c_mod_p, POINTER(c_char * 4)]
    _CGetModNumEmptyGRUPs.argtypes = [c_mod_p]
    _CGetModNumOrphans.argtypes = [c_mod_p]
    _CGetModOrphansFormIDs.argtypes = [c_mod_p, POINTER(c_ulong)]
    _CGetLongIDName.argtypes = [c_record_p, c_ulong, c_bool]
    _CMakeShortFormID.argtypes = [c_mod_p, c_ulong, c_bool]
    _CCreateRecord.argtypes = [c_mod_p, c_ulong, c_ulong, c_char_p, c_record_p, c_int]
    _CCopyRecord.argtypes = [c_record_p, c_mod_p, c_record_p, c_ulong, c_char_p, c_int]
    _CUnloadRecord.argtypes = [c_record_p]
    _CResetRecord.argtypes = [c_record_p]
    _CDeleteRecord.argtypes = [c_record_p]
    _CGetRecordID.argtypes = [c_mod_p, c_ulong, c_char_p]
    _CGetNumRecords.argtypes = [c_mod_p, c_ulong]
    _CGetRecordIDs.argtypes = [c_mod_p, c_ulong, POINTER(c_record_p)]
    _CIsRecordWinning.argtypes = [c_record_p, c_bool]
    _CGetNumRecordConflicts.argtypes = [c_record_p, c_bool]
    _CGetRecordConflicts.argtypes = [c_record_p, POINTER(c_record_p), c_bool]
    _CGetRecordHistory.argtypes = [c_record_p, POINTER(c_record_p)]
    _CGetNumIdenticalToMasterRecords.argtypes = [c_mod_p]
    _CGetIdenticalToMasterRecords.argtypes = [c_mod_p, POINTER(c_record_p)]
    _CIsRecordFormIDsInvalid.argtypes = [c_record_p]
    _CUpdateReferences.argtypes = [c_mod_p, c_record_p, POINTER(c_ulong), POINTER(c_ulong), POINTER(c_ulong), c_ulong]
    _CGetRecordUpdatedReferences.argtypes = [c_collection_p, c_record_p]
    _CSetIDFields.argtypes = [c_record_p, c_ulong, c_char_p]
    field_ids = [c_ulong] * 7
    _CSetField.argtypes = [c_record_p] + field_ids + [c_void_p, c_ulong]
    _CDeleteField.argtypes = [c_record_p] + field_ids
    _CGetFieldAttribute.argtypes = [c_record_p] + field_ids + [c_ulong]
    _CGetField.argtypes = [c_record_p] + field_ids + [c_void_p]

    _CGetVersionMajor.restype = c_ulong
    _CGetVersionMinor.restype = c_ulong
    _CGetVersionRevision.restype = c_ulong
    _CCreateCollection.restype = c_collection_p
    _CDeleteCollection.restype = c_long
    _CLoadCollection.restype = c_long
    _CUnloadCollection.restype = c_long
    _CGetCollectionType.restype = c_long
    _CUnloadAllCollections.restype = c_long
    _CDeleteAllCollections.restype = c_long
    _CAddMod.restype = c_mod_p
    _CLoadMod.restype = c_long
    _CUnloadMod.restype = c_long
    _CCleanModMasters.restype = c_long
    _CSaveMod.restype = c_long
    _CGetAllNumMods.restype = c_long
    _CGetAllModIDs.restype = c_long
    _CGetLoadOrderNumMods.restype = c_long
    _CGetLoadOrderModIDs.restype = c_long
    _CGetFileNameByID.restype = c_char_p
    _CGetFileNameByLoadOrder.restype = c_char_p
    _CGetModNameByID.restype = c_char_p
    _CGetModNameByLoadOrder.restype = c_char_p
    _CGetModIDByName.restype = c_mod_p
    _CGetModIDByLoadOrder.restype = c_mod_p
    _CGetModLoadOrderByName.restype = c_long
    _CGetModLoadOrderByID.restype = c_long
    _CGetModIDByRecordID.restype = c_mod_p
    _CGetCollectionIDByRecordID.restype = c_collection_p
    _CGetCollectionIDByModID.restype = c_collection_p
    _CIsModEmpty.restype = c_ulong
    _CGetModNumTypes.restype = c_long
    _CGetModTypes.restype = c_long
    _CGetModNumEmptyGRUPs.restype = c_long
    _CGetModNumOrphans.restype = c_long
    _CGetModOrphansFormIDs.restype = c_long
    _CGetLongIDName.restype = c_char_p
    _CMakeShortFormID.restype = c_ulong
    _CCreateRecord.restype = c_record_p
    _CCopyRecord.restype = c_record_p
    _CUnloadRecord.restype = c_long
    _CResetRecord.restype = c_long
    _CDeleteRecord.restype = c_long
    _CGetRecordID.restype = c_record_p
    _CGetNumRecords.restype = c_long
    _CGetRecordIDs.restype = c_long
    _CIsRecordWinning.restype = c_long
    _CGetNumRecordConflicts.restype = c_long
    _CGetRecordConflicts.restype = c_long
    _CGetRecordHistory.restype = c_long
    _CGetNumIdenticalToMasterRecords.restype = c_long
    _CGetIdenticalToMasterRecords.restype = c_long
    _CIsRecordFormIDsInvalid.restype = c_long
    _CUpdateReferences.restype = c_long
    _CGetRecordUpdatedReferences.restype = c_long
    _CSetIDFields.restype = c_long
    _CGetFieldAttribute.restype = c_ulong

    _CCreateCollection.errcheck = ZeroIsErrorCheck
    _CDeleteCollection.errcheck = NegativeIsErrorCheck
    _CLoadCollection.errcheck = NegativeIsErrorCheck
    _CUnloadCollection.errcheck = NegativeIsErrorCheck
    _CGetCollectionType.errcheck = NegativeIsErrorCheck
    _CUnloadAllCollections.errcheck = NegativeIsErrorCheck
    _CDeleteAllCollections.errcheck = NegativeIsErrorCheck
    _CAddMod.errcheck = ZeroIsErrorCheck
    _CLoadMod.errcheck = NegativeIsErrorCheck
    _CUnloadMod.errcheck = NegativeIsErrorCheck
    _CCleanModMasters.errcheck = NegativeIsErrorCheck
    _CSaveMod.errcheck = NegativeIsErrorCheck
    _CGetModNumTypes.errcheck = NegativeIsErrorCheck
    _CGetModTypes.errcheck = NegativeIsErrorCheck
    _CGetModNumEmptyGRUPs.errcheck = NegativeIsErrorCheck
    _CGetModNumOrphans.errcheck = NegativeIsErrorCheck
    _CGetModOrphansFormIDs.errcheck = NegativeIsErrorCheck

    LoggingCallback = CFUNCTYPE(c_long, c_char_p)(LoggingCB)
    RaiseCallback = CFUNCTYPE(None, c_char_p)(RaiseCB)
    _CBash.cb_RedirectMessages(LoggingCallback)
    _CBash.cb_AllowRaising(RaiseCallback)

class CBashApi (object):
    Enabled = _CBash is not None

    VersionMajor = _CGetVersionMajor() if Enabled else 0
    VersionMinor = _CGetVersionMinor() if Enabled else 0
    VersionRevision = _CGetVersionRevision() if Enabled else 0
    VersionInfo = (VersionMajor, VersionMinor, VersionRevision)

    VersionText = u'v%u.%u.%u' % VersionInfo if Enabled else u''

#Helper functions
class API_FIELDS(object):
    """These fields MUST be defined in the same order as in CBash's Common.h"""
    __slots__ = [u'UNKNOWN', u'MISSING', u'JUNK', u'BOOL', u'SINT8', u'UINT8',
                 u'SINT16', u'UINT16', u'SINT32', u'UINT32', u'FLOAT32',
                 u'RADIAN', u'FORMID', u'MGEFCODE', u'ACTORVALUE',
                 u'FORMID_OR_UINT32', u'FORMID_OR_FLOAT32', u'UINT8_OR_UINT32',
                 u'FORMID_OR_STRING', u'UNKNOWN_OR_FORMID_OR_UINT32',
                 u'UNKNOWN_OR_SINT32', u'UNKNOWN_OR_UINT32_FLAG',
                 u'MGEFCODE_OR_CHAR4',
                 u'FORMID_OR_MGEFCODE_OR_ACTORVALUE_OR_UINT32',
                 u'RESOLVED_MGEFCODE', u'STATIC_MGEFCODE',
                 u'RESOLVED_ACTORVALUE', u'STATIC_ACTORVALUE', u'CHAR',
                 u'CHAR4', u'STRING', u'ISTRING',
                 u'STRING_OR_FLOAT32_OR_SINT32', u'LIST', u'PARENTRECORD',
                 u'SUBRECORD', u'SINT8_FLAG', u'SINT8_TYPE',
                 u'SINT8_FLAG_TYPE', u'SINT8_ARRAY', u'UINT8_FLAG',
                 u'UINT8_TYPE', u'UINT8_FLAG_TYPE', u'UINT8_ARRAY',
                 u'SINT16_FLAG', u'SINT16_TYPE', u'SINT16_FLAG_TYPE',
                 u'SINT16_ARRAY', u'UINT16_FLAG', u'UINT16_TYPE',
                 u'UINT16_FLAG_TYPE', u'UINT16_ARRAY', u'SINT32_FLAG',
                 u'SINT32_TYPE', u'SINT32_FLAG_TYPE', u'SINT32_ARRAY',
                 u'UINT32_FLAG', u'UINT32_TYPE', u'UINT32_FLAG_TYPE',
                 u'UINT32_ARRAY', u'FLOAT32_ARRAY', u'RADIAN_ARRAY',
                 u'FORMID_ARRAY', u'FORMID_OR_UINT32_ARRAY',
                 u'MGEFCODE_OR_UINT32_ARRAY', u'STRING_ARRAY',
                 u'ISTRING_ARRAY', u'SUBRECORD_ARRAY', u'UNDEFINED']

for value, attr in enumerate(API_FIELDS.__slots__):
    setattr(API_FIELDS, attr, value)

class ICASEMixin(object):
    """Case insensitive string/unicode class mixin.  Performs like str/unicode,
       except comparisons are case insensitive."""
    def __eq__(self, other):
        try: return self.lower() == other.lower()
        except AttributeError: return False

    def __lt__(self, other):
        try: return self.lower() < other.lower()
        except AttributeError: return False

    def __le__(self, other):
        try: return self.lower() <= other.lower()
        except AttributeError: return False

    def __gt__(self, other):
        try: return self.lower() > other.lower()
        except AttributeError: return False

    def __ne__(self, other):
        try: return self.lower() != other.lower()
        except AttributeError: return False

    def __ge__(self, other):
        try: return self.lower() >= other.lower()
        except AttributeError: return False

    def __hash__(self):
        return hash(self.lower())

    def __contains__(self, other):
        try: return other.lower() in self.lower()
        except AttributeError: return False

    def count(self, other, *args):
        try:
            if isinstance(self,str): func = str.count
            else: func = unicode.count
            return func(self.lower(), other.lower(), *args)
        except AttributeError: return 0

    def endswith(self, other, *args):
        try:
            if isinstance(self,str): func = str.endswith
            else: func = unicode.endswith
            if isinstance(other, tuple):
                for value in other:
                    if func(self.lower(), value.lower(), *args):
                        return True
                return False
            return func(self.lower(), other.lower(), *args)
        except AttributeError: return False

    def find(self, other, *args):
        try:
            if isinstance(self,str): func = str.find
            else: func = unicode.find
            return func(self.lower(), other.lower(), *args)
        except AttributeError: return -1

    def index(self, other, *args):
        try:
            if isinstance(self,str): func = str.index
            else: func = unicode.index
            return func(self.lower(), other.lower(), *args)
        except AttributeError: return ValueError

    def rfind(self, other, *args):
        try:
            if isinstance(self,str): func = str.rfind
            else: func = unicode.rfind
            return func(self.lower(), other.lower(), *args)
        except AttributeError: return -1

    def rindex(self, other, *args):
        try:
            if isinstance(self,str): func = str.rindex
            else: func = unicode.rindex
            return func(self.lower(), other.lower(), *args)
        except AttributeError: return ValueError

    def startswith(self, other, *args):
        try:
            if isinstance(self,str): func = str.startswith
            else: func = unicode.startswith
            if isinstance(other, tuple):
                for value in other:
                    if func(self.lower(), value.lower(), *args):
                        return True
                return False
            return func(self.lower(), other.lower(), *args)
        except AttributeError: return False

class ISTRING(ICASEMixin,str):
    """Case insensitive strings class. Performs like str except comparisons are case insensitive."""
    pass

class IUNICODE(ICASEMixin,unicode):
    """Case insensitive unicode class.  Performs like unicode except comparisons
       are case insensitive."""
    pass


class FormID(object):
    """Represents a FormID"""
    __slots__ = [u'formID']

    class UnvalidatedFormID(object):
        """Represents an unchecked FormID. This the most common case by far.

           These occur when:
            1) A hard-coded Long FormID is used
            2) A Long FormID from a csv file is used
            3) Any CBash FormID is used

           It must be tested to see if it is safe for use in a particular collection.
           This class should never be instantiated except by class FormID(object)."""
        __slots__ = [u'master', u'objectID']

        def __init__(self, master, objectID):
            self.master, self.objectID = master, objectID

        def __hash__(self):
            return hash((self.master, self.objectID))

        def __getitem__(self, x):
            return self.master if x == 0 else int(self.objectID & 0x00FFFFFF)

        def __repr__(self):
            return u"UnvalidatedFormID('%s', 0x%06X)" % (self.master, int(self.objectID & 0x00FFFFFF))

        def Validate(self, target):
            """Unvalidated FormIDs have to be tested for each destination collection
               A FormID is valid if its master is part of the destination collection"""
            targetID = target.GetParentCollection()._CollectionID
            modID = _CGetModIDByName(targetID, _encode(self.master))
            return FormID.ValidFormID(self.master, self.objectID, _CMakeShortFormID(modID, self.objectID , 0), targetID) if modID else self

        def GetShortFormID(self, target):
            """Tries to resolve the formID for the given target.
               This should only get called if the FormID isn't validated prior to it being used by CBash."""
            formID = self.Validate(target)
            if isinstance(formID, FormID.ValidFormID): return formID.shortID
            raise TypeError(_(u'Attempted to set an invalid formID'))

    class InvalidFormID(object):
        """Represents an unsafe FormID.
           The FormIDs ModIndex won't properly match with the Collection's Load Order,
           so using it would cause the wrong record to become referenced.

           These occur when CBash is told to skip new records on loading a mod.
           This is most often done for scanned mods in Wrye Bash's Bashed Patch process.

           Invalid FormIDs are unsafe to use for any record in any collection.
           This class should never be instantiated except by class FormID(object)."""
        __slots__ = [u'objectID']

        def __init__(self, objectID):
            self.objectID = objectID

        def __hash__(self):
            return hash((None, self.objectID))

        def __getitem__(self, x):
            return None if x == 0 else int(self.objectID & 0x00FFFFFF)

        def __repr__(self):
            return u'InvalidFormID(None, 0x%06X)' % (self.objectID,)

        def Validate(self, target):
            """No validation is needed. It's invalid."""
            return self

        def GetShortFormID(self, target):
            """It isn't safe to use this formID. Any attempt to resolve it will be wrong."""
            raise TypeError(_(u'Attempted to set an invalid formID'))

    class ValidFormID(object):
        """Represents a safe FormID.

           These occur when an unvalidated FormID is validated for a specific record.
           Technically, the validation is good for an entire collection, but it's rare
           for the same FormID instance to be used for multiple records.

           This class should never be instantiated except by class FormID(object)."""
        __slots__ = [u'master', u'objectID', u'shortID', u'_CollectionID']

        def __init__(self, master, objectID, shortID, collectionID):
            self.master, self.objectID, self.shortID, self._CollectionID = master, objectID, shortID, collectionID

        def __hash__(self):
            return hash((self.master, self.objectID))

        def __getitem__(self, x):
            return self.master if x == 0 else int(self.objectID & 0x00FFFFFF)

        def __repr__(self):
            return u"ValidFormID('%s', 0x%06X)" % (self.master, int(self.objectID & 0x00FFFFFF))

        def Validate(self, target):
            """This FormID has already been validated for a specific collection.
               It must be revalidated if the target being used doesn't match the earlier validation."""
            return self if target.GetParentCollection()._CollectionID == self._CollectionID else FormID.UnvalidatedFormID(self.master, self.objectID).Validate(target)

        def GetShortFormID(self, target):
            """This FormID has already been resolved for a specific record.
               It must be re-resolved if the target being used doesn't match the earlier validation."""
            if target.GetParentCollection()._CollectionID == self._CollectionID: return self.shortID
            test = FormID.UnvalidatedFormID(self.master, self.objectID).Validate(target)
            if isinstance(test, FormID.ValidFormID): return test.shortID
            raise TypeError(_(u'Attempted to set an invalid formID'))

    class EmptyFormID(ValidFormID):
        """Represents an empty FormID.

           These occur when a particular field isn't set, or is set to 0.

           Empty FormIDs are safe to use for any record in any collection.
           This class should never be instantiated except by class FormID(object)."""
        __slots__ = []

        def __init__(self):
            pass

        def __hash__(self):
            return hash(0)

        def __getitem__(self, x):
            return None

        def __repr__(self):
            return u'EmptyFormID(None, None)'

        def Validate(self, target):
            """No validation is needed. There's nothing to validate."""
            return self

        def GetShortFormID(self, target):
            """An empty FormID is always valid, so it isn't resolved. That's why it subclasses ValidFormID."""
            return 0

    class RawFormID(ValidFormID):
        """Represents a non-checkable FormID. Should rarely be used due to safety issues.
           This class should never be instantiated except by class FormID(object)."""
        __slots__ = [u'shortID']

        def __init__(self, shortID):
            self.shortID = shortID

        def __hash__(self):
            return hash((self.shortID, None))

        def __getitem__(self, x):
            return self.shortID >> 24 if x == 0 else int(self.shortID & 0x00FFFFFF)

        def __repr__(self):
            return u'RawFormID(0x%08X)' % (self.shortID,)

        def Validate(self, target):
            """No validation is possible. It is impossible to tell what collection the value came from."""
            return self

        def GetShortFormID(self, target):
            """The raw FormID isn't resolved, so it's always valid. That's why it subclasses ValidFormID."""
            return self.shortID

    def __init__(self, master, objectID=None):
        """Initializes a FormID from these possible inputs:
           CBash FormID = (int(RecordID)   , int(FormID)) Internal use by CBash / cint only!
           Long FormID  = (string(ModName) , int(ObjectID))
           FormID       = (FormID()        , None)
           Raw FormID   = (int(FormID)     , None)
           Empty FormID = (None            , None)"""
        self.formID = FormID.EmptyFormID() if master is None else master.formID if isinstance(master, FormID) else FormID.RawFormID(master) if objectID is None else FormID.UnvalidatedFormID(GPath(master), objectID) if isinstance(master, (basestring, Path)) else None
        if self.formID is None:
            masterstr = _CGetLongIDName(master, objectID, 0)
            self.formID = FormID.ValidFormID(GPath(masterstr), objectID, objectID, _CGetCollectionIDByRecordID(master)) if masterstr else FormID.InvalidFormID(objectID)

    def __hash__(self):
        return hash(self.formID)

    def __eq__(self, other):
        if other is None and isinstance(self.formID, FormID.EmptyFormID): return True
        try: return other[1] == self.formID[1] and other[0] == self.formID[0]
        except TypeError: return False

    def __ne__(self, other):
        try: return other[1] != self.formID[1] or other[0] != self.formID[0]
        except TypeError: return False

    def __bool__(self):
        return not isinstance(self.formID, (FormID.EmptyFormID, FormID.InvalidFormID))
    # PY3: get rid of this once we port
    __nonzero__ = __bool__

    def __getitem__(self, x):
        return self.formID[0] if x == 0 else self.formID[1]

    def __setitem__(self, x, nValue):
        if x == 0: self.formID = FormID.EmptyFormID() if nValue is None else FormID.UnvalidatedFormID(nValue, self.formID[1]) if isinstance(nValue, basestring) else FormID.RawFormID(nValue)
        else: self.formID = FormID.UnvalidatedFormID(self.formID[0], nValue) if nValue is not None else FormID.EmptyFormID() if self.formID[0] is None else FormID.RawFormID(self.formID[0])

    def __len__(self):
        return 2

    def __repr__(self):
        return self.formID.__repr__()

    def __str__(self):
        return self.formID.__repr__()

    @staticmethod
    def FilterValid(formIDs, target, AsShort=False):
        if AsShort: return [x.GetShortFormID(target) for x in formIDs if x.ValidateFormID(target)]
        return [x for x in formIDs if x.ValidateFormID(target)]

    @staticmethod
    def FilterValidDict(formIDs, target, KeysAreFormIDs, ValuesAreFormIDs, AsShort=False):
        if KeysAreFormIDs:
            if ValuesAreFormIDs:
                if AsShort: return dict([(key.GetShortFormID(target), value.GetShortFormID(target)) for key, value in formIDs.iteritems() if key.ValidateFormID(target) and value.ValidateFormID(target)])
                return dict([(key, value) for key, value in formIDs.iteritems() if key.ValidateFormID(target) and value.ValidateFormID(target)])
            if AsShort: return dict([(key.GetShortFormID(target), value) for key, value in formIDs.iteritems() if key.ValidateFormID(target)])
            return dict([(key, value) for key, value in formIDs.iteritems() if key.ValidateFormID(target)])
        if ValuesAreFormIDs:
            if AsShort: return dict([(key, value.GetShortFormID(target)) for key, value in formIDs.iteritems() if value.ValidateFormID(target)])
            return dict([(key, value) for key, value in formIDs.iteritems() if value.ValidateFormID(target)])
        return formIDs

    def ValidateFormID(self, target):
        """Tests whether the FormID is valid for the destination.
           The test result is saved, so work isn't duplicated if FormIDs are first
           filtered for validity before being set by CBash with GetShortFormID."""
        self.formID = self.formID.Validate(target)
        return isinstance(self.formID, FormID.ValidFormID)

    def GetShortFormID(self, target):
        """Resolves the various FormID classes to a single 32-bit value used by CBash"""
        return self.formID.GetShortFormID(target)

class ActorValue(object):
    """Represents an OBME ActorValue. It is mostly identical to a FormID in resolution.
       The difference lay in that it is only resolved if the value is >= 0x800"""
    __slots__ = [u'actorValue']

    class UnvalidatedActorValue(object):
        """Represents an unchecked ActorValue. This the most common case by far.

           These occur when:
            1) A hard-coded Long ActorValue is used
            2) A Long ActorValue from a csv file is used
            3) Any CBash ActorValue is used

           It must be tested to see if it is safe for use in a particular collection.
           This class should never be instantiated except by class ActorValue(object)."""
        __slots__ = [u'master', u'objectID']

        def __init__(self, master, objectID):
            self.master, self.objectID = master, objectID

        def __hash__(self):
            return hash((self.master, self.objectID))

        def __getitem__(self, x):
            return self.master if x == 0 else int(self.objectID & 0x00FFFFFF)

        def __repr__(self):
            return u"UnvalidatedActorValue('%s', 0x%06X)" % (self.master, int(self.objectID & 0x00FFFFFF))

        def Validate(self, target):
            """Unvalidated ActorValues have to be tested for each destination collection.
               A ActorValue is valid if its master is part of the destination collection.

               Resolved Actor Value's are not formIDs, but can be treated as such for resolution."""
            targetID = target.GetParentCollection()._CollectionID
            modID = _CGetModIDByName(targetID, _encode(self.master))
            return ActorValue.ValidActorValue(self.master, self.objectID, _CMakeShortFormID(modID, self.objectID , 0), targetID) if modID else self

        def GetShortActorValue(self, target):
            """Tries to resolve the ActorValue for the given record.
               This should only get called if the ActorValue isn't validated prior to it being used by CBash."""
            actorValue = self.Validate(target)
            if isinstance(actorValue, ActorValue.ValidActorValue): return actorValue.shortID
            raise TypeError(_(u'Attempted to set an invalid actorValue'))

    class InvalidActorValue(object):
        """Represents an unsafe ActorValue.
           The ActorValues ModIndex won't properly match with the Collection's Load Order,
           so using it would cause the wrong record to become referenced.

           These occur when CBash is told to skip new records on loading a mod.
           This is most often done for scanned mods in Wrye Bash's Bashed Patch process.

           Invalid ActorValues are unsafe to use for any record in any collection.
           This class should never be instantiated except by class ActorValue(object)."""
        __slots__ = [u'objectID']

        def __init__(self, objectID):
            self.objectID = objectID

        def __hash__(self):
            return hash((None, self.objectID))

        def __getitem__(self, x):
            return None if x == 0 else int(self.objectID & 0x00FFFFFF)

        def __repr__(self):
            return u'InvalidActorValue(None, 0x%06X)' % (self.objectID,)

        def Validate(self, target):
            """No validation is needed. It's invalid."""
            return self

        def GetShortActorValue(self, target):
            """It isn't safe to use this ActorValue. Any attempt to resolve it will be wrong."""
            raise TypeError(_(u'Attempted to set an invalid actorValue'))

    class ValidActorValue(object):
        """Represents a safe ActorValue.

           These occur when an unvalidated ActorValue is validated for a specific record.
           Technically, the validation is good for an entire collection, but it's rare
           for the same ActorValue instance to be used for multiple records.

           This class should never be instantiated except by class ActorValue(object)."""
        __slots__ = [u'master', u'objectID', u'shortID', u'_CollectionID']

        def __init__(self, master, objectID, shortID, collectionID):
            self.master, self.objectID, self.shortID, self._CollectionID = master, objectID, shortID, collectionID

        def __hash__(self):
            return hash((self.master, self.objectID))

        def __getitem__(self, x):
            return self.master if x == 0 else int(self.objectID & 0x00FFFFFF)

        def __repr__(self):
            return u"ValidActorValue('%s', 0x%06X)" % (self.master, int(self.objectID & 0x00FFFFFF))

        def Validate(self, target):
            """This ActorValue has already been validated for a specific record.
               It must be revalidated if the record being used doesn't match the earlier validation."""
            return self if target.GetParentCollection()._CollectionID == self._CollectionID else ActorValue.UnvalidatedActorValue(self.master, self.objectID).Validate(target)

        def GetShortActorValue(self, target):
            """This ActorValue has already been resolved for a specific record.
               It must be re-resolved if the record being used doesn't match the earlier validation."""
            if target.GetParentCollection()._CollectionID == self._CollectionID: return self.shortID
            test = ActorValue.UnvalidatedActorValue(self.master, self.objectID).Validate(target)
            if isinstance(test, ActorValue.ValidActorValue): return test.shortID
            raise TypeError(_(u'Attempted to set an invalid actorValue'))

    class EmptyActorValue(ValidActorValue):
        """Represents an empty ActorValue.

           These occur when a particular field isn't set, or is set to 0.

           Empty ActorValues are safe to use for any record in any collection.
           This class should never be instantiated except by class ActorValue(object)."""
        __slots__ = []

        def __init__(self):
            pass

        def __hash__(self):
            return hash(0)

        def __getitem__(self, x):
            return None

        def __repr__(self):
            return u'EmptyActorValue(None, None)'

        def Validate(self, target):
            """No validation is needed. There's nothing to validate."""
            return self

        def GetShortActorValue(self, target):
            """An empty ActorValue isn't resolved, because it's always valid. That's why it subclasses ValidActorValue."""
            return None

    class RawActorValue(ValidActorValue):
        """Represents a non-checked ActorValue. It is either a static ActorValue, or a non-checkable ActorValue.
           Raw ActorValues < 0x800 (static) are safe since they aren't resolved,
           but raw values >= 0x800 should rarely be used due to safety issues.
           This class should never be instantiated except by class ActorValue(object)."""
        __slots__ = [u'shortID']

        def __init__(self, shortID):
            self.shortID = shortID

        def __hash__(self):
            return hash((self.shortID, None))

        def __getitem__(self, x):
            return self.shortID >> 24 if x == 0 else int(self.shortID & 0x00FFFFFF)

        def __repr__(self):
            return u'RawActorValue(0x%08X)' % (self.shortID,)

        def Validate(self, target):
            """No validation is possible. It is impossible to tell what collection the value came from."""
            return self

        def GetShortActorValue(self, target):
            """The raw ActorValue isn't resolved, so it's always valid. That's why it subclasses ValidActorValue."""
            return self.shortID


    def __init__(self, master, objectID=None):
        """Initializes an OBME ActorValue from these possible inputs:
           CBash ActorValue  = (int(RecordID)   , int(ActorValue)) Internal use by CBash / cint only!
           Long ActorValue   = (string(ModName) , int(ObjectID))
           ActorValue        = (ActorValue()    , None)
           Raw ActorValue    = (int(ActorValue) , None)
           Empty ActorValue  = (None            , None))"""
        self.actorValue = ActorValue.EmptyActorValue() if master is None else master.actorValue if isinstance(master, ActorValue) else ActorValue.RawActorValue(master) if objectID is None else ActorValue.UnvalidatedActorValue(GPath(master), objectID) if isinstance(master, (basestring, Path)) else ActorValue.RawActorValue(objectID) if objectID < 0x800 else None
        if self.actorValue is None:
            masterstr = _CGetLongIDName(master, objectID, 0)
            self.actorValue = ActorValue.ValidActorValue(GPath(masterstr), objectID, objectID, _CGetCollectionIDByRecordID(master)) if masterstr else ActorValue.InvalidActorValue(objectID)

    def __hash__(self):
        return hash(self.actorValue)

    def __eq__(self, other):
        if other is None and isinstance(self.actorValue, ActorValue.EmptyActorValue): return True
        try: return other[1] == self.actorValue[1] and other[0] == self.actorValue[0]
        except TypeError: return False

    def __ne__(self, other):
        try: return other[1] != self.actorValue[1] or other[0] != self.actorValue[0]
        except TypeError: return False

    def __bool__(self):
        return not isinstance(self.actorValue, (ActorValue.EmptyActorValue, ActorValue.InvalidActorValue))
    # PY3: get rid of this once we port
    __nonzero__ = __bool__

    def __getitem__(self, x):
        return self.actorValue[0] if x == 0 else self.actorValue[1]

    def __setitem__(self, x, nValue):
        if x == 0: self.actorValue = ActorValue.EmptyActorValue() if nValue is None else ActorValue.UnvalidatedActorValue(nValue, self.actorValue[1]) if isinstance(nValue, basestring) else ActorValue.RawActorValue(nValue)
        else:
            if nValue is None: self.actorValue = ActorValue.EmptyActorValue() if self.actorValue[0] is None else ActorValue.RawActorValue(self.actorValue[0])
            else: self.actorValue = ActorValue.RawActorValue(nValue) if nValue < 0x800 else ActorValue.UnvalidatedActorValue(self.actorValue[0], nValue)

    def __len__(self):
        return 2

    def __repr__(self):
        return self.actorValue.__repr__()

    def __str__(self):
        return self.actorValue.__repr__()

    @staticmethod
    def FilterValid(ActorValues, target, AsShort=False):
        if AsShort: return [x.GetShortActorValue(target) for x in ActorValues if x.ValidateActorValue(target)]
        return [x for x in ActorValues if x.ValidateActorValue(target)]

    @staticmethod
    def FilterValidDict(ActorValues, target, KeysAreActorValues, ValuesAreActorValues, AsShort=False):
        if KeysAreActorValues:
            if ValuesAreActorValues:
                if AsShort: return dict([(key.GetShortActorValue(target), value.GetShortFormID(target)) for key, value in ActorValues.iteritems() if key.ValidateActorValue(target) and value.ValidateActorValue(target)])
                return dict([(key, value) for key, value in ActorValues.iteritems() if key.ValidateActorValue(target) and value.ValidateActorValue(target)])
            if AsShort: return dict([(key.GetShortActorValue(target), value) for key, value in ActorValues.iteritems() if key.ValidateActorValue(target)])
            return dict([(key, value) for key, value in ActorValues.iteritems() if key.ValidateActorValue(target)])
        if ValuesAreActorValues:
            if AsShort: return dict([(key, value.GetShortActorValue(target)) for key, value in ActorValues.iteritems() if value.ValidateActorValue(target)])
            return dict([(key, value) for key, value in ActorValues.iteritems() if value.ValidateActorValue(target)])
        return ActorValues

    def ValidateActorValue(self, target):
        """Tests whether the ActorValue is valid for the destination target.
           The test result is saved, so work isn't duplicated if ActorValues are first
           filtered for validity before being set by CBash with GetShortActorValue."""
        self.actorValue = self.actorValue.Validate(target)
        return isinstance(self.actorValue, ActorValue.ValidActorValue)

    def GetShortActorValue(self, target):
        """Resolves the various ActorValue classes to a single 32-bit value used by CBash"""
        return self.actorValue.GetShortActorValue(target)

class MGEFCode(object):
    """Represents an OBME MGEFCode. It is mostly identical to a FormID in resolution.
       The difference lay in that it is only resolved if the value is >= 0x80000000,
       and that the ModIndex is in the lower bits."""
    __slots__ = [u'mgefCode']

    class UnvalidatedMGEFCode(object):
        """Represents an unchecked MGEFCode. This the most common case by far.

           These occur when:
            1) A hard-coded Long MGEFCode is used
            2) A Long MGEFCode from a csv file is used
            3) Any CBash MGEFCode is used

           It must be tested to see if it is safe for use in a particular collection.
           This class should never be instantiated except by class MGEFCode(object)."""
        __slots__ = [u'master', u'objectID']

        def __init__(self, master, objectID):
            self.master, self.objectID = master, objectID

        def __hash__(self):
            return hash((self.master, self.objectID))

        def __getitem__(self, x):
            return self.master if x == 0 else int(self.objectID & 0xFFFFFF00)

        def __repr__(self):
            return u"UnvalidatedMGEFCode('%s', 0x%06X)" % (self.master, int(self.objectID & 0xFFFFFF00))

        def Validate(self, target):
            """Unvalidated MGEFCodes have to be tested for each destination collection.
               A MGEFCode is valid if its master is part of the destination collection.

               Resolved MGEFCode's are not formIDs, but can be treated as such for resolution."""
            targetID = target.GetParentCollection()._CollectionID
            modID = _CGetModIDByName(targetID, _encode(self.master))
            return MGEFCode.ValidMGEFCode(self.master, self.objectID, _CMakeShortFormID(modID, self.objectID , 1), targetID) if modID else self

        def GetShortMGEFCode(self, target):
            """Tries to resolve the MGEFCode for the given record.
               This should only get called if the MGEFCode isn't validated prior to it being used by CBash."""
            mgefCode = self.Validate(target)
            if isinstance(mgefCode, MGEFCode.ValidMGEFCode): return mgefCode.shortID
            raise TypeError(_(u'Attempted to set an invalid mgefCode'))

    class InvalidMGEFCode(object):
        """Represents an unsafe MGEFCode.
           The MGEFCodes ModIndex won't properly match with the Collection's Load Order,
           so using it would cause the wrong record to become referenced.

           These occur when CBash is told to skip new records on loading a mod.
           This is most often done for scanned mods in Wrye Bash's Bashed Patch process.

           Invalid MGEFCodes are unsafe to use for any record in any collection.
           This class should never be instantiated except by class MGEFCode(object)."""
        __slots__ = [u'objectID']

        def __init__(self, objectID):
            self.objectID = objectID

        def __hash__(self):
            return hash((None, self.objectID))

        def __getitem__(self, x):
            return None if x == 0 else int(self.objectID & 0xFFFFFF00)

        def __repr__(self):
            return u'InvalidMGEFCode(None, 0x%06X)' % (self.objectID,)

        def Validate(self, target):
            """No validation is needed. It's invalid."""
            return self

        def GetShortMGEFCode(self, target):
            """It isn't safe to use this MGEFCode. Any attempt to resolve it will be wrong."""
            raise TypeError(_(u'Attempted to set an invalid mgefCode'))

    class ValidMGEFCode(object):
        """Represents a safe MGEFCode.

           These occur when an unvalidated MGEFCode is validated for a specific record.
           Technically, the validation is good for an entire collection, but it's rare
           for the same MGEFCode instance to be used for multiple records.

           This class should never be instantiated except by class MGEFCode(object)."""
        __slots__ = [u'master', u'objectID', u'shortID', u'_CollectionID']

        def __init__(self, master, objectID, shortID, collectionID):
            self.master, self.objectID, self.shortID, self._CollectionID = master, objectID, shortID, collectionID

        def __hash__(self):
            return hash((self.master, self.objectID))

        def __getitem__(self, x):
            return self.master if x == 0 else int(self.objectID & 0xFFFFFF00)

        def __repr__(self):
            return u"ValidMGEFCode('%s', 0x%06X)" % (self.master, int(self.objectID & 0xFFFFFF00))

        def Validate(self, target):
            """This MGEFCode has already been validated for a specific record.
               It must be revalidated if the record being used doesn't match the earlier validation."""
            return self if target.GetParentCollection()._CollectionID == self._CollectionID else MGEFCode.UnvalidatedMGEFCode(self.master, self.objectID).Validate(target)

        def GetShortMGEFCode(self, target):
            """This MGEFCode has already been resolved for a specific record.
               It must be re-resolved if the record being used doesn't match the earlier validation."""
            if target.GetParentCollection()._CollectionID == self._CollectionID: return self.shortID
            test = MGEFCode.UnvalidatedMGEFCode(self.master, self.objectID).Validate(target)
            if isinstance(test, MGEFCode.ValidMGEFCode): return test.shortID
            raise TypeError(_(u'Attempted to set an invalid mgefCode'))

    class EmptyMGEFCode(ValidMGEFCode):
        """Represents an empty MGEFCode.

           These occur when a particular field isn't set, or is set to 0.

           Empty MGEFCodes are safe to use for any record in any collection.
           This class should never be instantiated except by class MGEFCode(object)."""
        __slots__ = []

        def __init__(self):
            pass

        def __hash__(self):
            return hash(0)

        def __getitem__(self, x):
            return None

        def __repr__(self):
            return u'EmptyMGEFCode(None, None)'

        def Validate(self, target):
            """No validation is needed. There's nothing to validate."""
            return self

        def GetShortMGEFCode(self, target):
            """An empty MGEFCode isn't resolved, because it's always valid. That's why it subclasses ValidMGEFCode."""
            return None

    class RawMGEFCode(ValidMGEFCode):
        """Represents a non-checked MGEFCode. It is either a static MGEFCode, or a non-checkable MGEFCode.
           Raw MGEFCodes < 0x80000000 (static) are safe since they aren't resolved,
           but raw values >= 0x80000000 should rarely be used due to safety issues.

           Without OBME, all MGEFCodes may be displayed as a 4 character sequence.
           Ex: SEFF for Script Effect

           This class should never be instantiated except by class MGEFCode(object)."""
        __slots__ = [u'shortID']

        def __init__(self, shortID):
            self.shortID = (str(shortID) if isinstance(shortID,ISTRING)
                            else _encode(shortID) if isinstance(shortID,unicode)
                            else shortID)

        def __hash__(self):
            return hash((self.shortID, None))

        def __getitem__(self, x):
            return self.shortID if isinstance(self.shortID, basestring) else self.shortID >> 24 if x == 0 else int(self.shortID & 0xFFFFFF00)

        def __repr__(self):
            return u'RawMGEFCode(%s)' % (self.shortID,) if isinstance(self.shortID, basestring) else u'RawMGEFCode(0x%08X)' % (self.shortID,)

        def Validate(self, target):
            """No validation is possible. It is impossible to tell what collection the value came from."""
            return self

        def GetShortMGEFCode(self, target):
            """The raw MGEFCode isn't resolved, so it's always valid. That's why it subclasses ValidMGEFCode.
               If it is using a 4 character sequence, it needs to be cast as a 32 bit integer."""
            return cast(self.shortID, POINTER(c_ulong)).contents.value if isinstance(self.shortID, basestring) else self.shortID


    def __init__(self, master, objectID=None):
        """Initializes an OBME MGEFCode from these possible inputs:
           CBash MGEFCode     = (int(RecordID)   , int(MGEFCode)) Internal use by CBash / cint only!
           CBash Raw MGEFCode = (int(RecordID)   , string(MGEFCode)) Internal use by CBash / cint only!
           Long MGEFCode      = (string(ModName) , int(ObjectID))
           MGEFCode           = (MGEFCode()      , None)
           Raw MGEFCode       = (int(MGEFCode)   , None)
           Raw MGEFCode       = (string(MGEFCode), None)
           Empty MGEFCode     = (None            , None))"""
        self.mgefCode = MGEFCode.EmptyMGEFCode() if master is None else master.mgefCode if isinstance(master, MGEFCode) else MGEFCode.RawMGEFCode(master) if objectID is None else MGEFCode.RawMGEFCode(objectID) if isinstance(objectID, basestring) else MGEFCode.UnvalidatedMGEFCode(GPath(master), objectID) if isinstance(master, (basestring, Path)) else MGEFCode.RawMGEFCode(objectID) if objectID < 0x80000000 else None
        if self.mgefCode is None:
            masterstr = _CGetLongIDName(master, objectID, 1)
            self.mgefCode = MGEFCode.ValidMGEFCode(GPath(masterstr), objectID, objectID, _CGetCollectionIDByRecordID(master)) if masterstr else MGEFCode.InvalidMGEFCode(objectID)

    def __hash__(self):
        return hash(self.mgefCode)

    def __eq__(self, other):
        if other is None and isinstance(self.mgefCode, MGEFCode.EmptyMGEFCode): return True
        try: return other[1] == self.mgefCode[1] and other[0] == self.mgefCode[0]
        except TypeError: return False

    def __ne__(self, other):
        return other[1] != self.mgefCode[1] or other[0] != self.mgefCode[0]

    def __bool__(self):
        return not isinstance(self.mgefCode, (MGEFCode.EmptyMGEFCode, MGEFCode.InvalidMGEFCode))
    # PY3: get rid of this once we port
    __nonzero__ = __bool__

    def __getitem__(self, x):
        return self.mgefCode[0] if x == 0 else self.mgefCode[1]

    def __setitem__(self, x, nValue):
        if x == 0: self.mgefCode = MGEFCode.EmptyMGEFCode() if nValue is None else MGEFCode.UnvalidatedMGEFCode(nValue, self.mgefCode[1]) if isinstance(nValue, basestring) else MGEFCode.RawMGEFCode(nValue)
        else:
            if nValue is None: self.mgefCode = MGEFCode.EmptyMGEFCode() if self.mgefCode[0] is None else MGEFCode.RawMGEFCode(self.mgefCode[0])
            else: self.mgefCode = MGEFCode.RawMGEFCode(nValue) if nValue < 0x80000000 else MGEFCode.UnvalidatedMGEFCode(self.mgefCode[0], nValue)

    def __len__(self):
        return 2

    def __repr__(self):
        return self.mgefCode.__repr__()

    def __str__(self):
        return self.mgefCode.__repr__()

    @staticmethod
    def FilterValid(mgefCodes, target, AsShort=False):
        if AsShort: return [x.GetShortMGEFCode(target) for x in mgefCodes if x.ValidateMGEFCode(target)]
        return [x for x in mgefCodes if x.ValidateMGEFCode(target)]

    @staticmethod
    def FilterValidDict(mgefCodes, target, KeysAreMGEFCodes, ValuesAreMGEFCodes, AsShort=False):
        if KeysAreMGEFCodes:
            if ValuesAreMGEFCodes:
                if AsShort: return dict([(key.GetShortMGEFCode(target), value.GetShortFormID(target)) for key, value in mgefCodes.iteritems() if key.ValidateMGEFCode(target) and value.ValidateMGEFCode(target)])
                return dict([(key, value) for key, value in mgefCodes.iteritems() if key.ValidateMGEFCode(target) and value.ValidateMGEFCode(target)])
            if AsShort: return dict([(key.GetShortMGEFCode(target), value) for key, value in mgefCodes.iteritems() if key.ValidateMGEFCode(target)])
            return dict([(key, value) for key, value in mgefCodes.iteritems() if key.ValidateMGEFCode(target)])
        if ValuesAreMGEFCodes:
            if AsShort: return dict([(key, value.GetShortMGEFCode(target)) for key, value in mgefCodes.iteritems() if value.ValidateMGEFCode(target)])
            return dict([(key, value) for key, value in mgefCodes.iteritems() if value.ValidateMGEFCode(target)])
        return mgefCodes

    def ValidateMGEFCode(self, target):
        """Tests whether the MGEFCode is valid for the destination RecordID.
           The test result is saved, so work isn't duplicated if MGEFCodes are first
           filtered for validity before being set by CBash with GetShortMGEFCode."""
        self.mgefCode = self.mgefCode.Validate(target)
        return isinstance(self.mgefCode, MGEFCode.ValidMGEFCode)

    def GetShortMGEFCode(self, target):
        """Resolves the various MGEFCode classes to a single 32-bit value used by CBash"""
        return self.mgefCode.GetShortMGEFCode(target)

def ValidateList(Elements, target):
    """Convenience function to ensure that a tuple/list of values is valid for the destination.
       Supports nested tuple/list values.
       Returns true if all of the FormIDs/ActorValues/MGEFCodes in the tuple/list are valid."""
    for element in Elements:
        if isinstance(element, FormID) and not element.ValidateFormID(target): return False
        elif isinstance(element, ActorValue) and not element.ValidateActorValue(target): return False
        elif isinstance(element, MGEFCode) and not element.ValidateMGEFCode(target): return False
        elif isinstance(element, (tuple, list)) and not ValidateList(element, target): return False
    return True

def ValidateDict(Elements, target):
    """Convenience function to ensure that a dict is valid for the destination.
       Supports nested dictionaries, and tuple/list values.
       Returns true if all of the FormIDs/ActorValues/MGEFCodes in the dict are valid."""
    for key, value in Elements.iteritems():
        if isinstance(key, FormID) and not key.ValidateFormID(target): return False
        elif isinstance(key, ActorValue) and not key.ValidateActorValue(target): return False
        elif isinstance(key, MGEFCode) and not key.ValidateMGEFCode(target): return False
        elif isinstance(value, FormID) and not value.ValidateFormID(target): return False
        elif isinstance(value, ActorValue) and not value.ValidateActorValue(target): return False
        elif isinstance(value, MGEFCode) and not value.ValidateMGEFCode(target): return False
        elif isinstance(key, tuple) and not ValidateList(key, target): return False
        elif isinstance(value, (tuple, list)) and not ValidateList(value, target): return False
        elif isinstance(value, dict) and not ValidateDict(value, target): return False
    return True

def getattr_deep(obj, attr):
    return reduce(getattr, attr.split(u'.'), obj)

def setattr_deep(obj, attr, value):
    attrs = attr.split(u'.')
    setattr(reduce(getattr, attrs[:-1], obj), attrs[-1], value)

def ExtractCopyList(Elements):
    return [tuple(getattr(listElement, attr) for attr in listElement.copyattrs) for listElement in Elements]

def SetCopyList(oElements, nValues):
    for oElement, nValueTuple in zip(oElements, nValues):
        for nValue, attr in zip(nValueTuple, oElement.copyattrs):
            setattr(oElement, attr, nValue)

def ExtractExportList(Element):
    try: return [tuple(ExtractExportList(listElement) if hasattr(listElement, u'exportattrs') else getattr(listElement, attr) for attr in listElement.exportattrs) for listElement in Element]
    except TypeError: return [tuple(ExtractExportList(getattr(Element, attr)) if hasattr(getattr(Element, attr), u'exportattrs') else getattr(Element, attr) for attr in Element.exportattrs)]

_dump_RecIndent = 2
_dump_LastIndent = _dump_RecIndent
_dump_ExpandLists = True

def dump_record(record, expand=False):
    def printRecord(record):
        def fflags(y):
            for x in xrange(32):
                z = 1 << x
                if y & z == z:
                    print(hex(z))
        global _dump_RecIndent
        global _dump_LastIndent
        if hasattr(record, u'copyattrs'):
            if _dump_ExpandLists == True:
                msize = max([len(attr) for attr in record.copyattrs if not attr.endswith(u'_list')])
            else:
                msize = max([len(attr) for attr in record.copyattrs])
            for attr in record.copyattrs:
                wasList = False
                if _dump_ExpandLists == True:
                    if attr.endswith(u'_list'):
                        attr = attr[:-5]
                        wasList = True
                rec = getattr(record, attr)
                if _dump_RecIndent: print(u' ' * (_dump_RecIndent - 1), end=u' ')
                if wasList:
                    print(attr)
                else:
                    print(attr + u' ' * (msize - len(attr)), u':', end=u' ')
                if rec is None:
                    print(rec)
                elif u'flag' in attr.lower() or u'service' in attr.lower():
                    print(hex(rec))
                    if _dump_ExpandLists == True:
                        for x in xrange(32):
                            z = pow(2, x)
                            if rec & z == z:
                                print(u' ' * _dump_RecIndent, u' Active' + u' ' * (msize - len(u'  Active')), u'  :', hex(z))
                elif isinstance(rec, list):
                    if len(rec) > 0:
                        IsFidList = True
                        for obj in rec:
                            if not isinstance(obj, FormID):
                                IsFidList = False
                                break
                        if IsFidList:
                            print(rec)
                        elif not wasList:
                            print(rec)
                    elif not wasList:
                        print(rec)
                elif isinstance(rec, basestring):
                    print(repr(rec))
                elif not wasList:
                    print(rec)
                _dump_RecIndent += 2
                printRecord(rec)
                _dump_RecIndent -= 2
        elif isinstance(record, list):
            if len(record) > 0:
                if hasattr(record[0], u'copyattrs'):
                    _dump_LastIndent = _dump_RecIndent
                    for rec in record:
                        printRecord(rec)
                        if _dump_LastIndent == _dump_RecIndent:
                            print()
    global _dump_ExpandLists
    _dump_ExpandLists = expand
    try:
        msize = max([len(attr) for attr in record.copyattrs])
        print(u'  fid' + u' ' * (msize - len(u'fid')), u':', record.fid)
    except AttributeError:
        pass
    printRecord(record)

# Classes
# Any level Descriptors
class CBashAlias(object):
    __slots__ = [u'_AttrName']
    def __init__(self, AttrName):
        self._AttrName = AttrName

    def __get__(self, instance, owner):
        return getattr(instance, self._AttrName, None)

    def __set__(self, instance, nValue):
        setattr(instance, self._AttrName, nValue)

class CBashGrouped(object):
    __slots__ = [u'_FieldID', u'_Type', u'_AsList']
    def __init__(self, FieldID, Type, AsList=False):
        self._FieldID, self._Type, self._AsList = FieldID, Type, AsList

    def __get__(self, instance, owner):
        oElement = self._Type(instance._RecordID, self._FieldID)
        return tuple([getattr(oElement, attr) for attr in oElement.copyattrs]) if self._AsList else oElement

    def __set__(self, instance, nElement):
        oElement = self._Type(instance._RecordID, self._FieldID)
        for nValue, attr in zip(nElement if isinstance(nElement, tuple) else tuple([None for attr in oElement.copyattrs]) if nElement is None else tuple([getattr(nElement, attr) for attr in nElement.copyattrs]), oElement.copyattrs):
            setattr(oElement, attr, nValue)

class CBashJunk(object):
    __slots__ = []
    def __init__(self, FieldID):
        pass

    def __get__(self, instance, owner):
        return None

    def __set__(self, instance, nValue):
        pass

class CBashBasicFlag(object):
    __slots__ = [u'_AttrName', u'_Value']
    def __init__(self, AttrName, Value):
        self._AttrName, self._Value = AttrName, Value

    def __get__(self, instance, owner):
        field = getattr(instance, self._AttrName, None)
        return None if field is None else (field & self._Value) != 0

    def __set__(self, instance, nValue):
        field = getattr(instance, self._AttrName, None)
        setattr(instance, self._AttrName, field & ~self._Value if field and not nValue else field | self._Value if field else self._Value)

class CBashInvertedFlag(object):
    __slots__ = [u'_AttrName']
    def __init__(self, AttrName):
        self._AttrName = AttrName

    def __get__(self, instance, owner):
        field = getattr(instance, self._AttrName, None)
        return None if field is None else not field

    def __set__(self, instance, nValue):
        setattr(instance, self._AttrName, not nValue)

class CBashBasicType(object):
    __slots__ = [u'_AttrName', u'_Value', u'_DefaultFieldName']
    def __init__(self, AttrName, value, default):
        self._AttrName, self._Value, self._DefaultFieldName = AttrName, value, default

    def __get__(self, instance, owner):
        field = getattr(instance, self._AttrName, None)
        return None if field is None else field == self._Value

    def __set__(self, instance, nValue):
        setattr(instance, self._AttrName if nValue else self._DefaultFieldName, self._Value if nValue else True)

class CBashMaskedType(object):
    __slots__ = [u'_AttrName', u'_TypeMask', u'_Value', u'_DefaultFieldName']
    def __init__(self, AttrName, typeMask, value, default):
        self._AttrName, self._TypeMask, self._Value, self._DefaultFieldName = AttrName, typeMask, value & typeMask, default

    def __get__(self, instance, owner):
        field = getattr(instance, self._AttrName, None)
        return None if field is None else (field & self._TypeMask) == self._Value

    def __set__(self, instance, nValue):
        setattr(instance, self._AttrName if nValue else self._DefaultFieldName, (getattr(instance, self._AttrName, 0) & ~self._TypeMask) | self._Value if nValue else True)

# Grouped Top Descriptors
class CBashGeneric_GROUP(object):
    __slots__ = [u'_FieldID', u'_Type', u'_ResType']
    def __init__(self, FieldID, Type):
        self._FieldID, self._Type, self._ResType = FieldID, Type, POINTER(Type)

    def __get__(self, instance, owner):
        _CGetField.restype = self._ResType
        retValue = _CGetField(instance._RecordID, self._FieldID + instance._FieldID, 0, 0, 0, 0, 0, 0, 0)
        return retValue.contents.value if retValue else None

    def __set__(self, instance, nValue):
        if nValue is None: _CDeleteField(instance._RecordID, self._FieldID + instance._FieldID, 0, 0, 0, 0, 0, 0)
        else: _CSetField(instance._RecordID, self._FieldID + instance._FieldID, 0, 0, 0, 0, 0, 0, byref(self._Type(nValue)), 0)

class CBashFORMID_GROUP(object):
    __slots__ = [u'_FieldID']
    def __init__(self, FieldID):
        self._FieldID = FieldID

    def __get__(self, instance, owner):
        _CGetField.restype = POINTER(c_ulong)
        retValue = _CGetField(instance._RecordID, self._FieldID + instance._FieldID, 0, 0, 0, 0, 0, 0, 0)
        return FormID(instance._RecordID, retValue.contents.value) if retValue else FormID(None,None)

    def __set__(self, instance, nValue):
        nValue = None if nValue is None else nValue.GetShortFormID(instance)
        if nValue is None: _CDeleteField(instance._RecordID, self._FieldID + instance._FieldID, 0, 0, 0, 0, 0, 0)
        else: _CSetField(instance._RecordID, self._FieldID + instance._FieldID, 0, 0, 0, 0, 0, 0, byref(c_ulong(nValue), 0))

class CBashFORMID_OR_UINT32_ARRAY_GROUP(object):
    __slots__ = [u'_FieldID', u'_Size']
    def __init__(self, FieldID, Size=None):
        self._FieldID, self._Size = FieldID, Size

    def __get__(self, instance, owner):
        FieldID = self._FieldID + instance._FieldID
        numRecords = _CGetFieldAttribute(instance._RecordID, FieldID, 0, 0, 0, 0, 0, 0, 1)
        if(numRecords > 0):
            cRecords = (c_ulong * numRecords)()
            _CGetField(instance._RecordID, FieldID, 0, 0, 0, 0, 0, 0, byref(cRecords))
            return [FormID(instance._RecordID, cRecord) if _CGetFieldAttribute(instance._RecordID, FieldID, x, 1, 0, 0, 0, 0, 2) == API_FIELDS.FORMID else cRecord for x, cRecord in enumerate(cRecords)]
        return []

    def __set__(self, instance, nValue):
        FieldID = self._FieldID + instance._FieldID
        if nValue is None or not len(nValue): _CDeleteField(instance._RecordID, FieldID, 0, 0, 0, 0, 0, 0)
        else:
            nValue = [x for x in nValue if x is not None or (isinstance(x, FormID) and x.GetShortFormID(instance) is not None)]
            length = len(nValue)
            if self._Size and length != self._Size: return
            #Each element can be either a formID or UINT32, so they have to be set separately
            #Resize the list
            _CSetField(instance._RecordID, FieldID, 0, 0, 0, 0, 0, 0, 0, c_long(length))
            for x, value in enumerate(nValue):
                #Borrowing ArraySize to flag if the new value is a formID
                IsFormID = isinstance(value, FormID)
                _CSetField(instance._RecordID, FieldID, x, 1, 0, 0, 0, 0, byref(c_ulong(value.GetShortFormID(instance) if IsFormID else value)), IsFormID)

class CBashUINT8ARRAY_GROUP(object):
    __slots__ = [u'_FieldID', u'_Size']
    def __init__(self, FieldID, Size=None):
        self._FieldID, self._Size = FieldID, Size

    def __get__(self, instance, owner):
        numRecords = _CGetFieldAttribute(instance._RecordID, self._FieldID + instance._FieldID, 0, 0, 0, 0, 0, 0, 1)
        if(numRecords > 0):
            cRecords = POINTER(c_ubyte * numRecords)()
            _CGetField(instance._RecordID, self._FieldID + instance._FieldID, 0, 0, 0, 0, 0, 0, byref(cRecords))
            return [cRecords.contents[x] for x in xrange(numRecords)]
        return []

    def __set__(self, instance, nValue):
        if nValue is None or not len(nValue): _CDeleteField(instance._RecordID, self._FieldID + instance._FieldID, 0, 0, 0, 0, 0, 0)
        else:
            length = len(nValue)
            if self._Size and length != self._Size: return
            cRecords = (c_ubyte * length)(*nValue)
            _CSetField(instance._RecordID, self._FieldID + instance._FieldID, 0, 0, 0, 0, 0, 0, byref(cRecords), length)

class CBashFLOAT32_GROUP(object):
    __slots__ = [u'_FieldID']
    def __init__(self, FieldID):
        self._FieldID = FieldID

    def __get__(self, instance, owner):
        _CGetField.restype = POINTER(c_float)
        retValue = _CGetField(instance._RecordID, self._FieldID + instance._FieldID, 0, 0, 0, 0, 0, 0, 0)
        return round(retValue.contents.value,6) if retValue else None

    def __set__(self, instance, nValue):
        if nValue is None: _CDeleteField(instance._RecordID, self._FieldID + instance._FieldID, 0, 0, 0, 0, 0, 0)
        else: _CSetField(instance._RecordID, self._FieldID + instance._FieldID, 0, 0, 0, 0, 0, 0, byref(c_float(round(nValue,6))), 0)

class CBashSTRING_GROUP(object):
    __slots__ = [u'_FieldID']
    def __init__(self, FieldID):
        self._FieldID = FieldID

    def __get__(self, instance, owner):
        _CGetField.restype = c_char_p
        retValue = _CGetField(instance._RecordID, self._FieldID + instance._FieldID, 0, 0, 0, 0, 0, 0, 0)
        return _unicode(retValue) if retValue else None

    def __set__(self, instance, nValue):
        if nValue is None: _CDeleteField(instance._RecordID, self._FieldID + instance._FieldID, 0, 0, 0, 0, 0, 0)
        else: _CSetField(instance._RecordID, self._FieldID + instance._FieldID, 0, 0, 0, 0, 0, 0, _encode(nValue), 0)

class CBashISTRING_GROUP(object):
    __slots__ = [u'_FieldID']
    def __init__(self, FieldID):
        self._FieldID = FieldID

    def __get__(self, instance, owner):
        _CGetField.restype = c_char_p
        retValue = _CGetField(instance._RecordID, self._FieldID + instance._FieldID, 0, 0, 0, 0, 0, 0, 0)
        return IUNICODE(_unicode(retValue)) if retValue else None

    def __set__(self, instance, nValue):
        if nValue is None: _CDeleteField(instance._RecordID, self._FieldID + instance._FieldID, 0, 0, 0, 0, 0, 0)
        else: _CSetField(instance._RecordID, self._FieldID + instance._FieldID, 0, 0, 0, 0, 0, 0, _encode(nValue), 0)

class CBashLIST_GROUP(object):
    __slots__ = [u'_FieldID', u'_Type', u'_AsList']
    def __init__(self, FieldID, Type, AsList=False):
        self._FieldID, self._Type, self._AsList = FieldID, Type, AsList

    def __get__(self, instance, owner):
        FieldID = self._FieldID + instance._FieldID
        return ExtractCopyList([self._Type(instance._RecordID, FieldID, x) for x in xrange(_CGetFieldAttribute(instance._RecordID, FieldID, 0, 0, 0, 0, 0, 0, 1))]) if self._AsList else [self._Type(instance._RecordID, FieldID, x) for x in xrange(_CGetFieldAttribute(instance._RecordID, FieldID, 0, 0, 0, 0, 0, 0, 1))]

    def __set__(self, instance, nElements):
        FieldID = self._FieldID + instance._FieldID
        if nElements is None or not len(nElements): _CDeleteField(instance._RecordID, FieldID, 0, 0, 0, 0, 0, 0)
        else:
            length = len(nElements)
            if not isinstance(nElements[0], tuple): nElements = ExtractCopyList(nElements)
            ##Resizes the list
            _CSetField(instance._RecordID, FieldID, 0, 0, 0, 0, 0, 0, 0, c_long(length))
            SetCopyList([self._Type(instance._RecordID, FieldID, x) for x in xrange(_CGetFieldAttribute(instance._RecordID, FieldID, 0, 0, 0, 0, 0, 0, 1))], nElements)

# Top level Descriptors
class CBashLIST(object):
    __slots__ = [u'_FieldID', u'_Type', u'_AsList']
    def __init__(self, FieldID, Type, AsList=False):
        self._FieldID, self._Type, self._AsList = FieldID, Type, AsList

    def __get__(self, instance, owner):
        return ExtractCopyList([self._Type(instance._RecordID, self._FieldID, x) for x in xrange(_CGetFieldAttribute(instance._RecordID, self._FieldID, 0, 0, 0, 0, 0, 0, 1))]) if self._AsList else [self._Type(instance._RecordID, self._FieldID, x) for x in xrange(_CGetFieldAttribute(instance._RecordID, self._FieldID, 0, 0, 0, 0, 0, 0, 1))]

    def __set__(self, instance, nElements):
        if nElements is None or not len(nElements): _CDeleteField(instance._RecordID, self._FieldID, 0, 0, 0, 0, 0, 0)
        else:
            length = len(nElements)
            if not isinstance(nElements[0], tuple): nElements = ExtractCopyList(nElements)
            ##Resizes the list
            _CSetField(instance._RecordID, self._FieldID, 0, 0, 0, 0, 0, 0, 0, c_ulong(length))
            SetCopyList([self._Type(instance._RecordID, self._FieldID, x) for x in xrange(_CGetFieldAttribute(instance._RecordID, self._FieldID, 0, 0, 0, 0, 0, 0, 1))], nElements)

class CBashUNKNOWN_OR_GENERIC(object):
    __slots__ = [u'_FieldID', u'_Type', u'_ResType']
    def __init__(self, FieldID, Type):
        self._FieldID, self._Type, self._ResType = FieldID, Type, POINTER(Type)

    def __get__(self, instance, owner):
        if _CGetFieldAttribute(instance._RecordID, self._FieldID, 0, 0, 0, 0, 0, 0, 2) == API_FIELDS.UNKNOWN: return None
        _CGetField.restype = self._ResType
        retValue = _CGetField(instance._RecordID, self._FieldID, 0, 0, 0, 0, 0, 0, 0)
        return retValue.contents.value if retValue else None

    def __set__(self, instance, nValue):
        if _CGetFieldAttribute(instance._RecordID, self._FieldID, 0, 0, 0, 0, 0, 0, 2) == API_FIELDS.UNKNOWN: return
        if nValue is None: _CDeleteField(instance._RecordID, self._FieldID, 0, 0, 0, 0, 0, 0)
        else: _CSetField(instance._RecordID, self._FieldID, 0, 0, 0, 0, 0, 0, byref(self._Type(nValue)), 0)

class CBashXSED(object):
    """To delete the field, you have to set the current accessor to None."""
    __slots__ = [u'_FieldID', u'_AsOffset', u'_ResType']
    def __init__(self, FieldID, AsOffset=False):
        self._FieldID, self._AsOffset = FieldID, AsOffset
        self._ResType = POINTER(c_ubyte) if AsOffset else POINTER(c_ulong)

    def __get__(self, instance, owner):
        if (_CGetFieldAttribute(instance._RecordID, self._FieldID, 0, 0, 0, 0, 0, 0, 2) != API_FIELDS.UINT32) != self._AsOffset: return None
        _CGetField.restype = self._ResType
        retValue = _CGetField(instance._RecordID, self._FieldID, 0, 0, 0, 0, 0, 0, 0)
        return retValue.contents.value if retValue else None

    def __set__(self, instance, nValue):
        if nValue is None:
            if (_CGetFieldAttribute(instance._RecordID, self._FieldID, 0, 0, 0, 0, 0, 0, 2) != API_FIELDS.UINT32) != self._AsOffset: return
            _CDeleteField(instance._RecordID, self._FieldID, 0, 0, 0, 0, 0, 0)
        #Borrowing ArraySize to flag if the new value is an offset
        else: _CSetField(instance._RecordID, self._FieldID, 0, 0, 0, 0, 0, 0, byref(c_ubyte(nValue) if self._AsOffset else c_ulong(nValue)), c_bool(self._AsOffset))

class CBashISTRINGARRAY(object):
    __slots__ = [u'_FieldID']
    def __init__(self, FieldID):
        self._FieldID = FieldID

    def __get__(self, instance, owner):
        numRecords = _CGetFieldAttribute(instance._RecordID, self._FieldID, 0, 0, 0, 0, 0, 0, 1)
        if(numRecords > 0):
            cRecords = (POINTER(c_char_p) * numRecords)()
            _CGetField(instance._RecordID, self._FieldID, 0, 0, 0, 0, 0, 0, byref(cRecords))
            return [IUNICODE(_unicode(string_at(cRecords[x]))) for x in xrange(numRecords)]
        return []

    def __set__(self, instance, nValue):
        if nValue is None or not len(nValue): _CDeleteField(instance._RecordID, self._FieldID, 0, 0, 0, 0, 0, 0)
        else:
            length = len(nValue)
            nValue = [_encode(value) for value in nValue]
            _CSetField(instance._RecordID, self._FieldID, 0, 0, 0, 0, 0, 0, byref((c_char_p * length)(*nValue)), length)

class CBashIUNICODEARRAY(object):
    # Almost exactly like CBashISTRINGARRAY, but instead of using the bolt.pluginEncoding
    # for encoding, uses the automatic encoding detection.  Only really useful for TES4
    # record (masters)
    __slots__ = [u'_FieldID']
    def __init__(self, FieldID):
        self._FieldID = FieldID

    def __get__(self, instance, owner):
        numRecords = _CGetFieldAttribute(instance._RecordID, self._FieldID, 0, 0, 0, 0, 0, 0, 1)
        if (numRecords > 0):
            cRecords = (POINTER(c_void_p) * numRecords)()
            _CGetField(instance._RecordID, self._FieldID, 0, 0, 0, 0, 0, 0, cRecords)
            cRecords = cast(cRecords, POINTER(c_char_p))
            return [IUNICODE(_uni(string_at(cRecords[x]))) for x in xrange(numRecords)]
        return []

    def __set__(self, instance, nValue):
        if nValue is None or not len(nValue): _CDeleteField(instance._RecordID, self._FieldID, 0, 0, 0, 0, 0, 0)
        else:
            length = len(nValue)
            nValue = [_enc(value) for value in nValue]
            _CSetField(instance._RecordID, self._FieldID, 0, 0, 0, 0, 0, 0, byref((c_char_p * length)(*nValue)), length)

class CBashGeneric(object):
    __slots__ = [u'_FieldID', u'_Type', u'_ResType']
    def __init__(self, FieldID, Type):
        self._FieldID, self._Type, self._ResType = FieldID, Type, POINTER(Type)

    def __get__(self, instance, owner):
        _CGetField.restype = self._ResType
        retValue = _CGetField(instance._RecordID, self._FieldID, 0, 0, 0, 0, 0, 0, 0)
        return retValue.contents.value if retValue else None

    def __set__(self, instance, nValue):
        if nValue is None: _CDeleteField(instance._RecordID, self._FieldID, 0, 0, 0, 0, 0, 0)
        else: _CSetField(instance._RecordID, self._FieldID, 0, 0, 0, 0, 0, 0, byref(self._Type(nValue)), 0)

class CBashFORMID(object):
    __slots__ = [u'_FieldID']
    def __init__(self, FieldID):
        self._FieldID = FieldID

    def __get__(self, instance, owner):
        _CGetField.restype = POINTER(c_ulong)
        retValue = _CGetField(instance._RecordID, self._FieldID, 0, 0, 0, 0, 0, 0, 0)
        return FormID(instance._RecordID, retValue.contents.value) if retValue else FormID(None,None)

    def __set__(self, instance, nValue):
        nValue = None if nValue is None else nValue.GetShortFormID(instance)
        if nValue is None: _CDeleteField(instance._RecordID, self._FieldID, 0, 0, 0, 0, 0, 0)
        else: _CSetField(instance._RecordID, self._FieldID, 0, 0, 0, 0, 0, 0, byref(c_ulong(nValue)), 0)

class CBashMGEFCODE(object):
    __slots__ = [u'_FieldID']
    def __init__(self, FieldID):
        self._FieldID = FieldID

    def __get__(self, instance, owner):
        _CGetField.restype = POINTER(c_char * 4) if _CGetFieldAttribute(instance._RecordID, self._FieldID, 0, 0, 0, 0, 0, 0, 2) == API_FIELDS.CHAR4 else POINTER(c_ulong)
        retValue = _CGetField(instance._RecordID, self._FieldID, 0, 0, 0, 0, 0, 0, 0)
        return MGEFCode(instance._RecordID, retValue.contents.value) if retValue else MGEFCode(None,None)

    def __set__(self, instance, nValue):
        nValue = None if nValue is None else nValue.GetShortMGEFCode(instance)
        if nValue is None: _CDeleteField(instance._RecordID, self._FieldID, 0, 0, 0, 0, 0, 0)
        else: _CSetField(instance._RecordID, self._FieldID, 0, 0, 0, 0, 0, 0, byref(c_ulong(nValue)), 0)

class CBashFORMIDARRAY(object):
    __slots__ = [u'_FieldID']
    def __init__(self, FieldID):
        self._FieldID = FieldID

    def __get__(self, instance, owner):
        numRecords = _CGetFieldAttribute(instance._RecordID, self._FieldID, 0, 0, 0, 0, 0, 0, 1)
        if(numRecords > 0):
            cRecords = POINTER(c_ulong * numRecords)()
            _CGetField(instance._RecordID, self._FieldID, 0, 0, 0, 0, 0, 0, byref(cRecords))
            return [FormID(instance._RecordID, cRecords.contents[x]) for x in xrange(numRecords)]
        return []

    def __set__(self, instance, nValue):
        if nValue is None or not len(nValue): _CDeleteField(instance._RecordID, self._FieldID, 0, 0, 0, 0, 0, 0)
        else:
            nValue = [x.GetShortFormID(instance) for x in nValue if x.GetShortFormID(instance) is not None]
            length = len(nValue)
            _CSetField(instance._RecordID, self._FieldID, 0, 0, 0, 0, 0, 0, byref((c_ulong * length)(*nValue)), length)

class CBashFORMID_OR_UINT32(object):
    __slots__ = [u'_FieldID']
    def __init__(self, FieldID):
        self._FieldID = FieldID

    def __get__(self, instance, owner):
        _CGetField.restype = POINTER(c_ulong)
        retValue = _CGetField(instance._RecordID, self._FieldID, 0, 0, 0, 0, 0, 0, 0)
        return (FormID(instance._RecordID, retValue.contents.value) if retValue else FormID(None,None)) if _CGetFieldAttribute(instance._RecordID, self._FieldID, 0, 0, 0, 0, 0, 0, 2) == API_FIELDS.FORMID else retValue.contents.value if retValue else None

    def __set__(self, instance, nValue):
        nValue = nValue.GetShortFormID(instance) if isinstance(nValue, FormID) else nValue
        if nValue is None: _CDeleteField(instance._RecordID, self._FieldID, 0, 0, 0, 0, 0, 0)
        else: _CSetField(instance._RecordID, self._FieldID, 0, 0, 0, 0, 0, 0, byref(c_ulong(nValue)), 0)

class CBashFORMID_OR_STRING(object):
    __slots__ = [u'_FieldID']
    def __init__(self, FieldID):
        self._FieldID = FieldID

    def __get__(self, instance, owner):
        IsFormID = _CGetFieldAttribute(instance._RecordID, self._FieldID, 0, 0, 0, 0, 0, 0, 2) == API_FIELDS.FORMID
        _CGetField.restype = POINTER(c_ulong) if IsFormID else c_char_p
        retValue = _CGetField(instance._RecordID, self._FieldID, 0, 0, 0, 0, 0, 0, 0)
        return (FormID(instance._RecordID, retValue.contents.value) if retValue else FormID(None,None)) if IsFormID else _unicode(retValue) if retValue else None

    def __set__(self, instance, nValue):
        IsFormID = _CGetFieldAttribute(instance._RecordID, self._FieldID, 0, 0, 0, 0, 0, 0, 2) == API_FIELDS.FORMID
        nValue = None if nValue is None else nValue.GetShortFormID(instance) if IsFormID else nValue
        if nValue is None: _CDeleteField(instance._RecordID, self._FieldID, 0, 0, 0, 0, 0, 0)
        else: _CSetField(instance._RecordID, self._FieldID, 0, 0, 0, 0, 0, 0, byref(c_ulong(nValue)) if IsFormID else _encode(nValue), 0)

class CBashFORMID_OR_UINT32_ARRAY(object):
    __slots__ = [u'_FieldID', u'_Size']
    def __init__(self, FieldID, Size=None):
        self._FieldID, self._Size = FieldID, Size

    def __get__(self, instance, owner):
        numRecords = _CGetFieldAttribute(instance._RecordID, self._FieldID, 0, 0, 0, 0, 0, 0, 1)
        if(numRecords > 0):
            cRecords = (c_ulong * numRecords)()
            _CGetField(instance._RecordID, self._FieldID, 0, 0, 0, 0, 0, 0, byref(cRecords))
            return [FormID(instance._RecordID, cRecord) if _CGetFieldAttribute(instance._RecordID, self._FieldID, x, 1, 0, 0, 0, 0, 2) == API_FIELDS.FORMID else cRecord for x, cRecord in enumerate(cRecords)]
        return []

    def __set__(self, instance, nValue):
        if nValue is None or not len(nValue): _CDeleteField(instance._RecordID, self._FieldID, 0, 0, 0, 0, 0, 0)
        else:
            nValue = [x for x in nValue if x is not None or (isinstance(x, FormID) and x.GetShortFormID(instance) is not None)]
            length = len(nValue)
            if self._Size and length != self._Size: return
            #Each element can be either a formID or UINT32, so they have to be set separately
            #Resize the list
            _CSetField(instance._RecordID, self._FieldID, 0, 0, 0, 0, 0, 0, 0, c_long(length))
            for x, value in enumerate(nValue):
                #Borrowing ArraySize to flag if the new value is a formID
                IsFormID = isinstance(value, FormID)
                _CSetField(instance._RecordID, self._FieldID, x, 1, 0, 0, 0, 0, byref(c_ulong(value.GetShortFormID(instance) if IsFormID else value)), IsFormID)

class CBashMGEFCODE_ARRAY(object):
    __slots__ = [u'_FieldID', u'_Size']
    def __init__(self, FieldID, Size=None):
        self._FieldID, self._Size = FieldID, Size

    def __get__(self, instance, owner):
        numRecords = _CGetFieldAttribute(instance._RecordID, self._FieldID, 0, 0, 0, 0, 0, 0, 1)
        if(numRecords > 0):
            cRecords = POINTER(c_ulong * numRecords)()
            _CGetField(instance._RecordID, self._FieldID, 0, 0, 0, 0, 0, 0, byref(cRecords))
            return [MGEFCode(instance._RecordID, cast(POINTER(c_ulong)(c_ulong(cRecords.contents[x])), POINTER(c_char * 4)).contents.value if _CGetFieldAttribute(instance._RecordID, self._FieldID, x, 1, 0, 0, 0, 0, 2) == API_FIELDS.CHAR4 else cRecords.contents[x]) for x in xrange(numRecords)]
        return []

    def __set__(self, instance, nValue):
        if nValue is None or not len(nValue): _CDeleteField(instance._RecordID, self._FieldID, 0, 0, 0, 0, 0, 0)
        else:
            nValue = [x.GetShortMGEFCode(instance) for x in nValue if x.GetShortMGEFCode(instance) is not None]
            length = len(nValue)
            if self._Size and length != self._Size: return
            _CSetField(instance._RecordID, self._FieldID, 0, 0, 0, 0, 0, 0, byref((c_ulong * length)(*nValue)), length)

class CBashUINT8ARRAY(object):
    __slots__ = [u'_FieldID', u'_Size']
    def __init__(self, FieldID, Size=None):
        self._FieldID, self._Size = FieldID, Size

    def __get__(self, instance, owner):
        numRecords = _CGetFieldAttribute(instance._RecordID, self._FieldID, 0, 0, 0, 0, 0, 0, 1)
        if(numRecords > 0):
            cRecords = POINTER(c_ubyte * numRecords)()
            _CGetField(instance._RecordID, self._FieldID, 0, 0, 0, 0, 0, 0, byref(cRecords))
            return [cRecords.contents[x] for x in xrange(numRecords)]
        return []

    def __set__(self, instance, nValue):
        if nValue is None or not len(nValue): _CDeleteField(instance._RecordID, self._FieldID, 0, 0, 0, 0, 0, 0)
        else:
            length = len(nValue)
            if self._Size and length != self._Size: return
            _CSetField(instance._RecordID, self._FieldID, 0, 0, 0, 0, 0, 0, byref((c_ubyte * length)(*nValue)), length)

class CBashUINT32ARRAY(object):
    __slots__ = [u'_FieldID', u'_Size']
    def __init__(self, FieldID, Size=None):
        self._FieldID, self._Size = FieldID, Size

    def __get__(self, instance, owner):
        numRecords = _CGetFieldAttribute(instance._RecordID, self._FieldID, 0, 0, 0, 0, 0, 0, 1)
        if(numRecords > 0):
            cRecords = POINTER(c_ulong * numRecords)()
            _CGetField(instance._RecordID, self._FieldID, 0, 0, 0, 0, 0, 0, byref(cRecords))
            return [cRecords.contents[x] for x in xrange(numRecords)]
        return []

    def __set__(self, instance, nValue):
        if nValue is None or not len(nValue): _CDeleteField(instance._RecordID, self._FieldID, 0, 0, 0, 0, 0, 0)
        else:
            length = len(nValue)
            if self._Size and length != self._Size: return
            _CSetField(instance._RecordID, self._FieldID, 0, 0, 0, 0, 0, 0, byref((c_ulong * length)(*nValue)), length)

class CBashSINT16ARRAY(object):
    __slots__ = [u'_FieldID', u'_Size']
    def __init__(self, FieldID, Size=None):
        self._FieldID, self._Size = FieldID, Size

    def __get__(self, instance, owner):
        numRecords = _CGetFieldAttribute(instance._RecordID, self._FieldID, 0, 0, 0, 0, 0, 0, 1)
        if(numRecords > 0):
            cRecords = POINTER(c_short * numRecords)()
            _CGetField(instance._RecordID, self._FieldID, 0, 0, 0, 0, 0, 0, byref(cRecords))
            return [cRecords.contents[x] for x in xrange(numRecords)]
        return []

    def __set__(self, instance, nValue):
        if nValue is None or not len(nValue): _CDeleteField(instance._RecordID, self._FieldID, 0, 0, 0, 0, 0, 0)
        else:
            length = len(nValue)
            if self._Size and length != self._Size: return
            _CSetField(instance._RecordID, self._FieldID, 0, 0, 0, 0, 0, 0, byref((c_short * length)(*nValue)), length)

class CBashFLOAT32(object):
    __slots__ = [u'_FieldID']
    def __init__(self, FieldID):
        self._FieldID = FieldID

    def __get__(self, instance, owner):
        _CGetField.restype = POINTER(c_float)
        retValue = _CGetField(instance._RecordID, self._FieldID, 0, 0, 0, 0, 0, 0, 0)
        return round(retValue.contents.value,6) if retValue else None

    def __set__(self, instance, nValue):
        if nValue is None: _CDeleteField(instance._RecordID, self._FieldID, 0, 0, 0, 0, 0, 0)
        else: _CSetField(instance._RecordID, self._FieldID, 0, 0, 0, 0, 0, 0, byref(c_float(round(nValue,6))), 0)

class CBashDEGREES(object):
    __slots__ = [u'_FieldID']
    def __init__(self, FieldID):
        self._FieldID = FieldID

    def __get__(self, instance, owner):
        _CGetField.restype = POINTER(c_float)
        retValue = _CGetField(instance._RecordID, self._FieldID, 0, 0, 0, 0, 0, 0, 0)
        return round(math.degrees(retValue.contents.value),6) if retValue else None

    def __set__(self, instance, nValue):
        try: nValue = math.radians(nValue)
        except TypeError: nValue = None
        if nValue is None: _CDeleteField(instance._RecordID, self._FieldID, 0, 0, 0, 0, 0, 0)
        else: _CSetField(instance._RecordID, self._FieldID, 0, 0, 0, 0, 0, 0, byref(c_float(round(nValue,6))), 0)

class CBashSTRING(object):
    __slots__ = [u'_FieldID']
    def __init__(self, FieldID):
        self._FieldID = FieldID

    def __get__(self, instance, owner):
        _CGetField.restype = c_char_p
        retValue = _CGetField(instance._RecordID, self._FieldID, 0, 0, 0, 0, 0, 0, 0)
        return _unicode(retValue,avoidEncodings=(u'utf8', u'utf-8')) if retValue else None

    def __set__(self, instance, nValue):
        if nValue is None: _CDeleteField(instance._RecordID, self._FieldID, 0, 0, 0, 0, 0, 0)
        else: _CSetField(instance._RecordID, self._FieldID, 0, 0, 0, 0, 0, 0, _encode(nValue), 0)

class CBashUNICODE(object):
    # Almost exactly like CBashSTRING, only instead of using the bolt.pluginEncoding
    # specified encoding first, uses the automatic encoding detection.  Only really
    # useful for the TES4 record
    __slots__ = [u'_FieldID']
    def __init__(self, FieldID):
        self._FieldID = FieldID

    def __get__(self, instance, owner):
        _CGetField.restype = c_char_p
        retValue = _CGetField(instance._RecordID, self._FieldID, 0, 0, 0, 0, 0, 0, 0)
        return _uni(retValue,avoidEncodings=(u'utf8', u'utf-8')) if retValue else None

    def __set__(self, instance, nValue):
        if nValue is None: _CDeleteField(instance._RecordID, self._FieldID, 0, 0, 0, 0, 0, 0)
        else: _CSetField(instance._RecordID, self._FieldID, 0, 0, 0, 0, 0, 0, cast(_enc(nValue), c_void_p), 0)

class CBashISTRING(object):
    __slots__ = [u'_FieldID']
    def __init__(self, FieldID):
        self._FieldID = FieldID

    def __get__(self, instance, owner):
        _CGetField.restype = c_char_p
        retValue = _CGetField(instance._RecordID, self._FieldID, 0, 0, 0, 0, 0, 0, 0)
        return IUNICODE(_unicode(retValue)) if retValue else None

    def __set__(self, instance, nValue):
        if nValue is None: _CDeleteField(instance._RecordID, self._FieldID, 0, 0, 0, 0, 0, 0)
        else: _CSetField(instance._RecordID, self._FieldID, 0, 0, 0, 0, 0, 0, _encode(nValue), 0)

class CBashRECORDARRAY(object):
    __slots__ = [u'_Type', u'_TypeName']
    def __init__(self, Type, TypeName):
        self._Type, self._TypeName = Type, cast(TypeName, POINTER(c_ulong)).contents.value

    def __get__(self, instance, owner):
        numRecords = _CGetNumRecords(instance._ModID, self._TypeName)
        if(numRecords > 0):
            cRecords = (c_record_p * numRecords)()
            _CGetRecordIDs(instance._ModID, self._TypeName, cRecords)
            return [self._Type(x) for x in cRecords]
        return []

    def __set__(self, instance, nValue):
        return

class CBashSUBRECORD(object):
    __slots__ = [u'_FieldID', u'_Type', u'_TypeName']
    def __init__(self, FieldID, Type, TypeName):
        self._FieldID, self._Type, self._TypeName = FieldID, Type, cast(TypeName, POINTER(c_ulong)).contents.value

    def __get__(self, instance, owner):
        _CGetField.restype = c_ulong
        retValue = _CGetField(instance._RecordID, self._FieldID, 0, 0, 0, 0, 0, 0, 0)
        return self._Type(retValue) if retValue else None

    def __set__(self, instance, nValue):
        return

class CBashSUBRECORDARRAY(object):
    __slots__ = [u'_FieldID', u'_Type']
    def __init__(self, FieldID, Type, TypeName): #TypeName not currently used
        self._FieldID, self._Type = FieldID, Type

    def __get__(self, instance, owner):
        numRecords = _CGetFieldAttribute(instance._RecordID, self._FieldID, 0, 0, 0, 0, 0, 0, 1)
        if(numRecords > 0):
            cRecords = (c_void_p * numRecords)()
            _CGetField(instance._RecordID, self._FieldID, 0, 0, 0, 0, 0, 0, byref(cRecords))
            return [self._Type(x) for x in cRecords]
        return []

    def __set__(self, instance, nValue):
        return

# ListX1 Descriptors
class CBashLIST_LIST(object):
    __slots__ = [u'_ListFieldID', u'_Type', u'_AsList']
    def __init__(self, ListFieldID, Type, AsList=False):
        self._ListFieldID, self._Type, self._AsList = ListFieldID, Type, AsList

    def __get__(self, instance, owner):
        return ExtractCopyList([self._Type(instance._RecordID, instance._FieldID, instance._ListIndex, self._ListFieldID, x) for x in xrange(_CGetFieldAttribute(instance._RecordID, instance._FieldID, instance._ListIndex, self._ListFieldID, 0, 0, 0, 0, 1))]) if self._AsList else [self._Type(instance._RecordID, instance._FieldID, instance._ListIndex, self._ListFieldID, x) for x in xrange(_CGetFieldAttribute(instance._RecordID, instance._FieldID, instance._ListIndex, self._ListFieldID, 0, 0, 0, 0, 1))]

    def __set__(self, instance, nElements):
        if nElements is None or not len(nElements): _CDeleteField(instance._RecordID, instance._FieldID, instance._ListIndex, self._ListFieldID, 0, 0, 0, 0)
        else:
            length = len(nElements)
            if not isinstance(nElements[0], tuple): nElements = ExtractCopyList(nElements)
            ##Resizes the list
            _CSetField(instance._RecordID, instance._FieldID, instance._ListIndex, self._ListFieldID, 0, 0, 0, 0, 0, c_long(length))
            SetCopyList([self._Type(instance._RecordID, instance._FieldID, instance._ListIndex, self._ListFieldID, x) for x in xrange(_CGetFieldAttribute(instance._RecordID, instance._FieldID, instance._ListIndex, self._ListFieldID, 0, 0, 0, 0, 1))], nElements)

class CBashGeneric_LIST(object):
    __slots__ = [u'_ListFieldID', u'_Type', u'_ResType']
    def __init__(self, ListFieldID, Type):
        self._ListFieldID, self._Type, self._ResType = ListFieldID, Type, POINTER(Type)

    def __get__(self, instance, owner):
        _CGetField.restype = self._ResType
        retValue = _CGetField(instance._RecordID, instance._FieldID, instance._ListIndex, self._ListFieldID, 0, 0, 0, 0, 0)
        return retValue.contents.value if retValue else None

    def __set__(self, instance, nValue):
        if nValue is None: _CDeleteField(instance._RecordID, instance._FieldID, instance._ListIndex, self._ListFieldID, 0, 0, 0, 0)
        else: _CSetField(instance._RecordID, instance._FieldID, instance._ListIndex, self._ListFieldID, 0, 0, 0, 0, byref(self._Type(nValue)), 0)

class CBashFORMID_LIST(object):
    __slots__ = [u'_ListFieldID']
    def __init__(self, ListFieldID):
        self._ListFieldID = ListFieldID

    def __get__(self, instance, owner):
        _CGetField.restype = POINTER(c_ulong)
        retValue = _CGetField(instance._RecordID, instance._FieldID, instance._ListIndex, self._ListFieldID, 0, 0, 0, 0, 0)
        return FormID(instance._RecordID, retValue.contents.value) if retValue else FormID(None,None)

    def __set__(self, instance, nValue):
        nValue = None if nValue is None else nValue.GetShortFormID(instance)
        if nValue is None: _CDeleteField(instance._RecordID, instance._FieldID, instance._ListIndex, self._ListFieldID, 0, 0, 0, 0)
        else: _CSetField(instance._RecordID, instance._FieldID, instance._ListIndex, self._ListFieldID, 0, 0, 0, 0, byref(c_ulong(nValue)), 0)

class CBashACTORVALUE_LIST(object):
    __slots__ = [u'_ListFieldID']
    def __init__(self, ListFieldID):
        self._ListFieldID = ListFieldID

    def __get__(self, instance, owner):
        _CGetField.restype = POINTER(c_ulong)
        retValue = _CGetField(instance._RecordID, instance._FieldID, instance._ListIndex, self._ListFieldID, 0, 0, 0, 0, 0)
        return ActorValue(instance._RecordID, retValue.contents.value) if retValue else ActorValue(None,None)

    def __set__(self, instance, nValue):
        nValue = None if nValue is None else nValue.GetShortActorValue(instance)
        if nValue is None: _CDeleteField(instance._RecordID, instance._FieldID, instance._ListIndex, self._ListFieldID, 0, 0, 0, 0)
        else: _CSetField(instance._RecordID, instance._FieldID, instance._ListIndex, self._ListFieldID, 0, 0, 0, 0, byref(c_ulong(nValue)), 0)

class CBashFORMIDARRAY_LIST(object):
    __slots__ = [u'_ListFieldID']
    def __init__(self, ListFieldID):
        self._ListFieldID = ListFieldID

    def __get__(self, instance, owner):
        numRecords = _CGetFieldAttribute(instance._RecordID, instance._FieldID, instance._ListIndex, self._ListFieldID, 0, 0, 0, 0, 1)
        if(numRecords > 0):
            cRecords = POINTER(c_ulong * numRecords)()
            _CGetField(instance._RecordID, instance._FieldID, instance._ListIndex, self._ListFieldID, 0, 0, 0, 0, byref(cRecords))
            return [FormID(instance._RecordID, cRecords.contents[x]) for x in xrange(numRecords)]
        return []

    def __set__(self, instance, nValue):
        if nValue is None or not len(nValue): _CDeleteField(instance._RecordID, instance._FieldID, instance._ListIndex, self._ListFieldID, 0, 0, 0, 0)
        else:
            nValue = [x.GetShortFormID(instance) for x in nValue if x.GetShortFormID(instance) is not None]
            length = len(nValue)
            _CSetField(instance._RecordID, instance._FieldID, instance._ListIndex, self._ListFieldID, 0, 0, 0, 0, byref((c_ulong * length)(*nValue)), length)

class CBashUNKNOWN_OR_FORMID_OR_UINT32_LIST(object):
    __slots__ = [u'_ListFieldID']
    def __init__(self, ListFieldID):
        self._ListFieldID = ListFieldID

    def __get__(self, instance, owner):
        fieldtype = _CGetFieldAttribute(instance._RecordID, instance._FieldID, instance._ListIndex, self._ListFieldID, 0, 0, 0, 0, 2)
        if fieldtype == API_FIELDS.UNKNOWN: return None
        _CGetField.restype = POINTER(c_ulong)
        retValue = _CGetField(instance._RecordID, instance._FieldID, instance._ListIndex, self._ListFieldID, 0, 0, 0, 0, 0)
        return (FormID(instance._RecordID, retValue.contents.value) if retValue else FormID(None,None)) if fieldtype == API_FIELDS.FORMID else retValue.contents.value if retValue else None

    def __set__(self, instance, nValue):
        fieldtype = _CGetFieldAttribute(instance._RecordID, instance._FieldID, instance._ListIndex, self._ListFieldID, 0, 0, 0, 0, 2)
        if fieldtype == API_FIELDS.UNKNOWN: return
        nValue = None if nValue is None else nValue.GetShortFormID(instance) if fieldtype == API_FIELDS.FORMID else nValue
        if nValue is None: _CDeleteField(instance._RecordID, instance._FieldID, instance._ListIndex, self._ListFieldID, 0, 0, 0, 0)
        else: _CSetField(instance._RecordID, instance._FieldID, instance._ListIndex, self._ListFieldID, 0, 0, 0, 0, byref(c_ulong(nValue)), 0)

class CBashMGEFCODE_LIST(object):
    __slots__ = [u'_ListFieldID']
    def __init__(self, ListFieldID):
        self._ListFieldID = ListFieldID

    def __get__(self, instance, owner):
        _CGetField.restype = POINTER(c_char * 4) if _CGetFieldAttribute(instance._RecordID, instance._FieldID, instance._ListIndex, self._ListFieldID, 0, 0, 0, 0, 2) == API_FIELDS.CHAR4 else POINTER(c_ulong)
        retValue = _CGetField(instance._RecordID, instance._FieldID, instance._ListIndex, self._ListFieldID, 0, 0, 0, 0, 0)
        return MGEFCode(instance._RecordID, retValue.contents.value) if retValue else MGEFCode(None,None)

    def __set__(self, instance, nValue):
        nValue = None if nValue is None else nValue.GetShortMGEFCode(instance)
        if nValue is None: _CDeleteField(instance._RecordID, instance._FieldID, instance._ListIndex, self._ListFieldID, 0, 0, 0, 0)
        else: _CSetField(instance._RecordID, instance._FieldID, instance._ListIndex, self._ListFieldID, 0, 0, 0, 0, byref(c_ulong(nValue)), 0)

class CBashFORMID_OR_MGEFCODE_OR_ACTORVALUE_OR_UINT32_LIST(object):
    __slots__ = [u'_ListFieldID']
    def __init__(self, ListFieldID):
        self._ListFieldID = ListFieldID

    def __get__(self, instance, owner):
        fieldtype = _CGetFieldAttribute(instance._RecordID, instance._FieldID, instance._ListIndex, self._ListFieldID, 0, 0, 0, 0, 2)
        _CGetField.restype = POINTER(c_char * 4) if fieldtype == API_FIELDS.CHAR4 else POINTER(c_ulong)
        retValue = _CGetField(instance._RecordID, instance._FieldID, instance._ListIndex, self._ListFieldID, 0, 0, 0, 0, 0)
        return (FormID(instance._RecordID, retValue.contents.value) if retValue else FormID(None,None)) if fieldtype == API_FIELDS.FORMID else (ActorValue(instance._RecordID, retValue.contents.value) if retValue else ActorValue(None,None)) if fieldtype in (API_FIELDS.STATIC_ACTORVALUE, API_FIELDS.RESOLVED_ACTORVALUE) else (MGEFCode(instance._RecordID, retValue.contents.value) if retValue else MGEFCode(None,None)) if fieldtype in (API_FIELDS.STATIC_MGEFCODE, API_FIELDS.RESOLVED_MGEFCODE) else retValue.contents.value if retValue else None

    def __set__(self, instance, nValue):
        fieldtype = _CGetFieldAttribute(instance._RecordID, instance._FieldID, instance._ListIndex, self._ListFieldID, 0, 0, 0, 0, 2)
        nValue = None if nValue is None else nValue.GetShortFormID(instance) if fieldtype == API_FIELDS.FORMID else nValue.GetShortActorValue(instance) if fieldtype in (API_FIELDS.STATIC_ACTORVALUE, API_FIELDS.RESOLVED_ACTORVALUE) else nValue.GetShortMGEFCode(instance) if fieldtype in (API_FIELDS.STATIC_MGEFCODE, API_FIELDS.RESOLVED_MGEFCODE) else nValue
        if nValue is None: _CDeleteField(instance._RecordID, instance._FieldID, instance._ListIndex, self._ListFieldID, 0, 0, 0, 0)
        else: _CSetField(instance._RecordID, instance._FieldID, instance._ListIndex, self._ListFieldID, 0, 0, 0, 0, byref(c_ulong(nValue)), 0)

class CBashUINT8ARRAY_LIST(object):
    __slots__ = [u'_ListFieldID', u'_Size']
    def __init__(self, ListFieldID, Size=None):
        self._ListFieldID, self._Size = ListFieldID, Size

    def __get__(self, instance, owner):
        numRecords = _CGetFieldAttribute(instance._RecordID, instance._FieldID, instance._ListIndex, self._ListFieldID, 0, 0, 0, 0, 1)
        if(numRecords > 0):
            cRecords = POINTER(c_ubyte * numRecords)()
            _CGetField(instance._RecordID, instance._FieldID, instance._ListIndex, self._ListFieldID, 0, 0, 0, 0, byref(cRecords))
            return [cRecords.contents[x] for x in xrange(numRecords)]
        return []

    def __set__(self, instance, nValue):
        if nValue is None or not len(nValue): _CDeleteField(instance._RecordID, instance._FieldID, instance._ListIndex, self._ListFieldID, 0, 0, 0, 0)
        else:
            length = len(nValue)
            if self._Size and length != self._Size: return
            _CSetField(instance._RecordID, instance._FieldID, instance._ListIndex, self._ListFieldID, 0, 0, 0, 0, byref((c_ubyte * length)(*nValue)), length)

class CBashUINT32ARRAY_LIST(object):
    __slots__ = [u'_ListFieldID', u'_Size']
    def __init__(self, ListFieldID, Size=None):
        self._ListFieldID, self._Size = ListFieldID, Size

    def __get__(self, instance, owner):
        numRecords = _CGetFieldAttribute(instance._RecordID, instance._FieldID, instance._ListIndex, self._ListFieldID, 0, 0, 0, 0, 1)
        if(numRecords > 0):
            cRecords = POINTER(c_ulong * numRecords)()
            _CGetField(instance._RecordID, instance._FieldID, instance._ListIndex, self._ListFieldID, 0, 0, 0, 0, byref(cRecords))
            return [cRecords.contents[x] for x in xrange(numRecords)]
        return []

    def __set__(self, instance, nValue):
        if nValue is None or not len(nValue): _CDeleteField(instance._RecordID, instance._FieldID, instance._ListIndex, self._ListFieldID, 0, 0, 0, 0)
        else:
            length = len(nValue)
            if self._Size and length != self._Size: return
            _CSetField(instance._RecordID, instance._FieldID, instance._ListIndex, self._ListFieldID, 0, 0, 0, 0, byref((c_ulong * length)(*nValue)), length)

class CBashFORMID_OR_UINT32_ARRAY_LIST(object):
    __slots__ = [u'_ListFieldID', u'_Size']
    def __init__(self, ListFieldID, Size=None):
        self._ListFieldID, self._Size = ListFieldID, Size

    def __get__(self, instance, owner):
        numRecords = _CGetFieldAttribute(instance._RecordID, instance._FieldID, instance._ListIndex, self._ListFieldID, 0, 0, 0, 0, 1)
        if(numRecords > 0):
            cRecords = (c_ulong * numRecords)()
            _CGetField(instance._RecordID, instance._FieldID, instance._ListIndex, self._ListFieldID, 0, 0, 0, 0, byref(cRecords))
            return [FormID(instance._RecordID, cRecord) if _CGetFieldAttribute(instance._RecordID, instance._FieldID, instance._ListIndex, self._ListFieldID, x, 1, 0, 0, 2) == API_FIELDS.FORMID else cRecord for x, cRecord in enumerate(cRecords)]
        return []

    def __set__(self, instance, nValue):
        if nValue is None or not len(nValue): _CDeleteField(instance._RecordID, instance._FieldID, instance._ListIndex, self._ListFieldID, 0, 0, 0, 0)
        else:
            nValue = [x for x in nValue if x is not None or (isinstance(x, FormID) and x.GetShortFormID(instance) is not None)]
            length = len(nValue)
            if self._Size and length != self._Size: return
            #Each element can be either a formID or UINT32, so they have to be set separately
            #Resize the list
            _CSetField(instance._RecordID, instance._FieldID, instance._ListIndex, self._ListFieldID, 0, 0, 0, 0, 0, c_long(length))
            for x, value in enumerate(nValue):
                #Borrowing ArraySize to flag if the new value is a formID
                IsFormID = isinstance(value, FormID)
                _CSetField(instance._RecordID, instance._FieldID, instance._ListIndex, self._ListFieldID, x, 1, 0, 0, byref(c_ulong(value.GetShortFormID(instance) if IsFormID else value)), IsFormID)

class CBashFLOAT32_LIST(object):
    __slots__ = [u'_ListFieldID']
    def __init__(self, ListFieldID):
        self._ListFieldID = ListFieldID

    def __get__(self, instance, owner):
        _CGetField.restype = POINTER(c_float)
        retValue = _CGetField(instance._RecordID, instance._FieldID, instance._ListIndex, self._ListFieldID, 0, 0, 0, 0, 0)
        return round(retValue.contents.value,6) if retValue else None

    def __set__(self, instance, nValue):
        if nValue is None: _CDeleteField(instance._RecordID, instance._FieldID, instance._ListIndex, self._ListFieldID, 0, 0, 0, 0)
        else: _CSetField(instance._RecordID, instance._FieldID, instance._ListIndex, self._ListFieldID, 0, 0, 0, 0, byref(c_float(round(nValue,6))), 0)

class CBashSTRING_LIST(object):
    __slots__ = [u'_ListFieldID']
    def __init__(self, ListFieldID):
        self._ListFieldID = ListFieldID

    def __get__(self, instance, owner):
        _CGetField.restype = c_char_p
        retValue = _CGetField(instance._RecordID, instance._FieldID, instance._ListIndex, self._ListFieldID, 0, 0, 0, 0, 0)
        return _unicode(retValue) if retValue else None

    def __set__(self, instance, nValue):
        if nValue is None: _CDeleteField(instance._RecordID, instance._FieldID, instance._ListIndex, self._ListFieldID, 0, 0, 0, 0)
        else: _CSetField(instance._RecordID, instance._FieldID, instance._ListIndex, self._ListFieldID, 0, 0, 0, 0, _encode(nValue), 0)

class CBashISTRING_LIST(object):
    __slots__ = [u'_ListFieldID']
    def __init__(self, ListFieldID):
        self._ListFieldID = ListFieldID

    def __get__(self, instance, owner):
        _CGetField.restype = c_char_p
        retValue = _CGetField(instance._RecordID, instance._FieldID, instance._ListIndex, self._ListFieldID, 0, 0, 0, 0, 0)
        return IUNICODE(_unicode(retValue)) if retValue else None

    def __set__(self, instance, nValue):
        if nValue is None: _CDeleteField(instance._RecordID, instance._FieldID, instance._ListIndex, self._ListFieldID, 0, 0, 0, 0)
        else: _CSetField(instance._RecordID, instance._FieldID, instance._ListIndex, self._ListFieldID, 0, 0, 0, 0, _encode(nValue), 0)

# ListX2 Descriptors
class CBashLIST_LISTX2(object):
    __slots__ = [u'_ListX2FieldID', u'_Type', u'_AsList']
    def __init__(self, ListX2FieldID, Type, AsList=False):
        self._ListX2FieldID, self._Type, self._AsList = ListX2FieldID, Type, AsList

    def __get__(self, instance, owner):
        return ExtractCopyList([self._Type(instance._RecordID, instance._FieldID, instance._ListIndex, instance._ListFieldID, instance._ListX2Index, self._ListX2FieldID, x) for x in xrange(_CGetFieldAttribute(instance._RecordID, instance._FieldID, instance._ListIndex, instance._ListFieldID, instance._ListX2Index, self._ListX2FieldID, 0, 0, 1))]) if self._AsList else [self._Type(instance._RecordID, instance._FieldID, instance._ListIndex, instance._ListFieldID, instance._ListX2Index, self._ListX2FieldID, x) for x in xrange(_CGetFieldAttribute(instance._RecordID, instance._FieldID, instance._ListIndex, instance._ListFieldID, instance._ListX2Index, self._ListX2FieldID, 0, 0, 1))]

    def __set__(self, instance, nElements):
        if nElements is None or not len(nElements): _CDeleteField(instance._RecordID, instance._FieldID, instance._ListIndex, instance._ListFieldID, instance._ListX2Index, self._ListX2FieldID, 0, 0)
        else:
            length = len(nElements)
            if not isinstance(nElements[0], tuple): nElements = ExtractCopyList(nElements)
            ##Resizes the list
            _CSetField(instance._RecordID, instance._FieldID, instance._ListIndex, instance._ListFieldID, instance._ListX2Index, self._ListX2FieldID, 0, 0, 0, c_long(length))
            SetCopyList([self._Type(instance._RecordID, instance._FieldID, instance._ListIndex, instance._ListFieldID, instance._ListX2Index, self._ListX2FieldID, x) for x in xrange(_CGetFieldAttribute(instance._RecordID, instance._FieldID, instance._ListIndex, instance._ListFieldID, instance._ListX2Index, self._ListX2FieldID, 0, 0, 1))], nElements)

class CBashGeneric_LISTX2(object):
    __slots__ = [u'_ListX2FieldID', u'_Type', u'_ResType']
    def __init__(self, ListX2FieldID, Type):
        self._ListX2FieldID, self._Type, self._ResType = ListX2FieldID, Type, POINTER(Type)

    def __get__(self, instance, owner):
        _CGetField.restype = self._ResType
        retValue = _CGetField(instance._RecordID, instance._FieldID, instance._ListIndex, instance._ListFieldID, instance._ListX2Index, self._ListX2FieldID, 0, 0, 0)
        return retValue.contents.value if retValue else None

    def __set__(self, instance, nValue):
        if nValue is None: _CDeleteField(instance._RecordID, instance._FieldID, instance._ListIndex, instance._ListFieldID, instance._ListX2Index, self._ListX2FieldID, 0, 0)
        else: _CSetField(instance._RecordID, instance._FieldID, instance._ListIndex, instance._ListFieldID, instance._ListX2Index, self._ListX2FieldID, 0, 0, byref(self._Type(nValue)), 0)

class CBashFLOAT32_LISTX2(object):
    __slots__ = [u'_ListX2FieldID']
    def __init__(self, ListX2FieldID):
        self._ListX2FieldID = ListX2FieldID

    def __get__(self, instance, owner):
        _CGetField.restype = POINTER(c_float)
        retValue = _CGetField(instance._RecordID, instance._FieldID, instance._ListIndex, instance._ListFieldID, instance._ListX2Index, self._ListX2FieldID, 0, 0, 0)
        return round(retValue.contents.value,6) if retValue else None

    def __set__(self, instance, nValue):
        if nValue is None: _CDeleteField(instance._RecordID, instance._FieldID, instance._ListIndex, instance._ListFieldID, instance._ListX2Index, self._ListX2FieldID, 0, 0)
        else: _CSetField(instance._RecordID, instance._FieldID, instance._ListIndex, instance._ListFieldID, instance._ListX2Index, self._ListX2FieldID, 0, 0, byref(c_float(round(nValue,6))), 0)

class CBashDEGREES_LISTX2(object):
    __slots__ = [u'_ListX2FieldID']
    def __init__(self, ListX2FieldID):
        self._ListX2FieldID = ListX2FieldID

    def __get__(self, instance, owner):
        _CGetField.restype = POINTER(c_float)
        retValue = _CGetField(instance._RecordID, instance._FieldID, instance._ListIndex, instance._ListFieldID, instance._ListX2Index, self._ListX2FieldID, 0, 0, 0)
        return round(math.degrees(retValue.contents.value),6) if retValue else None

    def __set__(self, instance, nValue):
        try: nValue = math.radians(nValue)
        except TypeError: nValue = None
        if nValue is None: _CDeleteField(instance._RecordID, instance._FieldID, instance._ListIndex, instance._ListFieldID, instance._ListX2Index, self._ListX2FieldID, 0, 0)
        else: _CSetField(instance._RecordID, instance._FieldID, instance._ListIndex, instance._ListFieldID, instance._ListX2Index, self._ListX2FieldID, 0, 0, byref(c_float(round(nValue,6))), 0)

class CBashUINT8ARRAY_LISTX2(object):
    __slots__ = [u'_ListX2FieldID', u'_Size']
    def __init__(self, ListX2FieldID, Size=None):
        self._ListX2FieldID, self._Size = ListX2FieldID, Size

    def __get__(self, instance, owner):
        numRecords = _CGetFieldAttribute(instance._RecordID, instance._FieldID, instance._ListIndex, instance._ListFieldID, instance._ListX2Index, self._ListX2FieldID, 0, 0, 1)
        if(numRecords > 0):
            cRecords = POINTER(c_ubyte * numRecords)()
            _CGetField(instance._RecordID, instance._FieldID, instance._ListIndex, instance._ListFieldID, instance._ListX2Index, self._ListX2FieldID, 0, 0, byref(cRecords))
            return [cRecords.contents[x] for x in xrange(numRecords)]
        return []

    def __set__(self, instance, nValue):
        if nValue is None or not len(nValue): _CDeleteField(instance._RecordID, instance._FieldID, instance._ListIndex, instance._ListFieldID, instance._ListX2Index, self._ListX2FieldID, 0, 0)
        else:
            length = len(nValue)
            if self._Size and length != self._Size: return
            _CSetField(instance._RecordID, instance._FieldID, instance._ListIndex, instance._ListFieldID, instance._ListX2Index, self._ListX2FieldID, 0, 0, byref((c_ubyte * length)(*nValue)), length)

class CBashFORMID_OR_UINT32_ARRAY_LISTX2(object):
    __slots__ = [u'_ListX2FieldID', u'_Size']
    def __init__(self, ListX2FieldID, Size=None):
        self._ListX2FieldID, self._Size = ListX2FieldID, Size

    def __get__(self, instance, owner):
        numRecords = _CGetFieldAttribute(instance._RecordID, instance._FieldID, instance._ListIndex, instance._ListFieldID, instance._ListX2Index, self._ListX2FieldID, 0, 0, 1)
        if(numRecords > 0):
            cRecords = (c_ulong * numRecords)()
            _CGetField(instance._RecordID, instance._FieldID, instance._ListIndex, instance._ListFieldID, instance._ListX2Index, self._ListX2FieldID, 0, 0, byref(cRecords))
            return [FormID(instance._RecordID, cRecord) if _CGetFieldAttribute(instance._RecordID, instance._FieldID, instance._ListIndex, instance._ListFieldID, instance._ListX2Index, self._ListX2FieldID, x, 1, 2) == API_FIELDS.FORMID else cRecord for x, cRecord in enumerate(cRecords)]
        return []

    def __set__(self, instance, nValue):
        if nValue is None or not len(nValue): _CDeleteField(instance._RecordID, instance._FieldID, instance._ListIndex, instance._ListFieldID, instance._ListX2Index, self._ListX2FieldID, 0, 0)
        else:
            nValue = [x for x in nValue if x is not None or (isinstance(x, FormID) and x.GetShortFormID(instance) is not None)]
            length = len(nValue)
            if self._Size and length != self._Size: return
            #Each element can be either a formID or UINT32, so they have to be set separately
            #Resize the list
            _CSetField(instance._RecordID, instance._FieldID, instance._ListIndex, instance._ListFieldID, instance._ListX2Index, self._ListX2FieldID, 0, 0, 0, c_long(length))
            for x, value in enumerate(nValue):
                #Borrowing ArraySize to flag if the new value is a formID
                IsFormID = isinstance(value, FormID)
                _CSetField(instance._RecordID, instance._FieldID, instance._ListIndex, instance._ListFieldID, instance._ListX2Index, self._ListX2FieldID, x, 1, byref(c_ulong(value.GetShortFormID(instance) if IsFormID else value)), IsFormID)

class CBashFORMID_LISTX2(object):
    __slots__ = [u'_ListX2FieldID']
    def __init__(self, ListX2FieldID):
        self._ListX2FieldID = ListX2FieldID

    def __get__(self, instance, owner):
        _CGetField.restype = POINTER(c_ulong)
        retValue = _CGetField(instance._RecordID, instance._FieldID, instance._ListIndex, instance._ListFieldID, instance._ListX2Index, self._ListX2FieldID, 0, 0, 0)
        return FormID(instance._RecordID, retValue.contents.value) if retValue else FormID(None,None)

    def __set__(self, instance, nValue):
        nValue = None if nValue is None else nValue.GetShortFormID(instance)
        if nValue is None: _CDeleteField(instance._RecordID, instance._FieldID, instance._ListIndex, instance._ListFieldID, instance._ListX2Index, self._ListX2FieldID, 0, 0)
        else: _CSetField(instance._RecordID, instance._FieldID, instance._ListIndex, instance._ListFieldID, instance._ListX2Index, self._ListX2FieldID, 0, 0, byref(c_ulong(nValue)), 0)

class CBashFORMID_OR_FLOAT32_LISTX2(object):
    __slots__ = [u'_ListX2FieldID']
    def __init__(self, ListX2FieldID):
        self._ListX2FieldID = ListX2FieldID

    def __get__(self, instance, owner):
        IsFormID = _CGetFieldAttribute(instance._RecordID, instance._FieldID, instance._ListIndex, instance._ListFieldID, instance._ListX2Index, self._ListX2FieldID, 0, 0, 2) == API_FIELDS.FORMID
        _CGetField.restype = POINTER(c_ulong) if IsFormID else POINTER(c_float)
        retValue = _CGetField(instance._RecordID, instance._FieldID, instance._ListIndex, instance._ListFieldID, instance._ListX2Index, self._ListX2FieldID, 0, 0, 0)
        return (FormID(instance._RecordID, retValue.contents.value) if retValue else FormID(None,None)) if IsFormID else round(retValue.contents.value,6) if retValue else None

    def __set__(self, instance, nValue):
        IsFormID = _CGetFieldAttribute(instance._RecordID, instance._FieldID, instance._ListIndex, instance._ListFieldID, instance._ListX2Index, self._ListX2FieldID, 0, 0, 2) == API_FIELDS.FORMID
        try: nValue = None if nValue is None else nValue.GetShortFormID(instance) if IsFormID else float(round(nValue,6))
        except TypeError: nValue = None
        if nValue is None: _CDeleteField(instance._RecordID, instance._FieldID, instance._ListIndex, instance._ListFieldID, instance._ListX2Index, self._ListX2FieldID, 0, 0)
        else: _CSetField(instance._RecordID, instance._FieldID, instance._ListIndex, instance._ListFieldID, instance._ListX2Index, self._ListX2FieldID, 0, 0, byref(c_ulong(nValue)) if IsFormID else byref(nValue), 0)

class CBashSTRING_LISTX2(object):
    __slots__ = [u'_ListX2FieldID']
    def __init__(self, ListX2FieldID):
        self._ListX2FieldID = ListX2FieldID

    def __get__(self, instance, owner):
        _CGetField.restype = c_char_p
        retValue = _CGetField(instance._RecordID, instance._FieldID, instance._ListIndex, instance._ListFieldID, instance._ListX2Index, self._ListX2FieldID, 0, 0, 0)
        return _unicode(retValue) if retValue else None

    def __set__(self, instance, nValue):
        if nValue is None: _CDeleteField(instance._RecordID, instance._FieldID, instance._ListIndex, instance._ListFieldID, instance._ListX2Index, self._ListX2FieldID, 0, 0)
        else: _CSetField(instance._RecordID, instance._FieldID, instance._ListIndex, instance._ListFieldID, instance._ListX2Index, self._ListX2FieldID, 0, 0, _encode(nValue), 0)

class CBashISTRING_LISTX2(object):
    __slots__ = [u'_ListX2FieldID']
    def __init__(self, ListX2FieldID):
        self._ListX2FieldID = ListX2FieldID

    def __get__(self, instance, owner):
        _CGetField.restype = c_char_p
        retValue = _CGetField(instance._RecordID, instance._FieldID, instance._ListIndex, instance._ListFieldID, instance._ListX2Index, self._ListX2FieldID, 0, 0, 0)
        return IUNICODE(_unicode(retValue)) if retValue else None

    def __set__(self, instance, nValue):
        if nValue is None: _CDeleteField(instance._RecordID, instance._FieldID, instance._ListIndex, instance._ListFieldID, instance._ListX2Index, self._ListX2FieldID, 0, 0)
        else: _CSetField(instance._RecordID, instance._FieldID, instance._ListIndex, instance._ListFieldID, instance._ListX2Index, self._ListX2FieldID, 0, 0, _encode(nValue), 0)

class CBashUNKNOWN_OR_FORMID_OR_UINT32_LISTX2(object):
    __slots__ = [u'_ListX2FieldID']
    def __init__(self, ListX2FieldID):
        self._ListX2FieldID = ListX2FieldID

    def __get__(self, instance, owner):
        fieldtype = _CGetFieldAttribute(instance._RecordID, instance._FieldID, instance._ListIndex, instance._ListFieldID, instance._ListX2Index, self._ListX2FieldID, 0, 0, 2)
        if fieldtype == API_FIELDS.UNKNOWN: return None
        _CGetField.restype = POINTER(c_ulong)
        retValue = _CGetField(instance._RecordID, instance._FieldID, instance._ListIndex, instance._ListFieldID, instance._ListX2Index, self._ListX2FieldID, 0, 0, 0)
        return (FormID(instance._RecordID, retValue.contents.value) if retValue else FormID(None,None)) if fieldtype == API_FIELDS.FORMID else retValue.contents.value if retValue else None

    def __set__(self, instance, nValue):
        fieldtype = _CGetFieldAttribute(instance._RecordID, instance._FieldID, instance._ListIndex, instance._ListFieldID, instance._ListX2Index, self._ListX2FieldID, 0, 0, 2)
        if fieldtype == API_FIELDS.UNKNOWN: return
        nValue = None if nValue is None else nValue.GetShortFormID(instance) if fieldtype == API_FIELDS.FORMID else nValue
        if nValue is None: _CDeleteField(instance._RecordID, instance._FieldID, instance._ListIndex, instance._ListFieldID, instance._ListX2Index, self._ListX2FieldID, 0, 0)
        else: _CSetField(instance._RecordID, instance._FieldID, instance._ListIndex, instance._ListFieldID, instance._ListX2Index, self._ListX2FieldID, 0, 0, byref(c_ulong(nValue)), 0)

# ListX3 Descriptors
class CBashGeneric_LISTX3(object):
    __slots__ = [u'_ListX3FieldID', u'_Type', u'_ResType']
    def __init__(self, ListX3FieldID, Type):
        self._ListX3FieldID, self._Type, self._ResType = ListX3FieldID, Type, POINTER(Type)

    def __get__(self, instance, owner):
        _CGetField.restype = self._ResType
        retValue = _CGetField(instance._RecordID, instance._FieldID, instance._ListIndex, instance._ListFieldID, instance._ListX2Index, instance._ListX2FieldID, instance._ListX3Index, self._ListX3FieldID, 0)
        return retValue.contents.value if retValue else None

    def __set__(self, instance, nValue):
        if nValue is None: _CDeleteField(instance._RecordID, instance._FieldID, instance._ListIndex, instance._ListFieldID, instance._ListX2Index, instance._ListX2FieldID, instance._ListX3Index, self._ListX3FieldID)
        else: _CSetField(instance._RecordID, instance._FieldID, instance._ListIndex, instance._ListFieldID, instance._ListX2Index, instance._ListX2FieldID, instance._ListX3Index, self._ListX3FieldID, byref(self._Type(nValue)), 0)

class CBashUINT8ARRAY_LISTX3(object):
    __slots__ = [u'_ListX3FieldID', u'_Size']
    def __init__(self, ListX3FieldID, Size=None):
        self._ListX3FieldID, self._Size = ListX3FieldID, Size

    def __get__(self, instance, owner):
        numRecords = _CGetFieldAttribute(instance._RecordID, instance._FieldID, instance._ListIndex, instance._ListFieldID, instance._ListX2Index, instance._ListX2FieldID, instance._ListX3Index, self._ListX3FieldID, 1)
        if(numRecords > 0):
            cRecords = POINTER(c_ubyte * numRecords)()
            _CGetField(instance._RecordID, instance._FieldID, instance._ListIndex, instance._ListFieldID, instance._ListX2Index, instance._ListX2FieldID, instance._ListX3Index, self._ListX3FieldID, byref(cRecords))
            return [cRecords.contents[x] for x in xrange(numRecords)]
        return []

    def __set__(self, instance, nValue):
        if nValue is None or not len(nValue): _CDeleteField(instance._RecordID, instance._FieldID, instance._ListIndex, instance._ListFieldID, instance._ListX2Index, instance._ListX2FieldID, instance._ListX3Index, self._ListX3FieldID)
        else:
            length = len(nValue)
            if self._Size and length != self._Size: return
            _CSetField(instance._RecordID, instance._FieldID, instance._ListIndex, instance._ListFieldID, instance._ListX2Index, instance._ListX2FieldID, instance._ListX3Index, self._ListX3FieldID, byref((c_ubyte * length)(*nValue)), length)

class CBashFORMID_OR_FLOAT32_LISTX3(object):
    __slots__ = [u'_ListX3FieldID']
    def __init__(self, ListX3FieldID):
        self._ListX3FieldID = ListX3FieldID

    def __get__(self, instance, owner):
        IsFormID = _CGetFieldAttribute(instance._RecordID, instance._FieldID, instance._ListIndex, instance._ListFieldID, instance._ListX2Index, instance._ListX2FieldID, instance._ListX3Index, self._ListX3FieldID, 2) == API_FIELDS.FORMID
        _CGetField.restype = POINTER(c_ulong) if IsFormID else POINTER(c_float)
        retValue = _CGetField(instance._RecordID, instance._FieldID, instance._ListIndex, instance._ListFieldID, instance._ListX2Index, instance._ListX2FieldID, instance._ListX3Index, self._ListX3FieldID, 0)
        return (FormID(instance._RecordID, retValue.contents.value) if retValue else FormID(None,None)) if IsFormID else round(retValue.contents.value,6) if retValue else None

    def __set__(self, instance, nValue):
        IsFormID = _CGetFieldAttribute(instance._RecordID, instance._FieldID, instance._ListIndex, instance._ListFieldID, instance._ListX2Index, instance._ListX2FieldID, instance._ListX3Index, self._ListX3FieldID, 2) == API_FIELDS.FORMID
        try: nValue = None if nValue is None else nValue.GetShortFormID(instance) if IsFormID else float(round(nValue,6))
        except TypeError: nValue = None
        if nValue is None: _CDeleteField(instance._RecordID, instance._FieldID, instance._ListIndex, instance._ListFieldID, instance._ListX2Index, instance._ListX2FieldID, instance._ListX3Index, self._ListX3FieldID)
        else: _CSetField(instance._RecordID, instance._FieldID, instance._ListIndex, instance._ListFieldID, instance._ListX2Index, instance._ListX2FieldID, instance._ListX3Index, self._ListX3FieldID, byref(c_ulong(nValue)) if IsFormID else byref(nValue), 0)

class CBashFLOAT32_LISTX3(object):
    __slots__ = [u'_ListX3FieldID']
    def __init__(self, ListX3FieldID):
        self._ListX3FieldID = ListX3FieldID

    def __get__(self, instance, owner):
        _CGetField.restype = POINTER(c_float)
        retValue = _CGetField(instance._RecordID, instance._FieldID, instance._ListIndex, instance._ListFieldID, instance._ListX2Index, instance._ListX2FieldID, instance._ListX3Index, self._ListX3FieldID, 0)
        return round(retValue.contents.value,6) if retValue else None

    def __set__(self, instance, nValue):
        if nValue is None: _CDeleteField(instance._RecordID, instance._FieldID, instance._ListIndex, instance._ListFieldID, instance._ListX2Index, instance._ListX2FieldID, instance._ListX3Index, self._ListX3FieldID)
        else: _CSetField(instance._RecordID, instance._FieldID, instance._ListIndex, instance._ListFieldID, instance._ListX2Index, instance._ListX2FieldID, instance._ListX3Index, self._ListX3FieldID, byref(c_float(round(nValue,6))), 0)

class CBashSTRING_LISTX3(object):
    __slots__ = [u'_ListX3FieldID']
    def __init__(self, ListX3FieldID):
        self._ListX3FieldID = ListX3FieldID

    def __get__(self, instance, owner):
        _CGetField.restype = c_char_p
        retValue = _CGetField(instance._RecordID, instance._FieldID, instance._ListIndex, instance._ListFieldID, instance._ListX2Index, instance._ListX2FieldID, instance._ListX3Index, self._ListX3FieldID, 0)
        return _unicode(retValue) if retValue else None

    def __set__(self, instance, nValue):
        if nValue is None: _CDeleteField(instance._RecordID, instance._FieldID, instance._ListIndex, instance._ListFieldID, instance._ListX2Index, instance._ListX2FieldID, instance._ListX3Index, self._ListX3FieldID)
        else: _CSetField(instance._RecordID, instance._FieldID, instance._ListIndex, instance._ListFieldID, instance._ListX2Index, instance._ListX2FieldID, instance._ListX3Index, self._ListX3FieldID, _encode(nValue), 0)

class CBashISTRING_LISTX3(object):
    __slots__ = [u'_ListX3FieldID']
    def __init__(self, ListX3FieldID):
        self._ListX3FieldID = ListX3FieldID

    def __get__(self, instance, owner):
        _CGetField.restype = c_char_p
        retValue = _CGetField(instance._RecordID, instance._FieldID, instance._ListIndex, instance._ListFieldID, instance._ListX2Index, instance._ListX2FieldID, instance._ListX3Index, self._ListX3FieldID, 0)
        return IUNICODE(_unicode(retValue)) if retValue else None

    def __set__(self, instance, nValue):
        if nValue is None: _CDeleteField(instance._RecordID, instance._FieldID, instance._ListIndex, instance._ListFieldID, instance._ListX2Index, instance._ListX2FieldID, instance._ListX3Index, self._ListX3FieldID)
        else: _CSetField(instance._RecordID, instance._FieldID, instance._ListIndex, instance._ListFieldID, instance._ListX2Index, instance._ListX2FieldID, instance._ListX3Index, self._ListX3FieldID, _encode(nValue), 0)

class CBashUNKNOWN_OR_FORMID_OR_UINT32_LISTX3(object):
    __slots__ = [u'_ListX3FieldID']
    def __init__(self, ListX3FieldID):
        self._ListX3FieldID = ListX3FieldID

    def __get__(self, instance, owner):
        fieldtype = _CGetFieldAttribute(instance._RecordID, instance._FieldID, instance._ListIndex, instance._ListFieldID, instance._ListX2Index, instance._ListX2FieldID, instance._ListX3Index, self._ListX3FieldID, 2)
        if fieldtype == API_FIELDS.UNKNOWN: return None
        _CGetField.restype = POINTER(c_ulong)
        retValue = _CGetField(instance._RecordID, instance._FieldID, instance._ListIndex, instance._ListFieldID, instance._ListX2Index, instance._ListX2FieldID, instance._ListX3Index, self._ListX3FieldID, 0)
        return (FormID(instance._RecordID, retValue.contents.value) if retValue else FormID(None,None)) if fieldtype == API_FIELDS.FORMID else retValue.contents.value if retValue else None

    def __set__(self, instance, nValue):
        fieldtype = _CGetFieldAttribute(instance._RecordID, instance._FieldID, instance._ListIndex, instance._ListFieldID, instance._ListX2Index, instance._ListX2FieldID, instance._ListX3Index, self._ListX3FieldID, 2)
        if fieldtype == API_FIELDS.UNKNOWN: return
        nValue = None if nValue is None else nValue.GetShortFormID(instance) if fieldtype == API_FIELDS.FORMID else nValue
        if nValue is None: _CDeleteField(instance._RecordID, instance._FieldID, instance._ListIndex, instance._ListFieldID, instance._ListX2Index, instance._ListX2FieldID, instance._ListX3Index, self._ListX3FieldID)
        else: _CSetField(instance._RecordID, instance._FieldID, instance._ListIndex, instance._ListFieldID, instance._ListX2Index, instance._ListX2FieldID, instance._ListX3Index, self._ListX3FieldID, byref(c_ulong(nValue)), 0)

#Record accessors
#--Accessor Components
class BaseComponent(object):
    __slots__ = [u'_RecordID', u'_FieldID']
    def __init__(self, RecordID, FieldID):
        self._RecordID, self._FieldID = RecordID, FieldID

    def GetParentCollection(self):
        return ObCollection(_CGetCollectionIDByRecordID(self._RecordID))

class ListComponent(object):
    __slots__ = [u'_RecordID', u'_FieldID', u'_ListIndex']
    def __init__(self, RecordID, FieldID, ListIndex):
        self._RecordID, self._FieldID, self._ListIndex = RecordID, FieldID, ListIndex

    def GetParentCollection(self):
        return ObCollection(_CGetCollectionIDByRecordID(self._RecordID))

class ListX2Component(object):
    __slots__ = [u'_RecordID', u'_FieldID', u'_ListIndex', u'_ListFieldID', u'_ListX2Index']
    def __init__(self, RecordID, FieldID, ListIndex, ListFieldID, ListX2Index):
        self._RecordID, self._FieldID, self._ListIndex, self._ListFieldID, self._ListX2Index = RecordID, FieldID, ListIndex, ListFieldID, ListX2Index

    def GetParentCollection(self):
        return ObCollection(_CGetCollectionIDByRecordID(self._RecordID))

class ListX3Component(object):
    __slots__ = [u'_RecordID', u'_FieldID', u'_ListIndex', u'_ListFieldID', u'_ListX2Index', u'_ListX2FieldID', u'_ListX3Index']
    def __init__(self, RecordID, FieldID, ListIndex, ListFieldID, ListX2Index, ListX2FieldID, ListX3Index):
        self._RecordID, self._FieldID, self._ListIndex, self._ListFieldID, self._ListX2Index, self._ListX2FieldID, self._ListX3Index = RecordID, FieldID, ListIndex, ListFieldID, ListX2Index, ListX2FieldID, ListX3Index

    def GetParentCollection(self):
        return ObCollection(_CGetCollectionIDByRecordID(self._RecordID))

class Model(BaseComponent):
    __slots__ = []
    modPath = CBashISTRING_GROUP(0)
    modb = CBashFLOAT32_GROUP(1)
    modt_p = CBashUINT8ARRAY_GROUP(2)
    copyattrs = [u'modPath', u'modb', u'modt_p']
    exportattrs = copyattrs[:]
    exportattrs.remove(u'modt_p')

class Item(ListComponent):
    __slots__ = []
    item = CBashFORMID_LIST(1)
    count = CBashGeneric_LIST(2, c_long)
    exportattrs = copyattrs = [u'item', u'count']

class FNVItem(ListComponent):
    __slots__ = []
    item = CBashFORMID_LIST(1)
    count = CBashGeneric_LIST(2, c_long)
    owner = CBashFORMID_LIST(3)
    globalOrRank = CBashUNKNOWN_OR_FORMID_OR_UINT32_LIST(4)
    condition = CBashFLOAT32_LIST(5)
    exportattrs = copyattrs = [u'item', u'count', u'owner',
                               u'globalOrRank', u'condition']

class Condition(ListComponent):
    __slots__ = []
    operType = CBashGeneric_LIST(1, c_ubyte)
    unused1 = CBashUINT8ARRAY_LIST(2, 3)
    compValue = CBashFLOAT32_LIST(3)
    ifunc = CBashGeneric_LIST(4, c_ulong)
    param1 = CBashUNKNOWN_OR_FORMID_OR_UINT32_LIST(5)
    param2 = CBashUNKNOWN_OR_FORMID_OR_UINT32_LIST(6)
    unused2 = CBashUINT8ARRAY_LIST(7, 4)
    IsEqual = CBashMaskedType(u'operType', 0xF0, 0x00, u'IsNotEqual')
    IsNotEqual = CBashMaskedType(u'operType', 0xF0, 0x20, u'IsEqual')
    IsGreater = CBashMaskedType(u'operType', 0xF0, 0x40, u'IsEqual')
    IsGreaterOrEqual = CBashMaskedType(u'operType', 0xF0, 0x60, u'IsEqual')
    IsLess = CBashMaskedType(u'operType', 0xF0, 0x80, u'IsEqual')
    IsLessOrEqual = CBashMaskedType(u'operType', 0xF0, 0xA0, u'IsEqual')
    IsOr = CBashBasicFlag(u'operType', 0x01)
    IsRunOnTarget = CBashBasicFlag(u'operType', 0x02)
    IsUseGlobal = CBashBasicFlag(u'operType', 0x04)
    exportattrs = copyattrs = [u'operType', u'compValue', u'ifunc', u'param1',
                               u'param2']

class FNVCondition(ListComponent):
    __slots__ = []
    operType = CBashGeneric_LIST(1, c_ubyte)
    unused1 = CBashUINT8ARRAY_LIST(2, 3)
    compValue = CBashFLOAT32_LIST(3)
    ifunc = CBashGeneric_LIST(4, c_ulong)
    param1 = CBashUNKNOWN_OR_FORMID_OR_UINT32_LIST(5)
    param2 = CBashUNKNOWN_OR_FORMID_OR_UINT32_LIST(6)
    runOn = CBashGeneric_LIST(7, c_ulong)
    reference = CBashUNKNOWN_OR_FORMID_OR_UINT32_LIST(8)
    IsEqual = CBashMaskedType(u'operType', 0xF0, 0x00, u'IsNotEqual')
    IsNotEqual = CBashMaskedType(u'operType', 0xF0, 0x20, u'IsEqual')
    IsGreater = CBashMaskedType(u'operType', 0xF0, 0x40, u'IsEqual')
    IsGreaterOrEqual = CBashMaskedType(u'operType', 0xF0, 0x60, u'IsEqual')
    IsLess = CBashMaskedType(u'operType', 0xF0, 0x80, u'IsEqual')
    IsLessOrEqual = CBashMaskedType(u'operType', 0xF0, 0xA0, u'IsEqual')
    IsOr = CBashBasicFlag(u'operType', 0x01)
    IsRunOnTarget = CBashBasicFlag(u'operType', 0x02)
    IsUseGlobal = CBashBasicFlag(u'operType', 0x04)
    IsResultOnSubject = CBashBasicType(u'runOn', 0, u'IsResultOnTarget')
    IsResultOnTarget = CBashBasicType(u'runOn', 1, u'IsResultOnSubject')
    IsResultOnReference = CBashBasicType(u'runOn', 2, u'IsResultOnSubject')
    IsResultOnCombatTarget = CBashBasicType(u'runOn', 3, u'IsResultOnSubject')
    IsResultOnLinkedReference = CBashBasicType(u'runOn', 4, u'IsResultOnSubject')
    exportattrs = copyattrs = [u'operType', u'compValue', u'ifunc', u'param1',
                               u'param2', u'runOn', u'reference']

class FNVConditionX2(ListX2Component):
    __slots__ = []
    operType = CBashGeneric_LISTX2(1, c_ubyte)
    unused1 = CBashUINT8ARRAY_LISTX2(2, 3)
    compValue = CBashFORMID_OR_FLOAT32_LISTX2(3)
    ifunc = CBashGeneric_LISTX2(4, c_ulong)
    param1 = CBashUNKNOWN_OR_FORMID_OR_UINT32_LISTX2(5)
    param2 = CBashUNKNOWN_OR_FORMID_OR_UINT32_LISTX2(6)
    runOn = CBashGeneric_LISTX2(7, c_ulong)
    reference = CBashUNKNOWN_OR_FORMID_OR_UINT32_LISTX2(8)
    IsEqual = CBashMaskedType(u'operType', 0xF0, 0x00, u'IsNotEqual')
    IsNotEqual = CBashMaskedType(u'operType', 0xF0, 0x20, u'IsEqual')
    IsGreater = CBashMaskedType(u'operType', 0xF0, 0x40, u'IsEqual')
    IsGreaterOrEqual = CBashMaskedType(u'operType', 0xF0, 0x60, u'IsEqual')
    IsLess = CBashMaskedType(u'operType', 0xF0, 0x80, u'IsEqual')
    IsLessOrEqual = CBashMaskedType(u'operType', 0xF0, 0xA0, u'IsEqual')
    IsOr = CBashBasicFlag(u'operType', 0x01)
    IsRunOnTarget = CBashBasicFlag(u'operType', 0x02)
    IsUseGlobal = CBashBasicFlag(u'operType', 0x04)
    IsResultOnSubject = CBashBasicType(u'runOn', 0, u'IsResultOnTarget')
    IsResultOnTarget = CBashBasicType(u'runOn', 1, u'IsResultOnSubject')
    IsResultOnReference = CBashBasicType(u'runOn', 2, u'IsResultOnSubject')
    IsResultOnCombatTarget = CBashBasicType(u'runOn', 3, u'IsResultOnSubject')
    IsResultOnLinkedReference = CBashBasicType(u'runOn', 4, u'IsResultOnSubject')
    exportattrs = copyattrs = [u'operType', u'compValue', u'ifunc', u'param1',
                               u'param2', u'runOn', u'reference']

class FNVConditionX3(ListX3Component):
    __slots__ = []
    operType = CBashGeneric_LISTX3(1, c_ubyte)
    unused1 = CBashUINT8ARRAY_LISTX3(2, 3)
    compValue = CBashFORMID_OR_FLOAT32_LISTX3(3)
    ifunc = CBashGeneric_LISTX3(4, c_ulong)
    param1 = CBashUNKNOWN_OR_FORMID_OR_UINT32_LISTX3(5)
    param2 = CBashUNKNOWN_OR_FORMID_OR_UINT32_LISTX3(6)
    runOn = CBashGeneric_LISTX3(7, c_ulong)
    reference = CBashUNKNOWN_OR_FORMID_OR_UINT32_LISTX3(8)
    IsEqual = CBashMaskedType(u'operType', 0xF0, 0x00, u'IsNotEqual')
    IsNotEqual = CBashMaskedType(u'operType', 0xF0, 0x20, u'IsEqual')
    IsGreater = CBashMaskedType(u'operType', 0xF0, 0x40, u'IsEqual')
    IsGreaterOrEqual = CBashMaskedType(u'operType', 0xF0, 0x60, u'IsEqual')
    IsLess = CBashMaskedType(u'operType', 0xF0, 0x80, u'IsEqual')
    IsLessOrEqual = CBashMaskedType(u'operType', 0xF0, 0xA0, u'IsEqual')
    IsOr = CBashBasicFlag(u'operType', 0x01)
    IsRunOnTarget = CBashBasicFlag(u'operType', 0x02)
    IsUseGlobal = CBashBasicFlag(u'operType', 0x04)
    IsResultOnSubject = CBashBasicType(u'runOn', 0, u'IsResultOnTarget')
    IsResultOnTarget = CBashBasicType(u'runOn', 1, u'IsResultOnSubject')
    IsResultOnReference = CBashBasicType(u'runOn', 2, u'IsResultOnSubject')
    IsResultOnCombatTarget = CBashBasicType(u'runOn', 3, u'IsResultOnSubject')
    IsResultOnLinkedReference = CBashBasicType(u'runOn', 4, u'IsResultOnSubject')
    exportattrs = copyattrs = [u'operType', u'compValue', u'ifunc', u'param1',
                               u'param2', u'runOn', u'reference']

class Var(ListComponent):
    __slots__ = []
    index = CBashGeneric_LIST(1, c_ulong)
    unused1 = CBashUINT8ARRAY_LIST(2, 12)
    flags = CBashGeneric_LIST(3, c_ubyte)
    unused2 = CBashUINT8ARRAY_LIST(4, 7)
    name = CBashISTRING_LIST(5)

    IsLongOrShort = CBashBasicFlag(u'flags', 0x00000001)
    exportattrs = copyattrs = [u'index', u'flags', u'name']

class VarX2(ListX2Component):
    __slots__ = []
    index = CBashGeneric_LISTX2(1, c_ulong)
    unused1 = CBashUINT8ARRAY_LISTX2(2, 12)
    flags = CBashGeneric_LISTX2(3, c_ubyte)
    unused2 = CBashUINT8ARRAY_LISTX2(4, 7)
    name = CBashISTRING_LISTX2(5)

    IsLongOrShort = CBashBasicFlag(u'flags', 0x00000001)
    exportattrs = copyattrs = [u'index', u'flags', u'name']

class VarX3(ListX3Component):
    __slots__ = []
    index = CBashGeneric_LISTX3(1, c_ulong)
    unused1 = CBashUINT8ARRAY_LISTX3(2, 12)
    flags = CBashGeneric_LISTX3(3, c_ubyte)
    unused2 = CBashUINT8ARRAY_LISTX3(4, 7)
    name = CBashISTRING_LISTX3(5)

    IsLongOrShort = CBashBasicFlag(u'flags', 0x00000001)
    exportattrs = copyattrs = [u'index', u'flags', u'name']

class Effect(ListComponent):
    __slots__ = []
    ##name0 and name are both are always the same value, so setting one will set both. They're basically aliases
    name0 = CBashMGEFCODE_LIST(1)
    name = CBashMGEFCODE_LIST(2)
    magnitude = CBashGeneric_LIST(3, c_ulong)
    area = CBashGeneric_LIST(4, c_ulong)
    duration = CBashGeneric_LIST(5, c_ulong)
    rangeType = CBashGeneric_LIST(6, c_ulong)
    actorValue = CBashFORMID_OR_MGEFCODE_OR_ACTORVALUE_OR_UINT32_LIST(7) #OBME
    script = CBashFORMID_OR_MGEFCODE_OR_ACTORVALUE_OR_UINT32_LIST(8) #OBME
    schoolType = CBashGeneric_LIST(9, c_ulong)
    visual = CBashMGEFCODE_LIST(10) #OBME
    flags = CBashGeneric_LIST(11, c_ubyte)
    unused1 = CBashUINT8ARRAY_LIST(12, 3)
    full = CBashSTRING_LIST(13) #OBME
    IsHostile = CBashBasicFlag(u'flags', 0x01)
    IsSelf = CBashBasicType(u'rangeType', 0, u'IsTouch')
    IsTouch = CBashBasicType(u'rangeType', 1, u'IsSelf')
    IsTarget = CBashBasicType(u'rangeType', 2, u'IsSelf')
    IsAlteration = CBashBasicType(u'schoolType', 0, u'IsConjuration')
    IsConjuration = CBashBasicType(u'schoolType', 1, u'IsAlteration')
    IsDestruction = CBashBasicType(u'schoolType', 2, u'IsAlteration')
    IsIllusion = CBashBasicType(u'schoolType', 3, u'IsAlteration')
    IsMysticism = CBashBasicType(u'schoolType', 4, u'IsAlteration')
    IsRestoration = CBashBasicType(u'schoolType', 5, u'IsAlteration')
    ##OBME Fields. Setting any of the below fields will make the mod require JRoush's OBME plugin for OBSE
    ##To see if OBME is in use, check the recordVersion field for a non-None value
    recordVersion = CBashGeneric_LIST(14, c_ubyte) #OBME
    betaVersion = CBashGeneric_LIST(15, c_ubyte) #OBME
    minorVersion = CBashGeneric_LIST(16, c_ubyte) #OBME
    majorVersion = CBashGeneric_LIST(17, c_ubyte) #OBME
    efitParamInfo = CBashGeneric_LIST(18, c_ubyte) #OBME
    efixParamInfo = CBashGeneric_LIST(19, c_ubyte) #OBME
    reserved1 = CBashUINT8ARRAY_LIST(20, 0xA) #OBME
    iconPath = CBashISTRING_LIST(21) #OBME
    ##If efixOverrides ever equals 0, the EFIX chunk will become unloaded
    ##This includes the fields: efixOverrides,  efixFlags, baseCost, resistAV, reserved2
    efixOverrides = CBashGeneric_LIST(22, c_ulong) #OBME
    efixFlags = CBashGeneric_LIST(23, c_ulong) #OBME
    baseCost = CBashFLOAT32_LIST(24) #OBME
    resistAV = CBashACTORVALUE_LIST(25) #OBME
    reserved2 = CBashUINT8ARRAY_LIST(26, 0x10) #OBME
    ##OBME Fields. Setting any of the below fields will make the mod require JRoush's OBME plugin for OBSE
    ##To see if OBME is in use, check the recordVersion field for a non-None value
    IsUsingHostileOverride = CBashBasicFlag(u'efixOverrides', 0x00000001) #OBME
    IsUsingRecoversOverride = CBashBasicFlag(u'efixOverrides', 0x00000002) #OBME
    IsUsingParamFlagAOverride = CBashBasicFlag(u'efixOverrides', 0x00000004) #OBME
    IsUsingBeneficialOverride = CBashBasicFlag(u'efixOverrides', 0x00000008) #OBME
    IsUsingEFIXParamOverride = CBashBasicFlag(u'efixOverrides', 0x00000010) #OBME
    IsUsingSchoolOverride = CBashBasicFlag(u'efixOverrides', 0x00000020) #OBME
    IsUsingNameOverride = CBashBasicFlag(u'efixOverrides', 0x00000040) #OBME
    IsUsingVFXCodeOverride = CBashBasicFlag(u'efixOverrides', 0x00000080) #OBME
    IsUsingBaseCostOverride = CBashBasicFlag(u'efixOverrides', 0x00000100) #OBME
    IsUsingResistAVOverride = CBashBasicFlag(u'efixOverrides', 0x00000200) #OBME
    IsUsingFXPersistsOverride = CBashBasicFlag(u'efixOverrides', 0x00000400) #OBME
    IsUsingIconOverride = CBashBasicFlag(u'efixOverrides', 0x00000800) #OBME
    IsUsingDoesntTeachOverride = CBashBasicFlag(u'efixOverrides', 0x00001000) #OBME
    IsUsingUnknownFOverride = CBashBasicFlag(u'efixOverrides', 0x00004000) #OBME
    IsUsingNoRecastOverride = CBashBasicFlag(u'efixOverrides', 0x00008000) #OBME
    IsUsingParamFlagBOverride = CBashBasicFlag(u'efixOverrides', 0x00010000) #OBME
    IsUsingMagnitudeIsRangeOverride = CBashBasicFlag(u'efixOverrides', 0x00020000) #OBME
    IsUsingAtomicResistanceOverride = CBashBasicFlag(u'efixOverrides', 0x00040000) #OBME
    IsUsingParamFlagCOverride = CBashBasicFlag(u'efixOverrides', 0x00080000) #OBME
    IsUsingParamFlagDOverride = CBashBasicFlag(u'efixOverrides', 0x00100000) #OBME
    IsUsingDisabledOverride = CBashBasicFlag(u'efixOverrides', 0x00400000) #OBME
    IsUsingUnknownOOverride = CBashBasicFlag(u'efixOverrides', 0x00800000) #OBME
    IsUsingNoHitEffectOverride = CBashBasicFlag(u'efixOverrides', 0x08000000) #OBME
    IsUsingPersistOnDeathOverride = CBashBasicFlag(u'efixOverrides', 0x10000000) #OBME
    IsUsingExplodesWithForceOverride = CBashBasicFlag(u'efixOverrides', 0x20000000) #OBME
    IsUsingHiddenOverride = CBashBasicFlag(u'efixOverrides', 0x40000000) #OBME
    ##The related efixOverrides flag must be set for the following to be used
    IsHostileOverride = CBashBasicFlag(u'efixFlags', 0x00000001) #OBME
    IsRecoversOverride = CBashBasicFlag(u'efixFlags', 0x00000002) #OBME
    IsParamFlagAOverride = CBashBasicFlag(u'efixFlags', 0x00000004) #OBME
    IsBeneficialOverride = CBashBasicFlag(u'efixFlags', 0x00000008) #OBME
    IsFXPersistsOverride = CBashBasicFlag(u'efixFlags', 0x00000400) #OBME
    IsUnknownFOverride = CBashBasicFlag(u'efixFlags', 0x00004000) #OBME
    IsNoRecastOverride = CBashBasicFlag(u'efixFlags', 0x00008000) #OBME
    IsParamFlagBOverride = CBashBasicFlag(u'efixFlags', 0x00010000) #OBME
    IsMagnitudeIsRangeOverride = CBashBasicFlag(u'efixFlags', 0x00020000) #OBME
    IsAtomicResistanceOverride = CBashBasicFlag(u'efixFlags', 0x00040000) #OBME
    IsParamFlagCOverride = CBashBasicFlag(u'efixFlags', 0x00080000) #OBME
    IsParamFlagDOverride = CBashBasicFlag(u'efixFlags', 0x00100000) #OBME
    IsDisabledOverride = CBashBasicFlag(u'efixFlags', 0x00400000) #OBME
    IsUnknownOOverride = CBashBasicFlag(u'efixFlags', 0x00800000) #OBME
    IsNoHitEffectOverride = CBashBasicFlag(u'efixFlags', 0x08000000) #OBME
    IsPersistOnDeathOverride = CBashBasicFlag(u'efixFlags', 0x10000000) #OBME
    IsExplodesWithForceOverride = CBashBasicFlag(u'efixFlags', 0x20000000) #OBME
    IsHiddenOverride = CBashBasicFlag(u'efixFlags', 0x40000000) #OBME
    exportattrs = copyattrs = [u'name', u'magnitude', u'area', u'duration', u'rangeType',
                               u'actorValue', u'script', u'schoolType', u'visual', u'IsHostile',
                               u'full']
    copyattrsOBME = copyattrs + [u'recordVersion', u'betaVersion',
                                 u'minorVersion', u'majorVersion',
                                 u'efitParamInfo', u'efixParamInfo',
                                 u'reserved1', u'iconPath', u'efixOverrides',
                                 u'efixFlags', u'baseCost', u'resistAV',
                                 u'reserved2']
    exportattrsOBME = copyattrsOBME[:]
    exportattrsOBME.remove(u'reserved1')
    exportattrsOBME.remove(u'reserved2')

class FNVEffect(ListComponent):
    __slots__ = []
    effect = CBashFORMID_LIST(1)
    magnitude = CBashGeneric_LIST(2, c_ulong)
    area = CBashGeneric_LIST(3, c_ulong)
    duration = CBashGeneric_LIST(4, c_ulong)
    rangeType = CBashGeneric_LIST(5, c_ulong)
    actorValue = CBashGeneric_LIST(6, c_long)

    def create_condition(self):
        length = _CGetFieldAttribute(self._RecordID, self._FieldID, self._ListIndex, 7, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, self._FieldID, self._ListIndex, 7, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return FNVConditionX2(self._RecordID, self._FieldID, self._ListIndex, 7, length)
    conditions = CBashLIST_LIST(7, FNVConditionX2)
    conditions_list = CBashLIST_LIST(7, FNVConditionX2, True)


    IsSelf = CBashBasicType(u'rangeType', 0, u'IsTouch')
    IsTouch = CBashBasicType(u'rangeType', 1, u'IsSelf')
    IsTarget = CBashBasicType(u'rangeType', 2, u'IsSelf')
    exportattrs = copyattrs = [u'effect', u'magnitude', u'area', u'duration',
                               u'rangeType', u'actorValue', u'conditions_list']

class Faction(ListComponent):
    __slots__ = []
    faction = CBashFORMID_LIST(1)
    rank = CBashGeneric_LIST(2, c_ubyte)
    unused1 = CBashUINT8ARRAY_LIST(3, 3)
    exportattrs = copyattrs = [u'faction', u'rank']

class Relation(ListComponent):
    __slots__ = []
    faction = CBashFORMID_LIST(1)
    mod = CBashGeneric_LIST(2, c_long)
    exportattrs = copyattrs = [u'faction', u'mod']

class FNVRelation(ListComponent):
    __slots__ = []
    faction = CBashFORMID_LIST(1)
    mod = CBashGeneric_LIST(2, c_long)
    groupReactionType = CBashGeneric_LIST(3, c_ulong)

    IsNeutral = CBashBasicType(u'groupReactionType', 0, u'IsEnemy')
    IsEnemy = CBashBasicType(u'groupReactionType', 1, u'IsNeutral')
    IsAlly = CBashBasicType(u'groupReactionType', 2, u'IsNeutral')
    IsFriend = CBashBasicType(u'groupReactionType', 3, u'IsNeutral')
    exportattrs = copyattrs = [u'faction', u'mod', u'groupReactionType']

class FNVAltTexture(ListComponent):
    __slots__ = []
    name = CBashSTRING_LIST(1)
    texture = CBashFORMID_LIST(2)
    index = CBashGeneric_LIST(3, c_long)
    exportattrs = copyattrs = [u'name', u'texture', u'index']

class FNVDestructable(BaseComponent):
    __slots__ = []
    class Stage(ListComponent):
        __slots__ = []
        health = CBashGeneric_LIST(1, c_ubyte)
        index = CBashGeneric_LIST(2, c_ubyte)
        stage = CBashGeneric_LIST(3, c_ubyte)
        flags = CBashGeneric_LIST(4, c_ubyte)
        dps = CBashGeneric_LIST(5, c_long)
        explosion = CBashFORMID_LIST(6)
        debris = CBashFORMID_LIST(7)
        debrisCount = CBashGeneric_LIST(8, c_long)
        modPath = CBashISTRING_LIST(9)
        modt_p = CBashUINT8ARRAY_LIST(10)

        IsCapDamage = CBashBasicFlag(u'flags', 0x01)
        IsDisable = CBashBasicFlag(u'flags', 0x02)
        IsDestroy = CBashBasicFlag(u'flags', 0x04)
        copyattrs = [u'health', u'index', u'stage',
                     u'flags', u'dps', u'explosion',
                     u'debris', u'debrisCount',
                     u'modPath', u'modt_p']
        exportattrs = copyattrs[:]
        exportattrs.remove(u'modt_p')

    health = CBashGeneric_GROUP(0, c_long)
    count = CBashGeneric_GROUP(1, c_ubyte)
    flags = CBashGeneric_GROUP(2, c_ubyte)
    unused1 = CBashUINT8ARRAY_GROUP(3, 2)

    def create_stage(self):
        FieldID = self._FieldID + 4
        length = _CGetFieldAttribute(self._RecordID, FieldID, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, FieldID, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return self.Stage(self._RecordID, FieldID, length)
    stages = CBashLIST_GROUP(4, Stage)
    stages_list = CBashLIST_GROUP(4, Stage, True)
    IsVATSTargetable = CBashBasicFlag(u'flags', 0x01)
    exportattrs = copyattrs = [u'health', u'count', u'flags', u'stages_list']

class WorldModel(BaseComponent):
    __slots__ = []
    modPath = CBashISTRING_GROUP(0)
    modt_p = CBashUINT8ARRAY_GROUP(1)

    def create_altTexture(self):
        FieldID = self._FieldID + 2
        length = _CGetFieldAttribute(self._RecordID, FieldID, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, FieldID, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return FNVAltTexture(self._RecordID, FieldID, length)
    altTextures = CBashLIST_GROUP(2, FNVAltTexture)
    altTextures_list = CBashLIST_GROUP(2, FNVAltTexture, True)
    copyattrs = [u'modPath', u'modt_p', u'altTextures_list']
    exportattrs = copyattrs[:]
    exportattrs.remove(u'modt_p')

class PGRP(ListComponent):
    __slots__ = []
    x = CBashFLOAT32_LIST(1)
    y = CBashFLOAT32_LIST(2)
    z = CBashFLOAT32_LIST(3)
    connections = CBashGeneric_LIST(4, c_ubyte)
    unused1 = CBashUINT8ARRAY_LIST(5, 3)
    exportattrs = copyattrs = [u'x', u'y', u'z', u'connections']

#--Accessors
#--Fallout New Vegas
class FnvBaseRecord(object):
    __slots__ = [u'_RecordID']
    _Type = b'BASE'
    def __init__(self, RecordID):
        self._RecordID = RecordID

    def __eq__(self, other):
        return self._RecordID == other._RecordID if type(other) is type(self) else False

    def __ne__(self, other):
        return not self.__eq__(other)

    def GetParentMod(self):
        return FnvModFile(_CGetModIDByRecordID(self._RecordID))

    def GetParentCollection(self):
        return ObCollection(_CGetCollectionIDByRecordID(self._RecordID))

    def ResetRecord(self):
        _CResetRecord(self._RecordID)

    def UnloadRecord(self):
        _CUnloadRecord(self._RecordID)

    def DeleteRecord(self):
        _CDeleteRecord(self._RecordID)

    def GetRecordUpdatedReferences(self):
        return _CGetRecordUpdatedReferences(0, self._RecordID)

    def UpdateReferences(self, Old_NewFormIDs):
        Old_NewFormIDs = FormID.FilterValidDict(Old_NewFormIDs, self, True, True, AsShort=True)
        length = len(Old_NewFormIDs)
        if not length: return []
        OldFormIDs = (c_ulong * length)(*Old_NewFormIDs.keys())
        NewFormIDs = (c_ulong * length)(*Old_NewFormIDs.values())
        Changes = (c_ulong * length)()
        _CUpdateReferences(0, self._RecordID, OldFormIDs, NewFormIDs, byref(Changes), length)
        return [x for x in Changes]

    def History(self):
        cRecordIDs = (c_record_p * 257)() #just allocate enough for the max number + size
        numRecords = _CGetRecordHistory(self._RecordID, byref(cRecordIDs))
        return [self.__class__(cRecordIDs[x]) for x in xrange(numRecords)]

    def IsWinning(self, GetExtendedConflicts=False):
        """Returns true if the record is the last to load.
           If GetExtendedConflicts is True, scanned records will be considered.
           More efficient than running Conflicts() and checking the first value."""
        return _CIsRecordWinning(self._RecordID, c_ulong(GetExtendedConflicts)) > 0

    def HasInvalidFormIDs(self):
        return _CIsRecordFormIDsInvalid(self._RecordID) > 0

    def Conflicts(self, GetExtendedConflicts=False):
        numRecords = _CGetNumRecordConflicts(self._RecordID, c_ulong(GetExtendedConflicts)) #gives upper bound
        if(numRecords > 1):
            cRecordIDs = (c_record_p * numRecords)()
            numRecords = _CGetRecordConflicts(self._RecordID, byref(cRecordIDs), c_ulong(GetExtendedConflicts))
            return [self.__class__(cRecordIDs[x]) for x in xrange(numRecords)]
        return []

    def ConflictDetails(self, attrs=None):
        """New: attrs is an iterable, for each item, the following is checked:
           if the item is a string type: changes are reported
           if the item is another iterable (set,list,tuple), then if any of the subitems is
             different, then all sub items are reported.  This allows grouping of dependant
             items."""
        conflicting = {}
        if attrs is None: attrs = self.copyattrs
        if not attrs: return conflicting

        parentRecords = self.History()
        if parentRecords:
            for attr in attrs:
                if isinstance(attr,basestring):
                    # Single attr
                    conflicting.update([(attr,reduce(getattr, attr.split(u'.'), self)) for parentRecord in parentRecords if reduce(getattr, attr.split(u'.'), self) != reduce(getattr, attr.split(u'.'), parentRecord)])
                elif isinstance(attr,(list,tuple,set)):
                    # Group of attrs that need to stay together
                    for parentRecord in parentRecords:
                        subconflicting = {}
                        conflict = False
                        for subattr in attr:
                            self_value = reduce(getattr, subattr.split(u'.'), self)
                            if not conflict and self_value != reduce(getattr, subattr.split(u'.'), parentRecord):
                                conflict = True
                            subconflicting.update([(subattr,self_value)])
                        if conflict: conflicting.update(subconflicting)
        else: #is the first instance of the record
            for attr in attrs:
                if isinstance(attr, basestring):
                    conflicting.update([(attr,reduce(getattr, attr.split(u'.'), self))])
                elif isinstance(attr,(list,tuple,set)):
                    conflicting.update([(subattr,reduce(getattr, subattr.split(u'.'), self)) for subattr in attr])

        skipped_conflicting = [(attr, value) for attr, value in conflicting.iteritems() if isinstance(value, FormID) and not value.ValidateFormID(self)]
        for attr, value in skipped_conflicting:
            try:
                deprint(_(u'%s attribute of %s record (maybe named: %s) importing from %s referenced an unloaded object (probably %s) - value skipped') % (attr, self.fid, self.full, self.GetParentMod().GName, value))
            except: #a record type that doesn't have a full chunk:
                deprint(_(u'%s attribute of %s record importing from %s referenced an unloaded object (probably %s) - value skipped') % (attr, self.fid, self.GetParentMod().GName, value))
            del conflicting[attr]

        return conflicting

    def mergeFilter(self, target):
        """This method is called by the bashed patch mod merger. The intention is
        to allow a record to be filtered according to the specified modSet. E.g.
        for a list record, items coming from mods not in the modSet could be
        removed from the list."""
        pass

    def CopyAsOverride(self, target, UseWinningParents=False):
        ##Record Creation Flags
        ##SetAsOverride       = 0x00000001
        ##CopyWinningParent   = 0x00000002
        DestParentID, DestModID = (0, target._ModID) if not hasattr(self, u'_ParentID') else (self._ParentID, target._ModID) if isinstance(target, FnvModFile) else (target._RecordID, target.GetParentMod()._ModID)
        RecordID = _CCopyRecord(self._RecordID, DestModID, DestParentID, 0, 0, c_ulong(0x00000003 if UseWinningParents else 0x00000001))
        return self.__class__(RecordID) if RecordID else None

    def CopyAsNew(self, target, UseWinningParents=False, RecordFormID=0):
        ##Record Creation Flags
        ##SetAsOverride       = 0x00000001
        ##CopyWinningParent   = 0x00000002
        DestParentID, DestModID = (0, target._ModID) if not hasattr(self, u'_ParentID') else (self._ParentID, target._ModID) if isinstance(target, FnvModFile) else (target._RecordID, target.GetParentMod()._ModID)
        RecordID = _CCopyRecord(self._RecordID, DestModID, DestParentID, RecordFormID.GetShortFormID(target) if RecordFormID else 0, 0, c_ulong(0x00000002 if UseWinningParents else 0))
        return self.__class__(RecordID) if RecordID else None

    @property
    def Parent(self):
        RecordID = getattr(self, u'_ParentID', None)
        if RecordID:
            _CGetFieldAttribute.restype = (c_char * 4)
            retValue = _CGetFieldAttribute(RecordID, 0, 0, 0, 0, 0, 0, 0, 0)
            _CGetFieldAttribute.restype = c_ulong
            return fnv_type_record[retValue.value](RecordID)
        return None

    @property
    def recType(self):
        _CGetFieldAttribute.restype = (c_char * 4)
        retValue = _CGetFieldAttribute(self._RecordID, 0, 0, 0, 0, 0, 0, 0, 0).value
        _CGetFieldAttribute.restype = c_ulong
        return retValue

    flags1 = CBashGeneric(1, c_ulong)

    def get_fid(self):
        _CGetField.restype = POINTER(c_ulong)
        retValue = _CGetField(self._RecordID, 2, 0, 0, 0, 0, 0, 0, 0)
        return FormID(self._RecordID, retValue.contents.value) if retValue else FormID(None,None)
    def set_fid(self, nValue):
        _CSetIDFields(self._RecordID, 0 if nValue is None else nValue.GetShortFormID(self), self.eid or 0)
    fid = property(get_fid, set_fid)

    versionControl1 = CBashUINT8ARRAY(3, 4)
    formVersion = CBashGeneric(5, c_ushort)
    versionControl2 = CBashUINT8ARRAY(6, 2)

    def get_eid(self):
        _CGetField.restype = c_char_p
        retValue = _CGetField(self._RecordID, 4, 0, 0, 0, 0, 0, 0, 0)
        return IUNICODE(_unicode(retValue)) if retValue else None
    def set_eid(self, nValue):
        nValue = 0 if nValue is None or not len(nValue) else _encode(nValue)
        _CGetField.restype = POINTER(c_ulong)
        _CSetIDFields(self._RecordID, _CGetField(self._RecordID, 2, 0, 0, 0, 0, 0, 0, 0).contents.value, nValue)
    eid = property(get_eid, set_eid)

    IsDeleted = CBashBasicFlag(u'flags1', 0x00000020)
    IsHasTreeLOD = CBashBasicFlag(u'flags1', 0x00000040)
    IsConstant = CBashAlias(u'IsHasTreeLOD')
    IsHiddenFromLocalMap = CBashAlias(u'IsHasTreeLOD')
    IsTurnOffFire = CBashBasicFlag(u'flags1', 0x00000080)
    IsInaccessible = CBashBasicFlag(u'flags1', 0x00000100)
    IsOnLocalMap = CBashBasicFlag(u'flags1', 0x00000200)
    IsMotionBlur = CBashAlias(u'IsOnLocalMap')
    IsPersistent = CBashBasicFlag(u'flags1', 0x00000400)
    IsQuest = CBashAlias(u'IsPersistent')
    IsQuestOrPersistent = CBashAlias(u'IsPersistent')
    IsInitiallyDisabled = CBashBasicFlag(u'flags1', 0x00000800)
    IsIgnored = CBashBasicFlag(u'flags1', 0x00001000)
    IsNoVoiceFilter = CBashBasicFlag(u'flags1', 0x00002000)
    IsVoiceFilter = CBashInvertedFlag(u'IsNoVoiceFilter')
    IsVisibleWhenDistant = CBashBasicFlag(u'flags1', 0x00008000)
    IsVWD = CBashAlias(u'IsVisibleWhenDistant')
    IsRandomAnimStartOrHighPriorityLOD = CBashBasicFlag(u'flags1', 0x00010000)
    IsRandomAnimStart = CBashAlias(u'IsRandomAnimStartOrHighPriorityLOD')
    IsHighPriorityLOD = CBashAlias(u'IsRandomAnimStartOrHighPriorityLOD')
    IsTalkingActivator = CBashBasicFlag(u'flags1', 0x00020000)
    IsCompressed = CBashBasicFlag(u'flags1', 0x00040000)
    IsPlatformSpecificTexture = CBashBasicFlag(u'flags1', 0x00080000)
    IsObstacleOrNoAIAcquire = CBashBasicFlag(u'flags1', 0x02000000)
    IsObstacle = CBashAlias(u'IsObstacleOrNoAIAcquire')
    IsNoAIAcquire = CBashAlias(u'IsObstacleOrNoAIAcquire')
    IsNavMeshFilter = CBashBasicFlag(u'flags1', 0x04000000)
    IsNavMeshBoundBox = CBashBasicFlag(u'flags1', 0x08000000)
    IsNonPipboyOrAutoReflected = CBashBasicFlag(u'flags1', 0x10000000)
    IsNonPipboy = CBashAlias(u'IsNonPipboyOrAutoReflected')
    IsAutoReflected = CBashAlias(u'IsNonPipboyOrAutoReflected')
    IsPipboy = CBashInvertedFlag(u'IsNonPipboyOrAutoReflected')
    IsChildUsableOrAutoRefracted = CBashBasicFlag(u'flags1', 0x20000000)
    IsChildUsable = CBashAlias(u'IsChildUsableOrAutoRefracted')
    IsAutoRefracted = CBashAlias(u'IsChildUsableOrAutoRefracted')
    IsNavMeshGround = CBashBasicFlag(u'flags1', 0x40000000)
    baseattrs = [u'flags1', u'versionControl1', u'formVersion',
                 u'versionControl2', u'eid']

class FnvTES4Record(object):
    __slots__ = [u'_RecordID']
    _Type = b'TES4'
    def __init__(self, RecordID):
        self._RecordID = RecordID

    def GetParentMod(self):
        return FnvModFile(_CGetModIDByRecordID(self._RecordID))

    def GetParentCollection(self):
        return ObCollection(_CGetCollectionIDByRecordID(self._RecordID))

    def ResetRecord(self):
        pass

    def UnloadRecord(self):
        pass

    @property
    def recType(self):
        return self._Type

    flags1 = CBashGeneric(1, c_ulong)
    versionControl1 = CBashUINT8ARRAY(3, 4)
    formVersion = CBashGeneric(14, c_ushort)
    versionControl2 = CBashUINT8ARRAY(15, 2)
    version = CBashFLOAT32(5)
    numRecords = CBashGeneric(6, c_ulong)
    nextObject = CBashGeneric(7, c_ulong)
    ofst_p = CBashUINT8ARRAY(8)
    dele_p = CBashUINT8ARRAY(9)
    author = CBashUNICODE(10)
    description = CBashUNICODE(11)
    masters = CBashIUNICODEARRAY(12)
    DATA = CBashJunk(13)
    overrides = CBashFORMIDARRAY(16)
    screenshot_p = CBashUINT8ARRAY(17)

    IsESM = CBashBasicFlag(u'flags1', 0x00000001)
    exportattrs = copyattrs = [u'flags1', u'versionControl1', u'formVersion',
                               u'versionControl2', u'version', u'numRecords',
                               u'nextObject', u'author', u'description',
                               u'masters', u'overrides', u'screenshot_p']

class FnvACHRRecord(FnvBaseRecord):
    __slots__ = []
    @property
    def _ParentID(self):
        _CGetField.restype = c_record_p
        return _CGetField(self._RecordID, 55, 0, 0, 0, 0, 0, 0, 0)

    _Type = b'ACHR'
    class Decal(ListComponent):
        __slots__ = []
        reference = CBashFORMID_LIST(1)
        unknown1 = CBashUINT8ARRAY_LIST(2, 24)
        copyattrs = [u'reference', u'unknown1']
        exportattrs = copyattrs[:]
        exportattrs.remove(u'unknown1')

    class ParentRef(ListComponent):
        __slots__ = []
        reference = CBashFORMID_LIST(1)
        delay = CBashFLOAT32_LIST(2)
        exportattrs = copyattrs = [u'reference', u'delay']

    base = CBashFORMID(7)
    encounterZone = CBashFORMID(8)
    xrgd_p = CBashUINT8ARRAY(9)
    xrgb_p = CBashUINT8ARRAY(10)
    idleTime = CBashFLOAT32(11)
    idle = CBashFORMID(12)
    unused1 = CBashUINT8ARRAY(13, 4)
    numRefs = CBashGeneric(14, c_ulong)
    compiledSize = CBashGeneric(15, c_ulong)
    lastIndex = CBashGeneric(16, c_ulong)
    scriptType = CBashGeneric(17, c_ushort)
    scriptFlags = CBashGeneric(18, c_ushort)
    compiled_p = CBashUINT8ARRAY(19)
    scriptText = CBashISTRING(20)

    def create_var(self):
        length = _CGetFieldAttribute(self._RecordID, 21, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 21, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return Var(self._RecordID, 21, length)
    vars = CBashLIST(21, Var)
    vars_list = CBashLIST(21, Var, True)

    references = CBashFORMID_OR_UINT32_ARRAY(22)
    topic = CBashFORMID(23)
    levelMod = CBashGeneric(24, c_long)
    merchantContainer = CBashFORMID(25)
    count = CBashGeneric(26, c_long)
    radius = CBashFLOAT32(27)
    health = CBashFLOAT32(28)

    def create_decal(self):
        length = _CGetFieldAttribute(self._RecordID, 29, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 29, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return self.Decal(self._RecordID, 29, length)
    decals = CBashLIST(29, Decal)
    decals_list = CBashLIST(29, Decal, True)

    linkedReference = CBashFORMID(30)
    startRed = CBashGeneric(31, c_ubyte)
    startGreen = CBashGeneric(32, c_ubyte)
    startBlue = CBashGeneric(33, c_ubyte)
    unused2 = CBashUINT8ARRAY(34, 1)
    endRed = CBashGeneric(35, c_ubyte)
    endGreen = CBashGeneric(36, c_ubyte)
    endBlue = CBashGeneric(37, c_ubyte)
    unused3 = CBashUINT8ARRAY(38, 1)
    activateParentFlags = CBashGeneric(39, c_ubyte)

    def create_activateParentRef(self):
        length = _CGetFieldAttribute(self._RecordID, 40, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 40, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return self.ParentRef(self._RecordID, 40, length)
    activateParentRefs = CBashLIST(40, ParentRef)
    activateParentRefs_list = CBashLIST(40, ParentRef, True)

    prompt = CBashSTRING(41)
    parent = CBashFORMID(42)
    parentFlags = CBashGeneric(43, c_ubyte)
    unused4 = CBashUINT8ARRAY(44, 3)
    emittance = CBashFORMID(45)
    boundRef = CBashFORMID(46)
    ignoredBySandbox = CBashGeneric(47, c_bool)
    scale = CBashFLOAT32(48)
    posX = CBashFLOAT32(49)
    posY = CBashFLOAT32(50)
    posZ = CBashFLOAT32(51)
    rotX = CBashFLOAT32(52)
    rotX_degrees = CBashDEGREES(52)
    rotY = CBashFLOAT32(53)
    rotY_degrees = CBashDEGREES(53)
    rotZ = CBashFLOAT32(54)
    rotZ_degrees = CBashDEGREES(54)

    IsEnabled = CBashBasicFlag(u'scriptFlags', 0x0001)

    IsOppositeParent = CBashBasicFlag(u'parentFlags', 0x00000001)
    IsPopIn = CBashBasicFlag(u'parentFlags', 0x00000002)

    IsObject = CBashBasicType(u'scriptType', 0x0000, u'IsQuest')
    IsQuest = CBashBasicType(u'scriptType', 0x0001, u'IsObject')
    IsEffect = CBashBasicType(u'scriptType', 0x0100, u'IsObject')

    copyattrs = FnvBaseRecord.baseattrs + [
        u'base', u'encounterZone', u'xrgd_p', u'xrgb_p', u'idleTime', u'idle',
        u'numRefs', u'compiledSize', u'lastIndex', u'scriptType',
        u'scriptFlags', u'compiled_p', u'scriptText', u'vars_list',
        u'references', u'topic', u'levelMod', u'merchantContainer', u'count',
        u'radius', u'health', u'decals_list', u'linkedReference', u'startRed',
        u'startGreen', u'startBlue', u'endRed', u'endGreen', u'endBlue',
        u'activateParentFlags', u'activateParentRefs_list', u'prompt',
        u'parent', u'parentFlags', u'emittance', u'boundRef',
        u'ignoredBySandbox', u'scale', u'posX', u'posY', u'posZ', u'rotX',
        u'rotY', u'rotZ']
    exportattrs = copyattrs[:]
    exportattrs.remove(u'xrgd_p')
    exportattrs.remove(u'xrgb_p')
    exportattrs.remove(u'compiled_p')

class FnvACRERecord(FnvBaseRecord):
    __slots__ = []
    @property
    def _ParentID(self):
        _CGetField.restype = c_record_p
        return _CGetField(self._RecordID, 57, 0, 0, 0, 0, 0, 0, 0)

    _Type = b'ACRE'
    class Decal(ListComponent):
        __slots__ = []
        reference = CBashFORMID_LIST(1)
        unknown1 = CBashUINT8ARRAY_LIST(2, 24)
        copyattrs = [u'reference', u'unknown1']
        exportattrs = copyattrs[:]
        exportattrs.remove(u'unknown1')

    class ParentRef(ListComponent):
        __slots__ = []
        reference = CBashFORMID_LIST(1)
        delay = CBashFLOAT32_LIST(2)
        exportattrs = copyattrs = [u'reference', u'delay']

    base = CBashFORMID(7)
    encounterZone = CBashFORMID(8)
    xrgd_p = CBashUINT8ARRAY(9)
    xrgb_p = CBashUINT8ARRAY(10)
    idleTime = CBashFLOAT32(11)
    idle = CBashFORMID(12)
    unused1 = CBashUINT8ARRAY(13, 4)
    numRefs = CBashGeneric(14, c_ulong)
    compiledSize = CBashGeneric(15, c_ulong)
    lastIndex = CBashGeneric(16, c_ulong)
    scriptType = CBashGeneric(17, c_ushort)
    scriptFlags = CBashGeneric(18, c_ushort)
    compiled_p = CBashUINT8ARRAY(19)
    scriptText = CBashISTRING(20)

    def create_var(self):
        length = _CGetFieldAttribute(self._RecordID, 21, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 21, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return Var(self._RecordID, 21, length)
    vars = CBashLIST(21, Var)
    vars_list = CBashLIST(21, Var, True)

    references = CBashFORMID_OR_UINT32_ARRAY(22)
    topic = CBashFORMID(23)
    levelMod = CBashGeneric(24, c_long)
    owner = CBashFORMID(25)
    rank = CBashGeneric(26, c_long)
    merchantContainer = CBashFORMID(27)
    count = CBashGeneric(28, c_long)
    radius = CBashFLOAT32(29)
    health = CBashFLOAT32(30)

    def create_decal(self):
        length = _CGetFieldAttribute(self._RecordID, 31, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 31, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return self.Decal(self._RecordID, 31, length)
    decals = CBashLIST(31, Decal)
    decals_list = CBashLIST(31, Decal, True)

    linkedReference = CBashFORMID(32)
    startRed = CBashGeneric(33, c_ubyte)
    startGreen = CBashGeneric(34, c_ubyte)
    startBlue = CBashGeneric(35, c_ubyte)
    unused2 = CBashUINT8ARRAY(36, 1)
    endRed = CBashGeneric(37, c_ubyte)
    endGreen = CBashGeneric(38, c_ubyte)
    endBlue = CBashGeneric(39, c_ubyte)
    unused3 = CBashUINT8ARRAY(40, 1)
    activateParentFlags = CBashGeneric(41, c_ubyte)

    def create_activateParentRef(self):
        length = _CGetFieldAttribute(self._RecordID, 42, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 42, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return self.ParentRef(self._RecordID, 42, length)
    activateParentRefs = CBashLIST(42, ParentRef)
    activateParentRefs_list = CBashLIST(42, ParentRef, True)

    prompt = CBashSTRING(43)
    parent = CBashFORMID(44)
    parentFlags = CBashGeneric(45, c_ubyte)
    unused4 = CBashUINT8ARRAY(46, 3)
    emittance = CBashFORMID(47)
    boundRef = CBashFORMID(48)
    ignoredBySandbox = CBashGeneric(49, c_bool)
    scale = CBashFLOAT32(50)
    posX = CBashFLOAT32(51)
    posY = CBashFLOAT32(52)
    posZ = CBashFLOAT32(53)
    rotX = CBashFLOAT32(54)
    rotX_degrees = CBashDEGREES(54)
    rotY = CBashFLOAT32(55)
    rotY_degrees = CBashDEGREES(55)
    rotZ = CBashFLOAT32(56)
    rotZ_degrees = CBashDEGREES(56)

    IsEnabled = CBashBasicFlag(u'scriptFlags', 0x0001)

    IsOppositeParent = CBashBasicFlag(u'parentFlags', 0x00000001)
    IsPopIn = CBashBasicFlag(u'parentFlags', 0x00000002)

    IsObject = CBashBasicType(u'scriptType', 0x0000, u'IsQuest')
    IsQuest = CBashBasicType(u'scriptType', 0x0001, u'IsObject')
    IsEffect = CBashBasicType(u'scriptType', 0x0100, u'IsObject')

    copyattrs = FnvBaseRecord.baseattrs + [
        u'base', u'encounterZone', u'xrgd_p', u'xrgb_p', u'idleTime', u'idle',
        u'numRefs', u'compiledSize', u'lastIndex', u'scriptType',
        u'scriptFlags', u'compiled_p', u'scriptText', u'vars_list',
        u'references', u'topic', u'levelMod', u'owner', u'rank',
        u'merchantContainer', u'count', u'radius', u'health', u'decals_list',
        u'linkedReference', u'startRed', u'startGreen', u'startBlue',
        u'endRed', u'endGreen', u'endBlue', u'activateParentFlags',
        u'activateParentRefs_list', u'prompt', u'parent', u'parentFlags',
        u'emittance', u'boundRef', u'ignoredBySandbox', u'scale', u'posX',
        u'posY', u'posZ', u'rotX', u'rotY', u'rotZ']
    exportattrs = copyattrs[:]
    exportattrs.remove(u'xrgd_p')
    exportattrs.remove(u'xrgb_p')
    exportattrs.remove(u'compiled_p')

class FnvREFRRecord(FnvBaseRecord):
    __slots__ = []
    @property
    def _ParentID(self):
        _CGetField.restype = c_record_p
        return _CGetField(self._RecordID, 141, 0, 0, 0, 0, 0, 0, 0)

    _Type = b'REFR'
    class Decal(ListComponent):
        __slots__ = []
        reference = CBashFORMID_LIST(1)
        unknown1 = CBashUINT8ARRAY_LIST(2, 24)
        copyattrs = [u'reference', u'unknown1']
        exportattrs = copyattrs[:]
        exportattrs.remove(u'unknown1')

    class ParentRef(ListComponent):
        __slots__ = []
        reference = CBashFORMID_LIST(1)
        delay = CBashFLOAT32_LIST(2)
        exportattrs = copyattrs = [u'reference', u'delay']

    class ReflRefr(ListComponent):
        __slots__ = []
        reference = CBashFORMID_LIST(1)
        type = CBashGeneric_LIST(2, c_ulong)

        IsReflection = CBashBasicType(u'type', 0, u'IsRefraction')
        IsRefraction = CBashBasicType(u'type', 1, u'IsReflection')
        exportattrs = copyattrs = [u'reference', u'type']

    base = CBashFORMID(7)
    encounterZone = CBashFORMID(8)
    xrgd_p = CBashUINT8ARRAY(9)
    xrgb_p = CBashUINT8ARRAY(10)
    idleTime = CBashFLOAT32(11)
    idle = CBashFORMID(12)
    unused1 = CBashUINT8ARRAY(13, 4)
    numRefs = CBashGeneric(14, c_ulong)
    compiledSize = CBashGeneric(15, c_ulong)
    lastIndex = CBashGeneric(16, c_ulong)
    scriptType = CBashGeneric(17, c_ushort)
    scriptFlags = CBashGeneric(18, c_ushort)
    compiled_p = CBashUINT8ARRAY(19)
    scriptText = CBashISTRING(20)

    def create_var(self):
        length = _CGetFieldAttribute(self._RecordID, 21, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 21, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return Var(self._RecordID, 21, length)
    vars = CBashLIST(21, Var)
    vars_list = CBashLIST(21, Var, True)

    references = CBashFORMID_OR_UINT32_ARRAY(22)
    topic = CBashFORMID(23)
    levelMod = CBashGeneric(24, c_long)
    owner = CBashFORMID(25)
    rank = CBashGeneric(26, c_long)
    count = CBashGeneric(27, c_long)
    radius = CBashFLOAT32(28)
    health = CBashFLOAT32(29)
    radiation = CBashFLOAT32(30)
    charge = CBashFLOAT32(31)

    def create_decal(self):
        length = _CGetFieldAttribute(self._RecordID, 32, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 32, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return self.Decal(self._RecordID, 32, length)
    decals = CBashLIST(32, Decal)
    decals_list = CBashLIST(32, Decal, True)

    linkedReference = CBashFORMID(33)
    startRed = CBashGeneric(34, c_ubyte)
    startRed = CBashGeneric(35, c_ubyte)
    startBlue = CBashGeneric(36, c_ubyte)
    unused2 = CBashUINT8ARRAY(37, 1)
    endRed = CBashGeneric(38, c_ubyte)
    endGreen = CBashGeneric(39, c_ubyte)
    endBlue = CBashGeneric(40, c_ubyte)
    unused3 = CBashUINT8ARRAY(41, 1)
    rclr_p = CBashUINT8ARRAY(42)
    activateParentFlags = CBashGeneric(43, c_ubyte)

    def create_activateParentRef(self):
        length = _CGetFieldAttribute(self._RecordID, 44, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 44, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return self.ParentRef(self._RecordID, 44, length)
    activateParentRefs = CBashLIST(44, ParentRef)
    activateParentRefs_list = CBashLIST(44, ParentRef, True)

    prompt = CBashSTRING(45)
    parent = CBashFORMID(46)
    parentFlags = CBashGeneric(47, c_ubyte)
    unused4 = CBashUINT8ARRAY(48, 3)
    emittance = CBashFORMID(49)
    boundRef = CBashFORMID(50)
    primitiveX = CBashFLOAT32(51)
    primitiveY = CBashFLOAT32(52)
    primitiveZ = CBashFLOAT32(53)
    primitiveRed = CBashFLOAT32(54)
    primitiveGreen = CBashFLOAT32(55)
    primitiveBlue = CBashFLOAT32(56)
    primitiveUnknown = CBashFLOAT32(57)
    primitiveType = CBashGeneric(58, c_ulong)
    collisionType = CBashGeneric(59, c_ulong)
    extentX = CBashFLOAT32(60)
    extentY = CBashFLOAT32(61)
    extentZ = CBashFLOAT32(62)
    destinationFid = CBashFORMID(63)
    destinationPosX = CBashFLOAT32(64)
    destinationPosY = CBashFLOAT32(65)
    destinationPosZ = CBashFLOAT32(66)
    destinationRotX = CBashFLOAT32(67)
    destinationRotX_degrees = CBashDEGREES(67)
    destinationRotY = CBashFLOAT32(68)
    destinationRotY_degrees = CBashDEGREES(68)
    destinationRotZ = CBashFLOAT32(69)
    destinationRotZ_degrees = CBashDEGREES(69)
    destinationFlags = CBashGeneric(70, c_ulong)
    markerFlags = CBashGeneric(71, c_ubyte)
    markerFull = CBashSTRING(72)
    markerType = CBashGeneric(73, c_ubyte)
    unused5 = CBashUINT8ARRAY(74, 1)
    markerReputation = CBashFORMID(75)
    audioFull_p = CBashUINT8ARRAY(76)
    audioLocation = CBashFORMID(77)
    audioBnam_p = CBashUINT8ARRAY(78)
    audioUnknown1 = CBashFLOAT32(79)
    audioUnknown2 = CBashFLOAT32(80)
    xsrf_p = CBashUINT8ARRAY(81)
    xsrd_p = CBashUINT8ARRAY(82)
    target = CBashFORMID(83)
    rangeRadius = CBashFLOAT32(84)
    rangeType = CBashGeneric(85, c_ulong)
    staticPercentage = CBashFLOAT32(86)
    positionReference = CBashFORMID(87)
    lockLevel = CBashGeneric(88, c_ubyte)
    unused6 = CBashUINT8ARRAY(89, 3)
    lockKey = CBashFORMID(90)
    lockFlags = CBashGeneric(91, c_ubyte)
    unused7 = CBashUINT8ARRAY(92, 3)
    lockUnknown1 = CBashUINT8ARRAY(93)
    ammo = CBashFORMID(94)
    ammoCount = CBashGeneric(95, c_long)

    def create_reflrefr(self):
        length = _CGetFieldAttribute(self._RecordID, 96, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 96, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return self.ReflRefr(self._RecordID, 96, length)
    reflrefrs = CBashLIST(96, ReflRefr)
    reflrefrs_list = CBashLIST(96, ReflRefr, True)

    litWaters = CBashFORMIDARRAY(97)
    actionFlags = CBashGeneric(98, c_ulong)
    navMesh = CBashFORMID(99)
    navUnknown1 = CBashGeneric(100, c_ushort)
    unused8 = CBashUINT8ARRAY(101, 2)
    portalLinkedRoom1 = CBashFORMID(102)
    portalLinkedRoom2 = CBashFORMID(103)
    portalWidth = CBashFLOAT32(104)
    portalHeight = CBashFLOAT32(105)
    portalPosX = CBashFLOAT32(106)
    portalPosY = CBashFLOAT32(107)
    portalPosZ = CBashFLOAT32(108)
    portalQ1 = CBashFLOAT32(109)
    portalQ2 = CBashFLOAT32(110)
    portalQ3 = CBashFLOAT32(111)
    portalQ4 = CBashFLOAT32(112)
    seed = CBashGeneric(113, c_ubyte)
    roomCount = CBashGeneric(114, c_ushort)
    roomUnknown1 = CBashUINT8ARRAY(115)
    rooms = CBashFORMIDARRAY(116)
    occPlaneWidth = CBashFLOAT32(117)
    occPlaneHeight = CBashFLOAT32(118)
    occPlanePosX = CBashFLOAT32(119)
    occPlanePosY = CBashFLOAT32(120)
    occPlanePosZ = CBashFLOAT32(121)
    occPlaneQ1 = CBashFLOAT32(122)
    occPlaneQ2 = CBashFLOAT32(123)
    occPlaneQ3 = CBashFLOAT32(124)
    occPlaneQ4 = CBashFLOAT32(125)
    occPlaneRight = CBashFORMID(126)
    occPlaneLeft = CBashFORMID(127)
    occPlaneBottom = CBashFORMID(128)
    occPlaneTop = CBashFORMID(129)
    lod1 = CBashFLOAT32(130)
    lod2 = CBashFLOAT32(131)
    lod3 = CBashFLOAT32(132)
    ignoredBySandbox = CBashGeneric(133, c_bool)
    scale = CBashFLOAT32(134)
    posX = CBashFLOAT32(135)
    posY = CBashFLOAT32(136)
    posZ = CBashFLOAT32(137)
    rotX = CBashFLOAT32(138)
    rotX_degrees = CBashDEGREES(138)
    rotY = CBashFLOAT32(139)
    rotY_degrees = CBashDEGREES(139)
    rotZ = CBashFLOAT32(140)
    rotZ_degrees = CBashDEGREES(140)

    IsEnabled = CBashBasicFlag(u'scriptFlags', 0x0001)

    IsNoAlarm = CBashBasicFlag(u'destinationFlags', 0x00000001)

    IsVisible = CBashBasicFlag(u'markerFlags', 0x00000001)
    IsCanTravelTo = CBashBasicFlag(u'markerFlags', 0x00000002)

    IsUseDefault = CBashBasicFlag(u'actionFlags', 0x00000001)
    IsActivate = CBashBasicFlag(u'actionFlags', 0x00000002)
    IsOpen = CBashBasicFlag(u'actionFlags', 0x00000004)
    IsOpenByDefault = CBashBasicFlag(u'actionFlags', 0x00000008)

    IsOppositeParent = CBashBasicFlag(u'parentFlags', 0x00000001)
    IsPopIn = CBashBasicFlag(u'parentFlags', 0x00000002)

    IsLeveledLock = CBashBasicFlag(u'lockFlags', 0x00000004)

    IsObject = CBashBasicType(u'scriptType', 0x0000, u'IsQuest')
    IsQuest = CBashBasicType(u'scriptType', 0x0001, u'IsObject')
    IsEffect = CBashBasicType(u'scriptType', 0x0100, u'IsObject')

    IsNone = CBashBasicType(u'primitiveType', 0, u'IsBox')
    IsBox = CBashBasicType(u'primitiveType', 1, u'IsNone')
    IsSphere = CBashBasicType(u'primitiveType', 2, u'IsNone')
    IsPortalBox = CBashBasicType(u'primitiveType', 3, u'IsNone')

    IsUnidentified = CBashBasicType(u'collisionType', 0, u'IsStatic')
    IsStatic = CBashBasicType(u'collisionType', 1, u'IsUnidentified')
    IsAnimStatic = CBashBasicType(u'collisionType', 2, u'IsUnidentified')
    IsTransparent = CBashBasicType(u'collisionType', 3, u'IsUnidentified')
    IsClutter = CBashBasicType(u'collisionType', 4, u'IsUnidentified')
    IsWeapon = CBashBasicType(u'collisionType', 5, u'IsUnidentified')
    IsProjectile = CBashBasicType(u'collisionType', 6, u'IsUnidentified')
    IsSpell = CBashBasicType(u'collisionType', 7, u'IsUnidentified')
    IsBiped = CBashBasicType(u'collisionType', 8, u'IsUnidentified')
    IsTrees = CBashBasicType(u'collisionType', 9, u'IsUnidentified')
    IsProps = CBashBasicType(u'collisionType', 10, u'IsUnidentified')
    IsWater = CBashBasicType(u'collisionType', 11, u'IsUnidentified')
    IsTrigger = CBashBasicType(u'collisionType', 12, u'IsUnidentified')
    IsTerrain = CBashBasicType(u'collisionType', 13, u'IsUnidentified')
    IsTrap = CBashBasicType(u'collisionType', 14, u'IsUnidentified')
    IsNonCollidable = CBashBasicType(u'collisionType', 15, u'IsUnidentified')
    IsCloudTrap = CBashBasicType(u'collisionType', 16, u'IsUnidentified')
    IsGround = CBashBasicType(u'collisionType', 17, u'IsUnidentified')
    IsPortal = CBashBasicType(u'collisionType', 18, u'IsUnidentified')
    IsDebrisSmall = CBashBasicType(u'collisionType', 19, u'IsUnidentified')
    IsDebrisLarge = CBashBasicType(u'collisionType', 20, u'IsUnidentified')
    IsAcousticSpace = CBashBasicType(u'collisionType', 21, u'IsUnidentified')
    IsActorZone = CBashBasicType(u'collisionType', 22, u'IsUnidentified')
    IsProjectileZone = CBashBasicType(u'collisionType', 23, u'IsUnidentified')
    IsGasTrap = CBashBasicType(u'collisionType', 24, u'IsUnidentified')
    IsShellCasing = CBashBasicType(u'collisionType', 25, u'IsUnidentified')
    IsTransparentSmall = CBashBasicType(u'collisionType', 26, u'IsUnidentified')
    IsInvisibleWall = CBashBasicType(u'collisionType', 27, u'IsUnidentified')
    IsTransparentSmallAnim = CBashBasicType(u'collisionType', 28, u'IsUnidentified')
    IsDeadBip = CBashBasicType(u'collisionType', 29, u'IsUnidentified')
    IsCharController = CBashBasicType(u'collisionType', 30, u'IsUnidentified')
    IsAvoidBox = CBashBasicType(u'collisionType', 31, u'IsUnidentified')
    IsCollisionBox = CBashBasicType(u'collisionType', 32, u'IsUnidentified')
    IsCameraSphere = CBashBasicType(u'collisionType', 33, u'IsUnidentified')
    IsDoorDetection = CBashBasicType(u'collisionType', 34, u'IsUnidentified')
    IsCameraPick = CBashBasicType(u'collisionType', 35, u'IsUnidentified')
    IsItemPick = CBashBasicType(u'collisionType', 36, u'IsUnidentified')
    IsLineOfSight = CBashBasicType(u'collisionType', 37, u'IsUnidentified')
    IsPathPick = CBashBasicType(u'collisionType', 38, u'IsUnidentified')
    IsCustomPick1 = CBashBasicType(u'collisionType', 39, u'IsUnidentified')
    IsCustomPick2 = CBashBasicType(u'collisionType', 40, u'IsUnidentified')
    IsSpellExplosion = CBashBasicType(u'collisionType', 41, u'IsUnidentified')
    IsDroppingPick = CBashBasicType(u'collisionType', 42, u'IsUnidentified')

    IsMarkerNone = CBashBasicType(u'markerType', 0, u'IsMarkerNone')
    IsCity = CBashBasicType(u'markerType', 1, u'IsMarkerNone')
    IsSettlement = CBashBasicType(u'markerType', 2, u'IsMarkerNone')
    IsEncampment = CBashBasicType(u'markerType', 3, u'IsMarkerNone')
    IsNaturalLandmark = CBashBasicType(u'markerType', 4, u'IsMarkerNone')
    IsCave = CBashBasicType(u'markerType', 5, u'IsMarkerNone')
    IsFactory = CBashBasicType(u'markerType', 6, u'IsMarkerNone')
    IsMonument = CBashBasicType(u'markerType', 7, u'IsMarkerNone')
    IsMilitary = CBashBasicType(u'markerType', 8, u'IsMarkerNone')
    IsOffice = CBashBasicType(u'markerType', 9, u'IsMarkerNone')
    IsTownRuins = CBashBasicType(u'markerType', 10, u'IsMarkerNone')
    IsUrbanRuins = CBashBasicType(u'markerType', 11, u'IsMarkerNone')
    IsSewerRuins = CBashBasicType(u'markerType', 12, u'IsMarkerNone')
    IsMetro = CBashBasicType(u'markerType', 13, u'IsMarkerNone')
    IsVault = CBashBasicType(u'markerType', 14, u'IsMarkerNone')

    IsRadius = CBashBasicType(u'rangeType', 0, u'IsEverywhere')
    IsEverywhere = CBashBasicType(u'rangeType', 1, u'IsRadius')
    IsWorldAndLinkedInteriors = CBashBasicType(u'rangeType', 2, u'IsRadius')
    IsLinkedInteriors = CBashBasicType(u'rangeType', 3, u'IsRadius')
    IsCurrentCellOnly = CBashBasicType(u'rangeType', 4, u'IsRadius')
    copyattrs = FnvBaseRecord.baseattrs + [
        u'base', u'encounterZone', u'xrgd_p', u'xrgb_p', u'idleTime', u'idle',
        u'numRefs', u'compiledSize', u'lastIndex', u'scriptType',
        u'scriptFlags', u'compiled_p', u'scriptText', u'vars_list',
        u'references', u'topic', u'levelMod', u'owner', u'rank', u'count',
        u'radius', u'health', u'radiation', u'charge', u'decals_list',
        u'linkedReference', u'startRed', u'startRed', u'startBlue', u'endRed',
        u'endGreen', u'endBlue', u'rclr_p', u'activateParentFlags',
        u'activateParentRefs_list', u'prompt', u'parent', u'parentFlags',
        u'emittance', u'boundRef', u'primitiveX', u'primitiveY', u'primitiveZ',
        u'primitiveRed', u'primitiveGreen', u'primitiveBlue',
        u'primitiveUnknown', u'primitiveType', u'collisionType', u'extentX',
        u'extentY', u'extentZ', u'destinationFid', u'destinationPosX',
        u'destinationPosY', u'destinationPosZ', u'destinationRotX',
        u'destinationRotY', u'destinationRotZ', u'destinationFlags',
        u'markerFlags', u'markerFull', u'markerType', u'markerReputation',
        u'audioFull_p', u'audioLocation', u'audioBnam_p', u'audioUnknown1',
        u'audioUnknown2', u'xsrf_p', u'xsrd_p', u'target', u'rangeRadius',
        u'rangeType', u'staticPercentage', u'positionReference', u'lockLevel',
        u'lockKey', u'lockFlags', u'lockUnknown1', u'ammo', u'ammoCount',
        u'reflrefrs_list', u'litWaters', u'actionFlags', u'navMesh',
        u'navUnknown1', u'portalLinkedRoom1', u'portalLinkedRoom2',
        u'portalWidth', u'portalHeight', u'portalPosX', u'portalPosY',
        u'portalPosZ', u'portalQ1', u'portalQ2', u'portalQ3', u'portalQ4',
        u'seed', u'roomCount', u'roomUnknown1', u'rooms', u'occPlaneWidth',
        u'occPlaneHeight', u'occPlanePosX', u'occPlanePosY', u'occPlanePosZ',
        u'occPlaneQ1', u'occPlaneQ2', u'occPlaneQ3', u'occPlaneQ4',
        u'occPlaneRight', u'occPlaneLeft', u'occPlaneBottom', u'occPlaneTop',
        u'lod1', u'lod2', u'lod3', u'ignoredBySandbox', u'scale', u'posX',
        u'posY', u'posZ', u'rotX', u'rotY', u'rotZ']
    exportattrs = copyattrs[:]
    exportattrs.remove(u'xsrf_p')
    exportattrs.remove(u'xsrd_p')
    exportattrs.remove(u'audioBnam_p')
    exportattrs.remove(u'audioFull_p')
    exportattrs.remove(u'rclr_p')
    exportattrs.remove(u'xrgd_p')
    exportattrs.remove(u'xrgb_p')
    exportattrs.remove(u'compiled_p')

class FnvPGRERecord(FnvBaseRecord):
    __slots__ = []
    @property
    def _ParentID(self):
        _CGetField.restype = c_record_p
        return _CGetField(self._RecordID, 56, 0, 0, 0, 0, 0, 0, 0)

    _Type = b'PGRE'
    class Decal(ListComponent):
        __slots__ = []
        reference = CBashFORMID_LIST(1)
        unknown1 = CBashUINT8ARRAY_LIST(2, 24)
        copyattrs = [u'reference', u'unknown1']
        exportattrs = copyattrs[:]
        exportattrs.remove(u'unknown1')

    class ParentRef(ListComponent):
        __slots__ = []
        reference = CBashFORMID_LIST(1)
        delay = CBashFLOAT32_LIST(2)
        exportattrs = copyattrs = [u'reference', u'delay']

    class ReflRefr(ListComponent):
        __slots__ = []
        reference = CBashFORMID_LIST(1)
        type = CBashGeneric_LIST(2, c_ulong)

        IsReflection = CBashBasicType(u'type', 0, u'IsRefraction')
        IsRefraction = CBashBasicType(u'type', 1, u'IsReflection')
        exportattrs = copyattrs = [u'reference', u'type']

    base = CBashFORMID(7)
    encounterZone = CBashFORMID(8)
    xrgd_p = CBashUINT8ARRAY(9)
    xrgb_p = CBashUINT8ARRAY(10)
    idleTime = CBashFLOAT32(11)
    idle = CBashFORMID(12)
    unused1 = CBashUINT8ARRAY(13, 4)
    numRefs = CBashGeneric(14, c_ulong)
    compiledSize = CBashGeneric(15, c_ulong)
    lastIndex = CBashGeneric(16, c_ulong)
    scriptType = CBashGeneric(17, c_ushort)
    scriptFlags = CBashGeneric(18, c_ushort)
    compiled_p = CBashUINT8ARRAY(19)
    scriptText = CBashISTRING(20)

    def create_var(self):
        length = _CGetFieldAttribute(self._RecordID, 21, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 21, 0, 0, 0, 0, 0, 0, 0, c_ulong(length +
                                                                    1))
        return Var(self._RecordID, 21, length)
    vars = CBashLIST(21, Var)
    vars_list = CBashLIST(21, Var, True)

    references = CBashFORMID_OR_UINT32_ARRAY(22)
    topic = CBashFORMID(23)
    owner = CBashFORMID(24)
    rank = CBashGeneric(25, c_long)
    count = CBashGeneric(26, c_long)
    radius = CBashFLOAT32(27)
    health = CBashFLOAT32(28)

    def create_decal(self):
        length = _CGetFieldAttribute(self._RecordID, 29, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 29, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return self.Decal(self._RecordID, 29, length)
    decals = CBashLIST(29, Decal)
    decals_list = CBashLIST(29, Decal, True)

    linkedReference = CBashFORMID(30)
    startRed = CBashGeneric(31, c_ubyte)
    startGreen = CBashGeneric(32, c_ubyte)
    startBlue = CBashGeneric(33, c_ubyte)
    unused2 = CBashUINT8ARRAY(34, 1)
    endRed = CBashGeneric(35, c_ubyte)
    endGreen = CBashGeneric(36, c_ubyte)
    endBlue = CBashGeneric(37, c_ubyte)
    unused3 = CBashUINT8ARRAY(38, 1)
    activateParentFlags = CBashGeneric(39, c_ubyte)

    def create_activateParentRef(self):
        length = _CGetFieldAttribute(self._RecordID, 40, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 40, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return self.ParentRef(self._RecordID, 40, length)
    activateParentRefs = CBashLIST(40, ParentRef)
    activateParentRefs_list = CBashLIST(40, ParentRef, True)

    prompt = CBashSTRING(41)
    parent = CBashFORMID(42)
    parentFlags = CBashGeneric(43, c_ubyte)
    unused4 = CBashUINT8ARRAY(44, 3)
    emittance = CBashFORMID(45)
    boundRef = CBashFORMID(46)

    def create_reflrefr(self):
        length = _CGetFieldAttribute(self._RecordID, 47, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 47, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return self.ReflRefr(self._RecordID, 47, length)
    reflrefrs = CBashLIST(47, ReflRefr)
    reflrefrs_list = CBashLIST(47, ReflRefr, True)

    ignoredBySandbox = CBashGeneric(48, c_bool)
    scale = CBashFLOAT32(49)
    posX = CBashFLOAT32(50)
    posY = CBashFLOAT32(51)
    posZ = CBashFLOAT32(52)
    rotX = CBashFLOAT32(53)
    rotX_degrees = CBashDEGREES(53)
    rotY = CBashFLOAT32(54)
    rotY_degrees = CBashDEGREES(54)
    rotZ = CBashFLOAT32(55)
    rotZ_degrees = CBashDEGREES(55)

    IsEnabled = CBashBasicFlag(u'scriptFlags', 0x0001)

    IsOppositeParent = CBashBasicFlag(u'parentFlags', 0x00000001)
    IsPopIn = CBashBasicFlag(u'parentFlags', 0x00000002)

    IsObject = CBashBasicType(u'scriptType', 0x0000, u'IsQuest')
    IsQuest = CBashBasicType(u'scriptType', 0x0001, u'IsObject')
    IsEffect = CBashBasicType(u'scriptType', 0x0100, u'IsObject')

    copyattrs = FnvBaseRecord.baseattrs + [
        u'base', u'encounterZone', u'xrgd_p', u'xrgb_p', u'idleTime', u'idle',
        u'numRefs', u'compiledSize', u'lastIndex', u'scriptType',
        u'scriptFlags', u'compiled_p', u'scriptText', u'vars_list',
        u'references', u'topic', u'owner', u'rank', u'count', u'radius',
        u'health', u'decals_list', u'linkedReference', u'startRed',
        u'startGreen', u'startBlue', u'endRed', u'endGreen', u'endBlue',
        u'activateParentFlags', u'activateParentRefs_list', u'prompt',
        u'parent', u'parentFlags', u'emittance', u'boundRef',
        u'reflrefrs_list', u'ignoredBySandbox', u'scale', u'posX', u'posY',
        u'posZ', u'rotX', u'rotY', u'rotZ']
    exportattrs = copyattrs[:]
    exportattrs.remove(u'xrgd_p')
    exportattrs.remove(u'xrgb_p')
    exportattrs.remove(u'compiled_p')

class FnvPMISRecord(FnvBaseRecord):
    __slots__ = []
    @property
    def _ParentID(self):
        _CGetField.restype = c_record_p
        return _CGetField(self._RecordID, 56, 0, 0, 0, 0, 0, 0, 0)

    _Type = b'PMIS'
    class Decal(ListComponent):
        __slots__ = []
        reference = CBashFORMID_LIST(1)
        unknown1 = CBashUINT8ARRAY_LIST(2, 24)
        copyattrs = [u'reference', u'unknown1']
        exportattrs = copyattrs[:]
        exportattrs.remove(u'unknown1')

    class ParentRef(ListComponent):
        __slots__ = []
        reference = CBashFORMID_LIST(1)
        delay = CBashFLOAT32_LIST(2)
        exportattrs = copyattrs = [u'reference', u'delay']

    class ReflRefr(ListComponent):
        __slots__ = []
        reference = CBashFORMID_LIST(1)
        type = CBashGeneric_LIST(2, c_ulong)

        IsReflection = CBashBasicType(u'type', 0, u'IsRefraction')
        IsRefraction = CBashBasicType(u'type', 1, u'IsReflection')
        exportattrs = copyattrs = [u'reference', u'type']

    base = CBashFORMID(7)
    encounterZone = CBashFORMID(8)
    xrgd_p = CBashUINT8ARRAY(9)
    xrgb_p = CBashUINT8ARRAY(10)
    idleTime = CBashFLOAT32(11)
    idle = CBashFORMID(12)
    unused1 = CBashUINT8ARRAY(13, 4)
    numRefs = CBashGeneric(14, c_ulong)
    compiledSize = CBashGeneric(15, c_ulong)
    lastIndex = CBashGeneric(16, c_ulong)
    scriptType = CBashGeneric(17, c_ushort)
    scriptFlags = CBashGeneric(18, c_ushort)
    compiled_p = CBashUINT8ARRAY(19)
    scriptText = CBashISTRING(20)

    def create_var(self):
        length = _CGetFieldAttribute(self._RecordID, 21, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 21, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return Var(self._RecordID, 21, length)
    vars = CBashLIST(21, Var)
    vars_list = CBashLIST(21, Var, True)

    references = CBashFORMID_OR_UINT32_ARRAY(22)
    topic = CBashFORMID(23)
    owner = CBashFORMID(24)
    rank = CBashGeneric(25, c_long)
    count = CBashGeneric(26, c_long)
    radius = CBashFLOAT32(27)
    health = CBashFLOAT32(28)

    def create_decal(self):
        length = _CGetFieldAttribute(self._RecordID, 29, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 29, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return self.Decal(self._RecordID, 29, length)
    decals = CBashLIST(29, Decal)
    decals_list = CBashLIST(29, Decal, True)

    linkedReference = CBashFORMID(30)
    startRed = CBashGeneric(31, c_ubyte)
    startGreen = CBashGeneric(32, c_ubyte)
    startBlue = CBashGeneric(33, c_ubyte)
    unused2 = CBashUINT8ARRAY(34, 1)
    endRed = CBashGeneric(35, c_ubyte)
    endGreen = CBashGeneric(36, c_ubyte)
    endBlue = CBashGeneric(37, c_ubyte)
    unused3 = CBashUINT8ARRAY(38, 1)
    activateParentFlags = CBashGeneric(39, c_ubyte)

    def create_activateParentRef(self):
        length = _CGetFieldAttribute(self._RecordID, 40, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 40, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return self.ParentRef(self._RecordID, 40, length)
    activateParentRefs = CBashLIST(40, ParentRef)
    activateParentRefs_list = CBashLIST(40, ParentRef, True)

    prompt = CBashSTRING(41)
    parent = CBashFORMID(42)
    parentFlags = CBashGeneric(43, c_ubyte)
    unused4 = CBashUINT8ARRAY(44, 3)
    emittance = CBashFORMID(45)
    boundRef = CBashFORMID(46)

    def create_reflrefr(self):
        length = _CGetFieldAttribute(self._RecordID, 47, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 47, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return self.ReflRefr(self._RecordID, 47, length)
    reflrefrs = CBashLIST(47, ReflRefr)
    reflrefrs_list = CBashLIST(47, ReflRefr, True)

    ignoredBySandbox = CBashGeneric(48, c_bool)
    scale = CBashFLOAT32(49)
    posX = CBashFLOAT32(50)
    posY = CBashFLOAT32(51)
    posZ = CBashFLOAT32(52)
    rotX = CBashFLOAT32(53)
    rotX_degrees = CBashDEGREES(53)
    rotY = CBashFLOAT32(54)
    rotY_degrees = CBashDEGREES(54)
    rotZ = CBashFLOAT32(55)
    rotZ_degrees = CBashDEGREES(55)

    IsEnabled = CBashBasicFlag(u'scriptFlags', 0x0001)

    IsOppositeParent = CBashBasicFlag(u'parentFlags', 0x00000001)
    IsPopIn = CBashBasicFlag(u'parentFlags', 0x00000002)

    IsObject = CBashBasicType(u'scriptType', 0x0000, u'IsQuest')
    IsQuest = CBashBasicType(u'scriptType', 0x0001, u'IsObject')
    IsEffect = CBashBasicType(u'scriptType', 0x0100, u'IsObjecut')

    copyattrs = FnvBaseRecord.baseattrs + [
        u'base', u'encounterZone', u'xrgd_p', u'xrgb_p', u'idleTime', u'idle',
        u'numRefs', u'compiledSize', u'lastIndex', u'scriptType',
        u'scriptFlags', u'compiled_p', u'scriptText', u'vars_list',
        u'references', u'topic', u'owner', u'rank', u'count', u'radius',
        u'health', u'decals_list', u'linkedReference', u'startRed',
        u'startGreen', u'startBlue', u'endRed', u'endGreen', u'endBlue',
        u'activateParentFlags', u'activateParentRefs_list', u'prompt',
        u'parent', u'parentFlags', u'emittance', u'boundRef',
        u'reflrefrs_list', u'ignoredBySandbox', u'scale', u'posX', u'posY',
        u'posZ', u'rotX', u'rotY', u'rotZ']
    exportattrs = copyattrs[:]
    exportattrs.remove(u'xrgd_p')
    exportattrs.remove(u'xrgb_p')
    exportattrs.remove(u'compiled_p')

class FnvPBEARecord(FnvBaseRecord):
    __slots__ = []
    @property
    def _ParentID(self):
        _CGetField.restype = c_record_p
        return _CGetField(self._RecordID, 56, 0, 0, 0, 0, 0, 0, 0)

    _Type = b'PBEA'
    class Decal(ListComponent):
        __slots__ = []
        reference = CBashFORMID_LIST(1)
        unknown1 = CBashUINT8ARRAY_LIST(2, 24)
        copyattrs = [u'reference', u'unknown1']
        exportattrs = copyattrs[:]
        exportattrs.remove(u'unknown1')

    class ParentRef(ListComponent):
        __slots__ = []
        reference = CBashFORMID_LIST(1)
        delay = CBashFLOAT32_LIST(2)
        exportattrs = copyattrs = [u'reference', u'delay']

    class ReflRefr(ListComponent):
        __slots__ = []
        reference = CBashFORMID_LIST(1)
        type = CBashGeneric_LIST(2, c_ulong)

        IsReflection = CBashBasicType(u'type', 0, u'IsRefraction')
        IsRefraction = CBashBasicType(u'type', 1, u'IsReflection')
        exportattrs = copyattrs = [u'reference', u'type']

    base = CBashFORMID(7)
    encounterZone = CBashFORMID(8)
    xrgd_p = CBashUINT8ARRAY(9)
    xrgb_p = CBashUINT8ARRAY(10)
    idleTime = CBashFLOAT32(11)
    idle = CBashFORMID(12)
    unused1 = CBashUINT8ARRAY(13, 4)
    numRefs = CBashGeneric(14, c_ulong)
    compiledSize = CBashGeneric(15, c_ulong)
    lastIndex = CBashGeneric(16, c_ulong)
    scriptType = CBashGeneric(17, c_ushort)
    scriptFlags = CBashGeneric(18, c_ushort)
    compiled_p = CBashUINT8ARRAY(19)
    scriptText = CBashISTRING(20)

    def create_var(self):
        length = _CGetFieldAttribute(self._RecordID, 21, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 21, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return Var(self._RecordID, 21, length)
    vars = CBashLIST(21, Var)
    vars_list = CBashLIST(21, Var, True)

    references = CBashFORMID_OR_UINT32_ARRAY(22)
    topic = CBashFORMID(23)
    owner = CBashFORMID(24)
    rank = CBashGeneric(25, c_long)
    count = CBashGeneric(26, c_long)
    radius = CBashFLOAT32(27)
    health = CBashFLOAT32(28)

    def create_decal(self):
        length = _CGetFieldAttribute(self._RecordID, 29, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 29, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return self.Decal(self._RecordID, 29, length)
    decals = CBashLIST(29, Decal)
    decals_list = CBashLIST(29, Decal, True)

    linkedReference = CBashFORMID(30)
    startRed = CBashGeneric(31, c_ubyte)
    startGreen = CBashGeneric(32, c_ubyte)
    startBlue = CBashGeneric(33, c_ubyte)
    unused2 = CBashUINT8ARRAY(34, 1)
    endRed = CBashGeneric(35, c_ubyte)
    endGreen = CBashGeneric(36, c_ubyte)
    endBlue = CBashGeneric(37, c_ubyte)
    unused3 = CBashUINT8ARRAY(38, 1)
    activateParentFlags = CBashGeneric(39, c_ubyte)

    def create_activateParentRef(self):
        length = _CGetFieldAttribute(self._RecordID, 40, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 40, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return self.ParentRef(self._RecordID, 40, length)
    activateParentRefs = CBashLIST(40, ParentRef)
    activateParentRefs_list = CBashLIST(40, ParentRef, True)

    prompt = CBashSTRING(41)
    parent = CBashFORMID(42)
    parentFlags = CBashGeneric(43, c_ubyte)
    unused4 = CBashUINT8ARRAY(44, 3)
    emittance = CBashFORMID(45)
    boundRef = CBashFORMID(46)

    def create_reflrefr(self):
        length = _CGetFieldAttribute(self._RecordID, 47, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 47, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return self.ReflRefr(self._RecordID, 47, length)
    reflrefrs = CBashLIST(47, ReflRefr)
    reflrefrs_list = CBashLIST(47, ReflRefr, True)

    ignoredBySandbox = CBashGeneric(48, c_bool)
    scale = CBashFLOAT32(49)
    posX = CBashFLOAT32(50)
    posY = CBashFLOAT32(51)
    posZ = CBashFLOAT32(52)
    rotX = CBashFLOAT32(53)
    rotX_degrees = CBashDEGREES(53)
    rotY = CBashFLOAT32(54)
    rotY_degrees = CBashDEGREES(54)
    rotZ = CBashFLOAT32(55)
    rotZ_degrees = CBashDEGREES(55)

    IsEnabled = CBashBasicFlag(u'scriptFlags', 0x0001)

    IsOppositeParent = CBashBasicFlag(u'parentFlags', 0x00000001)
    IsPopIn = CBashBasicFlag(u'parentFlags', 0x00000002)

    IsObject = CBashBasicType(u'scriptType', 0x0000, u'IsQuest')
    IsQuest = CBashBasicType(u'scriptType', 0x0001, u'IsObject')
    IsEffect = CBashBasicType(u'scriptType', 0x0100, u'IsObject')

    copyattrs = FnvBaseRecord.baseattrs + [
        u'base', u'encounterZone', u'xrgd_p', u'xrgb_p', u'idleTime', u'idle',
        u'numRefs', u'compiledSize', u'lastIndex', u'scriptType',
        u'scriptFlags', u'compiled_p', u'scriptText', u'vars_list',
        u'references', u'topic', u'owner', u'rank', u'count', u'radius',
        u'health', u'decals_list', u'linkedReference', u'startRed',
        u'startGreen', u'startBlue', u'endRed', u'endGreen', u'endBlue',
        u'activateParentFlags', u'activateParentRefs_list', u'prompt',
        u'parent', u'parentFlags', u'emittance', u'boundRef',
        u'reflrefrs_list', u'ignoredBySandbox', u'scale', u'posX', u'posY',
        u'posZ', u'rotX', u'rotY', u'rotZ']
    exportattrs = copyattrs[:]
    exportattrs.remove(u'xrgd_p')
    exportattrs.remove(u'xrgb_p')
    exportattrs.remove(u'compiled_p')

class FnvPFLARecord(FnvBaseRecord):
    __slots__ = []
    @property
    def _ParentID(self):
        _CGetField.restype = c_record_p
        return _CGetField(self._RecordID, 56, 0, 0, 0, 0, 0, 0, 0)

    _Type = b'PFLA'
    class Decal(ListComponent):
        __slots__ = []
        reference = CBashFORMID_LIST(1)
        unknown1 = CBashUINT8ARRAY_LIST(2, 24)
        copyattrs = [u'reference', u'unknown1']
        exportattrs = copyattrs[:]
        exportattrs.remove(u'unknown1')

    class ParentRef(ListComponent):
        __slots__ = []
        reference = CBashFORMID_LIST(1)
        delay = CBashFLOAT32_LIST(2)
        exportattrs = copyattrs = [u'reference', u'delay']

    class ReflRefr(ListComponent):
        __slots__ = []
        reference = CBashFORMID_LIST(1)
        type = CBashGeneric_LIST(2, c_ulong)

        IsReflection = CBashBasicType(u'type', 0, u'IsRefraction')
        IsRefraction = CBashBasicType(u'type', 1, u'IsReflection')
        exportattrs = copyattrs = [u'reference', u'type']

    base = CBashFORMID(7)
    encounterZone = CBashFORMID(8)
    xrgd_p = CBashUINT8ARRAY(9)
    xrgb_p = CBashUINT8ARRAY(10)
    idleTime = CBashFLOAT32(11)
    idle = CBashFORMID(12)
    unused1 = CBashUINT8ARRAY(13, 4)
    numRefs = CBashGeneric(14, c_ulong)
    compiledSize = CBashGeneric(15, c_ulong)
    lastIndex = CBashGeneric(16, c_ulong)
    scriptType = CBashGeneric(17, c_ushort)
    scriptFlags = CBashGeneric(18, c_ushort)
    compiled_p = CBashUINT8ARRAY(19)
    scriptText = CBashISTRING(20)

    def create_var(self):
        length = _CGetFieldAttribute(self._RecordID, 21, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 21, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return Var(self._RecordID, 21, length)
    vars = CBashLIST(21, Var)
    vars_list = CBashLIST(21, Var, True)

    references = CBashFORMID_OR_UINT32_ARRAY(22)
    topic = CBashFORMID(23)
    owner = CBashFORMID(24)
    rank = CBashGeneric(25, c_long)
    count = CBashGeneric(26, c_long)
    radius = CBashFLOAT32(27)
    health = CBashFLOAT32(28)

    def create_decal(self):
        length = _CGetFieldAttribute(self._RecordID, 29, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 29, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return self.Decal(self._RecordID, 29, length)
    decals = CBashLIST(29, Decal)
    decals_list = CBashLIST(29, Decal, True)

    linkedReference = CBashFORMID(30)
    startRed = CBashGeneric(31, c_ubyte)
    startGreen = CBashGeneric(32, c_ubyte)
    startBlue = CBashGeneric(33, c_ubyte)
    unused2 = CBashUINT8ARRAY(34, 1)
    endRed = CBashGeneric(35, c_ubyte)
    endGreen = CBashGeneric(36, c_ubyte)
    endBlue = CBashGeneric(37, c_ubyte)
    unused3 = CBashUINT8ARRAY(38, 1)
    activateParentFlags = CBashGeneric(39, c_ubyte)

    def create_activateParentRef(self):
        length = _CGetFieldAttribute(self._RecordID, 40, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 40, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return self.ParentRef(self._RecordID, 40, length)
    activateParentRefs = CBashLIST(40, ParentRef)
    activateParentRefs_list = CBashLIST(40, ParentRef, True)

    prompt = CBashSTRING(41)
    parent = CBashFORMID(42)
    parentFlags = CBashGeneric(43, c_ubyte)
    unused4 = CBashUINT8ARRAY(44, 3)
    emittance = CBashFORMID(45)
    boundRef = CBashFORMID(46)

    def create_reflrefr(self):
        length = _CGetFieldAttribute(self._RecordID, 47, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 47, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return self.ReflRefr(self._RecordID, 47, length)
    reflrefrs = CBashLIST(47, ReflRefr)
    reflrefrs_list = CBashLIST(47, ReflRefr, True)

    ignoredBySandbox = CBashGeneric(48, c_bool)
    scale = CBashFLOAT32(49)
    posX = CBashFLOAT32(50)
    posY = CBashFLOAT32(51)
    posZ = CBashFLOAT32(52)
    rotX = CBashFLOAT32(53)
    rotX_degrees = CBashDEGREES(53)
    rotY = CBashFLOAT32(54)
    rotY_degrees = CBashDEGREES(54)
    rotZ = CBashFLOAT32(55)
    rotZ_degrees = CBashDEGREES(55)

    IsEnabled = CBashBasicFlag(u'scriptFlags', 0x0001)

    IsOppositeParent = CBashBasicFlag(u'parentFlags', 0x00000001)
    IsPopIn = CBashBasicFlag(u'parentFlags', 0x00000002)

    IsObject = CBashBasicType(u'scriptType', 0x0000, u'IsQuest')
    IsQuest = CBashBasicType(u'scriptType', 0x0001, u'IsObject')
    IsEffect = CBashBasicType(u'scriptType', 0x0100, u'IsObject')

    copyattrs = FnvBaseRecord.baseattrs + [
        u'base', u'encounterZone', u'xrgd_p', u'xrgb_p', u'idleTime', u'idle',
        u'numRefs', u'compiledSize', u'lastIndex', u'scriptType',
        u'scriptFlags', u'compiled_p', u'scriptText', u'vars_list',
        u'references', u'topic', u'owner', u'rank', u'count', u'radius',
        u'health', u'decals_list', u'linkedReference', u'startRed',
        u'startGreen', u'startBlue', u'endRed', u'endGreen', u'endBlue',
        u'activateParentFlags', u'activateParentRefs_list', u'prompt',
        u'parent', u'parentFlags', u'emittance', u'boundRef',
        u'reflrefrs_list', u'ignoredBySandbox', u'scale', u'posX', u'posY',
        u'posZ', u'rotX', u'rotY', u'rotZ']
    exportattrs = copyattrs[:]
    exportattrs.remove(u'xrgd_p')
    exportattrs.remove(u'xrgb_p')
    exportattrs.remove(u'compiled_p')

class FnvPCBERecord(FnvBaseRecord):
    __slots__ = []
    @property
    def _ParentID(self):
        _CGetField.restype = c_record_p
        return _CGetField(self._RecordID, 56, 0, 0, 0, 0, 0, 0, 0)

    _Type = b'PCBE'
    class Decal(ListComponent):
        __slots__ = []
        reference = CBashFORMID_LIST(1)
        unknown1 = CBashUINT8ARRAY_LIST(2, 24)
        copyattrs = [u'reference', u'unknown1']
        exportattrs = copyattrs[:]
        exportattrs.remove(u'unknown1')

    class ParentRef(ListComponent):
        __slots__ = []
        reference = CBashFORMID_LIST(1)
        delay = CBashFLOAT32_LIST(2)
        exportattrs = copyattrs = [u'reference', u'delay']

    class ReflRefr(ListComponent):
        __slots__ = []
        reference = CBashFORMID_LIST(1)
        type = CBashGeneric_LIST(2, c_ulong)

        IsReflection = CBashBasicType(u'type', 0, u'IsRefraction')
        IsRefraction = CBashBasicType(u'type', 1, u'IsReflection')
        exportattrs = copyattrs = [u'reference', u'type']

    base = CBashFORMID(7)
    encounterZone = CBashFORMID(8)
    xrgd_p = CBashUINT8ARRAY(9)
    xrgb_p = CBashUINT8ARRAY(10)
    idleTime = CBashFLOAT32(11)
    idle = CBashFORMID(12)
    unused1 = CBashUINT8ARRAY(13, 4)
    numRefs = CBashGeneric(14, c_ulong)
    compiledSize = CBashGeneric(15, c_ulong)
    lastIndex = CBashGeneric(16, c_ulong)
    scriptType = CBashGeneric(17, c_ushort)
    scriptFlags = CBashGeneric(18, c_ushort)
    compiled_p = CBashUINT8ARRAY(19)
    scriptText = CBashISTRING(20)

    def create_var(self):
        length = _CGetFieldAttribute(self._RecordID, 21, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 21, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return Var(self._RecordID, 21, length)
    vars = CBashLIST(21, Var)
    vars_list = CBashLIST(21, Var, True)

    references = CBashFORMID_OR_UINT32_ARRAY(22)
    topic = CBashFORMID(23)
    owner = CBashFORMID(24)
    rank = CBashGeneric(25, c_long)
    count = CBashGeneric(26, c_long)
    radius = CBashFLOAT32(27)
    health = CBashFLOAT32(28)

    def create_decal(self):
        length = _CGetFieldAttribute(self._RecordID, 29, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 29, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return self.Decal(self._RecordID, 29, length)
    decals = CBashLIST(29, Decal)
    decals_list = CBashLIST(29, Decal, True)

    linkedReference = CBashFORMID(30)
    startRed = CBashGeneric(31, c_ubyte)
    startGreen = CBashGeneric(32, c_ubyte)
    startBlue = CBashGeneric(33, c_ubyte)
    unused2 = CBashUINT8ARRAY(34, 1)
    endRed = CBashGeneric(35, c_ubyte)
    endGreen = CBashGeneric(36, c_ubyte)
    endBlue = CBashGeneric(37, c_ubyte)
    unused3 = CBashUINT8ARRAY(38, 1)
    activateParentFlags = CBashGeneric(39, c_ubyte)

    def create_activateParentRef(self):
        length = _CGetFieldAttribute(self._RecordID, 40, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 40, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return self.ParentRef(self._RecordID, 40, length)
    activateParentRefs = CBashLIST(40, ParentRef)
    activateParentRefs_list = CBashLIST(40, ParentRef, True)

    prompt = CBashSTRING(41)
    parent = CBashFORMID(42)
    parentFlags = CBashGeneric(43, c_ubyte)
    unused4 = CBashUINT8ARRAY(44, 3)
    emittance = CBashFORMID(45)
    boundRef = CBashFORMID(46)

    def create_reflrefr(self):
        length = _CGetFieldAttribute(self._RecordID, 47, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 47, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return self.ReflRefr(self._RecordID, 47, length)
    reflrefrs = CBashLIST(47, ReflRefr)
    reflrefrs_list = CBashLIST(47, ReflRefr, True)

    ignoredBySandbox = CBashGeneric(48, c_bool)
    scale = CBashFLOAT32(49)
    posX = CBashFLOAT32(50)
    posY = CBashFLOAT32(51)
    posZ = CBashFLOAT32(52)
    rotX = CBashFLOAT32(53)
    rotX_degrees = CBashDEGREES(53)
    rotY = CBashFLOAT32(54)
    rotY_degrees = CBashDEGREES(54)
    rotZ = CBashFLOAT32(55)
    rotZ_degrees = CBashDEGREES(55)

    IsEnabled = CBashBasicFlag(u'scriptFlags', 0x0001)

    IsOppositeParent = CBashBasicFlag(u'parentFlags', 0x00000001)
    IsPopIn = CBashBasicFlag(u'parentFlags', 0x00000002)

    IsObject = CBashBasicType(u'scriptType', 0x0000, u'IsQuest')
    IsQuest = CBashBasicType(u'scriptType', 0x0001, u'IsObject')
    IsEffect = CBashBasicType(u'scriptType', 0x0100, u'IsObject')

    copyattrs = FnvBaseRecord.baseattrs + [
        u'base', u'encounterZone', u'xrgd_p', u'xrgb_p', u'idleTime', u'idle',
        u'numRefs', u'compiledSize', u'lastIndex', u'scriptType',
        u'scriptFlags', u'compiled_p', u'scriptText', u'vars_list',
        u'references', u'topic', u'owner', u'rank', u'count', u'radius',
        u'health', u'decals_list', u'linkedReference', u'startRed',
        u'startGreen', u'startBlue', u'endRed', u'endGreen', u'endBlue',
        u'activateParentFlags', u'activateParentRefs_list', u'prompt',
        u'parent', u'parentFlags', u'emittance', u'boundRef',
        u'reflrefrs_list', u'ignoredBySandbox', u'scale', u'posX', u'posY',
        u'posZ', u'rotX', u'rotY', u'rotZ']
    exportattrs = copyattrs[:]
    exportattrs.remove(u'xrgd_p')
    exportattrs.remove(u'xrgb_p')
    exportattrs.remove(u'compiled_p')

class FnvNAVMRecord(FnvBaseRecord):
    __slots__ = []
    @property
    def _ParentID(self):
        _CGetField.restype = c_record_p
        return _CGetField(self._RecordID, 20, 0, 0, 0, 0, 0, 0, 0)

    _Type = b'NAVM'
    class Vertex(ListComponent):
        __slots__ = []
        x = CBashFLOAT32_LIST(1)
        y = CBashFLOAT32_LIST(2)
        z = CBashFLOAT32_LIST(3)

        exportattrs = copyattrs = [u'x', u'y', u'z']

    class Triangle(ListComponent):
        __slots__ = []
        vertex1 = CBashGeneric_LIST(1, c_short)
        vertex2 = CBashGeneric_LIST(2, c_short)
        vertex3 = CBashGeneric_LIST(3, c_short)
        edge1 = CBashGeneric_LIST(4, c_short)
        edge2 = CBashGeneric_LIST(5, c_short)
        edge3 = CBashGeneric_LIST(6, c_short)
        flags = CBashGeneric_LIST(7, c_ulong)

        IsTriangle0External = CBashBasicFlag(u'flags', 0x00000001)
        IsTriangle1External = CBashBasicFlag(u'flags', 0x00000002)
        IsTriangle2External = CBashBasicFlag(u'flags', 0x00000004)
        IsUnknown4 = CBashBasicFlag(u'flags', 0x00000008)
        IsUnknown5 = CBashBasicFlag(u'flags', 0x00000010)
        IsUnknown6 = CBashBasicFlag(u'flags', 0x00000020)
        IsUnknown7 = CBashBasicFlag(u'flags', 0x00000040)
        IsUnknown8 = CBashBasicFlag(u'flags', 0x00000080)
        IsUnknown9 = CBashBasicFlag(u'flags', 0x00000100)
        IsUnknown10 = CBashBasicFlag(u'flags', 0x00000200)
        IsUnknown11 = CBashBasicFlag(u'flags', 0x00000400)
        IsUnknown12 = CBashBasicFlag(u'flags', 0x00000800)
        IsUnknown13 = CBashBasicFlag(u'flags', 0x00001000)
        IsUnknown14 = CBashBasicFlag(u'flags', 0x00002000)
        IsUnknown15 = CBashBasicFlag(u'flags', 0x00004000)
        IsUnknown16 = CBashBasicFlag(u'flags', 0x00008000)
        IsUnknown17 = CBashBasicFlag(u'flags', 0x00010000)
        IsUnknown18 = CBashBasicFlag(u'flags', 0x00020000)
        IsUnknown19 = CBashBasicFlag(u'flags', 0x00040000)
        IsUnknown20 = CBashBasicFlag(u'flags', 0x00080000)
        IsUnknown21 = CBashBasicFlag(u'flags', 0x00100000)
        IsUnknown22 = CBashBasicFlag(u'flags', 0x00200000)
        IsUnknown23 = CBashBasicFlag(u'flags', 0x00400000)
        IsUnknown24 = CBashBasicFlag(u'flags', 0x00800000)
        IsUnknown25 = CBashBasicFlag(u'flags', 0x01000000)
        IsUnknown26 = CBashBasicFlag(u'flags', 0x02000000)
        IsUnknown27 = CBashBasicFlag(u'flags', 0x04000000)
        IsUnknown28 = CBashBasicFlag(u'flags', 0x08000000)
        IsUnknown29 = CBashBasicFlag(u'flags', 0x10000000)
        IsUnknown30 = CBashBasicFlag(u'flags', 0x20000000)
        IsUnknown31 = CBashBasicFlag(u'flags', 0x40000000)
        IsUnknown32 = CBashBasicFlag(u'flags', 0x80000000)
        exportattrs = copyattrs = [u'vertex1', u'vertex2', u'vertex3',
                                   u'edge1', u'edge2', u'edge3', u'flags']

    class Door(ListComponent):
        __slots__ = []
        door = CBashFORMID_LIST(1)
        unknown1 = CBashGeneric_LIST(2, c_ushort)
        unused1 = CBashUINT8ARRAY_LIST(3, 2)

        exportattrs = copyattrs = [u'door', u'unknown1']

    class Connection(ListComponent):
        __slots__ = []
        unknown1 = CBashUINT8ARRAY_LIST(1)
        mesh = CBashFORMID_LIST(2)
        triangle = CBashGeneric_LIST(3, c_ushort)

        exportattrs = copyattrs = [u'unknown1', u'mesh', u'triangle']

    version = CBashGeneric(7, c_ulong)
    cell = CBashFORMID(8)
    numVertices = CBashGeneric(9, c_ulong)
    numTriangles = CBashGeneric(10, c_ulong)
    numConnections = CBashGeneric(11, c_ulong)
    numUnknown = CBashGeneric(12, c_ulong)
    numDoors = CBashGeneric(13, c_ulong)

    def create_vertic(self):
        length = _CGetFieldAttribute(self._RecordID, 14, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 14, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return self.Vertex(self._RecordID, 14, length)
    vertices = CBashLIST(14, Vertex)
    vertices_list = CBashLIST(14, Vertex, True)

    def create_triangle(self):
        length = _CGetFieldAttribute(self._RecordID, 15, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 15, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return self.Triangle(self._RecordID, 15, length)
    triangles = CBashLIST(15, Triangle)
    triangles_list = CBashLIST(15, Triangle, True)

    unknown1 = CBashSINT16ARRAY(16)

    def create_door(self):
        length = _CGetFieldAttribute(self._RecordID, 17, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 17, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return self.Door(self._RecordID, 17, length)
    doors = CBashLIST(17, Door)
    doors_list = CBashLIST(17, Door, True)

    nvgd_p = CBashUINT8ARRAY(18)

    def create_connection(self):
        length = _CGetFieldAttribute(self._RecordID, 19, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 19, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return self.Connection(self._RecordID, 19, length)
    connections = CBashLIST(19, Connection)
    connections_list = CBashLIST(19, Connection, True)

    copyattrs = FnvBaseRecord.baseattrs + [u'version', u'cell', u'numVertices',
                                           u'numTriangles', u'numConnections',
                                           u'numUnknown', u'numDoors',
                                           u'vertices_list', u'triangles_list',
                                           u'unknown1', u'doors_list', u'nvgd_p',
                                           u'connections_list']
    exportattrs = copyattrs[:]
    exportattrs.remove(u'nvgd_p')

class FnvLANDRecord(FnvBaseRecord):
    __slots__ = []
    @property
    def _ParentID(self):
        _CGetField.restype = c_record_p
        return _CGetField(self._RecordID, 17, 0, 0, 0, 0, 0, 0, 0)

    _Type = b'LAND'
    class Normal(ListX2Component):
        __slots__ = []
        x = CBashGeneric_LISTX2(1, c_ubyte)
        y = CBashGeneric_LISTX2(2, c_ubyte)
        z = CBashGeneric_LISTX2(3, c_ubyte)
        exportattrs = copyattrs = [u'x', u'y', u'z']

    class Height(ListX2Component):
        __slots__ = []
        height = CBashGeneric_LISTX2(1, c_byte)
        exportattrs = copyattrs = [u'height']

    class Color(ListX2Component):
        __slots__ = []
        red = CBashGeneric_LISTX2(1, c_ubyte)
        green = CBashGeneric_LISTX2(2, c_ubyte)
        blue = CBashGeneric_LISTX2(3, c_ubyte)
        exportattrs = copyattrs = [u'red', u'green', u'blue']

    class BaseTexture(ListComponent):
        __slots__ = []
        texture = CBashFORMID_LIST(1)
        quadrant = CBashGeneric_LIST(2, c_byte)
        unused1 = CBashUINT8ARRAY_LIST(3, 1)
        layer = CBashGeneric_LIST(4, c_short)
        exportattrs = copyattrs = [u'texture', u'quadrant', u'layer']

    class AlphaLayer(ListComponent):
        __slots__ = []
        class Opacity(ListX2Component):
            __slots__ = []
            position = CBashGeneric_LISTX2(1, c_ushort)
            unused1 = CBashUINT8ARRAY_LISTX2(2, 2)
            opacity = CBashFLOAT32_LISTX2(3)
            exportattrs = copyattrs = [u'position', u'opacity']
        texture = CBashFORMID_LIST(1)
        quadrant = CBashGeneric_LIST(2, c_byte)
        unused1 = CBashUINT8ARRAY_LIST(3, 1)
        layer = CBashGeneric_LIST(4, c_short)

        def create_opacity(self):
            length = _CGetFieldAttribute(self._RecordID, self._FieldID, self._ListIndex, 5, 0, 0, 0, 0, 1)
            _CSetField(self._RecordID, self._FieldID, self._ListIndex, 5, 0, 0, 0, 0, 0, c_ulong(length + 1))
            return self.Opacity(self._RecordID, self._FieldID, self._ListIndex, 5, length)
        opacities = CBashLIST_LIST(5, Opacity)
        opacities_list = CBashLIST_LIST(5, Opacity, True)

        exportattrs = copyattrs = [u'texture', u'quadrant', u'layer',
                                   u'opacities_list']

    class VertexTexture(ListComponent):
        __slots__ = []
        texture = CBashFORMID_LIST(1)
        exportattrs = copyattrs = [u'texture']

    class Position(ListX2Component):
        __slots__ = []
        height = CBashFLOAT32_LISTX2(1)
        normalX = CBashGeneric_LISTX2(2, c_ubyte)
        normalY = CBashGeneric_LISTX2(3, c_ubyte)
        normalZ = CBashGeneric_LISTX2(4, c_ubyte)
        red = CBashGeneric_LISTX2(5, c_ubyte)
        green = CBashGeneric_LISTX2(6, c_ubyte)
        blue = CBashGeneric_LISTX2(7, c_ubyte)
        baseTexture = CBashFORMID_LISTX2(8)
        alphaLayer1Texture = CBashFORMID_LISTX2(9)
        alphaLayer1Opacity = CBashFLOAT32_LISTX2(10)
        alphaLayer2Texture = CBashFORMID_LISTX2(11)
        alphaLayer2Opacity = CBashFLOAT32_LISTX2(12)
        alphaLayer3Texture = CBashFORMID_LISTX2(13)
        alphaLayer3Opacity = CBashFLOAT32_LISTX2(14)
        alphaLayer4Texture = CBashFORMID_LISTX2(15)
        alphaLayer4Opacity = CBashFLOAT32_LISTX2(16)
        alphaLayer5Texture = CBashFORMID_LISTX2(17)
        alphaLayer5Opacity = CBashFLOAT32_LISTX2(18)
        alphaLayer6Texture = CBashFORMID_LISTX2(19)
        alphaLayer6Opacity = CBashFLOAT32_LISTX2(20)
        alphaLayer7Texture = CBashFORMID_LISTX2(21)
        alphaLayer7Opacity = CBashFLOAT32_LISTX2(22)
        alphaLayer8Texture = CBashFORMID_LISTX2(23)
        alphaLayer8Opacity = CBashFLOAT32_LISTX2(24)
        exportattrs = copyattrs = [
            u'height', u'normalX', u'normalY', u'normalZ', u'red', u'green',
            u'blue', u'baseTexture', u'alphaLayer1Texture',
            u'alphaLayer1Opacity', u'alphaLayer2Texture',
            u'alphaLayer2Opacity', u'alphaLayer3Texture',
            u'alphaLayer3Opacity', u'alphaLayer4Texture',
            u'alphaLayer4Opacity', u'alphaLayer5Texture',
            u'alphaLayer5Opacity', u'alphaLayer6Texture',
            u'alphaLayer6Opacity', u'alphaLayer7Texture',
            u'alphaLayer7Opacity', u'alphaLayer8Texture',
            u'alphaLayer8Opacity']

    data_p = CBashUINT8ARRAY(7)

    def get_normals(self):
        return [[self.Normal(self._RecordID, 8, x, 0, y) for y in xrange(0,
                                                                         33)] for x in xrange(0,33)]
    def set_normals(self, nElements):
        if nElements is None or len(nElements) != 33: return
        for oElement, nElement in zip(self.normals, nElements if isinstance(nElements[0], tuple) else [ExtractCopyList(nElements[x]) for x in xrange(0,33)]):
            SetCopyList(oElement, nElement)
    normals = property(get_normals, set_normals)
    def get_normals_list(self):
        return [ExtractCopyList([self.Normal(self._RecordID, 8, x, 0, y) for y in xrange(0,33)]) for x in xrange(0,33)]

    normals_list = property(get_normals_list, set_normals)

    heightOffset = CBashFLOAT32(9)

    def get_heights(self):
        return [[self.Height(self._RecordID, 10, x, 0, y) for y in xrange(0,33)] for x in xrange(0,33)]
    def set_heights(self, nElements):
        if nElements is None or len(nElements) != 33: return
        for oElement, nElement in zip(self.heights, nElements if isinstance(nElements[0], tuple) else [ExtractCopyList(nElements[x]) for x in xrange(0,33)]):
            SetCopyList(oElement, nElement)

    heights = property(get_heights, set_heights)
    def get_heights_list(self):
        return [ExtractCopyList([self.Height(self._RecordID, 10, x, 0, y) for y in xrange(0,33)]) for x in xrange(0,33)]
    heights_list = property(get_heights_list, set_heights)

    unused1 = CBashUINT8ARRAY(11, 3)

    def get_colors(self):
        return [[self.Color(self._RecordID, 12, x, 0, y) for y in xrange(0,33)] for x in xrange(0,33)]
    def set_colors(self, nElements):
        if nElements is None or len(nElements) != 33: return
        for oElement, nElement in zip(self.colors, nElements if isinstance(nElements[0], tuple) else [ExtractCopyList(nElements[x]) for x in xrange(0,33)]):
            SetCopyList(oElement, nElement)

    colors = property(get_colors, set_colors)
    def get_colors_list(self):
        return [ExtractCopyList([self.Color(self._RecordID, 12, x, 0, y) for y in xrange(0,33)]) for x in xrange(0,33)]
    colors_list = property(get_colors_list, set_colors)

    def create_baseTexture(self):
        length = _CGetFieldAttribute(self._RecordID, 13, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 13, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return self.BaseTexture(self._RecordID, 13, length)
    baseTextures = CBashLIST(13, BaseTexture)
    baseTextures_list = CBashLIST(13, BaseTexture, True)

    def create_alphaLayer(self):
        length = _CGetFieldAttribute(self._RecordID, 14, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 14, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return self.AlphaLayer(self._RecordID, 14, length)
    alphaLayers = CBashLIST(14, AlphaLayer)
    alphaLayers_list = CBashLIST(14, AlphaLayer, True)

    def create_vertexTexture(self):
        length = _CGetFieldAttribute(self._RecordID, 15, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 15, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return self.VertexTexture(self._RecordID, 15, length)
    vertexTextures = CBashLIST(15, VertexTexture)
    vertexTextures_list = CBashLIST(15, VertexTexture, True)

    ##The Positions accessor is unique in that it duplicates the above accessors. It just presents the data in a more friendly format.
    def get_Positions(self):
        return [[self.Position(self._RecordID, 16, row, 0, column) for column in xrange(0,33)] for row in xrange(0,33)]
    def set_Positions(self, nElements):
        if nElements is None or len(nElements) != 33: return
        for oElement, nElement in zip(self.Positions, nElements if isinstance(nElements[0], tuple) else [ExtractCopyList(nElements[x]) for x in xrange(0,33)]):
            SetCopyList(oElement, nElement)
    Positions = property(get_Positions, set_Positions)
    def get_Positions_list(self):
        return [ExtractCopyList([self.Position(self._RecordID, 16, x, 0, y) for y in xrange(0,33)]) for x in xrange(0,33)]
    Positions_list = property(get_Positions_list, set_Positions)
    copyattrs = FnvBaseRecord.baseattrs + [
        u'data_p', u'normals_list', u'heights_list', u'heightOffset',
        u'colors_list', u'baseTextures_list', u'alphaLayers_list',
        u'vertexTextures_list']
    exportattrs = copyattrs[:]
    exportattrs.remove(u'data_p')

class FnvINFORecord(FnvBaseRecord):
    __slots__ = []
    @property
    def _ParentID(self):
        _CGetField.restype = c_record_p
        return _CGetField(self._RecordID, 44, 0, 0, 0, 0, 0, 0, 0)

    _Type = b'INFO'
    class Response(ListComponent):
        __slots__ = []
        emotionType = CBashGeneric_LIST(1, c_ulong)
        emotionValue = CBashGeneric_LIST(2, c_long)
        unused1 = CBashUINT8ARRAY_LIST(3, 4)
        responseNum = CBashGeneric_LIST(4, c_ubyte)
        unused2 = CBashUINT8ARRAY_LIST(5, 3)
        sound = CBashFORMID_LIST(6)
        flags = CBashGeneric_LIST(7, c_ubyte)
        unused3 = CBashUINT8ARRAY_LIST(8, 3)
        responseText = CBashSTRING_LIST(9)
        actorNotes = CBashISTRING_LIST(10)
        editNotes = CBashISTRING_LIST(11)
        speakerAnim = CBashFORMID_LIST(12)
        listenerAnim = CBashFORMID_LIST(13)

        IsUseEmotionAnim = CBashBasicFlag(u'flags', 0x01)

        IsNeutral = CBashBasicType(u'emotionType', 0, u'IsAnger')
        IsAnger = CBashBasicType(u'emotionType', 1, u'IsNeutral')
        IsDisgust = CBashBasicType(u'emotionType', 2, u'IsNeutral')
        IsFear = CBashBasicType(u'emotionType', 3, u'IsNeutral')
        IsSad = CBashBasicType(u'emotionType', 4, u'IsNeutral')
        IsHappy = CBashBasicType(u'emotionType', 5, u'IsNeutral')
        IsSurprise = CBashBasicType(u'emotionType', 6, u'IsNeutral')
        IsPained = CBashBasicType(u'emotionType', 7, u'IsNeutral')
        exportattrs = copyattrs = [u'emotionType', u'emotionValue', u'responseNum',
                                   u'sound', u'flags', u'responseText', u'actorNotes',
                                   u'editNotes', u'speakerAnim', u'listenerAnim']

    class InfoScript(BaseComponent):
        __slots__ = []
        unused1 = CBashUINT8ARRAY_GROUP(0, 4)
        numRefs = CBashGeneric_GROUP(1, c_ulong)
        compiledSize = CBashGeneric_GROUP(2, c_ulong)
        lastIndex = CBashGeneric_GROUP(3, c_ulong)
        scriptType = CBashGeneric_GROUP(4, c_ushort)
        scriptFlags = CBashGeneric_GROUP(5, c_ushort)
        compiled_p = CBashUINT8ARRAY_GROUP(6)
        scriptText = CBashISTRING_GROUP(7)
        def create_var(self):
            FieldID = self._FieldID + 8
            length = _CGetFieldAttribute(self._RecordID, FieldID, 0, 0, 0, 0, 0, 0, 1)
            _CSetField(self._RecordID, FieldID, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
            return Var(self._RecordID, FieldID, length)
        vars = CBashLIST_GROUP(8, Var)
        vars_list = CBashLIST_GROUP(8, Var, True)
        references = CBashFORMID_OR_UINT32_ARRAY_GROUP(9)

        IsEnabled = CBashBasicFlag(u'scriptFlags', 0x0001)

        IsObject = CBashBasicType(u'scriptType', 0x0000, u'IsQuest')
        IsQuest = CBashBasicType(u'scriptType', 0x0001, u'IsObject')
        IsEffect = CBashBasicType(u'scriptType', 0x0100, u'IsObject')
        copyattrs = [u'numRefs', u'compiledSize', u'lastIndex',
                     u'scriptType', u'scriptFlags', u'compiled_p',
                     u'scriptText', u'vars_list', u'references']
        exportattrs = copyattrs[:]
        exportattrs.remove(u'compiled_p')

    dialType = CBashGeneric(7, c_ubyte)
    nextSpeaker = CBashGeneric(8, c_ubyte)
    flags = CBashGeneric(9, c_ushort)
    quest = CBashFORMID(10)
    topic = CBashFORMID(11)
    prevInfo = CBashFORMID(12)
    addTopics = CBashFORMIDARRAY(13)

    def create_response(self):
        length = _CGetFieldAttribute(self._RecordID, 14, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 14, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return self.Response(self._RecordID, 14, length)
    responses = CBashLIST(14, Response)
    responses_list = CBashLIST(14, Response, True)

    def create_condition(self):
        length = _CGetFieldAttribute(self._RecordID, 15, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 15, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return FNVCondition(self._RecordID, 15, length)
    conditions = CBashLIST(15, FNVCondition)
    conditions_list = CBashLIST(15, FNVCondition, True)

    choices = CBashFORMIDARRAY(16)
    linksFrom = CBashFORMIDARRAY(17)
    unknown = CBashFORMIDARRAY(18)
    begin = CBashGrouped(19, InfoScript)
    begin_list = CBashGrouped(19, InfoScript, True)

    end = CBashGrouped(29, InfoScript)
    end_list = CBashGrouped(29, InfoScript, True)

    unusedSound = CBashFORMID(39)
    prompt = CBashSTRING(40)
    speaker = CBashFORMID(41)
    actorValueOrPerk = CBashFORMID(42)
    challengeType = CBashGeneric(43, c_ulong)

    IsGoodbye = CBashBasicFlag(u'flags', 0x0001)
    IsRandom = CBashBasicFlag(u'flags', 0x0002)
    IsSayOnce = CBashBasicFlag(u'flags', 0x0004)
    IsRunImmediately = CBashBasicFlag(u'flags', 0x0008)
    IsInfoRefusal = CBashBasicFlag(u'flags', 0x0010)
    IsRandomEnd = CBashBasicFlag(u'flags', 0x0020)
    IsRunForRumors = CBashBasicFlag(u'flags', 0x0040)
    IsSpeechChallenge = CBashBasicFlag(u'flags', 0x0080)
    IsSayOnceADay = CBashBasicFlag(u'flags', 0x0100)
    IsAlwaysDarken = CBashBasicFlag(u'flags', 0x0200)

    IsTopic = CBashBasicType(u'dialType', 0, u'IsConversation')
    IsConversation = CBashBasicType(u'dialType', 1, u'IsTopic')
    IsCombat = CBashBasicType(u'dialType', 2, u'IsTopic')
    IsPersuasion = CBashBasicType(u'dialType', 3, u'IsTopic')
    IsDetection = CBashBasicType(u'dialType', 4, u'IsTopic')
    IsService = CBashBasicType(u'dialType', 5, u'IsTopic')
    IsMisc = CBashBasicType(u'dialType', 6, u'IsTopic')
    IsRadio = CBashBasicType(u'dialType', 7, u'IsTopic')

    IsTarget = CBashBasicType(u'nextSpeaker', 0, u'IsSelf')
    IsSelf = CBashBasicType(u'nextSpeaker', 1, u'IsTarget')
    IsEither = CBashBasicType(u'nextSpeaker', 2, u'IsTarget')

    IsNone = CBashBasicType(u'challengeType', 0, u'IsVeryEasy')
    IsVeryEasy = CBashBasicType(u'challengeType', 1, u'IsNone')
    IsEasy = CBashBasicType(u'challengeType', 2, u'IsNone')
    IsAverage = CBashBasicType(u'challengeType', 3, u'IsNone')
    IsHard = CBashBasicType(u'challengeType', 4, u'IsNone')
    IsVeryHard = CBashBasicType(u'challengeType', 5, u'IsNone')
    exportattrs = copyattrs = FnvBaseRecord.baseattrs + [
        u'dialType', u'nextSpeaker', u'flags', u'quest', u'topic', u'prevInfo',
        u'addTopics', u'responses_list', u'conditions_list', u'choices',
        u'linksFrom', u'unknown', u'begin_list', u'end_list', u'prompt',
        u'speaker', u'actorValueOrPerk', u'challengeType']

class FnvGMSTRecord(FnvBaseRecord):
    __slots__ = []
    _Type = b'GMST'
    def get_value(self):
        fieldtype = _CGetFieldAttribute(self._RecordID, 7, 0, 0, 0, 0, 0, 0, 2)
        if fieldtype == API_FIELDS.UNKNOWN: return None
        _CGetField.restype = POINTER(c_long) if fieldtype == \
                                                API_FIELDS.SINT32 else POINTER(c_float) if fieldtype == API_FIELDS.FLOAT32 else c_char_p
        retValue = _CGetField(self._RecordID, 7, 0, 0, 0, 0, 0, 0, 0)
        return (_unicode(retValue) if fieldtype == API_FIELDS.STRING else round(retValue.contents.value,6) if fieldtype == API_FIELDS.FLOAT32 else retValue.contents.value) if retValue else None
    def set_value(self, nValue):
        if nValue is None: _CDeleteField(self._RecordID, 7, 0, 0, 0, 0, 0, 0)
        else:
            fieldtype = _CGetFieldAttribute(self._RecordID, 7, 0, 0, 0, 0, 0, 0, 2)
            _CSetField(self._RecordID, 7, 0, 0, 0, 0, 0, 0, byref(c_long(nValue)) if fieldtype == API_FIELDS.SINT32 else byref(c_float(round(nValue,6))) if fieldtype == API_FIELDS.FLOAT32 else _encode(nValue), 0)
    value = property(get_value, set_value)
    exportattrs = copyattrs = FnvBaseRecord.baseattrs + [u'value']

class FnvTXSTRecord(FnvBaseRecord):
    __slots__ = []
    _Type = b'TXST'
    boundX1 = CBashGeneric(7, c_short)
    boundY1 = CBashGeneric(8, c_short)
    boundZ1 = CBashGeneric(9, c_short)
    boundX2 = CBashGeneric(10, c_short)
    boundY2 = CBashGeneric(11, c_short)
    boundZ2 = CBashGeneric(12, c_short)
    baseImageOrTransparencyPath = CBashISTRING(13)
    normalMapOrSpecularPath = CBashISTRING(14)
    envMapMaskOrUnkPath = CBashISTRING(15)
    glowMapOrUnusedPath = CBashISTRING(16)
    parallaxMapOrUnusedPath = CBashISTRING(17)
    envMapOrUnusedPath = CBashISTRING(18)
    decalMinWidth = CBashFLOAT32(19)
    decalMaxWidth = CBashFLOAT32(20)
    decalMinHeight = CBashFLOAT32(21)
    decalMaxHeight = CBashFLOAT32(22)
    decalDepth = CBashFLOAT32(23)
    decalShininess = CBashFLOAT32(24)
    decalScale = CBashFLOAT32(25)
    decalPasses = CBashGeneric(26, c_ubyte)
    decalFlags = CBashGeneric(27, c_ubyte)
    decalUnused1 = CBashUINT8ARRAY(28, 2)
    decalRed = CBashGeneric(29, c_ubyte)
    decalGreen = CBashGeneric(30, c_ubyte)
    decalBlue = CBashGeneric(31, c_ubyte)
    decalUnused2 = CBashUINT8ARRAY(32, 1)
    flags = CBashGeneric(33, c_ushort)

    IsNoSpecularMap = CBashBasicFlag(u'flags', 0x00000001)
    IsSpecularMap = CBashInvertedFlag(u'IsNoSpecularMap')

    IsObjectParallax = CBashBasicFlag(u'decalFlags', 0x00000001)
    IsObjectAlphaBlending = CBashBasicFlag(u'decalFlags', 0x00000002)
    IsObjectAlphaTesting = CBashBasicFlag(u'decalFlags', 0x00000004)
    copyattrs = FnvBaseRecord.baseattrs + [
        u'boundX1', u'boundY1', u'boundZ1', u'boundX2', u'boundY2', u'boundZ2',
        u'baseImageOrTransparencyPath', u'normalMapOrSpecularPath',
        u'envMapMaskOrUnkPath', u'glowMapOrUnusedPath',
        u'parallaxMapOrUnusedPath', u'envMapOrUnusedPath', u'decalMinWidth',
        u'decalMaxWidth', u'decalMinHeight', u'decalMaxHeight', u'decalDepth',
        u'decalShininess', u'decalScale', u'decalPasses', u'decalFlags',
        u'decalUnused1', u'decalRed', u'decalGreen', u'decalBlue',
        u'decalUnused2', u'flags']
    exportattrs = copyattrs[:]
    exportattrs.remove(u'decalUnused1')
    exportattrs.remove(u'decalUnused2')

class FnvMICNRecord(FnvBaseRecord):
    __slots__ = []
    _Type = b'MICN'
    iconPath = CBashISTRING(7)
    smallIconPath = CBashISTRING(8)

    exportattrs = copyattrs = FnvBaseRecord.baseattrs + [u'iconPath', u'smallIconPath']

class FnvGLOBRecord(FnvBaseRecord):
    __slots__ = []
    _Type = b'GLOB'
    format = CBashGeneric(7, c_char)
    value = CBashFLOAT32(8)

    exportattrs = copyattrs = FnvBaseRecord.baseattrs + [u'format', u'value']

class FnvCLASRecord(FnvBaseRecord):
    __slots__ = []
    _Type = b'CLAS'
    full = CBashSTRING(7)
    description = CBashSTRING(8)
    iconPath = CBashISTRING(9)
    smallIconPath = CBashISTRING(10)
    tagSkills1 = CBashGeneric(11, c_long)
    tagSkills2 = CBashGeneric(12, c_long)
    tagSkills3 = CBashGeneric(13, c_long)
    tagSkills4 = CBashGeneric(14, c_long)
    flags = CBashGeneric(15, c_ulong)
    services = CBashGeneric(16, c_ulong)
    trainSkill = CBashGeneric(17, c_byte)
    trainLevel = CBashGeneric(18, c_ubyte)
    unused1 = CBashUINT8ARRAY(19, 2)
    strength = CBashGeneric(20, c_ubyte)
    perception = CBashGeneric(21, c_ubyte)
    endurance = CBashGeneric(22, c_ubyte)
    charisma = CBashGeneric(23, c_ubyte)
    intelligence = CBashGeneric(24, c_ubyte)
    agility = CBashGeneric(25, c_ubyte)
    luck = CBashGeneric(26, c_ubyte)

    IsPlayable = CBashBasicFlag(u'flags', 0x00000001)
    IsGuard = CBashBasicFlag(u'flags', 0x00000002)

    IsServicesWeapons = CBashBasicFlag(u'services', 0x00000001)
    IsServicesArmor = CBashBasicFlag(u'services', 0x00000002)
    IsServicesClothing = CBashBasicFlag(u'services', 0x00000004)
    IsServicesBooks = CBashBasicFlag(u'services', 0x00000008)
    IsServicesFood = CBashBasicFlag(u'services', 0x00000010)
    IsServicesChems = CBashBasicFlag(u'services', 0x00000020)
    IsServicesStimpacks = CBashBasicFlag(u'services', 0x00000040)
    IsServicesLights = CBashBasicFlag(u'services', 0x00000080)
    IsServicesMiscItems = CBashBasicFlag(u'services', 0x00000400)
    IsServicesPotions = CBashBasicFlag(u'services', 0x00002000)
    IsServicesTraining = CBashBasicFlag(u'services', 0x00004000)
    IsServicesRecharge = CBashBasicFlag(u'services', 0x00010000)
    IsServicesRepair = CBashBasicFlag(u'services', 0x00020000)
    exportattrs = copyattrs = FnvBaseRecord.baseattrs + [
        u'full', u'description', u'iconPath', u'smallIconPath', u'tagSkills1',
        u'tagSkills2', u'tagSkills3', u'tagSkills4', u'flags', u'services',
        u'trainSkill', u'trainLevel', u'strength', u'perception', u'endurance',
        u'charisma', u'intelligence', u'agility', u'luck']

class FnvFACTRecord(FnvBaseRecord):
    __slots__ = []
    _Type = b'FACT'
    class Rank(ListComponent):
        __slots__ = []
        rank = CBashGeneric_LIST(1, c_long)
        male = CBashSTRING_LIST(2)
        female = CBashSTRING_LIST(3)
        insigniaPath = CBashISTRING_LIST(4)
        exportattrs = copyattrs = [u'rank', u'male', u'female', u'insigniaPath']

    full = CBashSTRING(7)

    def create_relation(self):
        length = _CGetFieldAttribute(self._RecordID, 8, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 8, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return FNVRelation(self._RecordID, 8, length)
    relations = CBashLIST(8, FNVRelation)
    relations_list = CBashLIST(8, FNVRelation, True)

    flags = CBashGeneric(9, c_ushort)
    unused1 = CBashUINT8ARRAY(10, 2)
    crimeGoldMultiplier = CBashFLOAT32(11)

    def create_rank(self):
        length = _CGetFieldAttribute(self._RecordID, 12, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 12, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return self.Rank(self._RecordID, 12, length)
    ranks = CBashLIST(12, Rank)
    ranks_list = CBashLIST(12, Rank, True)

    reputation = CBashFORMID(13)

    IsHiddenFromPC = CBashBasicFlag(u'flags', 0x0001)
    IsEvil = CBashBasicFlag(u'flags', 0x0002)
    IsSpecialCombat = CBashBasicFlag(u'flags', 0x0004)
    IsTrackCrime = CBashBasicFlag(u'flags', 0x0100)
    IsAllowSell = CBashBasicFlag(u'flags', 0x0200)
    exportattrs = copyattrs = FnvBaseRecord.baseattrs + [u'full', u'relations_list', u'flags',
                                                         u'crimeGoldMultiplier', u'ranks_list', u'reputation']

class FnvHDPTRecord(FnvBaseRecord):
    __slots__ = []
    _Type = b'HDPT'
    full = CBashSTRING(7)
    modPath = CBashISTRING(8)
    modb = CBashFLOAT32(9)
    modt_p = CBashUINT8ARRAY(10)

    def create_altTexture(self):
        length = _CGetFieldAttribute(self._RecordID, 11, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 11, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return FNVAltTexture(self._RecordID, 11, length)
    altTextures = CBashLIST(11, FNVAltTexture)
    altTextures_list = CBashLIST(11, FNVAltTexture, True)

    modelFlags = CBashGeneric(12, c_ubyte)
    flags = CBashGeneric(13, c_ubyte)
    parts = CBashFORMIDARRAY(14)

    IsPlayable = CBashBasicFlag(u'flags', 0x01)

    IsHead = CBashBasicFlag(u'modelFlags', 0x01)
    IsTorso = CBashBasicFlag(u'modelFlags', 0x02)
    IsRightHand = CBashBasicFlag(u'modelFlags', 0x04)
    IsLeftHand = CBashBasicFlag(u'modelFlags', 0x08)
    copyattrs = FnvBaseRecord.baseattrs + [u'full', u'modPath', u'modb',
                                           u'modt_p', u'altTextures_list',
                                           u'modelFlags', u'flags', u'parts']
    exportattrs = copyattrs[:]
    exportattrs.remove(u'modt_p')

class FnvHAIRRecord(FnvBaseRecord):
    __slots__ = []
    _Type = b'HAIR'
    full = CBashSTRING(7)
    modPath = CBashISTRING(8)
    modb = CBashFLOAT32(9)
    modt_p = CBashUINT8ARRAY(10)

    def create_altTexture(self):
        length = _CGetFieldAttribute(self._RecordID, 11, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 11, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return FNVAltTexture(self._RecordID, 11, length)
    altTextures = CBashLIST(11, FNVAltTexture)
    altTextures_list = CBashLIST(11, FNVAltTexture, True)

    modelFlags = CBashGeneric(12, c_ubyte)
    iconPath = CBashISTRING(13)
    flags = CBashGeneric(14, c_ubyte)

    IsPlayable = CBashBasicFlag(u'flags', 0x01)
    IsNotMale = CBashBasicFlag(u'flags', 0x02)
    IsMale = CBashInvertedFlag(u'IsNotMale')
    IsNotFemale = CBashBasicFlag(u'flags', 0x04)
    IsFemale = CBashInvertedFlag(u'IsNotFemale')
    IsFixedColor = CBashBasicFlag(u'flags', 0x08)

    IsHead = CBashBasicFlag(u'modelFlags', 0x01)
    IsTorso = CBashBasicFlag(u'modelFlags', 0x02)
    IsRightHand = CBashBasicFlag(u'modelFlags', 0x04)
    IsLeftHand = CBashBasicFlag(u'modelFlags', 0x08)
    copyattrs = FnvBaseRecord.baseattrs + [u'full', u'modPath', u'modb',
                                           u'modt_p', u'altTextures_list',
                                           u'modelFlags', u'iconPath', u'flags']
    exportattrs = copyattrs[:]
    exportattrs.remove(u'modt_p')

class FnvEYESRecord(FnvBaseRecord):
    __slots__ = []
    _Type = b'EYES'
    full = CBashSTRING(7)
    iconPath = CBashISTRING(8)
    flags = CBashGeneric(9, c_ubyte)

    IsPlayable = CBashBasicFlag(u'flags', 0x01)
    IsNotMale = CBashBasicFlag(u'flags', 0x02)
    IsMale = CBashInvertedFlag(u'IsNotMale')
    IsNotFemale = CBashBasicFlag(u'flags', 0x04)
    IsFemale = CBashInvertedFlag(u'IsNotFemale')
    exportattrs = copyattrs = FnvBaseRecord.baseattrs + [u'full', u'iconPath', u'flags']

class FnvRACERecord(FnvBaseRecord):
    __slots__ = []
    _Type = b'RACE'
    class RaceModel(BaseComponent):
        __slots__ = []
        modPath = CBashISTRING_GROUP(0)
        modb = CBashFLOAT32_GROUP(1)
        modt_p = CBashUINT8ARRAY_GROUP(2)

        def create_altTexture(self):
            FieldID = self._FieldID + 3
            length = _CGetFieldAttribute(self._RecordID, FieldID, 0, 0, 0, 0, 0, 0, 1)
            _CSetField(self._RecordID, FieldID, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
            return FNVAltTexture(self._RecordID, FieldID, length)
        altTextures = CBashLIST_GROUP(3, FNVAltTexture)
        altTextures_list = CBashLIST_GROUP(3, FNVAltTexture, True)
        flags = CBashGeneric_GROUP(4, c_ubyte)
        iconPath = CBashISTRING_GROUP(5)
        smallIconPath = CBashISTRING_GROUP(6)

        IsHead = CBashBasicFlag(u'flags', 0x01)
        IsTorso = CBashBasicFlag(u'flags', 0x02)
        IsRightHand = CBashBasicFlag(u'flags', 0x04)
        IsLeftHand = CBashBasicFlag(u'flags', 0x08)
        copyattrs = [u'modPath', u'modb', u'modt_p', u'altTextures_list',
                     u'flags', u'iconPath', u'smallIconPath']
        exportattrs = copyattrs[:]
        exportattrs.remove(u'modt_p')

    full = CBashSTRING(7)
    description = CBashSTRING(8)

    def create_relation(self):
        length = _CGetFieldAttribute(self._RecordID, 9, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 9, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return FNVRelation(self._RecordID, 9, length)
    relations = CBashLIST(9, FNVRelation)
    relations_list = CBashLIST(9, FNVRelation, True)

    skill1 = CBashGeneric(10, c_byte)
    skill1Boost = CBashGeneric(11, c_byte)
    skill2 = CBashGeneric(12, c_byte)
    skill2Boost = CBashGeneric(13, c_byte)
    skill3 = CBashGeneric(14, c_byte)
    skill3Boost = CBashGeneric(15, c_byte)
    skill4 = CBashGeneric(16, c_byte)
    skill4Boost = CBashGeneric(17, c_byte)
    skill5 = CBashGeneric(18, c_byte)
    skill5Boost = CBashGeneric(19, c_byte)
    skill6 = CBashGeneric(20, c_byte)
    skill6Boost = CBashGeneric(21, c_byte)
    skill7 = CBashGeneric(22, c_byte)
    skill7Boost = CBashGeneric(23, c_byte)
    unused1 = CBashUINT8ARRAY(24, 2)
    maleHeight = CBashFLOAT32(25)
    femaleHeight = CBashFLOAT32(26)
    maleWeight = CBashFLOAT32(27)
    femaleWeight = CBashFLOAT32(28)
    flags = CBashGeneric(29, c_ulong)
    older = CBashFORMID(30)
    younger = CBashFORMID(31)
    maleVoice = CBashFORMID(32)
    femaleVoice = CBashFORMID(33)
    defaultHairMale = CBashFORMID(34)
    defaultHairFemale = CBashFORMID(35)
    defaultHairMaleColor = CBashGeneric(36, c_ubyte)
    defaultHairFemaleColor = CBashGeneric(37, c_ubyte)
    mainClamp = CBashFLOAT32(38)
    faceClamp = CBashFLOAT32(39)
    attr_p = CBashUINT8ARRAY(40)
    maleHead = CBashGrouped(41, RaceModel)
    maleHead_list = CBashGrouped(41, RaceModel, True)

    maleEars = CBashGrouped(48, RaceModel)
    maleEars_list = CBashGrouped(48, RaceModel, True)

    maleMouth = CBashGrouped(55, RaceModel)
    maleMouth_list = CBashGrouped(55, RaceModel, True)

    maleTeethLower = CBashGrouped(62, RaceModel)
    maleTeethLower_list = CBashGrouped(62, RaceModel, True)

    maleTeethUpper = CBashGrouped(69, RaceModel)
    maleTeethUpper_list = CBashGrouped(69, RaceModel, True)

    maleTongue = CBashGrouped(76, RaceModel)
    maleTongue_list = CBashGrouped(76, RaceModel, True)

    maleLeftEye = CBashGrouped(83, RaceModel)
    maleLeftEye_list = CBashGrouped(83, RaceModel, True)

    maleRightEye = CBashGrouped(90, RaceModel)
    maleRightEye_list = CBashGrouped(90, RaceModel, True)

    femaleHead = CBashGrouped(97, RaceModel)
    femaleHead_list = CBashGrouped(97, RaceModel, True)

    femaleEars = CBashGrouped(104, RaceModel)
    femaleEars_list = CBashGrouped(104, RaceModel, True)

    femaleMouth = CBashGrouped(111, RaceModel)
    femaleMouth_list = CBashGrouped(111, RaceModel, True)

    femaleTeethLower = CBashGrouped(118, RaceModel)
    femaleTeethLower_list = CBashGrouped(118, RaceModel, True)

    femaleTeethUpper = CBashGrouped(125, RaceModel)
    femaleTeethUpper_list = CBashGrouped(125, RaceModel, True)

    femaleTongue = CBashGrouped(132, RaceModel)
    femaleTongue_list = CBashGrouped(132, RaceModel, True)

    femaleLeftEye = CBashGrouped(139, RaceModel)
    femaleLeftEye_list = CBashGrouped(139, RaceModel, True)

    femaleRightEye = CBashGrouped(146, RaceModel)
    femaleRightEye_list = CBashGrouped(146, RaceModel, True)

    maleUpperBody = CBashGrouped(153, RaceModel)
    maleUpperBody_list = CBashGrouped(153, RaceModel, True)

    maleLeftHand = CBashGrouped(160, RaceModel)
    maleLeftHand_list = CBashGrouped(160, RaceModel, True)

    maleRightHand = CBashGrouped(167, RaceModel)
    maleRightHand_list = CBashGrouped(167, RaceModel, True)

    maleUpperBodyTexture = CBashGrouped(174, RaceModel)
    maleUpperBodyTexture_list = CBashGrouped(174, RaceModel, True)

    femaleUpperBody = CBashGrouped(181, RaceModel)
    femaleUpperBody_list = CBashGrouped(181, RaceModel, True)

    femaleLeftHand = CBashGrouped(188, RaceModel)
    femaleLeftHand_list = CBashGrouped(188, RaceModel, True)

    femaleRightHand = CBashGrouped(195, RaceModel)
    femaleRightHand_list = CBashGrouped(195, RaceModel, True)

    femaleUpperBodyTexture = CBashGrouped(202, RaceModel)
    femaleUpperBodyTexture_list = CBashGrouped(202, RaceModel, True)

    hairs = CBashFORMIDARRAY(209)
    eyes = CBashFORMIDARRAY(210)
    maleFggs_p = CBashUINT8ARRAY(211, 200)
    maleFgga_p = CBashUINT8ARRAY(212, 120)
    maleFgts_p = CBashUINT8ARRAY(213, 200)
    maleSnam_p = CBashUINT8ARRAY(214, 2)
    femaleFggs_p = CBashUINT8ARRAY(215, 200)
    femaleFgga_p = CBashUINT8ARRAY(216, 120)
    femaleFgts_p = CBashUINT8ARRAY(217, 200)
    femaleSnam_p = CBashUINT8ARRAY(218, 2)

    IsPlayable = CBashBasicFlag(u'flags', 0x00000001)
    IsChild = CBashBasicFlag(u'flags', 0x00000004)
    copyattrs = FnvBaseRecord.baseattrs + [
        u'full', u'description', u'relations_list', u'skill1', u'skill1Boost',
        u'skill2', u'skill2Boost', u'skill3', u'skill3Boost', u'skill4',
        u'skill4Boost', u'skill5', u'skill5Boost', u'skill6', u'skill6Boost',
        u'skill7', u'skill7Boost', u'maleHeight', u'femaleHeight',
        u'maleWeight', u'femaleWeight', u'flags', u'older', u'younger',
        u'maleVoice', u'femaleVoice', u'defaultHairMale', u'defaultHairFemale',
        u'defaultHairMaleColor', u'defaultHairFemaleColor', u'mainClamp',
        u'faceClamp', u'attr_p', u'maleHead_list', u'maleEars_list',
        u'maleMouth_list', u'maleTeethLower_list', u'maleTeethUpper_list',
        u'maleTongue_list', u'maleLeftEye_list', u'maleRightEye_list',
        u'femaleHead_list', u'femaleEars_list', u'femaleMouth_list',
        u'femaleTeethLower_list', u'femaleTeethUpper_list',
        u'femaleTongue_list', u'femaleLeftEye_list', u'femaleRightEye_list',
        u'maleUpperBody_list', u'maleLeftHand_list', u'maleRightHand_list',
        u'maleUpperBodyTexture_list', u'femaleUpperBody_list',
        u'femaleLeftHand_list', u'femaleRightHand_list',
        u'femaleUpperBodyTexture_list', u'hairs', u'eyes', u'maleFggs_p',
        u'maleFgga_p', u'maleFgts_p', u'maleSnam_p', u'femaleFggs_p',
        u'femaleFgga_p', u'femaleFgts_p', u'femaleSnam_p']
    exportattrs = copyattrs[:]
    exportattrs.remove(u'attr_p')
    exportattrs.remove(u'maleFggs_p')
    exportattrs.remove(u'maleFgga_p')
    exportattrs.remove(u'maleFgts_p')
    exportattrs.remove(u'maleSnam_p')
    exportattrs.remove(u'femaleFggs_p')
    exportattrs.remove(u'femaleFgga_p')
    exportattrs.remove(u'femaleFgts_p')
    exportattrs.remove(u'femaleSnam_p')

class FnvSOUNRecord(FnvBaseRecord):
    __slots__ = []
    _Type = b'SOUN'
    boundX1 = CBashGeneric(7, c_short)
    boundY1 = CBashGeneric(8, c_short)
    boundZ1 = CBashGeneric(9, c_short)
    boundX2 = CBashGeneric(10, c_short)
    boundY2 = CBashGeneric(11, c_short)
    boundZ2 = CBashGeneric(12, c_short)
    soundPath = CBashISTRING(13)
    chance = CBashGeneric(14, c_ubyte)
    minDistance = CBashGeneric(15, c_ubyte)
    maxDistance = CBashGeneric(16, c_ubyte)
    freqAdjustment = CBashGeneric(17, c_byte)
    unused1 = CBashUINT8ARRAY(18, 1)
    flags = CBashGeneric(19, c_ulong)
    staticAtten = CBashGeneric(20, c_short)
    stopTime = CBashGeneric(21, c_ubyte)
    startTime = CBashGeneric(22, c_ubyte)
    attenCurve = CBashSINT16ARRAY(23, 5)
    reverb = CBashGeneric(24, c_short)
    priority = CBashGeneric(25, c_long)
    x = CBashGeneric(26, c_long)
    y = CBashGeneric(27, c_long)

    IsRandomFrequencyShift = CBashBasicFlag(u'flags', 0x00000001)
    IsPlayAtRandom = CBashBasicFlag(u'flags', 0x00000002)
    IsEnvironmentIgnored = CBashBasicFlag(u'flags', 0x00000004)
    IsRandomLocation = CBashBasicFlag(u'flags', 0x00000008)
    IsLoop = CBashBasicFlag(u'flags', 0x00000010)
    IsMenuSound = CBashBasicFlag(u'flags', 0x00000020)
    Is2D = CBashBasicFlag(u'flags', 0x00000040)
    Is360LFE = CBashBasicFlag(u'flags', 0x00000080)
    IsDialogueSound = CBashBasicFlag(u'flags', 0x00000100)
    IsEnvelopeFast = CBashBasicFlag(u'flags', 0x00000200)
    IsEnvelopeSlow = CBashBasicFlag(u'flags', 0x00000400)
    Is2DRadius = CBashBasicFlag(u'flags', 0x00000800)
    IsMuteWhenSubmerged = CBashBasicFlag(u'flags', 0x00001000)
    copyattrs = FnvBaseRecord.baseattrs + [
        u'boundX1', u'boundY1', u'boundZ1', u'boundX2', u'boundY2', u'boundZ2',
        u'soundPath', u'chance', u'minDistance', u'maxDistance',
        u'freqAdjustment', u'unused1', u'flags', u'staticAtten', u'stopTime',
        u'startTime', u'attenCurve', u'reverb', u'priority', u'x', u'y']
    exportattrs = copyattrs[:]
    exportattrs.remove(u'unused1')

class FnvASPCRecord(FnvBaseRecord):
    __slots__ = []
    _Type = b'ASPC'
    boundX1 = CBashGeneric(7, c_short)
    boundY1 = CBashGeneric(8, c_short)
    boundZ1 = CBashGeneric(9, c_short)
    boundX2 = CBashGeneric(10, c_short)
    boundY2 = CBashGeneric(11, c_short)
    boundZ2 = CBashGeneric(12, c_short)
    dawnOrDefaultLoop = CBashFORMID(13)
    afternoon = CBashFORMID(14)
    dusk = CBashFORMID(15)
    night = CBashFORMID(16)
    walla = CBashFORMID(17)
    wallaTriggerCount = CBashGeneric(18, c_ulong)
    regionSound = CBashFORMID(19)
    environmentType = CBashGeneric(20, c_ulong)
    spaceType = CBashGeneric(21, c_ulong)

    IsEnvironmentNone = CBashBasicType(u'environmentType', 0, u'IsEnvironmentDefault')
    IsEnvironmentDefault = CBashBasicType(u'environmentType', 1, u'IsEnvironmentNone')
    IsEnvironmentGeneric = CBashBasicType(u'environmentType', 2, u'IsEnvironmentNone')
    IsEnvironmentPaddedCell = CBashBasicType(u'environmentType', 3, u'IsEnvironmentNone')
    IsEnvironmentRoom = CBashBasicType(u'environmentType', 4, u'IsEnvironmentNone')
    IsEnvironmentBathroom = CBashBasicType(u'environmentType', 5, u'IsEnvironmentNone')
    IsEnvironmentLivingroom = CBashBasicType(u'environmentType', 6, u'IsEnvironmentNone')
    IsEnvironmentStoneRoom = CBashBasicType(u'environmentType', 7, u'IsEnvironmentNone')
    IsEnvironmentAuditorium = CBashBasicType(u'environmentType', 8, u'IsEnvironmentNone')
    IsEnvironmentConcerthall = CBashBasicType(u'environmentType', 9, u'IsEnvironmentNone')
    IsEnvironmentCave = CBashBasicType(u'environmentType', 10, u'IsEnvironmentNone')
    IsEnvironmentArena = CBashBasicType(u'environmentType', 11, u'IsEnvironmentNone')
    IsEnvironmentHangar = CBashBasicType(u'environmentType', 12, u'IsEnvironmentNone')
    IsEnvironmentCarpetedHallway = CBashBasicType(u'environmentType', 13, u'IsEnvironmentNone')
    IsEnvironmentHallway = CBashBasicType(u'environmentType', 14, u'IsEnvironmentNone')
    IsEnvironmentStoneCorridor = CBashBasicType(u'environmentType', 15, u'IsEnvironmentNone')
    IsEnvironmentAlley = CBashBasicType(u'environmentType', 16, u'IsEnvironmentNone')
    IsEnvironmentForest = CBashBasicType(u'environmentType', 17, u'IsEnvironmentNone')
    IsEnvironmentCity = CBashBasicType(u'environmentType', 18, u'IsEnvironmentNone')
    IsEnvironmentMountains = CBashBasicType(u'environmentType', 19, u'IsEnvironmentNone')
    IsEnvironmentQuarry = CBashBasicType(u'environmentType', 20, u'IsEnvironmentNone')
    IsEnvironmentPlain = CBashBasicType(u'environmentType', 21, u'IsEnvironmentNone')
    IsEnvironmentParkinglot = CBashBasicType(u'environmentType', 22, u'IsEnvironmentNone')
    IsEnvironmentSewerpipe = CBashBasicType(u'environmentType', 23, u'IsEnvironmentNone')
    IsEnvironmentUnderwater = CBashBasicType(u'environmentType', 24, u'IsEnvironmentNone')
    IsEnvironmentSmallRoom = CBashBasicType(u'environmentType', 25, u'IsEnvironmentNone')
    IsEnvironmentMediumRoom = CBashBasicType(u'environmentType', 26, u'IsEnvironmentNone')
    IsEnvironmentLargeRoom = CBashBasicType(u'environmentType', 27, u'IsEnvironmentNone')
    IsEnvironmentMediumHall = CBashBasicType(u'environmentType', 28, u'IsEnvironmentNone')
    IsEnvironmentLargeHall = CBashBasicType(u'environmentType', 29, u'IsEnvironmentNone')
    IsEnvironmentPlate = CBashBasicType(u'environmentType', 30, u'IsEnvironmentNone')

    IsSpaceExterior = CBashBasicType(u'spaceType', 0, u'IsSpaceInterior')
    IsSpaceInterior = CBashBasicType(u'spaceType', 1, u'IsSpaceExterior')
    exportattrs = copyattrs = FnvBaseRecord.baseattrs + [u'boundX1', u'boundY1', u'boundZ1',
                                                         u'boundX2', u'boundY2', u'boundZ2',
                                                         u'dawnOrDefaultLoop', u'afternoon',
                                                         u'dusk', u'night', u'walla',
                                                         u'wallaTriggerCount', u'regionSound',
                                                         u'environmentType', u'spaceType']

class FnvMGEFRecord(FnvBaseRecord):
    __slots__ = []
    _Type = b'MGEF'
    full = CBashSTRING(7)
    description = CBashSTRING(8)
    iconPath = CBashISTRING(9)
    smallIconPath = CBashISTRING(10)
    modPath = CBashISTRING(11)
    modb = CBashFLOAT32(12)
    modt_p = CBashUINT8ARRAY(13)

    def create_altTexture(self):
        length = _CGetFieldAttribute(self._RecordID, 14, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 14, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return FNVAltTexture(self._RecordID, 14, length)
    altTextures = CBashLIST(14, FNVAltTexture)
    altTextures_list = CBashLIST(14, FNVAltTexture, True)

    modelFlags = CBashGeneric(15, c_ubyte)
    flags = CBashGeneric(16, c_ulong)
    baseCostUnused = CBashFLOAT32(17)
    associated = CBashFORMID(18)
    schoolUnused = CBashGeneric(19, c_long)
    resistType = CBashGeneric(20, c_long)
    numCounters = CBashGeneric(21, c_ushort)
    unused1 = CBashUINT8ARRAY(22, 2)
    light = CBashFORMID(23)
    projectileSpeed = CBashFLOAT32(24)
    effectShader = CBashFORMID(25)
    displayShader = CBashFORMID(26)
    effectSound = CBashFORMID(27)
    boltSound = CBashFORMID(28)
    hitSound = CBashFORMID(29)
    areaSound = CBashFORMID(30)
    cefEnchantmentUnused = CBashFLOAT32(31)
    cefBarterUnused = CBashFLOAT32(32)
    archType = CBashGeneric(33, c_ulong)
    actorValue = CBashGeneric(34, c_long)

    IsHostile = CBashBasicFlag(u'flags', 0x00000001)
    IsRecover = CBashBasicFlag(u'flags', 0x00000002)
    IsDetrimental = CBashBasicFlag(u'flags', 0x00000004)
    IsSelf = CBashBasicFlag(u'flags', 0x00000010)
    IsTouch = CBashBasicFlag(u'flags', 0x00000020)
    IsTarget = CBashBasicFlag(u'flags', 0x00000040)
    IsNoDuration = CBashBasicFlag(u'flags', 0x00000080)
    IsNoMagnitude = CBashBasicFlag(u'flags', 0x00000100)
    IsNoArea = CBashBasicFlag(u'flags', 0x00000200)
    IsFXPersist = CBashBasicFlag(u'flags', 0x00000400)
    IsGoryVisuals = CBashBasicFlag(u'flags', 0x00001000)
    IsDisplayNameOnly = CBashBasicFlag(u'flags', 0x00002000)
    IsRadioBroadcast = CBashBasicFlag(u'flags', 0x00008000)
    IsUseSkill = CBashBasicFlag(u'flags', 0x00080000)
    IsUseAttr = CBashBasicFlag(u'flags', 0x00100000)
    IsPainless = CBashBasicFlag(u'flags', 0x01000000)
    IsSprayType = CBashBasicFlag(u'flags', 0x02000000)
    IsBoltType = CBashBasicFlag(u'flags', 0x04000000)
    IsFogType = CBashBasicFlag(u'flags', 0x06000000)
    IsNoHitEffect = CBashBasicFlag(u'flags', 0x08000000)
    IsPersistOnDeath = CBashBasicFlag(u'flags', 0x10000000)
    IsUnknown1 = CBashBasicFlag(u'flags', 0x20000000)

    IsHead = CBashBasicFlag(u'modelFlags', 0x01)
    IsTorso = CBashBasicFlag(u'modelFlags', 0x02)
    IsRightHand = CBashBasicFlag(u'modelFlags', 0x04)
    IsLeftHand = CBashBasicFlag(u'modelFlags', 0x08)

    IsValueModifier = CBashBasicType(u'archType', 0, u'IsScript')
    IsScript = CBashBasicType(u'archType', 1, u'IsValueModifier')
    IsDispel = CBashBasicType(u'archType', 2, u'IsValueModifier')
    IsCureDisease = CBashBasicType(u'archType', 3, u'IsValueModifier')
    IsInvisibility = CBashBasicType(u'archType', 11, u'IsValueModifier')
    IsChameleon = CBashBasicType(u'archType', 12, u'IsValueModifier')
    IsLight = CBashBasicType(u'archType', 13, u'IsValueModifier')
    IsLock = CBashBasicType(u'archType', 16, u'IsValueModifier')
    IsOpen = CBashBasicType(u'archType', 17, u'IsValueModifier')
    IsBoundItem = CBashBasicType(u'archType', 18, u'IsValueModifier')
    IsSummonCreature = CBashBasicType(u'archType', 19, u'IsValueModifier')
    IsParalysis = CBashBasicType(u'archType', 24, u'IsValueModifier')
    IsCureParalysis = CBashBasicType(u'archType', 30, u'IsValueModifier')
    IsCureAddiction = CBashBasicType(u'archType', 31, u'IsValueModifier')
    IsCurePoison = CBashBasicType(u'archType', 32, u'IsValueModifier')
    IsConcussion = CBashBasicType(u'archType', 33, u'IsValueModifier')
    IsValueAndParts = CBashBasicType(u'archType', 34, u'IsValueModifier')
    IsLimbCondition = CBashBasicType(u'archType', 35, u'IsValueModifier')
    IsTurbo = CBashBasicType(u'archType', 36, u'IsValueModifier')
    copyattrs = FnvBaseRecord.baseattrs + [
        u'full', u'description', u'iconPath', u'smallIconPath', u'modPath',
        u'modb', u'modt_p', u'altTextures_list', u'modelFlags', u'flags',
        u'baseCostUnused', u'associated', u'schoolUnused', u'resistType',
        u'numCounters', u'unused1', u'light', u'projectileSpeed',
        u'effectShader', u'displayShader', u'effectSound', u'boltSound',
        u'hitSound', u'areaSound', u'cefEnchantmentUnused', u'cefBarterUnused',
        u'archType', u'actorValue']
    exportattrs = copyattrs[:]
    exportattrs.remove(u'modt_p')
    exportattrs.remove(u'baseCostUnused')
    exportattrs.remove(u'schoolUnused')
    exportattrs.remove(u'unused1')
    exportattrs.remove(u'cefEnchantmentUnused')
    exportattrs.remove(u'cefBarterUnused')

class FnvSCPTRecord(FnvBaseRecord):
    __slots__ = []
    _Type = b'SCPT'
    unused1 = CBashUINT8ARRAY(7, 4)
    numRefs = CBashGeneric(8, c_ulong)
    compiledSize = CBashGeneric(9, c_ulong)
    lastIndex = CBashGeneric(10, c_ulong)
    scriptType = CBashGeneric(11, c_ushort)
    scriptFlags = CBashGeneric(12, c_ushort)
    compiled_p = CBashUINT8ARRAY(13)
    scriptText = CBashISTRING(14)

    def create_var(self):
        length = _CGetFieldAttribute(self._RecordID, 15, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 15, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return Var(self._RecordID, 15, length)
    vars = CBashLIST(15, Var)
    vars_list = CBashLIST(15, Var, True)

    references = CBashFORMID_OR_UINT32_ARRAY(16)

    IsEnabled = CBashBasicFlag(u'scriptFlags', 0x0001)

    IsObject = CBashBasicType(u'scriptType', 0x0000, u'IsQuest')
    IsQuest = CBashBasicType(u'scriptType', 0x0001, u'IsObject')
    IsEffect = CBashBasicType(u'scriptType', 0x0100, u'IsObject')
    copyattrs = FnvBaseRecord.baseattrs + [u'unused1', u'numRefs', u'compiledSize',
                                           u'lastIndex', u'scriptType', u'scriptFlags',
                                           u'compiled_p', u'scriptText',
                                           u'vars_list', u'references']
    exportattrs = copyattrs[:]
    exportattrs.remove(u'unused1')
    exportattrs.remove(u'compiled_p')

class FnvLTEXRecord(FnvBaseRecord):
    __slots__ = []
    _Type = b'LTEX'
    iconPath = CBashISTRING(7)
    smallIconPath = CBashISTRING(8)
    texture = CBashFORMID(9)
    types = CBashGeneric(10, c_ubyte)
    friction = CBashGeneric(11, c_ubyte)
    restitution = CBashGeneric(12, c_ubyte)
    specularExponent = CBashGeneric(13, c_ubyte)
    grasses = CBashFORMIDARRAY(14)

    IsStone = CBashBasicType(u'types', 0, u'IsCloth')
    IsCloth = CBashBasicType(u'types', 1, u'IsStone')
    IsDirt = CBashBasicType(u'types', 2, u'IsStone')
    IsGlass = CBashBasicType(u'types', 3, u'IsStone')
    IsGrass = CBashBasicType(u'types', 4, u'IsStone')
    IsMetal = CBashBasicType(u'types', 5, u'IsStone')
    IsOrganic = CBashBasicType(u'types', 6, u'IsStone')
    IsSkin = CBashBasicType(u'types', 7, u'IsStone')
    IsWater = CBashBasicType(u'types', 8, u'IsStone')
    IsWood = CBashBasicType(u'types', 9, u'IsStone')
    IsHeavyStone = CBashBasicType(u'types', 10, u'IsStone')
    IsHeavyMetal = CBashBasicType(u'types', 11, u'IsStone')
    IsHeavyWood = CBashBasicType(u'types', 12, u'IsStone')
    IsChain = CBashBasicType(u'types', 13, u'IsStone')
    IsSnow = CBashBasicType(u'types', 14, u'IsStone')
    IsElevator = CBashBasicType(u'types', 15, u'IsStone')
    IsHollowMetal = CBashBasicType(u'types', 16, u'IsStone')
    IsSheetMetal = CBashBasicType(u'types', 17, u'IsStone')
    IsSand = CBashBasicType(u'types', 18, u'IsStone')
    IsBrokenConcrete = CBashBasicType(u'types', 19, u'IsStone')
    IsVehicleBody = CBashBasicType(u'types', 20, u'IsStone')
    IsVehiclePartSolid = CBashBasicType(u'types', 21, u'IsStone')
    IsVehiclePartHollow = CBashBasicType(u'types', 22, u'IsStone')
    IsBarrel = CBashBasicType(u'types', 23, u'IsStone')
    IsBottle = CBashBasicType(u'types', 24, u'IsStone')
    IsSodaCan = CBashBasicType(u'types', 25, u'IsStone')
    IsPistol = CBashBasicType(u'types', 26, u'IsStone')
    IsRifle = CBashBasicType(u'types', 27, u'IsStone')
    IsShoppingCart = CBashBasicType(u'types', 28, u'IsStone')
    IsLunchBox = CBashBasicType(u'types', 29, u'IsStone')
    IsBabyRattle = CBashBasicType(u'types', 30, u'IsStone')
    IsRubberBall = CBashBasicType(u'types', 31, u'IsStone')
    exportattrs = copyattrs = FnvBaseRecord.baseattrs + [u'iconPath', u'smallIconPath', u'texture',
                                                         u'types', u'friction', u'restitution',
                                                         u'specularExponent', u'grasses']

class FnvENCHRecord(FnvBaseRecord):
    __slots__ = []
    _Type = b'ENCH'
    full = CBashSTRING(7)
    itemType = CBashGeneric(8, c_ulong)
    chargeAmountUnused = CBashGeneric(9, c_ulong)
    enchantCostUnused = CBashGeneric(10, c_ulong)
    flags = CBashGeneric(11, c_ubyte)
    unused1 = CBashUINT8ARRAY(12, 3)

    def create_effect(self):
        length = _CGetFieldAttribute(self._RecordID, 13, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 13, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return FNVEffect(self._RecordID, 13, length)
    effects = CBashLIST(13, FNVEffect)
    effects_list = CBashLIST(13, FNVEffect, True)


    IsNoAutoCalc = CBashBasicFlag(u'flags', 0x01)
    IsAutoCalc = CBashInvertedFlag(u'IsNoAutoCalc')
    IsHideEffect = CBashBasicFlag(u'flags', 0x04)
    IsWeapon = CBashBasicType(u'itemType', 2, u'IsApparel')
    IsApparel = CBashBasicType(u'itemType', 3, u'IsWeapon')
    copyattrs = FnvBaseRecord.baseattrs + [u'full', u'itemType', u'chargeAmountUnused',
                                           u'enchantCostUnused', u'flags', u'effects_list']
    exportattrs = copyattrs[:]
    exportattrs.remove(u'chargeAmountUnused')
    exportattrs.remove(u'enchantCostUnused')

class FnvSPELRecord(FnvBaseRecord):
    __slots__ = []
    _Type = b'SPEL'
    full = CBashSTRING(7)
    spellType = CBashGeneric(8, c_ulong)
    costUnused = CBashGeneric(9, c_ulong)
    levelTypeUnused = CBashGeneric(10, c_ulong)
    flags = CBashGeneric(11, c_ubyte)
    unused1 = CBashUINT8ARRAY(12, 3)

    def create_effect(self):
        length = _CGetFieldAttribute(self._RecordID, 13, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 13, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return FNVEffect(self._RecordID, 13, length)
    effects = CBashLIST(13, FNVEffect)
    effects_list = CBashLIST(13, FNVEffect, True)


    IsManualCost = CBashBasicFlag(u'flags', 0x01)
    IsStartSpell = CBashBasicFlag(u'flags', 0x04)
    IsSilenceImmune = CBashBasicFlag(u'flags', 0x0A)
    IsAreaEffectIgnoresLOS = CBashBasicFlag(u'flags', 0x10)
    IsAEIgnoresLOS = CBashAlias(u'IsAreaEffectIgnoresLOS')
    IsScriptAlwaysApplies = CBashBasicFlag(u'flags', 0x20)
    IsDisallowAbsorbReflect = CBashBasicFlag(u'flags', 0x40)
    IsDisallowAbsorb = CBashAlias(u'IsDisallowAbsorbReflect')
    IsDisallowReflect = CBashAlias(u'IsDisallowAbsorbReflect')
    IsTouchExplodesWOTarget = CBashBasicFlag(u'flags', 0x80)
    IsTouchExplodes = CBashAlias(u'IsTouchExplodesWOTarget')

    IsActorEffect = CBashBasicType(u'spellType', 0, u'IsDisease')
    IsDisease = CBashBasicType(u'spellType', 1, u'IsActorEffect')
    IsPower = CBashBasicType(u'spellType', 2, u'IsActorEffect')
    IsLesserPower = CBashBasicType(u'spellType', 3, u'IsActorEffect')
    IsAbility = CBashBasicType(u'spellType', 4, u'IsActorEffect')
    IsPoison = CBashBasicType(u'spellType', 5, u'IsActorEffect')
    IsAddiction = CBashBasicType(u'spellType', 10, u'IsActorEffect')
    copyattrs = FnvBaseRecord.baseattrs + [u'full', u'spellType', u'costUnused',
                                           u'levelTypeUnused', u'flags', u'effects_list']
    exportattrs = copyattrs[:]
    exportattrs.remove(u'costUnused')
    exportattrs.remove(u'levelTypeUnused')

class FnvACTIRecord(FnvBaseRecord):
    __slots__ = []
    _Type = b'ACTI'
    boundX1 = CBashGeneric(7, c_short)
    boundY1 = CBashGeneric(8, c_short)
    boundZ1 = CBashGeneric(9, c_short)
    boundX2 = CBashGeneric(10, c_short)
    boundY2 = CBashGeneric(11, c_short)
    boundZ2 = CBashGeneric(12, c_short)
    full = CBashSTRING(13)
    modPath = CBashISTRING(14)
    modb = CBashFLOAT32(15)
    modt_p = CBashUINT8ARRAY(16)

    def create_altTexture(self):
        length = _CGetFieldAttribute(self._RecordID, 17, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 17, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return FNVAltTexture(self._RecordID, 17, length)
    altTextures = CBashLIST(17, FNVAltTexture)
    altTextures_list = CBashLIST(17, FNVAltTexture, True)

    modelFlags = CBashGeneric(18, c_ubyte)
    script = CBashFORMID(19)
    destructable = CBashGrouped(20, FNVDestructable)
    destructable_list = CBashGrouped(20, FNVDestructable, True)

    loopSound = CBashFORMID(25)
    actSound = CBashFORMID(26)
    radioTemplate = CBashFORMID(27)
    radioStation = CBashFORMID(28)
    water = CBashFORMID(29)
    prompt = CBashSTRING(30)

    IsHead = CBashBasicFlag(u'modelFlags', 0x01)
    IsTorso = CBashBasicFlag(u'modelFlags', 0x02)
    IsRightHand = CBashBasicFlag(u'modelFlags', 0x04)
    IsLeftHand = CBashBasicFlag(u'modelFlags', 0x08)
    copyattrs = FnvBaseRecord.baseattrs + [u'boundX1', u'boundY1', u'boundZ1',
                                           u'boundX2', u'boundY2', u'boundZ2',
                                           u'full', u'modPath', u'modb', u'modt_p',
                                           u'altTextures_list', u'modelFlags',
                                           u'script', u'destructable_list',
                                           u'loopSound', u'actSound',
                                           u'radioTemplate', u'radioStation',
                                           u'water', u'prompt']
    exportattrs = copyattrs[:]
    exportattrs.remove(u'modt_p')

class FnvTACTRecord(FnvBaseRecord):
    __slots__ = []
    _Type = b'TACT'
    boundX1 = CBashGeneric(7, c_short)
    boundY1 = CBashGeneric(8, c_short)
    boundZ1 = CBashGeneric(9, c_short)
    boundX2 = CBashGeneric(10, c_short)
    boundY2 = CBashGeneric(11, c_short)
    boundZ2 = CBashGeneric(12, c_short)
    full = CBashSTRING(13)
    modPath = CBashISTRING(14)
    modb = CBashFLOAT32(15)
    modt_p = CBashUINT8ARRAY(16)

    def create_altTexture(self):
        length = _CGetFieldAttribute(self._RecordID, 17, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 17, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return FNVAltTexture(self._RecordID, 17, length)
    altTextures = CBashLIST(17, FNVAltTexture)
    altTextures_list = CBashLIST(17, FNVAltTexture, True)

    modelFlags = CBashGeneric(18, c_ubyte)
    script = CBashFORMID(19)
    destructable = CBashGrouped(20, FNVDestructable)
    destructable_list = CBashGrouped(20, FNVDestructable, True)

    loopSound = CBashFORMID(25)
    voice = CBashFORMID(26)
    radioTemplate = CBashFORMID(27)

    IsHead = CBashBasicFlag(u'modelFlags', 0x01)
    IsTorso = CBashBasicFlag(u'modelFlags', 0x02)
    IsRightHand = CBashBasicFlag(u'modelFlags', 0x04)
    IsLeftHand = CBashBasicFlag(u'modelFlags', 0x08)
    copyattrs = FnvBaseRecord.baseattrs + [u'boundX1', u'boundY1', u'boundZ1',
                                           u'boundX2', u'boundY2', u'boundZ2',
                                           u'full', u'modPath', u'modb', u'modt_p',
                                           u'altTextures_list', u'modelFlags',
                                           u'script', u'destructable_list',
                                           u'loopSound', u'voice', u'radioTemplate']
    exportattrs = copyattrs[:]
    exportattrs.remove(u'modt_p')

class FnvTERMRecord(FnvBaseRecord):
    __slots__ = []
    _Type = b'TERM'
    class Menu(ListComponent):
        __slots__ = []
        text = CBashSTRING_LIST(1)
        resultText = CBashSTRING_LIST(2)
        flags = CBashGeneric_LIST(3, c_ubyte)
        displayNote = CBashFORMID_LIST(4)
        subMenu = CBashFORMID_LIST(5)
        unused1 = CBashUINT8ARRAY_LIST(6, 4)
        numRefs = CBashGeneric_LIST(7, c_ulong)
        compiledSize = CBashGeneric_LIST(8, c_ulong)
        lastIndex = CBashGeneric_LIST(9, c_ulong)
        scriptType = CBashGeneric_LIST(10, c_ushort)
        scriptFlags = CBashGeneric_LIST(11, c_ushort)
        compiled_p = CBashUINT8ARRAY_LIST(12)
        scriptText = CBashISTRING_LIST(13)

        def create_var(self):
            length = _CGetFieldAttribute(self._RecordID, self._FieldID, self._ListIndex, 14, 0, 0, 0, 0, 1)
            _CSetField(self._RecordID, self._FieldID, self._ListIndex, 14, 0, 0, 0, 0, 0, c_ulong(length + 1))
            return VarX2(self._RecordID, self._FieldID, self._ListIndex, 14, length)
        vars = CBashLIST_LIST(14, VarX2)
        vars_list = CBashLIST_LIST(14, VarX2, True)


        references = CBashFORMID_OR_UINT32_ARRAY_LIST(15)
        def create_condition(self):
            length = _CGetFieldAttribute(self._RecordID, self._FieldID, self._ListIndex, 16, 0, 0, 0, 0, 1)
            _CSetField(self._RecordID, self._FieldID, self._ListIndex, 16, 0, 0, 0, 0, 0, c_ulong(length + 1))
            return FNVConditionX2(self._RecordID, self._FieldID, self._ListIndex, 16, length)
        conditions = CBashLIST_LIST(16, FNVConditionX2)
        conditions_list = CBashLIST_LIST(16, FNVConditionX2, True)


        IsAddNote = CBashBasicFlag(u'flags', 0x01)
        IsForceRedraw = CBashBasicFlag(u'flags', 0x02)

        IsEnabled = CBashBasicFlag(u'scriptFlags', 0x0001)

        IsObject = CBashBasicType(u'scriptType', 0x0000, u'IsQuest')
        IsQuest = CBashBasicType(u'scriptType', 0x0001, u'IsObject')
        IsEffect = CBashBasicType(u'scriptType', 0x0100, u'IsObject')
        copyattrs = [u'text', u'resultText', u'flags',
                     u'displayNote', u'subMenu', u'numRefs',
                     u'compiledSize', u'lastIndex',
                     u'scriptType', u'scriptFlags', u'compiled_p',
                     u'scriptText', u'vars_list',
                     u'references', u'conditions_list']
        exportattrs = copyattrs[:]
        exportattrs.remove(u'compiled_p')

    boundX1 = CBashGeneric(7, c_short)
    boundY1 = CBashGeneric(8, c_short)
    boundZ1 = CBashGeneric(9, c_short)
    boundX2 = CBashGeneric(10, c_short)
    boundY2 = CBashGeneric(11, c_short)
    boundZ2 = CBashGeneric(12, c_short)
    full = CBashSTRING(13)
    modPath = CBashISTRING(14)
    modb = CBashFLOAT32(15)
    modt_p = CBashUINT8ARRAY(16)

    def create_altTexture(self):
        length = _CGetFieldAttribute(self._RecordID, 17, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 17, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return FNVAltTexture(self._RecordID, 17, length)
    altTextures = CBashLIST(17, FNVAltTexture)
    altTextures_list = CBashLIST(17, FNVAltTexture, True)

    modelFlags = CBashGeneric(18, c_ubyte)
    script = CBashFORMID(19)
    destructable = CBashGrouped(20, FNVDestructable)
    destructable_list = CBashGrouped(20, FNVDestructable, True)

    description = CBashSTRING(25)
    loopSound = CBashFORMID(26)
    passNote = CBashFORMID(27)
    difficultyType = CBashGeneric(28, c_ubyte)
    flags = CBashGeneric(29, c_ubyte)
    serverType = CBashGeneric(30, c_ubyte)
    unused1 = CBashUINT8ARRAY(31, 1)

    def create_menu(self):
        length = _CGetFieldAttribute(self._RecordID, 32, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 32, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return self.Menu(self._RecordID, 32, length)
    menus = CBashLIST(32, Menu)
    menus_list = CBashLIST(32, Menu, True)


    IsVeryEasy = CBashBasicType(u'difficultyType', 0, u'IsEasy')
    IsEasy = CBashBasicType(u'difficultyType', 1, u'IsVeryEasy')
    IsAverage = CBashBasicType(u'difficultyType', 2, u'IsVeryEasy')
    IsHard = CBashBasicType(u'difficultyType', 3, u'IsVeryEasy')
    IsVeryHard = CBashBasicType(u'difficultyType', 4, u'IsVeryEasy')
    IsRequiresKey = CBashBasicType(u'difficultyType', 5, u'IsVeryEasy')

    IsLeveled = CBashBasicFlag(u'flags', 0x01)
    IsUnlocked = CBashBasicFlag(u'flags', 0x02)
    IsAlternateColors = CBashBasicFlag(u'flags', 0x04)
    IsHideWelcomeTextWhenDisplayingImage = CBashBasicFlag(u'flags', 0x08)

    IsHead = CBashBasicFlag(u'modelFlags', 0x01)
    IsTorso = CBashBasicFlag(u'modelFlags', 0x02)
    IsRightHand = CBashBasicFlag(u'modelFlags', 0x04)
    IsLeftHand = CBashBasicFlag(u'modelFlags', 0x08)

    IsServer1 = CBashBasicType(u'serverType', 0, u'IsServer2')
    IsServer2 = CBashBasicType(u'serverType', 1, u'IsServer1')
    IsServer3 = CBashBasicType(u'serverType', 2, u'IsServer1')
    IsServer4 = CBashBasicType(u'serverType', 3, u'IsServer1')
    IsServer5 = CBashBasicType(u'serverType', 4, u'IsServer1')
    IsServer6 = CBashBasicType(u'serverType', 5, u'IsServer1')
    IsServer7 = CBashBasicType(u'serverType', 6, u'IsServer1')
    IsServer8 = CBashBasicType(u'serverType', 7, u'IsServer1')
    IsServer9 = CBashBasicType(u'serverType', 8, u'IsServer1')
    IsServer10 = CBashBasicType(u'serverType', 9, u'IsServer1')
    copyattrs = FnvBaseRecord.baseattrs + [u'boundX1', u'boundY1', u'boundZ1',
                                           u'boundX2', u'boundY2', u'boundZ2',
                                           u'full', u'modPath', u'modb', u'modt_p',
                                           u'altTextures_list', u'modelFlags',
                                           u'script', u'destructable_list',
                                           u'description', u'loopSound',
                                           u'passNote', u'difficultyType',
                                           u'flags', u'serverType', u'menus_list']
    exportattrs = copyattrs[:]
    exportattrs.remove(u'modt_p')

class FnvARMORecord(FnvBaseRecord):
    __slots__ = []
    _Type = b'ARMO'
    class BipedModel(BaseComponent):
        __slots__ = []
        modPath = CBashISTRING_GROUP(0)
        modt_p = CBashUINT8ARRAY_GROUP(1)

        def create_altTexture(self):
            FieldID = self._FieldID + 2
            length = _CGetFieldAttribute(self._RecordID, FieldID, 0, 0, 0, 0, 0, 0, 1)
            _CSetField(self._RecordID, FieldID, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
            return FNVAltTexture(self._RecordID, FieldID, length)
        altTextures = CBashLIST_GROUP(2, FNVAltTexture)
        altTextures_list = CBashLIST_GROUP(2, FNVAltTexture, True)
        flags = CBashGeneric_GROUP(3, c_ubyte)

        IsHead = CBashBasicFlag(u'flags', 0x01)
        IsTorso = CBashBasicFlag(u'flags', 0x02)
        IsRightHand = CBashBasicFlag(u'flags', 0x04)
        IsLeftHand = CBashBasicFlag(u'flags', 0x08)
        copyattrs = [u'modPath', u'modt_p', u'altTextures_list', u'flags']
        exportattrs = copyattrs[:]
        exportattrs.remove(u'modt_p')

    class Sound(ListComponent):
        __slots__ = []
        sound = CBashFORMID_LIST(1)
        chance = CBashGeneric_LIST(2, c_ubyte)
        unused1 = CBashUINT8ARRAY_LIST(3, 3)
        type = CBashGeneric_LIST(4, c_ulong)
        IsWalk = CBashBasicType(u'type', 17, u'IsSneak')
        IsSneak = CBashBasicType(u'type', 18, u'IsWalk')
        IsRun = CBashBasicType(u'type', 19, u'IsWalk')
        IsSneakArmor = CBashBasicType(u'type', 20, u'IsWalk')
        IsRunArmor = CBashBasicType(u'type', 21, u'IsWalk')
        IsWalkArmor = CBashBasicType(u'type', 22, u'IsWalk')
        exportattrs = copyattrs = [u'sound', u'chance', u'type']

    boundX1 = CBashGeneric(7, c_short)
    boundY1 = CBashGeneric(8, c_short)
    boundZ1 = CBashGeneric(9, c_short)
    boundX2 = CBashGeneric(10, c_short)
    boundY2 = CBashGeneric(11, c_short)
    boundZ2 = CBashGeneric(12, c_short)
    full = CBashSTRING(13)
    script = CBashFORMID(14)
    effect = CBashFORMID(15)
    flags = CBashGeneric(16, c_ulong)
    extraFlags = CBashGeneric(17, c_ubyte)
    unused1 = CBashUINT8ARRAY(18, 3)
    male = CBashGrouped(19, BipedModel)
    male_list = CBashGrouped(19, BipedModel, True)

    maleWorld = CBashGrouped(23, WorldModel)
    maleWorld_list = CBashGrouped(23, WorldModel, True)

    maleIconPath = CBashISTRING(26)
    maleSmallIconPath = CBashISTRING(27)
    female = CBashGrouped(28, BipedModel)
    female_list = CBashGrouped(28, BipedModel, True)

    femaleWorld = CBashGrouped(32, WorldModel)
    femaleWorld_list = CBashGrouped(32, WorldModel, True)

    femaleIconPath = CBashISTRING(35)
    femaleSmallIconPath = CBashISTRING(36)
    ragdollTemplatePath = CBashISTRING(37)
    repairList = CBashFORMID(38)
    modelList = CBashFORMID(39)
    equipmentType = CBashGeneric(40, c_long)
    pickupSound = CBashFORMID(41)
    dropSound = CBashFORMID(42)
    value = CBashGeneric(43, c_long)
    health = CBashGeneric(44, c_long)
    weight = CBashFLOAT32(45)
    AR = CBashGeneric(46, c_short)
    voiceFlags = CBashGeneric(47, c_ushort)
    DT = CBashFLOAT32(48)
    unknown1 = CBashUINT8ARRAY(49, 4)
    overrideSounds = CBashGeneric(50, c_ulong)
    def create_sound(self):
        length = _CGetFieldAttribute(self._RecordID, 51, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 51, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return self.Sound(self._RecordID, 51, length)
    sounds = CBashLIST(51, Sound)
    sounds_list = CBashLIST(51, Sound, True)

    soundsTemplate = CBashFORMID(52)

    IsHead = CBashBasicFlag(u'flags', 0x00000001)
    IsHair = CBashBasicFlag(u'flags', 0x00000002)
    IsUpperBody = CBashBasicFlag(u'flags', 0x00000004)
    IsLeftHand = CBashBasicFlag(u'flags', 0x00000008)
    IsRightHand = CBashBasicFlag(u'flags', 0x00000010)
    IsWeapon = CBashBasicFlag(u'flags', 0x00000020)
    IsPipBoy = CBashBasicFlag(u'flags', 0x00000040)
    IsBackpack = CBashBasicFlag(u'flags', 0x00000080)
    IsNecklace = CBashBasicFlag(u'flags', 0x00000100)
    IsHeadband = CBashBasicFlag(u'flags', 0x00000200)
    IsHat = CBashBasicFlag(u'flags', 0x00000400)
    IsEyeGlasses = CBashBasicFlag(u'flags', 0x00000800)
    IsNoseRing = CBashBasicFlag(u'flags', 0x00001000)
    IsEarrings = CBashBasicFlag(u'flags', 0x00002000)
    IsMask = CBashBasicFlag(u'flags', 0x00004000)
    IsChoker = CBashBasicFlag(u'flags', 0x00008000)
    IsMouthObject = CBashBasicFlag(u'flags', 0x00010000)
    IsBodyAddon1 = CBashBasicFlag(u'flags', 0x00020000)
    IsBodyAddon2 = CBashBasicFlag(u'flags', 0x00040000)
    IsBodyAddon3 = CBashBasicFlag(u'flags', 0x00080000)

    IsUnknown1 = CBashBasicFlag(u'extraFlags', 0x0001)
    IsUnknown2 = CBashBasicFlag(u'extraFlags', 0x0002)
    IsHasBackpack = CBashBasicFlag(u'extraFlags', 0x0004)
    IsMedium = CBashBasicFlag(u'extraFlags', 0x0008)
    IsUnknown3 = CBashBasicFlag(u'extraFlags', 0x0010)
    IsPowerArmor = CBashBasicFlag(u'extraFlags', 0x0020)
    IsNonPlayable = CBashBasicFlag(u'extraFlags', 0x0040)
    IsHeavy = CBashBasicFlag(u'extraFlags', 0x0080)

    IsNone = CBashBasicType(u'equipmentType', -1, u'IsBigGuns')
    IsBigGuns = CBashBasicType(u'equipmentType', 0, u'IsNone')
    IsEnergyWeapons = CBashBasicType(u'equipmentType', 1, u'IsNone')
    IsSmallGuns = CBashBasicType(u'equipmentType', 2, u'IsNone')
    IsMeleeWeapons = CBashBasicType(u'equipmentType', 3, u'IsNone')
    IsUnarmedWeapon = CBashBasicType(u'equipmentType', 4, u'IsNone')
    IsThrownWeapons = CBashBasicType(u'equipmentType', 5, u'IsNone')
    IsMine = CBashBasicType(u'equipmentType', 6, u'IsNone')
    IsBodyWear = CBashBasicType(u'equipmentType', 7, u'IsNone')
    IsHeadWear = CBashBasicType(u'equipmentType', 8, u'IsNone')
    IsHandWear = CBashBasicType(u'equipmentType', 9, u'IsNone')
    IsChems = CBashBasicType(u'equipmentType', 10, u'IsNone')
    IsStimpack = CBashBasicType(u'equipmentType', 11, u'IsNone')
    IsEdible = CBashBasicType(u'equipmentType', 12, u'IsNone')
    IsAlcohol = CBashBasicType(u'equipmentType', 13, u'IsNone')

    IsNotOverridingSounds = CBashBasicType(u'overrideSounds', 0, u'IsOverridingSounds')
    IsOverridingSounds = CBashBasicType(u'overrideSounds', 1, u'IsNotOverridingSounds')

    IsModulatesVoice = CBashBasicFlag(u'voiceFlags', 0x0001)
    exportattrs = copyattrs = FnvBaseRecord.baseattrs + [
        u'boundX1', u'boundY1', u'boundZ1', u'boundX2', u'boundY2', u'boundZ2',
        u'full', u'script', u'effect', u'flags', u'extraFlags', u'male_list',
        u'maleWorld_list', u'maleIconPath', u'maleSmallIconPath',
        u'female_list', u'femaleWorld_list', u'femaleIconPath',
        u'femaleSmallIconPath', u'ragdollTemplatePath', u'repairList',
        u'modelList', u'equipmentType', u'pickupSound', u'dropSound', u'value',
        u'health', u'weight', u'AR', u'voiceFlags', u'DT', u'unknown1',
        u'overrideSounds', u'sounds_list', u'soundsTemplate']

class FnvBOOKRecord(FnvBaseRecord):
    __slots__ = []
    _Type = b'BOOK'
    boundX1 = CBashGeneric(7, c_short)
    boundY1 = CBashGeneric(8, c_short)
    boundZ1 = CBashGeneric(9, c_short)
    boundX2 = CBashGeneric(10, c_short)
    boundY2 = CBashGeneric(11, c_short)
    boundZ2 = CBashGeneric(12, c_short)
    full = CBashSTRING(13)
    modPath = CBashISTRING(14)
    modb = CBashFLOAT32(15)
    modt_p = CBashUINT8ARRAY(16)

    def create_altTexture(self):
        length = _CGetFieldAttribute(self._RecordID, 17, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 17, 0, 0, 0, 0, 0, 0, 0, c_ulong(length +
                                                                    1))
        return FNVAltTexture(self._RecordID, 17, length)
    altTextures = CBashLIST(17, FNVAltTexture)
    altTextures_list = CBashLIST(17, FNVAltTexture, True)

    modelFlags = CBashGeneric(18, c_ubyte)
    iconPath = CBashISTRING(19)
    smallIconPath = CBashISTRING(20)
    script = CBashFORMID(21)
    description = CBashSTRING(22)
    destructable = CBashGrouped(23, FNVDestructable)
    destructable_list = CBashGrouped(23, FNVDestructable, True)

    flags = CBashGeneric(28, c_ubyte)
    teaches = CBashGeneric(29, c_byte)
    value = CBashGeneric(30, c_long)
    weight = CBashFLOAT32(31)

    IsHead = CBashBasicFlag(u'modelFlags', 0x01)
    IsTorso = CBashBasicFlag(u'modelFlags', 0x02)
    IsRightHand = CBashBasicFlag(u'modelFlags', 0x04)
    IsLeftHand = CBashBasicFlag(u'modelFlags', 0x08)

    IsFixed = CBashBasicFlag(u'flags', 0x00000002)
    IsCantBeTaken = CBashAlias(u'IsFixed')
    copyattrs = FnvBaseRecord.baseattrs + [u'boundX1', u'boundY1', u'boundZ1',
                                           u'boundX2', u'boundY2', u'boundZ2',
                                           u'full', u'modPath', u'modb', u'modt_p',
                                           u'altTextures_list', u'modelFlags',
                                           u'iconPath', u'smallIconPath',
                                           u'script', u'description',
                                           u'destructable_list', u'flags',
                                           u'teaches', u'value', u'weight']
    exportattrs = copyattrs[:]
    exportattrs.remove(u'modt_p')

class FnvCONTRecord(FnvBaseRecord):
    __slots__ = []
    _Type = b'CONT'
    def mergeFilter(self, target):
        """Filter out items that don't come from specified modSet.
        Filters items."""
        self.items = [x for x in self.items if x.item.ValidateFormID(target)]

    boundX1 = CBashGeneric(7, c_short)
    boundY1 = CBashGeneric(8, c_short)
    boundZ1 = CBashGeneric(9, c_short)
    boundX2 = CBashGeneric(10, c_short)
    boundY2 = CBashGeneric(11, c_short)
    boundZ2 = CBashGeneric(12, c_short)
    full = CBashSTRING(13)
    modPath = CBashISTRING(14)
    modb = CBashFLOAT32(15)
    modt_p = CBashUINT8ARRAY(16)

    def create_altTexture(self):
        length = _CGetFieldAttribute(self._RecordID, 17, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 17, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return FNVAltTexture(self._RecordID, 17, length)
    altTextures = CBashLIST(17, FNVAltTexture)
    altTextures_list = CBashLIST(17, FNVAltTexture, True)

    modelFlags = CBashGeneric(18, c_ubyte)
    script = CBashFORMID(19)

    def create_item(self):
        length = _CGetFieldAttribute(self._RecordID, 20, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 20, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return FNVItem(self._RecordID, 20, length)
    items = CBashLIST(20, FNVItem)
    items_list = CBashLIST(20, FNVItem, True)

    destructable = CBashGrouped(21, FNVDestructable)
    destructable_list = CBashGrouped(21, FNVDestructable, True)

    flags = CBashGeneric(26, c_ubyte)
    weight = CBashFLOAT32(27)
    openSound = CBashFORMID(28)
    closeSound = CBashFORMID(29)
    loopSound = CBashFORMID(30)

    IsHead = CBashBasicFlag(u'modelFlags', 0x01)
    IsTorso = CBashBasicFlag(u'modelFlags', 0x02)
    IsRightHand = CBashBasicFlag(u'modelFlags', 0x04)
    IsLeftHand = CBashBasicFlag(u'modelFlags', 0x08)

    IsRespawn = CBashBasicFlag(u'flags', 0x00000001)
    copyattrs = FnvBaseRecord.baseattrs + [u'boundX1', u'boundY1', u'boundZ1',
                                           u'boundX2', u'boundY2', u'boundZ2',
                                           u'full', u'modPath', u'modb', u'modt_p',
                                           u'altTextures_list', u'modelFlags',
                                           u'script', u'items_list',
                                           u'destructable_list', u'flags',
                                           u'weight', u'openSound',
                                           u'closeSound', u'loopSound']
    exportattrs = copyattrs[:]
    exportattrs.remove(u'modt_p')

class FnvDOORRecord(FnvBaseRecord):
    __slots__ = []
    _Type = b'DOOR'
    boundX1 = CBashGeneric(7, c_short)
    boundY1 = CBashGeneric(8, c_short)
    boundZ1 = CBashGeneric(9, c_short)
    boundX2 = CBashGeneric(10, c_short)
    boundY2 = CBashGeneric(11, c_short)
    boundZ2 = CBashGeneric(12, c_short)
    full = CBashSTRING(13)
    modPath = CBashISTRING(14)
    modb = CBashFLOAT32(15)
    modt_p = CBashUINT8ARRAY(16)

    def create_altTexture(self):
        length = _CGetFieldAttribute(self._RecordID, 17, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 17, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return FNVAltTexture(self._RecordID, 17, length)
    altTextures = CBashLIST(17, FNVAltTexture)
    altTextures_list = CBashLIST(17, FNVAltTexture, True)

    modelFlags = CBashGeneric(18, c_ubyte)
    script = CBashFORMID(19)
    destructable = CBashGrouped(20, FNVDestructable)
    destructable_list = CBashGrouped(20, FNVDestructable, True)

    openSound = CBashFORMID(25)
    closeSound = CBashFORMID(26)
    loopSound = CBashFORMID(27)
    flags = CBashGeneric(28, c_ubyte)

    IsHead = CBashBasicFlag(u'modelFlags', 0x01)
    IsTorso = CBashBasicFlag(u'modelFlags', 0x02)
    IsRightHand = CBashBasicFlag(u'modelFlags', 0x04)
    IsLeftHand = CBashBasicFlag(u'modelFlags', 0x08)

    IsAutomatic = CBashBasicFlag(u'flags', 0x02)
    IsHidden = CBashBasicFlag(u'flags', 0x04)
    IsMinimalUse = CBashBasicFlag(u'flags', 0x08)
    IsSlidingDoor = CBashBasicFlag(u'flags', 0x10)
    copyattrs = FnvBaseRecord.baseattrs + [u'boundX1', u'boundY1', u'boundZ1',
                                           u'boundX2', u'boundY2', u'boundZ2',
                                           u'full', u'modPath', u'modb', u'modt_p',
                                           u'altTextures_list', u'modelFlags',
                                           u'script', u'destructable_list',
                                           u'openSound', u'closeSound',
                                           u'loopSound', u'flags']
    exportattrs = copyattrs[:]
    exportattrs.remove(u'modt_p')

class FnvINGRRecord(FnvBaseRecord):
    __slots__ = []
    _Type = b'INGR'
    boundX1 = CBashGeneric(7, c_short)
    boundY1 = CBashGeneric(8, c_short)
    boundZ1 = CBashGeneric(9, c_short)
    boundX2 = CBashGeneric(10, c_short)
    boundY2 = CBashGeneric(11, c_short)
    boundZ2 = CBashGeneric(12, c_short)
    full = CBashSTRING(13)
    modPath = CBashISTRING(14)
    modb = CBashFLOAT32(15)
    modt_p = CBashUINT8ARRAY(16)

    def create_altTexture(self):
        length = _CGetFieldAttribute(self._RecordID, 17, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 17, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return FNVAltTexture(self._RecordID, 17, length)
    altTextures = CBashLIST(17, FNVAltTexture)
    altTextures_list = CBashLIST(17, FNVAltTexture, True)

    modelFlags = CBashGeneric(18, c_ubyte)
    iconPath = CBashISTRING(19)
    smallIconPath = CBashISTRING(20)
    script = CBashFORMID(21)
    equipmentType = CBashGeneric(22, c_long)
    weight = CBashFLOAT32(23)
    value = CBashGeneric(24, c_long)
    flags = CBashGeneric(25, c_ubyte)
    unused1 = CBashUINT8ARRAY(26, 3)

    def create_effect(self):
        length = _CGetFieldAttribute(self._RecordID, 27, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 27, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return FNVEffect(self._RecordID, 27, length)
    effects = CBashLIST(27, FNVEffect)
    effects_list = CBashLIST(27, FNVEffect, True)


    IsHead = CBashBasicFlag(u'modelFlags', 0x01)
    IsTorso = CBashBasicFlag(u'modelFlags', 0x02)
    IsRightHand = CBashBasicFlag(u'modelFlags', 0x04)
    IsLeftHand = CBashBasicFlag(u'modelFlags', 0x08)
    copyattrs = FnvBaseRecord.baseattrs + [u'boundX1', u'boundY1', u'boundZ1',
                                           u'boundX2', u'boundY2', u'boundZ2',
                                           u'full', u'modPath', u'modb', u'modt_p',
                                           u'altTextures_list', u'modelFlags',
                                           u'iconPath', u'smallIconPath',
                                           u'script', u'equipmentType',
                                           u'weight', u'value', u'flags',
                                           u'effects_list']
    exportattrs = copyattrs[:]
    exportattrs.remove(u'modt_p')

class FnvLIGHRecord(FnvBaseRecord):
    __slots__ = []
    _Type = b'LIGH'
    boundX1 = CBashGeneric(7, c_short)
    boundY1 = CBashGeneric(8, c_short)
    boundZ1 = CBashGeneric(9, c_short)
    boundX2 = CBashGeneric(10, c_short)
    boundY2 = CBashGeneric(11, c_short)
    boundZ2 = CBashGeneric(12, c_short)
    full = CBashSTRING(13)
    modPath = CBashISTRING(14)
    modb = CBashFLOAT32(15)
    modt_p = CBashUINT8ARRAY(16)

    def create_altTexture(self):
        length = _CGetFieldAttribute(self._RecordID, 17, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 17, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return FNVAltTexture(self._RecordID, 17, length)
    altTextures = CBashLIST(17, FNVAltTexture)
    altTextures_list = CBashLIST(17, FNVAltTexture, True)

    modelFlags = CBashGeneric(18, c_ubyte)
    iconPath = CBashISTRING(19)
    smallIconPath = CBashISTRING(20)
    script = CBashFORMID(21)
    duration = CBashGeneric(22, c_long)
    radius = CBashGeneric(23, c_ulong)
    red = CBashGeneric(24, c_ubyte)
    green = CBashGeneric(25, c_ubyte)
    blue = CBashGeneric(26, c_ubyte)
    unused1 = CBashUINT8ARRAY(27, 1)
    flags = CBashGeneric(28, c_ulong)
    falloff = CBashFLOAT32(29)
    fov = CBashFLOAT32(30)
    value = CBashGeneric(31, c_ulong)
    weight = CBashFLOAT32(32)
    fade = CBashFLOAT32(33)
    sound = CBashFORMID(34)

    IsDynamic = CBashBasicFlag(u'flags', 0x00000001)
    IsCanTake = CBashBasicFlag(u'flags', 0x00000002)
    IsNegative = CBashBasicFlag(u'flags', 0x00000004)
    IsFlickers = CBashBasicFlag(u'flags', 0x00000008)
    IsOffByDefault = CBashBasicFlag(u'flags', 0x00000020)
    IsFlickerSlow = CBashBasicFlag(u'flags', 0x00000040)
    IsPulse = CBashBasicFlag(u'flags', 0x00000080)
    IsPulseSlow = CBashBasicFlag(u'flags', 0x00000100)
    IsSpotLight = CBashBasicFlag(u'flags', 0x00000200)
    IsSpotShadow = CBashBasicFlag(u'flags', 0x00000400)

    IsHead = CBashBasicFlag(u'modelFlags', 0x01)
    IsTorso = CBashBasicFlag(u'modelFlags', 0x02)
    IsRightHand = CBashBasicFlag(u'modelFlags', 0x04)
    IsLeftHand = CBashBasicFlag(u'modelFlags', 0x08)
    copyattrs = FnvBaseRecord.baseattrs + [u'boundX1', u'boundY1', u'boundZ1',
                                           u'boundX2', u'boundY2', u'boundZ2',
                                           u'full', u'modPath', u'modb', u'modt_p',
                                           u'altTextures_list', u'modelFlags',
                                           u'iconPath', u'smallIconPath',
                                           u'script', u'duration', u'radius',
                                           u'red', u'green', u'blue',
                                           u'flags', u'falloff', u'fov',
                                           u'value', u'weight', u'fade', u'sound']
    exportattrs = copyattrs[:]
    exportattrs.remove(u'modt_p')

class FnvMISCRecord(FnvBaseRecord):
    __slots__ = []
    _Type = b'MISC'
    boundX1 = CBashGeneric(7, c_short)
    boundY1 = CBashGeneric(8, c_short)
    boundZ1 = CBashGeneric(9, c_short)
    boundX2 = CBashGeneric(10, c_short)
    boundY2 = CBashGeneric(11, c_short)
    boundZ2 = CBashGeneric(12, c_short)
    full = CBashSTRING(13)
    modPath = CBashISTRING(14)
    modb = CBashFLOAT32(15)
    modt_p = CBashUINT8ARRAY(16)

    def create_altTexture(self):
        length = _CGetFieldAttribute(self._RecordID, 17, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 17, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return FNVAltTexture(self._RecordID, 17, length)
    altTextures = CBashLIST(17, FNVAltTexture)
    altTextures_list = CBashLIST(17, FNVAltTexture, True)

    modelFlags = CBashGeneric(18, c_ubyte)
    iconPath = CBashISTRING(19)
    smallIconPath = CBashISTRING(20)
    script = CBashFORMID(21)
    destructable = CBashGrouped(22, FNVDestructable)
    destructable_list = CBashGrouped(22, FNVDestructable, True)

    pickupSound = CBashFORMID(27)
    dropSound = CBashFORMID(28)
    value = CBashGeneric(29, c_long)
    weight = CBashFLOAT32(30)
    loopSound = CBashFORMID(31)

    IsHead = CBashBasicFlag(u'modelFlags', 0x01)
    IsTorso = CBashBasicFlag(u'modelFlags', 0x02)
    IsRightHand = CBashBasicFlag(u'modelFlags', 0x04)
    IsLeftHand = CBashBasicFlag(u'modelFlags', 0x08)
    copyattrs = FnvBaseRecord.baseattrs + [u'boundX1', u'boundY1', u'boundZ1',
                                           u'boundX2', u'boundY2', u'boundZ2',
                                           u'full', u'modPath', u'modb', u'modt_p',
                                           u'altTextures_list', u'modelFlags',
                                           u'iconPath', u'smallIconPath',
                                           u'script', u'destructable_list',
                                           u'pickupSound', u'dropSound',
                                           u'value', u'weight', u'loopSound']
    exportattrs = copyattrs[:]
    exportattrs.remove(u'modt_p')

class FnvSTATRecord(FnvBaseRecord):
    __slots__ = []
    _Type = b'STAT'
    boundX1 = CBashGeneric(7, c_short)
    boundY1 = CBashGeneric(8, c_short)
    boundZ1 = CBashGeneric(9, c_short)
    boundX2 = CBashGeneric(10, c_short)
    boundY2 = CBashGeneric(11, c_short)
    boundZ2 = CBashGeneric(12, c_short)
    modPath = CBashISTRING(13)
    modb = CBashFLOAT32(14)
    modt_p = CBashUINT8ARRAY(15)

    def create_altTexture(self):
        length = _CGetFieldAttribute(self._RecordID, 16, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 16, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return FNVAltTexture(self._RecordID, 16, length)
    altTextures = CBashLIST(16, FNVAltTexture)
    altTextures_list = CBashLIST(16, FNVAltTexture, True)

    modelFlags = CBashGeneric(17, c_ubyte)
    passSound = CBashGeneric(18, c_byte)
    loopSound = CBashFORMID(19)

    IsHead = CBashBasicFlag(u'modelFlags', 0x01)
    IsTorso = CBashBasicFlag(u'modelFlags', 0x02)
    IsRightHand = CBashBasicFlag(u'modelFlags', 0x04)
    IsLeftHand = CBashBasicFlag(u'modelFlags', 0x08)

    IsNone = CBashBasicType(u'passSound', -1, u'IsBushA')
    IsBushA = CBashBasicType(u'passSound', 0, u'IsNone')
    IsBushB = CBashBasicType(u'passSound', 1, u'IsNone')
    IsBushC = CBashBasicType(u'passSound', 2, u'IsNone')
    IsBushD = CBashBasicType(u'passSound', 3, u'IsNone')
    IsBushE = CBashBasicType(u'passSound', 4, u'IsNone')
    IsBushF = CBashBasicType(u'passSound', 5, u'IsNone')
    IsBushG = CBashBasicType(u'passSound', 6, u'IsNone')
    IsBushH = CBashBasicType(u'passSound', 7, u'IsNone')
    IsBushI = CBashBasicType(u'passSound', 8, u'IsNone')
    IsBushJ = CBashBasicType(u'passSound', 9, u'IsNone')
    copyattrs = FnvBaseRecord.baseattrs + [u'boundX1', u'boundY1', u'boundZ1',
                                           u'boundX2', u'boundY2', u'boundZ2',
                                           u'modPath', u'modb', u'modt_p',
                                           u'altTextures_list', u'modelFlags',
                                           u'passSound', u'loopSound']
    exportattrs = copyattrs[:]
    exportattrs.remove(u'modt_p')

class FnvSCOLRecord(FnvBaseRecord):
    __slots__ = []
    _Type = b'SCOL'
    class Static(ListComponent):
        __slots__ = []
        class Placement(ListX2Component):
            __slots__ = []
            posX = CBashFLOAT32_LISTX2(1)
            posY = CBashFLOAT32_LISTX2(2)
            posZ = CBashFLOAT32_LISTX2(3)
            rotX = CBashFLOAT32_LISTX2(4)
            rotX_degrees = CBashDEGREES_LISTX2(4)
            rotY = CBashFLOAT32_LISTX2(5)
            rotY_degrees = CBashDEGREES_LISTX2(5)
            rotZ = CBashFLOAT32_LISTX2(6)
            rotZ_degrees = CBashDEGREES_LISTX2(6)
            scale = CBashFLOAT32_LISTX2(7)
            exportattrs = copyattrs = [u'posX', u'posY', u'posZ',
                                       u'rotX', u'rotY', u'rotZ',
                                       u'scale']

        static = CBashFORMID_LIST(1)

        def create_placement(self):
            length = _CGetFieldAttribute(self._RecordID, self._FieldID, self._ListIndex, 2, 0, 0, 0, 0, 1)
            _CSetField(self._RecordID, self._FieldID, self._ListIndex, 2, 0, 0, 0, 0, 0, c_ulong(length + 1))
            return self.Placement(self._RecordID, self._FieldID, self._ListIndex, 2, length)
        placements = CBashLIST_LIST(2, Placement)
        placements_list = CBashLIST_LIST(2, Placement, True)

        exportattrs = copyattrs = [u'static', u'placements_list']

    boundX1 = CBashGeneric(7, c_short)
    boundY1 = CBashGeneric(8, c_short)
    boundZ1 = CBashGeneric(9, c_short)
    boundX2 = CBashGeneric(10, c_short)
    boundY2 = CBashGeneric(11, c_short)
    boundZ2 = CBashGeneric(12, c_short)
    modPath = CBashISTRING(13)
    modb = CBashFLOAT32(14)
    modt_p = CBashUINT8ARRAY(15)

    def create_altTexture(self):
        length = _CGetFieldAttribute(self._RecordID, 16, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 16, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return FNVAltTexture(self._RecordID, 16, length)
    altTextures = CBashLIST(16, FNVAltTexture)
    altTextures_list = CBashLIST(16, FNVAltTexture, True)

    modelFlags = CBashGeneric(17, c_ubyte)

    def create_static(self):
        length = _CGetFieldAttribute(self._RecordID, 18, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 18, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return self.Static(self._RecordID, 18, length)
    statics = CBashLIST(18, Static)
    statics_list = CBashLIST(18, Static, True)


    IsHead = CBashBasicFlag(u'modelFlags', 0x01)
    IsTorso = CBashBasicFlag(u'modelFlags', 0x02)
    IsRightHand = CBashBasicFlag(u'modelFlags', 0x04)
    IsLeftHand = CBashBasicFlag(u'modelFlags', 0x08)
    copyattrs = FnvBaseRecord.baseattrs + [u'boundX1', u'boundY1', u'boundZ1',
                                           u'boundX2', u'boundY2', u'boundZ2',
                                           u'modPath', u'modb', u'modt_p',
                                           u'altTextures_list', u'modelFlags',
                                           u'statics_list']
    exportattrs = copyattrs[:]
    exportattrs.remove(u'modt_p')

class FnvMSTTRecord(FnvBaseRecord):
    __slots__ = []
    _Type = b'MSTT'
    boundX1 = CBashGeneric(7, c_short)
    boundY1 = CBashGeneric(8, c_short)
    boundZ1 = CBashGeneric(9, c_short)
    boundX2 = CBashGeneric(10, c_short)
    boundY2 = CBashGeneric(11, c_short)
    boundZ2 = CBashGeneric(12, c_short)
    full = CBashSTRING(13)
    modPath = CBashISTRING(14)
    modb = CBashFLOAT32(15)
    modt_p = CBashUINT8ARRAY(16)

    def create_altTexture(self):
        length = _CGetFieldAttribute(self._RecordID, 17, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 17, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return FNVAltTexture(self._RecordID, 17, length)
    altTextures = CBashLIST(17, FNVAltTexture)
    altTextures_list = CBashLIST(17, FNVAltTexture, True)

    modelFlags = CBashGeneric(18, c_ubyte)
    destructable = CBashGrouped(19, FNVDestructable)
    destructable_list = CBashGrouped(19, FNVDestructable, True)

    data_p = CBashUINT8ARRAY(24)
    sound = CBashFORMID(25)

    IsHead = CBashBasicFlag(u'modelFlags', 0x01)
    IsTorso = CBashBasicFlag(u'modelFlags', 0x02)
    IsRightHand = CBashBasicFlag(u'modelFlags', 0x04)
    IsLeftHand = CBashBasicFlag(u'modelFlags', 0x08)
    copyattrs = FnvBaseRecord.baseattrs + [u'boundX1', u'boundY1', u'boundZ1',
                                           u'boundX2', u'boundY2', u'boundZ2',
                                           u'full', u'modPath', u'modb', u'modt_p',
                                           u'altTextures_list', u'modelFlags',
                                           u'destructable_list', u'data_p',
                                           u'sound']
    exportattrs = copyattrs[:]
    exportattrs.remove(u'modt_p')
    exportattrs.remove(u'data_p')

class FnvPWATRecord(FnvBaseRecord):
    __slots__ = []
    _Type = b'PWAT'
    boundX1 = CBashGeneric(7, c_short)
    boundY1 = CBashGeneric(8, c_short)
    boundZ1 = CBashGeneric(9, c_short)
    boundX2 = CBashGeneric(10, c_short)
    boundY2 = CBashGeneric(11, c_short)
    boundZ2 = CBashGeneric(12, c_short)
    modPath = CBashISTRING(13)
    modb = CBashFLOAT32(14)
    modt_p = CBashUINT8ARRAY(15)

    def create_altTexture(self):
        length = _CGetFieldAttribute(self._RecordID, 16, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 16, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return FNVAltTexture(self._RecordID, 16, length)
    altTextures = CBashLIST(16, FNVAltTexture)
    altTextures_list = CBashLIST(16, FNVAltTexture, True)

    modelFlags = CBashGeneric(17, c_ubyte)
    flags = CBashGeneric(18, c_ulong)
    water = CBashFORMID(19)

    IsHead = CBashBasicFlag(u'modelFlags', 0x01)
    IsTorso = CBashBasicFlag(u'modelFlags', 0x02)
    IsRightHand = CBashBasicFlag(u'modelFlags', 0x04)
    IsLeftHand = CBashBasicFlag(u'modelFlags', 0x08)

    IsReflects = CBashBasicFlag(u'flags', 0x00000001)
    IsReflectsActors = CBashBasicFlag(u'flags', 0x00000002)
    IsReflectsLand = CBashBasicFlag(u'flags', 0x00000004)
    IsReflectsLODLand = CBashBasicFlag(u'flags', 0x00000008)
    IsReflectsLODBuildings = CBashBasicFlag(u'flags', 0x00000010)
    IsReflectsTrees = CBashBasicFlag(u'flags', 0x00000020)
    IsReflectsSky = CBashBasicFlag(u'flags', 0x00000040)
    IsReflectsDynamicObjects = CBashBasicFlag(u'flags', 0x00000080)
    IsReflectsDeadBodies = CBashBasicFlag(u'flags', 0x00000100)
    IsRefracts = CBashBasicFlag(u'flags', 0x00000200)
    IsRefractsActors = CBashBasicFlag(u'flags', 0x00000400)
    IsRefractsLand = CBashBasicFlag(u'flags', 0x00000800)
    IsRefractsDynamicObjects = CBashBasicFlag(u'flags', 0x00010000)
    IsRefractsDeadBodies = CBashBasicFlag(u'flags', 0x00020000)
    IsSilhouetteReflections = CBashBasicFlag(u'flags', 0x00040000)
    IsDepth = CBashBasicFlag(u'flags', 0x10000000)
    IsObjectTextureCoordinates = CBashBasicFlag(u'flags', 0x20000000)
    IsNoUnderwaterFog = CBashBasicFlag(u'flags', 0x80000000)
    IsUnderwaterFog = CBashInvertedFlag(u'IsNoUnderwaterFog')
    copyattrs = FnvBaseRecord.baseattrs + [u'boundX1', u'boundY1', u'boundZ1',
                                           u'boundX2', u'boundY2', u'boundZ2',
                                           u'modPath', u'modb', u'modt_p',
                                           u'altTextures_list',
                                           u'modelFlags', u'flags', u'water']
    exportattrs = copyattrs[:]
    exportattrs.remove(u'modt_p')

class FnvGRASRecord(FnvBaseRecord):
    __slots__ = []
    _Type = b'GRAS'
    boundX1 = CBashGeneric(7, c_short)
    boundY1 = CBashGeneric(8, c_short)
    boundZ1 = CBashGeneric(9, c_short)
    boundX2 = CBashGeneric(10, c_short)
    boundY2 = CBashGeneric(11, c_short)
    boundZ2 = CBashGeneric(12, c_short)
    modPath = CBashISTRING(13)
    modb = CBashFLOAT32(14)
    modt_p = CBashUINT8ARRAY(15)

    def create_altTexture(self):
        length = _CGetFieldAttribute(self._RecordID, 16, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 16, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return FNVAltTexture(self._RecordID, 16, length)
    altTextures = CBashLIST(16, FNVAltTexture)
    altTextures_list = CBashLIST(16, FNVAltTexture, True)

    modelFlags = CBashGeneric(17, c_ubyte)
    density = CBashGeneric(18, c_ubyte)
    minSlope = CBashGeneric(19, c_ubyte)
    maxSlope = CBashGeneric(20, c_ubyte)
    unused1 = CBashUINT8ARRAY(21, 1)
    waterDistance = CBashGeneric(22, c_ushort)
    unused2 = CBashUINT8ARRAY(23, 2)
    waterOp = CBashGeneric(24, c_ulong)
    posRange = CBashFLOAT32(25)
    heightRange = CBashFLOAT32(26)
    colorRange = CBashFLOAT32(27)
    wavePeriod = CBashFLOAT32(28)
    flags = CBashGeneric(29, c_ubyte)
    unused3 = CBashUINT8ARRAY(30, 3)

    IsHead = CBashBasicFlag(u'modelFlags', 0x01)
    IsTorso = CBashBasicFlag(u'modelFlags', 0x02)
    IsRightHand = CBashBasicFlag(u'modelFlags', 0x04)
    IsLeftHand = CBashBasicFlag(u'modelFlags', 0x08)

    IsVLighting = CBashBasicFlag(u'flags', 0x00000001)
    IsVertexLighting = CBashAlias(u'IsVLighting')
    IsUScaling = CBashBasicFlag(u'flags', 0x00000002)
    IsUniformScaling = CBashAlias(u'IsUScaling')
    IsFitSlope = CBashBasicFlag(u'flags', 0x00000004)
    IsFitToSlope = CBashAlias(u'IsFitSlope')
    copyattrs = FnvBaseRecord.baseattrs + [u'boundX1', u'boundY1', u'boundZ1',
                                           u'boundX2', u'boundY2', u'boundZ2',
                                           u'modPath', u'modb', u'modt_p',
                                           u'altTextures_list', u'modelFlags',
                                           u'density', u'minSlope', u'maxSlope',
                                           u'waterDistance', u'waterOp',
                                           u'posRange', u'heightRange',
                                           u'colorRange', u'wavePeriod',
                                           u'flags']
    exportattrs = copyattrs[:]
    exportattrs.remove(u'modt_p')

class FnvTREERecord(FnvBaseRecord):
    __slots__ = []
    _Type = b'TREE'
    boundX1 = CBashGeneric(7, c_short)
    boundY1 = CBashGeneric(8, c_short)
    boundZ1 = CBashGeneric(9, c_short)
    boundX2 = CBashGeneric(10, c_short)
    boundY2 = CBashGeneric(11, c_short)
    boundZ2 = CBashGeneric(12, c_short)
    modPath = CBashISTRING(13)
    modb = CBashFLOAT32(14)
    modt_p = CBashUINT8ARRAY(15)

    def create_altTexture(self):
        length = _CGetFieldAttribute(self._RecordID, 16, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 16, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return FNVAltTexture(self._RecordID, 16, length)
    altTextures = CBashLIST(16, FNVAltTexture)
    altTextures_list = CBashLIST(16, FNVAltTexture, True)

    modelFlags = CBashGeneric(17, c_ubyte)
    iconPath = CBashISTRING(18)
    smallIconPath = CBashISTRING(19)
    speedTree = CBashUINT32ARRAY(20)
    curvature = CBashFLOAT32(21)
    minAngle = CBashFLOAT32(22)
    maxAngle = CBashFLOAT32(23)
    branchDim = CBashFLOAT32(24)
    leafDim = CBashFLOAT32(25)
    shadowRadius = CBashGeneric(26, c_long)
    rockSpeed = CBashFLOAT32(27)
    rustleSpeed = CBashFLOAT32(28)
    widthBill = CBashFLOAT32(29)
    heightBill = CBashFLOAT32(30)
    copyattrs = FnvBaseRecord.baseattrs + [u'boundX1', u'boundY1', u'boundZ1',
                                           u'boundX2', u'boundY2', u'boundZ2',
                                           u'modPath', u'modb', u'modt_p',
                                           u'altTextures_list', u'modelFlags',
                                           u'iconPath', u'smallIconPath',
                                           u'speedTree', u'curvature',
                                           u'minAngle', u'maxAngle',
                                           u'branchDim', u'leafDim',
                                           u'shadowRadius', u'rockSpeed',
                                           u'rustleSpeed', u'widthBill',
                                           u'heightBill']
    exportattrs = copyattrs[:]
    exportattrs.remove(u'modt_p')

class FnvFURNRecord(FnvBaseRecord):
    __slots__ = []
    _Type = b'FURN'
    boundX1 = CBashGeneric(7, c_short)
    boundY1 = CBashGeneric(8, c_short)
    boundZ1 = CBashGeneric(9, c_short)
    boundX2 = CBashGeneric(10, c_short)
    boundY2 = CBashGeneric(11, c_short)
    boundZ2 = CBashGeneric(12, c_short)
    full = CBashSTRING(13)
    modPath = CBashISTRING(14)
    modb = CBashFLOAT32(15)
    modt_p = CBashUINT8ARRAY(16)

    def create_altTexture(self):
        length = _CGetFieldAttribute(self._RecordID, 17, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 17, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return FNVAltTexture(self._RecordID, 17, length)
    altTextures = CBashLIST(17, FNVAltTexture)
    altTextures_list = CBashLIST(17, FNVAltTexture, True)

    modelFlags = CBashGeneric(18, c_ubyte)
    script = CBashFORMID(19)
    destructable = CBashGrouped(20, FNVDestructable)
    destructable_list = CBashGrouped(20, FNVDestructable, True)

    flags = CBashGeneric(25, c_ulong)

    IsAnim01 = CBashBasicFlag(u'flags', 0x00000001)
    IsAnim02 = CBashBasicFlag(u'flags', 0x00000002)
    IsAnim03 = CBashBasicFlag(u'flags', 0x00000004)
    IsAnim04 = CBashBasicFlag(u'flags', 0x00000008)
    IsAnim05 = CBashBasicFlag(u'flags', 0x00000010)
    IsAnim06 = CBashBasicFlag(u'flags', 0x00000020)
    IsAnim07 = CBashBasicFlag(u'flags', 0x00000040)
    IsAnim08 = CBashBasicFlag(u'flags', 0x00000080)
    IsAnim09 = CBashBasicFlag(u'flags', 0x00000100)
    IsAnim10 = CBashBasicFlag(u'flags', 0x00000200)
    IsAnim11 = CBashBasicFlag(u'flags', 0x00000400)
    IsAnim12 = CBashBasicFlag(u'flags', 0x00000800)
    IsAnim13 = CBashBasicFlag(u'flags', 0x00001000)
    IsAnim14 = CBashBasicFlag(u'flags', 0x00002000)
    IsAnim15 = CBashBasicFlag(u'flags', 0x00004000)
    IsAnim16 = CBashBasicFlag(u'flags', 0x00008000)
    IsAnim17 = CBashBasicFlag(u'flags', 0x00010000)
    IsAnim18 = CBashBasicFlag(u'flags', 0x00020000)
    IsAnim19 = CBashBasicFlag(u'flags', 0x00040000)
    IsAnim20 = CBashBasicFlag(u'flags', 0x00080000)
    IsAnim21 = CBashBasicFlag(u'flags', 0x00100000)
    IsAnim22 = CBashBasicFlag(u'flags', 0x00200000)
    IsAnim23 = CBashBasicFlag(u'flags', 0x00400000)
    IsAnim24 = CBashBasicFlag(u'flags', 0x00800000)
    IsAnim25 = CBashBasicFlag(u'flags', 0x01000000)
    IsAnim26 = CBashBasicFlag(u'flags', 0x02000000)
    IsAnim27 = CBashBasicFlag(u'flags', 0x04000000)
    IsAnim28 = CBashBasicFlag(u'flags', 0x08000000)
    IsAnim29 = CBashBasicFlag(u'flags', 0x10000000)
    IsAnim30 = CBashBasicFlag(u'flags', 0x20000000)
    IsSitAnim = CBashMaskedType(u'flags', 0xC0000000, 0x40000000, u'IsSleepAnim')
    IsSleepAnim = CBashMaskedType(u'flags', 0xC0000000, 0x80000000, u'IsSitAnim')
    copyattrs = FnvBaseRecord.baseattrs + [u'boundX1', u'boundY1', u'boundZ1',
                                           u'boundX2', u'boundY2', u'boundZ2',
                                           u'full', u'modPath', u'modb', u'modt_p',
                                           u'altTextures_list', u'modelFlags',
                                           u'script', u'destructable_list',
                                           u'flags']
    exportattrs = copyattrs[:]
    exportattrs.remove(u'modt_p')

class FnvWEAPRecord(FnvBaseRecord):
    __slots__ = []
    _Type = b'WEAP'
    boundX1 = CBashGeneric(7, c_short)
    boundY1 = CBashGeneric(8, c_short)
    boundZ1 = CBashGeneric(9, c_short)
    boundX2 = CBashGeneric(10, c_short)
    boundY2 = CBashGeneric(11, c_short)
    boundZ2 = CBashGeneric(12, c_short)
    full = CBashSTRING(13)
    modPath = CBashISTRING(14)
    modb = CBashFLOAT32(15)
    modt_p = CBashUINT8ARRAY(16)

    def create_altTexture(self):
        length = _CGetFieldAttribute(self._RecordID, 17, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 17, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return FNVAltTexture(self._RecordID, 17, length)
    altTextures = CBashLIST(17, FNVAltTexture)
    altTextures_list = CBashLIST(17, FNVAltTexture, True)

    modelFlags = CBashGeneric(18, c_ubyte)
    iconPath = CBashISTRING(19)
    smallIconPath = CBashISTRING(20)
    script = CBashFORMID(21)
    effect = CBashFORMID(22)
    chargeAmount = CBashGeneric(23, c_short)
    ammo = CBashFORMID(24)
    destructable = CBashGrouped(25, FNVDestructable)
    destructable_list = CBashGrouped(25, FNVDestructable, True)

    repairList = CBashFORMID(30)
    equipmentType = CBashGeneric(31, c_long)
    modelList = CBashFORMID(32)
    pickupSound = CBashFORMID(33)
    dropSound = CBashFORMID(34)
    shell = CBashGrouped(35, WorldModel)
    shell_list = CBashGrouped(35, WorldModel, True)

    scope = CBashGrouped(38, WorldModel)
    scope_list = CBashGrouped(38, WorldModel, True)

    scopeEffect = CBashFORMID(41)
    world = CBashGrouped(42, WorldModel)
    world_list = CBashGrouped(42, WorldModel, True)

    vatsName = CBashSTRING(45)
    weaponNode = CBashSTRING(46)
    model1Path = CBashISTRING(47)
    model2Path = CBashISTRING(48)
    model12Path = CBashISTRING(49)
    model3Path = CBashISTRING(50)
    model13Path = CBashISTRING(51)
    model23Path = CBashISTRING(52)
    model123Path = CBashISTRING(53)
    impact = CBashFORMID(54)
    model = CBashFORMID(55)
    model1 = CBashFORMID(56)
    model2 = CBashFORMID(57)
    model12 = CBashFORMID(58)
    model3 = CBashFORMID(59)
    model13 = CBashFORMID(60)
    model23 = CBashFORMID(61)
    model123 = CBashFORMID(62)
    mod1 = CBashFORMID(63)
    mod2 = CBashFORMID(64)
    mod3 = CBashFORMID(65)
    sound3D = CBashFORMID(66)
    soundDist = CBashFORMID(67)
    sound2D = CBashFORMID(68)
    sound3DLoop = CBashFORMID(69)
    soundMelee = CBashFORMID(70)
    soundBlock = CBashFORMID(71)
    soundIdle = CBashFORMID(72)
    soundEquip = CBashFORMID(73)
    soundUnequip = CBashFORMID(74)
    soundMod3D = CBashFORMID(75)
    soundModDist = CBashFORMID(76)
    soundMod2D = CBashFORMID(77)
    value = CBashGeneric(78, c_long)
    health = CBashGeneric(79, c_long)
    weight = CBashFLOAT32(80)
    damage = CBashGeneric(81, c_short)
    clipSize = CBashGeneric(82, c_ubyte)
    animType = CBashGeneric(83, c_ulong)
    animMult = CBashFLOAT32(84)
    reach = CBashFLOAT32(85)
    flags = CBashGeneric(86, c_ubyte)
    gripAnim = CBashGeneric(87, c_ubyte)
    ammoUse = CBashGeneric(88, c_ubyte)
    reloadAnim = CBashGeneric(89, c_ubyte)
    minSpread = CBashFLOAT32(90)
    spread = CBashFLOAT32(91)
    unknown1 = CBashFLOAT32(92)
    sightFOV = CBashFLOAT32(93)
    unknown2 = CBashFLOAT32(94)
    projectile = CBashFORMID(95)
    VATSHitChance = CBashGeneric(96, c_ubyte)
    attackAnim = CBashGeneric(97, c_ubyte)
    projectileCount = CBashGeneric(98, c_ubyte)
    weaponAV = CBashGeneric(99, c_ubyte)
    minRange = CBashFLOAT32(100)
    maxRange = CBashFLOAT32(101)
    onHit = CBashGeneric(102, c_ulong)
    extraFlags = CBashGeneric(103, c_ulong)
    animAttackMult = CBashFLOAT32(104)
    fireRate = CBashFLOAT32(105)
    overrideAP = CBashFLOAT32(106)
    leftRumble = CBashFLOAT32(107)
    timeRumble = CBashFLOAT32(108)
    overrideDamageToWeapon = CBashFLOAT32(109)
    reloadTime = CBashFLOAT32(110)
    jamTime = CBashFLOAT32(111)
    aimArc = CBashFLOAT32(112)
    skill = CBashGeneric(113, c_long)
    rumbleType = CBashGeneric(114, c_ulong)
    rumbleWavelength = CBashFLOAT32(115)
    limbDamageMult = CBashFLOAT32(116)
    resistType = CBashGeneric(117, c_long)
    sightUsage = CBashFLOAT32(118)
    semiFireDelayMin = CBashFLOAT32(119)
    semiFireDelayMax = CBashFLOAT32(120)
    unknown3 = CBashFLOAT32(121)
    effectMod1 = CBashGeneric(122, c_ulong)
    effectMod2 = CBashGeneric(123, c_ulong)
    effectMod3 = CBashGeneric(124, c_ulong)
    valueAMod1 = CBashFLOAT32(125)
    valueAMod2 = CBashFLOAT32(126)
    valueAMod3 = CBashFLOAT32(127)
    overridePwrAtkAnim = CBashGeneric(128, c_ulong)
    strengthReq = CBashGeneric(129, c_ulong)
    unknown4 = CBashGeneric(130, c_ubyte)
    reloadAnimMod = CBashGeneric(131, c_ubyte)
    unknown5 = CBashUINT8ARRAY(132, 2)
    regenRate = CBashFLOAT32(133)
    killImpulse = CBashFLOAT32(134)
    valueBMod1 = CBashFLOAT32(135)
    valueBMod2 = CBashFLOAT32(136)
    valueBMod3 = CBashFLOAT32(137)
    skillReq = CBashGeneric(138, c_ulong)
    critDamage = CBashGeneric(139, c_ushort)
    unused1 = CBashUINT8ARRAY(140, 2)
    critMult = CBashFLOAT32(141)
    critFlags = CBashGeneric(142, c_ubyte)
    unused2 = CBashUINT8ARRAY(143, 3)
    critEffect = CBashFORMID(144)
    vatsEffect = CBashFORMID(145)
    vatsSkill = CBashFLOAT32(146)
    vatsDamageMult = CBashFLOAT32(147)
    AP = CBashFLOAT32(148)
    silenceType = CBashGeneric(149, c_ubyte)
    modRequiredType = CBashGeneric(150, c_ubyte)
    unused3 = CBashUINT8ARRAY(151, 2)
    soundLevelType = CBashGeneric(152, c_ulong)

    IsNotNormalWeapon = CBashBasicFlag(u'flags', 0x01)
    IsNormalWeapon = CBashInvertedFlag(u'IsNotNormalWeapon')
    IsAutomatic = CBashBasicFlag(u'flags', 0x02)
    IsHasScope = CBashBasicFlag(u'flags', 0x04)
    IsCantDrop = CBashBasicFlag(u'flags', 0x08)
    IsCanDrop = CBashInvertedFlag(u'IsCantDrop')
    IsHideBackpack = CBashBasicFlag(u'flags', 0x10)
    IsEmbeddedWeapon = CBashBasicFlag(u'flags', 0x20)
    IsDontUse1stPersonISAnimations = CBashBasicFlag(u'flags', 0x40)
    IsUse1stPersonISAnimations = CBashInvertedFlag(u'IsDontUse1stPersonISAnimations')
    IsNonPlayable = CBashBasicFlag(u'flags', 0x80)
    IsPlayable = CBashInvertedFlag(u'IsNonPlayable')

    IsPlayerOnly = CBashBasicFlag(u'extraFlags', 0x00000001)
    IsNPCsUseAmmo = CBashBasicFlag(u'extraFlags', 0x00000002)
    IsNoJamAfterReload = CBashBasicFlag(u'extraFlags', 0x00000004)
    IsJamAfterReload = CBashInvertedFlag(u'IsNoJamAfterReload')
    IsOverrideActionPoints = CBashBasicFlag(u'extraFlags', 0x00000008)
    IsMinorCrime = CBashBasicFlag(u'extraFlags', 0x00000010)
    IsRangeFixed = CBashBasicFlag(u'extraFlags', 0x00000020)
    IsNotUsedInNormalCombat = CBashBasicFlag(u'extraFlags', 0x00000040)
    IsUsedInNormalCombat = CBashInvertedFlag(u'IsNotUsedInNormalCombat')
    IsOverrideDamageToWeaponMult = CBashBasicFlag(u'extraFlags', 0x00000080)
    IsDontUse3rdPersonISAnimations = CBashBasicFlag(u'extraFlags', 0x00000100)
    IsUse3rdPersonISAnimations = CBashInvertedFlag(u'IsDontUse3rdPersonISAnimations')
    IsShortBurst = CBashBasicFlag(u'extraFlags', 0x00000200)
    IsRumbleAlternate = CBashBasicFlag(u'extraFlags', 0x00000400)
    IsLongBurst = CBashBasicFlag(u'extraFlags', 0x00000800)
    IsScopeHasNightVision = CBashBasicFlag(u'extraFlags', 0x00001000)
    IsScopeFromMod = CBashBasicFlag(u'extraFlags', 0x00002000)

    IsCritOnDeath = CBashBasicFlag(u'critFlags', 0x01)

    IsHead = CBashBasicFlag(u'modelFlags', 0x01)
    IsTorso = CBashBasicFlag(u'modelFlags', 0x02)
    IsRightHand = CBashBasicFlag(u'modelFlags', 0x04)
    IsLeftHand = CBashBasicFlag(u'modelFlags', 0x08)

    IsNone = CBashBasicType(u'equipmentType', -1, u'IsBigGuns')
    IsBigGuns = CBashBasicType(u'equipmentType', 0, u'IsNone')
    IsEnergyWeapons = CBashBasicType(u'equipmentType', 1, u'IsNone')
    IsSmallGuns = CBashBasicType(u'equipmentType', 2, u'IsNone')
    IsMeleeWeapons = CBashBasicType(u'equipmentType', 3, u'IsNone')
    IsUnarmedWeapon = CBashBasicType(u'equipmentType', 4, u'IsNone')
    IsThrownWeapons = CBashBasicType(u'equipmentType', 5, u'IsNone')
    IsMine = CBashBasicType(u'equipmentType', 6, u'IsNone')
    IsBodyWear = CBashBasicType(u'equipmentType', 7, u'IsNone')
    IsHeadWear = CBashBasicType(u'equipmentType', 8, u'IsNone')
    IsHandWear = CBashBasicType(u'equipmentType', 9, u'IsNone')
    IsChems = CBashBasicType(u'equipmentType', 10, u'IsNone')
    IsStimpack = CBashBasicType(u'equipmentType', 11, u'IsNone')
    IsEdible = CBashBasicType(u'equipmentType', 12, u'IsNone')
    IsAlcohol = CBashBasicType(u'equipmentType', 13, u'IsNone')

    IsHand2Hand = CBashBasicType(u'animType', 0, u'IsMelee1Hand')
    IsMelee1Hand = CBashBasicType(u'animType', 1, u'IsHand2Hand')
    IsMelee2Hand = CBashBasicType(u'animType', 2, u'IsHand2Hand')
    IsPistolBallistic1Hand = CBashBasicType(u'animType', 3, u'IsHand2Hand')
    IsPistolEnergy1Hand = CBashBasicType(u'animType', 4, u'IsHand2Hand')
    IsRifleBallistic2Hand = CBashBasicType(u'animType', 5, u'IsHand2Hand')
    IsRifleAutomatic2Hand = CBashBasicType(u'animType', 6, u'IsHand2Hand')
    IsRifleEnergy2Hand = CBashBasicType(u'animType', 7, u'IsHand2Hand')
    IsHandle2Hand = CBashBasicType(u'animType', 8, u'IsHand2Hand')
    IsLauncher2Hand = CBashBasicType(u'animType', 9, u'IsHand2Hand')
    IsGrenadeThrow1Hand = CBashBasicType(u'animType', 10, u'IsHand2Hand')
    IsLandMine1Hand = CBashBasicType(u'animType', 11, u'IsHand2Hand')
    IsMineDrop1Hand = CBashBasicType(u'animType', 12, u'IsHand2Hand')
    IsThrown1Hand = CBashBasicType(u'animType', 13, u'IsHand2Hand')

    IsHandGrip1 = CBashBasicType(u'gripAnim', 230, u'IsHandGrip2')
    IsHandGrip2 = CBashBasicType(u'gripAnim', 231, u'IsHandGrip1')
    IsHandGrip3 = CBashBasicType(u'gripAnim', 232, u'IsHandGrip1')
    IsHandGrip4 = CBashBasicType(u'gripAnim', 233, u'IsHandGrip1')
    IsHandGrip5 = CBashBasicType(u'gripAnim', 234, u'IsHandGrip1')
    IsHandGrip6 = CBashBasicType(u'gripAnim', 235, u'IsHandGrip1')
    IsHandGripDefault = CBashBasicType(u'gripAnim', 236, u'IsHandGrip1')

    IsReloadA = CBashBasicType(u'reloadAnim', 0, u'IsReloadB')
    IsReloadB = CBashBasicType(u'reloadAnim', 1, u'IsReloadA')
    IsReloadC = CBashBasicType(u'reloadAnim', 2, u'IsReloadA')
    IsReloadD = CBashBasicType(u'reloadAnim', 3, u'IsReloadA')
    IsReloadE = CBashBasicType(u'reloadAnim', 4, u'IsReloadA')
    IsReloadF = CBashBasicType(u'reloadAnim', 5, u'IsReloadA')
    IsReloadG = CBashBasicType(u'reloadAnim', 6, u'IsReloadA')
    IsReloadH = CBashBasicType(u'reloadAnim', 7, u'IsReloadA')
    IsReloadI = CBashBasicType(u'reloadAnim', 8, u'IsReloadA')
    IsReloadJ = CBashBasicType(u'reloadAnim', 9, u'IsReloadA')
    IsReloadK = CBashBasicType(u'reloadAnim', 10, u'IsReloadA')
    IsReloadL = CBashBasicType(u'reloadAnim', 11, u'IsReloadA')
    IsReloadM = CBashBasicType(u'reloadAnim', 12, u'IsReloadA')
    IsReloadN = CBashBasicType(u'reloadAnim', 13, u'IsReloadA')
    IsReloadO = CBashBasicType(u'reloadAnim', 14, u'IsReloadA')
    IsReloadP = CBashBasicType(u'reloadAnim', 15, u'IsReloadA')
    IsReloadQ = CBashBasicType(u'reloadAnim', 16, u'IsReloadA')
    IsReloadR = CBashBasicType(u'reloadAnim', 17, u'IsReloadA')
    IsReloadS = CBashBasicType(u'reloadAnim', 18, u'IsReloadA')
    IsReloadW = CBashBasicType(u'reloadAnim', 19, u'IsReloadA')
    IsReloadX = CBashBasicType(u'reloadAnim', 20, u'IsReloadA')
    IsReloadY = CBashBasicType(u'reloadAnim', 21, u'IsReloadA')
    IsReloadZ = CBashBasicType(u'reloadAnim', 22, u'IsReloadA')

    IsAttackLeft = CBashBasicType(u'attackAnim', 26, u'IsAttackRight')
    IsAttackRight = CBashBasicType(u'attackAnim', 32, u'IsAttackLeft')
    IsAttack3 = CBashBasicType(u'attackAnim', 38, u'IsAttackLeft')
    IsAttack4 = CBashBasicType(u'attackAnim', 44, u'IsAttackLeft')
    IsAttack5 = CBashBasicType(u'attackAnim', 50, u'IsAttackLeft')
    IsAttack6 = CBashBasicType(u'attackAnim', 56, u'IsAttackLeft')
    IsAttack7 = CBashBasicType(u'attackAnim', 62, u'IsAttackLeft')
    IsAttack8 = CBashBasicType(u'attackAnim', 68, u'IsAttackLeft')
    IsAttack9 = CBashBasicType(u'attackAnim', 144, u'IsAttackLeft')
    IsAttackLoop = CBashBasicType(u'attackAnim', 74, u'IsAttackLeft')
    IsAttackSpin = CBashBasicType(u'attackAnim', 80, u'IsAttackLeft')
    IsAttackSpin2 = CBashBasicType(u'attackAnim', 86, u'IsAttackLeft')
    IsAttackThrow = CBashBasicType(u'attackAnim', 114, u'IsAttackLeft')
    IsAttackThrow2 = CBashBasicType(u'attackAnim', 120, u'IsAttackLeft')
    IsAttackThrow3 = CBashBasicType(u'attackAnim', 126, u'IsAttackLeft')
    IsAttackThrow4 = CBashBasicType(u'attackAnim', 132, u'IsAttackLeft')
    IsAttackThrow5 = CBashBasicType(u'attackAnim', 138, u'IsAttackLeft')
    IsAttackThrow6 = CBashBasicType(u'attackAnim', 150, u'IsAttackLeft')
    IsAttackThrow7 = CBashBasicType(u'attackAnim', 156, u'IsAttackLeft')
    IsAttackThrow8 = CBashBasicType(u'attackAnim', 162, u'IsAttackLeft')
    IsPlaceMine = CBashBasicType(u'attackAnim', 102, u'IsAttackLeft')
    IsPlaceMine2 = CBashBasicType(u'attackAnim', 108, u'IsAttackLeft')
    IsAttackDefault = CBashBasicType(u'attackAnim', 255, u'IsAttackLeft')

    IsNormalFormulaBehavior = CBashBasicType(u'weaponAV', 0, u'IsDismemberOnly')
    IsDismemberOnly = CBashBasicType(u'weaponAV', 1, u'IsNormalFormulaBehavior')
    IsExplodeOnly = CBashBasicType(u'weaponAV', 2, u'IsNormalFormulaBehavior')
    IsNoDismemberExplode = CBashBasicType(u'weaponAV', 3, u'IsNormalFormulaBehavior')
    IsDismemberExplode = CBashInvertedFlag(u'IsNoDismemberExplode')

    IsOnHitPerception = CBashBasicType(u'onHit', 0, u'IsEndurance')
    IsOnHitEndurance = CBashBasicType(u'onHit', 1, u'IsPerception')
    IsOnHitLeftAttack = CBashBasicType(u'onHit', 2, u'IsPerception')
    IsOnHitRightAttack = CBashBasicType(u'onHit', 3, u'IsPerception')
    IsOnHitLeftMobility = CBashBasicType(u'onHit', 4, u'IsPerception')
    IsOnHitRightMobilty = CBashBasicType(u'onHit', 5, u'IsPerception')
    IsOnHitBrain = CBashBasicType(u'onHit', 6, u'IsPerception')

    IsRumbleConstant = CBashBasicType(u'rumbleType', 0, u'IsSquare')
    IsRumbleSquare = CBashBasicType(u'rumbleType', 1, u'IsConstant')
    IsRumbleTriangle = CBashBasicType(u'rumbleType', 2, u'IsConstant')
    IsRumbleSawtooth = CBashBasicType(u'rumbleType', 3, u'IsConstant')

    IsUnknown0 = CBashBasicType(u'overridePwrAtkAnim', 0, u'IsAttackCustom1Power')
    IsAttackCustom1Power = CBashBasicType(u'overridePwrAtkAnim', 97, u'IsAttackCustom2Power')
    IsAttackCustom2Power = CBashBasicType(u'overridePwrAtkAnim', 98, u'IsAttackCustom1Power')
    IsAttackCustom3Power = CBashBasicType(u'overridePwrAtkAnim', 99, u'IsAttackCustom1Power')
    IsAttackCustom4Power = CBashBasicType(u'overridePwrAtkAnim', 100, u'IsAttackCustom1Power')
    IsAttackCustom5Power = CBashBasicType(u'overridePwrAtkAnim', 101, u'IsAttackCustom1Power')
    IsAttackCustomDefault = CBashBasicType(u'overridePwrAtkAnim', 255, u'IsAttackCustom1Power')

    IsModReloadA = CBashBasicType(u'reloadAnimMod', 0, u'IsModReloadB')
    IsModReloadB = CBashBasicType(u'reloadAnimMod', 1, u'IsModReloadA')
    IsModReloadC = CBashBasicType(u'reloadAnimMod', 2, u'IsModReloadA')
    IsModReloadD = CBashBasicType(u'reloadAnimMod', 3, u'IsModReloadA')
    IsModReloadE = CBashBasicType(u'reloadAnimMod', 4, u'IsModReloadA')
    IsModReloadF = CBashBasicType(u'reloadAnimMod', 5, u'IsModReloadA')
    IsModReloadG = CBashBasicType(u'reloadAnimMod', 6, u'IsModReloadA')
    IsModReloadH = CBashBasicType(u'reloadAnimMod', 7, u'IsModReloadA')
    IsModReloadI = CBashBasicType(u'reloadAnimMod', 8, u'IsModReloadA')
    IsModReloadJ = CBashBasicType(u'reloadAnimMod', 9, u'IsModReloadA')
    IsModReloadK = CBashBasicType(u'reloadAnimMod', 10, u'IsModReloadA')
    IsModReloadL = CBashBasicType(u'reloadAnimMod', 11, u'IsModReloadA')
    IsModReloadM = CBashBasicType(u'reloadAnimMod', 12, u'IsModReloadA')
    IsModReloadN = CBashBasicType(u'reloadAnimMod', 13, u'IsModReloadA')
    IsModReloadO = CBashBasicType(u'reloadAnimMod', 14, u'IsModReloadA')
    IsModReloadP = CBashBasicType(u'reloadAnimMod', 15, u'IsModReloadA')
    IsModReloadQ = CBashBasicType(u'reloadAnimMod', 16, u'IsModReloadA')
    IsModReloadR = CBashBasicType(u'reloadAnimMod', 17, u'IsModReloadA')
    IsModReloadS = CBashBasicType(u'reloadAnimMod', 18, u'IsModReloadA')
    IsModReloadW = CBashBasicType(u'reloadAnimMod', 19, u'IsModReloadA')
    IsModReloadX = CBashBasicType(u'reloadAnimMod', 20, u'IsModReloadA')
    IsModReloadY = CBashBasicType(u'reloadAnimMod', 21, u'IsModReloadA')
    IsModReloadZ = CBashBasicType(u'reloadAnimMod', 22, u'IsModReloadA')

    IsVATSNotSilent = CBashBasicType(u'silenceType', 0, u'IsVATSSilent')
    IsVATSSilent = CBashBasicType(u'silenceType', 1, u'IsVATSNotSilent')

    IsVATSNotModRequired = CBashBasicType(u'modRequiredType', 0, u'IsVATSNotModRequired')
    IsVATSModRequired = CBashBasicType(u'modRequiredType', 1, u'IsVATSModRequired')

    IsLoud = CBashBasicType(u'soundLevelType', 0, u'IsNormal')
    IsNormal = CBashBasicType(u'soundLevelType', 1, u'IsLoud')
    IsSilent = CBashBasicType(u'soundLevelType', 2, u'IsLoud')
    copyattrs = FnvBaseRecord.baseattrs + [
        u'boundX1', u'boundY1', u'boundZ1', u'boundX2', u'boundY2', u'boundZ2',
        u'full', u'modPath', u'modb', u'modt_p', u'altTextures_list',
        u'modelFlags', u'iconPath', u'smallIconPath', u'script', u'effect',
        u'chargeAmount', u'ammo', u'destructable_list', u'repairList',
        u'equipmentType', u'modelList', u'pickupSound', u'dropSound',
        u'shell_list', u'scope_list', u'scopeEffect', u'world_list',
        u'vatsName', u'weaponNode', u'model1Path', u'model2Path',
        u'model12Path', u'model3Path', u'model13Path', u'model23Path',
        u'model123Path', u'impact', u'model', u'model1', u'model2', u'model12',
        u'model3', u'model13', u'model23', u'model123', u'mod1', u'mod2',
        u'mod3', u'sound3D', u'soundDist', u'sound2D', u'sound3DLoop',
        u'soundMelee', u'soundBlock', u'soundIdle', u'soundEquip',
        u'soundUnequip', u'soundMod3D', u'soundModDist', u'soundMod2D',
        u'value', u'health', u'weight', u'damage', u'clipSize', u'animType',
        u'animMult', u'reach', u'flags', u'gripAnim', u'ammoUse',
        u'reloadAnim', u'minSpread', u'spread', u'unknown1', u'sightFOV',
        u'unknown2', u'projectile', u'VATSHitChance', u'attackAnim',
        u'projectileCount', u'weaponAV', u'minRange', u'maxRange', u'onHit',
        u'extraFlags', u'animAttackMult', u'fireRate', u'overrideAP',
        u'leftRumble', u'timeRumble', u'overrideDamageToWeapon', u'reloadTime',
        u'jamTime', u'aimArc', u'skill', u'rumbleType', u'rumbleWavelength',
        u'limbDamageMult', u'resistType', u'sightUsage', u'semiFireDelayMin',
        u'semiFireDelayMax', u'unknown3', u'effectMod1', u'effectMod2',
        u'effectMod3', u'valueAMod1', u'valueAMod2', u'valueAMod3',
        u'overridePwrAtkAnim', u'strengthReq', u'unknown4', u'reloadAnimMod',
        u'unknown5', u'regenRate', u'killImpulse', u'valueBMod1',
        u'valueBMod2', u'valueBMod3', u'skillReq', u'critDamage', u'critMult',
        u'critFlags', u'critEffect', u'vatsEffect', u'vatsSkill',
        u'vatsDamageMult', u'AP', u'silenceType', u'modRequiredType',
        u'soundLevelType']
    exportattrs = copyattrs[:]
    exportattrs.remove(u'modt_p')
    exportattrs.remove(u'unknown1')
    exportattrs.remove(u'unknown2')
    exportattrs.remove(u'unknown3')
    exportattrs.remove(u'unknown4')
    exportattrs.remove(u'unknown5')

class FnvAMMORecord(FnvBaseRecord):
    __slots__ = []
    _Type = b'AMMO'
    boundX1 = CBashGeneric(7, c_short)
    boundY1 = CBashGeneric(8, c_short)
    boundZ1 = CBashGeneric(9, c_short)
    boundX2 = CBashGeneric(10, c_short)
    boundY2 = CBashGeneric(11, c_short)
    boundZ2 = CBashGeneric(12, c_short)
    full = CBashSTRING(13)
    modPath = CBashISTRING(14)
    modb = CBashFLOAT32(15)
    modt_p = CBashUINT8ARRAY(16)

    def create_altTexture(self):
        length = _CGetFieldAttribute(self._RecordID, 17, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 17, 0, 0, 0, 0, 0, 0, 0, c_ulong(length +
                                                                    1))
        return FNVAltTexture(self._RecordID, 17, length)
    altTextures = CBashLIST(17, FNVAltTexture)
    altTextures_list = CBashLIST(17, FNVAltTexture, True)

    modelFlags = CBashGeneric(18, c_ubyte)
    iconPath = CBashISTRING(19)
    smallIconPath = CBashISTRING(20)
    script = CBashFORMID(21)
    destructable = CBashGrouped(22, FNVDestructable)
    destructable_list = CBashGrouped(22, FNVDestructable, True)

    pickupSound = CBashFORMID(27)
    dropSound = CBashFORMID(28)
    speed = CBashFLOAT32(29)
    flags = CBashGeneric(30, c_ubyte)
    unused1 = CBashUINT8ARRAY(31, 3)
    value = CBashGeneric(32, c_long)
    clipRounds = CBashGeneric(33, c_ubyte)
    projectilesPerShot = CBashGeneric(34, c_ulong)
    projectile = CBashFORMID(35)
    weight = CBashFLOAT32(36)
    consumedAmmo = CBashFORMID(37)
    consumedPercentage = CBashFLOAT32(38)
    shortName = CBashSTRING(39)
    abbreviation = CBashSTRING(40)
    effects = CBashFORMIDARRAY(41)

    IsNotNormalWeapon = CBashBasicFlag(u'flags', 0x01)
    IsNormalWeapon = CBashInvertedFlag(u'IsNotNormalWeapon')
    IsNonPlayable = CBashBasicFlag(u'flags', 0x02)
    IsPlayable = CBashInvertedFlag(u'IsNonPlayable')

    IsHead = CBashBasicFlag(u'modelFlags', 0x01)
    IsTorso = CBashBasicFlag(u'modelFlags', 0x02)
    IsRightHand = CBashBasicFlag(u'modelFlags', 0x04)
    IsLeftHand = CBashBasicFlag(u'modelFlags', 0x08)
    copyattrs = FnvBaseRecord.baseattrs + [u'boundX1', u'boundY1', u'boundZ1',
                                           u'boundX2', u'boundY2', u'boundZ2',
                                           u'full', u'modPath', u'modb', u'modt_p',
                                           u'altTextures_list', u'modelFlags',
                                           u'iconPath', u'smallIconPath', u'script',
                                           u'destructable_list', u'pickupSound',
                                           u'dropSound', u'speed', u'flags',
                                           u'value', u'clipRounds',
                                           u'projectilesPerShot', u'projectile',
                                           u'weight', u'consumedAmmo',
                                           u'consumedPercentage', u'shortName',
                                           u'abbreviation', u'effects']
    exportattrs = copyattrs[:]
    exportattrs.remove(u'modt_p')

class FnvNPC_Record(FnvBaseRecord):
    __slots__ = []
    _Type = b'NPC_'
    def mergeFilter(self, target):
        """Filter out items that don't come from specified modSet.
        Filters items."""
        self.items = [x for x in self.items if x.item.ValidateFormID(target)]

    boundX1 = CBashGeneric(7, c_short)
    boundY1 = CBashGeneric(8, c_short)
    boundZ1 = CBashGeneric(9, c_short)
    boundX2 = CBashGeneric(10, c_short)
    boundY2 = CBashGeneric(11, c_short)
    boundZ2 = CBashGeneric(12, c_short)
    full = CBashSTRING(13)
    modPath = CBashISTRING(14)
    modb = CBashFLOAT32(15)
    modt_p = CBashUINT8ARRAY(16)

    def create_altTexture(self):
        length = _CGetFieldAttribute(self._RecordID, 17, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 17, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return FNVAltTexture(self._RecordID, 17, length)
    altTextures = CBashLIST(17, FNVAltTexture)
    altTextures_list = CBashLIST(17, FNVAltTexture, True)

    modelFlags = CBashGeneric(18, c_ubyte)
    flags = CBashGeneric(19, c_ulong)
    fatigue = CBashGeneric(20, c_ushort)
    barterGold = CBashGeneric(21, c_ushort)
    level = CBashGeneric(22, c_short)
    calcMin = CBashGeneric(23, c_ushort)
    calcMax = CBashGeneric(24, c_ushort)
    speedMult = CBashGeneric(25, c_ushort)
    karma = CBashFLOAT32(26)
    dispBase = CBashGeneric(27, c_short)
    templateFlags = CBashGeneric(28, c_ushort)

    def create_faction(self):
        length = _CGetFieldAttribute(self._RecordID, 29, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 29, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return Faction(self._RecordID, 29, length)
    factions = CBashLIST(29, Faction)
    factions_list = CBashLIST(29, Faction, True)

    deathItem = CBashFORMID(30)
    voice = CBashFORMID(31)
    template = CBashFORMID(32)
    race = CBashFORMID(33)
    actorEffects = CBashFORMIDARRAY(34)
    unarmedEffect = CBashFORMID(35)
    unarmedAnim = CBashGeneric(36, c_ushort)
    destructable = CBashGrouped(37, FNVDestructable)
    destructable_list = CBashGrouped(37, FNVDestructable, True)

    script = CBashFORMID(42)

    def create_item(self):
        length = _CGetFieldAttribute(self._RecordID, 43, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 43, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return FNVItem(self._RecordID, 43, length)
    items = CBashLIST(43, FNVItem)
    items_list = CBashLIST(43, FNVItem, True)

    aggression = CBashGeneric(44, c_ubyte)
    confidence = CBashGeneric(45, c_ubyte)
    energyLevel = CBashGeneric(46, c_ubyte)
    responsibility = CBashGeneric(47, c_ubyte)
    mood = CBashGeneric(48, c_ubyte)
    unused1 = CBashUINT8ARRAY(49, 3)
    services = CBashGeneric(50, c_ulong)
    trainSkill = CBashGeneric(51, c_byte)
    trainLevel = CBashGeneric(52, c_ubyte)
    assistance = CBashGeneric(53, c_ubyte)
    aggroFlags = CBashGeneric(54, c_ubyte)
    aggroRadius = CBashGeneric(55, c_long)
    aiPackages = CBashFORMIDARRAY(56)
    iclass = CBashFORMID(57)
    baseHealth = CBashGeneric(58, c_long)
    strength = CBashGeneric(59, c_ubyte)
    perception = CBashGeneric(60, c_ubyte)
    endurance = CBashGeneric(61, c_ubyte)
    charisma = CBashGeneric(62, c_ubyte)
    intelligence = CBashGeneric(63, c_ubyte)
    agility = CBashGeneric(64, c_ubyte)
    luck = CBashGeneric(65, c_ubyte)
    barter = CBashGeneric(66, c_ubyte)
    bigGuns = CBashGeneric(67, c_ubyte)
    energy = CBashGeneric(68, c_ubyte)
    explosives = CBashGeneric(69, c_ubyte)
    lockpick = CBashGeneric(70, c_ubyte)
    medicine = CBashGeneric(71, c_ubyte)
    melee = CBashGeneric(72, c_ubyte)
    repair = CBashGeneric(73, c_ubyte)
    science = CBashGeneric(74, c_ubyte)
    guns = CBashGeneric(75, c_ubyte)
    sneak = CBashGeneric(76, c_ubyte)
    speech = CBashGeneric(77, c_ubyte)
    survival = CBashGeneric(78, c_ubyte)
    unarmed = CBashGeneric(79, c_ubyte)
    barterBoost = CBashGeneric(80, c_ubyte)
    bigGunsBoost = CBashGeneric(81, c_ubyte)
    energyBoost = CBashGeneric(82, c_ubyte)
    explosivesBoost = CBashGeneric(83, c_ubyte)
    lockpickBoost = CBashGeneric(84, c_ubyte)
    medicineBoost = CBashGeneric(85, c_ubyte)
    meleeBoost = CBashGeneric(86, c_ubyte)
    repairBoost = CBashGeneric(87, c_ubyte)
    scienceBoost = CBashGeneric(88, c_ubyte)
    gunsBoost = CBashGeneric(89, c_ubyte)
    sneakBoost = CBashGeneric(90, c_ubyte)
    speechBoost = CBashGeneric(91, c_ubyte)
    survivalBoost = CBashGeneric(92, c_ubyte)
    unarmedBoost = CBashGeneric(93, c_ubyte)
    headParts = CBashFORMIDARRAY(94)
    hair = CBashFORMID(95)
    hairLength = CBashFLOAT32(96)
    eyes = CBashFORMID(97)
    hairRed = CBashGeneric(98, c_ubyte)
    hairGreen = CBashGeneric(99, c_ubyte)
    hairBlue = CBashGeneric(100, c_ubyte)
    unused2 = CBashUINT8ARRAY(101, 1)
    combatStyle = CBashFORMID(102)
    impactType = CBashGeneric(103, c_ulong)
    fggs_p = CBashUINT8ARRAY(104, 200)
    fgga_p = CBashUINT8ARRAY(105, 120)
    fgts_p = CBashUINT8ARRAY(106, 200)
    unknown = CBashGeneric(107, c_ushort)
    height = CBashFLOAT32(108)
    weight = CBashFLOAT32(109)

    IsFemale = CBashBasicFlag(u'flags', 0x00000001)
    IsEssential = CBashBasicFlag(u'flags', 0x00000002)
    IsCharGenFacePreset = CBashBasicFlag(u'flags', 0x00000004)
    IsRespawn = CBashBasicFlag(u'flags', 0x00000008)
    IsAutoCalcStats = CBashBasicFlag(u'flags', 0x00000010)
    IsPCLevelOffset = CBashBasicFlag(u'flags', 0x00000080)
    IsUseTemplate = CBashBasicFlag(u'flags', 0x00000100)
    IsNoLowLevel = CBashBasicFlag(u'flags', 0x00000200)
    IsNoBloodSpray = CBashBasicFlag(u'flags', 0x00000800)
    IsNoBloodDecal = CBashBasicFlag(u'flags', 0x00001000)
    IsNoVATSMelee = CBashBasicFlag(u'flags', 0x00100000)
    IsCanBeAllRaces = CBashBasicFlag(u'flags', 0x00400000)
    IsAutoCalcService = CBashBasicFlag(u'flags', 0x00800000)
    IsNoKnockdowns = CBashBasicFlag(u'flags', 0x03000000)
    IsNotPushable = CBashBasicFlag(u'flags', 0x08000000)
    IsNoHeadTracking = CBashBasicFlag(u'flags', 0x40000000)

    IsUseTraits = CBashBasicFlag(u'templateFlags', 0x00000001)
    IsUseStats = CBashBasicFlag(u'templateFlags', 0x00000002)
    IsUseFactions = CBashBasicFlag(u'templateFlags', 0x00000004)
    IsUseAEList = CBashBasicFlag(u'templateFlags', 0x00000008)
    IsUseAIData = CBashBasicFlag(u'templateFlags', 0x00000010)
    IsUseAIPackages = CBashBasicFlag(u'templateFlags', 0x00000020)
    IsUseModelAnim = CBashBasicFlag(u'templateFlags', 0x00000040)
    IsUseBaseData = CBashBasicFlag(u'templateFlags', 0x00000080)
    IsUseInventory = CBashBasicFlag(u'templateFlags', 0x00000100)
    IsUseScript = CBashBasicFlag(u'templateFlags', 0x00000200)

    IsAggroRadiusBehavior = CBashBasicFlag(u'aggroFlags', 0x01)

    IsHead = CBashBasicFlag(u'modelFlags', 0x01)
    IsTorso = CBashBasicFlag(u'modelFlags', 0x02)
    IsRightHand = CBashBasicFlag(u'modelFlags', 0x04)
    IsLeftHand = CBashBasicFlag(u'modelFlags', 0x08)

    IsUnaggressive = CBashBasicType(u'aggression', 0, u'IsAggressive')
    IsAggressive = CBashBasicType(u'aggression', 1, u'IsUnaggressive')
    IsVeryAggressive = CBashBasicType(u'aggression', 2, u'IsUnaggressive')
    IsFrenzied = CBashBasicType(u'aggression', 3, u'IsUnaggressive')

    IsCowardly = CBashBasicType(u'confidence', 0, u'IsCautious')
    IsCautious = CBashBasicType(u'confidence', 1, u'IsCowardly')
    IsAverage = CBashBasicType(u'confidence', 2, u'IsCowardly')
    IsBrave = CBashBasicType(u'confidence', 3, u'IsCowardly')
    IsFoolhardy = CBashBasicType(u'confidence', 4, u'IsCowardly')

    IsNeutral = CBashBasicType(u'mood', 0, u'IsAfraid')
    IsAfraid = CBashBasicType(u'mood', 1, u'IsNeutral')
    IsAnnoyed = CBashBasicType(u'mood', 2, u'IsNeutral')
    IsCocky = CBashBasicType(u'mood', 3, u'IsNeutral')
    IsDrugged = CBashBasicType(u'mood', 4, u'IsNeutral')
    IsPleasant = CBashBasicType(u'mood', 5, u'IsNeutral')
    IsAngry = CBashBasicType(u'mood', 6, u'IsNeutral')
    IsSad = CBashBasicType(u'mood', 7, u'IsNeutral')

    IsHelpsNobody = CBashBasicType(u'assistance', 0, u'IsHelpsAllies')
    IsHelpsAllies = CBashBasicType(u'assistance', 1, u'IsHelpsNobody')
    IsHelpsFriendsAndAllies = CBashBasicType(u'assistance', 2, u'IsHelpsNobody')

    IsStone = CBashBasicType(u'impactType', 0, u'IsDirt')
    IsDirt = CBashBasicType(u'impactType', 1, u'IsStone')
    IsGrass = CBashBasicType(u'impactType', 2, u'IsStone')
    IsGlass = CBashBasicType(u'impactType', 3, u'IsStone')
    IsMetal = CBashBasicType(u'impactType', 4, u'IsStone')
    IsWood = CBashBasicType(u'impactType', 5, u'IsStone')
    IsOrganic = CBashBasicType(u'impactType', 6, u'IsStone')
    IsCloth = CBashBasicType(u'impactType', 7, u'IsStone')
    IsWater = CBashBasicType(u'impactType', 8, u'IsStone')
    IsHollowMetal = CBashBasicType(u'impactType', 9, u'IsStone')
    IsOrganicBug = CBashBasicType(u'impactType', 10, u'IsStone')
    IsOrganicGlow = CBashBasicType(u'impactType', 11, u'IsStone')
    copyattrs = FnvBaseRecord.baseattrs + [
        u'boundX1', u'boundY1', u'boundZ1', u'boundX2', u'boundY2', u'boundZ2',
        u'full', u'modPath', u'modb', u'modt_p', u'altTextures_list',
        u'modelFlags', u'flags', u'fatigue', u'barterGold', u'level',
        u'calcMin', u'calcMax', u'speedMult', u'karma', u'dispBase',
        u'templateFlags', u'factions_list', u'deathItem', u'voice',
        u'template', u'race', u'actorEffects', u'unarmedEffect',
        u'unarmedAnim', u'destructable_list', u'script', u'items_list',
        u'aggression', u'confidence', u'energyLevel', u'responsibility',
        u'mood', u'services', u'trainSkill', u'trainLevel', u'assistance',
        u'aggroFlags', u'aggroRadius', u'aiPackages', u'iclass', u'baseHealth',
        u'strength', u'perception', u'endurance', u'charisma', u'intelligence',
        u'agility', u'luck', u'barter', u'bigGuns', u'energy', u'explosives',
        u'lockpick', u'medicine', u'melee', u'repair', u'science', u'guns',
        u'sneak', u'speech', u'survival', u'unarmed', u'barterBoost',
        u'bigGunsBoost', u'energyBoost', u'explosivesBoost', u'lockpickBoost',
        u'medicineBoost', u'meleeBoost', u'repairBoost', u'scienceBoost',
        u'gunsBoost', u'sneakBoost', u'speechBoost', u'survivalBoost',
        u'unarmedBoost', u'headParts', u'hair', u'hairLength', u'eyes',
        u'hairRed', u'hairGreen', u'hairBlue', u'combatStyle', u'impactType',
        u'fggs_p', u'fgga_p', u'fgts_p', u'unknown', u'height', u'weight']
    exportattrs = copyattrs[:]
    exportattrs.remove(u'modt_p')
    exportattrs.remove(u'fggs_p')
    exportattrs.remove(u'fgga_p')
    exportattrs.remove(u'fgts_p')
    exportattrs.remove(u'unknown')

class FnvCREARecord(FnvBaseRecord):
    __slots__ = []
    _Type = b'CREA'
    def mergeFilter(self, target):
        """Filter out items that don't come from specified modSet.
        Filters items."""
        self.items = [x for x in self.items if x.item.ValidateFormID(target)]

    class SoundType(ListComponent):
        __slots__ = []
        class Sound(ListX2Component):
            __slots__ = []
            sound = CBashFORMID_LISTX2(1)
            chance = CBashGeneric_LISTX2(2, c_ubyte)
            exportattrs = copyattrs = [u'sound', u'chance']

        soundType = CBashGeneric_LIST(1, c_ulong)
        def create_sound(self):
            length = _CGetFieldAttribute(self._RecordID, self._FieldID,
                                         self._ListIndex, 2, 0, 0, 0, 0, 1)
            _CSetField(self._RecordID, self._FieldID, self._ListIndex, 2, 0,
             0, 0, 0, 0, c_ulong(length + 1))
            return self.Sound(self._RecordID, self._FieldID,
            self._ListIndex, 2, length)
        sounds = CBashLIST_LIST(2, Sound)
        sounds_list = CBashLIST_LIST(2, Sound, True)


        IsLeftFoot = CBashBasicType(u'soundType', 0, u'IsRightFoot')
        IsRightFoot = CBashBasicType(u'soundType', 1, u'IsLeftFoot')
        IsLeftBackFoot = CBashBasicType(u'soundType', 2, u'IsLeftFoot')
        IsRightBackFoot = CBashBasicType(u'soundType', 3, u'IsLeftFoot')
        IsIdle = CBashBasicType(u'soundType', 4, u'IsLeftFoot')
        IsAware = CBashBasicType(u'soundType', 5, u'IsLeftFoot')
        IsAttack = CBashBasicType(u'soundType', 6, u'IsLeftFoot')
        IsHit = CBashBasicType(u'soundType', 7, u'IsLeftFoot')
        IsDeath = CBashBasicType(u'soundType', 8, u'IsLeftFoot')
        IsWeapon = CBashBasicType(u'soundType', 9, u'IsLeftFoot')
        IsMovementLoop = CBashBasicType(u'soundType', 10, u'IsLeftFoot')
        IsConsciousLoop = CBashBasicType(u'soundType', 11, u'IsLeftFoot')
        IsAuxiliary1 = CBashBasicType(u'soundType', 12, u'IsLeftFoot')
        IsAuxiliary2 = CBashBasicType(u'soundType', 13, u'IsLeftFoot')
        IsAuxiliary3 = CBashBasicType(u'soundType', 14, u'IsLeftFoot')
        IsAuxiliary4 = CBashBasicType(u'soundType', 15, u'IsLeftFoot')
        IsAuxiliary5 = CBashBasicType(u'soundType', 16, u'IsLeftFoot')
        IsAuxiliary6 = CBashBasicType(u'soundType', 17, u'IsLeftFoot')
        IsAuxiliary7 = CBashBasicType(u'soundType', 18, u'IsLeftFoot')
        IsAuxiliary8 = CBashBasicType(u'soundType', 19, u'IsLeftFoot')
        IsJump = CBashBasicType(u'soundType', 20, u'IsLeftFoot')
        IsPlayRandomLoop = CBashBasicType(u'soundType', 21, u'IsLeftFoot')
        exportattrs = copyattrs = [u'soundType', u'sounds_list']

    boundX1 = CBashGeneric(7, c_short)
    boundY1 = CBashGeneric(8, c_short)
    boundZ1 = CBashGeneric(9, c_short)
    boundX2 = CBashGeneric(10, c_short)
    boundY2 = CBashGeneric(11, c_short)
    boundZ2 = CBashGeneric(12, c_short)
    full = CBashSTRING(13)
    modPath = CBashISTRING(14)
    modb = CBashFLOAT32(15)
    modt_p = CBashUINT8ARRAY(16)

    def create_altTexture(self):
        length = _CGetFieldAttribute(self._RecordID, 17, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 17, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return FNVAltTexture(self._RecordID, 17, length)
    altTextures = CBashLIST(17, FNVAltTexture)
    altTextures_list = CBashLIST(17, FNVAltTexture, True)

    modelFlags = CBashGeneric(18, c_ubyte)
    actorEffects = CBashFORMIDARRAY(19)
    unarmedEffect = CBashFORMID(20)
    unarmedAnim = CBashGeneric(21, c_ushort)
    bodyParts = CBashISTRINGARRAY(22)
    nift_p = CBashUINT8ARRAY(23)
    flags = CBashGeneric(24, c_ulong)
    fatigue = CBashGeneric(25, c_ushort)
    barterGold = CBashGeneric(26, c_ushort)
    level = CBashGeneric(27, c_short)
    calcMin = CBashGeneric(28, c_ushort)
    calcMax = CBashGeneric(29, c_ushort)
    speedMult = CBashGeneric(30, c_ushort)
    karma = CBashFLOAT32(31)
    dispBase = CBashGeneric(32, c_short)
    templateFlags = CBashGeneric(33, c_ushort)
    def create_faction(self):
        length = _CGetFieldAttribute(self._RecordID, 34, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 34, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return Faction(self._RecordID, 34, length)
    factions = CBashLIST(34, Faction)
    factions_list = CBashLIST(34, Faction, True)

    deathItem = CBashFORMID(35)
    voice = CBashFORMID(36)
    template = CBashFORMID(37)
    destructable = CBashGrouped(38, FNVDestructable)
    destructable_list = CBashGrouped(38, FNVDestructable, True)

    script = CBashFORMID(43)

    def create_item(self):
        length = _CGetFieldAttribute(self._RecordID, 44, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 44, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return FNVItem(self._RecordID, 44, length)
    items = CBashLIST(44, FNVItem)
    items_list = CBashLIST(44, FNVItem, True)

    aggression = CBashGeneric(45, c_ubyte)
    confidence = CBashGeneric(46, c_ubyte)
    energyLevel = CBashGeneric(47, c_ubyte)
    responsibility = CBashGeneric(48, c_ubyte)
    mood = CBashGeneric(49, c_ubyte)
    unused1 = CBashUINT8ARRAY(50, 3)
    services = CBashGeneric(51, c_ulong)
    trainSkill = CBashGeneric(52, c_byte)
    trainLevel = CBashGeneric(53, c_ubyte)
    assistance = CBashGeneric(54, c_ubyte)
    aggroFlags = CBashGeneric(55, c_ubyte)
    aggroRadius = CBashGeneric(56, c_long)
    aiPackages = CBashFORMIDARRAY(57)
    animations = CBashISTRINGARRAY(58)
    creatureType = CBashGeneric(59, c_ubyte)
    combat = CBashGeneric(60, c_ubyte)
    magic = CBashGeneric(61, c_ubyte)
    stealth = CBashGeneric(62, c_ubyte)
    health = CBashGeneric(63, c_ushort)
    unused2 = CBashUINT8ARRAY(64, 2)
    attackDamage = CBashGeneric(65, c_short)
    strength = CBashGeneric(66, c_ubyte)
    perception = CBashGeneric(67, c_ubyte)
    endurance = CBashGeneric(68, c_ubyte)
    charisma = CBashGeneric(69, c_ubyte)
    intelligence = CBashGeneric(70, c_ubyte)
    agility = CBashGeneric(71, c_ubyte)
    luck = CBashGeneric(72, c_ubyte)
    attackReach = CBashGeneric(73, c_ubyte)
    combatStyle = CBashFORMID(74)
    partData = CBashFORMID(75)
    turningSpeed = CBashFLOAT32(76)
    baseScale = CBashFLOAT32(77)
    footWeight = CBashFLOAT32(78)
    impactType = CBashGeneric(79, c_ulong)
    soundLevel = CBashGeneric(80, c_ulong)
    inheritsSoundsFrom = CBashFORMID(81)

    def create_soundTyp(self):
        length = _CGetFieldAttribute(self._RecordID, 82, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 82, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return self.SoundType(self._RecordID, 82, length)
    soundTypes = CBashLIST(82, SoundType)
    soundTypes_list = CBashLIST(82, SoundType, True)

    impactData = CBashFORMID(83)
    meleeList = CBashFORMID(84)

    IsBiped = CBashBasicFlag(u'flags', 0x00000001)
    IsEssential = CBashBasicFlag(u'flags', 0x00000002)
    IsWeaponAndShield = CBashBasicFlag(u'flags', 0x00000004)
    IsRespawn = CBashBasicFlag(u'flags', 0x00000008)
    IsSwims = CBashBasicFlag(u'flags', 0x00000010)
    IsFlies = CBashBasicFlag(u'flags', 0x00000020)
    IsWalks = CBashBasicFlag(u'flags', 0x00000040)
    IsPCLevelOffset = CBashBasicFlag(u'flags', 0x00000080)
    IsUnknown1 = CBashBasicFlag(u'flags', 0x00000100)
    IsNoLowLevel = CBashBasicFlag(u'flags', 0x00000200)
    IsLowLevel = CBashInvertedFlag(u'IsNoLowLevel')
    IsNoBloodSpray = CBashBasicFlag(u'flags', 0x00000800)
    IsBloodSpray = CBashInvertedFlag(u'IsNoBloodSpray')
    IsNoBloodDecal = CBashBasicFlag(u'flags', 0x00001000)
    IsBloodDecal = CBashInvertedFlag(u'IsNoBloodDecal')
    IsNoHead = CBashBasicFlag(u'flags', 0x00008000)
    IsHead = CBashInvertedFlag(u'IsNoHead')
    IsNoRightArm = CBashBasicFlag(u'flags', 0x00010000)
    IsRightArm = CBashInvertedFlag(u'IsNoRightArm')
    IsNoLeftArm = CBashBasicFlag(u'flags', 0x00020000)
    IsLeftArm = CBashInvertedFlag(u'IsNoLeftArm')
    IsNoCombatInWater = CBashBasicFlag(u'flags', 0x00040000)
    IsCombatInWater = CBashInvertedFlag(u'IsNoCombatInWater')
    IsNoShadow = CBashBasicFlag(u'flags', 0x00080000)
    IsShadow = CBashInvertedFlag(u'IsNoShadow')
    IsNoVATSMelee = CBashBasicFlag(u'flags', 0x00100000)
    IsVATSMelee = CBashInvertedFlag(u'IsNoVATSMelee')
    IsAllowPCDialogue = CBashBasicFlag(u'flags', 0x00200000)
    IsCantOpenDoors = CBashBasicFlag(u'flags', 0x00400000)
    IsCanOpenDoors = CBashInvertedFlag(u'IsCantOpenDoors')
    IsImmobile = CBashBasicFlag(u'flags', 0x00800000)
    IsTiltFrontBack = CBashBasicFlag(u'flags', 0x01000000)
    IsTiltLeftRight = CBashBasicFlag(u'flags', 0x02000000)
    IsNoKnockdowns = CBashBasicFlag(u'flags', 0x03000000)
    IsKnockdowns = CBashInvertedFlag(u'IsNoKnockdowns')
    IsNotPushable = CBashBasicFlag(u'flags', 0x08000000)
    IsPushable = CBashInvertedFlag(u'IsNotPushable')
    IsAllowPickpocket = CBashBasicFlag(u'flags', 0x10000000)
    IsGhost = CBashBasicFlag(u'flags', 0x20000000)
    IsNoHeadTracking = CBashBasicFlag(u'flags', 0x40000000)
    IsHeadTracking = CBashInvertedFlag(u'IsNoHeadTracking')
    IsInvulnerable = CBashBasicFlag(u'flags', 0x80000000)

    IsUseTraits = CBashBasicFlag(u'templateFlags', 0x00000001)
    IsUseStats = CBashBasicFlag(u'templateFlags', 0x00000002)
    IsUseFactions = CBashBasicFlag(u'templateFlags', 0x00000004)
    IsUseAEList = CBashBasicFlag(u'templateFlags', 0x00000008)
    IsUseAIData = CBashBasicFlag(u'templateFlags', 0x00000010)
    IsUseAIPackages = CBashBasicFlag(u'templateFlags', 0x00000020)
    IsUseModelAnim = CBashBasicFlag(u'templateFlags', 0x00000040)
    IsUseBaseData = CBashBasicFlag(u'templateFlags', 0x00000080)
    IsUseInventory = CBashBasicFlag(u'templateFlags', 0x00000100)
    IsUseScript = CBashBasicFlag(u'templateFlags', 0x00000200)

    IsAggroRadiusBehavior = CBashBasicFlag(u'aggroFlags', 0x01)

    IsServicesWeapons = CBashBasicFlag(u'services', 0x00000001)
    IsServicesArmor = CBashBasicFlag(u'services', 0x00000002)
    IsServicesClothing = CBashBasicFlag(u'services', 0x00000004)
    IsServicesBooks = CBashBasicFlag(u'services', 0x00000008)
    IsServicesIngredients = CBashBasicFlag(u'services', 0x00000010)
    IsServicesLights = CBashBasicFlag(u'services', 0x00000080)
    IsServicesApparatus = CBashBasicFlag(u'services', 0x00000100)
    IsServicesMiscItems = CBashBasicFlag(u'services', 0x00000400)
    IsServicesSpells = CBashBasicFlag(u'services', 0x00000800)
    IsServicesMagicItems = CBashBasicFlag(u'services', 0x00001000)
    IsServicesPotions = CBashBasicFlag(u'services', 0x00002000)
    IsServicesTraining = CBashBasicFlag(u'services', 0x00004000)
    IsServicesRecharge = CBashBasicFlag(u'services', 0x00010000)
    IsServicesRepair = CBashBasicFlag(u'services', 0x00020000)

    IsHead = CBashBasicFlag(u'modelFlags', 0x01)
    IsTorso = CBashBasicFlag(u'modelFlags', 0x02)
    IsRightHand = CBashBasicFlag(u'modelFlags', 0x04)
    IsLeftHand = CBashBasicFlag(u'modelFlags', 0x08)

    IsAnimal = CBashBasicType(u'creatureType', 0, u'IsMutatedAnimal')
    IsMutatedAnimal = CBashBasicType(u'creatureType', 1, u'IsAnimal')
    IsMutatedInsect = CBashBasicType(u'creatureType', 2, u'IsAnimal')
    IsAbomination = CBashBasicType(u'creatureType', 3, u'IsAnimal')
    IsSuperMutant = CBashBasicType(u'creatureType', 4, u'IsAnimal')
    IsFeralGhoul = CBashBasicType(u'creatureType', 5, u'IsAnimal')
    IsRobot = CBashBasicType(u'creatureType', 6, u'IsAnimal')
    IsGiant = CBashBasicType(u'creatureType', 7, u'IsAnimal')

    IsLoud = CBashBasicType(u'soundLevel', 0, u'IsNormal')
    IsNormal = CBashBasicType(u'soundLevel', 1, u'IsLoud')
    IsSilent = CBashBasicType(u'soundLevel', 2, u'IsLoud')

    IsUnaggressive = CBashBasicType(u'aggression', 0, u'IsAggressive')
    IsAggressive = CBashBasicType(u'aggression', 1, u'IsUnaggressive')
    IsVeryAggressive = CBashBasicType(u'aggression', 2, u'IsUnaggressive')
    IsFrenzied = CBashBasicType(u'aggression', 3, u'IsUnaggressive')

    IsCowardly = CBashBasicType(u'confidence', 0, u'IsCautious')
    IsCautious = CBashBasicType(u'confidence', 1, u'IsCowardly')
    IsAverage = CBashBasicType(u'confidence', 2, u'IsCowardly')
    IsBrave = CBashBasicType(u'confidence', 3, u'IsCowardly')
    IsFoolhardy = CBashBasicType(u'confidence', 4, u'IsCowardly')

    IsNeutral = CBashBasicType(u'mood', 0, u'IsAfraid')
    IsAfraid = CBashBasicType(u'mood', 1, u'IsNeutral')
    IsAnnoyed = CBashBasicType(u'mood', 2, u'IsNeutral')
    IsCocky = CBashBasicType(u'mood', 3, u'IsNeutral')
    IsDrugged = CBashBasicType(u'mood', 4, u'IsNeutral')
    IsPleasant = CBashBasicType(u'mood', 5, u'IsNeutral')
    IsAngry = CBashBasicType(u'mood', 6, u'IsNeutral')
    IsSad = CBashBasicType(u'mood', 7, u'IsNeutral')

    IsHelpsNobody = CBashBasicType(u'assistance', 0, u'IsHelpsAllies')
    IsHelpsAllies = CBashBasicType(u'assistance', 1, u'IsHelpsNobody')
    IsHelpsFriendsAndAllies = CBashBasicType(u'assistance', 2, u'IsHelpsNobody')

    IsStone = CBashBasicType(u'impactType', 0, u'IsDirt')
    IsDirt = CBashBasicType(u'impactType', 1, u'IsStone')
    IsGrass = CBashBasicType(u'impactType', 2, u'IsStone')
    IsGlass = CBashBasicType(u'impactType', 3, u'IsStone')
    IsMetal = CBashBasicType(u'impactType', 4, u'IsStone')
    IsWood = CBashBasicType(u'impactType', 5, u'IsStone')
    IsOrganic = CBashBasicType(u'impactType', 6, u'IsStone')
    IsCloth = CBashBasicType(u'impactType', 7, u'IsStone')
    IsWater = CBashBasicType(u'impactType', 8, u'IsStone')
    IsHollowMetal = CBashBasicType(u'impactType', 9, u'IsStone')
    IsOrganicBug = CBashBasicType(u'impactType', 10, u'IsStone')
    IsOrganicGlow = CBashBasicType(u'impactType', 11, u'IsStone')

    IsAttackLeft = CBashBasicType(u'unarmedAnim', 26, u'IsAttackLeftUp')
    IsAttackLeftUp = CBashBasicType(u'unarmedAnim', 27, u'IsAttackLeft')
    IsAttackLeftDown = CBashBasicType(u'unarmedAnim', 28, u'IsAttackLeft')
    IsAttackLeftIS = CBashBasicType(u'unarmedAnim', 29, u'IsAttackLeft')
    IsAttackLeftISUp = CBashBasicType(u'unarmedAnim', 30, u'IsAttackLeft')
    IsAttackLeftISDown = CBashBasicType(u'unarmedAnim', 31, u'IsAttackLeft')
    IsAttackRight = CBashBasicType(u'unarmedAnim', 32, u'IsAttackLeft')
    IsAttackRightUp = CBashBasicType(u'unarmedAnim', 33, u'IsAttackLeft')
    IsAttackRightDown = CBashBasicType(u'unarmedAnim', 34, u'IsAttackLeft')
    IsAttackRightIS = CBashBasicType(u'unarmedAnim', 35, u'IsAttackLeft')
    IsAttackRightISUp = CBashBasicType(u'unarmedAnim', 36, u'IsAttackLeft')
    IsAttackRightISDown = CBashBasicType(u'unarmedAnim', 37, u'IsAttackLeft')
    IsAttack3 = CBashBasicType(u'unarmedAnim', 38, u'IsAttackLeft')
    IsAttack3Up = CBashBasicType(u'unarmedAnim', 39, u'IsAttackLeft')
    IsAttack3Down = CBashBasicType(u'unarmedAnim', 40, u'IsAttackLeft')
    IsAttack3IS = CBashBasicType(u'unarmedAnim', 41, u'IsAttackLeft')
    IsAttack3ISUp = CBashBasicType(u'unarmedAnim', 42, u'IsAttackLeft')
    IsAttack3ISDown = CBashBasicType(u'unarmedAnim', 43, u'IsAttackLeft')
    IsAttack4 = CBashBasicType(u'unarmedAnim', 44, u'IsAttackLeft')
    IsAttack4Up = CBashBasicType(u'unarmedAnim', 45, u'IsAttackLeft')
    IsAttack4Down = CBashBasicType(u'unarmedAnim', 46, u'IsAttackLeft')
    IsAttack4IS = CBashBasicType(u'unarmedAnim', 47, u'IsAttackLeft')
    IsAttack4ISUp = CBashBasicType(u'unarmedAnim', 48, u'IsAttackLeft')
    IsAttack4ISDown = CBashBasicType(u'unarmedAnim', 49, u'IsAttackLeft')
    IsAttack5 = CBashBasicType(u'unarmedAnim', 50, u'IsAttackLeft')
    IsAttack5Up = CBashBasicType(u'unarmedAnim', 51, u'IsAttackLeft')
    IsAttack5Down = CBashBasicType(u'unarmedAnim', 52, u'IsAttackLeft')
    IsAttack5IS = CBashBasicType(u'unarmedAnim', 53, u'IsAttackLeft')
    IsAttack5ISUp = CBashBasicType(u'unarmedAnim', 54, u'IsAttackLeft')
    IsAttack5ISDown = CBashBasicType(u'unarmedAnim', 55, u'IsAttackLeft')
    IsAttack6 = CBashBasicType(u'unarmedAnim', 56, u'IsAttackLeft')
    IsAttack6Up = CBashBasicType(u'unarmedAnim', 57, u'IsAttackLeft')
    IsAttack6Down = CBashBasicType(u'unarmedAnim', 58, u'IsAttackLeft')
    IsAttack6IS = CBashBasicType(u'unarmedAnim', 59, u'IsAttackLeft')
    IsAttack6ISUp = CBashBasicType(u'unarmedAnim', 60, u'IsAttackLeft')
    IsAttack6ISDown = CBashBasicType(u'unarmedAnim', 61, u'IsAttackLeft')
    IsAttack7 = CBashBasicType(u'unarmedAnim', 62, u'IsAttackLeft')
    IsAttack7Up = CBashBasicType(u'unarmedAnim', 63, u'IsAttackLeft')
    IsAttack7Down = CBashBasicType(u'unarmedAnim', 64, u'IsAttackLeft')
    IsAttack7IS = CBashBasicType(u'unarmedAnim', 65, u'IsAttackLeft')
    IsAttack7ISUp = CBashBasicType(u'unarmedAnim', 66, u'IsAttackLeft')
    IsAttack7ISDown = CBashBasicType(u'unarmedAnim', 67, u'IsAttackLeft')
    IsAttack8 = CBashBasicType(u'unarmedAnim', 68, u'IsAttackLeft')
    IsAttack8Up = CBashBasicType(u'unarmedAnim', 69, u'IsAttackLeft')
    IsAttack8Down = CBashBasicType(u'unarmedAnim', 70, u'IsAttackLeft')
    IsAttack8IS = CBashBasicType(u'unarmedAnim', 71, u'IsAttackLeft')
    IsAttack8ISUp = CBashBasicType(u'unarmedAnim', 72, u'IsAttackLeft')
    IsAttack8ISDown = CBashBasicType(u'unarmedAnim', 73, u'IsAttackLeft')
    IsAttackLoop = CBashBasicType(u'unarmedAnim', 74, u'IsAttackLeft')
    IsAttackLoopUp = CBashBasicType(u'unarmedAnim', 75, u'IsAttackLeft')
    IsAttackLoopDown = CBashBasicType(u'unarmedAnim', 76, u'IsAttackLeft')
    IsAttackLoopIS = CBashBasicType(u'unarmedAnim', 77, u'IsAttackLeft')
    IsAttackLoopISUp = CBashBasicType(u'unarmedAnim', 78, u'IsAttackLeft')
    IsAttackLoopISDown = CBashBasicType(u'unarmedAnim', 79, u'IsAttackLeft')
    IsAttackSpin = CBashBasicType(u'unarmedAnim', 80, u'IsAttackLeft')
    IsAttackSpinUp = CBashBasicType(u'unarmedAnim', 81, u'IsAttackLeft')
    IsAttackSpinDown = CBashBasicType(u'unarmedAnim', 82, u'IsAttackLeft')
    IsAttackSpinIS = CBashBasicType(u'unarmedAnim', 83, u'IsAttackLeft')
    IsAttackSpinISUp = CBashBasicType(u'unarmedAnim', 84, u'IsAttackLeft')
    IsAttackSpinISDown = CBashBasicType(u'unarmedAnim', 85, u'IsAttackLeft')
    IsAttackSpin2 = CBashBasicType(u'unarmedAnim', 86, u'IsAttackLeft')
    IsAttackSpin2Up = CBashBasicType(u'unarmedAnim', 87, u'IsAttackLeft')
    IsAttackSpin2Down = CBashBasicType(u'unarmedAnim', 88, u'IsAttackLeft')
    IsAttackSpin2IS = CBashBasicType(u'unarmedAnim', 89, u'IsAttackLeft')
    IsAttackSpin2ISUp = CBashBasicType(u'unarmedAnim', 90, u'IsAttackLeft')
    IsAttackSpin2ISDown = CBashBasicType(u'unarmedAnim', 91, u'IsAttackLeft')
    IsAttackPower = CBashBasicType(u'unarmedAnim', 92, u'IsAttackLeft')
    IsAttackForwardPower = CBashBasicType(u'unarmedAnim', 93, u'IsAttackLeft')
    IsAttackBackPower = CBashBasicType(u'unarmedAnim', 94, u'IsAttackLeft')
    IsAttackLeftPower = CBashBasicType(u'unarmedAnim', 95, u'IsAttackLeft')
    IsAttackRightPower = CBashBasicType(u'unarmedAnim', 96, u'IsAttackLeft')
    IsPlaceMine = CBashBasicType(u'unarmedAnim', 97, u'IsAttackLeft')
    IsPlaceMineUp = CBashBasicType(u'unarmedAnim', 98, u'IsAttackLeft')
    IsPlaceMineDown = CBashBasicType(u'unarmedAnim', 99, u'IsAttackLeft')
    IsPlaceMineIS = CBashBasicType(u'unarmedAnim', 100, u'IsAttackLeft')
    IsPlaceMineISUp = CBashBasicType(u'unarmedAnim', 101, u'IsAttackLeft')
    IsPlaceMineISDown = CBashBasicType(u'unarmedAnim', 102, u'IsAttackLeft')
    IsPlaceMine2 = CBashBasicType(u'unarmedAnim', 103, u'IsAttackLeft')
    IsPlaceMine2Up = CBashBasicType(u'unarmedAnim', 104, u'IsAttackLeft')
    IsPlaceMine2Down = CBashBasicType(u'unarmedAnim', 105, u'IsAttackLeft')
    IsPlaceMine2IS = CBashBasicType(u'unarmedAnim', 106, u'IsAttackLeft')
    IsPlaceMine2ISUp = CBashBasicType(u'unarmedAnim', 107, u'IsAttackLeft')
    IsPlaceMine2ISDown = CBashBasicType(u'unarmedAnim', 108, u'IsAttackLeft')
    IsAttackThrow = CBashBasicType(u'unarmedAnim', 109, u'IsAttackLeft')
    IsAttackThrowUp = CBashBasicType(u'unarmedAnim', 110, u'IsAttackLeft')
    IsAttackThrowDown = CBashBasicType(u'unarmedAnim', 111, u'IsAttackLeft')
    IsAttackThrowIS = CBashBasicType(u'unarmedAnim', 112, u'IsAttackLeft')
    IsAttackThrowISUp = CBashBasicType(u'unarmedAnim', 113, u'IsAttackLeft')
    IsAttackThrowISDown = CBashBasicType(u'unarmedAnim', 114, u'IsAttackLeft')
    IsAttackThrow2 = CBashBasicType(u'unarmedAnim', 115, u'IsAttackLeft')
    IsAttackThrow2Up = CBashBasicType(u'unarmedAnim', 116, u'IsAttackLeft')
    IsAttackThrow2Down = CBashBasicType(u'unarmedAnim', 117, u'IsAttackLeft')
    IsAttackThrow2IS = CBashBasicType(u'unarmedAnim', 118, u'IsAttackLeft')
    IsAttackThrow2ISUp = CBashBasicType(u'unarmedAnim', 119, u'IsAttackLeft')
    IsAttackThrow2ISDown = CBashBasicType(u'unarmedAnim', 120, u'IsAttackLeft')
    IsAttackThrow3 = CBashBasicType(u'unarmedAnim', 121, u'IsAttackLeft')
    IsAttackThrow3Up = CBashBasicType(u'unarmedAnim', 122, u'IsAttackLeft')
    IsAttackThrow3Down = CBashBasicType(u'unarmedAnim', 123, u'IsAttackLeft')
    IsAttackThrow3IS = CBashBasicType(u'unarmedAnim', 124, u'IsAttackLeft')
    IsAttackThrow3ISUp = CBashBasicType(u'unarmedAnim', 125, u'IsAttackLeft')
    IsAttackThrow3ISDown = CBashBasicType(u'unarmedAnim', 126, u'IsAttackLeft')
    IsAttackThrow4 = CBashBasicType(u'unarmedAnim', 127, u'IsAttackLeft')
    IsAttackThrow4Up = CBashBasicType(u'unarmedAnim', 128, u'IsAttackLeft')
    IsAttackThrow4Down = CBashBasicType(u'unarmedAnim', 129, u'IsAttackLeft')
    IsAttackThrow4IS = CBashBasicType(u'unarmedAnim', 130, u'IsAttackLeft')
    IsAttackThrow4ISUp = CBashBasicType(u'unarmedAnim', 131, u'IsAttackLeft')
    IsAttackThrow4ISDown = CBashBasicType(u'unarmedAnim', 132, u'IsAttackLeft')
    IsAttackThrow5 = CBashBasicType(u'unarmedAnim', 133, u'IsAttackLeft')
    IsAttackThrow5Up = CBashBasicType(u'unarmedAnim', 134, u'IsAttackLeft')
    IsAttackThrow5Down = CBashBasicType(u'unarmedAnim', 135, u'IsAttackLeft')
    IsAttackThrow5IS = CBashBasicType(u'unarmedAnim', 136, u'IsAttackLeft')
    IsAttackThrow5ISUp = CBashBasicType(u'unarmedAnim', 137, u'IsAttackLeft')
    IsAttackThrow5ISDown = CBashBasicType(u'unarmedAnim', 138, u'IsAttackLeft')
    IsPipBoy = CBashBasicType(u'unarmedAnim', 167, u'IsAttackLeft')
    IsPipBoyChild = CBashBasicType(u'unarmedAnim', 178, u'IsAttackLeft')
    IsANY = CBashBasicType(u'unarmedAnim', 255, u'IsAttackLeft')
    copyattrs = FnvBaseRecord.baseattrs + [
        u'boundX1', u'boundY1', u'boundZ1', u'boundX2', u'boundY2', u'boundZ2',
        u'full', u'modPath', u'modb', u'modt_p', u'altTextures_list',
        u'modelFlags', u'actorEffects', u'unarmedEffect', u'unarmedAnim',
        u'bodyParts', u'nift_p', u'flags', u'fatigue', u'barterGold', u'level',
        u'calcMin', u'calcMax', u'speedMult', u'karma', u'dispBase',
        u'templateFlags', u'factions_list', u'deathItem', u'voice',
        u'template', u'destructable_list', u'script', u'items_list',
        u'aggression', u'confidence', u'energyLevel', u'responsibility',
        u'mood', u'services', u'trainSkill', u'trainLevel', u'assistance',
        u'aggroFlags', u'aggroRadius', u'aiPackages', u'animations',
        u'creatureType', u'combat', u'magic', u'stealth', u'health',
        u'attackDamage', u'strength', u'perception', u'endurance', u'charisma',
        u'intelligence', u'agility', u'luck', u'attackReach', u'combatStyle',
        u'partData', u'turningSpeed', u'baseScale', u'footWeight',
        u'impactType', u'soundLevel', u'inheritsSoundsFrom',
        u'soundTypes_list', u'impactData', u'meleeList']
    exportattrs = copyattrs[:]
    exportattrs.remove(u'modt_p')
    exportattrs.remove(u'nift_p')

class FnvLVLCRecord(FnvBaseRecord):
    __slots__ = []
    _Type = b'LVLC'
    def mergeFilter(self, target):
        """Filter out items that don't come from specified modSet."""
        self.entries = [entry for entry in self.entries if
                        entry.listId.ValidateFormID(target)]

    class Entry(ListComponent):
        __slots__ = []
        level = CBashGeneric_LIST(1, c_short)
        unused1 = CBashUINT8ARRAY_LIST(2, 2)
        listId = CBashFORMID_LIST(3)
        count = CBashGeneric_LIST(4, c_short)
        unused2 = CBashUINT8ARRAY_LIST(5, 2)
        owner = CBashFORMID_LIST(6)
        globalOrRank = CBashUNKNOWN_OR_FORMID_OR_UINT32_LIST(7)
        condition = CBashFLOAT32_LIST(8)
        exportattrs = copyattrs = [u'level', u'listId', u'count', u'owner',
                                   u'globalOrRank', u'condition']

    boundX1 = CBashGeneric(7, c_short)
    boundY1 = CBashGeneric(8, c_short)
    boundZ1 = CBashGeneric(9, c_short)
    boundX2 = CBashGeneric(10, c_short)
    boundY2 = CBashGeneric(11, c_short)
    boundZ2 = CBashGeneric(12, c_short)
    chanceNone = CBashGeneric(13, c_ubyte)
    flags = CBashGeneric(14, c_ubyte)

    def create_entry(self):
        length = _CGetFieldAttribute(self._RecordID, 15, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 15, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return self.Entry(self._RecordID, 15, length)
    entries = CBashLIST(15, Entry)
    entries_list = CBashLIST(15, Entry, True)

    modPath = CBashISTRING(16)
    modb = CBashFLOAT32(17)
    modt_p = CBashUINT8ARRAY(18)

    def create_altTexture(self):
        length = _CGetFieldAttribute(self._RecordID, 19, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 19, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return FNVAltTexture(self._RecordID, 19, length)
    altTextures = CBashLIST(19, FNVAltTexture)
    altTextures_list = CBashLIST(19, FNVAltTexture, True)

    modelFlags = CBashGeneric(20, c_ubyte)

    IsCalcFromAllLevels = CBashBasicFlag(u'flags', 0x00000001)
    IsCalcForEachItem = CBashBasicFlag(u'flags', 0x00000002)
    IsUseAll = CBashBasicFlag(u'flags', 0x00000004)

    IsHead = CBashBasicFlag(u'modelFlags', 0x01)
    IsTorso = CBashBasicFlag(u'modelFlags', 0x02)
    IsRightHand = CBashBasicFlag(u'modelFlags', 0x04)
    IsLeftHand = CBashBasicFlag(u'modelFlags', 0x08)
    copyattrs = FnvBaseRecord.baseattrs + [u'boundX1', u'boundY1', u'boundZ1',
                                           u'boundX2', u'boundY2', u'boundZ2',
                                           u'chanceNone', u'flags',
                                           u'entries_list', u'modPath',
                                           u'modb', u'modt_p',
                                           u'altTextures_list', u'modelFlags']
    exportattrs = copyattrs[:]
    exportattrs.remove(u'modt_p')

class FnvLVLNRecord(FnvBaseRecord):
    __slots__ = []
    _Type = b'LVLN'
    def mergeFilter(self, target):
        """Filter out items that don't come from specified modSet."""
        self.entries = [entry for entry in self.entries if entry.listId.ValidateFormID(target)]

    class Entry(ListComponent):
        __slots__ = []
        level = CBashGeneric_LIST(1, c_short)
        unused1 = CBashUINT8ARRAY_LIST(2, 2)
        listId = CBashFORMID_LIST(3)
        count = CBashGeneric_LIST(4, c_short)
        unused2 = CBashUINT8ARRAY_LIST(5, 2)
        owner = CBashFORMID_LIST(6)
        globalOrRank = CBashUNKNOWN_OR_FORMID_OR_UINT32_LIST(7)
        condition = CBashFLOAT32_LIST(8)
        exportattrs = copyattrs = [u'level', u'listId', u'count', u'owner',
                                   u'globalOrRank', u'condition']

    boundX1 = CBashGeneric(7, c_short)
    boundY1 = CBashGeneric(8, c_short)
    boundZ1 = CBashGeneric(9, c_short)
    boundX2 = CBashGeneric(10, c_short)
    boundY2 = CBashGeneric(11, c_short)
    boundZ2 = CBashGeneric(12, c_short)
    chanceNone = CBashGeneric(13, c_ubyte)
    flags = CBashGeneric(14, c_ubyte)

    def create_entry(self):
        length = _CGetFieldAttribute(self._RecordID, 15, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 15, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return self.Entry(self._RecordID, 15, length)
    entries = CBashLIST(15, Entry)
    entries_list = CBashLIST(15, Entry, True)

    modPath = CBashISTRING(16)
    modb = CBashFLOAT32(17)
    modt_p = CBashUINT8ARRAY(18)

    def create_altTexture(self):
        length = _CGetFieldAttribute(self._RecordID, 19, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 19, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return FNVAltTexture(self._RecordID, 19, length)
    altTextures = CBashLIST(19, FNVAltTexture)
    altTextures_list = CBashLIST(19, FNVAltTexture, True)

    modelFlags = CBashGeneric(20, c_ubyte)

    IsCalcFromAllLevels = CBashBasicFlag(u'flags', 0x00000001)
    IsCalcForEachItem = CBashBasicFlag(u'flags', 0x00000002)
    IsUseAll = CBashBasicFlag(u'flags', 0x00000004)

    IsHead = CBashBasicFlag(u'modelFlags', 0x01)
    IsTorso = CBashBasicFlag(u'modelFlags', 0x02)
    IsRightHand = CBashBasicFlag(u'modelFlags', 0x04)
    IsLeftHand = CBashBasicFlag(u'modelFlags', 0x08)
    copyattrs = FnvBaseRecord.baseattrs + [u'boundX1', u'boundY1', u'boundZ1',
                                           u'boundX2', u'boundY2', u'boundZ2',
                                           u'chanceNone', u'flags',
                                           u'entries_list', u'modPath',
                                           u'modb', u'modt_p',
                                           u'altTextures_list', u'modelFlags']
    exportattrs = copyattrs[:]
    exportattrs.remove(u'modt_p')

class FnvKEYMRecord(FnvBaseRecord):
    __slots__ = []
    _Type = b'KEYM'
    boundX1 = CBashGeneric(7, c_short)
    boundY1 = CBashGeneric(8, c_short)
    boundZ1 = CBashGeneric(9, c_short)
    boundX2 = CBashGeneric(10, c_short)
    boundY2 = CBashGeneric(11, c_short)
    boundZ2 = CBashGeneric(12, c_short)
    full = CBashSTRING(13)
    modPath = CBashISTRING(14)
    modb = CBashFLOAT32(15)
    modt_p = CBashUINT8ARRAY(16)

    def create_altTexture(self):
        length = _CGetFieldAttribute(self._RecordID, 17, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 17, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return FNVAltTexture(self._RecordID, 17, length)
    altTextures = CBashLIST(17, FNVAltTexture)
    altTextures_list = CBashLIST(17, FNVAltTexture, True)

    modelFlags = CBashGeneric(18, c_ubyte)
    iconPath = CBashISTRING(19)
    smallIconPath = CBashISTRING(20)
    script = CBashFORMID(21)
    destructable = CBashGrouped(22, FNVDestructable)
    destructable_list = CBashGrouped(22, FNVDestructable, True)

    pickupSound = CBashFORMID(27)
    dropSound = CBashFORMID(28)
    value = CBashGeneric(29, c_long)
    weight = CBashFLOAT32(30)
    loopSound = CBashFORMID(31)

    IsHead = CBashBasicFlag(u'modelFlags', 0x01)
    IsTorso = CBashBasicFlag(u'modelFlags', 0x02)
    IsRightHand = CBashBasicFlag(u'modelFlags', 0x04)
    IsLeftHand = CBashBasicFlag(u'modelFlags', 0x08)
    copyattrs = FnvBaseRecord.baseattrs + [u'boundX1', u'boundY1', u'boundZ1',
                                           u'boundX2', u'boundY2', u'boundZ2',
                                           u'full', u'modPath', u'modb', u'modt_p',
                                           u'altTextures_list', u'modelFlags',
                                           u'iconPath', u'smallIconPath',
                                           u'script', u'destructable_list',
                                           u'pickupSound', u'dropSound',
                                           u'value', u'weight', u'loopSound']
    exportattrs = copyattrs[:]
    exportattrs.remove(u'modt_p')

class FnvALCHRecord(FnvBaseRecord):
    __slots__ = []
    _Type = b'ALCH'
    boundX1 = CBashGeneric(7, c_short)
    boundY1 = CBashGeneric(8, c_short)
    boundZ1 = CBashGeneric(9, c_short)
    boundX2 = CBashGeneric(10, c_short)
    boundY2 = CBashGeneric(11, c_short)
    boundZ2 = CBashGeneric(12, c_short)
    full = CBashSTRING(13)
    modPath = CBashISTRING(14)
    modb = CBashFLOAT32(15)
    modt_p = CBashUINT8ARRAY(16)

    def create_altTexture(self):
        length = _CGetFieldAttribute(self._RecordID, 17, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 17, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return FNVAltTexture(self._RecordID, 17, length)
    altTextures = CBashLIST(17, FNVAltTexture)
    altTextures_list = CBashLIST(17, FNVAltTexture, True)

    modelFlags = CBashGeneric(18, c_ubyte)
    iconPath = CBashISTRING(19)
    smallIconPath = CBashISTRING(20)
    script = CBashFORMID(21)
    equipmentType = CBashGeneric(22, c_long)
    weight = CBashFLOAT32(23)
    value = CBashGeneric(24, c_long)
    flags = CBashGeneric(25, c_ubyte)
    unused1 = CBashUINT8ARRAY(26, 3)

    withdrawalEffect = CBashFORMID(27)
    addictionChance = CBashFLOAT32(28)
    consumeSound = CBashFORMID(29)

    def create_effect(self):
        length = _CGetFieldAttribute(self._RecordID, 30, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 30, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return FNVEffect(self._RecordID, 30, length)
    effects = CBashLIST(30, FNVEffect)
    effects_list = CBashLIST(30, FNVEffect, True)

    destructable = CBashGrouped(31, FNVDestructable)
    destructable_list = CBashGrouped(31, FNVDestructable, True)

    pickupSound = CBashFORMID(36)
    dropSound = CBashFORMID(37)

    IsNoAutoCalc = CBashBasicFlag(u'flags', 0x00000001)
    IsAutoCalc = CBashInvertedFlag(u'IsNoAutoCalc')
    IsFood = CBashBasicFlag(u'flags', 0x00000002)
    IsMedicine = CBashBasicFlag(u'flags', 0x00000004)

    IsHead = CBashBasicFlag(u'modelFlags', 0x01)
    IsTorso = CBashBasicFlag(u'modelFlags', 0x02)
    IsRightHand = CBashBasicFlag(u'modelFlags', 0x04)
    IsLeftHand = CBashBasicFlag(u'modelFlags', 0x08)

    IsNone = CBashBasicType(u'equipmentType', -1, u'IsBigGuns')
    IsBigGuns = CBashBasicType(u'equipmentType', 0, u'IsNone')
    IsEnergyWeapons = CBashBasicType(u'equipmentType', 1, u'IsNone')
    IsSmallGuns = CBashBasicType(u'equipmentType', 2, u'IsNone')
    IsMeleeWeapons = CBashBasicType(u'equipmentType', 3, u'IsNone')
    IsUnarmedWeapon = CBashBasicType(u'equipmentType', 4, u'IsNone')
    IsThrownWeapons = CBashBasicType(u'equipmentType', 5, u'IsNone')
    IsMine = CBashBasicType(u'equipmentType', 6, u'IsNone')
    IsBodyWear = CBashBasicType(u'equipmentType', 7, u'IsNone')
    IsHeadWear = CBashBasicType(u'equipmentType', 8, u'IsNone')
    IsHandWear = CBashBasicType(u'equipmentType', 9, u'IsNone')
    IsChems = CBashBasicType(u'equipmentType', 10, u'IsNone')
    IsStimpack = CBashBasicType(u'equipmentType', 11, u'IsNone')
    IsEdible = CBashBasicType(u'equipmentType', 12, u'IsNone')
    IsAlcohol = CBashBasicType(u'equipmentType', 13, u'IsNone')
    copyattrs = FnvBaseRecord.baseattrs + [
        u'boundX1', u'boundY1', u'boundZ1', u'boundX2', u'boundY2', u'boundZ2',
        u'full', u'modPath', u'modb', u'modt_p', u'altTextures_list',
        u'modelFlags', u'iconPath', u'smallIconPath', u'script',
        u'equipmentType', u'weight', u'value', u'flags', u'withdrawalEffect',
        u'addictionChance', u'consumeSound', u'effects_list',
        u'destructable_list', u'pickupSound', u'dropSound']
    exportattrs = copyattrs[:]
    exportattrs.remove(u'modt_p')

class FnvIDLMRecord(FnvBaseRecord):
    __slots__ = []
    _Type = b'IDLM'
    boundX1 = CBashGeneric(7, c_short)
    boundY1 = CBashGeneric(8, c_short)
    boundZ1 = CBashGeneric(9, c_short)
    boundX2 = CBashGeneric(10, c_short)
    boundY2 = CBashGeneric(11, c_short)
    boundZ2 = CBashGeneric(12, c_short)
    flags = CBashGeneric(13, c_ubyte)
    count = CBashGeneric(14, c_ubyte)
    timer = CBashFLOAT32(15)
    animations = CBashFORMIDARRAY(16)

    IsRunInSequence = CBashBasicFlag(u'flags', 0x00000001)
    IsDoOnce = CBashBasicFlag(u'flags', 0x00000004)
    exportattrs = copyattrs = FnvBaseRecord.baseattrs + [u'boundX1', u'boundY1', u'boundZ1',
                                                         u'boundX2', u'boundY2', u'boundZ2',
                                                         u'flags', u'count', u'timer',
                                                         u'animations']

class FnvNOTERecord(FnvBaseRecord):
    __slots__ = []
    _Type = b'NOTE'
    boundX1 = CBashGeneric(7, c_short)
    boundY1 = CBashGeneric(8, c_short)
    boundZ1 = CBashGeneric(9, c_short)
    boundX2 = CBashGeneric(10, c_short)
    boundY2 = CBashGeneric(11, c_short)
    boundZ2 = CBashGeneric(12, c_short)
    full = CBashSTRING(13)
    modPath = CBashISTRING(14)
    modb = CBashFLOAT32(15)
    modt_p = CBashUINT8ARRAY(16)

    def create_altTexture(self):
        length = _CGetFieldAttribute(self._RecordID, 17, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 17, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return FNVAltTexture(self._RecordID, 17, length)
    altTextures = CBashLIST(17, FNVAltTexture)
    altTextures_list = CBashLIST(17, FNVAltTexture, True)

    modelFlags = CBashGeneric(18, c_ubyte)
    iconPath = CBashISTRING(19)
    smallIconPath = CBashISTRING(20)
    pickupSound = CBashFORMID(21)
    dropSound = CBashFORMID(22)
    noteType = CBashGeneric(23, c_ubyte)
    quests = CBashFORMIDARRAY(24)
    texturePath = CBashISTRING(25)
    textOrTopic = CBashFORMID_OR_STRING(26) #Is a topic formID if IsVoice is true, otherwise text
    sound = CBashFORMID(27)

    IsSound = CBashBasicType(u'flags', 0, u'IsText')
    IsText = CBashBasicType(u'flags', 1, u'IsSound')
    IsImage = CBashBasicType(u'flags', 2, u'IsSound')
    IsVoice = CBashBasicType(u'flags', 3, u'IsSound')

    IsHead = CBashBasicFlag(u'modelFlags', 0x01)
    IsTorso = CBashBasicFlag(u'modelFlags', 0x02)
    IsRightHand = CBashBasicFlag(u'modelFlags', 0x04)
    IsLeftHand = CBashBasicFlag(u'modelFlags', 0x08)
    copyattrs = FnvBaseRecord.baseattrs + [u'boundX1', u'boundY1', u'boundZ1',
                                           u'boundX2', u'boundY2', u'boundZ2',
                                           u'full', u'modPath', u'modb', u'modt_p',
                                           u'altTextures_list', u'modelFlags',
                                           u'iconPath', u'smallIconPath',
                                           u'pickupSound', u'dropSound',
                                           u'noteType', u'quests', u'texturePath',
                                           u'textOrTopic', u'sound']
    exportattrs = copyattrs[:]
    exportattrs.remove(u'modt_p')

class FnvCOBJRecord(FnvBaseRecord):
    __slots__ = []
    _Type = b'COBJ'
    boundX1 = CBashGeneric(7, c_short)
    boundY1 = CBashGeneric(8, c_short)
    boundZ1 = CBashGeneric(9, c_short)
    boundX2 = CBashGeneric(10, c_short)
    boundY2 = CBashGeneric(11, c_short)
    boundZ2 = CBashGeneric(12, c_short)
    full = CBashSTRING(13)
    modPath = CBashISTRING(14)
    modb = CBashFLOAT32(15)
    modt_p = CBashUINT8ARRAY(16)

    def create_altTexture(self):
        length = _CGetFieldAttribute(self._RecordID, 17, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 17, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return FNVAltTexture(self._RecordID, 17, length)
    altTextures = CBashLIST(17, FNVAltTexture)
    altTextures_list = CBashLIST(17, FNVAltTexture, True)

    modelFlags = CBashGeneric(18, c_ubyte)
    iconPath = CBashISTRING(19)
    smallIconPath = CBashISTRING(20)
    script = CBashFORMID(21)
    pickupSound = CBashFORMID(22)
    dropSound = CBashFORMID(23)
    value = CBashGeneric(24, c_long)
    weight = CBashFLOAT32(25)

    IsHead = CBashBasicFlag(u'modelFlags', 0x01)
    IsTorso = CBashBasicFlag(u'modelFlags', 0x02)
    IsRightHand = CBashBasicFlag(u'modelFlags', 0x04)
    IsLeftHand = CBashBasicFlag(u'modelFlags', 0x08)
    copyattrs = FnvBaseRecord.baseattrs + [u'boundX1', u'boundY1', u'boundZ1',
                                           u'boundX2', u'boundY2', u'boundZ2',
                                           u'full', u'modPath', u'modb', u'modt_p',
                                           u'altTextures_list', u'modelFlags',
                                           u'iconPath', u'smallIconPath',
                                           u'script', u'pickupSound',
                                           u'dropSound', u'value', u'weight']
    exportattrs = copyattrs[:]
    exportattrs.remove(u'modt_p')

class FnvPROJRecord(FnvBaseRecord):
    __slots__ = []
    _Type = b'PROJ'
    boundX1 = CBashGeneric(7, c_short)
    boundY1 = CBashGeneric(8, c_short)
    boundZ1 = CBashGeneric(9, c_short)
    boundX2 = CBashGeneric(10, c_short)
    boundY2 = CBashGeneric(11, c_short)
    boundZ2 = CBashGeneric(12, c_short)
    full = CBashSTRING(13)
    modPath = CBashISTRING(14)
    modb = CBashFLOAT32(15)
    modt_p = CBashUINT8ARRAY(16)

    def create_altTexture(self):
        length = _CGetFieldAttribute(self._RecordID, 17, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 17, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return FNVAltTexture(self._RecordID, 17, length)
    altTextures = CBashLIST(17, FNVAltTexture)
    altTextures_list = CBashLIST(17, FNVAltTexture, True)

    modelFlags = CBashGeneric(18, c_ubyte)
    destructable = CBashGrouped(19, FNVDestructable)
    destructable_list = CBashGrouped(19, FNVDestructable, True)

    flags = CBashGeneric(24, c_ushort)
    projType = CBashGeneric(25, c_ushort)
    gravity = CBashFLOAT32(26)
    speed = CBashFLOAT32(27)
    range = CBashFLOAT32(28)
    light = CBashFORMID(29)
    flash = CBashFORMID(30)
    tracerChance = CBashFLOAT32(31)
    altExplProximityTrigger = CBashFLOAT32(32)
    altExplProximityTimer = CBashFLOAT32(33)
    explosion = CBashFORMID(34)
    sound = CBashFORMID(35)
    flashDuration = CBashFLOAT32(36)
    fadeDuration = CBashFLOAT32(37)
    impactForce = CBashFLOAT32(38)
    soundCountdown = CBashFORMID(39)
    soundDisable = CBashFORMID(40)
    defaultWeaponSource = CBashFORMID(41)
    rotX = CBashFLOAT32(42)
    rotY = CBashFLOAT32(43)
    rotZ = CBashFLOAT32(44)
    bouncyMult = CBashFLOAT32(45)
    modelPath = CBashISTRING(46)
    nam2_p = CBashUINT8ARRAY(47)
    soundLevel = CBashGeneric(48, c_ulong)

    IsHitscan = CBashBasicFlag(u'flags', 0x0001)
    IsExplosion = CBashBasicFlag(u'flags', 0x0002)
    IsAltTrigger = CBashBasicFlag(u'flags', 0x0004)
    IsMuzzleFlash = CBashBasicFlag(u'flags', 0x0008)
    IsDisableable = CBashBasicFlag(u'flags', 0x0020)
    IsPickupable = CBashBasicFlag(u'flags', 0x0040)
    IsSupersonic = CBashBasicFlag(u'flags', 0x0080)
    IsPinsLimbs = CBashBasicFlag(u'flags', 0x0100)
    IsPassSmallTransparent = CBashBasicFlag(u'flags', 0x0200)
    IsDetonates = CBashBasicFlag(u'flags', 0x0400)
    IsRotation = CBashBasicFlag(u'flags', 0x0800)

    IsHead = CBashBasicFlag(u'modelFlags', 0x01)
    IsTorso = CBashBasicFlag(u'modelFlags', 0x02)
    IsRightHand = CBashBasicFlag(u'modelFlags', 0x04)
    IsLeftHand = CBashBasicFlag(u'modelFlags', 0x08)

    IsMissile = CBashBasicType(u'projType', 1, u'IsLobber')
    IsLobber = CBashBasicType(u'projType', 2, u'IsMissile')
    IsBeam = CBashBasicType(u'projType', 4, u'IsMissile')
    IsFlame = CBashBasicType(u'projType', 8, u'IsMissile')
    IsContinuousBeam = CBashBasicType(u'projType', 16, u'IsMissile')

    IsLoud = CBashBasicType(u'soundLevel', 0, u'IsNormal')
    IsNormal = CBashBasicType(u'soundLevel', 1, u'IsLoud')
    IsSilent = CBashBasicType(u'soundLevel', 2, u'IsLoud')
    copyattrs = FnvBaseRecord.baseattrs + [
        u'boundX1', u'boundY1', u'boundZ1', u'boundX2', u'boundY2', u'boundZ2',
        u'full', u'modPath', u'modb', u'modt_p', u'altTextures_list',
        u'modelFlags', u'destructable_list', u'flags', u'projType', u'gravity',
        u'speed', u'range', u'light', u'flash', u'tracerChance',
        u'altExplProximityTrigger', u'altExplProximityTimer', u'explosion',
        u'sound', u'flashDuration', u'fadeDuration', u'impactForce',
        u'soundCountdown', u'soundDisable', u'defaultWeaponSource', u'rotX',
        u'rotY', u'rotZ', u'bouncyMult', u'modelPath', u'nam2_p',
        u'soundLevel']
    exportattrs = copyattrs[:]
    exportattrs.remove(u'modt_p')
    exportattrs.remove(u'nam2_p')

class FnvLVLIRecord(FnvBaseRecord):
    __slots__ = []
    _Type = b'LVLI'
    def mergeFilter(self, target):
        """Filter out items that don't come from specified modSet."""
        self.entries = [entry for entry in self.entries if
                        entry.listId.ValidateFormID(target)]

    class Entry(ListComponent):
        __slots__ = []
        level = CBashGeneric_LIST(1, c_short)
        unused1 = CBashUINT8ARRAY_LIST(2, 2)
        listId = CBashFORMID_LIST(3)
        count = CBashGeneric_LIST(4, c_short)
        unused2 = CBashUINT8ARRAY_LIST(5, 2)
        owner = CBashFORMID_LIST(6)
        globalOrRank = CBashUNKNOWN_OR_FORMID_OR_UINT32_LIST(7)
        condition = CBashFLOAT32_LIST(8)
        exportattrs = copyattrs = [u'level', u'listId', u'count', u'owner',
                                   u'globalOrRank', u'condition']

    boundX1 = CBashGeneric(7, c_short)
    boundY1 = CBashGeneric(8, c_short)
    boundZ1 = CBashGeneric(9, c_short)
    boundX2 = CBashGeneric(10, c_short)
    boundY2 = CBashGeneric(11, c_short)
    boundZ2 = CBashGeneric(12, c_short)
    chanceNone = CBashGeneric(13, c_ubyte)
    flags = CBashGeneric(14, c_ubyte)
    globalId = CBashFORMID(15)

    def create_entry(self):
        length = _CGetFieldAttribute(self._RecordID, 16, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 16, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return self.Entry(self._RecordID, 16, length)
    entries = CBashLIST(16, Entry)
    entries_list = CBashLIST(16, Entry, True)


    IsCalcFromAllLevels = CBashBasicFlag(u'flags', 0x00000001)
    IsCalcForEachItem = CBashBasicFlag(u'flags', 0x00000002)
    IsUseAll = CBashBasicFlag(u'flags', 0x00000004)
    exportattrs = copyattrs = FnvBaseRecord.baseattrs + [u'boundX1', u'boundY1', u'boundZ1',
                                                         u'boundX2', u'boundY2', u'boundZ2',
                                                         u'chanceNone', u'flags',
                                                         u'globalId', u'entries_list']

class FnvWTHRRecord(FnvBaseRecord):
    __slots__ = []
    _Type = b'WTHR'
    class WTHRColor(BaseComponent):
        __slots__ = []
        riseRed = CBashGeneric_GROUP(0, c_ubyte)
        riseGreen = CBashGeneric_GROUP(1, c_ubyte)
        riseBlue = CBashGeneric_GROUP(2, c_ubyte)
        unused1 = CBashUINT8ARRAY_GROUP(3, 1)
        dayRed = CBashGeneric_GROUP(4, c_ubyte)
        dayGreen = CBashGeneric_GROUP(5, c_ubyte)
        dayBlue = CBashGeneric_GROUP(6, c_ubyte)
        unused2 = CBashUINT8ARRAY_GROUP(7, 1)
        setRed = CBashGeneric_GROUP(8, c_ubyte)
        setGreen = CBashGeneric_GROUP(9, c_ubyte)
        setBlue = CBashGeneric_GROUP(10, c_ubyte)
        unused3 = CBashUINT8ARRAY_GROUP(11, 1)
        nightRed = CBashGeneric_GROUP(12, c_ubyte)
        nightGreen = CBashGeneric_GROUP(13, c_ubyte)
        nightBlue = CBashGeneric_GROUP(14, c_ubyte)
        unused4 = CBashUINT8ARRAY_GROUP(15, 1)

        noonRed = CBashGeneric_GROUP(16, c_ubyte)
        noonGreen = CBashGeneric_GROUP(17, c_ubyte)
        noonBlue = CBashGeneric_GROUP(18, c_ubyte)
        unused5 = CBashUINT8ARRAY_GROUP(19, 1)

        midnightRed = CBashGeneric_GROUP(20, c_ubyte)
        midnightGreen = CBashGeneric_GROUP(21, c_ubyte)
        midnightBlue = CBashGeneric_GROUP(22, c_ubyte)
        unused6 = CBashUINT8ARRAY_GROUP(23, 1)
        exportattrs = copyattrs = [u'riseRed', u'riseGreen', u'riseBlue',
                                   u'dayRed', u'dayGreen', u'dayBlue',
                                   u'setRed', u'setGreen', u'setBlue',
                                   u'nightRed', u'nightGreen', u'nightBlue',
                                   u'noonRed', u'noonGreen', u'noonBlue',
                                   u'midnightRed', u'midnightGreen', u'midnightBlue']

    class Sound(ListComponent):
        __slots__ = []
        sound = CBashFORMID_LIST(1)
        type = CBashGeneric_LIST(2, c_ulong)
        IsDefault = CBashBasicType(u'type', 0, u'IsPrecip')
        IsPrecipitation = CBashBasicType(u'type', 1, u'IsDefault')
        IsPrecip = CBashAlias(u'IsPrecipitation')
        IsWind = CBashBasicType(u'type', 2, u'IsDefault')
        IsThunder = CBashBasicType(u'type', 3, u'IsDefault')
        exportattrs = copyattrs = [u'sound', u'type']

    sunriseImageSpace = CBashFORMID(7)
    dayImageSpace = CBashFORMID(8)
    sunsetImageSpace = CBashFORMID(9)
    nightImageSpace = CBashFORMID(10)
    unknown1ImageSpace = CBashFORMID(11)
    unknown2ImageSpace = CBashFORMID(12)
    cloudLayer0Path = CBashISTRING(13)
    cloudLayer1Path = CBashISTRING(14)
    cloudLayer2Path = CBashISTRING(15)
    cloudLayer3Path = CBashISTRING(16)
    modPath = CBashISTRING(17)
    modb = CBashFLOAT32(18)
    modt_p = CBashUINT8ARRAY(19)

    def create_altTexture(self):
        length = _CGetFieldAttribute(self._RecordID, 20, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 20, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return FNVAltTexture(self._RecordID, 20, length)
    altTextures = CBashLIST(20, FNVAltTexture)
    altTextures_list = CBashLIST(20, FNVAltTexture, True)

    modelFlags = CBashGeneric(21, c_ubyte)
    unknown1 = CBashGeneric(22, c_ulong)
    layer0Speed = CBashGeneric(23, c_ubyte)
    layer1Speed = CBashGeneric(24, c_ubyte)
    layer2Speed = CBashGeneric(25, c_ubyte)
    layer3Speed = CBashGeneric(26, c_ubyte)
    pnam_p = CBashUINT8ARRAY(27)
    upperSky = CBashGrouped(28, WTHRColor)
    upperSky_list = CBashGrouped(28, WTHRColor, True)

    fog = CBashGrouped(52, WTHRColor)
    fog_list = CBashGrouped(52, WTHRColor, True)

    lowerClouds = CBashGrouped(76, WTHRColor)
    lowerClouds_list = CBashGrouped(76, WTHRColor, True)

    ambient = CBashGrouped(100, WTHRColor)
    ambient_list = CBashGrouped(100, WTHRColor, True)

    sunlight = CBashGrouped(124, WTHRColor)
    sunlight_list = CBashGrouped(124, WTHRColor, True)

    sun = CBashGrouped(148, WTHRColor)
    sun_list = CBashGrouped(148, WTHRColor, True)

    stars = CBashGrouped(172, WTHRColor)
    stars_list = CBashGrouped(172, WTHRColor, True)

    lowerSky = CBashGrouped(196, WTHRColor)
    lowerSky_list = CBashGrouped(196, WTHRColor, True)

    horizon = CBashGrouped(220, WTHRColor)
    horizon_list = CBashGrouped(220, WTHRColor, True)

    upperClouds = CBashGrouped(244, WTHRColor)
    upperClouds_list = CBashGrouped(244, WTHRColor, True)

    fogDayNear = CBashFLOAT32(268)
    fogDayFar = CBashFLOAT32(269)
    fogNightNear = CBashFLOAT32(270)
    fogNightFar = CBashFLOAT32(271)
    fogDayPower = CBashFLOAT32(272)
    fogNightPower = CBashFLOAT32(273)
    inam_p = CBashUINT8ARRAY(274)
    windSpeed = CBashGeneric(275, c_ubyte)
    lowerCloudSpeed = CBashGeneric(276, c_ubyte)
    upperCloudSpeed = CBashGeneric(277, c_ubyte)
    transDelta = CBashGeneric(278, c_ubyte)
    sunGlare = CBashGeneric(279, c_ubyte)
    sunDamage = CBashGeneric(280, c_ubyte)
    rainFadeIn = CBashGeneric(281, c_ubyte)
    rainFadeOut = CBashGeneric(282, c_ubyte)
    boltFadeIn = CBashGeneric(283, c_ubyte)
    boltFadeOut = CBashGeneric(284, c_ubyte)
    boltFrequency = CBashGeneric(285, c_ubyte)
    weatherType = CBashGeneric(286, c_ubyte)
    boltRed = CBashGeneric(287, c_ubyte)
    boltGreen = CBashGeneric(288, c_ubyte)
    boltBlue = CBashGeneric(289, c_ubyte)

    def create_sound(self):
        length = _CGetFieldAttribute(self._RecordID, 290, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 290, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return self.Sound(self._RecordID, 290, length)
    sounds = CBashLIST(290, Sound)
    sounds_list = CBashLIST(290, Sound, True)

    ##actually flags, but all are exclusive(except unknowns)...so like a Type
    ##Manual hackery will make the CS think it is multiple types. It isn't known how the game would react.
    IsNone = CBashMaskedType(u'weatherType',  0x0F, 0x00, u'IsPleasant')
    IsPleasant = CBashMaskedType(u'weatherType',  0x0F, 0x01, u'IsNone')
    IsCloudy = CBashMaskedType(u'weatherType',  0x0F, 0x02, u'IsNone')
    IsRainy = CBashMaskedType(u'weatherType',  0x0F, 0x04, u'IsNone')
    IsSnow = CBashMaskedType(u'weatherType',  0x0F, 0x08, u'IsNone')
    IsUnk1 = CBashBasicFlag(u'weatherType', 0x40)
    IsUnk2 = CBashBasicFlag(u'weatherType', 0x80)
    copyattrs = FnvBaseRecord.baseattrs + [
        u'sunriseImageSpace', u'dayImageSpace', u'sunsetImageSpace',
        u'nightImageSpace', u'unknown1ImageSpace', u'unknown2ImageSpace',
        u'cloudLayer0Path', u'cloudLayer1Path', u'cloudLayer2Path',
        u'cloudLayer3Path', u'modPath', u'modb', u'modt_p',
        u'altTextures_list', u'modelFlags', u'unknown1', u'layer0Speed',
        u'layer1Speed', u'layer2Speed', u'layer3Speed', u'pnam_p',
        u'upperSky_list', u'fog_list', u'lowerClouds_list', u'ambient_list',
        u'sunlight_list', u'sun_list', u'stars_list', u'lowerSky_list',
        u'horizon_list', u'upperClouds_list', u'fogDayNear', u'fogDayFar',
        u'fogNightNear', u'fogNightFar', u'fogDayPower', u'fogNightPower',
        u'inam_p', u'windSpeed', u'lowerCloudSpeed', u'upperCloudSpeed',
        u'transDelta', u'sunGlare', u'sunDamage', u'rainFadeIn',
        u'rainFadeOut', u'boltFadeIn', u'boltFadeOut', u'boltFrequency',
        u'weatherType', u'boltRed', u'boltGreen', u'boltBlue', u'sounds_list']
    exportattrs = copyattrs[:]
    exportattrs.remove(u'modt_p')
    exportattrs.remove(u'pnam_p')
    exportattrs.remove(u'inam_p')
    exportattrs.remove(u'unknown1ImageSpace')
    exportattrs.remove(u'unknown2ImageSpace')

class FnvCLMTRecord(FnvBaseRecord):
    __slots__ = []
    _Type = b'CLMT'
    class Weather(ListComponent):
        __slots__ = []
        weather = CBashFORMID_LIST(1)
        chance = CBashGeneric_LIST(2, c_long)
        globalId = CBashFORMID_LIST(3)
        copyattrs = [u'weather', u'chance', u'globalId']

    def create_weather(self):
        length = _CGetFieldAttribute(self._RecordID, 7, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 7, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return self.Weather(self._RecordID, 7, length)
    weathers = CBashLIST(7, Weather)
    weathers_list = CBashLIST(7, Weather, True)

    sunPath = CBashISTRING(8)
    glarePath = CBashISTRING(9)
    modPath = CBashISTRING(10)
    modb = CBashFLOAT32(11)
    modt_p = CBashUINT8ARRAY(12)

    def create_altTexture(self):
        length = _CGetFieldAttribute(self._RecordID, 13, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 13, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return FNVAltTexture(self._RecordID, 13, length)
    altTextures = CBashLIST(13, FNVAltTexture)
    altTextures_list = CBashLIST(13, FNVAltTexture, True)

    modelFlags = CBashGeneric(14, c_ubyte)
    riseBegin = CBashGeneric(15, c_ubyte)
    riseEnd = CBashGeneric(16, c_ubyte)
    setBegin = CBashGeneric(17, c_ubyte)
    setEnd = CBashGeneric(18, c_ubyte)
    volatility = CBashGeneric(19, c_ubyte)
    phaseLength = CBashGeneric(20, c_ubyte)

    IsHead = CBashBasicFlag(u'modelFlags', 0x01)
    IsTorso = CBashBasicFlag(u'modelFlags', 0x02)
    IsRightHand = CBashBasicFlag(u'modelFlags', 0x04)
    IsLeftHand = CBashBasicFlag(u'modelFlags', 0x08)
    copyattrs = FnvBaseRecord.baseattrs + [u'weathers_list', u'sunPath',
                                           u'glarePath', u'modPath',
                                           u'modb', u'modt_p',
                                           u'altTextures_list',
                                           u'modelFlags', u'riseBegin',
                                           u'riseEnd', u'setBegin',
                                           u'setEnd', u'volatility',
                                           u'phaseLength']
    exportattrs = copyattrs[:]
    exportattrs.remove(u'modt_p')

class FnvREGNRecord(FnvBaseRecord):
    __slots__ = []
    _Type = b'REGN'
    class Area(ListComponent):
        __slots__ = []
        class Point(ListX2Component):
            __slots__ = []
            posX = CBashFLOAT32_LISTX2(1)
            posY = CBashFLOAT32_LISTX2(2)
            exportattrs = copyattrs = [u'posX', u'posY']

        edgeFalloff = CBashGeneric_LIST(1, c_ulong)

        def create_point(self):
            length = _CGetFieldAttribute(self._RecordID, self._FieldID, self._ListIndex, 2, 0, 0, 0, 0, 1)
            _CSetField(self._RecordID, self._FieldID, self._ListIndex, 2, 0, 0, 0, 0, 0, c_ulong(length + 1))
            return self.Point(self._RecordID, self._FieldID, self._ListIndex, 2, length)
        points = CBashLIST_LIST(2, Point)
        points_list = CBashLIST_LIST(2, Point, True)

        exportattrs = copyattrs = [u'edgeFalloff', u'points_list']

    class Entry(ListComponent):
        __slots__ = []
        class Object(ListX2Component):
            __slots__ = []
            objectId = CBashFORMID_LISTX2(1)
            parentIndex = CBashGeneric_LISTX2(2, c_ushort)
            unused1 = CBashUINT8ARRAY_LISTX2(3, 2)
            density = CBashFLOAT32_LISTX2(4)
            clustering = CBashGeneric_LISTX2(5, c_ubyte)
            minSlope = CBashGeneric_LISTX2(6, c_ubyte)
            maxSlope = CBashGeneric_LISTX2(7, c_ubyte)
            flags = CBashGeneric_LISTX2(8, c_ubyte)
            radiusWRTParent = CBashGeneric_LISTX2(9, c_ushort)
            radius = CBashGeneric_LISTX2(10, c_ushort)
            unk1 = CBashUINT8ARRAY_LISTX2(11, 4)
            maxHeight = CBashFLOAT32_LISTX2(12)
            sink = CBashFLOAT32_LISTX2(13)
            sinkVar = CBashFLOAT32_LISTX2(14)
            sizeVar = CBashFLOAT32_LISTX2(15)
            angleVarX = CBashGeneric_LISTX2(16, c_ushort)
            angleVarY = CBashGeneric_LISTX2(17, c_ushort)
            angleVarZ = CBashGeneric_LISTX2(18, c_ushort)
            unused2 = CBashUINT8ARRAY_LISTX2(19, 1)
            unk2 = CBashUINT8ARRAY_LISTX2(20, 4)
            IsConformToSlope = CBashBasicFlag(u'flags', 0x00000001)
            IsPaintVertices = CBashBasicFlag(u'flags', 0x00000002)
            IsSizeVariance = CBashBasicFlag(u'flags', 0x00000004)
            IsXVariance = CBashBasicFlag(u'flags', 0x00000008)
            IsYVariance = CBashBasicFlag(u'flags', 0x00000010)
            IsZVariance = CBashBasicFlag(u'flags', 0x00000020)
            IsTree = CBashBasicFlag(u'flags', 0x00000040)
            IsHugeRock = CBashBasicFlag(u'flags', 0x00000080)
            copyattrs = [u'objectId', u'parentIndex', u'density', u'clustering',
                         u'minSlope', u'maxSlope', u'flags', u'radiusWRTParent',
                         u'radius', u'unk1', u'maxHeight', u'sink', u'sinkVar',
                         u'sizeVar', u'angleVarX', u'angleVarY', u'angleVarZ',
                         u'unk2']
            exportattrs = copyattrs[:]
            exportattrs.remove(u'unk1')
            exportattrs.remove(u'unk2')

        class Grass(ListX2Component):
            __slots__ = []
            grass = CBashFORMID_LISTX2(1)
            unk1 = CBashUINT8ARRAY_LISTX2(2, 4)
            copyattrs = [u'grass', u'unk1']
            exportattrs = copyattrs[:]
            exportattrs.remove(u'unk1')

        class Sound(ListX2Component):
            __slots__ = []
            sound = CBashFORMID_LISTX2(1)
            flags = CBashGeneric_LISTX2(2, c_ulong)
            chance = CBashGeneric_LISTX2(3, c_ulong)
            IsPleasant = CBashBasicFlag(u'flags', 0x00000001)
            IsCloudy = CBashBasicFlag(u'flags', 0x00000002)
            IsRainy = CBashBasicFlag(u'flags', 0x00000004)
            IsSnowy = CBashBasicFlag(u'flags', 0x00000008)
            exportattrs = copyattrs = [u'sound', u'flags', u'chance']

        class Weather(ListX2Component):
            __slots__ = []
            weather = CBashFORMID_LISTX2(1)
            chance = CBashGeneric_LISTX2(2, c_ulong)
            globalId = CBashFORMID_LISTX2(1)
            exportattrs = copyattrs = [u'weather', u'chance', u'globalId']

        entryType = CBashGeneric_LIST(1, c_ulong)
        flags = CBashGeneric_LIST(2, c_ubyte)
        priority = CBashGeneric_LIST(3, c_ubyte)
        unused1 = CBashUINT8ARRAY_LIST(4, 4)

        def create_object(self):
            length = _CGetFieldAttribute(self._RecordID, self._FieldID, self._ListIndex, 5, 0, 0, 0, 0, 1)
            _CSetField(self._RecordID, self._FieldID, self._ListIndex, 5, 0, 0, 0, 0, 0, c_ulong(length + 1))
            return self.Object(self._RecordID, self._FieldID, self._ListIndex, 5, length)
        objects = CBashLIST_LIST(5, Object)
        objects_list = CBashLIST_LIST(5, Object, True)

        mapName = CBashSTRING_LIST(6)
        iconPath = CBashSTRING_LIST(7)

        def create_grass(self):
            length = _CGetFieldAttribute(self._RecordID, self._FieldID, self._ListIndex, 8, 0, 0, 0, 0, 1)
            _CSetField(self._RecordID, self._FieldID, self._ListIndex, 8, 0, 0, 0, 0, 0, c_ulong(length + 1))
            return self.Grass(self._RecordID, self._FieldID, self._ListIndex, 8, length)
        grasses = CBashLIST_LIST(8, Grass)
        grasses_list = CBashLIST_LIST(8, Grass, True)

        musicType = CBashGeneric_LIST(9, c_ulong)
        music = CBashFORMID_LIST(10)
        incidentalMedia = CBashFORMID_LIST(11)
        battleMedias = CBashFORMIDARRAY_LIST(12)

        def create_sound(self):
            length = _CGetFieldAttribute(self._RecordID, self._FieldID, self._ListIndex, 13, 0, 0, 0, 0, 1)
            _CSetField(self._RecordID, self._FieldID, self._ListIndex, 13, 0, 0, 0, 0, 0, c_ulong(length + 1))
            return self.Sound(self._RecordID, self._FieldID, self._ListIndex, 13, length)
        sounds = CBashLIST_LIST(13, Sound)
        sounds_list = CBashLIST_LIST(13, Sound, True)


        def create_weather(self):
            length = _CGetFieldAttribute(self._RecordID, self._FieldID, self._ListIndex, 14, 0, 0, 0, 0, 1)
            _CSetField(self._RecordID, self._FieldID, self._ListIndex, 14, 0, 0, 0, 0, 0, c_ulong(length + 1))
            return self.Weather(self._RecordID, self._FieldID, self._ListIndex, 14, length)
        weathers = CBashLIST_LIST(14, Weather)
        weathers_list = CBashLIST_LIST(14, Weather, True)

        imposters = CBashFORMIDARRAY_LIST(15)

        IsOverride = CBashBasicFlag(u'flags', 0x00000001)

        IsObject = CBashBasicType(u'entryType', 2, u'IsWeather')
        IsWeather = CBashBasicType(u'entryType', 3, u'IsObject')
        IsMap = CBashBasicType(u'entryType', 4, u'IsObject')
        IsLand = CBashBasicType(u'entryType', 5, u'IsObject')
        IsGrass = CBashBasicType(u'entryType', 6, u'IsObject')
        IsSound = CBashBasicType(u'entryType', 7, u'IsObject')
        IsImposter = CBashBasicType(u'entryType', 8, u'IsObject')
        IsDefault = CBashBasicType(u'musicType', 0, u'IsPublic')
        IsPublic = CBashBasicType(u'musicType', 1, u'IsDefault')
        IsDungeon = CBashBasicType(u'musicType', 2, u'IsDefault')
        exportattrs = copyattrs = [u'entryType', u'flags', u'priority', u'objects_list',
                                   u'mapName', u'iconPath', u'grasses_list', u'musicType',
                                   u'music', u'incidentalMedia', u'battleMedias',
                                   u'sounds_list', u'weathers_list', u'imposters']

    iconPath = CBashISTRING(7)
    smallIconPath = CBashISTRING(8)
    mapRed = CBashGeneric(9, c_ubyte)
    mapGreen = CBashGeneric(10, c_ubyte)
    mapBlue = CBashGeneric(11, c_ubyte)
    unused1 = CBashUINT8ARRAY(12, 1)
    worldspace = CBashFORMID(13)

    def create_area(self):
        length = _CGetFieldAttribute(self._RecordID, 14, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 14, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return self.Area(self._RecordID, 14, length)
    areas = CBashLIST(14, Area)
    areas_list = CBashLIST(14, Area, True)

    def create_entry(self):
        length = _CGetFieldAttribute(self._RecordID, 15, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 15, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return self.Entry(self._RecordID, 15, length)
    entries = CBashLIST(15, Entry)
    entries_list = CBashLIST(15, Entry, True)

    exportattrs = copyattrs = FnvBaseRecord.baseattrs + [u'iconPath', u'smallIconPath',
                                                         u'mapRed', u'mapGreen', u'mapBlue',
                                                         u'worldspace', u'areas_list',
                                                         u'entries_list']

class FnvNAVIRecord(FnvBaseRecord):
    __slots__ = []
    _Type = b'NAVI'
    class _NVMI(ListComponent):
        __slots__ = []
        unknown1 = CBashUINT8ARRAY_LIST(1, 4)
        mesh = CBashFORMID_LIST(2)
        location = CBashFORMID_LIST(3)
        xGrid = CBashGeneric_LIST(4, c_short)
        yGrid = CBashGeneric_LIST(5, c_short)
        unknown2_p = CBashUINT8ARRAY_LIST(6)
        copyattrs = [u'unknown1', u'mesh', u'location',
                     u'xGrid', u'yGrid', u'unknown2_p']
        exportattrs = copyattrs[:]
        exportattrs.remove(u'unknown1')
        exportattrs.remove(u'unknown2_p')

    class _NVCI(ListComponent):
        __slots__ = []
        unknown1 = CBashFORMID_LIST(1)
        unknown2 = CBashFORMIDARRAY_LIST(2)
        unknown3 = CBashFORMIDARRAY_LIST(3)
        doors = CBashFORMIDARRAY_LIST(4)
        copyattrs = [u'unknown1', u'unknown2', u'unknown3', u'doors']
        exportattrs = copyattrs[:]
        exportattrs.remove(u'unknown1')
        exportattrs.remove(u'unknown2')
        exportattrs.remove(u'unknown3')

    version = CBashGeneric(7, c_ulong)

    def create_NVMI(self):
        length = _CGetFieldAttribute(self._RecordID, 8, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 8, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return self._NVMI(self._RecordID, 8, length)
    NVMI = CBashLIST(8, _NVMI)
    NVMI_list = CBashLIST(8, _NVMI, True)


    def create_NVCI(self):
        length = _CGetFieldAttribute(self._RecordID, 9, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 9, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return self._NVCI(self._RecordID, 9, length)
    NVCI = CBashLIST(9, _NVCI)
    NVCI_list = CBashLIST(9, _NVCI, True)

    exportattrs = copyattrs = FnvBaseRecord.baseattrs + [u'version', u'NVMI_list', u'NVCI_list']

class FnvCELLRecord(FnvBaseRecord):
    __slots__ = []
    _Type = b'CELL'
    @property
    def _ParentID(self):
        _CGetField.restype = c_record_p
        return _CGetField(self._RecordID, 67, 0, 0, 0, 0, 0, 0, 0)

    @property
    def bsb(self):
        """Returns tesfile block and sub-block indices for cells in this group.
        For interior cell, bsb is (blockNum,subBlockNum). For exterior cell, bsb is
        ((blockX,blockY),(subblockX,subblockY))."""
        #--Interior cell
        if self.IsInterior:
            ObjectID = self.fid[1]
            return (ObjectID % 10, (ObjectID // 10) % 10)
        #--Exterior cell
        else:
            subblockX = int(math.floor((self.posX or 0) / 8.0))
            subblockY = int(math.floor((self.posY or 0) / 8.0))
            return ((int(math.floor(subblockX / 4.0)), int(math.floor(subblockY / 4.0))), (subblockX, subblockY))

    class SwappedImpact(ListComponent):
        __slots__ = []
        material = CBashGeneric_LIST(1, c_ulong)
        oldImpact = CBashFORMID_LIST(2)
        newImpact = CBashFORMID_LIST(3)

        IsStone = CBashBasicType(u'material', 0, u'IsDirt')
        IsDirt = CBashBasicType(u'material', 1, u'IsStone')
        IsGrass = CBashBasicType(u'material', 2, u'IsStone')
        IsGlass = CBashBasicType(u'material', 3, u'IsStone')
        IsMetal = CBashBasicType(u'material', 4, u'IsStone')
        IsWood = CBashBasicType(u'material', 5, u'IsStone')
        IsOrganic = CBashBasicType(u'material', 6, u'IsStone')
        IsCloth = CBashBasicType(u'material', 7, u'IsStone')
        IsWater = CBashBasicType(u'material', 8, u'IsStone')
        IsHollowMetal = CBashBasicType(u'material', 9, u'IsStone')
        IsOrganicBug = CBashBasicType(u'material', 10, u'IsStone')
        IsOrganicGlow = CBashBasicType(u'material', 11, u'IsStone')
        exportattrs = copyattrs = [u'material', u'oldImpact', u'newImpact']

    full = CBashSTRING(7)
    flags = CBashGeneric(8, c_ubyte)
    posX = CBashUNKNOWN_OR_GENERIC(9, c_long)
    posY = CBashUNKNOWN_OR_GENERIC(10, c_long)
    quadFlags = CBashUNKNOWN_OR_GENERIC(11, c_ulong)
    ambientRed = CBashGeneric(12, c_ubyte)
    ambientGreen = CBashGeneric(13, c_ubyte)
    ambientBlue = CBashGeneric(14, c_ubyte)
    unused1 = CBashUINT8ARRAY(15, 1)
    directionalRed = CBashGeneric(16, c_ubyte)
    directionalGreen = CBashGeneric(17, c_ubyte)
    directionalBlue = CBashGeneric(18, c_ubyte)
    unused2 = CBashUINT8ARRAY(19, 1)
    fogRed = CBashGeneric(20, c_ubyte)
    fogGreen = CBashGeneric(21, c_ubyte)
    fogBlue = CBashGeneric(22, c_ubyte)
    unused3 = CBashUINT8ARRAY(23, 1)
    fogNear = CBashFLOAT32(24)
    fogFar = CBashFLOAT32(25)
    directionalXY = CBashGeneric(26, c_long)
    directionalZ = CBashGeneric(27, c_long)
    directionalFade = CBashFLOAT32(28)
    fogClip = CBashFLOAT32(29)
    fogPower = CBashFLOAT32(30)

    def create_swappedImpact(self):
        length = _CGetFieldAttribute(self._RecordID, 31, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 31, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return self.SwappedImpact(self._RecordID, 31, length)
    swappedImpacts = CBashLIST(31, SwappedImpact)
    swappedImpacts_list = CBashLIST(31, SwappedImpact, True)

    concSolid = CBashSTRING(32)
    concBroken = CBashSTRING(33)
    metalSolid = CBashSTRING(34)
    metalHollow = CBashSTRING(35)
    metalSheet = CBashSTRING(36)
    wood = CBashSTRING(37)
    sand = CBashSTRING(38)
    dirt = CBashSTRING(39)
    grass = CBashSTRING(40)
    water = CBashSTRING(41)
    lightTemplate = CBashFORMID(42)
    lightFlags = CBashGeneric(43, c_ulong)
    waterHeight = CBashFLOAT32(44)
    waterNoisePath = CBashISTRING(45)
    regions = CBashFORMIDARRAY(46)
    imageSpace = CBashFORMID(47)
    xcet_p = CBashUINT8ARRAY(48)
    encounterZone = CBashFORMID(49)
    climate = CBashFORMID(50)
    water = CBashFORMID(51)
    owner = CBashFORMID(52)
    rank = CBashGeneric(53, c_long)
    acousticSpace = CBashFORMID(54)
    xcmt_p = CBashUINT8ARRAY(55)
    music = CBashFORMID(56)
    def create_ACHR(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self.GetParentMod()._ModID, cast(b'ACHR', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, self._RecordID)
        return FnvACHRRecord(RecordID) if RecordID else None
    ACHR = CBashSUBRECORDARRAY(57, FnvACHRRecord, b'ACHR')

    def create_ACRE(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self.GetParentMod()._ModID, cast(b'ACRE', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, self._RecordID)
        return FnvACRERecord(RecordID) if RecordID else None
    ACRE = CBashSUBRECORDARRAY(58, FnvACRERecord, b'ACRE')

    def create_REFR(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self.GetParentMod()._ModID, cast(b'REFR', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, self._RecordID)
        return FnvREFRRecord(RecordID) if RecordID else None
    REFR = CBashSUBRECORDARRAY(59, FnvREFRRecord, b'REFR')

    def create_PGRE(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self.GetParentMod()._ModID, cast(b'PGRE', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, self._RecordID)
        return FnvPGRERecord(RecordID) if RecordID else None
    PGRE = CBashSUBRECORDARRAY(60, FnvPGRERecord, b'PGRE')

    def create_PMIS(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self.GetParentMod()._ModID, cast(b'PMIS', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, self._RecordID)
        return FnvPMISRecord(RecordID) if RecordID else None
    PMIS = CBashSUBRECORDARRAY(61, FnvPMISRecord, b'PMIS')

    def create_PBEA(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self.GetParentMod()._ModID, cast(b'PBEA', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, self._RecordID)
        return FnvPBEARecord(RecordID) if RecordID else None
    PBEA = CBashSUBRECORDARRAY(62, FnvPBEARecord, b'PBEA')

    def create_PFLA(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self.GetParentMod()._ModID, cast(b'PFLA', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, self._RecordID)
        return FnvPFLARecord(RecordID) if RecordID else None
    PFLA = CBashSUBRECORDARRAY(63, FnvPFLARecord, b'PFLA')

    def create_PCBE(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self.GetParentMod()._ModID, cast(b'PCBE', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, self._RecordID)
        return FnvPCBERecord(RecordID) if RecordID else None
    PCBE = CBashSUBRECORDARRAY(64, FnvPCBERecord, b'PCBE')

    def create_NAVM(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self.GetParentMod()._ModID, cast(b'NAVM', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, self._RecordID)
        return FnvNAVMRecord(RecordID) if RecordID else None
    NAVM = CBashSUBRECORDARRAY(65, FnvNAVMRecord, b'NAVM')

    def create_LAND(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self.GetParentMod()._ModID, cast(b'LAND', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, self._RecordID)
        return FnvLANDRecord(RecordID) if RecordID else None
    LAND = CBashSUBRECORD(66, FnvLANDRecord, b'LAND')


    IsInterior = CBashBasicFlag(u'flags', 0x00000001)
    IsHasWater = CBashBasicFlag(u'flags', 0x00000002)
    IsInvertFastTravel = CBashBasicFlag(u'flags', 0x00000004)
    IsForceHideLand = CBashBasicFlag(u'flags', 0x00000008) #Exterior cells only
    IsOblivionInterior = CBashBasicFlag(u'flags', 0x00000008) #Interior cells only
    IsPublicPlace = CBashBasicFlag(u'flags', 0x00000020)
    IsHandChanged = CBashBasicFlag(u'flags', 0x00000040)
    IsBehaveLikeExterior = CBashBasicFlag(u'flags', 0x00000080)

    IsQuad1ForceHidden = CBashBasicFlag(u'quadFlags', 0x00000001)
    IsQuad2ForceHidden = CBashBasicFlag(u'quadFlags', 0x00000002)
    IsQuad3ForceHidden = CBashBasicFlag(u'quadFlags', 0x00000004)
    IsQuad4ForceHidden = CBashBasicFlag(u'quadFlags', 0x00000008)

    IsLightAmbientInherited = CBashBasicFlag(u'lightFlags', 0x00000001)
    IsLightDirectionalColorInherited = CBashBasicFlag(u'lightFlags', 0x00000002)
    IsLightFogColorInherited = CBashBasicFlag(u'lightFlags', 0x00000004)
    IsLightFogNearInherited = CBashBasicFlag(u'lightFlags', 0x00000008)
    IsLightFogFarInherited = CBashBasicFlag(u'lightFlags', 0x00000010)
    IsLightDirectionalRotationInherited = CBashBasicFlag(u'lightFlags', 0x00000020)
    IsLightDirectionalFadeInherited = CBashBasicFlag(u'lightFlags', 0x00000040)
    IsLightFogClipInherited = CBashBasicFlag(u'lightFlags', 0x00000080)
    IsLightFogPowerInherited = CBashBasicFlag(u'lightFlags', 0x00000100)
    copyattrs = FnvBaseRecord.baseattrs + [
        u'full', u'flags', u'posX', u'posY', u'quadFlags', u'ambientRed',
        u'ambientGreen', u'ambientBlue', u'directionalRed',
        u'directionalGreen', u'directionalBlue', u'fogRed', u'fogGreen',
        u'fogBlue', u'fogNear', u'fogFar', u'directionalXY', u'directionalZ',
        u'directionalFade', u'fogClip', u'fogPower', u'concSolid',
        u'concBroken', u'metalSolid', u'metalHollow', u'metalSheet', u'wood',
        u'sand', u'dirt', u'grass', u'water', u'lightTemplate', u'lightFlags',
        u'waterHeight', u'waterNoisePath', u'regions', u'imageSpace',
        u'xcet_p', u'encounterZone', u'climate', u'water', u'owner', u'rank',
        u'acousticSpace', u'xcmt_p', u'music']
    exportattrs = copyattrs[:]
    exportattrs.remove(u'xcet_p')
    exportattrs.remove(u'xcmt_p')

class FnvWRLDRecord(FnvBaseRecord):
    __slots__ = []
    _Type = b'WRLD'
    class SwappedImpact(ListComponent):
        __slots__ = []
        material = CBashGeneric_LIST(1, c_ulong)
        oldImpact = CBashFORMID_LIST(2)
        newImpact = CBashFORMID_LIST(3)

        IsStone = CBashBasicType(u'material', 0, u'IsDirt')
        IsDirt = CBashBasicType(u'material', 1, u'IsStone')
        IsGrass = CBashBasicType(u'material', 2, u'IsStone')
        IsGlass = CBashBasicType(u'material', 3, u'IsStone')
        IsMetal = CBashBasicType(u'material', 4, u'IsStone')
        IsWood = CBashBasicType(u'material', 5, u'IsStone')
        IsOrganic = CBashBasicType(u'material', 6, u'IsStone')
        IsCloth = CBashBasicType(u'material', 7, u'IsStone')
        IsWater = CBashBasicType(u'material', 8, u'IsStone')
        IsHollowMetal = CBashBasicType(u'material', 9, u'IsStone')
        IsOrganicBug = CBashBasicType(u'material', 10, u'IsStone')
        IsOrganicGlow = CBashBasicType(u'material', 11, u'IsStone')
        exportattrs = copyattrs = [u'material', u'oldImpact', u'newImpact']

    full = CBashSTRING(7)
    encounterZone = CBashFORMID(8)
    parent = CBashFORMID(9)
    parentFlags = CBashGeneric(10, c_ushort)
    climate = CBashFORMID(11)
    water = CBashFORMID(12)
    lodWater = CBashFORMID(13)
    lodWaterHeight = CBashFLOAT32(14)
    defaultLandHeight = CBashFLOAT32(15)
    defaultWaterHeight = CBashFLOAT32(16)
    iconPath = CBashISTRING(17)
    smallIconPath = CBashISTRING(18)
    dimX = CBashGeneric(19, c_long)
    dimY = CBashGeneric(20, c_long)
    NWCellX = CBashGeneric(21, c_short)
    NWCellY = CBashGeneric(22, c_short)
    SECellX = CBashGeneric(23, c_short)
    SECellY = CBashGeneric(24, c_short)
    mapScale = CBashFLOAT32(25)
    xCellOffset = CBashFLOAT32(26)
    yCellOffset = CBashFLOAT32(27)
    imageSpace = CBashFORMID(28)
    flags = CBashGeneric(29, c_ubyte)
    xMinObjBounds = CBashFLOAT32(30)
    yMinObjBounds = CBashFLOAT32(31)
    xMaxObjBounds = CBashFLOAT32(32)
    yMaxObjBounds = CBashFLOAT32(33)
    music = CBashFORMID(34)
    canopyShadowPath = CBashISTRING(35)
    waterNoisePath = CBashISTRING(36)

    def create_swappedImpact(self):
        length = _CGetFieldAttribute(self._RecordID, 37, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 37, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return self.SwappedImpact(self._RecordID, 37, length)
    swappedImpacts = CBashLIST(37, SwappedImpact)
    swappedImpacts_list = CBashLIST(37, SwappedImpact, True)

    concSolid = CBashSTRING(38)
    concBroken = CBashSTRING(39)
    metalSolid = CBashSTRING(40)
    metalHollow = CBashSTRING(41)
    metalSheet = CBashSTRING(42)
    wood = CBashSTRING(43)
    sand = CBashSTRING(44)
    dirt = CBashSTRING(45)
    grass = CBashSTRING(46)
    water = CBashSTRING(47)
    ofst_p = CBashUINT8ARRAY(48)

    def create_WorldCELL(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self.GetParentMod()._ModID, cast(b'WCEL', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, self._RecordID)
        return FnvCELLRecord(RecordID) if RecordID else None
    WorldCELL = CBashSUBRECORD(49, FnvCELLRecord, b'WCEL')
##b'WCEL' is an artificial type CBash uses to distinguish World Cells
    def create_CELLS(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self.GetParentMod()._ModID, cast(b'CELL', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, self._RecordID)
        return FnvCELLRecord(RecordID) if RecordID else None
    CELLS = CBashSUBRECORDARRAY(50, FnvCELLRecord, b'CELL')


    IsSmallWorld = CBashBasicFlag(u'flags', 0x01)
    IsNoFastTravel = CBashBasicFlag(u'flags', 0x02)
    IsUnknown2 = CBashBasicFlag(u'flags', 0x04)
    IsNoLODWater = CBashBasicFlag(u'flags', 0x10)
    IsNoLODNoise = CBashBasicFlag(u'flags', 0x20)
    IsNoNPCFallDmg = CBashBasicFlag(u'flags', 0x40)

    IsUseLandData = CBashBasicFlag(u'parentFlags', 0x0001)
    IsUseLODData = CBashBasicFlag(u'parentFlags', 0x0002)
    IsUseMapData = CBashBasicFlag(u'parentFlags', 0x0004)
    IsUseWaterData = CBashBasicFlag(u'parentFlags', 0x0008)
    IsUseClimateData = CBashBasicFlag(u'parentFlags', 0x0010)
    IsUseImageSpaceData = CBashBasicFlag(u'parentFlags', 0x0020)
    IsUnknown1 = CBashBasicFlag(u'parentFlags', 0x0040)
    IsNeedsWaterAdjustment = CBashBasicFlag(u'parentFlags', 0x0080)
    copyattrs = FnvBaseRecord.baseattrs + [
        u'full', u'encounterZone', u'parent', u'parentFlags', u'climate',
        u'water', u'lodWater', u'lodWaterHeight', u'defaultLandHeight',
        u'defaultWaterHeight', u'iconPath', u'smallIconPath', u'dimX', u'dimY',
        u'NWCellX', u'NWCellY', u'SECellX', u'SECellY', u'mapScale',
        u'xCellOffset', u'yCellOffset', u'imageSpace', u'flags',
        u'xMinObjBounds', u'yMinObjBounds', u'xMaxObjBounds', u'yMaxObjBounds',
        u'music', u'canopyShadowPath', u'waterNoisePath',
        u'swappedImpacts_list', u'concSolid', u'concBroken', u'metalSolid',
        u'metalHollow', u'metalSheet', u'wood', u'sand', u'dirt', u'grass',
        u'water', u'ofst_p']
    exportattrs = copyattrs[:]
    exportattrs.remove(u'ofst_p')

class FnvDIALRecord(FnvBaseRecord):
    __slots__ = []
    _Type = b'DIAL'
    class Quest(ListComponent):
        __slots__ = []
        class QuestUnknown(ListX2Component):
            __slots__ = []
            unknownId = CBashFORMID_LISTX2(1)
            unknown = CBashGeneric_LISTX2(2, c_long)
            copyattrs = [u'unknownId', u'unknown']
            exportattrs = copyattrs[:]
            exportattrs.remove(u'unknownId')
            exportattrs.remove(u'unknown')

        quest = CBashFORMID_LIST(1)

        def create_unknown(self):
            length = _CGetFieldAttribute(self._RecordID, self._FieldID, self._ListIndex, 2, 0, 0, 0, 0, 1)
            _CSetField(self._RecordID, self._FieldID, self._ListIndex, 2, 0, 0, 0, 0, 0, c_ulong(length + 1))
            return self.QuestUnknown(self._RecordID, self._FieldID, self._ListIndex, 2, length)
        unknowns = CBashLIST_LIST(2, QuestUnknown)
        unknowns_list = CBashLIST_LIST(2, QuestUnknown, True)

        exportattrs = copyattrs = [u'quest', u'unknowns_list']

    def create_quest(self):
        length = _CGetFieldAttribute(self._RecordID, 7, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 7, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return self.Quest(self._RecordID, 7, length)
    quests = CBashLIST(7, Quest)
    quests_list = CBashLIST(7, Quest, True)

    def create_removedQuest(self):
        length = _CGetFieldAttribute(self._RecordID, 8, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 8, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return self.Quest(self._RecordID, 8, length)
    removedQuests = CBashLIST(8, Quest)
    removedQuests_list = CBashLIST(8, Quest, True)


    full = CBashSTRING(9)
    priority = CBashFLOAT32(10)
    unknown = CBashSTRING(11)
    dialType = CBashGeneric(12, c_ubyte)
    flags = CBashGeneric(13, c_ubyte)
    def create_INFO(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self.GetParentMod()._ModID, cast(b'INFO', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, self._RecordID)
        return FnvINFORecord(RecordID) if RecordID else None
    INFO = CBashSUBRECORDARRAY(14, FnvINFORecord, b'INFO')


    IsRumors = CBashBasicFlag(u'flags', 0x01)
    IsTopLevel = CBashBasicFlag(u'flags', 0x02)

    IsTopic = CBashBasicType(u'dialType', 0, u'IsConversation')
    IsConversation = CBashBasicType(u'dialType', 1, u'IsTopic')
    IsCombat = CBashBasicType(u'dialType', 2, u'IsTopic')
    IsPersuasion = CBashBasicType(u'dialType', 3, u'IsTopic')
    IsDetection = CBashBasicType(u'dialType', 4, u'IsTopic')
    IsService = CBashBasicType(u'dialType', 5, u'IsTopic')
    IsMisc = CBashBasicType(u'dialType', 6, u'IsTopic')
    IsRadio = CBashBasicType(u'dialType', 7, u'IsTopic')
    copyattrs = FnvBaseRecord.baseattrs + [u'quests_list', u'removedQuests_list',
                                           u'full', u'priority', u'unknown',
                                           u'dialType', u'flags']
    exportattrs = copyattrs[:]
    exportattrs.remove(u'unknown')

class FnvQUSTRecord(FnvBaseRecord):
    __slots__ = []
    _Type = b'QUST'
    def mergeFilter(self, target):
        """Filter out items that don't come from specified modSet.
        Filters items."""
        self.conditions = [x for x in self.conditions if (
            (not isinstance(x.param1,FormID) or x.param1.ValidateFormID(target))
            and
            (not isinstance(x.param2,FormID) or x.param2.ValidateFormID(target))
            )]
        #for target in self.targets_list:
        #    target.conditions = [x for x in target.conditions_list if (
        #        (not isinstance(x.param1,FormID) or x.param1[0] in modSet)
        #        and
        #        (not isinstance(x.param2,FormID) or x.param2[0] in modSet)
        #        )]

    class Stage(ListComponent):
        __slots__ = []
        class Entry(ListX2Component):
            __slots__ = []
            flags = CBashGeneric_LISTX2(1, c_ubyte)

            def create_condition(self):
                length = _CGetFieldAttribute(self._RecordID, self._FieldID, self._ListIndex, self._ListFieldID, self._ListX2Index, 2, 0, 0, 1)
                _CSetField(self._RecordID, self._FieldID, self._ListIndex, self._ListFieldID, self._ListX2Index, 2, 0, 0, 0, c_ulong(length + 1))
                return FNVConditionX3(self._RecordID, self._FieldID, self._ListIndex, self._ListFieldID, self._ListX2Index, 2, length)
            conditions = CBashLIST_LISTX2(2, FNVConditionX3)
            conditions_list = CBashLIST_LISTX2(2, FNVConditionX3, True)

            text = CBashSTRING_LISTX2(3)
            unused1 = CBashUINT8ARRAY_LISTX2(4, 4)
            numRefs = CBashGeneric_LISTX2(5, c_ulong)
            compiledSize = CBashGeneric_LISTX2(6, c_ulong)
            lastIndex = CBashGeneric_LISTX2(7, c_ulong)
            scriptType = CBashGeneric_LISTX2(8, c_ulong)
            scriptFlags = CBashGeneric_LISTX2(9, c_ushort)
            compiled_p = CBashUINT8ARRAY_LISTX2(10)
            scriptText = CBashISTRING_LISTX2(11)

            def create_var(self):
                length = _CGetFieldAttribute(self._RecordID, self._FieldID, self._ListIndex, self._ListFieldID, self._ListX2Index, 12, 0, 0, 1)
                _CSetField(self._RecordID, self._FieldID, self._ListIndex, self._ListFieldID, self._ListX2Index, 12, 0, 0, 0, c_ulong(length + 1))
                return VarX3(self._RecordID, self._FieldID, self._ListIndex, self._ListFieldID, self._ListX2Index, 12, length)
            vars = CBashLIST_LISTX2(12, VarX3)
            vars_list = CBashLIST_LISTX2(12, VarX3, True)

            references = CBashFORMID_OR_UINT32_ARRAY_LISTX2(13)
            nextQuest = CBashFORMID_LISTX2(14)

            IsCompletes = CBashBasicFlag(u'flags', 0x00000001)
            IsFailed = CBashBasicFlag(u'flags', 0x00000002)

            IsEnabled = CBashBasicFlag(u'scriptFlags', 0x0001)

            IsObject = CBashBasicType(u'scriptType', 0x0000, u'IsQuest')
            IsQuest = CBashBasicType(u'scriptType', 0x0001, u'IsObject')
            IsEffect = CBashBasicType(u'scriptType', 0x0100, u'IsObject')
            copyattrs = [u'flags', u'conditions_list', u'text',
                         u'numRefs', u'compiledSize',
                         u'lastIndex', u'scriptType', u'flags',
                         u'compiled_p', u'scriptText',
                         u'vars_list', u'references',
                         u'nextQuest']
            exportattrs = copyattrs[:]
            exportattrs.remove(u'compiled_p')

        stage = CBashGeneric_LIST(1, c_short)

        def create_entry(self):
            length = _CGetFieldAttribute(self._RecordID, self._FieldID, self._ListIndex, 2, 0, 0, 0, 0, 1)
            _CSetField(self._RecordID, self._FieldID, self._ListIndex, 2, 0, 0, 0, 0, 0, c_ulong(length + 1))
            return self.Entry(self._RecordID, self._FieldID, self._ListIndex, 2, length)
        entries = CBashLIST_LIST(2, Entry)
        entries_list = CBashLIST_LIST(2, Entry, True)

        exportattrs = copyattrs = [u'stage', u'entries_list']

    class Objective(ListComponent):
        __slots__ = []
        class Target(ListX2Component):
            __slots__ = []
            targetId = CBashFORMID_LISTX2(1)
            flags = CBashGeneric_LISTX2(2, c_ubyte)
            unused1 = CBashUINT8ARRAY_LISTX2(3, 3)

            def create_condition(self):
                length = _CGetFieldAttribute(self._RecordID, self._FieldID, self._ListIndex, self._ListFieldID, self._ListX2Index, 4, 0, 0, 1)
                _CSetField(self._RecordID, self._FieldID, self._ListIndex, self._ListFieldID, self._ListX2Index, 4, 0, 0, 0, c_ulong(length + 1))
                return FNVConditionX3(self._RecordID, self._FieldID, self._ListIndex, self._ListFieldID, self._ListX2Index, 4, length)
            conditions = CBashLIST_LISTX2(4, FNVConditionX3)
            conditions_list = CBashLIST_LISTX2(4, FNVConditionX3, True)


            IsIgnoresLocks = CBashBasicFlag(u'flags', 0x00000001)
            exportattrs = copyattrs = [u'targetId', u'flags', u'conditions_list']

        objective = CBashGeneric_LIST(1, c_long)
        text = CBashSTRING_LIST(2)

        def create_target(self):
            length = _CGetFieldAttribute(self._RecordID, self._FieldID, self._ListIndex, 3, 0, 0, 0, 0, 1)
            _CSetField(self._RecordID, self._FieldID, self._ListIndex, 3, 0, 0, 0, 0, 0, c_ulong(length + 1))
            return self.Target(self._RecordID, self._FieldID, self._ListIndex, 3, length)
        targets = CBashLIST_LIST(3, Target)
        targets_list = CBashLIST_LIST(3, Target, True)

        exportattrs = copyattrs = [u'objective', u'text', u'targets_list']

    script = CBashFORMID(7)
    full = CBashSTRING(8)
    iconPath = CBashISTRING(9)
    smallIconPath = CBashISTRING(10)
    flags = CBashGeneric(11, c_ubyte)
    priority = CBashGeneric(12, c_ubyte)
    unused1 = CBashUINT8ARRAY(13, 2)
    delay = CBashFLOAT32(14)

    def create_condition(self):
        length = _CGetFieldAttribute(self._RecordID, 15, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 15, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return FNVCondition(self._RecordID, 15, length)
    conditions = CBashLIST(15, FNVCondition)
    conditions_list = CBashLIST(15, FNVCondition, True)

    def create_stage(self):
        length = _CGetFieldAttribute(self._RecordID, 16, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 16, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return self.Stage(self._RecordID, 16, length)
    stages = CBashLIST(16, Stage)
    stages_list = CBashLIST(16, Stage, True)

    def create_objectiv(self):
        length = _CGetFieldAttribute(self._RecordID, 17, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 17, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return self.Objective(self._RecordID, 17, length)
    objectives = CBashLIST(17, Objective)
    objectives_list = CBashLIST(17, Objective, True)


    IsStartEnabled = CBashBasicFlag(u'flags', 0x00000001)
    IsRepeatedTopics = CBashBasicFlag(u'flags', 0x00000004)
    IsRepeatedStages = CBashBasicFlag(u'flags', 0x00000008)
    IsUnknown = CBashBasicFlag(u'flags', 0x00000010)
    exportattrs = copyattrs = FnvBaseRecord.baseattrs + [u'script', u'full', u'iconPath',
                                                         u'smallIconPath', u'flags',
                                                         u'priority', u'delay',
                                                         u'conditions_list',
                                                         u'stages_list', u'objectives_list']

class FnvIDLERecord(FnvBaseRecord):
    __slots__ = []
    _Type = b'IDLE'
    modPath = CBashISTRING(7)
    modb = CBashFLOAT32(8)
    modt_p = CBashUINT8ARRAY(9)

    def create_altTexture(self):
        length = _CGetFieldAttribute(self._RecordID, 10, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 10, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return FNVAltTexture(self._RecordID, 10, length)
    altTextures = CBashLIST(10, FNVAltTexture)
    altTextures_list = CBashLIST(10, FNVAltTexture, True)

    modelFlags = CBashGeneric(11, c_ubyte)
    def create_condition(self):
        length = _CGetFieldAttribute(self._RecordID, 12, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 12, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return FNVCondition(self._RecordID, 12, length)
    conditions = CBashLIST(12, FNVCondition)
    conditions_list = CBashLIST(12, FNVCondition, True)

    animations = CBashFORMIDARRAY(13)
    group = CBashGeneric(14, c_ubyte)
    minLooping = CBashGeneric(15, c_ubyte)
    maxLooping = CBashGeneric(16, c_ubyte)
    unused1 = CBashUINT8ARRAY(17, 1)
    replayDelay = CBashGeneric(18, c_short)
    flags = CBashGeneric(19, c_ubyte)
    unused2 = CBashUINT8ARRAY(20, 1)

    IsNoAttacking = CBashBasicFlag(u'flags', 0x00000001)
    IsAttacking = CBashInvertedFlag(u'IsNoAttacking')

    IsIdle = CBashMaskedType(u'group',  ~0xC0, 0, u'IsIdle')
    IsMovement = CBashMaskedType(u'group',  ~0xC0, 1, u'IsMovement')
    IsLeftArm = CBashMaskedType(u'group',  ~0xC0, 2, u'IsMovement')
    IsLeftHand = CBashMaskedType(u'group',  ~0xC0, 3, u'IsMovement')
    IsWeapon = CBashMaskedType(u'group',  ~0xC0, 4, u'IsMovement')
    IsWeaponUp = CBashMaskedType(u'group',  ~0xC0, 5, u'IsMovement')
    IsWeaponDown = CBashMaskedType(u'group',  ~0xC0, 6, u'IsMovement')
    IsSpecialIdle = CBashMaskedType(u'group',  ~0xC0, 7, u'IsMovement')
    IsWholeBody = CBashMaskedType(u'group',  ~0xC0, 20, u'IsMovement')
    IsUpperBody = CBashMaskedType(u'group',  ~0xC0, 21, u'IsMovement')

    IsUnknown1 = CBashBasicFlag(u'group', 0x40)
    IsNotReturnFile = CBashBasicFlag(u'group', 0x80)
    IsReturnFile = CBashInvertedFlag(u'IsNotReturnFile')
    copyattrs = FnvBaseRecord.baseattrs + [u'modPath', u'modb', u'modt_p',
                                           u'altTextures_list', u'modelFlags',
                                           u'conditions_list', u'animations',
                                           u'group', u'minLooping',
                                           u'maxLooping', u'replayDelay',
                                           u'flags']
    exportattrs = copyattrs[:]
    exportattrs.remove(u'modt_p')

class FnvPACKRecord(FnvBaseRecord):
    __slots__ = []
    _Type = b'PACK'
    class PackScript(BaseComponent):
        __slots__ = []
        idle = CBashFORMID_GROUP(0)
        unused1 = CBashUINT8ARRAY_GROUP(1, 4)
        numRefs = CBashGeneric_GROUP(2, c_ulong)
        compiledSize = CBashGeneric_GROUP(3, c_ulong)
        lastIndex = CBashGeneric_GROUP(4, c_ulong)
        scriptType = CBashGeneric_GROUP(5, c_ushort)
        scriptFlags = CBashGeneric_GROUP(6, c_ushort)
        compiled_p = CBashUINT8ARRAY_GROUP(7)
        scriptText = CBashISTRING_GROUP(8)
        def create_var(self):
            FieldID = self._FieldID + 9
            length = _CGetFieldAttribute(self._RecordID, FieldID, 0, 0, 0, 0, 0, 0, 1)
            _CSetField(self._RecordID, FieldID, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
            return Var(self._RecordID, FieldID, length)
        vars = CBashLIST_GROUP(9, Var)
        vars_list = CBashLIST_GROUP(9, Var, True)
        references = CBashFORMID_OR_UINT32_ARRAY_GROUP(10)
        topic = CBashFORMID_GROUP(11)

        IsEnabled = CBashBasicFlag(u'scriptFlags', 0x0001)

        IsObject = CBashBasicType(u'scriptType', 0x0000, u'IsQuest')
        IsQuest = CBashBasicType(u'scriptType', 0x0001, u'IsObject')
        IsEffect = CBashBasicType(u'scriptType', 0x0100, u'IsObject')
        copyattrs = [u'idle', u'numRefs', u'compiledSize',
                     u'lastIndex', u'scriptType', u'scriptFlags',
                     u'compiled_p', u'scriptText',
                     u'vars_list', u'references', u'topic']
        exportattrs = copyattrs[:]
        exportattrs.remove(u'compiled_p')

    flags = CBashGeneric(7, c_ulong)
    aiType = CBashGeneric(8, c_ubyte)
    unused1 = CBashUINT8ARRAY(9, 1)
    behaviorFlags = CBashGeneric(10, c_ushort)
    specificFlags = CBashGeneric(11, c_ushort)
    unused2 = CBashUINT8ARRAY(12, 2)
    loc1Type = CBashGeneric(13, c_long)
    loc1Id = CBashFORMID_OR_UINT32(14)
    loc1Radius = CBashGeneric(15, c_long)
    loc2Type = CBashGeneric(16, c_long)
    loc2Id = CBashFORMID_OR_UINT32(17)
    loc2Radius = CBashGeneric(18, c_long)
    month = CBashGeneric(19, c_byte)
    day = CBashGeneric(20, c_byte)
    date = CBashGeneric(21, c_ubyte)
    time = CBashGeneric(22, c_byte)
    duration = CBashGeneric(23, c_long)
    target1Type = CBashGeneric(24, c_long)
    target1Id = CBashFORMID_OR_UINT32(25)
    target1CountOrDistance = CBashGeneric(26, c_long)
    target1Unknown = CBashFLOAT32(27)

    def create_condition(self):
        length = _CGetFieldAttribute(self._RecordID, 28, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 28, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return FNVCondition(self._RecordID, 28, length)
    conditions = CBashLIST(28, FNVCondition)
    conditions_list = CBashLIST(28, FNVCondition, True)

    idleAnimFlags = CBashGeneric(29, c_ubyte)
    idleAnimCount = CBashGeneric(30, c_ubyte)
    idleTimer = CBashFLOAT32(31)
    animations = CBashFORMIDARRAY(32)
    unusedIDLB_p = CBashUINT8ARRAY(33)
    escortDistance = CBashGeneric(34, c_ulong)
    combatStyle = CBashFORMID(35)
    followTriggerRadius = CBashFLOAT32(36)
    patrolType = CBashGeneric(37, c_ushort)
    weaponFlags = CBashGeneric(38, c_ulong)
    fireRate = CBashGeneric(39, c_ubyte)
    fireType = CBashGeneric(40, c_ubyte)
    burstNum = CBashGeneric(41, c_ushort)
    minShots = CBashGeneric(42, c_ushort)
    maxShots = CBashGeneric(43, c_ushort)
    minPause = CBashFLOAT32(44)
    maxPause = CBashFLOAT32(45)
    unused3 = CBashUINT8ARRAY(46, 4)
    target2Type = CBashGeneric(47, c_long)
    target2Id = CBashFORMID_OR_UINT32(48)
    target2CountOrDistance = CBashGeneric(49, c_long)
    target2Unknown = CBashFLOAT32(50)
    FOV = CBashFLOAT32(51)
    topic = CBashFORMID(52)
    dialFlags = CBashGeneric(53, c_ulong)
    unused4 = CBashUINT8ARRAY(54, 4)
    dialType = CBashGeneric(55, c_ulong)
    dialUnknown = CBashUINT8ARRAY(56)
    begin = CBashGrouped(57, PackScript)
    begin_list = CBashGrouped(57, PackScript, True)

    end = CBashGrouped(69, PackScript)
    end_list = CBashGrouped(69, PackScript, True)

    change = CBashGrouped(81, PackScript)
    change_list = CBashGrouped(81, PackScript, True)


    IsOffersServices = CBashBasicFlag(u'flags', 0x00000001)
    IsMustReachLocation = CBashBasicFlag(u'flags', 0x00000002)
    IsMustComplete = CBashBasicFlag(u'flags', 0x00000004)
    IsLockAtStart = CBashBasicFlag(u'flags', 0x00000008)
    IsLockAtEnd = CBashBasicFlag(u'flags', 0x00000010)
    IsLockAtLocation = CBashBasicFlag(u'flags', 0x00000020)
    IsUnlockAtStart = CBashBasicFlag(u'flags', 0x00000040)
    IsUnlockAtEnd = CBashBasicFlag(u'flags', 0x00000080)
    IsUnlockAtLocation = CBashBasicFlag(u'flags', 0x00000100)
    IsContinueIfPcNear = CBashBasicFlag(u'flags', 0x00000200)
    IsOncePerDay = CBashBasicFlag(u'flags', 0x00000400)
    IsSkipFallout = CBashBasicFlag(u'flags', 0x00001000)
    IsAlwaysRun = CBashBasicFlag(u'flags', 0x00002000)
    IsAlwaysSneak = CBashBasicFlag(u'flags', 0x00020000)
    IsAllowSwimming = CBashBasicFlag(u'flags', 0x00040000)
    IsAllowFalls = CBashBasicFlag(u'flags', 0x00080000)
    IsHeadTrackingOff = CBashBasicFlag(u'flags', 0x00100000)
    IsUnequipWeapons = CBashBasicFlag(u'flags', 0x00200000)
    IsDefensiveCombat = CBashBasicFlag(u'flags', 0x00400000)
    IsWeaponDrawn = CBashBasicFlag(u'flags', 0x00800000)
    IsNoIdleAnims = CBashBasicFlag(u'flags', 0x01000000)
    IsPretendInCombat = CBashBasicFlag(u'flags', 0x02000000)
    IsContinueDuringCombat = CBashBasicFlag(u'flags', 0x04000000)
    IsNoCombatAlert = CBashBasicFlag(u'flags', 0x08000000)
    IsNoWarnAttackBehavior = CBashBasicFlag(u'flags', 0x10000000)

    IsHellosToPlayer = CBashBasicFlag(u'behaviorFlags', 0x00000001)
    IsRandomConversations = CBashBasicFlag(u'behaviorFlags', 0x00000002)
    IsObserveCombatBehavior = CBashBasicFlag(u'behaviorFlags', 0x00000004)
    IsUnknown4 = CBashBasicFlag(u'behaviorFlags', 0x00000008)
    IsReactionToPlayerActions = CBashBasicFlag(u'behaviorFlags', 0x00000010)
    IsFriendlyFireComments = CBashBasicFlag(u'behaviorFlags', 0x00000020)
    IsAggroRadiusBehavior = CBashBasicFlag(u'behaviorFlags', 0x00000040)
    IsAllowIdleChatter = CBashBasicFlag(u'behaviorFlags', 0x00000080)
    IsAvoidRadiation = CBashBasicFlag(u'behaviorFlags', 0x00000100)

    IsHide = CBashBasicFlag(u'specificFlags', 0x00000001) #Ambush only
    IsNoEating = CBashBasicFlag(u'specificFlags', 0x00000001)
    IsNoSleeping = CBashBasicFlag(u'specificFlags', 0x00000002)
    IsSitDown = CBashBasicFlag(u'specificFlags', 0x00000002) #Use Item At only
    IsNoConversation = CBashBasicFlag(u'specificFlags', 0x00000004)
    IsRemainNearReference = CBashBasicFlag(u'specificFlags', 0x00000004) #Guard only
    IsNoIdleMarkers = CBashBasicFlag(u'specificFlags', 0x00000008)
    IsNoFurniture = CBashBasicFlag(u'specificFlags', 0x00000010)
    IsNoWandering = CBashBasicFlag(u'specificFlags', 0x00000020)
    IsAllowBuying = CBashBasicFlag(u'specificFlags', 0x00000100)
    IsAllowKilling = CBashBasicFlag(u'specificFlags', 0x00000200)
    IsAllowStealing = CBashBasicFlag(u'specificFlags', 0x00000400)

    IsRunInSequence = CBashBasicFlag(u'idleAnimFlags', 0x00000001)
    IsDoOnce = CBashBasicFlag(u'idleAnimFlags', 0x00000004)

    IsAlwaysHit = CBashBasicFlag(u'weaponFlags', 0x00000001)
    IsDoNoDamage = CBashBasicFlag(u'weaponFlags', 0x00000100)
    IsCrouchToReload = CBashBasicFlag(u'weaponFlags', 0x00010000)
    IsHoldFireWhenBlocked = CBashBasicFlag(u'weaponFlags', 0x01000000)

    IsNoHeadtracking = CBashBasicFlag(u'dialFlags', 0x00000001)
    IsDontControlTargetMovement = CBashBasicFlag(u'dialFlags', 0x00000100)

    IsAIFind = CBashBasicType(u'aiType', 0, u'IsAIFollow')
    IsAIFollow = CBashBasicType(u'aiType', 1, u'IsAIFind')
    IsAIEscort = CBashBasicType(u'aiType', 2, u'IsAIFind')
    IsAIEat = CBashBasicType(u'aiType', 3, u'IsAIFind')
    IsAISleep = CBashBasicType(u'aiType', 4, u'IsAIFind')
    IsAIWander = CBashBasicType(u'aiType', 5, u'IsAIFind')
    IsAITravel = CBashBasicType(u'aiType', 6, u'IsAIFind')
    IsAIAccompany = CBashBasicType(u'aiType', 7, u'IsAIFind')
    IsAIUseItemAt = CBashBasicType(u'aiType', 8, u'IsAIFind')
    IsAIAmbush = CBashBasicType(u'aiType', 9, u'IsAIFind')
    IsAIFleeNotCombat = CBashBasicType(u'aiType', 10, u'IsAIFind')
    IsAISandbox = CBashBasicType(u'aiType', 12, u'IsAIFind')
    IsAIPatrol = CBashBasicType(u'aiType', 13, u'IsAIFind')
    IsAIGuard = CBashBasicType(u'aiType', 14, u'IsAIFind')
    IsAIDialogue = CBashBasicType(u'aiType', 15, u'IsAIFind')
    IsAIUseWeapon = CBashBasicType(u'aiType', 16, u'IsAIFind')

    IsLoc1NearReference = CBashBasicType(u'loc1Type', 0, u'IsLoc1InCell')
    IsLoc1InCell = CBashBasicType(u'loc1Type', 1, u'IsLoc1NearReference')
    IsLoc1NearCurrentLocation = CBashBasicType(u'loc1Type', 2, u'IsLoc1NearReference')
    IsLoc1NearEditorLocation = CBashBasicType(u'loc1Type', 3, u'IsLoc1NearReference')
    IsLoc1ObjectID = CBashBasicType(u'loc1Type', 4, u'IsLoc1NearReference')
    IsLoc1ObjectType = CBashBasicType(u'loc1Type', 5, u'IsLoc1NearReference')
    IsLoc1NearLinkedReference = CBashBasicType(u'loc1Type', 6, u'IsLoc1NearReference')
    IsLoc1AtPackageLocation = CBashBasicType(u'loc1Type', 7, u'IsLoc1NearReference')

    IsLoc2NearReference = CBashBasicType(u'loc2Type', 0, u'IsLoc2InCell')
    IsLoc2InCell = CBashBasicType(u'loc2Type', 1, u'IsLoc2NearReference')
    IsLoc2NearCurrentLocation = CBashBasicType(u'loc2Type', 2, u'IsLoc2NearReference')
    IsLoc2NearEditorLocation = CBashBasicType(u'loc2Type', 3, u'IsLoc2NearReference')
    IsLoc2ObjectID = CBashBasicType(u'loc2Type', 4, u'IsLoc2NearReference')
    IsLoc2ObjectType = CBashBasicType(u'loc2Type', 5, u'IsLoc2NearReference')
    IsLoc2NearLinkedReference = CBashBasicType(u'loc2Type', 6, u'IsLoc2NearReference')
    IsLoc2AtPackageLocation = CBashBasicType(u'loc2Type', 7, u'IsLoc2NearReference')

    IsAnyDay = CBashBasicType(u'day', -1, u'IsSunday')
    IsSunday = CBashBasicType(u'day', 0, u'IsAnyDay')
    IsMonday = CBashBasicType(u'day', 1, u'IsAnyDay')
    IsTuesday = CBashBasicType(u'day', 2, u'IsAnyDay')
    IsWednesday = CBashBasicType(u'day', 3, u'IsAnyDay')
    IsThursday = CBashBasicType(u'day', 4, u'IsAnyDay')
    IsFriday = CBashBasicType(u'day', 5, u'IsAnyDay')
    IsSaturday = CBashBasicType(u'day', 6, u'IsAnyDay')
    IsWeekdays = CBashBasicType(u'day', 7, u'IsAnyDay')
    IsWeekends = CBashBasicType(u'day', 8, u'IsAnyDay')
    IsMWF = CBashBasicType(u'day', 9, u'IsAnyDay')
    IsTTh = CBashBasicType(u'day', 10, u'IsAnyDay')

    IsTarget1Reference = CBashBasicType(u'target1Type', 0, u'IsTarget1Reference')
    IsTarget1ObjectID = CBashBasicType(u'target1Type', 1, u'IsTarget1Reference')
    IsTarget1ObjectType = CBashBasicType(u'target1Type', 2, u'IsTarget1Reference')
    IsTarget1LinkedReference = CBashBasicType(u'target1Type', 3, u'IsTarget1Reference')

    IsTarget2Reference = CBashBasicType(u'target2Type', 0, u'IsTarget2Reference')
    IsTarget2ObjectID = CBashBasicType(u'target2Type', 1, u'IsTarget2Reference')
    IsTarget2ObjectType = CBashBasicType(u'target2Type', 2, u'IsTarget2Reference')
    IsTarget2LinkedReference = CBashBasicType(u'target2Type', 3, u'IsTarget2Reference')

    IsNotRepeatable = CBashBasicType(u'patrolType', 0, u'IsRepeatable')
    IsRepeatable = CBashBasicType(u'patrolType', 1, u'IsNotRepeatable')

    IsAutoFire = CBashBasicType(u'fireRate', 0, u'IsVolleyFire')
    IsVolleyFire = CBashBasicType(u'fireRate', 1, u'IsAutoFire')

    IsNumberOfBursts = CBashBasicType(u'fireType', 0, u'IsRepeatFire')
    IsRepeatFire = CBashBasicType(u'fireType', 1, u'IsNumberOfBursts')

    IsConversation = CBashBasicType(u'dialType', 0, u'IsSayTo')
    IsSayTo = CBashBasicType(u'dialType', 1, u'IsConversation')
    copyattrs = FnvBaseRecord.baseattrs + [
        u'flags', u'aiType', u'behaviorFlags', u'specificFlags', u'loc1Type',
        u'loc1Id', u'loc1Radius', u'loc2Type', u'loc2Id', u'loc2Radius',
        u'month', u'day', u'date', u'time', u'duration', u'target1Type',
        u'target1Id', u'target1CountOrDistance', u'target1Unknown',
        u'conditions_list', u'idleAnimFlags', u'idleAnimCount', u'idleTimer',
        u'animations', u'escortDistance', u'combatStyle',
        u'followTriggerRadius', u'patrolType', u'weaponFlags', u'fireRate',
        u'fireType', u'burstNum', u'minShots', u'maxShots', u'minPause',
        u'maxPause', u'target2Type', u'target2Id', u'target2CountOrDistance',
        u'target2Unknown', u'FOV', u'topic', u'dialFlags', u'dialType',
        u'dialUnknown', u'begin_list', u'end_list', u'change_list']
    exportattrs = copyattrs[:]
    exportattrs.remove(u'target1Unknown')
    exportattrs.remove(u'target2Unknown')
    exportattrs.remove(u'dialUnknown')

class FnvCSTYRecord(FnvBaseRecord):
    __slots__ = []
    _Type = b'CSTY'
    dodgeChance = CBashGeneric(7, c_ubyte)
    lrChance = CBashGeneric(8, c_ubyte)
    unused1 = CBashUINT8ARRAY(9, 2)
    lrTimerMin = CBashFLOAT32(10)
    lrTimerMax = CBashFLOAT32(11)
    forTimerMin = CBashFLOAT32(12)
    forTimerMax = CBashFLOAT32(13)
    backTimerMin = CBashFLOAT32(14)
    backTimerMax = CBashFLOAT32(15)
    idleTimerMin = CBashFLOAT32(16)
    idleTimerMax = CBashFLOAT32(17)
    blkChance = CBashGeneric(18, c_ubyte)
    atkChance = CBashGeneric(19, c_ubyte)
    unused2 = CBashUINT8ARRAY(20, 2)
    atkBRecoil = CBashFLOAT32(21)
    atkBUnc = CBashFLOAT32(22)
    atkBh2h = CBashFLOAT32(23)
    pAtkChance = CBashGeneric(24, c_ubyte)
    unused3 = CBashUINT8ARRAY(25, 3)
    pAtkBRecoil = CBashFLOAT32(26)
    pAtkBUnc = CBashFLOAT32(27)
    pAtkNormal = CBashGeneric(28, c_ubyte)
    pAtkFor = CBashGeneric(29, c_ubyte)
    pAtkBack = CBashGeneric(30, c_ubyte)
    pAtkL = CBashGeneric(31, c_ubyte)
    pAtkR = CBashGeneric(32, c_ubyte)
    unused4 = CBashUINT8ARRAY(33, 3)
    holdTimerMin = CBashFLOAT32(34)
    holdTimerMax = CBashFLOAT32(35)
    flags = CBashGeneric(36, c_ushort)
    unused5 = CBashUINT8ARRAY(37, 2)
    acroDodge = CBashGeneric(38, c_ubyte)
    rushChance = CBashGeneric(39, c_ubyte)
    unused6 = CBashUINT8ARRAY(40, 2)
    rushMult = CBashFLOAT32(41)
    dodgeFMult = CBashFLOAT32(42)
    dodgeFBase = CBashFLOAT32(43)
    encSBase = CBashFLOAT32(44)
    encSMult = CBashFLOAT32(45)
    dodgeAtkMult = CBashFLOAT32(46)
    dodgeNAtkMult = CBashFLOAT32(47)
    dodgeBAtkMult = CBashFLOAT32(48)
    dodgeBNAtkMult = CBashFLOAT32(49)
    dodgeFAtkMult = CBashFLOAT32(50)
    dodgeFNAtkMult = CBashFLOAT32(51)
    blockMult = CBashFLOAT32(52)
    blockBase = CBashFLOAT32(53)
    blockAtkMult = CBashFLOAT32(54)
    blockNAtkMult = CBashFLOAT32(55)
    atkMult = CBashFLOAT32(56)
    atkBase = CBashFLOAT32(57)
    atkAtkMult = CBashFLOAT32(58)
    atkNAtkMult = CBashFLOAT32(59)
    atkBlockMult = CBashFLOAT32(60)
    pAtkFBase = CBashFLOAT32(61)
    pAtkFMult = CBashFLOAT32(62)
    coverRadius = CBashFLOAT32(63)
    coverChance = CBashFLOAT32(64)
    waitTimerMin = CBashFLOAT32(65)
    waitTimerMax = CBashFLOAT32(66)
    waitFireTimerMin = CBashFLOAT32(67)
    waitFireTimerMax = CBashFLOAT32(68)
    fireTimerMin = CBashFLOAT32(69)
    fireTimerMax = CBashFLOAT32(70)
    rangedRangeMultMin = CBashFLOAT32(71)
    unused7 = CBashUINT8ARRAY(72, 4)
    weaponRestrictions = CBashGeneric(73, c_ulong)
    rangedRangeMultMax = CBashFLOAT32(74)
    targetMaxFOV = CBashFLOAT32(75)
    combatRadius = CBashFLOAT32(76)
    semiAutoFireDelayMultMin = CBashFLOAT32(77)
    semiAutoFireDelayMultMax = CBashFLOAT32(78)

    IsUseChanceForAttack = CBashBasicFlag(u'flags', 0x00000001)
    IsMeleeAlertOK = CBashBasicFlag(u'flags', 0x00000002)
    IsFleeForSurvival = CBashBasicFlag(u'flags', 0x00000004)
    IsIgnoreThreats = CBashBasicFlag(u'flags', 0x00000010)
    IsIgnoreDamagingSelf = CBashBasicFlag(u'flags', 0x00000020)
    IsIgnoreDamagingGroup = CBashBasicFlag(u'flags', 0x00000040)
    IsIgnoreDamagingSpectator = CBashBasicFlag(u'flags', 0x00000080)
    IsNoUseStealthboy = CBashBasicFlag(u'flags', 0x00000100)

    IsNone = CBashBasicType(u'weaponRestrictions', 0, u'IsMeleeOnly')
    IsMeleeOnly = CBashBasicType(u'weaponRestrictions', 1, u'IsNone')
    IsRangedOnly = CBashBasicType(u'weaponRestrictions', 2, u'IsNone')
    exportattrs = copyattrs = FnvBaseRecord.baseattrs + [
        u'dodgeChance', u'lrChance', u'lrTimerMin', u'lrTimerMax',
        u'forTimerMin', u'forTimerMax', u'backTimerMin', u'backTimerMax',
        u'idleTimerMin', u'idleTimerMax', u'blkChance', u'atkChance',
        u'atkBRecoil', u'atkBUnc', u'atkBh2h', u'pAtkChance', u'pAtkBRecoil',
        u'pAtkBUnc', u'pAtkNormal', u'pAtkFor', u'pAtkBack', u'pAtkL',
        u'pAtkR', u'holdTimerMin', u'holdTimerMax', u'flags', u'acroDodge',
        u'rushChance', u'rushMult', u'dodgeFMult', u'dodgeFBase', u'encSBase',
        u'encSMult', u'dodgeAtkMult', u'dodgeNAtkMult', u'dodgeBAtkMult',
        u'dodgeBNAtkMult', u'dodgeFAtkMult', u'dodgeFNAtkMult', u'blockMult',
        u'blockBase', u'blockAtkMult', u'blockNAtkMult', u'atkMult',
        u'atkBase', u'atkAtkMult', u'atkNAtkMult', u'atkBlockMult',
        u'pAtkFBase', u'pAtkFMult', u'coverRadius', u'coverChance',
        u'waitTimerMin', u'waitTimerMax', u'waitFireTimerMin',
        u'waitFireTimerMax', u'fireTimerMin', u'fireTimerMax',
        u'rangedRangeMultMin', u'weaponRestrictions', u'rangedRangeMultMax',
        u'targetMaxFOV', u'combatRadius', u'semiAutoFireDelayMultMin',
        u'semiAutoFireDelayMultMax']

class FnvLSCRRecord(FnvBaseRecord):
    __slots__ = []
    _Type = b'LSCR'
    class Location(ListComponent):
        __slots__ = []
        direct = CBashFORMID_LIST(1)
        indirect = CBashFORMID_LIST(2)
        gridY = CBashGeneric_LIST(3, c_short)
        gridX = CBashGeneric_LIST(4, c_short)
        exportattrs = copyattrs = [u'direct', u'indirect', u'gridY', u'gridX']

    iconPath = CBashISTRING(7)
    smallIconPath = CBashISTRING(8)
    text = CBashSTRING(9)

    def create_location(self):
        length = _CGetFieldAttribute(self._RecordID, 10, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 10, 0, 0, 0, 0, 0, 0, 0, c_ulong(length +
                                                                    1))
        return self.Location(self._RecordID, 10, length)
    locations = CBashLIST(10, Location)
    locations_list = CBashLIST(10, Location, True)

    screentype = CBashFORMID(11)
    exportattrs = copyattrs = FnvBaseRecord.baseattrs + [u'iconPath',
                                                         u'smallIconPath', u'text',
                                                         u'locations_list',
                                                         u'screentype']

class FnvANIORecord(FnvBaseRecord):
    __slots__ = []
    _Type = b'ANIO'
    modPath = CBashISTRING(7)
    modb = CBashFLOAT32(8)
    modt_p = CBashUINT8ARRAY(9)

    def create_altTexture(self):
        length = _CGetFieldAttribute(self._RecordID, 10, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 10, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return FNVAltTexture(self._RecordID, 10, length)
    altTextures = CBashLIST(10, FNVAltTexture)
    altTextures_list = CBashLIST(10, FNVAltTexture, True)

    modelFlags = CBashGeneric(11, c_ubyte)
    animation = CBashFORMID(12)
    copyattrs = FnvBaseRecord.baseattrs + [u'modPath', u'modb', u'modt_p',
                                           u'altTextures_list',
                                           u'modelFlags', u'animation']
    exportattrs = copyattrs[:]
    exportattrs.remove(u'modt_p')

class FnvWATRRecord(FnvBaseRecord):
    __slots__ = []
    _Type = b'WATR'
    full = CBashSTRING(7)
    noisePath = CBashISTRING(8)
    opacity = CBashGeneric(9, c_ubyte)
    flags = CBashGeneric(10, c_ubyte)
    material = CBashISTRING(11)
    sound = CBashFORMID(12)
    effect = CBashFORMID(13)
    damage = CBashGeneric(14, c_ushort)
    unknown1 = CBashFLOAT32(15)
    unknown2 = CBashFLOAT32(16)
    unknown3 = CBashFLOAT32(17)
    unknown4 = CBashFLOAT32(18)
    sunPower = CBashFLOAT32(19)
    reflectAmt = CBashFLOAT32(20)
    fresnelAmt = CBashFLOAT32(21)
    unused1 = CBashUINT8ARRAY(22, 4)
    fogNear = CBashFLOAT32(23)
    fogFar = CBashFLOAT32(24)
    shallowRed = CBashGeneric(25, c_ubyte)
    shallowGreen = CBashGeneric(26, c_ubyte)
    shallowBlue = CBashGeneric(27, c_ubyte)
    unused2 = CBashUINT8ARRAY(28, 1)
    deepRed = CBashGeneric(29, c_ubyte)
    deepGreen = CBashGeneric(30, c_ubyte)
    deepBlue = CBashGeneric(31, c_ubyte)
    unused3 = CBashUINT8ARRAY(32, 1)
    reflRed = CBashGeneric(33, c_ubyte)
    reflGreen = CBashGeneric(34, c_ubyte)
    reflBlue = CBashGeneric(35, c_ubyte)
    unused4 = CBashUINT8ARRAY(36, 1)
    unused5 = CBashUINT8ARRAY(37, 4)
    rainForce = CBashFLOAT32(38)
    rainVelocity = CBashFLOAT32(39)
    rainFalloff = CBashFLOAT32(40)
    rainDampner = CBashFLOAT32(41)
    dispSize = CBashFLOAT32(42)
    dispForce = CBashFLOAT32(43)
    dispVelocity = CBashFLOAT32(44)
    dispFalloff = CBashFLOAT32(45)
    dispDampner = CBashFLOAT32(46)
    rainSize = CBashFLOAT32(47)
    normalsNoiseScale = CBashFLOAT32(48)
    noise1Direction = CBashFLOAT32(49)
    noise2Direction = CBashFLOAT32(50)
    noise3Direction = CBashFLOAT32(51)
    noise1Speed = CBashFLOAT32(52)
    noise2Speed = CBashFLOAT32(53)
    noise3Speed = CBashFLOAT32(54)
    normalsFalloffStart = CBashFLOAT32(55)
    normalsFalloffEnd = CBashFLOAT32(56)
    fogAmt = CBashFLOAT32(57)
    normalsUVScale = CBashFLOAT32(58)
    underFogAmt = CBashFLOAT32(59)
    underFogNear = CBashFLOAT32(60)
    underFogFar = CBashFLOAT32(61)
    distAmt = CBashFLOAT32(62)
    shininess = CBashFLOAT32(63)
    hdrMult = CBashFLOAT32(64)
    lightRadius = CBashFLOAT32(65)
    lightBright = CBashFLOAT32(66)
    noise1UVScale = CBashFLOAT32(67)
    noise2UVScale = CBashFLOAT32(68)
    noise3UVScale = CBashFLOAT32(69)
    noise1AmpScale = CBashFLOAT32(70)
    noise2AmpScale = CBashFLOAT32(71)
    noise3AmpScale = CBashFLOAT32(72)
    dayWater = CBashFORMID(73)
    nightWater = CBashFORMID(74)
    underWater = CBashFORMID(75)
    IsCausesDamage = CBashBasicFlag(u'flags', 0x01)
    IsReflective = CBashBasicFlag(u'flags', 0x02)
    copyattrs = FnvBaseRecord.baseattrs + [
        u'full', u'noisePath', u'opacity', u'flags', u'material', u'sound',
        u'effect', u'damage', u'unknown1', u'unknown2', u'unknown3',
        u'unknown4', u'sunPower', u'reflectAmt', u'fresnelAmt', u'fogNear',
        u'fogFar', u'shallowRed', u'shallowGreen', u'shallowBlue', u'deepRed',
        u'deepGreen', u'deepBlue', u'reflRed', u'reflGreen', u'reflBlue',
        u'rainForce', u'rainVelocity', u'rainFalloff', u'rainDampner',
        u'dispSize', u'dispForce', u'dispVelocity', u'dispFalloff',
        u'dispDampner', u'rainSize', u'normalsNoiseScale', u'noise1Direction',
        u'noise2Direction', u'noise3Direction', u'noise1Speed', u'noise2Speed',
        u'noise3Speed', u'normalsFalloffStart', u'normalsFalloffEnd',
        u'fogAmt', u'normalsUVScale', u'underFogAmt', u'underFogNear',
        u'underFogFar', u'distAmt', u'shininess', u'hdrMult', u'lightRadius',
        u'lightBright', u'noise1UVScale', u'noise2UVScale', u'noise3UVScale',
        u'noise1AmpScale', u'noise2AmpScale', u'noise3AmpScale', u'dayWater',
        u'nightWater', u'underWater']
    exportattrs = copyattrs[:]
    exportattrs.remove(u'unknown1')
    exportattrs.remove(u'unknown2')
    exportattrs.remove(u'unknown3')
    exportattrs.remove(u'unknown4')

class FnvEFSHRecord(FnvBaseRecord):
    __slots__ = []
    _Type = b'EFSH'
    fillPath = CBashISTRING(7)
    particlePath = CBashISTRING(8)
    holesPath = CBashISTRING(9)
    flags = CBashGeneric(10, c_ubyte)
    unused1 = CBashUINT8ARRAY(11, 3)
    memSBlend = CBashGeneric(12, c_ulong)
    memBlendOp = CBashGeneric(13, c_ulong)
    memZFunc = CBashGeneric(14, c_ulong)
    fillRed = CBashGeneric(15, c_ubyte)
    fillGreen = CBashGeneric(16, c_ubyte)
    fillBlue = CBashGeneric(17, c_ubyte)
    unused2 = CBashUINT8ARRAY(18, 1)
    fillAIn = CBashFLOAT32(19)
    fillAFull = CBashFLOAT32(20)
    fillAOut = CBashFLOAT32(21)
    fillAPRatio = CBashFLOAT32(22)
    fillAAmp = CBashFLOAT32(23)
    fillAFreq = CBashFLOAT32(24)
    fillAnimSpdU = CBashFLOAT32(25)
    fillAnimSpdV = CBashFLOAT32(26)
    edgeEffOff = CBashFLOAT32(27)
    edgeEffRed = CBashGeneric(28, c_ubyte)
    edgeEffGreen = CBashGeneric(29, c_ubyte)
    edgeEffBlue = CBashGeneric(30, c_ubyte)
    unused3 = CBashUINT8ARRAY(31, 1)
    edgeEffAIn = CBashFLOAT32(32)
    edgeEffAFull = CBashFLOAT32(33)
    edgeEffAOut = CBashFLOAT32(34)
    edgeEffAPRatio = CBashFLOAT32(35)
    edgeEffAAmp = CBashFLOAT32(36)
    edgeEffAFreq = CBashFLOAT32(37)
    fillAFRatio = CBashFLOAT32(38)
    edgeEffAFRatio = CBashFLOAT32(39)
    memDBlend = CBashGeneric(40, c_ulong)
    partSBlend = CBashGeneric(41, c_ulong)
    partBlendOp = CBashGeneric(42, c_ulong)
    partZFunc = CBashGeneric(43, c_ulong)
    partDBlend = CBashGeneric(44, c_ulong)
    partBUp = CBashFLOAT32(45)
    partBFull = CBashFLOAT32(46)
    partBDown = CBashFLOAT32(47)
    partBFRatio = CBashFLOAT32(48)
    partBPRatio = CBashFLOAT32(49)
    partLTime = CBashFLOAT32(50)
    partLDelta = CBashFLOAT32(51)
    partNSpd = CBashFLOAT32(52)
    partNAcc = CBashFLOAT32(53)
    partVel1 = CBashFLOAT32(54)
    partVel2 = CBashFLOAT32(55)
    partVel3 = CBashFLOAT32(56)
    partAcc1 = CBashFLOAT32(57)
    partAcc2 = CBashFLOAT32(58)
    partAcc3 = CBashFLOAT32(59)
    partKey1 = CBashFLOAT32(60)
    partKey2 = CBashFLOAT32(61)
    partKey1Time = CBashFLOAT32(62)
    partKey2Time = CBashFLOAT32(63)
    key1Red = CBashGeneric(64, c_ubyte)
    key1Green = CBashGeneric(65, c_ubyte)
    key1Blue = CBashGeneric(66, c_ubyte)
    unused4 = CBashUINT8ARRAY(67, 1)
    key2Red = CBashGeneric(68, c_ubyte)
    key2Green = CBashGeneric(69, c_ubyte)
    key2Blue = CBashGeneric(70, c_ubyte)
    unused5 = CBashUINT8ARRAY(71, 1)
    key3Red = CBashGeneric(72, c_ubyte)
    key3Green = CBashGeneric(73, c_ubyte)
    key3Blue = CBashGeneric(74, c_ubyte)
    unused6 = CBashUINT8ARRAY(75, 1)
    key1A = CBashFLOAT32(76)
    key2A = CBashFLOAT32(77)
    key3A = CBashFLOAT32(78)
    key1Time = CBashFLOAT32(79)
    key2Time = CBashFLOAT32(80)
    key3Time = CBashFLOAT32(81)
    partInitSpd = CBashFLOAT32(82)
    partInitRot = CBashFLOAT32(83)
    partInitRotDelta = CBashFLOAT32(84)
    partRotSpd = CBashFLOAT32(85)
    partRotDelta = CBashFLOAT32(86)
    addon = CBashFORMID(87)
    holesSTime = CBashFLOAT32(88)
    holesETime = CBashFLOAT32(89)
    holesSValue = CBashFLOAT32(90)
    holesEValue = CBashFLOAT32(91)
    edgeWidth = CBashFLOAT32(92)
    edgeRed = CBashGeneric(93, c_ubyte)
    edgeGreen = CBashGeneric(94, c_ubyte)
    edgeBlue = CBashGeneric(95, c_ubyte)
    unused7 = CBashUINT8ARRAY(96, 1)
    explWindSpd = CBashFLOAT32(97)
    textCountU = CBashGeneric(98, c_ulong)
    textCountV = CBashGeneric(99, c_ulong)
    addonFITime = CBashFLOAT32(100)
    addonFOTime = CBashFLOAT32(101)
    addonScaleStart = CBashFLOAT32(102)
    addonScaleEnd = CBashFLOAT32(103)
    addonScaleInTime = CBashFLOAT32(104)
    addonScaleOutTime = CBashFLOAT32(105)

    IsNoMemShader = CBashBasicFlag(u'flags', 0x00000001)
    IsNoPartShader = CBashBasicFlag(u'flags', 0x00000008)
    IsEdgeInverse = CBashBasicFlag(u'flags', 0x00000010)
    IsMemSkinOnly = CBashBasicFlag(u'flags', 0x00000020)
    exportattrs = copyattrs = FnvBaseRecord.baseattrs + [
        u'fillPath', u'particlePath', u'holesPath', u'flags', u'memSBlend',
        u'memBlendOp', u'memZFunc', u'fillRed', u'fillGreen', u'fillBlue',
        u'fillAIn', u'fillAFull', u'fillAOut', u'fillAPRatio', u'fillAAmp',
        u'fillAFreq', u'fillAnimSpdU', u'fillAnimSpdV', u'edgeEffOff',
        u'edgeEffRed', u'edgeEffGreen', u'edgeEffBlue', u'edgeEffAIn',
        u'edgeEffAFull', u'edgeEffAOut', u'edgeEffAPRatio', u'edgeEffAAmp',
        u'edgeEffAFreq', u'fillAFRatio', u'edgeEffAFRatio', u'memDBlend',
        u'partSBlend', u'partBlendOp', u'partZFunc', u'partDBlend', u'partBUp',
        u'partBFull', u'partBDown', u'partBFRatio', u'partBPRatio',
        u'partLTime', u'partLDelta', u'partNSpd', u'partNAcc', u'partVel1',
        u'partVel2', u'partVel3', u'partAcc1', u'partAcc2', u'partAcc3',
        u'partKey1', u'partKey2', u'partKey1Time', u'partKey2Time', u'key1Red',
        u'key1Green', u'key1Blue', u'key2Red', u'key2Green', u'key2Blue',
        u'key3Red', u'key3Green', u'key3Blue', u'key1A', u'key2A', u'key3A',
        u'key1Time', u'key2Time', u'key3Time', u'partInitSpd', u'partInitRot',
        u'partInitRotDelta', u'partRotSpd', u'partRotDelta', u'addon',
        u'holesSTime', u'holesETime', u'holesSValue', u'holesEValue',
        u'edgeWidth', u'edgeRed', u'edgeGreen', u'edgeBlue', u'explWindSpd',
        u'textCountU', u'textCountV', u'addonFITime', u'addonFOTime',
        u'addonScaleStart', u'addonScaleEnd', u'addonScaleInTime',
        u'addonScaleOutTime']

class FnvEXPLRecord(FnvBaseRecord):
    __slots__ = []
    _Type = b'EXPL'
    boundX1 = CBashGeneric(7, c_short)
    boundY1 = CBashGeneric(8, c_short)
    boundZ1 = CBashGeneric(9, c_short)
    boundX2 = CBashGeneric(10, c_short)
    boundY2 = CBashGeneric(11, c_short)
    boundZ2 = CBashGeneric(12, c_short)
    full = CBashSTRING(13)
    modPath = CBashISTRING(14)
    modb = CBashFLOAT32(15)
    modt_p = CBashUINT8ARRAY(16)

    def create_altTexture(self):
        length = _CGetFieldAttribute(self._RecordID, 17, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 17, 0, 0, 0, 0, 0, 0, 0, c_ulong(length +
                                                                    1))
        return FNVAltTexture(self._RecordID, 17, length)
    altTextures = CBashLIST(17, FNVAltTexture)
    altTextures_list = CBashLIST(17, FNVAltTexture, True)

    modelFlags = CBashGeneric(18, c_ubyte)
    effect = CBashFORMID(19)
    imageSpace = CBashFORMID(20)
    force = CBashFLOAT32(21)
    damage = CBashFLOAT32(22)
    radius = CBashFLOAT32(23)
    light = CBashFORMID(24)
    sound1 = CBashFORMID(25)
    flags = CBashGeneric(26, c_ulong)
    ISRadius = CBashFLOAT32(27)
    impactDataSet = CBashFORMID(28)
    sound2 = CBashFORMID(29)
    radLevel = CBashFLOAT32(30)
    radTime = CBashFLOAT32(31)
    radRadius = CBashFLOAT32(32)
    soundLevel = CBashGeneric(33, c_ulong)
    impact = CBashFORMID(34)

    IsUnknown1 = CBashBasicFlag(u'flags', 0x00000001)
    IsAlwaysUsesWorldOrientation = CBashBasicFlag(u'flags', 0x00000002)
    IsAlwaysKnockDown = CBashBasicFlag(u'flags', 0x00000004)
    IsFormulaKnockDown = CBashBasicFlag(u'flags', 0x00000008)
    IsIgnoreLOS = CBashBasicFlag(u'flags', 0x00000010)
    IsPushExplosionSourceRefOnly = CBashBasicFlag(u'flags', 0x00000020)
    IsIgnoreImageSpaceSwap = CBashBasicFlag(u'flags', 0x00000040)

    IsHead = CBashBasicFlag(u'modelFlags', 0x01)
    IsTorso = CBashBasicFlag(u'modelFlags', 0x02)
    IsRightHand = CBashBasicFlag(u'modelFlags', 0x04)
    IsLeftHand = CBashBasicFlag(u'modelFlags', 0x08)

    IsLoud = CBashBasicType(u'soundLevel', 0, u'IsNormal')
    IsNormal = CBashBasicType(u'soundLevel', 1, u'IsLoud')
    IsSilent = CBashBasicType(u'soundLevel', 2, u'IsLoud')
    copyattrs = FnvBaseRecord.baseattrs + [u'boundX1', u'boundY1', u'boundZ1',
                                           u'boundX2', u'boundY2', u'boundZ2',
                                           u'full', u'modPath', u'modb', u'modt_p',
                                           u'altTextures_list', u'modelFlags',
                                           u'effect', u'imageSpace', u'force',
                                           u'damage', u'radius', u'light',
                                           u'sound1', u'flags', u'ISRadius',
                                           u'impactDataSet', u'sound2',
                                           u'radLevel', u'radTime',
                                           u'radRadius', u'soundLevel', u'impact']
    exportattrs = copyattrs[:]
    exportattrs.remove(u'modt_p')

class FnvDEBRRecord(FnvBaseRecord):
    __slots__ = []
    _Type = b'DEBR'
    class DebrisModel(ListComponent):
        __slots__ = []
        percentage = CBashGeneric_LIST(1, c_ubyte)
        modPath = CBashISTRING_LIST(2)
        flags = CBashGeneric_LIST(3, c_ubyte)
        modt_p = CBashUINT8ARRAY_LIST(4)

        IsHasCollisionData = CBashBasicFlag(u'flags', 0x01)
        copyattrs = [u'percentage', u'modPath', u'flags', u'modt_p']
        exportattrs = copyattrs[:]
        exportattrs.remove(u'modt_p')

    def create_model(self):
        length = _CGetFieldAttribute(self._RecordID, 7, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 7, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return self.DebrisModel(self._RecordID, 7, length)
    models = CBashLIST(7, DebrisModel)
    models_list = CBashLIST(7, DebrisModel, True)

    exportattrs = copyattrs = FnvBaseRecord.baseattrs + [u'models_list']

class FnvIMGSRecord(FnvBaseRecord):
    __slots__ = []
    _Type = b'IMGS'

    exportattrs = copyattrs = FnvBaseRecord.baseattrs + []

class FnvIMADRecord(FnvBaseRecord):
    __slots__ = []
    _Type = b'IMAD'

    exportattrs = copyattrs = FnvBaseRecord.baseattrs + []

class FnvFLSTRecord(FnvBaseRecord):
    __slots__ = []
    _Type = b'FLST'

    exportattrs = copyattrs = FnvBaseRecord.baseattrs + []

class FnvPERKRecord(FnvBaseRecord):
    __slots__ = []
    _Type = b'PERK'

    exportattrs = copyattrs = FnvBaseRecord.baseattrs + []

class FnvBPTDRecord(FnvBaseRecord):
    __slots__ = []
    _Type = b'BPTD'

    exportattrs = copyattrs = FnvBaseRecord.baseattrs + []

class FnvADDNRecord(FnvBaseRecord):
    __slots__ = []
    _Type = b'ADDN'

    exportattrs = copyattrs = FnvBaseRecord.baseattrs + []

class FnvAVIFRecord(FnvBaseRecord):
    __slots__ = []
    _Type = b'AVIF'

    exportattrs = copyattrs = FnvBaseRecord.baseattrs + []

class FnvRADSRecord(FnvBaseRecord):
    __slots__ = []
    _Type = b'RADS'

    exportattrs = copyattrs = FnvBaseRecord.baseattrs + []

class FnvCAMSRecord(FnvBaseRecord):
    __slots__ = []
    _Type = b'CAMS'

    exportattrs = copyattrs = FnvBaseRecord.baseattrs + []

class FnvCPTHRecord(FnvBaseRecord):
    __slots__ = []
    _Type = b'CPTH'

    exportattrs = copyattrs = FnvBaseRecord.baseattrs + []

class FnvVTYPRecord(FnvBaseRecord):
    __slots__ = []
    _Type = b'VTYP'

    exportattrs = copyattrs = FnvBaseRecord.baseattrs + []

class FnvIPCTRecord(FnvBaseRecord):
    __slots__ = []
    _Type = b'IPCT'

    exportattrs = copyattrs = FnvBaseRecord.baseattrs + []

class FnvIPDSRecord(FnvBaseRecord):
    __slots__ = []
    _Type = b'IPDS'

    exportattrs = copyattrs = FnvBaseRecord.baseattrs + []

class FnvARMARecord(FnvBaseRecord):
    __slots__ = []
    _Type = b'ARMA'

    exportattrs = copyattrs = FnvBaseRecord.baseattrs + []

class FnvECZNRecord(FnvBaseRecord):
    __slots__ = []
    _Type = b'ECZN'

    exportattrs = copyattrs = FnvBaseRecord.baseattrs + []

class FnvMESGRecord(FnvBaseRecord):
    __slots__ = []
    _Type = b'MESG'

    exportattrs = copyattrs = FnvBaseRecord.baseattrs + []

class FnvRGDLRecord(FnvBaseRecord):
    __slots__ = []
    _Type = b'RGDL'

    exportattrs = copyattrs = FnvBaseRecord.baseattrs + []

class FnvDOBJRecord(FnvBaseRecord):
    __slots__ = []
    _Type = b'DOBJ'

    exportattrs = copyattrs = FnvBaseRecord.baseattrs + []

class FnvLGTMRecord(FnvBaseRecord):
    __slots__ = []
    _Type = b'LGTM'

    exportattrs = copyattrs = FnvBaseRecord.baseattrs + []

class FnvMUSCRecord(FnvBaseRecord):
    __slots__ = []
    _Type = b'MUSC'

    exportattrs = copyattrs = FnvBaseRecord.baseattrs + []

class FnvIMODRecord(FnvBaseRecord):
    __slots__ = []
    _Type = b'IMOD'

    exportattrs = copyattrs = FnvBaseRecord.baseattrs + []

class FnvREPURecord(FnvBaseRecord):
    __slots__ = []
    _Type = b'REPU'

    exportattrs = copyattrs = FnvBaseRecord.baseattrs + []

class FnvRCPERecord(FnvBaseRecord):
    __slots__ = []
    _Type = b'RCPE'

    exportattrs = copyattrs = FnvBaseRecord.baseattrs + []

class FnvRCCTRecord(FnvBaseRecord):
    __slots__ = []
    _Type = b'RCCT'

    exportattrs = copyattrs = FnvBaseRecord.baseattrs + []

class FnvCHIPRecord(FnvBaseRecord):
    __slots__ = []
    _Type = b'CHIP'

    exportattrs = copyattrs = FnvBaseRecord.baseattrs + []

class FnvCSNORecord(FnvBaseRecord):
    __slots__ = []
    _Type = b'CSNO'

    exportattrs = copyattrs = FnvBaseRecord.baseattrs + []

class FnvLSCTRecord(FnvBaseRecord):
    __slots__ = []
    _Type = b'LSCT'

    exportattrs = copyattrs = FnvBaseRecord.baseattrs + []

class FnvMSETRecord(FnvBaseRecord):
    __slots__ = []
    _Type = b'MSET'

    exportattrs = copyattrs = FnvBaseRecord.baseattrs + []

class FnvALOCRecord(FnvBaseRecord):
    __slots__ = []
    _Type = b'ALOC'

    exportattrs = copyattrs = FnvBaseRecord.baseattrs + []

class FnvCHALRecord(FnvBaseRecord):
    __slots__ = []
    _Type = b'CHAL'

    exportattrs = copyattrs = FnvBaseRecord.baseattrs + []

class FnvAMEFRecord(FnvBaseRecord):
    __slots__ = []
    _Type = b'AMEF'

    exportattrs = copyattrs = FnvBaseRecord.baseattrs + []

class FnvCCRDRecord(FnvBaseRecord):
    __slots__ = []
    _Type = b'CCRD'

    exportattrs = copyattrs = FnvBaseRecord.baseattrs + []

class FnvCMNYRecord(FnvBaseRecord):
    __slots__ = []
    _Type = b'CMNY'

    exportattrs = copyattrs = FnvBaseRecord.baseattrs + []

class FnvCDCKRecord(FnvBaseRecord):
    __slots__ = []
    _Type = b'CDCK'

    exportattrs = copyattrs = FnvBaseRecord.baseattrs + []

class FnvDEHYRecord(FnvBaseRecord):
    __slots__ = []
    _Type = b'DEHY'

    exportattrs = copyattrs = FnvBaseRecord.baseattrs + []

class FnvHUNGRecord(FnvBaseRecord):
    __slots__ = []
    _Type = b'HUNG'

    exportattrs = copyattrs = FnvBaseRecord.baseattrs + []

class FnvSLPDRecord(FnvBaseRecord):
    __slots__ = []
    _Type = b'SLPD'

    exportattrs = copyattrs = FnvBaseRecord.baseattrs + []

#--Oblivion
class ObBaseRecord(object):
    __slots__ = [u'_RecordID']
    _Type = b'BASE'
    def __init__(self, RecordID):
        self._RecordID = RecordID

    def __eq__(self, other):
        return self._RecordID == other._RecordID if type(other) is type(self) else False

    def __ne__(self, other):
        return not self.__eq__(other)

    def GetParentMod(self):
        return ObModFile(_CGetModIDByRecordID(self._RecordID))

    def GetParentCollection(self):
        return ObCollection(_CGetCollectionIDByRecordID(self._RecordID))

    def ResetRecord(self):
        _CResetRecord(self._RecordID)

    def UnloadRecord(self):
        _CUnloadRecord(self._RecordID)

    def DeleteRecord(self):
        _CDeleteRecord(self._RecordID)

    def GetRecordUpdatedReferences(self):
        return _CGetRecordUpdatedReferences(None, self._RecordID)

    def UpdateReferences(self, Old_NewFormIDs):
        Old_NewFormIDs = FormID.FilterValidDict(Old_NewFormIDs, self, True, True, AsShort=True)
        length = len(Old_NewFormIDs)
        if not length: return []
        OldFormIDs = (c_ulong * length)(*Old_NewFormIDs.keys())
        NewFormIDs = (c_ulong * length)(*Old_NewFormIDs.values())
        Changes = (c_ulong * length)()
        _CUpdateReferences(0, self._RecordID, OldFormIDs, NewFormIDs, byref(Changes), length)
        return [x for x in Changes]

    def History(self):
        cRecordIDs = (c_record_p * 257)() #just allocate enough for the max number + size
        numRecords = _CGetRecordHistory(self._RecordID, cRecordIDs)
        return [self.__class__(cRecordIDs[x]) for x in xrange(numRecords)]

    def IsWinning(self, GetExtendedConflicts=False):
        """Returns true if the record is the last to load.
           If GetExtendedConflicts is True, scanned records will be considered.
           More efficient than running Conflicts() and checking the first value."""
        return _CIsRecordWinning(self._RecordID, c_ulong(GetExtendedConflicts)) > 0

    def HasInvalidFormIDs(self):
        return _CIsRecordFormIDsInvalid(self._RecordID) > 0

    def Conflicts(self, GetExtendedConflicts=False):
        numRecords = _CGetNumRecordConflicts(self._RecordID, c_ulong(GetExtendedConflicts)) #gives upper bound
        if(numRecords > 1):
            cRecordIDs = (c_record_p * numRecords)()
            numRecords = _CGetRecordConflicts(self._RecordID, cRecordIDs, c_ulong(GetExtendedConflicts))
            return [self.__class__(cRecordIDs[x]) for x in xrange(numRecords)]
        return []

    def ConflictDetails(self, attrs=None):
        """New: attrs is an iterable, for each item, the following is checked:
           if the item is a string type: changes are reported
           if the item is another iterable (set,list,tuple), then if any of the subitems is
             different, then all sub items are reported.  This allows grouping of dependant
             items."""
        conflicting = {}
        if attrs is None: attrs = self.copyattrs
        if not attrs: return conflicting

        parentRecords = self.History()
        if parentRecords:
            for attr in attrs:
                if isinstance(attr,basestring):
                    # Single attr
                    conflicting.update([(attr,reduce(getattr, attr.split(u'.'), self)) for parentRecord in parentRecords if reduce(getattr, attr.split(u'.'), self) != reduce(getattr, attr.split(u'.'), parentRecord)])
                elif isinstance(attr,(list,tuple,set)):
                    # Group of attrs that need to stay together
                    for parentRecord in parentRecords:
                        subconflicting = {}
                        conflict = False
                        for subattr in attr:
                            self_value = reduce(getattr, subattr.split(u'.'), self)
                            if not conflict and self_value != reduce(getattr, subattr.split(u'.'), parentRecord):
                                conflict = True
                            subconflicting.update([(subattr,self_value)])
                        if conflict:
                            conflicting.update(subconflicting)
        else: #is the first instance of the record
            for attr in attrs:
                if isinstance(attr, basestring):
                    conflicting.update([(attr,reduce(getattr, attr.split(u'.'), self))])
                elif isinstance(attr,(list,tuple,set)):
                    conflicting.update([(subattr,reduce(getattr, subattr.split(u'.'), self)) for subattr in attr])

        skipped_conflicting = [(attr, value) for attr, value in conflicting.iteritems() if isinstance(value, FormID) and not value.ValidateFormID(self)]
        for attr, value in skipped_conflicting:
            try:
                deprint(_(u'%s attribute of %s record (maybe named: %s) importing from %s referenced an unloaded object (probably %s) - value skipped') % (attr, self.fid, self.full, self.GetParentMod().GName, value))
            except: #a record type that doesn't have a full chunk:
                deprint(_(u'%s attribute of %s record importing from %s referenced an unloaded object (probably %s) - value skipped') % (attr, self.fid, self.GetParentMod().GName, value))
            del conflicting[attr]

        return conflicting

    def mergeFilter(self, target):
        """This method is called by the bashed patch mod merger. The intention is
        to allow a record to be filtered according to the specified modSet. E.g.
        for a list record, items coming from mods not in the modSet could be
        removed from the list."""
        pass

    def CopyAsOverride(self, target, UseWinningParents=False):
        ##Record Creation Flags
        ##SetAsOverride       = 0x00000001
        ##CopyWinningParent   = 0x00000002
        DestParentID, DestModID = (None, target._ModID) if not hasattr(self, u'_ParentID') else (self._ParentID, target._ModID) if isinstance(target, ObModFile) else (target._RecordID, target.GetParentMod()._ModID)
        RecordID = _CCopyRecord(self._RecordID, DestModID, DestParentID, 0, None, c_int(0x00000003 if UseWinningParents else 0x00000001))
        return self.__class__(RecordID) if RecordID else None

    def CopyAsNew(self, target, UseWinningParents=False, RecordFormID=0):
        ##Record Creation Flags
        ##SetAsOverride       = 0x00000001
        ##CopyWinningParent   = 0x00000002
        DestParentID, DestModID = (None, target._ModID) if not hasattr(self, u'_ParentID') else (self._ParentID, target._ModID) if isinstance(target, ObModFile) else (target._RecordID, target.GetParentMod()._ModID)
        RecordID = _CCopyRecord(self._RecordID, DestModID, DestParentID, RecordFormID.GetShortFormID(target) if RecordFormID else 0, 0, c_int(0x00000002 if UseWinningParents else 0))
        return self.__class__(RecordID) if RecordID else None

    @property
    def Parent(self):
        RecordID = getattr(self, u'_ParentID', None)
        if RecordID:
            _CGetFieldAttribute.restype = (c_char * 4)
            retValue = _CGetFieldAttribute(RecordID, 0, 0, 0, 0, 0, 0, 0, 0)
            _CGetFieldAttribute.restype = c_ulong
            return type_record[retValue.value](RecordID)
        return None

    @property
    def recType(self):
        _CGetFieldAttribute.restype = (c_char * 4)
        retValue = _CGetFieldAttribute(self._RecordID, 0, 0, 0, 0, 0, 0, 0, 0).value
        _CGetFieldAttribute.restype = c_ulong
        return retValue

    flags1 = CBashGeneric(1, c_ulong)

    def get_fid(self):
        _CGetField.restype = POINTER(c_ulong)
        retValue = _CGetField(self._RecordID, 2, 0, 0, 0, 0, 0, 0, 0)
        return FormID(self._RecordID, retValue.contents.value) if retValue else FormID(None,None)
    def set_fid(self, nValue):
        _CSetIDFields(self._RecordID, 0 if nValue is None else nValue.GetShortFormID(self), self.eid or 0)
    fid = property(get_fid, set_fid)

    flags2 = CBashGeneric(3, c_ulong)

    def get_eid(self):
        _CGetField.restype = c_char_p
        retValue = _CGetField(self._RecordID, 4, 0, 0, 0, 0, 0, 0, 0)
        return IUNICODE(_unicode(retValue)) if retValue else None
    def set_eid(self, nValue):
        nValue = None if nValue is None or not len(nValue) else _encode(nValue)
        _CGetField.restype = POINTER(c_ulong)
        _CSetIDFields(self._RecordID, _CGetField(self._RecordID, 2, 0, 0, 0, 0, 0, 0, 0).contents.value, nValue)
    eid = property(get_eid, set_eid)

    IsDeleted = CBashBasicFlag(u'flags1', 0x00000020)
    IsBorderRegion = CBashBasicFlag(u'flags1', 0x00000040)
    IsTurnOffFire = CBashBasicFlag(u'flags1', 0x00000080)
    IsCastsShadows = CBashBasicFlag(u'flags1', 0x00000200)
    IsPersistent = CBashBasicFlag(u'flags1', 0x00000400)
    IsQuest = CBashAlias(u'IsPersistent')
    IsQuestOrPersistent = CBashAlias(u'IsPersistent')
    IsInitiallyDisabled = CBashBasicFlag(u'flags1', 0x00000800)
    IsIgnored = CBashBasicFlag(u'flags1', 0x00001000)
    IsVisibleWhenDistant = CBashBasicFlag(u'flags1', 0x00008000)
    IsVWD = CBashAlias(u'IsVisibleWhenDistant')
    IsDangerousOrOffLimits = CBashBasicFlag(u'flags1', 0x00020000)
    IsCompressed = CBashBasicFlag(u'flags1', 0x00040000)
    IsCantWait = CBashBasicFlag(u'flags1', 0x00080000)
    baseattrs = [u'flags1', u'flags2', u'eid']

class ObTES4Record(object):
    __slots__ = [u'_RecordID']
    _Type = b'TES4'
    def __init__(self, RecordID):
        self._RecordID = RecordID

    def GetParentMod(self):
        return ObModFile(_CGetModIDByRecordID(self._RecordID))

    def GetParentCollection(self):
        return ObCollection(_CGetCollectionIDByRecordID(self._RecordID))

    def ResetRecord(self):
        pass

    def UnloadRecord(self):
        pass

    @property
    def recType(self):
        return self._Type

    flags1 = CBashGeneric(1, c_ulong)
    flags2 = CBashGeneric(3, c_ulong)
    version = CBashFLOAT32(5)
    numRecords = CBashGeneric(6, c_ulong)
    nextObject = CBashGeneric(7, c_ulong)
    ofst_p = CBashUINT8ARRAY(8)
    dele_p = CBashUINT8ARRAY(9)
    author = CBashUNICODE(10)
    description = CBashUNICODE(11)
    masters = CBashIUNICODEARRAY(12)
    DATA = CBashJunk(13)
    IsESM = CBashBasicFlag(u'flags1', 0x00000001)
    exportattrs = copyattrs = [u'flags1', u'flags2', u'version', u'numRecords',
                               u'nextObject', u'author', u'description', u'masters']

class ObGMSTRecord(ObBaseRecord):
    __slots__ = []
    _Type = b'GMST'
    def get_value(self):
        fieldtype = _CGetFieldAttribute(self._RecordID, 5, 0, 0, 0, 0, 0, 0, 2)
        if fieldtype == API_FIELDS.UNKNOWN: return None
        _CGetField.restype = POINTER(c_long) if fieldtype == API_FIELDS.SINT32 else POINTER(c_float) if fieldtype == API_FIELDS.FLOAT32 else c_char_p
        retValue = _CGetField(self._RecordID, 5, 0, 0, 0, 0, 0, 0, 0)
        return (_unicode(retValue) if fieldtype == API_FIELDS.STRING else round(retValue.contents.value,6) if fieldtype == API_FIELDS.FLOAT32 else retValue.contents.value) if retValue else None
    def set_value(self, nValue):
        if nValue is None: _CDeleteField(self._RecordID, 5, 0, 0, 0, 0, 0, 0)
        else:
            fieldtype = _CGetFieldAttribute(self._RecordID, 5, 0, 0, 0, 0, 0, 0, 2)
            try: _CSetField(self._RecordID, 5, 0, 0, 0, 0, 0, 0, byref(c_long(int(nValue))) if fieldtype == API_FIELDS.SINT32 else byref(c_float(round(nValue,6))) if fieldtype == API_FIELDS.FLOAT32 else _encode(nValue), 0)
            except TypeError: return
            except ValueError: return
    value = property(get_value, set_value)
    exportattrs = copyattrs = ObBaseRecord.baseattrs + [u'value']

class ObACHRRecord(ObBaseRecord):
    __slots__ = []
    @property
    def _ParentID(self):
        _CGetField.restype = c_record_p
        return _CGetField(self._RecordID, 24, 0, 0, 0, 0, 0, 0, 0)

    _Type = b'ACHR'
    base = CBashFORMID(5)
    unknownXPCIFormID = CBashFORMID(6)
    unknownXPCIString = CBashISTRING(7)
    lod1 = CBashFLOAT32(8)
    lod2 = CBashFLOAT32(9)
    lod3 = CBashFLOAT32(10)
    parent = CBashFORMID(11)
    parentFlags = CBashGeneric(12, c_ubyte)
    unused1 = CBashUINT8ARRAY(13, 3)
    merchantContainer = CBashFORMID(14)
    horse = CBashFORMID(15)
    xrgd_p = CBashUINT8ARRAY(16)
    scale = CBashFLOAT32(17)
    posX = CBashFLOAT32(18)
    posY = CBashFLOAT32(19)
    posZ = CBashFLOAT32(20)
    rotX = CBashFLOAT32(21)
    rotX_degrees = CBashDEGREES(21)
    rotY = CBashFLOAT32(22)
    rotY_degrees = CBashDEGREES(22)
    rotZ = CBashFLOAT32(23)
    rotZ_degrees = CBashDEGREES(23)
    IsOppositeParent = CBashBasicFlag(u'parentFlags', 0x00000001)
    copyattrs = ObBaseRecord.baseattrs + [u'base', u'unknownXPCIFormID', u'unknownXPCIString',
                                          u'lod1', u'lod2', u'lod3', u'parent', u'parentFlags',
                                          u'merchantContainer', u'horse', u'xrgd_p', u'scale',
                                          u'posX', u'posY', u'posZ', u'rotX', u'rotY', u'rotZ']
    exportattrs = copyattrs[:]
    exportattrs.remove(u'xrgd_p')
    exportattrs.remove(u'unknownXPCIFormID')
    exportattrs.remove(u'unknownXPCIString')

class ObACRERecord(ObBaseRecord):
    __slots__ = []
    @property
    def _ParentID(self):
        _CGetField.restype = c_record_p
        return _CGetField(self._RecordID, 23, 0, 0, 0, 0, 0, 0, 0)

    _Type = b'ACRE'
    base = CBashFORMID(5)
    owner = CBashFORMID(6)
    rank = CBashGeneric(7, c_long)
    globalVariable = CBashFORMID(8)
    lod1 = CBashFLOAT32(9)
    lod2 = CBashFLOAT32(10)
    lod3 = CBashFLOAT32(11)
    parent = CBashFORMID(12)
    parentFlags = CBashGeneric(13, c_ubyte)
    unused1 = CBashUINT8ARRAY(14, 3)
    xrgd_p = CBashUINT8ARRAY(15)
    scale = CBashFLOAT32(16)
    posX = CBashFLOAT32(17)
    posY = CBashFLOAT32(18)
    posZ = CBashFLOAT32(19)
    rotX = CBashFLOAT32(20)
    rotX_degrees = CBashDEGREES(20)
    rotY = CBashFLOAT32(21)
    rotY_degrees = CBashDEGREES(21)
    rotZ = CBashFLOAT32(22)
    rotZ_degrees = CBashDEGREES(22)
    IsOppositeParent = CBashBasicFlag(u'parentFlags', 0x00000001)
    copyattrs = ObBaseRecord.baseattrs + [u'base', u'owner', u'rank', u'globalVariable',
                                          u'lod1', u'lod2', u'lod3', u'parent', u'parentFlags',
                                          u'xrgd_p', u'scale', u'posX', u'posY', u'posZ', u'rotX',
                                          u'rotY', u'rotZ']
    exportattrs = copyattrs[:]
    exportattrs.remove(u'xrgd_p')

class ObREFRRecord(ObBaseRecord):
    __slots__ = []
    @property
    def _ParentID(self):
        _CGetField.restype = c_record_p
        return _CGetField(self._RecordID, 50, 0, 0, 0, 0, 0, 0, 0)

    _Type = b'REFR'
    base = CBashFORMID(5)
    destination = CBashFORMID(6)
    destinationPosX = CBashFLOAT32(7)
    destinationPosY = CBashFLOAT32(8)
    destinationPosZ = CBashFLOAT32(9)
    destinationRotX = CBashFLOAT32(10)
    destinationRotX_degrees = CBashDEGREES(10)
    destinationRotY = CBashFLOAT32(11)
    destinationRotY_degrees = CBashDEGREES(11)
    destinationRotZ = CBashFLOAT32(12)
    destinationRotZ_degrees = CBashDEGREES(12)
    lockLevel = CBashGeneric(13, c_ubyte)
    unused1 = CBashUINT8ARRAY(14, 3)
    lockKey = CBashFORMID(15)
    unused2 = CBashUINT8ARRAY(16, 4)
    lockFlags = CBashGeneric(17, c_ubyte)
    unused3 = CBashUINT8ARRAY(18, 3)
    owner = CBashFORMID(19)
    rank = CBashGeneric(20, c_long)
    globalVariable = CBashFORMID(21)
    parent = CBashFORMID(22)
    parentFlags = CBashGeneric(23, c_ubyte)
    unused4 = CBashUINT8ARRAY(24, 3)
    target = CBashFORMID(25)
    seed = CBashXSED(26)
    seed_as_offset = CBashXSED(26, True)
    lod1 = CBashFLOAT32(27)
    lod2 = CBashFLOAT32(28)
    lod3 = CBashFLOAT32(29)
    charge = CBashFLOAT32(30)
    health = CBashGeneric(31, c_long)
    unknownXPCIFormID = CBashFORMID(32)
    unknownXPCIString = CBashISTRING(33)
    levelMod = CBashGeneric(34, c_long)
    unknownXRTMFormID = CBashFORMID(35)
    actionFlags = CBashGeneric(36, c_ulong)
    count = CBashGeneric(37, c_long)
    markerFlags = CBashGeneric(38, c_ubyte)
    markerName = CBashSTRING(39)
    markerType = CBashGeneric(40, c_ubyte)
    markerUnused = CBashUINT8ARRAY(41, 1)
    scale = CBashFLOAT32(42)
    soulType = CBashGeneric(43, c_ubyte)
    posX = CBashFLOAT32(44)
    posY = CBashFLOAT32(45)
    posZ = CBashFLOAT32(46)
    rotX = CBashFLOAT32(47)
    rotX_degrees = CBashDEGREES(47)
    rotY = CBashFLOAT32(48)
    rotY_degrees = CBashDEGREES(48)
    rotZ = CBashFLOAT32(49)
    rotZ_degrees = CBashDEGREES(49)
    IsLeveledLock = CBashBasicFlag(u'lockFlags', 0x00000004)
    IsOppositeParent = CBashBasicFlag(u'parentFlags', 0x00000001)
    IsUseDefault = CBashBasicFlag(u'actionFlags', 0x00000001)
    IsActivate = CBashBasicFlag(u'actionFlags', 0x00000002)
    IsOpen = CBashBasicFlag(u'actionFlags', 0x00000004)
    IsOpenByDefault = CBashBasicFlag(u'actionFlags', 0x00000008)
    IsVisible = CBashBasicFlag(u'markerFlags', 0x00000001)
    IsCanTravelTo = CBashBasicFlag(u'markerFlags', 0x00000002)
    IsMarkerNone = CBashBasicType(u'markerType', 0, u'IsCamp')
    IsCamp = CBashBasicType(u'markerType', 1, u'IsMarkerNone')
    IsCave = CBashBasicType(u'markerType', 2, u'IsMarkerNone')
    IsCity = CBashBasicType(u'markerType', 3, u'IsMarkerNone')
    IsElvenRuin = CBashBasicType(u'markerType', 4, u'IsMarkerNone')
    IsFortRuin = CBashBasicType(u'markerType', 5, u'IsMarkerNone')
    IsMine = CBashBasicType(u'markerType', 6, u'IsMarkerNone')
    IsLandmark = CBashBasicType(u'markerType', 7, u'IsMarkerNone')
    IsTavern = CBashBasicType(u'markerType', 8, u'IsMarkerNone')
    IsSettlement = CBashBasicType(u'markerType', 9, u'IsMarkerNone')
    IsDaedricShrine = CBashBasicType(u'markerType', 10, u'IsMarkerNone')
    IsOblivionGate = CBashBasicType(u'markerType', 11, u'IsMarkerNone')
    IsUnknownDoorIcon = CBashBasicType(u'markerType', 12, u'IsMarkerNone')
    IsNoSoul = CBashBasicType(u'soulType', 0, u'IsPettySoul')
    IsPettySoul = CBashBasicType(u'soulType', 1, u'IsNoSoul')
    IsLesserSoul = CBashBasicType(u'soulType', 2, u'IsNoSoul')
    IsCommonSoul = CBashBasicType(u'soulType', 3, u'IsNoSoul')
    IsGreaterSoul = CBashBasicType(u'soulType', 4, u'IsNoSoul')
    IsGrandSoul = CBashBasicType(u'soulType', 5, u'IsNoSoul')
    exportattrs = copyattrs = ObBaseRecord.baseattrs + [
        u'base', u'destination', u'destinationPosX', u'destinationPosY',
        u'destinationPosZ', u'destinationRotX', u'destinationRotY',
        u'destinationRotZ', u'lockLevel', u'lockKey', u'lockFlags', u'owner',
        u'rank', u'globalVariable', u'parent', u'parentFlags', u'target',
        u'seed', u'seed_as_offset', u'lod1', u'lod2', u'lod3', u'charge',
        u'health', u'levelMod', u'actionFlags', u'count', u'markerFlags',
        u'markerName', u'markerType', u'scale', u'soulType', u'posX', u'posY',
        u'posZ', u'rotX', u'rotY', u'rotZ']

class ObINFORecord(ObBaseRecord):
    __slots__ = []
    @property
    def _ParentID(self):
        _CGetField.restype = c_record_p
        return _CGetField(self._RecordID, 23, 0, 0, 0, 0, 0, 0, 0)

    _Type = b'INFO'
    class Response(ListComponent):
        __slots__ = []
        emotionType = CBashGeneric_LIST(1, c_ulong)
        emotionValue = CBashGeneric_LIST(2, c_long)
        unused1 = CBashUINT8ARRAY_LIST(3, 4)
        responseNum = CBashGeneric_LIST(4, c_ubyte)
        unused2 = CBashUINT8ARRAY_LIST(5, 3)
        responseText = CBashSTRING_LIST(6)
        actorNotes = CBashISTRING_LIST(7)
        IsNeutral = CBashBasicType(u'emotionType', 0, u'IsAnger')
        IsAnger = CBashBasicType(u'emotionType', 1, u'IsNeutral')
        IsDisgust = CBashBasicType(u'emotionType', 2, u'IsNeutral')
        IsFear = CBashBasicType(u'emotionType', 3, u'IsNeutral')
        IsSad = CBashBasicType(u'emotionType', 4, u'IsNeutral')
        IsHappy = CBashBasicType(u'emotionType', 5, u'IsNeutral')
        IsSurprise = CBashBasicType(u'emotionType', 6, u'IsNeutral')
        exportattrs = copyattrs = [u'emotionType', u'emotionValue', u'responseNum',
                                   u'responseText', u'actorNotes']

    dialType = CBashGeneric(5, c_ushort)
    flags = CBashGeneric(6, c_ubyte)
    quest = CBashFORMID(7)
    topic = CBashFORMID(8)
    prevInfo = CBashFORMID(9)
    addTopics = CBashFORMIDARRAY(10)

    def create_response(self):
        length = _CGetFieldAttribute(self._RecordID, 11, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 11, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return self.Response(self._RecordID, 11, length)
    responses = CBashLIST(11, Response)
    responses_list = CBashLIST(11, Response, True)

    def create_condition(self):
        length = _CGetFieldAttribute(self._RecordID, 12, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 12, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return Condition(self._RecordID, 12, length)
    conditions = CBashLIST(12, Condition)
    conditions_list = CBashLIST(12, Condition, True)

    choices = CBashFORMIDARRAY(13)
    linksFrom = CBashFORMIDARRAY(14)
    unused1 = CBashUINT8ARRAY(15, 4)
    numRefs = CBashGeneric(16, c_ulong)
    compiledSize = CBashGeneric(17, c_ulong)
    lastIndex = CBashGeneric(18, c_ulong)
    scriptType = CBashGeneric(19, c_ulong)
    compiled_p = CBashUINT8ARRAY(20)
    scriptText = CBashISTRING(21)
    references = CBashFORMID_OR_UINT32_ARRAY(22)
    IsTopic = CBashBasicType(u'dialType', 0, u'IsConversation')
    IsConversation = CBashBasicType(u'dialType', 1, u'IsTopic')
    IsCombat = CBashBasicType(u'dialType', 2, u'IsTopic')
    IsPersuasion = CBashBasicType(u'dialType', 3, u'IsTopic')
    IsDetection = CBashBasicType(u'dialType', 4, u'IsTopic')
    IsService = CBashBasicType(u'dialType', 5, u'IsTopic')
    IsMisc = CBashBasicType(u'dialType', 6, u'IsTopic')
    IsObject = CBashBasicType(u'scriptType', 0x00000000, u'IsQuest')
    IsQuest = CBashBasicType(u'scriptType', 0x00000001, u'IsObject')
    IsMagicEffect = CBashBasicType(u'scriptType', 0x00000100, u'IsObject')
    IsGoodbye = CBashBasicFlag(u'flags', 0x00000001)
    IsRandom = CBashBasicFlag(u'flags', 0x00000002)
    IsSayOnce = CBashBasicFlag(u'flags', 0x00000004)
    IsRunImmediately = CBashBasicFlag(u'flags', 0x00000008)
    IsInfoRefusal = CBashBasicFlag(u'flags', 0x00000010)
    IsRandomEnd = CBashBasicFlag(u'flags', 0x00000020)
    IsRunForRumors = CBashBasicFlag(u'flags', 0x00000040)
    copyattrs = ObBaseRecord.baseattrs + [u'dialType', u'flags', u'quest', u'topic',
                                          u'prevInfo', u'addTopics', u'responses_list',
                                          u'conditions_list', u'choices', u'linksFrom',
                                          u'numRefs', u'compiledSize', u'lastIndex',
                                          u'scriptType', u'compiled_p', u'scriptText',
                                          u'references']
    exportattrs = copyattrs[:]
    exportattrs.remove(u'compiled_p')

class ObLANDRecord(ObBaseRecord):
    __slots__ = []
    @property
    def _ParentID(self):
        _CGetField.restype = c_record_p
        return _CGetField(self._RecordID, 15, 0, 0, 0, 0, 0, 0, 0)

    _Type = b'LAND'
    class Normal(ListX2Component):
        __slots__ = []
        x = CBashGeneric_LISTX2(1, c_ubyte)
        y = CBashGeneric_LISTX2(2, c_ubyte)
        z = CBashGeneric_LISTX2(3, c_ubyte)
        exportattrs = copyattrs = [u'x', u'y', u'z']

    class Height(ListX2Component):
        __slots__ = []
        height = CBashGeneric_LISTX2(1, c_byte)
        exportattrs = copyattrs = [u'height']

    class Color(ListX2Component):
        __slots__ = []
        red = CBashGeneric_LISTX2(1, c_ubyte)
        green = CBashGeneric_LISTX2(2, c_ubyte)
        blue = CBashGeneric_LISTX2(3, c_ubyte)
        exportattrs = copyattrs = [u'red', u'green', u'blue']

    class BaseTexture(ListComponent):
        __slots__ = []
        texture = CBashFORMID_LIST(1)
        quadrant = CBashGeneric_LIST(2, c_byte)
        unused1 = CBashUINT8ARRAY_LIST(3, 1)
        layer = CBashGeneric_LIST(4, c_short)
        exportattrs = copyattrs = [u'texture', u'quadrant', u'layer']

    class AlphaLayer(ListComponent):
        __slots__ = []
        class Opacity(ListX2Component):
            __slots__ = []
            position = CBashGeneric_LISTX2(1, c_ushort)
            unused1 = CBashUINT8ARRAY_LISTX2(2, 2)
            opacity = CBashFLOAT32_LISTX2(3)
            exportattrs = copyattrs = [u'position', u'opacity']
        texture = CBashFORMID_LIST(1)
        quadrant = CBashGeneric_LIST(2, c_byte)
        unused1 = CBashUINT8ARRAY_LIST(3, 1)
        layer = CBashGeneric_LIST(4, c_short)

        def create_opacity(self):
            length = _CGetFieldAttribute(self._RecordID, self._FieldID, self._ListIndex, 5, 0, 0, 0, 0, 1)
            _CSetField(self._RecordID, self._FieldID, self._ListIndex, 5, 0, 0, 0, 0, 0, c_ulong(length + 1))
            return self.Opacity(self._RecordID, self._FieldID, self._ListIndex, 5, length)
        opacities = CBashLIST_LIST(5, Opacity)
        opacities_list = CBashLIST_LIST(5, Opacity, True)

        exportattrs = copyattrs = [u'texture', u'quadrant', u'layer', u'opacities_list']

    class VertexTexture(ListComponent):
        __slots__ = []
        texture = CBashFORMID_LIST(1)
        exportattrs = copyattrs = [u'texture']

    class Position(ListX2Component):
        __slots__ = []
        height = CBashFLOAT32_LISTX2(1)
        normalX = CBashGeneric_LISTX2(2, c_ubyte)
        normalY = CBashGeneric_LISTX2(3, c_ubyte)
        normalZ = CBashGeneric_LISTX2(4, c_ubyte)
        red = CBashGeneric_LISTX2(5, c_ubyte)
        green = CBashGeneric_LISTX2(6, c_ubyte)
        blue = CBashGeneric_LISTX2(7, c_ubyte)
        baseTexture = CBashFORMID_LISTX2(8)
        alphaLayer1Texture = CBashFORMID_LISTX2(9)
        alphaLayer1Opacity = CBashFLOAT32_LISTX2(10)
        alphaLayer2Texture = CBashFORMID_LISTX2(11)
        alphaLayer2Opacity = CBashFLOAT32_LISTX2(12)
        alphaLayer3Texture = CBashFORMID_LISTX2(13)
        alphaLayer3Opacity = CBashFLOAT32_LISTX2(14)
        alphaLayer4Texture = CBashFORMID_LISTX2(15)
        alphaLayer4Opacity = CBashFLOAT32_LISTX2(16)
        alphaLayer5Texture = CBashFORMID_LISTX2(17)
        alphaLayer5Opacity = CBashFLOAT32_LISTX2(18)
        alphaLayer6Texture = CBashFORMID_LISTX2(19)
        alphaLayer6Opacity = CBashFLOAT32_LISTX2(20)
        alphaLayer7Texture = CBashFORMID_LISTX2(21)
        alphaLayer7Opacity = CBashFLOAT32_LISTX2(22)
        alphaLayer8Texture = CBashFORMID_LISTX2(23)
        alphaLayer8Opacity = CBashFLOAT32_LISTX2(24)
        exportattrs = copyattrs = [u'height', u'normalX', u'normalY', u'normalZ',
                                   u'red', u'green', u'blue', u'baseTexture',
                                   u'alphaLayer1Texture', u'alphaLayer1Opacity',
                                   u'alphaLayer2Texture', u'alphaLayer2Opacity',
                                   u'alphaLayer3Texture', u'alphaLayer3Opacity',
                                   u'alphaLayer4Texture', u'alphaLayer4Opacity',
                                   u'alphaLayer5Texture', u'alphaLayer5Opacity',
                                   u'alphaLayer6Texture', u'alphaLayer6Opacity',
                                   u'alphaLayer7Texture', u'alphaLayer7Opacity',
                                   u'alphaLayer8Texture', u'alphaLayer8Opacity']

    data_p = CBashUINT8ARRAY(5)

    def get_normals(self):
        return [[self.Normal(self._RecordID, 6, x, 0, y) for y in xrange(0,33)] for x in xrange(0,33)]
    def set_normals(self, nElements):
        if nElements is None or len(nElements) != 33: return
        for oElement, nElement in zip(self.normals, nElements if isinstance(nElements[0], tuple) else [ExtractCopyList(nElements[x]) for x in xrange(0,33)]):
            SetCopyList(oElement, nElement)
    normals = property(get_normals, set_normals)
    def get_normals_list(self):
        return [ExtractCopyList([self.Normal(self._RecordID, 6, x, 0, y) for y in xrange(0,33)]) for x in xrange(0,33)]

    normals_list = property(get_normals_list, set_normals)

    heightOffset = CBashFLOAT32(7)

    def get_heights(self):
        return [[self.Height(self._RecordID, 8, x, 0, y) for y in xrange(0,33)] for x in xrange(0,33)]
    def set_heights(self, nElements):
        if nElements is None or len(nElements) != 33: return
        for oElement, nElement in zip(self.heights, nElements if isinstance(nElements[0], tuple) else [ExtractCopyList(nElements[x]) for x in xrange(0,33)]):
            SetCopyList(oElement, nElement)

    heights = property(get_heights, set_heights)
    def get_heights_list(self):
        return [ExtractCopyList([self.Height(self._RecordID, 8, x, 0, y) for y in xrange(0,33)]) for x in xrange(0,33)]
    heights_list = property(get_heights_list, set_heights)

    unused1 = CBashUINT8ARRAY(9, 3)

    def get_colors(self):
        return [[self.Color(self._RecordID, 10, x, 0, y) for y in xrange(0,33)] for x in xrange(0,33)]
    def set_colors(self, nElements):
        if nElements is None or len(nElements) != 33: return
        for oElement, nElement in zip(self.colors, nElements if isinstance(nElements[0], tuple) else [ExtractCopyList(nElements[x]) for x in xrange(0,33)]):
            SetCopyList(oElement, nElement)

    colors = property(get_colors, set_colors)
    def get_colors_list(self):
        return [ExtractCopyList([self.Color(self._RecordID, 10, x, 0, y) for y in xrange(0,33)]) for x in xrange(0,33)]
    colors_list = property(get_colors_list, set_colors)

    def create_baseTexture(self):
        length = _CGetFieldAttribute(self._RecordID, 11, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 11, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return self.BaseTexture(self._RecordID, 11, length)
    baseTextures = CBashLIST(11, BaseTexture)
    baseTextures_list = CBashLIST(11, BaseTexture, True)

    def create_alphaLayer(self):
        length = _CGetFieldAttribute(self._RecordID, 12, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 12, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return self.AlphaLayer(self._RecordID, 12, length)
    alphaLayers = CBashLIST(12, AlphaLayer)
    alphaLayers_list = CBashLIST(12, AlphaLayer, True)

    def create_vertexTexture(self):
        length = _CGetFieldAttribute(self._RecordID, 13, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 13, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return self.VertexTexture(self._RecordID, 13, length)
    vertexTextures = CBashLIST(13, VertexTexture)
    vertexTextures_list = CBashLIST(13, VertexTexture, True)

    ##The Positions accessor is unique in that it duplicates the above accessors. It just presents the data in a more friendly format.
    def get_Positions(self):
        return [[self.Position(self._RecordID, 14, row, 0, column) for column in xrange(0,33)] for row in xrange(0,33)]
    def set_Positions(self, nElements):
        if nElements is None or len(nElements) != 33: return
        for oElement, nElement in zip(self.Positions, nElements if isinstance(nElements[0], tuple) else [ExtractCopyList(nElements[x]) for x in xrange(0,33)]):
            SetCopyList(oElement, nElement)
    Positions = property(get_Positions, set_Positions)
    def get_Positions_list(self):
        return [ExtractCopyList([self.Position(self._RecordID, 14, x, 0, y) for y in xrange(0,33)]) for x in xrange(0,33)]
    Positions_list = property(get_Positions_list, set_Positions)
    copyattrs = ObBaseRecord.baseattrs + [u'data_p', u'normals_list', u'heights_list', u'heightOffset',
                                          u'colors_list', u'baseTextures_list', u'alphaLayers_list',
                                          u'vertexTextures_list']
    exportattrs = copyattrs[:]
    exportattrs.remove(u'data_p')

class ObPGRDRecord(ObBaseRecord):
    __slots__ = []
    @property
    def _ParentID(self):
        _CGetField.restype = c_record_p
        return _CGetField(self._RecordID, 11, 0, 0, 0, 0, 0, 0, 0)

    _Type = b'PGRD'
    class PGRI(ListComponent):
        __slots__ = []
        point = CBashGeneric_LIST(1, c_ushort)
        unused1 = CBashUINT8ARRAY_LIST(2, 2)
        x = CBashFLOAT32_LIST(3)
        y = CBashFLOAT32_LIST(4)
        z = CBashFLOAT32_LIST(5)
        exportattrs = copyattrs = [u'point', u'x', u'y', u'z']

    class PGRL(ListComponent):
        __slots__ = []
        reference = CBashFORMID_LIST(1)
        points = CBashUINT32ARRAY_LIST(2)
        exportattrs = copyattrs = [u'reference', u'points']

    count = CBashGeneric(5, c_ushort)

    def create_pgrp(self):
        length = _CGetFieldAttribute(self._RecordID, 6, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 6, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return PGRP(self._RecordID, 6, length)
    pgrp = CBashLIST(6, PGRP)
    pgrp_list = CBashLIST(6, PGRP, True)

    pgag_p = CBashUINT8ARRAY(7)
    pgrr_p = CBashUINT8ARRAY(8)

    def create_pgri(self):
        length = _CGetFieldAttribute(self._RecordID, 9, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 9, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return self.PGRI(self._RecordID, 9, length)
    pgri = CBashLIST(9, PGRI)
    pgri_list = CBashLIST(9, PGRI, True)

    def create_pgrl(self):
        length = _CGetFieldAttribute(self._RecordID, 10, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 10, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return self.PGRL(self._RecordID, 10, length)
    pgrl = CBashLIST(10, PGRL)
    pgrl_list = CBashLIST(10, PGRL, True)

    copyattrs = ObBaseRecord.baseattrs + [u'count', u'pgrp_list', u'pgag_p',
                                          u'pgrr_p', u'pgri_list', u'pgrl_list']
    exportattrs = copyattrs[:]
    exportattrs.remove(u'pgag_p')
    exportattrs.remove(u'pgrr_p')

class ObROADRecord(ObBaseRecord):
    __slots__ = []
    @property
    def _ParentID(self):
        _CGetField.restype = c_record_p
        return _CGetField(self._RecordID, 7, 0, 0, 0, 0, 0, 0, 0)

    _Type = b'ROAD'
    class PGRR(ListComponent):
        __slots__ = []
        x = CBashFLOAT32_LIST(1)
        y = CBashFLOAT32_LIST(2)
        z = CBashFLOAT32_LIST(3)
        exportattrs = copyattrs = [u'x', u'y', u'z']

    def create_pgrp(self):
        length = _CGetFieldAttribute(self._RecordID, 5, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 5, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return PGRP(self._RecordID, 5, length)
    pgrp = CBashLIST(5, PGRP)
    pgrp_list = CBashLIST(5, PGRP, True)

    def create_pgrr(self):
        length = _CGetFieldAttribute(self._RecordID, 6, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 6, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return self.PGRR(self._RecordID, 6, length)
    pgrr = CBashLIST(6, PGRR)
    pgrr_list = CBashLIST(6, PGRR, True)

    exportattrs = copyattrs = ObBaseRecord.baseattrs + [u'pgrp_list', u'pgrr_list']

class ObACTIRecord(ObBaseRecord):
    __slots__ = []
    _Type = b'ACTI'
    full = CBashSTRING(5)
    modPath = CBashISTRING(6)
    modb = CBashFLOAT32(7)
    modt_p = CBashUINT8ARRAY(8)
    script = CBashFORMID(9)
    sound = CBashFORMID(10)
    copyattrs = ObBaseRecord.baseattrs + [u'full', u'modPath', u'modb',
                                          u'modt_p', u'script', u'sound']
    exportattrs = copyattrs[:]
    exportattrs.remove(u'modt_p')

class ObALCHRecord(ObBaseRecord):
    __slots__ = []
    _Type = b'ALCH'
    full = CBashSTRING(5)
    modPath = CBashISTRING(6)
    modb = CBashFLOAT32(7)
    modt_p = CBashUINT8ARRAY(8)
    iconPath = CBashISTRING(9)
    script = CBashFORMID(10)
    weight = CBashFLOAT32(11)
    value = CBashGeneric(12, c_long)
    flags = CBashGeneric(13, c_ubyte)
    unused1 = CBashUINT8ARRAY(14, 3)

    def create_effect(self):
        length = _CGetFieldAttribute(self._RecordID, 15, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 15, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return Effect(self._RecordID, 15, length)
    effects = CBashLIST(15, Effect)
    effects_list = CBashLIST(15, Effect, True)

    IsNoAutoCalc = CBashBasicFlag(u'flags', 0x00000001)
    IsAutoCalc = CBashInvertedFlag(u'IsNoAutoCalc')
    IsFood = CBashBasicFlag(u'flags', 0x00000002)
    ##OBME Fields. Setting any of the below fields will make the mod require JRoush's OBME plugin for OBSE
    ##To see if OBME is in use, check the recordVersion field for a non-None value
    recordVersion = CBashGeneric(16, c_ubyte) #OBME
    betaVersion = CBashGeneric(17, c_ubyte) #OBME
    minorVersion = CBashGeneric(18, c_ubyte) #OBME
    majorVersion = CBashGeneric(19, c_ubyte) #OBME
    reserved = CBashUINT8ARRAY(20, 0x1C) #OBME
    datx_p = CBashUINT8ARRAY(21, 0x20) #OBME
    copyattrs = ObBaseRecord.baseattrs + [u'full', u'modPath', u'modb', u'modt_p',
                                          u'iconPath', u'script', u'weight',
                                          u'value', u'flags', u'effects_list']
    exportattrs = copyattrs[:]
    exportattrs.remove(u'modt_p')
    copyattrsOBME = copyattrs + [u'recordVersion', u'betaVersion',
                                 u'minorVersion', u'majorVersion',
                                 u'reserved',u'datx_p']
    exportattrsOBME = copyattrsOBME[:]
    exportattrsOBME.remove(u'modt_p')
    exportattrsOBME.remove(u'reserved')
    exportattrsOBME.remove(u'datx_p')

class ObAMMORecord(ObBaseRecord):
    __slots__ = []
    _Type = b'AMMO'
    full = CBashSTRING(5)
    modPath = CBashISTRING(6)
    modb = CBashFLOAT32(7)
    modt_p = CBashUINT8ARRAY(8)
    iconPath = CBashISTRING(9)
    enchantment = CBashFORMID(10)
    enchantPoints = CBashGeneric(11, c_ushort)
    speed = CBashFLOAT32(12)
    flags = CBashGeneric(13, c_ubyte)
    unused1 = CBashUINT8ARRAY(14, 3)
    value = CBashGeneric(15, c_ulong)
    weight = CBashFLOAT32(16)
    damage = CBashGeneric(17, c_ushort)
    IsNotNormal = CBashBasicFlag(u'flags', 0x00000001)
    IsNotNormalWeapon = CBashAlias(u'IsNotNormal')
    IsNormal = CBashInvertedFlag(u'IsNotNormal')
    IsNormalWeapon = CBashAlias(u'IsNormal')
    copyattrs = ObBaseRecord.baseattrs + [u'full', u'modPath', u'modb', u'modt_p',
                                          u'iconPath', u'enchantment',
                                          u'enchantPoints', u'speed', u'flags',
                                          u'value', u'weight', u'damage']
    exportattrs = copyattrs[:]
    exportattrs.remove(u'modt_p')

class ObANIORecord(ObBaseRecord):
    __slots__ = []
    _Type = b'ANIO'
    modPath = CBashISTRING(5)
    modb = CBashFLOAT32(6)
    modt_p = CBashUINT8ARRAY(7)
    animationId = CBashFORMID(8)
    copyattrs = ObBaseRecord.baseattrs + [u'modPath', u'modb', u'modt_p', u'animationId']
    exportattrs = copyattrs[:]
    exportattrs.remove(u'modt_p')

class ObAPPARecord(ObBaseRecord):
    __slots__ = []
    _Type = b'APPA'
    full = CBashSTRING(5)
    modPath = CBashISTRING(6)
    modb = CBashFLOAT32(7)
    modt_p = CBashUINT8ARRAY(8)
    iconPath = CBashISTRING(9)
    script = CBashFORMID(10)
    apparatusType = CBashGeneric(11, c_ubyte)
    value = CBashGeneric(12, c_ulong)
    weight = CBashFLOAT32(13)
    quality = CBashFLOAT32(14)
    IsMortarPestle = CBashBasicType(u'apparatus', 0, u'IsAlembic')
    IsAlembic = CBashBasicType(u'apparatus', 1, u'IsMortarPestle')
    IsCalcinator = CBashBasicType(u'apparatus', 2, u'IsMortarPestle')
    IsRetort = CBashBasicType(u'apparatus', 3, u'IsMortarPestle')
    copyattrs = ObBaseRecord.baseattrs + [u'full', u'modPath', u'modb', u'modt_p',
                                          u'iconPath', u'script', u'apparatusType',
                                          u'value', u'weight', u'quality']
    exportattrs = copyattrs[:]
    exportattrs.remove(u'modt_p')

class ObARMORecord(ObBaseRecord):
    __slots__ = []
    _Type = b'ARMO'
    full = CBashSTRING(5)
    script = CBashFORMID(6)
    enchantment = CBashFORMID(7)
    enchantPoints = CBashGeneric(8, c_ushort)
    flags = CBashGeneric(9, c_ulong)
    maleBody = CBashGrouped(10, Model)
    maleBody_list = CBashGrouped(10, Model, True)

    maleWorld = CBashGrouped(13, Model)
    maleWorld_list = CBashGrouped(13, Model, True)

    maleIconPath = CBashISTRING(16)
    femaleBody = CBashGrouped(17, Model)
    femaleBody_list = CBashGrouped(17, Model, True)

    femaleWorld = CBashGrouped(20, Model)
    femaleWorld_list = CBashGrouped(20, Model, True)

    femaleIconPath = CBashISTRING(23)
    strength = CBashGeneric(24, c_ushort)
    value = CBashGeneric(25, c_ulong)
    health = CBashGeneric(26, c_ulong)
    weight = CBashFLOAT32(27)
    IsHead = CBashBasicFlag(u'flags', 0x00000001)
    IsHair = CBashBasicFlag(u'flags', 0x00000002)
    IsUpperBody = CBashBasicFlag(u'flags', 0x00000004)
    IsLowerBody = CBashBasicFlag(u'flags', 0x00000008)
    IsHand = CBashBasicFlag(u'flags', 0x00000010)
    IsFoot = CBashBasicFlag(u'flags', 0x00000020)
    IsRightRing = CBashBasicFlag(u'flags', 0x00000040)
    IsLeftRing = CBashBasicFlag(u'flags', 0x00000080)
    IsAmulet = CBashBasicFlag(u'flags', 0x00000100)
    IsWeapon = CBashBasicFlag(u'flags', 0x00000200)
    IsBackWeapon = CBashBasicFlag(u'flags', 0x00000400)
    IsSideWeapon = CBashBasicFlag(u'flags', 0x00000800)
    IsQuiver = CBashBasicFlag(u'flags', 0x00001000)
    IsShield = CBashBasicFlag(u'flags', 0x00002000)
    IsTorch = CBashBasicFlag(u'flags', 0x00004000)
    IsTail = CBashBasicFlag(u'flags', 0x00008000)
    IsHideRings = CBashBasicFlag(u'flags', 0x00010000)
    IsHideAmulets = CBashBasicFlag(u'flags', 0x00020000)
    IsNonPlayable = CBashBasicFlag(u'flags', 0x00400000)
    IsPlayable = CBashInvertedFlag(u'IsNonPlayable')
    IsHeavyArmor = CBashBasicFlag(u'flags', 0x00800000)
    exportattrs = copyattrs = ObBaseRecord.baseattrs + [
        u'full', u'script', u'enchantment', u'enchantPoints', u'flags',
        u'maleBody_list', u'maleWorld_list', u'maleIconPath',
        u'femaleBody_list', u'femaleWorld_list', u'femaleIconPath',
        u'strength', u'value', u'health', u'weight']

class ObBOOKRecord(ObBaseRecord):
    __slots__ = []
    _Type = b'BOOK'
    full = CBashSTRING(5)
    modPath = CBashISTRING(6)
    modb = CBashFLOAT32(7)
    modt_p = CBashUINT8ARRAY(8)
    iconPath = CBashISTRING(9)
    text = CBashSTRING(10)
    script = CBashFORMID(11)
    enchantment = CBashFORMID(12)
    enchantPoints = CBashGeneric(13, c_ushort)
    flags = CBashGeneric(14, c_ubyte)
    teaches = CBashGeneric(15, c_byte)
    value = CBashGeneric(16, c_ulong)
    weight = CBashFLOAT32(17)
    IsScroll = CBashBasicFlag(u'flags', 0x00000001)
    IsFixed = CBashBasicFlag(u'flags', 0x00000002)
    IsCantBeTaken = CBashAlias(u'IsFixed')
    copyattrs = ObBaseRecord.baseattrs + [
        u'full', u'modPath', u'modb', u'modt_p', u'iconPath', u'text',
        u'script', u'enchantment', u'enchantPoints', u'flags', u'teaches',
        u'value', u'weight']
    exportattrs = copyattrs[:]
    exportattrs.remove(u'modt_p')

class ObBSGNRecord(ObBaseRecord):
    __slots__ = []
    _Type = b'BSGN'
    full = CBashSTRING(5)
    iconPath = CBashISTRING(6)
    text = CBashSTRING(7)
    spells = CBashFORMIDARRAY(8)
    exportattrs = copyattrs = ObBaseRecord.baseattrs + [u'full', u'iconPath',
                                                        u'text', u'spells']

class ObCELLRecord(ObBaseRecord):
    __slots__ = []
    _Type = b'CELL'
    @property
    def _ParentID(self):
        _CGetField.restype = c_record_p
        return _CGetField(self._RecordID, 40, 0, 0, 0, 0, 0, 0, 0)

    @property
    def bsb(self):
        """Returns tesfile block and sub-block indices for cells in this group.
        For interior cell, bsb is (blockNum,subBlockNum). For exterior cell, bsb is
        ((blockX,blockY),(subblockX,subblockY))."""
        #--Interior cell
        if self.IsInterior:
            ObjectID = self.fid[1]
            return (ObjectID % 10, (ObjectID // 10) % 10)
        #--Exterior cell
        else:
            subblockX = int(math.floor((self.posX or 0) / 8.0))
            subblockY = int(math.floor((self.posY or 0) / 8.0))
            return ((int(math.floor(subblockX / 4.0)), int(math.floor(subblockY / 4.0))), (subblockX, subblockY))

    full = CBashSTRING(5)
    flags = CBashGeneric(6, c_ubyte)
    ambientRed = CBashGeneric(7, c_ubyte)
    ambientGreen = CBashGeneric(8, c_ubyte)
    ambientBlue = CBashGeneric(9, c_ubyte)
    unused1 = CBashUINT8ARRAY(10, 1)
    directionalRed = CBashGeneric(11, c_ubyte)
    directionalGreen = CBashGeneric(12, c_ubyte)
    directionalBlue = CBashGeneric(13, c_ubyte)
    unused2 = CBashUINT8ARRAY(14, 1)
    fogRed = CBashGeneric(15, c_ubyte)
    fogGreen = CBashGeneric(16, c_ubyte)
    fogBlue = CBashGeneric(17, c_ubyte)
    unused3 = CBashUINT8ARRAY(18, 1)
    fogNear = CBashFLOAT32(19)
    fogFar = CBashFLOAT32(20)
    directionalXY = CBashGeneric(21, c_long)
    directionalZ = CBashGeneric(22, c_long)
    directionalFade = CBashFLOAT32(23)
    fogClip = CBashFLOAT32(24)
    musicType = CBashGeneric(25, c_ubyte)
    owner = CBashFORMID(26)
    rank = CBashGeneric(27, c_long)
    globalVariable = CBashFORMID(28)
    climate = CBashFORMID(29)
    waterHeight = CBashFLOAT32(30)
    regions = CBashFORMIDARRAY(31)
    posX = CBashUNKNOWN_OR_GENERIC(32, c_long)
    posY = CBashUNKNOWN_OR_GENERIC(33, c_long)
    water = CBashFORMID(34)
    def create_ACHR(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self.GetParentMod()._ModID, cast(b'ACHR', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, self._RecordID)
        return ObACHRRecord(RecordID) if RecordID else None
    ACHR = CBashSUBRECORDARRAY(35, ObACHRRecord, b'ACHR')

    def create_ACRE(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self.GetParentMod()._ModID, cast(b'ACRE', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, self._RecordID)
        return ObACRERecord(RecordID) if RecordID else None
    ACRE = CBashSUBRECORDARRAY(36, ObACRERecord, b'ACRE')

    def create_REFR(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self.GetParentMod()._ModID, cast(b'REFR', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, self._RecordID)
        return ObREFRRecord(RecordID) if RecordID else None
    REFR = CBashSUBRECORDARRAY(37, ObREFRRecord, b'REFR')

    def create_PGRD(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self.GetParentMod()._ModID, cast(b'PGRD', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, self._RecordID)
        return ObPGRDRecord(RecordID) if RecordID else None
    PGRD = CBashSUBRECORD(38, ObPGRDRecord, b'PGRD')

    def create_LAND(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self.GetParentMod()._ModID, cast(b'LAND', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, self._RecordID)
        return ObLANDRecord(RecordID) if RecordID else None
    LAND = CBashSUBRECORD(39, ObLANDRecord, b'LAND')

    IsInterior = CBashBasicFlag(u'flags', 0x00000001)
    IsHasWater = CBashBasicFlag(u'flags', 0x00000002)
    IsInvertFastTravel = CBashBasicFlag(u'flags', 0x00000004)
    IsForceHideLand = CBashBasicFlag(u'flags', 0x00000008)
    IsPublicPlace = CBashBasicFlag(u'flags', 0x00000020)
    IsHandChanged = CBashBasicFlag(u'flags', 0x00000040)
    IsBehaveLikeExterior = CBashBasicFlag(u'flags', 0x00000080)
    IsDefault = CBashBasicType(u'music', 0, u'IsPublic')
    IsPublic = CBashBasicType(u'music', 1, u'IsDefault')
    IsDungeon = CBashBasicType(u'music', 2, u'IsDefault')
    exportattrs = copyattrs = ObBaseRecord.baseattrs + [
        u'full', u'flags', u'ambientRed', u'ambientGreen', u'ambientBlue',
        u'directionalRed', u'directionalGreen', u'directionalBlue', u'fogRed',
        u'fogGreen', u'fogBlue', u'fogNear', u'fogFar', u'directionalXY',
        u'directionalZ', u'directionalFade', u'fogClip', u'musicType',
        u'owner', u'rank', u'globalVariable', u'climate', u'waterHeight',
        u'regions', u'posX', u'posY', u'water']

class ObCLASRecord(ObBaseRecord):
    __slots__ = []
    _Type = b'CLAS'
    full = CBashSTRING(5)
    description = CBashSTRING(6)
    iconPath = CBashISTRING(7)
    primary1 = CBashGeneric(8, c_long)
    primary2 = CBashGeneric(9, c_long)
    specialization = CBashGeneric(10, c_ulong)
    major1 = CBashGeneric(11, c_long)
    major2 = CBashGeneric(12, c_long)
    major3 = CBashGeneric(13, c_long)
    major4 = CBashGeneric(14, c_long)
    major5 = CBashGeneric(15, c_long)
    major6 = CBashGeneric(16, c_long)
    major7 = CBashGeneric(17, c_long)
    flags = CBashGeneric(18, c_ulong)
    services = CBashGeneric(19, c_ulong)
    trainSkill = CBashGeneric(20, c_byte)
    trainLevel = CBashGeneric(21, c_ubyte)
    unused1 = CBashUINT8ARRAY(22, 2)
    IsPlayable = CBashBasicFlag(u'flags', 0x00000001)
    IsGuard = CBashBasicFlag(u'flags', 0x00000002)
    IsServicesWeapons = CBashBasicFlag(u'services', 0x00000001)
    IsServicesArmor = CBashBasicFlag(u'services', 0x00000002)
    IsServicesClothing = CBashBasicFlag(u'services', 0x00000004)
    IsServicesBooks = CBashBasicFlag(u'services', 0x00000008)
    IsServicesIngredients = CBashBasicFlag(u'services', 0x00000010)
    IsServicesLights = CBashBasicFlag(u'services', 0x00000080)
    IsServicesApparatus = CBashBasicFlag(u'services', 0x00000100)
    IsServicesMiscItems = CBashBasicFlag(u'services', 0x00000400)
    IsServicesSpells = CBashBasicFlag(u'services', 0x00000800)
    IsServicesMagicItems = CBashBasicFlag(u'services', 0x00001000)
    IsServicesPotions = CBashBasicFlag(u'services', 0x00002000)
    IsServicesTraining = CBashBasicFlag(u'services', 0x00004000)
    IsServicesRecharge = CBashBasicFlag(u'services', 0x00010000)
    IsServicesRepair = CBashBasicFlag(u'services', 0x00020000)
    exportattrs = copyattrs = ObBaseRecord.baseattrs + [u'full', u'description', u'iconPath', u'primary1',
                                                        u'primary2', u'specialization', u'major1',
                                                        u'major2', u'major3', u'major4', u'major5',
                                                        u'major6', u'major7', u'flags', u'services',
                                                        u'trainSkill', u'trainLevel']

class ObCLMTRecord(ObBaseRecord):
    __slots__ = []
    _Type = b'CLMT'
    class Weather(ListComponent):
        __slots__ = []
        weather = CBashFORMID_LIST(1)
        chance = CBashGeneric_LIST(2, c_long)
        exportattrs = copyattrs = [u'weather', u'chance']

    def create_weather(self):
        length = _CGetFieldAttribute(self._RecordID, 5, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 5, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return self.Weather(self._RecordID, 5, length)
    weathers = CBashLIST(5, Weather)
    weathers_list = CBashLIST(5, Weather, True)

    sunPath = CBashISTRING(6)
    glarePath = CBashISTRING(7)
    modPath = CBashISTRING(8)
    modb = CBashFLOAT32(9)
    modt_p = CBashUINT8ARRAY(10)
    riseBegin = CBashGeneric(11, c_ubyte)
    riseEnd = CBashGeneric(12, c_ubyte)
    setBegin = CBashGeneric(13, c_ubyte)
    setEnd = CBashGeneric(14, c_ubyte)
    volatility = CBashGeneric(15, c_ubyte)
    phaseLength = CBashGeneric(16, c_ubyte)
    copyattrs = ObBaseRecord.baseattrs + [u'weathers_list', u'sunPath', u'glarePath', u'modPath',
                                          u'modb', u'modt_p', u'riseBegin', u'riseEnd',
                                          u'setBegin', u'setEnd', u'volatility', u'phaseLength']
    exportattrs = copyattrs[:]
    exportattrs.remove(u'modt_p')

class ObCLOTRecord(ObBaseRecord):
    __slots__ = []
    _Type = b'CLOT'
    full = CBashSTRING(5)
    script = CBashFORMID(6)
    enchantment = CBashFORMID(7)
    enchantPoints = CBashGeneric(8, c_ushort)
    flags = CBashGeneric(9, c_ulong)
    maleBody = CBashGrouped(10, Model)
    maleBody_list = CBashGrouped(10, Model, True)

    maleWorld = CBashGrouped(13, Model)
    maleWorld_list = CBashGrouped(13, Model, True)

    maleIconPath = CBashISTRING(16)
    femaleBody = CBashGrouped(17, Model)
    femaleBody_list = CBashGrouped(17, Model, True)

    femaleWorld = CBashGrouped(20, Model)
    femaleWorld_list = CBashGrouped(20, Model, True)

    femaleIconPath = CBashISTRING(23)
    value = CBashGeneric(24, c_ulong)
    weight = CBashFLOAT32(25)
    IsHead = CBashBasicFlag(u'flags', 0x00000001)
    IsHair = CBashBasicFlag(u'flags', 0x00000002)
    IsUpperBody = CBashBasicFlag(u'flags', 0x00000004)
    IsLowerBody = CBashBasicFlag(u'flags', 0x00000008)
    IsHand = CBashBasicFlag(u'flags', 0x00000010)
    IsFoot = CBashBasicFlag(u'flags', 0x00000020)
    IsRightRing = CBashBasicFlag(u'flags', 0x00000040)
    IsLeftRing = CBashBasicFlag(u'flags', 0x00000080)
    IsAmulet = CBashBasicFlag(u'flags', 0x00000100)
    IsWeapon = CBashBasicFlag(u'flags', 0x00000200)
    IsBackWeapon = CBashBasicFlag(u'flags', 0x00000400)
    IsSideWeapon = CBashBasicFlag(u'flags', 0x00000800)
    IsQuiver = CBashBasicFlag(u'flags', 0x00001000)
    IsShield = CBashBasicFlag(u'flags', 0x00002000)
    IsTorch = CBashBasicFlag(u'flags', 0x00004000)
    IsTail = CBashBasicFlag(u'flags', 0x00008000)
    IsHideRings = CBashBasicFlag(u'flags', 0x00010000)
    IsHideAmulets = CBashBasicFlag(u'flags', 0x00020000)
    IsNonPlayable = CBashBasicFlag(u'flags', 0x00400000)
    IsPlayable = CBashInvertedFlag(u'IsNonPlayable')
    exportattrs = copyattrs = ObBaseRecord.baseattrs + [u'full', u'script', u'enchantment',
                                                        u'enchantPoints', u'flags', u'maleBody_list', u'maleWorld_list',
                                                        u'maleIconPath', u'femaleBody_list', u'femaleWorld_list',
                                                        u'femaleIconPath', u'value', u'weight']

class ObCONTRecord(ObBaseRecord):
    __slots__ = []
    _Type = b'CONT'
    def mergeFilter(self, target):
        """Filter out items that don't come from specified modSet.
        Filters items."""
        self.items = [x for x in self.items if x.item.ValidateFormID(target)]

    full = CBashSTRING(5)
    modPath = CBashISTRING(6)
    modb = CBashFLOAT32(7)
    modt_p = CBashUINT8ARRAY(8)
    script = CBashFORMID(9)

    def create_item(self):
        length = _CGetFieldAttribute(self._RecordID, 10, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 10, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return Item(self._RecordID, 10, length)
    items = CBashLIST(10, Item)
    items_list = CBashLIST(10, Item, True)

    flags = CBashGeneric(11, c_ubyte)
    weight = CBashFLOAT32(12)
    soundOpen = CBashFORMID(13)
    soundClose = CBashFORMID(14)
    IsRespawn = CBashBasicFlag(u'flags', 0x00000001)
    copyattrs = ObBaseRecord.baseattrs + [u'full', u'modPath', u'modb', u'modt_p',
                                          u'script', u'items_list', u'flags', u'weight',
                                          u'soundOpen', u'soundClose']
    exportattrs = copyattrs[:]
    exportattrs.remove(u'modt_p')

class ObCREARecord(ObBaseRecord):
    __slots__ = []
    _Type = b'CREA'
    def mergeFilter(self, target):
        """Filter out items that don't come from specified modSet.
        Filters spells, factions and items."""
        self.spells = [x for x in self.spells if x.ValidateFormID(target)]
        self.factions = [x for x in self.factions if x.faction.ValidateFormID(target)]
        self.items = [x for x in self.items if x.item.ValidateFormID(target)]

    class Sound(ListComponent):
        __slots__ = []
        soundType = CBashGeneric_LIST(1, c_ulong)
        sound = CBashFORMID_LIST(2)
        chance = CBashGeneric_LIST(3, c_ubyte)
        IsLeftFoot = CBashBasicType(u'soundType', 0, u'IsRightFoot')
        IsRightFoot = CBashBasicType(u'soundType', 1, u'IsLeftFoot')
        IsLeftBackFoot = CBashBasicType(u'soundType', 2, u'IsLeftFoot')
        IsRightBackFoot = CBashBasicType(u'soundType', 3, u'IsLeftFoot')
        IsIdle = CBashBasicType(u'soundType', 4, u'IsLeftFoot')
        IsAware = CBashBasicType(u'soundType', 5, u'IsLeftFoot')
        IsAttack = CBashBasicType(u'soundType', 6, u'IsLeftFoot')
        IsHit = CBashBasicType(u'soundType', 7, u'IsLeftFoot')
        IsDeath = CBashBasicType(u'soundType', 8, u'IsLeftFoot')
        IsWeapon = CBashBasicType(u'soundType', 9, u'IsLeftFoot')
        exportattrs = copyattrs = [u'soundType', u'sound', u'chance']

    full = CBashSTRING(5)
    modPath = CBashISTRING(6)
    modb = CBashFLOAT32(7)
    modt_p = CBashUINT8ARRAY(8)
    spells = CBashFORMIDARRAY(9)
    bodyParts = CBashISTRINGARRAY(10)
    nift_p = CBashUINT8ARRAY(11)
    flags = CBashGeneric(12, c_ulong)
    baseSpell = CBashGeneric(13, c_ushort)
    fatigue = CBashGeneric(14, c_ushort)
    barterGold = CBashGeneric(15, c_ushort)
    level = CBashGeneric(16, c_short)
    calcMin = CBashGeneric(17, c_ushort)
    calcMax = CBashGeneric(18, c_ushort)

    def create_faction(self):
        length = _CGetFieldAttribute(self._RecordID, 19, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 19, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return Faction(self._RecordID, 19, length)
    factions = CBashLIST(19, Faction)
    factions_list = CBashLIST(19, Faction, True)

    deathItem = CBashFORMID(20)
    script = CBashFORMID(21)

    def create_item(self):
        length = _CGetFieldAttribute(self._RecordID, 22, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 22, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return Item(self._RecordID, 22, length)
    items = CBashLIST(22, Item)
    items_list = CBashLIST(22, Item, True)

    aggression = CBashGeneric(23, c_ubyte)
    confidence = CBashGeneric(24, c_ubyte)
    energyLevel = CBashGeneric(25, c_ubyte)
    responsibility = CBashGeneric(26, c_ubyte)
    services = CBashGeneric(27, c_ulong)
    trainSkill = CBashGeneric(28, c_byte)
    trainLevel = CBashGeneric(29, c_ubyte)
    unused1 = CBashUINT8ARRAY(30, 2)
    aiPackages = CBashFORMIDARRAY(31)
    animations = CBashISTRINGARRAY(32)
    creatureType = CBashGeneric(33, c_ubyte)
    combat = CBashGeneric(34, c_ubyte)
    magic = CBashGeneric(35, c_ubyte)
    stealth = CBashGeneric(36, c_ubyte)
    soulType = CBashGeneric(37, c_ubyte)
    unused2 = CBashUINT8ARRAY(38, 1)
    health = CBashGeneric(39, c_ushort)
    unused3 = CBashUINT8ARRAY(40, 2)
    attackDamage = CBashGeneric(41, c_ushort)
    strength = CBashGeneric(42, c_ubyte)
    intelligence = CBashGeneric(43, c_ubyte)
    willpower = CBashGeneric(44, c_ubyte)
    agility = CBashGeneric(45, c_ubyte)
    speed = CBashGeneric(46, c_ubyte)
    endurance = CBashGeneric(47, c_ubyte)
    personality = CBashGeneric(48, c_ubyte)
    luck = CBashGeneric(49, c_ubyte)
    attackReach = CBashGeneric(50, c_ubyte)
    combatStyle = CBashFORMID(51)
    turningSpeed = CBashFLOAT32(52)
    baseScale = CBashFLOAT32(53)
    footWeight = CBashFLOAT32(54)
    inheritsSoundsFrom = CBashFORMID(55)
    bloodSprayPath = CBashISTRING(56)
    bloodDecalPath = CBashISTRING(57)

    def create_sound(self):
        length = _CGetFieldAttribute(self._RecordID, 58, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 58, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return self.Sound(self._RecordID, 58, length)
    sounds = CBashLIST(58, Sound)
    sounds_list = CBashLIST(58, Sound, True)

    IsBiped = CBashBasicFlag(u'flags', 0x00000001)
    IsEssential = CBashBasicFlag(u'flags', 0x00000002)
    IsWeaponAndShield = CBashBasicFlag(u'flags', 0x00000004)
    IsRespawn = CBashBasicFlag(u'flags', 0x00000008)
    IsSwims = CBashBasicFlag(u'flags', 0x00000010)
    IsFlies = CBashBasicFlag(u'flags', 0x00000020)
    IsWalks = CBashBasicFlag(u'flags', 0x00000040)
    IsPCLevelOffset = CBashBasicFlag(u'flags', 0x00000080)
    IsNoLowLevel = CBashBasicFlag(u'flags', 0x00000200)
    IsLowLevel = CBashInvertedFlag(u'IsNoLowLevel')
    IsNoBloodSpray = CBashBasicFlag(u'flags', 0x00000800)
    IsBloodSpray = CBashInvertedFlag(u'IsNoBloodSpray')
    IsNoBloodDecal = CBashBasicFlag(u'flags', 0x00001000)
    IsBloodDecal = CBashInvertedFlag(u'IsNoBloodDecal')
    IsSummonable = CBashBasicFlag(u'flags', 0x00004000)
    IsNoHead = CBashBasicFlag(u'flags', 0x00008000)
    IsHead = CBashInvertedFlag(u'IsNoHead')
    IsNoRightArm = CBashBasicFlag(u'flags', 0x00010000)
    IsRightArm = CBashInvertedFlag(u'IsNoRightArm')
    IsNoLeftArm = CBashBasicFlag(u'flags', 0x00020000)
    IsLeftArm = CBashInvertedFlag(u'IsNoLeftArm')
    IsNoCombatInWater = CBashBasicFlag(u'flags', 0x00040000)
    IsCombatInWater = CBashInvertedFlag(u'IsNoCombatInWater')
    IsNoShadow = CBashBasicFlag(u'flags', 0x00080000)
    IsShadow = CBashInvertedFlag(u'IsNoShadow')
    IsNoCorpseCheck = CBashBasicFlag(u'flags', 0x00100000)
    IsCorpseCheck = CBashInvertedFlag(u'IsNoCorpseCheck')
    IsServicesWeapons = CBashBasicFlag(u'services', 0x00000001)
    IsServicesArmor = CBashBasicFlag(u'services', 0x00000002)
    IsServicesClothing = CBashBasicFlag(u'services', 0x00000004)
    IsServicesBooks = CBashBasicFlag(u'services', 0x00000008)
    IsServicesIngredients = CBashBasicFlag(u'services', 0x00000010)
    IsServicesLights = CBashBasicFlag(u'services', 0x00000080)
    IsServicesApparatus = CBashBasicFlag(u'services', 0x00000100)
    IsServicesMiscItems = CBashBasicFlag(u'services', 0x00000400)
    IsServicesSpells = CBashBasicFlag(u'services', 0x00000800)
    IsServicesMagicItems = CBashBasicFlag(u'services', 0x00001000)
    IsServicesPotions = CBashBasicFlag(u'services', 0x00002000)
    IsServicesTraining = CBashBasicFlag(u'services', 0x00004000)
    IsServicesRecharge = CBashBasicFlag(u'services', 0x00010000)
    IsServicesRepair = CBashBasicFlag(u'services', 0x00020000)
    IsCreature = CBashBasicType(u'creatureType', 0, u'IsDaedra')
    IsDaedra = CBashBasicType(u'creatureType', 1, u'IsCreature')
    IsUndead = CBashBasicType(u'creatureType', 2, u'IsCreature')
    IsHumanoid = CBashBasicType(u'creatureType', 3, u'IsCreature')
    IsHorse = CBashBasicType(u'creatureType', 4, u'IsCreature')
    IsGiant = CBashBasicType(u'creatureType', 5, u'IsCreature')
    IsNoSoul = CBashBasicType(u'soulType', 0, u'IsPettySoul')
    IsPettySoul = CBashBasicType(u'soulType', 1, u'IsNoSoul')
    IsLesserSoul = CBashBasicType(u'soulType', 2, u'IsNoSoul')
    IsCommonSoul = CBashBasicType(u'soulType', 3, u'IsNoSoul')
    IsGreaterSoul = CBashBasicType(u'soulType', 4, u'IsNoSoul')
    IsGrandSoul = CBashBasicType(u'soulType', 5, u'IsNoSoul')
    copyattrs = ObBaseRecord.baseattrs + [
        u'full', u'modPath', u'modb', u'modt_p', u'spells', u'bodyParts',
        u'nift_p', u'flags', u'baseSpell', u'fatigue', u'barterGold', u'level',
        u'calcMin', u'calcMax', u'factions_list', u'deathItem', u'script',
        u'items_list', u'aggression', u'confidence', u'energyLevel',
        u'responsibility', u'services', u'trainSkill', u'trainLevel',
        u'aiPackages', u'animations', u'creatureType', u'combat', u'magic',
        u'stealth', u'soulType', u'health', u'attackDamage', u'strength',
        u'intelligence', u'willpower', u'agility', u'speed', u'endurance',
        u'personality', u'luck', u'attackReach', u'combatStyle',
        u'turningSpeed', u'baseScale', u'footWeight', u'inheritsSoundsFrom',
        u'bloodSprayPath', u'bloodDecalPath', u'sounds_list']
    exportattrs = copyattrs[:]
    exportattrs.remove(u'modt_p')
    exportattrs.remove(u'nift_p')

class ObCSTYRecord(ObBaseRecord):
    __slots__ = []
    _Type = b'CSTY'
    dodgeChance = CBashGeneric(5, c_ubyte)
    lrChance = CBashGeneric(6, c_ubyte)
    unused1 = CBashUINT8ARRAY(7, 2)
    lrTimerMin = CBashFLOAT32(8)
    lrTimerMax = CBashFLOAT32(9)
    forTimerMin = CBashFLOAT32(10)
    forTimerMax = CBashFLOAT32(11)
    backTimerMin = CBashFLOAT32(12)
    backTimerMax = CBashFLOAT32(13)
    idleTimerMin = CBashFLOAT32(14)
    idleTimerMax = CBashFLOAT32(15)
    blkChance = CBashGeneric(16, c_ubyte)
    atkChance = CBashGeneric(17, c_ubyte)
    unused2 = CBashUINT8ARRAY(18, 2)
    atkBRecoil = CBashFLOAT32(19)
    atkBUnc = CBashFLOAT32(20)
    atkBh2h = CBashFLOAT32(21)
    pAtkChance = CBashGeneric(22, c_ubyte)
    unused3 = CBashUINT8ARRAY(23, 3)
    pAtkBRecoil = CBashFLOAT32(24)
    pAtkBUnc = CBashFLOAT32(25)
    pAtkNormal = CBashGeneric(26, c_ubyte)
    pAtkFor = CBashGeneric(27, c_ubyte)
    pAtkBack = CBashGeneric(28, c_ubyte)
    pAtkL = CBashGeneric(29, c_ubyte)
    pAtkR = CBashGeneric(30, c_ubyte)
    unused4 = CBashUINT8ARRAY(31, 3)
    holdTimerMin = CBashFLOAT32(32)
    holdTimerMax = CBashFLOAT32(33)
    flagsA = CBashGeneric(34, c_ubyte)
    acroDodge = CBashGeneric(35, c_ubyte)
    unused5 = CBashUINT8ARRAY(36, 2)
    rMultOpt = CBashFLOAT32(37)
    rMultMax = CBashFLOAT32(38)
    mDistance = CBashFLOAT32(39)
    rDistance = CBashFLOAT32(40)
    buffStand = CBashFLOAT32(41)
    rStand = CBashFLOAT32(42)
    groupStand = CBashFLOAT32(43)
    rushChance = CBashGeneric(44, c_ubyte)
    unused6 = CBashUINT8ARRAY(45, 3)
    rushMult = CBashFLOAT32(46)
    flagsB = CBashGeneric(47, c_ulong)
    dodgeFMult = CBashFLOAT32(48)
    dodgeFBase = CBashFLOAT32(49)
    encSBase = CBashFLOAT32(50)
    encSMult = CBashFLOAT32(51)
    dodgeAtkMult = CBashFLOAT32(52)
    dodgeNAtkMult = CBashFLOAT32(53)
    dodgeBAtkMult = CBashFLOAT32(54)
    dodgeBNAtkMult = CBashFLOAT32(55)
    dodgeFAtkMult = CBashFLOAT32(56)
    dodgeFNAtkMult = CBashFLOAT32(57)
    blockMult = CBashFLOAT32(58)
    blockBase = CBashFLOAT32(59)
    blockAtkMult = CBashFLOAT32(60)
    blockNAtkMult = CBashFLOAT32(61)
    atkMult = CBashFLOAT32(62)
    atkBase = CBashFLOAT32(63)
    atkAtkMult = CBashFLOAT32(64)
    atkNAtkMult = CBashFLOAT32(65)
    atkBlockMult = CBashFLOAT32(66)
    pAtkFBase = CBashFLOAT32(67)
    pAtkFMult = CBashFLOAT32(68)
    IsUseAdvanced = CBashBasicFlag(u'flagsA', 0x00000001)
    IsUseChanceForAttack = CBashBasicFlag(u'flagsA', 0x00000002)
    IsIgnoreAllies = CBashBasicFlag(u'flagsA', 0x00000004)
    IsWillYield = CBashBasicFlag(u'flagsA', 0x00000008)
    IsRejectsYields = CBashBasicFlag(u'flagsA', 0x00000010)
    IsFleeingDisabled = CBashBasicFlag(u'flagsA', 0x00000020)
    IsPrefersRanged = CBashBasicFlag(u'flagsA', 0x00000040)
    IsMeleeAlertOK = CBashBasicFlag(u'flagsA', 0x00000080)
    IsDoNotAcquire = CBashBasicFlag(u'flagsB', 0x00000001)
    exportattrs = copyattrs = ObBaseRecord.baseattrs + [
        u'dodgeChance', u'lrChance', u'lrTimerMin', u'lrTimerMax',
        u'forTimerMin', u'forTimerMax', u'backTimerMin', u'backTimerMax',
        u'idleTimerMin', u'idleTimerMax', u'blkChance', u'atkChance',
        u'atkBRecoil', u'atkBUnc', u'atkBh2h', u'pAtkChance', u'pAtkBRecoil',
        u'pAtkBUnc', u'pAtkNormal', u'pAtkFor', u'pAtkBack', u'pAtkL',
        u'pAtkR', u'holdTimerMin', u'holdTimerMax', u'flagsA', u'acroDodge',
        u'rMultOpt', u'rMultMax', u'mDistance', u'rDistance', u'buffStand',
        u'rStand', u'groupStand', u'rushChance', u'rushMult', u'flagsB',
        u'dodgeFMult', u'dodgeFBase', u'encSBase', u'encSMult',
        u'dodgeAtkMult', u'dodgeNAtkMult', u'dodgeBAtkMult', u'dodgeBNAtkMult',
        u'dodgeFAtkMult', u'dodgeFNAtkMult', u'blockMult', u'blockBase',
        u'blockAtkMult', u'blockNAtkMult', u'atkMult', u'atkBase',
        u'atkAtkMult', u'atkNAtkMult', u'atkBlockMult', u'pAtkFBase',
        u'pAtkFMult']

class ObDIALRecord(ObBaseRecord):
    __slots__ = []
    _Type = b'DIAL'
    quests = CBashFORMIDARRAY(5)
    removedQuests = CBashFORMIDARRAY(6)
    full = CBashSTRING(7)
    dialType = CBashGeneric(8, c_ubyte)
    def create_INFO(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self.GetParentMod()._ModID, cast(b'INFO', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, self._RecordID)
        return ObINFORecord(RecordID) if RecordID else None
    INFO = CBashSUBRECORDARRAY(9, ObINFORecord, b'INFO')

    IsTopic = CBashBasicType(u'dialType', 0, u'IsConversation')
    IsConversation = CBashBasicType(u'dialType', 1, u'IsTopic')
    IsCombat = CBashBasicType(u'dialType', 2, u'IsTopic')
    IsPersuasion = CBashBasicType(u'dialType', 3, u'IsTopic')
    IsDetection = CBashBasicType(u'dialType', 4, u'IsTopic')
    IsService = CBashBasicType(u'dialType', 5, u'IsTopic')
    IsMisc = CBashBasicType(u'dialType', 6, u'IsTopic')
    exportattrs = copyattrs = ObBaseRecord.baseattrs + [u'quests', u'removedQuests',
                                                        u'full', u'dialType']

class ObDOORRecord(ObBaseRecord):
    __slots__ = []
    _Type = b'DOOR'
    full = CBashSTRING(5)
    modPath = CBashISTRING(6)
    modb = CBashFLOAT32(7)
    modt_p = CBashUINT8ARRAY(8)
    script = CBashFORMID(9)
    soundOpen = CBashFORMID(10)
    soundClose = CBashFORMID(11)
    soundLoop = CBashFORMID(12)
    flags = CBashGeneric(13, c_ubyte)
    destinations = CBashFORMIDARRAY(14)
    IsOblivionGate = CBashBasicFlag(u'flags', 0x00000001)
    IsAutomatic = CBashBasicFlag(u'flags', 0x00000002)
    IsHidden = CBashBasicFlag(u'flags', 0x00000004)
    IsMinimalUse = CBashBasicFlag(u'flags', 0x00000008)
    copyattrs = ObBaseRecord.baseattrs + [u'full', u'modPath', u'modb', u'modt_p',
                                          u'script', u'soundOpen',
                                          u'soundClose', u'soundLoop',
                                          u'flags', u'destinations']
    exportattrs = copyattrs[:]
    exportattrs.remove(u'modt_p')

class ObEFSHRecord(ObBaseRecord):
    __slots__ = []
    _Type = b'EFSH'
    fillTexturePath = CBashISTRING(5)
    particleTexturePath = CBashISTRING(6)
    flags = CBashGeneric(7, c_ubyte)
    unused1 = CBashUINT8ARRAY(8, 3)
    memSBlend = CBashGeneric(9, c_ulong)
    memBlendOp = CBashGeneric(10, c_ulong)
    memZFunc = CBashGeneric(11, c_ulong)
    fillRed = CBashGeneric(12, c_ubyte)
    fillGreen = CBashGeneric(13, c_ubyte)
    fillBlue = CBashGeneric(14, c_ubyte)
    unused2 = CBashUINT8ARRAY(15, 1)
    fillAIn = CBashFLOAT32(16)
    fillAFull = CBashFLOAT32(17)
    fillAOut = CBashFLOAT32(18)
    fillAPRatio = CBashFLOAT32(19)
    fillAAmp = CBashFLOAT32(20)
    fillAFreq = CBashFLOAT32(21)
    fillAnimSpdU = CBashFLOAT32(22)
    fillAnimSpdV = CBashFLOAT32(23)
    edgeOff = CBashFLOAT32(24)
    edgeRed = CBashGeneric(25, c_ubyte)
    edgeGreen = CBashGeneric(26, c_ubyte)
    edgeBlue = CBashGeneric(27, c_ubyte)
    unused3 = CBashUINT8ARRAY(28, 1)
    edgeAIn = CBashFLOAT32(29)
    edgeAFull = CBashFLOAT32(30)
    edgeAOut = CBashFLOAT32(31)
    edgeAPRatio = CBashFLOAT32(32)
    edgeAAmp = CBashFLOAT32(33)
    edgeAFreq = CBashFLOAT32(34)
    fillAFRatio = CBashFLOAT32(35)
    edgeAFRatio = CBashFLOAT32(36)
    memDBlend = CBashGeneric(37, c_ubyte)
    partSBlend = CBashGeneric(38, c_ubyte)
    partBlendOp = CBashGeneric(39, c_ubyte)
    partZFunc = CBashGeneric(40, c_ubyte)
    partDBlend = CBashGeneric(41, c_ubyte)
    partBUp = CBashFLOAT32(42)
    partBFull = CBashFLOAT32(43)
    partBDown = CBashFLOAT32(44)
    partBFRatio = CBashFLOAT32(45)
    partBPRatio = CBashFLOAT32(46)
    partLTime = CBashFLOAT32(47)
    partLDelta = CBashFLOAT32(48)
    partNSpd = CBashFLOAT32(49)
    partNAcc = CBashFLOAT32(50)
    partVel1 = CBashFLOAT32(51)
    partVel2 = CBashFLOAT32(52)
    partVel3 = CBashFLOAT32(53)
    partAcc1 = CBashFLOAT32(54)
    partAcc2 = CBashFLOAT32(55)
    partAcc3 = CBashFLOAT32(56)
    partKey1 = CBashFLOAT32(57)
    partKey2 = CBashFLOAT32(58)
    partKey1Time = CBashFLOAT32(59)
    partKey2Time = CBashFLOAT32(60)
    key1Red = CBashGeneric(61, c_ubyte)
    key1Green = CBashGeneric(62, c_ubyte)
    key1Blue = CBashGeneric(63, c_ubyte)
    unused4 = CBashUINT8ARRAY(64, 1)
    key2Red = CBashGeneric(65, c_ubyte)
    key2Green = CBashGeneric(66, c_ubyte)
    key2Blue = CBashGeneric(67, c_ubyte)
    unused5 = CBashUINT8ARRAY(68, 1)
    key3Red = CBashGeneric(69, c_ubyte)
    key3Green = CBashGeneric(70, c_ubyte)
    key3Blue = CBashGeneric(71, c_ubyte)
    unused6 = CBashUINT8ARRAY(72, 1)
    key1A = CBashFLOAT32(73)
    key2A = CBashFLOAT32(74)
    key3A = CBashFLOAT32(75)
    key1Time = CBashFLOAT32(76)
    key2Time = CBashFLOAT32(77)
    key3Time = CBashFLOAT32(78)
    IsNoMemShader = CBashBasicFlag(u'flags', 0x00000001)
    IsNoMembraneShader = CBashAlias(u'IsNoMemShader')
    IsNoPartShader = CBashBasicFlag(u'flags', 0x00000008)
    IsNoParticleShader = CBashAlias(u'IsNoPartShader')
    IsEdgeInverse = CBashBasicFlag(u'flags', 0x00000010)
    IsEdgeEffectInverse = CBashAlias(u'IsEdgeInverse')
    IsMemSkinOnly = CBashBasicFlag(u'flags', 0x00000020)
    IsMembraneShaderSkinOnly = CBashAlias(u'IsMemSkinOnly')
    exportattrs = copyattrs = ObBaseRecord.baseattrs + [
        u'fillTexturePath', u'particleTexturePath', u'flags', u'memSBlend',
        u'memBlendOp', u'memZFunc', u'fillRed', u'fillGreen', u'fillBlue',
        u'fillAIn', u'fillAFull', u'fillAOut', u'fillAPRatio', u'fillAAmp',
        u'fillAFreq', u'fillAnimSpdU', u'fillAnimSpdV', u'edgeOff', u'edgeRed',
        u'edgeGreen', u'edgeBlue', u'edgeAIn', u'edgeAFull', u'edgeAOut',
        u'edgeAPRatio', u'edgeAAmp', u'edgeAFreq', u'fillAFRatio',
        u'edgeAFRatio', u'memDBlend', u'partSBlend', u'partBlendOp',
        u'partZFunc', u'partDBlend', u'partBUp', u'partBFull', u'partBDown',
        u'partBFRatio', u'partBPRatio', u'partLTime', u'partLDelta',
        u'partNSpd', u'partNAcc', u'partVel1', u'partVel2', u'partVel3',
        u'partAcc1', u'partAcc2', u'partAcc3', u'partKey1', u'partKey2',
        u'partKey1Time', u'partKey2Time', u'key1Red', u'key1Green',
        u'key1Blue', u'key2Red', u'key2Green', u'key2Blue', u'key3Red',
        u'key3Green', u'key3Blue', u'key1A', u'key2A', u'key3A', u'key1Time',
        u'key2Time', u'key3Time']

class ObENCHRecord(ObBaseRecord):
    __slots__ = []
    _Type = b'ENCH'
    full = CBashSTRING(5)
    itemType = CBashGeneric(6, c_ulong)
    chargeAmount = CBashGeneric(7, c_ulong)
    enchantCost = CBashGeneric(8, c_ulong)
    flags = CBashGeneric(9, c_ubyte)
    unused1 = CBashUINT8ARRAY(10, 3)

    def create_effect(self):
        length = _CGetFieldAttribute(self._RecordID, 11, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 11, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return Effect(self._RecordID, 11, length)
    effects = CBashLIST(11, Effect)
    effects_list = CBashLIST(11, Effect, True)

    IsNoAutoCalc = CBashBasicFlag(u'flags', 0x00000001)
    IsAutoCalc = CBashInvertedFlag(u'IsNoAutoCalc')
    IsScroll = CBashBasicType(u'itemType', 0, u'IsStaff')
    IsStaff = CBashBasicType(u'itemType', 1, u'IsScroll')
    IsWeapon = CBashBasicType(u'itemType', 2, u'IsScroll')
    IsApparel = CBashBasicType(u'itemType', 3, u'IsScroll')
    ##OBME Fields. Setting any of the below fields will make the mod require JRoush's OBME plugin for OBSE
    ##To see if OBME is in use, check the recordVersion field for a non-None value
    recordVersion = CBashGeneric(12, c_ubyte)
    betaVersion = CBashGeneric(13, c_ubyte)
    minorVersion = CBashGeneric(14, c_ubyte)
    majorVersion = CBashGeneric(15, c_ubyte)
    reserved = CBashUINT8ARRAY(16, 0x1C)
    datx_p = CBashUINT8ARRAY(17, 0x20)
    exportattrs = copyattrs = ObBaseRecord.baseattrs + [u'full', u'itemType', u'chargeAmount',
                                                        u'enchantCost', u'flags', u'effects_list']
    copyattrsOBME = copyattrs + [u'recordVersion', u'betaVersion',
                                 u'minorVersion', u'majorVersion',
                                 u'reserved', u'datx_p']
    exportattrsOBME = copyattrsOBME[:]
    exportattrsOBME.remove(u'reserved')
    exportattrsOBME.remove(u'datx_p')

class ObEYESRecord(ObBaseRecord):
    __slots__ = []
    _Type = b'EYES'
    full = CBashSTRING(5)
    iconPath = CBashISTRING(6)
    flags = CBashGeneric(7, c_ubyte)
    IsPlayable = CBashBasicFlag(u'flags', 0x00000001)
    exportattrs = copyattrs = ObBaseRecord.baseattrs + [u'full', u'iconPath', u'flags']

class ObFACTRecord(ObBaseRecord):
    __slots__ = []
    _Type = b'FACT'
    class Rank(ListComponent):
        __slots__ = []
        rank = CBashGeneric_LIST(1, c_long)
        male = CBashSTRING_LIST(2)
        female = CBashSTRING_LIST(3)
        insigniaPath = CBashISTRING_LIST(4)
        exportattrs = copyattrs = [u'rank', u'male', u'female', u'insigniaPath']

    full = CBashSTRING(5)

    def create_relation(self):
        length = _CGetFieldAttribute(self._RecordID, 6, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 6, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return Relation(self._RecordID, 6, length)
    relations = CBashLIST(6, Relation)
    relations_list = CBashLIST(6, Relation, True)

    flags = CBashGeneric(7, c_ubyte)
    crimeGoldMultiplier = CBashFLOAT32(8)

    def create_rank(self):
        length = _CGetFieldAttribute(self._RecordID, 9, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 9, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return self.Rank(self._RecordID, 9, length)
    ranks = CBashLIST(9, Rank)
    ranks_list = CBashLIST(9, Rank, True)

    IsHiddenFromPC = CBashBasicFlag(u'flags', 0x00000001)
    IsEvil = CBashBasicFlag(u'flags', 0x00000002)
    IsSpecialCombat = CBashBasicFlag(u'flags', 0x00000004)
    exportattrs = copyattrs = ObBaseRecord.baseattrs + [u'full', u'relations_list', u'flags',
                                                        u'crimeGoldMultiplier', u'ranks_list']

class ObFLORRecord(ObBaseRecord):
    __slots__ = []
    _Type = b'FLOR'
    full = CBashSTRING(5)
    modPath = CBashISTRING(6)
    modb = CBashFLOAT32(7)
    modt_p = CBashUINT8ARRAY(8)
    script = CBashFORMID(9)
    ingredient = CBashFORMID(10)
    spring = CBashGeneric(11, c_ubyte)
    summer = CBashGeneric(12, c_ubyte)
    fall = CBashGeneric(13, c_ubyte)
    winter = CBashGeneric(14, c_ubyte)
    copyattrs = ObBaseRecord.baseattrs + [u'full', u'modPath', u'modb', u'modt_p',
                                          u'script', u'ingredient', u'spring',
                                          u'summer', u'fall', u'winter']
    exportattrs = copyattrs[:]
    exportattrs.remove(u'modt_p')

class ObFURNRecord(ObBaseRecord):
    __slots__ = []
    _Type = b'FURN'
    full = CBashSTRING(5)
    modPath = CBashISTRING(6)
    modb = CBashFLOAT32(7)
    modt_p = CBashUINT8ARRAY(8)
    script = CBashFORMID(9)
    flags = CBashGeneric(10, c_ulong)
    IsAnim01 = CBashBasicFlag(u'flags', 0x00000001)
    IsAnim02 = CBashBasicFlag(u'flags', 0x00000002)
    IsAnim03 = CBashBasicFlag(u'flags', 0x00000004)
    IsAnim04 = CBashBasicFlag(u'flags', 0x00000008)
    IsAnim05 = CBashBasicFlag(u'flags', 0x00000010)
    IsAnim06 = CBashBasicFlag(u'flags', 0x00000020)
    IsAnim07 = CBashBasicFlag(u'flags', 0x00000040)
    IsAnim08 = CBashBasicFlag(u'flags', 0x00000080)
    IsAnim09 = CBashBasicFlag(u'flags', 0x00000100)
    IsAnim10 = CBashBasicFlag(u'flags', 0x00000200)
    IsAnim11 = CBashBasicFlag(u'flags', 0x00000400)
    IsAnim12 = CBashBasicFlag(u'flags', 0x00000800)
    IsAnim13 = CBashBasicFlag(u'flags', 0x00001000)
    IsAnim14 = CBashBasicFlag(u'flags', 0x00002000)
    IsAnim15 = CBashBasicFlag(u'flags', 0x00004000)
    IsAnim16 = CBashBasicFlag(u'flags', 0x00008000)
    IsAnim17 = CBashBasicFlag(u'flags', 0x00010000)
    IsAnim18 = CBashBasicFlag(u'flags', 0x00020000)
    IsAnim19 = CBashBasicFlag(u'flags', 0x00040000)
    IsAnim20 = CBashBasicFlag(u'flags', 0x00080000)
    IsAnim21 = CBashBasicFlag(u'flags', 0x00100000)
    IsAnim22 = CBashBasicFlag(u'flags', 0x00200000)
    IsAnim23 = CBashBasicFlag(u'flags', 0x00400000)
    IsAnim24 = CBashBasicFlag(u'flags', 0x00800000)
    IsAnim25 = CBashBasicFlag(u'flags', 0x01000000)
    IsAnim26 = CBashBasicFlag(u'flags', 0x02000000)
    IsAnim27 = CBashBasicFlag(u'flags', 0x04000000)
    IsAnim28 = CBashBasicFlag(u'flags', 0x08000000)
    IsAnim29 = CBashBasicFlag(u'flags', 0x10000000)
    IsAnim30 = CBashBasicFlag(u'flags', 0x20000000)
    IsSitAnim = CBashMaskedType(u'flags', 0xC0000000, 0x40000000, u'IsSleepAnim')
    IsSleepAnim = CBashMaskedType(u'flags', 0xC0000000, 0x80000000, u'IsSitAnim')
    copyattrs = ObBaseRecord.baseattrs + [u'full', u'modPath', u'modb',
                                          u'modt_p', u'script', u'flags']
    exportattrs = copyattrs[:]
    exportattrs.remove(u'modt_p')

class ObGLOBRecord(ObBaseRecord):
    __slots__ = []
    _Type = b'GLOB'
    format = CBashGeneric(5, c_char)
    value = CBashFLOAT32(6)
    exportattrs = copyattrs = ObBaseRecord.baseattrs + [u'format', u'value']

class ObGRASRecord(ObBaseRecord):
    __slots__ = []
    _Type = b'GRAS'
    modPath = CBashISTRING(5)
    modb = CBashFLOAT32(6)
    modt_p = CBashUINT8ARRAY(7)
    density = CBashGeneric(8, c_ubyte)
    minSlope = CBashGeneric(9, c_ubyte)
    maxSlope = CBashGeneric(10, c_ubyte)
    unused1 = CBashUINT8ARRAY(11, 1)
    waterDistance = CBashGeneric(12, c_ushort)
    unused2 = CBashUINT8ARRAY(13, 2)
    waterOp = CBashGeneric(14, c_ulong)
    posRange = CBashFLOAT32(15)
    heightRange = CBashFLOAT32(16)
    colorRange = CBashFLOAT32(17)
    wavePeriod = CBashFLOAT32(18)
    flags = CBashGeneric(19, c_ubyte)
    unused3 = CBashUINT8ARRAY(20, 3)
    IsVLighting = CBashBasicFlag(u'flags', 0x00000001)
    IsVertexLighting = CBashAlias(u'IsVLighting')
    IsUScaling = CBashBasicFlag(u'flags', 0x00000002)
    IsUniformScaling = CBashAlias(u'IsUScaling')
    IsFitSlope = CBashBasicFlag(u'flags', 0x00000004)
    IsFitToSlope = CBashAlias(u'IsFitSlope')
    copyattrs = ObBaseRecord.baseattrs + [u'modPath', u'modb', u'modt_p', u'density',
                                          u'minSlope', u'maxSlope', u'waterDistance',
                                          u'waterOp', u'posRange', u'heightRange',
                                          u'colorRange', u'wavePeriod', u'flags']
    exportattrs = copyattrs[:]
    exportattrs.remove(u'modt_p')

class ObHAIRRecord(ObBaseRecord):
    __slots__ = []
    _Type = b'HAIR'
    full = CBashSTRING(5)
    modPath = CBashISTRING(6)
    modb = CBashFLOAT32(7)
    modt_p = CBashUINT8ARRAY(8)
    iconPath = CBashISTRING(9)
    flags = CBashGeneric(10, c_ubyte)
    IsPlayable = CBashBasicFlag(u'flags', 0x00000001)
    IsNotMale = CBashBasicFlag(u'flags', 0x00000002)
    IsMale = CBashInvertedFlag(u'IsNotMale')
    IsNotFemale = CBashBasicFlag(u'flags', 0x00000004)
    IsFemale = CBashInvertedFlag(u'IsNotFemale')
    IsFixedColor = CBashBasicFlag(u'flags', 0x00000008)
    copyattrs = ObBaseRecord.baseattrs + [u'full', u'modPath', u'modb',
                                          u'modt_p', u'iconPath', u'flags']
    exportattrs = copyattrs[:]
    exportattrs.remove(u'modt_p')

class ObIDLERecord(ObBaseRecord):
    __slots__ = []
    _Type = b'IDLE'
    modPath = CBashISTRING(5)
    modb = CBashFLOAT32(6)
    modt_p = CBashUINT8ARRAY(7)

    def create_condition(self):
        length = _CGetFieldAttribute(self._RecordID, 8, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 8, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return Condition(self._RecordID, 8, length)
    conditions = CBashLIST(8, Condition)
    conditions_list = CBashLIST(8, Condition, True)

    group = CBashGeneric(9, c_ubyte)
    parent = CBashFORMID(10)
    prevId = CBashFORMID(11)
    IsLowerBody = CBashMaskedType(u'group',  0x0F, 0x00, u'IsLeftArm')
    IsLeftArm = CBashMaskedType(u'group',  0x0F, 0x01, u'IsLowerBody')
    IsLeftHand = CBashMaskedType(u'group',  0x0F, 0x02, u'IsLowerBody')
    IsRightArm = CBashMaskedType(u'group',  0x0F, 0x03, u'IsLowerBody')
    IsSpecialIdle = CBashMaskedType(u'group',  0x0F, 0x04, u'IsLowerBody')
    IsWholeBody = CBashMaskedType(u'group',  0x0F, 0x05, u'IsLowerBody')
    IsUpperBody = CBashMaskedType(u'group',  0x0F, 0x06, u'IsLowerBody')
    IsNotReturnFile = CBashBasicFlag(u'group', 0x80)
    IsReturnFile = CBashInvertedFlag(u'IsNotReturnFile')
    copyattrs = ObBaseRecord.baseattrs + [u'modPath', u'modb', u'modt_p',
                                          u'conditions_list', u'group', u'parent', u'prevId']
    exportattrs = copyattrs[:]
    exportattrs.remove(u'modt_p')

class ObINGRRecord(ObBaseRecord):
    __slots__ = []
    _Type = b'INGR'
    full = CBashSTRING(5)
    modPath = CBashISTRING(6)
    modb = CBashFLOAT32(7)
    modt_p = CBashUINT8ARRAY(8)
    iconPath = CBashISTRING(9)
    script = CBashFORMID(10)
    weight = CBashFLOAT32(11)
    value = CBashGeneric(12, c_long)
    flags = CBashGeneric(13, c_ubyte)
    unused1 = CBashUINT8ARRAY(14, 3)

    def create_effect(self):
        length = _CGetFieldAttribute(self._RecordID, 15, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 15, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return Effect(self._RecordID, 15, length)
    effects = CBashLIST(15, Effect)
    effects_list = CBashLIST(15, Effect, True)

    IsNoAutoCalc = CBashBasicFlag(u'flags', 0x00000001)
    IsAutoCalc = CBashInvertedFlag(u'IsNoAutoCalc')
    IsFood = CBashBasicFlag(u'flags', 0x00000002)
    ##OBME Fields. Setting any of the below fields will make the mod require JRoush's OBME plugin for OBSE
    ##To see if OBME is in use, check the recordVersion field for a non-None value
    recordVersion = CBashGeneric(16, c_ubyte)
    betaVersion = CBashGeneric(17, c_ubyte)
    minorVersion = CBashGeneric(18, c_ubyte)
    majorVersion = CBashGeneric(19, c_ubyte)
    reserved = CBashUINT8ARRAY(20, 0x1C)
    datx_p = CBashUINT8ARRAY(21, 0x20)
    copyattrs = ObBaseRecord.baseattrs + [u'full', u'modPath', u'modb', u'modt_p', u'iconPath',
                                          u'script', u'weight', u'value', u'flags',
                                          u'effects_list']
    exportattrs = copyattrs[:]
    exportattrs.remove(u'modt_p')
    copyattrsOBME = copyattrs + [u'recordVersion', u'betaVersion',
                                 u'minorVersion', u'majorVersion',
                                 u'reserved', u'datx_p']
    exportattrsOBME = copyattrsOBME[:]
    exportattrsOBME.remove(u'modt_p')
    exportattrsOBME.remove(u'reserved')
    exportattrsOBME.remove(u'datx_p')

class ObKEYMRecord(ObBaseRecord):
    __slots__ = []
    _Type = b'KEYM'
    full = CBashSTRING(5)
    modPath = CBashISTRING(6)
    modb = CBashFLOAT32(7)
    modt_p = CBashUINT8ARRAY(8)
    iconPath = CBashISTRING(9)
    script = CBashFORMID(10)
    value = CBashGeneric(11, c_long)
    weight = CBashFLOAT32(12)
    copyattrs = ObBaseRecord.baseattrs + [u'full', u'modPath', u'modb', u'modt_p',
                                          u'iconPath', u'script', u'value', u'weight']
    exportattrs = copyattrs[:]
    exportattrs.remove(u'modt_p')

class ObLIGHRecord(ObBaseRecord):
    __slots__ = []
    _Type = b'LIGH'
    modPath = CBashISTRING(5)
    modb = CBashFLOAT32(6)
    modt_p = CBashUINT8ARRAY(7)
    script = CBashFORMID(8)
    full = CBashSTRING(9)
    iconPath = CBashISTRING(10)
    duration = CBashGeneric(11, c_long)
    radius = CBashGeneric(12, c_ulong)
    red = CBashGeneric(13, c_ubyte)
    green = CBashGeneric(14, c_ubyte)
    blue = CBashGeneric(15, c_ubyte)
    unused1 = CBashUINT8ARRAY(16, 1)
    flags = CBashGeneric(17, c_ulong)
    falloff = CBashFLOAT32(18)
    fov = CBashFLOAT32(19)
    value = CBashGeneric(20, c_ulong)
    weight = CBashFLOAT32(21)
    fade = CBashFLOAT32(22)
    sound = CBashFORMID(23)
    IsDynamic = CBashBasicFlag(u'flags', 0x00000001)
    IsCanTake = CBashBasicFlag(u'flags', 0x00000002)
    IsNegative = CBashBasicFlag(u'flags', 0x00000004)
    IsFlickers = CBashBasicFlag(u'flags', 0x00000008)
    IsOffByDefault = CBashBasicFlag(u'flags', 0x00000020)
    IsFlickerSlow = CBashBasicFlag(u'flags', 0x00000040)
    IsPulse = CBashBasicFlag(u'flags', 0x00000080)
    IsPulseSlow = CBashBasicFlag(u'flags', 0x00000100)
    IsSpotLight = CBashBasicFlag(u'flags', 0x00000200)
    IsSpotShadow = CBashBasicFlag(u'flags', 0x00000400)
    copyattrs = ObBaseRecord.baseattrs + [u'modPath', u'modb', u'modt_p', u'script', u'full',
                                          u'iconPath', u'duration', u'radius', u'red',
                                          u'green', u'blue', u'flags', u'falloff', u'fov',
                                          u'value', u'weight', u'fade', u'sound']
    exportattrs = copyattrs[:]
    exportattrs.remove(u'modt_p')

class ObLSCRRecord(ObBaseRecord):
    __slots__ = []
    _Type = b'LSCR'
    class Location(ListComponent):
        __slots__ = []
        direct = CBashFORMID_LIST(1)
        indirect = CBashFORMID_LIST(2)
        gridY = CBashGeneric_LIST(3, c_short)
        gridX = CBashGeneric_LIST(4, c_short)
        exportattrs = copyattrs = [u'direct', u'indirect', u'gridY', u'gridX']

    iconPath = CBashISTRING(5)
    text = CBashSTRING(6)

    def create_location(self):
        length = _CGetFieldAttribute(self._RecordID, 7, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 7, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return self.Location(self._RecordID, 7, length)
    locations = CBashLIST(7, Location)
    locations_list = CBashLIST(7, Location, True)

    exportattrs = copyattrs = ObBaseRecord.baseattrs + [u'iconPath', u'text', u'locations_list']

class ObLTEXRecord(ObBaseRecord):
    __slots__ = []
    _Type = b'LTEX'
    iconPath = CBashISTRING(5)
    types = CBashGeneric(6, c_ubyte)
    friction = CBashGeneric(7, c_ubyte)
    restitution = CBashGeneric(8, c_ubyte)
    specular = CBashGeneric(9, c_ubyte)
    grass = CBashFORMIDARRAY(10)
    IsStone = CBashBasicType(u'types', 0, u'IsDirt')
    IsCloth = CBashBasicType(u'types', 1, u'IsDirt')
    IsDirt = CBashBasicType(u'types', 2, u'IsStone')
    IsGlass = CBashBasicType(u'types', 3, u'IsDirt')
    IsGrass = CBashBasicType(u'types', 4, u'IsDirt')
    IsMetal = CBashBasicType(u'types', 5, u'IsDirt')
    IsOrganic = CBashBasicType(u'types', 6, u'IsDirt')
    IsSkin = CBashBasicType(u'types', 7, u'IsDirt')
    IsWater = CBashBasicType(u'types', 8, u'IsDirt')
    IsWood = CBashBasicType(u'types', 9, u'IsDirt')
    IsHeavyStone = CBashBasicType(u'types', 10, u'IsDirt')
    IsHeavyMetal = CBashBasicType(u'types', 11, u'IsDirt')
    IsHeavyWood = CBashBasicType(u'types', 12, u'IsDirt')
    IsChain = CBashBasicType(u'types', 13, u'IsDirt')
    IsSnow = CBashBasicType(u'types', 14, u'IsDirt')
    IsStoneStairs = CBashBasicType(u'types', 15, u'IsDirt')
    IsClothStairs = CBashBasicType(u'types', 16, u'IsDirt')
    IsDirtStairs = CBashBasicType(u'types', 17, u'IsDirt')
    IsGlassStairs = CBashBasicType(u'types', 18, u'IsDirt')
    IsGrassStairs = CBashBasicType(u'types', 19, u'IsDirt')
    IsMetalStairs = CBashBasicType(u'types', 20, u'IsDirt')
    IsOrganicStairs = CBashBasicType(u'types', 21, u'IsDirt')
    IsSkinStairs = CBashBasicType(u'types', 22, u'IsDirt')
    IsWaterStairs = CBashBasicType(u'types', 23, u'IsDirt')
    IsWoodStairs = CBashBasicType(u'types', 24, u'IsDirt')
    IsHeavyStoneStairs = CBashBasicType(u'types', 25, u'IsDirt')
    IsHeavyMetalStairs = CBashBasicType(u'types', 26, u'IsDirt')
    IsHeavyWoodStairs = CBashBasicType(u'types', 27, u'IsDirt')
    IsChainStairs = CBashBasicType(u'types', 28, u'IsDirt')
    IsSnowStairs = CBashBasicType(u'types', 29, u'IsDirt')
    IsElevator = CBashBasicType(u'types', 30, u'IsDirt')
    exportattrs = copyattrs = ObBaseRecord.baseattrs + [u'iconPath', u'types', u'friction', u'restitution',
                                                        u'specular', u'grass']

class ObLVLCRecord(ObBaseRecord):
    __slots__ = []
    _Type = b'LVLC'
    class Entry(ListComponent):
        __slots__ = []
        level = CBashGeneric_LIST(1, c_short)
        unused1 = CBashUINT8ARRAY_LIST(2, 2)
        listId = CBashFORMID_LIST(3)
        count = CBashGeneric_LIST(4, c_short)
        unused2 = CBashUINT8ARRAY_LIST(5, 2)
        exportattrs = copyattrs = [u'level', u'listId', u'count']

    def mergeFilter(self, target):
        """Filter out items that don't come from specified modSet."""
        self.entries = [entry for entry in self.entries if entry.listId.ValidateFormID(target)]

    chanceNone = CBashGeneric(5, c_ubyte)
    flags = CBashGeneric(6, c_ubyte)
    script = CBashFORMID(7)
    template = CBashFORMID(8)

    def create_entry(self):
        length = _CGetFieldAttribute(self._RecordID, 9, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 9, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return self.Entry(self._RecordID, 9, length)
    entries = CBashLIST(9, Entry)
    entries_list = CBashLIST(9, Entry, True)

    IsCalcFromAllLevels = CBashBasicFlag(u'flags', 0x00000001)
    IsCalcForEachItem = CBashBasicFlag(u'flags', 0x00000002)
    IsUseAllSpells = CBashBasicFlag(u'flags', 0x00000004)
    exportattrs = copyattrs = ObBaseRecord.baseattrs + [u'chanceNone', u'flags', u'script',
                                                        u'template', u'entries_list']

class ObLVLIRecord(ObBaseRecord):
    __slots__ = []
    _Type = b'LVLI'
    class Entry(ListComponent):
        __slots__ = []
        level = CBashGeneric_LIST(1, c_short)
        unused1 = CBashUINT8ARRAY_LIST(2, 2)
        listId = CBashFORMID_LIST(3)
        count = CBashGeneric_LIST(4, c_short)
        unused2 = CBashUINT8ARRAY_LIST(5, 2)
        exportattrs = copyattrs = [u'level', u'listId', u'count']

    def mergeFilter(self, target):
        """Filter out items that don't come from specified modSet."""
        self.entries = [entry for entry in self.entries if entry.listId.ValidateFormID(target)]

    chanceNone = CBashGeneric(5, c_ubyte)
    flags = CBashGeneric(6, c_ubyte)
    script = CBashJunk(7) #Doesn't actually exist, but is here so that LVLC,LVLI,LVSP can be processed similarly
    template = CBashJunk(8) #ditto

    def create_entry(self):
        length = _CGetFieldAttribute(self._RecordID, 9, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 9, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return self.Entry(self._RecordID, 9, length)
    entries = CBashLIST(9, Entry)
    entries_list = CBashLIST(9, Entry, True)

    IsCalcFromAllLevels = CBashBasicFlag(u'flags', 0x00000001)
    IsCalcForEachItem = CBashBasicFlag(u'flags', 0x00000002)
    IsUseAllSpells = CBashBasicFlag(u'flags', 0x00000004)
    exportattrs = copyattrs = ObBaseRecord.baseattrs + [u'chanceNone', u'flags', u'entries_list']

class ObLVSPRecord(ObBaseRecord):
    __slots__ = []
    _Type = b'LVSP'
    class Entry(ListComponent):
        __slots__ = []
        level = CBashGeneric_LIST(1, c_short)
        unused1 = CBashUINT8ARRAY_LIST(2, 2)
        listId = CBashFORMID_LIST(3)
        count = CBashGeneric_LIST(4, c_short)
        unused2 = CBashUINT8ARRAY_LIST(5, 2)
        exportattrs = copyattrs = [u'level', u'listId', u'count']

    def mergeFilter(self, target):
        """Filter out items that don't come from specified modSet."""
        self.entries = [entry for entry in self.entries if entry.listId.ValidateFormID(target)]

    chanceNone = CBashGeneric(5, c_ubyte)
    flags = CBashGeneric(6, c_ubyte)
    script = CBashJunk(7) #Doesn't actually exist, but is here so that LVLC,LVLI,LVSP can be processed similarly
    template = CBashJunk(8) #ditto

    def create_entry(self):
        length = _CGetFieldAttribute(self._RecordID, 9, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 9, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return self.Entry(self._RecordID, 9, length)
    entries = CBashLIST(9, Entry)
    entries_list = CBashLIST(9, Entry, True)

    IsCalcFromAllLevels = CBashBasicFlag(u'flags', 0x00000001)
    IsCalcForEachItem = CBashBasicFlag(u'flags', 0x00000002)
    IsUseAllSpells = CBashBasicFlag(u'flags', 0x00000004)
    exportattrs = copyattrs = ObBaseRecord.baseattrs + [u'chanceNone', u'flags', u'entries_list']

class ObMGEFRecord(ObBaseRecord):
    __slots__ = []
    _Type = b'MGEF'
    full = CBashSTRING(5)
    text = CBashSTRING(6)
    iconPath = CBashISTRING(7)
    modPath = CBashISTRING(8)
    modb = CBashFLOAT32(9)
    modt_p = CBashUINT8ARRAY(10)
    flags = CBashGeneric(11, c_ulong)
    baseCost = CBashFLOAT32(12)
    associated = CBashFORMID(13)
    schoolType = CBashGeneric(14, c_ulong)
    ##0xFFFFFFFF is None for resistValue
    resistValue = CBashGeneric(15, c_ulong)
    numCounters = CBashGeneric(16, c_ushort)
    unused1 = CBashUINT8ARRAY(17)
    light = CBashFORMID(18)
    projectileSpeed = CBashFLOAT32(19)
    effectShader = CBashFORMID(20)
    enchantEffect = CBashFORMID(21)
    castingSound = CBashFORMID(22)
    boltSound = CBashFORMID(23)
    hitSound = CBashFORMID(24)
    areaSound = CBashFORMID(25)
    cefEnchantment = CBashFLOAT32(26)
    cefBarter = CBashFLOAT32(27)
    counterEffects = CBashMGEFCODE_ARRAY(28)
    IsAlteration = CBashBasicType(u'schoolType', 0, u'IsConjuration')
    IsConjuration = CBashBasicType(u'schoolType', 1, u'IsAlteration')
    IsDestruction = CBashBasicType(u'schoolType', 2, u'IsAlteration')
    IsIllusion = CBashBasicType(u'schoolType', 3, u'IsAlteration')
    IsMysticism = CBashBasicType(u'schoolType', 4, u'IsAlteration')
    IsRestoration = CBashBasicType(u'schoolType', 5, u'IsAlteration')
    #Note: the vanilla code discards mod changes to most flag bits
    #  only those listed as changeable below may be edited by non-obme mods
    # comments garnered from JRoush's OBME
    IsHostile = CBashBasicFlag(u'flags', 0x00000001)
    IsRecover = CBashBasicFlag(u'flags', 0x00000002)
    IsDetrimental = CBashBasicFlag(u'flags', 0x00000004) #OBME Deprecated, used for ValueModifier effects AV is decreased rather than increased
    IsMagnitudeIsPercent = CBashBasicFlag(u'flags', 0x00000008) #OBME Deprecated
    IsSelf = CBashBasicFlag(u'flags', 0x00000010)
    IsTouch = CBashBasicFlag(u'flags', 0x00000020)
    IsTarget = CBashBasicFlag(u'flags', 0x00000040)
    IsNoDuration = CBashBasicFlag(u'flags', 0x00000080)
    IsNoMagnitude = CBashBasicFlag(u'flags', 0x00000100)
    IsNoArea = CBashBasicFlag(u'flags', 0x00000200)
    IsFXPersist = CBashBasicFlag(u'flags', 0x00000400) #Changeable
    IsSpellmaking = CBashBasicFlag(u'flags', 0x00000800) #Changeable
    IsEnchanting = CBashBasicFlag(u'flags', 0x00001000) #Changeable
    IsNoIngredient = CBashBasicFlag(u'flags', 0x00002000) #Changeable
    IsUnknownF = CBashBasicFlag(u'flags', 0x00004000) #no effects have this flag set
    IsNoRecast = CBashBasicFlag(u'flags', 0x00008000) #no effects have this flag set
    IsUseWeapon = CBashBasicFlag(u'flags', 0x00010000) #OBME Deprecated
    IsUseArmor = CBashBasicFlag(u'flags', 0x00020000) #OBME Deprecated
    IsUseCreature = CBashBasicFlag(u'flags', 0x00040000) #OBME Deprecated
    IsUseSkill = CBashBasicFlag(u'flags', 0x00080000) #OBME Deprecated
    IsUseAttr = CBashBasicFlag(u'flags', 0x00100000) #OBME Deprecated
    IsPCHasEffect = CBashBasicFlag(u'flags', 0x00200000) #whether or not PC has effect, forced to zero during loading
    IsDisabled = CBashBasicFlag(u'flags', 0x00400000) #Changeable, many if not all methods that loop over effects ignore those with this flag.
                                                    #  Spells with an effect with this flag are apparently uncastable.
    IsUnknownO = CBashBasicFlag(u'flags', 0x00800000) #Changeable, POSN,DISE - these effects have *only* this bit set,
                                                    #  perhaps a flag for meta effects
    IsUseAV = CBashBasicFlag(u'flags', 0x01000000) #OBME Deprecated, Changeable, but once set by default or by a previously loaded mod file
                                                    #  it cannot be unset by another mod, nor can the mgefParam be overriden

    IsBallType = CBashMaskedType(u'flags', 0x06000000, 0, u'IsBoltType')  #Changeable
    IsFogType = CBashMaskedType(u'flags', 0x06000000, 0x06000000, u'IsBallType')  #Changeable

    def get_IsSprayType(self):
        return self.flags is not None and not self.IsFogType and (self.flags & 0x02000000) != 0
    def set_IsSprayType(self, nValue):
        if nValue: self.flags = (self.flags & ~0x06000000) | 0x02000000
        elif self.IsSprayType: self.IsBallType = True
    IsSprayType = property(get_IsSprayType, set_IsSprayType)  #Changeable

    def get_IsBoltType(self):
        return self.flags is not None and not self.IsFogType and (self.flags & 0x04000000) != 0
    def set_IsBoltType(self, nValue):
        if nValue: self.flags = (self.flags & ~0x06000000) | 0x04000000
        elif self.IsBoltType: self.IsBallType = True
    IsBoltType = property(get_IsBoltType, set_IsBoltType)  #Changeable

    IsFogType = CBashBasicFlag(u'flags', 0x06000000) #Changeable
    IsNoHitEffect = CBashBasicFlag(u'flags', 0x08000000) #Changeable, no hit shader on target
    IsPersistOnDeath = CBashBasicFlag(u'flags', 0x10000000) #Effect is not automatically removed when its target dies
    IsExplodesWithForce = CBashBasicFlag(u'flags', 0x20000000) #causes explosion that can move loose objects (e.g. ragdolls)
    IsMagnitudeIsLevel = CBashBasicFlag(u'flags', 0x40000000) #OBME Deprecated
    IsMagnitudeIsFeet = CBashBasicFlag(u'flags', 0x80000000)  #OBME Deprecated
    ##OBME Fields. Setting any of the below fields will make the mod require JRoush's OBME plugin for OBSE
    ##To see if OBME is in use, check the recordVersion field for a non-None value
    recordVersion = CBashGeneric(29, c_ubyte) #OBME
    betaVersion = CBashGeneric(30, c_ubyte) #OBME
    minorVersion = CBashGeneric(31, c_ubyte) #OBME
    majorVersion = CBashGeneric(32, c_ubyte) #OBME
    mgefParamAInfo = CBashGeneric(33, c_ubyte) #OBME
    mgefParamBInfo = CBashGeneric(34, c_ubyte) #OBME
    reserved1 = CBashUINT8ARRAY(35, 0x2) #OBME
    handlerCode = CBashGeneric(36, c_ulong) #OBME
    OBMEFlags = CBashGeneric(37, c_ulong) #OBME
    mgefParamB = CBashGeneric(38, c_ulong) #OBME
    reserved2 = CBashUINT8ARRAY(39, 0x1C) #OBME
    mgefCode = CBashMGEFCODE(40) #OBME
    datx_p = CBashUINT8ARRAY(41, 0x20) #OBME
    IsBeneficial = CBashBasicFlag(u'OBMEFlags', 0x00000008) #OBME
    IsMagnitudeIsRange = CBashBasicFlag(u'OBMEFlags', 0x00020000) #OBME
    IsAtomicResistance = CBashBasicFlag(u'OBMEFlags', 0x00040000) #OBME
    IsParamFlagA = CBashBasicFlag(u'OBMEFlags', 0x00000004) #OBME #Meaning varies with effect handler
    IsParamFlagB = CBashBasicFlag(u'OBMEFlags', 0x00010000) #OBME #Meaning varies with effect handler
    IsParamFlagC = CBashBasicFlag(u'OBMEFlags', 0x00080000) #OBME #Meaning varies with effect handler
    IsParamFlagD = CBashBasicFlag(u'OBMEFlags', 0x00100000) #OBME #Meaning varies with effect handler
    IsHidden = CBashBasicFlag(u'OBMEFlags', 0x40000000) #OBME
    copyattrs = ObBaseRecord.baseattrs + [u'full', u'text', u'iconPath', u'modPath',
                                          u'modb', u'modt_p', u'flags', u'baseCost',
                                          u'associated', u'schoolType', u'resistValue',
                                          u'numCounters', u'light', u'projectileSpeed',
                                          u'effectShader', u'enchantEffect',
                                          u'castingSound', u'boltSound', u'hitSound',
                                          u'areaSound', u'cefEnchantment', u'cefBarter',
                                          u'counterEffects']
    exportattrs = copyattrs[:]
    exportattrs.remove(u'modt_p')
    copyattrsOBME = copyattrs + [u'recordVersion', u'betaVersion',
                                 u'minorVersion', u'majorVersion',
                                 u'mgefParamAInfo', u'mgefParamBInfo',
                                 u'reserved1', u'handlerCode', u'OBMEFlags',
                                 u'mgefParamB', u'reserved2', u'mgefCode', u'datx_p']
    exportattrsOBME = copyattrsOBME[:]
    exportattrsOBME.remove(u'modt_p')
    exportattrsOBME.remove(u'reserved1')
    exportattrsOBME.remove(u'reserved2')
    exportattrsOBME.remove(u'datx_p')

class ObMISCRecord(ObBaseRecord):
    __slots__ = []
    _Type = b'MISC'
    full = CBashSTRING(5)
    modPath = CBashISTRING(6)
    modb = CBashFLOAT32(7)
    modt_p = CBashUINT8ARRAY(8)
    iconPath = CBashISTRING(9)
    script = CBashFORMID(10)
    value = CBashGeneric(11, c_long)
    weight = CBashFLOAT32(12)
    copyattrs = ObBaseRecord.baseattrs + [u'full', u'modPath', u'modb', u'modt_p', u'iconPath',
                                          u'script', u'value', u'weight']
    exportattrs = copyattrs[:]
    exportattrs.remove(u'modt_p')

class ObNPC_Record(ObBaseRecord):
    __slots__ = []
    _Type = b'NPC_'
    def mergeFilter(self, target):
        """Filter out items that don't come from specified modSet.
        Filters spells, factions and items."""
        self.spells = [x for x in self.spells if x.ValidateFormID(target)]
        self.factions = [x for x in self.factions if x.faction.ValidateFormID(target)]
        self.items = [x for x in self.items if x.item.ValidateFormID(target)]

    full = CBashSTRING(5)
    modPath = CBashISTRING(6)
    modb = CBashFLOAT32(7)
    modt_p = CBashUINT8ARRAY(8)
    flags = CBashGeneric(9, c_ulong)
    baseSpell = CBashGeneric(10, c_ushort)
    fatigue = CBashGeneric(11, c_ushort)
    barterGold = CBashGeneric(12, c_ushort)
    level = CBashGeneric(13, c_short)
    calcMin = CBashGeneric(14, c_ushort)
    calcMax = CBashGeneric(15, c_ushort)

    def create_faction(self):
        length = _CGetFieldAttribute(self._RecordID, 16, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 16, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return Faction(self._RecordID, 16, length)
    factions = CBashLIST(16, Faction)
    factions_list = CBashLIST(16, Faction, True)

    deathItem = CBashFORMID(17)
    race = CBashFORMID(18)
    spells = CBashFORMIDARRAY(19)
    script = CBashFORMID(20)

    def create_item(self):
        length = _CGetFieldAttribute(self._RecordID, 21, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 21, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return Item(self._RecordID, 21, length)
    items = CBashLIST(21, Item)
    items_list = CBashLIST(21, Item, True)

    aggression = CBashGeneric(22, c_ubyte)
    confidence = CBashGeneric(23, c_ubyte)
    energyLevel = CBashGeneric(24, c_ubyte)
    responsibility = CBashGeneric(25, c_ubyte)
    services = CBashGeneric(26, c_ulong)
    trainSkill = CBashGeneric(27, c_byte)
    trainLevel = CBashGeneric(28, c_ubyte)
    unused1 = CBashUINT8ARRAY(29, 2)
    aiPackages = CBashFORMIDARRAY(30)
    animations = CBashISTRINGARRAY(31)
    iclass = CBashFORMID(32)
    armorer = CBashGeneric(33, c_ubyte)
    athletics = CBashGeneric(34, c_ubyte)
    blade = CBashGeneric(35, c_ubyte)
    block = CBashGeneric(36, c_ubyte)
    blunt = CBashGeneric(37, c_ubyte)
    h2h = CBashGeneric(38, c_ubyte)
    heavyArmor = CBashGeneric(39, c_ubyte)
    alchemy = CBashGeneric(40, c_ubyte)
    alteration = CBashGeneric(41, c_ubyte)
    conjuration = CBashGeneric(42, c_ubyte)
    destruction = CBashGeneric(43, c_ubyte)
    illusion = CBashGeneric(44, c_ubyte)
    mysticism = CBashGeneric(45, c_ubyte)
    restoration = CBashGeneric(46, c_ubyte)
    acrobatics = CBashGeneric(47, c_ubyte)
    lightArmor = CBashGeneric(48, c_ubyte)
    marksman = CBashGeneric(49, c_ubyte)
    mercantile = CBashGeneric(50, c_ubyte)
    security = CBashGeneric(51, c_ubyte)
    sneak = CBashGeneric(52, c_ubyte)
    speechcraft = CBashGeneric(53, c_ubyte)
    health = CBashGeneric(54, c_ushort)
    unused2 = CBashUINT8ARRAY(55, 2)
    strength = CBashGeneric(56, c_ubyte)
    intelligence = CBashGeneric(57, c_ubyte)
    willpower = CBashGeneric(58, c_ubyte)
    agility = CBashGeneric(59, c_ubyte)
    speed = CBashGeneric(60, c_ubyte)
    endurance = CBashGeneric(61, c_ubyte)
    personality = CBashGeneric(62, c_ubyte)
    luck = CBashGeneric(63, c_ubyte)
    hair = CBashFORMID(64)
    hairLength = CBashFLOAT32(65)
    eye = CBashFORMID(66)
    hairRed = CBashGeneric(67, c_ubyte)
    hairGreen = CBashGeneric(68, c_ubyte)
    hairBlue = CBashGeneric(69, c_ubyte)
    unused3 = CBashUINT8ARRAY(70, 1)
    combatStyle = CBashFORMID(71)
    fggs_p = CBashUINT8ARRAY(72, 200)
    fgga_p = CBashUINT8ARRAY(73, 120)
    fgts_p = CBashUINT8ARRAY(74, 200)
    fnam = CBashGeneric(75, c_ushort)
    IsFemale = CBashBasicFlag(u'flags', 0x00000001)
    IsMale = CBashInvertedFlag(u'IsFemale')
    IsEssential = CBashBasicFlag(u'flags', 0x00000002)
    IsRespawn = CBashBasicFlag(u'flags', 0x00000008)
    IsAutoCalc = CBashBasicFlag(u'flags', 0x00000010)
    IsPCLevelOffset = CBashBasicFlag(u'flags', 0x00000080)
    IsNoLowLevel = CBashBasicFlag(u'flags', 0x00000200)
    IsLowLevel = CBashInvertedFlag(u'IsNoLowLevel')
    IsNoRumors = CBashBasicFlag(u'flags', 0x00002000)
    IsRumors = CBashInvertedFlag(u'IsNoRumors')
    IsSummonable = CBashBasicFlag(u'flags', 0x00004000)
    IsNoPersuasion = CBashBasicFlag(u'flags', 0x00008000)
    IsPersuasion = CBashInvertedFlag(u'IsNoPersuasion')
    IsCanCorpseCheck = CBashBasicFlag(u'flags', 0x00100000)
    IsServicesWeapons = CBashBasicFlag(u'services', 0x00000001)
    IsServicesArmor = CBashBasicFlag(u'services', 0x00000002)
    IsServicesClothing = CBashBasicFlag(u'services', 0x00000004)
    IsServicesBooks = CBashBasicFlag(u'services', 0x00000008)
    IsServicesIngredients = CBashBasicFlag(u'services', 0x00000010)
    IsServicesLights = CBashBasicFlag(u'services', 0x00000080)
    IsServicesApparatus = CBashBasicFlag(u'services', 0x00000100)
    IsServicesMiscItems = CBashBasicFlag(u'services', 0x00000400)
    IsServicesSpells = CBashBasicFlag(u'services', 0x00000800)
    IsServicesMagicItems = CBashBasicFlag(u'services', 0x00001000)
    IsServicesPotions = CBashBasicFlag(u'services', 0x00002000)
    IsServicesTraining = CBashBasicFlag(u'services', 0x00004000)
    IsServicesRecharge = CBashBasicFlag(u'services', 0x00010000)
    IsServicesRepair = CBashBasicFlag(u'services', 0x00020000)
    copyattrs = ObBaseRecord.baseattrs + [
        u'full', u'modPath', u'modb', u'modt_p', u'flags', u'baseSpell',
        u'fatigue', u'barterGold', u'level', u'calcMin', u'calcMax',
        u'factions_list', u'deathItem', u'race', u'spells', u'script',
        u'items_list', u'aggression', u'confidence', u'energyLevel',
        u'responsibility', u'services', u'trainSkill', u'trainLevel',
        u'aiPackages', u'animations', u'iclass', u'armorer', u'athletics',
        u'blade', u'block', u'blunt', u'h2h', u'heavyArmor', u'alchemy',
        u'alteration', u'conjuration', u'destruction', u'illusion',
        u'mysticism', u'restoration', u'acrobatics', u'lightArmor',
        u'marksman', u'mercantile', u'security', u'sneak', u'speechcraft',
        u'health', u'strength', u'intelligence', u'willpower', u'agility',
        u'speed', u'endurance', u'personality', u'luck', u'hair',
        u'hairLength', u'eye', u'hairRed', u'hairGreen', u'hairBlue',
        u'combatStyle', u'fggs_p', u'fgga_p', u'fgts_p', u'fnam']
    exportattrs = copyattrs[:]
    exportattrs.remove(u'modt_p')
    exportattrs.remove(u'fggs_p')
    exportattrs.remove(u'fgga_p')
    exportattrs.remove(u'fgts_p')

class ObPACKRecord(ObBaseRecord):
    __slots__ = []
    _Type = b'PACK'
    flags = CBashGeneric(5, c_ulong)
    aiType = CBashGeneric(6, c_ubyte)
    unused1 = CBashUINT8ARRAY(7, 3)
    locType = CBashGeneric(8, c_long)
    locId = CBashFORMID_OR_UINT32(9)
    locRadius = CBashGeneric(10, c_long)
    month = CBashGeneric(11, c_byte)
    day = CBashGeneric(12, c_byte)
    date = CBashGeneric(13, c_ubyte)
    time = CBashGeneric(14, c_byte)
    duration = CBashGeneric(15, c_long)
    targetType = CBashGeneric(16, c_long)
    targetId = CBashFORMID_OR_UINT32(17)
    targetCount = CBashGeneric(18, c_long)

    def create_condition(self):
        length = _CGetFieldAttribute(self._RecordID, 19, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 19, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return Condition(self._RecordID, 19, length)
    conditions = CBashLIST(19, Condition)
    conditions_list = CBashLIST(19, Condition, True)

    IsOffersServices = CBashBasicFlag(u'flags', 0x00000001)
    IsMustReachLocation = CBashBasicFlag(u'flags', 0x00000002)
    IsMustComplete = CBashBasicFlag(u'flags', 0x00000004)
    IsLockAtStart = CBashBasicFlag(u'flags', 0x00000008)
    IsLockAtEnd = CBashBasicFlag(u'flags', 0x00000010)
    IsLockAtLocation = CBashBasicFlag(u'flags', 0x00000020)
    IsUnlockAtStart = CBashBasicFlag(u'flags', 0x00000040)
    IsUnlockAtEnd = CBashBasicFlag(u'flags', 0x00000080)
    IsUnlockAtLocation = CBashBasicFlag(u'flags', 0x00000100)
    IsContinueIfPcNear = CBashBasicFlag(u'flags', 0x00000200)
    IsOncePerDay = CBashBasicFlag(u'flags', 0x00000400)
    IsSkipFallout = CBashBasicFlag(u'flags', 0x00001000)
    IsAlwaysRun = CBashBasicFlag(u'flags', 0x00002000)
    IsAlwaysSneak = CBashBasicFlag(u'flags', 0x00020000)
    IsAllowSwimming = CBashBasicFlag(u'flags', 0x00040000)
    IsAllowFalls = CBashBasicFlag(u'flags', 0x00080000)
    IsUnequipArmor = CBashBasicFlag(u'flags', 0x00100000)
    IsUnequipWeapons = CBashBasicFlag(u'flags', 0x00200000)
    IsDefensiveCombat = CBashBasicFlag(u'flags', 0x00400000)
    IsUseHorse = CBashBasicFlag(u'flags', 0x00800000)
    IsNoIdleAnims = CBashBasicFlag(u'flags', 0x01000000)
    IsAIFind = CBashBasicType(u'aiType', 0, u'IsAIFollow')
    IsAIFollow = CBashBasicType(u'aiType', 1, u'IsAIFind')
    IsAIEscort = CBashBasicType(u'aiType', 2, u'IsAIFind')
    IsAIEat = CBashBasicType(u'aiType', 3, u'IsAIFind')
    IsAISleep = CBashBasicType(u'aiType', 4, u'IsAIFind')
    IsAIWander = CBashBasicType(u'aiType', 5, u'IsAIFind')
    IsAITravel = CBashBasicType(u'aiType', 6, u'IsAIFind')
    IsAIAccompany = CBashBasicType(u'aiType', 7, u'IsAIFind')
    IsAIUseItemAt = CBashBasicType(u'aiType', 8, u'IsAIFind')
    IsAIAmbush = CBashBasicType(u'aiType', 9, u'IsAIFind')
    IsAIFleeNotCombat = CBashBasicType(u'aiType', 10, u'IsAIFind')
    IsAICastMagic = CBashBasicType(u'aiType', 11, u'IsAIFind')
    IsLocNearReference = CBashBasicType(u'locType', 0, u'IsLocInCell')
    IsLocInCell = CBashBasicType(u'locType', 1, u'IsLocNearReference')
    IsLocNearCurrentLocation = CBashBasicType(u'locType', 2, u'IsLocNearReference')
    IsLocNearEditorLocation = CBashBasicType(u'locType', 3, u'IsLocNearReference')
    IsLocObjectID = CBashBasicType(u'locType', 4, u'IsLocNearReference')
    IsLocObjectType = CBashBasicType(u'locType', 5, u'IsLocNearReference')
    IsTargetReference = CBashBasicType(u'locType', 0, u'IsTargetObjectID')
    IsTargetObjectID = CBashBasicType(u'locType', 1, u'IsTargetReference')
    IsTargetObjectType = CBashBasicType(u'locType', 2, u'IsTargetReference')
    exportattrs = copyattrs = ObBaseRecord.baseattrs + [u'flags', u'aiType', u'locType', u'locId',
                                                        u'locRadius', u'month', u'day', u'date', u'time',
                                                        u'duration', u'targetType', u'targetId',
                                                        u'targetCount', u'conditions_list']

class ObQUSTRecord(ObBaseRecord):
    __slots__ = []
    _Type = b'QUST'
    def mergeFilter(self, target):
        """Filter out items that don't come from specified modSet.
        Filters items."""
        self.conditions = [x for x in self.conditions if (
            (not isinstance(x.param1,FormID) or x.param1.ValidateFormID(target))
            and
            (not isinstance(x.param2,FormID) or x.param2.ValidateFormID(target))
            )]
        #for target in self.targets_list:
        #    target.conditions = [x for x in target.conditions_list if (
        #        (not isinstance(x.param1,FormID) or x.param1.ValidateFormID(target))
        #        and
        #        (not isinstance(x.param2,FormID) or x.param2.ValidateFormID(target))
        #        )]

    class Stage(ListComponent):
        __slots__ = []
        class Entry(ListX2Component):
            __slots__ = []
            class ConditionX3(ListX3Component):
                __slots__ = []
                operType = CBashGeneric_LISTX3(1, c_ubyte)
                unused1 = CBashUINT8ARRAY_LISTX3(2, 3)
                compValue = CBashFLOAT32_LISTX3(3)
                ifunc = CBashGeneric_LISTX3(4, c_ulong)
                param1 = CBashUNKNOWN_OR_FORMID_OR_UINT32_LISTX3(5)
                param2 = CBashUNKNOWN_OR_FORMID_OR_UINT32_LISTX3(6)
                unused2 = CBashUINT8ARRAY_LISTX3(7, 4)
                IsEqual = CBashMaskedType(u'operType', 0xF0, 0x00, u'IsNotEqual')
                IsNotEqual = CBashMaskedType(u'operType', 0xF0, 0x20, u'IsEqual')
                IsGreater = CBashMaskedType(u'operType', 0xF0, 0x40, u'IsEqual')
                IsGreaterOrEqual = CBashMaskedType(u'operType', 0xF0, 0x60, u'IsEqual')
                IsLess = CBashMaskedType(u'operType', 0xF0, 0x80, u'IsEqual')
                IsLessOrEqual = CBashMaskedType(u'operType', 0xF0, 0xA0, u'IsEqual')
                IsOr = CBashBasicFlag(u'operType', 0x01)
                IsRunOnTarget = CBashBasicFlag(u'operType', 0x02)
                IsUseGlobal = CBashBasicFlag(u'operType', 0x04)
                exportattrs = copyattrs = [u'operType', u'compValue', u'ifunc',
                                           u'param1', u'param2']

            flags = CBashGeneric_LISTX2(1, c_ubyte)

            def create_condition(self):
                length = _CGetFieldAttribute(self._RecordID, self._FieldID, self._ListIndex, self._ListFieldID, self._ListX2Index, 2, 0, 0, 1)
                _CSetField(self._RecordID, self._FieldID, self._ListIndex, self._ListFieldID, self._ListX2Index, 2, 0, 0, 0, c_ulong(length + 1))
                return self.ConditionX3(self._RecordID, self._FieldID, self._ListIndex, self._ListFieldID, self._ListX2Index, 2, length)
            conditions = CBashLIST_LISTX2(2, ConditionX3)
            conditions_list = CBashLIST_LISTX2(2, ConditionX3, True)

            text = CBashSTRING_LISTX2(3)
            unused1 = CBashUINT8ARRAY_LISTX2(4, 4)
            numRefs = CBashGeneric_LISTX2(5, c_ulong)
            compiledSize = CBashGeneric_LISTX2(6, c_ulong)
            lastIndex = CBashGeneric_LISTX2(7, c_ulong)
            scriptType = CBashGeneric_LISTX2(8, c_ulong)
            compiled_p = CBashUINT8ARRAY_LISTX2(9)
            scriptText = CBashISTRING_LISTX2(10)
            references = CBashFORMID_OR_UINT32_ARRAY_LISTX2(11)
            IsCompletes = CBashBasicFlag(u'flags', 0x00000001)
            IsObject = CBashBasicType(u'scriptType', 0x00000000, u'IsQuest')
            IsQuest = CBashBasicType(u'scriptType', 0x00000001, u'IsObject')
            IsMagicEffect = CBashBasicType(u'scriptType', 0x00000100, u'IsObject')
            copyattrs = [u'flags', u'conditions_list', u'text', u'numRefs', u'compiledSize',
                         u'lastIndex', u'scriptType', u'compiled_p', u'scriptText',
                         u'references']
            exportattrs = copyattrs[:]
            exportattrs.remove(u'compiled_p')

        stage = CBashGeneric_LIST(1, c_ushort)

        def create_entry(self):
            length = _CGetFieldAttribute(self._RecordID, self._FieldID, self._ListIndex, 2, 0, 0, 0, 0, 1)
            _CSetField(self._RecordID, self._FieldID, self._ListIndex, 2, 0, 0, 0, 0, 0, c_ulong(length + 1))
            return self.Entry(self._RecordID, self._FieldID, self._ListIndex, 2, length)
        entries = CBashLIST_LIST(2, Entry)
        entries_list = CBashLIST_LIST(2, Entry, True)

        exportattrs = copyattrs = [u'stage', u'entries_list']

    class Target(ListComponent):
        __slots__ = []
        class ConditionX2(ListX2Component):
            __slots__ = []
            operType = CBashGeneric_LISTX2(1, c_ubyte)
            unused1 = CBashUINT8ARRAY_LISTX2(2, 3)
            compValue = CBashFLOAT32_LISTX2(3)
            ifunc = CBashGeneric_LISTX2(4, c_ulong)
            param1 = CBashUNKNOWN_OR_FORMID_OR_UINT32_LISTX2(5)
            param2 = CBashUNKNOWN_OR_FORMID_OR_UINT32_LISTX2(6)
            unused2 = CBashUINT8ARRAY_LISTX2(7, 4)
            IsEqual = CBashMaskedType(u'operType', 0xF0, 0x00, u'IsNotEqual')
            IsNotEqual = CBashMaskedType(u'operType', 0xF0, 0x20, u'IsEqual')
            IsGreater = CBashMaskedType(u'operType', 0xF0, 0x40, u'IsEqual')
            IsGreaterOrEqual = CBashMaskedType(u'operType', 0xF0, 0x60, u'IsEqual')
            IsLess = CBashMaskedType(u'operType', 0xF0, 0x80, u'IsEqual')
            IsLessOrEqual = CBashMaskedType(u'operType', 0xF0, 0xA0, u'IsEqual')
            IsOr = CBashBasicFlag(u'operType', 0x01)
            IsRunOnTarget = CBashBasicFlag(u'operType', 0x02)
            IsUseGlobal = CBashBasicFlag(u'operType', 0x04)
            exportattrs = copyattrs = [u'operType', u'compValue', u'ifunc',
                                       u'param1', u'param2']

        targetId = CBashFORMID_LIST(1)
        flags = CBashGeneric_LIST(2, c_ubyte)
        unused1 = CBashUINT8ARRAY_LIST(3, 3)

        def create_condition(self):
            length = _CGetFieldAttribute(self._RecordID, self._FieldID, self._ListIndex, 4, 0, 0, 0, 0, 1)
            _CSetField(self._RecordID, self._FieldID, self._ListIndex, 4, 0, 0, 0, 0, 0, c_ulong(length + 1))
            return self.ConditionX2(self._RecordID, self._FieldID, self._ListIndex, 4, length)
        conditions = CBashLIST_LIST(4, ConditionX2)
        conditions_list = CBashLIST_LIST(4, ConditionX2, True)

        IsIgnoresLocks = CBashBasicFlag(u'flags', 0x00000001)
        exportattrs = copyattrs = [u'targetId', u'flags', u'conditions_list']

    script = CBashFORMID(5)
    full = CBashSTRING(6)
    iconPath = CBashISTRING(7)
    flags = CBashGeneric(8, c_ubyte)
    priority = CBashGeneric(9, c_ubyte)

    def create_condition(self):
        length = _CGetFieldAttribute(self._RecordID, 10, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 10, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return Condition(self._RecordID, 10, length)
    conditions = CBashLIST(10, Condition)
    conditions_list = CBashLIST(10, Condition, True)

    def create_stage(self):
        length = _CGetFieldAttribute(self._RecordID, 11, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 11, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return self.Stage(self._RecordID, 11, length)
    stages = CBashLIST(11, Stage)
    stages_list = CBashLIST(11, Stage, True)

    def create_target(self):
        length = _CGetFieldAttribute(self._RecordID, 12, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 12, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return self.Target(self._RecordID, 12, length)
    targets = CBashLIST(12, Target)
    targets_list = CBashLIST(12, Target, True)

    IsStartEnabled = CBashBasicFlag(u'flags', 0x00000001)
    IsRepeatedTopics = CBashBasicFlag(u'flags', 0x00000004)
    IsRepeatedStages = CBashBasicFlag(u'flags', 0x00000008)
    exportattrs = copyattrs = ObBaseRecord.baseattrs + [u'script', u'full', u'iconPath',
                                                        u'flags', u'priority', u'conditions_list',
                                                        u'stages_list', u'targets_list']

class ObRACERecord(ObBaseRecord):
    __slots__ = []
    _Type = b'RACE'
    class RaceModel(BaseComponent):
        __slots__ = []
        modPath = CBashISTRING_GROUP(0)
        modb = CBashFLOAT32_GROUP(1)
        iconPath = CBashISTRING_GROUP(2)
        modt_p = CBashUINT8ARRAY_GROUP(3)
        copyattrs = [u'modPath', u'modb', u'iconPath', u'modt_p']
        exportattrs = copyattrs[:]
        exportattrs.remove(u'modt_p')

    full = CBashSTRING(5)
    text = CBashSTRING(6)
    spells = CBashFORMIDARRAY(7)

    def create_relation(self):
        length = _CGetFieldAttribute(self._RecordID, 8, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 8, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return Relation(self._RecordID, 8, length)
    relations = CBashLIST(8, Relation)
    relations_list = CBashLIST(8, Relation, True)

    skill1 = CBashGeneric(9, c_byte)
    skill1Boost = CBashGeneric(10, c_byte)
    skill2 = CBashGeneric(11, c_byte)
    skill2Boost = CBashGeneric(12, c_byte)
    skill3 = CBashGeneric(13, c_byte)
    skill3Boost = CBashGeneric(14, c_byte)
    skill4 = CBashGeneric(15, c_byte)
    skill4Boost = CBashGeneric(16, c_byte)
    skill5 = CBashGeneric(17, c_byte)
    skill5Boost = CBashGeneric(18, c_byte)
    skill6 = CBashGeneric(19, c_byte)
    skill6Boost = CBashGeneric(20, c_byte)
    skill7 = CBashGeneric(21, c_byte)
    skill7Boost = CBashGeneric(22, c_byte)
    unused1 = CBashUINT8ARRAY(23, 2)
    maleHeight = CBashFLOAT32(24)
    femaleHeight = CBashFLOAT32(25)
    maleWeight = CBashFLOAT32(26)
    femaleWeight = CBashFLOAT32(27)
    flags = CBashGeneric(28, c_ulong)
    maleVoice = CBashFORMID(29)
    femaleVoice = CBashFORMID(30)
    defaultHairMale = CBashFORMID(31)
    defaultHairFemale = CBashFORMID(32)
    defaultHairColor = CBashGeneric(33, c_ubyte)
    mainClamp = CBashFLOAT32(34)
    faceClamp = CBashFLOAT32(35)
    maleStrength = CBashGeneric(36, c_ubyte)
    maleIntelligence = CBashGeneric(37, c_ubyte)
    maleWillpower = CBashGeneric(38, c_ubyte)
    maleAgility = CBashGeneric(39, c_ubyte)
    maleSpeed = CBashGeneric(40, c_ubyte)
    maleEndurance = CBashGeneric(41, c_ubyte)
    malePersonality = CBashGeneric(42, c_ubyte)
    maleLuck = CBashGeneric(43, c_ubyte)
    femaleStrength = CBashGeneric(44, c_ubyte)
    femaleIntelligence = CBashGeneric(45, c_ubyte)
    femaleWillpower = CBashGeneric(46, c_ubyte)
    femaleAgility = CBashGeneric(47, c_ubyte)
    femaleSpeed = CBashGeneric(48, c_ubyte)
    femaleEndurance = CBashGeneric(49, c_ubyte)
    femalePersonality = CBashGeneric(50, c_ubyte)
    femaleLuck = CBashGeneric(51, c_ubyte)
    head = CBashGrouped(52, RaceModel)
    head_list = CBashGrouped(52, RaceModel, True)

    maleEars = CBashGrouped(56, RaceModel)
    maleEars_list = CBashGrouped(56, RaceModel, True)

    femaleEars = CBashGrouped(60, RaceModel)
    femaleEars_list = CBashGrouped(60, RaceModel, True)

    mouth = CBashGrouped(64, RaceModel)
    mouth_list = CBashGrouped(64, RaceModel, True)

    teethLower = CBashGrouped(68, RaceModel)
    teethLower_list = CBashGrouped(68, RaceModel, True)

    teethUpper = CBashGrouped(72, RaceModel)
    teethUpper_list = CBashGrouped(72, RaceModel, True)

    tongue = CBashGrouped(76, RaceModel)
    tongue_list = CBashGrouped(76, RaceModel, True)

    leftEye = CBashGrouped(80, RaceModel)
    leftEye_list = CBashGrouped(80, RaceModel, True)

    rightEye = CBashGrouped(84, RaceModel)
    rightEye_list = CBashGrouped(84, RaceModel, True)

    maleTail = CBashGrouped(88, Model)
    maleTail_list = CBashGrouped(88, Model, True)

    maleUpperBodyPath = CBashISTRING(91)
    maleLowerBodyPath = CBashISTRING(92)
    maleHandPath = CBashISTRING(93)
    maleFootPath = CBashISTRING(94)
    maleTailPath = CBashISTRING(95)
    femaleTail = CBashGrouped(96, Model)
    femaleTail_list = CBashGrouped(96, Model, True)

    femaleUpperBodyPath = CBashISTRING(99)
    femaleLowerBodyPath = CBashISTRING(100)
    femaleHandPath = CBashISTRING(101)
    femaleFootPath = CBashISTRING(102)
    femaleTailPath = CBashISTRING(103)
    hairs = CBashFORMIDARRAY(104)
    eyes = CBashFORMIDARRAY(105)
    fggs_p = CBashUINT8ARRAY(106, 200)
    fgga_p = CBashUINT8ARRAY(107, 120)
    fgts_p = CBashUINT8ARRAY(108, 200)
    snam_p = CBashUINT8ARRAY(109, 2)
    IsPlayable = CBashBasicFlag(u'flags', 0x00000001)
    copyattrs = ObBaseRecord.baseattrs + [
        u'full', u'text', u'spells', u'relations_list', u'skill1',
        u'skill1Boost', u'skill2', u'skill2Boost', u'skill3', u'skill3Boost',
        u'skill4', u'skill4Boost', u'skill5', u'skill5Boost', u'skill6',
        u'skill6Boost', u'skill7', u'skill7Boost', u'maleHeight',
        u'femaleHeight', u'maleWeight', u'femaleWeight', u'flags',
        u'maleVoice', u'femaleVoice', u'defaultHairMale', u'defaultHairFemale',
        u'defaultHairColor', u'mainClamp', u'faceClamp', u'maleStrength',
        u'maleIntelligence', u'maleAgility', u'maleSpeed', u'maleEndurance',
        u'malePersonality', u'maleLuck', u'femaleStrength',
        u'femaleIntelligence', u'femaleWillpower', u'femaleAgility',
        u'femaleSpeed', u'femaleEndurance', u'femalePersonality',
        u'femaleLuck', u'head_list', u'maleEars_list', u'femaleEars_list',
        u'mouth_list', u'teethLower_list', u'teethUpper_list', u'tongue_list',
        u'leftEye_list', u'rightEye_list', u'maleTail_list',
        u'maleUpperBodyPath', u'maleLowerBodyPath', u'maleHandPath',
        u'maleFootPath', u'maleTailPath', u'femaleTail_list',
        u'femaleUpperBodyPath', u'femaleLowerBodyPath', u'femaleHandPath',
        u'femaleFootPath', u'femaleTailPath', u'hairs', u'eyes', u'fggs_p',
        u'fgga_p', u'fgts_p', u'snam_p']
    exportattrs = copyattrs[:]
    exportattrs.remove(u'fggs_p')
    exportattrs.remove(u'fgga_p')
    exportattrs.remove(u'fgts_p')
    exportattrs.remove(u'snam_p')

class ObREGNRecord(ObBaseRecord):
    __slots__ = []
    _Type = b'REGN'
    class Area(ListComponent):
        __slots__ = []
        class Point(ListX2Component):
            __slots__ = []
            posX = CBashFLOAT32_LISTX2(1)
            posY = CBashFLOAT32_LISTX2(2)
            exportattrs = copyattrs = [u'posX', u'posY']

        edgeFalloff = CBashGeneric_LIST(1, c_ulong)

        def create_point(self):
            length = _CGetFieldAttribute(self._RecordID, self._FieldID, self._ListIndex, 2, 0, 0, 0, 0, 1)
            _CSetField(self._RecordID, self._FieldID, self._ListIndex, 2, 0, 0, 0, 0, 0, c_ulong(length + 1))
            return self.Point(self._RecordID, self._FieldID, self._ListIndex, 2, length)
        points = CBashLIST_LIST(2, Point)
        points_list = CBashLIST_LIST(2, Point, True)

        exportattrs = copyattrs = [u'edgeFalloff', u'points_list']

    class Entry(ListComponent):
        __slots__ = []
        class Object(ListX2Component):
            __slots__ = []
            objectId = CBashFORMID_LISTX2(1)
            parentIndex = CBashGeneric_LISTX2(2, c_ushort)
            unused1 = CBashUINT8ARRAY_LISTX2(3, 2)
            density = CBashFLOAT32_LISTX2(4)
            clustering = CBashGeneric_LISTX2(5, c_ubyte)
            minSlope = CBashGeneric_LISTX2(6, c_ubyte)
            maxSlope = CBashGeneric_LISTX2(7, c_ubyte)
            flags = CBashGeneric_LISTX2(8, c_ubyte)
            radiusWRTParent = CBashGeneric_LISTX2(9, c_ushort)
            radius = CBashGeneric_LISTX2(10, c_ushort)
            unk1 = CBashUINT8ARRAY_LISTX2(11, 4)
            maxHeight = CBashFLOAT32_LISTX2(12)
            sink = CBashFLOAT32_LISTX2(13)
            sinkVar = CBashFLOAT32_LISTX2(14)
            sizeVar = CBashFLOAT32_LISTX2(15)
            angleVarX = CBashGeneric_LISTX2(16, c_ushort)
            angleVarY = CBashGeneric_LISTX2(17, c_ushort)
            angleVarZ = CBashGeneric_LISTX2(18, c_ushort)
            unused2 = CBashUINT8ARRAY_LISTX2(19, 1)
            unk2 = CBashUINT8ARRAY_LISTX2(20, 4)
            IsConformToSlope = CBashBasicFlag(u'flags', 0x00000001)
            IsPaintVertices = CBashBasicFlag(u'flags', 0x00000002)
            IsSizeVariance = CBashBasicFlag(u'flags', 0x00000004)
            IsXVariance = CBashBasicFlag(u'flags', 0x00000008)
            IsYVariance = CBashBasicFlag(u'flags', 0x00000010)
            IsZVariance = CBashBasicFlag(u'flags', 0x00000020)
            IsTree = CBashBasicFlag(u'flags', 0x00000040)
            IsHugeRock = CBashBasicFlag(u'flags', 0x00000080)
            copyattrs = [u'objectId', u'parentIndex', u'density', u'clustering',
                         u'minSlope', u'maxSlope', u'flags', u'radiusWRTParent',
                         u'radius', u'unk1', u'maxHeight', u'sink', u'sinkVar',
                         u'sizeVar', u'angleVarX', u'angleVarY', u'angleVarZ',
                         u'unk2']
            exportattrs = copyattrs[:]
            exportattrs.remove(u'unk1')
            exportattrs.remove(u'unk2')

        class Grass(ListX2Component):
            __slots__ = []
            grass = CBashFORMID_LISTX2(1)
            unk1 = CBashUINT8ARRAY_LISTX2(2, 4)
            copyattrs = [u'grass', u'unk1']
            exportattrs = copyattrs[:]
            exportattrs.remove(u'unk1')

        class Sound(ListX2Component):
            __slots__ = []
            sound = CBashFORMID_LISTX2(1)
            flags = CBashGeneric_LISTX2(2, c_ulong)
            chance = CBashGeneric_LISTX2(3, c_ulong)
            IsPleasant = CBashBasicFlag(u'flags', 0x00000001)
            IsCloudy = CBashBasicFlag(u'flags', 0x00000002)
            IsRainy = CBashBasicFlag(u'flags', 0x00000004)
            IsSnowy = CBashBasicFlag(u'flags', 0x00000008)
            exportattrs = copyattrs = [u'sound', u'flags', u'chance']

        class Weather(ListX2Component):
            __slots__ = []
            weather = CBashFORMID_LISTX2(1)
            chance = CBashGeneric_LISTX2(2, c_ulong)
            exportattrs = copyattrs = [u'weather', u'chance']

        entryType = CBashGeneric_LIST(1, c_ulong)
        flags = CBashGeneric_LIST(2, c_ubyte)
        priority = CBashGeneric_LIST(3, c_ubyte)
        unused1 = CBashUINT8ARRAY_LIST(4, 4)

        def create_object(self):
            length = _CGetFieldAttribute(self._RecordID, self._FieldID, self._ListIndex, 5, 0, 0, 0, 0, 1)
            _CSetField(self._RecordID, self._FieldID, self._ListIndex, 5, 0, 0, 0, 0, 0, c_ulong(length + 1))
            return self.Object(self._RecordID, self._FieldID, self._ListIndex, 5, length)
        objects = CBashLIST_LIST(5, Object)
        objects_list = CBashLIST_LIST(5, Object, True)

        mapName = CBashSTRING_LIST(6)
        iconPath = CBashISTRING_LIST(7)

        def create_grass(self):
            length = _CGetFieldAttribute(self._RecordID, self._FieldID, self._ListIndex, 8, 0, 0, 0, 0, 1)
            _CSetField(self._RecordID, self._FieldID, self._ListIndex, 8, 0, 0, 0, 0, 0, c_ulong(length + 1))
            return self.Grass(self._RecordID, self._FieldID, self._ListIndex, 8, length)
        grasses = CBashLIST_LIST(8, Grass)
        grasses_list = CBashLIST_LIST(8, Grass, True)

        musicType = CBashGeneric_LIST(9, c_ulong)

        def create_sound(self):
            length = _CGetFieldAttribute(self._RecordID, self._FieldID, self._ListIndex, 10, 0, 0, 0, 0, 1)
            _CSetField(self._RecordID, self._FieldID, self._ListIndex, 10, 0, 0, 0, 0, 0, c_ulong(length + 1))
            return self.Sound(self._RecordID, self._FieldID, self._ListIndex, 10, length)
        sounds = CBashLIST_LIST(10, Sound)
        sounds_list = CBashLIST_LIST(10, Sound, True)

        def create_weather(self):
            length = _CGetFieldAttribute(self._RecordID, self._FieldID, self._ListIndex, 11, 0, 0, 0, 0, 1)
            _CSetField(self._RecordID, self._FieldID, self._ListIndex, 11, 0, 0, 0, 0, 0, c_ulong(length + 1))
            return self.Weather(self._RecordID, self._FieldID, self._ListIndex, 11, length)
        weathers = CBashLIST_LIST(11, Weather)
        weathers_list = CBashLIST_LIST(11, Weather, True)

        IsObject = CBashBasicType(u'entryType', 2, u'IsWeather')
        IsWeather = CBashBasicType(u'entryType', 3, u'IsObject')
        IsMap = CBashBasicType(u'entryType', 4, u'IsObject')
        IsIcon = CBashBasicType(u'entryType', 5, u'IsObject')
        IsGrass = CBashBasicType(u'entryType', 6, u'IsObject')
        IsSound = CBashBasicType(u'entryType', 7, u'IsObject')
        IsDefault = CBashBasicType(u'musicType', 0, u'IsPublic')
        IsPublic = CBashBasicType(u'musicType', 1, u'IsDefault')
        IsDungeon = CBashBasicType(u'musicType', 2, u'IsDefault')
        IsOverride = CBashBasicFlag(u'flags', 0x00000001)
        exportattrs = copyattrs = [u'entryType', u'flags', u'priority', u'objects_list', u'mapName',
                                   u'iconPath', u'grasses_list', u'musicType', u'sounds_list', u'weathers_list']

    iconPath = CBashISTRING(5)
    mapRed = CBashGeneric(6, c_ubyte)
    mapGreen = CBashGeneric(7, c_ubyte)
    mapBlue = CBashGeneric(8, c_ubyte)
    unused1 = CBashUINT8ARRAY(9, 1)
    worldspace = CBashFORMID(10)

    def create_area(self):
        length = _CGetFieldAttribute(self._RecordID, 11, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 11, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return self.Area(self._RecordID, 11, length)
    areas = CBashLIST(11, Area)
    areas_list = CBashLIST(11, Area, True)

    def create_entry(self):
        length = _CGetFieldAttribute(self._RecordID, 12, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 12, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return self.Entry(self._RecordID, 12, length)
    entries = CBashLIST(12, Entry)
    entries_list = CBashLIST(12, Entry, True)

    exportattrs = copyattrs = ObBaseRecord.baseattrs + [u'iconPath', u'mapRed', u'mapGreen',
                                                        u'mapBlue', u'worldspace', u'areas_list',
                                                        u'entries_list']

class ObSBSPRecord(ObBaseRecord):
    __slots__ = []
    _Type = b'SBSP'
    sizeX = CBashFLOAT32(5)
    sizeY = CBashFLOAT32(6)
    sizeZ = CBashFLOAT32(7)
    exportattrs = copyattrs = ObBaseRecord.baseattrs + [u'sizeX', u'sizeY', u'sizeZ']

class ObSCPTRecord(ObBaseRecord):
    __slots__ = []
    _Type = b'SCPT'
    unused1 = CBashUINT8ARRAY(5, 2)
    numRefs = CBashGeneric(6, c_ulong)
    compiledSize = CBashGeneric(7, c_ulong)
    lastIndex = CBashGeneric(8, c_ulong)
    scriptType = CBashGeneric(9, c_ulong)
    compiled_p = CBashUINT8ARRAY(10)
    scriptText = CBashISTRING(11)

    def create_var(self):
        length = _CGetFieldAttribute(self._RecordID, 12, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 12, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return Var(self._RecordID, 12, length)
    vars = CBashLIST(12, Var)
    vars_list = CBashLIST(12, Var, True)

    references = CBashFORMID_OR_UINT32_ARRAY(13)

    IsObject = CBashBasicType(u'scriptType', 0x00000000, u'IsQuest')
    IsQuest = CBashBasicType(u'scriptType', 0x00000001, u'IsObject')
    IsMagicEffect = CBashBasicType(u'scriptType', 0x00000100, u'IsObject')
    copyattrs = ObBaseRecord.baseattrs + [u'numRefs', u'compiledSize', u'lastIndex',
                                          u'scriptType', u'compiled_p', u'scriptText',
                                          u'vars_list', u'references']
    exportattrs = copyattrs[:]
    exportattrs.remove(u'compiled_p')

class ObSGSTRecord(ObBaseRecord):
    __slots__ = []
    _Type = b'SGST'
    full = CBashSTRING(5)
    modPath = CBashISTRING(6)
    modb = CBashFLOAT32(7)
    modt_p = CBashUINT8ARRAY(8)
    iconPath = CBashISTRING(9)
    script = CBashFORMID(10)

    def create_effect(self):
        length = _CGetFieldAttribute(self._RecordID, 11, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 11, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return Effect(self._RecordID, 11, length)
    effects = CBashLIST(11, Effect)
    effects_list = CBashLIST(11, Effect, True)

    uses = CBashGeneric(12, c_ubyte)
    value = CBashGeneric(13, c_long)
    weight = CBashFLOAT32(14)
    ##OBME Fields. Setting any of the below fields will make the mod require JRoush's OBME plugin for OBSE
    ##To see if OBME is in use, check the recordVersion field for a non-None value
    recordVersion = CBashGeneric(15, c_ubyte)
    betaVersion = CBashGeneric(16, c_ubyte)
    minorVersion = CBashGeneric(17, c_ubyte)
    majorVersion = CBashGeneric(18, c_ubyte)
    reserved = CBashUINT8ARRAY(19, 0x1C)
    datx_p = CBashUINT8ARRAY(20, 0x20)
    copyattrs = ObBaseRecord.baseattrs + [u'full', u'modPath', u'modb', u'modt_p',
                                          u'iconPath', u'script', u'effects_list',
                                          u'uses', u'value', u'weight']
    exportattrs = copyattrs[:]
    exportattrs.remove(u'modt_p')
    copyattrsOBME = copyattrs + [u'recordVersion', u'betaVersion',
                                 u'minorVersion', u'majorVersion',
                                 u'reserved', u'datx_p']
    exportattrsOBME = copyattrsOBME[:]
    exportattrsOBME.remove(u'modt_p')
    exportattrsOBME.remove(u'reserved')
    exportattrsOBME.remove(u'datx_p')

class ObSKILRecord(ObBaseRecord):
    __slots__ = []
    _Type = b'SKIL'
    skill = CBashGeneric(5, c_long)
    description = CBashSTRING(6)
    iconPath = CBashISTRING(7)
    action = CBashGeneric(8, c_long)
    attribute = CBashGeneric(9, c_long)
    specialization = CBashGeneric(10, c_ulong)
    use0 = CBashFLOAT32(11)
    use1 = CBashFLOAT32(12)
    apprentice = CBashSTRING(13)
    journeyman = CBashSTRING(14)
    expert = CBashSTRING(15)
    master = CBashSTRING(16)
    exportattrs = copyattrs = ObBaseRecord.baseattrs + [u'skill', u'description', u'iconPath',
                                                        u'action', u'attribute', u'specialization',
                                                        u'use0', u'use1', u'apprentice',
                                                        u'journeyman', u'expert', u'master']

class ObSLGMRecord(ObBaseRecord):
    __slots__ = []
    _Type = b'SLGM'
    full = CBashSTRING(5)
    modPath = CBashISTRING(6)
    modb = CBashFLOAT32(7)
    modt_p = CBashUINT8ARRAY(8)
    iconPath = CBashISTRING(9)
    script = CBashFORMID(10)
    value = CBashGeneric(11, c_long)
    weight = CBashFLOAT32(12)
    soulType = CBashGeneric(13, c_ubyte)
    capacityType = CBashGeneric(14, c_ubyte)
    IsNoSoul = CBashBasicType(u'soulType', 0, u'IsPettySoul')
    IsPettySoul = CBashBasicType(u'soulType', 1, u'IsNoSoul')
    IsLesserSoul = CBashBasicType(u'soulType', 2, u'IsNoSoul')
    IsCommonSoul = CBashBasicType(u'soulType', 3, u'IsNoSoul')
    IsGreaterSoul = CBashBasicType(u'soulType', 4, u'IsNoSoul')
    IsGrandSoul = CBashBasicType(u'soulType', 5, u'IsNoSoul')
    IsNoCapacity = CBashBasicType(u'capacityType', 0, u'IsPettyCapacity')
    IsPettyCapacity = CBashBasicType(u'capacityType', 1, u'IsNoCapacity')
    IsLesserCapacity = CBashBasicType(u'capacityType', 2, u'IsNoCapacity')
    IsCommonCapacity = CBashBasicType(u'capacityType', 3, u'IsNoCapacity')
    IsGreaterCapacity = CBashBasicType(u'capacityType', 4, u'IsNoCapacity')
    IsGrandCapacity = CBashBasicType(u'capacityType', 5, u'IsNoCapacity')
    copyattrs = ObBaseRecord.baseattrs + [u'full', u'modPath', u'modb', u'modt_p',
                                          u'iconPath', u'script', u'value',
                                          u'weight', u'soulType', u'capacityType']
    exportattrs = copyattrs[:]
    exportattrs.remove(u'modt_p')

class ObSOUNRecord(ObBaseRecord):
    __slots__ = []
    _Type = b'SOUN'
    soundPath = CBashISTRING(5)
    minDistance = CBashGeneric(6, c_ubyte)
    maxDistance = CBashGeneric(7, c_ubyte)
    freqAdjustment = CBashGeneric(8, c_byte)
    unused1 = CBashUINT8ARRAY(9, 1)
    flags = CBashGeneric(10, c_ushort)
    unused2 = CBashUINT8ARRAY(11, 2)
    staticAtten = CBashGeneric(12, c_short)
    stopTime = CBashGeneric(13, c_ubyte)
    startTime = CBashGeneric(14, c_ubyte)
    IsRandomFrequencyShift = CBashBasicFlag(u'flags', 0x00000001)
    IsPlayAtRandom = CBashBasicFlag(u'flags', 0x00000002)
    IsEnvironmentIgnored = CBashBasicFlag(u'flags', 0x00000004)
    IsRandomLocation = CBashBasicFlag(u'flags', 0x00000008)
    IsLoop = CBashBasicFlag(u'flags', 0x00000010)
    IsMenuSound = CBashBasicFlag(u'flags', 0x00000020)
    Is2D = CBashBasicFlag(u'flags', 0x00000040)
    Is360LFE = CBashBasicFlag(u'flags', 0x00000080)
    exportattrs = copyattrs = ObBaseRecord.baseattrs + [u'soundPath', u'minDistance', u'maxDistance',
                                                        u'freqAdjustment', u'flags', u'staticAtten',
                                                        u'stopTime', u'startTime']

class ObSPELRecord(ObBaseRecord):
    __slots__ = []
    _Type = b'SPEL'
    full = CBashSTRING(5)
    spellType = CBashGeneric(6, c_ulong)
    cost = CBashGeneric(7, c_ulong)
    levelType = CBashGeneric(8, c_ulong)
    flags = CBashGeneric(9, c_ubyte)
    unused1 = CBashUINT8ARRAY(10, 3)

    def create_effect(self):
        length = _CGetFieldAttribute(self._RecordID, 11, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 11, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return Effect(self._RecordID, 11, length)
    effects = CBashLIST(11, Effect)
    effects_list = CBashLIST(11, Effect, True)

    IsManualCost = CBashBasicFlag(u'flags', 0x00000001)
    IsStartSpell = CBashBasicFlag(u'flags', 0x00000004)
    IsSilenceImmune = CBashBasicFlag(u'flags', 0x0000000A)
    IsAreaEffectIgnoresLOS = CBashBasicFlag(u'flags', 0x00000010)
    IsAEIgnoresLOS = CBashAlias(u'IsAreaEffectIgnoresLOS')
    IsScriptAlwaysApplies = CBashBasicFlag(u'flags', 0x00000020)
    IsDisallowAbsorbReflect = CBashBasicFlag(u'flags', 0x00000040)
    IsDisallowAbsorb = CBashAlias(u'IsDisallowAbsorbReflect')
    IsDisallowReflect = CBashAlias(u'IsDisallowAbsorbReflect')
    IsTouchExplodesWOTarget = CBashBasicFlag(u'flags', 0x00000080)
    IsTouchExplodes = CBashAlias(u'IsTouchExplodesWOTarget')
    IsSpell = CBashBasicType(u'spellType', 0, u'IsDisease')
    IsDisease = CBashBasicType(u'spellType', 1, u'IsSpell')
    IsPower = CBashBasicType(u'spellType', 2, u'IsSpell')
    IsLesserPower = CBashBasicType(u'spellType', 3, u'IsSpell')
    IsAbility = CBashBasicType(u'spellType', 4, u'IsSpell')
    IsPoison = CBashBasicType(u'spellType', 5, u'IsSpell')
    IsNovice = CBashBasicType(u'levelType', 0, u'IsApprentice')
    IsApprentice = CBashBasicType(u'levelType', 1, u'IsNovice')
    IsJourneyman = CBashBasicType(u'levelType', 2, u'IsNovice')
    IsExpert = CBashBasicType(u'levelType', 3, u'IsNovice')
    IsMaster = CBashBasicType(u'levelType', 4, u'IsNovice')
    ##OBME Fields. Setting any of the below fields will make the mod require JRoush's OBME plugin for OBSE
    ##To see if OBME is in use, check the recordVersion field for a non-None value
    recordVersion = CBashGeneric(12, c_ubyte)
    betaVersion = CBashGeneric(13, c_ubyte)
    minorVersion = CBashGeneric(14, c_ubyte)
    majorVersion = CBashGeneric(15, c_ubyte)
    reserved = CBashUINT8ARRAY(16, 0x1C)
    datx_p = CBashUINT8ARRAY(17, 0x20)
    exportattrs = copyattrs = ObBaseRecord.baseattrs + [u'full', u'spellType', u'cost',
                                                        u'levelType', u'flags', u'effects_list']
    copyattrsOBME = copyattrs + [u'recordVersion', u'betaVersion',
                                 u'minorVersion', u'majorVersion',
                                 u'reserved', u'datx_p']
    exportattrsOBME = copyattrsOBME[:]
    exportattrsOBME.remove(u'reserved')
    exportattrsOBME.remove(u'datx_p')

class ObSTATRecord(ObBaseRecord):
    __slots__ = []
    _Type = b'STAT'
    modPath = CBashISTRING(5)
    modb = CBashFLOAT32(6)
    modt_p = CBashUINT8ARRAY(7)
    copyattrs = ObBaseRecord.baseattrs + [u'modPath', u'modb', u'modt_p']
    exportattrs = copyattrs[:]
    exportattrs.remove(u'modt_p')

class ObTREERecord(ObBaseRecord):
    __slots__ = []
    _Type = b'TREE'
    modPath = CBashISTRING(5)
    modb = CBashFLOAT32(6)
    modt_p = CBashUINT8ARRAY(7)
    iconPath = CBashISTRING(8)
    speedTree = CBashUINT32ARRAY(9)
    curvature = CBashFLOAT32(10)
    minAngle = CBashFLOAT32(11)
    maxAngle = CBashFLOAT32(12)
    branchDim = CBashFLOAT32(13)
    leafDim = CBashFLOAT32(14)
    shadowRadius = CBashGeneric(15, c_long)
    rockSpeed = CBashFLOAT32(16)
    rustleSpeed = CBashFLOAT32(17)
    widthBill = CBashFLOAT32(18)
    heightBill = CBashFLOAT32(19)
    copyattrs = ObBaseRecord.baseattrs + [u'modPath', u'modb', u'modt_p', u'iconPath',
                                          u'speedTree', u'curvature', u'minAngle',
                                          u'maxAngle', u'branchDim', u'leafDim',
                                          u'shadowRadius', u'rockSpeed',
                                          u'rustleSpeed', u'widthBill', u'heightBill']
    exportattrs = copyattrs[:]
    exportattrs.remove(u'modt_p')

class ObWATRRecord(ObBaseRecord):
    __slots__ = []
    _Type = b'WATR'
    texturePath = CBashISTRING(5)
    opacity = CBashGeneric(6, c_ubyte)
    flags = CBashGeneric(7, c_ubyte)
    materialPath = CBashISTRING(8)
    sound = CBashFORMID(9)
    windVelocity = CBashFLOAT32(10)
    windDirection = CBashFLOAT32(11)
    waveAmp = CBashFLOAT32(12)
    waveFreq = CBashFLOAT32(13)
    sunPower = CBashFLOAT32(14)
    reflectAmt = CBashFLOAT32(15)
    fresnelAmt = CBashFLOAT32(16)
    xSpeed = CBashFLOAT32(17)
    ySpeed = CBashFLOAT32(18)
    fogNear = CBashFLOAT32(19)
    fogFar = CBashFLOAT32(20)
    shallowRed = CBashGeneric(21, c_ubyte)
    shallowGreen = CBashGeneric(22, c_ubyte)
    shallowBlue = CBashGeneric(23, c_ubyte)
    unused1 = CBashUINT8ARRAY(24, 1)
    deepRed = CBashGeneric(25, c_ubyte)
    deepGreen = CBashGeneric(26, c_ubyte)
    deepBlue = CBashGeneric(27, c_ubyte)
    unused2 = CBashUINT8ARRAY(28, 1)
    reflRed = CBashGeneric(29, c_ubyte)
    reflGreen = CBashGeneric(30, c_ubyte)
    reflBlue = CBashGeneric(31, c_ubyte)
    unused3 = CBashUINT8ARRAY(32, 1)
    blend = CBashGeneric(33, c_ubyte)
    unused4 = CBashUINT8ARRAY(34, 3)
    rainForce = CBashFLOAT32(35)
    rainVelocity = CBashFLOAT32(36)
    rainFalloff = CBashFLOAT32(37)
    rainDampner = CBashFLOAT32(38)
    rainSize = CBashFLOAT32(39)
    dispForce = CBashFLOAT32(40)
    dispVelocity = CBashFLOAT32(41)
    dispFalloff = CBashFLOAT32(42)
    dispDampner = CBashFLOAT32(43)
    dispSize = CBashFLOAT32(44)
    damage = CBashGeneric(45, c_ushort)
    dayWater = CBashFORMID(46)
    nightWater = CBashFORMID(47)
    underWater = CBashFORMID(48)
    IsCausesDamage = CBashBasicFlag(u'flags', 0x00000001)
    IsCausesDmg = CBashAlias(u'IsCausesDamage')
    IsReflective = CBashBasicFlag(u'flags', 0x00000002)
    exportattrs = copyattrs = ObBaseRecord.baseattrs + [
        u'texturePath', u'opacity', u'flags', u'materialPath', u'sound',
        u'windVelocity', u'windDirection', u'waveAmp', u'waveFreq',
        u'sunPower', u'reflectAmt', u'fresnelAmt', u'xSpeed', u'ySpeed',
        u'fogNear', u'fogFar', u'shallowRed', u'shallowGreen', u'shallowBlue',
        u'deepRed', u'deepGreen', u'deepBlue', u'reflRed', u'reflGreen',
        u'reflBlue', u'blend', u'rainForce', u'rainVelocity', u'rainFalloff',
        u'rainDampner', u'rainSize', u'dispForce', u'dispVelocity',
        u'dispFalloff', u'dispDampner', u'dispSize', u'damage', u'dayWater',
        u'nightWater', u'underWater']

class ObWEAPRecord(ObBaseRecord):
    __slots__ = []
    _Type = b'WEAP'
    full = CBashSTRING(5)
    modPath = CBashISTRING(6)
    modb = CBashFLOAT32(7)
    modt_p = CBashUINT8ARRAY(8)
    iconPath = CBashISTRING(9)
    script = CBashFORMID(10)
    enchantment = CBashFORMID(11)
    enchantPoints = CBashGeneric(12, c_ushort)
    weaponType = CBashGeneric(13, c_ulong)
    speed = CBashFLOAT32(14)
    reach = CBashFLOAT32(15)
    flags = CBashGeneric(16, c_ulong)
    value = CBashGeneric(17, c_ulong)
    health = CBashGeneric(18, c_ulong)
    weight = CBashFLOAT32(19)
    damage = CBashGeneric(20, c_ushort)
    IsBlade1Hand = CBashBasicType(u'weaponType', 0, u'IsBlade2Hand')
    IsBlade2Hand = CBashBasicType(u'weaponType', 1, u'IsBlade1Hand')
    IsBlunt1Hand = CBashBasicType(u'weaponType', 2, u'IsBlade1Hand')
    IsBlunt2Hand = CBashBasicType(u'weaponType', 3, u'IsBlade1Hand')
    IsStaff = CBashBasicType(u'weaponType', 4, u'IsBlade1Hand')
    IsBow = CBashBasicType(u'weaponType', 5, u'IsBlade1Hand')
    IsNotNormalWeapon = CBashBasicFlag(u'flags', 0x00000001)
    IsNotNormal = CBashAlias(u'IsNotNormalWeapon')
    IsNormalWeapon = CBashInvertedFlag(u'IsNotNormalWeapon')
    IsNormal = CBashAlias(u'IsNormalWeapon')
    copyattrs = ObBaseRecord.baseattrs + [u'full', u'modPath', u'modb', u'modt_p',
                                          u'iconPath', u'script', u'enchantment',
                                          u'enchantPoints', u'weaponType',
                                          u'speed', u'reach', u'flags', u'value',
                                          u'health', u'weight', u'damage']
    exportattrs = copyattrs[:]
    exportattrs.remove(u'modt_p')

class ObWRLDRecord(ObBaseRecord):
    __slots__ = []
    _Type = b'WRLD'
    full = CBashSTRING(5)
    parent = CBashFORMID(6)
    climate = CBashFORMID(7)
    water = CBashFORMID(8)
    mapPath = CBashISTRING(9)
    dimX = CBashGeneric(10, c_long)
    dimY = CBashGeneric(11, c_long)
    NWCellX = CBashGeneric(12, c_short)
    NWCellY = CBashGeneric(13, c_short)
    SECellX = CBashGeneric(14, c_short)
    SECellY = CBashGeneric(15, c_short)
    flags = CBashGeneric(16, c_ubyte)
    xMinObjBounds = CBashFLOAT32(17)
    yMinObjBounds = CBashFLOAT32(18)
    xMaxObjBounds = CBashFLOAT32(19)
    yMaxObjBounds = CBashFLOAT32(20)
    musicType = CBashGeneric(21, c_ulong)
    ofst_p = CBashUINT8ARRAY(22)
    def create_ROAD(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self.GetParentMod()._ModID, cast(b'ROAD', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, self._RecordID)
        return ObROADRecord(RecordID) if RecordID else None
    ROAD = CBashSUBRECORD(23, ObROADRecord, b'ROAD')

    def create_WorldCELL(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self.GetParentMod()._ModID, cast(b'WCEL', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, self._RecordID)
        return ObCELLRecord(RecordID) if RecordID else None
    WorldCELL = CBashSUBRECORD(24, ObCELLRecord, b'WCEL')
##b'WCEL' is an artificial type CBash uses to distinguish World Cells
    def create_CELLS(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self.GetParentMod()._ModID, cast(b'CELL', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, self._RecordID)
        return ObCELLRecord(RecordID) if RecordID else None
    CELLS = CBashSUBRECORDARRAY(25, ObCELLRecord, b'CELL')

    IsSmallWorld = CBashBasicFlag(u'flags', 0x00000001)
    IsNoFastTravel = CBashBasicFlag(u'flags', 0x00000002)
    IsFastTravel = CBashInvertedFlag(u'IsNoFastTravel')
    IsOblivionWorldspace = CBashBasicFlag(u'flags', 0x00000004)
    IsNoLODWater = CBashBasicFlag(u'flags', 0x00000010)
    IsLODWater = CBashInvertedFlag(u'IsNoLODWater')
    IsDefault = CBashBasicType(u'musicType', 0, u'IsPublic')
    IsPublic = CBashBasicType(u'musicType', 1, u'IsDefault')
    IsDungeon = CBashBasicType(u'musicType', 2, u'IsDefault')
    exportattrs = copyattrs = ObBaseRecord.baseattrs + [u'full', u'parent', u'climate', u'water', u'mapPath',
                                                        u'dimX', u'dimY', u'NWCellX', u'NWCellY', u'SECellX',
                                                        u'SECellY', u'flags', u'xMinObjBounds', u'yMinObjBounds',
                                                        u'xMaxObjBounds', u'yMaxObjBounds', u'musicType', u'ROAD', u'WorldCELL'] # u'ofst_p',

class ObWTHRRecord(ObBaseRecord):
    __slots__ = []
    _Type = b'WTHR'
    class WTHRColor(BaseComponent):
        __slots__ = []
        riseRed = CBashGeneric_GROUP(0, c_ubyte)
        riseGreen = CBashGeneric_GROUP(1, c_ubyte)
        riseBlue = CBashGeneric_GROUP(2, c_ubyte)
        unused1 = CBashUINT8ARRAY_GROUP(3, 1)
        dayRed = CBashGeneric_GROUP(4, c_ubyte)
        dayGreen = CBashGeneric_GROUP(5, c_ubyte)
        dayBlue = CBashGeneric_GROUP(6, c_ubyte)
        unused2 = CBashUINT8ARRAY_GROUP(7, 1)
        setRed = CBashGeneric_GROUP(8, c_ubyte)
        setGreen = CBashGeneric_GROUP(9, c_ubyte)
        setBlue = CBashGeneric_GROUP(10, c_ubyte)
        unused3 = CBashUINT8ARRAY_GROUP(11, 1)
        nightRed = CBashGeneric_GROUP(12, c_ubyte)
        nightGreen = CBashGeneric_GROUP(13, c_ubyte)
        nightBlue = CBashGeneric_GROUP(14, c_ubyte)
        unused4 = CBashUINT8ARRAY_GROUP(15, 1)
        exportattrs = copyattrs = [u'riseRed', u'riseGreen', u'riseBlue',
                                   u'dayRed', u'dayGreen', u'dayBlue',
                                   u'setRed', u'setGreen', u'setBlue',
                                   u'nightRed', u'nightGreen', u'nightBlue']

    class Sound(ListComponent):
        __slots__ = []
        sound = CBashFORMID_LIST(1)
        type = CBashGeneric_LIST(2, c_ulong)
        IsDefault = CBashBasicType(u'type', 0, u'IsPrecip')
        IsPrecipitation = CBashBasicType(u'type', 1, u'IsDefault')
        IsPrecip = CBashAlias(u'IsPrecipitation')
        IsWind = CBashBasicType(u'type', 2, u'IsDefault')
        IsThunder = CBashBasicType(u'type', 3, u'IsDefault')
        exportattrs = copyattrs = [u'sound', u'type']

    lowerLayerPath = CBashISTRING(5)
    upperLayerPath = CBashISTRING(6)
    modPath = CBashISTRING(7)
    modb = CBashFLOAT32(8)
    modt_p = CBashUINT8ARRAY(9)
    upperSky = CBashGrouped(10, WTHRColor)
    upperSky_list = CBashGrouped(10, WTHRColor, True)

    fog = CBashGrouped(26, WTHRColor)
    fog_list = CBashGrouped(26, WTHRColor, True)

    lowerClouds = CBashGrouped(42, WTHRColor)
    lowerClouds_list = CBashGrouped(42, WTHRColor, True)

    ambient = CBashGrouped(58, WTHRColor)
    ambient_list = CBashGrouped(58, WTHRColor, True)

    sunlight = CBashGrouped(74, WTHRColor)
    sunlight_list = CBashGrouped(74, WTHRColor, True)

    sun = CBashGrouped(90, WTHRColor)
    sun_list = CBashGrouped(90, WTHRColor, True)

    stars = CBashGrouped(106, WTHRColor)
    stars_list = CBashGrouped(106, WTHRColor, True)

    lowerSky = CBashGrouped(122, WTHRColor)
    lowerSky_list = CBashGrouped(122, WTHRColor, True)

    horizon = CBashGrouped(138, WTHRColor)
    horizon_list = CBashGrouped(138, WTHRColor, True)

    upperClouds = CBashGrouped(154, WTHRColor)
    upperClouds_list = CBashGrouped(154, WTHRColor, True)

    fogDayNear = CBashFLOAT32(170)
    fogDayFar = CBashFLOAT32(171)
    fogNightNear = CBashFLOAT32(172)
    fogNightFar = CBashFLOAT32(173)
    eyeAdaptSpeed = CBashFLOAT32(174)
    blurRadius = CBashFLOAT32(175)
    blurPasses = CBashFLOAT32(176)
    emissiveMult = CBashFLOAT32(177)
    targetLum = CBashFLOAT32(178)
    upperLumClamp = CBashFLOAT32(179)
    brightScale = CBashFLOAT32(180)
    brightClamp = CBashFLOAT32(181)
    lumRampNoTex = CBashFLOAT32(182)
    lumRampMin = CBashFLOAT32(183)
    lumRampMax = CBashFLOAT32(184)
    sunlightDimmer = CBashFLOAT32(185)
    grassDimmer = CBashFLOAT32(186)
    treeDimmer = CBashFLOAT32(187)
    windSpeed = CBashGeneric(188, c_ubyte)
    lowerCloudSpeed = CBashGeneric(189, c_ubyte)
    upperCloudSpeed = CBashGeneric(190, c_ubyte)
    transDelta = CBashGeneric(191, c_ubyte)
    sunGlare = CBashGeneric(192, c_ubyte)
    sunDamage = CBashGeneric(193, c_ubyte)
    rainFadeIn = CBashGeneric(194, c_ubyte)
    rainFadeOut = CBashGeneric(195, c_ubyte)
    boltFadeIn = CBashGeneric(196, c_ubyte)
    boltFadeOut = CBashGeneric(197, c_ubyte)
    boltFrequency = CBashGeneric(198, c_ubyte)
    weatherType = CBashGeneric(199, c_ubyte)
    boltRed = CBashGeneric(200, c_ubyte)
    boltGreen = CBashGeneric(201, c_ubyte)
    boltBlue = CBashGeneric(202, c_ubyte)

    def create_sound(self):
        length = _CGetFieldAttribute(self._RecordID, 203, 0, 0, 0, 0, 0, 0, 1)
        _CSetField(self._RecordID, 203, 0, 0, 0, 0, 0, 0, 0, c_ulong(length + 1))
        return self.Sound(self._RecordID, 203, length)
    sounds = CBashLIST(203, Sound)
    sounds_list = CBashLIST(203, Sound, True)

    ##actually flags, but all are exclusive(except unknowns)...so like a Type
    ##Manual hackery will make the CS think it is multiple types. It isn't known how the game would react.
    IsNone = CBashMaskedType(u'weatherType',  0x0F, 0x00, u'IsPleasant')
    IsPleasant = CBashMaskedType(u'weatherType',  0x0F, 0x01, u'IsNone')
    IsCloudy = CBashMaskedType(u'weatherType',  0x0F, 0x02, u'IsNone')
    IsRainy = CBashMaskedType(u'weatherType',  0x0F, 0x04, u'IsNone')
    IsSnow = CBashMaskedType(u'weatherType',  0x0F, 0x08, u'IsNone')
    IsUnk1 = CBashBasicFlag(u'weatherType', 0x40)
    IsUnk2 = CBashBasicFlag(u'weatherType', 0x80)
    copyattrs = ObBaseRecord.baseattrs + [
        u'lowerLayerPath', u'upperLayerPath', u'modPath', u'modb', u'modt_p',
        u'upperSky_list', u'fog_list', u'lowerClouds_list', u'ambient_list',
        u'sunlight_list', u'sun_list', u'stars_list', u'lowerSky_list',
        u'horizon_list', u'upperClouds_list', u'fogDayNear', u'fogDayFar',
        u'fogNightNear', u'fogNightFar', u'eyeAdaptSpeed', u'blurRadius',
        u'blurPasses', u'emissiveMult', u'targetLum', u'upperLumClamp',
        u'brightScale', u'brightClamp', u'lumRampNoTex', u'lumRampMin',
        u'lumRampMax', u'sunlightDimmer', u'grassDimmer', u'treeDimmer',
        u'windSpeed', u'lowerCloudSpeed', u'upperCloudSpeed', u'transDelta',
        u'sunGlare', u'sunDamage', u'rainFadeIn', u'rainFadeOut',
        u'boltFadeIn', u'boltFadeOut', u'boltFrequency', u'weatherType',
        u'boltRed', u'boltGreen', u'boltBlue', u'sounds_list']
    exportattrs = copyattrs[:]
    exportattrs.remove(u'modt_p')

#Helper functions
validTypes = {b'GMST',b'GLOB',b'CLAS',b'FACT',b'HAIR',b'EYES',b'RACE',
              b'SOUN',b'SKIL',b'MGEF',b'SCPT',b'LTEX',b'ENCH',b'SPEL',
              b'BSGN',b'ACTI',b'APPA',b'ARMO',b'BOOK',b'CLOT',b'CONT',
              b'DOOR',b'INGR',b'LIGH',b'MISC',b'STAT',b'GRAS',b'TREE',
              b'FLOR',b'FURN',b'WEAP',b'AMMO',b'NPC_',b'CREA',b'LVLC',
              b'SLGM',b'KEYM',b'ALCH',b'SBSP',b'SGST',b'LVLI',b'WTHR',
              b'CLMT',b'REGN',b'WRLD',b'CELL',b'ACHR',b'ACRE',b'REFR',
              b'PGRD',b'LAND',b'ROAD',b'DIAL',b'INFO',b'QUST',b'IDLE',
              b'PACK',b'CSTY',b'LSCR',b'LVSP',b'ANIO',b'WATR',b'EFSH'}

aggregateTypes = {b'GMST',b'GLOB',b'CLAS',b'FACT',b'HAIR',b'EYES',b'RACE',
                  b'SOUN',b'SKIL',b'MGEF',b'SCPT',b'LTEX',b'ENCH',b'SPEL',
                  b'BSGN',b'ACTI',b'APPA',b'ARMO',b'BOOK',b'CLOT',b'CONT',
                  b'DOOR',b'INGR',b'LIGH',b'MISC',b'STAT',b'GRAS',b'TREE',
                  b'FLOR',b'FURN',b'WEAP',b'AMMO',b'NPC_',b'CREA',b'LVLC',
                  b'SLGM',b'KEYM',b'ALCH',b'SBSP',b'SGST',b'LVLI',b'WTHR',
                  b'CLMT',b'REGN',b'WRLD',b'CELLS',b'ACHRS',b'ACRES',b'REFRS',
                  b'PGRDS',b'LANDS',b'ROADS',b'DIAL',b'INFOS',b'QUST',b'IDLE',
                  b'PACK',b'CSTY',b'LSCR',b'LVSP',b'ANIO',b'WATR',b'EFSH'}

pickupables = {b'APPA',b'ARMO',b'BOOK',b'CLOT',b'INGR',b'LIGH',b'MISC',
               b'WEAP',b'AMMO',b'SLGM',b'KEYM',b'ALCH',b'SGST'}

type_record = dict([(b'BASE',ObBaseRecord),(None,None),(b'',None),
                    (b'GMST',ObGMSTRecord),(b'GLOB',ObGLOBRecord),(b'CLAS',ObCLASRecord),
                    (b'FACT',ObFACTRecord),(b'HAIR',ObHAIRRecord),(b'EYES',ObEYESRecord),
                    (b'RACE',ObRACERecord),(b'SOUN',ObSOUNRecord),(b'SKIL',ObSKILRecord),
                    (b'MGEF',ObMGEFRecord),(b'SCPT',ObSCPTRecord),(b'LTEX',ObLTEXRecord),
                    (b'ENCH',ObENCHRecord),(b'SPEL',ObSPELRecord),(b'BSGN',ObBSGNRecord),
                    (b'ACTI',ObACTIRecord),(b'APPA',ObAPPARecord),(b'ARMO',ObARMORecord),
                    (b'BOOK',ObBOOKRecord),(b'CLOT',ObCLOTRecord),(b'CONT',ObCONTRecord),
                    (b'DOOR',ObDOORRecord),(b'INGR',ObINGRRecord),(b'LIGH',ObLIGHRecord),
                    (b'MISC',ObMISCRecord),(b'STAT',ObSTATRecord),(b'GRAS',ObGRASRecord),
                    (b'TREE',ObTREERecord),(b'FLOR',ObFLORRecord),(b'FURN',ObFURNRecord),
                    (b'WEAP',ObWEAPRecord),(b'AMMO',ObAMMORecord),(b'NPC_',ObNPC_Record),
                    (b'CREA',ObCREARecord),(b'LVLC',ObLVLCRecord),(b'SLGM',ObSLGMRecord),
                    (b'KEYM',ObKEYMRecord),(b'ALCH',ObALCHRecord),(b'SBSP',ObSBSPRecord),
                    (b'SGST',ObSGSTRecord),(b'LVLI',ObLVLIRecord),(b'WTHR',ObWTHRRecord),
                    (b'CLMT',ObCLMTRecord),(b'REGN',ObREGNRecord),(b'WRLD',ObWRLDRecord),
                    (b'CELL',ObCELLRecord),(b'ACHR',ObACHRRecord),(b'ACRE',ObACRERecord),
                    (b'REFR',ObREFRRecord),(b'PGRD',ObPGRDRecord),(b'LAND',ObLANDRecord),
                    (b'ROAD',ObROADRecord),(b'DIAL',ObDIALRecord),(b'INFO',ObINFORecord),
                    (b'QUST',ObQUSTRecord),(b'IDLE',ObIDLERecord),(b'PACK',ObPACKRecord),
                    (b'CSTY',ObCSTYRecord),(b'LSCR',ObLSCRRecord),(b'LVSP',ObLVSPRecord),
                    (b'ANIO',ObANIORecord),(b'WATR',ObWATRRecord),(b'EFSH',ObEFSHRecord)])

fnv_validTypes = set()

fnv_aggregateTypes = set()

fnv_pickupables = set()

fnv_type_record = dict([(b'BASE',FnvBaseRecord),(None,None),(b'',None),
                        (b'GMST',FnvGMSTRecord),(b'TXST',FnvTXSTRecord),(b'MICN',FnvMICNRecord),
                        (b'GLOB',FnvGLOBRecord),(b'CLAS',FnvCLASRecord),(b'FACT',FnvFACTRecord),
                        (b'HDPT',FnvHDPTRecord),(b'HAIR',FnvHAIRRecord),(b'EYES',FnvEYESRecord),
                        (b'RACE',FnvRACERecord),(b'SOUN',FnvSOUNRecord),(b'ASPC',FnvASPCRecord),
                        (b'MGEF',FnvMGEFRecord),(b'SCPT',FnvSCPTRecord),(b'LTEX',FnvLTEXRecord),
                        (b'ENCH',FnvENCHRecord),(b'SPEL',FnvSPELRecord),(b'ACTI',FnvACTIRecord),
                        (b'TACT',FnvTACTRecord),(b'TERM',FnvTERMRecord),(b'ARMO',FnvARMORecord),
                        (b'BOOK',FnvBOOKRecord),(b'CONT',FnvCONTRecord),(b'DOOR',FnvDOORRecord),
                        (b'INGR',FnvINGRRecord),(b'LIGH',FnvLIGHRecord),(b'MISC',FnvMISCRecord),
                        (b'STAT',FnvSTATRecord),(b'SCOL',FnvSCOLRecord),(b'MSTT',FnvMSTTRecord),
                        (b'PWAT',FnvPWATRecord),(b'GRAS',FnvGRASRecord),(b'TREE',FnvTREERecord),
                        (b'FURN',FnvFURNRecord),(b'WEAP',FnvWEAPRecord),(b'AMMO',FnvAMMORecord),
                        (b'NPC_',FnvNPC_Record),(b'CREA',FnvCREARecord),(b'LVLC',FnvLVLCRecord),
                        (b'LVLN',FnvLVLNRecord),(b'KEYM',FnvKEYMRecord),(b'ALCH',FnvALCHRecord),
                        (b'IDLM',FnvIDLMRecord),(b'NOTE',FnvNOTERecord),(b'COBJ',FnvCOBJRecord),
                        (b'PROJ',FnvPROJRecord),(b'LVLI',FnvLVLIRecord),(b'WTHR',FnvWTHRRecord),
                        (b'CLMT',FnvCLMTRecord),(b'REGN',FnvREGNRecord),(b'NAVI',FnvNAVIRecord),
                        (b'CELL',FnvCELLRecord),(b'ACHR',FnvACHRRecord),(b'ACRE',FnvACRERecord),
                        (b'REFR',FnvREFRRecord),(b'PGRE',FnvPGRERecord),(b'PMIS',FnvPMISRecord),
                        (b'PBEA',FnvPBEARecord),(b'NAVM',FnvNAVMRecord),(b'WRLD',FnvWRLDRecord),
                        (b'LAND',FnvLANDRecord),(b'DIAL',FnvDIALRecord),(b'INFO',FnvINFORecord),
                        (b'QUST',FnvQUSTRecord),(b'IDLE',FnvIDLERecord),(b'PACK',FnvPACKRecord),
                        (b'CSTY',FnvCSTYRecord),(b'LSCR',FnvLSCRRecord),(b'ANIO',FnvANIORecord),
                        (b'WATR',FnvWATRRecord),(b'EFSH',FnvEFSHRecord),(b'EXPL',FnvEXPLRecord),
                        (b'DEBR',FnvDEBRRecord),(b'IMGS',FnvIMGSRecord),(b'IMAD',FnvIMADRecord),
                        (b'FLST',FnvFLSTRecord),(b'PERK',FnvPERKRecord),(b'BPTD',FnvBPTDRecord),
                        (b'ADDN',FnvADDNRecord),(b'AVIF',FnvAVIFRecord),(b'RADS',FnvRADSRecord),
                        (b'CAMS',FnvCAMSRecord),(b'CPTH',FnvCPTHRecord),(b'VTYP',FnvVTYPRecord),
                        (b'IPCT',FnvIPCTRecord),(b'IPDS',FnvIPDSRecord),(b'ARMA',FnvARMARecord),
                        (b'ECZN',FnvECZNRecord),(b'MESG',FnvMESGRecord),(b'RGDL',FnvRGDLRecord),
                        (b'DOBJ',FnvDOBJRecord),(b'LGTM',FnvLGTMRecord),(b'MUSC',FnvMUSCRecord),
                        (b'IMOD',FnvIMODRecord),(b'REPU',FnvREPURecord),(b'RCPE',FnvRCPERecord),
                        (b'RCCT',FnvRCCTRecord),(b'CHIP',FnvCHIPRecord),(b'CSNO',FnvCSNORecord),
                        (b'LSCT',FnvLSCTRecord),(b'MSET',FnvMSETRecord),(b'ALOC',FnvALOCRecord),
                        (b'CHAL',FnvCHALRecord),(b'AMEF',FnvAMEFRecord),(b'CCRD',FnvCCRDRecord),
                        (b'CMNY',FnvCMNYRecord),(b'CDCK',FnvCDCKRecord),(b'DEHY',FnvDEHYRecord),
                        (b'HUNG',FnvHUNGRecord),(b'SLPD',FnvSLPDRecord),])

class ObModFile(object):
    __slots__ = [u'_ModID']
    def __init__(self, ModID):
        self._ModID = ModID

    def __eq__(self, other):
        return self._ModID == other._ModID if type(other) is type(self) else False

    def __ne__(self, other):
        return not self.__eq__(other)

    @property
    def FileName(self):
        return _uni(_CGetFileNameByID(self._ModID)) or u'Missing'

    @property
    def ModName(self):
        return _uni(_CGetModNameByID(self._ModID)) or u'Missing'

    @property
    def GName(self):
        return GPath(self.ModName)

    def GetParentCollection(self):
        return ObCollection(_CGetCollectionIDByModID(self._ModID))

    def HasRecord(self, RecordIdentifier):
        if not RecordIdentifier: return False
        formID, editorID = (0, _encode(RecordIdentifier)) if isinstance(RecordIdentifier, basestring) else (RecordIdentifier.GetShortFormID(self),0)
        if not (formID or editorID): return False
        return bool(_CGetRecordID(self._ModID, formID, editorID))

    def LookupRecord(self, RecordIdentifier):
        if not RecordIdentifier: return None
        formID, editorID = (0, _encode(RecordIdentifier)) if isinstance(RecordIdentifier, basestring) else (RecordIdentifier.GetShortFormID(self),None)
        if not (formID or editorID): return None
        RecordID = _CGetRecordID(self._ModID, formID, editorID)
        if RecordID:
            _CGetFieldAttribute.restype = (c_char * 4)
            RecordType = type_record[_CGetFieldAttribute(RecordID, 0, 0, 0, 0, 0, 0, 0, 0).value]
            _CGetFieldAttribute.restype = c_ulong
            return RecordType(RecordID)
        return None

    def IsEmpty(self):
        return _CIsModEmpty(self._ModID) > 0

    def GetNewRecordTypes(self):
        numRecords = _CGetModNumTypes(self._ModID)
        if(numRecords > 0):
            cRecords = ((c_char * 4) * numRecords)()
            _CGetModTypes(self._ModID, cRecords)
            return [cRecord.value for cRecord in cRecords if cRecord]
        return []

    def GetNumEmptyGRUPs(self):
        return _CGetModNumEmptyGRUPs(self._ModID)

    def GetOrphanedFormIDs(self):
        numFormIDs = _CGetModNumOrphans(self._ModID)
        if(numFormIDs > 0):
            cFormIDs = (c_ulong * numFormIDs)()
            _CGetModOrphansFormIDs(self._ModID, byref(cFormIDs))
            RecordID = _CGetRecordID(self._ModID, 0, None)
            return [FormID(_CGetLongIDName(RecordID, cFormID, 0), cFormID) for cFormID in cFormIDs if cFormID]
        return []

    def UpdateReferences(self, Old_NewFormIDs):
        Old_NewFormIDs = FormID.FilterValidDict(Old_NewFormIDs, self, True, True, AsShort=True)
        length = len(Old_NewFormIDs)
        if not length: return []
        OldFormIDs = (c_ulong * length)(*Old_NewFormIDs.keys())
        NewFormIDs = (c_ulong * length)(*Old_NewFormIDs.values())
        Changes = (c_ulong * length)()
        _CUpdateReferences(self._ModID, 0, OldFormIDs, NewFormIDs, byref(Changes), length)
        return [x for x in Changes]

    def CleanMasters(self):
        return _CCleanModMasters(self._ModID)

    def GetRecordsIdenticalToMaster(self):
        numRecords = _CGetNumIdenticalToMasterRecords(self._ModID)
        if(numRecords > 0):
            cRecords = (c_record_p * numRecords)()
            _CGetIdenticalToMasterRecords(self._ModID, cRecords)
            _CGetFieldAttribute.restype = (c_char * 4)
            values = [type_record[_CGetFieldAttribute(x, 0, 0, 0, 0, 0, 0, 0, 0).value](x) for x in cRecords]
            _CGetFieldAttribute.restype = c_ulong
            return values
        return []

    def Load(self):
        _CLoadMod(self._ModID)

    def Unload(self):
        _CUnloadMod(self._ModID)

    def save(self, CloseCollection=True, CleanMasters=True, DestinationName=None):
        return _CSaveMod(self._ModID, c_int(0 | (0x00000001 if CleanMasters else 0) | (0x00000002 if CloseCollection else 0)), _encode(DestinationName) if DestinationName else DestinationName)

    @property
    def TES4(self):
        return ObTES4Record(_CGetRecordID(self._ModID, 0, None))

    def create_GMST(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'GMST', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, None, 0)
        return ObGMSTRecord(RecordID) if RecordID else None
    GMST = CBashRECORDARRAY(ObGMSTRecord, b'GMST')

    def create_GLOB(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'GLOB', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return ObGLOBRecord(RecordID) if RecordID else None
    GLOB = CBashRECORDARRAY(ObGLOBRecord, b'GLOB')

    def create_CLAS(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'CLAS', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return ObCLASRecord(RecordID) if RecordID else None
    CLAS = CBashRECORDARRAY(ObCLASRecord, b'CLAS')

    def create_FACT(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'FACT', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return ObFACTRecord(RecordID) if RecordID else None
    FACT = CBashRECORDARRAY(ObFACTRecord, b'FACT')

    def create_HAIR(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'HAIR', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return ObHAIRRecord(RecordID) if RecordID else None
    HAIR = CBashRECORDARRAY(ObHAIRRecord, b'HAIR')

    def create_EYES(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'EYES', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return ObEYESRecord(RecordID) if RecordID else None
    EYES = CBashRECORDARRAY(ObEYESRecord, b'EYES')

    def create_RACE(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'RACE', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return ObRACERecord(RecordID) if RecordID else None
    RACE = CBashRECORDARRAY(ObRACERecord, b'RACE')

    def create_SOUN(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'SOUN', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return ObSOUNRecord(RecordID) if RecordID else None
    SOUN = CBashRECORDARRAY(ObSOUNRecord, b'SOUN')

    def create_SKIL(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'SKIL', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return ObSKILRecord(RecordID) if RecordID else None
    SKIL = CBashRECORDARRAY(ObSKILRecord, b'SKIL')

    def create_MGEF(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'MGEF', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return ObMGEFRecord(RecordID) if RecordID else None
    MGEF = CBashRECORDARRAY(ObMGEFRecord, b'MGEF')

    def create_SCPT(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'SCPT', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return ObSCPTRecord(RecordID) if RecordID else None
    SCPT = CBashRECORDARRAY(ObSCPTRecord, b'SCPT')

    def create_LTEX(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'LTEX', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return ObLTEXRecord(RecordID) if RecordID else None
    LTEX = CBashRECORDARRAY(ObLTEXRecord, b'LTEX')

    def create_ENCH(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'ENCH', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return ObENCHRecord(RecordID) if RecordID else None
    ENCH = CBashRECORDARRAY(ObENCHRecord, b'ENCH')

    def create_SPEL(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'SPEL', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return ObSPELRecord(RecordID) if RecordID else None
    SPEL = CBashRECORDARRAY(ObSPELRecord, b'SPEL')

    def create_BSGN(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'BSGN', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return ObBSGNRecord(RecordID) if RecordID else None
    BSGN = CBashRECORDARRAY(ObBSGNRecord, b'BSGN')

    def create_ACTI(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'ACTI', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return ObACTIRecord(RecordID) if RecordID else None
    ACTI = CBashRECORDARRAY(ObACTIRecord, b'ACTI')

    def create_APPA(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'APPA', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return ObAPPARecord(RecordID) if RecordID else None
    APPA = CBashRECORDARRAY(ObAPPARecord, b'APPA')

    def create_ARMO(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'ARMO', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return ObARMORecord(RecordID) if RecordID else None
    ARMO = CBashRECORDARRAY(ObARMORecord, b'ARMO')

    def create_BOOK(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'BOOK', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return ObBOOKRecord(RecordID) if RecordID else None
    BOOK = CBashRECORDARRAY(ObBOOKRecord, b'BOOK')

    def create_CLOT(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'CLOT', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return ObCLOTRecord(RecordID) if RecordID else None
    CLOT = CBashRECORDARRAY(ObCLOTRecord, b'CLOT')

    def create_CONT(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'CONT', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return ObCONTRecord(RecordID) if RecordID else None
    CONT = CBashRECORDARRAY(ObCONTRecord, b'CONT')

    def create_DOOR(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'DOOR', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return ObDOORRecord(RecordID) if RecordID else None
    DOOR = CBashRECORDARRAY(ObDOORRecord, b'DOOR')

    def create_INGR(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'INGR', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return ObINGRRecord(RecordID) if RecordID else None
    INGR = CBashRECORDARRAY(ObINGRRecord, b'INGR')

    def create_LIGH(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'LIGH', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return ObLIGHRecord(RecordID) if RecordID else None
    LIGH = CBashRECORDARRAY(ObLIGHRecord, b'LIGH')

    def create_MISC(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'MISC', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return ObMISCRecord(RecordID) if RecordID else None
    MISC = CBashRECORDARRAY(ObMISCRecord, b'MISC')

    def create_STAT(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'STAT', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return ObSTATRecord(RecordID) if RecordID else None
    STAT = CBashRECORDARRAY(ObSTATRecord, b'STAT')

    def create_GRAS(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'GRAS', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return ObGRASRecord(RecordID) if RecordID else None
    GRAS = CBashRECORDARRAY(ObGRASRecord, b'GRAS')

    def create_TREE(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'TREE', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return ObTREERecord(RecordID) if RecordID else None
    TREE = CBashRECORDARRAY(ObTREERecord, b'TREE')

    def create_FLOR(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'FLOR', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return ObFLORRecord(RecordID) if RecordID else None
    FLOR = CBashRECORDARRAY(ObFLORRecord, b'FLOR')

    def create_FURN(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'FURN', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return ObFURNRecord(RecordID) if RecordID else None
    FURN = CBashRECORDARRAY(ObFURNRecord, b'FURN')

    def create_WEAP(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'WEAP', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return ObWEAPRecord(RecordID) if RecordID else None
    WEAP = CBashRECORDARRAY(ObWEAPRecord, b'WEAP')

    def create_AMMO(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'AMMO', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return ObAMMORecord(RecordID) if RecordID else None
    AMMO = CBashRECORDARRAY(ObAMMORecord, b'AMMO')

    def create_NPC_(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'NPC_', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return ObNPC_Record(RecordID) if RecordID else None
    NPC_ = CBashRECORDARRAY(ObNPC_Record, b'NPC_')

    def create_CREA(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'CREA', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return ObCREARecord(RecordID) if RecordID else None
    CREA = CBashRECORDARRAY(ObCREARecord, b'CREA')

    def create_LVLC(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'LVLC', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return ObLVLCRecord(RecordID) if RecordID else None
    LVLC = CBashRECORDARRAY(ObLVLCRecord, b'LVLC')

    def create_SLGM(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'SLGM', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return ObSLGMRecord(RecordID) if RecordID else None
    SLGM = CBashRECORDARRAY(ObSLGMRecord, b'SLGM')

    def create_KEYM(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'KEYM', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return ObKEYMRecord(RecordID) if RecordID else None
    KEYM = CBashRECORDARRAY(ObKEYMRecord, b'KEYM')

    def create_ALCH(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'ALCH', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return ObALCHRecord(RecordID) if RecordID else None
    ALCH = CBashRECORDARRAY(ObALCHRecord, b'ALCH')

    def create_SBSP(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'SBSP', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return ObSBSPRecord(RecordID) if RecordID else None
    SBSP = CBashRECORDARRAY(ObSBSPRecord, b'SBSP')

    def create_SGST(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'SGST', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return ObSGSTRecord(RecordID) if RecordID else None
    SGST = CBashRECORDARRAY(ObSGSTRecord, b'SGST')

    def create_LVLI(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'LVLI', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return ObLVLIRecord(RecordID) if RecordID else None
    LVLI = CBashRECORDARRAY(ObLVLIRecord, b'LVLI')

    def create_WTHR(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'WTHR', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return ObWTHRRecord(RecordID) if RecordID else None
    WTHR = CBashRECORDARRAY(ObWTHRRecord, b'WTHR')

    def create_CLMT(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'CLMT', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return ObCLMTRecord(RecordID) if RecordID else None
    CLMT = CBashRECORDARRAY(ObCLMTRecord, b'CLMT')

    def create_REGN(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'REGN', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return ObREGNRecord(RecordID) if RecordID else None
    REGN = CBashRECORDARRAY(ObREGNRecord, b'REGN')

    def create_WRLD(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'WRLD', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return ObWRLDRecord(RecordID) if RecordID else None
    WRLD = CBashRECORDARRAY(ObWRLDRecord, b'WRLD')

    def create_CELL(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'CELL', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return ObCELLRecord(RecordID) if RecordID else None
    CELL = CBashRECORDARRAY(ObCELLRecord, b'CELL')

    def create_DIAL(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'DIAL', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return ObDIALRecord(RecordID) if RecordID else None
    DIAL = CBashRECORDARRAY(ObDIALRecord, b'DIAL')

    def create_QUST(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'QUST', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return ObQUSTRecord(RecordID) if RecordID else None
    QUST = CBashRECORDARRAY(ObQUSTRecord, b'QUST')

    def create_IDLE(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'IDLE', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return ObIDLERecord(RecordID) if RecordID else None
    IDLE = CBashRECORDARRAY(ObIDLERecord, b'IDLE')

    def create_PACK(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'PACK', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return ObPACKRecord(RecordID) if RecordID else None
    PACK = CBashRECORDARRAY(ObPACKRecord, b'PACK')

    def create_CSTY(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'CSTY', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return ObCSTYRecord(RecordID) if RecordID else None
    CSTY = CBashRECORDARRAY(ObCSTYRecord, b'CSTY')

    def create_LSCR(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'LSCR', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return ObLSCRRecord(RecordID) if RecordID else None
    LSCR = CBashRECORDARRAY(ObLSCRRecord, b'LSCR')

    def create_LVSP(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'LVSP', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return ObLVSPRecord(RecordID) if RecordID else None
    LVSP = CBashRECORDARRAY(ObLVSPRecord, b'LVSP')

    def create_ANIO(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'ANIO', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return ObANIORecord(RecordID) if RecordID else None
    ANIO = CBashRECORDARRAY(ObANIORecord, b'ANIO')

    def create_WATR(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'WATR', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return ObWATRRecord(RecordID) if RecordID else None
    WATR = CBashRECORDARRAY(ObWATRRecord, b'WATR')

    def create_EFSH(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'EFSH', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return ObEFSHRecord(RecordID) if RecordID else None
    EFSH = CBashRECORDARRAY(ObEFSHRecord, b'EFSH')

    ##Aggregate properties. Useful for iterating through all records without going through the parent records.
    WorldCELLS = CBashRECORDARRAY(ObCELLRecord, b'WCEL') ##"WCEL" is an artificial type CBash uses to distinguish World Cells
    CELLS = CBashRECORDARRAY(ObCELLRecord, b'CLLS') ##"CLLS" is an artificial type CBash uses to distinguish all cells (includes WCEL)
    INFOS = CBashRECORDARRAY(ObINFORecord, b'INFO')
    ACHRS = CBashRECORDARRAY(ObACHRRecord, b'ACHR')
    ACRES = CBashRECORDARRAY(ObACRERecord, b'ACRE')
    REFRS = CBashRECORDARRAY(ObREFRRecord, b'REFR')
    PGRDS = CBashRECORDARRAY(ObPGRDRecord, b'PGRD')
    LANDS = CBashRECORDARRAY(ObLANDRecord, b'LAND')
    ROADS = CBashRECORDARRAY(ObROADRecord, b'ROAD')

    @property
    def tops(self):
        return dict(((b'GMST', self.GMST),(b'GLOB', self.GLOB),(b'CLAS', self.CLAS),(b'FACT', self.FACT),
                     (b'HAIR', self.HAIR),(b'EYES', self.EYES),(b'RACE', self.RACE),(b'SOUN', self.SOUN),
                     (b'SKIL', self.SKIL),(b'MGEF', self.MGEF),(b'SCPT', self.SCPT),(b'LTEX', self.LTEX),
                     (b'ENCH', self.ENCH),(b'SPEL', self.SPEL),(b'BSGN', self.BSGN),(b'ACTI', self.ACTI),
                     (b'APPA', self.APPA),(b'ARMO', self.ARMO),(b'BOOK', self.BOOK),(b'CLOT', self.CLOT),
                     (b'CONT', self.CONT),(b'DOOR', self.DOOR),(b'INGR', self.INGR),(b'LIGH', self.LIGH),
                     (b'MISC', self.MISC),(b'STAT', self.STAT),(b'GRAS', self.GRAS),(b'TREE', self.TREE),
                     (b'FLOR', self.FLOR),(b'FURN', self.FURN),(b'WEAP', self.WEAP),(b'AMMO', self.AMMO),
                     (b'NPC_', self.NPC_),(b'CREA', self.CREA),(b'LVLC', self.LVLC),(b'SLGM', self.SLGM),
                     (b'KEYM', self.KEYM),(b'ALCH', self.ALCH),(b'SBSP', self.SBSP),(b'SGST', self.SGST),
                     (b'LVLI', self.LVLI),(b'WTHR', self.WTHR),(b'CLMT', self.CLMT),(b'REGN', self.REGN),
                     (b'CELL', self.CELL),(b'WRLD', self.WRLD),(b'DIAL', self.DIAL),(b'QUST', self.QUST),
                     (b'IDLE', self.IDLE),(b'PACK', self.PACK),(b'CSTY', self.CSTY),(b'LSCR', self.LSCR),
                     (b'LVSP', self.LVSP),(b'ANIO', self.ANIO),(b'WATR', self.WATR),(b'EFSH', self.EFSH)))

    @property
    def aggregates(self):
        return dict(((b'GMST', self.GMST),(b'GLOB', self.GLOB),(b'CLAS', self.CLAS),(b'FACT', self.FACT),
                     (b'HAIR', self.HAIR),(b'EYES', self.EYES),(b'RACE', self.RACE),(b'SOUN', self.SOUN),
                     (b'SKIL', self.SKIL),(b'MGEF', self.MGEF),(b'SCPT', self.SCPT),(b'LTEX', self.LTEX),
                     (b'ENCH', self.ENCH),(b'SPEL', self.SPEL),(b'BSGN', self.BSGN),(b'ACTI', self.ACTI),
                     (b'APPA', self.APPA),(b'ARMO', self.ARMO),(b'BOOK', self.BOOK),(b'CLOT', self.CLOT),
                     (b'CONT', self.CONT),(b'DOOR', self.DOOR),(b'INGR', self.INGR),(b'LIGH', self.LIGH),
                     (b'MISC', self.MISC),(b'STAT', self.STAT),(b'GRAS', self.GRAS),(b'TREE', self.TREE),
                     (b'FLOR', self.FLOR),(b'FURN', self.FURN),(b'WEAP', self.WEAP),(b'AMMO', self.AMMO),
                     (b'NPC_', self.NPC_),(b'CREA', self.CREA),(b'LVLC', self.LVLC),(b'SLGM', self.SLGM),
                     (b'KEYM', self.KEYM),(b'ALCH', self.ALCH),(b'SBSP', self.SBSP),(b'SGST', self.SGST),
                     (b'LVLI', self.LVLI),(b'WTHR', self.WTHR),(b'CLMT', self.CLMT),(b'REGN', self.REGN),
                     (b'WRLD', self.WRLD),(b'CELL', self.CELLS),(b'ACHR', self.ACHRS),(b'ACRE', self.ACRES),
                     (b'REFR', self.REFRS),(b'PGRD', self.PGRDS),(b'LAND', self.LANDS),(b'ROAD', self.ROADS),
                     (b'DIAL', self.DIAL),(b'INFO', self.INFOS),(b'QUST', self.QUST),(b'IDLE', self.IDLE),
                     (b'PACK', self.PACK),(b'CSTY', self.CSTY),(b'LSCR', self.LSCR),(b'LVSP', self.LVSP),
                     (b'ANIO', self.ANIO),(b'WATR', self.WATR),(b'EFSH', self.EFSH)))

class FnvModFile(object):
    __slots__ = [u'_ModID']
    def __init__(self, ModID):
        self._ModID = ModID

    def __eq__(self, other):
        return self._ModID == other._ModID if type(other) is type(self) else False

    def __ne__(self, other):
        return not self.__eq__(other)

    @property
    def FileName(self):
        return _uni(_CGetFileNameByID(self._ModID)) or u'Missing'

    @property
    def ModName(self):
        return _uni(_CGetModNameByID(self._ModID)) or u'Missing'

    @property
    def GName(self):
        return GPath(self.ModName)

    def GetParentCollection(self):
        return ObCollection(_CGetCollectionIDByModID(self._ModID))

    def HasRecord(self, RecordIdentifier):
        if not RecordIdentifier: return False
        formID, editorID = (0, _encode(RecordIdentifier)) if isinstance(RecordIdentifier, basestring) else (RecordIdentifier.GetShortFormID(self),0)
        if not (formID or editorID): return False
        return bool(_CGetRecordID(self._ModID, formID, editorID))

    def LookupRecord(self, RecordIdentifier):
        if not RecordIdentifier: return None
        formID, editorID = (0, _encode(RecordIdentifier)) if isinstance(RecordIdentifier, basestring) else (RecordIdentifier.GetShortFormID(self),0)
        if not (formID or editorID): return None
        RecordID = _CGetRecordID(self._ModID, formID, editorID)
        if RecordID:
            _CGetFieldAttribute.restype = (c_char * 4)
            RecordType = fnv_type_record[_CGetFieldAttribute(RecordID, 0, 0, 0, 0, 0, 0, 0, 0).value]
            _CGetFieldAttribute.restype = c_ulong
            return RecordType(RecordID)
        return None

    def IsEmpty(self):
        return _CIsModEmpty(self._ModID) > 0

    def GetNewRecordTypes(self):
        numRecords = _CGetModNumTypes(self._ModID)
        if(numRecords > 0):
            cRecords = ((c_char * 4) * numRecords)()
            _CGetModTypes(self._ModID, byref(cRecords))
            return [cRecord.value for cRecord in cRecords if cRecord]
        return []

    def GetNumEmptyGRUPs(self):
        return _CGetModNumEmptyGRUPs(self._ModID)

    def GetOrphanedFormIDs(self):
        numFormIDs = _CGetModNumOrphans(self._ModID)
        if(numFormIDs > 0):
            cFormIDs = (c_ulong * numFormIDs)()
            _CGetModOrphansFormIDs(self._ModID, byref(cFormIDs))
            RecordID = _CGetRecordID(self._ModID, 0, None)
            return [FormID(_CGetLongIDName(RecordID, cFormID, 0), cFormID) for cFormID in cFormIDs if cFormID]
        return []

    def UpdateReferences(self, Old_NewFormIDs):
        Old_NewFormIDs = FormID.FilterValidDict(Old_NewFormIDs, self, True, True, AsShort=True)
        length = len(Old_NewFormIDs)
        if not length: return []
        OldFormIDs = (c_ulong * length)(*Old_NewFormIDs.keys())
        NewFormIDs = (c_ulong * length)(*Old_NewFormIDs.values())
        Changes = (c_ulong * length)()
        _CUpdateReferences(self._ModID, 0, OldFormIDs, NewFormIDs, byref(Changes), length)
        return [x for x in Changes]

    def CleanMasters(self):
        return _CCleanModMasters(self._ModID)

    def GetRecordsIdenticalToMaster(self):
        numRecords = _CGetNumIdenticalToMasterRecords(self._ModID)
        if(numRecords > 0):
            cRecords = (c_record_p * numRecords)()
            _CGetIdenticalToMasterRecords(self._ModID, cRecords)
            _CGetFieldAttribute.restype = (c_char * 4)
            values = [fnv_type_record[_CGetFieldAttribute(x, 0, 0, 0, 0, 0, 0, 0, 0).value](x) for x in cRecords]
            _CGetFieldAttribute.restype = c_ulong
            return values
        return []

    def Load(self):
        _CLoadMod(self._ModID)

    def Unload(self):
        _CUnloadMod(self._ModID)

    def save(self, CloseCollection=True, CleanMasters=True, DestinationName=None):
        return _CSaveMod(self._ModID, c_ulong(0 | (0x00000001 if CleanMasters else 0) | (0x00000002 if CloseCollection else 0)), _encode(DestinationName) if DestinationName else DestinationName)

    @property
    def TES4(self):
        return FnvTES4Record(_CGetRecordID(self._ModID, 0, None))

    def create_GMST(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'GMST', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return FnvGMSTRecord(RecordID) if RecordID else None
    GMST = CBashRECORDARRAY(FnvGMSTRecord, b'GMST')

    def create_TXST(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'TXST', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return FnvTXSTRecord(RecordID) if RecordID else None
    TXST = CBashRECORDARRAY(FnvTXSTRecord, b'TXST')

    def create_MICN(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'MICN', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return FnvMICNRecord(RecordID) if RecordID else None
    MICN = CBashRECORDARRAY(FnvMICNRecord, b'MICN')

    def create_GLOB(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'GLOB', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return FnvGLOBRecord(RecordID) if RecordID else None
    GLOB = CBashRECORDARRAY(FnvGLOBRecord, b'GLOB')

    def create_CLAS(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'CLAS', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return FnvCLASRecord(RecordID) if RecordID else None
    CLAS = CBashRECORDARRAY(FnvCLASRecord, b'CLAS')

    def create_FACT(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'FACT', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return FnvFACTRecord(RecordID) if RecordID else None
    FACT = CBashRECORDARRAY(FnvFACTRecord, b'FACT')

    def create_HDPT(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'HDPT', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return FnvHDPTRecord(RecordID) if RecordID else None
    HDPT = CBashRECORDARRAY(FnvHDPTRecord, b'HDPT')

    def create_HAIR(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'HAIR', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return FnvHAIRRecord(RecordID) if RecordID else None
    HAIR = CBashRECORDARRAY(FnvHAIRRecord, b'HAIR')

    def create_EYES(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'EYES', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return FnvEYESRecord(RecordID) if RecordID else None
    EYES = CBashRECORDARRAY(FnvEYESRecord, b'EYES')

    def create_RACE(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'RACE', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return FnvRACERecord(RecordID) if RecordID else None
    RACE = CBashRECORDARRAY(FnvRACERecord, b'RACE')

    def create_SOUN(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'SOUN', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return FnvSOUNRecord(RecordID) if RecordID else None
    SOUN = CBashRECORDARRAY(FnvSOUNRecord, b'SOUN')

    def create_ASPC(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'ASPC', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return FnvASPCRecord(RecordID) if RecordID else None
    ASPC = CBashRECORDARRAY(FnvASPCRecord, b'ASPC')

    def create_MGEF(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'MGEF', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return FnvMGEFRecord(RecordID) if RecordID else None
    MGEF = CBashRECORDARRAY(FnvMGEFRecord, b'MGEF')

    def create_SCPT(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'SCPT', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return FnvSCPTRecord(RecordID) if RecordID else None
    SCPT = CBashRECORDARRAY(FnvSCPTRecord, b'SCPT')

    def create_LTEX(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'LTEX', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return FnvLTEXRecord(RecordID) if RecordID else None
    LTEX = CBashRECORDARRAY(FnvLTEXRecord, b'LTEX')

    def create_ENCH(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'ENCH', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return FnvENCHRecord(RecordID) if RecordID else None
    ENCH = CBashRECORDARRAY(FnvENCHRecord, b'ENCH')

    def create_SPEL(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'SPEL', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return FnvSPELRecord(RecordID) if RecordID else None
    SPEL = CBashRECORDARRAY(FnvSPELRecord, b'SPEL')

    def create_ACTI(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'ACTI', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return FnvACTIRecord(RecordID) if RecordID else None
    ACTI = CBashRECORDARRAY(FnvACTIRecord, b'ACTI')

    def create_TACT(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'TACT', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return FnvTACTRecord(RecordID) if RecordID else None
    TACT = CBashRECORDARRAY(FnvTACTRecord, b'TACT')

    def create_TERM(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'TERM', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return FnvTERMRecord(RecordID) if RecordID else None
    TERM = CBashRECORDARRAY(FnvTERMRecord, b'TERM')

    def create_ARMO(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'ARMO', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return FnvARMORecord(RecordID) if RecordID else None
    ARMO = CBashRECORDARRAY(FnvARMORecord, b'ARMO')

    def create_BOOK(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'BOOK', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return FnvBOOKRecord(RecordID) if RecordID else None
    BOOK = CBashRECORDARRAY(FnvBOOKRecord, b'BOOK')

    def create_CONT(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'CONT', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return FnvCONTRecord(RecordID) if RecordID else None
    CONT = CBashRECORDARRAY(FnvCONTRecord, b'CONT')

    def create_DOOR(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'DOOR', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return FnvDOORRecord(RecordID) if RecordID else None
    DOOR = CBashRECORDARRAY(FnvDOORRecord, b'DOOR')

    def create_INGR(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'INGR', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return FnvINGRRecord(RecordID) if RecordID else None
    INGR = CBashRECORDARRAY(FnvINGRRecord, b'INGR')

    def create_LIGH(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'LIGH', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return FnvLIGHRecord(RecordID) if RecordID else None
    LIGH = CBashRECORDARRAY(FnvLIGHRecord, b'LIGH')

    def create_MISC(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'MISC', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return FnvMISCRecord(RecordID) if RecordID else None
    MISC = CBashRECORDARRAY(FnvMISCRecord, b'MISC')

    def create_STAT(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'STAT', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return FnvSTATRecord(RecordID) if RecordID else None
    STAT = CBashRECORDARRAY(FnvSTATRecord, b'STAT')

    def create_SCOL(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'SCOL', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return FnvSCOLRecord(RecordID) if RecordID else None
    SCOL = CBashRECORDARRAY(FnvSCOLRecord, b'SCOL')

    def create_MSTT(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'MSTT', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return FnvMSTTRecord(RecordID) if RecordID else None
    MSTT = CBashRECORDARRAY(FnvMSTTRecord, b'MSTT')

    def create_PWAT(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'PWAT', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return FnvPWATRecord(RecordID) if RecordID else None
    PWAT = CBashRECORDARRAY(FnvPWATRecord, b'PWAT')

    def create_GRAS(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'GRAS', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return FnvGRASRecord(RecordID) if RecordID else None
    GRAS = CBashRECORDARRAY(FnvGRASRecord, b'GRAS')

    def create_TREE(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'TREE', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return FnvTREERecord(RecordID) if RecordID else None
    TREE = CBashRECORDARRAY(FnvTREERecord, b'TREE')

    def create_FURN(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'FURN', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return FnvFURNRecord(RecordID) if RecordID else None
    FURN = CBashRECORDARRAY(FnvFURNRecord, b'FURN')

    def create_WEAP(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'WEAP', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return FnvWEAPRecord(RecordID) if RecordID else None
    WEAP = CBashRECORDARRAY(FnvWEAPRecord, b'WEAP')

    def create_AMMO(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'AMMO', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return FnvAMMORecord(RecordID) if RecordID else None
    AMMO = CBashRECORDARRAY(FnvAMMORecord, b'AMMO')

    def create_NPC_(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'NPC_', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return FnvNPC_Record(RecordID) if RecordID else None
    NPC_ = CBashRECORDARRAY(FnvNPC_Record, b'NPC_')

    def create_CREA(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'CREA', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return FnvCREARecord(RecordID) if RecordID else None
    CREA = CBashRECORDARRAY(FnvCREARecord, b'CREA')

    def create_LVLC(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'LVLC', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return FnvLVLCRecord(RecordID) if RecordID else None
    LVLC = CBashRECORDARRAY(FnvLVLCRecord, b'LVLC')

    def create_LVLN(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'LVLN', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return FnvLVLNRecord(RecordID) if RecordID else None
    LVLN = CBashRECORDARRAY(FnvLVLNRecord, b'LVLN')

    def create_KEYM(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'KEYM', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return FnvKEYMRecord(RecordID) if RecordID else None
    KEYM = CBashRECORDARRAY(FnvKEYMRecord, b'KEYM')

    def create_ALCH(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'ALCH', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return FnvALCHRecord(RecordID) if RecordID else None
    ALCH = CBashRECORDARRAY(FnvALCHRecord, b'ALCH')

    def create_IDLM(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'IDLM', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return FnvIDLMRecord(RecordID) if RecordID else None
    IDLM = CBashRECORDARRAY(FnvIDLMRecord, b'IDLM')

    def create_NOTE(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'NOTE', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return FnvNOTERecord(RecordID) if RecordID else None
    NOTE = CBashRECORDARRAY(FnvNOTERecord, b'NOTE')

    def create_COBJ(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'COBJ', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return FnvCOBJRecord(RecordID) if RecordID else None
    COBJ = CBashRECORDARRAY(FnvCOBJRecord, b'COBJ')

    def create_PROJ(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'PROJ', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return FnvPROJRecord(RecordID) if RecordID else None
    PROJ = CBashRECORDARRAY(FnvPROJRecord, b'PROJ')

    def create_LVLI(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'LVLI', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return FnvLVLIRecord(RecordID) if RecordID else None
    LVLI = CBashRECORDARRAY(FnvLVLIRecord, b'LVLI')

    def create_WTHR(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'WTHR', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return FnvWTHRRecord(RecordID) if RecordID else None
    WTHR = CBashRECORDARRAY(FnvWTHRRecord, b'WTHR')

    def create_CLMT(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'CLMT', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return FnvCLMTRecord(RecordID) if RecordID else None
    CLMT = CBashRECORDARRAY(FnvCLMTRecord, b'CLMT')

    def create_REGN(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'REGN', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return FnvREGNRecord(RecordID) if RecordID else None
    REGN = CBashRECORDARRAY(FnvREGNRecord, b'REGN')

    def create_NAVI(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'NAVI', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return FnvNAVIRecord(RecordID) if RecordID else None
    NAVI = CBashRECORDARRAY(FnvNAVIRecord, b'NAVI')

    def create_CELL(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'CELL', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return FnvCELLRecord(RecordID) if RecordID else None
    CELL = CBashRECORDARRAY(FnvCELLRecord, b'CELL')

    def create_WRLD(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'WRLD', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return FnvWRLDRecord(RecordID) if RecordID else None
    WRLD = CBashRECORDARRAY(FnvWRLDRecord, b'WRLD')

    def create_DIAL(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'DIAL', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return FnvDIALRecord(RecordID) if RecordID else None
    DIAL = CBashRECORDARRAY(FnvDIALRecord, b'DIAL')

    def create_QUST(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'QUST', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return FnvQUSTRecord(RecordID) if RecordID else None
    QUST = CBashRECORDARRAY(FnvQUSTRecord, b'QUST')

    def create_IDLE(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'IDLE', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return FnvIDLERecord(RecordID) if RecordID else None
    IDLE = CBashRECORDARRAY(FnvIDLERecord, b'IDLE')

    def create_PACK(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'PACK', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return FnvPACKRecord(RecordID) if RecordID else None
    PACK = CBashRECORDARRAY(FnvPACKRecord, b'PACK')

    def create_CSTY(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'CSTY', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return FnvCSTYRecord(RecordID) if RecordID else None
    CSTY = CBashRECORDARRAY(FnvCSTYRecord, b'CSTY')

    def create_LSCR(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'LSCR', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return FnvLSCRRecord(RecordID) if RecordID else None
    LSCR = CBashRECORDARRAY(FnvLSCRRecord, b'LSCR')

    def create_ANIO(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'ANIO', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return FnvANIORecord(RecordID) if RecordID else None
    ANIO = CBashRECORDARRAY(FnvANIORecord, b'ANIO')

    def create_WATR(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'WATR', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return FnvWATRRecord(RecordID) if RecordID else None
    WATR = CBashRECORDARRAY(FnvWATRRecord, b'WATR')

    def create_EFSH(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'EFSH', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return FnvEFSHRecord(RecordID) if RecordID else None
    EFSH = CBashRECORDARRAY(FnvEFSHRecord, b'EFSH')

    def create_EXPL(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'EXPL', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return FnvEXPLRecord(RecordID) if RecordID else None
    EXPL = CBashRECORDARRAY(FnvEXPLRecord, b'EXPL')

    def create_DEBR(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'DEBR', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return FnvDEBRRecord(RecordID) if RecordID else None
    DEBR = CBashRECORDARRAY(FnvDEBRRecord, b'DEBR')

    def create_IMGS(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'IMGS', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return FnvIMGSRecord(RecordID) if RecordID else None
    IMGS = CBashRECORDARRAY(FnvIMGSRecord, b'IMGS')

    def create_IMAD(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'IMAD', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return FnvIMADRecord(RecordID) if RecordID else None
    IMAD = CBashRECORDARRAY(FnvIMADRecord, b'IMAD')

    def create_FLST(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'FLST', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return FnvFLSTRecord(RecordID) if RecordID else None
    FLST = CBashRECORDARRAY(FnvFLSTRecord, b'FLST')

    def create_PERK(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'PERK', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return FnvPERKRecord(RecordID) if RecordID else None
    PERK = CBashRECORDARRAY(FnvPERKRecord, b'PERK')

    def create_BPTD(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'BPTD', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return FnvBPTDRecord(RecordID) if RecordID else None
    BPTD = CBashRECORDARRAY(FnvBPTDRecord, b'BPTD')

    def create_ADDN(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'ADDN', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return FnvADDNRecord(RecordID) if RecordID else None
    ADDN = CBashRECORDARRAY(FnvADDNRecord, b'ADDN')

    def create_AVIF(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'AVIF', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return FnvAVIFRecord(RecordID) if RecordID else None
    AVIF = CBashRECORDARRAY(FnvAVIFRecord, b'AVIF')

    def create_RADS(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'RADS', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return FnvRADSRecord(RecordID) if RecordID else None
    RADS = CBashRECORDARRAY(FnvRADSRecord, b'RADS')

    def create_CAMS(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'CAMS', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return FnvCAMSRecord(RecordID) if RecordID else None
    CAMS = CBashRECORDARRAY(FnvCAMSRecord, b'CAMS')

    def create_CPTH(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'CPTH', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return FnvCPTHRecord(RecordID) if RecordID else None
    CPTH = CBashRECORDARRAY(FnvCPTHRecord, b'CPTH')

    def create_VTYP(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'VTYP', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return FnvVTYPRecord(RecordID) if RecordID else None
    VTYP = CBashRECORDARRAY(FnvVTYPRecord, b'VTYP')

    def create_IPCT(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'IPCT', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return FnvIPCTRecord(RecordID) if RecordID else None
    IPCT = CBashRECORDARRAY(FnvIPCTRecord, b'IPCT')

    def create_IPDS(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'IPDS', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return FnvIPDSRecord(RecordID) if RecordID else None
    IPDS = CBashRECORDARRAY(FnvIPDSRecord, b'IPDS')

    def create_ARMA(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'ARMA', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return FnvARMARecord(RecordID) if RecordID else None
    ARMA = CBashRECORDARRAY(FnvARMARecord, b'ARMA')

    def create_ECZN(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'ECZN', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return FnvECZNRecord(RecordID) if RecordID else None
    ECZN = CBashRECORDARRAY(FnvECZNRecord, b'ECZN')

    def create_MESG(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'MESG', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return FnvMESGRecord(RecordID) if RecordID else None
    MESG = CBashRECORDARRAY(FnvMESGRecord, b'MESG')

    def create_RGDL(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'RGDL', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return FnvRGDLRecord(RecordID) if RecordID else None
    RGDL = CBashRECORDARRAY(FnvRGDLRecord, b'RGDL')

    def create_DOBJ(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'DOBJ', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return FnvDOBJRecord(RecordID) if RecordID else None
    DOBJ = CBashRECORDARRAY(FnvDOBJRecord, b'DOBJ')

    def create_LGTM(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'LGTM', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return FnvLGTMRecord(RecordID) if RecordID else None
    LGTM = CBashRECORDARRAY(FnvLGTMRecord, b'LGTM')

    def create_MUSC(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'MUSC', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return FnvMUSCRecord(RecordID) if RecordID else None
    MUSC = CBashRECORDARRAY(FnvMUSCRecord, b'MUSC')

    def create_IMOD(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'IMOD', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return FnvIMODRecord(RecordID) if RecordID else None
    IMOD = CBashRECORDARRAY(FnvIMODRecord, b'IMOD')

    def create_REPU(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'REPU', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return FnvREPURecord(RecordID) if RecordID else None
    REPU = CBashRECORDARRAY(FnvREPURecord, b'REPU')

    def create_RCPE(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'RCPE', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return FnvRCPERecord(RecordID) if RecordID else None
    RCPE = CBashRECORDARRAY(FnvRCPERecord, b'RCPE')

    def create_RCCT(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'RCCT', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return FnvRCCTRecord(RecordID) if RecordID else None
    RCCT = CBashRECORDARRAY(FnvRCCTRecord, b'RCCT')

    def create_CHIP(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'CHIP', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return FnvCHIPRecord(RecordID) if RecordID else None
    CHIP = CBashRECORDARRAY(FnvCHIPRecord, b'CHIP')

    def create_CSNO(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'CSNO', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return FnvCSNORecord(RecordID) if RecordID else None
    CSNO = CBashRECORDARRAY(FnvCSNORecord, b'CSNO')

    def create_LSCT(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'LSCT', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return FnvLSCTRecord(RecordID) if RecordID else None
    LSCT = CBashRECORDARRAY(FnvLSCTRecord, b'LSCT')

    def create_MSET(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'MSET', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return FnvMSETRecord(RecordID) if RecordID else None
    MSET = CBashRECORDARRAY(FnvMSETRecord, b'MSET')

    def create_ALOC(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'ALOC', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return FnvALOCRecord(RecordID) if RecordID else None
    ALOC = CBashRECORDARRAY(FnvALOCRecord, b'ALOC')

    def create_CHAL(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'CHAL', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return FnvCHALRecord(RecordID) if RecordID else None
    CHAL = CBashRECORDARRAY(FnvCHALRecord, b'CHAL')

    def create_AMEF(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'AMEF', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return FnvAMEFRecord(RecordID) if RecordID else None
    AMEF = CBashRECORDARRAY(FnvAMEFRecord, b'AMEF')

    def create_CCRD(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'CCRD', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return FnvCCRDRecord(RecordID) if RecordID else None
    CCRD = CBashRECORDARRAY(FnvCCRDRecord, b'CCRD')

    def create_CMNY(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'CMNY', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return FnvCMNYRecord(RecordID) if RecordID else None
    CMNY = CBashRECORDARRAY(FnvCMNYRecord, b'CMNY')

    def create_CDCK(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'CDCK', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return FnvCDCKRecord(RecordID) if RecordID else None
    CDCK = CBashRECORDARRAY(FnvCDCKRecord, b'CDCK')

    def create_DEHY(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'DEHY', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return FnvDEHYRecord(RecordID) if RecordID else None
    DEHY = CBashRECORDARRAY(FnvDEHYRecord, b'DEHY')

    def create_HUNG(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'HUNG', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return FnvHUNGRecord(RecordID) if RecordID else None
    HUNG = CBashRECORDARRAY(FnvHUNGRecord, b'HUNG')

    def create_SLPD(self, EditorID=0, formID=FormID(None, None)):
        RecordID = _CCreateRecord(self._ModID, cast(b'SLPD', POINTER(c_ulong)).contents.value, formID.GetShortFormID(self), _encode(EditorID) if EditorID else EditorID, 0)
        return FnvSLPDRecord(RecordID) if RecordID else None
    SLPD = CBashRECORDARRAY(FnvSLPDRecord, b'SLPD')

    ##Aggregate properties. Useful for iterating through all records without going through the parent records.
    WorldCELLS = CBashRECORDARRAY(FnvCELLRecord, b'WCEL') ##"WCEL" is an artificial type CBash uses to distinguish World Cells
    CELLS = CBashRECORDARRAY(FnvCELLRecord, b'CLLS') ##"CLLS" is an artificial type CBash uses to distinguish all cells (includes WCEL)
    INFOS = CBashRECORDARRAY(FnvINFORecord, b'INFO')
    ACHRS = CBashRECORDARRAY(FnvACHRRecord, b'ACHR')
    ACRES = CBashRECORDARRAY(FnvACRERecord, b'ACRE')
    REFRS = CBashRECORDARRAY(FnvREFRRecord, b'REFR')
    PGRES = CBashRECORDARRAY(FnvPGRERecord, b'PGRE')
    PMISS = CBashRECORDARRAY(FnvPMISRecord, b'PMIS')
    PBEAS = CBashRECORDARRAY(FnvPBEARecord, b'PBEA')
    PFLAS = CBashRECORDARRAY(FnvPFLARecord, b'PFLA')
    PCBES = CBashRECORDARRAY(FnvPCBERecord, b'PCBE')
    NAVMS = CBashRECORDARRAY(FnvNAVMRecord, b'NAVM')
    LANDS = CBashRECORDARRAY(FnvLANDRecord, b'LAND')

    @property
    def tops(self):
        return dict(((b'GMST', self.GMST),(b'TXST', self.TXST),(b'MICN', self.MICN),
                     (b'GLOB', self.GLOB),(b'CLAS', self.CLAS),(b'FACT', self.FACT),
                     (b'HDPT', self.HDPT),(b'HAIR', self.HAIR),(b'EYES', self.EYES),
                     (b'RACE', self.RACE),(b'SOUN', self.SOUN),(b'ASPC', self.ASPC),
                     (b'MGEF', self.MGEF),(b'SCPT', self.SCPT),(b'LTEX', self.LTEX),
                     (b'ENCH', self.ENCH),(b'SPEL', self.SPEL),(b'ACTI', self.ACTI),
                     (b'TACT', self.TACT),(b'TERM', self.TERM),(b'ARMO', self.ARMO),
                     (b'BOOK', self.BOOK),(b'CONT', self.CONT),(b'DOOR', self.DOOR),
                     (b'INGR', self.INGR),(b'LIGH', self.LIGH),(b'MISC', self.MISC),
                     (b'STAT', self.STAT),(b'SCOL', self.SCOL),(b'MSTT', self.MSTT),
                     (b'PWAT', self.PWAT),(b'GRAS', self.GRAS),(b'TREE', self.TREE),
                     (b'FURN', self.FURN),(b'WEAP', self.WEAP),(b'AMMO', self.AMMO),
                     (b'NPC_', self.NPC_),(b'CREA', self.CREA),(b'LVLC', self.LVLC),
                     (b'LVLN', self.LVLN),(b'KEYM', self.KEYM),(b'ALCH', self.ALCH),
                     (b'IDLM', self.IDLM),(b'NOTE', self.NOTE),(b'COBJ', self.COBJ),
                     (b'PROJ', self.PROJ),(b'LVLI', self.LVLI),(b'WTHR', self.WTHR),
                     (b'CLMT', self.CLMT),(b'REGN', self.REGN),(b'NAVI', self.NAVI),
                     (b'CELL', self.CELL),(b'WRLD', self.WRLD),(b'DIAL', self.DIAL),
                     (b'QUST', self.QUST),(b'IDLE', self.IDLE),(b'PACK', self.PACK),
                     (b'CSTY', self.CSTY),(b'LSCR', self.LSCR),(b'ANIO', self.ANIO),
                     (b'WATR', self.WATR),(b'EFSH', self.EFSH),(b'EXPL', self.EXPL),
                     (b'DEBR', self.DEBR),(b'IMGS', self.IMGS),(b'IMAD', self.IMAD),
                     (b'FLST', self.FLST),(b'PERK', self.PERK),(b'BPTD', self.BPTD),
                     (b'ADDN', self.ADDN),(b'AVIF', self.AVIF),(b'RADS', self.RADS),
                     (b'CAMS', self.CAMS),(b'CPTH', self.CPTH),(b'VTYP', self.VTYP),
                     (b'IPCT', self.IPCT),(b'IPDS', self.IPDS),(b'ARMA', self.ARMA),
                     (b'ECZN', self.ECZN),(b'MESG', self.MESG),(b'RGDL', self.RGDL),
                     (b'DOBJ', self.DOBJ),(b'LGTM', self.LGTM),(b'MUSC', self.MUSC),
                     (b'IMOD', self.IMOD),(b'REPU', self.REPU),(b'RCPE', self.RCPE),
                     (b'RCCT', self.RCCT),(b'CHIP', self.CHIP),(b'CSNO', self.CSNO),
                     (b'LSCT', self.LSCT),(b'MSET', self.MSET),(b'ALOC', self.ALOC),
                     (b'CHAL', self.CHAL),(b'AMEF', self.AMEF),(b'CCRD', self.CCRD),
                     (b'CMNY', self.CMNY),(b'CDCK', self.CDCK),(b'DEHY', self.DEHY),
                     (b'HUNG', self.HUNG),(b'SLPD', self.SLPD),))

    @property
    def aggregates(self):
        return dict(((b'GMST', self.GMST),(b'TXST', self.TXST),(b'MICN', self.MICN),
                     (b'GLOB', self.GLOB),(b'CLAS', self.CLAS),(b'FACT', self.FACT),
                     (b'HDPT', self.HDPT),(b'HAIR', self.HAIR),(b'EYES', self.EYES),
                     (b'RACE', self.RACE),(b'SOUN', self.SOUN),(b'ASPC', self.ASPC),
                     (b'MGEF', self.MGEF),(b'SCPT', self.SCPT),(b'LTEX', self.LTEX),
                     (b'ENCH', self.ENCH),(b'SPEL', self.SPEL),(b'ACTI', self.ACTI),
                     (b'TACT', self.TACT),(b'TERM', self.TERM),(b'ARMO', self.ARMO),
                     (b'BOOK', self.BOOK),(b'CONT', self.CONT),(b'DOOR', self.DOOR),
                     (b'INGR', self.INGR),(b'LIGH', self.LIGH),(b'MISC', self.MISC),
                     (b'STAT', self.STAT),(b'SCOL', self.SCOL),(b'MSTT', self.MSTT),
                     (b'PWAT', self.PWAT),(b'GRAS', self.GRAS),(b'TREE', self.TREE),
                     (b'FURN', self.FURN),(b'WEAP', self.WEAP),(b'AMMO', self.AMMO),
                     (b'NPC_', self.NPC_),(b'CREA', self.CREA),(b'LVLC', self.LVLC),
                     (b'LVLN', self.LVLN),(b'KEYM', self.KEYM),(b'ALCH', self.ALCH),
                     (b'IDLM', self.IDLM),(b'NOTE', self.NOTE),(b'COBJ', self.COBJ),
                     (b'PROJ', self.PROJ),(b'LVLI', self.LVLI),(b'WTHR', self.WTHR),
                     (b'CLMT', self.CLMT),(b'REGN', self.REGN),(b'NAVI', self.NAVI),
                     (b'CELL', self.CELLS),(b'ACHR', self.ACHRS),(b'ACRE', self.ACRES),
                     (b'REFR', self.REFRS),(b'PGRE', self.PGRES),(b'PMIS', self.PMISS),
                     (b'PBEA', self.PBEAS),(b'PFLA', self.PFLAS),(b'PCBE', self.PCBES),
                     (b'NAVM', self.NAVMS),(b'WRLD', self.WRLD),(b'LAND', self.LANDS),
                     (b'DIAL', self.DIAL),(b'INFO', self.INFOS),
                     (b'QUST', self.QUST),(b'IDLE', self.IDLE),(b'PACK', self.PACK),
                     (b'CSTY', self.CSTY),(b'LSCR', self.LSCR),(b'ANIO', self.ANIO),
                     (b'WATR', self.WATR),(b'EFSH', self.EFSH),(b'EXPL', self.EXPL),
                     (b'DEBR', self.DEBR),(b'IMGS', self.IMGS),(b'IMAD', self.IMAD),
                     (b'FLST', self.FLST),(b'PERK', self.PERK),(b'BPTD', self.BPTD),
                     (b'ADDN', self.ADDN),(b'AVIF', self.AVIF),(b'RADS', self.RADS),
                     (b'CAMS', self.CAMS),(b'CPTH', self.CPTH),(b'VTYP', self.VTYP),
                     (b'IPCT', self.IPCT),(b'IPDS', self.IPDS),(b'ARMA', self.ARMA),
                     (b'ECZN', self.ECZN),(b'MESG', self.MESG),(b'RGDL', self.RGDL),
                     (b'DOBJ', self.DOBJ),(b'LGTM', self.LGTM),(b'MUSC', self.MUSC),
                     (b'IMOD', self.IMOD),(b'REPU', self.REPU),(b'RCPE', self.RCPE),
                     (b'RCCT', self.RCCT),(b'CHIP', self.CHIP),(b'CSNO', self.CSNO),
                     (b'LSCT', self.LSCT),(b'MSET', self.MSET),(b'ALOC', self.ALOC),
                     (b'CHAL', self.CHAL),(b'AMEF', self.AMEF),(b'CCRD', self.CCRD),
                     (b'CMNY', self.CMNY),(b'CDCK', self.CDCK),(b'DEHY', self.DEHY),
                     (b'HUNG', self.HUNG),(b'SLPD', self.SLPD),))

class ObCollection(object):
    """Collection of esm/esp's."""
    __slots__ = [u'_CollectionID', u'_WhichGame', u'_ModIndex', u'_ModType',
                 u'LoadOrderMods', u'AllMods', u'_cwd']
    def __init__(self, CollectionID=None, ModsPath=u'.', CollectionType=0):
        #CollectionType == 0, Oblivion
        #CollectionType == 1, Fallout 3
        #CollectionType == 2, Fallout New Vegas
        self._CollectionID, self._WhichGame = (CollectionID,_CGetCollectionType(CollectionID)) if CollectionID else (_CCreateCollection(_encode(ModsPath), CollectionType),CollectionType)
        self._ModIndex, self.LoadOrderMods, self.AllMods = -1, [], []
        self._ModType = ObModFile if self._WhichGame == 0 else FnvModFile
        self._cwd = os.getcwd()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.Close()

    def __eq__(self, other):
        return self._CollectionID == other._CollectionID if type(other) is type(self) else False

    def __ne__(self, other):
        return not self.__eq__(other)

    def GetParentCollection(self):
        return self

    def Unload(self):
        _CUnloadCollection(self._CollectionID)

    def Close(self):
        os.chdir(self._cwd)
        _CDeleteCollection(self._CollectionID)

    @staticmethod
    def UnloadAllCollections():
        return _CUnloadAllCollections()

    @staticmethod
    def DeleteAllCollections():
        return _CDeleteAllCollections()

    def addMod(self, FileName, MinLoad=True, NoLoad=False, CreateNew=False, Saveable=True, LoadMasters=True, Flags=None):
##        //CreateNew, Saveable, and LoadMasters are ignored if Flags is set
##
##        //MinLoad and FullLoad are exclusive
##        // If both are set, FullLoad takes priority
##        // If neither is set, the mod isn't loaded
##
##        //SkipNewRecords causes any new record to be ignored when the mod is loaded
##        // This may leave broken records behind (such as a quest override pointing to a new script that was ignored)
##        // So it shouldn't be used if planning on copying records unless you either check that there are no new records being referenced
##
##        //InLoadOrder makes the mod count towards the 255 limit and enables record creation and copying as new.
##        // If it is false, it forces Saveable to be false.
##        // Any mod with new records should have this set unless you're ignoring the new records.
##        // It causes the mod to be reported by GetNumModIDs, GetModIDs
##
##        //Saveable allows the mod to be saved.
##
##        //AddMasters causes the mod's masters to be added
##        // This is essential for most mod editing functions.
##
##        //LoadMasters causes the mod's masters to be added to the load order and loaded into memory
##        // This has no effect if AddMasters is false
##        // This is required if you want to lookup overridden records
##
##        //ExtendedConflicts causes any conflicting records to be ignored by most functions
##        // IsRecordWinning, GetNumRecordConflicts, GetRecordConflicts will report the extended conflicts only if asked
##
##        //TrackNewTypes causes the loader to track which record types in a mod are new and not overrides
##        // Increases load time per mod.
##        // It enables GetModNumTypes and GetModTypes for that mod.
##
##        //IndexLANDs causes LAND records to have extra indexing.
##        // Increases load time per mod.
##        // It allows the safe editing of land records heights.
##        // Modifying one LAND may require changes in an adjacent LAND to prevent seams
##
##        //FixupPlaceables moves any REFR,ACHR,ACRE records in a world cell to the actual cell they belong to.
##        // Increases load time per mod.
##        // Use if you're planning on iterating through every placeable in a specific cell
##        //   so that you don't have to check the world cell as well.
##
##        //IgnoreInactiveMasters causes any records that override masters not in the load order to be dropped
##        // If it is true, it forces IsAddMasters to be false.
##        // Allows mods not in load order to copy records
##
##        //SkipAllRecords causes all records to be ignored when loading. TrackNewTypes still works, but that's all.
##        // Vastly decreases load time per mod.
##        // Use it when you want to check for new record types, but don't care about the actual records.
##
##        //Only the following combinations are tested:
##        // Normal:  (fIsMinLoad or fIsFullLoad) + fIsInLoadOrder + fIsSaveable + fIsAddMasters + fIsLoadMasters
##        // Merged:  (fIsMinLoad or fIsFullLoad) + fIsSkipNewRecords + fIsIgnoreInactiveMasters
##        // Scanned: (fIsMinLoad or fIsFullLoad) + fIsSkipNewRecords + fIsIgnoreInactiveMasters + fIsExtendedConflicts

##        fIsMinLoad               = 0x00000001
##        fIsFullLoad              = 0x00000002
##        fIsSkipNewRecords        = 0x00000004
##        fIsInLoadOrder           = 0x00000008
##        fIsSaveable              = 0x00000010
##        fIsAddMasters            = 0x00000020
##        fIsLoadMasters           = 0x00000040
##        fIsExtendedConflicts     = 0x00000080
##        fIsTrackNewTypes         = 0x00000100
##        fIsIndexLANDs            = 0x00000200
##        fIsFixupPlaceables       = 0x00000400
##        fIsCreateNew             = 0x00000800
##        fIsIgnoreInactiveMasters = 0x00001000
##        fIsSkipAllRecords        = 0x00002000

        if Flags is None: Flags = 0x00000069 | (0x00000800 if CreateNew else 0) | (0x00000010 if Saveable else 0) | (0x00000040 if LoadMasters else 0)
        return self._ModType(_CAddMod(self._CollectionID, _encode(FileName), Flags & ~0x00000003 if NoLoad else ((Flags & ~0x00000002) | 0x00000001) if MinLoad else ((Flags & ~0x00000001) | 0x00000002)))

    def addMergeMod(self, FileName):
        #fIsIgnoreInactiveMasters, fIsSkipNewRecords
        return self.addMod(FileName, Flags=0x00001004)

    def addScanMod(self, FileName):
        #fIsIgnoreInactiveMasters, fIsExtendedConflicts, fIsSkipNewRecords
        return self.addMod(FileName, Flags=0x00001084)

    def load(self):
        def _callback(current, last, modName):
            return True

        cb = CFUNCTYPE(c_bool, c_uint32, c_uint32, c_char_p)(_callback)
        _CLoadCollection(self._CollectionID, cb)

        _NumModsIDs = _CGetLoadOrderNumMods(self._CollectionID)
        if _NumModsIDs > 0:
            cModIDs = (c_mod_p * _NumModsIDs)()
            _CGetLoadOrderModIDs(self._CollectionID, cModIDs)
            self.LoadOrderMods = [self._ModType(ModID) for ModID in cModIDs]

        _NumModsIDs = _CGetAllNumMods(self._CollectionID)
        if _NumModsIDs > 0:
            cModIDs = (c_mod_p * _NumModsIDs)()
            _CGetAllModIDs(self._CollectionID, cModIDs)
            self.AllMods = [self._ModType(ModID) for ModID in cModIDs]

    def LookupRecords(self, RecordIdentifier, GetExtendedConflicts=False):
        if not RecordIdentifier: return None
        return [record for record in [mod.LookupRecord(RecordIdentifier) for mod in reversed(self.AllMods if GetExtendedConflicts else self.LoadOrderMods)] if record is not None]

    def LookupModFile(self, ModName):
        ModID = _CGetModIDByName(self._CollectionID, _encode(ModName))
        if ModID == 0: raise KeyError(_(u'ModName(%s) not found in collection (%08X)') % (ModName, self._CollectionID) + self.Debug_DumpModFiles() + u'\n')
        return self._ModType(ModID)

    def LookupModFileLoadOrder(self, ModName):
        return _CGetModLoadOrderByName(self._CollectionID, _encode(ModName))

    def UpdateReferences(self, Old_NewFormIDs):
        return sum([mod.UpdateReferences(Old_NewFormIDs) for mod in self.LoadOrderMods])

    def ClearReferenceLog(self):
        return _CGetRecordUpdatedReferences(self._CollectionID, None)

    def Debug_DumpModFiles(self):
        col = [_(u"Collection contains the following modfiles:")]
        lo_mods = [(_CGetModLoadOrderByID(mod._ModID), mod.ModName,
                    mod.FileName) for mod in self.AllMods]
        files = [_(u'Load Order (%s), Name(%s)') % (
            u'--' if lo == -1 else (u'%02X' % lo), mname) if mname == fname else
                 _(u'Load Order (%s), ModName(%s) FileName(%s)') % (
            u'--' if lo == -1 else (u'%02X' % lo), mname, fname)
                 for lo, mname, fname in lo_mods]
        col.extend(files)
        return u'\n'.join(col)
