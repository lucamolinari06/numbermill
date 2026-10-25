"""Position this game's Windows window without changing the monitor mode."""
import ctypes
from ctypes import wintypes
import sys

import pygame


def _api():
    api = ctypes.WinDLL("user32", use_last_error=True)
    api.MonitorFromWindow.argtypes = (wintypes.HWND, wintypes.DWORD)
    api.MonitorFromWindow.restype = wintypes.HANDLE
    api.GetMonitorInfoW.argtypes = (wintypes.HANDLE, ctypes.c_void_p)
    api.GetMonitorInfoW.restype = wintypes.BOOL
    api.GetWindowRect.argtypes = (wintypes.HWND, ctypes.POINTER(wintypes.RECT))
    api.GetWindowRect.restype = wintypes.BOOL
    api.SetWindowPos.argtypes = (wintypes.HWND, wintypes.HWND, ctypes.c_int,
                                ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.UINT)
    api.SetWindowPos.restype = wintypes.BOOL
    return api


def geometry():
    """Return actual pixel bounds for the monitor containing our window."""
    if sys.platform != "win32" or pygame.display.get_driver() == "dummy":
        return None

    class MonitorInfo(ctypes.Structure):
        _fields_ = [("size", wintypes.DWORD), ("monitor", wintypes.RECT),
                    ("work", wintypes.RECT), ("flags", wintypes.DWORD)]

    api = _api()
    hwnd = pygame.display.get_wm_info().get("window")
    monitor = api.MonitorFromWindow(hwnd, 2)  # nearest monitor, including negative origins
    info = MonitorInfo()
    info.size = ctypes.sizeof(info)
    if not api.GetMonitorInfoW(monitor, ctypes.byref(info)):
        raise pygame.error("Could not read monitor bounds")

    def rect(value):
        return pygame.Rect(value.left, value.top, value.right-value.left, value.bottom-value.top)

    window = wintypes.RECT()
    has_window = hwnd and api.GetWindowRect(hwnd, ctypes.byref(window))
    return {"monitor": rect(info.monitor), "work": rect(info.work),
            "window": rect(window) if has_window else None}


def position(bounds, *, resize=False):
    """Move only the current Pygame window; preserve its normal z-order."""
    hwnd = pygame.display.get_wm_info().get("window")
    flags = 0x0004 | 0x0010 | 0x0020  # NOZORDER, NOACTIVATE, FRAMECHANGED
    if not resize:
        flags |= 0x0001  # NOSIZE
    if not _api().SetWindowPos(hwnd, None, bounds.x, bounds.y, bounds.w, bounds.h, flags):
        raise pygame.error("Could not position game window")
