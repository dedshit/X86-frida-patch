import frida
import time
import sys

MAIN_PROCESS_NAME = "Adobe Premiere Pro.exe"
LIC_PROCESS_NAME = "adobe_licensing_wf.exe"

JS_LIC = r"""'use strict';
let user32 = null;
for (const m of Process.enumerateModules()) {
    if (m.name.toLowerCase() === "user32.dll") {
        user32 = m;
        break;
    }
}
if (!user32) throw new Error("user32.dll unavailable");
function getExportAddress(mod, name) {
    const base = mod.base;
    const pe = base.add(0x3C).readU32();
    const exportDirRva = base.add(pe + 0x88).readU32();
    const exportDir = base.add(exportDirRva);
    const numNames = exportDir.add(0x18).readU32();
    const namesRva = exportDir.add(0x20).readU32();
    const ordinalsRva = exportDir.add(0x24).readU32();
    const funcsRva = exportDir.add(0x1C).readU32();
    for (let i = 0; i < numNames; i++) {
        const nameRva = base.add(namesRva + i * 4).readU32();
        const fname = base.add(nameRva).readUtf8String();
        if (fname === name) {
            const ord = base.add(ordinalsRva + i * 2).readU16();
            const funcRva = base.add(funcsRva + ord * 4).readU32();
            return base.add(funcRva);
        }
    }
    return ptr(0);
}
const procLabel = (Process.enumerateModules()[0].name || "Process").replace(/\.exe$/i, "");
function log(msg) {
    send(procLabel + ": " + msg);
}
const showWindowPtr = getExportAddress(user32, "ShowWindow");
if (showWindowPtr.isNull()) throw new Error("ShowWindow not found");
const ShowWindow = new NativeFunction(showWindowPtr, "bool", ["pointer","int"]);
const SW_HIDE = 0;
let licModule = null;
for (const m of Process.enumerateModules()) {
    if (m.name.toLowerCase() === "adobe_licensing_wf.exe") {
        licModule = m;
        break;
    }
}
if (licModule === null) {
    licModule = Process.enumerateModules()[0];
    log("adobe_licensing_wf module not found by name, using " + licModule.name);
} else {
    log("Using module " + licModule.name);
}
const WINPROC_OFFSET = 0x10a9f0;
const WinProc = licModule.base.add(WINPROC_OFFSET);
log("Window procedure located at " + WinProc);
Interceptor.attach(WinProc, {
    onEnter(args) {
        const hwnd = args[0];
        if (!hwnd.isNull()) {
            ShowWindow(hwnd, SW_HIDE);
        }
    }
});
log("Hook installed successfully");
"""

JS_MAIN = r"""'use strict';
const TARGET_CLASS = "Premiere Pro";
const TARGET_TITLE = "Adobe Premiere Pro 2025";
const INITIAL_DELAY_MS = 1000;
const SCAN_INTERVAL_MS = 1000;
const MAX_SCAN_TRIES = 120;
const MAX_ENABLE_TRIES = 600;

const procLabel = (Process.enumerateModules()[0].name || "Process").replace(/\.exe$/i, "");
function log(msg) {
    send(procLabel + ": " + msg);
}

let apisResolved = false;
let GetTopWindow = null;
let GetWindow = null;
let GetClassNameW = null;
let GetWindowTextW = null;
let GetWindowThreadProcessId = null;
let EnableWindow = null;
const GW_HWNDNEXT = 2;

function getExportAddress(moduleName, exportName) {
    const mod = Process.getModuleByName(moduleName);
    const exps = mod.enumerateExports();
    for (let i = 0; i < exps.length; i++) {
        const e = exps[i];
        if (e.name === exportName) {
            return e.address;
        }
    }
    return ptr(0);
}

function resolveApis() {
    if (apisResolved) return true;
    try {
        Process.getModuleByName("user32.dll");
        let addr;
        addr = getExportAddress("user32.dll", "GetTopWindow");
        if (addr.isNull()) throw new Error("GetTopWindow not found");
        GetTopWindow = new NativeFunction(addr, "pointer", ["pointer"]);
        addr = getExportAddress("user32.dll", "GetWindow");
        if (addr.isNull()) throw new Error("GetWindow not found");
        GetWindow = new NativeFunction(addr, "pointer", ["pointer", "uint32"]);
        addr = getExportAddress("user32.dll", "GetClassNameW");
        if (addr.isNull()) throw new Error("GetClassNameW not found");
        GetClassNameW = new NativeFunction(addr, "int", ["pointer", "pointer", "int"]);
        addr = getExportAddress("user32.dll", "GetWindowTextW");
        if (addr.isNull()) throw new Error("GetWindowTextW not found");
        GetWindowTextW = new NativeFunction(addr, "int", ["pointer", "pointer", "int"]);
        addr = getExportAddress("user32.dll", "GetWindowThreadProcessId");
        if (addr.isNull()) throw new Error("GetWindowThreadProcessId not found");
        GetWindowThreadProcessId = new NativeFunction(addr, "uint32", ["pointer", "pointer"]);
        addr = getExportAddress("user32.dll", "EnableWindow");
        if (addr.isNull()) throw new Error("EnableWindow not found");
        EnableWindow = new NativeFunction(addr, "bool", ["pointer", "bool"]);
        apisResolved = true;
        return true;
    } catch (e) {
        log("API binding failed: " + e.message);
        return false;
    }
}

function findTargetWindow() {
    if (!apisResolved) {
        log("API bindings not ready, skipping scan");
        return ptr(0);
    }
    let hwnd = GetTopWindow(ptr(0));
    let targetHwnd = ptr(0);
    while (!hwnd.isNull()) {
        const pidBuf = Memory.alloc(4);
        GetWindowThreadProcessId(hwnd, pidBuf);
        const pid = pidBuf.readU32();
        if (pid === Process.id) {
            const clsBuf = Memory.alloc(256 * 2);
            GetClassNameW(hwnd, clsBuf, 256);
            const cls = clsBuf.readUtf16String() || "";
            const txtBuf = Memory.alloc(512 * 2);
            GetWindowTextW(hwnd, txtBuf, 512);
            const title = txtBuf.readUtf16String() || "";
            if (cls === TARGET_CLASS && title === TARGET_TITLE) {
                targetHwnd = hwnd;
                break;
            }
        }
        hwnd = GetWindow(hwnd, GW_HWNDNEXT);
    }
    return targetHwnd;
}

function startWindowSearch() {
    let scanTries = 0;
    let enableTries = 0;
    let targetHwnd = ptr(0);
    function tick() {
        if (!resolveApis()) {
            setTimeout(tick, 500);
            return;
        }
        if (targetHwnd.isNull()) {
            scanTries++;
            log("Scanning for target window");
            targetHwnd = findTargetWindow();
            if (targetHwnd.isNull()) {
                if (scanTries >= MAX_SCAN_TRIES) {
                    log("Target window not found, aborting operation");
                    return;
                }
                setTimeout(tick, SCAN_INTERVAL_MS);
                return;
            }
            log("Target window discovered (HWND=" + targetHwnd + ")");
        }
        enableTries++;
        log("Apply EnableWindow(TRUE)");
        const prevState = EnableWindow(targetHwnd, 1);
        if (prevState) {
            log("Operation completed successfully");
            return;
        }
        if (enableTries >= MAX_ENABLE_TRIES) {
            log("Maximum EnableWindow attempts reached, aborting operation");
            return;
        }
        setTimeout(tick, SCAN_INTERVAL_MS);
    }
    setTimeout(tick, INITIAL_DELAY_MS);
}

function validateProductLicense() {
    const mod = Process.getModuleByName("Registration.dll");
    const addr = mod.base.add(0xCBE87A);
    const ok = Memory.protect(addr, 1, "rw-");
    if (!ok) {
        log("Failed to change protection");
        return;
    }
    addr.writeU8(0x1);
    log("Patched validateProductLicense @ 0xCBE87A");
}

validateProductLicense();
startWindowSearch();
"""

def colorize(msg):
    lower = msg.lower()
    if "failed" in lower or "not found" in lower or "aborting" in lower or "maximum" in lower:
        return "\033[31m" + msg + "\033[0m"
    if "completed successfully" in lower or "discovered" in lower or "hook installed successfully" in lower:
        return "\033[32m" + msg + "\033[0m"
    if "patched" in lower or "scanning" in lower:
        return "\033[36m" + msg + "\033[0m"
    if msg.startswith("[*]") or msg.startswith("[+]"):
        return "\033[35m" + msg + "\033[0m"
    return msg

def on_message(message, data):
    if message["type"] == "send":
        print(colorize(message["payload"]))
    elif message["type"] == "error":
        print("\033[31m[JS ERROR]\033[0m")
        if "stack" in message:
            print(message["stack"])
        else:
            print(message)

def wait_for_process(device, name: str):
    print(colorize(f"[*] Waiting for process: {name}"))
    while True:
        for proc in device.enumerate_processes():
            if proc.name.lower() == name.lower():
                print(colorize(f"[+] Found process {name} (PID {proc.pid})"))
                return proc
        time.sleep(0.5)

def main():
    device = frida.get_local_device()
    main_proc = wait_for_process(device, MAIN_PROCESS_NAME)
    main_pid = main_proc.pid
    lic_proc = wait_for_process(device, LIC_PROCESS_NAME)
    lic_pid = lic_proc.pid
    print(colorize(f"[*] Attaching to {LIC_PROCESS_NAME} (PID {lic_pid})"))
    session_lic = device.attach(lic_pid)
    script_lic = session_lic.create_script(JS_LIC)
    script_lic.on("message", on_message)
    script_lic.load()
    print(colorize(f"[*] Attaching to {MAIN_PROCESS_NAME} (PID {main_pid})"))
    session_main = device.attach(main_pid)
    script_main = session_main.create_script(JS_MAIN)
    script_main.on("message", on_message)
    script_main.load()
    print(colorize("[*] Hooks installed. Press Enter or Ctrl+C to detach"))
    try:
        sys.stdin.read()
    except KeyboardInterrupt:
        pass
    finally:
        try:
            session_main.detach()
        except Exception:
            pass
        try:
            session_lic.detach()
        except Exception:
            pass
        print(colorize("[*] Detached, exiting"))

if __name__ == "__main__":
    main()