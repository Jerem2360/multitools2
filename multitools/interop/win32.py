from . import *


HANDLE = HDEVNOTIFY = Pointer
DWORD = ULong
WORD = UShort


class GUID(Struct):
    Data1: ULong
    Data2: Short
    Data3: Short
    Data4: Array[Char, 8]


class DEV_BROADCAST_DEVICE_INTERFACE_A(Struct):
    dbcc_size: DWORD
    dbcc_devicetype: DWORD
    dbcc_reserved: DWORD
    dbcc_classguid: GUID
    dbcc_name: String


class DEV_BROADCAST_DEVICE_INTERFACE_W(Struct):
    dbcc_size: DWORD
    dbcc_devicetype: DWORD
    dbcc_reserved: DWORD
    dbcc_classguid: GUID
    dbcc_name: WString


class DEV_BROADCAST_HANDLE(Struct):
    dbch_size: DWORD
    dbch_devicetype: DWORD
    dbch_reserved: DWORD
    dbch_handle: HANDLE
    dbch_hdevnotify: HDEVNOTIFY
    dbch_eventguid: GUID
    dbch_nameoffset: Long
    dbch_data: Array[Byte, 1]


class DEV_BROADCAST_HDR(Struct):
    dbch_size: DWORD
    dbch_devicetype: DWORD
    dbch_reserved: DWORD


class DEV_BROADCAST_OEM(Struct):
    dbco_size: DWORD
    dbco_devicetype: DWORD
    dbco_reserved: DWORD
    dbco_identifier: DWORD
    dbco_suppfunc: DWORD


class DEV_BROADCAST_PORT_A(Struct):
    dbcp_size: DWORD
    dbcp_devicetype: DWORD
    dbcp_reserved: DWORD
    dbcp_name: String


class DEV_BROADCAST_PORT_W(Struct):
    dbcp_size: DWORD
    dbcp_devicetype: DWORD
    dbcp_reserved: DWORD
    dbcp_name: WString


class DEV_BROADCAST_VOLUME(Struct):
    dbcv_size: DWORD
    dbcv_devicetype: DWORD
    dbcv_reserved: DWORD
    dbcv_unitmask: DWORD
    dbcv_flags: WORD

