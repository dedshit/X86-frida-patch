import frida
import time
import sys
import os
from datetime import datetime

def check_terminal_support():
    try:
        if os.name == 'nt':
            import ctypes
            kernel32 = ctypes.windll.kernel32
            mode = ctypes.c_uint32()
            handle = kernel32.GetStdHandle(-11)
            if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
                return (mode.value & 0x0004) != 0
        return True
    except Exception:
        return False
        
TARGET_PROCESS = "DouWan.exe"
COLOR_SUPPORT = check_terminal_support()
JS_PAYLOAD = """
'use strict';
const TARGET_TEXT = "DouWan";
const REQUIRED_DLL = "usp10.dll";
let isHookActive = false;
const originalConsoleLog = console.log;
console.log = function(message) {
    send(message);
    originalConsoleLog.apply(console, arguments);
};

function ScriptShapeHook() {
    try {
        const dllModule = Process.getModuleByName(REQUIRED_DLL);
        const scriptShapeFunc = dllModule.getExportByName("ScriptShape");
        if (scriptShapeFunc.isNull()) {
            send("[-] Failed to locate ScriptShape");
            return false;
        }
        send("[+] Hooked ScriptShape @ " + scriptShapeFunc);
        Interceptor.attach(scriptShapeFunc, {
            onEnter: function(args) {
                const textPointer = args[2];
                const textLength = args[3].toInt32();
                if (textPointer.isNull() || textLength <= 0) return;
                const currentText = textPointer.readUtf16String(textLength);
                const targetIndex = currentText.indexOf(TARGET_TEXT);
                if (targetIndex === -1) return;
                for (let i = 0; i < TARGET_TEXT.length && (targetIndex + i) < textLength; i++) {
                    const charPosition = textPointer.add(2 * (targetIndex + i));
                    charPosition.writeU16(0x0020);
                }
            }
        });
        send("[+] Watermark Removed");
        return true;
    } catch (err) {
        send("[-] Hook setup failed: " + err.message);
        return false;
    }
}

function RecordLimitHook() {
    const mainModule = Process.getModuleByName("DouWan.exe");
    const functionAddress = mainModule.base.add(0x19D50);
    send("[+] Hook attached to time-limit handler  @ " + functionAddress);
    Interceptor.attach(functionAddress, {
        onEnter: function(args) {
            Stalker.follow(Process.getCurrentThreadId(), {
                transform: function(iterator) {
                    let instruction = iterator.next();
                    do {
                        if (instruction.address.equals(functionAddress.add(0x8b))) {
                            iterator.putCallout(function(context) {
                                context.r14 = 0x0;
                            });
                        }
                        iterator.keep();
                    } while ((instruction = iterator.next()) !== null);
                }
            });
        },
        onLeave: function(retval) {
            Stalker.unfollow(Process.getCurrentThreadId());
        }
    });
    send("[+] Bypassed record limit");
}

function monitorForDllLoad() {
    let attemptCount = 0;
    function checkForDll() {
        attemptCount++;
        try {
            Process.getModuleByName(REQUIRED_DLL);
            if (ScriptShapeHook()) {
                isHookActive = true;
                return;
            }
        } catch (e) {
        }
        setTimeout(checkForDll, 1000);
    }
    setTimeout(checkForDll, 1000);
}
monitorForDllLoad();
RecordLimitHook();
"""

def get_current_time():
    return datetime.now().strftime("%H:%M:%S")

def format_message(message):
    if not COLOR_SUPPORT:
        return message
    message_lower = message.lower()
    if any(word in message_lower for word in ["failed", "error", "[-]"]):
        return "\033[91m" + message + "\033[0m"
    elif any(word in message_lower for word in ["[+]", "active"]):
        return "\033[92m" + message + "\033[0m"
    elif any(word in message_lower for word in ["[*]", "monitoring"]):
        return "\033[34m" + message + "\033[0m"
        
    return message

def handle_frida_message(message, data):
    if message["type"] == "send":
        print(format_message(f"[{get_current_time()}] {message['payload']}"))
    elif message["type"] == "error":
        error_color = "\033[31m" if COLOR_SUPPORT else ""
        reset_color = "\033[0m" if COLOR_SUPPORT else ""
        print(f"{error_color}[{get_current_time()}] [ERROR]{reset_color} {str(message)}")

class ProcessWatcher:
    def __init__(self, target_process, javascript_payload):
        self.target_name = target_process
        self.js_payload = javascript_payload
        self.frida_device = frida.get_local_device()
        self.active_session = None
        self.active_script = None
        self.is_running = False
        
    def check_process_alive(self, process_id):
        try:
            for proc in self.frida_device.enumerate_processes():
                if proc.pid == process_id:
                    return True
            return False
        except Exception:
            return False
            
    def locate_target_process(self):
        for process in self.frida_device.enumerate_processes():
            if process.name.lower() == self.target_name.lower():
                return process
        return None
        
    def inject_into_process(self, process):
        try:
            print(format_message(f"[{get_current_time()}] [*] Attaching to {self.target_name} (PID {process.pid})"))
            self.active_session = self.frida_device.attach(process.pid)
            self.active_script = self.active_session.create_script(self.js_payload)
            self.active_script.on("message", handle_frida_message)
            self.active_script.load()
            return True
        except Exception as e:
            print(format_message(f"[{get_current_time()}] [-] Attachment failed: {e}"))
            return False
            
    def cleanup_session(self):
        if self.active_session:
            try:
                self.active_session.detach()
                self.active_session = None
                self.active_script = None
            except Exception:
                pass
                
    def start_monitoring(self):
        self.is_running = True
        current_process_id = None
        terminal_type = "CMD" if not COLOR_SUPPORT else "PowerShell/Terminal"
        while self.is_running:
            try:
                if current_process_id and self.check_process_alive(current_process_id):
                    time.sleep(2)
                    continue
                if current_process_id:
                    print(format_message(f"[{get_current_time()}] [-] Process terminated (PID {current_process_id})\n\n"))
                    self.cleanup_session()
                    current_process_id = None
                target_process = self.locate_target_process()
                if target_process:
                    if self.inject_into_process(target_process):
                        current_process_id = target_process.pid
                        print(format_message(f"[{get_current_time()}] [*] Monitoring active for PID {current_process_id}"))
                    else:
                        time.sleep(3)
                else:
                    time.sleep(2)
            except KeyboardInterrupt:
                self.is_running = False
                break
            except Exception as e:
                print(format_message(f"[{get_current_time()}] [-] Monitor error: {e}"))
                time.sleep(3)
        self.cleanup_session()

def main():
    target_app = sys.argv[1] if len(sys.argv) > 1 else TARGET_PROCESS
    print(format_message(f"[{get_current_time()}] [*] Waiting for process : {target_app}"))
    try:
        watcher = ProcessWatcher(target_app, JS_PAYLOAD)
        watcher.start_monitoring()
    except Exception as e:
        print(format_message(f"[{get_current_time()}] [-] Service error: {e}"))

if __name__ == "__main__":

    main()
