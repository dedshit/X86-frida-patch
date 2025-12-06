import frida
import time
import ctypes
import threading
import psutil
import argparse
import sys

GRE = "\033[92m"
RED = "\033[91m"
YEL = "\033[93m"
CYA = "\033[96m"
MAG = "\033[95m"
RES = "\033[0m"
TARGET_EXE = "AfterFX.exe"
__ = r"""
'use strict';
const img = 'afterfxlib.dll';
const disableSplash = __;
let patches = [
    { off: ptr('0x832BB0'), len: 2, type: 'LicenseCheck' },
];
if (disableSplash) {
    patches.push({ off: ptr('0x8BECEA'), len: 5, type: 'SplashScreen' });
}

function applyPatches(mod) {
    for (const p of patches) {
        const addr = mod.base.add(p.off);
        send("PATCH|" + p.type + "|" + addr);
        Memory.patchCode(addr, p.len, buf => {
            const w = new X86Writer(buf, { pc: addr });
            if (p.type === 'LicenseCheck') w.putXorRegReg('eax', 'eax');
            else if (p.type === 'SplashScreen') w.putMovRegU32('eax', 1);
            w.flush();
        });
        send("OK|" + p.type);
    }
}

try {
    applyPatches(Process.getModuleByName(img));
} catch (e) {
    const obs = Process.attachModuleObserver({
        onAdded: m => { if (m.name === img) { applyPatches(m); obs.detach(); } }
    });
}
"""
JS_CODE = None

def kill_process_tree_by_parent_ppid(root_ppid):
    try:
        procs = list(psutil.process_iter(attrs=['pid', 'ppid', 'name']))
    except:
        return
    children = {}
    for p in procs:
        children.setdefault(p.info['ppid'], []).append(p)
    visited = set()

    def walk(ppid):
        if ppid in visited:
            return
        visited.add(ppid)
        for child in children.get(ppid, []):
            walk(child.info['pid'])
            pid = child.info['pid']
            name = child.info.get('name', '?')
            print(f"{CYA} └─ killed {name} ({pid}){RES}")
            try:
                child.terminate()
                child.wait(2)
            except:
                try: child.kill()
                except: pass
    walk(root_ppid)

def on_message(msg, _):
    if msg["type"] == "send":
        payload = msg["payload"]
        if payload.startswith("PATCH"):
            _, t, addr = payload.split("|")
            print(f"{MAG} • patching {t} @ {addr}{RES}")
        elif payload.startswith("OK"):
            _, t = payload.split("|")
            print(f"{GRE}   ✓ {t} patched{RES}")
    else:
        print(f"{RED}{msg}{RES}")

def find_pid_by_name(device, name):
    name = name.lower()
    for p in device.enumerate_processes():
        if p.name.lower() == name:
            return p.pid
    return None

def attach_and_monitor(dev, pid):
    global JS_CODE
    session = None
    script = None
    done = threading.Event()
    reason = None

    def on_det(r):
        nonlocal reason
        reason = r
        print(f"{RED}[detach] {r}{RES}")
        done.set()
    try:
        print(f"{YEL}[attach] PID {pid}{RES}")
        try:
            session = dev.attach(pid)
            session.on('detached', on_det)
        except Exception as e:
            print(f"{RED}[error] attach failed: {e}{RES}")
            return
        try:
            script = session.create_script(JS_CODE)
            script.on("message", on_message)
            script.load()
        except Exception as e:
            print(f"{RED}[error] script load failed: {e}{RES}")
            try: session.detach()
            except: pass
            return
        while not done.is_set():
            time.sleep(0.25)
        if isinstance(reason, str) and reason.startswith("process-"):
            print(f"{RED}[exit] process terminated → cleaning tree{RES}")
            kill_process_tree_by_parent_ppid(pid)
    finally:
        try:
            if script: script.unload()
        except: pass
        try:
            if session: session.detach()
        except: pass

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--no-splash", action="store_true")
    return p.parse_args()

def main():
    global JS_CODE
    args = parse_args()
    splash_disabled = args.no_splash
    JS_CODE = __.replace(
        "__",
        "true" if splash_disabled else "false"
    )
    print(f"\n{GRE}Waiting for Process : {TARGET_EXE} {RES}")
    dev = frida.get_local_device()
    try:
        while True:
            pid = find_pid_by_name(dev, TARGET_EXE)
            if pid is None:
                time.sleep(0.4)
                continue
            attach_and_monitor(dev, pid)
            time.sleep(0.4)
    except KeyboardInterrupt:
        print(f"{RED}\nexiting…{RES}")
        sys.exit(0)
        
if __name__ == "__main__":
    main()