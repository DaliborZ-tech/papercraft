"""Opt-in own-window minimal Inkscape A/B; coordinate the desktop before running.

These are newly authored test fixtures, not patched production export. The
same Unicode input events are sent to absence/presence of xml:space only.
"""
import argparse
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import xml.etree.ElementTree as ET

parser=argparse.ArgumentParser()
parser.add_argument("--inkscape",type=Path,required=True)
parser.add_argument("--output",type=Path,required=True)
parser.add_argument("--desktop-coordinated",action="store_true")
args=parser.parse_args()
if os.name!="nt" or not args.desktop_coordinated:
    parser.error("Windows and explicit desktop coordination are required")
if args.output.exists():
    parser.error("Output evidence must be new")
scratch=Path(tempfile.mkdtemp(prefix="pc006a-review-space-minimal-"))
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
app=QApplication.instance() or QApplication([])
user32=ctypes.WinDLL("user32",use_last_error=True)
user32.GetForegroundWindow.restype=wintypes.HWND
user32.GetWindowThreadProcessId.argtypes=[wintypes.HWND,ctypes.POINTER(wintypes.DWORD)]
user32.GetWindowThreadProcessId.restype=wintypes.DWORD
user32.SetForegroundWindow.argtypes=[wintypes.HWND]
user32.ShowWindow.argtypes=[wintypes.HWND,ctypes.c_int]
user32.BringWindowToTop.argtypes=[wintypes.HWND]
user32.AttachThreadInput.argtypes=[wintypes.DWORD,wintypes.DWORD,wintypes.BOOL]
user32.IsWindowVisible.argtypes=[wintypes.HWND]
user32.GetWindowRect.argtypes=[wintypes.HWND,ctypes.POINTER(wintypes.RECT)]
user32.GetWindowTextW.argtypes=[wintypes.HWND,wintypes.LPWSTR,ctypes.c_int]
user32.PostMessageW.argtypes=[wintypes.HWND,wintypes.UINT,wintypes.WPARAM,wintypes.LPARAM]
callback_type=ctypes.WINFUNCTYPE(wintypes.BOOL,wintypes.HWND,wintypes.LPARAM)
user32.EnumWindows.argtypes=[callback_type,wintypes.LPARAM]
class Mouse(ctypes.Structure):
    _fields_=[("dx",wintypes.LONG),("dy",wintypes.LONG),("mouseData",wintypes.DWORD),("dwFlags",wintypes.DWORD),("time",wintypes.DWORD),("dwExtraInfo",ctypes.c_size_t)]
class Keyboard(ctypes.Structure):
    _fields_=[("wVk",wintypes.WORD),("wScan",wintypes.WORD),("dwFlags",wintypes.DWORD),("time",wintypes.DWORD),("dwExtraInfo",ctypes.c_size_t)]
class Union(ctypes.Union):
    _fields_=[("mi",Mouse),("ki",Keyboard)]
class Input(ctypes.Structure):
    _anonymous_=("u",)
    _fields_=[("type",wintypes.DWORD),("u",Union)]
user32.SendInput.argtypes=[wintypes.UINT,ctypes.POINTER(Input),ctypes.c_int]
user32.SendInput.restype=wintypes.UINT
results=[]
for preserve in (False,True):
    folder=scratch/("preserve" if preserve else "default")
    folder.mkdir()
    svg=folder/"minimal.svg"
    attribute=' xml:space="preserve"' if preserve else ''
    svg.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="210mm" height="297mm" viewBox="0 0 210 297"><text id="probe" x="20" y="30" font-size="10"'+attribute+'>Seed</text></svg>',encoding="utf-8")
    original=folder/"input-original.svg"
    original.write_bytes(svg.read_bytes())
    environment=dict(os.environ)
    environment["INKSCAPE_PROFILE_DIR"]=str(folder/"profile")
    record={"xml_space_preserve":preserve,"file":str(svg),"input_original":str(original),"initial_sha256":hashlib.sha256(svg.read_bytes()).hexdigest(),"requested_text":"Wall 1 left","input_method":"own-window F8/CtrlA; identical Unicode SendInput pairs for all characters including U+0020; CtrlS"}
    process=None;hwnd=None
    try:
        process=subprocess.Popen([str(args.inkscape),str(svg),"--with-gui","--actions=zoom-page;select-by-id:probe"],env=environment)
        record["own_pid"]=process.pid
        found=[]
        def visit(handle,_):
            pid=wintypes.DWORD();user32.GetWindowThreadProcessId(handle,ctypes.byref(pid))
            if pid.value==process.pid and user32.IsWindowVisible(handle):
                rect=wintypes.RECT();user32.GetWindowRect(handle,ctypes.byref(rect))
                title=ctypes.create_unicode_buffer(1024);user32.GetWindowTextW(handle,title,1024)
                if "minimal.svg" in title.value and rect.right-rect.left>500 and rect.bottom-rect.top>300:
                    found.append(handle)
            return True
        deadline=time.monotonic()+15
        while not found and time.monotonic()<deadline:
            if process.poll() is not None:raise AssertionError("Own editor process exited before its document window: "+str(process.returncode))
            user32.EnumWindows(callback_type(visit),0);time.sleep(.15)
        if not found:raise AssertionError("No own process document window")
        hwnd=found[0];record["own_hwnd"]=int(hwnd)
        QTest.qWait(1800)
        record["before_foreground_hwnd"]=int(user32.GetForegroundWindow() or 0)
        user32.ShowWindow(hwnd,9)
        user32.SetForegroundWindow(hwnd);QTest.qWait(200)
        if user32.GetForegroundWindow()!=hwnd:
            kernel32=ctypes.WinDLL("kernel32",use_last_error=True)
            kernel32.GetCurrentThreadId.restype=wintypes.DWORD
            current_thread=kernel32.GetCurrentThreadId()
            foreground_thread=user32.GetWindowThreadProcessId(user32.GetForegroundWindow(),None)
            attached=False
            try:
                if foreground_thread and current_thread!=foreground_thread:
                    attached=bool(user32.AttachThreadInput(current_thread,foreground_thread,True))
                user32.BringWindowToTop(hwnd)
                user32.SetForegroundWindow(hwnd);QTest.qWait(150)
            finally:
                if attached:user32.AttachThreadInput(current_thread,foreground_thread,False)
            record["temporary_initial_activation_queue_attachment"]=attached
        def foreground():
            pid=wintypes.DWORD();user32.GetWindowThreadProcessId(hwnd,ctypes.byref(pid))
            if pid.value!=process.pid or user32.GetForegroundWindow()!=hwnd:
                raise AssertionError("Own document foreground lost; no global input sent")
        def chord(key,control=False):
            foreground()
            if control:user32.keybd_event(0x11,0,0,0)
            try:
                user32.keybd_event(key,0,0,0);user32.keybd_event(key,0,2,0)
            finally:
                if control:user32.keybd_event(0x11,0,2,0)
            time.sleep(.15)
        chord(0x77);chord(0x41,True)
        for char in record["requested_text"]:
            foreground()
            sequence=(Input*2)(Input(type=1,ki=Keyboard(wVk=0,wScan=ord(char),dwFlags=4,time=0,dwExtraInfo=0)),Input(type=1,ki=Keyboard(wVk=0,wScan=ord(char),dwFlags=6,time=0,dwExtraInfo=0)))
            if user32.SendInput(2,sequence,ctypes.sizeof(Input))!=2:raise RuntimeError("Input was refused")
            time.sleep(.025)
        chord(0x53,True);time.sleep(.8)
        text=ET.parse(svg).getroot().find("{http://www.w3.org/2000/svg}text")
        record.update(actual_text=''.join(text.itertext()),actual_codepoints=[hex(ord(c)) for c in ''.join(text.itertext())],saved_xml_space=text.attrib.get('{http://www.w3.org/XML/1998/namespace}space'),exact_text_preserved=''.join(text.itertext())==record["requested_text"],final_sha256=hashlib.sha256(svg.read_bytes()).hexdigest(),foreground_verified=True)
    except Exception as exc:
        record["error"]=repr(exc)
    finally:
        if process is not None and process.poll() is None:
            if hwnd is not None:user32.PostMessageW(hwnd,0x0010,0,0)
            try:process.wait(timeout=4)
            except subprocess.TimeoutExpired:
                process.terminate();process.wait(timeout=4);record["own_disposable_process_terminated"]=True
    results.append(record)
result={"kind":"independent_minimal_fixture_native_AB_not_production_export_approval","script_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),"inkscape_executable":str(args.inkscape),"inkscape_executable_sha256":hashlib.sha256(args.inkscape.read_bytes()).hexdigest(),"scratch":str(scratch),"results":results,"physical_build":"NOT_RUN","new_user_test":"NOT_RUN"}
args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result,ensure_ascii=False))
